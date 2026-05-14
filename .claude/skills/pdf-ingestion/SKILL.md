---
name: pdf-ingestion
description: >
  Workflow zur Aufnahme einer DZ-Publikation ins Wiki. Konvertiert eine PDF aus
  publikationen/ zu strukturiertem Markdown unter wiki/publikationen/, extrahiert
  Frontmatter + Kernthesen + Schlussfolgerungen + Zahlen und legt den Slug fest.
  Verwende diesen Skill immer wenn eine neue PDF zum Wiki hinzugefügt werden soll.
---

# DZ Wiki – PDF Ingestion

Bringt eine PDF aus `publikationen/` als strukturierte Markdown-Datei nach `wiki/publikationen/`. Nicht für den Graphen — das macht der `network-maker` Skill anschließend.

## Aufruf

```
/pdf-ingestion <dateiname.pdf>
```

Pfad relativ zu `publikationen/`. Beispiel:

```
/pdf-ingestion "Wie sieht ein guter Arbeitsmarkt aus.pdf"
```

### Vor dem Lauf: nichts überschreiben was schon gut ist

`scripts/needs_reprocessing.py` listet, welche PDFs noch keinen Stub-konformen Eintrag in `wiki/publikationen/` haben. Diesen Skill **nur auf solche PDFs** anwenden — Stub-konforme `.md`s nicht neu erzeugen.

```
python scripts/needs_reprocessing.py
python scripts/needs_reprocessing.py --pdfs    # nur Dateinamen, pipeable
```

### Bestehende `.md` mit `ignore: yes` nicht zerstören

Wenn beim Re-Lauf eine `.md` mit `ignore: "yes"` existiert (englische Übersetzung, FAQ-Duplikat, Geschwister-Publikation): **die Datei nicht überschreiben**. `ignore: yes` ist ein bewusst gesetzter Duplikat-Marker; siehe Abschnitt „Wann ignore: yes setzen" weiter unten.

## Zielformat

```markdown
---
title: "Titel der Publikation"
date: "YYYY-MM-DD"
authors: ["Vorname Nachname", "Vorname Nachname"]
cluster: "fiskalpolitik"
format: "policy-paper"
tags: ["schuldenbremse", "konjunkturkomponente"]
pdf_url: "/publikationen/Original-Dateiname.pdf"
web_url: "https://dezernatzukunft.org/..."
summary: "1–2 Sätze Kernaussage."
---

## Kernthesen
- These 1 (1 Satz)
- These 2 (1 Satz)
- These 3 (1 Satz)

## Schlussfolgerungen
- Offene Frage / Nächster Schritt → [[Folge-Publikation]]
- Politikempfehlung

## Zahlen
| Kennzahl | Wert |
|---|---|
| Beispiel | 13 Mrd. € |
```

**Kein Fließtext.** Nur strukturierte Daten für den Graphen:
- **Kernthesen** = Was sagt das Papier?
- **Schlussfolgerungen** = Wohin führt es? (→ Graph-Kanten)
- **Zahlen** = Zentrale Datenpunkte

Vollständige Frontmatter-Spec: [schemas/frontmatter-schema.md](../../../schemas/frontmatter-schema.md). Cluster-Definitionen und Entscheidungsbaum: [CLAUDE.md](../../../CLAUDE.md#themencluster-kanonisch).

## Workflow

### 1. PDF konvertieren (Rohtext)

```bash
python scripts/convert_pdf_to_markdown.py "publikationen/<dateiname>.pdf" wiki/publikationen/
```

### 2. Strukturieren

**Bei langen Papers (>15.000 Wörter Rohkonvertierung) zuerst splitten:**

```bash
python scripts/extract_long_paper_sections.py wiki/publikationen/<datei>.md
```

Der Helper schneidet das Paper in drei fokussierte Abschnitte:
- **Anfang** (erste 8.000 Wörter): Title, Exec Summary, Einleitung — daraus die **Kernthesen**
- **Schluss** (letzte 4.000 Wörter VOR Annex/Literaturverzeichnis): Conclusion, Policy Recommendations — daraus die **Schlussfolgerungen**
- **Tabellen** (alle aus dem Hauptteil): numerische Datenpunkte — daraus die **Zahlen**

Strukturiere aus diesen drei Stücken — nicht aus dem Volltext. Bei kurzen Papers (<15.000 Wörter) wird die ganze Datei ausgegeben, dann normal weiterarbeiten.

**Wichtig:** Die Stub-Datei **ersetzt** die Rohkonvertierung (`<500 Wörter Body`), nicht zusätzlich.

Lies die Rohkonvertierung (oder bei langen Papers: den Helper-Output) und extrahiere:

**Frontmatter:**
- `title` — Titel der Publikation
- `date` — Erscheinungsdatum (YYYY-MM-DD)
- `authors` — Liste der vollen Namen der DZ-Autor:innen (nur Personen aus dem Dezernat)
- `coauthors` — externe Ko-Autor:innen / Partnerorganisationen. **Pflicht** wenn das Papier mit anderen Think Tanks oder NGOs co-publiziert wurde. Beispiel: `["Agora Energiewende", "Stiftung Klimaneutralität"]`. Auch externe Einzel-Co-Autor:innen (z. B. Prof. Müller bei Rechtsgutachten) hier.
- `cluster` — Einer der 7 IDs (siehe CLAUDE.md-Entscheidungsbaum)
- `format` — siehe Format-Heuristik unten
- `tags` — 3-5 Schlagwörter aus der Taxonomie (lowercase, keine Umlaute)
- `pdf_url`, `web_url`, `summary` — optional
- `ignore` — nur setzen wenn Duplikat; siehe „Wann ignore: yes setzen"

### Format-Heuristik

Das `format`-Feld vor dem Frontmatter-Schreiben anhand dieser Signale festlegen:

| Signal | Format |
|---|---|
| Header im Volltext: `GELDBRIEF` oder Filename enthält „Geldbrief" | `geldbrief` |
| Header im Volltext: `STELLUNGNAHME` oder Titel `Stellungnahme vor dem Ausschuss …` oder englisch „Statement at …" / „Introductory Statement" | `stellungnahme` |
| Header im Volltext: `PRESSEMITTEILUNG` | `pressemitteilung` |
| Header: `POLICY PAPER` oder `HINTERGRUNDPAPIER` | `policy-paper` |
| Header: `STUDIE`, `RECHTSGUTACHTEN`, akademisch (Working Paper, formales Abstract) | `studie` |
| Filename endet auf `- Dezernat Zukunft.pdf` (HTML-Snapshot einer dezernatzukunft.org-Seite) | `blogpost` |
| Keine eindeutigen Signale, lange deutsche DZ-Analyse mit Politikempfehlungen | `policy-paper` |
| Lange englischsprachige akademische Arbeit | `studie` |
| Sehr kurzer DZ-Webartikel ohne Policy-Paper-Charakter | `blogpost` |
| Kommentar / Op-Ed / Diskussionsbeitrag, **kein** Anhörungs-Statement | `kommentar` |

Vollständige Format-Werte: `policy-paper`, `studie`, `geldbrief`, `blogpost`, `kommentar`, `stellungnahme`, `pressemitteilung`.

### Wann `ignore: yes` setzen

`ignore: yes` markiert eine `.md` als Duplikat-Repräsentation einer schon existierenden Publikation. Sie wird vom Graph- und Coverage-Tooling übersprungen. Setzen in genau diesen Fällen:

- **Übersetzungen** — englische Version eines deutschen Originals (oder umgekehrt). Beispiel: `a-proposal-for-reforming-the-stability-and-growth-pact.md` (en) → ignore=yes, weil das deutsche Pendant `weiterentwicklung-europaeische-fiskalregeln.md` der Hauptknoten ist.
- **FAQs** zu einer anderen Publikation, die selbst keine eigenständige These hat.
- **Zwei `.md`-Repräsentationen desselben PDFs** mit unterschiedlichen Slugs (z. B. lang-name + Kurzform): die Kurzform als Hauptknoten, lange als ignore.

Nicht setzen, wenn das Papier eine eigenständige Publikation ist — auch wenn es thematisch ähnlich zu einer anderen ist.

**Kernthesen (3-5 Bullets):**
Aus Executive Summary / Einleitung. Hauptargumente als einzelne Sätze.

**Schlussfolgerungen:**
Aus Fazit / Schluss / Policy Recommendations. Offene Fragen, Folgearbeiten, Verlinkungen zu existierenden Publikationen mit `[[Titel]]` bzw. `[[slug]]`.

**Zahlen:**
2-5 zentrale Kennzahlen aus dem Papier.

### 3. Slug generieren und Datei umbenennen

```
python scripts/slugify.py "Titel der Publikation"
# Ausgabe: titel-der-publikation
```

Umbenennen plattform-unabhängig per Python (statt `mv` / `Move-Item`):

```
python -c "import pathlib, sys; pathlib.Path(sys.argv[1]).rename(sys.argv[2])" wiki/publikationen/<alte-datei>.md wiki/publikationen/<slug>.md
```

### 4. Frontmatter, Stub-Format und Zahlen validieren

```
python scripts/normalize_frontmatter.py
python scripts/check_stub_format.py wiki/publikationen/<slug>.md
python scripts/check_stub_numbers.py wiki/publikationen/<slug>.md "publikationen/<original>.pdf"
python scripts/validate_graph.py
```

- `normalize_frontmatter.py` ist idempotent und enthält intern `sys.stdout = TextIOWrapper(..., encoding="utf-8")` — kein `PYTHONIOENCODING`-Prefix nötig (funktioniert auf PowerShell und Bash gleichermaßen).
- `check_stub_format.py` prüft: Body ≤ 500 Wörter, `## Kernthesen` mit 3-5 Bullets, `## Schlussfolgerungen` mit ≥1 Bullet, Frontmatter gegen Schema. Bei FAIL: nicht weiter — Stub korrigieren.
- `check_stub_numbers.py` prüft, dass jede Zahl aus der `## Zahlen`-Tabelle als Ziffernfolge im konvertierten Original-PDF vorkommt. Schutz gegen Zahlen-Halluzination. WARN ≠ FAIL — bei Mangel manuell gegen PDF prüfen.
- `validate_graph.py` prüft den Gesamtgraphen.

### 5. In den Graphen aufnehmen

Dafür den Skill `network-maker` aufrufen:

```
/network-maker add wiki/publikationen/<slug>.md
```

### 6. Nach site/ synchronisieren

```bash
python scripts/sync_to_site.py
```

Kopiert `wiki/publikationen/*.md` → `site/docs/publikationen/` und `publikationen/*.pdf` → `site/static/publikationen/`.

## Geldbrief-Sonderfall (kein nativer PDF-Download)

Für Geldbriefe von dezernatzukunft.org, die keinen PDF-Download anbieten: HTML-Snapshot per `weasyprint` als Print-PDF nach `publikationen/<Titel> - Dezernat Zukunft.pdf` erzeugen (siehe `scripts/download_fachtexte.py` als Referenz), dann normaler Workflow.

Dateinamenkonvention für Geldbriefe: `<Titel> - Dezernat Zukunft.pdf`. Für Fachtexte: `<Erstautor>-<YYYY>-<Kurztitel>.pdf`.

## Checkliste

- [ ] PDF in `publikationen/`
- [ ] `needs_reprocessing.py` zeigt das Paper als unbearbeitet (sonst nicht doppelt machen)
- [ ] Bestehende `.md` mit `ignore: yes` nicht überschrieben
- [ ] Bei >15.000 Wörter Rohkonvertierung: `extract_long_paper_sections.py` benutzt
- [ ] Stub-Datei hat ≤500 Wörter Body (Rohtext **ersetzt**, nicht angehängt)
- [ ] Frontmatter vollständig (title, date, authors, cluster, format, tags)
- [ ] `coauthors` gesetzt bei externer Ko-Autorschaft
- [ ] `format` nach Heuristik korrekt (Stellungnahme → `stellungnahme`, nicht `kommentar`)
- [ ] 3-5 Kernthesen
- [ ] Schlussfolgerungen mit `[[Links]]` zu verwandten Publikationen
- [ ] Zentrale Zahlen in Tabelle
- [ ] Slug-Dateiname
- [ ] `python scripts/check_stub_format.py <datei>` läuft mit `[OK]` durch
- [ ] `python scripts/check_stub_numbers.py <datei> <pdf>` zeigt 0 fehlende Zahlen (oder Abweichungen sind dokumentiert)
- [ ] `python scripts/validate_graph.py` läuft durch
- [ ] `network-maker add` ausgeführt
- [ ] `python scripts/sync_to_site.py` ausgeführt
