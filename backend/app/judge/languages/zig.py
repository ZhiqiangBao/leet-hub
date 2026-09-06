from __future__ import annotations

import os
from pathlib import Path

from ..base import CompileResult, LanguageAdapter
from ..sandbox import run_limited
from .bins import find_tool
from .idents import inner_list
from .versions import fmt_version, zig_flavor, zig_version

# Ubuntu 26.04 `apt install zig` provides Zig 0.14.x (zig-defaults → zig0.14).


def zig_type(type_name: str, *, ret: bool = False) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        if inner == "str":
            return "[][]const u8" if ret else "[]const []const u8"
        leaf = {"int": "i32", "long": "i64", "float": "f64", "bool": "bool"}[inner]
        return f"[]{leaf}" if ret else f"[]const {leaf}"
    if t == "str":
        return "[]const u8"
    return {"int": "i32", "long": "i64", "float": "f64", "bool": "bool"}[t]


def zig_from(type_name: str) -> str:
    return "leetFrom_" + type_name.replace("[", "_").replace("]", "")


def zig_to(type_name: str) -> str:
    return "leetTo_" + type_name.replace("[", "_").replace("]", "")


def needs_alloc(type_name: str) -> bool:
    return inner_list(type_name) is not None


def call_from(type_name: str, expr: str) -> str:
    fn = zig_from(type_name)
    if needs_alloc(type_name):
        return f"try {fn}(alloc, {expr})"
    return f"try {fn}({expr})"


def call_to(type_name: str, expr: str) -> str:
    fn = zig_to(type_name)
    if needs_alloc(type_name):
        return f"try {fn}(alloc, {expr})"
    return f"{fn}({expr})"


def emit_zig_converters(types: list[str], flavor: str = "14") -> str:
    seen: set[str] = set()
    chunks: list[str] = []

    def emit(type_name: str) -> None:
        if type_name in seen:
            return
        inner = inner_list(type_name)
        if inner is not None:
            emit(inner)
        seen.add(type_name)
        fn = zig_from(type_name)
        toj = zig_to(type_name)
        if type_name == "int":
            chunks.append(
                "fn leetFrom_int(v: std.json.Value) !i32 {\n"
                "    return switch (v) {\n"
                "        .integer => |n| @intCast(n),\n"
                "        .float => |n| @intFromFloat(n),\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_int(v: i32) std.json.Value {\n"
                "    return .{ .integer = @as(i64, v) };\n"
                "}"
            )
        elif type_name == "long":
            chunks.append(
                "fn leetFrom_long(v: std.json.Value) !i64 {\n"
                "    return switch (v) {\n"
                "        .integer => |n| n,\n"
                "        .float => |n| @intFromFloat(n),\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_long(v: i64) std.json.Value {\n"
                "    return .{ .integer = v };\n"
                "}"
            )
        elif type_name == "float":
            chunks.append(
                "fn leetFrom_float(v: std.json.Value) !f64 {\n"
                "    return switch (v) {\n"
                "        .integer => |n| @floatFromInt(n),\n"
                "        .float => |n| n,\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_float(v: f64) std.json.Value {\n"
                "    return .{ .float = v };\n"
                "}"
            )
        elif type_name == "bool":
            chunks.append(
                "fn leetFrom_bool(v: std.json.Value) !bool {\n"
                "    return switch (v) {\n"
                "        .bool => |b| b,\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_bool(v: bool) std.json.Value {\n"
                "    return .{ .bool = v };\n"
                "}"
            )
        elif type_name == "str":
            chunks.append(
                "fn leetFrom_str(v: std.json.Value) ![]const u8 {\n"
                "    return switch (v) {\n"
                "        .string => |s| s,\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_str(v: []const u8) std.json.Value {\n"
                "    return .{ .string = v };\n"
                "}"
            )
        else:
            assert inner is not None
            zt = zig_type(type_name, ret=True)
            inner_zt = zig_type(inner, ret=True)
            inner_from = call_from(inner, "item")
            inner_to = call_to(inner, "item")
            if flavor == "16":
                arr_init = "    var arr: std.ArrayList(std.json.Value) = .empty;"
                arr_append = f"        try arr.append(alloc, {inner_to});"
            else:
                arr_init = "    var arr = std.ArrayList(std.json.Value).init(alloc);"
                arr_append = f"        try arr.append({inner_to});"
            chunks.append(
                f"fn {fn}(alloc: std.mem.Allocator, v: std.json.Value) !{zt} {{\n"
                f"    const arr = switch (v) {{\n"
                f"        .array => |a| a,\n"
                f"        else => return error.BadJson,\n"
                f"    }};\n"
                f"    const out = try alloc.alloc({inner_zt}, arr.items.len);\n"
                f"    for (arr.items, 0..) |item, i| {{\n"
                f"        out[i] = {inner_from};\n"
                f"    }}\n"
                f"    return out;\n"
                f"}}\n"
                f"fn {toj}(alloc: std.mem.Allocator, v: {zt}) !std.json.Value {{\n"
                f"{arr_init}\n"
                f"    for (v) |item| {{\n"
                f"{arr_append}\n"
                f"    }}\n"
                f"    return .{{ .array = arr }};\n"
                f"}}"
            )

    for t in types:
        emit(t)
    return "\n\n".join(chunks)


def zig_runtime_bits(flavor: str) -> dict[str, str]:
    if flavor == "16":
        return {
            "dump_new": "    var out: std.ArrayList(u8) = .empty;",
            "dump_push": "    try out.appendSlice(alloc, s);",
            "dump_owned": "    return out.toOwnedSlice(alloc);",
            "tests_new": "    var tests: std.ArrayList([]const u8) = .empty;",
            "tests_append": "        try tests.append(alloc, line);",
            "stdin": "    const data = try std.fs.File.stdin().readToEndAlloc(alloc, 32 * 1024 * 1024);",
            "stdout": (
                "    _ = try std.fs.File.stdout().write(s);\n"
                '    _ = try std.fs.File.stdout().write("\\n");'
            ),
        }
    if flavor == "15":
        return {
            "dump_new": "    var out = std.ArrayList(u8).init(alloc);",
            "dump_push": "    try out.appendSlice(s);",
            "dump_owned": "    return out.toOwnedSlice();",
            "tests_new": "    var tests = std.ArrayList([]const u8).init(alloc);",
            "tests_append": "        try tests.append(line);",
            "stdin": "    const data = try std.fs.File.stdin().readToEndAlloc(alloc, 32 * 1024 * 1024);",
            "stdout": (
                "    try std.fs.File.stdout().writeAll(s);\n"
                '    try std.fs.File.stdout().writeAll("\\n");'
            ),
        }
    return {
        "dump_new": "    var out = std.ArrayList(u8).init(alloc);",
        "dump_push": "    try out.appendSlice(s);",
        "dump_owned": "    return out.toOwnedSlice();",
        "tests_new": "    var tests = std.ArrayList([]const u8).init(alloc);",
        "tests_append": "        try tests.append(line);",
        "stdin": "    const data = try std.io.getStdIn().reader().readAllAlloc(alloc, 32 * 1024 * 1024);",
        "stdout": '    try std.io.getStdOut().writer().print("{s}\\n", .{s});',
    }


def zig_helpers(flavor: str) -> str:
    b = zig_runtime_bits(flavor)
    return f'''
fn leetClose(a: std.json.Value, b: std.json.Value) bool {{
    return switch (a) {{
        .null => b == .null,
        .bool => |x| switch (b) {{ .bool => |y| x == y, else => false }},
        .integer => |x| switch (b) {{
            .integer => |y| x == y,
            .float => |y| blk: {{
                const xf: f64 = @floatFromInt(x);
                const d = @abs(xf - y);
                break :blk d <= 1e-6 or d <= 1e-6 * @max(@abs(xf), @abs(y));
            }},
            else => false,
        }},
        .float => |x| switch (b) {{
            .integer => |y| blk: {{
                const yf: f64 = @floatFromInt(y);
                const d = @abs(x - yf);
                break :blk d <= 1e-6 or d <= 1e-6 * @max(@abs(x), @abs(yf));
            }},
            .float => |y| blk: {{
                const d = @abs(x - y);
                break :blk d <= 1e-6 or d <= 1e-6 * @max(@abs(x), @abs(y));
            }},
            else => false,
        }},
        .string => |x| switch (b) {{ .string => |y| std.mem.eql(u8, x, y), else => false }},
        .array => |x| switch (b) {{
            .array => |y| blk: {{
                if (x.items.len != y.items.len) break :blk false;
                for (x.items, y.items) |p, q| {{
                    if (!leetClose(p, q)) break :blk false;
                }}
                break :blk true;
            }},
            else => false,
        }},
        else => false,
    }};
}}

fn leetPush(alloc: std.mem.Allocator, out: *std.ArrayList(u8), s: []const u8) !void {{
{"" if flavor == "16" else "    _ = alloc;"}
    {"try out.appendSlice(alloc, s);" if flavor == "16" else "try out.appendSlice(s);"}
}}

fn leetDump(alloc: std.mem.Allocator, v: std.json.Value) ![]u8 {{
{b["dump_new"]}
    try leetDumpInto(alloc, &out, v);
{b["dump_owned"]}
}}

fn leetDumpInto(alloc: std.mem.Allocator, out: *std.ArrayList(u8), v: std.json.Value) !void {{
    switch (v) {{
        .null => try leetPush(alloc, out, "null"),
        .bool => |flag| try leetPush(alloc, out, if (flag) "true" else "false"),
        .integer => |n| {{
            var buf: [32]u8 = undefined;
            const s = std.fmt.bufPrint(&buf, "{{d}}", .{{n}}) catch unreachable;
            try leetPush(alloc, out, s);
        }},
        .float => |n| {{
            var buf: [64]u8 = undefined;
            const s = std.fmt.bufPrint(&buf, "{{d}}", .{{n}}) catch unreachable;
            try leetPush(alloc, out, s);
        }},
        .number_string => |s| try leetPush(alloc, out, s),
        .string => |s| {{
            try leetPush(alloc, out, "\\"");
            try leetPush(alloc, out, s);
            try leetPush(alloc, out, "\\"");
        }},
        .array => |a| {{
            try leetPush(alloc, out, "[");
            for (a.items, 0..) |item, i| {{
                if (i != 0) try leetPush(alloc, out, ",");
                try leetDumpInto(alloc, out, item);
            }}
            try leetPush(alloc, out, "]");
        }},
        .object => |o| {{
            try leetPush(alloc, out, "{{");
            var first = true;
            var it = o.iterator();
            while (it.next()) |kv| {{
                if (!first) try leetPush(alloc, out, ",");
                first = false;
                try leetPush(alloc, out, "\\"");
                try leetPush(alloc, out, kv.key_ptr.*);
                try leetPush(alloc, out, "\\":");
                try leetDumpInto(alloc, out, kv.value_ptr.*);
            }}
            try leetPush(alloc, out, "}}");
        }},
    }}
}}

fn leetEq(alloc: std.mem.Allocator, got: std.json.Value, expected: std.json.Value, any_order: bool) !bool {{
    if (any_order) {{
        switch (got) {{
            .array => |g| switch (expected) {{
                .array => |e| {{
                    if (g.items.len != e.items.len) return false;
                    const gs = try alloc.alloc([]u8, g.items.len);
                    const es = try alloc.alloc([]u8, e.items.len);
                    for (g.items, 0..) |item, i| gs[i] = try leetDump(alloc, item);
                    for (e.items, 0..) |item, i| es[i] = try leetDump(alloc, item);
                    const less = struct {{
                        fn f(_: void, a: []u8, b: []u8) bool {{
                            return std.mem.lessThan(u8, a, b);
                        }}
                    }}.f;
                    std.mem.sort([]u8, gs, {{}}, less);
                    std.mem.sort([]u8, es, {{}}, less);
                    for (gs, es) |a, b| {{
                        if (!std.mem.eql(u8, a, b)) return false;
                    }}
                    return true;
                }},
                else => {{}},
            }},
            else => {{}},
        }}
    }}
    return leetClose(got, expected);
}}

fn leetWrite(alloc: std.mem.Allocator, v: std.json.Value) !void {{
    const s = try leetDump(alloc, v);
{b["stdout"]}
}}
'''


def wrap_zig(user_code: str, signature: dict, flavor: str = "14") -> str:
    method = signature["method"]
    class_name = signature.get("class_name") or "Solution"
    compare = signature.get("compare") or "exact"
    params = signature.get("params") or []
    return_type = signature["return_type"]
    types = [p["type"] for p in params] + [return_type]
    converters = emit_zig_converters(types, flavor)
    bits = zig_runtime_bits(flavor)
    helpers = zig_helpers(flavor)
    bind_lines = []
    call_args = []
    for i, p in enumerate(params):
        bind_lines.append(
            f"            const arg{i} = {call_from(p['type'], f'args.items[{i}]')};"
        )
        call_args.append(f"arg{i}")
    bind = "\n".join(bind_lines)
    call = ", ".join(call_args)
    any_order = "true" if compare == "any_order" else "false"
    to_got = call_to(return_type, "got")
    body = user_code.rstrip()
    if '@import("std")' not in body and "@import(\"std\")" not in body:
        body = 'const std = @import("std");\n\n' + body
    return f'''{body}

{converters}

{helpers}

pub fn main() !void {{
    var gpa = std.heap.GeneralPurposeAllocator(.{{}}){{}};
    defer _ = gpa.deinit();
    const alloc = gpa.allocator();
{bits["stdin"]}
{bits["tests_new"]}
    var it = std.mem.splitScalar(u8, data, '\\n');
    while (it.next()) |raw| {{
        const line = std.mem.trim(u8, raw, " \\r");
        if (line.len == 0) continue;
{bits["tests_append"]}
    }}
    const total: i64 = @intCast(tests.items.len);
    const sol = {class_name}{{}};
    for (tests.items, 0..) |line, index| {{
        var parsed = std.json.parseFromSlice(std.json.Value, alloc, line, .{{}}) catch {{
            try leetWrite(alloc, .{{ .object = blk: {{
                var o = std.json.ObjectMap.init(alloc);
                try o.put("verdict", .{{ .string = "RE" }});
                try o.put("message", .{{ .string = "json parse" }});
                break :blk o;
            }} }});
            return;
        }};
        defer parsed.deinit();
        const obj = parsed.value.object;
        const args_v = obj.get("args") orelse return error.MissingArgs;
        const expected = obj.get("expected") orelse return error.MissingExpected;
        const args = switch (args_v.*) {{
            .array => |a| a,
            else => return error.BadArgs,
        }};
{bind}
        const got = sol.{method}({call});
        const gotj = {to_got};
        if (!try leetEq(alloc, gotj, expected.*, {any_order})) {{
            var o = std.json.ObjectMap.init(alloc);
            try o.put("verdict", .{{ .string = "WA" }});
            try o.put("failed_index", .{{ .integer = @intCast(index) }});
            try o.put("got", gotj);
            try o.put("passed", .{{ .integer = @intCast(index) }});
            try o.put("total", .{{ .integer = total }});
            try leetWrite(alloc, .{{ .object = o }});
            return;
        }}
    }}
    var o = std.json.ObjectMap.init(alloc);
    try o.put("verdict", .{{ .string = "AC" }});
    try o.put("passed", .{{ .integer = total }});
    try o.put("total", .{{ .integer = total }});
    try leetWrite(alloc, .{{ .object = o }});
}}
'''


class ZigAdapter(LanguageAdapter):
    id = "zig"
    display_name = "Zig"
    source_filename = "solution.zig"
    implemented = True

    def zig_bin(self) -> str | None:
        return find_tool("zig", linux_paths=("/usr/bin/zig", "/usr/local/bin/zig"))

    def detect(self) -> bool:
        return self.zig_bin() is not None

    def runtime_version(self) -> str | None:
        path = self.zig_bin()
        return fmt_version(zig_version(path)) if path else None

    def wrap(self, user_code: str, signature: dict) -> str:
        path = self.zig_bin()
        flavor = zig_flavor(zig_version(path) if path else None)
        return wrap_zig(user_code, signature, flavor)

    def compile(self, workdir: str) -> CompileResult:
        compiler = self.zig_bin()
        if not compiler:
            return CompileResult(ok=False, log="zig not found")
        out = "program.exe" if os.name == "nt" else "program"
        result = run_limited(
            [compiler, "build-exe", self.source_filename, "-O", "ReleaseFast", f"-femit-bin={out}"],
            cwd=Path(workdir),
            stdin="",
            time_ms=30000,
            memory_mb=4096,
            for_compile=True,
        )
        if result.tle:
            return CompileResult(ok=False, log="compile timeout")
        if result.returncode != 0:
            return CompileResult(ok=False, log=(result.stderr or result.stdout)[-8000:])
        return CompileResult(ok=True)

    def run_argv(self, workdir: str) -> list[str]:
        exe = Path(workdir) / ("program.exe" if os.name == "nt" else "program")
        if not exe.exists():
            exe = Path(workdir) / "program"
        return [str(exe)]
