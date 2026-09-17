#!/usr/bin/env python3
"""
validate_plugins.py - Verifica i manifest dei plugin Claude Code del monorepo.

Controlla: JSON valido, nome uguale alla cartella del plugin, ogni percorso in "skills"
esistente, e ogni skill del repo coperta da almeno un plugin (altrimenti sarebbe
installabile via npx skills ma invisibile a chi usa il marketplace).

Uso: python3 scripts/validate_plugins.py
Exit code: 0 ok | 1 incoerenze | 2 errore di esecuzione
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
        print(f"Manca {MARKETPLACE.relative_to(ROOT)}", file=sys.stderr)
        return 2

    try:
        market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"marketplace.json non valido: {exc}", file=sys.stderr)
        return 1

    for key in ("name", "owner", "plugins"):
        if key not in market:
            problems.append(f"marketplace.json: manca '{key}'")

    covered: set[str] = set()
    for entry in market.get("plugins", []):
        src = ROOT / str(entry.get("source", "")).lstrip("./")
        manifest = src / ".claude-plugin" / "plugin.json"
        if not manifest.is_file():
            problems.append(f"{entry.get('name')}: manifest mancante in {manifest.relative_to(ROOT)}")
            continue
        try:
            plugin = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{manifest.relative_to(ROOT)}: JSON non valido ({exc})")
            continue
        if plugin.get("name") != src.name:
            problems.append(f"{src.name}: 'name' ({plugin.get('name')!r}) diverso dalla cartella")
        if plugin.get("name") != entry.get("name"):
            problems.append(f"{src.name}: nome diverso fra marketplace.json e plugin.json")
        for rel in plugin.get("skills", []):
            target = (src / rel).resolve()
            if not (target / "SKILL.md").is_file():
                problems.append(f"{src.name}: skill inesistente '{rel}'")
            else:
                covered.add(target.name)

    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        if skill_md.parent.name not in covered:
            problems.append(f"{skill_md.parent.name}: nessun plugin la include (aggiungila a un pacchetto)")

    if problems:
        print("Problemi nei plugin:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"Plugin ok: {len(market.get('plugins', []))} pacchetti, {len(covered)} skill coperte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
