# DZ-Wiki Frontmatter Schema

YAML-Frontmatter für Publikationen in `wiki/publikationen/`. Maschinenlesbares Schema: [frontmatter.schema.json](frontmatter.schema.json).

## Beispiel

```yaml
---
title: "Eigenkapital für die Energiewende"
subtitle: "Ein Deutschland-Standard zur Stärkung der Kapitalbasis kommunaler Energieversorger"
date: "2026-04-22"
authors:
  - "Johannes Schröten"
  - "Janek Steitz"
  - "Mediha Inan"
cluster: "infra"
format: "policy-paper"
tags:
  - "energiewende"
  - "investitionen"
  - "kommunen"
  - "deutschlandfonds"
pdf_url: "/publikationen/Eigenkapital-fuer-die-Energiewende-2026.pdf"
web_url: "https://dezernatzukunft.org/publikationen/eigenkapital-energiewende"
summary: "Kommunale Energieversorger brauchen Eigenkapital, um die Energiewende zu stemmen."
---
```

## Felder

### Pflicht

| Feld | Typ | Beschreibung |
|---|---|---|
| `title` | string | Haupttitel |
| `date` | string | `YYYY-MM-DD` |
| `authors` | string[] | Liste der DZ-Autor:innen |
| `cluster` | enum | Themencluster (s.u.) |

### Optional

| Feld | Typ | Beschreibung |
|---|---|---|
| `format` | enum | Publikationstyp (s.u.) — nice-to-have, nicht graph-relevant |
| `subtitle` | string | Untertitel |
| `coauthors` | string[] | Externe Ko-Autor:innen / Partnerorganisationen |
| `tags` | string[] | Inhaltliche Schlagworte (3–5 empfohlen) |
| `pdf_url` | string | Relativer Pfad zur PDF in `site/static/` |
| `web_url` | string | URL auf dezernatzukunft.org |
| `dataset_url` | string | URL des begleitenden Datensatzes (Excel/CSV/Landing Page) |
| `summary` | string | 1–2 Sätze Kernaussage |
| `ignore` | string | `"yes"` → Publikation wird vom Graph-Tooling übersprungen |
| `edge_notes` | string | Hinweise an `network-maker`, welche Edges manuell gesetzt werden sollen |

## Enums

### `cluster`

Genau **ein** Wert (kein Array). Definition siehe [CLAUDE.md](../CLAUDE.md#themencluster-kanonisch).

| Wert | Anzeigename |
|---|---|
| `fiskalpolitik` | Fiskalpolitik (Schuldenregeln, Schuldenbremse, SGP) |
| `haushalt` | Haushalt (öffentliche Ausgaben, Finanzbedarfe) |
| `geldpolitik` | Geldpolitik & Anleihemärkte |
| `infra` | Infrastruktur (Energie-Infra außerhalb Bundeshaushalt) |
| `wirtschaftspolitik` | Wirtschaftspolitik (private Unternehmen, Industriepolitik) |
| `makro` | Makro (Gesamtwirtschaft, Arbeitsmarkt, Konjunktur) |
| `ausland` | Ausland (international/geopolitisch, nicht EU-Fiskalregeln) |

### `format`

| Wert | Beschreibung |
|---|---|
| `policy-paper` | Ausführliche Policy-Analyse mit Handlungsempfehlungen |
| `studie` | Empirische Studie / Datenanalyse |
| `geldbrief` | Newsletter-Ausgabe |
| `blogpost` | Kürzerer Blogbeitrag |
| `kommentar` | Meinungsbeitrag / Op-Ed |
| `stellungnahme` | Stellungnahme (z.B. vor Ausschüssen) |
| `pressemitteilung` | Pressemitteilung |
| `datenset` | Eigenständiges Daten-Tool / Monitor (kein Paper) |

## Tag-Taxonomie (Auswahl)

Frei wählbar, aber bevorzugt aus dieser Liste, damit der Graph konsistent filtert:

**Makro-Themen:** `geldpolitik`, `fiskalpolitik`, `schuldenbremse`, `industriepolitik`, `energiewende`, `sozialstaat`, `arbeitsmarkt`

**Institutionen:** `ezb`, `bundesbank`, `kfw`, `deutschlandfonds`

**Instrumente:** `investitionen`, `transfers`, `steuern`, `schulden`, `eigenkapital`

**Akteure:** `kommunen`, `laender`, `bund`, `eu`

**Regionen:** `deutschland`, `eurozone`, `usa`, `china`

## Validierung

```bash
python scripts/validate_graph.py
```

Prüft Frontmatter aller Dateien in `wiki/publikationen/` gegen [frontmatter.schema.json](frontmatter.schema.json) und stellt sicher, dass alle Edge-Referenzen in `publikationsgraph/data.json` auf existierende Nodes zeigen.

## Graph-Edges (`publikationsgraph/data.json`)

Jede Edge ist ein JSON-Objekt mit folgenden Feldern:

| Feld | Typ | Beschreibung |
|---|---|---|
| `from` | string | Slug des **neueren** Papiers, das auf `to` aufbaut |
| `to` | string | Slug des **älteren** Papiers, das die Quelle ist |
| `label` | string | Kurze Beschreibung der Verbindung |
| `confidence` | enum | `hoch` \| `mittel` \| `niedrig` |

### Konfidenz-Werte

| Wert | Kriterium |
|---|---|
| `hoch` | `edge_notes` im Frontmatter ODER direkter inhaltlicher Verweis im Volltext ODER Erwähnung im Literaturverzeichnis ODER bestätigtes Übersetzungspaar |
| `mittel` | Plausible thematische Verwandtschaft ohne expliziten Beleg, von Nutzer:in bestätigt |
| `niedrig` | Vermutung, noch nicht bestätigt |

### Edge-Richtung

`from` = neueres Papier, `to` = älteres Papier. Daraus folgt: `from.date >= to.date` muss immer gelten. Reverse-chronologische Edges werden von `scripts/check_repo.py` und `scripts/validate_graph.py` als Warnung gemeldet.

**Ausnahme: Übersetzungspaare** sind via `ignore: yes` aus dem Graph ausgeschlossen — sie tauchen also nicht als Edges auf.
