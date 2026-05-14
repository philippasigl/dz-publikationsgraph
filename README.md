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
pip install pyyaml weasyprint markitdown
cd site && npm install
```

Vorausgesetzt: Python ≥ 3.10, Node ≥ 20.

## Tägliche Workflows

Alle Workflows sind als Claude-Skills implementiert — in einer Claude-Code-Session via `/skill-name` aufrufbar, die zugrundeliegenden Skripte stehen unter `scripts/` und können auch direkt aus dem Terminal genutzt werden.

### Neue Publikation aufnehmen

```
/pdf-ingestion "Name der Datei.pdf"
```

Konvertiert die PDF aus `publikationen/` zu einer strukturierten Markdown-Datei unter `wiki/publikationen/<slug>.md` mit Frontmatter, Kernthesen, Schlussfolgerungen und Zahlen. Details: [.claude/skills/pdf-ingestion/SKILL.md](.claude/skills/pdf-ingestion/SKILL.md).

### Graph pflegen

```
/network-maker add wiki/publikationen/<slug>.md     # neue Publikation eintragen
/network-maker review                               # alle Edges + Cluster prüfen
/network-maker focus <cluster>                      # einzelnen Cluster reviewen
/network-maker validate                             # nur prüfen, nichts ändern
```

Pflegt `publikationsgraph/data.json` (Nodes + Edges zwischen Publikationen). Details: [.claude/skills/network-maker/SKILL.md](.claude/skills/network-maker/SKILL.md).

### Site bauen und testen

```bash
python scripts/sync_to_site.py    # wiki/+publikationen/ → site/docs/+site/static/
cd site && npm start              # lokaler Dev-Server auf http://localhost:3000
cd site && npm run build          # Production-Build nach site/build/
```

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
| `geldpolitik` | Geldpolitik & Anleihemärkte | Bundeswertpapiere, Spreads, EZB, Zinsen |
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

### Volle Wiki-Site (Docusaurus)

```bash
python scripts/sync_to_site.py
cd site && npm run build
# site/build/ auf GitHub Pages oder Netlify deployen — keine Backend nötig
```

### Publikationsgraph standalone

Der interaktive Publikationsgraph ist als eigenständige GitHub-Pages-Seite veröffentlicht:

**🔗 https://philippasigl.github.io/dz-wiki/**

Repo: [github.com/philippasigl/dz-wiki](https://github.com/philippasigl/dz-wiki)

Updates publizieren mit einem Befehl:

```bash
python scripts/publish_graph.py
python scripts/publish_graph.py -m "Cluster-Update Mai"   # eigene Commit-Message
python scripts/publish_graph.py --dry-run                 # nur Vorschau
```

[scripts/publish_graph.py](scripts/publish_graph.py) macht:

1. Kopiert `index.html`, `data.json`, `nodes.csv`, `edges.csv` aus `publikationsgraph/` nach `~/dev/dz-wiki/` (klont das Repo dort beim ersten Lauf automatisch).
2. `git add . && git commit && git push`
3. GitHub Pages baut → nach ~1 Min ist der neue Stand live.

Backup-CSVs und `geschichte.md` bleiben lokal — nur die für die Visualisierung nötigen Dateien werden publiziert.

**Voraussetzungen** (einmalig):
- Lese-/Schreibzugriff auf `philippasigl/dz-wiki` per HTTPS (Git-Credential-Manager oder Personal Access Token)
- Pages-Konfiguration: Source = Deploy from a branch, Branch = `main` / `/ (root)` (im Repo-Settings → Pages)
