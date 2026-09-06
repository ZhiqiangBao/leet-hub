"""Emit empty starter files from problems/<slug>/signature.yaml."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CORE_LANGS = ("python3", "c", "cpp17")
EXTRA_LANGS = ("javascript", "go", "rust", "zig", "typescript")
ALL_LANGS = CORE_LANGS + EXTRA_LANGS

EXT = {
    "python3": ".py",
    "c": ".c",
    "cpp17": ".cpp",
    "javascript": ".js",
    "go": ".go",
    "rust": ".rs",
    "zig": ".zig",
    "typescript": ".ts",
}


def load_signature(path: Path) -> dict:
    class_name = "Solution"
    method = ""
    return_type = "int"
    params: list[dict] = []
    current: dict | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("class_name:"):
            class_name = s.split(":", 1)[1].strip()
        elif s.startswith("method:"):
            method = s.split(":", 1)[1].strip()
        elif s.startswith("return_type:"):
            return_type = s.split(":", 1)[1].strip().split("#", 1)[0].strip()
        elif s.startswith("- name:"):
            current = {"name": s.split(":", 1)[1].strip(), "type": "int"}
            params.append(current)
        elif s.startswith("type:") and current is not None and raw[:1] in " \t":
            current["type"] = s.split(":", 1)[1].strip().split("#", 1)[0].strip()
    if not method:
        raise SystemExit(f"missing method in {path}")
    return {"class_name": class_name, "method": method, "params": params, "return_type": return_type}


def inner_list(type_name: str) -> str | None:
    t = type_name.strip()
    if t.startswith("List[") and t.endswith("]"):
        return t[5:-1].strip()
    return None


def is_nested_list(type_name: str) -> bool:
    inner = inner_list(type_name)
    return inner is not None and inner_list(inner) is not None


def pascal(name: str) -> str:
    if "_" in name:
        return "".join(p[:1].upper() + p[1:] for p in name.split("_") if p)
    return name[:1].upper() + name[1:]


def snake(name: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i and name[i - 1] != "_":
            out.append("_")
        out.append(ch.lower())
    return "".join(out).replace("__", "_")


def py_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"list[{py_type(inner)}]"
    return {"int": "int", "long": "int", "float": "float", "bool": "bool", "str": "str"}[t]


def c_scalar(type_name: str) -> str:
    return {"int": "int", "long": "long long", "float": "double", "bool": "bool", "str": "char*"}[type_name]


def c_params(params: list[dict], return_type: str) -> str:
    parts: list[str] = []
    for p in params:
        t, name = p["type"], p["name"]
        inner = inner_list(t)
        if inner is not None:
            if is_nested_list(t) or inner not in ("int", "long", "str"):
                raise ValueError(f"unsupported C param type: {t}")
            ptr = {"int": "int*", "long": "long long*", "str": "char**"}[inner]
            parts.append(f"{ptr} {name}")
            parts.append(f"int {name}Size")
        else:
            parts.append(f"{c_scalar(t)} {name}")
    ret_inner = inner_list(return_type)
    if ret_inner is not None:
        parts.append("int* returnSize")
    return ", ".join(parts)


def c_return(return_type: str) -> str:
    inner = inner_list(return_type)
    if inner is not None:
        if inner == "int":
            return "int*"
        if inner == "long":
            return "long long*"
        if inner == "str":
            return "char**"
        raise ValueError(f"unsupported C return type: {return_type}")
    return c_scalar(return_type)


def cpp_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"vector<{cpp_type(inner)}>"
    return {"int": "int", "long": "long long", "float": "double", "bool": "bool", "str": "string"}[t]


def cpp_param(type_name: str, name: str) -> str:
    ct = cpp_type(type_name)
    if inner_list(type_name) is not None:
        return f"{ct}& {name}"
    return f"{ct} {name}"


def js_doc(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"{js_doc(inner)}[]"
    return {"int": "number", "long": "number", "float": "number", "bool": "boolean", "str": "string"}[t]


def ts_type(type_name: str) -> str:
    return js_doc(type_name)


def go_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"[]{go_type(inner)}"
    return {"int": "int", "long": "int64", "float": "float64", "bool": "bool", "str": "string"}[t]


def rust_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"Vec<{rust_type(inner)}>"
    return {"int": "i32", "long": "i64", "float": "f64", "bool": "bool", "str": "String"}[t]


def zig_type(type_name: str, *, ret: bool = False) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        if is_nested_list(t):
            raise ValueError(f"unsupported Zig type: {t}")
        if inner == "str":
            return "[][]const u8" if ret else "[]const []const u8"
        leaf = {"int": "i32", "long": "i64", "float": "f64", "bool": "bool"}[inner]
        return f"[]{leaf}" if ret else f"[]const {leaf}"
    if t == "str":
        return "[]const u8"
    return {"int": "i32", "long": "i64", "float": "f64", "bool": "bool"}[t]


def emit_python3(sig: dict) -> str:
    args = ", ".join(
        ["self"] + [f"{p['name']}: {py_type(p['type'])}" for p in sig["params"]]
    )
    ret = py_type(sig["return_type"])
    return (
        f"class {sig['class_name']}:\n"
        f"    def {sig['method']}({args}) -> {ret}:\n"
        f"        \n"
    )


def emit_c(sig: dict) -> str:
    ret = c_return(sig["return_type"])
    args = c_params(sig["params"], sig["return_type"])
    header = ""
    if inner_list(sig["return_type"]):
        header = (
            "/**\n"
            " * Note: The returned array must be malloced, assume caller calls free().\n"
            " */\n"
        )
    return f"{header}{ret} {sig['method']}({args}) {{\n    \n}}\n"


def emit_cpp17(sig: dict) -> str:
    args = ", ".join(cpp_param(p["type"], p["name"]) for p in sig["params"])
    ret = cpp_type(sig["return_type"])
    return (
        f"class {sig['class_name']} {{\n"
        f"public:\n"
        f"    {ret} {sig['method']}({args}) {{\n"
        f"        \n"
        f"    }}\n"
        f"}};\n"
    )


def emit_javascript(sig: dict) -> str:
    args = ", ".join(p["name"] for p in sig["params"])
    docs = []
    for p in sig["params"]:
        docs.append(f"     * @param {{{js_doc(p['type'])}}} {p['name']}")
    docs.append(f"     * @return {{{js_doc(sig['return_type'])}}}")
    doc = "    /**\n" + "\n".join(docs) + "\n     */\n" if docs else ""
    return (
        f"class {sig['class_name']} {{\n"
        f"{doc}"
        f"    {sig['method']}({args}) {{\n"
        f"        \n"
        f"    }}\n"
        f"}}\n"
    )


def emit_typescript(sig: dict) -> str:
    args = ", ".join(f"{p['name']}: {ts_type(p['type'])}" for p in sig["params"])
    ret = ts_type(sig["return_type"])
    return (
        f"class {sig['class_name']} {{\n"
        f"    {sig['method']}({args}): {ret} {{\n"
        f"        \n"
        f"    }}\n"
        f"}}\n"
    )


def emit_go(sig: dict) -> str:
    args = ", ".join(f"{p['name']} {go_type(p['type'])}" for p in sig["params"])
    ret = go_type(sig["return_type"])
    method = pascal(sig["method"])
    used = {p["name"] for p in sig["params"]}
    recv = "sol"
    if recv in used:
        recv = "this"
    return (
        f"package main\n"
        f"\n"
        f"type {sig['class_name']} struct{{}}\n"
        f"\n"
        f"func ({recv} *{sig['class_name']}) {method}({args}) {ret} {{\n"
        f"    \n"
        f"}}\n"
    )


def emit_rust(sig: dict) -> str:
    args = ", ".join(f"{p['name']}: {rust_type(p['type'])}" for p in sig["params"])
    ret = rust_type(sig["return_type"])
    method = snake(sig["method"])
    cls = sig["class_name"]
    return (
        f"pub struct {cls};\n"
        f"\n"
        f"impl {cls} {{\n"
        f"    pub fn {method}({args}) -> {ret} {{\n"
        f"        \n"
        f"    }}\n"
        f"}}\n"
    )


def emit_zig(sig: dict) -> str:
    args = ", ".join(
        ["self: @This()"] + [f"{p['name']}: {zig_type(p['type'])}" for p in sig["params"]]
    )
    ret = zig_type(sig["return_type"], ret=True)
    return (
        f"const {sig['class_name']} = struct {{\n"
        f"    pub fn {sig['method']}({args}) {ret} {{\n"
        f"        \n"
        f"    }}\n"
        f"}};\n"
    )


EMITTERS = {
    "python3": emit_python3,
    "c": emit_c,
    "cpp17": emit_cpp17,
    "javascript": emit_javascript,
    "typescript": emit_typescript,
    "go": emit_go,
    "rust": emit_rust,
    "zig": emit_zig,
}


def write_starters(root: Path, slug: str, langs: list[str]) -> dict:
    sig_path = root / "problems" / slug / "signature.yaml"
    if not sig_path.is_file():
        raise SystemExit(f"missing {sig_path}")
    sig = load_signature(sig_path)
    dest = root / "problems" / slug / "starter"
    dest.mkdir(parents=True, exist_ok=True)
    wrote: list[str] = []
    skipped: list[str] = []
    for lang in langs:
        emit = EMITTERS[lang]
        try:
            text = emit(sig)
        except (KeyError, ValueError) as exc:
            skipped.append(f"{lang}:{exc}")
            continue
        path = dest / f"{lang}{EXT[lang]}"
        path.write_text(text, encoding="utf-8")
        wrote.append(lang)
    ok = all(lang in wrote for lang in CORE_LANGS if lang in langs)
    return {"ok": ok, "slug": slug, "wrote": wrote, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default="")
    parser.add_argument("--core", action="store_true", help="only python3/c/cpp17")
    parser.add_argument("--langs", default="", help="comma-separated language ids")
    args = parser.parse_args()
    root = Path(args.root) if args.root else Path(__file__).resolve().parents[2]
    if args.langs:
        langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    elif args.core:
        langs = list(CORE_LANGS)
    else:
        langs = list(ALL_LANGS)
    unknown = [x for x in langs if x not in EMITTERS]
    if unknown:
        raise SystemExit(f"unknown langs: {unknown}")
    from utf8io import dump

    summary = write_starters(root, args.slug, langs)
    dump(summary)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
