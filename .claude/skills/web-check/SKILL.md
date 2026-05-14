---
name: web-check
description: >
  Selbststaendiger Browser-Check fuer Website-Aenderungen — keine Screenshots
  von der Nutzerin noetig. Startet bei Bedarf den Dev-Server (Docusaurus unter
  site/ oder publikationsgraph/), oeffnet die relevante Seite via
  chrome-devtools-mcp, prueft Console-Errors, Netzwerk-Fehler, Layout und
  meldet konkrete Befunde zurueck. Verwende diesen Skill immer wenn eine
  Aenderung visuell oder im Browser-Verhalten verifiziert werden muss.
---

# Web-Check

Statt die Nutzerin um Screenshots zu bitten: selber im Browser nachschauen.
Setzt voraus, dass der MCP-Server `chrome-devtools` laeuft (Tools `mcp__chrome-devtools__*`).

## Wann

- Nach jeder Aenderung an `site/` (Docusaurus, MDX, CSS, Komponenten)
- Nach jeder Aenderung an `publikationsgraph/` (data.json, index.html, JS)
- Nach `python scripts/sync_to_site.py` zur Verifikation
- Vor "fertig" — nicht nur Build-Erfolg, sondern Render im Browser

## Targets im Repo

| Target | Pfad | Wie starten | URL |
|---|---|---|---|
| Docusaurus | `site/` | `npm --prefix site start` (Background) | http://localhost:3000 |
| Publikationsgraph | `publikationsgraph/index.html` | `python -m http.server 8765 --directory publikationsgraph` (Background) | http://localhost:8765 |

Beide Server als Background-Prozess starten (`run_in_background: true`), Port-Check vorher, NICHT killen ohne Grund — die Nutzerin hat ggf. schon einen laufen.

## Workflow

1. **Server-Check** — laeuft der relevante Dev-Server schon? `Test-NetConnection -ComputerName localhost -Port 3000`. Wenn nein: starten und ~3 Sek auf "ready" warten (Monitor-Tool).
2. **Navigate** — `mcp__chrome-devtools__navigate_page` mit der Ziel-URL.
3. **Console-Errors** — `mcp__chrome-devtools__list_console_messages`. Jeder Error/Warning ist relevant. React/MDX-Warnings ernst nehmen.
4. **Network-Fehler** — `mcp__chrome-devtools__list_network_requests`. 404/500 = Bug. Besonders bei Wikilinks und Asset-Pfaden nach Sync.
5. **Visueller Check** — `mcp__chrome-devtools__take_screenshot` (oder `take_snapshot` fuer DOM-Struktur). Bei Layout-Aenderungen: vorher/nachher-Vergleich.
6. **Interaktion bei Bedarf** — Click via `mcp__chrome-devtools__click`, scroll, fill-form. Nicht ueberinterpretieren — nur testen was die Aenderung betrifft.

## Report-Format

Knapp. Keine Romane.

```
Geprueft: http://localhost:3000/wiki/publikationen/<slug>
- Console: 0 Errors, 1 Warning ("Image alt missing in <slug>.md L42")
- Network: alle 200
- Render: OK (Frontmatter, Kernthesen, Tabelle sichtbar)
- Screenshot: <pfad>
```

Bei Fehlern: konkrete Fix-Vorschlaege, nicht nur "kaputt".

## Was NICHT

- **Keine A11y-Audits oder Lighthouse-Runs** ungefragt — sprengt Scope.
- **Keine UI-Vorschlaege** auf Eigeninitiative. Nur das pruefen, was die aktuelle Aenderung betrifft.
- **Nicht den User-Chrome stoeren** — chrome-devtools-mcp startet seine eigene Instanz. Wenn doch ein bestehendes Profil/Tab gebraucht wird, vorher mit der Nutzerin abstimmen.
- **Keinen Dev-Server killen, der nicht von dir gestartet wurde**. Im Zweifel: parallelen Port nutzen (3001, 8766).

## Fallback wenn MCP-Tools fehlen

Wenn `mcp__chrome-devtools__*` nicht verfuegbar ist:
1. Pruefen ob MCP-Server gestartet ist (`.mcp.json` im Repo-Root).
2. Nutzerin bitten, Claude Code neu zu laden (MCP-Server werden beim Start geladen).
3. Erst dann zurueckfallen auf "Screenshot bitte".

## Typische Befunde Wiki-Kontext

- **Wikilink-Bruch** nach Slug-Aenderung → 404 im Network-Log
- **MDX-Compile-Error** durch Sonderzeichen in Frontmatter → Build-Fehler in Console
- **Asset-Pfad falsch** nach `sync_to_site.py` → Bild/PDF 404
- **Graph-Render kaputt** durch invaliden `data.json` → Console JS-Error
