#!/usr/bin/env python3
"""
Verifiziert dass alle Zahlen in `## Zahlen` eines Stubs auch im konvertierten
PDF-Text vorkommen. Schuetzt vor Zahlen-Halluzination beim Strukturieren.

Verwendung:
    python scripts/check_stub_numbers.py <stub.md> <source.pdf>
    python scripts/check_stub_numbers.py <stub.md> --converted <pre_converted.md>

Vergleichsstrategie:
  - Aus der `## Zahlen`-Tabelle des Stubs werden alle numerischen Sequenzen
    (Form: \\d+[.,]\\d+ ... mehrfach) extrahiert.
  - Trennzeichen (Punkte, Kommas in Tausendern UND Dezimalstellen) werden
    fuer den Vergleich entfernt; verglichen werden reine Ziffernfolgen.
  - Eine Ziffernfolge gilt als gefunden, wenn sie als Substring im
    normalisierten PDF-Text vorkommt.
  - Sequenzen mit weniger als 2 Ziffern werden ignoriert (zu viele
    Zufallstreffer).

Output:
  - Pro Zelle in der Zahlen-Tabelle: OK oder WARN mit Liste fehlender Zahlen
  - Exit 1 bei `--strict` und mindestens einer fehlenden Zahl.
"""

import argparse
import io
import re
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
MIN_DIGITS = 2  # ignore short numbers (too many random hits)
MARKITDOWN_TIMEOUT = 120


def digits_only(s: str) -> str:
    return re.sub(r"[^\d]", "", s)


def extract_numbers(s: str) -> list[str]:
    """All number-like substrings, normalized to digits-only, minimum length."""
    out = []
    for raw in NUM_RE.findall(s):
        d = digits_only(raw)
        if len(d) >= MIN_DIGITS:
            out.append(d)
    return out


def convert_pdf(pdf: Path) -> str:
    """Run markitdown, return raw stdout."""
    result = subprocess.run(
        ["markitdown", str(pdf)],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=MARKITDOWN_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"markitdown failed: {result.stderr}")
    return result.stdout


def parse_zahlen_table(stub_text: str) -> list[tuple[str, str]]:
    """Returns list of (label, value) from ## Zahlen table. Skips header/sep rows."""
    m = re.search(r"^##\s+Zahlen\s*$(.*?)(?=^##\s|\Z)", stub_text, re.MULTILINE | re.DOTALL)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        s = line.strip()
        if not s.startswith("|") or not s.endswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        # Skip the markdown table header separator (|---|---|)
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        # Skip the actual header row (label like "Kennzahl")
        if cells[0].lower() in {"kennzahl", "metric", "indicator"}:
            continue
        rows.append((cells[0], " | ".join(cells[1:])))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("stub", type=Path, help="Pfad zur Stub-.md")
    p.add_argument("pdf", type=Path, nargs="?", help="Pfad zur Quell-PDF")
    p.add_argument("--converted", type=Path,
                   help="Pre-konvertierte .md (statt PDF on-the-fly)")
    p.add_argument("--strict", action="store_true",
                   help="Exit 1 bei mindestens einer fehlenden Zahl")
    args = p.parse_args()

    if not args.stub.exists():
        print(f"FEHLER: Stub {args.stub} existiert nicht", file=sys.stderr)
        return 1

    # Get source text
    if args.converted:
        source_text = args.converted.read_text(encoding="utf-8")
    elif args.pdf:
        if not args.pdf.exists():
            print(f"FEHLER: PDF {args.pdf} existiert nicht", file=sys.stderr)
            return 1
        try:
            source_text = convert_pdf(args.pdf)
        except (subprocess.TimeoutExpired, RuntimeError, FileNotFoundError) as e:
            print(f"FEHLER bei Konvertierung: {e}", file=sys.stderr)
            return 1
    else:
        print("FEHLER: Entweder PDF oder --converted angeben", file=sys.stderr)
        return 1

    source_digits = digits_only(source_text)

    stub_text = args.stub.read_text(encoding="utf-8")
    rows = parse_zahlen_table(stub_text)
    if not rows:
        print(f"WARN: keine `## Zahlen`-Tabelle gefunden in {args.stub.name}")
        return 0

    total_nums = 0
    missing_total = 0
    print(f"Pruefe Zahlen aus {args.stub.name} gegen {args.pdf or args.converted}")
    print()
    for label, value in rows:
        nums = extract_numbers(value)
        if not nums:
            continue
        missing = [n for n in nums if n not in source_digits]
        total_nums += len(nums)
        missing_total += len(missing)
        status = "OK  " if not missing else "WARN"
        print(f"  [{status}] {label}: {value}")
        for m in missing:
            print(f"           -> nicht im PDF: '{m}'")

    print()
    print(f"Geprueft: {total_nums} Zahlen, {missing_total} nicht gefunden")
    if missing_total > 0:
        print()
        print("HINWEIS: Fehlende Zahlen koennen echte Hallucination sein ODER")
        print("durch PDF-Konvertierungs-Mangel verloren gegangen sein.")
        print("Manuell gegen Quell-PDF pruefen, bevor der Stub als final gilt.")

    return 1 if args.strict and missing_total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
