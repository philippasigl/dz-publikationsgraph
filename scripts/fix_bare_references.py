"""Konvertiert nackten Titel-Text nach Pfeil/Bullet in Wikilinks.

Suchmuster:
    - `→ Foo Bar`         (Pfeil-Listen in Schlussfolgerungen)
    - Wo "Foo Bar" mit dem Frontmatter-`title` einer existierenden
      Publikation/Theme/Konzept-Datei (fuzzy) uebereinstimmt → ersetze
      durch `[[slug|Foo Bar]]`.

Ueberspringt:
    - Bereits formatierte `[…](…)` Markdown-Links
    - Bereits formatierte `[[…]]` Wikilinks

Aufruf:
    python scripts/fix_bare_references.py             # Dry-run
    python scripts/fix_bare_references.py --apply
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from slugify import slugify  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AREAS = ("themen", "konzepte", "publikationen")

STOPWORDS = {
    "der", "die", "das", "den", "dem", "des", "und", "oder", "ein", "eine",
    "in", "im", "auf", "zu", "zur", "zum", "fuer", "für", "von", "vom",
    "the", "of", "and", "to", "for", "in", "on", "with",
    "wie", "was", "warum", "nach", "bei", "an", "am", "uns", "unser",
}


def tokens(s: str) -> set[str]:
    s = s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return {w for w in re.findall(r"[a-z0-9]{3,}", s) if w not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def build_title_index() -> list[tuple[str, str, set[str]]]:
    """list of (slug, title, token_set) — fuer fuzzy lookup."""
    out = []
    for area in AREAS:
        d = ROOT / "wiki" / area
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            text = p.read_text(encoding="utf-8")
            # title from frontmatter or first '# '
            title = p.stem
            m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if m:
                tm = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$',
                               m.group(1), re.MULTILINE)
                if tm:
                    title = tm.group(1).strip().strip('"').strip("'")
            if title == p.stem:
                for line in text.splitlines():
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
            # Skip ignored
            if m:
                try:
                    fm = yaml.safe_load(m.group(1)) or {}
                except yaml.YAMLError:
                    fm = {}
                iv = fm.get("ignore")
                if iv is True or str(iv).strip().lower() == "yes":
                    continue
            out.append((p.stem, title, tokens(title) | tokens(p.stem)))
    return out


def find_best_match(text: str, idx: list[tuple[str, str, set[str]]],
                    threshold: float = 0.5) -> tuple[str, str, float] | None:
    target_tok = tokens(text)
    if not target_tok:
        return None
    best = None
    best_score = 0.0
    target_slug = slugify(text)
    for slug, title, toks in idx:
        # Exact slug match → score 1.0
        if target_slug == slug:
            return slug, title, 1.0
        score = jaccard(target_tok, toks)
        if score > best_score:
            best = (slug, title, score)
            best_score = score
    if best and best_score >= threshold:
        return best
    return None


# Pattern: line starts with bullet (-/*) optional whitespace,
# contains → followed by space, then PLAINTEXT (not [...](...) and not [[...]])
# capture: (prefix, plaintext)
# zB:  "- Detaillierte Ausarbeitung folgt in → FAQ zu unserem Reformvorschlag…"
ARROW_LINE_RE = re.compile(
    r"^(\s*[-*]\s.*?→\s+)(?!\[)(?!\*\[)(.+?)\s*$",
    re.MULTILINE,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args()

    idx = build_title_index()
    print(f"Slug-Index: {len(idx)} bekannte Slugs\n")

    n_files = n_converted = n_unmatched = 0
    for area in AREAS:
        d = ROOT / "wiki" / area
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            text = p.read_text(encoding="utf-8")
            changed = False

            def replace(m: re.Match) -> str:
                nonlocal changed
                global_acc = m.group(0)
                prefix, plaintext = m.group(1), m.group(2).strip()
                # Skip if it already contains link/wikilink syntax
                if "[[" in plaintext or "[" in plaintext or "](" in plaintext:
                    return global_acc
                # Skip very short refs (3 chars or fewer)
                if len(plaintext) < 4:
                    return global_acc
                match = find_best_match(plaintext, idx, args.threshold)
                if not match:
                    nonlocal_unmatched.append((p.stem, plaintext))
                    return global_acc
                slug, title, score = match
                # Self-link check
                if slug == p.stem:
                    return global_acc
                changed = True
                print(f"  [{score:.2f}] {area}/{p.stem}  '→ {plaintext}'  →  [[{slug}|{plaintext}]]")
                return f"{prefix}[[{slug}|{plaintext}]]"

            nonlocal_unmatched: list[tuple[str, str]] = []
            new_text = ARROW_LINE_RE.sub(replace, text)
            if changed:
                n_files += 1
                n_converted += new_text.count("[[") - text.count("[[")
                if args.apply:
                    p.write_text(new_text, encoding="utf-8")
            n_unmatched += len(nonlocal_unmatched)
            if nonlocal_unmatched:
                for slug, pt in nonlocal_unmatched:
                    print(f"  [SKIP] {area}/{slug}: '→ {pt}' (kein guter Match)")

    print(f"\nDateien geaendert: {n_files}")
    print(f"Wikilinks erzeugt: {n_converted}")
    print(f"Nicht zugeordnet:  {n_unmatched}")
    if not args.apply:
        print("\nDry-run. --apply schreibt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
