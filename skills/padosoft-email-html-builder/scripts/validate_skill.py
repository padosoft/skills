#!/usr/bin/env python3
"""
validate_skill.py - Validates an Agent Skill against the agentskills.io specification.

Checks: YAML frontmatter present and parsable, `name` (1-64 chars, [a-z0-9-], no leading/trailing/double
hyphens, identical to the directory), `description` (1-1024 chars), `compatibility` (<=500),
unknown fields, the progressive disclosure budget (SKILL.md <= 500 lines / ~5000 tokens),
existence of the files referenced with relative paths and the execute bit of the scripts.

Usage:
    python3 scripts/validate_skill.py [SKILL_DIR] [--json]

Exit code: 0 valid | 1 validation errors | 2 execution error
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
CHARS_PER_TOKEN = 4  # conservative estimate


@dataclass
class Issue:
    level: str  # ERROR | WARN
    message: str


def parse_frontmatter(text: str) -> tuple[dict[str, object], int]:
    """Extracts the minimal YAML frontmatter (top-level keys, scalars, >-/| blocks and maps).

    Deliberately without PyYAML: the validation has to run everywhere with no dependencies.
    Returns (map, number of frontmatter lines).
    """
    if not text.startswith("---\n"):
        raise ValueError("The file does not start with '---': missing frontmatter")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise ValueError("Frontmatter not closed by '---'")
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
            raise ValueError(f"Invalid frontmatter line: {raw!r}")
        flush()
        current_key, value = m.group(1), m.group(2).strip()
        buffer = [] if value in (">", ">-", "|", "|-", "") else [value]
    flush()
    return data, block.count("\n") + 2


def validate(skill_dir: Path) -> list[Issue]:
    issues: list[Issue] = []
    skill_md = skill_dir / "SKILL.md"

    # Guard: SKILL.md must exist
    if not skill_md.is_file():
        return [Issue("ERROR", f"SKILL.md missing in {skill_dir}")]

    text = skill_md.read_text(encoding="utf-8")
    try:
        fm, fm_lines = parse_frontmatter(text)
    except ValueError as exc:
        return [Issue("ERROR", str(exc))]

    # name
    name = str(fm.get("name", ""))
    if not name:
        issues.append(Issue("ERROR", "Missing 'name' field"))
    else:
        if not 1 <= len(name) <= 64:
            issues.append(Issue("ERROR", f"'name' is {len(name)} characters long (1-64 allowed)"))
        if not NAME_RE.match(name):
            issues.append(Issue("ERROR", f"invalid 'name': {name!r} (only [a-z0-9-], no double or edge hyphens)"))
        if name != skill_dir.resolve().name:
            issues.append(Issue("ERROR", f"'name' ({name}) differs from the directory name ({skill_dir.resolve().name})"))

    # description
    desc = str(fm.get("description", ""))
    if not desc:
        issues.append(Issue("ERROR", "Missing 'description' field"))
    elif len(desc) > 1024:
        issues.append(Issue("ERROR", f"'description' is {len(desc)} characters long (max 1024)"))
    elif len(desc) < 40:
        issues.append(Issue("WARN", "'description' very short: the skill may never trigger"))

    # compatibility
    compat = str(fm.get("compatibility", ""))
    if compat and len(compat) > 500:
        issues.append(Issue("ERROR", f"'compatibility' is {len(compat)} characters long (max 500)"))

    # unknown keys
    for key in fm:
        if key not in KNOWN_KEYS:
            issues.append(Issue("WARN", f"Out-of-spec frontmatter key: '{key}'"))

    # budget progressive disclosure
    body = text[len(text) - len(text.split("\n---\n", 1)[-1]):] if "\n---\n" in text else text
    lines = text.count("\n") + 1
    approx_tokens = len(body) // CHARS_PER_TOKEN
    if lines > MAX_LINES:
        issues.append(Issue("WARN", f"SKILL.md di {lines} righe (consigliato <= {MAX_LINES}): sposta materiale in references/"))
    if approx_tokens > MAX_TOKENS:
        issues.append(Issue("WARN", f"SKILL.md ~{approx_tokens} token (consigliato <= {MAX_TOKENS})"))

    # relative references
    for ref in sorted(set(REF_RE.findall(text))):
        if not (skill_dir / ref).exists():
            issues.append(Issue("ERROR", f"Referenced file does not exist: {ref}"))

    # scripts executable and free of CRLF
    for script in sorted((skill_dir / "scripts").glob("*")) if (skill_dir / "scripts").is_dir() else []:
        if script.suffix in (".py", ".sh") and not script.stat().st_mode & 0o111:
            issues.append(Issue("WARN", f"Script not executable: scripts/{script.name} (chmod +x)"))
        if script.suffix == ".sh" and b"\r\n" in script.read_bytes():
            issues.append(Issue("ERROR", f"Script with CRLF line endings: scripts/{script.name}"))

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill_dir", nargs="?", default=".", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    skill_dir = args.skill_dir.resolve()
    if not skill_dir.is_dir():
        print(f"Directory not found: {skill_dir}", file=sys.stderr)
        return 2

    try:
        issues = validate(skill_dir)
    except Exception as exc:
        print(f"Execution error: {exc}", file=sys.stderr)
        return 2

    errors = [i for i in issues if i.level == "ERROR"]
    if args.json:
        print(json.dumps({"skill": str(skill_dir), "errors": len(errors),
                          "issues": [i.__dict__ for i in issues]}, ensure_ascii=False, indent=2))
    else:
        print(f"Skill: {skill_dir}")
        for i in issues:
            print(f"  [{i.level:5}] {i.message}")
        print(f"\nErrors: {len(errors)} | Warnings: {len(issues) - len(errors)} | "
              f"result: {'FAIL' if errors else 'PASS'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
