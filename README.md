# Publikationsgraph — Dezernat Zukunft

Interaktive Visualisierung der DZ-Fachtexte und ihrer Verbindungen.

**Live:** https://philippasigl.github.io/dz-publikationsgraph/

## Dateien

- `index.html` — Visualisierung (D3.js)
- `data.json` — Nodes + Edges + Cluster-Definitionen
- `nodes.csv` — Publikationsmetadaten (id, clusterA, clusterB, datum, titel)
- `edges.csv` — Verbindungen mit Konfidenz und Label
- `geschichte.md` — Chronik der Bearbeitung

## Ansicht

- **X-Achse:** Datum der Publikation (lose Zeitachse)
- **Y-Achse:** Cluster (Themen oder Finanzierungstyp via Toggle)
- **Node-Größe:** Anzahl Verbindungen
- **Pfeile:** zeigen auf das jüngere Paper (Lesefluss links → rechts)
