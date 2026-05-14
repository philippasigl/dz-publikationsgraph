#!/usr/bin/env python3
"""
Generiert URL-Slugs aus deutschen Titeln.
Cross-Platform (Windows/Mac/Linux).

Verwendung:
    python scripts/slugify.py "Titel der Publikation"
    python scripts/slugify.py "Warum die Konjunkturkomponente ihren Zweck nicht mehr erfüllt"
    # Ausgabe: warum-die-konjunkturkomponente-ihren-zweck-nicht-mehr-erfuellt
"""

import re
import sys
import unicodedata

UMLAUT_MAP = {
    'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
    'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue',
    'ß': 'ss'
}

def slugify(text: str) -> str:
    """Konvertiert Text zu URL-Slug."""
    # Umlaute ersetzen
    for umlaut, replacement in UMLAUT_MAP.items():
        text = text.replace(umlaut, replacement)

    # Zu lowercase
    text = text.lower()

    # Unicode normalisieren und Akzente entfernen
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Alles außer Buchstaben und Zahlen durch Bindestriche ersetzen
    text = re.sub(r'[^a-z0-9]+', '-', text)

    # Mehrfache Bindestriche zusammenfassen
    text = re.sub(r'-+', '-', text)

    # Bindestriche am Anfang/Ende entfernen
    text = text.strip('-')

    return text


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Verwendung: python slugify.py \"Titel der Publikation\"")
        sys.exit(1)

    title = ' '.join(sys.argv[1:])
    slug = slugify(title)
    print(slug)
