#!/usr/bin/env python3
"""
Publiziert den aktuellen Stand des Publikationsgraphen nach GitHub Pages.

Workflow:
  1. Kopiert index.html, data.json, nodes.csv, edges.csv aus
     publikationsgraph/ nach ~/dev/dz-wiki/
  2. git add + commit + push im Zielrepo
  3. GitHub Actions oder Pages baut → Live unter
     https://philippasigl.github.io/dz-wiki/

Verwendung:
    python scripts/publish_graph.py
    python scripts/publish_graph.py -m "Cluster-Update Mai"
    python scripts/publish_graph.py --dry-run     # nichts schreiben/pushen

Voraussetzungen (einmalig):
  - GitHub-Repo philippasigl/dz-wiki existiert
  - Lokales Clone unter ~/dev/dz-wiki (wird ggf. neu geklont)
  - GitHub Pages auf main / root aktiviert
"""

import argparse
import io
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).parent.parent
SOURCE_DIR = ROOT / "publikationsgraph"
TARGET_DIR = Path.home() / "dev" / "dz-wiki"
REPO_URL = "https://github.com/philippasigl/dz-wiki.git"

# Nur diese Dateien werden publiziert. Backup-CSVs und geschichte.md bleiben lokal.
PUBLISH_FILES = ["index.html", "data.json", "wiki-meta.json"]


def run(cmd, cwd=None, check=True):
    """Run a shell command and stream output."""
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd, check=check,
                            capture_output=True, text=True, encoding="utf-8")
    if result.stdout.strip():
        for line in result.stdout.splitlines():
            print(f"    {line}")
    if result.stderr.strip() and result.returncode != 0:
        for line in result.stderr.splitlines():
            print(f"    [stderr] {line}", file=sys.stderr)
    return result


def ensure_target(dry_run: bool):
    """Klone das Repo wenn das Target-Verzeichnis fehlt."""
    if TARGET_DIR.exists() and (TARGET_DIR / ".git").exists():
        return
    if dry_run:
        print(f"  [dry-run] would clone {REPO_URL} to {TARGET_DIR}")
        return
    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)
    print(f"Klone Repo nach {TARGET_DIR} ...")
    run(["git", "clone", REPO_URL, str(TARGET_DIR)])


def copy_files(dry_run: bool):
    """Kopiere die zu publizierenden Files."""
    print(f"\nKopiere {len(PUBLISH_FILES)} Datei(en) {SOURCE_DIR} → {TARGET_DIR}")
    for name in PUBLISH_FILES:
        src = SOURCE_DIR / name
        dst = TARGET_DIR / name
        if not src.exists():
            print(f"  WARN: {src} existiert nicht — uebersprungen")
            continue
        if dry_run:
            print(f"  [dry-run] copy {name}")
            continue
        shutil.copy2(src, dst)
        print(f"  ✓ {name}")


def git_publish(message: str, dry_run: bool):
    """git add + commit + push."""
    print(f"\nCommit + Push in {TARGET_DIR}")
    if dry_run:
        print(f"  [dry-run] would: git add . ; git commit -m {message!r} ; git push")
        return
    run(["git", "add", "."], cwd=TARGET_DIR)
    status = run(["git", "status", "--porcelain"], cwd=TARGET_DIR)
    if not status.stdout.strip():
        print("  Keine Änderungen — Push uebersprungen.")
        return
    run(["git", "commit", "-m", message], cwd=TARGET_DIR)
    run(["git", "push"], cwd=TARGET_DIR)
    print("\n✓ Publiziert. Live nach ~1 Min unter:")
    print("  https://philippasigl.github.io/dz-wiki/")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-m", "--message", default=None,
                   help="Commit-Message (default: 'Update <timestamp>')")
    p.add_argument("--dry-run", action="store_true",
                   help="zeigt nur, was passieren wuerde — kein Schreiben/Pushen")
    args = p.parse_args()

    msg = args.message or f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    if not SOURCE_DIR.exists():
        print(f"FEHLER: {SOURCE_DIR} existiert nicht.", file=sys.stderr)
        return 1

    ensure_target(args.dry_run)
    copy_files(args.dry_run)
    git_publish(msg, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
