# DZ Wiki

Eine durchsuchbare, vernetzte Wissensbase aller Publikationen von [Dezernat Zukunft](https://dezernatzukunft.org), einem wirtschaftspolitischen Think Tank in Berlin.

**Live:** [philippasigl.github.io/dz-wiki](https://philippasigl.github.io/dz-wiki/)

## Worum es geht

Dezernat Zukunft veröffentlicht seit 2021 Policy-Papiere, Studien und Geldbriefe zu Fiskalpolitik, Geldpolitik, Industriepolitik, Sozialstaat und Infrastruktur. Diese Materialien sind reichhaltig, aber bisher verstreut. Diese Wissensbase macht sie greifbar:

- **Publikations-Stubs** — pro Paper eine Seite mit Kernthesen, Schlussfolgerungen und zentralen Zahlen
- **Themen-Hubs** — kuratierte Übersichten zu Bundeshaushalt, Schuldenbremse, Wohnungspolitik, Energiewende usw., die die DZ-Position über mehrere Papiere hinweg destillieren
- **Konzept-Seiten** — ökonomische Fachbegriffe wie Konjunkturkomponente, Sondervermögen, NAWRU, Schuldentragfähigkeitsanalyse, kurz und definitorisch
- **Publikationsgraph** — interaktive Visualisierung aller Papiere als vernetzte Karte: chronologisch sortiert, nach Cluster gruppiert, mit expliziten Verbindungslinien zwischen Vorgänger- und Folge-Arbeiten

## Wer das nutzt

Gedacht für Journalist:innen, Politik-Mitarbeitende, Forschende und alle, die zu deutscher und europäischer Wirtschaftspolitik recherchieren. Inhalte sind auf Deutsch, Originaldokumente verlinkt.

## Inhalte unter `/`

| Pfad | Was |
|---|---|
| `/` | Interaktiver Publikationsgraph (D3.js) |
| `/wiki/` | Wiki (Docusaurus) — Publikationen, Themen, Konzepte |
| `/publikationen/` | Original-PDFs |

## Graph-Bedienung

- **X-Achse:** Datum der Publikation
- **Y-Achse:** Cluster (umschaltbar zwischen Themen und Finanzierungstyp)
- **Knotengröße:** Anzahl Verbindungen
- **Pfeile:** zeigen vom neueren auf das ältere Paper

## Datendateien

- `data.json` — Graph-Definition (Nodes, Edges, Cluster)
- `nodes.csv` / `edges.csv` — Tabellen-Export desselben Stands für externe Auswertung
- `wiki-meta.json` — Index der Wiki-Seiten für den Graphen

## Status

Beta. Inhalte werden laufend gepflegt und fact-gecheckt. Methode: Publikationen werden LLM-gestützt aus den Original-PDFs zu strukturierten Markdown-Stubs verarbeitet, die einer Mensch-im-Loop-Qualitätskontrolle unterliegen. Fehler bitte als Issue melden.

## Lizenz

Inhalte: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.de) — Dezernat Zukunft e.V.
Site-Code: Philippa Sigl-Glöckner.
