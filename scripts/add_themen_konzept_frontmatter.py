"""Ergaenzt fehlendes YAML-Frontmatter in wiki/themen/*.md und wiki/konzepte/*.md.

Liest die erste `# `-Zeile als Titel und schreibt:
    ---
    title: <Titel>
    sidebar_label: <Titel>   # gleicher Wert, damit Docusaurus den Slug
                              # nicht auto-capitalisiert
    ---

Aufruf:
    python scripts/add_themen_konzept_frontmatter.py             # Dry-run
    python scripts/add_themen_konzept_frontmatter.py --apply
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    touched = 0
    for area in ("themen", "konzepte"):
        d = ROOT / "wiki" / area
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            text = p.read_text(encoding="utf-8")
            if text.startswith("---"):
                continue  # bereits Frontmatter
            # Titel = erste '# '-Zeile
            title = p.stem
            for line in text.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            fm = (
                "---\n"
                f"title: \"{title}\"\n"
                f"sidebar_label: \"{title}\"\n"
                "---\n\n"
            )
            new_text = fm + text
            print(f"[+FM] {area}/{p.stem}  → \"{title}\"")
            if args.apply:
                p.write_text(new_text, encoding="utf-8")
            touched += 1
    print(f"\nTouched: {touched}")
    if not args.apply:
        print("Dry-run. --apply schreibt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
