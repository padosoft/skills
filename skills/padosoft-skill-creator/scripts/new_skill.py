#!/usr/bin/env python3
"""
new_skill.py - Scaffolding of a new Padosoft skill that follows the repo conventions.

Creates skills/padosoft-<name>/ with a SKILL.md filled in from the template, the supporting folders and an
eval file already set up. It touches neither CATALOG.md nor profiles.json: those are regenerated with
`make catalog`.

Usage:
    python3 skills/padosoft-skill-creator/scripts/new_skill.py laravel-conventions \\
        --profiles laravel api --scope project --title "Padosoft Laravel conventions"

    python3 .../new_skill.py email-sequence --profiles email --dry-run

Main options:
    --profiles P [P...]   Declared profiles (required, they must exist in KNOWN_PROFILES)
    --scope {project,global}   Default: project. 'global' requires the core profile.
    --title TEXT          Human title of the file (default: derived from the name)
    --with-scripts        Also create scripts/ with a validator skeleton
    --dry-run             Show what it would create, without writing

Exit code: 0 created | 1 invalid input or skill already present | 2 execution error
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]          # skills/padosoft-skill-creator
REPO_ROOT = SKILL_ROOT.parents[1]                          # repo root
SKILLS_DIR = REPO_ROOT / "skills"
TEMPLATE = SKILL_ROOT / "templates" / "SKILL.template.md"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

VALIDATOR_STUB = '''#!/usr/bin/env python3
"""
{name}_check.py - Validator for the {name} skill.

Replace this logic with the real domain checks. Padosoft requirements:
standard library only, no interactive prompts, --help with examples, distinct exit codes.

Usage: python3 scripts/{name}_check.py <input> [--json]
Exit code: 0 ok | 1 problems found | 2 execution error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    # Guard: the input exists
    if not args.target.exists():
        print(f"Not found: {{args.target}}", file=sys.stderr)
        return 2

    problems: list[str] = []
    # TODO: domain checks

    if args.json:
        print(json.dumps({{"target": str(args.target), "problems": problems}}, ensure_ascii=False, indent=2))
    else:
        for p in problems:
            print(f"  - {{p}}")
        print(f"\\nProblems: {{len(problems)}} | result: {{'FAIL' if problems else 'PASS'}}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
'''

EVALS = """[
  { "query": "<realistic request that MUST trigger the skill, without naming the domain>", "should_trigger": true },
  { "query": "<explicit request in the domain>", "should_trigger": true },
  { "query": "<request with a file path and personal context>", "should_trigger": true },
  { "query": "<near miss: same domain, task that belongs to another skill>", "should_trigger": false },
  { "query": "<near miss: similar keywords, different domain>", "should_trigger": false }
]
"""

REFERENCE_STUB = """# References for {title}

Detailed material loaded **on demand**. In SKILL.md write when to read it, for example:
"open `references/{slug}.md` when the command answers with a 4xx error".

## <Section>

<content>
"""


def load_known_profiles() -> tuple[str, ...]:
    """Reads KNOWN_PROFILES from scripts/build_catalog.py so the list is not duplicated."""
    build = REPO_ROOT / "scripts" / "build_catalog.py"
    if not build.is_file():
        return ()
    m = re.search(r"KNOWN_PROFILES: tuple\[str, \.\.\.\] = \(([^)]*)\)", build.read_text(encoding="utf-8"), re.S)
    if not m:
        return ()
    return tuple(p.strip().strip('"\'') for p in m.group(1).split(",") if p.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="name without the prefix, e.g. laravel-conventions")
    ap.add_argument("--profiles", nargs="+", required=True)
    ap.add_argument("--scope", choices=("project", "global"), default="project")
    ap.add_argument("--title", default=None)
    ap.add_argument("--with-scripts", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    slug = args.name if args.name.startswith("padosoft-") else f"padosoft-{args.name}"

    # Guard: name compliant with the specification
    if not NAME_RE.match(slug) or len(slug) > 64:
        print(f"Invalid name: {slug!r} (only [a-z0-9-], max 64, no double hyphens)", file=sys.stderr)
        return 1

    known = load_known_profiles()
    if known:
        unknown = [p for p in args.profiles if p not in known]
        if unknown:
            print(f"Unknown profiles: {', '.join(unknown)} (allowed: {', '.join(known)})", file=sys.stderr)
            return 1

    # Guard: global/core consistency, the same rule CI applies
    if args.scope == "global" and "core" not in args.profiles:
        print("scope global requires the 'core' profile (see CONTRIBUTING.md)", file=sys.stderr)
        return 1

    target = SKILLS_DIR / slug
    if target.exists():
        print(f"Already present: {target.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1
    if not TEMPLATE.is_file():
        print(f"Missing template: {TEMPLATE}", file=sys.stderr)
        return 2

    title = args.title or slug.replace("padosoft-", "").replace("-", " ").title()
    skill_md = (TEMPLATE.read_text(encoding="utf-8")
                .replace("{{name}}", slug)
                .replace("{{profiles}}", ", ".join(args.profiles))
                .replace("{{scope}}", args.scope)
                .replace("{{Title}}", title)
                .replace("{{comma-separated keywords}}", ", ".join(args.profiles)))

    files: dict[Path, str] = {
        target / "SKILL.md": skill_md,
        target / "references" / f"{slug.replace('padosoft-', '')}.md":
            REFERENCE_STUB.format(title=title, slug=slug.replace("padosoft-", "")),
        target / "evals" / "queries.json": EVALS,
    }
    if args.with_scripts:
        files[target / "scripts" / f"{slug.replace('padosoft-', '').replace('-', '_')}_check.py"] = \
            VALIDATOR_STUB.format(name=slug.replace("padosoft-", "").replace("-", "_"))

    if args.dry_run:
        print(f"Would create {target.relative_to(REPO_ROOT)}:")
        for f in files:
            print(f"  - {f.relative_to(target)}")
        return 0

    try:
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            if path.suffix == ".py":
                path.chmod(0o755)
    except OSError as exc:
        print(f"Write error: {exc}", file=sys.stderr)
        return 2

    print(f"Created {target.relative_to(REPO_ROOT)}")
    print("\nNext steps:")
    print("  1. fill in the description and the body of SKILL.md (see the padosoft-skill-creator skill, §4 and §5)")
    print(f"  2. add {slug} to a package in plugins/")
    print("  3. make catalog && make all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
