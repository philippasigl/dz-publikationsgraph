"""Erkennt nackte Slug-Texte in wiki/*.md und konvertiert/entfernt sie.

Eine Slug-Form ist `wort-wort-wort` (mind. 3 Hyphen-separierte lowercase
Tokens). Pruefe gegen Slug-Index:

    - Slug existiert + nicht ignoriert  → wandle in `[[slug]]`
    - Slug existiert + `ignore: yes`    → entferne den Slug-Text
    - Slug existiert nicht (z.B. "across-the-board") → lass stehen

Anschliessend werden Komma-Reste, „und ." und leere Listen-Trailer
aufgeraeumt.

Aufruf:
    python scripts/fix_bare_slugs.py            # Dry-run
    python scripts/fix_bare_slugs.py --apply
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
AREAS = ("themen", "konzepte", "publikationen")

# Slug-Muster: mind. 3 lowercase-hyphen Tokens, am Wortgrenz-Rand
SLUG_RE = re.compile(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+){2,}\b")


def build_indices() -> tuple[set[str], set[str]]:
    active: set[str] = set()
    ignored: set[str] = set()
    for area in AREAS:
        d = ROOT / "wiki" / area
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            t = p.read_text(encoding="utf-8")
            m = re.match(r"^---\s*\n(.*?)\n---", t, re.DOTALL)
            iv = None
            if m:
                try:
                    fm = yaml.safe_load(m.group(1)) or {}
                except yaml.YAMLError:
                    fm = {}
                iv = fm.get("ignore")
            if iv is True or str(iv).strip().lower() == "yes":
                ignored.add(p.stem)
            else:
                active.add(p.stem)
    return active, ignored


def in_protected_context(text: str, start: int, end: int) -> bool:
    """True wenn position innerhalb von [[…]], [...](...) oder URL liegt."""
    # Innerhalb [[ … ]]?
    pre = text[max(0, start - 200):start]
    if pre.rfind("[[") > pre.rfind("]]"):
        return True
    # Innerhalb (…/…)?
    if pre.rfind("(") > pre.rfind(")"):
        # check if it's a markdown link URL
        last_paren = pre.rfind("(")
        if last_paren >= 1 and pre[last_paren - 1] == "]":
            return True
        if "/wiki/" in pre[last_paren:]:
            return True
    # Innerhalb [...](: display text — keep slug
    if pre.rfind("[") > pre.rfind("]"):
        return True
    # In frontmatter? (zwischen ersten zwei ---)
    if text[:end].count("---\n") == 1:
        return True
    return False


def cleanup_dangling(text: str) -> str:
    # ", ," → ","
    text = re.sub(r",\s*,", ",", text)
    # " ,  und" / ", und" → " und"
    text = re.sub(r",\s*(?=\s+und\b)", "", text)
    # "und ." → "."
    text = re.sub(r"\bund\s+\.", ".", text)
    # "in ." / "in :" → entfernt
    text = re.sub(r"\b(?:in|siehe|siehe auch|dazu in|weiterf[üu]hrend in|related to|related contributions:)\s*\.", "", text, flags=re.IGNORECASE)
    # "Weiterführend: " mit nichts dahinter (vor Zeilenende)
    text = re.sub(r"^\s*[-*]\s*Weiterf[üu]hrend\s*:?\s*\.?\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r"^\s*[-*]\s*Related\s+contributions:\s*\.?\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
    # double commas/separators in lists
    text = re.sub(r",\s+und\b", " und", text)
    # zwei spaces → ein space
    text = re.sub(r"  +", " ", text)
    # ggf entstandene Leerzeilen
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    active, ignored = build_indices()
    print(f"Slug-Index: {len(active)} aktiv, {len(ignored)} ignored\n")

    stats = {"converted": 0, "removed": 0, "skipped_unknown": 0, "files": 0}

    for area in AREAS:
        d = ROOT / "wiki" / area
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            text = p.read_text(encoding="utf-8")

            def repl(m: re.Match) -> str:
                s = m.group(0)
                if in_protected_context(text, m.start(), m.end()):
                    return s
                if s == p.stem:  # self-reference
                    return s
                if s in active:
                    stats["converted"] += 1
                    print(f"  [CONV] {area}/{p.stem}: {s} → [[{s}]]")
                    return f"[[{s}]]"
                if s in ignored:
                    stats["removed"] += 1
                    print(f"  [DROP] {area}/{p.stem}: {s} (ignored target)")
                    return ""
                stats["skipped_unknown"] += 1
                return s  # not a slug we know

            new_text = SLUG_RE.sub(repl, text)
            if new_text != text:
                new_text = cleanup_dangling(new_text)
                stats["files"] += 1
                if args.apply:
                    p.write_text(new_text, encoding="utf-8")

    print(f"\nDateien geaendert: {stats['files']}")
    print(f"  konvertiert (in [[…]]): {stats['converted']}")
    print(f"  entfernt (ignored):     {stats['removed']}")
    print(f"  uebersprungen (kein bekannter Slug): {stats['skipped_unknown']}")
    if not args.apply:
        print("\nDry-run. --apply schreibt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
