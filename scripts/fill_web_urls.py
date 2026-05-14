"""Fuellt `web_url` in wiki/publikationen/*.md aus dem WordPress REST-API von
dezernatzukunft.org.

Aufruf:
    python scripts/fill_web_urls.py              # Dry-run mit Vorschlaegen
    python scripts/fill_web_urls.py --apply      # Schreibt web_url in Frontmatter
    python scripts/fill_web_urls.py --threshold 0.5   # Match-Schwelle (Default 0.55)
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import time
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from slugify import slugify  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = ROOT / "wiki" / "publikationen"
API = "https://dezernatzukunft.org/wp-json/wp/v2/posts"

STOPWORDS = {
    "der", "die", "das", "und", "in", "zu", "fuer", "von", "den", "ein",
    "eine", "auf", "mit", "im", "an", "the", "of", "to", "and", "a", "for",
    "is", "are", "wie", "was", "warum", "ueber", "unter", "des", "dem", "bei",
    "dezernat", "zukunft",
}


def content_tokens(slug: str) -> set[str]:
    return {t for t in slug.split("-") if t and t not in STOPWORDS and len(t) > 1}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def fetch_all_posts() -> dict[str, str]:
    """Slug -> URL fuer alle DZ-Posts."""
    posts: dict[str, str] = {}
    page = 1
    while True:
        r = requests.get(API, params={"per_page": 100, "page": page}, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        for p in data:
            slug = p.get("slug")
            url = p.get("link")
            if slug and url:
                posts[slug] = url
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        print(f"  Seite {page}/{total_pages}: +{len(data)} (gesamt {len(posts)})")
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)  # nicht hammern
    return posts


def best_match(slug: str, candidates: dict[str, str]) -> tuple[str | None, str | None, float]:
    target = content_tokens(slug)
    if not target:
        return None, None, 0.0
    best_slug, best_url, best_score = None, None, 0.0
    for cand_slug, cand_url in candidates.items():
        s = jaccard(target, content_tokens(cand_slug))
        if s > best_score:
            best_slug, best_url, best_score = cand_slug, cand_url, s
    return best_slug, best_url, best_score


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.55)
    args = ap.parse_args()

    print("Lade DZ-Posts via WordPress API...")
    posts = fetch_all_posts()
    print(f"\nDZ-Pool: {len(posts)} Posts")

    proposals = []
    skipped_low = []
    already, ignored = 0, 0

    for md in sorted(WIKI_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError:
            continue
        if not fm:
            continue
        iv = fm.get("ignore")
        if iv is True or str(iv).strip().lower() == "yes":
            ignored += 1
            continue
        if fm.get("web_url"):
            already += 1
            continue
        cand_slug, cand_url, score = best_match(md.stem, posts)
        if cand_url is None:
            continue
        rec = (md, cand_slug, cand_url, score)
        if score >= args.threshold:
            proposals.append(rec)
        else:
            skipped_low.append(rec)

    print(f"\n  schon mit web_url: {already}")
    print(f"  ignored:           {ignored}")
    print(f"  unter Schwelle:    {len(skipped_low)}")
    print(f"  Vorschlaege:       {len(proposals)}")
    print()

    print(f"=== Vorschlaege (Schwelle {args.threshold}) ===\n")
    for md, cand_slug, cand_url, score in proposals:
        print(f"  [{score:.2f}] {md.stem}")
        print(f"         -> {cand_url}")

    if skipped_low:
        print(f"\n=== Unter Schwelle (zur Kontrolle) ===\n")
        for md, cand_slug, cand_url, score in skipped_low:
            print(f"  [{score:.2f}] {md.stem}")
            print(f"         -> {cand_url}")

    if not args.apply:
        print("\nDry-run. --apply schreibt die web_url in die Frontmatter.")
        return 0

    written = 0
    for md, _, cand_url, _ in proposals:
        text = md.read_text(encoding="utf-8")
        m = re.match(r"^(---\s*\n)(.*?)(\n---)", text, re.DOTALL)
        if not m:
            continue
        fm_text = m.group(2)
        if "web_url:" in fm_text:
            continue
        new_fm = fm_text + f'\nweb_url: "{cand_url}"'
        new_text = m.group(1) + new_fm + m.group(3) + text[m.end():]
        md.write_text(new_text, encoding="utf-8")
        written += 1
    print(f"\nGeschrieben: {written} web_url-Eintraege")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
