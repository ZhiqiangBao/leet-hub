"""Score a problem statement against index/clones.jsonl. One JSON line. No statements printed."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

TOKEN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    raw = TOKEN.findall(text.lower())
    cjk = [t for t in raw if "\u4e00" <= t <= "\u9fff"]
    words = [t for t in raw if t.isascii() and len(t) > 1]
    bigrams = [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
    camel = []
    for w in words:
        camel.extend(p for p in re.findall(r"[a-z]+|\d+", w) if len(p) > 1)
    return words + camel + bigrams


def query_from(root: Path, slug: str) -> str:
    stmt = root / "problems" / slug / "statement.md"
    sig = root / "problems" / slug / "signature.yaml"
    meta = root / "problems" / slug / "meta.yaml"
    parts: list[str] = []
    if meta.is_file():
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.startswith("title:"):
                parts.append(line.split(":", 1)[1].strip().strip("\"'"))
                break
    if stmt.is_file():
        body = stmt.read_text(encoding="utf-8")
        first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
        if first.startswith("# "):
            parts.append(first[2:].strip())
        cut = re.split(r"\n##\s*示例", body, maxsplit=1)[0]
        desc = re.sub(r"^#.*", "", cut, count=1, flags=re.M).strip()
        parts.append(desc[:160])
    if sig.is_file():
        for line in sig.read_text(encoding="utf-8").splitlines():
            if line.startswith("method:"):
                parts.append(line.split(":", 1)[1].strip())
    return "\n".join(parts)


def load_index(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def doc_text(rec: dict) -> str:
    tags = rec.get("tags") or []
    tag_s = " ".join(tags) if isinstance(tags, list) else str(tags)
    return " ".join(
        [
            str(rec.get("id") or ""),
            rec.get("title_cn") or "",
            rec.get("title_en") or "",
            rec.get("slug") or "",
            tag_s,
        ]
    )


def bm25(query: list[str], docs: list[list[str]], k1: float = 1.2, b: float = 0.75) -> list[float]:
    n = len(docs)
    df: Counter[str] = Counter()
    for toks in docs:
        df.update(set(toks))
    avgdl = sum(len(t) for t in docs) / max(n, 1)
    qset = set(query)
    scores = []
    for toks in docs:
        tf = Counter(toks)
        dl = len(toks) or 1
        s = 0.0
        for term in qset:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            freq = tf[term]
            s += idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)
    return scores


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    index_path = root / "index" / "clones.jsonl"
    out: dict = {"ok": True, "slug": args.slug, "n": 0, "hits": [], "issues": []}
    if not index_path.is_file():
        out["ok"] = False
        out["issues"].append("[原创] 未核 missing index/clones.jsonl")
        json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))
        print()
        return 1
    rows = load_index(index_path)
    q = tokenize(query_from(root, args.slug))
    docs = [tokenize(doc_text(r)) for r in rows]
    scores = bm25(q, docs)
    titles_q = tokenize(" ".join(query_from(root, args.slug).split("\n")[:2]))
    tset = set(titles_q)
    for i, rec in enumerate(rows):
        title_toks = set(tokenize((rec.get("title_cn") or "") + " " + (rec.get("title_en") or "") + " " + (rec.get("slug") or "")))
        overlap = len(tset & title_toks)
        if overlap:
            scores[i] += 8.0 * overlap
    ranked = sorted(range(len(rows)), key=lambda i: scores[i], reverse=True)[: max(args.k, 1)]
    hits = []
    for i in ranked:
        if scores[i] <= 0:
            continue
        rec = rows[i]
        hits.append(
            {
                "src": rec.get("src"),
                "id": rec.get("id"),
                "title_cn": rec.get("title_cn") or "",
                "title_en": rec.get("title_en") or "",
                "slug": rec.get("slug") or "",
                "score": round(scores[i], 3),
            }
        )
    out["n"] = len(hits)
    out["hits"] = hits
    json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
