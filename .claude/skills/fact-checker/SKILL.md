---
name: fact-checker
description: >
  Prueft Wiki-Texte gegen ihre Quellen und kann Findings nach Bestaetigung
  direkt in der Quell-MD fixen. Drei Klassen: Zahlen, Zitationen/Zuschreibungen,
  feststehende Konzepte. Publikations-Stubs gegen Original-PDF (intern).
  Themen/Konzepte gegen Web-Recherche (extern). Output: kompakte Tabelle
  mit nummerierten Findings + Fix-Vorschlaegen unter wiki/_fact-check/<slug>.md.
  Verwende nach groesseren Wiki-Aenderungen oder vor Publikation.
---

# Fact-Checker

Prueft was im Wiki steht — gegen Quellen, nicht gegen Stil. Kann nach
Bestaetigung der Nutzerin Fixes direkt anwenden.

## Was geprueft wird

1. **Zahlen** — jede Geldmenge, Quote, Jahresangabe, Statistik
2. **Zitationen / Zuschreibungen** — „X sagt Y", „Konzept Z wurde von W entwickelt"
3. **Feststehende Konzepte** — Definitionen, Mechanismen, rechtliche Bezuege
4. **Autoren-Namen im Frontmatter** — **immer** pruefen: Vor- und Nachname, Schreibweise, Diakritika

### Autoren-Check (Pflicht bei publikationen)

Bei jedem Publikations-Stub: `authors`- und `coauthors`-Felder im Frontmatter
gegen das PDF-Deckblatt (Seite 1) und ggf. `web_url` abgleichen. Typische Fehlerklassen:

- Tippfehler im Namen (z.B. „Heißlmann" statt „Heilmann", „Hoffnung" statt „Hornung")
- Falscher Vorname (z.B. „Niklas Schulte" statt „Sara Schulte", „Gabriel Illenseer" statt „Niklas Illenseer")
- Fehlende Diakritika („Krah" statt „Krahé")
- Unvollstaendige Autorenliste (nur einige der tatsaechlichen Co-Autoren)
- Inkonsistente Namen-Variante (z.B. „Florian Schuster" vs „Florian Schuster-Johnson" — auf konsistente DZ-Schreibweise normalisieren)

Severity:
- Tippfehler / fehlendes Diakritikum → ✗ (klar falsch)
- Unvollstaendige Liste → ⚠ (ergaenzen)
- Inkonsistente Schreibweise zwischen Files → ⚠ mit Hinweis auf gewuenschte Form

Belege im Befund: PDF-Seite (meist Deckblatt) oder DZ-Website-URL.

## Was nicht geprueft wird

- Wertende Aussagen, Politik-Empfehlungen, Stil/Grammatik
- Plausibilitaet der DZ-eigenen Modellrechnungen

## Aufruf

```
/fact-check single <slug>            Eine Seite
/fact-check publikationen [N]        Batch (alle oder N Stubs)
/fact-check themen                   Alle Theme-Hubs
/fact-check konzepte                 Alle Konzept-Seiten
/fact-check fix <slug> <ids...>      Findings #N umsetzen (z.B. "fix slug 1 3 5")
/fact-check fix <slug> all-wrong     Alle ✗-Findings umsetzen
/fact-check report                   Aggregat-View: nur Files mit ✗/⚠
```

## Output-Format (Tabelle)

Pro gepruefter Datei: `wiki/_fact-check/<slug>.md`

```markdown
# Fact-Check: <slug>

Geprueft: 2026-05-14 · Quelle: publikationen/Datei.pdf

| # | ✗⚠✓ | Klasse | Behauptung | Befund | Fix-Vorschlag |
|---|---|---|---|---|---|
| 1 | ✗ | Zahl | "Status quo 20-24 Mrd" | PDF: Status quo = 4,5 Mrd; 20-24 = Vollbeschaeftigungs-Szenario | Tabellenzeile umbenennen in "Vollbeschaeftigungs-Szenario \| 20-24 Mrd"; neue Zeile "Status quo (BMWi) \| 4,5 Mrd" einfuegen (PDF S. 2156) |
| 2 | ✗ | Zitation | "Functional Finance (Blanchard et al.)" | Lerner 1943; Blanchard et al. greifen es 2020 auf | Ersetze durch "Functional Finance (Lerner 1943; Blanchard et al. 2020)" |
| 3 | ⚠ | Zahl | "Reformen = 50-60 Mrd" | Gilt nur fuer volles Reformpaket | Praezisieren: "(volles Reformpaket: Produktionspotenzial + Budgetsemielastizitaet 0,5)" |
| 4 | ⚠ | Zahl | "Budgetsemielastizitaet aktuell 0,2" | Bund: 0,203; Gesamt: 0,5 | Splitten: "Bund: 0,2 \| Gesamtstaat: 0,5" |
| 5 | ✓ | Konzept | "r < g als Bedingung" | Korrekt referenziert (PDF S. 131-138) | — |

**Summary:** 2 ✗, 2 ⚠, 1 ✓. Kritisch: #1, #2.
```

**Tabellen-Regeln:**
- Eine Zeile pro Befund. Knapp halten — keine Mehrzeilen-Bullets.
- "Behauptung" = woertliches Zitat oder enge Paraphrase, < 80 Zeichen
- "Befund" = was die Quelle sagt, < 100 Zeichen
- "Fix-Vorschlag" = konkrete Edit-Anweisung. Bei ✓: "—". Pipe in Tabellen-Zellen mit `\|` escapen.
- Findings sortiert: ✗ zuerst, dann ⚠, dann ✓
- Nummerierung beginnt bei 1, fortlaufend

Severity:
- `✓` belegt
- `⚠` teilweise / Praezisierung noetig / Rundungsabweichung
- `✗` nicht belegt / falsch / nicht in der Quelle gefunden

## Mode: `single <slug>`

1. Slug aufloesen → MD-Pfad
2. **Behauptungen extrahieren**: Bullets/Tabellenzeilen mit Zahl ODER Eigenname ODER Konzeptname
3. **Quelle laden** (publikationen: PDF; themen/konzepte: Web)
4. **Pro Behauptung pruefen**, einsortieren, nummerieren
5. **Tabellen-Report schreiben** unter `wiki/_fact-check/<slug>.md`
6. **Stichworte zur Nutzerin**: „X ✗, Y ⚠, Z ✓ — Report unter [path]. Zum Fixen: `/fact-check fix <slug> 1 3 5`"

## Mode: `publikationen [N]` / `themen` / `konzepte`

Batch. Spawn 3-5 Sub-Agents (general-purpose) parallel. Jeder bekommt:
- Pfad zur MD + zur Quelle (PDF / Web-Search-Auftrag)
- Skill-Datei lesen (das hier)
- Tabellen-Report ausgeben

Hauptagent sammelt Summaries, schreibt `wiki/_fact-check/_INDEX.md` als Tabelle:

```markdown
| Slug | ✗ | ⚠ | ✓ | Top-Issue |
|---|---|---|---|---|
| eine-neue-deutsche-finanzpolitik | 2 | 2 | 4 | Functional Finance falsch zugeschrieben |
| was-kostet-...                   | 0 | 1 | 6 | — |
```

## Mode: `fix <slug> <ids...>`

Setzt einzelne Findings um.

1. Report `wiki/_fact-check/<slug>.md` lesen, Tabelle parsen
2. Quell-MD `wiki/<area>/<slug>.md` lesen
3. Pro angeforderter ID:
   - Fix-Vorschlag aus Tabelle nehmen
   - Edit auf Quell-MD anwenden
   - Wenn unklar (z.B. Fix-Vorschlag nicht 1:1 als Edit umsetzbar): pausieren, Nutzerin fragen, NICHT raten
4. Report nachfuehren: gefixte Zeile bekommt `✗→FIXED`-Marker plus Datum
5. **Vor jedem Fix anzeigen**: alte Zeile + neue Zeile (diff-Stil), Bestaetigung wenn nicht offensichtlich
6. Bei `all-wrong`: alle `✗` der Reihe nach durchgehen

**Fix-Sicherheit:**
- Nie raten bei mehrdeutigen Fix-Vorschlaegen
- Nie ueber Wikilinks druebereditieren ohne Check
- Bei Tabellen-Fixes: Spaltenstruktur erhalten
- Bei Frontmatter-Fixes: YAML-Syntax wahren

## Mode: `report`

Liest `wiki/_fact-check/_INDEX.md` und alle Reports. Gibt:

```
publikationen/X — 2 ✗, 1 ⚠
themen/Y       — 1 ✗
konzepte/Z     — 3 ⚠
```

Plus die 3 schwerwiegendsten ✗-Findings repo-weit.

## Pruefregeln

### Zahlen
- Exact match → ✓
- Diff < 5% oder Rundung → ⚠ + Hinweis
- Nicht in Quelle, plausibel/sekundaer belegt → ⚠
- Unbelegt/widerspruechlich → ✗
- Berechnete/abgeleitete Werte → ⚠ + „abgeleitet"

### Zitationen
- Eigenname mit Konzept → Web-Search
- Wikipedia + 1 weitere Quelle bestaetigen → ✓
- Quellen nennen anderes → ✗ + Korrektur
- Keine eindeutige Quelle → ⚠

### Autoren-Namen (Frontmatter, immer pruefen)
- Schritt 1: Frontmatter-`authors`/`coauthors` extrahieren
- Schritt 2: Gegen PDF-Deckblatt (Seite 1, meistens) abgleichen
- Schritt 3: Bei Abweichung — Tippfehler vs. unvollstaendige Liste vs. inkonsistente Form
- Severity wie oben: Tippfehler/Diakritika = ✗, Unvollstaendigkeit = ⚠
- Bei Sammelautoren („Dezernat Zukunft") nur pruefen, ob PDF tatsaechlich keine Einzel-Autoren nennt

### Konzepte
- Definition gg. mind. 1 etablierte Quelle (Lehrbuch, Glossar, primary)
- Substanz muss stimmen, keine Wortgleichheit
- Rechtliche Verweise (Art. X GG, EU-Verordnungen): exact match, sonst ✗

## Wichtige Quellen (Defaults)

Wikipedia (DE+EN), IMF/OECD/Weltbank, EZB/Bundesbank-Glossare, NBER/RePEc/SSRN,
BMF/BMWK/Destatis, gesetze-im-internet.de. Bei Konflikten zwischen Quellen:
alle nennen, ⚠.

## Was tun wenn die Quelle fehlt

- PDF nicht da: Zeile "nicht pruefbar — PDF fehlt", separater Bereich
- web_url tot: Web-Search-Fallback, ggf. archive.org
- Behauptung zu vage: ueberspringen (nicht ✗)

## Nicht-Ziele

- **Kein Stil-Check** — falsche Formulierungen, Holprigkeiten sind nicht Sache dieses Skills
- **Kein silent Fix** — Fix-Modus laeuft nur explizit auf Anweisung der Nutzerin, nie automatisch nach Check
