"""Statisches HTML ohne JavaScript: Tabelle mit Checkboxen pro Finding.

Filter wird via <details>-Sections und CSS-only realisiert.
"""
from __future__ import annotations
import sys, io, re
from pathlib import Path
from html import escape

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
FC_DIR = ROOT / "wiki" / "_fact-check"
OUT = FC_DIR / "findings-static.html"

ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$")


def classify_area(slug: str) -> str:
    for area in ("publikationen", "themen", "konzepte"):
        if (ROOT / "wiki" / area / f"{slug}.md").exists():
            return area
    if slug.endswith("-konzept"):
        return "konzepte"
    return "?"


def parse_report(path: Path):
    slug = path.stem
    if slug.startswith("_"):
        return None
    text = path.read_text(encoding="utf-8")
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        n, status, klasse, behauptung, befund, fix = m.groups()
        if n == "#":
            continue
        rows.append({
            "n": int(n), "status": status.strip(), "klasse": klasse.strip(),
            "behauptung": behauptung.strip(), "befund": befund.strip(), "fix": fix.strip(),
        })
    if not rows:
        return None
    actual_slug = slug.replace("-konzept", "") if slug.endswith("-konzept") else slug
    area = "konzepte" if slug.endswith("-konzept") else classify_area(slug)
    return {"slug": slug, "source_slug": actual_slug, "area": area, "rows": rows}


def status_class(s: str) -> str:
    if "FIXED" in s: return "fixed"
    if "✗" in s: return "x"
    if "⚠" in s: return "warn"
    if "✓" in s: return "ok"
    return ""


def render():
    files = []
    for p in sorted(FC_DIR.glob("*.md")):
        d = parse_report(p)
        if d:
            files.append(d)

    counts = {"x": 0, "warn": 0, "ok": 0, "fixed": 0, "": 0}
    for f in files:
        for r in f["rows"]:
            counts[status_class(r["status"])] += 1
    counts.pop("", None)

    # Sort files: most ✗+⚠ first
    def open_count(f):
        return sum(1 for r in f["rows"] if status_class(r["status"]) in ("x", "warn"))
    files.sort(key=lambda f: (-open_count(f), f["slug"]))

    parts = ["""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<title>Fact-Check Findings (static) · DZ Wiki</title>
<style>
* { box-sizing: border-box; }
body { font-family: 'Inter', system-ui, sans-serif; margin: 0; background: #fafafa; color: #1a1a2e; font-size: 14px; }
header { background: #1a1a2e; color: #fff; padding: 1.5rem 2rem 1rem; }
header h1 { margin: 0 0 0.4rem; font-size: 1.4rem; }
header .meta { color: #b0b0c0; font-size: 0.85rem; }
.stats { display: flex; gap: 1.5rem; padding: 0.75rem 2rem; background: #fff; border-bottom: 1px solid #e8e8e8; font-size: 0.9rem; }
.stats b { font-size: 1.1rem; }
.stat.x b { color: #c0392b; }
.stat.warn b { color: #d68910; }
.stat.ok b { color: #2d8a47; }
.stat.fixed b { color: #2c5282; }
main { padding: 1rem 2rem 3rem; }
details { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; margin-bottom: 0.75rem; }
summary { padding: 0.7rem 1rem; cursor: pointer; font-weight: 500; display: flex; gap: 1rem; align-items: baseline; user-select: none; }
summary:hover { background: #f5f5f7; }
summary .tag { font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 3px; color: #fff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.tag-publikationen { background: #2c5282; }
.tag-themen { background: #7a4caf; }
.tag-konzepte { background: #2d8a47; }
summary .slug { flex: 1; font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.85rem; }
summary .slug a { color: #1a1a2e; text-decoration: none; border-bottom: 1px dotted #aaa; }
summary .badges { display: flex; gap: 0.5rem; font-size: 0.78rem; }
summary .b-x { color: #c0392b; font-weight: 600; }
summary .b-warn { color: #d68910; }
summary .b-fixed { color: #2c5282; }
summary .b-ok { color: #2d8a47; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { padding: 0.5rem 0.7rem; text-align: left; vertical-align: top; border-bottom: 1px solid #f0f0f2; }
th { background: #fafafa; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: #5c5c6d; }
tr:last-child td { border-bottom: 0; }
td.n { width: 30px; color: #9090a0; font-family: monospace; }
td.status { width: 90px; font-weight: 500; }
td.status.x { color: #c0392b; }
td.status.warn { color: #d68910; }
td.status.ok { color: #2d8a47; }
td.status.fixed { color: #2c5282; }
td.klasse { width: 90px; color: #5c5c6d; font-size: 0.78rem; }
td.behauptung { width: 25%; }
td.befund { color: #5c5c6d; width: 28%; }
td.fix { font-style: italic; }
td.check { width: 32px; }
td.check input { transform: scale(1.15); cursor: pointer; }
tr.row-x { background: #fef5f5; }
tr.row-warn { background: #fffaf0; }
tr.row-ok { background: #f4faf6; }
tr.row-fixed { background: #f0f4fa; }
.toc { padding: 1rem 2rem; background: #fff; border-bottom: 1px solid #e8e8e8; font-size: 0.85rem; }
.toc a { color: #2c5282; text-decoration: none; margin-right: 0.8rem; border-bottom: 1px dotted #2c5282; }
</style>
</head>
<body>
<header>
<h1>Fact-Check Findings (statisch)</h1>
<div class="meta">Stand: 2026-05-14 · """ + str(len(files)) + """ Files · """ + str(sum(counts.values())) + """ Findings · Klick auf Header oeffnet Tabelle. Sortierung: meiste offene Findings zuerst.</div>
</header>

<div class="stats">
<div class="stat x"><b>""" + str(counts["x"]) + """</b> ✗ falsch</div>
<div class="stat warn"><b>""" + str(counts["warn"]) + """</b> ⚠ Praezisierung</div>
<div class="stat ok"><b>""" + str(counts["ok"]) + """</b> ✓ belegt</div>
<div class="stat fixed"><b>""" + str(counts["fixed"]) + """</b> FIXED</div>
</div>

<main>
"""]

    for f in files:
        fc = {"x": 0, "warn": 0, "ok": 0, "fixed": 0, "": 0}
        for r in f["rows"]:
            fc[status_class(r["status"])] += 1
        badges = []
        if fc["x"]: badges.append(f'<span class="b-x">✗ {fc["x"]}</span>')
        if fc["warn"]: badges.append(f'<span class="b-warn">⚠ {fc["warn"]}</span>')
        if fc["fixed"]: badges.append(f'<span class="b-fixed">FIXED {fc["fixed"]}</span>')
        badges.append(f'<span class="b-ok">✓ {fc["ok"]}</span>')

        open_default = " open" if (fc["x"] + fc["warn"]) > 0 else ""
        parts.append(f'<details{open_default}>')
        parts.append('<summary>')
        parts.append(f'<span class="tag tag-{f["area"]}">{f["area"]}</span>')
        parts.append(f'<span class="slug"><a href="../{f["area"]}/{f["source_slug"]}.md" target="_blank">{f["source_slug"]}</a></span>')
        parts.append(f'<span class="badges">{" · ".join(badges)}</span>')
        parts.append('</summary>')
        parts.append('<table>')
        parts.append('<thead><tr><th></th><th>#</th><th>Status</th><th>Klasse</th><th>Behauptung</th><th>Befund</th><th>Fix-Vorschlag</th></tr></thead>')
        parts.append('<tbody>')
        for r in f["rows"]:
            sc = status_class(r["status"])
            parts.append(f'<tr class="row-{sc}">')
            parts.append('<td class="check"><input type="checkbox"></td>')
            parts.append(f'<td class="n">{r["n"]}</td>')
            parts.append(f'<td class="status {sc}">{escape(r["status"])}</td>')
            parts.append(f'<td class="klasse">{escape(r["klasse"])}</td>')
            parts.append(f'<td class="behauptung">{escape(r["behauptung"])}</td>')
            parts.append(f'<td class="befund">{escape(r["befund"])}</td>')
            parts.append(f'<td class="fix">{escape(r["fix"])}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></details>')

    parts.append('</main></body></html>')
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"OK -> {OUT.relative_to(ROOT)}")
    print(f"   {len(files)} Files, {sum(counts.values())} Findings")
    print(f"   ✗ {counts['x']}  ⚠ {counts['warn']}  ✓ {counts['ok']}  FIXED {counts['fixed']}")


if __name__ == "__main__":
    render()
