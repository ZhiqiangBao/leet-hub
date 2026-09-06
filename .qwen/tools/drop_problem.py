"""Remove one abandoned slug from disk. Editor only. Does not touch catalog or desk."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def drop_problem(root: Path, slug: str) -> dict:
    if not SLUG_RE.fullmatch(slug):
        return {"ok": False, "slug": slug, "error": "bad slug", "removed": []}
    problems_root = (root / "problems").resolve()
    problem_dir = (problems_root / slug).resolve()
    try:
        problem_dir.relative_to(problems_root)
    except ValueError:
        return {"ok": False, "slug": slug, "error": "bad slug", "removed": []}
    if problem_dir == problems_root:
        return {"ok": False, "slug": slug, "error": "bad slug", "removed": []}

    removed: list[str] = []
    if problem_dir.is_dir():
        shutil.rmtree(problem_dir)
        removed.append(f"problems/{slug}")

    tmp = (root / ".qwen" / "tmp").resolve()
    if tmp.is_dir():
        for path in sorted(tmp.glob(f"{slug}_*.py")):
            if not path.is_file():
                continue
            path.unlink()
            removed.append(f".qwen/tmp/{path.name}")

    return {"ok": True, "slug": slug, "removed": removed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default="")
    args = parser.parse_args()
    root = Path(args.root) if args.root else Path(__file__).resolve().parents[2]
    summary = drop_problem(root.resolve(), args.slug.strip())
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
