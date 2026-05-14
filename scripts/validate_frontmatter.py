#!/usr/bin/env python3
"""
Validiert das YAML-Frontmatter aller Publikations-Markdown-Dateien
gegen schemas/frontmatter.schema.json.

Verwendung:
    python scripts/validate_frontmatter.py
    python scripts/validate_frontmatter.py --strict   # Exit 1 bei Fehlern
    python scripts/validate_frontmatter.py --only-missing format
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCHEMA_FILE = PROJECT_ROOT / "schemas" / "frontmatter.schema.json"
DEFAULT_DOCS_DIR = PROJECT_ROOT / "wiki" / "publikationen"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def load_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, "kein YAML-Frontmatter gefunden"
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return None, f"YAML-Parse-Fehler: {e}"
    return data, None


def normalize_dates(data: dict) -> dict:
    """date kann als YAML-date geparst werden; Schema erwartet String."""
    import datetime
    out = dict(data)
    if isinstance(out.get("date"), (datetime.date, datetime.datetime)):
        out["date"] = out["date"].strftime("%Y-%m-%d")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1, wenn Fehler vorliegen")
    parser.add_argument("--only-missing", metavar="FIELD",
                        help="Nur Dateien anzeigen, denen FIELD fehlt")
    parser.add_argument("--path", default=str(DEFAULT_DOCS_DIR),
                        help=f"Verzeichnis mit .md-Dateien (Default: {DEFAULT_DOCS_DIR})")
    args = parser.parse_args()
    docs_dir = Path(args.path)

    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    files = sorted(docs_dir.glob("*.md"))
    if not files:
        print(f"Keine Markdown-Dateien in {docs_dir}")
        return 0
    print(f"Pruefe {len(files)} Dateien in {docs_dir}")

    total = len(files)
    ok = 0
    ignored = 0
    errors_by_field = {}
    file_errors = []

    for f in files:
        data, parse_err = load_frontmatter(f)
        if parse_err:
            file_errors.append((f, [parse_err]))
            errors_by_field.setdefault("(parse)", []).append(f.name)
            continue

        if str(data.get("ignore", "")).lower() in ("yes", "true"):
            ignored += 1
            continue

        data = normalize_dates(data)
        errs = sorted(validator.iter_errors(data), key=lambda e: e.path)

        if args.only_missing:
            errs = [e for e in errs
                    if e.validator == "required"
                    and args.only_missing in e.message]

        if not errs:
            ok += 1
            continue

        msgs = []
        for e in errs:
            field = ".".join(str(p) for p in e.absolute_path) or e.validator
            if e.validator == "required":
                missing = re.search(r"'([^']+)' is a required property", e.message)
                if missing:
                    field = missing.group(1)
            errors_by_field.setdefault(field, []).append(f.name)
            msgs.append(f"  - [{field}] {e.message}")
        file_errors.append((f, msgs))

    # Ausgabe
    if file_errors and not args.only_missing:
        print(f"=== {len(file_errors)} Datei(en) mit Fehlern ===\n")
        for f, msgs in file_errors[:20]:
            print(f"FAIL  {f.name}")
            for m in msgs:
                print(m)
        if len(file_errors) > 20:
            print(f"\n... und {len(file_errors) - 20} weitere\n")

    print("\n=== Zusammenfassung pro Feld ===")
    for field, fnames in sorted(errors_by_field.items(), key=lambda x: -len(x[1])):
        print(f"  {field}: {len(fnames)} Datei(en)")

    print(f"\n{ok}/{total} Dateien valide  |  {ignored} ignoriert  |  {len(file_errors)} mit Fehlern")

    if args.only_missing:
        print(f"\nDateien ohne '{args.only_missing}':")
        for fname in errors_by_field.get(args.only_missing, []):
            print(f"  {fname}")

    return 1 if args.strict and file_errors else 0


if __name__ == "__main__":
    sys.exit(main())
