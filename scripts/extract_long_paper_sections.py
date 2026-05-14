#!/usr/bin/env python3
"""
Schneidet lange konvertierte Papers in drei fokussierte Abschnitte fuer die
Strukturierungs-Phase (pdf-ingestion Skill).

Strategie ab 15.000 Woertern:
  - Anfang:   erste ~8.000 Woerter (Title + Exec Summary + Einleitung + Section 1)
  - Schluss:  letzte ~4.000 Woerter VOR dem ersten Annex/Lit-Marker
  - Zahlen:   alle Tabellen aus dem gesamten Body

Output: drei klar getrennte Sections auf stdout. Claude kann das Ergebnis lesen
und daraus die strukturierte Stub-Markdown bauen.

Verwendung:
    python scripts/extract_long_paper_sections.py wiki/publikationen/<datei>.md
"""

import argparse
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

LONG_THRESHOLD = 15_000   # Woerter
HEAD_WORDS = 8_000        # Anfang
TAIL_WORDS = 4_000        # Schluss vor Annex

# Annex/Literatur-Marker (case-insensitive, am Zeilenanfang nach optionalen # / Whitespace)
ANNEX_PATTERNS = [
    r"literatur(verzeichnis)?",
    r"references?",
    r"bibliographie?",
    r"bibliography",
    r"anhang",
    r"annex",
    r"appendix",
    r"quellen(verzeichnis)?",
    r"endnoten",
]
ANNEX_RE = re.compile(
    r"^\s*#{0,6}\s*(" + "|".join(ANNEX_PATTERNS) + r")\b[\s:]*$",
    re.IGNORECASE | re.MULTILINE,
)

# Markdown-Tabellenzeile: mind. 2 Spalten
TABLE_ROW_RE = re.compile(r"^\s*\|.+\|.+\|\s*$", re.MULTILINE)


def split_frontmatter(text: str) -> tuple[str, str]:
    """Returns (frontmatter_block_or_empty, body)."""
    m = re.match(r"^(---\n.*?\n---\n)(.*)", text, re.S)
    if m:
        return m.group(1), m.group(2)
    return "", text


def find_annex_offset(body: str) -> int | None:
    """Returns char offset of first annex/lit marker in the SECOND HALF, or None.

    Search only in the second half to avoid matching table-of-contents entries
    in the front matter (e.g. 'Anhang: Annahmen der Sensitivitaeten' listed in TOC).
    """
    half = len(body) // 2
    m = ANNEX_RE.search(body, half)
    return m.start() if m else None


def take_first_words(text: str, n: int) -> str:
    words = text.split()
    return " ".join(words[:n])


def take_last_words(text: str, n: int) -> str:
    words = text.split()
    return " ".join(words[-n:]) if len(words) > n else text


def extract_tables(text: str) -> list[str]:
    """Find blocks of consecutive table rows. Returns list of table strings."""
    lines = text.splitlines()
    tables = []
    current = []
    for ln in lines:
        if TABLE_ROW_RE.match(ln):
            current.append(ln)
        else:
            if len(current) >= 2:  # at least header + one row
                tables.append("\n".join(current))
            current = []
    if len(current) >= 2:
        tables.append("\n".join(current))
    return tables


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", type=Path, help="Pfad zur konvertierten .md-Datei")
    p.add_argument("--threshold", type=int, default=LONG_THRESHOLD,
                   help=f"Wort-Schwellwert fuer 'lang' (default: {LONG_THRESHOLD})")
    args = p.parse_args()

    if not args.path.exists():
        print(f"FEHLER: {args.path} existiert nicht", file=sys.stderr)
        sys.exit(1)

    text = args.path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    total_words = len(body.split())

    print(f"# Long-Paper-Extraction Report")
    print(f"# Datei:     {args.path.name}")
    print(f"# Woerter:   {total_words}")
    print(f"# Threshold: {args.threshold}")
    print()

    if total_words < args.threshold:
        print(f"# Paper ist KURZ ({total_words} < {args.threshold}) — kein Splitting noetig.")
        print("# Strukturiere die ganze Datei normal.")
        print()
        print("=" * 70)
        print("VOLLER BODY")
        print("=" * 70)
        print(body.strip())
        return 0

    # Long paper: split
    annex_offset = find_annex_offset(body)
    if annex_offset is not None:
        main_body = body[:annex_offset]
        annex_section = body[annex_offset:]
        annex_info = f"Annex/Lit-Marker gefunden bei Zeichen {annex_offset}"
    else:
        main_body = body
        annex_section = ""
        annex_info = "Kein Annex/Lit-Marker gefunden — Schluss aus gesamtem Body"

    anfang = take_first_words(main_body, HEAD_WORDS)
    schluss = take_last_words(main_body, TAIL_WORDS)
    tables = extract_tables(main_body)

    print(f"# Paper ist LANG ({total_words} >= {args.threshold}) — gesplittet:")
    print(f"# Anfang:   erste {HEAD_WORDS} Woerter")
    print(f"# Schluss:  letzte {TAIL_WORDS} Woerter")
    print(f"# Tabellen: {len(tables)} im Hauptteil gefunden")
    print(f"# {annex_info}")
    print()

    print("=" * 70)
    print("ANFANG (Exec Summary + Einleitung — fuer Kernthesen)")
    print("=" * 70)
    print(anfang)
    print()

    print("=" * 70)
    print("SCHLUSS (Conclusion + Policy Recommendations — fuer Schlussfolgerungen)")
    print("=" * 70)
    print(schluss)
    print()

    if tables:
        print("=" * 70)
        print(f"TABELLEN ({len(tables)} — fuer Zahlen)")
        print("=" * 70)
        for i, t in enumerate(tables, 1):
            print(f"\n## Tabelle {i}")
            print(t)
    else:
        print("=" * 70)
        print("TABELLEN — keine gefunden, Zahlen aus Fliesstext extrahieren")
        print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
