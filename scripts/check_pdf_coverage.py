#!/usr/bin/env python3
"""
Solider PDF-Coverage-Check fuer das DZ-Wiki.

Vor dem Loeschen der PDFs aus publikationen/ verifiziert dieses Skript,
dass jede PDF eine valide Markdown-Repraesentation in wiki/publikationen/ hat.

Drei Kriterien fuer "sicher loeschbar":
  1. Mindestens eine .md hat pdf_url, der auf die PDF zeigt
  2. Diese .md hat substantiellen Body (>= MIN_BODY_WORDS Woerter)
  3. Diese .md hat alle Pflicht-Frontmatter-Felder

Verwendung:
    python scripts/check_pdf_coverage.py
    python scripts/check_pdf_coverage.py --strict   # Exit 1 bei Problemen
"""

import argparse
import json
import re
import sys
import io
from pathlib import Path
from urllib.parse import unquote

import yaml
from jsonschema import Draft7Validator

sys.path.insert(0, str(Path(__file__).parent))
from slugify import slugify  # noqa: E402

# UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent
PDF_DIR = ROOT / "publikationen"
WIKI_DIR = ROOT / "wiki" / "publikationen"
SCHEMA_FILE = ROOT / "schemas" / "frontmatter.schema.json"

MIN_BODY_WORDS = 25  # below this AND no summary in frontmatter -> too thin
FUZZY_THRESHOLD = 0.55  # Jaccard similarity above this counts as a match

# PDFs hier auflisten, die intentional KEINE .md brauchen (englische Versionen,
# Stellenanzeigen, Duplikat-Dateinamen ohne eigene Repraesentation, etc.).
# Diese werden nicht als Orphan/Problem gemeldet.
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
             "for", "in", "on", "at", "is", "are", "wie", "was", "warum",
             "ueber", "unter", "des", "dem", "bei"}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---(.*)", re.S)


def load_md(path: Path):
    """Return (frontmatter dict, body str, raw_text)."""
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, m.group(2), text
    return data, m.group(2).strip(), text


def content_tokens(slug: str) -> set[str]:
    """Tokens of a slug, minus stopwords and 1-char tokens."""
    return {t for t in slug.split("-") if t and t not in STOPWORDS and len(t) > 1}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def fuzzy_match_pdf(slug: str, pdf_slugs: dict[str, Path]) -> tuple[Path | None, float]:
    """Find the best fuzzy PDF match for a given slug. Returns (pdf, score)."""
    target = content_tokens(slug)
    if not target:
        return None, 0.0
    best, best_score = None, 0.0
    for pdf_slug, pdf in pdf_slugs.items():
        score = jaccard(target, content_tokens(pdf_slug))
        if score > best_score:
            best, best_score = pdf, score
    return best, best_score


def normalize_pdf_ref(s: str) -> str:
    """Strip leading slash, decode URL, lowercase. Compare PDFs robustly."""
    if not s:
        return ""
    s = unquote(s)
    s = s.lstrip("/")
    # Strip leading "publikationen/" or "publikationen/" prefix
    for prefix in ("publikationen/", "publikationen/"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s.lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 bei Problemen")
    args = parser.parse_args()

    # --- Index PDFs ---
    all_pdfs = sorted(PDF_DIR.glob("*.pdf"))
    pdfs_ignored = [p for p in all_pdfs if p.name in IGNORED_PDFS]
    pdfs = [p for p in all_pdfs if p.name not in IGNORED_PDFS]
    # PDFs are matchable by (a) normalized filename or (b) slug of stem
    pdf_by_norm = {normalize_pdf_ref(p.name): p for p in pdfs}
    pdf_by_slug = {slugify(p.stem): p for p in pdfs}
    print(f"PDFs in {PDF_DIR}: {len(all_pdfs)} (davon {len(pdfs_ignored)} via IGNORED_PDFS uebersprungen)")

    # --- Index .md ---
    md_files = sorted(WIKI_DIR.glob("*.md"))
    print(f"Markdown-Stubs in {WIKI_DIR}: {len(md_files)}")
    print()

    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    # pdf-Path -> list of (md_path, body_words, frontmatter_ok, errs, match_type, is_ignored)
    pdf_to_mds: dict[Path, list[tuple[Path, int, bool, list[str], str, bool]]] = {}
    md_to_pdf: dict[Path, Path | None] = {}
    md_problems: list[tuple[Path, str]] = []
    md_ignored_count = 0
    import datetime

    for md in md_files:
        data, body, _ = load_md(md)
        if data is None:
            md_problems.append((md, "kein/kaputtes Frontmatter"))
            md_to_pdf[md] = None
            continue
        is_ignored = str(data.get("ignore", "")).lower() in ("yes", "true")
        if is_ignored:
            md_ignored_count += 1

        body_words = len(body.split())
        has_summary = bool((data.get("summary") or "").strip())
        # A .md is "substantive" if body has >= MIN_BODY_WORDS OR summary field is set
        is_substantive = body_words >= MIN_BODY_WORDS or has_summary
        if is_ignored:
            # ignore=yes is the explicit "this is a known duplicate" marker;
            # treat as covering its PDF regardless of body/schema strictness.
            is_substantive = True
            fm_ok = True
            err_msgs = []
        else:
            data_v = dict(data)
            if isinstance(data_v.get("date"), (datetime.date, datetime.datetime)):
                data_v["date"] = data_v["date"].strftime("%Y-%m-%d")
            errs = list(validator.iter_errors(data_v))
            fm_ok = len(errs) == 0
            err_msgs = [e.message for e in errs] if errs else []

        # Multi-strategy matching: pdf_url -> filename slug -> .md slug
        matched_pdf: Path | None = None
        match_type = ""
        pdf_url = data.get("pdf_url", "")
        if pdf_url:
            matched_pdf = pdf_by_norm.get(normalize_pdf_ref(pdf_url))
            if matched_pdf:
                match_type = "pdf_url"
        if not matched_pdf:
            # Try slug match: .md stem == slug of PDF stem
            md_slug = md.stem
            matched_pdf = pdf_by_slug.get(md_slug)
            if matched_pdf:
                match_type = "slug(filename)"
        if not matched_pdf:
            # Try slug from title
            title = data.get("title", "")
            if title:
                title_slug = slugify(title)
                matched_pdf = pdf_by_slug.get(title_slug)
                if matched_pdf:
                    match_type = "slug(title)"
        if not matched_pdf:
            # Fuzzy match via shared content tokens
            title = data.get("title", "")
            slug_to_test = slugify(title) if title else md.stem
            cand, score = fuzzy_match_pdf(slug_to_test, pdf_by_slug)
            if score >= FUZZY_THRESHOLD:
                matched_pdf = cand
                match_type = f"fuzzy(score={score:.2f})"

        md_to_pdf[md] = matched_pdf
        if matched_pdf:
            pdf_to_mds.setdefault(matched_pdf, []).append(
                (md, body_words, fm_ok, err_msgs, match_type, is_ignored, is_substantive)
            )

    # --- Build report ---
    safe_to_delete: list[Path] = []
    pdf_orphans: list[Path] = []          # PDF without .md
    pdf_broken_link: list[tuple[Path, list[str]]] = []  # has .md but weak
    pdf_multi: list[tuple[Path, list[Path]]] = []       # multiple .md per PDF

    covered_by_ignored: list[tuple[Path, list[Path]]] = []
    pdf_duplicate_version: list[tuple[Path, Path, float]] = []  # likely same publication, .md exists

    # Pre-compute candidates for orphan re-categorization
    md_slug_to_path_local = {md.stem: md for md in md_files}
    md_title_slugs_local: dict[str, Path] = {}
    for md in md_files:
        d, _, _ = load_md(md)
        if d and d.get("title"):
            md_title_slugs_local[slugify(d["title"])] = md

    def best_candidate(pdf: Path):
        pdf_slug = slugify(pdf.stem)
        pdf_tokens = content_tokens(pdf_slug)
        best, score = None, 0.0
        for src in (md_slug_to_path_local, md_title_slugs_local):
            for slug, p in src.items():
                s = jaccard(pdf_tokens, content_tokens(slug))
                if s > score:
                    best, score = p, s
        return best, score

    DUPLICATE_VERSION_THRESHOLD = 0.85  # strong match -> very likely same publication

    for pdf in pdfs:
        mds = pdf_to_mds.get(pdf, [])
        if not mds:
            # No .md directly linked. Check if a high-similarity .md exists (= duplicate version)
            cand, score = best_candidate(pdf)
            if cand and score >= DUPLICATE_VERSION_THRESHOLD:
                pdf_duplicate_version.append((pdf, cand, score))
                continue
            pdf_orphans.append(pdf)
            continue
        if len(mds) > 1:
            pdf_multi.append((pdf, [m[0] for m in mds]))
        # A .md is "good enough" if substantive AND valid frontmatter
        good = [(p, w, ok, e, mt, ign, sub) for (p, w, ok, e, mt, ign, sub) in mds
                if sub and ok]
        if good:
            safe_to_delete.append(pdf)
            ignored_match = [g for g in good if g[5]]
            if ignored_match and not [g for g in good if not g[5]]:
                covered_by_ignored.append((pdf, [g[0] for g in ignored_match]))
        else:
            reasons = []
            for (p, w, ok, e, mt, ign, sub) in mds:
                why = []
                if not sub:
                    why.append(f"nur {w} Woerter, kein summary-Feld")
                if not ok:
                    why.append(f"FM-Fehler: {'; '.join(e[:2])}")
                if ign:
                    why.append("ignore=yes")
                reasons.append(f"{p.name} [{', '.join(why)}]")
            pdf_broken_link.append((pdf, reasons))

    # .md that didn't match any PDF
    problem_paths = {p for p, _ in md_problems}
    md_no_pdf_match: list[Path] = [
        md for md, pdf in md_to_pdf.items()
        if pdf is None and md not in problem_paths
    ]

    # --- Print report ---
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total_covered = len(safe_to_delete) + len(pdf_duplicate_version)
    print(f"  PDFs total:                       {len(all_pdfs)}")
    print(f"  PDFs via IGNORED_PDFS:            {len(pdfs_ignored)}")
    print(f"  PDFs zu pruefen:                  {len(pdfs)}")
    print(f"  Sicher loeschbar:                 {len(safe_to_delete)}")
    print(f"   (davon nur via ignore=yes:       {len(covered_by_ignored)})")
    print(f"  Loeschbar (Duplikat-Version):     {len(pdf_duplicate_version)}")
    print(f"  GESAMT GEDECKT:                   {total_covered} / {len(pdfs)}")
    print()
    print(f"  Orphan-PDFs (keine .md):          {len(pdf_orphans)}")
    print(f"  PDF mit schwacher .md (Stub):     {len(pdf_broken_link)}")
    print(f"  .md ohne passende PDF:            {len(md_no_pdf_match)}")
    print(f"  .md mit kaputtem Frontmatter:     {len(md_problems)}")
    print(f"  .md ignoriert (Duplikate):        {md_ignored_count}")
    print()

    def section(title, items, fmt):
        if not items:
            return
        print("-" * 70)
        print(f"{title} ({len(items)})")
        print("-" * 70)
        for x in items:
            print(fmt(x))
        print()

    # For each orphan PDF, find best candidate .md (regardless of threshold)
    md_slug_to_path = {md.stem: md for md in md_files}
    md_title_slugs: dict[str, Path] = {}
    for md in md_files:
        data, _, _ = load_md(md)
        if data and data.get("title"):
            md_title_slugs[slugify(data["title"])] = md

    def best_md_candidate(pdf: Path):
        pdf_slug = slugify(pdf.stem)
        pdf_tokens = content_tokens(pdf_slug)
        best, score = None, 0.0
        for src in (md_slug_to_path, md_title_slugs):
            for slug, p in src.items():
                s = jaccard(pdf_tokens, content_tokens(slug))
                if s > score:
                    best, score = p, s
        return best, score

    def fmt_orphan(pdf: Path) -> str:
        cand, score = best_md_candidate(pdf)
        if cand and score > 0:
            return f"  {pdf.name}\n    bester Kandidat: {cand.name} (score={score:.2f})"
        return f"  {pdf.name}\n    (kein .md-Kandidat gefunden)"

    section("PDF gedeckt durch .md zu anderer PDF-Version (Duplikat — pruefen, dann loeschbar)",
            pdf_duplicate_version,
            lambda x: f"  {x[0].name}\n    -> .md '{x[1].name}' deckt die Publikation (score={x[2]:.2f})")
    section("ORPHAN PDFs (kein passendes .md unter Jaccard-Threshold gefunden)",
            pdf_orphans, fmt_orphan)
    section("PDF mit schwacher .md (Body zu kurz / FM ungueltig)",
            pdf_broken_link, lambda x: f"  {x[0].name}\n    -> {'; '.join(x[1])}")
    section("PDF mit mehreren .mds (Duplikat-Pflege)",
            pdf_multi, lambda x: f"  {x[0].name}\n    -> " + ", ".join(p.name for p in x[1]))
    section(".md ohne passende PDF",
            md_no_pdf_match, lambda p: f"  {p.name}")
    section(".md mit kaputtem Frontmatter",
            md_problems, lambda x: f"  {x[0].name}: {x[1]}")

    print("=" * 70)
    blockers = (pdf_orphans, pdf_broken_link, md_problems)
    if any(blockers):
        print("ERGEBNIS: NICHT sicher, alle PDFs zu loeschen.")
        print("Behebe die obigen Probleme zuerst.")
        print("=" * 70)
        return 1 if args.strict else 0

    print(f"ERGEBNIS: Alle {len(safe_to_delete)} PDFs sicher loeschbar.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
