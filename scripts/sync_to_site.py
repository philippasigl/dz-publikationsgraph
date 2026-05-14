"""Sync content from the wiki source layer into the Docusaurus site/ layer.

`wiki/` and `publikationen/` are the source of truth. `site/docs/` and
`site/static/` are generated mirrors used by Docusaurus.

Run from repo root: `python scripts/sync_to_site.py`

Copies (overwrite-if-newer):
- wiki/publikationen/*.md          -> site/docs/publikationen/
- wiki/themen/*.md                 -> site/docs/themen/
- wiki/konzepte/*.md               -> site/docs/konzepte/
- wiki/index.md                    -> site/docs/index.md
- publikationen/*.pdf              -> site/static/publikationen/

Deletes stray files in the destination that no longer exist in the source
(prevents drift from manual `cp` operations that were never reversed).
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from slugify import slugify  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# (source_dir, dest_dir, glob_pattern)
DIR_SYNCS: list[tuple[Path, Path, str]] = [
    (ROOT / "wiki" / "publikationen", ROOT / "site" / "docs" / "publikationen", "*.md"),
    (ROOT / "wiki" / "themen",        ROOT / "site" / "docs" / "themen",        "*.md"),
    (ROOT / "wiki" / "konzepte",      ROOT / "site" / "docs" / "konzepte",      "*.md"),
    (ROOT / "publikationen",          ROOT / "site" / "static" / "publikationen", "*.pdf"),
    # publikationsgraph/* wird NICHT mehr nach site/static/ gespiegelt —
    # der Graph-Viewer wird via publish_graph.py separat nach dev/ Root
    # deployed, nicht als Docusaurus-Subpfad.
]

# (source_file, dest_file)
FILE_SYNCS: list[tuple[Path, Path]] = [
    (ROOT / "wiki" / "index.md",
     ROOT / "site" / "docs" / "index.md"),
]


def sync_dir(src: Path, dst: Path, pattern: str) -> tuple[int, int, int]:
    """Mirror src/<pattern> to dst. Returns (copied, skipped, deleted)."""
    if not src.exists():
        print(f"[SKIP] source missing: {src}")
        return (0, 0, 0)
    dst.mkdir(parents=True, exist_ok=True)

    src_files = {f.name: f for f in src.glob(pattern) if f.is_file()}
    dst_files = {f.name: f for f in dst.glob(pattern) if f.is_file()}

    copied = skipped = deleted = 0

    for name, src_file in src_files.items():
        dst_file = dst / name
        if dst_file.exists() and dst_file.stat().st_mtime >= src_file.stat().st_mtime:
            skipped += 1
            continue
        shutil.copy2(src_file, dst_file)
        copied += 1

    for name, dst_file in dst_files.items():
        if name not in src_files:
            dst_file.unlink()
            deleted += 1

    print(f"[DIR ] {str(src.relative_to(ROOT)):30s} -> {dst.relative_to(ROOT)}  "
          f"copied={copied} skipped={skipped} deleted={deleted}")
    return (copied, skipped, deleted)


def sync_file(src: Path, dst: Path) -> bool:
    """Copy src to dst if src is newer. Returns True if copied."""
    if not src.exists():
        print(f"[SKIP] source missing: {src}")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        print(f"[FILE] {src.relative_to(ROOT)}  up-to-date")
        return False
    shutil.copy2(src, dst)
    print(f"[FILE] {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
    return True


WIKILINK_RE = re.compile(r"\[\[([^\]\n]+)\]\]")
TITLE_FRONTMATTER_RE = re.compile(
    r'^title:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)


def extract_title(text: str, fallback: str) -> str:
    """title aus Frontmatter, sonst erste `# `-Zeile, sonst fallback."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if m:
        tm = TITLE_FRONTMATTER_RE.search(m.group(1))
        if tm:
            return tm.group(1).strip().strip('"').strip("'")
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def build_slug_indices() -> tuple[dict[str, str], dict[str, str]]:
    """slug → area  und  slug → title."""
    area_idx: dict[str, str] = {}
    title_idx: dict[str, str] = {}
    for area in ("themen", "konzepte", "publikationen"):
        d = ROOT / "wiki" / area
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            area_idx[p.stem] = area
            title_idx[p.stem] = extract_title(
                p.read_text(encoding="utf-8"), p.stem)
    return area_idx, title_idx


def transform_wikilinks_in_site() -> tuple[int, int, int]:
    """Walk site/docs/ and convert [[slug]] / [[slug|display]] to MD links.

    Display-Text wird automatisch der Frontmatter-Titel des Ziels, wenn
    [[slug]] ohne `|display` benutzt wird.

    Returns (files_changed, links_resolved, links_unresolved).
    """
    slug_to_area, slug_to_title = build_slug_indices()
    docs = ROOT / "site" / "docs"
    n_files = n_links = n_missing = 0

    def replace(m: re.Match) -> str:
        nonlocal n_links, n_missing
        raw = m.group(1).strip()
        explicit_display: str | None = None
        if "|" in raw:
            target, explicit_display = [s.strip() for s in raw.split("|", 1)]
        else:
            target = raw
        # 1) Wörtlicher Slug match
        area = slug_to_area.get(target)
        if not area:
            # 2) Slugified fallback (handles Title-style wikilinks)
            slug_try = slugify(target)
            area = slug_to_area.get(slug_try)
            if area:
                target = slug_try
        if area:
            n_links += 1
            display = explicit_display or slug_to_title.get(target, target)
            return f"[{display}](/wiki/{area}/{target})"
        n_missing += 1
        # Unaufloesbar: ganz entfernen
        return ""

    for p in docs.rglob("*.md"):
        text = p.read_text(encoding="utf-8")
        new_text = WIKILINK_RE.sub(replace, text)
        # Cleanup leftover-Separatoren wenn Wikilinks komplett entfernt wurden:
        # "[link] · " → "[link] " (trailing) und " ·  · " → " · "
        new_text = re.sub(r"\s·\s+·\s", " · ", new_text)        # doppelter dot
        new_text = re.sub(r"\s·\s*(?=\n)", "", new_text)         # dot vor Zeilenende
        new_text = re.sub(r"(?<=\n)\s*·\s+", "", new_text)       # dot am Zeilenanfang
        new_text = re.sub(r"^- $", "", new_text, flags=re.MULTILINE)  # leerer Bullet
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            n_files += 1
    return n_files, n_links, n_missing


def main() -> int:
    print(f"Syncing from {ROOT}\n")
    for src, dst, pattern in DIR_SYNCS:
        sync_dir(src, dst, pattern)
    print()
    for src, dst in FILE_SYNCS:
        sync_file(src, dst)
    print()
    n_files, n_links, n_missing = transform_wikilinks_in_site()
    print(f"[WIKILINKS] {n_files} Dateien transformiert, "
          f"{n_links} Links aufgeloest, {n_missing} unaufloesbar")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
