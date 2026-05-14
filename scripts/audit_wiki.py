"""Auditiert die Themen- und Konzept-Abdeckung im Wiki.

Liest:
    publikationsgraph/nodes.csv  (clusterA, clusterB pro Paper)
    wiki/publikationen/*.md      (Frontmatter + Kernthesen)
    wiki/themen/*.md             (bestehende Themen-Hubs)
    wiki/konzepte/*.md           (bestehende Konzept-Seiten)

Schreibt:
    publikationsgraph/wiki-audit.json   (strukturiert, fuer den auto-wiki Skill)

Konsolen-Output:
    Themen-Lücken (Cluster ohne Hub-Seite oder Hub mit veraltetem Stand)
    Konzept-Kandidaten (recurring terms in Kernthesen)
    Veraltete Hubs (Themen-Seiten, die nicht alle relevanten Papers listen)

Aufruf:
    python scripts/audit_wiki.py            # Konsolen-Report
    python scripts/audit_wiki.py --json     # nur die JSON-Datei, kein Print
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
NODES_CSV = ROOT / "publikationsgraph" / "nodes.csv"
PUB_DIR = ROOT / "wiki" / "publikationen"
THEMEN_DIR = ROOT / "wiki" / "themen"
KONZ_DIR = ROOT / "wiki" / "konzepte"
OUTPUT = ROOT / "publikationsgraph" / "wiki-audit.json"


# Manuelle Zuordnung: welche bestehenden Themen-Slugs decken welche clusterA-Werte.
# Erweitern wenn neue Themen angelegt werden.
THEMA_TO_CLUSTER_A = {
    "bundeshaushalt":   ["Finanzpolitik"],
    "schuldenbremse":   ["Finanzpolitik"],
    "wohnungspolitik":  ["Wohnen"],
    "kitas":            ["Bildung"],
    "energiewende":     ["Energie", "Dekarbonisierung"],
    "geldpolitik":      ["geldpolitik und anleihemärkte"],
    "china":            ["Souveränität"],
    "wirtschaft":       ["Wirtschaft"],
    "arbeitsmarkt":     ["Arbeitsmarkt"],
    "verkehr":          ["Verkehr"],
    "sozialstaat":      ["Sozialstaat"],
}


def slugify(s: str) -> str:
    s = s.lower()
    repl = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
    for k, v in repl.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    return re.sub(r"\s+", "-", s).strip("-")


def parse_frontmatter(text: str) -> tuple[dict | None, str]:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return None, text[m.end():]


def load_nodes_csv() -> dict[str, dict]:
    """slug -> {clusterA, clusterB, datum, titel}"""
    out = {}
    if not NODES_CSV.exists():
        return out
    with NODES_CSV.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            sid = row.get("id", "").strip()
            if sid:
                out[sid] = row
    return out


def load_publications() -> dict[str, dict]:
    """slug -> {fm, body, kernthesen_text}"""
    out = {}
    for p in PUB_DIR.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if not fm:
            continue
        iv = fm.get("ignore")
        if iv is True or str(iv).strip().lower() == "yes":
            continue
        # Kernthesen-Block extrahieren fuer Term-Extraction
        m = re.search(r"## Kernthesen\s*\n(.*?)(\n## |\n# |$)", body, re.DOTALL)
        kern = m.group(1) if m else ""
        out[p.stem] = {"fm": fm, "body": body, "kern": kern}
    return out


def existing_themen() -> dict[str, dict]:
    out = {}
    if not THEMEN_DIR.exists():
        return out
    for p in THEMEN_DIR.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        wikilinks = re.findall(r"\[\[([^\]]+)\]\]", text)
        out[p.stem] = {
            "linked_pubs": [w.split("|")[0].strip() for w in wikilinks],
            "lines": text.count("\n") + 1,
            "has_dz_position": "## DZ-Position" in text,
            "has_zahlen": "## Zahlen" in text,
        }
    return out


def existing_konzepte() -> set[str]:
    if not KONZ_DIR.exists():
        return set()
    return {p.stem for p in KONZ_DIR.glob("*.md")}


def find_theme_gaps(nodes_csv, themen):
    """Cluster-Werte ohne Themen-Hub."""
    covered = set()
    for slug, clusters in THEMA_TO_CLUSTER_A.items():
        if slug in themen:
            covered.update(clusters)
    cluster_counts = Counter(r.get("clusterA", "") for r in nodes_csv.values())
    gaps = []
    for cluster, count in cluster_counts.most_common():
        if not cluster or cluster in covered:
            continue
        gaps.append({"cluster": cluster, "paper_count": count})
    return gaps


def find_outdated_themen(nodes_csv, themen):
    """Themen-Hubs, die nicht alle relevanten Papers listen."""
    out = []
    for slug, meta in themen.items():
        clusters = THEMA_TO_CLUSTER_A.get(slug, [])
        if not clusters:
            continue
        relevant = [nid for nid, row in nodes_csv.items()
                    if row.get("clusterA") in clusters]
        listed = set(meta["linked_pubs"])
        missing = [r for r in relevant if r not in listed]
        if missing:
            out.append({
                "theme": slug,
                "missing_count": len(missing),
                "missing_papers": missing[:10],
            })
    return out


# Stopwords (German) + DZ-Filler — Wörter die NICHT als Konzepte zählen
STOPWORDS = {
    "der", "die", "das", "den", "dem", "des", "und", "oder", "aber",
    "ein", "eine", "einen", "eines", "einer", "einem",
    "ist", "sind", "war", "wird", "werden", "wurde", "haben", "hat",
    "in", "im", "auf", "an", "am", "zu", "zum", "zur", "bei", "mit",
    "fuer", "für", "von", "vom", "aus", "nach", "über", "unter",
    "nicht", "auch", "noch", "schon", "sehr", "mehr", "kann", "muss",
    "soll", "wenn", "dass", "weil", "während", "ohne", "gegen",
    "the", "of", "and", "to", "for", "on", "in", "with", "by", "is",
    "this", "that", "be", "will", "as",
    "Deutschland", "DZ", "Dezernat", "Jahr", "Jahre", "Mrd", "Prozent",
}


def extract_term_candidates(publications):
    """Rekurrente Substantive in Kernthesen — Konzept-Kandidaten."""
    # Sehr einfach: Wörter mit großem Anfangsbuchstaben (Substantive),
    # Länge >= 5, in mindestens 4 Papers vorkommend
    occurrences = defaultdict(set)  # term -> {slug, slug, ...}
    word_re = re.compile(r"\b([A-ZÄÖÜ][a-zäöüß-]{4,})\b")
    for slug, p in publications.items():
        text = p["kern"]
        for term in set(word_re.findall(text)):
            if term in STOPWORDS:
                continue
            occurrences[term].add(slug)
    # Filter: in mind. 4 Papers + nicht schon ein Konzept
    have = existing_konzepte()
    candidates = []
    for term, slugs in occurrences.items():
        if len(slugs) < 4:
            continue
        if slugify(term) in have:
            continue
        candidates.append({"term": term, "in_papers": len(slugs),
                            "sample": sorted(slugs)[:5]})
    candidates.sort(key=lambda x: -x["in_papers"])
    return candidates


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="Nur JSON, kein Print")
    args = ap.parse_args()

    nodes_csv = load_nodes_csv()
    publications = load_publications()
    themen = existing_themen()
    konzepte = existing_konzepte()

    theme_gaps = find_theme_gaps(nodes_csv, themen)
    outdated = find_outdated_themen(nodes_csv, themen)
    candidates = extract_term_candidates(publications)

    report = {
        "summary": {
            "publications": len(publications),
            "themen": len(themen),
            "konzepte": len(konzepte),
            "theme_gaps": len(theme_gaps),
            "outdated_themen": len(outdated),
            "concept_candidates": len(candidates),
        },
        "theme_gaps": theme_gaps,
        "outdated_themen": outdated,
        "concept_candidates": candidates[:30],
        "existing_themen": sorted(themen),
        "existing_konzepte": sorted(konzepte),
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                      encoding="utf-8")

    if args.json:
        return 0

    s = report["summary"]
    print(f"\n=== Wiki-Audit ===\n")
    print(f"Publikationen: {s['publications']}")
    print(f"Themen:        {s['themen']}")
    print(f"Konzepte:      {s['konzepte']}")
    print()
    print(f"=== Themen-Lücken ({s['theme_gaps']}) ===")
    print(f"Cluster ohne dedizierten Hub:\n")
    for gap in theme_gaps:
        print(f"  {gap['paper_count']:3d} Papers  {gap['cluster']}")
    print()
    print(f"=== Veraltete Themen ({s['outdated_themen']}) ===")
    for ot in outdated:
        print(f"  {ot['theme']:25s}  fehlen {ot['missing_count']} Papers")
        for p in ot["missing_papers"][:5]:
            print(f"      - {p}")
    print()
    print(f"=== Top 20 Konzept-Kandidaten (in 4+ Papers, nicht existent) ===")
    for c in candidates[:20]:
        print(f"  {c['in_papers']:2d}x  {c['term']}")
    print()
    print(f"Output: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
