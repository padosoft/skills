#!/usr/bin/env python3
"""
new_skill.py - Scaffolding di una nuova skill Padosoft conforme alle convenzioni del repo.

Crea skills/padosoft-<nome>/ con SKILL.md compilato dal template, le cartelle di supporto e un file
di eval gia' impostato. Non tocca CATALOG.md ne' profiles.json: quelli si rigenerano con `make catalog`.

Uso:
    python3 skills/padosoft-skill-creator/scripts/new_skill.py laravel-conventions \\
        --profiles laravel api --scope project --title "Convenzioni Laravel Padosoft"

    python3 .../new_skill.py email-sequence --profiles email --dry-run

Opzioni principali:
    --profiles P [P...]   Profili dichiarati (obbligatorio, devono esistere in KNOWN_PROFILES)
    --scope {project,global}   Default: project. 'global' richiede il profilo core.
    --title TESTO         Titolo umano del file (default: derivato dal nome)
    --with-scripts        Crea anche scripts/ con uno scheletro di validatore
    --dry-run             Mostra cosa creerebbe, senza scrivere

Exit code: 0 creata | 1 input non valido o skill gia' esistente | 2 errore di esecuzione
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]          # skills/padosoft-skill-creator
REPO_ROOT = SKILL_ROOT.parents[1]                          # radice del repo
SKILLS_DIR = REPO_ROOT / "skills"
TEMPLATE = SKILL_ROOT / "templates" / "SKILL.template.md"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

VALIDATOR_STUB = '''#!/usr/bin/env python3
"""
{name}_check.py - Validatore della skill {name}.

Sostituisci questa logica con i controlli reali del dominio. Requisiti Padosoft:
solo standard library, nessun prompt interattivo, --help con esempi, exit code distinti.

Uso: python3 scripts/{name}_check.py <input> [--json]
Exit code: 0 ok | 1 problemi trovati | 2 errore di esecuzione
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

    # Guard: input presente
    if not args.target.exists():
        print(f"Non trovato: {{args.target}}", file=sys.stderr)
        return 2

    problems: list[str] = []
    # TODO: controlli del dominio

    if args.json:
        print(json.dumps({{"target": str(args.target), "problems": problems}}, ensure_ascii=False, indent=2))
    else:
        for p in problems:
            print(f"  - {{p}}")
        print(f"\\nProblemi: {{len(problems)}} | esito: {{'FAIL' if problems else 'PASS'}}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
'''

EVALS = """[
  { "query": "<richiesta realistica che DEVE attivare la skill, senza nominare il dominio>", "should_trigger": true },
  { "query": "<richiesta esplicita nel dominio>", "should_trigger": true },
  { "query": "<richiesta con file path e contesto personale>", "should_trigger": true },
  { "query": "<near-miss: stesso dominio, compito che spetta a un'altra skill>", "should_trigger": false },
  { "query": "<near-miss: parole chiave simili, dominio diverso>", "should_trigger": false }
]
"""

REFERENCE_STUB = """# Riferimenti di {title}

Materiale di dettaglio caricato **su richiesta**. In SKILL.md scrivi quando leggerlo, per esempio:
"apri `references/{slug}.md` quando il comando risponde con un errore 4xx".

## <Sezione>

<contenuto>
"""


def load_known_profiles() -> tuple[str, ...]:
    """Legge KNOWN_PROFILES da scripts/build_catalog.py per non duplicare l'elenco."""
    build = REPO_ROOT / "scripts" / "build_catalog.py"
    if not build.is_file():
        return ()
    m = re.search(r"KNOWN_PROFILES: tuple\[str, \.\.\.\] = \(([^)]*)\)", build.read_text(encoding="utf-8"), re.S)
    if not m:
        return ()
    return tuple(p.strip().strip('"\'') for p in m.group(1).split(",") if p.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="nome senza prefisso, es. laravel-conventions")
    ap.add_argument("--profiles", nargs="+", required=True)
    ap.add_argument("--scope", choices=("project", "global"), default="project")
    ap.add_argument("--title", default=None)
    ap.add_argument("--with-scripts", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    slug = args.name if args.name.startswith("padosoft-") else f"padosoft-{args.name}"

    # Guard: nome conforme alla specifica
    if not NAME_RE.match(slug) or len(slug) > 64:
        print(f"Nome non valido: {slug!r} (solo [a-z0-9-], max 64, niente trattini doppi)", file=sys.stderr)
        return 1

    known = load_known_profiles()
    if known:
        unknown = [p for p in args.profiles if p not in known]
        if unknown:
            print(f"Profili sconosciuti: {', '.join(unknown)} (ammessi: {', '.join(known)})", file=sys.stderr)
            return 1

    # Guard: coerenza global/core, la stessa regola che applica la CI
    if args.scope == "global" and "core" not in args.profiles:
        print("scope global richiede il profilo 'core' (vedi CONTRIBUTING.md)", file=sys.stderr)
        return 1

    target = SKILLS_DIR / slug
    if target.exists():
        print(f"Esiste gia': {target.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1
    if not TEMPLATE.is_file():
        print(f"Template mancante: {TEMPLATE}", file=sys.stderr)
        return 2

    title = args.title or slug.replace("padosoft-", "").replace("-", " ").title()
    skill_md = (TEMPLATE.read_text(encoding="utf-8")
                .replace("{{name}}", slug)
                .replace("{{profili}}", ", ".join(args.profiles))
                .replace("{{scope}}", args.scope)
                .replace("{{Titolo}}", title)
                .replace("{{parole chiave separate da virgola}}", ", ".join(args.profiles)))

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
        print(f"Creerei {target.relative_to(REPO_ROOT)}:")
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
        print(f"Errore di scrittura: {exc}", file=sys.stderr)
        return 2

    print(f"Creata {target.relative_to(REPO_ROOT)}")
    print("\nProssimi passi:")
    print("  1. compila description e corpo di SKILL.md (vedi la skill padosoft-skill-creator, §4 e §5)")
    print(f"  2. aggiungi {slug} a un pacchetto in plugins/")
    print("  3. make catalog && make all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
