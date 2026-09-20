#!/usr/bin/env python3
"""Fail when a skill carries provenance: the facts that say where it came from.

A skill is the rule. The story behind it - the date, the customer, the server, the
row id, the person - is *input* to writing the rule and must not survive into an
artifact that gets published and installed by strangers.

This scanner looks for facts, not for topics: a calendar date, an address, a
credential, a long identifier, a path from someone's machine, a term on the
project denylist. Those shapes can only come from a real event.

    python3 check_provenance.py skills/                 # scan every skill
    python3 check_provenance.py skills/my-skill --json   # machine-readable
    python3 check_provenance.py . --denylist ~/.padosoft-denylist

Suppress a genuine false positive with a reason, on the line or the one above it:

    <!-- provenance-ok: TEST-NET range, from the RFC 5737 documentation block -->

Exit codes: 0 clean, 1 findings, 2 usage or execution error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024  # larger than this is a finding, never a skip
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "vendor", "dist", "build"}
SUPPRESS = re.compile(r"provenance-ok:\s*(\S.{2,})")

# Placeholders: a value containing one of these is a template, not a real secret.
PLACEHOLDER = re.compile(
    r"(?i)(your|my|the)[-_]?|xxx|\.\.\.|<|\{\{|changeme|placeholder|example|redacted|dummy|fake|sample"
)
_DOC_IP = re.compile(r"^(?:127\.|0\.0\.0\.0|255\.|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.|8\.8\.8\.8|1\.1\.1\.1)")
_MONTHS = (
    "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    "|gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre"
)


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern[str]
    message: str
    hint: str
    topic: bool = False  # dropped by --topic-ok


RULES: tuple[Rule, ...] = (
    Rule(
        "date",
        re.compile(
            r"\b\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b"
            r"|\b(?:0?[1-9]|[12]\d|3[01])[/.](?:0?[1-9]|1[0-2])[/.](?:19|20)\d{2}\b"
            rf"|\b(?:{_MONTHS})[a-z]*\.?\s+\d{{1,2}},?\s+(?:19|20)\d{{2}}\b"
            rf"|\b\d{{1,2}}\s+(?:{_MONTHS})[a-z]*\s+(?:19|20)\d{{2}}\b"
        ),
        "a calendar date pins the rule to one event",
        "state the condition instead: 'when the payload exceeds the scanner limit', not 'on <date>'",
    ),
    Rule(
        "email",
        re.compile(
            r"\b[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)[A-Za-z0-9.-]+"
            # not a retina asset (img/x@2x.jpg): a file extension is never a TLD
            r"\.(?!(?:jpe?g|png|gif|webp|svg|avif|ico|css|js|mjs|html?|md|py|php|tsx?|jsx?|json|ya?ml|txt|pdf|zip|sql)\b)"
            r"[A-Za-z]{2,}\b"
        ),
        "an address identifies a person or a company",
        "drop it, or use example.com if the shape matters to the reader",
    ),
    Rule(
        "credential",
        re.compile(
            r"AKIA[0-9A-Z]{16}"
            r"|\bgh[pousr]_[A-Za-z0-9]{20,}"
            r"|\bsk-[A-Za-z0-9_-]{20,}"
            r"|\bxox[baprs]-[A-Za-z0-9-]{10,}"
            r"|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."
            r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
            r"|[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/@:]+:[^\s/@]{3,}@"
            r"|\b(?i:(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token))\s*[:=]\s*[\"']?"
            r"[A-Za-z0-9!@#$%^&*_+=./-]{8,}"
        ),
        "a credential, or something shaped like one",
        "rotate it if it is real, then remove it; a placeholder must read as one",
    ),
    Rule(
        "private-host",
        re.compile(r"\b[A-Za-z0-9][A-Za-z0-9-]*\.(?:local|internal|intranet|lan|corp|home|test)\b"),
        "an internal hostname describes someone's infrastructure",
        "describe the role of the host, not its name",
    ),
    Rule(
        "ip-address",
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "an IP address is infrastructure, and a private one is somebody's network",
        "use the documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) or a name",
    ),
    Rule(
        "personal-id",
        re.compile(
            r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b"  # codice fiscale
            r"|\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"  # IBAN
            r"|\b(?:IT|VAT)\s?\d{11}\b"
            r"|\+\d{1,3}[\s.-]?\d[\d\s.-]{7,}\d"  # phone
        ),
        "a personal or fiscal identifier",
        "personal data has no place in a rule; remove it entirely",
    ),
    Rule(
        "identifier",
        re.compile(
            # No ticket-key rule (ABC-123): rule tables use that exact shape for their own ids,
            # and a gate that cries wolf on every rules file is a gate somebody turns off.
            r"\b\d{6,}\b"
            r"|\b(?i:id|uuid|row|order|invoice|user)\s*[:=#]\s*\d{3,}\b"
        ),
        "a real identifier: a row, a ticket, an order",
        "use a placeholder - {id}, <ticket> - so nobody can look it up",
    ),
    Rule(
        "local-path",
        re.compile(
            r"[A-Za-z]:\\+Users\\+(?!<|\{)[A-Za-z0-9._-]+"
            r"|/(?:home|Users)/(?!runner\b|you\b|user\b|<|\{)[A-Za-z0-9._-]+"
        ),
        "an absolute path from the machine it was written on",
        "use a repo-relative path, or ~/ if the home directory matters",
    ),
    Rule(
        "narration",
        re.compile(
            r"\b(?i:our (?:client|customer|tenant)s?)\b"
            # a named party ("the customer <Name>"), not an acronym ("the client IP")
            r"|\bthe (?:client|customer) [A-Z][a-z]{2,}"
            r"|\b(?i:(?:a|the|one|this) (?:client|customer) (?:reported|complained|called|asked|noticed))"
            # provenance-ok: these are the patterns themselves, not instances of them
            r"|\b(?i:we (?:discovered|leaked|were hacked|got breached|lost the))\b"
            r"|\b(?i:(?:was|were|got) (?:leaked|exfiltrated|breached))\b"
            r"|\b(?i:in production (?:we|i|they))\b"
        ),
        "narration: this tells the story instead of stating the rule",
        "rewrite as a defect class - what can go wrong, and what prevents it",
    ),
    Rule(
        "incident-topic",
        # provenance-ok: these are the patterns themselves, not instances of them
        re.compile(r"\b(?i:post-?mortem|data breach|security incident|the leak|root cause analysis)\b"),
        "incident vocabulary",
        "keep the rule, drop the event; pass --topic-ok if the skill is genuinely about incident response",
        topic=True,
    ),
)


@dataclass
class Finding:
    path: str
    line: int
    rule_id: str
    message: str
    hint: str
    excerpt: str

    def as_text(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule_id}] {self.message}\n    {self.excerpt}\n    -> {self.hint}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    suppressed: int = 0
    files: int = 0
    denylist_terms: int = 0


def load_denylist(explicit: str | None, root: Path) -> list[str]:
    """Terms that identify a customer, a brand or a person. One per line, # comments."""
    candidates = [explicit] if explicit else [os.environ.get("PROVENANCE_DENYLIST"), str(root / ".provenance-denylist")]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if not path.is_file():
            continue
        terms = []
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            term = raw.split("#", 1)[0].strip()
            if term:
                terms.append(term)
        return terms
    return []


def iter_files(target: Path, report: Report) -> list[Path]:
    """Collect files to scan. Anything unreadable is a finding, never a silent skip."""
    if target.is_file():
        return [target]
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink() and not str(path.resolve()).startswith(str(target.resolve())):
                report.findings.append(
                    Finding(str(path), 0, "symlink-escape", "a symlink leaving the scanned tree", "remove it", "")
                )
                continue
            found.append(path)
    return sorted(found)


def read_text(path: Path, report: Report) -> str | None:
    try:
        size = path.stat().st_size
    except OSError as exc:  # pragma: no cover - filesystem level
        report.findings.append(Finding(str(path), 0, "unreadable", f"cannot stat: {exc}", "check permissions", ""))
        return None
    if size > MAX_BYTES:
        report.findings.append(
            Finding(str(path), 0, "too-large", f"{size} bytes exceeds the scan limit", "split it or exclude it", "")
        )
        return None
    try:
        raw = path.read_bytes()
    except OSError as exc:  # pragma: no cover - filesystem level
        report.findings.append(Finding(str(path), 0, "unreadable", f"cannot read: {exc}", "check permissions", ""))
        return None
    if b"\x00" in raw[:8192] and not raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return None  # genuinely binary
    return raw.decode("utf-8", errors="replace").replace("\x00", "")


def scan_line(text: str, rules: tuple[Rule, ...], denylist: list[str]) -> list[tuple[str, str, str, str]]:
    """Return (rule_id, message, hint, match) for every hit on one line."""
    hits: list[tuple[str, str, str, str]] = []
    for rule in rules:
        for match in rule.pattern.finditer(text):
            value = match.group(0)
            if rule.rule_id == "credential" and PLACEHOLDER.search(value):
                continue
            if rule.rule_id == "ip-address" and _DOC_IP.match(value):
                continue
            hits.append((rule.rule_id, rule.message, rule.hint, value))
    lowered = text.lower()
    for term in denylist:
        if term.lower() in lowered:
            hits.append(("denylist", f"'{term}' is on the project denylist", "remove every mention", term))
    return hits


def scan_file(path: Path, rules: tuple[Rule, ...], denylist: list[str], report: Report) -> None:
    content = read_text(path, report)
    if content is None:
        return
    report.files += 1
    lines = content.splitlines()
    for number, line in enumerate(lines, start=1):
        hits = scan_line(line, rules, denylist)
        if not hits:
            continue
        previous = lines[number - 2] if number >= 2 else ""
        if SUPPRESS.search(line) or SUPPRESS.search(previous):
            report.suppressed += len(hits)
            continue
        for rule_id, message, hint, value in hits:
            excerpt = line.strip()
            if len(excerpt) > 120:
                start = max(0, line.find(value) - 40)
                excerpt = "..." + line[start : start + 120].strip() + "..."
            report.findings.append(Finding(str(path), number, rule_id, message, hint, excerpt))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when a skill carries the provenance of the work it was learned from.",
        epilog="Examples:\n"
        "  python3 check_provenance.py skills/\n"
        "  python3 check_provenance.py skills/padosoft-api-security-review --json\n"
        "  PROVENANCE_DENYLIST=~/.padosoft-denylist python3 check_provenance.py skills/\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="+", help="files or directories to scan")
    parser.add_argument("--denylist", help="file of customer/brand/person terms, one per line")
    parser.add_argument("--topic-ok", action="store_true", help="allow incident vocabulary (incident-response skills)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):  # an excerpt carries the scanned file's own characters
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    targets = [Path(p) for p in args.paths]
    missing = [str(t) for t in targets if not t.exists()]
    if missing:
        print(f"error: path not found: {', '.join(missing)}", file=sys.stderr)
        return 2

    rules = tuple(r for r in RULES if not (args.topic_ok and r.topic))
    root = Path.cwd()
    denylist = load_denylist(args.denylist, root)

    report = Report(denylist_terms=len(denylist))
    for target in targets:
        for path in iter_files(target, report):
            scan_file(path, rules, denylist, report)

    if args.as_json:
        print(
            json.dumps(
                {
                    "files": report.files,
                    "findings": [f.__dict__ for f in report.findings],
                    "suppressed": report.suppressed,
                    "denylist_terms": report.denylist_terms,
                },
                indent=2,
            )
        )
        return 1 if report.findings else 0

    for finding in report.findings:
        print(finding.as_text())
    summary = f"{report.files} files | findings: {len(report.findings)} | suppressed: {report.suppressed}"
    print(f"\n{summary} | denylist terms: {report.denylist_terms}")
    if not denylist:
        print(
            "note: no denylist configured. Create one with your customer, brand and person names\n"
            "      so no skill can ever mention them. Keep it OUT of a public repository:\n"
            "      a list of client names is itself the thing you are protecting.\n"
            "      Use PROVENANCE_DENYLIST=<path outside the repo>, or a CI secret."
        )
    return 1 if report.findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(2)
