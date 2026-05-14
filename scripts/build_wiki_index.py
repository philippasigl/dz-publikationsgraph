"""Generiert wiki/index.md aus wiki/themen/*.md, wiki/konzepte/*.md
und wiki/publikationen/*.md.

Liest:
    wiki/themen/*.md         → Titel aus Frontmatter, Kurz-Beschreibung aus erstem Paragraph
    wiki/konzepte/*.md       → dito
    wiki/publikationen/*.md  → nur Count fuer die Statistik

Schreibt:
    wiki/index.md

Aufruf:
    python scripts/build_wiki_index.py            # regenerieren
    python scripts/build_wiki_index.py --check    # nur pruefen (exit 1 bei Drift)
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
INDEX = WIKI / "index.md"


def title_of(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if m:
        tm = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', m.group(1), re.MULTILINE)
        if tm:
            return tm.group(1).strip().strip('"').strip("'")
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def first_para(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    paras, cur = [], []
    for line in text.splitlines():
        if line.startswith("#"):
            if cur:
                paras.append(" ".join(cur)); cur = []
            continue
        if line.strip() == "":
            if cur:
                paras.append(" ".join(cur)); cur = []
        else:
            cur.append(line.strip())
    if cur:
        paras.append(" ".join(cur))
    return paras[0] if paras else ""


def shorten(text: str, max_len: int) -> str:
    text = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("|", "/").replace("  ", " ").strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > max_len * 0.5 else cut).rstrip(",;:—-") + "…"


def collect(area: str, max_desc: int) -> list[tuple[str, str]]:
    d = WIKI / area
    return [
        (p.stem, shorten(first_para(p), max_desc))
        for p in sorted(d.glob("*.md"))
    ]


def render_table(rows: list[tuple[str, str]]) -> str:
    # Wikilink ohne |display — sync_to_site.py setzt Frontmatter-Titel ein.
    # Vermeidet Pipe-Konflikt mit Markdown-Tabellen-Spalten.
    out = ["| Seite | Beschreibung |", "|---|---|"]
    for slug, desc in rows:
        out.append(f"| [[{slug}]] | {desc} |")
    return "\n".join(out)


def build() -> str:
    themen = collect("themen", max_desc=110)
    konzepte = collect("konzepte", max_desc=85)
    npubs = len(list((WIKI / "publikationen").glob("*.md")))
    today = date.today().isoformat()
    return f"""# DZ Wiki – Index

Katalog aller Wiki-Seiten. Vollständige Navigation auch über die Sidebar.

---

## Themen

{render_table(themen)}

---

## Konzepte

Alphabetisch sortiert.

{render_table(konzepte)}

---

## Statistik

- **{len(themen)} Themen-Seiten**
- **{len(konzepte)} Konzept-Seiten**
- **{npubs} Publikationen** im Korpus

---

*Letzte Aktualisierung: {today}*
"""


def strip_date(text: str) -> str:
    """Entferne Datum-Zeile fuer Drift-Vergleich (Datum aendert sich taeglich)."""
    return re.sub(r"\*Letzte Aktualisierung: \d{4}-\d{2}-\d{2}\*", "", text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="Nur pruefen, ob index aktuell ist; exit 1 bei Drift")
    args = ap.parse_args()

    new = build()
    if args.check:
        if not INDEX.exists():
            print("wiki/index.md fehlt"); return 1
        old = INDEX.read_text(encoding="utf-8")
        if strip_date(old) != strip_date(new):
            print("Drift erkannt: wiki/index.md weicht von der Soll-Form ab.")
            print("Fix mit: python scripts/build_wiki_index.py")
            return 1
        print("wiki/index.md ist aktuell.")
        return 0

    INDEX.write_text(new, encoding="utf-8")
    themen = new.count("\n| [[") // 2  # rough, just for log
    print(f"wrote {INDEX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
