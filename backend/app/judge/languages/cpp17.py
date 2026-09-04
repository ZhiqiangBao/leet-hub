from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ..base import CompileResult, LanguageAdapter
from ..sandbox import run_limited

JSON_HEADER = Path(__file__).resolve().parents[1] / "runtimes" / "cpp" / "mini_json.hpp"


def cpp_type(type_name: str) -> str:
    name = type_name.strip()
    mapping = {"int": "int", "float": "double", "bool": "bool", "str": "string"}
    if name in mapping:
        return mapping[name]
    if name.startswith("List[") and name.endswith("]"):
        return f"vector<{cpp_type(name[5:-1])}>"
    raise ValueError(f"unsupported C++ type: {type_name}")


def conv_name(type_name: str) -> str:
    return "conv_" + type_name.replace("[", "_").replace("]", "").replace(" ", "")


def emit_converters(types: list[str]) -> str:
    seen: set[str] = set()
    chunks: list[str] = []

    def emit(type_name: str) -> None:
        if type_name in seen:
            return
        if type_name.startswith("List[") and type_name.endswith("]"):
            emit(type_name[5:-1])
        seen.add(type_name)
        fn = conv_name(type_name)
        ctype = cpp_type(type_name)
        if type_name == "int":
            chunks.append(f"int {fn}(const JsonValue& v) {{ return v.as_int(); }}")
        elif type_name == "float":
            chunks.append(f"double {fn}(const JsonValue& v) {{ return v.as_double(); }}")
        elif type_name == "bool":
            chunks.append(f"bool {fn}(const JsonValue& v) {{ return v.as_bool(); }}")
        elif type_name == "str":
            chunks.append(f"string {fn}(const JsonValue& v) {{ return v.as_string(); }}")
        else:
            inner = type_name[5:-1]
            chunks.append(
                f"{ctype} {fn}(const JsonValue& v) {{\n"
                f"  {ctype} out;\n"
                f"  for (const auto& item : v.as_array()) out.push_back({conv_name(inner)}(item));\n"
                f"  return out;\n"
                f"}}"
            )

    for t in types:
        emit(t)
    return "\n".join(chunks)


def wrap_cpp(user_code: str, signature: dict) -> str:
    class_name = signature.get("class_name") or "Solution"
    method = signature["method"]
    compare = signature.get("compare") or "exact"
    params = signature.get("params") or []
    return_type = signature["return_type"]
    types = [p["type"] for p in params] + [return_type]
    converters = emit_converters(types)
    bind_lines = [
        f"            auto arg{i} = {conv_name(p['type'])}(args[{i}]);"
        for i, p in enumerate(params)
    ]
    bind = "\n".join(bind_lines) if bind_lines else ""
    call_args = ", ".join(f"arg{i}" for i in range(len(params)))
    any_order = "true" if compare == "any_order" else "false"
    return f'''#include <bits/stdc++.h>
#include "mini_json.hpp"
using namespace std;

{user_code.rstrip()}

{converters}

int main() {{
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    vector<string> lines;
    string line;
    while (getline(cin, line)) {{
        if (!line.empty()) lines.push_back(line);
    }}
    int total = (int)lines.size();
    {class_name} sol;
    for (int index = 0; index < total; ++index) {{
        JsonValue root = JsonValue::parse(lines[index]);
        JsonValue args = root["args"];
        JsonValue expected = root["expected"];
        try {{
{bind}
            auto got = sol.{method}({call_args});
            JsonValue gotj = to_json_val(got);
            if (!json_equal(gotj, expected, {any_order})) {{
                JsonValue payload;
                payload.type = JsonValue::OBJ;
                payload.o["verdict"] = JsonValue::from_str("WA");
                payload.o["failed_index"] = JsonValue::from_num(index);
                payload.o["got"] = gotj;
                payload.o["passed"] = JsonValue::from_num(index);
                payload.o["total"] = JsonValue::from_num(total);
                cout << payload.dumps() << endl;
                return 0;
            }}
        }} catch (const exception& ex) {{
            JsonValue payload;
            payload.type = JsonValue::OBJ;
            payload.o["verdict"] = JsonValue::from_str("RE");
            payload.o["failed_index"] = JsonValue::from_num(index);
            payload.o["message"] = JsonValue::from_str(ex.what());
            payload.o["passed"] = JsonValue::from_num(index);
            payload.o["total"] = JsonValue::from_num(total);
            cout << payload.dumps() << endl;
            return 0;
        }}
    }}
    JsonValue payload;
    payload.type = JsonValue::OBJ;
    payload.o["verdict"] = JsonValue::from_str("AC");
    payload.o["passed"] = JsonValue::from_num(total);
    payload.o["total"] = JsonValue::from_num(total);
    cout << payload.dumps() << endl;
    return 0;
}}
'''


class Cpp17Adapter(LanguageAdapter):
    id = "cpp17"
    display_name = "C++20"
    source_filename = "solution.cpp"
    implemented = True

    def gxx(self) -> str | None:
        if sys.platform.startswith("linux"):
            for path in ("/usr/bin/g++", "/usr/local/bin/g++"):
                if Path(path).exists():
                    return path
        return shutil.which("g++")

    def detect(self) -> bool:
        return self.gxx() is not None

    def wrap(self, user_code: str, signature: dict) -> str:
        return wrap_cpp(user_code, signature)

    def compile(self, workdir: str) -> CompileResult:
        compiler = self.gxx()
        if not compiler:
            return CompileResult(ok=False, log="g++ not found")
        shutil.copy2(JSON_HEADER, Path(workdir) / "mini_json.hpp")
        result = run_limited(
            [compiler, "-O2", "-std=c++20", "-pipe", "-o", "program", self.source_filename],
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
