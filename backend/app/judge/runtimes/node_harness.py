from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HARNESS = r'''
// --- local-leet harness (do not edit) ---
const METHOD = {method};
const COMPARE = {compare};

function _canon(value) {{
  if (value === undefined) throw new TypeError("unsupported return type: undefined");
  if (value === null || typeof value === "boolean" || typeof value === "string") return value;
  if (typeof value === "number") {{
    if (!Number.isFinite(value)) throw new TypeError("unsupported number");
    return value;
  }}
  if (Array.isArray(value)) return value.map(_canon);
  throw new TypeError("unsupported return type: " + (value && value.constructor && value.constructor.name || typeof value));
}}

function _isclose(a, b) {{
  const diff = Math.abs(a - b);
  return diff <= 1e-6 || diff <= 1e-6 * Math.max(Math.abs(a), Math.abs(b));
}}

function _close(a, b) {{
  if (typeof a === "boolean" || typeof b === "boolean") {{
    return a === b && typeof a === typeof b;
  }}
  if (typeof a === "number" && typeof b === "number") {{
    if (Number.isInteger(a) && Number.isInteger(b)) return a === b;
    return _isclose(a, b);
  }}
  if (Array.isArray(a) && Array.isArray(b)) {{
    if (a.length !== b.length) return false;
    return a.every((x, i) => _close(x, b[i]));
  }}
  return a === b;
}}

function _sortKey(value) {{
  return JSON.stringify(value);
}}

function _eq(got, expected, mode) {{
  if (mode === "any_order" && Array.isArray(got) && Array.isArray(expected)) {{
    if (got.length !== expected.length) return false;
    const gs = [...got].sort((x, y) => (_sortKey(x) < _sortKey(y) ? -1 : _sortKey(x) > _sortKey(y) ? 1 : 0));
    const es = [...expected].sort((x, y) => (_sortKey(x) < _sortKey(y) ? -1 : _sortKey(x) > _sortKey(y) ? 1 : 0));
    return gs.every((x, i) => _sortKey(x) === _sortKey(es[i])) || gs.every((x, i) => _close(x, es[i]));
  }}
  return _close(got, expected);
}}

function _emit(payload) {{
  process.stdout.write(JSON.stringify(payload) + "\n");
}}

function main() {{
  const fs = require("fs");
  const tests = [];
  const raw = fs.readFileSync(0, "utf8");
  for (const line of raw.split(/\r?\n/)) {{
    const s = line.trim();
    if (s) tests.push(JSON.parse(s));
  }}
  if (typeof {class_name} !== "function") {{
    _emit({{"verdict": "RE", "message": "missing class {class_name}"}});
    return;
  }}
  let inst;
  try {{
    inst = new {class_name}();
  }} catch (exc) {{
    _emit({{"verdict": "RE", "message": "construct {class_name}: " + String(exc)}});
    return;
  }}
  const method = inst[METHOD];
  if (typeof method !== "function") {{
    _emit({{"verdict": "RE", "message": "missing method " + METHOD}});
    return;
  }}
  const total = tests.length;
  for (let index = 0; index < total; index++) {{
    const test = tests[index];
    const args = test.args || [];
    const expected = test.expected;
    let got_c;
    try {{
      got_c = _canon(method.apply(inst, args));
    }} catch (exc) {{
      const message = (exc && exc.stack) ? String(exc.stack) : String(exc);
      _emit({{
        "verdict": "RE",
        "failed_index": index,
        "message": message.slice(-2000),
        "passed": index,
        "total": total,
      }});
      return;
    }}
    if (!_eq(got_c, expected, COMPARE)) {{
      _emit({{
        "verdict": "WA",
        "failed_index": index,
        "got": got_c,
        "passed": index,
        "total": total,
      }});
      return;
    }}
  }}
  _emit({{"verdict": "AC", "passed": total, "total": total}});
}}

main();
'''

TS_DECLARES = """declare function require(id: string): any;
declare const process: { stdout: { write(chunk: string): void } };

"""

_node: str | None | bool = False
_tsc: list[str] | None | bool = False


def _usable(path: str) -> bool:
    if "WindowsApps" in path:
        return False
    try:
        proc = subprocess.run(
            [path, "-e", "process.stdout.write('ok')"],
            capture_output=True,
            timeout=5,
            text=True,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "ok"


def find_node() -> str | None:
    global _node
    if _node is not False:
        return _node  # type: ignore[return-value]
    candidates: list[str] = []
    if sys.platform.startswith("linux"):
        candidates += ["/usr/bin/node", "/usr/local/bin/node"]
    found = shutil.which("node")
    if found:
        candidates.append(found)
    seen: set[str] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if _usable(path):
            _node = path
            return path
    _node = None
    return None


def find_tsc() -> list[str] | None:
    """Return argv that compiles TypeScript (tsc or node + tsc.js)."""
    global _tsc
    if _tsc is not False:
        return _tsc  # type: ignore[return-value]
    node = find_node()
    script_candidates = [
        "/usr/lib/node_modules/typescript/bin/tsc",
        "/usr/local/lib/node_modules/typescript/bin/tsc",
    ]
    which = shutil.which("tsc")
    argv_candidates: list[list[str]] = []
    if which:
        argv_candidates.append([which])
    if sys.platform.startswith("linux"):
        for path in ("/usr/bin/tsc", "/usr/local/bin/tsc"):
            argv_candidates.append([path])
    if node:
        for script in script_candidates:
            argv_candidates.append([node, script])
    seen: set[tuple[str, ...]] = set()
    for argv in argv_candidates:
        key = tuple(argv)
        if key in seen:
            continue
        seen.add(key)
        if not all(part == node or Path(part).exists() for part in argv):
            continue
        try:
            proc = subprocess.run(
                argv + ["--version"],
                capture_output=True,
                timeout=8,
                text=True,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode == 0:
            text = (proc.stdout or "") + (proc.stderr or "")
            if "Version" in text or any(ch.isdigit() for ch in text):
                _tsc = argv
                return argv
    _tsc = None
    return None


def wrap_javascript(user_code: str, signature: dict[str, Any]) -> str:
    class_name = signature.get("class_name") or "Solution"
    harness = HARNESS.format(
        method=repr(signature["method"]),
        class_name=class_name,
        compare=repr(signature.get("compare") or "exact"),
    )
    return user_code.rstrip() + "\n\n" + harness


def wrap_typescript(user_code: str, signature: dict[str, Any]) -> str:
    class_name = signature.get("class_name") or "Solution"
    harness = TS_DECLARES + HARNESS.format(
        method=repr(signature["method"]),
        class_name=class_name,
        compare=repr(signature.get("compare") or "exact"),
    )
    return user_code.rstrip() + "\n\n" + harness
