"""Rewrite statement.md example lines to the R2 machine-check shape. Does not judge answers."""
from __future__ import annotations

import argparse
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
import sys

if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from constraints import load_params  # noqa: E402
from examples import rewrite_inputs_positional  # noqa: E402
from utf8io import dump  # noqa: E402
import re


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


def normalize(text: str, params: list[tuple[str, str]] | None = None) -> str:
    body = _normalize_triple_lines(_unwrap_example_fences(text))
    if params:
        body, _ = rewrite_inputs_positional(body, params)
    return body


def normalize_with_edits(
    text: str, params: list[tuple[str, str]] | None = None
) -> tuple[str, list[dict]]:
    body = _normalize_triple_lines(_unwrap_example_fences(text))
    edits: list[dict] = []
    if body != text:
        edits.append({"i": 0, "field": "layout", "kind": "fence_or_colon"})
    if params:
        body, more = rewrite_inputs_positional(body, params)
        edits.extend(more)
    return body, edits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    path = root / "problems" / args.slug / "statement.md"
    out: dict = {"ok": False, "slug": args.slug, "changed": False, "path": None, "edits": []}
    if not path.is_file():
        out["issues"] = ["missing statement.md"]
        dump(out)
        return 1
    raw = path.read_text(encoding="utf-8")
    params = load_params(root, args.slug)
    new, edits = normalize_with_edits(raw, params)
    out["path"] = str(path).replace("\\", "/")
    out["changed"] = new != raw
    out["edits"] = edits
    if out["changed"]:
        path.write_text(new, encoding="utf-8", newline="\n")
    out["ok"] = True
    dump(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
