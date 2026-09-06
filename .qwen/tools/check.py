"""Mechanical checks for problems/<slug>/tests.jsonl. Do not print the cases."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from constraints import (  # noqa: E402
    args_n_kind,
    case_n,
    check_hits,
    hist_hidden,
    load_bounds,
    load_params,
    public_bounds,
    scale_issues,
    tags_for,
)
from examples import parse_statement_examples  # noqa: E402
from int_bounds import load_sig_types, range_flags  # noqa: E402
from utf8io import dump  # noqa: E402

LINE_LIMIT = 7_500_000


def load_verdict(root: Path, slug: str) -> str | None:
    path = root / "desk" / "裁决" / f"{slug}.md"
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "## 结论" and i + 1 < len(lines):
            v = lines[i + 1].strip().split()[0] if lines[i + 1].strip() else ""
            if v in ("author", "solver", "both-wrong", "statement-ambiguous"):
                return v
    return None


def write_report(root: Path, slug: str, out: dict) -> None:
    desk = root / "desk" / "校对"
    desk.mkdir(parents=True, exist_ok=True)
    rows = [f"# 校对 {slug}", "## 结论", "通过" if out.get("ok") else "不通过", "## 问题"]
    issues = out.get("issues") or []
    if not issues:
        rows.append("- （无）")
    else:
        for iss in issues:
            rows.append(f"- {iss}")
    path = desk / f"{slug}.md"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    rel = path.relative_to(root).as_posix()
    out["report"] = rel


def load_solve(path: Path):
    spec = importlib.util.spec_from_file_location("leet_ref", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "solve", None)


def load_compare(root: Path, slug: str) -> str:
    path = root / "problems" / slug / "signature.yaml"
    if not path.is_file():
        return "exact"
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("compare:"):
            return s.split(":", 1)[1].strip().split("#", 1)[0].strip() or "exact"
    return "exact"


def values_equal(got, expected, compare: str) -> bool:
    if compare == "any_order" and isinstance(got, list) and isinstance(expected, list):
        if len(got) != len(expected):
            return False
        key = lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False)
        return sorted(got, key=key) == sorted(expected, key=key)
    return got == expected


def run_solve(solve, args):
    if solve is None:
        return "missing", None
    try:
        return "ok", solve(*args)
    except Exception as exc:
        return type(exc).__name__, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--ref", default="")
    parser.add_argument("--solver", default="")
    args = parser.parse_args()
    root = Path(args.root)
    tests_path = root / "problems" / args.slug / "tests.jsonl"
    ref_path = Path(args.ref) if args.ref else root / ".qwen" / "tmp" / f"{args.slug}_ref.py"
    solver_path = (
        Path(args.solver) if args.solver else root / ".qwen" / "tmp" / f"{args.slug}_solve2.py"
    )
    bounds = load_bounds(root, args.slug)
    params = load_params(root, args.slug)
    verdict = load_verdict(root, args.slug)
    ignore_solver = verdict == "author"

    out: dict = {
        "ok": True,
        "slug": args.slug,
        "public": 0,
        "hidden": 0,
        "lines": 0,
        "issues": [],
        "tags": [],
        "ref": str(ref_path).replace("\\", "/") if ref_path.is_file() else None,
        "solver": str(solver_path).replace("\\", "/") if solver_path.is_file() else None,
        "expected_mismatch": 0,
        "solver_mismatch": 0,
        "int32_bad": 0,
        "int64_bad": 0,
        "oversize_lines": 0,
        "mismatch_lines": [],
        "n_min": None,
        "n_max": None,
        "U": bounds["n_max"],
        "hidden_n": {},
        "n_kind": "length",
        "example_mismatch": 0,
        "statement_title": True,
        "verdict": verdict,
        "bounds": public_bounds(bounds),
        "bound_hits": [],
        "expected_call_error": 0,
        "solver_call_error": 0,
    }

    if not tests_path.is_file():
        out["ok"] = False
        out["issues"].append("missing tests.jsonl")
        out["tags"].append("count")
        write_report(root, args.slug, out)
        dump(out)
        return 1

    hns: list[int] = []
    kinds: list[str] = []
    public_rows: list[tuple[list, object]] = []
    hit_acc: dict[tuple, dict] = {}
    author = load_solve(ref_path) if ref_path.is_file() else None
    solver = load_solve(solver_path) if solver_path.is_file() else None
    compare = load_compare(root, args.slug)
    param_types, return_type = load_sig_types(root, args.slug)
    if author is None:
        out["ok"] = False
        out["issues"].append("dump: missing ref.py solve()")
    if solver is None and not ignore_solver:
        out["ok"] = False
        out["issues"].append("missing solve2.py; re-dispatch solver")

    def _keep_hit(h: dict) -> None:
        key = (h["code"], h["param"])
        prev = hit_acc.get(key)
        if prev is None:
            hit_acc[key] = h
            return
        if isinstance(h.get("got"), int) and isinstance(prev.get("got"), int):
            if abs(h["got"]) > abs(prev["got"]):
                hit_acc[key] = h

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
        case_args = obj.get("args") or []
        if obj.get("hidden"):
            out["hidden"] += 1
            hns.append(case_n(case_args))
            kinds.append(args_n_kind(case_args))
        else:
            out["public"] += 1
            public_rows.append((obj.get("args"), obj.get("expected")))
        for h in check_hits(case_args, params, bounds):
            _keep_hit(h)
        bad32, bad64 = range_flags(
            obj.get("args"), obj.get("expected"), param_types, return_type
        )
        if bad32:
            out["int32_bad"] += 1
            out["issues"].append(f"line {i} int32")
        if bad64:
            out["int64_bad"] += 1
            out["issues"].append(f"line {i} int64")
        expected = obj.get("expected")
        st, got = run_solve(author, case_args)
        if author is not None and st != "ok":
            out["expected_mismatch"] += 1
            out["expected_call_error"] += 1
            if len(out["mismatch_lines"]) < 8:
                out["mismatch_lines"].append(i)
                out["issues"].append(f"line {i} dump: solve not called")
        elif author is not None and not values_equal(got, expected, compare):
            out["expected_mismatch"] += 1
            if len(out["mismatch_lines"]) < 8:
                out["mismatch_lines"].append(i)
                out["issues"].append(f"line {i} dump: ref≠expected")
        if ignore_solver:
            continue
        st2, got2 = run_solve(solver, case_args)
        if solver is not None and st2 != "ok":
            out["solver_mismatch"] += 1
            out["solver_call_error"] += 1
            if len(out["mismatch_lines"]) < 8:
                out["mismatch_lines"].append(i)
            if out["solver_call_error"] <= 5:
                out["issues"].append(f"line {i} answer: solve not called")
        elif solver is not None and not values_equal(got2, expected, compare):
            out["solver_mismatch"] += 1
            if len(out["mismatch_lines"]) < 8:
                out["mismatch_lines"].append(i)
            if out["solver_mismatch"] <= 5:
                out["issues"].append(f"line {i} answer: solver≠expected")

    out["n_min"] = min(hns) if hns else None
    out["n_max"] = max(hns) if hns else None
    out["hidden_n"] = hist_hidden(hns)
    out["n_kind"] = "length" if any(k == "length" for k in kinds) else "scalar"
    out["bound_hits"] = list(hit_acc.values())
    bound_codes = list(dict.fromkeys(h["code"] for h in out["bound_hits"]))
    issue_codes = list(dict.fromkeys(bound_codes + scale_issues(hns, out["n_kind"], bounds)))
    for code in issue_codes:
        if code == "out_of_bounds":
            for h in out["bound_hits"]:
                if h["code"] == "out_of_bounds":
                    out["issues"].append(
                        f"out_of_bounds param={h['param']} got={h['got']} min={h['min']} max={h['max']}"
                    )
        else:
            out["issues"].append(code)
    for warn in bounds.get("warnings") or []:
        out["ok"] = False
        out["issues"].append(warn)
    if bounds.get("notes"):
        out["bounds_notes"] = list(bounds["notes"])
    stmt_path = root / "problems" / args.slug / "statement.md"
    if stmt_path.is_file():
        stmt = stmt_path.read_text(encoding="utf-8")
        first = next((ln.strip() for ln in stmt.splitlines() if ln.strip()), "")
        if not first.startswith("# "):
            out["statement_title"] = False
            out["ok"] = False
            out["issues"].append("checklist: statement first line not # title")
        if "def solve" in stmt:
            out["ok"] = False
            out["issues"].append("checklist: statement contains def solve")
        parsed, bind_issues, _n = parse_statement_examples(stmt, params)
        out["issues"].extend(bind_issues)
        if bind_issues:
            out["ok"] = False
            out["example_mismatch"] += 1
        if parsed:
            ncmp = min(len(parsed), len(public_rows))
            if len(parsed) != len(public_rows):
                out["example_mismatch"] += 1
                out["issues"].append("examples: public count ≠ statement examples")
            for i in range(ncmp):
                a_args, a_exp = parsed[i]
                p_args, p_exp = public_rows[i]
                if a_args != p_args or not values_equal(p_exp, a_exp, compare):
                    out["example_mismatch"] += 1
                    out["issues"].append(f"examples: public[{i}] ≠ statement example")
    if out["example_mismatch"]:
        out["ok"] = False
    if not (2 <= out["public"] <= 3):
        out["ok"] = False
        out["issues"].append(f"public count {out['public']} not in 2..3")
    if out["hidden"] < 20:
        out["ok"] = False
        out["issues"].append(f"hidden count {out['hidden']} < 20")
    solver_blocks = (not ignore_solver) and out["solver_mismatch"] > 0
    if (
        out["int32_bad"]
        or out["int64_bad"]
        or out["oversize_lines"]
        or out["expected_mismatch"]
        or solver_blocks
        or issue_codes
    ):
        out["ok"] = False

    tags: list[str] = []

    def add_tag(tag: str) -> None:
        if tag and tag not in tags:
            tags.append(tag)

    for iss in out["issues"]:
        head = iss.split(":", 1)[0].strip() if ":" in iss else ""
        mapped = {
            "checklist": "checklist",
            "examples": "examples",
            "answer": "answer",
            "dump": "dump",
            "starter": "starter",
            "signature": "signature",
            "C": "C",
            "statement": "statement",
            "out_of_bounds": "constraints",
        }.get(head)
        if mapped:
            add_tag(mapped)
    for tag in tags_for(issue_codes):
        add_tag(tag)
    if bounds.get("warnings"):
        add_tag("constraints")
    if out["int32_bad"] or out["int64_bad"]:
        add_tag("C")
    if not (2 <= out["public"] <= 3) or out["hidden"] < 20:
        add_tag("count")
    if out["solver_mismatch"]:
        add_tag("answer")
    if out["expected_mismatch"]:
        add_tag("dump")
    out["tags"] = tags
    out["issues"] = out["issues"][:12]
    write_report(root, args.slug, out)
    dump(out)
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
