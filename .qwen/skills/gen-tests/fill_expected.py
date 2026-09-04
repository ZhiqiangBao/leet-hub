"""Refill tests.jsonl expected from a solve() file. Do not print cases."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT_DEFAULT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default="")
    parser.add_argument("--ref", default="", help="solve() file; default tmp/<slug>_ref.py")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="copy --ref onto tmp/<slug>_ref.py after filling",
    )
    args = parser.parse_args()
    root = Path(args.root) if args.root else ROOT_DEFAULT
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from emit import fill_jsonl_expected

    ref = Path(args.ref) if args.ref else root / ".qwen" / "tmp" / f"{args.slug}_ref.py"
    out = fill_jsonl_expected(args.slug, root, ref)
    if args.promote and ref.resolve() != (root / ".qwen" / "tmp" / f"{args.slug}_ref.py").resolve():
        dest = root / ".qwen" / "tmp" / f"{args.slug}_ref.py"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ref, dest)
        out["promoted"] = str(dest).replace("\\", "/")
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    return 0 if out.get("solve_err", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
