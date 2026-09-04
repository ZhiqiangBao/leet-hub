"""Write problems/<slug>/tests.jsonl. Print metrics only — never the cases."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SKILLS = Path(__file__).resolve().parent.parent
if str(_SKILLS) not in sys.path:
    sys.path.insert(0, str(_SKILLS))
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


def case_n(args) -> int:
    if not isinstance(args, (list, tuple)) or not args:
        return 0
    for x in args:
        if isinstance(x, (list, str)):
            return len(x)
    if isinstance(args[0], int) and not isinstance(args[0], bool):
        return int(args[0])
    return 0


def dump(slug: str, rows: list[dict], root: Path) -> None:
    solve = load_solve(slug, root)
    param_types, return_type = load_sig_types(root, slug)
    public = 0
    hidden = 0
    hns: list[int] = []
    int32_bad = 0
    int64_bad = 0
    oversize = 0
    solve_err = 0
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
        if rec["hidden"]:
            hidden += 1
            hns.append(case_n(args or []))
        else:
            public += 1
    ok = (
        2 <= public <= 3
        and hidden >= 20
        and int32_bad == 0
        and int64_bad == 0
        and oversize == 0
        and solve_err == 0
    )
    path = root / "problems" / slug / "tests.jsonl"
    path.write_text("".join(chunks), encoding="utf-8")
    nmax = max(hns) if hns else None
    hist = {
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
    summary = {
        "ok": ok,
        "slug": slug,
        "public": public,
        "hidden": hidden,
        "n_min": min(hns) if hns else None,
        "n_max": nmax,
        "hidden_n": hist,
        "n_kind": "length"
        if any(isinstance(x, (list, str)) for r in rows if r.get("hidden") for x in (r.get("args") or []))
        else "scalar",
        "int32_bad": int32_bad,
        "int64_bad": int64_bad,
        "oversize_lines": oversize,
        "solve_err": solve_err,
    }
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    if not ok:
        raise SystemExit(1)
