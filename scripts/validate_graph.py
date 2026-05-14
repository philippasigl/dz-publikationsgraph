#!/usr/bin/env python3
"""
Validiert den Publikations-Graphen.

Verwendung:
    python scripts/validate_graph.py

Prüft:
- JSON-Syntax valide
- Alle Edge-Referenzen zeigen auf existierende Nodes
- Pflichtfelder vorhanden
- Keine Duplikate
- Cluster sind gültig
"""

import json
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
GRAPH_FILE = PROJECT_ROOT / "publikationsgraph" / "data.json"

VALID_CLUSTER_B = {"fiskalpolitik", "haushalt", "geldpolitik und anleihemärkte", "infra", "wirtschaftspolitik", "makro", "ausland"}
VALID_CONFIDENCE = {"hoch", "mittel", "niedrig"}
REQUIRED_NODE_FIELDS = ["id", "title", "date", "clusterA", "clusterB", "authors"]
REQUIRED_EDGE_FIELDS = ["from", "to", "label", "confidence"]


def load_graph() -> dict:
    """Lädt und parst den Graphen."""
    content = GRAPH_FILE.read_text(encoding='utf-8')
    return json.loads(content)


def validate_nodes(nodes: list, valid_cluster_a: set) -> list:
    """Validiert alle Nodes."""
    errors = []
    ids = []

    for i, node in enumerate(nodes):
        node_id = node.get('id', f'<index {i}>')

        # Pflichtfelder
        for field in REQUIRED_NODE_FIELDS:
            if field not in node:
                errors.append(f"Node '{node_id}': Pflichtfeld '{field}' fehlt")
            elif not node[field]:
                errors.append(f"Node '{node_id}': Feld '{field}' ist leer")

        # clusterB (Finanzierungstyp) gegen kanonische 7 Cluster
        cluster_b = node.get('clusterB')
        if cluster_b and cluster_b not in VALID_CLUSTER_B:
            errors.append(f"Node '{node_id}': Ungültiger clusterB '{cluster_b}'")

        # clusterA (Thema) gegen Definitionen in graph.clusters.A.items
        cluster_a = node.get('clusterA')
        if cluster_a and valid_cluster_a and cluster_a not in valid_cluster_a:
            errors.append(f"Node '{node_id}': Ungültiger clusterA '{cluster_a}' (nicht in clusters.A.items definiert)")

        # ID sammeln für Duplikat-Check
        if 'id' in node:
            ids.append(node['id'])

    # Duplikate
    id_counts = Counter(ids)
    for node_id, count in id_counts.items():
        if count > 1:
            errors.append(f"Duplikat: Node-ID '{node_id}' kommt {count}x vor")

    return errors


def validate_edges(edges: list, node_ids: set, date_by_id: dict) -> tuple[list, list]:
    """Validiert alle Edges. Returns (errors, warnings)."""
    errors = []
    warnings = []

    for i, edge in enumerate(edges):
        from_id = edge.get('from')
        to_id = edge.get('to')
        label = edge.get('label', '<kein Label>')
        conf = edge.get('confidence')

        if not from_id:
            errors.append(f"Edge {i}: 'from' fehlt")
        elif from_id not in node_ids:
            errors.append(f"Edge '{from_id}' -> '...': 'from' verweist auf nicht existierenden Node")

        if not to_id:
            errors.append(f"Edge {i}: 'to' fehlt")
        elif to_id not in node_ids:
            errors.append(f"Edge '...' -> '{to_id}': 'to' verweist auf nicht existierenden Node (Label: {label})")

        # Confidence: Pflichtfeld
        if not conf:
            errors.append(f"Edge '{from_id}' -> '{to_id}': 'confidence' fehlt (erlaubt: {sorted(VALID_CONFIDENCE)})")
        elif conf not in VALID_CONFIDENCE:
            errors.append(f"Edge '{from_id}' -> '{to_id}': ungueltige confidence '{conf}'")

        # Reverse-Chronology-Warnung (nicht-blockierend; Uebersetzungen
        # sollten via ignore:yes ausgefiltert sein bevor sie hier landen)
        if from_id and to_id and from_id in date_by_id and to_id in date_by_id:
            fd, td = date_by_id[from_id], date_by_id[to_id]
            if fd and td and fd < td:
                warnings.append(f"Reverse-Chronology: {from_id} ({fd}) -> {to_id} ({td}) — neueres Papier sollte from sein")

    return errors, warnings


def validate_graph():
    """Hauptvalidierung."""
    print(f"Validiere {GRAPH_FILE}...")
    print()

    # JSON laden
    try:
        graph = load_graph()
    except json.JSONDecodeError as e:
        print(f"FEHLER: Ungültiges JSON - {e}")
        return False
    except FileNotFoundError:
        print(f"FEHLER: Datei nicht gefunden - {GRAPH_FILE}")
        return False

    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])

    print(f"Gefunden: {len(nodes)} Nodes, {len(edges)} Edges")
    print()

    # Validieren
    all_errors = []

    valid_cluster_a = set(graph.get('clusters', {}).get('A', {}).get('items', {}).keys())
    node_errors = validate_nodes(nodes, valid_cluster_a)
    all_errors.extend(node_errors)

    node_ids = {node['id'] for node in nodes if 'id' in node}
    date_by_id = {node['id']: node.get('date', '') for node in nodes if 'id' in node}
    edge_errors, edge_warnings = validate_edges(edges, node_ids, date_by_id)
    all_errors.extend(edge_errors)

    # Ergebnis
    if all_errors:
        print(f"FEHLER: {len(all_errors)} Probleme gefunden:")
        print()
        for err in all_errors:
            print(f"  - {err}")
        print()
        return False

    print("OK: Keine Fehler gefunden.")

    if edge_warnings:
        print()
        print(f"WARNUNGEN: {len(edge_warnings)}")
        for w in edge_warnings:
            print(f"  - {w}")

    # Statistiken
    clusters_b = Counter(node.get('clusterB', 'unknown') for node in nodes)
    print()
    print("clusterB-Verteilung (Finanzierungstyp):")
    for cluster, count in sorted(clusters_b.items(), key=lambda x: -x[1]):
        print(f"  {cluster}: {count}")

    clusters_a = Counter(node.get('clusterA', 'unknown') for node in nodes)
    print()
    print("clusterA-Verteilung (Thema):")
    for cluster, count in sorted(clusters_a.items(), key=lambda x: -x[1]):
        print(f"  {cluster}: {count}")

    confidences = Counter(edge.get('confidence', '?') for edge in edges)
    print()
    print("Konfidenz-Verteilung:")
    for c, n in sorted(confidences.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")

    return True


if __name__ == '__main__':
    success = validate_graph()
    sys.exit(0 if success else 1)
