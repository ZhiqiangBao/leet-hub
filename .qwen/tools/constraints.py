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
    "lt100": "scale",
    "missing_at_max": "scale",
    "n_max_ne_U": "scale",
    "out_of_bounds": "constraints",
    "n_below_min": "constraints",
    "n_above_max": "constraints",
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


def _put_bound(out: dict[str, dict[str, int]], name: str, side: str, value: int) -> None:
    slot = out.setdefault(name, {})
    slot[side] = value


def _apply_bound_key(out: dict[str, dict[str, int]], key: str, value) -> bool:
    k = str(key).strip()
    if isinstance(value, dict):
        slot: dict[str, int] = dict(out.get(k) or {})
        if "min" in value:
            slot["min"] = int(value["min"])
        if "max" in value:
            slot["max"] = int(value["max"])
        if slot:
            out[k] = slot
            return True
        return False
    n = parse_int(str(value)) if not isinstance(value, int) else int(value)
    if n is None:
        return False
    if k.endswith("_min"):
        _put_bound(out, k[:-4], "min", n)
        return True
    if k.endswith("_max"):
        _put_bound(out, k[:-4], "max", n)
        return True
    return False


def _parse_flow_map(rest: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    try:
        raw = json.loads(rest.replace("'", '"'))
    except json.JSONDecodeError:
        raw = None
    if isinstance(raw, dict):
        for k, v in raw.items():
            _apply_bound_key(out, k, v)
        return out
    for m in re.finditer(r"([A-Za-z_]\w*)\s*:\s*(\{[^}]*\}|-?\d+)", rest):
        key, val = m.group(1), m.group(2)
        if val.startswith("{"):
            inner: dict[str, int] = {}
            for side, num in re.findall(r"(min|max)\s*:\s*(-?\d+)", val):
                inner[side] = int(num)
            _apply_bound_key(out, key, inner)
        else:
            _apply_bound_key(out, key, val)
    return out


def _parse_param_bounds_block(
    lines: list[str], i: int
) -> tuple[dict[str, dict[str, int]], int, list[str]]:
    """Parse param_bounds from line i. Nested, flow, or flat name_min/name_max."""
    out: dict[str, dict[str, int]] = {}
    warnings: list[str] = []
    first = lines[i].strip()
    rest = first.split(":", 1)[1].strip()
    if rest.startswith("{"):
        parsed = _parse_flow_map(rest)
        if not parsed:
            warnings.append("param_bounds flow map not recognized")
        return parsed, i + 1, warnings
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
            if cur.endswith("_min") or cur.endswith("_max"):
                pass
            else:
                out.setdefault(cur, {})
            i += 1
            continue
        if ":" in s:
            key, val = s.split(":", 1)
            key, val = key.strip(), val.strip()
            n = parse_int(val)
            if key in ("min", "max") and cur and n is not None:
                _put_bound(out, cur, key, n)
            elif n is not None and _apply_bound_key(out, key, n):
                cur = ""
            else:
                warnings.append(f"param_bounds key {key} not recognized")
        i += 1
    return out, i, warnings


def load_bounds(root: Path, slug: str) -> dict:
    bounds = dict(DEFAULTS)
    bounds["param_bounds"] = {}
    bounds["warnings"] = []
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
            pb, i, warns = _parse_param_bounds_block(lines, i)
            bounds["param_bounds"] = pb
            bounds["warnings"].extend(warns)
            continue
        i += 1
    params = load_params(root, slug)
    names = {n for n, _ in params}
    notes: list[str] = []
    cleaned: dict[str, dict[str, int]] = {}
    for key, slot in (bounds["param_bounds"] or {}).items():
        if key in names:
            cleaned[key] = slot
        else:
            bounds["warnings"].append(f"param_bounds key {key} not recognized")
    bounds["param_bounds"] = cleaned
    for name, typ in params:
        if typ in ("int", "long") and name not in cleaned:
            notes.append(f"{name} using elem_min/elem_max")
    bounds["notes"] = notes
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
    out["warnings"] = list(bounds.get("warnings") or [])
    out["notes"] = list(bounds.get("notes") or [])
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
            _apply_bound_key(out["param_bounds"], k, v)
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


def check_hits(args, params: list[tuple[str, str]], bounds: dict) -> list[dict]:
    """Per-case bound hits. Scalars only in `got`; never the full args."""
    hits: list[dict] = []
    n = case_n(args)
    n_min, n_max = int(bounds["n_min"]), int(bounds["n_max"])
    if n < n_min:
        hits.append({"code": "n_below_min", "param": "n", "got": n, "min": n_min, "max": n_max})
    if n > n_max:
        hits.append({"code": "n_above_max", "param": "n", "got": n, "min": n_min, "max": n_max})
    if not isinstance(args, (list, tuple)):
        return hits
    for i, (name, typ) in enumerate(params):
        if i >= len(args):
            break
        val = args[i]
        inner = _inner(typ)
        if inner in ("int", "long") and isinstance(val, list):
            lo, hi = _leaf_range(bounds, name)
            for x in val:
                if isinstance(x, int) and not isinstance(x, bool) and (x < lo or x > hi):
                    hits.append(
                        {"code": "out_of_bounds", "param": name, "got": x, "min": lo, "max": hi}
                    )
                    break
        elif typ in ("int", "long") and isinstance(val, int) and not isinstance(val, bool):
            lo, hi = _leaf_range(bounds, name)
            if val < lo or val > hi:
                hits.append(
                    {"code": "out_of_bounds", "param": name, "got": val, "min": lo, "max": hi}
                )
        elif typ == "str" and isinstance(val, str) and "\0" in val:
            hits.append({"code": "out_of_bounds", "param": name, "got": "nul", "min": 0, "max": 0})
        elif inner == "str" and isinstance(val, list):
            if any(isinstance(x, str) and "\0" in x for x in val):
                hits.append(
                    {"code": "out_of_bounds", "param": name, "got": "nul", "min": 0, "max": 0}
                )
    return hits


def check_case(args, params: list[tuple[str, str]], bounds: dict) -> list[str]:
    return list(dict.fromkeys(h["code"] for h in check_hits(args, params, bounds)))


def public_bounds(bounds: dict) -> dict:
    return {
        "n_min": bounds["n_min"],
        "n_max": bounds["n_max"],
        "elem_min": bounds["elem_min"],
        "elem_max": bounds["elem_max"],
        "param_bounds": bounds.get("param_bounds") or {},
        "notes": list(bounds.get("notes") or []),
        "warnings": list(bounds.get("warnings") or []),
    }


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
