"""Mechanical checks for problems/<slug>/tests.jsonl. Do not print the cases."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

_SKILLS = Path(__file__).resolve().parent.parent
if str(_SKILLS) not in sys.path:
    sys.path.insert(0, str(_SKILLS))
from int_bounds import load_sig_types, range_flags  # noqa: E402

LINE_LIMIT = 7_500_000


def load_solve(path: Path):
    spec = importlib.util.spec_from_file_location("leet_ref", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "solve", None)


def case_n(args) -> int:
    if not isinstance(args, (list, tuple)) or not args:
        return 0
    for x in args:
        if isinstance(x, (list, str)):
            return len(x)
    if isinstance(args[0], int) and not isinstance(args[0], bool):
        return int(args[0])
    return 0


def hist_hidden(hns: list[int]) -> dict:
    nmax = max(hns) if hns else None
    return {
        "lt100": sum(1 for n in hns if n < 100),
        "m100_5000": sum(1 for n in hns if 100 <= n <= 5000),
        "eq_1e5": sum(1 for n in hns if n == 10**5),
        "eq_1e9": sum(1 for n in hns if n == 10**9),
        "at_max": sum(1 for n in hns if nmax is not None and n == nmax),
        "other": sum(
            1
            for n in hns
            if not (n < 100 or 100 <= n <= 5000 or n in (10**5, 10**9))
        ),
    }


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


def param_count(root: Path, slug: str) -> int:
    path = root / "problems" / slug / "signature.yaml"
    if not path.is_file():
        return 0
    n = 0
    in_params = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("params:"):
            in_params = True
            continue
        if in_params:
            if line.startswith(" ") or line.startswith("\t"):
                if line.strip().startswith("- "):
                    n += 1
            else:
                break
    return n


def coerce_expected(text: str):
    s = text.strip().strip("`").rstrip("。.")
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s.startswith("["):
        try:
            return json.loads(s.replace("'", '"'))
        except json.JSONDecodeError:
            return s
    try:
        return int(s)
    except ValueError:
        pass
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_args_blob(blob: str, n_params: int):
    blob = blob.strip().strip("`")
    strings = re.findall(r'"([^"]*)"', blob)
    lists: list = []
    for m in re.finditer(r"\[[^\[\]]*\]", blob):
        try:
            lists.append(json.loads(m.group().replace("'", '"')))
        except json.JSONDecodeError:
            pass
    ints = [int(x) for x in re.findall(r"-?\d+", blob)]
    if n_params <= 0:
        return None
    if n_params == 1:
        payload = blob.split("=", 1)[-1].strip()
        if payload.startswith("[") and lists:
            return [lists[0]]
        if strings:
            return [strings[0]]
        if lists:
            return [lists[0]]
        if ints:
            return [ints[0]]
        return None
    if strings:
        rest = n_params - len(strings)
        if rest < 0:
            return None
        if lists and rest:
            return strings + lists[:rest]
        if rest and len(ints) >= rest:
            return strings + ints[-rest:]
        if rest == 0:
            return strings
        return None
    if lists:
        rest = n_params - len(lists)
        if rest == 0:
            return lists
        if rest > 0 and len(ints) >= rest:
            return lists + ints[-rest:]
        return None
    if len(ints) >= n_params:
        return ints[:n_params]
    return None


def parse_statement_examples(text: str, n_params: int) -> list[tuple[list, object]]:
    rows: list[tuple[list, object]] = []
    matches = re.findall(r"输入[:：]\s*(.*?)\s*输出[:：]\s*([^\n]+)", text, flags=re.S)
    for raw_in, raw_out in matches:
        raw_in = re.sub(r"\s+", " ", raw_in).strip()
        args = parse_args_blob(raw_in, n_params)
        if args is None:
            continue
        rows.append((args, coerce_expected(raw_out)))
    return rows


def args_n_kind(args) -> str:
    if not isinstance(args, (list, tuple)):
        return "scalar"
    for x in args:
        if isinstance(x, (list, str)):
            return "length"
    return "scalar"


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

    out: dict = {
        "ok": True,
        "slug": args.slug,
        "public": 0,
        "hidden": 0,
        "lines": 0,
        "issues": [],
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
        "hidden_n": {},
        "n_kind": "length",
        "example_mismatch": 0,
        "statement_title": True,
    }

    if not tests_path.is_file():
        out["ok"] = False
        out["issues"].append("missing tests.jsonl")
        json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))
        print()
        return 1

    hns: list[int] = []
    kinds: list[str] = []
    public_rows: list[tuple[list, object]] = []
    author = load_solve(ref_path) if ref_path.is_file() else None
    solver = load_solve(solver_path) if solver_path.is_file() else None
    compare = load_compare(root, args.slug)
    param_types, return_type = load_sig_types(root, args.slug)
    if author is None:
        out["ok"] = False
        out["issues"].append("[dump] missing ref.py solve()")
    if solver is None:
        out["ok"] = False
        out["issues"].append("missing solve2.py; re-dispatch solver")

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
        if obj.get("hidden"):
            out["hidden"] += 1
            hns.append(case_n(obj.get("args") or []))
            kinds.append(args_n_kind(obj.get("args") or []))
        else:
            out["public"] += 1
            public_rows.append((obj.get("args"), obj.get("expected")))
        bad32, bad64 = range_flags(
            obj.get("args"), obj.get("expected"), param_types, return_type
        )
        if bad32:
            out["int32_bad"] += 1
            out["issues"].append(f"line {i} int32")
        if bad64:
            out["int64_bad"] += 1
            out["issues"].append(f"line {i} int64")
        case_args = obj.get("args")
        expected = obj.get("expected")
        st, got = run_solve(author, case_args)
        if author is not None and (st != "ok" or not values_equal(got, expected, compare)):
            out["expected_mismatch"] += 1
            if len(out["mismatch_lines"]) < 8:
                out["mismatch_lines"].append(i)
                out["issues"].append(f"line {i} [dump] ref≠expected")
        st2, got2 = run_solve(solver, case_args)
        if solver is not None and (st2 != "ok" or not values_equal(got2, expected, compare)):
            out["solver_mismatch"] += 1
            if len(out["mismatch_lines"]) < 8:
                out["mismatch_lines"].append(i)
            if out["solver_mismatch"] <= 5:
                out["issues"].append(f"line {i} [答案] solver≠expected")

    out["n_min"] = min(hns) if hns else None
    out["n_max"] = max(hns) if hns else None
    out["hidden_n"] = hist_hidden(hns)
    out["n_kind"] = "length" if any(k == "length" for k in kinds) else "scalar"
    stmt_path = root / "problems" / args.slug / "statement.md"
    if stmt_path.is_file():
        stmt = stmt_path.read_text(encoding="utf-8")
        first = next((ln.strip() for ln in stmt.splitlines() if ln.strip()), "")
        if not first.startswith("# "):
            out["statement_title"] = False
            out["ok"] = False
            out["issues"].append("[清单] statement first line not # title")
        if "def solve" in stmt:
            out["ok"] = False
            out["issues"].append("[清单] statement contains def solve")
        parsed = parse_statement_examples(stmt, param_count(root, args.slug))
        if parsed:
            ncmp = min(len(parsed), len(public_rows))
            if len(parsed) != len(public_rows):
                out["example_mismatch"] += 1
                out["issues"].append("[示例] public count ≠ statement examples")
            for i in range(ncmp):
                a_args, a_exp = parsed[i]
                p_args, p_exp = public_rows[i]
                if a_args != p_args or not values_equal(p_exp, a_exp, compare):
                    out["example_mismatch"] += 1
                    out["issues"].append(f"[示例] public[{i}] ≠ statement example")
    if out["example_mismatch"]:
        out["ok"] = False
    if not (2 <= out["public"] <= 3):
        out["ok"] = False
        out["issues"].append(f"public count {out['public']} not in 2..3")
    if out["hidden"] < 20:
        out["ok"] = False
        out["issues"].append(f"hidden count {out['hidden']} < 20")
    if out["int32_bad"] or out["int64_bad"] or out["oversize_lines"] or out["expected_mismatch"] or out["solver_mismatch"]:
        out["ok"] = False

    out["issues"] = out["issues"][:12]
    json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    print()
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
