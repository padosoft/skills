#!/usr/bin/env python3
"""
build_catalog.py - Genera CATALOG.md e profiles.json dal frontmatter delle skill.

La fonte di verita' e' il frontmatter di ogni SKILL.md:

    metadata:
      profiles: core, laravel        # uno o piu' profili dichiarati dall'autore
      scope: global                  # global | project  (dove va installata)

Lo script NON decide nulla: legge cio' che l'autore ha dichiarato, costruisce
l'indice e, con --check, fallisce se qualcosa non torna (skill senza profilo,
profilo sconosciuto, catalogo non rigenerato). I criteri per scegliere profilo
e scope sono in CONTRIBUTING.md.

Uso:
    python3 scripts/build_catalog.py            # rigenera CATALOG.md e profiles.json
    python3 scripts/build_catalog.py --check    # verifica che siano aggiornati (CI)
    python3 scripts/build_catalog.py --json     # stampa l'indice senza scrivere

Exit code: 0 ok | 1 problemi di coerenza (o file da rigenerare) | 2 errore di esecuzione
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
CATALOG = ROOT / "CATALOG.md"
PROFILES = ROOT / "profiles.json"
REPO = "padosoft/skills"

#: Profili ammessi. Aggiungerne uno e' una decisione esplicita: si modifica questa tupla
#: in PR, cosi' la nascita di un profilo passa da una review come ogni altra scelta.
KNOWN_PROFILES: tuple[str, ...] = (
    "core", "laravel", "node", "react-native", "email", "api", "payments", "data", "devops",
)
KNOWN_SCOPES: tuple[str, ...] = ("global", "project")

GENERATED_START = "<!-- CATALOG:START - generato da scripts/build_catalog.py, non modificare a mano -->"
GENERATED_END = "<!-- CATALOG:END -->"


@dataclass
class Skill:
    name: str
    path: Path
    description: str
    version: str = ""
    profiles: list[str] = field(default_factory=list)
    scope: str = ""

    @property
    def rel(self) -> str:
        return self.path.relative_to(ROOT).as_posix()

    @property
    def install_url(self) -> str:
        return f"https://github.com/{REPO}/tree/main/{self.rel}"

    @property
    def full_description(self) -> str:
        """Description compattata su una riga, per la scheda di dettaglio."""
        return " ".join(self.description.split())

    @property
    def summary(self) -> str:
        """Prima frase della description, per la tabella del catalogo."""
        first = re.split(r"(?<=[.:])\s", self.description.strip(), maxsplit=1)[0]
        return (first[:160] + "…") if len(first) > 160 else first


def parse_frontmatter(text: str) -> dict[str, str]:
    """Frontmatter YAML minimale: chiavi di primo livello + blocchi indentati di metadata."""
    if not text.startswith("---\n"):
        raise ValueError("frontmatter mancante")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise ValueError("frontmatter non chiuso")
    out: dict[str, str] = {}
    key: str | None = None
    buf: list[str] = []
    meta_prefix = False

    def flush() -> None:
        if key:
            out[key] = " ".join(x.strip() for x in buf).strip()

    for raw in text[4:end + 1].splitlines():
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")):
            if meta_prefix:
                m = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*)$", raw)
                if m:
                    flush()
                    key, value = f"metadata.{m.group(1)}", m.group(2).strip()
                    buf = [value] if value else []
                    continue
            buf.append(raw)
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if not m:
            raise ValueError(f"riga non valida nel frontmatter: {raw!r}")
        flush()
        key, value = m.group(1), m.group(2).strip()
        meta_prefix = key == "metadata"
        buf = [] if value in (">", ">-", "|", "|-", "") else [value]
    flush()
    return out


def load_skills() -> tuple[list[Skill], list[str]]:
    """Legge tutte le skill; ritorna (skill, problemi)."""
    skills: list[Skill] = []
    problems: list[str] = []

    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        try:
            fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        except ValueError as exc:
            problems.append(f"{skill_md.relative_to(ROOT)}: {exc}")
            continue

        name = fm.get("name", "")
        folder = skill_md.parent.name
        if name != folder:
            problems.append(f"{folder}: 'name' ({name!r}) diverso dalla cartella")

        profiles = [p.strip() for p in fm.get("metadata.profiles", "").replace(",", " ").split() if p.strip()]
        scope = fm.get("metadata.scope", "").strip()

        # Guard: ogni skill dichiara almeno un profilo e uno scope validi
        if not profiles:
            problems.append(f"{folder}: manca 'metadata.profiles' (vedi CONTRIBUTING.md)")
        for p in profiles:
            if p not in KNOWN_PROFILES:
                problems.append(f"{folder}: profilo sconosciuto '{p}' (ammessi: {', '.join(KNOWN_PROFILES)})")
        if scope not in KNOWN_SCOPES:
            problems.append(f"{folder}: 'metadata.scope' deve essere global o project (trovato {scope!r})")
        if scope == "global" and "core" not in profiles:
            problems.append(f"{folder}: scope global richiede il profilo 'core'")

        skills.append(Skill(
            name=name or folder,
            path=skill_md.parent,
            description=fm.get("description", "").strip(),
            version=fm.get("metadata.version", "").strip(),
            profiles=profiles,
            scope=scope,
        ))

    if not skills:
        problems.append("nessuna skill trovata in skills/*/SKILL.md")
    return skills, problems


def build_profiles(skills: list[Skill]) -> dict[str, object]:
    by_profile: dict[str, list[str]] = {p: [] for p in KNOWN_PROFILES}
    for s in skills:
        for p in s.profiles:
            if p in by_profile:
                by_profile[p].append(s.name)
    return {
        "repo": REPO,
        "profiles": {p: sorted(v) for p, v in by_profile.items() if v},
        "scope": {s.name: s.scope for s in sorted(skills, key=lambda x: x.name)},
    }


def build_catalog(skills: list[Skill], profiles: dict) -> str:
    lines: list[str] = [GENERATED_START, ""]
    lines.append(f"_{len(skills)} skill · indice generato automaticamente, non modificare a mano._\n")
    lines.append("| Skill | Profili | Scope | Cosa fa |")
    lines.append("|---|---|---|---|")
    for s in sorted(skills, key=lambda x: x.name):
        lines.append(f"| [`{s.name}`]({s.install_url}) | {', '.join(s.profiles)} | {s.scope} | {s.summary} |")
    lines.append("")
    lines.append("## Profili")
    lines.append("")
    for p, names in profiles["profiles"].items():
        lines.append(f"- **{p}** — {', '.join(f'`{n}`' for n in names)}")
    lines.append("")
    lines.append("## Installazione per profilo")
    lines.append("")
    lines.append("```bash")
    lines.append("./scripts/install-profile.sh core --global      # trasversali, su tutti i progetti")
    lines.append("./scripts/install-profile.sh laravel email      # lo stack di questo progetto")
    lines.append("```")
    lines.append("")
    lines.append("## Installazione di una singola skill")
    lines.append("")
    lines.append("```bash")
    for s in sorted(skills, key=lambda x: x.name):
        lines.append(f"npx skills add {s.install_url}")
    lines.append("```")
    lines.append("")
    lines.append(GENERATED_END)
    return "\n".join(lines) + "\n"


README = ROOT / "README.md"
README_START = "<!-- SKILLS:START - generato da scripts/build_catalog.py, non modificare a mano -->"
README_END = "<!-- SKILLS:END -->"


def build_readme_section(skills: list[Skill], profiles: dict) -> str:
    """Schede di dettaglio delle skill per il README: cosa fa, quando si attiva, scope, come si installa."""
    lines: list[str] = [README_START, ""]
    lines.append(f"_{len(skills)} skill in catalogo. Sezione generata dal frontmatter: si aggiorna con `make catalog`._")
    lines.append("")
    lines.append("| Skill | Profili | Scope | Versione |")
    lines.append("|---|---|---|---|")
    for s in sorted(skills, key=lambda x: (x.scope != "global", x.name)):
        anchor = s.name.replace("padosoft-", "")
        lines.append(f"| [`{s.name}`](#{anchor}) | {', '.join(s.profiles)} | {s.scope} | {s.version or '—'} |")
    lines.append("")

    for s in sorted(skills, key=lambda x: (x.scope != "global", x.name)):
        anchor = s.name.replace("padosoft-", "")
        where = ("installata **globalmente** con il profilo `core`: vale su ogni progetto"
                 if s.scope == "global" else
                 "installata **nel progetto** che ne ha bisogno, non globalmente")
        lines.append(f"### {anchor}")
        lines.append("")
        lines.append(f"**`{s.name}`** · profili: {', '.join(f'`{p}`' for p in s.profiles)} · "
                     f"scope: `{s.scope}` · versione: {s.version or '—'}")
        lines.append("")
        lines.append(f"**Quando si attiva** — {s.full_description}")
        lines.append("")
        lines.append(f"**Dove va** — {where}. Cartella: [`{s.rel}`]({s.rel}).")
        lines.append("")
        lines.append("```bash")
        lines.append(f"npx skills add {s.install_url}")
        lines.append("```")
        lines.append("")

    lines.append(README_END)
    return "\n".join(lines) + "\n"


def inject_readme(body: str) -> None:
    """Riscrive la sezione delle skill nel README, se i marcatori sono presenti."""
    if not README.is_file():
        return
    text = README.read_text(encoding="utf-8")
    if README_START not in text or README_END not in text:
        return
    pre = text.split(README_START)[0]
    post = text.split(README_END, 1)[1]
    README.write_text(pre + body.rstrip("\n") + post, encoding="utf-8")


def check_readme(body: str) -> bool:
    """True se la sezione del README e' allineata al frontmatter."""
    if not README.is_file():
        return True
    text = README.read_text(encoding="utf-8")
    if README_START not in text:
        return True
    current = README_START + text.split(README_START, 1)[1].split(README_END, 1)[0] + README_END
    return current.strip() == body.strip()


def wrap_catalog(body: str) -> str:
    header = (
        "# Catalogo delle skill Padosoft\n\n"
        "Questo file e' **generato**: si aggiorna leggendo il frontmatter di ogni `SKILL.md`.\n"
        "Per cambiare profilo o scope di una skill si modifica il suo frontmatter, non questo file.\n\n"
    )
    return header + body


ROUTER = SKILLS_DIR / "padosoft-skills-router" / "SKILL.md"


def inject_router(body: str) -> None:
    """Riscrive la sezione Catalogo della skill router, se presente."""
    if not ROUTER.is_file():
        return
    text = ROUTER.read_text(encoding="utf-8")
    if GENERATED_START not in text or GENERATED_END not in text:
        return
    pre = text.split(GENERATED_START)[0]
    post = text.split(GENERATED_END, 1)[1]
    ROUTER.write_text(pre + body.rstrip("\n") + post, encoding="utf-8")


def check_router(body: str) -> bool:
    """True se la sezione Catalogo della router e' allineata."""
    if not ROUTER.is_file():
        return True
    text = ROUTER.read_text(encoding="utf-8")
    if GENERATED_START not in text:
        return True
    current = GENERATED_START + text.split(GENERATED_START, 1)[1].split(GENERATED_END, 1)[0] + GENERATED_END
    return current.strip() == body.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verifica senza scrivere (CI)")
    ap.add_argument("--json", action="store_true", help="stampa l'indice JSON su stdout")
    args = ap.parse_args()

    try:
        skills, problems = load_skills()
    except Exception as exc:
        print(f"Errore di esecuzione: {exc}", file=sys.stderr)
        return 2

    profiles = build_profiles(skills)
    catalog = wrap_catalog(build_catalog(skills, profiles))
    profiles_json = json.dumps(profiles, ensure_ascii=False, indent=2) + "\n"

    if args.json:
        print(profiles_json, end="")
        return 1 if problems else 0

    if problems:
        print("Problemi di coerenza:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    if args.check:
        stale = [f.name for f, new in ((CATALOG, catalog), (PROFILES, profiles_json))
                 if not f.is_file() or f.read_text(encoding="utf-8") != new]
        if not check_router(build_catalog(skills, profiles)):
            stale.append("skills/padosoft-skills-router/SKILL.md")
        if not check_readme(build_readme_section(skills, profiles)):
            stale.append("README.md (sezione SKILLS)")
        if stale:
            print(f"Da rigenerare: {', '.join(stale)} — lancia `make catalog`", file=sys.stderr)
            return 1
        print(f"Catalogo aggiornato: {len(skills)} skill, {len(profiles['profiles'])} profili")
        return 0

    CATALOG.write_text(catalog, encoding="utf-8")
    PROFILES.write_text(profiles_json, encoding="utf-8")
    inject_router(build_catalog(skills, profiles))
    inject_readme(build_readme_section(skills, profiles))
    print(f"Scritti {CATALOG.name} e {PROFILES.name}: {len(skills)} skill, {len(profiles['profiles'])} profili")
    return 0


if __name__ == "__main__":
    sys.exit(main())
