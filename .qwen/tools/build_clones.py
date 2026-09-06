"""Build index/clones.jsonl from local doocs README tables. Output is self-contained; sources are not needed at runtime."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*(.*?)\s*\|",
    flags=re.M,
)


def slugify_folder(path: str) -> tuple[str, str]:
    path = unquote(path).replace("\\", "/")
    name = path.rstrip("/").split("/")[-2] if "/README" in path else path.split("/")[-1]
    if name.lower().startswith("readme"):
        parts = path.rstrip("/").split("/")
        name = parts[-2] if len(parts) >= 2 else name
    title_en = name.split(".", 1)[-1].strip() if "." in name else name
    slug = re.sub(r"[^a-z0-9]+", "-", title_en.lower()).strip("-")
    return title_en, slug


def tags_from(cell: str) -> list[str]:
    return [t.strip() for t in re.findall(r"`([^`]+)`", cell) if t.strip()]


def parse_table(text: str, title_key: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for m in ROW.finditer(text):
        pid = m.group(1).zfill(4)
        title = m.group(2).strip()
        folder_en, slug = slugify_folder(m.group(3))
        rec = out.setdefault(
            pid,
            {"src": "lc", "id": pid, "title_cn": "", "title_en": "", "slug": slug, "tags": []},
        )
        rec[title_key] = title
        if folder_en and not rec["title_en"]:
            rec["title_en"] = folder_en
        if slug:
            rec["slug"] = slug
        tags = tags_from(m.group(4))
        if tags:
            rec["tags"] = tags
    return out


def load_extra(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cn", required=True, help="doocs solution/README.md (local)")
    parser.add_argument("--en", required=True, help="doocs solution/README_EN.md (local)")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    cn_path = Path(args.cn)
    en_path = Path(args.en)
    if not cn_path.is_file() or not en_path.is_file():
        json.dump({"ok": False, "error": "missing README"}, sys.stdout, ensure_ascii=False)
        print()
        return 1
    by_id = parse_table(cn_path.read_text(encoding="utf-8"), "title_cn")
    for pid, rec in parse_table(en_path.read_text(encoding="utf-8"), "title_en").items():
        cur = by_id.setdefault(pid, rec)
        if rec.get("title_en"):
            cur["title_en"] = rec["title_en"]
        if rec.get("slug"):
            cur["slug"] = rec["slug"]
        if rec.get("tags") and not cur.get("tags"):
            cur["tags"] = rec["tags"]
    extra = load_extra(root / "index" / "clones-extra.jsonl")
    out_path = root / "index" / "clones.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [by_id[k] for k in sorted(by_id, key=lambda x: int(x))]
    seen = {(r.get("src"), r.get("id"), r.get("slug")) for r in rows}
    for rec in extra:
        key = (rec.get("src"), rec.get("id"), rec.get("slug"))
        if key in seen:
            continue
        rows.append(rec)
        seen.add(key)
    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        for rec in rows:
            fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
    json.dump(
        {"ok": True, "n": len(rows), "lc": len(by_id), "extra": len(extra), "path": str(out_path).replace("\\", "/")},
        sys.stdout,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
