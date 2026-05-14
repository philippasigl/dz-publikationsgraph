# DZ Wiki – Schema

Dieses Wiki dokumentiert das Wissen von **Dezernat Zukunft**, einem wirtschaftspolitischen Think Tank in Berlin.

## Architektur

```
/publikationen/            ← Original-PDFs (unveränderlich, ein Layer)
/wiki/                     ← Quelle: LLM-generierte Markdown-Seiten
  index.md
  log.md
  /publikationen/          ← Eine MD pro Publikation (Frontmatter + Kernthesen)
  /themen/                 ← Thematische Übersichtsseiten
  /konzepte/               ← Zentrale Begriffe
/publikationsgraph/        ← Graph-Daten (data.json, index.html)
/schemas/                  ← Frontmatter-Schema (Doku + JSON Schema)
/scripts/                  ← Konvertierung, Validierung, Sync nach site/
/site/                     ← Docusaurus (Serving-Layer; aus wiki/ + publikationen/ generiert)
/.claude/skills/           ← Workflow-Skills (pdf-ingestion, network-maker)
```

`wiki/` ist die Quelle der Wahrheit für Inhalte. `site/docs/` und `site/static/` werden per `scripts/sync_to_site.py` aus `wiki/` und `publikationen/` befüllt.

## Themencluster (kanonisch)

Sieben Cluster. Werte für das `cluster`-Frontmatter-Feld in Kleinbuchstaben:

| ID | Anzeigename | Kriterium | Beispiele |
|---|---|---|---|
| `fiskalpolitik` | Fiskalpolitik | Schuldenregeln (deutsch oder europäisch), Schuldenbremse, GG Art. 115, EU-Stabilitätspakt, Konjunkturkomponente | Reformvorschlag Konjunkturkomponente, SGP Reform, Schuldenquote |
| `haushalt` | Haushalt | Öffentliche Ausgaben, Finanzbedarfe, Ausgabenstruktur, was kostet X den Staat | Verteidigungsausgaben, Kita-Kosten, Verkehrsfinanzierung, Sozialstaat-Spielraum |
| `geldpolitik und anleihemärkte` | Geldpolitik & Anleihemärkte | Zinsen, Anleihemärkte, Staatsanleihen, EZB, Bundesbank, Inflation, monetäre Architektur | Bundeswertpapiere, Spreads, Zinserhöhungen, Euro-Internationalisierung |
| `infra` | Infrastruktur | Energie-Infrastruktur, öffentliche Finanzierung außerhalb Bundeshaushalt/Schuldenbremse, Netze, Stadtwerke | Stromnetzausbau, Daseinsvorsorge, Eigenkapital Energiewende |
| `wirtschaftspolitik` | Wirtschaftspolitik | Private Unternehmen, Industriepolitik, Energiekosten für Unternehmen, Wettbewerbsfähigkeit | Energieintensive Industrien, Emissionshandel, LNG, Turnarounds |
| `makro` | Makro | Gesamtwirtschaft, Arbeitsmarkt, Konjunktur, Wachstum, Löhne | Arbeitsmarktampel, Mindestlohn, Kipppunkte Klima, Gaspreisbremse |
| `ausland` | Ausland | Internationale/geopolitische Themen, EU-Außenbeziehungen, Handelsbeziehungen (NICHT EU-Fiskalregeln) | Europe's Trump Cards, Beyond Maastricht |

### Entscheidungsbaum

1. Schuldenregeln (Schuldenbremse, SGP, Art. 115)? → `fiskalpolitik`
2. Konkrete Ausgaben/Kosten des Staates? → `haushalt`
3. Zinsen, Anleihen, EZB, monetäre Fragen? → `geldpolitik und anleihemärkte`
4. Energie-Infrastruktur außerhalb des Bundeshaushalts? → `infra`
5. Private Unternehmen, Industriepolitik? → `wirtschaftspolitik`
6. Gesamtwirtschaft, Arbeitsmarkt, Konjunktur? → `makro`
7. Internationale/geopolitische Themen (nicht EU-Fiskalregeln)? → `ausland`

EU-Fiskalregeln (SGP, Maastricht) sind immer `fiskalpolitik`, nicht `ausland`. Bei Grenzfällen lieber fragen als raten.

## Frontmatter (Publikationen)

Pflichtfelder: `title`, `date`, `authors`, `cluster`, `format`. Vollständige Spezifikation in [schemas/frontmatter-schema.md](schemas/frontmatter-schema.md), maschinenlesbar in [schemas/frontmatter.schema.json](schemas/frontmatter.schema.json).

`cluster` ist immer **ein** String aus den sieben Cluster-IDs (kein Array, keine Klammern, kein quoting der Werte nötig wenn alphanumerisch).

## Workflows

Jeder Workflow lebt in seinem Skill — Templates, Schritte und Sonderregeln dort.

| Aufgabe | Skill |
|---|---|
| Neue PDF aufnehmen (→ `wiki/publikationen/<slug>.md`) | [pdf-ingestion](.claude/skills/pdf-ingestion/SKILL.md) |
| Themen-Hub oder Konzept-Seite anlegen/aktualisieren | [auto-wiki](.claude/skills/auto-wiki/SKILL.md) |
| Graph-Nodes + Edges pflegen | [network-maker](.claude/skills/network-maker/SKILL.md) |
| Quellen-Fact-Check | [fact-checker](.claude/skills/fact-checker/SKILL.md) |
| Browser-Verifikation nach UI-/Site-Änderung | [web-check](.claude/skills/web-check/SKILL.md) |
| Repo-Hygiene am Session-Ende | [cleanup-check](.claude/skills/cleanup-check/SKILL.md) |

Nach jeder inhaltlichen Änderung: `python scripts/sync_to_site.py` und Eintrag in `wiki/log.md`.

## Verifikation von Web-Outputs

Bei Änderungen an `site/` (Docusaurus) oder `publikationsgraph/`: **selbst im Browser prüfen** via [web-check](.claude/skills/web-check/SKILL.md) — nicht um Screenshots bitten. Voraussetzung ist der `chrome-devtools-mcp` Server (siehe `.mcp.json`). Wenn die MCP-Tools nicht verfügbar sind: erst MCP-Server checken, dann erst Screenshot anfragen.

## Konventionen

- **Sprache:** Deutsch
- **Links:** Wikilinks mit `[[Seitenname]]`
- **Daten:** Immer mit Quelle und Jahr
- **Widersprüche:** Explizit dokumentieren wenn DZ-Positionen sich entwickelt haben
- **Keine Meinungen:** Nur dokumentieren was DZ publiziert
