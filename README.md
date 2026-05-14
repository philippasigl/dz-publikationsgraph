# DZ Wiki

Wissensbase aller Publikationen des [Dezernat Zukunft](https://dezernatzukunft.org). Ziele:

1. **Intern** — schneller Zugriff auf DZ-Argumente, Zahlen und Positionen für Pitches und Präsentationen.
2. **Extern** — öffentlich zugängliche Seite, auf der Nutzer:innen DZ-Arbeit entdecken können (Karpathy-style Wiki, gehostet via Docusaurus).

Inspiration: [Andrej Karpathys LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Architektur und Schema-Konventionen liegen in [CLAUDE.md](CLAUDE.md).

## Architektur

Dreischichtig — `wiki/` ist die Quelle der Wahrheit, `site/` wird daraus gebaut:

```
publikationen/             ← Original-PDFs (unveränderlich)
wiki/                      ← Quelle: LLM-generierte Markdown-Stubs
  publikationen/           ← Eine MD pro Publikation (Frontmatter + Kernthesen)
  themen/                  ← Themenübersichten
  konzepte/                ← Begriffe
publikationsgraph/         ← data.json (Graph) + Visualisierung
schemas/                   ← Frontmatter-Spec (MD + JSON Schema)
scripts/                   ← Konvertierung, Validierung, Sync, Cleanup
site/                      ← Docusaurus (Serving-Layer, aus wiki/+publikationen/ generiert)
.claude/skills/            ← Claude-Skills für Workflow-Automatisierung
```

## Setup

```bash
pip install pyyaml jsonschema markitdown
cd site && npm install
```

Vorausgesetzt: Python ≥ 3.10, Node ≥ 20.

Einzelne Workflows brauchen zusätzliche Pakete: `requests` und `beautifulsoup4` werden vom Web-Scraper in `scripts/download_fachtexte.py` verwendet, `weasyprint` dient als HTML-zu-PDF-Fallback für Geldbriefe (siehe [pdf-ingestion-Skill](.claude/skills/pdf-ingestion/SKILL.md)).

## Tägliche Workflows

Alle Workflows sind als Claude-Skills implementiert — in einer Claude-Code-Session via `/skill-name` aufrufbar, die zugrundeliegenden Skripte stehen unter `scripts/` und können auch direkt aus dem Terminal genutzt werden.

### Neue Publikation aufnehmen

```
/pdf-ingestion "Name der Datei.pdf"
```

Der Skill konvertiert die PDF aus `publikationen/` zu einer strukturierten Markdown-Datei unter `wiki/publikationen/<slug>.md` mit Frontmatter, Kernthesen, Schlussfolgerungen und Zahlen. Details liegen in [.claude/skills/pdf-ingestion/SKILL.md](.claude/skills/pdf-ingestion/SKILL.md). Der frisch erstellte Stub sollte anschließend mit dem [Fact-Checker](#quellen-fact-check) gegen die Original-PDF geprüft werden, weil die LLM-Extraktion Zahlen, Zuschreibungen und Autor:innen-Namen nicht zuverlässig fehlerfrei erfasst.

### Themen- und Konzept-Seiten generieren

```
/auto-wiki audit                       # Read-only: zeigt Lücken und Kandidaten
/auto-wiki theme <slug>                # Ein Theme erstellen/aktualisieren
/auto-wiki concept <Begriff>           # Ein Konzept erstellen
/auto-wiki update-all                  # Alle Themen-Hubs auf aktuellen Paper-Stand bringen
/auto-wiki fill-gaps                   # Alle Theme-Lücken (Cluster ohne Hub) auf einmal anlegen
```

Der Skill synthetisiert Themen-Hubs unter `wiki/themen/` und Konzept-Seiten unter `wiki/konzepte/` aus den Kernthesen und Schlussfolgerungen der verlinkten Publikations-Stubs. Details liegen in [.claude/skills/auto-wiki/SKILL.md](.claude/skills/auto-wiki/SKILL.md). Auch diese generierten Seiten sollten mit dem [Fact-Checker](#quellen-fact-check) geprüft werden, bevor sie publiziert werden.

### Graph pflegen

```
/network-maker add wiki/publikationen/<slug>.md     # neue Publikation eintragen
/network-maker review                               # alle Edges + Cluster prüfen
/network-maker focus <cluster>                      # einzelnen Cluster reviewen
/network-maker validate                             # nur prüfen, nichts ändern
```

Der Skill pflegt `publikationsgraph/data.json` mit Nodes und Edges zwischen Publikationen. Details liegen in [.claude/skills/network-maker/SKILL.md](.claude/skills/network-maker/SKILL.md).

Die inhaltlichen Verknüpfungen zwischen Papern werden von den Skills auf Basis der Stubs nur vorgeschlagen und noch nicht zuverlässig erfasst, deshalb braucht jede Änderung am Graph eine manuelle Durchsicht. Die Modi `review` und `focus <cluster>` sind genau dafür gedacht, während `validate` ausschließlich die Schema-Konsistenz prüft und keinen inhaltlichen Check ersetzt.

### Quellen-Fact-Check

```
/fact-check single <slug>          # Eine Seite (Publikation, Thema oder Konzept)
/fact-check publikationen [N]      # Batch: alle Publikations-Stubs oder die ersten N
/fact-check themen                 # Batch: alle Theme-Hubs
/fact-check konzepte               # Batch: alle Konzept-Seiten
/fact-check fix <slug> <ids...>    # Bestätigte Findings #N direkt in der Quell-MD umsetzen
/fact-check report                 # Aggregat-View: nur Files mit ✗/⚠
```

Der Skill prüft Zahlen, Zitationen, Zuschreibungen und feststehende Konzepte gegen die jeweilige Quelle (Publikations-Stubs gegen die Original-PDF, Themen und Konzepte gegen Web-Recherche) und schreibt eine kompakte Befund-Tabelle nach `wiki/_fact-check/<slug>.md`. Nach Bestätigung kann er Fixes direkt in der Quell-MD anwenden. Details liegen in [.claude/skills/fact-checker/SKILL.md](.claude/skills/fact-checker/SKILL.md).

### Site bauen und testen

```bash
python scripts/build_wiki_index.py   # regeneriert wiki/index.md (nach neuem Themen-/Konzept-File)
python scripts/build_wiki_meta.py    # regeneriert publikationsgraph/wiki-meta.json (dito)
python scripts/sync_to_site.py       # wiki/+publikationen/ → site/docs/+site/static/
cd site && npm start                 # lokaler Dev-Server auf http://localhost:3000
cd site && npm run build             # Production-Build nach site/build/
```

### Browser-Verifikation nach UI-Änderungen

```
/web-check
```

Nach Änderungen an `site/` oder `publikationsgraph/` öffnet der Skill die relevante Seite selbst im Browser (via `chrome-devtools-mcp`), prüft Console-Errors, Netzwerk-Fehler und Layout und meldet konkrete Befunde zurück. Voraussetzung ist der `chrome-devtools-mcp`-Server (siehe `.mcp.json`). Details liegen in [.claude/skills/web-check/SKILL.md](.claude/skills/web-check/SKILL.md).

## Cleanup-Check am Ende der Session

```
/cleanup-check
```

Lässt [scripts/check_repo.py](scripts/check_repo.py) laufen und meldet, ob das Repo sauber ist. Geprüft werden u. a.:

- **Frontmatter** — jede Publikation hat `title`, `date`, `authors`, `cluster`; Cluster ist einer der 7 kanonischen Werte; Datum im Format `YYYY-MM-DD`.
- **Schema-Konsistenz** — die Cluster-Liste in `schemas/frontmatter.schema.json` ist deckungsgleich mit dem Kanon in `check_repo.py`.
- **Graph-Konsistenz** — `data.json` ist valides JSON, alle Edges zeigen auf existierende Nodes, kein Drift zwischen `wiki/` und Graph.
- **Sync-Drift** — `wiki/`+`publikationen/` ist nach `site/docs/`+`site/static/` propagiert.
- **Repo-Hygiene** — keine Windows-Shell-Artefakte (`nul`), keine OneDrive-Konfliktkopien (`*_1.md`), keine verwaisten Leerordner, `.gitignore` existiert und ist vollständig.
- **Skill-Struktur** — Skills liegen unter `.claude/skills/`, nicht Top-Level `skills/`.
- **Dubletten** — Heuristik auf Titel-Keyword-Overlap zwischen Publikationen.
- **Best Practices** — Wikilinks auflösbar, Slugs ASCII-kebab-case, keine vergessenen `# TODO`/`FIXME` in Skripten.

Direkt aus dem Terminal:

```bash
python scripts/check_repo.py              # Report
python scripts/check_repo.py --fix        # Auto-Fix der idempotenten Befunde
python scripts/check_repo.py --quiet      # nur Errors und Warnings
python scripts/check_repo.py --json       # maschinenlesbar (z. B. für CI)
```

Exit-Code = 0 wenn sauber, 1 wenn Probleme bestehen — eignet sich später als Pre-Commit-Hook (`pre-commit` Framework oder `.git/hooks/pre-commit`).

**Wann verwenden:** Am Ende jeder Arbeitssession, vor jedem `git commit`, nach größeren Schema-Änderungen. Details und Erweiterung neuer Checks: [.claude/skills/cleanup-check/SKILL.md](.claude/skills/cleanup-check/SKILL.md).

## Themencluster (kanonisch)

| ID | Anzeigename | Beispiele |
|---|---|---|
| `fiskalpolitik` | Fiskalpolitik | Schuldenbremse, SGP, Konjunkturkomponente |
| `haushalt` | Haushalt | Verteidigungsausgaben, Kita-Kosten, Verkehrsfinanzierung |
| `geldpolitik und anleihemärkte` | Geldpolitik & Anleihemärkte | Bundeswertpapiere, Spreads, EZB, Zinsen |
| `infra` | Infrastruktur | Stromnetzausbau, Daseinsvorsorge, Eigenkapital Energiewende |
| `wirtschaftspolitik` | Wirtschaftspolitik | Industriepolitik, Emissionshandel, LNG, Turnarounds |
| `makro` | Makro | Arbeitsmarkt, Mindestlohn, Gaspreisbremse |
| `ausland` | Ausland | China, USA, EU-Handelsbeziehungen |

Entscheidungsbaum und Definitionen in [CLAUDE.md](CLAUDE.md#themencluster-kanonisch).

## Konventionen

- **Sprache:** Deutsch
- **Links im Wiki:** `[[Wikilinks]]` mit Titel oder Slug der Zielpublikation
- **Daten:** Immer mit Quelle und Jahr
- **Widersprüche:** Explizit dokumentieren, wenn DZ-Positionen sich entwickelt haben
- **Keine Meinungen:** Nur dokumentieren, was DZ publiziert hat

## Deployment

Die Site ist live unter **🔗 https://philippa-sigl-gloeckner.de/dz-wiki/**, und der Quellcode liegt im Repo [github.com/philippasigl/dz-wiki](https://github.com/philippasigl/dz-wiki).

Jeder Push auf `main` triggert [.github/workflows/deploy.yml](.github/workflows/deploy.yml) und läuft durch folgende Schritte:

1. `python scripts/sync_to_site.py` propagiert `wiki/` und `publikationen/` nach `site/docs/` und `site/static/`.
2. `npm ci && npm run build` in `site/` erzeugt den Docusaurus-Build unter `site/build/`.
3. `publikationsgraph/index.html`, `data.json` und `wiki-meta.json` werden ins Build-Root kopiert, sodass die Pages-Startseite der interaktive Graph ist und die Wiki-Seiten darunter unter `/docs/` liegen.
4. `actions/deploy-pages@v4` publiziert das Artefakt, und der neue Stand ist nach ein bis zwei Minuten live.

Einmalig muss die Pages-Konfiguration im Repo unter Settings → Pages auf Source = **GitHub Actions** stehen (nicht "Deploy from a branch").

Eine lokale Vorschau ist im Abschnitt [Site bauen und testen](#site-bauen-und-testen) beschrieben. Der Publikationsgraph isoliert lässt sich öffnen, indem man `publikationsgraph/index.html` direkt im Browser aufruft — `data.json` wird dann vom Browser daneben geladen.
