#!/usr/bin/env python3
"""
PDF zu Markdown Konvertierungs-Pipeline
Nutzt markitdown und führt automatische Nachbearbeitung durch.
"""

import io
import re
import subprocess
import sys
from pathlib import Path

# UTF-8 stdout/stderr on Windows (no PYTHONIOENCODING prefix required)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Import cleanup functions
from cleanup_markdown import cleanup_markdown

MARKITDOWN_TIMEOUT = 300  # 5 min — komplexe lange PDFs koennen >120s brauchen


def convert_pdf(pdf_path: Path, output_dir: Path) -> tuple[bool, str, Path]:
    """
    Konvertiert eine PDF zu Markdown.

    Returns:
        Tuple[bool, str, Path]: (Erfolg, Nachricht, Ausgabepfad)
    """
    output_file = output_dir / f"{pdf_path.stem}.md"

    try:
        result = subprocess.run(
            ["markitdown", str(pdf_path)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=MARKITDOWN_TIMEOUT,
        )

        if result.returncode != 0:
            return False, f"markitdown Fehler: {result.stderr}", output_file

        if not result.stdout.strip():
            return False, "markitdown lieferte leere Ausgabe (PDF defekt oder Bild-Scan?)", output_file

        # Speichere Rohausgabe
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)

        return True, "Konvertiert", output_file

    except subprocess.TimeoutExpired:
        return False, f"Timeout (>{MARKITDOWN_TIMEOUT}s) bei Konvertierung", output_file
    except FileNotFoundError:
        return False, "markitdown nicht installiert (pip install markitdown)", output_file
    except Exception as e:
        return False, f"Fehler: {str(e)}", output_file


def cleanup_file(md_path: Path) -> tuple[bool, str, list[str]]:
    """
    Bereinigt eine Markdown-Datei.

    Returns:
        Tuple[bool, str, List[str]]: (Erfolg, Nachricht, Warnungen)
    """
    warnings = []

    try:
        with open(md_path, encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Cleanup durchführen
        cleaned = cleanup_markdown(content)

        # Speichern
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)

        # Qualitätsprüfung
        warnings = validate_markdown(cleaned, md_path.name)

        return True, "Bereinigt", warnings

    except Exception as e:
        return False, f"Fehler: {str(e)}", []


def validate_markdown(content: str, filename: str) -> list[str]:
    """
    Prüft Markdown auf verbleibende Probleme.

    Returns:
        List[str]: Liste von Warnungen
    """
    warnings = []
    lines = content.split('\n')

    # Suche nach verbleibenden Encoding-Problemen
    problem_patterns = [
        (r'[^\x00-\x7F]', "Nicht-ASCII-Zeichen"),  # Nicht unbedingt ein Problem
        (r'\b\w+fi\w+\b', "Mögliche fi-Ligatur"),
        (r'\b\w+fl\w+\b', "Mögliche fl-Ligatur"),
    ]

    # Spezifische bekannte Fehler
    known_errors = [
        ('Schifien', 'Schiffen'),
        ('Angrifis', 'Angriffs'),
        ('Angrifi', 'Angriff'),
        ('erklrt', 'erklärt'),
        ('Wertschpfung', 'Wertschöpfung'),
        ('unabhngig', 'unabhängig'),
        ('Mittelstndler', 'Mittelständler'),
        ('militrisch', 'militärisch'),
        ('Rohstofien', 'Rohstoffen'),
        ('Industriemaschiffnen', 'Industriemaschinen'),
        ('Werkzeugmaschiffnen', 'Werkzeugmaschinen'),
    ]

    for i, line in enumerate(lines, 1):
        for error, correct in known_errors:
            if error in line:
                warnings.append(f"Zeile {i}: '{error}' -> '{correct}'")

    # Prüfe ob Titel vorhanden
    if not content.strip():
        warnings.append("Datei ist leer")
    elif not any(line.startswith('#') for line in lines[:10]):
        # Kein Markdown-Header in den ersten 10 Zeilen
        if lines and lines[0].strip():
            # Erste Zeile als Titel vorschlagen
            pass  # Kein Problem, viele PDFs haben keinen expliziten Header

    return warnings


def detect_pdf_type(content: str) -> str:
    """
    Erkennt den PDF-Typ basierend auf Inhaltsindikatoren.

    Returns:
        str: 'website_printout' oder 'native_pdf'
    """
    indicators = {
        'website_printout': [
            r'\d+ von \d+',  # Seitenzahlen
            r'\d{2}\.\d{2}\.\d{4},\s*\d{2}:\d{2}',  # Timestamps
            r'https?://dezernatzukunft\.org',  # DZ URLs
            r'TEILE UNSERE INHALTE',
            r'Hat dir der Artikel gefallen',
        ],
        'native_pdf': []
    }

    website_score = sum(
        1 for pattern in indicators['website_printout']
        if re.search(pattern, content)
    )

    return 'website_printout' if website_score >= 2 else 'native_pdf'


def process_pdfs(input_path: Path, output_dir: Path = None) -> None:
    """Hauptfunktion: Verarbeitet PDFs."""

    # Bestimme Eingabedateien
    if input_path.is_file():
        if input_path.suffix.lower() != '.pdf':
            print(f"Fehler: {input_path} ist keine PDF-Datei")
            sys.exit(1)
        pdf_files = [input_path]
        base_dir = input_path.parent
    elif input_path.is_dir():
        pdf_files = list(input_path.glob('*.pdf'))
        base_dir = input_path
    else:
        print(f"Fehler: {input_path} existiert nicht")
        sys.exit(1)

    if not pdf_files:
        print("Keine PDF-Dateien gefunden.")
        sys.exit(0)

    # Ausgabeverzeichnis - immer auf absoluten Pfad aufloesen, damit unklar
    # ist, wo die Dateien landen
    if output_dir is None:
        output_dir = base_dir / 'markdown'
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("PDF zu Markdown Konvertierung")
    print(f"{'='*50}")
    print(f"Eingabe: {input_path.resolve()}")
    print(f"Ausgabe: {output_dir}    (absoluter Pfad)")
    print(f"Gefunden: {len(pdf_files)} PDF(s)")
    print()

    results = []

    for pdf_file in pdf_files:
        print(f"Verarbeite: {pdf_file.name}")

        # Schritt 1: Konvertieren
        success, msg, md_path = convert_pdf(pdf_file, output_dir)

        if not success:
            print(f"  [X] Konvertierung fehlgeschlagen: {msg}")
            results.append((pdf_file.name, 'error', msg, []))
            continue

        print("  [1/3] Konvertiert")

        # PDF-Typ erkennen
        with open(md_path, encoding='utf-8', errors='replace') as f:
            content = f.read()
        pdf_type = detect_pdf_type(content)
        print(f"  [2/3] Typ erkannt: {pdf_type.replace('_', ' ').title()}")

        # Schritt 2: Bereinigen
        success, msg, warnings = cleanup_file(md_path)

        if not success:
            print(f"  [X] Bereinigung fehlgeschlagen: {msg}")
            results.append((pdf_file.name, 'error', msg, []))
            continue

        print("  [3/3] Bereinigt")

        # Status bestimmen
        if warnings:
            status = 'warning'
            print(f"  [!] {len(warnings)} Warnung(en)")
            for w in warnings[:3]:
                print(f"      - {w}")
            if len(warnings) > 3:
                print(f"      ... und {len(warnings)-3} weitere")
        else:
            status = 'ok'
            print("  [OK] Erfolgreich")

        results.append((pdf_file.name, status, '', warnings))
        print()

    # Zusammenfassung
    print()
    print("Konvertierungsbericht")
    print("="*50)

    ok_count = sum(1 for r in results if r[1] == 'ok')
    warn_count = sum(1 for r in results if r[1] == 'warning')
    error_count = sum(1 for r in results if r[1] == 'error')

    print(f"Erfolgreich: {ok_count}")
    print(f"Mit Warnungen: {warn_count}")
    print(f"Fehler: {error_count}")
    print()

    if warn_count > 0:
        print("Dateien mit Warnungen:")
        for name, status, msg, warnings in results:
            if status == 'warning':
                print(f"  - {name}")
                for w in warnings:
                    print(f"    * {w}")
        print()

    if error_count > 0:
        print("Fehlgeschlagene Dateien:")
        for name, status, msg, warnings in results:
            if status == 'error':
                print(f"  - {name}: {msg}")
        print()

    print(f"Ausgabe gespeichert in: {output_dir}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Verwendung: python convert_pdf_to_markdown.py <pdf|ordner> [ausgabe-ordner]")
        print()
        print("Beispiele:")
        print("  python convert_pdf_to_markdown.py dokument.pdf")
        print("  python convert_pdf_to_markdown.py publikationen/")
        print("  python convert_pdf_to_markdown.py publikationen/ ausgabe/")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    process_pdfs(input_path, output_dir)
