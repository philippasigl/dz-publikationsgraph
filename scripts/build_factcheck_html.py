"""Erzeugt eine HTML-Uebersicht aus wiki/_fact-check/*.md.

Parst alle Tabellen-Reports und baut eine interaktive HTML-Seite mit:
- Checkbox pro Finding (per LocalStorage persistent)
- Filter nach Severity (✗ / ⚠ / ✓ / FIXED)
- Filter nach Bereich (Publikationen / Themen / Konzepte)
- Volltext-Filter
- Klick auf Slug oeffnet Quell-MD (relativer Link)

Aufruf: python scripts/build_factcheck_html.py
Output: wiki/_fact-check/findings.html
"""
from __future__ import annotations

import io
import json
import re
import sys
from html import escape
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
FC_DIR = ROOT / "wiki" / "_fact-check"
OUT = FC_DIR / "findings.html"

# Tabellen-Zeile: | # | ✗⚠✓ | Klasse | Behauptung | Befund | Fix-Vorschlag |
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$")


def classify_area(slug: str) -> str:
    for area in ("publikationen", "themen", "konzepte"):
        if (ROOT / "wiki" / area / f"{slug}.md").exists():
            return area
    # Sonderfall: schuldenbremse-konzept gehoert zu konzepten
    if slug.endswith("-konzept"):
        return "konzepte"
    return "?"


def parse_report(path: Path) -> dict:
    slug = path.stem
    if slug == "_INDEX" or slug.startswith("_"):
        return {}
    text = path.read_text(encoding="utf-8")
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        n, status, klasse, behauptung, befund, fix = m.groups()
        if n == "#":  # Header-Zeile
            continue
        status = status.strip()
        rows.append({
            "n": int(n),
            "status": status,
            "klasse": klasse.strip(),
            "behauptung": behauptung.strip(),
            "befund": befund.strip(),
            "fix": fix.strip(),
        })
    if not rows:
        return {}
    # Resolve actual slug for schuldenbremse-konzept etc.
    actual_slug = slug
    if slug == "schuldenbremse-konzept":
        actual_slug = "schuldenbremse"
        area = "konzepte"
    else:
        area = classify_area(slug)
    return {
        "slug": slug,
        "report_slug": slug,
        "source_slug": actual_slug,
        "area": area,
        "rows": rows,
    }


def main() -> int:
    files = []
    for p in sorted(FC_DIR.glob("*.md")):
        d = parse_report(p)
        if d:
            files.append(d)

    # Statistik
    total_findings = sum(len(f["rows"]) for f in files)
    counts = {"x": 0, "warn": 0, "ok": 0, "fixed": 0}
    for f in files:
        for r in f["rows"]:
            s = r["status"]
            if "FIXED" in s:
                counts["fixed"] += 1
            elif "✗" in s:
                counts["x"] += 1
            elif "⚠" in s:
                counts["warn"] += 1
            elif "✓" in s:
                counts["ok"] += 1

    # Encode as JSON for the page
    data = json.dumps(files, ensure_ascii=False)

    html = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Fact-Check Findings · DZ Wiki</title>
<style>
:root {{
  --bg: #fafafa;
  --paper: #fff;
  --edge: #e8e8e8;
  --ink: #1a1a2e;
  --ink-soft: #5c5c6d;
  --ink-faint: #9090a0;
  --red: #c0392b;
  --orange: #d68910;
  --green: #2d8a47;
  --blue: #2c5282;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-size: 14px;
  line-height: 1.4;
}}
header {{
  background: var(--ink);
  color: #fff;
  padding: 1.5rem 2rem 1rem;
}}
header h1 {{
  margin: 0 0 0.5rem;
  font-size: 1.4rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}}
header .meta {{
  color: #b0b0c0;
  font-size: 0.85rem;
}}
.stats {{
  display: flex;
  gap: 1.5rem;
  padding: 0.75rem 2rem;
  background: var(--paper);
  border-bottom: 1px solid var(--edge);
  font-size: 0.85rem;
  flex-wrap: wrap;
}}
.stat {{
  display: flex;
  align-items: center;
  gap: 0.4rem;
}}
.stat .v {{ font-weight: 600; font-size: 1rem; }}
.stat.x .v {{ color: var(--red); }}
.stat.warn .v {{ color: var(--orange); }}
.stat.ok .v {{ color: var(--green); }}
.stat.fixed .v {{ color: var(--blue); }}

.controls {{
  padding: 1rem 2rem;
  background: var(--paper);
  border-bottom: 1px solid var(--edge);
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  align-items: center;
}}
.controls label {{
  display: flex;
  align-items: center;
  gap: 0.3rem;
  cursor: pointer;
  user-select: none;
  font-size: 0.85rem;
}}
.controls input[type=checkbox] {{ cursor: pointer; }}
.controls input[type=text] {{
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--edge);
  border-radius: 4px;
  font-size: 0.85rem;
  min-width: 240px;
}}
.controls .actions {{
  margin-left: auto;
  display: flex;
  gap: 0.5rem;
}}
.controls button {{
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--edge);
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}}
.controls button:hover {{ background: var(--bg); }}

main {{
  padding: 1rem 2rem 3rem;
}}
.file-block {{
  background: var(--paper);
  border: 1px solid var(--edge);
  border-radius: 6px;
  margin-bottom: 1rem;
  overflow: hidden;
}}
.file-header {{
  padding: 0.75rem 1rem;
  background: #f7f7f9;
  border-bottom: 1px solid var(--edge);
  display: flex;
  align-items: center;
  gap: 1rem;
  font-weight: 500;
}}
.file-header .area-tag {{
  font-size: 0.7rem;
  padding: 0.15rem 0.5rem;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #fff;
  font-weight: 600;
}}
.area-publikationen {{ background: #2c5282; }}
.area-themen {{ background: #7a4caf; }}
.area-konzepte {{ background: #2d8a47; }}
.file-header .slug {{
  flex: 1;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 0.85rem;
}}
.file-header .slug a {{
  color: var(--ink);
  text-decoration: none;
  border-bottom: 1px solid transparent;
}}
.file-header .slug a:hover {{ border-color: var(--ink); }}
.file-header .summary {{
  font-size: 0.8rem;
  color: var(--ink-soft);
}}

table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}}
th, td {{
  padding: 0.5rem 0.75rem;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid var(--edge);
}}
th {{
  background: #fafafa;
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-soft);
}}
tr:last-child td {{ border-bottom: 0; }}
tr.checked {{ background: #f0f7f0; opacity: 0.6; }}
tr.checked td.behauptung,
tr.checked td.befund,
tr.checked td.fix {{ text-decoration: line-through; }}

td.check {{ width: 32px; }}
td.check input {{ cursor: pointer; transform: scale(1.15); }}
td.n {{ width: 30px; color: var(--ink-faint); font-family: monospace; }}
td.status {{ width: 80px; font-size: 0.85rem; font-weight: 500; }}
td.status.x {{ color: var(--red); }}
td.status.warn {{ color: var(--orange); }}
td.status.ok {{ color: var(--green); }}
td.status.fixed {{ color: var(--blue); }}
td.klasse {{ width: 90px; color: var(--ink-soft); font-size: 0.78rem; }}
td.behauptung {{ width: 25%; }}
td.befund {{ width: 30%; color: var(--ink-soft); }}
td.fix {{ font-style: italic; color: var(--ink); }}

.hidden {{ display: none !important; }}

@media (max-width: 900px) {{
  .controls, main, header, .stats {{ padding-left: 1rem; padding-right: 1rem; }}
  td.klasse, th.klasse {{ display: none; }}
  table {{ font-size: 0.78rem; }}
}}
</style>
</head>
<body>
<header>
  <h1>Fact-Check Findings</h1>
  <div class="meta">Stand: 2026-05-14 · {len(files)} Files · {total_findings} Findings · interaktive Checkliste (Status persistent im Browser)</div>
</header>

<div class="stats">
  <div class="stat x"><span class="v">{counts['x']}</span> <span>✗ falsch</span></div>
  <div class="stat warn"><span class="v">{counts['warn']}</span> <span>⚠ Praezisierung</span></div>
  <div class="stat ok"><span class="v">{counts['ok']}</span> <span>✓ belegt</span></div>
  <div class="stat fixed"><span class="v">{counts['fixed']}</span> <span>FIXED</span></div>
</div>

<div class="controls">
  <strong>Anzeigen:</strong>
  <label><input type="checkbox" data-filter="x" checked> ✗ falsch</label>
  <label><input type="checkbox" data-filter="warn" checked> ⚠ Praezisierung</label>
  <label><input type="checkbox" data-filter="ok"> ✓ belegt</label>
  <label><input type="checkbox" data-filter="fixed"> FIXED</label>
  <strong style="margin-left:1rem">Bereich:</strong>
  <label><input type="checkbox" data-area="publikationen" checked> Publikationen</label>
  <label><input type="checkbox" data-area="themen" checked> Themen</label>
  <label><input type="checkbox" data-area="konzepte" checked> Konzepte</label>
  <input type="text" id="search" placeholder="Volltext-Suche (Slug, Behauptung, Befund)..." />
  <div class="actions">
    <button id="export">Markierte exportieren</button>
    <button id="clear">Auswahl zurücksetzen</button>
  </div>
</div>

<main id="main"></main>

<script>
const DATA = {data};
const STORAGE_KEY = 'dz-factcheck-state-v1';

function loadState() {{
  try {{
    if (typeof localStorage === 'undefined') return {{}};
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{}}');
  }} catch (e) {{ return {{}}; }}
}}
function saveState(state) {{
  try {{
    if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }} catch (e) {{ /* ignore */ }}
}}
const state = loadState();

function statusClass(s) {{
  if (s.includes('FIXED')) return 'fixed';
  if (s.includes('✗')) return 'x';
  if (s.includes('⚠')) return 'warn';
  if (s.includes('✓')) return 'ok';
  return '';
}}

function el(tag, attrs, ...children) {{
  const e = document.createElement(tag);
  if (attrs) {{
    for (const k in attrs) {{
      const v = attrs[k];
      if (v == null) continue;
      if (k === 'class') e.className = v;
      else if (k === 'dataset') {{
        for (const dk in v) e.dataset[dk] = v[dk];
      }}
      else if (k === 'text') e.textContent = v;
      else if (k === 'checked') {{ if (v) e.checked = true; }}
      else e.setAttribute(k, v);
    }}
  }}
  for (const c of children) {{
    if (c == null) continue;
    e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }}
  return e;
}}

window.addEventListener('error', (ev) => {{
  const main = document.getElementById('main');
  if (main) main.innerHTML = '<pre style="color:#c00;padding:1rem;white-space:pre-wrap">JS-Fehler: ' + ev.message + '\\n' + (ev.error && ev.error.stack ? ev.error.stack : '') + '</pre>';
}});

function renderAll() {{
  const main = document.getElementById('main');
  main.innerHTML = '';
  let broken = 0;
  for (const file of DATA) {{
    try {{
      renderFile(main, file);
    }} catch (err) {{
      broken++;
      const errBlock = document.createElement('div');
      errBlock.style.cssText = 'background:#fee;padding:0.5rem;margin:0.5rem 0;border:1px solid #c00;font-family:monospace;font-size:0.8rem';
      errBlock.textContent = 'RENDER-FEHLER fuer ' + (file && file.slug) + ': ' + err.message;
      main.appendChild(errBlock);
    }}
  }}
  if (broken > 0) {{
    const banner = document.createElement('div');
    banner.style.cssText = 'background:#fffbe0;padding:0.75rem 1rem;margin-bottom:1rem;border:1px solid #d68910;font-weight:600';
    banner.textContent = broken + ' Files konnten nicht gerendert werden — siehe rote Bloecke unten';
    main.insertBefore(banner, main.firstChild);
  }}
  applyFilters();
}}

function renderFile(main, file) {{
    const counts = {{x:0,warn:0,ok:0,fixed:0}};
    for (const r of file.rows) counts[statusClass(r.status)]++;
    const parts = [];
    if (counts.x) parts.push('✗ ' + counts.x);
    if (counts.warn) parts.push('⚠ ' + counts.warn);
    if (counts.fixed) parts.push('FIXED ' + counts.fixed);
    parts.push('✓ ' + counts.ok);
    const summary = parts.join(' · ');

    const tbody = el('tbody');
    for (const r of file.rows) {{
      const key = file.slug + ':' + r.n;
      const checked = state[key] || false;
      const sc = statusClass(r.status);
      const cb = el('input', {{type:'checkbox', checked: checked}});
      const tr = el('tr', {{dataset:{{status:sc, key:key}}, class: checked?'checked':''}},
        el('td', {{class:'check'}}, cb),
        el('td', {{class:'n', text: String(r.n)}}),
        el('td', {{class:'status ' + sc, text: r.status}}),
        el('td', {{class:'klasse', text: r.klasse}}),
        el('td', {{class:'behauptung', text: r.behauptung}}),
        el('td', {{class:'befund', text: r.befund}}),
        el('td', {{class:'fix', text: r.fix}})
      );
      cb.addEventListener('change', (e) => {{
        state[key] = e.target.checked;
        saveState(state);
        tr.classList.toggle('checked', e.target.checked);
      }});
      tbody.appendChild(tr);
    }}

    const block = el('div', {{class:'file-block', dataset:{{slug:file.slug, area:file.area}}}},
      el('div', {{class:'file-header'}},
        el('span', {{class:'area-tag area-' + file.area, text: file.area}}),
        el('span', {{class:'slug'}},
          el('a', {{href: '../' + file.area + '/' + file.source_slug + '.md', target:'_blank', text: file.source_slug}})
        ),
        el('span', {{class:'summary', text: summary}})
      ),
      el('table', {{}},
        el('thead', {{}},
          el('tr', {{}},
            el('th'), el('th', {{text:'#'}}), el('th', {{text:'Status'}}),
            el('th', {{class:'klasse', text:'Klasse'}}),
            el('th', {{text:'Behauptung'}}), el('th', {{text:'Befund'}}), el('th', {{text:'Fix-Vorschlag'}})
          )
        ),
        tbody
      )
    );
    main.appendChild(block);
}}

function applyFilters() {{
  const sevFilters = {{}};
  document.querySelectorAll('[data-filter]').forEach(cb => sevFilters[cb.dataset.filter] = cb.checked);
  const areaFilters = {{}};
  document.querySelectorAll('[data-area]').forEach(cb => areaFilters[cb.dataset.area] = cb.checked);
  const q = document.getElementById('search').value.toLowerCase().trim();

  document.querySelectorAll('.file-block').forEach(block => {{
    if (!areaFilters[block.dataset.area]) {{
      block.classList.add('hidden');
      return;
    }}
    let anyVisible = false;
    block.querySelectorAll('tbody tr').forEach(tr => {{
      const matchSev = sevFilters[tr.dataset.status];
      const haystack = (tr.dataset.key + ' ' + tr.textContent).toLowerCase();
      const matchQ = !q || haystack.includes(q);
      const show = matchSev && matchQ;
      tr.classList.toggle('hidden', !show);
      if (show) anyVisible = true;
    }});
    block.classList.toggle('hidden', !anyVisible);
  }});
}}

document.querySelectorAll('[data-filter], [data-area]').forEach(cb => {{
  cb.addEventListener('change', applyFilters);
}});
document.getElementById('search').addEventListener('input', applyFilters);

document.getElementById('clear').addEventListener('click', () => {{
  if (!confirm('Alle Haken zuruecksetzen?')) return;
  for (const k in state) delete state[k];
  saveState(state);
  document.querySelectorAll('tbody tr').forEach(tr => {{
    tr.classList.remove('checked');
    const cb = tr.querySelector('input');
    if (cb) cb.checked = false;
  }});
}});

document.getElementById('export').addEventListener('click', () => {{
  const picks = [];
  for (const file of DATA) {{
    const ids = file.rows.filter(r => state[file.slug + ':' + r.n]).map(r => r.n);
    if (ids.length) picks.push(`${{file.slug}}: ${{ids.join(', ')}}`);
  }}
  if (!picks.length) {{ alert('Nichts markiert.'); return; }}
  const out = 'Zu fixen:\\n' + picks.join('\\n');
  navigator.clipboard.writeText(out).then(() => alert('In Zwischenablage kopiert:\\n\\n' + out));
}});

try {{
  renderAll();
}} catch (err) {{
  document.getElementById('main').innerHTML = '<pre style="color:#c00;padding:1rem;white-space:pre-wrap">JS-Fehler beim Render: ' + err.message + '\\n' + (err.stack || '') + '</pre>';
}}
</script>
</body>
</html>"""

    OUT.write_text(html, encoding="utf-8")
    print(f"OK -> {OUT.relative_to(ROOT)}")
    print(f"   {len(files)} Files, {total_findings} Findings")
    print(f"   ✗ {counts['x']}  ⚠ {counts['warn']}  ✓ {counts['ok']}  FIXED {counts['fixed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
