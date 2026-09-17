#!/usr/bin/env python3
"""
validate_skill.py - Valida un Agent Skill secondo la specifica agentskills.io.

Controlla: frontmatter YAML presente e parsabile, `name` (1-64 char, [a-z0-9-], senza trattini
iniziali/finali/doppi, uguale alla directory), `description` (1-1024 char), `compatibility` (<=500),
campi sconosciuti, budget di progressive disclosure (SKILL.md <= 500 righe / ~5000 token),
esistenza dei file referenziati con path relativi e bit di esecuzione degli script.

Uso:
    python3 scripts/validate_skill.py [SKILL_DIR] [--json]

Exit code: 0 valido | 1 errori di validazione | 2 errore di esecuzione
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KNOWN_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
REF_RE = re.compile(r"`((?:scripts|references|templates|assets)/[A-Za-z0-9._/-]+)`")
MAX_LINES = 500
MAX_TOKENS = 5000
CHARS_PER_TOKEN = 4  # stima conservativa


@dataclass
class Issue:
    level: str  # ERROR | WARN
    message: str


def parse_frontmatter(text: str) -> tuple[dict[str, object], int]:
    """Estrae il frontmatter YAML minimale (chiavi di primo livello, scalari e blocchi >-/| e mappe).

    Volutamente senza PyYAML: la validazione deve girare ovunque senza dipendenze.
    Ritorna (mappa, numero di righe del frontmatter).
    """
    if not text.startswith("---\n"):
        raise ValueError("Il file non inizia con '---': frontmatter mancante")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise ValueError("Frontmatter non chiuso da '---'")
    block = text[4:end + 1]
    data: dict[str, object] = {}
    current_key: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current_key is not None:
            data[current_key] = " ".join(x.strip() for x in buffer).strip()

    for raw in block.splitlines():
        if not raw.strip():
            continue
        if raw.startswith(("  ", "\t")):  # continuazione di un blocco o mappa annidata
            buffer.append(raw)
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if not m:
            raise ValueError(f"Riga di frontmatter non valida: {raw!r}")
        flush()
        current_key, value = m.group(1), m.group(2).strip()
        buffer = [] if value in (">", ">-", "|", "|-", "") else [value]
    flush()
    return data, block.count("\n") + 2


def validate(skill_dir: Path) -> list[Issue]:
    issues: list[Issue] = []
    skill_md = skill_dir / "SKILL.md"

    # Guard: SKILL.md deve esistere
    if not skill_md.is_file():
        return [Issue("ERROR", f"SKILL.md mancante in {skill_dir}")]

    text = skill_md.read_text(encoding="utf-8")
    try:
        fm, fm_lines = parse_frontmatter(text)
    except ValueError as exc:
        return [Issue("ERROR", str(exc))]

    # name
    name = str(fm.get("name", ""))
    if not name:
        issues.append(Issue("ERROR", "Campo 'name' mancante"))
    else:
        if not 1 <= len(name) <= 64:
            issues.append(Issue("ERROR", f"'name' di {len(name)} caratteri (ammessi 1-64)"))
        if not NAME_RE.match(name):
            issues.append(Issue("ERROR", f"'name' non valido: {name!r} (solo [a-z0-9-], senza trattini doppi o ai bordi)"))
        if name != skill_dir.resolve().name:
            issues.append(Issue("ERROR", f"'name' ({name}) diverso dal nome della directory ({skill_dir.resolve().name})"))

    # description
    desc = str(fm.get("description", ""))
    if not desc:
        issues.append(Issue("ERROR", "Campo 'description' mancante"))
    elif len(desc) > 1024:
        issues.append(Issue("ERROR", f"'description' di {len(desc)} caratteri (max 1024)"))
    elif len(desc) < 40:
        issues.append(Issue("WARN", "'description' molto corta: rischia di non attivare la skill"))

    # compatibility
    compat = str(fm.get("compatibility", ""))
    if compat and len(compat) > 500:
        issues.append(Issue("ERROR", f"'compatibility' di {len(compat)} caratteri (max 500)"))

    # chiavi sconosciute
    for key in fm:
        if key not in KNOWN_KEYS:
            issues.append(Issue("WARN", f"Chiave di frontmatter fuori specifica: '{key}'"))

    # budget progressive disclosure
    body = text[len(text) - len(text.split("\n---\n", 1)[-1]):] if "\n---\n" in text else text
    lines = text.count("\n") + 1
    approx_tokens = len(body) // CHARS_PER_TOKEN
    if lines > MAX_LINES:
        issues.append(Issue("WARN", f"SKILL.md di {lines} righe (consigliato <= {MAX_LINES}): sposta materiale in references/"))
    if approx_tokens > MAX_TOKENS:
        issues.append(Issue("WARN", f"SKILL.md ~{approx_tokens} token (consigliato <= {MAX_TOKENS})"))

    # riferimenti relativi
    for ref in sorted(set(REF_RE.findall(text))):
        if not (skill_dir / ref).exists():
            issues.append(Issue("ERROR", f"File referenziato inesistente: {ref}"))

    # script eseguibili e senza CRLF
    for script in sorted((skill_dir / "scripts").glob("*")) if (skill_dir / "scripts").is_dir() else []:
        if script.suffix in (".py", ".sh") and not script.stat().st_mode & 0o111:
            issues.append(Issue("WARN", f"Script non eseguibile: scripts/{script.name} (chmod +x)"))
        if script.suffix == ".sh" and b"\r\n" in script.read_bytes():
            issues.append(Issue("ERROR", f"Script con line ending CRLF: scripts/{script.name}"))

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill_dir", nargs="?", default=".", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    skill_dir = args.skill_dir.resolve()
    if not skill_dir.is_dir():
        print(f"Directory non trovata: {skill_dir}", file=sys.stderr)
        return 2

    try:
        issues = validate(skill_dir)
    except Exception as exc:
        print(f"Errore di esecuzione: {exc}", file=sys.stderr)
        return 2

    errors = [i for i in issues if i.level == "ERROR"]
    if args.json:
        print(json.dumps({"skill": str(skill_dir), "errors": len(errors),
                          "issues": [i.__dict__ for i in issues]}, ensure_ascii=False, indent=2))
    else:
        print(f"Skill: {skill_dir}")
        for i in issues:
            print(f"  [{i.level:5}] {i.message}")
        print(f"\nErrori: {len(errors)} | Avvisi: {len(issues) - len(errors)} | "
              f"esito: {'FAIL' if errors else 'PASS'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
