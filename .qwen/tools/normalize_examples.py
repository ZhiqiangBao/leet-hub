"""Rewrite statement.md to the R2 display shape. Does not judge answers."""
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

_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
_EX_NUM = re.compile(r"^### 示例 (\d+)\s*$")
_EX_HEAD = re.compile(
    r"^(?:#{2,3}\s*|\*\*)示例\s+(\d+)\s*[：:．.]?\s*\*{0,2}\s*$"
)
_LABEL = re.compile(r"^(?:\*\*)?(输入|输出|解释)[:：](?:\*\*)?\s*(.*?)\s*$")
_LABEL_START = re.compile(r"^(?:\*\*)?(输入|输出|解释)[:：]")


def _unwrap_example_fences(text: str) -> str:
    def repl(m: re.Match) -> str:
        body = m.group(1)
        if re.search(r"输入[:：]", body) and re.search(r"输出[:：]", body):
            return body.strip("\n") + "\n"
        return m.group(0)

    return _FENCE.sub(repl, text)


def _fullwidth_label_colons(text: str) -> str:
    return re.sub(r"^(\*\*)?(输入|输出|解释)[:：]", r"\1\2：", text, flags=re.M)


def _split_joined_labels(text: str) -> str:
    text = re.sub(r"(输入：[^\n]*?)\s+(输出：)", r"\1\n\2", text)
    text = re.sub(r"(输出：[^\n]*?)\s+(解释：)", r"\1\n\2", text)
    return text


def _alias_headings(text: str) -> str:
    text = re.sub(r"^##\s*(题目描述|题意)\s*\n+", "", text, flags=re.M)
    text = re.sub(
        r"^##\s*(?:输入格式|输出格式|参数与返回值|参数|返回值)\s*\n(?:(?!^## ).*\n)*",
        "",
        text,
        flags=re.M,
    )
    text = re.sub(r"^#{2,3}\s*约束(?:条件)?\s*$", "## 约束", text, flags=re.M)
    return text


def _convert_line_heading(line: str) -> str:
    stripped = line.strip()
    if stripped in ("---", "***", "___"):
        return ""
    m = _EX_HEAD.match(stripped)
    if m:
        return f"### 示例 {m.group(1)}"
    return line


def _insert_example_numbers(lines: list[str]) -> list[str]:
    out: list[str] = []
    n = 0
    for line in lines:
        m = _EX_NUM.match(line.strip())
        if m:
            n = int(m.group(1))
            out.append(f"### 示例 {n}")
            continue
        lab = _LABEL_START.match(line.strip())
        if lab and lab.group(1) == "输入":
            j = len(out) - 1
            while j >= 0 and out[j].strip() == "":
                j -= 1
            if j < 0 or not _EX_NUM.match(out[j].strip()):
                n += 1
                if out and out[-1].strip() != "":
                    out.append("")
                out.append(f"### 示例 {n}")
                out.append("")
            out.append(line)
            continue
        out.append(line)
    return out


def _insert_example_section(lines: list[str]) -> list[str]:
    if any(re.match(r"^##\s*示例\s*$", ln.strip()) for ln in lines):
        return lines
    for i, ln in enumerate(lines):
        if _EX_NUM.match(ln.strip()):
            return lines[:i] + ["## 示例", ""] + lines[i:]
    return lines


def _format_label_line(line: str) -> str:
    m = _LABEL.match(line.strip())
    if not m:
        return line
    rest = m.group(2).strip()
    if m.group(1) in ("输入", "输出"):
        rest = re.sub(r"`([^`]+)`", r"\1", rest)
    else:
        wrapped = re.fullmatch(r"`([^`]+)`", rest)
        if wrapped:
            rest = wrapped.group(1)
    body = f"{m.group(1)}：{rest}" if rest else f"{m.group(1)}："
    return body + "  "


def _pad_heading_spacing(text: str) -> str:
    text = re.sub(r"(?<!\n)\n(#{2,3} )", r"\n\n\1", text)
    text = re.sub(r"^(#{2,3} .+)\n(?!\n)", r"\1\n\n", text, flags=re.M)
    return text


def _squeeze_label_blanks(text: str) -> str:
    return re.sub(
        r"(^(?:输入|输出|解释)：[^\n]*\n)\n+(?=(?:输入|输出|解释)：)",
        r"\1",
        text,
        flags=re.M,
    )


def normalize_layout(text: str) -> str:
    """Canonical statement shape for the web page. Keeps `# title` (R2)."""
    body = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    body = _unwrap_example_fences(body)
    body = _fullwidth_label_colons(body)
    body = _split_joined_labels(body)
    body = _alias_headings(body)
    lines = [_convert_line_heading(ln) for ln in body.split("\n")]
    lines = _insert_example_numbers(lines)
    lines = _insert_example_section(lines)
    lines = [_format_label_line(ln) for ln in lines]
    body = _squeeze_label_blanks("\n".join(lines))
    body = _pad_heading_spacing(body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip() + "\n"


def normalize(text: str, params: list[tuple[str, str]] | None = None) -> str:
    body = normalize_layout(text)
    if params:
        body, _ = rewrite_inputs_positional(body, params)
        body = normalize_layout(body)
    return body


def normalize_with_edits(
    text: str, params: list[tuple[str, str]] | None = None
) -> tuple[str, list[dict]]:
    laid = normalize_layout(text)
    edits: list[dict] = []
    if laid != text.replace("\r\n", "\n").replace("\r", "\n"):
        edits.append({"i": 0, "field": "layout", "kind": "structure"})
    body = laid
    if params:
        body, more = rewrite_inputs_positional(body, params)
        edits.extend(more)
        body = normalize_layout(body)
    return body, edits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    slugs: list[str] = []
    if args.all:
        slugs = sorted(p.parent.name for p in (root / "problems").glob("*/statement.md"))
    elif str(args.slug or "").strip():
        slugs = [args.slug.strip()]
    else:
        dump({"ok": False, "issues": ["missing slug"]})
        return 1
    results = []
    ok = True
    for slug in slugs:
        path = root / "problems" / slug / "statement.md"
        item: dict = {"ok": False, "slug": slug, "changed": False, "path": None, "edits": []}
        if not path.is_file():
            item["issues"] = ["missing statement.md"]
            ok = False
            results.append(item)
            continue
        raw = path.read_text(encoding="utf-8")
        params = load_params(root, slug)
        new, edits = normalize_with_edits(raw, params)
        item["path"] = str(path).replace("\\", "/")
        item["changed"] = new != raw.replace("\r\n", "\n").replace("\r", "\n")
        item["edits"] = edits
        if new != raw:
            path.write_text(new, encoding="utf-8", newline="\n")
        item["ok"] = True
        results.append(item)
    if args.all:
        dump({"ok": ok, "n": len(results), "changed": sum(1 for r in results if r.get("changed")), "results": results})
        return 0 if ok else 1
    dump(results[0])
    return 0 if results[0].get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
