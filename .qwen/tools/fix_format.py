"""Fix problem-file format: example lines, missing meta bounds, starters. Does not judge 题意."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from constraints import load_bounds  # noqa: E402
from utf8io import dump  # noqa: E402

BOUND_DEFAULTS = (
    ("n_min", "1"),
    ("n_max", "100000"),
    ("elem_min", "-1000000000"),
    ("elem_max", "1000000000"),
)


def _run(script: Path, slug: str, root: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(script), "--slug", slug, "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    line = (proc.stdout or "").strip().splitlines()[-1] if (proc.stdout or "").strip() else ""
    try:
        data = json.loads(line) if line else {}
    except json.JSONDecodeError:
        data = {"ok": False, "raw": line[:200]}
    if proc.returncode != 0:
        data["ok"] = False
    return data


def ensure_meta_bounds(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    added: list[str] = []
    for key, default in BOUND_DEFAULTS:
        if re.search(rf"^{re.escape(key)}\s*:", text, flags=re.M):
            continue
        added.append(f"{key}: {default}")
    if not added:
        return False
    body = text.rstrip() + "\n" + "\n".join(added) + "\n"
    path.write_text(body, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--skip-starters", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    scripts = Path(__file__).resolve().parent
    meta = root / "problems" / args.slug / "meta.yaml"
    out: dict = {
        "ok": True,
        "slug": args.slug,
        "meta_bounds_filled": False,
        "examples": {},
        "starters": {},
    }
    if meta.is_file():
        out["meta_bounds_filled"] = ensure_meta_bounds(meta)
        b = load_bounds(root, args.slug)
        warns = list(b.get("warnings") or [])
        notes = list(b.get("notes") or [])
        if warns:
            out.setdefault("issues", []).extend(warns)
            out["ok"] = False
        if notes:
            out["bounds_notes"] = notes
    elif not (root / "problems" / args.slug).is_dir():
        out["ok"] = False
        out["issues"] = ["missing problem dir"]
        dump(out)
        return 1
    out["examples"] = _run(scripts / "normalize_examples.py", args.slug, root)
    if not out["examples"].get("ok", False):
        out["ok"] = False
    if not args.skip_starters and (root / "problems" / args.slug / "signature.yaml").is_file():
        out["starters"] = _run(scripts / "write_starters.py", args.slug, root)
        if not out["starters"].get("ok", False):
            out["ok"] = False
    dump(out)
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
