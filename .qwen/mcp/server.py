"""Stdio MCP for Qwen Code. Wraps .qwen/tools CLIs. Never dumps tests.jsonl."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / ".qwen" / "tools"
PYTHON = sys.executable
PROTOCOL = "2024-11-05"
MAX_STDERR = 800
MAX_RAW = 4000

os.environ.setdefault("PYTHONUNBUFFERED", "1")
sys.path.insert(0, str(TOOLS))


def _last_json(text: str) -> dict:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for line in reversed(lines):
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    snippet = (text or "").strip()[:MAX_RAW]
    return {"ok": False, "error": "no json line", "raw": snippet}


def _run(script: str, argv: list[str], timeout: int = 180) -> dict:
    path = TOOLS / script
    proc = subprocess.run(
        [PYTHON, str(path), *argv, "--root", str(ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        timeout=timeout,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    out = _last_json(proc.stdout)
    if proc.returncode != 0:
        out["ok"] = False
    err = (proc.stderr or "").strip()
    if err and not out.get("ok", True):
        out["stderr"] = err[:MAX_STDERR]
    return out


def _run_gen(slug: str) -> dict:
    gen = ROOT / ".qwen" / "tmp" / f"{slug}_gen.py"
    if not gen.is_file():
        return {"ok": False, "slug": slug, "issues": ["missing gen.py"]}
    try:
        proc = subprocess.run(
            [PYTHON, str(gen)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            timeout=300,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "slug": slug, "error": "timeout"}
    out = _last_json(proc.stdout)
    if proc.returncode != 0:
        out["ok"] = False
    err = (proc.stderr or "").strip()
    if err and not out.get("ok", True):
        out["stderr"] = err[:MAX_STDERR]
    return out


TOOLS_SPEC = [
    {
        "name": "fix_format",
        "description": "Rewrite example lines, fill missing meta bounds, generate empty starters. Author and quality. Does not judge 题意.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "statement_check",
        "description": "Parse statement examples and optionally run solve() on them. Quality: skip_ref=true. Oracle: defaults. Solver: ref=solve2. Returns ok, examples_parsed, examples_n, ref_example_mismatch, issues. Never prints examples.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "skip_ref": {"type": "boolean", "default": False},
                "ref": {
                    "type": "string",
                    "description": "Empty = tmp/<slug>_ref.py. 'solve2' = tmp/<slug>_solve2.py.",
                    "default": "",
                },
            },
            "required": ["slug"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "clone_check",
        "description": "Score the problem against index/clones.jsonl. Returns ok, hits (id, titles, score), issues. Do not treat hits as auto-fail.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "check_tests",
        "description": "Mechanical hidden-test checks. Editor after tests+solver. Returns ok, tags, solver_mismatch, expected_mismatch, issues. Writes desk/校对/<slug>.md. Never prints cases.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "run_gen",
        "description": "Run .qwen/tmp/<slug>_gen.py (must call dump). Returns the dump summary only: ok, public, hidden, hidden_n, issues. Never returns test cases.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    },
    {
        "name": "fill_expected",
        "description": "Arbiter only when verdict is solver: refill tests.jsonl expected from solve2 and copy it to ref.py. Returns filled, solve_err.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "promote": {"type": "boolean", "default": True},
            },
            "required": ["slug"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False},
    },
    {
        "name": "write_catalog",
        "description": "Regenerate problems/catalog.md from git-tracked problems plus this slug. Editor, commit only.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "drop_problem",
        "description": "Editor only after voiding a slug. Deletes problems/<slug>/ and .qwen/tmp/<slug>_*.py. Does not touch catalog.md, desk/, or other slugs. Returns ok, removed.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True},
    },
]


def dispatch(name: str, arguments: dict) -> dict:
    slug = str(arguments.get("slug") or "").strip()
    if not slug:
        return {"ok": False, "error": "missing slug"}
    if name == "fix_format":
        return _run("fix_format.py", ["--slug", slug])
    if name == "statement_check":
        argv = ["--slug", slug]
        if arguments.get("skip_ref"):
            argv.append("--skip-ref")
        ref = str(arguments.get("ref") or "").strip()
        if ref == "solve2":
            argv.extend(["--ref", str(ROOT / ".qwen" / "tmp" / f"{slug}_solve2.py")])
        elif ref:
            argv.extend(["--ref", ref])
        return _run("statement.py", argv)
    if name == "clone_check":
        return _run("clone_check.py", ["--slug", slug])
    if name == "check_tests":
        return _run("check.py", ["--slug", slug], timeout=180)
    if name == "run_gen":
        return _run_gen(slug)
    if name == "fill_expected":
        argv = [
            "--slug",
            slug,
            "--ref",
            str(ROOT / ".qwen" / "tmp" / f"{slug}_solve2.py"),
        ]
        if arguments.get("promote", True):
            argv.append("--promote")
        return _run("fill_expected.py", argv)
    if name == "write_catalog":
        return _run("write_catalog.py", ["--slug", slug])
    if name == "drop_problem":
        return _run("drop_problem.py", ["--slug", slug])
    return {"ok": False, "error": f"unknown tool {name}"}


def _read() -> dict | None:
    buf = sys.stdin.buffer
    headers: dict[str, str] = {}
    while True:
        line = buf.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        raw = line.decode("utf-8", errors="replace").strip()
        if ":" in raw:
            k, v = raw.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    n = int(headers.get("content-length") or "0")
    body = buf.read(n) if n else b""
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write(msg: dict) -> None:
    data = json.dumps(msg, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii") + data)
    sys.stdout.buffer.flush()


def _ok(req_id, result: dict) -> None:
    _write({"jsonrpc": "2.0", "id": req_id, "result": result})


def _err(req_id, code: int, message: str) -> None:
    _write({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


def main() -> int:
    while True:
        try:
            msg = _read()
        except Exception:
            return 1
        if msg is None:
            return 0
        method = msg.get("method")
        req_id = msg.get("id")
        if method == "initialize":
            _ok(
                req_id,
                {
                    "protocolVersion": PROTOCOL,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "leet", "version": "1.0.0"},
                },
            )
            continue
        if method == "notifications/initialized" or req_id is None:
            continue
        if method == "ping":
            _ok(req_id, {})
            continue
        if method == "tools/list":
            _ok(req_id, {"tools": TOOLS_SPEC})
            continue
        if method == "prompts/list":
            _ok(req_id, {"prompts": []})
            continue
        if method == "resources/list":
            _ok(req_id, {"resources": []})
            continue
        if method == "tools/call":
            params = msg.get("params") or {}
            name = params.get("name") or ""
            args = params.get("arguments") or {}
            try:
                result = dispatch(name, args if isinstance(args, dict) else {})
            except subprocess.TimeoutExpired:
                result = {"ok": False, "error": "timeout"}
            except Exception as exc:
                result = {"ok": False, "error": type(exc).__name__}
            text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
            _ok(
                req_id,
                {
                    "content": [{"type": "text", "text": text}],
                    "isError": not result.get("ok", False),
                },
            )
            continue
        _err(req_id, -32601, f"Method not found: {method}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
