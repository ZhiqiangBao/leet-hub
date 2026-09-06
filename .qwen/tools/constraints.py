"""Bounds and hidden-n scale checks. Defaults apply when meta omits a field."""
from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULTS = {
    "n_min": 1,
    "n_max": 100_000,
    "elem_min": -1_000_000_000,
    "elem_max": 1_000_000_000,
}

ISSUE_TAGS = {
    "lt100": "[规模]",
    "missing_at_max": "[规模]",
    "n_max_ne_U": "[规模]",
    "out_of_bounds": "[约束]",
    "n_below_min": "[约束]",
    "n_above_max": "[约束]",
}

_INT = re.compile(
    r"^(?P<sign>-)?(?:10\^(?P<p>\d+)|(?P<e>-?\d+(?:\.\d+)?[eE][+\-]?\d+)|(?P<n>-?\d+))$"
)


def parse_int(raw: str) -> int | None:
    s = raw.strip().strip("\"'")
    if not s:
        return None
    m = _INT.fullmatch(s)
    if not m:
        try:
            return int(s, 10)
        except ValueError:
            return None
    sign = -1 if m.group("sign") else 1
    if m.group("p") is not None:
        return sign * 10 ** int(m.group("p"))
    if m.group("e") is not None:
        return int(float(m.group("e")))
    n = m.group("n")
    if n is None:
        return None
    v = int(n, 10)
    return -abs(v) if sign < 0 and v >= 0 else v


def load_params(root: Path, slug: str) -> list[tuple[str, str]]:
    path = root / "problems" / slug / "signature.yaml"
    params: list[tuple[str, str]] = []
    name = ""
    if not path.is_file():
        return params
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s.startswith("- name:"):
            name = s.split(":", 1)[1].strip()
            params.append((name, "int"))
        elif s.startswith("type:") and name and (raw[:1] in " \t"):
            params[-1] = (name, s.split(":", 1)[1].strip().split("#", 1)[0].strip())
    return params


def _parse_param_bounds_block(lines: list[str], i: int) -> tuple[dict[str, dict[str, int]], int]:
    """Parse nested param_bounds from line i (the `param_bounds:` line). Return map, next index."""
    out: dict[str, dict[str, int]] = {}
    first = lines[i].strip()
    rest = first.split(":", 1)[1].strip()
    if rest.startswith("{"):
        try:
            raw = json.loads(rest.replace("'", '"'))
        except json.JSONDecodeError:
            return out, i + 1
        if isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(v, dict):
                    slot: dict[str, int] = {}
                    if "min" in v:
                        slot["min"] = int(v["min"])
                    if "max" in v:
                        slot["max"] = int(v["max"])
                    if slot:
                        out[str(k)] = slot
        return out, i + 1
    i += 1
    cur = ""
    while i < len(lines):
        raw = lines[i]
        if raw.strip() and not raw.startswith((" ", "\t")):
            break
        s = raw.strip()
        if not s or s.startswith("#"):
            i += 1
            continue
        if s.endswith(":") and not s.startswith(("min:", "max:")):
            cur = s[:-1].strip()
            out.setdefault(cur, {})
            i += 1
            continue
        if cur and s.startswith("min:"):
            v = parse_int(s.split(":", 1)[1])
            if v is not None:
                out[cur]["min"] = v
        elif cur and s.startswith("max:"):
            v = parse_int(s.split(":", 1)[1])
            if v is not None:
                out[cur]["max"] = v
        i += 1
    return out, i


def load_bounds(root: Path, slug: str) -> dict:
    bounds = dict(DEFAULTS)
    bounds["param_bounds"] = {}
    path = root / "problems" / slug / "meta.yaml"
    if not path.is_file():
        return bounds
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("n_min:"):
            v = parse_int(s.split(":", 1)[1])
            if v is not None:
                bounds["n_min"] = v
        elif s.startswith("n_max:"):
            v = parse_int(s.split(":", 1)[1])
            if v is not None:
                bounds["n_max"] = v
        elif s.startswith("elem_min:"):
            v = parse_int(s.split(":", 1)[1])
            if v is not None:
                bounds["elem_min"] = v
        elif s.startswith("elem_max:"):
            v = parse_int(s.split(":", 1)[1])
            if v is not None:
                bounds["elem_max"] = v
        elif s.startswith("param_bounds:"):
            pb, i = _parse_param_bounds_block(lines, i)
            bounds["param_bounds"] = pb
            continue
        i += 1
    return bounds


def overlay_bounds(
    bounds: dict,
    *,
    n_min=None,
    n_max=None,
    elem_min=None,
    elem_max=None,
    param_bounds=None,
) -> dict:
    out = dict(bounds)
    out["param_bounds"] = dict(bounds.get("param_bounds") or {})
    if n_min is not None:
        out["n_min"] = int(n_min)
    if n_max is not None:
        out["n_max"] = int(n_max)
    if elem_min is not None:
        out["elem_min"] = int(elem_min)
    if elem_max is not None:
        out["elem_max"] = int(elem_max)
    if param_bounds:
        for k, v in param_bounds.items():
            slot = dict(out["param_bounds"].get(k) or {})
            if isinstance(v, dict):
                if "min" in v:
                    slot["min"] = int(v["min"])
                if "max" in v:
                    slot["max"] = int(v["max"])
            out["param_bounds"][k] = slot
    return out


def _leaf_range(bounds: dict, name: str) -> tuple[int, int]:
    pb = (bounds.get("param_bounds") or {}).get(name) or {}
    lo = pb["min"] if "min" in pb else bounds["elem_min"]
    hi = pb["max"] if "max" in pb else bounds["elem_max"]
    return int(lo), int(hi)


def _inner(type_name: str) -> str | None:
    t = (type_name or "").strip()
    if t.startswith("List[") and t.endswith("]"):
        return t[5:-1].strip()
    return None


def case_n(args) -> int:
    if not isinstance(args, (list, tuple)) or not args:
        return 0
    for x in args:
        if isinstance(x, (list, str)):
            return len(x)
    if isinstance(args[0], int) and not isinstance(args[0], bool):
        return int(args[0])
    return 0


def args_n_kind(args) -> str:
    if not isinstance(args, (list, tuple)):
        return "scalar"
    for x in args:
        if isinstance(x, (list, str)):
            return "length"
    return "scalar"


def check_case(args, params: list[tuple[str, str]], bounds: dict) -> list[str]:
    """Return issue codes for one args list. Does not inspect expected."""
    found: list[str] = []
    n = case_n(args)
    n_min, n_max = int(bounds["n_min"]), int(bounds["n_max"])
    if n < n_min:
        found.append("n_below_min")
    if n > n_max:
        found.append("n_above_max")
    if not isinstance(args, (list, tuple)):
        return found
    for i, (name, typ) in enumerate(params):
        if i >= len(args):
            break
        val = args[i]
        inner = _inner(typ)
        if inner in ("int", "long") and isinstance(val, list):
            lo, hi = _leaf_range(bounds, name)
            for x in val:
                if isinstance(x, int) and not isinstance(x, bool) and (x < lo or x > hi):
                    found.append("out_of_bounds")
                    break
        elif typ in ("int", "long") and isinstance(val, int) and not isinstance(val, bool):
            lo, hi = _leaf_range(bounds, name)
            if val < lo or val > hi:
                found.append("out_of_bounds")
        elif typ == "str" and isinstance(val, str) and "\0" in val:
            found.append("out_of_bounds")
        elif inner == "str" and isinstance(val, list):
            if any(isinstance(x, str) and "\0" in x for x in val):
                found.append("out_of_bounds")
    return list(dict.fromkeys(found))


def hist_hidden(hns: list[int]) -> dict:
    nmax = max(hns) if hns else None
    return {
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


def scale_issues(hns: list[int], n_kind: str, bounds: dict) -> list[str]:
    if not hns:
        return []
    u = int(bounds["n_max"])
    nmax = max(hns)
    hist = hist_hidden(hns)
    found: list[str] = []
    if nmax != u:
        found.append("n_max_ne_U")
    if hist["at_max"] not in (1, 2):
        found.append("missing_at_max")
    if n_kind == "length" and u >= 5000 and hist["lt100"] > 4:
        found.append("lt100")
    return found


def tags_for(issue_codes: list[str]) -> list[str]:
    tags: list[str] = []
    for code in issue_codes:
        tag = ISSUE_TAGS.get(code)
        if tag and tag not in tags:
            tags.append(tag)
    return tags
