from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ..base import CompileResult, LanguageAdapter
from ..sandbox import run_limited

JSON_HEADER = Path(__file__).resolve().parents[1] / "runtimes" / "c" / "json.h"


def _emit_arg(index: int, type_name: str, name: str) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    call: list[str] = []
    src = f"json_at(args, {index})"
    if type_name == "int":
        lines.append(f"        int {name} = json_as_int({src});")
        call.append(name)
    elif type_name == "float":
        lines.append(f"        double {name} = json_as_double({src});")
        call.append(name)
    elif type_name == "bool":
        lines.append(f"        bool {name} = json_as_bool({src});")
        call.append(name)
    elif type_name == "str":
        lines.append(f"        char* {name} = json_as_cstr({src});")
        call.append(name)
    elif type_name == "List[int]":
        lines.append(f"        int {name}Size = 0;")
        lines.append(f"        int* {name} = json_as_int_array({src}, &{name}Size);")
        call.extend([name, f"{name}Size"])
    elif type_name == "List[str]":
        lines.append(f"        int {name}Size = 0;")
        lines.append(f"        char** {name} = json_as_str_array({src}, &{name}Size);")
        call.extend([name, f"{name}Size"])
    else:
        raise ValueError(f"unsupported C type: {type_name}")
    return lines, call


def _emit_call(method: str, params: list[dict], return_type: str) -> str:
    prep: list[str] = []
    call: list[str] = []
    for i, p in enumerate(params):
        extra, names = _emit_arg(i, p["type"], p["name"])
        prep.extend(extra)
        call.extend(names)
    joined = ", ".join(call)
    if return_type == "List[int]":
        prep.append("        int returnSize = 0;")
        prep.append(f"        int* got = {method}({joined}{', ' if joined else ''}&returnSize);")
        prep.append("        JsonValue gotj = json_from_int_array(got, returnSize);")
    elif return_type == "int":
        prep.append(f"        int got = {method}({joined});")
        prep.append("        JsonValue gotj = json_from_int(got);")
    elif return_type == "float":
        prep.append(f"        double got = {method}({joined});")
        prep.append("        JsonValue gotj = json_num(got);")
    elif return_type == "bool":
        prep.append(f"        bool got = {method}({joined});")
        prep.append("        JsonValue gotj = json_from_bool(got);")
    elif return_type == "str":
        prep.append(f"        char* got = {method}({joined});")
        prep.append("        JsonValue gotj = json_from_cstr(got);")
    else:
        raise ValueError(f"unsupported C return type: {return_type}")
    return "\n".join(prep)


def wrap_c(user_code: str, signature: dict) -> str:
    method = signature["method"]
    compare = signature.get("compare") or "exact"
    params = signature.get("params") or []
    return_type = signature["return_type"]
    any_order = "true" if compare == "any_order" else "false"
    body = _emit_call(method, params, return_type)
    return f'''#include "json.h"

{user_code.rstrip()}

int main(void) {{
    char line[1 << 20];
    char **lines = NULL;
    int total = 0;
    while (fgets(line, sizeof(line), stdin)) {{
        size_t n = strlen(line);
        while (n && (line[n - 1] == '\\n' || line[n - 1] == '\\r')) line[--n] = 0;
        if (!n) continue;
        lines = (char **)realloc(lines, sizeof(char *) * (total + 1));
        lines[total++] = strdup(line);
    }}
    for (int index = 0; index < total; ++index) {{
        JsonValue root = json_parse(lines[index]);
        const JsonValue *args = json_get(&root, "args");
        const JsonValue *expected = json_get(&root, "expected");
{body}
        if (!json_equal(&gotj, expected, {any_order})) {{
            char *got_s = json_dumps(&gotj);
            printf("{{\\"verdict\\":\\"WA\\",\\"failed_index\\":%d,\\"got\\":%s,\\"passed\\":%d,\\"total\\":%d}}\\n",
                   index, got_s, index, total);
            return 0;
        }}
    }}
    printf("{{\\"verdict\\":\\"AC\\",\\"passed\\":%d,\\"total\\":%d}}\\n", total, total);
    return 0;
}}
'''


class C11Adapter(LanguageAdapter):
    id = "c"
    display_name = "C"
    source_filename = "solution.c"
    implemented = True

    def gcc(self) -> str | None:
        if sys.platform.startswith("linux"):
            for path in ("/usr/bin/gcc", "/usr/local/bin/gcc"):
                if Path(path).exists():
                    return path
        return shutil.which("gcc")

    def detect(self) -> bool:
        return self.gcc() is not None

    def wrap(self, user_code: str, signature: dict) -> str:
        return wrap_c(user_code, signature)

    def compile(self, workdir: str) -> CompileResult:
        compiler = self.gcc()
        if not compiler:
            return CompileResult(ok=False, log="gcc not found")
        shutil.copy2(JSON_HEADER, Path(workdir) / "json.h")
        result = run_limited(
            [compiler, "-O2", "-std=gnu11", "-pipe", "-o", "program", self.source_filename, "-lm"],
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
