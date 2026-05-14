# DZ Wiki

Öffentliche Wissensbase aller Publikationen des [Dezernat Zukunft](https://dezernatzukunft.org).

**Live:** [philippasigl.github.io/dz-wiki](https://philippasigl.github.io/dz-wiki/)

## Was hier liegt

- **`/`** — interaktiver Publikationsgraph (D3.js): Cluster-Karte aller DZ-Fachtexte mit ihren Verbindungen
- **`/wiki/`** — Wiki mit Publikations-Stubs, Themen-Hubs und Konzept-Seiten (Docusaurus)
- **`/publikationen/`** — Original-PDFs

## Datenstand

- `data.json` — Nodes + Edges + Cluster-Definitionen für die Visualisierung
- `nodes.csv` / `edges.csv` — Tabellen-Export desselben Stands
- `wiki-meta.json` — Wiki-Index für den Graphen
- `geschichte.md` — Chronik der Bearbeitung

## Graph-Ansicht

- **X-Achse:** Datum der Publikation
- **Y-Achse:** Cluster (Themen oder Finanzierungstyp via Toggle)
- **Node-Größe:** Anzahl Verbindungen
- **Pfeile:** zeigen auf das jüngere Paper

## Lizenz

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.de) — Inhalte: Dezernat Zukunft e.V. Site-Code: Philippa Sigl-Glöckner. Beta-Deployment.
