---
name: auto-wiki
description: >
  Karpathy-style Wiki-Generator. Erstellt oder aktualisiert Themen-Hubs und
  Konzept-Seiten automatisch aus dem Publikations-Korpus. Synthetisiert
  DZ-Position, Zahlen-Tabelle und Paper-Liste aus den Kernthesen +
  Schlussfolgerungen der verlinkten Publikationen. Verwende diesen Skill
  zum Vervollständigen des Wikis oder nach dem Hinzufügen neuer Papers.
---

# Auto-Wiki — Themen- und Konzept-Generator

Hypertext-Layer über dem Publikations-Korpus: aggregiert verstreute Inhalte
zu Hubs, die die zwei Anwendungsfälle bedienen — schneller Pitch-Lookup und
externe Discovery.

## Aufruf

```
/auto-wiki audit                       Read-only: zeigt Lücken und Kandidaten
/auto-wiki theme <slug>                Ein Theme erstellen/aktualisieren
/auto-wiki concept <Begriff>           Ein Konzept erstellen
/auto-wiki update-all                  Alle bestehenden Themen-Hubs auf
                                       aktuellen Paper-Stand bringen
/auto-wiki fill-gaps                   Alle Theme-Lücken (Cluster ohne
                                       Hub) auf einmal anlegen
```

## Prerequisites

Vor dem Lauf:

```bash
python scripts/audit_wiki.py
```

Schreibt `publikationsgraph/wiki-audit.json` mit Lücken-Liste, veralteten
Themen und Konzept-Kandidaten. Der Skill liest diese Datei.

## Mode: `audit`

Schritte:

1. `python scripts/audit_wiki.py` ausführen
2. JSON parsen und in lesbarer Form ausgeben:
   - Statistik (Publikationen / Themen / Konzepte)
   - Theme-Lücken (clusterA ohne Hub-Seite)
   - Veraltete Themen (Hub listet nicht alle relevanten Papers)
   - Top-20 Konzept-Kandidaten
3. Vorschläge formulieren ("3 Hubs fehlen, soll ich sie anlegen?")
4. NICHTS ändern — Nutzer entscheidet nächsten Schritt

## Mode: `theme <slug-oder-clusterA-name>`

Erstellt oder überschreibt `wiki/themen/<slug>.md`.

### Vorgang

1. **Audit-Daten laden**: `publikationsgraph/wiki-audit.json` lesen
2. **Relevante Papers identifizieren**:
   - Aus `publikationsgraph/nodes.csv`: alle Papers wo `clusterA` zum Theme passt
   - Mapping `THEMA_TO_CLUSTER_A` in `audit_wiki.py` ist die kanonische Zuordnung
   - Falls neues Theme: passendes clusterA-Mapping mit Nutzer abstimmen
3. **Quellen lesen**:
   - Für jedes relevante Paper: Frontmatter + `## Kernthesen` + `## Schlussfolgerungen` + `## Zahlen`
   - Wenn >10 Papers: Sub-Agenten parallel beauftragen (3–5 gleichzeitig)
4. **Inhalte synthetisieren**:
   - **DZ-Position**: 2–4 Sätze, die die wichtigste gemeinsame Aussage zusammenfassen — nicht ein Paper paraphrasieren, sondern die *Cluster-übergreifende Linie* destillieren
   - **Zahlen**: 4–8 zentrale Kennzahlen aus den Papers, alle mit Quelle ([[paper-slug]]) und Jahr; nur Zahlen aufnehmen, die NICHT bereits in einer benachbarten Themen-Seite stehen (Duplikate vermeiden)
   - **Publikationen**: alle relevanten Papers chronologisch (neueste oben), als `[[slug]]` Wikilink + ein 1-Zeiler aus dem Summary-Feld bzw. der ersten Kernthese
   - **Siehe auch**: 2–5 verwandte Themen oder Konzepte (über Tags / clusterB / explizite edge_notes)
5. **Template schreiben** (s. u.)
6. `python scripts/build_wiki_meta.py` ausführen → Index regenerieren
7. `python scripts/sync_to_site.py` ausführen

### Themen-Template

```markdown
# <Titel>

<1–2 Sätze: Was umfasst dieses Thema? Eine Frage stellen + DZ-Linse.>

## DZ-Position

<2–4 Sätze, die die destillierte DZ-Sicht ausdrücken. Konkret und prägnant.
Keine Paraphrase, sondern Synthese aus mehreren Papers.>

## Zahlen

| Kennzahl | Wert | Quelle |
|---|---|---|
| <Kennzahl 1> | <Wert mit Einheit, Jahr> | [[paper-slug-1]] |
| <Kennzahl 2> | <Wert> | [[paper-slug-2]] |

## Publikationen

- **<Jahr>** [[slug-1]] — <Einzeiler aus Summary>
- **<Jahr>** [[slug-2]] — <Einzeiler>

## Siehe auch

[[verwandtes-thema]] · [[verwandtes-konzept]]
```

### Regel: Hub statt Roman

Themen-Seite ist **Signpost, kein Lehrbuch**. Max 60–80 Zeilen. Wenn mehr
gesagt werden müsste, gehört das in die einzelnen Publikations-Stubs.

## Mode: `concept <Begriff>`

Erstellt `wiki/konzepte/<slug>.md`.

### Vorgang

1. Slug aus Begriff erzeugen (`scripts/slugify.py` oder analog: lowercase,
   ASCII, kebab-case)
2. Papers identifizieren, die den Begriff erwähnen — Grep über
   `wiki/publikationen/**` für den Term (case-insensitive, word boundaries)
3. Top 3–5 Papers mit den klarsten Erwähnungen auswählen (oft schon im
   Konzept-Audit gelistet)
4. Definition synthetisieren: 1 Satz, neutral und technisch
5. DZ-spezifische Verwendung formulieren: 2–3 Sätze
6. Beispiele aus den Papers entnehmen (mit Wikilink)
7. Querverweise auf 2–3 verwandte Konzepte/Themen

### Was ist ein Konzept?

Konzepte sind **ökonomische Fachbegriffe, die nicht selbsterklärend sind** und im DZ-Diskurs eine definitorische Klärung brauchen.

**Rein:**
- Ökonomische Fachbegriffe: Objektförderung, Konjunkturkomponente, Sondervermögen
- Politisch-juristische Begriffe, wenn sie in einem Paper eine wichtige Rolle spielen: Konnexitätsprinzip, Anti-Coercion-Instrument
- DZ-eigene Konstrukte: Lebensqualitätsminimum

**Nicht rein:**
- Alltagssprachliche Begriffe mit ökonomischer Bedeutung (z.B. "Schuld")
- Institutionen / Akteure (EZB, KfW, Bundesbank)
- Begriffe aus anderen Wissenschaften (z.B. chemische Prozesse)

### Konzept-Template

```markdown
# <Begriff>

<1 Satz: Was ist das, mechanisch/definitorisch?>

## Funktion

<2–3 Sätze: Wie funktioniert es? Welcher Mechanismus?>

## DZ-Perspektive

<1–2 Sätze: Wie verwendet/bewertet DZ diesen Begriff?>

## Erwähnungen

- [[paper-slug-1]] — <kurze Kontext-Notiz>
- [[paper-slug-2]] — <kurze Kontext-Notiz>

## Siehe auch

[[verwandtes-konzept]] · [[verwandtes-thema]]
```

### Regel: Definition vs. Position

Konzept-Seite ist **definitorisch + DZ-Sicht**. Aggregiert keine Position
über mehrere Papers (das macht die Themen-Seite). Hier zählt Präzision der
Definition, nicht Vollständigkeit der Verwendung.

## Mode: `update-all`

Re-lauf für alle Themen-Hubs auf aktuellen Paper-Stand:

1. `audit_wiki.py --json` ausführen
2. Aus `outdated_themen` jedes Theme der Reihe nach (oder parallel mit
   Sub-Agenten) durchgehen
3. Für jedes Theme: nur die Sektionen `## Zahlen` und `## Publikationen`
   neu generieren — `## DZ-Position` und `## Siehe auch` bleiben (sind
   redaktioneller Inhalt)
4. Diff zur alten Version zeigen, vor dem Schreiben Bestätigung einholen
5. `python scripts/build_wiki_meta.py` + `python scripts/sync_to_site.py`

## Mode: `fill-gaps`

Alle clusterA-Werte ohne Hub auf einmal anlegen:

1. Aus Audit-Report: `theme_gaps` (Cluster + Paper-Count)
2. Pro Cluster: passender Theme-Titel + Slug vorschlagen
   - Cluster → Slug-Mapping wird zu `THEMA_TO_CLUSTER_A` in
     `audit_wiki.py` ergänzt (Skill schreibt diese Datei mit Edit-Tool)
3. Nutzer-Bestätigung für die Slugs vor der Generierung
4. Pro genehmigtem Slug: Mode `theme <slug>` ausführen (Sub-Agent)
5. Nach allen: `build_wiki_meta` + `sync_to_site`

## MDX-Falltüren (Docusaurus rendert mit MDX)

Vermeide in der Prosa:
- Spitze Klammern direkt vor Buchstaben: `r<g`, `<5%`, `x>0` → in Inline-Code packen: `` `r<g` ``, `` `<5%` ``
- Curly braces `{}` mit Code-artigem Inhalt → escape: `\{x\}` oder Inline-Code
- HTML-ähnliche Tags ohne Schließtag

Wenn unsicher: Inline-Code (Backticks) ist immer sicher.

## Synthese-Prinzipien (für alle Modi)

1. **Destillieren, nicht zitieren**: Hubs sind Signposts, nicht Sammlungen
   von Volltext-Auszügen.
2. **Zahlen mit Quelle**: jede Zahl mit `[[paper-slug]]` und Jahr — keine
   freischwebenden Behauptungen.
3. **Wikilinks reichlich**: zwischen Themen, Konzepten und Papers, beide
   Richtungen sollen über `[[…]]` möglich sein.
4. **DZ-Sicht expliziter**: bei Mehrdeutigkeit DZ-Position aus den
   Schlussfolgerungen ableiten, nicht raten.
5. **Idempotent**: jeder Modus darf mehrfach laufen ohne Schaden — der
   Skill darf eine bestehende Seite überschreiben, behält aber den
   redaktionellen Teil (siehe `update-all`).

## Dateien & Outputs

| Pfad | Was |
|---|---|
| `scripts/audit_wiki.py` | Identifiziert Lücken, schreibt `wiki-audit.json` |
| `publikationsgraph/wiki-audit.json` | Strukturierter Audit-Output |
| `scripts/build_wiki_meta.py` | Regeneriert `wiki-meta.json` (Index unter dem Graph) |
| `scripts/sync_to_site.py` | Pusht alles nach `site/static/` |
| `wiki/themen/<slug>.md` | Themen-Hub |
| `wiki/konzepte/<slug>.md` | Konzept-Seite |

## Checkliste pro Lauf

- [ ] `python scripts/audit_wiki.py` ausgeführt
- [ ] Quell-Papers gelesen (nicht nur Titel — Kernthesen + Zahlen)
- [ ] DZ-Position destilliert (nicht zitiert)
- [ ] Zahlen-Tabelle mit Quellen
- [ ] Mindestens 2 Querverweise im „Siehe auch"
- [ ] Slug konsistent (ASCII-kebab-case, keine Umlaute)
- [ ] `python scripts/build_wiki_meta.py`
- [ ] `python scripts/sync_to_site.py`
- [ ] Browser-Reload + visuelle Stichprobe
