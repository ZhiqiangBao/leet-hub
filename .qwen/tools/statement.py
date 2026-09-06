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
from int_bounds import load_sig_types, range_flags  # noqa: E402


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


def strip_starter_comments(body: str, lang: str) -> str:
    """Drop comments so `return` in notes does not look like a placeholder."""
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
        "ref": str(ref_path).replace("\\", "/") if ref_path.is_file() else None,
        "starter_missing": [],
        "starter_placeholder": [],
    }
    if not stmt_path.is_file():
        out["ok"] = False
        out["issues"].append("[清单] missing statement.md")
        return out
    stmt = stmt_path.read_text(encoding="utf-8")
    try:
        spec = importlib.util.spec_from_file_location(
            "leet_normalize_examples",
            Path(__file__).resolve().parent / "normalize_examples.py",
        )
        if spec is not None and spec.loader is not None:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fixed = mod.normalize(stmt)
            if fixed != stmt:
                stmt_path.write_text(fixed, encoding="utf-8", newline="\n")
                stmt = fixed
    except Exception:
        pass
    first = next((ln.strip() for ln in stmt.splitlines() if ln.strip()), "")
    if not first.startswith("# "):
        out["statement_title"] = False
        out["ok"] = False
        out["issues"].append("[清单] statement first line not # title")
    if "def solve" in stmt:
        out["ok"] = False
        out["issues"].append("[清单] statement contains def solve")
    if re.search(r"标准输入|stdin\b", stmt, flags=re.I):
        out["ok"] = False
        out["issues"].append("[题意] statement asks for stdin")
    if not sig_path.is_file():
        out["ok"] = False
        out["issues"].append("[签名] missing signature.yaml")
    if not meta_path.is_file():
        out["ok"] = False
        out["issues"].append("[清单] missing meta.yaml")
    for lang, path in starters.items():
        if not path.is_file():
            out["starter_missing"].append(lang)
            continue
        body = strip_starter_comments(path.read_text(encoding="utf-8"), lang)
        if re.search(r"\breturn\b", body) or re.search(r"\bmain\s*\(", body):
            out["starter_placeholder"].append(lang)
    if out["starter_missing"]:
        out["ok"] = False
        out["issues"].append("[starter] missing " + ",".join(out["starter_missing"]))
    if out["starter_placeholder"]:
        out["ok"] = False
        out["issues"].append("[starter] placeholder " + ",".join(out["starter_placeholder"]))
    n_params = param_count(root, slug)
    parsed = parse_statement_examples(stmt, n_params)
    out["examples_parsed"] = len(parsed)
    out["examples_n"] = len(re.findall(r"输入[:：]", stmt))
    if not (2 <= out["examples_n"] <= 3):
        out["ok"] = False
        out["issues"].append(f"[示例] statement example count {out['examples_n']} not in 2..3")
    elif parsed and len(parsed) != out["examples_n"]:
        out["ok"] = False
        out["issues"].append("[示例] could not parse all statement examples")
    compare = load_compare(root, slug)
    param_types, return_type = load_sig_types(root, slug)
    saw32 = saw64 = False
    for args, expected in parsed:
        bad32, bad64 = range_flags(args, expected, param_types, return_type)
        saw32 = saw32 or bad32
        saw64 = saw64 or bad64
    if saw32:
        out["ok"] = False
        out["issues"].append("[C] statement example int32")
    if saw64:
        out["ok"] = False
        out["issues"].append("[C] statement example int64")
    if not skip_ref:
        solve = load_solve(ref_path) if ref_path.is_file() else None
        if solve is None:
            out["ok"] = False
            out["issues"].append("[答案] missing solve()")
        else:
            for args, expected in parsed:
                st, got = run_solve(solve, args)
                if st != "ok" or not values_equal(got, expected, compare):
                    out["ref_example_mismatch"] += 1
        if out["ref_example_mismatch"]:
            out["ok"] = False
            out["issues"].append(f"[示例] ref≠statement example x{out['ref_example_mismatch']}")
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
    json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    print()
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
