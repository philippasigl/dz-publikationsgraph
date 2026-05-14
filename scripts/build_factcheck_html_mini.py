"""Mini-Variante: nur 3 Files zum Test."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'scripts')
from build_factcheck_html import parse_report
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FC = ROOT / 'wiki' / '_fact-check'

# Reduce to 3 simple files
test_slugs = ['eine-neue-deutsche-finanzpolitik', 'eine-oekonomisch-sinnvolle-schuldenregel', 'buergergeld']
files = []
for s in test_slugs:
    p = FC / f'{s}.md'
    if p.exists():
        d = parse_report(p)
        if d:
            files.append(d)
sys.stderr.write(f'{len(files)} files\n')
data_json = json.dumps(files, ensure_ascii=False)
sys.stderr.write(f'JSON size: {len(data_json)} bytes\n')

OUT = FC / 'findings-mini.html'

html = '<!doctype html><html><head><meta charset="utf-8"><title>Mini Test</title></head><body style="font-family:sans-serif;padding:2rem">'
html += '<h1>Mini Test</h1><div id="msg">init</div><div id="out"></div>'
html += '<script>\n'
html += 'const msg = document.getElementById("msg");\n'
html += 'try { msg.textContent = "before DATA"; } catch(e) { msg.textContent = "step0 err: "+e.message; }\n'
html += 'const DATA = ' + data_json + ';\n'
html += 'try { msg.textContent = "DATA loaded: " + DATA.length + " files"; } catch(e) { msg.textContent = "step1 err: "+e.message; }\n'
html += '''try {
  const out = document.getElementById('out');
  for (const f of DATA) {
    const h = document.createElement('h3');
    h.textContent = f.slug + ' (' + f.area + ') — ' + f.rows.length + ' rows';
    out.appendChild(h);
    const tbl = document.createElement('table');
    tbl.border = 1;
    tbl.style.borderCollapse = 'collapse';
    for (const r of f.rows) {
      const tr = document.createElement('tr');
      const c1 = document.createElement('td'); c1.textContent = r.n; tr.appendChild(c1);
      const c2 = document.createElement('td'); c2.textContent = r.status; tr.appendChild(c2);
      const c3 = document.createElement('td'); c3.textContent = r.behauptung; tr.appendChild(c3);
      tbl.appendChild(tr);
    }
    out.appendChild(tbl);
  }
  msg.textContent = 'ALL OK';
} catch(e) { msg.textContent = 'render err: '+e.message+'\\n'+e.stack; msg.style.whiteSpace='pre'; msg.style.color='red'; }
</script></body></html>'''

OUT.write_text(html, encoding='utf-8')
sys.stderr.write(f'-> {OUT.relative_to(ROOT)}')
