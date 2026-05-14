"""Normalize frontmatter of wiki/publikationen/*.md to the canonical schema.

One-shot migration: maps legacy `node:` field to `cluster:`, unwraps array clusters,
and fixes non-canonical cluster values. After this runs, every file should use
`cluster: <one of the 7 canonical values>` per schemas/frontmatter.schema.json.

Run from repo root: `python scripts/normalize_frontmatter.py`
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

# UTF-8 stdout/stderr on Windows (no PYTHONIOENCODING prefix required)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "wiki" / "publikationen"

VALID_CLUSTERS = {
    "fiskalpolitik", "haushalt", "geldpolitik und anleihemärkte", "infra",
    "wirtschaftspolitik", "makro", "ausland",
}

# Per-file overrides: filename -> canonical cluster.
# Derived from titles/topics; see CLAUDE.md decision tree.
OVERRIDES: dict[str, str] = {
    # node: "staat" → mostly Bundeshaushalt = haushalt
    "bundeshaushalt-2027-die-34-milliarden-euro-frage.md": "haushalt",
    "bundeshaushaltsmonitor-2026.md": "haushalt",
    "neustart-deutschland.md": "haushalt",
    "zinserhoehungen-wirken-weniger-als-erwartet.md": "geldpolitik und anleihemärkte",
    "zusaetzlichkeit-jetzt-lasst-mal-gut-sein.md": "haushalt",
    # node: "haushalte" → haushalt (public spending on social services)
    "5-milliarden-spielraum-im-sozialstaat-gewinnen.md": "haushalt",
    "bildungsfinanzchaos-wer-bestellt-bezahlt-meist-nicht.md": "haushalt",
    "das-bildungsfinanzgeflecht.md": "haushalt",
    "eine-kurze-fiskalgeschichte-der-deutschen-wohnungspolitik.md": "haushalt",
    "reformen-brauchen-kitas.md": "haushalt",
    "wohnungspolitik-in-einer-teuren-sackgasse.md": "haushalt",
    # node: "unternehmen" → wirtschaftspolitik / infra by topic
    "der-sanierungskostendeckel.md": "haushalt",
    "eigenkapital-fuer-die-energiewende.md": "infra",
    "hawkish-winds-wie-zinsen-die-energiewende-treffen.md": "infra",
    "was-taugt-der-deutschlandfonds.md": "infra",
    # node: "ausland" → mostly ausland; iran inflation = makro
    "us-iran-krieg-inflationsschock-in-der-eu-von-2-prozentpunkten-moeglich.md": "makro",
    # cluster: non-canonical → canonical
    "a-controversial-investment-intel-magdeburg.md": "wirtschaftspolitik",
    "intel-magdeburg-analyse-de.md": "wirtschaftspolitik",
    "emissionshandel-auf-dem-pruefstand.md": "wirtschaftspolitik",
    "lng-climate-and-energy-security-europe.md": "wirtschaftspolitik",
    "public-financing-needs-modernisation-germany-summary.md": "haushalt",
    "sovereign-debt-issuance-monetary-architecture-prussia-1740-1914.md": "geldpolitik und anleihemärkte",
}

# Simple value remaps applied when no override matches.
VALUE_REMAP = {
    "geldpolitik und anleihemärkte": "geldpolitik und anleihemärkte",
    "energie": "infra",
    # Legacy `node` values (4-cluster scheme) → 7-cluster.
    # These only apply when migrating a `node:` line and no override is set.
    "staat": "haushalt",       # default; overrides handle exceptions
    "haushalte": "haushalt",
    "unternehmen": "wirtschaftspolitik",
    # ausland stays ausland
}


def normalize_value(raw: str) -> str:
    """Strip quotes, brackets, and array syntax to get the first cluster value."""
    s = raw.strip()
    # Array form: ["a", "b"]  or  [a, b] — take first element, drop brackets.
    if s.startswith("["):
        s = s.lstrip("[").split(",", 1)[0]
    s = s.strip().strip("[]").strip().strip('"').strip("'").strip()
    return s.lower()


def process(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    changed = False
    new_cluster: str | None = None

    # Decide target cluster.
    if path.name in OVERRIDES:
        new_cluster = OVERRIDES[path.name]
    else:
        for line in lines[:20]:
            m = re.match(r"^(cluster|node):\s*(.+?)\s*$", line)
            if m:
                val = normalize_value(m.group(2))
                val = VALUE_REMAP.get(val, val)
                if val in VALID_CLUSTERS:
                    new_cluster = val
                break

    if new_cluster is None:
        print(f"[SKIP] {path.name}: no cluster/node line found", file=sys.stderr)
        return False
    if new_cluster not in VALID_CLUSTERS:
        print(f"[SKIP] {path.name}: cannot map -> '{new_cluster}'", file=sys.stderr)
        return False

    # Rewrite: replace the first cluster: or node: line; remove any duplicate.
    out: list[str] = []
    in_frontmatter = False
    seen = False
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_frontmatter = True
            out.append(line)
            continue
        if in_frontmatter and line.strip() == "---":
            in_frontmatter = False
            if not seen:
                out.append(f"cluster: {new_cluster}")
                seen = True
                changed = True
            out.append(line)
            continue
        if in_frontmatter and re.match(r"^(cluster|node):", line):
            if not seen:
                out.append(f"cluster: {new_cluster}")
                seen = True
                if line.strip() != f"cluster: {new_cluster}":
                    changed = True
            else:
                changed = True  # dropped duplicate
            continue
        out.append(line)

    if changed:
        path.write_text("\n".join(out), encoding="utf-8")
        print(f"[OK]   {path.name} -> cluster: {new_cluster}")
    return changed


def main() -> int:
    if not PUB.exists():
        print(f"Missing: {PUB}", file=sys.stderr)
        return 1
    total = 0
    changed = 0
    for md in sorted(PUB.glob("*.md")):
        total += 1
        if process(md):
            changed += 1
    print(f"\n{changed}/{total} files updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
