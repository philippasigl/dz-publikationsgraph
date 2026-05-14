#!/usr/bin/env python3
"""
Listet PDFs, die noch keine Stub-konforme .md in wiki/publikationen/ haben.

Verwendung:
    python scripts/needs_reprocessing.py
    python scripts/needs_reprocessing.py --all    # auch Stub-konforme zeigen
    python scripts/needs_reprocessing.py --pdfs   # nur PDF-Dateinamen, eine pro Zeile

Schreibt eine sortierte Liste zur stdout. Pipeable in /pdf-ingestion.

Kriterien fuer "needs reprocessing":
  1. PDF hat keine zugehoerige .md (orphan)
  2. .md existiert, aber Body >= 500 Wörter (Rohkonvertierung, nicht strukturiert)
  3. .md existiert, aber fehlt eine der Pflicht-Sections (## Kernthesen, ## Schlussfolgerungen)
  4. .md existiert, aber kein gueltiges Frontmatter

PDFs in IGNORED_PDFS (aus check_pdf_coverage.py) werden uebersprungen.
"""

import argparse
import io
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from slugify import slugify  # noqa: E402

# UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).parent.parent
PDF_DIR = ROOT / "publikationen"
WIKI_DIR = ROOT / "wiki" / "publikationen"

STUB_MAX_BODY_WORDS = 500
REQUIRED_SECTIONS = ("## Kernthesen", "## Schlussfolgerungen")

# Mirror of check_pdf_coverage.IGNORED_PDFS (PDFs that intentionally have no .md)
IGNORED_PDFS = {
    "A controversial investment.pdf",
    "A new fiscal policy for Germany.pdf",
    "Bang for the buck – Wie effizient sind die Subventionen im Bundeshaushalt.pdf",
    "Beyond Maastricht.pdf",
    "Europes Trump Cards.pdf",
    "How to finance Germany’s modernisation.pdf",
    "Jahresabschlussbericht unseres Fiskalprojekts.pdf",
    "Konjunkturkomponente und Staatsorganisation – warum die Auslastung der Wirtschaft nicht von Minister.pdf",
    "Schuster-Johnson-2026-Bang-for-the-buck.pdf",
    "Steigern Unternehmenssteuersenkungen das Wachstum.pdf",
    "Understanding Italy’s Stagnation.pdf",
    "Wir stellen ein – komm an Bord des Dezernats!.pdf",
}

STOPWORDS = {"der", "die", "das", "und", "in", "zu", "fuer", "von", "den", "ein",
             "eine", "auf", "mit", "im", "an", "the", "of", "to", "and", "a",
             "for", "is", "wie", "warum", "was", "des", "dem", "bei",
             "ueber", "unter"}


_STEMMER_SUFFIXES = ("ungen", "lichen", "ische", "isches", "ischen", "lich",
                     "ung", "heit", "keit", "en", "er", "es", "em", "e", "n", "s")


def light_stem(t: str) -> str:
    """Strip common German inflection suffixes. Conservative: only if remaining stem >=4 chars."""
    for suf in _STEMMER_SUFFIXES:
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[:-len(suf)]
    return t


def tokens(slug: str) -> set[str]:
    return {light_stem(t) for t in slug.split("-")
            if t and t not in STOPWORDS and len(t) > 1}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / max(len(a | b), 1) if (a or b) else 0.0


def overlap(a: set[str], b: set[str]) -> float:
    """One-way: how much of the smaller set is covered by the larger."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def find_md_for_pdf(pdf: Path, md_index: dict[str, Path],
                    pdf_url_index: dict[str, Path]) -> tuple[Path | None, str]:
    """Multi-strategy match. Returns (md_path, how-matched-or-'')."""
    pdf_slug = slugify(pdf.stem)
    # 1. exact stem
    if pdf_slug in md_index:
        return md_index[pdf_slug], "exact"
    # 2. .md whose pdf_url points to this PDF
    if pdf.name in pdf_url_index:
        return pdf_url_index[pdf.name], "pdf_url"
    # 3. Token-based: prefer high overlap (one-way), fallback to Jaccard
    pdf_tok = tokens(pdf_slug)
    best, best_overlap, best_jaccard = None, 0.0, 0.0
    for slug, p in md_index.items():
        md_tok = tokens(slug)
        ov = overlap(pdf_tok, md_tok)
        ja = jaccard(pdf_tok, md_tok)
        # Prefer files where overlap is high (one side is a near-subset of the other)
        if ov > best_overlap or (ov == best_overlap and ja > best_jaccard):
            best, best_overlap, best_jaccard = p, ov, ja
    if best_overlap >= 0.75:
        return best, f"overlap({best_overlap:.2f})"
    if best_jaccard >= 0.55:
        return best, f"jaccard({best_jaccard:.2f})"
    return None, ""


def classify_md(md: Path) -> tuple[str, str]:
    """Returns (status, reason). status in {'STUB','LONG','MISSING_SECTIONS','BAD_FRONTMATTER','IGNORED'}."""
    text = md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---(.*)", text, re.S)
    if not m:
        return "BAD_FRONTMATTER", "no frontmatter block"
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return "BAD_FRONTMATTER", f"YAML parse error: {e}"
    if str(fm.get("ignore", "")).lower() in ("yes", "true"):
        return "IGNORED", "ignore: yes"
    body = m.group(2).strip()
    body_words = len(body.split())
    if body_words > STUB_MAX_BODY_WORDS:
        return "LONG", f"body has {body_words} words (>{STUB_MAX_BODY_WORDS})"
    missing = [s for s in REQUIRED_SECTIONS if s not in body]
    if missing:
        return "MISSING_SECTIONS", f"fehlt: {', '.join(missing)}"
    return "STUB", f"{body_words} words"


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--all", action="store_true",
                   help="auch Stub-konforme PDFs anzeigen")
    p.add_argument("--pdfs", action="store_true",
                   help="nur PDF-Dateinamen ausgeben (pipeable)")
    args = p.parse_args()

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    md_files = list(WIKI_DIR.glob("*.md"))
    md_index = {md.stem: md for md in md_files}
    # Build pdf_url -> Path index from each .md's frontmatter
    pdf_url_index: dict[str, Path] = {}
    for md in md_files:
        text = md.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        url = fm.get("pdf_url", "")
        if url:
            pdf_name = url.rsplit("/", 1)[-1]
            pdf_url_index[pdf_name] = md

    rows = []  # (status, pdf, md_or_None, reason, match_how)
    for pdf in pdfs:
        if pdf.name in IGNORED_PDFS:
            rows.append(("IGNORED_PDF", pdf, None, "in IGNORED_PDFS", ""))
            continue
        md, how = find_md_for_pdf(pdf, md_index, pdf_url_index)
        if md is None:
            rows.append(("NO_MD", pdf, None, "kein .md gefunden", ""))
            continue
        status, reason = classify_md(md)
        rows.append((status, pdf, md, reason, how))

    needs = [r for r in rows if r[0] in ("NO_MD", "LONG", "MISSING_SECTIONS", "BAD_FRONTMATTER")]

    if args.pdfs:
        for status, pdf, md, reason, how in needs:
            print(pdf.name)
        return 0

    # Human-readable report
    print(f"# PDFs gesamt: {len(pdfs)}")
    print(f"# IGNORED_PDFS:           {sum(1 for r in rows if r[0] == 'IGNORED_PDF')}")
    print(f"# Stub-konform:           {sum(1 for r in rows if r[0] == 'STUB')}")
    print(f"# Ignored .md:            {sum(1 for r in rows if r[0] == 'IGNORED')}")
    print(f"# Brauchen Re-Processing: {len(needs)}")
    print()

    for category in ("NO_MD", "LONG", "MISSING_SECTIONS", "BAD_FRONTMATTER"):
        block = [r for r in needs if r[0] == category]
        if not block:
            continue
        print(f"## {category} ({len(block)})")
        for status, pdf, md, reason, how in block:
            md_name = md.name if md else "—"
            print(f"  - {pdf.name}")
            print(f"      .md: {md_name}  [{reason}]")
        print()

    if args.all:
        print(f"## STUB ({sum(1 for r in rows if r[0] == 'STUB')})")
        for status, pdf, md, reason, how in rows:
            if status == "STUB":
                print(f"  - {pdf.name} -> {md.name}  [{reason}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
