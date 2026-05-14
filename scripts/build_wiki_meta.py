"""Generiert publikationsgraph/wiki-meta.json mit Themen+Konzepte fuer die
Index-Section in publikationsgraph/index.html.

Liest:
    wiki/themen/*.md     → Titel aus erster '# '-Zeile, slug aus Dateiname
    wiki/konzepte/*.md   → dito

Schreibt:
    publikationsgraph/wiki-meta.json

Aufruf:
    python scripts/build_wiki_meta.py
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "publikationsgraph" / "wiki-meta.json"


def extract_title(text: str, fallback: str) -> str:
    """Titel aus Frontmatter (title:) oder erster '# ...'-Zeile, sonst fallback."""
    lines = text.splitlines()
    in_fm = False
    for i, line in enumerate(lines):
        s = line.strip()
        if i == 0 and s == "---":
            in_fm = True
            continue
        if in_fm:
            if s == "---":
                in_fm = False
                continue
            m = re.match(r'title\s*:\s*"?([^"]+)"?\s*$', s)
            if m:
                return m.group(1).strip()
            continue
        if s.startswith("# "):
            return s[2:].strip()
        if s:
            break
    return fallback


def extract_description(text: str, max_len: int = 140) -> str:
    """Erste nicht-leere Nicht-Header-Zeile als Kurzbeschreibung.

    - Wikilinks [[X]] werden zu X aufgelöst (sonst hängen sie als literale
      Klammern in der UI).
    - Truncation an Wortgrenze mit Ellipsis, nicht mitten im Wort.
    """
    lines = text.splitlines()
    in_fm = False
    raw = ""
    for i, line in enumerate(lines):
        s = line.strip()
        if i == 0 and s == "---":
            in_fm = True
            continue
        if in_fm:
            if s == "---":
                in_fm = False
            continue
        if not s or s.startswith("#"):
            continue
        raw = s
        break
    if not raw:
        return ""
    # [[Slug|Label]] → Label, [[Slug]] → Slug
    raw = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", raw)
    raw = re.sub(r"\[\[([^\]]+)\]\]", r"\1", raw)
    if len(raw) <= max_len:
        return raw
    cut = raw[:max_len].rsplit(" ", 1)[0]
    return cut.rstrip(",;:.-") + "…"


def collect(dirname: str) -> list[dict]:
    d = ROOT / "wiki" / dirname
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        out.append({
            "slug": p.stem,
            "title": extract_title(text, p.stem),
            "desc": extract_description(text),
        })
    return out


def main() -> int:
    themen = collect("themen")
    konzepte = collect("konzepte")
    meta = {"themen": themen, "konzepte": konzepte}
    OUTPUT.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Themen:   {len(themen)}")
    print(f"Konzepte: {len(konzepte)}")
    print(f"Output:   {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
