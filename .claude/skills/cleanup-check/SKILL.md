---
name: cleanup-check
description: >
  Repo-Cleanup-Check für die DZ-Wissensbase. Prüft am Ende einer Session,
  ob das Repo sauber ist: Frontmatter gegen Schema, Graph-Konsistenz, Sync-Drift
  wiki→site, leere Ordner, OneDrive-Konfliktkopien, Windows-Shell-Artefakte
  (nul, _N-Suffixe), Skill-Lokation, .gitignore-Coverage. Auto-Fix der idempotenten
  Befunde nach Bestätigung. Verwende diesen Skill am Ende jeder Arbeitssession.
---

# Cleanup Check

Dünner Wrapper um [scripts/check_repo.py](../../../scripts/check_repo.py). Der Skill ruft den Report auf, interpretiert die Findings, fragt vor dem Auto-Fix nach und meldet einen klaren Endzustand.

## Was geprüft wird

| Sektion | Was |
|---|---|
| `root` | Akzidentelle Dateien im Repo-Root (z. B. `nul`, OneDrive `_N`-Suffixe, unbekannte Einträge) |
| `empty-dirs` | Leere Ordner überall im Tree |
| `python-cache` | `__pycache__/` (sollte gitignored sein, aber nicht persistieren) |
| `gitignore` | `.gitignore` existiert + deckt `__pycache__/`, `node_modules/`, `site/build/`, `nul` ab |
| `temp-folders` | `temp/`, `tmp/`, `scratch/` im Root |
| `skills` | Skills unter `.claude/skills/` (nicht Top-Level `skills/`) |
| `schema` | `schemas/frontmatter.schema.json` deckt sich mit dem 7-Cluster-Kanon |
| `frontmatter` | Jede Publikation hat title/date/authors/cluster, Cluster ist ein einzelner gültiger String, Datum YYYY-MM-DD |
| `graph` | `publikationsgraph/data.json` ist valides JSON, keine dangling Edges, keine wiki↔graph-Drift |
| `sync` | `wiki/`+`publikationen/` mirror nach `site/docs/`+`site/static/` |
| `slugs` | Dateinamen in `wiki/publikationen/` sind ASCII-kebab-case |
| `duplicates` | Heuristik: zwei MDs mit sehr ähnlichem Titel = potentielle Dublette |
| `wikilinks` | `[[Wikilinks]]` zeigen auf existierende Slugs (Fuzzy-Match) |
| `debug-leftovers` | `TODO`/`FIXME`/`XXX`/`HACK` in `scripts/` |
| `large-files` | PDFs außerhalb der erwarteten Pfade |

## Aufruf

```
/cleanup-check          # Standard: Report + auf Bestätigung fragen vor Auto-Fix
/cleanup-check report   # Nur Report, kein Auto-Fix
/cleanup-check fix      # Auto-Fix ohne Rückfrage (CI-Mode)
```

## Ablauf

1. **Report erzeugen** — `PYTHONIOENCODING=utf-8 python scripts/check_repo.py --quiet` ausführen.
2. **Findings interpretieren** — die Sektionen durchgehen und in Kurzform zusammenfassen.
3. **Auto-Fix entscheiden:**
   - Wenn `[fixable]`-Befunde existieren: dem Nutzer die Liste zeigen und fragen, ob sie ausgeführt werden sollen.
   - Bei „Ja" oder im `fix`-Modus: `python scripts/check_repo.py --fix --quiet` laufen lassen.
4. **Unfixable Befunde** — als Aktionsliste zurückgeben:
   - **Frontmatter-Fehler** (fehlende Pflichtfelder, ungültige Cluster): MD-Dateien manuell ergänzen — meist beim nächsten `pdf-ingestion`-Lauf zu beheben.
   - **Graph-Drift** (Publikationen nicht im Graph): Skill `network-maker add <datei>` aufrufen.
   - **Potentielle Dubletten**: inhaltliche Entscheidung des Nutzers — beide Dateien lesen, dann konsolidieren oder als „nicht doppelt" bestätigen.
   - **OneDrive-Konfliktkopien** (`*_1.md` etc.): inhaltlich vergleichen und einen Pfad löschen.
5. **Endzustand zusammenfassen** — was läuft sauber, was bleibt offen.

## Exit-Codes

`check_repo.py` gibt zurück:

- `0` — sauber (nach optionalem Auto-Fix nichts mehr offen)
- `1` — Probleme gefunden / Restprobleme nach Fix
- `2` — interner Fehler im Script

Damit ist das Script auch außerhalb von Claude Code als Pre-Commit-Hook brauchbar.

## Was der Skill NICHT macht

- Keine inhaltlichen Entscheidungen (Cluster-Zuordnung neuer Papiere, Dubletten-Konsolidierung) — diese gehören in `pdf-ingestion` bzw. `network-maker`.
- Kein Push, kein Commit, keine destruktiven Aktionen ohne Bestätigung.

## Erweiterung neuer Checks

Neuer Check in [scripts/check_repo.py](../../../scripts/check_repo.py):

1. Funktion `check_<name>(report: Report) -> None` schreiben — Findings via `report.add(section=..., severity=..., message=..., path=..., fix=...)` hinzufügen.
2. Funktion in die `CHECKS`-Liste am Ende eintragen.
3. `--fix` ist nur sinnvoll, wenn die Aktion idempotent und destruktionsarm ist.