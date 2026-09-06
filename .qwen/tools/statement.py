"""Statement/starter/example checks. No tests.jsonl. Do not print examples."""
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
from constraints import load_params  # noqa: E402
from examples import parse_statement_examples  # noqa: E402
from int_bounds import load_sig_types, range_flags  # noqa: E402
from utf8io import dump  # noqa: E402


def values_equal(got, expected, compare: str) -> bool:
    if compare == "any_order" and isinstance(got, list) and isinstance(expected, list):
        if len(got) != len(expected):
            return False
        key = lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False)
        return sorted(got, key=key) == sorted(expected, key=key)
    return got == expected


def load_solve(path: Path):
    spec = importlib.util.spec_from_file_location("leet_ref", path)
    if spec is None or spec.loader is None:
        return None, "import_error"
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:
        return None, "import_error"
    solve = getattr(mod, "solve", None)
    if solve is None:
        return None, "import_error"
    return solve, None


def load_compare(root: Path, slug: str) -> str:
    path = root / "problems" / slug / "signature.yaml"
    if not path.is_file():
        return "exact"
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("compare:"):
            return s.split(":", 1)[1].strip().split("#", 1)[0].strip() or "exact"
    return "exact"


def strip_starter_comments(body: str, lang: str) -> str:
    if lang == "python3":
        return "\n".join(re.sub(r"#.*", "", line) for line in body.splitlines())
    out = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    out = re.sub(r"//.*", "", out)
    return out


def run_solve(solve, args):
    if solve is None:
        return "missing", None
    try:
        return "ok", solve(*args)
    except Exception as exc:
        return type(exc).__name__, None


def check_statement(
    root: Path, slug: str, *, skip_ref: bool = False, ref: Path | None = None
) -> dict:
    stmt_path = root / "problems" / slug / "statement.md"
    sig_path = root / "problems" / slug / "signature.yaml"
    meta_path = root / "problems" / slug / "meta.yaml"
    ref_path = Path(ref) if ref else root / ".qwen" / "tmp" / f"{slug}_ref.py"
    if not ref_path.is_absolute():
        ref_path = root / ref_path
    starters = {
        "python3": root / "problems" / slug / "starter" / "python3.py",
        "c": root / "problems" / slug / "starter" / "c.c",
        "cpp17": root / "problems" / slug / "starter" / "cpp17.cpp",
        "javascript": root / "problems" / slug / "starter" / "javascript.js",
        "typescript": root / "problems" / slug / "starter" / "typescript.ts",
        "go": root / "problems" / slug / "starter" / "go.go",
        "rust": root / "problems" / slug / "starter" / "rust.rs",
        "zig": root / "problems" / slug / "starter" / "zig.zig",
    }
    out: dict = {
        "ok": True,
        "slug": slug,
        "issues": [],
        "statement_title": True,
        "examples_n": 0,
        "examples_parsed": 0,
        "ref_example_mismatch": 0,
        "import_error": 0,
        "call_error": 0,
        "value_mismatch": 0,
        "ref": str(ref_path).replace("\\", "/") if ref_path.is_file() else None,
        "starter_missing": [],
        "starter_placeholder": [],
    }
    if not stmt_path.is_file():
        out["ok"] = False
        out["issues"].append("checklist: missing statement.md")
        return out
    stmt = stmt_path.read_text(encoding="utf-8")
    params = load_params(root, slug)
    try:
        from normalize_examples import normalize as _norm

        fixed = _norm(stmt, params)
        if fixed != stmt:
            stmt_path.write_text(fixed, encoding="utf-8", newline="\n")
            stmt = fixed
    except Exception:
        pass
    first = next((ln.strip() for ln in stmt.splitlines() if ln.strip()), "")
    if not first.startswith("# "):
        out["statement_title"] = False
        out["ok"] = False
        out["issues"].append("checklist: statement first line not # title")
    if "def solve" in stmt:
        out["ok"] = False
        out["issues"].append("checklist: statement contains def solve")
    if re.search(r"标准输入|stdin\b", stmt, flags=re.I):
        out["ok"] = False
        out["issues"].append("statement: statement asks for stdin")
    if not sig_path.is_file():
        out["ok"] = False
        out["issues"].append("signature: missing signature.yaml")
    if not meta_path.is_file():
        out["ok"] = False
        out["issues"].append("checklist: missing meta.yaml")
    for lang, path in starters.items():
        if not path.is_file():
            out["starter_missing"].append(lang)
            continue
        body = strip_starter_comments(path.read_text(encoding="utf-8"), lang)
        if re.search(r"\breturn\b", body) or re.search(r"\bmain\s*\(", body):
            out["starter_placeholder"].append(lang)
    if out["starter_missing"]:
        out["ok"] = False
        out["issues"].append("starter: missing " + ",".join(out["starter_missing"]))
    if out["starter_placeholder"]:
        out["ok"] = False
        out["issues"].append("starter: placeholder " + ",".join(out["starter_placeholder"]))
    parsed, bind_issues, examples_n = parse_statement_examples(stmt, params)
    out["examples_parsed"] = len(parsed)
    out["examples_n"] = examples_n
    out["issues"].extend(bind_issues)
    if bind_issues:
        out["ok"] = False
    if not (2 <= out["examples_n"] <= 3):
        out["ok"] = False
        out["issues"].append(f"examples: statement example count {out['examples_n']} not in 2..3")
    elif parsed and len(parsed) != out["examples_n"]:
        out["ok"] = False
        if not bind_issues:
            out["issues"].append("examples: could not parse all statement examples")
    compare = load_compare(root, slug)
    param_types, return_type = load_sig_types(root, slug)
    saw32 = saw64 = False
    for args, expected in parsed:
        bad32, bad64 = range_flags(args, expected, param_types, return_type)
        saw32 = saw32 or bad32
        saw64 = saw64 or bad64
    if saw32:
        out["ok"] = False
        out["issues"].append("C: statement example int32")
    if saw64:
        out["ok"] = False
        out["issues"].append("C: statement example int64")
    if not skip_ref:
        solve, ierr = load_solve(ref_path) if ref_path.is_file() else (None, "import_error")
        if solve is None:
            out["ok"] = False
            out["import_error"] = max(1, out["examples_n"] or 1)
            out["ref_example_mismatch"] = out["import_error"]
            out["issues"].append("answer: missing solve(); import_error")
        else:
            for args, expected in parsed:
                st, got = run_solve(solve, args)
                if st != "ok":
                    out["call_error"] += 1
                elif not values_equal(got, expected, compare):
                    out["value_mismatch"] += 1
            out["ref_example_mismatch"] = (
                out["import_error"] + out["call_error"] + out["value_mismatch"]
            )
            if out["call_error"]:
                out["ok"] = False
                out["issues"].append(
                    f"examples: solve not called x{out['call_error']} (call_error)"
                )
            if out["value_mismatch"]:
                out["ok"] = False
                out["issues"].append(
                    f"examples: ref≠statement example x{out['value_mismatch']} (value_mismatch)"
                )
    out["skip_ref"] = skip_ref
    out["issues"] = out["issues"][:12]
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--skip-ref",
        action="store_true",
        help="do not require or run solve() (quality stage, before oracle exists)",
    )
    parser.add_argument(
        "--ref",
        default="",
        help="solve() file; default .qwen/tmp/<slug>_ref.py",
    )
    args = parser.parse_args()
    ref = Path(args.ref) if args.ref else None
    out = check_statement(Path(args.root), args.slug, skip_ref=args.skip_ref, ref=ref)
    dump(out)
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
