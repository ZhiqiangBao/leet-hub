"""Stdio MCP for Qwen Code. Official SDK. Wraps .qwen/tools. Never dumps tests.jsonl."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from mcp.server import MCPServer
from mcp_types import ToolAnnotations

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from utf8io import configure as _utf8

    _utf8()
except Exception:
    pass
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / ".qwen" / "tools"
PYTHON = sys.executable
MAX_STDERR = 800
MAX_RAW = 4000

mcp = MCPServer("leet")


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


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
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
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
            env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
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


def _need_slug(slug: str) -> str | None:
    if not str(slug or "").strip():
        return _json({"ok": False, "error": "missing slug"})
    return None


@mcp.tool(
    description="Rewrite example lines (kv to positional), fill missing meta bounds, generate empty starters. Returns ok, examples.changed, examples.edits, bounds_notes, issues. Does not judge 题意.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    structured_output=False,
)
def fix_format(slug: str) -> str:
    miss = _need_slug(slug)
    if miss:
        return miss
    return _json(_run("fix_format.py", ["--slug", slug.strip()]))


@mcp.tool(
    description="Parse statement examples and bind them to signature.yaml. skip_ref=true: quality. Default ref: oracle. ref=solve2: solver. Returns ok, examples_parsed, examples_n, import_error, call_error, value_mismatch, ref_example_mismatch, issues. Bind failure is an issue even when skip_ref. Never prints examples.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    structured_output=False,
)
def statement_check(slug: str, skip_ref: bool = False, ref: str = "") -> str:
    miss = _need_slug(slug)
    if miss:
        return miss
    slug = slug.strip()
    argv = ["--slug", slug]
    if skip_ref:
        argv.append("--skip-ref")
    ref = str(ref or "").strip()
    if ref == "solve2":
        argv.extend(["--ref", str(ROOT / ".qwen" / "tmp" / f"{slug}_solve2.py")])
    elif ref:
        argv.extend(["--ref", ref])
    return _json(_run("statement.py", argv))


@mcp.tool(
    description="Score the problem against index/clones.jsonl. Returns ok, hits (id, titles, score), issues. Do not treat hits as auto-fail.",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    structured_output=False,
)
def clone_check(slug: str) -> str:
    miss = _need_slug(slug)
    if miss:
        return miss
    return _json(_run("clone_check.py", ["--slug", slug.strip()]))


@mcp.tool(
    description="Mechanical hidden-test checks. Editor after tests+solver. Returns ok, tags (ASCII: constraints/scale/answer/dump/examples/checklist/count/starter/C), bound_hits, solver_mismatch, expected_mismatch, issues. report is UTF-8 relative path. Never prints cases.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    structured_output=False,
)
def check_tests(slug: str) -> str:
    miss = _need_slug(slug)
    if miss:
        return miss
    return _json(_run("check.py", ["--slug", slug.strip()], timeout=180))


@mcp.tool(
    description="Run .qwen/tmp/<slug>_gen.py (must call dump). Returns dump summary only: ok, public, hidden, hidden_n, issues, bounds, overlay, bound_hits. Never returns test cases.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
    structured_output=False,
)
def run_gen(slug: str) -> str:
    miss = _need_slug(slug)
    if miss:
        return miss
    return _json(_run_gen(slug.strip()))


@mcp.tool(
    description="Arbiter only when verdict is solver: refill tests.jsonl expected from solve2 and copy it to ref.py. Returns filled, solve_err.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False),
    structured_output=False,
)
def fill_expected(slug: str, promote: bool = True) -> str:
    miss = _need_slug(slug)
    if miss:
        return miss
    slug = slug.strip()
    argv = ["--slug", slug, "--ref", str(ROOT / ".qwen" / "tmp" / f"{slug}_solve2.py")]
    if promote:
        argv.append("--promote")
    return _json(_run("fill_expected.py", argv))


@mcp.tool(
    description="Regenerate problems/catalog.md from git-tracked problems plus this slug. Editor, commit only.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    structured_output=False,
)
def write_catalog(slug: str) -> str:
    miss = _need_slug(slug)
    if miss:
        return miss
    return _json(_run("write_catalog.py", ["--slug", slug.strip()]))


@mcp.tool(
    description="Editor only after voiding a slug. Deletes problems/<slug>/ and .qwen/tmp/<slug>_*.py. Does not touch catalog.md, desk/, or other slugs. Returns ok, removed.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True),
    structured_output=False,
)
def drop_problem(slug: str) -> str:
    miss = _need_slug(slug)
    if miss:
        return miss
    return _json(_run("drop_problem.py", ["--slug", slug.strip()]))


if __name__ == "__main__":
    mcp.run(transport="stdio")
