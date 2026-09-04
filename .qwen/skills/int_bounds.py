"""Integer range checks keyed to signature.yaml types (int vs long)."""
from __future__ import annotations

from pathlib import Path

INT32_MIN = -2_147_483_648
INT32_MAX = 2_147_483_647
INT64_MIN = -9_223_372_036_854_775_808
INT64_MAX = 9_223_372_036_854_775_807


def load_sig_types(root: Path, slug: str) -> tuple[list[str], str]:
    path = root / "problems" / slug / "signature.yaml"
    types: list[str] = []
    ret = "int"
    if not path.is_file():
        return types, ret
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("type:"):
            types.append(s.split(":", 1)[1].strip().split("#", 1)[0].strip())
        elif s.startswith("return_type:"):
            ret = s.split(":", 1)[1].strip().split("#", 1)[0].strip() or "int"
    return types, ret


def _collect(value, type_name: str, acc: list[tuple[int, str]]) -> None:
    t = (type_name or "").strip()
    if t.startswith("List[") and t.endswith("]"):
        if isinstance(value, list):
            inner = t[5:-1]
            for x in value:
                _collect(x, inner, acc)
        return
    if t in ("int", "long") and isinstance(value, int) and not isinstance(value, bool):
        acc.append((value, t))


def range_flags(
    args,
    expected,
    param_types: list[str],
    return_type: str,
) -> tuple[bool, bool]:
    """Return (int32_out_of_range, int64_out_of_range) for typed fields.

    Untyped walk (no signature types) treats every integer as `int`.
    """
    acc: list[tuple[int, str]] = []
    if param_types:
        if isinstance(args, list):
            for val, t in zip(args, param_types):
                _collect(val, t, acc)
        _collect(expected, return_type, acc)
    else:

        def walk(v) -> None:
            if isinstance(v, bool) or v is None:
                return
            if isinstance(v, int):
                acc.append((v, "int"))
                return
            if isinstance(v, list):
                for x in v:
                    walk(x)

        walk(args)
        walk(expected)
    bad32 = bad64 = False
    for n, leaf in acc:
        if leaf == "long":
            if n < INT64_MIN or n > INT64_MAX:
                bad64 = True
        elif n < INT32_MIN or n > INT32_MAX:
            bad32 = True
    return bad32, bad64
