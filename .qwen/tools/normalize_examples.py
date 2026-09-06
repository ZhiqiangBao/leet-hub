"""Rewrite statement.md example lines to the R2 machine-check shape. Does not judge answers."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _unwrap_example_fences(text: str) -> str:
    def repl(m: re.Match) -> str:
        body = m.group(1)
        if re.search(r"输入[:：]", body) and re.search(r"输出[:：]", body):
            return body.strip("\n") + "\n"
        return m.group(0)

    return re.sub(r"```(?:[^\n]*)\n(.*?)```", repl, text, flags=re.S)


def _normalize_triple_lines(text: str) -> str:
    text = re.sub(r"(输入|输出|解释)[:：]", r"\1：", text)
    text = re.sub(
        r"^(\*\*)?(输入|输出|解释)：\s*\n\s*(\S[^\n]*?)(\*\*)?\s*$",
        r"\2：\3",
        text,
        flags=re.M,
    )
    text = re.sub(
        r"^\*\*((?:输入|输出|解释)：[^*]+)\*\*\s*$",
        r"\1",
        text,
        flags=re.M,
    )
    text = re.sub(
        r"^((?:输入|输出|解释)：)\s*`([^`]+)`\s*$",
        r"\1\2",
        text,
        flags=re.M,
    )
    return text


def normalize(text: str) -> str:
    return _normalize_triple_lines(_unwrap_example_fences(text))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    path = root / "problems" / args.slug / "statement.md"
    out: dict = {"ok": False, "slug": args.slug, "changed": False, "path": None}
    if not path.is_file():
        out["issues"] = ["missing statement.md"]
        json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))
        print()
        return 1
    raw = path.read_text(encoding="utf-8")
    new = normalize(raw)
    out["path"] = str(path).replace("\\", "/")
    out["changed"] = new != raw
    if out["changed"]:
        path.write_text(new, encoding="utf-8", newline="\n")
    out["ok"] = True
    json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
