#!/usr/bin/env python3
"""
validate_plugins.py - Checks the Claude Code plugin manifests of the monorepo.

Checks: valid JSON, name identical to the plugin folder, every path in "skills"
existing, and every skill of the repo covered by at least one plugin (otherwise it would be
installable through npx skills but invisible to whoever uses the marketplace).

Usage: python3 scripts/validate_plugins.py
Exit code: 0 ok | 1 inconsistencies | 2 execution error
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"


def main() -> int:
    problems: list[str] = []

    if not MARKETPLACE.is_file():
        print(f"Missing {MARKETPLACE.relative_to(ROOT)}", file=sys.stderr)
        return 2

    try:
        market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"invalid marketplace.json: {exc}", file=sys.stderr)
        return 1

    for key in ("name", "owner", "plugins"):
        if key not in market:
            problems.append(f"marketplace.json: missing '{key}'")

    covered: set[str] = set()
    for entry in market.get("plugins", []):
        src = ROOT / str(entry.get("source", "")).lstrip("./")
        manifest = src / ".claude-plugin" / "plugin.json"
        if not manifest.is_file():
            problems.append(f"{entry.get('name')}: missing manifest in {manifest.relative_to(ROOT)}")
            continue
        try:
            plugin = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{manifest.relative_to(ROOT)}: invalid JSON ({exc})")
            continue
        if plugin.get("name") != src.name:
            problems.append(f"{src.name}: 'name' ({plugin.get('name')!r}) differs from the folder")
        if plugin.get("name") != entry.get("name"):
            problems.append(f"{src.name}: name differs between marketplace.json and plugin.json")
        for rel in plugin.get("skills", []):
            target = (src / rel).resolve()
            if not (target / "SKILL.md").is_file():
                problems.append(f"{src.name}: skill does not exist '{rel}'")
            else:
                covered.add(target.name)

    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        if skill_md.parent.name not in covered:
            problems.append(f"{skill_md.parent.name}: no plugin includes it (add it to a package)")

    if problems:
        print("Problems in the plugins:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"Plugins ok: {len(market.get('plugins', []))} packages, {len(covered)} skills covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
