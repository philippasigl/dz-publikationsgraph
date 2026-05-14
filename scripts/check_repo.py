"""Repo-Cleanup-Check fuer die DZ-Wissensbase.

Prueft das wiki2-Repo gegen die in CLAUDE.md / schemas/ definierten Konventionen
und gegen Fallen, die in der Vergangenheit schon mal passiert sind (z. B. nul-Datei,
Schema-Drift, Sync-Drift, OneDrive-Konfliktkopien).

Aufruf:
    python scripts/check_repo.py             # Read-only Report
    python scripts/check_repo.py --fix       # mit Auto-Fix der idempotenten Befunde
    python scripts/check_repo.py --quiet     # nur Probleme + Summary
    python scripts/check_repo.py --json      # Maschinen-lesbar (fuer CI/Hooks)

Exit-Codes:
    0 = sauber (nach optionalem Fix nichts mehr offen)
    1 = Probleme gefunden (oder unfixable Restprobleme)
    2 = interner Fehler
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent

# Canonical schema (must stay in sync with schemas/frontmatter.schema.json)
VALID_CLUSTERS = {
    "fiskalpolitik", "haushalt", "geldpolitik und anleihemärkte",
    "infra", "wirtschaftspolitik", "makro", "ausland",
}
VALID_FORMATS = {
    "policy-paper", "studie", "geldbrief", "blogpost", "kommentar",
    "stellungnahme", "pressemitteilung", "datenset",
}
REQUIRED_FIELDS = ("title", "date", "authors", "cluster")

# Things that should never appear at repo root or in tracked content
WINDOWS_SHELL_ARTIFACTS = ("nul", "NUL", "con", "CON", "prn", "PRN", "aux", "AUX")
ONEDRIVE_CONFLICT = re.compile(r"_\d+(\.[a-zA-Z0-9]+)?$")  # foo_1.md, bar_2.pdf
PYTHON_CACHE_DIRS = ("__pycache__",)
DOCUSAURUS_GENERATED = ("node_modules", "build", ".docusaurus")

# Files/dirs that legitimately exist in repo root
ROOT_ALLOWED = {
    ".claude", ".git", ".gitattributes", ".github", ".gitignore", ".mcp.json",
    "CLAUDE.md", "LICENSE", "README.md",
    ".ruff_cache", "pyproject.toml",
    "Daten", "publikationen", "publikationsgraph", "schemas",
    "scripts", "site", "wiki",
    "dz-wiki-projektstand.md",
}


# ---------------------------------------------------------------------------
# Reporting plumbing
# ---------------------------------------------------------------------------

Severity = str  # "error" | "warning" | "info"


@dataclass
class Finding:
    section: str
    severity: Severity
    message: str
    path: str | None = None
    fix: Callable[[], None] | None = None  # None = not auto-fixable

    def to_dict(self) -> dict:
        return {
            "section": self.section,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "fixable": self.fix is not None,
        }


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def add(self, **kwargs) -> None:
        self.findings.append(Finding(**kwargs))

    def has_errors(self) -> bool:
        return any(f.severity == "error" for f in self.findings)

    def has_actionable(self) -> bool:
        """True if there are errors or warnings (infos don't fail the run)."""
        return any(f.severity in ("error", "warning") for f in self.findings)

    def has_any(self) -> bool:
        return bool(self.findings)

    def fixable(self) -> list[Finding]:
        return [f for f in self.findings if f.fix is not None]


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_root_hygiene(report: Report) -> None:
    """Detect accidental files at repo root (nul, OneDrive _N suffixes, etc.)."""
    for entry in ROOT.iterdir():
        name = entry.name
        if name in ROOT_ALLOWED:
            continue
        if name in WINDOWS_SHELL_ARTIFACTS:
            report.add(
                section="root", severity="error", path=name,
                message=f"Windows shell artifact '{name}' (von `> nul` o.ae.); loeschen",
                fix=(lambda p=entry: p.unlink()),
            )
            continue
        # OneDrive conflict copies: foo_1.md, image_2.png
        m = ONEDRIVE_CONFLICT.search(entry.stem if entry.is_file() else name)
        if m and entry.is_file():
            report.add(
                section="root", severity="warning", path=name,
                message="OneDrive-Konfliktkopie (Suffix _N) — pruefen, dann umbenennen oder loeschen",
            )
            continue
        # Unknown top-level entry — flag for inspection
        report.add(
            section="root", severity="warning", path=name,
            message="Unbekannter Eintrag im Repo-Root — pruefen ob er hier hingehoert",
        )


def check_empty_dirs(report: Report) -> None:
    """Flag empty directories anywhere in the source tree."""
    skip = {"node_modules", "build", ".docusaurus", ".git", "__pycache__"}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        if dirpath == str(ROOT):
            continue
        p = Path(dirpath)
        if not dirnames and not filenames:
            rel = p.relative_to(ROOT)
            report.add(
                section="empty-dirs", severity="warning", path=str(rel),
                message="Leerer Ordner — loeschen oder mit Inhalt fuellen",
                fix=(lambda p=p: p.rmdir()),
            )


def check_python_cache(report: Report) -> None:
    """__pycache__ accumulates from Python runs. Harmless if gitignored — info only."""
    gi = ROOT / ".gitignore"
    gitignored = gi.exists() and "__pycache__" in gi.read_text(encoding="utf-8")
    severity = "info" if gitignored else "warning"
    for cache in ROOT.rglob("__pycache__"):
        if any(part in {"node_modules", ".git"} for part in cache.parts):
            continue
        rel = cache.relative_to(ROOT)
        msg = "Python __pycache__ — loeschen (gitignored, kosmetisch)" if gitignored \
              else "Python __pycache__ — und nicht in .gitignore!"
        report.add(
            section="python-cache", severity=severity, path=str(rel),
            message=msg,
            fix=(lambda p=cache: shutil.rmtree(p, ignore_errors=True)),
        )


def check_gitignore(report: Report) -> None:
    """Ensure .gitignore exists and covers the obvious build artifacts."""
    gi = ROOT / ".gitignore"
    if not gi.exists():
        report.add(
            section="gitignore", severity="error", path=".gitignore",
            message="Fehlt — bitte anlegen mit __pycache__/, site/node_modules/, site/build/ usw.",
        )
        return
    text = gi.read_text(encoding="utf-8")
    required_patterns = ["__pycache__", "node_modules", "site/build", "nul"]
    missing = [p for p in required_patterns if p not in text]
    if missing:
        report.add(
            section="gitignore", severity="warning", path=".gitignore",
            message=f"Fehlende Patterns: {', '.join(missing)}",
        )


def check_temp_folders(report: Report) -> None:
    """temp/, tmp/, scratch/ at root are scratch space that shouldn't persist."""
    for name in ("temp", "tmp", "scratch"):
        p = ROOT / name
        if p.exists():
            report.add(
                section="temp-folders", severity="warning", path=name,
                message="Temp-Ordner im Root — Inhalte pruefen, dann loeschen",
            )


# ---- Frontmatter / Schema ---------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict | None, str]:
    """Naive YAML frontmatter parser. Returns (frontmatter, body) or (None, body)."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    fm_text = text[4:end]
    try:
        import yaml
        fm = yaml.safe_load(fm_text)
        if not isinstance(fm, dict):
            return None, text[end + 4:]
        return fm, text[end + 4:]
    except Exception:
        return None, text[end + 4:]


def check_frontmatter(report: Report) -> None:
    """Validate every publication's frontmatter against the canonical schema."""
    pub_dir = ROOT / "wiki" / "publikationen"
    if not pub_dir.exists():
        return
    for md in sorted(pub_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        rel = md.relative_to(ROOT).as_posix()
        if fm is None:
            report.add(section="frontmatter", severity="error", path=rel,
                       message="Kein gueltiges YAML-Frontmatter")
            continue
        # Skip ignored papers (translations etc.). YAML `ignore: yes` parses as bool True.
        ignore_val = fm.get("ignore")
        if ignore_val is True or str(ignore_val).strip().lower() == "yes":
            continue
        # Legacy field
        if "node" in fm and "cluster" not in fm:
            report.add(section="frontmatter", severity="error", path=rel,
                       message="Verwendet legacy Feld `node:` statt `cluster:` — pdf-ingestion-Skema einhalten")
            continue
        # Required fields
        for field_name in REQUIRED_FIELDS:
            if field_name not in fm or fm[field_name] in (None, "", []):
                report.add(section="frontmatter", severity="error", path=rel,
                           message=f"Pflichtfeld `{field_name}` fehlt")
        # Cluster value
        cluster = fm.get("cluster")
        if isinstance(cluster, list):
            report.add(section="frontmatter", severity="error", path=rel,
                       message=f"`cluster` ist Liste {cluster!r} — muss einzelner String sein")
        elif cluster and cluster not in VALID_CLUSTERS:
            report.add(section="frontmatter", severity="error", path=rel,
                       message=f"Ungueltiger Cluster '{cluster}' — erlaubt: {sorted(VALID_CLUSTERS)}")
        # Format value
        fmt = fm.get("format")
        if fmt and fmt not in VALID_FORMATS:
            report.add(section="frontmatter", severity="warning", path=rel,
                       message=f"Ungewoehnlicher format-Wert '{fmt}' — erlaubt: {sorted(VALID_FORMATS)}")
        # Date format
        date = str(fm.get("date", ""))
        if date and not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            report.add(section="frontmatter", severity="error", path=rel,
                       message=f"Datum '{date}' nicht im Format YYYY-MM-DD")


def check_schema_consistency(report: Report) -> None:
    """The canonical cluster list must match across schema files."""
    schema_json = ROOT / "schemas" / "frontmatter.schema.json"
    if not schema_json.exists():
        report.add(section="schema", severity="error", path=str(schema_json.relative_to(ROOT)),
                   message="Fehlt")
        return
    try:
        schema = json.loads(schema_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report.add(section="schema", severity="error", path="schemas/frontmatter.schema.json",
                   message=f"Ungueltiges JSON: {e}")
        return
    schema_clusters = set(schema["properties"]["cluster"]["enum"])
    if schema_clusters != VALID_CLUSTERS:
        diff = schema_clusters.symmetric_difference(VALID_CLUSTERS)
        report.add(section="schema", severity="error", path="schemas/frontmatter.schema.json",
                   message=f"Cluster-Liste weicht von check_repo.py ab (Diff: {sorted(diff)})")


def check_legacy_skills(report: Report) -> None:
    """The skills/ folder at repo root is a misplaced skill (should be .claude/skills/)."""
    if (ROOT / "skills").exists():
        report.add(section="skills", severity="error", path="skills/",
                   message="Skills muessen unter .claude/skills/ liegen — verschieben")
    if (ROOT / ".claude" / "commands").exists():
        report.add(section="skills", severity="warning", path=".claude/commands/",
                   message="Commands-Ordner — pruefen ob Inhalt nicht besser als Skill unter .claude/skills/ liegt")


# ---- Sync-Drift between source and site/ ------------------------------------

def check_sync_drift(report: Report) -> None:
    """wiki/ + publikationen/ + publikationsgraph/ must mirror to site/."""
    pairs = [
        (ROOT / "wiki" / "publikationen", ROOT / "site" / "docs" / "publikationen", "*.md"),
        (ROOT / "wiki" / "themen", ROOT / "site" / "docs" / "themen", "*.md"),
        (ROOT / "wiki" / "konzepte", ROOT / "site" / "docs" / "konzepte", "*.md"),
        (ROOT / "publikationen", ROOT / "site" / "static" / "publikationen", "*.pdf"),
    ]
    drift = False
    for src, dst, pattern in pairs:
        if not src.exists() or not dst.exists():
            continue
        src_names = {f.name for f in src.glob(pattern)}
        dst_names = {f.name for f in dst.glob(pattern)}
        only_src = src_names - dst_names
        only_dst = dst_names - src_names
        if only_src or only_dst:
            drift = True
            rel = src.relative_to(ROOT).as_posix()
            msg = f"Sync-Drift {rel}: +{len(only_src)} fehlt im site/, -{len(only_dst)} verwaist im site/"
            report.add(section="sync", severity="warning", path=rel, message=msg)
    if drift:
        # Single fixable entry that runs the sync.
        def _fix():
            subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_to_site.py")],
                           check=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        # Replace last warning with a fixable variant
        report.findings[-1].fix = _fix


def check_graph_consistency(report: Report) -> None:
    """publikationsgraph/data.json must validate and not drift from wiki/."""
    gj = ROOT / "publikationsgraph" / "data.json"
    if not gj.exists():
        report.add(section="graph", severity="error", path="publikationsgraph/data.json",
                   message="Fehlt")
        return
    try:
        graph = json.loads(gj.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report.add(section="graph", severity="error", path="publikationsgraph/data.json",
                   message=f"Ungueltiges JSON: {e}")
        return
    node_ids = {n["id"] for n in graph.get("nodes", []) if "id" in n}
    date_by_id = {n["id"]: n.get("date", "") for n in graph.get("nodes", []) if "id" in n}
    edges = graph.get("edges", [])
    edge_targets = set()
    for e in edges:
        edge_targets.update([e.get("from"), e.get("to")])
    dangling = {t for t in edge_targets if t and t not in node_ids}
    if dangling:
        report.add(section="graph", severity="error", path="publikationsgraph/data.json",
                   message=f"{len(dangling)} Edges zeigen auf nicht-existierende Nodes: "
                           f"{sorted(dangling)[:5]}{'...' if len(dangling) > 5 else ''}")

    # Confidence: jede Edge muss `confidence` haben mit gueltigem Wert
    VALID_CONFIDENCE = {"hoch", "mittel", "niedrig"}
    missing_conf = [e for e in edges if not e.get("confidence")]
    invalid_conf = [e for e in edges if e.get("confidence") and e["confidence"] not in VALID_CONFIDENCE]
    if missing_conf:
        sample = [f"{e.get('from')}->{e.get('to')}" for e in missing_conf[:3]]
        report.add(section="graph", severity="error", path="publikationsgraph/data.json",
                   message=f"{len(missing_conf)} Edges ohne `confidence` — Pflichtfeld; Beispiele: {sample}")
    if invalid_conf:
        sample = [f"{e.get('from')}->{e.get('to')}: '{e['confidence']}'" for e in invalid_conf[:3]]
        report.add(section="graph", severity="error", path="publikationsgraph/data.json",
                   message=f"{len(invalid_conf)} Edges mit ungueltiger confidence; Beispiele: {sample}")
    # Wiki vs graph drift
    pub_dir = ROOT / "wiki" / "publikationen"
    if pub_dir.exists():
        wiki_slugs = {p.stem for p in pub_dir.glob("*.md")}
        # Don't flag intentionally-ignored papers
        ignored = set()
        try:
            import yaml
            for md in pub_dir.glob("*.md"):
                fm, _ = parse_frontmatter(md.read_text(encoding="utf-8"))
                if fm:
                    iv = fm.get("ignore")
                    if iv is True or str(iv).strip().lower() == "yes":
                        ignored.add(md.stem)
        except Exception:
            pass
        missing_from_graph = wiki_slugs - node_ids - ignored
        orphan_in_graph = node_ids - wiki_slugs
        if missing_from_graph:
            sample = sorted(missing_from_graph)[:5]
            report.add(section="graph", severity="warning", path="publikationsgraph/data.json",
                       message=f"{len(missing_from_graph)} wiki-Publikationen nicht im Graph: {sample}"
                               f"{'...' if len(missing_from_graph) > 5 else ''}")
        if orphan_in_graph:
            sample = sorted(orphan_in_graph)[:5]
            report.add(section="graph", severity="error", path="publikationsgraph/data.json",
                       message=f"{len(orphan_in_graph)} Graph-Nodes ohne wiki-MD: {sample}"
                               f"{'...' if len(orphan_in_graph) > 5 else ''}")


# ---- Slugs / Naming / Potential duplicates ----------------------------------

def check_slugs(report: Report) -> None:
    """Slugs should be lowercase, ASCII, hyphen-separated."""
    pub_dir = ROOT / "wiki" / "publikationen"
    if not pub_dir.exists():
        return
    bad = re.compile(r"[^a-z0-9\-]")
    for md in pub_dir.glob("*.md"):
        slug = md.stem
        if bad.search(slug):
            rel = md.relative_to(ROOT).as_posix()
            report.add(section="slugs", severity="warning", path=rel,
                       message="Dateiname enthaelt Umlaute/Sonderzeichen/Grossbuchstaben")


def check_potential_duplicates(report: Report) -> None:
    """Heuristic: titles with very similar normalized form may be the same paper."""
    pub_dir = ROOT / "wiki" / "publikationen"
    if not pub_dir.exists():
        return
    by_norm: dict[str, list[str]] = {}
    for md in pub_dir.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        if not fm or not fm.get("title"):
            continue
        # Normalize: lowercase, only alphanumeric, drop short words
        title = re.sub(r"[^a-z0-9 ]", "", fm["title"].lower())
        keywords = sorted(w for w in title.split() if len(w) > 4)
        key = " ".join(keywords[:6])
        if not key:
            continue
        by_norm.setdefault(key, []).append(md.relative_to(ROOT).as_posix())
    for key, paths in by_norm.items():
        if len(paths) > 1:
            report.add(section="duplicates", severity="warning", path=paths[0],
                       message=f"Moegliche Dublette von {paths[1:]}: gleiche Titel-Keywords")


# ---- Markdown-level hygiene --------------------------------------------------

def check_wikilinks(report: Report) -> None:
    """Wikilinks in wiki/publikationen/ should resolve to existing slugs."""
    pub_dir = ROOT / "wiki" / "publikationen"
    if not pub_dir.exists():
        return
    slugs = {p.stem for p in pub_dir.glob("*.md")}
    link_re = re.compile(r"\[\[([^\]]+)\]\]")

    def to_slug(s: str) -> str:
        s = s.lower()
        s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        s = re.sub(r"[^a-z0-9\s-]", "", s)
        return re.sub(r"\s+", "-", s).strip("-")

    # Build a fuzzy lookup: stripped-keyword sets per slug
    def keyword_set(s: str) -> frozenset[str]:
        return frozenset(w for w in re.split(r"-|\s+", s.lower()) if len(w) > 4)

    slug_keywords = {s: keyword_set(s) for s in slugs}

    for md in pub_dir.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        rel = md.relative_to(ROOT).as_posix()
        for raw in link_re.findall(text):
            target = raw.strip()
            if target in slugs or to_slug(target) in slugs:
                continue
            # Fuzzy: if 50%+ of target's keywords appear in any slug, accept
            target_kw = keyword_set(target)
            if not target_kw:
                continue
            if any(len(target_kw & sk) / len(target_kw) >= 0.5 for sk in slug_keywords.values()):
                continue
            report.add(section="wikilinks", severity="info", path=rel,
                       message=f"Wikilink [[{target}]] hat kein eindeutiges Ziel im Wiki")


# ---- Stale debug leftovers ---------------------------------------------------

DEBUG_PATTERNS = re.compile(r"#\s*(TODO|FIXME|XXX|HACK)\b")  # only matches in comments

def check_debug_leftovers(report: Report) -> None:
    """Heads-up on TODOs/FIXMEs in script comments — they often outlive their reason."""
    scripts_dir = ROOT / "scripts"
    if not scripts_dir.exists():
        return
    self_path = Path(__file__).resolve()
    for py in scripts_dir.glob("*.py"):
        if py.resolve() == self_path:
            continue  # the check itself mentions these tokens
        rel = py.relative_to(ROOT).as_posix()
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if DEBUG_PATTERNS.search(line):
                report.add(section="debug-leftovers", severity="info",
                           path=f"{rel}:{i}",
                           message=line.strip()[:120])


# ---- Large files outside expected paths -------------------------------------

def check_large_unexpected_files(report: Report) -> None:
    """A PDF outside publikationen/ or site/static/ is probably an accident."""
    expected_pdf_roots = (
        ROOT / "publikationen",
        ROOT / "site" / "static" / "publikationen",
        ROOT / "site" / "build",  # Docusaurus copies static/ into build/
    )
    for pdf in ROOT.rglob("*.pdf"):
        if any(part in {"node_modules", ".git"} for part in pdf.parts):
            continue
        if any(str(pdf).startswith(str(e)) for e in expected_pdf_roots):
            continue
        rel = pdf.relative_to(ROOT).as_posix()
        report.add(section="large-files", severity="warning", path=rel,
                   message=f"PDF ausserhalb publikationen/ und site/static/ ({pdf.stat().st_size // 1024} KB)")


# ---- Reverse-Chronology --------------------------------------------------

def check_reverse_chronology(report: Report) -> None:
    """Edges duerfen nicht von einem aelteren auf ein neueres Papier zeigen.

    Konvention: `from` ist das neuere Papier, das auf `to` (aelter) aufbaut.
    Uebersetzungspaare werden via `ignore: yes` rausgefiltert bevor sie im
    Graph landen — sie tauchen hier also gar nicht erst auf.

    KEIN auto-fix: edges.csv ist Quelle der Wahrheit, Aenderungen erfolgen
    dort manuell. Sonst koennen wir versehentlich CSV-Edits ueberschreiben.
    """
    gj = ROOT / "publikationsgraph" / "data.json"
    if not gj.exists():
        return
    try:
        d = json.loads(gj.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    date_by_id = {n["id"]: n.get("date", "") for n in d.get("nodes", []) if "id" in n}

    for e in d.get("edges", []):
        f, t = e.get("from"), e.get("to")
        if not (f and t and f in date_by_id and t in date_by_id):
            continue
        fd, td = date_by_id[f], date_by_id[t]
        if fd and td and fd < td:
            report.add(section="reverse-chronology", severity="warning",
                       path="publikationsgraph/edges.csv",
                       message=f"{f} ({fd}) -> {t} ({td}): from-Datum aelter als to-Datum — in edges.csv pruefen/flippen")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECKS = [
    check_root_hygiene,
    check_empty_dirs,
    check_python_cache,
    check_gitignore,
    check_temp_folders,
    check_legacy_skills,
    check_schema_consistency,
    check_frontmatter,
    check_graph_consistency,
    check_reverse_chronology,
    check_sync_drift,
    check_slugs,
    check_potential_duplicates,
    check_wikilinks,
    check_debug_leftovers,
    check_large_unexpected_files,
]


SEV_ORDER = {"error": 0, "warning": 1, "info": 2}
SEV_COLOR = {"error": "ERR ", "warning": "WARN", "info": "INFO"}


def _message_template(msg: str) -> str:
    """Strip out path-like specifics so similar messages group together."""
    # e.g. "Ungueltiger Cluster 'foo' — erlaubt: [...]" -> "Ungueltiger Cluster — erlaubt: [...]"
    msg = re.sub(r"'[^']{1,80}'", "'…'", msg)
    msg = re.sub(r"\d+", "N", msg)
    return msg


def print_text_report(report: Report, quiet: bool) -> None:
    n_err = sum(1 for f in report.findings if f.severity == "error")
    n_warn = sum(1 for f in report.findings if f.severity == "warning")
    n_info = sum(1 for f in report.findings if f.severity == "info")
    if not report.findings:
        print("OK: Repo ist sauber.")
        return
    if quiet and n_err == 0 and n_warn == 0:
        print(f"OK: Repo ist sauber ({n_info} Infos unterdrueckt — ohne --quiet sichtbar).")
        return
    print(f"\nGefunden: {len(report.findings)} Befunde "
          f"({n_err} Errors, {n_warn} Warnings, {n_info} Infos)\n")

    by_section: dict[str, list[Finding]] = {}
    for f in report.findings:
        by_section.setdefault(f.section, []).append(f)

    for section, items in sorted(by_section.items()):
        items.sort(key=lambda f: SEV_ORDER[f.severity])
        if quiet and all(f.severity == "info" for f in items):
            continue

        # Group repeated message templates within a section.
        groups: dict[tuple[str, str], list[Finding]] = {}
        for f in items:
            if quiet and f.severity == "info":
                continue
            groups.setdefault((f.severity, _message_template(f.message)), []).append(f)
        if not groups:
            continue

        print(f"== {section} ==")
        for (severity, _tmpl), group in groups.items():
            sample = group[0]
            fix_marker = " [fixable]" if sample.fix else ""
            if len(group) == 1:
                path = f" {sample.path}" if sample.path else ""
                print(f"  [{SEV_COLOR[severity]}]{path}  {sample.message}{fix_marker}")
            else:
                print(f"  [{SEV_COLOR[severity]}] {len(group)}x  {sample.message}{fix_marker}")
                for f in group[:3]:
                    if f.path:
                        print(f"         - {f.path}")
                if len(group) > 3:
                    print(f"         - ... (+{len(group) - 3} weitere)")
        print()


def run_fixes(report: Report) -> int:
    fixable = report.fixable()
    if not fixable:
        return 0
    print(f"\nAuto-Fix: {len(fixable)} Eintraege werden gefixt...")
    applied = 0
    for f in fixable:
        try:
            f.fix()
            print(f"  [FIXED] {f.section}: {f.path or f.message}")
            applied += 1
        except Exception as e:
            print(f"  [FAIL ] {f.section}: {f.path or f.message} -- {e}")
    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true",
                        help="Auto-Fix der idempotent reparierbaren Befunde anwenden")
    parser.add_argument("--quiet", action="store_true",
                        help="Nur Errors und Warnings, keine Infos")
    parser.add_argument("--json", action="store_true",
                        help="Maschinen-lesbarer Output (fuer Hooks)")
    args = parser.parse_args(argv)

    report = Report()
    try:
        for check in CHECKS:
            check(report)
    except Exception as e:
        print(f"INTERNAL ERROR: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({
            "findings": [f.to_dict() for f in report.findings],
            "errors": sum(1 for f in report.findings if f.severity == "error"),
            "warnings": sum(1 for f in report.findings if f.severity == "warning"),
            "infos": sum(1 for f in report.findings if f.severity == "info"),
        }, indent=2))
    else:
        print_text_report(report, args.quiet)

    if args.fix:
        applied = run_fixes(report)
        if applied:
            print(f"\n{applied} Befunde gefixt. Erneuter Check:")
            report2 = Report()
            for check in CHECKS:
                check(report2)
            if args.json:
                print(json.dumps({
                    "findings": [f.to_dict() for f in report2.findings],
                }, indent=2))
            else:
                print_text_report(report2, args.quiet)
            return 1 if report2.has_actionable() else 0

    return 1 if report.has_actionable() else 0


if __name__ == "__main__":
    sys.exit(main())
