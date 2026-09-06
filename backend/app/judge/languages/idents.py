from __future__ import annotations


def inner_list(type_name: str) -> str | None:
    t = type_name.strip()
    if t.startswith("List[") and t.endswith("]"):
        return t[5:-1].strip()
    return None


def pascal(name: str) -> str:
    if "_" in name:
        return "".join(p[:1].upper() + p[1:] for p in name.split("_") if p)
    return name[:1].upper() + name[1:]


def snake(name: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i and name[i - 1] != "_":
            out.append("_")
        out.append(ch.lower())
    return "".join(out).replace("__", "_")
