"""Parse/bind statement example inputs to signature.yaml. Never print examples."""
from __future__ import annotations

import json
import re
from pathlib import Path

_INPUT_RE = re.compile(r"输入[:：]\s*(.*?)\s*输出[:：]\s*([^\n]+)", flags=re.S)
_NAME_EQ = re.compile(r"^([A-Za-z_]\w*)\s*=\s*(.*)$")
_IO_LINE = re.compile(r"^(\*\*)?(输入|输出)[:：](\*\*)?\s*(.*?)\s*$")
_FENCE_LANGS = (
    "json",
    "javascript",
    "js",
    "python",
    "py",
    "text",
    "txt",
    "html",
    "xml",
    "c",
    "cpp",
    "java",
)
_FENCE_LANG = re.compile(
    r"^(?:" + "|".join(_FENCE_LANGS) + r")\s+",
    re.I,
)
_FENCE_LANG_TOKEN = re.compile(
    r"^(?:" + "|".join(_FENCE_LANGS) + r")$",
    re.I,
)


def _compact_value(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _inner_from_inline_fence(rest: str) -> str | None:
    if not rest.startswith("```"):
        return None
    body = rest[3:]
    if "```" not in body:
        return None
    inner, _tail = body.rsplit("```", 1)
    inner = inner.strip()
    m = re.match(r"^([A-Za-z][\w+-]*)(?:\s+([\s\S]+))?$", inner)
    rest = (m.group(2) or "").strip() if m else ""
    if rest and m and _FENCE_LANG_TOKEN.match(m.group(1)):
        inner = rest
    return _compact_value(inner)


def unwrap_value_fences(text: str) -> str:
    """Hoist ``` fences that wrap only 输入/输出 values onto the label line."""
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    def consume_fence(start: int, open_rest: str) -> tuple[str, int]:
        parts: list[str] = []
        extra = open_rest.strip()
        if extra and not _FENCE_LANG_TOKEN.match(extra):
            parts.append(extra)
        j = start
        while j < n:
            stripped = lines[j].strip()
            if stripped.startswith("```"):
                return _compact_value("\n".join(parts)), j + 1
            parts.append(lines[j])
            j += 1
        return _compact_value("\n".join(parts)), j

    while i < n:
        m = _IO_LINE.match(lines[i].strip())
        if not m:
            out.append(lines[i])
            i += 1
            continue
        kind = m.group(2)
        rest = (m.group(4) or "").strip()
        inline = _inner_from_inline_fence(rest)
        if inline is not None:
            out.append(f"{kind}：{inline}" if inline else f"{kind}：")
            i += 1
            continue
        if rest.startswith("```"):
            inner, nxt = consume_fence(i + 1, rest[3:])
            out.append(f"{kind}：{inner}" if inner else f"{kind}：")
            i = nxt
            continue
        if rest == "":
            j = i + 1
            while j < n and lines[j].strip() == "":
                j += 1
            if j < n and lines[j].strip().startswith("```"):
                inner, nxt = consume_fence(j + 1, lines[j].strip()[3:])
                out.append(f"{kind}：{inner}" if inner else f"{kind}：")
                i = nxt
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def coerce_expected(text: str):
    s = (text or "").strip().replace("```", " ")
    s = _FENCE_LANG.sub("", s.strip())
    s = s.strip().strip("`").rstrip("。.")
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


def _inner(type_name: str) -> str | None:
    t = (type_name or "").strip()
    if t.startswith("List[") and t.endswith("]"):
        return t[5:-1].strip()
    return None


def parse_value(token: str):
    s = token.strip().strip("`")
    if not s:
        return None
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    try:
        return json.loads(s.replace("'", '"'))
    except json.JSONDecodeError:
        pass
    try:
        return int(s)
    except ValueError:
        return s


def value_matches(val, typ: str) -> bool:
    inner = _inner(typ)
    if typ in ("int", "long"):
        return isinstance(val, int) and not isinstance(val, bool)
    if typ == "bool":
        return isinstance(val, bool)
    if typ == "str":
        return isinstance(val, str)
    if inner in ("int", "long"):
        return isinstance(val, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in val)
    if inner == "str":
        return isinstance(val, list) and all(isinstance(x, str) for x in val)
    if inner == "bool":
        return isinstance(val, list) and all(isinstance(x, bool) for x in val)
    return True


def split_top(blob: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    in_str = False
    quote = ""
    for ch in blob:
        if in_str:
            buf.append(ch)
            if ch == quote:
                in_str = False
            continue
        if ch in "\"'":
            in_str = True
            quote = ch
            buf.append(ch)
            continue
        if ch in "[({":
            depth += 1
            buf.append(ch)
        elif ch in "])}":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == "," and depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
        else:
            buf.append(ch)
    part = "".join(buf).strip()
    if part:
        parts.append(part)
    return parts


def format_positional(args: list) -> str:
    bits = []
    for a in args:
        bits.append(json.dumps(a, ensure_ascii=False))
    return ", ".join(bits)


def _typecheck(args: list, params: list[tuple[str, str]]) -> str | None:
    if len(args) != len(params):
        names = ",".join(n for n, _ in params)
        return f"got {len(args)} args, signature has {len(params)} ({names})"
    for val, (name, typ) in zip(args, params):
        if not value_matches(val, typ):
            return f"param {name} cannot bind"
    return None


def bind_input(blob: str, params: list[tuple[str, str]]) -> tuple[list | None, str | None]:
    """Bind one 输入 blob to signature order. On failure args is None and err names the param."""
    blob = re.sub(r"\s+", " ", (blob or "").strip().strip("`"))
    if not params:
        return None, "missing signature params"
    parts = split_top(blob)
    names = [n for n, _ in params]
    named: dict[str, object] = {}
    unnamed: list[object] = []
    for part in parts:
        m = _NAME_EQ.match(part)
        if m:
            named[m.group(1)] = parse_value(m.group(2))
        else:
            unnamed.append(parse_value(part))
    if named:
        unknown = [k for k in named if k not in names]
        if unnamed or unknown:
            bad = unknown[0] if unknown else names[min(len(named), len(names) - 1)]
            return None, f"param {bad} cannot bind"
        args = []
        for name, typ in params:
            if name not in named:
                return None, f"param {name} cannot bind"
            args.append(named[name])
        err = _typecheck(args, params)
        return (None, err) if err else (args, None)
    if unnamed and len(unnamed) == len(params):
        err = _typecheck(unnamed, params)
        return (None, err) if err else (unnamed, None)
    if "=" in blob:
        miss = names[min(len(unnamed), len(names) - 1)]
        return None, f"param {miss} cannot bind"
    harvested = _harvest(blob, len(params))
    if harvested is None:
        miss = names[min(len(unnamed), len(names) - 1)]
        return None, f"param {miss} cannot bind"
    err = _typecheck(harvested, params)
    return (None, err) if err else (harvested, None)


def _harvest(blob: str, n_params: int) -> list | None:
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


def parse_statement_examples(
    text: str, params: list[tuple[str, str]]
) -> tuple[list[tuple[list, object]], list[str], int]:
    """Return bound rows, bind issues, and 输入 count."""
    text = unwrap_value_fences(text)
    rows: list[tuple[list, object]] = []
    issues: list[str] = []
    matches = _INPUT_RE.findall(text)
    for i, (raw_in, raw_out) in enumerate(matches, 1):
        args, err = bind_input(raw_in, params)
        if args is None:
            issues.append(f"examples: example {i} {err or 'cannot bind'}")
            continue
        rows.append((args, coerce_expected(raw_out)))
    return rows, issues, len(matches)


def rewrite_inputs_positional(text: str, params: list[tuple[str, str]]) -> tuple[str, list[dict]]:
    """Rewrite kv 输入 blobs to positional. edits do not include values."""
    edits: list[dict] = []
    idx = {"n": 0}

    def repl(m: re.Match) -> str:
        idx["n"] += 1
        raw_in, raw_out = m.group(1), m.group(2)
        compact = re.sub(r"\s+", " ", raw_in).strip()
        args, err = bind_input(raw_in, params)
        if args is None or err:
            return m.group(0)
        pos = format_positional(args)
        kind = None
        if "=" in compact and compact != pos:
            kind = "kv_to_positional"
        elif compact != pos:
            kind = "normalize"
        if kind:
            edits.append({"i": idx["n"], "field": "input", "kind": kind})
            return f"输入：{pos}\n输出：{raw_out.strip()}"
        return m.group(0)

    return _INPUT_RE.sub(repl, text), edits


def load_params_for(root: Path, slug: str) -> list[tuple[str, str]]:
    from constraints import load_params

    return load_params(root, slug)
