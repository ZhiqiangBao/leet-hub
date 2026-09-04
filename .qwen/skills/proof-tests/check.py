"""Mechanical checks for problems/<slug>/tests.jsonl. Do not print the cases."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

INT32_MIN = -2_147_483_648
INT32_MAX = 2_147_483_647
LINE_LIMIT = 7_500_000


def walk_ints(value, acc: list[int]) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        acc.append(value)
        return
    if isinstance(value, list):
        for x in value:
            walk_ints(x, acc)
        return
    if isinstance(value, dict):
        for x in value.values():
            walk_ints(x, acc)


def load_solve(path: Path):
    spec = importlib.util.spec_from_file_location("leet_ref", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "solve", None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--ref", default="")
    args = parser.parse_args()
    root = Path(args.root)
    tests_path = root / "problems" / args.slug / "tests.jsonl"
    ref_path = Path(args.ref) if args.ref else root / ".qwen" / "tmp" / f"{args.slug}_ref.py"

    out: dict = {
        "ok": True,
        "slug": args.slug,
        "path": str(tests_path).replace("\\", "/"),
        "public": 0,
        "hidden": 0,
        "lines": 0,
        "issues": [],
        "ref": str(ref_path).replace("\\", "/") if ref_path.is_file() else None,
        "expected_mismatch": 0,
        "int32_bad": 0,
        "oversize_lines": 0,
    }

    if not tests_path.is_file():
        out["ok"] = False
        out["issues"].append("missing tests.jsonl")
        json.dump(out, sys.stdout, ensure_ascii=False)
        print()
        return 1

    solve = load_solve(ref_path) if ref_path.is_file() else None
    if solve is None:
        out["issues"].append("no solve() in ref.py; skipped [答案] machine check")

    for i, raw in enumerate(tests_path.read_text(encoding="utf-8").splitlines()):
        if not raw.strip():
            continue
        out["lines"] += 1
        if len(raw.encode("utf-8")) > LINE_LIMIT:
            out["oversize_lines"] += 1
            out["issues"].append(f"line {i} over {LINE_LIMIT} bytes")
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            out["ok"] = False
            out["issues"].append(f"line {i} json: {exc}")
            continue
        hidden = bool(obj.get("hidden"))
        if hidden:
            out["hidden"] += 1
        else:
            out["public"] += 1
        ints: list[int] = []
        walk_ints(obj.get("args"), ints)
        walk_ints(obj.get("expected"), ints)
        for n in ints:
            if n < INT32_MIN or n > INT32_MAX:
                out["int32_bad"] += 1
                out["issues"].append(f"line {i} int {n} outside int32")
                break
        if solve is not None and "args" in obj:
            try:
                got = solve(*obj["args"])
                if got != obj.get("expected"):
                    out["expected_mismatch"] += 1
                    if out["expected_mismatch"] <= 5:
                        out["issues"].append(f"line {i} expected mismatch")
            except Exception as exc:
                out["expected_mismatch"] += 1
                out["issues"].append(f"line {i} solve error: {type(exc).__name__}")

    if not (2 <= out["public"] <= 3):
        out["ok"] = False
        out["issues"].append(f"public count {out['public']} not in 2..3")
    if out["hidden"] < 20:
        out["ok"] = False
        out["issues"].append(f"hidden count {out['hidden']} < 20")
    if out["int32_bad"] or out["oversize_lines"] or out["expected_mismatch"]:
        out["ok"] = False

    out["issues"] = out["issues"][:12]
    json.dump(out, sys.stdout, ensure_ascii=False)
    print()
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
