"""Fuellt `pdf_url` in wiki/publikationen/*.md fuer Stubs, die noch keinen haben.

Matched per Fuzzy-Slug-Vergleich gegen PDFs in publikationen/.

Aufruf:
    python scripts/fill_pdf_urls.py              # Dry-run mit Vorschlaegen
    python scripts/fill_pdf_urls.py --apply      # Schreibt pdf_url in Frontmatter
    python scripts/fill_pdf_urls.py --threshold 0.5   # Match-Schwelle anpassen (Default 0.55)
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from slugify import slugify  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "publikationen"
WIKI_DIR = ROOT / "wiki" / "publikationen"

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


def best_match(slug: str, pdf_slugs: dict[str, Path]) -> tuple[Path | None, float]:
    target = content_tokens(slug)
    if not target:
        return None, 0.0
    best, score_best = None, 0.0
    for pdf_slug, pdf in pdf_slugs.items():
        s = jaccard(target, content_tokens(pdf_slug))
        if s > score_best:
            best, score_best = pdf, s
    return best, score_best


def parse_frontmatter(text: str) -> tuple[dict | None, int, int]:
    """Returns (frontmatter_dict, start, end) where start/end bracket the body."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None, 0, 0
    try:
        return yaml.safe_load(m.group(1)), m.start(1), m.end(1)
    except yaml.YAMLError:
        return None, 0, 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Frontmatter beschreiben")
    ap.add_argument("--threshold", type=float, default=0.55, help="Match-Schwelle (Default 0.55)")
    args = ap.parse_args()

    pdf_slugs = {slugify(p.stem): p for p in PDF_DIR.glob("*.pdf")}
    print(f"PDF-Pool: {len(pdf_slugs)} PDFs in publikationen/")

    proposals: list[tuple[Path, str, float]] = []
    skipped_low_score: list[tuple[Path, str | None, float]] = []
    already_has: int = 0
    ignored: int = 0
    no_match: int = 0

    for md in sorted(WIKI_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        fm, _, _ = parse_frontmatter(text)
        if not fm:
            continue
        iv = fm.get("ignore")
        if iv is True or str(iv).strip().lower() == "yes":
            ignored += 1
            continue
        if fm.get("pdf_url"):
            already_has += 1
            continue
        pdf, score = best_match(md.stem, pdf_slugs)
        if pdf is None:
            no_match += 1
            continue
        if score < args.threshold:
            skipped_low_score.append((md, pdf.name if pdf else None, score))
            continue
        proposals.append((md, pdf.name, score))

    print(f"  schon mit pdf_url: {already_has}")
    print(f"  ignored:           {ignored}")
    print(f"  no match:          {no_match}")
    print(f"  unter Schwelle:    {len(skipped_low_score)}")
    print(f"  Vorschlaege:       {len(proposals)}")
    print()

    print(f"=== {len(proposals)} Matches (Schwelle {args.threshold}) ===\n")
    for md, pdf_name, score in proposals:
        print(f"  [{score:.2f}] {md.stem}")
        print(f"         -> {pdf_name}")

    if skipped_low_score:
        print(f"\n=== {len(skipped_low_score)} unter Schwelle (zur Kontrolle) ===\n")
        for md, pdf_name, score in skipped_low_score:
            print(f"  [{score:.2f}] {md.stem}  -> {pdf_name}")

    if not args.apply:
        print("\nDry-run. --apply schreibt die pdf_url in die Frontmatter.")
        return 0

    # Schreibe pdf_url ans Ende des Frontmatters
    written = 0
    for md, pdf_name, score in proposals:
        text = md.read_text(encoding="utf-8")
        m = re.match(r"^(---\s*\n)(.*?)(\n---)", text, re.DOTALL)
        if not m:
            continue
        fm_text = m.group(2)
        if "pdf_url:" in fm_text:
            continue
        new_fm = fm_text + f'\npdf_url: "/publikationen/{pdf_name}"'
        new_text = m.group(1) + new_fm + m.group(3) + text[m.end():]
        md.write_text(new_text, encoding="utf-8")
        written += 1
    print(f"\nGeschrieben: {written} pdf_url-Eintraege")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
