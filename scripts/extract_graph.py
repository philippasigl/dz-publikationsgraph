#!/usr/bin/env python3
"""
Extract publication graph from wiki markdown files.

Nodes kommen aus den .md-Frontmatters in wiki/publikationen/.
Edges kommen aus publikationsgraph/edges.csv (manuell kuratierte Quelle der
Wahrheit). Falls die CSV fehlt, wird ein leerer Edge-Satz ausgegeben und ein
Hinweis gedruckt.

Aufruf:
    python scripts/extract_graph.py
"""

import csv
import io
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from slugify import slugify  # noqa: E402, F401  (re-exported for downstream tools)

# UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).parent.parent
WIKI_DIR = ROOT / "wiki" / "publikationen"
NODES_CSV = ROOT / "publikationsgraph" / "nodes.csv"
EDGES_CSV = ROOT / "publikationsgraph" / "edges.csv"
OUTPUT = ROOT / "publikationsgraph" / "data.json"

# Palette fuer clusterA (Themen, 15 distinct). Im wk-Stil: gedaempfte Toene,
# unterscheidbar genug fuer eine Legende.
CLUSTER_A_PALETTE = {
    # Innerhalb einer Hue-Familie variieren wir Helligkeit deutlich, damit
    # benachbarte Cluster im selben Spektrum klar unterscheidbar bleiben.
    # Mittlere Helligkeit (~45–55%), gedaempfte Saettigung — gleich freundliches
    # Niveau wie clusterB, keine sehr dunklen Toene mehr.
    "Finanzpolitik":                  "#3a5a7a",  # mid slate-blau (umfasst Steuern, Kommunen, Investitionen)
    "Wirtschaft":                     "#4a8aaa",  # mid teal-blau
    "Energie":                        "#4a8a6a",  # mid forest green
    "Dekarbonisierung":               "#8ac05a",  # soft leaf
    "Verkehr":                        "#c0b04a",  # soft olive
    "Bildung":                        "#d4a850",  # gold
    "Wohnen":                         "#d48a6a",  # soft warm orange
    "Sozialstaat":                    "#d68aaa",  # soft rose-pink
    "Souveränität":                   "#b05a5a",  # soft mid red
    "Arbeitsmarkt":                   "#5ab0d0",  # soft sky-cyan
    "geldpolitik und anleihemärkte":  "#8a6aaa",  # soft plum
}

CLUSTER_B_PALETTE = {
    "fiskalpolitik":                  "#5a3a7a",  # deep purple
    "haushalt":                       "#9b4a3a",  # terracotta (= wk staat)
    "geldpolitik und anleihemärkte":  "#7a8a3a",  # olive
    "infra":                          "#3a8a8a",  # teal-cyan
    "wirtschaftspolitik":             "#2e6b5e",  # forest green (= wk markt)
    "makro":                          "#c89438",  # warm amber
    "ausland":                        "#5c6b7a",  # slate (= wk ausland)
}

CLUSTER_B_LABELS = {
    "fiskalpolitik": "Fiskalpolitik",
    "haushalt": "Haushalt",
    "geldpolitik und anleihemärkte": "Geldpolitik & Anleihemärkte",
    "infra": "Infrastruktur",
    "wirtschaftspolitik": "Wirtschaftspolitik",
    "makro": "Makro",
    "ausland": "Ausland",
}

# Display-Labels für clusterA (nur Abweichungen vom Raw-Wert).
CLUSTER_A_LABELS = {
    "geldpolitik und anleihemärkte": "Geldpolitik & Anleihemärkte",
}

# Vertikale Reihenfolge (oben → unten) für die Y-Bänder im Graph.
# Wert nicht in der Liste? → wird unten angehaengt.
CLUSTER_A_ORDER = [
    "Finanzpolitik",
    "Bildung",
    "Sozialstaat",
    "Wohnen",
    "Verkehr",
    "Energie",
    "Dekarbonisierung",
    "Arbeitsmarkt",
    "Wirtschaft",
    "Souveränität",
    "geldpolitik und anleihemärkte",
]

CLUSTER_B_ORDER = [
    "fiskalpolitik",
    "ausland",
    "geldpolitik und anleihemärkte",
    "haushalt",
    "infra",
    "wirtschaftspolitik",
    "makro",
]


def order_by(values, canonical):
    """Sort values: canonical order first, unknown values appended alphabetically."""
    known = [v for v in canonical if v in values]
    unknown = sorted(v for v in values if v not in set(canonical))
    return known + unknown


def parse_date(s: str) -> str:
    """Returns YYYY-MM-DD. Accepts YYYY-MM-DD or DD.MM.YYYY."""
    s = (s or "").strip()
    if not s:
        return ""
    if "." in s:
        parts = s.split(".")
        if len(parts) == 3 and len(parts[2]) == 4:
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return s


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}
    return {}


def main():
    # Load .md frontmatter once (Authors, tags, urls, summary)
    md_data = {}
    for md_file in WIKI_DIR.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        fm = extract_frontmatter(content)
        if not fm.get("title"):
            continue
        if str(fm.get("ignore", "")).lower() in ("yes", "true"):
            continue
        md_data[md_file.stem] = {
            "title": fm.get("title", md_file.stem),
            "date": str(fm.get("date", "")),
            "authors": fm.get("authors", []),
            "tags": fm.get("tags", []),
            "pdf_url": fm.get("pdf_url", ""),
            "web_url": fm.get("web_url", ""),
            "summary": fm.get("summary", ""),
        }

    # Nodes-Quelle: nodes.csv (enthaelt clusterA + clusterB)
    publications = []
    if NODES_CSV.exists():
        with NODES_CSV.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f, delimiter=";"):
                node_id = row["id"].strip()
                if not node_id or node_id not in md_data:
                    continue
                md = md_data[node_id]
                publications.append({
                    "id": node_id,
                    "title": md["title"],
                    "date": md["date"] or parse_date(row.get("datum", "")),
                    "clusterA": row.get("clusterA", "").strip() or "Sonstiges",
                    "clusterB": row.get("clusterB", "").strip() or "unknown",
                    "authors": md["authors"],
                    "tags": md["tags"],
                    "pdf_url": md["pdf_url"],
                    "web_url": md["web_url"],
                    "summary": md["summary"],
                })
    else:
        print(f"WARN: {NODES_CSV} fehlt — fallback auf .md cluster only.")
        for nid, md in md_data.items():
            publications.append({
                "id": nid,
                **md,
                "clusterA": "Sonstiges",
                "clusterB": "unknown",
            })

    node_ids = {p["id"] for p in publications}

    # --- Edges: read manually-curated edges.csv ---
    edges = []
    invalid = []
    if EDGES_CSV.exists():
        with EDGES_CSV.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f, delimiter=";"):
                src = row["von"].strip()
                tgt = row["nach"].strip()
                if not src or not tgt:
                    continue
                if src not in node_ids or tgt not in node_ids:
                    invalid.append((src, tgt))
                    continue
                if src == tgt:
                    continue
                edges.append({
                    "from": src,
                    "to": tgt,
                    "label": row.get("label", "").strip(),
                    "confidence": (row.get("konfidenz", "").strip() or "hoch"),
                })
    else:
        print(f"WARN: {EDGES_CSV} fehlt — Edges-Liste ist leer.")

    # Cluster-Dimensionen: clusterA = Themen, clusterB = Policy.
    # Reihenfolge folgt CLUSTER_*_ORDER (oben → unten in der Y-Achse).
    used_a = {p["clusterA"] for p in publications}
    used_b = {p["clusterB"] for p in publications}

    cluster_a = {}
    for theme in order_by(used_a, CLUSTER_A_ORDER):
        cluster_a[theme] = {
            "label": CLUSTER_A_LABELS.get(theme, theme),
            "color": CLUSTER_A_PALETTE.get(theme, "#9090a0"),
        }
    cluster_b = {}
    for c in order_by(used_b, CLUSTER_B_ORDER):
        cluster_b[c] = {
            "label": CLUSTER_B_LABELS.get(c, c),
            "color": CLUSTER_B_PALETTE.get(c, "#9090a0"),
        }

    graph = {
        "nodes": publications,
        "edges": edges,
        "clusters": {
            "A": {
                "label": "Themen",
                "items": cluster_a,
            },
            "B": {
                "label": "Finanzierungstyp",
                "items": cluster_b,
            },
        },
    }

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Extracted {len(publications)} publications, {len(edges)} edges")
    print(f"Output: {OUTPUT}")
    print()
    for dim_key, dim_label, field in [("A", "Themen", "clusterA"), ("B", "Policy", "clusterB")]:
        print(f"\nPublikationen nach {dim_label} (cluster{dim_key}):")
        by = {}
        for p in publications:
            by[p[field]] = by.get(p[field], 0) + 1
        for c, n in sorted(by.items(), key=lambda x: -x[1]):
            print(f"  {c}: {n}")

    if invalid:
        print(f"\nWARN: {len(invalid)} Edges in edges.csv haben unbekannte Slugs (uebersprungen):")
        for s, t in invalid[:10]:
            print(f"  {s} -> {t}")


if __name__ == "__main__":
    main()
