#!/usr/bin/env python3
"""List render() template paths vs files on disk. Run from project root."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def template_dirs():
    dirs = [ROOT / "templates"]
    dirs.extend(p for p in ROOT.glob("*/templates") if p.is_dir())
    return dirs


def existing_templates():
    found = set()
    for td in template_dirs():
        for p in td.rglob("*.html"):
            found.add(str(p.relative_to(td)).replace("\\", "/"))
    return found


def render_calls():
    renders = []
    for py in ROOT.rglob("*.py"):
        parts = py.parts
        if any(x in parts for x in (".git", "venv", "migrations")):
            continue
        try:
            src = py.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in re.finditer(r"render\s*\(\s*request\s*,\s*['\"]([^'\"]+)['\"]", src):
            renders.append({"file": str(py.relative_to(ROOT)), "template": m.group(1)})
    return renders


def main():
    templates = existing_templates()
    renders = render_calls()
    missing = [r for r in renders if r["template"] not in templates]

    print(f"Templates on disk: {len(templates)}")
    print(f"render() calls: {len(renders)}")
    print(f"Missing: {len(missing)}")
    for m in sorted(missing, key=lambda x: x["template"]):
        print(f"  MISSING  {m['template']}  ({m['file']})")

    out = ROOT / "docs" / "template_inventory.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Template inventory (render vs filesystem)\n\n",
        "Regenerate: `python scripts/check_template_inventory.py`\n\n",
        "## Missing templates\n\n",
    ]
    if missing:
        for m in sorted(missing, key=lambda x: x["template"]):
            lines.append(f"- `{m['template']}` — `{m['file']}`\n")
    else:
        lines.append("_None_\n")
    lines.append("\n## All render() calls\n\n")
    for r in sorted(renders, key=lambda x: x["template"]):
        status = "OK" if r["template"] in templates else "MISSING"
        lines.append(f"- [{status}] `{r['template']}` — `{r['file']}`\n")
    out.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
