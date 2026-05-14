---
name: network-maker
description: >
  Reviewt, standardisiert und vernetzt DZ-Publikationen im Publikationsgraphen
  (publikationsgraph/data.json). Vier Modi: review (alles), add (neue Publikation),
  focus <cluster> (nur ein Cluster), validate (read-only). Verwende diesen Skill
  zum Pflegen des Graphen — nach pdf-ingestion oder zur Qualitätssicherung.
---

# Network Maker – Publikationsgraph Manager

Pflegt `publikationsgraph/data.json` mit maximaler Präzision. Cluster-Definitionen kommen aus [CLAUDE.md](../../../CLAUDE.md#themencluster-kanonisch); Frontmatter-Schema aus [schemas/frontmatter-schema.md](../../../schemas/frontmatter-schema.md).

## Aufruf

```
/network-maker [modus] [optionen]
```

### Modi

| Modus | Beschreibung |
|---|---|
| `review` | Vollständiger Review aller Publikationen |
| `add <datei.md>` | Einzelne neue Publikation hinzufügen |
| `focus <cluster>` | Nur bestimmten Cluster reviewen |
| `validate` | Nur Validierung ohne Änderungen |

### Beispiele

```
/network-maker review
/network-maker add wiki/publikationen/neue-studie.md
/network-maker focus fiskalpolitik
/network-maker validate
```

---

## Kernprinzipien

1. **Präzision vor Vollständigkeit** — lieber weniger, dafür korrekte Edges.
2. **Transparenz** — jede Änderung dokumentieren; bei Unsicherheit fragen.
3. **Kontrollierter Ablauf** — Schritt für Schritt; Nutzer kann jederzeit eingreifen.

## Cluster-Zuordnung

Die 7 Cluster mit Entscheidungsbaum stehen in [CLAUDE.md](../../../CLAUDE.md#themencluster-kanonisch). Wichtige Regel: **EU-Fiskalregeln (SGP, Maastricht) sind immer `fiskalpolitik`, nicht `ausland`.**

### Grenzfälle (IMMER FRAGEN)

- Schuldenregel UND konkrete Ausgaben → fragen
- Energie: Infrastruktur vs. Industriepolitik → fragen
- Arbeitsmarkt: Makro vs. Haushalt → fragen

---

## Edge-Logik

### Was IST eine Edge?

1. **Thematische Vertiefung** — Papier B vertieft einen Aspekt aus Papier A
2. **Methodische Weiterentwicklung** — B entwickelt Ansatz aus A weiter
3. **Explizite Referenz** — B baut erkennbar auf A auf
4. Ein Papier kann mehrere Edges haben, aber jede Edge muss klar begründet sein.

### Was ist KEINE Edge?

- Übersetzung
- Zufällige thematische Überschneidung
- Gleicher Autor, anderes Thema
- Allgemeine Cluster-Zugehörigkeit

### Zentrale Ankerpapiere

| Papier | ID | Cluster | Rolle |
|---|---|---|---|
| Eine neue deutsche Finanzpolitik (2021) | `eine-neue-deutsche-finanzpolitik` | fiskalpolitik | Grundlagenpapier Schuldenbremse |
| Warum die Konjunkturkomponente ihren Zweck nicht mehr erfüllt (2021) | `warum-die-konjunkturkomponente-ihren-zweck-nicht-mehr-erfuellt` | fiskalpolitik | Konjunkturkomponente-Analyse |
| Eine ökonomisch sinnvolle Schuldenregel (2025) | `eine-oekonomisch-sinnvolle-schuldenregel` | fiskalpolitik | Reformvorschlag Schuldenregel |
| Zur Weiterentwicklung der europäischen Fiskalregeln (2022) | `weiterentwicklung-europaeische-fiskalregeln` | fiskalpolitik | EU-Fiskalregeln |
| Was kostet eine sichere, lebenswerte und nachhaltige Zukunft | `was-kostet-sichere-lebenswerte-nachhaltige-zukunft` | haushalt | Ankerpapier Haushalt – Finanzbedarfe |

### Edge-Richtung (HARTE REGEL)

```
"from" → "to" bedeutet: "from" baut auf "to" auf / verweist auf "to"
```

`from` ist immer das **neuere** Papier. Daraus folgt:

```
from.date >= to.date  (außer Übersetzungspaare → die sind via ignore:yes
                       aus dem Graph)
```

**Vor jedem Edge-Vorschlag automatisch Datums-Check:**

```
[OK]   from.date (2025-06) >= to.date (2024-09)
[WARN] from.date (2022-04) < to.date (2022-05)  →  Richtung umkehren?
```

Bei Reverse-Chronology-Warnung: niemals stillschweigend trotzdem setzen. Entweder Richtung umkehren oder Edge verwerfen.

### Edge-Identifikation (Prüfreihenfolge — strikt)

1. **`edge_notes` im Frontmatter** → Direkte Anweisung, umsetzen
2. **Explizite Textreferenz** → Fließtext-Verweis („Wie in X gezeigt…", „Aufbauend auf Y…") ODER Erwähnung im Literaturverzeichnis
3. **Thematische Kette** → Gleiches Spezialthema, chronologisch, plus Nutzer-Bestätigung

**„Cluster + Datum" alleine reicht NICHT mehr** — zu schwach, führt zu falschen Edges.

### Konfidenz-Schwellen (Pflichtfeld `confidence` in jeder Edge)

| Konfidenz | Kriterium | Aktion |
|---|---|---|
| **`hoch`** | `edge_notes` ODER direkter Textverweis ODER Lit-Verzeichnis-Erwähnung ODER bestätigtes Übersetzungspaar | Vorschlag mit Belegsatz, automatisch nach Bestätigung |
| **`mittel`** | Plausible thematische Verwandtschaft, Nutzer:in bestätigt | **PRO EDGE bestätigen** mit Belegsatz oder explizitem Grund — niemals Batch |
| **`niedrig`** | Vermutung, noch nicht bestätigt | Nicht setzen, nur als Vorschlag notieren |

### Vage Referenzen

Wenn Nutzer:in „papier zu X" oder ähnlich vage Referenz angibt: **nie raten**. Immer top-3 Kandidaten mit Datum + 1-Satz-Summary präsentieren, dann auswählen lassen.

```
Frage: „papier zu evus" - welches gemeint?
  a) eigenkapital-fuer-die-energiewende  (2026-04, infra)
     Eigenkapital für kommunale Energieversorger
  b) was-taugt-der-deutschlandfonds  (2026-01, infra)
     Deutschlandfonds-Fremdkapitalinstrumente für EVU
  c) effekte-staatlicher-beteiligungen-...  (2025-09, infra)
     Übertragungsnetz-Beteiligungen des Bundes
```

---

## Workflow: Review-Modus

### Phase 1: Bestandsaufnahme

1. Lade `publikationsgraph/data.json`
2. Lade alle `wiki/publikationen/*.md`
3. Erstelle Übersicht: Nodes, Edges, Cluster-Verteilung, Papiere ohne Edges

### Phase 2: Cluster-Review

Für jedes Papier:
1. Frontmatter lesen (title, date, cluster)
2. Erster Absatz / Executive Summary lesen
3. Gegen Cluster-Definitionen prüfen
4. Bei Abweichung dokumentieren

### Phase 3: Edge-Review

1. Existierende Edges auf Plausibilität prüfen
2. Fehlende Edges suchen (edge_notes, thematische Ketten, Chronologie)
3. Vorschläge dokumentieren

### Phase 4: Änderungen anwenden

1. Alle geplanten Änderungen zeigen
2. Auf Nutzer-Bestätigung warten
3. `publikationsgraph/data.json` aktualisieren
4. ggf. Frontmatter in MD-Dateien aktualisieren (Cluster-Änderungen)
5. `python scripts/sync_to_site.py`

---

## Workflow: Add-Modus

```
1. MD-Datei lesen
2. Frontmatter validieren (siehe Validierungsregeln)
3. Cluster-Zuordnung prüfen → bei Unsicherheit FRAGEN
4. Potenzielle Edges suchen:
   - edge_notes
   - Papiere im gleichen Cluster
   - Thematische Verwandtschaft
5. Vorschlag zeigen (Cluster + Edges)
6. Auf Bestätigung warten
7. Node + Edges in data.json eintragen
8. python scripts/sync_to_site.py
```

---

## Validierungsregeln

### Frontmatter (Pflichtfelder)

| Feld | Format |
|---|---|
| `title` | string |
| `date` | YYYY-MM-DD |
| `authors` | string[] (mind. 1) |
| `cluster` | eine der 7 IDs |
| `format` | einer der 6 Werte (siehe Schema) |
| `tags` | string[] (3-5 empfohlen) |
| `ignore` | optional, `"yes"` überspringt das Papier |
| `edge_notes` | optional, String mit Edge-Hinweisen |

### data.json

- Jeder Node: `id`, `title`, `date`, `cluster`, `authors`, `tags`
- Jede Edge: `from`, `to`, `label`, **`confidence`** (`hoch` | `mittel` | `niedrig`)
- `from`/`to` müssen auf existierende Node-IDs verweisen
- `from.date >= to.date` muss gelten (Reverse-Chronology wird gewarnt)
- Keine Duplikate

Automatisierte Prüfung: `python scripts/validate_graph.py`.

CSV-Export für externe Reviews: `python scripts/export_graph_csv.py` → `publikationsgraph/nodes.csv` + `edges.csv` (UTF-8 BOM, Semikolon-Delimiter, mit `konfidenz`-Spalte).

---

## Ausgabeformat

### Bei Edge-Vorschlag

Jede vorgeschlagene Edge braucht Datums-Check, Konfidenz und Quelle:

```
[1] Edge hinzufügen:
    von:        zinserhoehungen-wirken-weniger-als-erwartet  (2026-02-10)
    auf:        overcoming-myopia-ecb-2025-strategy-review   (2025-01-15)
    [OK]        Chronologie korrekt (from >= to)
    label:      ECB Strategy Review
    confidence: hoch
    quelle:     edge_notes "folgt auf overcoming-myopia"
    
Anwenden? [j/n]
```

Bei MITTEL-Konfidenz: gleicher Aufbau, aber `quelle:` enthält Belegsatz aus dem Volltext oder expliziten Grund.

### Bei Änderungen (Cluster etc.)

```
ÄNDERUNGEN
==========
[1] Cluster geändert: "papier-titel"
    Alt: fiskalpolitik
    Neu: haushalt

Änderungen anwenden? [j/n]
```

### Bei Fragen

```
FRAGE
=====
Cluster für "Titel des Papiers" unklar.

Das Papier behandelt:
- Schuldenregel-Reform (→ fiskalpolitik)
- Konkrete Klimaausgaben (→ haushalt)

Welcher Cluster ist korrekt?
1. fiskalpolitik
2. haushalt
```

---

## Dateipfade

```
wiki/publikationen/*.md             ← Quelle (Frontmatter + Inhalt)
publikationsgraph/data.json         ← Graph-Daten (Quelle)
site/static/publikationsgraph/data.json ← Graph-Daten (gehostete Kopie)
publikationen/*.pdf                 ← Original-PDFs
```

Sync nach `site/`: `python scripts/sync_to_site.py`.
