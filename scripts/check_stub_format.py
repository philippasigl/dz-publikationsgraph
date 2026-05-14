#!/usr/bin/env python3
"""
Validiert dass eine .md ein DZ-Wiki-Stub im Sollformat ist.

Erwartet:
  - Frontmatter (validiert gegen schemas/frontmatter.schema.json)
  - Body <= MAX_BODY_WORDS Woerter (default 500)
  - Section '## Kernthesen' mit 3-5 Bullet-Points
  - Section '## Schlussfolgerungen' mit mind. 1 Bullet
  - Section '## Zahlen' optional, aber wenn vorhanden: muss eine Markdown-Tabelle enthalten

Ignored .mds (`ignore: yes`) werden uebersprungen.

Verwendung:
    python scripts/check_stub_format.py wiki/publikationen/<datei>.md
    python scripts/check_stub_format.py wiki/publikationen/        # alle .mds im Dir
    python scripts/check_stub_format.py --strict ...               # Exit 1 bei Fehlern
"""

import argparse
import io
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).parent.parent
SCHEMA_FILE = ROOT / "schemas" / "frontmatter.schema.json"

MAX_BODY_WORDS = 500
MIN_KERNTHESEN = 3
MAX_KERNTHESEN = 5
MIN_SCHLUSSFOLGERUNGEN = 1

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---(.*)", re.S)
BULLET_RE = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
TABLE_ROW_RE = re.compile(r"^\s*\|.+\|.+\|\s*$", re.MULTILINE)


def parse_md(path: Path):
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text, "kein Frontmatter-Block"
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return None, text, f"YAML-Parse-Fehler: {e}"
    return fm, m.group(2).strip(), None


def section_body(body: str, heading: str) -> str | None:
    """Extract text between '## <heading>' and next '##' (or end)."""
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
                         re.MULTILINE | re.DOTALL)
    m = pattern.search(body)
    return m.group(1).strip() if m else None


def count_bullets(section: str) -> int:
    return len(BULLET_RE.findall(section))


def check_file(path: Path, validator: Draft7Validator) -> tuple[str, list[str]]:
    """Returns ('OK'|'WARN'|'FAIL'|'SKIP', list of messages)."""
    fm, body, err = parse_md(path)
    if err:
        return "FAIL", [err]

    if str(fm.get("ignore", "")).lower() in ("yes", "true"):
        return "SKIP", ["ignore: yes"]

    issues: list[str] = []

    # 1. Frontmatter against schema
    import datetime
    fm_v = dict(fm)
    if isinstance(fm_v.get("date"), (datetime.date, datetime.datetime)):
        fm_v["date"] = fm_v["date"].strftime("%Y-%m-%d")
    for e in validator.iter_errors(fm_v):
        field = ".".join(str(p) for p in e.absolute_path) or e.validator
        issues.append(f"FM/{field}: {e.message}")

    # 2. Body length
    words = len(body.split())
    if words > MAX_BODY_WORDS:
        issues.append(f"body: {words} Woerter (>{MAX_BODY_WORDS}) — Rohkonvertierung, kein Stub")

    # 3. Required section: Kernthesen
    kt = section_body(body, "Kernthesen")
    if kt is None:
        issues.append("Section '## Kernthesen' fehlt")
    else:
        n = count_bullets(kt)
        if n < MIN_KERNTHESEN:
            issues.append(f"## Kernthesen: nur {n} Bullets (Soll: {MIN_KERNTHESEN}-{MAX_KERNTHESEN})")
        elif n > MAX_KERNTHESEN:
            issues.append(f"## Kernthesen: {n} Bullets (Soll: {MIN_KERNTHESEN}-{MAX_KERNTHESEN})")

    # 4. Required section: Schlussfolgerungen
    sf = section_body(body, "Schlussfolgerungen")
    if sf is None:
        issues.append("Section '## Schlussfolgerungen' fehlt")
    else:
        n = count_bullets(sf)
        if n < MIN_SCHLUSSFOLGERUNGEN:
            issues.append(f"## Schlussfolgerungen: nur {n} Bullets (mind. {MIN_SCHLUSSFOLGERUNGEN})")

    # 5. Optional section: Zahlen — wenn vorhanden, muss eine Tabelle drinstecken
    za = section_body(body, "Zahlen")
    if za is not None and not TABLE_ROW_RE.search(za):
        issues.append("## Zahlen vorhanden, aber keine Markdown-Tabelle")

    if not issues:
        return "OK", [f"valider Stub ({words} Woerter)"]
    # FAIL if critical fields/sections missing, WARN otherwise
    critical = any(
        "fehlt" in m or "FM/" in m or "Rohkonvertierung" in m
        for m in issues
    )
    return ("FAIL" if critical else "WARN"), issues


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", type=Path, help="Datei oder Verzeichnis")
    p.add_argument("--strict", action="store_true", help="Exit 1 bei Fehlern")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="nur Fehler/Warnungen zeigen, nicht OK/SKIP")
    args = p.parse_args()

    if not args.path.exists():
        print(f"FEHLER: {args.path} existiert nicht", file=sys.stderr)
        return 1

    files = sorted(args.path.glob("*.md")) if args.path.is_dir() else [args.path]
    if not files:
        print(f"Keine .md-Dateien in {args.path}", file=sys.stderr)
        return 1

    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    counts = {"OK": 0, "WARN": 0, "FAIL": 0, "SKIP": 0}
    for f in files:
        status, msgs = check_file(f, validator)
        counts[status] += 1
        if args.quiet and status in ("OK", "SKIP"):
            continue
        print(f"[{status}] {f.name}")
        for m in msgs:
            print(f"    - {m}")

    print()
    print(f"OK:   {counts['OK']}")
    print(f"WARN: {counts['WARN']}")
    print(f"FAIL: {counts['FAIL']}")
    print(f"SKIP: {counts['SKIP']}")

    return 1 if args.strict and (counts['FAIL'] > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
