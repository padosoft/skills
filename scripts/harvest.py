#!/usr/bin/env python3
"""Find what changed in the know-how files of the repositories you harvest from.

The deterministic half of a harvest: it reads a list of sources, finds their
knowledge files (lessons, rules, skills, decision records, docs), compares them
against a ledger of what was already considered, and prints a work order of what
is new, changed or gone. It decides nothing about content — that is the agent's
job, and `padosoft-knowhow-harvest` is the skill that does it.

    python3 scripts/harvest.py scan                     # the work order
    python3 scripts/harvest.py scan --json              # same, machine-readable
    python3 scripts/harvest.py scan --id laravel-app    # one source only
    python3 scripts/harvest.py record <key> covered --skill padosoft-x --note "..."
    python3 scripts/harvest.py adopt --id <source>      # what to thin in that repo
    python3 scripts/harvest.py status                   # what is still pending

The ledger is written only by `record`, never by `scan`: a session that dies
half way must not leave everything marked as processed.

Exit codes: 0 nothing to do | 1 there is work (or a problem) | 2 usage error.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / ".harvest-sources.json"
DEFAULT_LEDGER = ROOT / ".harvest-ledger.json"

#: Where know-how tends to live. A source can override this list.
DEFAULT_GLOBS: tuple[str, ...] = (
    "LESSON.md",
    "LESSONS.md",
    "docs/LESSON.md",
    "docs/LESSONS.md",
    ".claude/rules/*.md",
    ".claude/rules/**/*.md",
    ".claude/skills/*/SKILL.md",
    ".agents/skills/*/SKILL.md",
    "docs/adr/*.md",
    "docs/security/*.md",
    "docs/RULES.md",
    "AGENTS.md",
    "CLAUDE.md",
)

SKIP_DIRS = {".git", "node_modules", "vendor", "__pycache__", ".venv", "dist", "build"}
MAX_BYTES = 2 * 1024 * 1024
OUTCOMES = ("covered", "rejected", "pending")


@dataclass
class Finding:
    key: str
    source: str
    path: str
    state: str          # new | changed | gone | unreadable
    size: int = 0
    added_lines: int = 0
    outcome: str = ""
    note: str = ""


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    scanned: int = 0
    sources: int = 0
    problems: list[str] = field(default_factory=list)


def die(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def load_json(path: Path, what: str) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(die(f"cannot read the {what} ({path}): {exc}"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def iter_source_files(base: Path, globs: tuple[str, ...]) -> list[Path]:
    """Files matching any glob, walked once so a large tree stays cheap."""
    wanted: list[Path] = []
    plain = [g for g in globs if "*" not in g]
    patterns = [g for g in globs if "*" in g]

    for rel in plain:
        candidate = base / rel
        if candidate.is_file():
            wanted.append(candidate)

    if patterns:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                path = Path(dirpath) / name
                rel = path.relative_to(base).as_posix()
                if any(fnmatch.fnmatch(rel, p) for p in patterns):
                    wanted.append(path)

    return sorted(set(wanted))


def scan(sources: dict, ledger: dict, only: str | None) -> Report:
    report = Report()
    entries: dict = ledger.get("entries", {})
    seen_keys: set[str] = set()

    for source in sources.get("sources", []):
        source_id = str(source.get("id", "")).strip()
        raw_path = str(source.get("path", "")).strip()
        if not source_id or not raw_path:
            report.problems.append(f"a source is missing 'id' or 'path': {source!r}")
            continue
        if only and source_id != only:
            continue

        report.sources += 1
        base = Path(os.path.expandvars(raw_path)).expanduser()
        # A source that cannot be read is a finding, never a silent skip.
        if not base.is_dir():
            report.problems.append(f"{source_id}: path not found ({raw_path})")
            continue

        globs = tuple(source.get("globs") or DEFAULT_GLOBS)
        for path in iter_source_files(base, globs):
            rel = path.relative_to(base).as_posix()
            key = f"{source_id}|{rel}"
            seen_keys.add(key)
            try:
                size = path.stat().st_size
                if size > MAX_BYTES:
                    report.findings.append(Finding(key, source_id, rel, "unreadable", size))
                    continue
                data = path.read_bytes()
            except OSError as exc:
                report.problems.append(f"{key}: {exc}")
                continue

            report.scanned += 1
            digest = sha(data)
            known = entries.get(key)
            if known is None:
                report.findings.append(Finding(key, source_id, rel, "new", size,
                                               added_lines=data.count(b"\n") + 1))
            elif known.get("hash") != digest:
                before = int(known.get("lines", 0))
                after = data.count(b"\n") + 1
                report.findings.append(Finding(key, source_id, rel, "changed", size,
                                               added_lines=max(0, after - before),
                                               outcome=known.get("outcome", ""),
                                               note=known.get("note", "")))

    for key, known in entries.items():
        if key in seen_keys:
            continue
        source_id = key.split("|", 1)[0]
        if only and source_id != only:
            continue
        if known.get("state") == "gone":
            continue
        report.findings.append(Finding(key, source_id, key.split("|", 1)[1], "gone",
                                       outcome=known.get("outcome", ""), note=known.get("note", "")))
    return report


def catalogue() -> list[tuple[str, str, str, str]]:
    """(name, summary, profiles, scope) for every skill, so the agent can match a finding to one."""
    out: list[tuple[str, str, str, str]] = []
    profiles_file = ROOT / "profiles.json"
    scopes = json.loads(profiles_file.read_text(encoding="utf-8")).get("scope", {}) if profiles_file.is_file() else {}
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        head = text.split("\n---\n", 2)[0] if text.startswith("---") else ""
        summary = profiles = ""
        for line in head.splitlines():
            stripped = line.strip()
            if stripped.startswith("summary:"):
                summary = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("profiles:"):
                profiles = stripped.split(":", 1)[1].strip()
        name = skill_md.parent.name
        out.append((name, summary, profiles, scopes.get(name, "")))
    return out


def print_work_order(report: Report, show_catalogue: bool) -> None:
    by_state: dict[str, list[Finding]] = {}
    for f in report.findings:
        by_state.setdefault(f.state, []).append(f)

    print(f"# Harvest work order — {date.today().isoformat()}")
    print()
    print(f"Sources scanned: {report.sources} · files read: {report.scanned} · "
          f"findings: {len(report.findings)}")
    print()

    if report.problems:
        print("## Problems (these are findings, not skips)")
        print()
        for p in report.problems:
            print(f"- {p}")
        print()

    labels = {
        "new": "New — never considered",
        "changed": "Changed since it was last considered",
        "gone": "Gone from the source — check whether a rule now rests on nothing",
        "unreadable": "Too large to read in one pass — split or exclude deliberately",
    }
    for state in ("new", "changed", "gone", "unreadable"):
        items = by_state.get(state, [])
        if not items:
            continue
        print(f"## {labels[state]} ({len(items)})")
        print()
        for f in items:
            extra = f"  ·  +{f.added_lines} lines" if f.added_lines else ""
            prior = f"  ·  previously: {f.outcome}" + (f" ({f.note})" if f.note else "") if f.outcome else ""
            print(f"- `{f.key}`{extra}{prior}")
        print()

    if show_catalogue:
        print("## Current catalogue, to match findings against")
        print()
        print("| Skill | The rule | Profiles | Scope |")
        print("|---|---|---|---|")
        for name, summary, profiles, scope in catalogue():
            print(f"| `{name}` | {summary} | {profiles} | {scope} |")
        print()

    print("---")
    print()
    print("Next: read the changed files, decide, then record each key with")
    print("`python3 scripts/harvest.py record <key> covered|rejected --skill <name> --note \"<why>\"`.")
    print("Nothing is written to the ledger until you do.")


def cmd_scan(args: argparse.Namespace) -> int:
    sources = load_json(Path(args.sources), "sources file")
    if not sources.get("sources"):
        return die(f"no sources configured in {args.sources} — copy .harvest-sources.example.json")
    ledger = load_json(Path(args.ledger), "ledger")
    report = scan(sources, ledger, args.id)

    if args.as_json:
        print(json.dumps({
            "date": date.today().isoformat(),
            "sources": report.sources,
            "scanned": report.scanned,
            "problems": report.problems,
            "findings": [f.__dict__ for f in report.findings],
            "catalogue": [{"name": n, "summary": s, "profiles": p, "scope": sc}
                          for n, s, p, sc in catalogue()],
        }, indent=2, ensure_ascii=False))
    else:
        print_work_order(report, show_catalogue=not args.no_catalogue)

    return 1 if (report.findings or report.problems) else 0


def cmd_record(args: argparse.Namespace) -> int:
    if args.outcome not in OUTCOMES:
        return die(f"outcome must be one of {', '.join(OUTCOMES)}")
    if args.outcome == "covered" and not args.skill:
        return die("'covered' needs --skill: the whole point is knowing where it went")
    if args.outcome == "rejected" and not args.note:
        return die("'rejected' needs --note: a reason, so nobody re-mines it")

    sources = load_json(Path(args.sources), "sources file")
    ledger = load_json(Path(args.ledger), "ledger")
    ledger.setdefault("version", 1)
    entries = ledger.setdefault("entries", {})

    source_id, _, rel = args.key.partition("|")
    if not rel:
        return die("key must be '<source-id>|<relative/path.md>'")

    base = None
    for source in sources.get("sources", []):
        if str(source.get("id")) == source_id:
            base = Path(os.path.expandvars(str(source.get("path", "")))).expanduser()
    digest, lines = "", 0
    if base is not None and (base / rel).is_file():
        data = (base / rel).read_bytes()
        digest, lines = sha(data), data.count(b"\n") + 1
    elif args.outcome != "rejected":
        return die(f"{args.key}: file not found — record 'rejected' if the source is gone")

    entries[args.key] = {
        "hash": digest,
        "lines": lines,
        "considered": date.today().isoformat(),
        "outcome": args.outcome,
        "skill": args.skill or "",
        "note": args.note or "",
        "state": "gone" if not digest else "present",
    }
    ledger["last_record"] = date.today().isoformat()
    Path(args.ledger).write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8", newline="\n")
    print(f"recorded {args.key} → {args.outcome}" + (f" ({args.skill})" if args.skill else ""))
    return 0


def cmd_adopt(args: argparse.Namespace) -> int:
    """Per source, the local files a skill now covers — the list to thin down to its binding."""
    ledger = load_json(Path(args.ledger), "ledger")
    entries = ledger.get("entries", {})
    if not entries:
        print("Ledger empty: run a harvest first, the adoption list comes out of it.")
        return 1

    by_source: dict[str, list[tuple[str, str]]] = {}
    for key, e in entries.items():
        if e.get("outcome") != "covered" or e.get("state") == "gone":
            continue
        source_id, _, rel = key.partition("|")
        if args.id and source_id != args.id:
            continue
        by_source.setdefault(source_id, []).append((rel, e.get("skill", "")))

    if not by_source:
        print("Nothing covered yet for that source.")
        return 1

    print(f"# Adoption list — {date.today().isoformat()}")
    print()
    print("Each file below has its general rule in an installed skill. Thin it to the **binding**:")
    print("what that rule means *here* — the table, the helper, the path, the documented exception —")
    print("and a line naming the skill. Do not delete it unless nothing project-specific is left,")
    print("and do not leave the full copy: two copies of one rule drift, and the agent reads both.")
    print()
    for source_id in sorted(by_source):
        rows = sorted(by_source[source_id])
        print(f"## `{source_id}` — {len(rows)} files")
        print()
        for rel, skill in rows:
            print(f"- `{rel}`  →  **{skill}**")
        print()
    print("---")
    print()
    print("Derived instruction files for other agents follow the same thinning, or you have just")
    print("created a disagreement — see `padosoft-agent-instructions-sync`.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ledger = load_json(Path(args.ledger), "ledger")
    entries = ledger.get("entries", {})
    if not entries:
        print("Ledger empty: nothing has been considered yet.")
        return 1
    counts: dict[str, int] = {}
    by_skill: dict[str, int] = {}
    for key, e in entries.items():
        counts[e.get("outcome", "?")] = counts.get(e.get("outcome", "?"), 0) + 1
        if e.get("skill"):
            by_skill[e["skill"]] = by_skill.get(e["skill"], 0) + 1
    print(f"Ledger: {len(entries)} files considered · last record {ledger.get('last_record', '—')}")
    for outcome, n in sorted(counts.items()):
        print(f"  {outcome:<10} {n}")
    if by_skill:
        print("\nSources feeding each skill (independent convergence is what earns a promotion):")
        for name, n in sorted(by_skill.items(), key=lambda kv: -kv[1]):
            print(f"  {n:>3}  {name}")
    pending = [k for k, e in entries.items() if e.get("outcome") == "pending"]
    if pending:
        print(f"\nStill pending ({len(pending)}):")
        for k in pending[:20]:
            print(f"  {k}")
    return 1 if pending else 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default=str(DEFAULT_SOURCES))
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    sub = ap.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="print the work order")
    s.add_argument("--id", help="only this source")
    s.add_argument("--json", action="store_true", dest="as_json")
    s.add_argument("--no-catalogue", action="store_true")
    s.set_defaults(func=cmd_scan)

    r = sub.add_parser("record", help="write the outcome of one file into the ledger")
    r.add_argument("key", help="<source-id>|<relative/path.md>")
    r.add_argument("outcome", choices=OUTCOMES)
    r.add_argument("--skill")
    r.add_argument("--note")
    r.set_defaults(func=cmd_record)

    ad = sub.add_parser("adopt", help="the local files a skill now covers, to thin to their binding")
    ad.add_argument("--id", help="only this source")
    ad.set_defaults(func=cmd_adopt)

    st = sub.add_parser("status", help="what has been considered, and what is pending")
    st.set_defaults(func=cmd_status)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(2)
