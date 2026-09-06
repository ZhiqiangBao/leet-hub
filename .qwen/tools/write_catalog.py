"""Generate problems/catalog.md from git-tracked (plus optional --slug) meta+signature."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def load_meta(path: Path) -> tuple[str, list[str]]:
    title = path.parent.name
    tags: list[str] = []
    in_tags = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("title:"):
            title = stripped.split(":", 1)[1].strip().strip("\"'")
            in_tags = False
            continue
        if stripped.startswith("tags:"):
            rest = stripped.split(":", 1)[1].strip()
            in_tags = True
            if rest.startswith("["):
                inner = rest.strip("[]")
                tags = [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]
                in_tags = False
            continue
        if in_tags and stripped.startswith("- "):
            tags.append(stripped[2:].strip().strip("\"'"))
            continue
        if ":" in stripped:
            in_tags = False
    return title, tags


def load_signature(path: Path) -> str:
    method = ""
    return_type = "int"
    params: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("method:"):
            method = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("return_type:"):
            return_type = stripped.split(":", 1)[1].strip().split("#", 1)[0].strip()
        elif stripped.startswith("- name:"):
            current = {"name": stripped.split(":", 1)[1].strip(), "type": "int"}
            params.append(current)
        elif stripped.startswith("type:") and current is not None and raw[:1] in " \t":
            current["type"] = stripped.split(":", 1)[1].strip().split("#", 1)[0].strip()
    if not method:
        raise ValueError(f"missing method in {path}")
    args = ", ".join(f"{p['name']}: {p['type']}" for p in params)
    return f"{method}({args}) -> {return_type}"


def git_tracked_slugs(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", "problems/*/meta.yaml"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    slugs: list[str] = []
    for line in proc.stdout.splitlines():
        parts = Path(line.strip().replace("\\", "/")).parts
        if len(parts) >= 3 and parts[0] == "problems" and parts[-1] == "meta.yaml":
            slugs.append(parts[1])
    return slugs


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_catalog(root: Path, extra_slugs: list[str]) -> dict:
    slugs = sorted(set(git_tracked_slugs(root)) | {s for s in extra_slugs if s})
    rows: list[tuple[str, str, str, str]] = []
    skipped: list[str] = []
    for slug in slugs:
        meta_path = root / "problems" / slug / "meta.yaml"
        sig_path = root / "problems" / slug / "signature.yaml"
        if not meta_path.is_file() or not sig_path.is_file():
            skipped.append(slug)
            continue
        title, tags = load_meta(meta_path)
        try:
            signature = load_signature(sig_path)
        except ValueError:
            skipped.append(slug)
            continue
        rows.append((slug, title, ", ".join(tags), signature))
    lines = [
        "# 已出题表",
        "",
        "| slug | title | tags | signature |",
        "| --- | --- | --- | --- |",
    ]
    for slug, title, tags, signature in rows:
        lines.append(
            f"| {cell(slug)} | {cell(title)} | {cell(tags)} | `{cell(signature)}` |"
        )
    lines.append("")
    dest = root / "problems" / "catalog.md"
    dest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return {"ok": True, "n": len(rows), "path": "problems/catalog.md", "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="")
    parser.add_argument(
        "--slug",
        action="append",
        default=[],
        help="also include this on-disk slug (the problem being committed)",
    )
    args = parser.parse_args()
    root = Path(args.root) if args.root else Path(__file__).resolve().parents[2]
    extra = [s.strip() for s in args.slug if s.strip()]
    if not git_tracked_slugs(root) and not extra:
        print(json.dumps({"ok": False, "error": "no git-tracked problems and no --slug"}, ensure_ascii=False))
        return 1
    summary = write_catalog(root, extra)
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
