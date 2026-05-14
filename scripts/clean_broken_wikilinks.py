"""Entfernt unaufloesbare [[wikilinks]] aus den Source-MDs in wiki/.

Geht alle wiki/themen/*.md, wiki/konzepte/*.md, wiki/publikationen/*.md durch.
Wikilinks deren Slug nicht in den existierenden Dateien gefunden wird, werden
entfernt. Separatoren (` · `, `\\n- `) werden anschliessend bereinigt.

Aufruf:
    python scripts/clean_broken_wikilinks.py            # Dry-run mit Liste
    python scripts/clean_broken_wikilinks.py --apply    # Schreibt die Aenderungen
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from slugify import slugify  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AREAS = ("themen", "konzepte", "publikationen")
WIKILINK_RE = re.compile(r"\[\[([^\]\n]+)\]\]")


def build_slug_index() -> set[str]:
    out: set[str] = set()
    for area in AREAS:
        d = ROOT / "wiki" / area
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            out.add(p.stem)
    return out


def clean_text(text: str, slugs: set[str], broken_acc: list[tuple[str, str]],
               source: str) -> str:
    def repl(m: re.Match) -> str:
        raw = m.group(1).strip()
        target = raw.split("|")[0].strip()
        # 1) literal match
        if target in slugs:
            return m.group(0)
        # 2) slugify fallback — rewrite link to canonical slug
        canon = slugify(target)
        if canon in slugs:
            if "|" in raw:
                display = raw.split("|", 1)[1].strip()
                return f"[[{canon}|{display}]]"
            return f"[[{canon}|{target}]]"
        broken_acc.append((source, raw))
        return ""
    text = WIKILINK_RE.sub(repl, text)
    # Cleanup leftover separators
    text = re.sub(r"\s·\s+·\s", " · ", text)
    text = re.sub(r"\s·\s*(?=\n)", "", text)
    text = re.sub(r"(?<=\n)\s*·\s+", "", text)
    text = re.sub(r"^- $", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    slugs = build_slug_index()
    broken: list[tuple[str, str]] = []
    n_changed = 0

    for area in AREAS:
        d = ROOT / "wiki" / area
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            text = p.read_text(encoding="utf-8")
            new_text = clean_text(text, slugs, broken, f"{area}/{p.stem}")
            if new_text != text:
                n_changed += 1
                if args.apply:
                    p.write_text(new_text, encoding="utf-8")

    print(f"Slug-Index: {len(slugs)} bekannte Slugs")
    print(f"Unaufloesbare Wikilinks: {len(broken)}")
    if broken:
        # Gruppieren nach Slug
        by_slug: dict[str, list[str]] = {}
        for src, raw in broken:
            slug = raw.split("|")[0].strip()
            by_slug.setdefault(slug, []).append(src)
        for slug, sources in sorted(by_slug.items(), key=lambda x: -len(x[1])):
            print(f"  {len(sources):3d}x  [[{slug}]]")
            for s in sources[:3]:
                print(f"           in {s}")
            if len(sources) > 3:
                print(f"           ... +{len(sources)-3} weitere")
    print()
    print(f"Dateien betroffen: {n_changed}")
    if not args.apply:
        print("\nDry-run. --apply schreibt die Aenderungen in wiki/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
