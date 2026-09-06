"""Write problems/<slug>/tests.jsonl. Print metrics only — never the cases."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from constraints import (  # noqa: E402
    args_n_kind,
    case_n,
    check_case,
    hist_hidden,
    load_bounds,
    load_params,
    overlay_bounds,
    scale_issues,
    tags_for,
)
from int_bounds import load_sig_types, range_flags  # noqa: E402

LINE_LIMIT = 7_500_000


def load_solve_path(path: Path):
    spec = importlib.util.spec_from_file_location("leet_ref", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"missing {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    solve = getattr(mod, "solve", None)
    if solve is None:
        raise SystemExit(f"no solve() in {path}")
    return solve


def load_solve(slug: str, root: Path) -> object:
    return load_solve_path(root / ".qwen" / "tmp" / f"{slug}_ref.py")


def fill_jsonl_expected(slug: str, root: Path, ref_path: Path | None = None) -> dict:
    """Rewrite expected in tests.jsonl from solve. Print nothing but return counts."""
    solve = load_solve_path(ref_path) if ref_path else load_solve(slug, root)
    path = root / "problems" / slug / "tests.jsonl"
    if not path.is_file():
        raise SystemExit(f"missing {path}")
    rows = []
    err = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        try:
            obj["expected"] = solve(*obj["args"])
        except Exception:
            err += 1
        rows.append(obj)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8",
    )
    return {"slug": slug, "filled": len(rows), "solve_err": err}


def dump(
    slug: str,
    rows: list[dict],
    root: Path,
    n_min=None,
    n_max=None,
    elem_min=None,
    elem_max=None,
    param_bounds=None,
) -> None:
    """Write jsonl. Optional bound kwargs overlay meta.yaml (long 题可把 elem_max 提到 int64)."""
    solve = load_solve(slug, root)
    param_types, return_type = load_sig_types(root, slug)
    params = load_params(root, slug)
    bounds = overlay_bounds(
        load_bounds(root, slug),
        n_min=n_min,
        n_max=n_max,
        elem_min=elem_min,
        elem_max=elem_max,
        param_bounds=param_bounds,
    )
    public = 0
    hidden = 0
    hns: list[int] = []
    kinds: list[str] = []
    int32_bad = 0
    int64_bad = 0
    oversize = 0
    solve_err = 0
    bound_codes: list[str] = []
    chunks: list[str] = []
    for r in rows:
        args = r.get("args")
        try:
            expected = solve(*args)
        except Exception:
            solve_err += 1
            expected = r.get("expected")
        rec = {"args": args, "expected": expected, "hidden": bool(r.get("hidden"))}
        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        if len(line.encode("utf-8")) > LINE_LIMIT:
            oversize += 1
        chunks.append(line + "\n")
        bad32, bad64 = range_flags(args, expected, param_types, return_type)
        if bad32:
            int32_bad += 1
        if bad64:
            int64_bad += 1
        bound_codes.extend(check_case(args or [], params, bounds))
        if rec["hidden"]:
            hidden += 1
            hns.append(case_n(args or []))
            kinds.append(args_n_kind(args or []))
        else:
            public += 1
    n_kind = "length" if any(k == "length" for k in kinds) else "scalar"
    scale_codes = scale_issues(hns, n_kind, bounds)
    issue_codes = list(dict.fromkeys(bound_codes + scale_codes))
    ok = (
        2 <= public <= 3
        and hidden >= 20
        and int32_bad == 0
        and int64_bad == 0
        and oversize == 0
        and solve_err == 0
        and not issue_codes
    )
    path = root / "problems" / slug / "tests.jsonl"
    path.write_text("".join(chunks), encoding="utf-8")
    nmax = max(hns) if hns else None
    summary = {
        "ok": ok,
        "slug": slug,
        "public": public,
        "hidden": hidden,
        "n_min": min(hns) if hns else None,
        "n_max": nmax,
        "U": bounds["n_max"],
        "hidden_n": hist_hidden(hns),
        "n_kind": n_kind,
        "int32_bad": int32_bad,
        "int64_bad": int64_bad,
        "oversize_lines": oversize,
        "solve_err": solve_err,
        "issues": issue_codes,
        "tags": tags_for(issue_codes),
    }
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    if not ok:
        raise SystemExit(1)
