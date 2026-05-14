#!/usr/bin/env python3
"""
Fügt eine Publikation zum Publikations-Graphen hinzu.

Verwendung:
    python scripts/add_to_graph.py wiki/publikationen/mein-slug.md

Das Script:
- Liest das YAML-Frontmatter der Markdown-Datei
- Erstellt einen neuen Node in publikationsgraph/data.json
- Prüft auf Duplikate
"""

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Fehler: PyYAML nicht installiert. Bitte 'pip install pyyaml' ausführen.")
    sys.exit(1)


SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
GRAPH_FILE = PROJECT_ROOT / "publikationsgraph" / "data.json"

VALID_CLUSTERS = {"fiskalpolitik", "haushalt", "geldpolitik", "infra", "wirtschaftspolitik", "makro", "ausland"}


def extract_frontmatter(md_path: Path) -> dict:
    """Extrahiert YAML-Frontmatter aus Markdown-Datei."""
    content = md_path.read_text(encoding='utf-8')

    # Frontmatter zwischen --- ... ---
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        raise ValueError(f"Kein Frontmatter gefunden in {md_path}")

    frontmatter = yaml.safe_load(match.group(1))
    return frontmatter


def validate_frontmatter(fm: dict, slug: str) -> list:
    """Prüft Frontmatter auf Vollständigkeit."""
    errors = []

    required = ['title', 'date', 'authors', 'cluster']
    for field in required:
        if field not in fm or not fm[field]:
            errors.append(f"Pflichtfeld '{field}' fehlt")

    if 'cluster' in fm and fm['cluster'] not in VALID_CLUSTERS:
        errors.append(f"Ungültiger Cluster '{fm['cluster']}'. Erlaubt: {', '.join(VALID_CLUSTERS)}")

    if 'date' in fm:
        date_str = str(fm['date'])
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            errors.append(f"Datum '{date_str}' nicht im Format YYYY-MM-DD")

    if 'authors' in fm and not isinstance(fm['authors'], list):
        errors.append("'authors' muss eine Liste sein")

    if 'tags' in fm and not isinstance(fm['tags'], list):
        errors.append("'tags' muss eine Liste sein")

    return errors


def load_graph() -> dict:
    """Lädt den Publikations-Graphen."""
    if not GRAPH_FILE.exists():
        return {"nodes": [], "edges": [], "clusters": {}}

    return json.loads(GRAPH_FILE.read_text(encoding='utf-8'))


def save_graph(data: dict):
    """Speichert den Publikations-Graphen."""
    GRAPH_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


def add_node(graph: dict, slug: str, frontmatter: dict) -> bool:
    """Fügt einen neuen Node hinzu. Gibt False zurück wenn Duplikat."""
    # Duplikat-Check
    existing_ids = {node['id'] for node in graph['nodes']}
    if slug in existing_ids:
        print(f"Node '{slug}' existiert bereits.")
        return False

    node = {
        "id": slug,
        "title": frontmatter['title'],
        "date": str(frontmatter['date']),
        "cluster": frontmatter['cluster'],
        "authors": frontmatter['authors'],
        "tags": frontmatter.get('tags', [])
    }

    graph['nodes'].append(node)
    return True


def main():
    if len(sys.argv) < 2:
        print("Verwendung: python add_to_graph.py <pfad-zu-markdown>")
        print("Beispiel:   python add_to_graph.py wiki/publikationen/mein-artikel.md")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"Fehler: Datei nicht gefunden: {md_path}")
        sys.exit(1)

    # Slug aus Dateiname
    slug = md_path.stem

    # Frontmatter lesen
    try:
        frontmatter = extract_frontmatter(md_path)
    except ValueError as e:
        print(f"Fehler: {e}")
        sys.exit(1)

    # Validieren
    errors = validate_frontmatter(frontmatter, slug)
    if errors:
        print("Validierungsfehler:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    # Graph laden und Node hinzufügen
    graph = load_graph()

    if add_node(graph, slug, frontmatter):
        save_graph(graph)
        print(f"Node '{slug}' hinzugefügt.")
        print(f"  Titel:   {frontmatter['title']}")
        print(f"  Datum:   {frontmatter['date']}")
        print(f"  Cluster: {frontmatter['cluster']}")
        print(f"  Autoren: {', '.join(frontmatter['authors'])}")
        print()
        print("Vergiss nicht, Edges manuell hinzuzufügen!")
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
