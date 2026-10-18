#!/usr/bin/env python3
"""
audit_skills.py - The deterministic half of a skill audit: every check a script can do better than a model.

Finds the Agent Skills of a project (.claude/skills, .agents/skills, a catalog skills/ folder, plugin skills,
claude.ai synced skills) and, unless --no-commands, the legacy .claude/commands files. Checks each one
against references/guidelines.md and reports findings with the guideline rule IDs (G-FM-02, G-DESC-05…):
frontmatter that does not parse, names and descriptions that break loading or triggering, structure
(size, tables of contents, reference depth, dead links, paths), wording the current models handle badly
(capitals for emphasis, requests to write out the reasoning, generic re-check instructions), undeclared
script dependencies, and collection-level problems (duplicates, mirrors that drifted, per-model copies).

It never writes anything. The judgment - what to keep, what to cut, how to rewrite - stays with the agent
running the audit; this script only tells it where to look.

Usage:
    python3 scripts/audit_skills.py ROOT_OR_SKILL [MORE ...] [--json] [--strict] [--shared]
                                                  [--no-commands] [--min-level LEVEL]

Examples:
    python3 scripts/audit_skills.py .                         # every skill under the current project
    python3 scripts/audit_skills.py .claude/skills/deploy     # a single skill
    python3 scripts/audit_skills.py . --json > audit.json     # machine-readable, for the review phase
    python3 scripts/audit_skills.py skills/ --shared --strict # a catalog shared with other agents, CI-style

Levels: ERROR (breaks loading, upload or triggering, or invites a refusal), WARN (should be fixed),
INFO (worth a look; often fine). A genuine false positive is silenced with a reason, on the line or the
line above it:  <!-- audit-ok: quoting the anti-pattern, not using it -->

Exit code: 0 no ERROR (and no WARN with --strict) | 1 blocking findings | 2 execution error
"""
from __future__ import annotations

import argparse
import ast
import bisect
import difflib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- Limits, each with the source that sets it --------------------------------------------------------
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")  # agentskills.io spec: no edge or double hyphens
MAX_NAME = 64                 # spec and Anthropic best practices
MAX_DESC = 1024               # spec hard limit
MAX_DESC_LISTING = 1536       # Claude Code truncates description + when_to_use here
MIN_DESC = 40                 # below this a description cannot say both what and when
MAX_COMPAT = 500              # spec
MAX_LINES = 500               # SKILL.md body guidance (Anthropic + spec)
MAX_TOKENS = 5000             # spec: instructions under ~5000 tokens
CHARS_PER_TOKEN = 4           # conservative estimate, same as the repo validator
TOC_THRESHOLD = 100           # Anthropic: reference files over 100 lines open with a table of contents
SKILL_TOC_THRESHOLD = 300     # a long SKILL.md without an index is worth a look, not a warning
TOC_WINDOW = 40               # a contents list further down than this is not seen by a partial read
CAPS_ABSOLUTE = 5             # this many capitalised imperatives in one file is the old emphasis habit
CAPS_DENSITY_LINES = 40       # ...or one every 40 lines, once there are at least CAPS_DENSITY_MIN
CAPS_DENSITY_MIN = 3
SIMILAR_DESC = 0.85           # difflib ratio above which two descriptions claim the same requests
MAX_BYTES = 2 * 1024 * 1024   # larger files are reported, not scanned
SHOW_LINES = 5                # line numbers listed per aggregated finding

PORTABLE_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
CLAUDE_CODE_KEYS = {
    "when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable",
    "allowed-tools", "disallowed-tools", "model", "effort", "context", "agent", "background",
    "hooks", "paths", "shell",
}
COMMAND_FORBIDDEN_KEYS = {"name", "paths"}  # Claude Code commands accept everything else a skill does
RESERVED_WORDS = ("anthropic", "claude")
MODEL_FAMILIES = ("haiku", "sonnet", "opus", "fable")
SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", ".venv", "venv", "__pycache__", ".next",
    "storage", ".cache", ".tox", "fixtures", "__fixtures__", "testdata",
}
IGNORED_BUNDLED = {"LICENSE", "LICENSE.md", "LICENSE.txt", ".DS_Store", ".gitkeep", "Thumbs.db"}
PIP_NAMES = {  # import name -> the package a SKILL.md would mention
    "PIL": "pillow", "yaml": "pyyaml", "bs4": "beautifulsoup4", "cv2": "opencv", "sklearn": "scikit-learn",
    "docx": "python-docx", "pptx": "python-pptx", "fitz": "pymupdf", "dateutil": "python-dateutil",
}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}

SUPPRESS = re.compile(r"audit-ok:\s*\S.{2,}")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"`[^`\n]*`")
QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”|«[^»\n]*»')
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
MD_LINK = re.compile(r"\[[^\]\n]*\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
BUNDLED_PATH = re.compile(r"^(?:\./)?((?:scripts|references|reference|assets|templates|examples)/[A-Za-z0-9._/-]+)$")
# $1, $2 ... standing alone: Claude Code substitutes arguments into the skill text, and an awk field or a
# positional parameter looks the same
POSITIONAL = re.compile(r"(?<![\\$])\$[0-9]+(?!\w)")
ARGUMENT_NAME = re.compile(r"[A-Za-z_]\w*")
COMMAND_PATH = re.compile(
    r"(?<![\w/.$-])(?:\$\{?CLAUDE_SKILL_DIR\}?/|\./)?"
    r"((?:scripts|references|reference|assets|templates|examples)/[A-Za-z0-9._/-]*[A-Za-z0-9_]\.[A-Za-z0-9]+)"
    r"(?![A-Za-z0-9_/-])"
)
SKILL_CONTAINERS = {".claude", ".agents", "skills", "commands", "synced"}
SHELL_FENCES = ("bash", "sh", "shell", "zsh", "console", "powershell", "pwsh", "cmd", "batch")
URL_SPAN = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s)>\]]+")
BACKSLASH_PATH = re.compile(r"^[A-Za-z0-9._-]+(?:\\[A-Za-z0-9._-]+)+$")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
STUB_TARGET = re.compile(r"([\w.~/\\-]*[/\\])SKILL\.md\b")
READ_VERB = re.compile(r"(?i)\b(read|leggi|follow|segui|open|apri|see|vedi|load|carica)\b")

# Absolute paths that only exist on one machine. The patterns describe the shape, never a real path.
USER_PATH = re.compile(  # provenance-ok: the pattern of a user path, not a path
    r"\b[A-Za-z]:[\\/]+Users[\\/]+(?![<{])[A-Za-z0-9._-]+"
    r"|(?<![\w.-])/(?:home|Users)/(?!(?:runner|you|user|username|name|me)\b|[<{$])[A-Za-z0-9._-]+"
)
DRIVE_PATH = re.compile(r"(?<![\w/])[A-Za-z]:\\[A-Za-z0-9_]")

CAPS_WORDS = re.compile(
    r"\b(MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT|REQUIRED|MANDATORY|DO NOT|DON'T|"
    r"MAI|SEMPRE|OBBLIGATORIO|OBBLIGATORIA|INVIOLABILE|IMPORTANTE|NON)\b"
)
REASONING_EXTRACTION = re.compile(
    # "your": the model's own reasoning. "Write the reasoning behind the change" in a commit is a rationale.
    r"(?i)\b(?:show|write(?: out)?|print|transcribe|reproduce|echo)\s+your\s+"
    r"(?:full\s+|internal\s+|step[- ]by[- ]step\s+)?(?:reasoning|thinking|thought process|chain[- ]of[- ]thought)"
    r"|\bexplain\s+your\s+reasoning\s+step[- ]by[- ]step"
    r"|\bthink\s+step[- ]by[- ]step\s+and\s+(?:write|show|output|print)"
    r"|\bthink\s+(?:out loud|aloud)"
    r"|<thinking>"
    r"|\b(?:mostra|scrivi|riporta|esponi)\s+(?:il\s+)?tuo\s+ragionamento"
    r"|\bspiega\s+(?:il\s+)?(?:tuo\s+)?ragionamento\s+passo\s+(?:per|a)\s+passo"
    r"|\bragionamento\s+(?:esplicito\s+)?nella\s+risposta"
)
THINKING_SCRIPT = re.compile(
    r"(?i)\bthink\s+step[- ]by[- ]step\b|\bthink\s+(?:carefully|hard|deeply)\s+before\b|\bpensa\s+passo\s+(?:per|a)\s+passo\b"
)
GENERIC_VERIFY = re.compile(
    r"(?i)\bdouble[- ]check|\bre-?verify\b|\bverify\s+your\s+(?:answer|work|output|response)"
    r"|\buse\s+(?:a\s+)?sub-?agent\s+to\s+(?:verify|double-check|check)"
    r"|\bricontrolla|\bverifica\s+due\s+volte|\bcontrolla\s+due\s+volte"
)
ANTI_LAZINESS = re.compile(
    r"(?i)\btake\s+your\s+time\b|\bquality\s+is\s+more\s+important\s+than\s+speed|\bdo\s+not\s+skip\s+(?:any\s+)?validation"
    r"|\bif\s+in\s+doubt,?\s+use\b|\bprenditi\s+(?:tutto\s+)?il\s+tempo"
)
_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|november|december"
    "|gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre"
)
TIME_SENSITIVE = re.compile(
    rf"(?i)\b(?:before|after|until|since|by|prima\s+di|dopo|fino\s+a|entro|dal|dalla)\s+(?:the\s+end\s+of\s+)?"
    rf"(?:{_MONTHS})\s+(?:19|20)\d{{2}}\b"
    rf"|\bas\s+of\s+(?:(?:{_MONTHS})\s+)?(?:19|20)\d{{2}}\b"
    rf"|\b(?:until|before|after|since|fino\s+al|prima\s+del|dopo\s+il|dal)\s+(?:19|20)\d{{2}}\b"
)
MODEL_NAME = re.compile(r"(?i)\b(haiku|sonnet|opus|fable)\b")
PLACEHOLDER = re.compile(r"\b(?:TODO|FIXME|TBD|XXX)\b|\{\{[^}\n]+\}\}")

DESC_FIRST_PERSON = re.compile(  # "a crash you can reproduce" is fine; "You can use this to…" is not
    r"\bI\s+(?:can|will|help|am|'ll)\b|\bI'm\b|(?i:\blet\s+me\b|\byou\s+can\s+use\b|\bti\s+aiuto\b|\bposso\s+aiutarti\b)"
    r"|(?:^|[.!?:]\s+)(?i:you\s+can)\b"
)
RFC_LEVEL_LABEL = re.compile(r"^\**\s*[.:]")  # "**MUST.**", "MUST:" - a rule level, not emphasis
RFC_LEVELS = {"MUST", "REQUIRED", "MANDATORY"}
DESC_WHEN = re.compile(
    r"(?i)\buse\s+(?:this\s+skill\s+|it\s+)?(?:when|whenever|for|if)\b|\bwhen\s+(?:the\s+)?user|\bwhenever\b"
    r"|\busa(?:la)?\s+(?:questa\s+skill\s+)?(?:quando|per|se)\b|\bquando\b|\bogni\s+volta\b|\bda\s+invocare\b"
    r"|\btrigger|\bactivates?\b|\binvoke\s+when"
)
DESC_BOUNDARY = re.compile(
    r"(?i)\b(?:do\s+not|don't|never)\s+use\b|\bnot\s+for\b|\bnot\s+intended\s+for\b|\bnon\s+usar(?:la|e|lo)\b"
    r"|\bnon\s+(?:è|e')\s+per\b|\binstead\b"
)
DESC_QUOTED = re.compile(r'"[^"\n]{1,80}"|“[^”\n]{1,80}”')
XML_TAG = re.compile(r"<\s*/?\s*[A-Za-z!?][^<>]*>")

LEVEL_RANK = {"ERROR": 0, "WARN": 1, "INFO": 2}


# --- Data ----------------------------------------------------------------------------------------------
@dataclass
class Finding:
    id: str
    level: str
    file: str
    line: int
    message: str

    def as_dict(self) -> dict[str, object]:
        return {"id": self.id, "level": self.level, "file": self.file, "line": self.line, "message": self.message}


@dataclass
class Skill:
    entry: Path          # SKILL.md, or the command .md, as discovered (not resolved: keeps symlinked names)
    root: Path           # the scan root it was found under, for relative paths
    kind: str            # skill | command | synced
    location: str        # claude | agents | catalog | plugin | direct | command
    text: str = ""
    lines: list[str] = field(default_factory=list)
    frontmatter: dict[str, object] = field(default_factory=dict)
    key_lines: dict[str, int] = field(default_factory=dict)
    fm_ok: bool = False
    body_start: int = 0  # 0-based index of the first body line
    findings: list[Finding] = field(default_factory=list)
    unreadable: list[str] = field(default_factory=list)  # bundled folders that could not be listed
    aliases: list[str] = field(default_factory=list)  # other locations the same file was reached from (symlinks)

    @property
    def folder(self) -> Path:
        return self.entry.parent

    @property
    def name(self) -> str:
        declared = self.frontmatter.get("name")
        if isinstance(declared, str) and declared.strip():
            return declared.strip()
        return self.entry.stem if self.kind == "command" else self.folder.name

    @property
    def description(self) -> str:
        value = self.frontmatter.get("description", "")
        return value if isinstance(value, str) else str(value)

    def rel(self, path: Path) -> str:
        return relative(path, self.root)

    def add(self, rule_id: str, level: str, path: Path, line: int, message: str) -> None:
        self.findings.append(Finding(rule_id, level, self.rel(path), line, message))


def relative(path: Path, root: Path) -> str:
    """Forward-slash path relative to the root; symlinked skills keep the name they were found under."""
    for base in (root, root.resolve()):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.as_posix()


# --- Reading and parsing -------------------------------------------------------------------------------
def read_text(path: Path) -> str:
    """UTF-8 with replacement, no BOM, LF only: the shape every check below assumes."""
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if text.startswith("﻿"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n")


class FrontmatterError(ValueError):
    def __init__(self, message: str, line: int = 1) -> None:
        super().__init__(message)
        self.line = line


YAML_ESCAPES = set("0abt\tnvfre \"/\\N_LPxuU")
HEX_ESCAPES = {"x": 2, "u": 4, "U": 8}
_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "0": "\0", "a": "\a", "b": "\b", "v": "\v", "f": "\f", "e": "\x1b",
    " ": " ", '"': '"', "\\": "\\", "/": "/", "N": "\x85", "_": "\xa0", "L": "\u2028", "P": "\u2029",
}


def _quoted_scalar(value: str, line: int, problems: list[tuple[int, str, str]]) -> str:
    """A YAML quoted scalar: the text between the quotes, honouring escapes, with what follows it checked.

    A value that opens a quote and never closes it is rejected by every YAML loader, so the skill would load
    with no fields: that is reported, not tolerated. A trailing ' # comment' is legal and dropped.
    """
    quote, out, i = value[0], [], 1
    while i < len(value):
        ch = value[i]
        if quote == '"' and ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            digits = HEX_ESCAPES.get(nxt)
            if digits and re.fullmatch(r"[0-9a-fA-F]{%d}" % digits, value[i + 2:i + 2 + digits]):
                code = int(value[i + 2:i + 2 + digits], 16)
                if code <= 0x10FFFF:
                    out.append(chr(code))
                    i += 2 + digits
                    continue
                problems.append((line, "ERROR", f"'\\{nxt}{value[i + 2:i + 2 + digits]}' is beyond the last "
                                                "Unicode code point"))
            if nxt not in YAML_ESCAPES:
                problems.append((line, "ERROR", f"'\\{nxt}' is not a YAML escape: a double-quoted value rejects it, so "
                                                "the skill loads with no fields. Double the backslash or use single quotes"))
            elif digits and not re.fullmatch(r"[0-9a-fA-F]{%d}" % digits, value[i + 2:i + 2 + digits]):
                problems.append((line, "ERROR", f"'\\{nxt}' needs {digits} hex digits in a YAML double-quoted value"))
            out.append(_ESCAPES.get(nxt, "\\" + nxt))
            i += 2
            continue
        if quote == "'" and ch == "'" and value[i + 1:i + 2] == "'":
            out.append("'")
            i += 2
            continue
        if ch == quote:
            rest = value[i + 1:].strip()
            if rest and not rest.startswith("#"):
                problems.append((line, "ERROR", f"text after the closing quote ({rest[:30]!r}): YAML rejects the "
                                                "value, so the skill loads with no fields"))
            return "".join(out)
        out.append(ch)
        i += 1
    problems.append((line, "ERROR", f"the quoted value opened with {quote} is never closed: YAML rejects it, so the "
                                    "skill loads with no fields. Close the quote or use '>-'"))
    return "".join(out)


def _unquote(value: str) -> str:
    """Quoted list items and the like; problems with them are not worth a finding of their own."""
    return _quoted_scalar(value, 0, []) if value[:1] in ("'", '"') else value


NON_TEXT_SCALAR = re.compile(
        r"(?P<null>null|Null|NULL|~)|(?P<bool>true|True|TRUE|false|False|FALSE)"
        r"|(?P<number>[-+]?(?:\d[\d_]*)(?:\.\d*)?(?:[eE][-+]?\d+)?|0x[0-9a-fA-F]+|0o[0-7]+|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))"
)


def _non_text_scalar(raw: str) -> str | None:
    """'null', 'a boolean' or 'a number' when a plain (unquoted) scalar is not text to a YAML loader."""
    value = raw.split(" #", 1)[0].strip()
    m = NON_TEXT_SCALAR.fullmatch(value) if value else None
    if not m:
        return None
    return {"null": "null", "bool": "a boolean", "number": "a number"}[m.lastgroup]


def _split_flow(inner: str) -> list[str]:
    """Top-level comma-separated items of a flow collection body, quotes and nesting respected."""
    parts: list[str] = []
    current: list[str] = []
    depth, quote = 0, ""
    for ch in inner:
        if quote:
            current.append(ch)
            quote = "" if ch == quote else quote
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    parts.append("".join(current).strip())
    return [part for part in parts if part]


def _flow_collection(value: str, line: int, problems: list[tuple[int, str, str]]) -> object:
    """'[a, b]' is a list and '{a: b}' a mapping in YAML, whatever the field: keep the type so it can be checked."""
    closing = "]" if value[0] == "[" else "}"
    body = value.split(" #", 1)[0].strip()
    if not body.endswith(closing):
        problems.append((line, "ERROR", f"the collection opened with {value[0]} is never closed with {closing}: YAML "
                                        "rejects it, so the skill loads with no fields"))
        return value

    def scalar(text: str) -> str:
        return _unquote(text) if text[:1] in ("'", '"') else text

    items = _split_flow(body[1:-1])
    if closing == "]":
        return [scalar(item) for item in items]
    mapping: dict[str, object] = {}
    for item in items:
        key, _, rest = item.partition(":")
        mapping[scalar(key.strip())] = scalar(rest.strip())
    return mapping


def _plain_scalar(value: str, line: int, problems: list[tuple[int, str, str]]) -> str:
    """A YAML plain scalar, with the two ways it silently breaks a real YAML parser checked."""
    if value.startswith(("'", '"')):
        return _quoted_scalar(value, line, problems)
    if value.startswith(("[", "{")):
        return _flow_collection(value, line, problems)
    if value[:1] in ("`", "@", "%", "*", "&"):
        problems.append((line, "ERROR", f"an unquoted value cannot start with {value[0]!r}: YAML rejects it, "
                                        "so the skill loads with no fields. Quote it or use '>-'"))
    if " #" in value:  # a comment, which YAML drops: what it says must not be judged as part of the value
        problems.append((line, "WARN", "the text after ' #' is a YAML comment and is dropped from the value: quote it"))
        value = value.split(" #", 1)[0].strip()
    if re.search(r":\s", value) or value.endswith(":"):
        problems.append((line, "ERROR", "an unquoted value contains ': ', which YAML reads as a nested mapping "
                                        "and rejects: the skill then loads with no fields. Quote it or use '>-'"))
    return value.strip()


def parse_frontmatter(text: str) -> tuple[dict[str, object], dict[str, int], int, list[tuple[int, str, str]]]:
    """A deliberately small YAML subset: top-level keys, quoted and plain scalars, >-/| blocks, one nested level.

    Without PyYAML on purpose - the audit must run anywhere with no dependencies. Returns
    (data, line of each key, 0-based index of the first body line, [(line, level, problem)]).
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("the file does not start with '---' on line 1: Claude Code reads no frontmatter "
                               "and the description never reaches the listing")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise FrontmatterError("the frontmatter is not closed by a '---' line")
    data: dict[str, object] = {}
    key_lines: dict[str, int] = {}
    problems: list[tuple[int, str, str]] = []
    i = 1
    while i < end:
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if raw[0] in " \t":
            raise FrontmatterError(f"indented line without a parent key: {raw.strip()[:60]!r}", i + 1)
        m = re.match(r"^([A-Za-z0-9_.-]+):(\s.*|)$", raw)
        if not m:
            raise FrontmatterError(f"not a 'key: value' line (the colon needs a space after it): "
                                   f"{raw.strip()[:60]!r}", i + 1)
        key, value = m.group(1), m.group(2).strip()
        if value.startswith("#"):  # "key: # comment" is an empty value followed by a comment
            value = ""
        key_lines[key] = i + 1
        block: list[str] = []
        j = i + 1
        while j < end and (not lines[j].strip() or lines[j][0] in " \t"):
            block.append(lines[j])
            j += 1
        while block and not block[-1].strip():
            block.pop()
        data[key] = _value(value, block, i + 1, problems)
        if key in ("name", "description") and not block:
            kind = _non_text_scalar(value)
            if kind:
                problems.append((i + 1, "ERROR", f"'{key}: {value}' is read by YAML as {kind}, not as text: quote it, "
                                                 "or the skill is not loaded"))
        i = j
    return data, key_lines, end + 1, problems


def _value(value: str, block: list[str], line: int, problems: list[tuple[int, str, str]]) -> object:
    texts = [b.strip() for b in block]
    if value.startswith((">", "|")):
        if value.startswith("|"):
            return "\n".join(texts).strip()
        return re.sub(r"\s+", " ", " ".join(t for t in texts if t)).strip()
    if value == "":
        items = [t for t in texts if t]
        if items and all(t.startswith("- ") or t == "-" for t in items):
            return [_unquote(t[1:].strip()) for t in items]
        if items and all(re.match(r"^[A-Za-z0-9_.-]+:(\s|$)", t) for t in items):
            nested: dict[str, object] = {}
            for offset, t in enumerate(texts):
                if not t:
                    continue
                k, _, v = t.partition(":")
                nested[k.strip()] = _plain_scalar(v.strip(), line + 1 + offset, problems) if v.strip() else ""
            return nested
        return " ".join(items)
    if value.startswith(('"', "'")):
        if texts and any(texts):
            value = " ".join([value, *[t for t in texts if t]])  # a quoted scalar spanning lines
        return _quoted_scalar(value, line, problems)
    if texts and any(texts):
        value = " ".join([value, *[t for t in texts if t]])  # a multi-line plain scalar
    return _plain_scalar(value, line, problems)


# --- Discovery -----------------------------------------------------------------------------------------
def discover(roots: list[Path], with_commands: bool) -> tuple[list[Skill], list[str]]:
    """Every skill and command under the roots, once each even when symlinked from several places."""
    found: list[Skill] = []
    seen: dict[str, Skill] = {}
    walk_errors: list[str] = []

    def add(entry: Path, root: Path, kind: str, location: str) -> None:
        try:
            resolved = entry.resolve()
        except OSError:
            resolved = entry
        key = os.path.normcase(str(resolved))
        if kind == "skill" and _under_synced(resolved):
            kind = "synced"  # reached through a link, but a claude.ai copy all the same: the next sync overwrites it
        if key in seen:
            # Same file through another path (a symlink): audit it once, but remember where else it is exposed,
            # so the order the roots are given in cannot change whether it is held to the shared-skill rules.
            seen[key].aliases.append(location)
            if kind == "synced":  # the read-only classification must not depend on which path came first
                seen[key].kind = "synced"
            return
        skill = Skill(entry=entry, root=root, kind=kind, location=location)
        seen[key] = skill
        found.append(skill)

    for root in roots:
        if root.is_file():
            if root.name != "SKILL.md":
                add(root, root.parent, "command", "command")
                continue
            kind, location = _layout_of(root)
            add(root, root.parent.parent, kind, location)
            continue
        if (root / "SKILL.md").is_file():
            kind, location = _layout_of(root / "SKILL.md")
            add(root / "SKILL.md", root.parent, kind, location)
            continue
        _walk(root, with_commands, add, walk_errors)
    return found, walk_errors


def _layout_of(skill_md: Path) -> tuple[str, str]:
    """(kind, location) of a skill named directly on the command line, read from the folders around it.

    Narrowing an audit to one skill must not change what is checked: a skill under .agents/skills is shared
    with other agents, one under .claude/skills/synced is a claude.ai copy, whichever way it was reached.
    """
    folder = skill_md.absolute().parent
    for ancestor in (folder.parent.parent, folder.parent.parent.parent):
        if ancestor.name == "synced" and ancestor.parent.name == "skills" and ancestor.parent.parent.name == ".claude":
            return "synced", "claude"
    if folder.parent.name == "skills":
        location = _skills_dir_location(folder.parent, folder.parent.parent)
        return "skill", location or "catalog"
    return "skill", "direct"


def _under_synced(skill_md: Path) -> bool:
    """True for a SKILL.md inside .claude/skills/synced/<account>/<skill>/, wherever the link to it lives."""
    for ancestor in (skill_md.parent.parent.parent, skill_md.parent.parent):
        if ancestor.name == "synced" and ancestor.parent.name == "skills" and ancestor.parent.parent.name == ".claude":
            return True
    return False


def _synced_depth(folder: Path) -> int | None:
    """0 for .claude/skills/synced itself, 1 for one of its account folders, None anywhere else."""
    here = folder.absolute()
    for depth, synced in ((0, here), (1, here.parent)):
        if synced.name == "synced" and synced.parent.name == "skills" and synced.parent.parent.name == ".claude":
            return depth
    return None


def _skills_dir_location(skills_dir: Path, root: Path) -> str | None:
    parent = skills_dir.parent
    if parent.name == ".claude":
        return "claude"
    if parent.name == ".agents":
        return "agents"
    if (parent / ".claude-plugin").is_dir():
        return "plugin"
    if skills_dir == root or parent == root:
        return "catalog"
    return None


def _walk(root: Path, with_commands: bool, add, walk_errors: list[str]) -> None:
    def on_error(exc: OSError) -> None:  # an unreadable folder is reported, never skipped in silence
        walk_errors.append(f"cannot read {getattr(exc, 'filename', '?')}: {exc.strerror or exc}")

    visited: set[str] = set()
    pending = [root]
    while pending:
        _walk_one(pending.pop(0), root, with_commands, add, on_error, visited, pending)


def _walk_one(top: Path, root: Path, with_commands: bool, add, on_error, visited: set[str], pending: list[Path]) -> None:
    for dirpath, dirnames, _ in os.walk(top, onerror=on_error):
        here = Path(dirpath)
        real = os.path.normcase(os.path.realpath(dirpath))
        if real in visited:
            # Reached before through another path (a link): never walk it twice, but the skills in it are also
            # exposed here, and that exposure decides how strictly they are judged.
            location = _skills_dir_location(here, root) if here.name == "skills" else None
            if location:
                for child in sorted(dirnames):
                    if (here / child / "SKILL.md").is_file():
                        add(here / child / "SKILL.md", root, "skill", location)
            dirnames[:] = []
            continue
        visited.add(real)
        # os.walk lists a symlinked directory but does not enter it. The folders that hold skills are often
        # links to a shared location, so those are followed (once each, cycles cut by `visited`).
        for name in dirnames:
            if name in SKILL_CONTAINERS and (here / name).is_symlink():
                pending.append(here / name)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        synced_depth = _synced_depth(here)
        if synced_depth is not None:  # the walk was started inside ~/.claude/skills/synced
            for skill_md in sorted(here.glob("*/*/SKILL.md" if synced_depth == 0 else "*/SKILL.md")):
                add(skill_md, root, "synced", "claude")
            dirnames[:] = []
            continue
        if here.name == "skills":
            location = _skills_dir_location(here, root)
            if location:
                for child in sorted(dirnames):
                    child_dir = here / child
                    if location == "claude" and child == "synced":
                        for skill_md in sorted(child_dir.glob("*/*/SKILL.md")):
                            add(skill_md, root, "synced", "claude")
                        continue
                    if (child_dir / "SKILL.md").is_file():
                        add(child_dir / "SKILL.md", root, "skill", location)
                # a skill folder holds no further skills: no need to walk its references and scripts
                dirnames[:] = [d for d in dirnames if not (here / d / "SKILL.md").is_file() and d != "synced"]
        if with_commands and here.name == "commands" and here.parent.name == ".claude":
            for command in sorted(here.rglob("*.md")):
                if not any(part in SKIP_DIRS for part in command.relative_to(here).parts):
                    add(command, root, "command", "command")
            dirnames[:] = []


# --- Per-skill checks ----------------------------------------------------------------------------------
def audit_skill(skill: Skill, shared: bool) -> None:
    try:
        if skill.entry.stat().st_size > MAX_BYTES:
            skill.add("G-STRUCT-01", "ERROR", skill.entry, 1, "file too large to load as a skill: split it")
            return
        skill.text = read_text(skill.entry)
    except OSError as exc:
        skill.add("G-FM-01", "ERROR", skill.entry, 1, f"cannot read the file: {exc}")
        return
    skill.lines = skill.text.split("\n")
    check_frontmatter(skill, shared)
    if skill.fm_ok:
        check_description(skill)
    check_size(skill)
    files = bundled_files(skill)
    check_links_and_paths(skill, files)
    check_content(skill, files)
    check_scripts(skill, files)


def check_frontmatter(skill: Skill, shared: bool) -> None:
    try:
        data, key_lines, body_start, problems = parse_frontmatter(skill.text)
    except FrontmatterError as exc:
        skill.add("G-FM-01", "ERROR", skill.entry, exc.line, f"{exc}")
        return
    skill.frontmatter, skill.key_lines, skill.body_start = data, key_lines, body_start
    skill.fm_ok = not any(level == "ERROR" for _, level, _ in problems)
    for field_name, rule_id in (("name", "G-FM-02"), ("description", "G-DESC-01")):
        value = data.get(field_name)
        if value is not None and not isinstance(value, str):
            kind = "a list" if isinstance(value, list) else "a mapping" if isinstance(value, dict) else type(value).__name__
            skill.add(rule_id, "ERROR", skill.entry, key_lines.get(field_name, 1),
                      f"'{field_name}' is {kind}: it must be a single string, or the skill is not loaded")
            skill.fm_ok = False
    for line, level, message in problems:
        skill.add("G-FM-01", level, skill.entry, line, message)
    if skill.kind == "command":
        _command_keys(skill)
        return
    _name(skill, shared)
    _keys(skill, shared)
    compat = data.get("compatibility")
    if isinstance(compat, str) and len(compat) > MAX_COMPAT:
        skill.add("G-FM-03", "ERROR", skill.entry, key_lines.get("compatibility", 1),
                  f"'compatibility' is {len(compat)} characters (max {MAX_COMPAT})")
    if (skill.folder / "README.md").is_file():
        skill.add("G-FM-05", "INFO", skill.folder / "README.md", 1,
                  "README.md inside the skill folder: move its content to SKILL.md or references/")


def _is_shared(skill: Skill, shared: bool) -> bool:
    return shared or any(place in ("agents", "catalog") for place in (skill.location, *skill.aliases))


def _name(skill: Skill, shared: bool) -> None:
    line = skill.key_lines.get("name", 1)
    name = skill.frontmatter.get("name")
    folder = skill.folder.name
    if not isinstance(name, str) or not name.strip():
        level = "ERROR" if _is_shared(skill, shared) else "WARN"
        skill.add("G-FM-02", level, skill.entry, 1,
                  f"no 'name': the spec requires it; Claude Code falls back to the folder name ({folder})")
        return
    name = name.strip()
    if not 1 <= len(name) <= MAX_NAME or not NAME_RE.match(name):
        skill.add("G-FM-02", "ERROR", skill.entry, line,
                  f"invalid name {name!r}: 1-{MAX_NAME} characters, lowercase letters, digits and single hyphens")
    if name != folder:
        skill.add("G-FM-02", "ERROR", skill.entry, line,
                  f"name {name!r} differs from the folder {folder!r}: the spec requires them to match")
    for word in RESERVED_WORDS:
        if word in name.lower():
            skill.add("G-FM-02", "ERROR", skill.entry, line, f"name contains the reserved word {word!r}")


def _keys(skill: Skill, shared: bool) -> None:
    for key in skill.frontmatter:
        line = skill.key_lines.get(key, 1)
        if key in PORTABLE_KEYS:
            continue
        if key in CLAUDE_CODE_KEYS:
            if _is_shared(skill, shared):
                skill.add("G-FM-03", "WARN", skill.entry, line,
                          f"'{key}' is Claude Code-only: other agents ignore it and a claude.ai or API upload "
                          "rejects it. Move it under 'metadata' or keep the skill Claude Code-only")
            else:
                skill.add("G-FM-03", "INFO", skill.entry, line,
                          f"'{key}' is Claude Code-only: fine here, but a claude.ai or API upload would reject it")
            continue
        skill.add("G-FM-03", "WARN", skill.entry, line,
                  f"unknown frontmatter key '{key}': no client reads it. Put custom data under 'metadata'")


def _command_keys(skill: Skill) -> None:
    for key in skill.frontmatter:
        line = skill.key_lines.get(key, 1)
        if key in COMMAND_FORBIDDEN_KEYS:
            skill.add("G-FM-03", "WARN", skill.entry, line,
                      f"'{key}' is not supported in .claude/commands files: convert the command to a skill to use it")
        elif key not in PORTABLE_KEYS | CLAUDE_CODE_KEYS:
            skill.add("G-FM-03", "WARN", skill.entry, line, f"unknown frontmatter key '{key}'")


def check_description(skill: Skill) -> None:
    desc = skill.description.strip()
    line = skill.key_lines.get("description", 1)
    where = skill.entry
    if not desc:
        level = "WARN" if skill.kind == "command" else "ERROR"
        skill.add("G-DESC-01", level, where, 1, "no description: the skill cannot be matched to a request")
        return
    if len(desc) > MAX_DESC:
        skill.add("G-DESC-01", "ERROR", where, line, f"description is {len(desc)} characters (max {MAX_DESC})")
    when = skill.frontmatter.get("when_to_use")
    combined = len(desc) + (len(when) if isinstance(when, str) else 0)
    if combined > MAX_DESC_LISTING:
        skill.add("G-DESC-01", "WARN", where, line,
                  f"description + when_to_use is {combined} characters: Claude Code cuts the listing at "
                  f"{MAX_DESC_LISTING}. Put the key use case first and trim")
    if len(desc) < MIN_DESC:
        skill.add("G-DESC-01", "WARN", where, line,
                  "description very short: it cannot say both what the skill does and when to use it")
    m = DESC_FIRST_PERSON.search(desc)
    if m:
        skill.add("G-DESC-02", "WARN", where, line,
                  f"description in first or second person ({m.group(0)!r}): write 'Generates…' or 'Use this skill when…'")
    if not DESC_WHEN.search(desc):
        skill.add("G-DESC-03", "INFO", where, line,
                  "description has no 'when' clause: add the situations that should trigger it, in the user's words")
    if skill.kind != "command" and not DESC_BOUNDARY.search(desc):
        skill.add("G-DESC-05", "INFO", where, line,
                  "description states no boundary: say what it does not cover and which sibling skill does")
    quoted = DESC_QUOTED.findall(desc)
    if len(quoted) >= 6 and sum(len(q) for q in quoted) > 0.5 * len(desc):
        skill.add("G-DESC-06", "WARN", where, line,
                  f"description is mostly a keyword list ({len(quoted)} quoted phrases): describe the situations in "
                  "sentences and keep at most a short trigger tail")
    for field_name in ("name", "description"):
        value = str(skill.frontmatter.get(field_name, ""))
        if XML_TAG.search(value):
            skill.add("G-DESC-07", "ERROR", where, skill.key_lines.get(field_name, 1),
                      f"XML-like tag in '{field_name}': it lands in the system prompt and uploads reject it")
        elif "<" in value or ">" in value:
            skill.add("G-DESC-07", "WARN", where, skill.key_lines.get(field_name, 1),
                      f"angle bracket in '{field_name}': claude.ai and the Skills API reject '<' and '>' here")
    caps = _caps_hits(desc)
    if caps:
        skill.add("G-GEN-02", "WARN", where, line,
                  f"capitals for emphasis in the description ({', '.join(sorted(set(caps)))}): plain wording "
                  "triggers better on the current models")


def check_size(skill: Skill) -> None:
    total = len(skill.lines)
    body = "\n".join(skill.lines[skill.body_start:]) if skill.fm_ok or skill.body_start else skill.text
    tokens = len(body) // CHARS_PER_TOKEN
    if total > MAX_LINES:
        skill.add("G-STRUCT-01", "WARN", skill.entry, 1,
                  f"{total} lines (keep under {MAX_LINES}): move detail into references/ and say when to read it")
    if tokens > MAX_TOKENS:
        skill.add("G-STRUCT-01", "WARN", skill.entry, 1, f"about {tokens} tokens of instructions (keep under {MAX_TOKENS})")
    if skill.kind != "command" and total > SKILL_TOC_THRESHOLD and not has_toc(skill.lines[skill.body_start:]):
        skill.add("G-STRUCT-03", "INFO", skill.entry, 1,
                  f"{total} lines and no index near the top: a short contents list helps a partial read")


def has_toc(lines: list[str]) -> bool:
    """A contents heading, or three consecutive list items that link to anchors or files."""
    window = [ln for ln in lines if ln.strip()][:TOC_WINDOW]
    streak = 0
    for ln in window:
        h = HEADING.match(ln)
        if h and re.search(r"(?i)\b(contents|table of contents|toc|indice|sommario|contenuti|index)\b", h.group(2)):
            return True
        if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+.*\[[^\]]+\]\((?:#|[^)]+\.md)", ln):
            streak += 1
            if streak >= 3:
                return True
        else:
            streak = 0
    return False


def bundled_files(skill: Skill) -> list[Path]:
    if skill.kind == "command":
        return []
    files: list[Path] = []

    def on_error(exc: OSError) -> None:  # a folder we could not list is files we did not check
        skill.unreadable.append(f"cannot read {getattr(exc, 'filename', '?')}: {exc.strerror or exc}")

    visited: set[str] = set()
    # followlinks: a references/ or scripts/ folder that is a link to a shared location is still part of the skill
    for dirpath, dirnames, filenames in os.walk(skill.folder, onerror=on_error, followlinks=True):
        real = os.path.normcase(os.path.realpath(dirpath))
        if real in visited:  # reached again through a link: listed once already, and this cuts any cycle
            dirnames[:] = []
            continue
        visited.add(real)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.name == "SKILL.md" and path.parent == skill.folder:
                continue
            files.append(path)
    return sorted(files)


def _md_files(skill: Skill, files: list[Path]) -> list[Path]:
    return [f for f in files if f.suffix.lower() == ".md" and "evals" not in f.relative_to(skill.folder).parts]


def _closes(fence: str, marker: str, line: str) -> bool:
    """A line ends an open fence only with the same character, at least as long, and nothing after it."""
    return marker[0] == fence[0] and len(marker) >= len(fence) and not line.strip()[len(marker):].strip()


def iter_prose(lines: list[str], start: int = 0):
    """(0-based index, line) outside fenced code blocks."""
    fence: str | None = None
    for index in range(start, len(lines)):
        line = lines[index]
        m = FENCE.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence = marker[0] * len(marker)
            elif _closes(fence, marker, line):
                fence = None
            continue
        if fence is None:
            yield index, line


def declared_arguments(skill: Skill) -> set[str]:
    """Names from the `arguments` frontmatter field: a space-separated string, or a list of names or of {name: ...}."""
    value = skill.frontmatter.get("arguments")
    items = value.split() if isinstance(value, str) else value if isinstance(value, list) else []
    names = (item.get("name") if isinstance(item, dict) else item for item in items)
    return {n for n in names if isinstance(n, str) and ARGUMENT_NAME.fullmatch(n)}


def iter_shell_lines(lines: list[str], start: int = 0):
    """(0-based index, line) inside fenced blocks that hold shell commands, comment lines left out."""
    fence: str | None = None
    shell = False
    for index in range(start, len(lines)):
        line = lines[index]
        m = FENCE.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence = marker[0] * len(marker)
                language = line.strip()[len(marker):].strip().split(" ")[0].lower()
                shell = language in SHELL_FENCES
            elif _closes(fence, marker, line):
                fence, shell = None, False
            continue
        if fence is not None and shell and not line.lstrip().startswith("#"):
            yield index, line


def _suppressed(lines: list[str], index: int) -> bool:
    return bool(SUPPRESS.search(lines[index]) or (index > 0 and SUPPRESS.search(lines[index - 1])))


def _resolves(target: str, candidates: list[Path]) -> bool:
    if target.startswith("~"):
        try:
            return Path(target).expanduser().exists()
        except (RuntimeError, OSError):  # no home directory to expand against
            return False
    return any((base / target).exists() for base in candidates)


def _bases(skill: Skill, md_file: Path) -> list[Path]:
    """Where a relative reference may legitimately point: next to the file, the skill root, the project.

    The project is found by walking up to the folder that holds .git, whatever the scan root: a skill under
    skills/ routinely names a script of the repository (scripts/harvest.py), which is not a dead reference.
    """
    bases = [md_file.parent, skill.folder]
    current = skill.folder
    for _ in range(12):  # a project root is never further than this from one of its skills
        parent = current.parent
        if parent == current:
            break
        bases.append(parent)
        if (parent / ".git").exists():
            break
        current = parent
    return bases


def _references(skill: Skill, md_file: Path, lines: list[str], start: int) -> list[tuple[int, str, str]]:
    """(line index, kind, target) for every markdown link and backticked bundled path outside code blocks."""
    refs: list[tuple[int, str, str]] = []
    for index, line in iter_prose(lines, start):
        quoted = [(q.start(), q.end()) for q in QUOTED.finditer(line)]

        def in_quotes(pos: int) -> bool:  # "read `references/x.md` if…" quotes an example, it does not link
            return any(a < pos < b for a, b in quoted)

        for m in MD_LINK.finditer(INLINE_CODE.sub(lambda c: " " * len(c.group(0)), line)):
            if not in_quotes(m.start()):
                refs.append((index, "link", m.group(1)))
        for m in CODE_SPAN.finditer(line):
            if in_quotes(m.start()):
                continue
            span = m.group(1).strip()
            if BUNDLED_PATH.match(span):
                refs.append((index, "path", BUNDLED_PATH.match(span).group(1)))
            elif BACKSLASH_PATH.match(span) and "." in span:
                refs.append((index, "backslash", span))
            else:  # a command: "scripts/run.py --since TAG", "python3 scripts/run.py"
                refs.extend((index, "path", c.group(1)) for c in COMMAND_PATH.finditer(span))
    for index, line in iter_shell_lines(lines, start):
        refs.extend((index, "path", c.group(1)) for c in COMMAND_PATH.finditer(line))
    return refs


def _clean_target(target: str) -> str | None:
    if not target or target.startswith("#") or SCHEME.match(target) or any(c in target for c in "<>{}$*"):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0]
    return target or None


def check_links_and_paths(skill: Skill, files: list[Path]) -> None:
    md_docs = [(skill.entry, skill.lines, skill.body_start)]
    for md in _md_files(skill, files):
        try:
            md_docs.append((md, read_text(md).split("\n"), 0))
        except OSError as exc:
            skill.add("G-STRUCT-08", "WARN", md, 1, f"cannot read: {exc}")
            skill.unreadable.append(f"cannot read {skill.rel(md)}: {exc.strerror or exc}")
    linked_from_skill: set[Path] = set()
    for md_file, lines, start in md_docs:
        bases = _bases(skill, md_file)
        for index, kind, raw_target in _references(skill, md_file, lines, start):
            if _suppressed(lines, index):
                continue
            if kind == "backslash" or "\\" in raw_target:
                skill.add("G-STRUCT-06", "WARN", md_file, index + 1,
                          f"backslash path {raw_target!r}: use forward slashes, they work on every OS")
                continue
            target = _clean_target(raw_target)
            if target is None:
                continue
            if kind == "path" and not _resolves(target, bases[:2]) and _resolves(target, bases):
                # Next to the skill is where a bundled file lives. A project file with the same name must not
                # hide a bundled script that is missing: say what it resolved to and let the author decide.
                skill.add("G-STRUCT-08", "INFO", md_file, index + 1,
                          f"{target} is not in this skill but exists in the project: bundle it with the skill, or "
                          "say in the text that it is a project script")
                continue
            if not _resolves(target, bases):
                if target.startswith("~"):
                    skill.add("G-STRUCT-08", "INFO", md_file, index + 1,
                              f"home-relative path {target} is not on this machine: cannot tell if it is dead")
                elif kind == "path" and md_file != skill.entry:
                    # A reference file mentions paths as examples far more often than SKILL.md does.
                    skill.add("G-STRUCT-08", "INFO", md_file, index + 1,
                              f"mentioned path not found: {target} (ignore it if it is an example)")
                else:
                    skill.add("G-STRUCT-08", "ERROR", md_file, index + 1, f"referenced file does not exist: {target}")
                continue
            if md_file == skill.entry:
                resolved = (md_file.parent / target) if (md_file.parent / target).exists() else (skill.folder / target)
                linked_from_skill.add(_norm(resolved))
        for index, line in enumerate(lines):
            if _suppressed(lines, index):
                continue
            m = USER_PATH.search(line)
            if m:
                skill.add("G-PORT-02", "WARN", md_file, index + 1,
                          "absolute path from one machine: use a path relative to the skill or the project, or ~/")
            elif DRIVE_PATH.search(line) and not re.search(r"\\[dswbnrtDSWB]", line):
                skill.add("G-PORT-02", "INFO", md_file, index + 1,
                          "absolute Windows path: it exists only on machines laid out the same way")
    if skill.kind == "command":
        return
    _depth_and_stubs(skill, md_docs, linked_from_skill)
    _orphans(skill, files, linked_from_skill)


def _norm(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path


def _depth_and_stubs(skill: Skill, md_docs, linked_from_skill: set[Path]) -> None:
    for index, line in iter_prose(skill.lines, skill.body_start):
        urls = [u.span() for u in URL_SPAN.finditer(line)]
        m = next((c for c in STUB_TARGET.finditer(line) if not any(a <= c.start() < b for a, b in urls)), None)
        if not m or not READ_VERB.search(line) or _suppressed(skill.lines, index):
            continue
        target = m.group(0)
        if _norm(skill.folder / target) == _norm(skill.entry):
            continue
        anywhere = [skill.folder, *skill.folder.parents][:14]  # the project root may be above the scan root
        if not _resolves(target, anywhere):
            if target.startswith("~"):  # another machine may have it where this one does not
                skill.add("G-STRUCT-08", "INFO", skill.entry, index + 1,
                          f"the home-relative SKILL.md {target} is not on this machine: cannot tell if it is dead")
            else:
                skill.add("G-STRUCT-08", "ERROR", skill.entry, index + 1,
                          f"the SKILL.md this skill sends the reader to does not exist: {target}")
        skill.add("G-STRUCT-09", "WARN", skill.entry, index + 1,
                  f"this skill sends the reader to another SKILL.md ({target}): one source of truth, ideally a "
                  "symlink, keeps the two descriptions from drifting and saves a reference level")
        break
    for md_file, lines, _ in md_docs[1:]:
        if _norm(md_file) not in linked_from_skill:
            continue
        for index, kind, raw_target in _references(skill, md_file, lines, 0):
            target = _clean_target(raw_target)
            if kind == "backslash" or target is None or not target.lower().endswith(".md"):
                continue
            for base in (md_file.parent, skill.folder):
                candidate = _norm(base / target)
                if not candidate.is_file() or candidate == _norm(md_file) or candidate.name == "SKILL.md":
                    continue
                inside = str(candidate).startswith(str(_norm(skill.folder)))
                if inside and candidate not in linked_from_skill:
                    skill.add("G-STRUCT-02", "WARN", md_file, index + 1,
                              f"second-level reference to {relative(candidate, _norm(skill.folder))}: link it "
                              "directly from SKILL.md, nested references get read partially")
                break


def _orphans(skill: Skill, files: list[Path], linked_from_skill: set[Path]) -> None:
    body = skill.text
    orphans: list[str] = []
    for path in files:
        rel = path.relative_to(skill.folder)
        parts = rel.parts
        if path.name in IGNORED_BUNDLED or path.name == "README.md" or parts[0] == "evals":
            continue
        if path.suffix == ".pyc" or "__pycache__" in parts:
            continue
        posix = rel.as_posix()
        if posix in body or path.name in body or _norm(path) in linked_from_skill:
            continue
        if any(f"{Path(*parts[:k]).as_posix()}/" in body for k in range(1, len(parts))):
            continue  # "templates/" in SKILL.md covers the folder
        orphans.append(posix)
    if orphans:
        shown = ", ".join(orphans[:8]) + (f" (+{len(orphans) - 8} more)" if len(orphans) > 8 else "")
        skill.add("G-STRUCT-08", "INFO", skill.entry, 1,
                  f"bundled files never mentioned in SKILL.md: {shown}. Link them with 'read X when Y', or delete them")


def _caps_hits(text: str) -> list[str]:
    hits = []
    stripped = QUOTED.sub(" ", INLINE_CODE.sub(" ", text))
    for m in CAPS_WORDS.finditer(stripped):
        before = stripped[max(0, m.start() - 1):m.start()]
        after = stripped[m.end():m.end() + 1]
        if before == "/" or after == "/":
            continue  # MUST/SHOULD/MAY: a level, not emphasis
        if m.group(1) in RFC_LEVELS and RFC_LEVEL_LABEL.match(stripped[m.end():m.end() + 4]):
            continue  # the label of a normative rule, as in a rules file with MUST/SHOULD/MAY levels
        hits.append(m.group(1))
    return hits


class _Aggregate:
    """Content findings grouped per (file, rule): one line in the report, every line number in it."""

    def __init__(self) -> None:
        self.hits: dict[tuple[str, str, Path], tuple[str, list[int]]] = {}

    def hit(self, rule_id: str, level: str, path: Path, line: int, message: str) -> None:
        key = (rule_id, level, path)
        if key not in self.hits:
            self.hits[key] = (message, [])
        self.hits[key][1].append(line)

    def flush(self, skill: Skill) -> None:
        for (rule_id, level, path), (message, lines) in self.hits.items():
            shown = ", ".join(str(n) for n in lines[:SHOW_LINES])
            more = f" +{len(lines) - SHOW_LINES} more" if len(lines) > SHOW_LINES else ""
            skill.add(rule_id, level, path, lines[0], f"{message} (line{'s' if len(lines) > 1 else ''} {shown}{more})")


LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
# A sentence that forbids the behaviour ("Never show your reasoning") is the rule being followed, not broken.
NEGATION_BEFORE = re.compile(
    r"(?i)\b(?:never|do\s+not|don'?t|must\s+not|should\s+not|avoid|without|not\s+to|non|mai|senza|evita|evitare|vietato)\b"
    r"[^.!?;:\n]{0,40}$"
)
NEGATION_WINDOW = 60
PHRASE_RULES = (
    (REASONING_EXTRACTION, "G-GEN-05", "ERROR",
     "asks the model to write out its reasoning in the response: the current Opus and Fable models may refuse "
     "(reasoning_extraction). Ask for a short explanation or a summary instead"),
    (THINKING_SCRIPT, "G-GEN-06", "INFO",
     "scripts the thinking ('think step by step'): thinking depth is set by effort; usually removable"),
    (GENERIC_VERIFY, "G-GEN-07", "INFO",
     "generic re-check instruction: keep it only if it names an objective check (script, tests, build); on the "
     "current Opus models it causes over-verification"),
    (ANTI_LAZINESS, "G-GEN-11", "INFO",
     "anti-laziness prompt written for older models: effort and concrete gates do this now"),
    (TIME_SENSITIVE, "G-BODY-10", "WARN",
     "time-sensitive wording: state the current method and move the legacy one under 'Old patterns'"),
)


def _mask(text: str) -> str:
    """Blank out inline code and quoted examples without moving anything, so match offsets stay valid."""
    def blank(m: re.Match) -> str:
        return " " * len(m.group(0))

    return QUOTED.sub(blank, INLINE_CODE.sub(blank, text))


def _paragraphs(lines: list[str], start: int):
    """Runs of soft-wrapped prose as [(line index, text)]. Blank lines, headings, bullets, tables and fences end one."""
    current: list[tuple[int, str]] = []
    previous = -2
    for index, line in iter_prose(lines, start):
        single = bool(HEADING.match(line)) or line.lstrip().startswith("|")
        if current and (not line.strip() or single or LIST_ITEM.match(line) or index != previous + 1):
            yield current
            current = []
        previous = index
        if single:
            yield [(index, line.strip())]
        elif line.strip():
            current.append((index, line.strip()))
    if current:
        yield current


def _phrase_findings(agg: "_Aggregate", path: Path, lines: list[str], start: int) -> None:
    """The phrase rules, matched across line wraps and skipped when the sentence forbids the behaviour."""
    for paragraph in _paragraphs(lines, start):
        joined = " ".join(text for _, text in paragraph)
        starts, offset = [], 0
        for _, text in paragraph:
            starts.append(offset)
            offset += len(text) + 1
        prose = _mask(joined)
        reasoning_lines: set[int] = set()
        for pattern, rule_id, level, message in PHRASE_RULES:
            for m in pattern.finditer(prose):
                index = paragraph[bisect.bisect_right(starts, m.start()) - 1][0]
                if _suppressed(lines, index):
                    continue
                window = prose[max(0, m.start() - NEGATION_WINDOW):m.start()]
                if rule_id != "G-BODY-10" and NEGATION_BEFORE.search(window):
                    continue
                if rule_id == "G-GEN-06" and index in reasoning_lines:
                    continue
                if rule_id == "G-GEN-05":
                    reasoning_lines.add(index)
                agg.hit(rule_id, level, path, index + 1, message)


def check_content(skill: Skill, files: list[Path]) -> None:
    docs = [(skill.entry, skill.lines, skill.body_start)]
    for md in _md_files(skill, files):
        parts = md.relative_to(skill.folder).parts
        if parts[0] in ("templates", "assets"):
            continue  # output material: its placeholders and capitals belong to what it generates
        try:
            docs.append((md, read_text(md).split("\n"), 0))
        except OSError:
            continue  # already reported by the link check
    agg = _Aggregate()
    for path, lines, start in docs:
        in_models_file = "models" in path.relative_to(skill.folder).parts if skill.kind != "command" else False
        caps_lines: list[int] = []
        heading = ""
        for index, line in iter_prose(lines, start):
            h = HEADING.match(line)
            if h:
                heading = h.group(2)
            if _suppressed(lines, index):
                continue
            prose = QUOTED.sub(" ", INLINE_CODE.sub(" ", line))
            if not (line.lstrip().startswith("|") and re.search(r"\|\s*(MUST|SHOULD|MAY)\s*\|", line)):
                caps_lines.extend([index + 1] * len(_caps_hits(line)))
            if (not in_models_file and MODEL_NAME.search(prose) and "model" not in heading.lower()
                    and skill.kind != "synced"):
                agg.hit("G-MODEL-04", "INFO", path, index + 1,
                        "model-specific guidance in the body: keep the base model-agnostic and move measured "
                        "differences to references/models/<family>.md behind a 'Model notes' section")
            if PLACEHOLDER.search(prose):
                agg.hit("G-BODY-01", "INFO", path, index + 1, "TODO or unfilled {{placeholder}} left in the text")
        if path == skill.entry:
            for index, line in iter_shell_lines(lines, start):
                for name in sorted(declared_arguments(skill)):
                    if re.search(r"(?:^|[\s;&|(])" + re.escape(name) + r"=", line) and not _suppressed(lines, index):
                        agg.hit("G-PORT-06", "INFO", path, index + 1,
                                f"the shell variable {name} has the name of a declared argument: ${name} in this text "
                                "is substituted before the shell sees it; rename the variable")
                if POSITIONAL.search(line) and not _suppressed(lines, index):
                    agg.hit("G-PORT-06", "INFO", path, index + 1,
                            "a positional placeholder ($1, $2...) in a shell snippet: Claude Code substitutes arguments "
                            "into the skill text, so an awk field or parameter may be rewritten; use cut or sed, or a "
                            "script under scripts/")
        _phrase_findings(agg, path, lines, start)
        body_lines = max(1, len(lines) - start)
        count = len(caps_lines)
        if count >= CAPS_ABSOLUTE or (count >= CAPS_DENSITY_MIN and body_lines / count <= CAPS_DENSITY_LINES):
            shown = ", ".join(str(n) for n in sorted(set(caps_lines))[:SHOW_LINES])
            skill.add("G-GEN-02", "WARN", path, caps_lines[0],
                      f"{count} words in capitals for emphasis (lines {shown}…): give the reason in plain words; "
                      "a rule that must always hold belongs in a hook or a script (G-FREE-02)")
        if path != skill.entry and len(lines) > TOC_THRESHOLD and not has_toc(lines):
            skill.add("G-STRUCT-03", "WARN", path, 1,
                      f"{len(lines)} lines and no table of contents in the first {TOC_WINDOW}: a partial read misses "
                      "what is below")
    agg.flush(skill)


def check_scripts(skill: Skill, files: list[Path]) -> None:
    if skill.kind == "command":
        return
    mentioned = skill.text.lower()
    requirements = skill.folder / "requirements.txt"
    if requirements.is_file():
        try:
            mentioned += "\n" + read_text(requirements).lower()
        except OSError:
            pass
    for path in files:
        if path.suffix == ".py":
            _python_script(skill, path, mentioned)
        elif path.suffix == ".sh":
            try:
                lines = read_text(path).split("\n")
            except OSError as exc:
                skill.unreadable.append(f"cannot read {skill.rel(path)}: {exc.strerror or exc}")
                continue
            for index, line in enumerate(lines):
                if re.match(r"^\s*read\b[^#\n]*\s-[a-zA-Z]*p\b", line):
                    skill.add("G-SCRIPT-03", "WARN", path, index + 1,
                              "interactive prompt ('read -p'): an agent shell cannot answer it. Take a flag or env var")


def _python_script(skill: Skill, path: Path, mentioned: str) -> None:
    try:
        source = read_text(path)
    except OSError as exc:
        skill.unreadable.append(f"cannot read {skill.rel(path)}: {exc.strerror or exc}")
        return
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:  # a limit of this check, not an unreadable file
        skill.add("G-SCRIPT-08", "INFO", path, 1, f"could not parse the script ({exc.__class__.__name__}): not checked")
        return
    local = {p.stem for p in path.parent.glob("*.py")} | {p.name for p in path.parent.iterdir() if p.is_dir()}
    third_party: dict[str, int] = {}
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module.split(".")[0]]
        for name in names:
            if name not in STDLIB and name not in local:
                third_party.setdefault(name, getattr(node, "lineno", 1))
        if isinstance(node, ast.Call):
            func = node.func
            called = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            if called in ("input", "getpass"):
                skill.add("G-SCRIPT-03", "WARN", path, getattr(node, "lineno", 1),
                          f"interactive '{called}()': an agent shell cannot answer it. Take a flag, env var or stdin")
    if not third_party or "# /// script" in source:
        return
    undeclared = [n for n in third_party if n.lower() not in mentioned and PIP_NAMES.get(n, n.lower()) not in mentioned]
    if undeclared:
        skill.add("G-SCRIPT-08", "WARN", path, min(third_party[n] for n in undeclared),
                  f"imports {', '.join(sorted(undeclared))} with no declared dependency: add a PEP 723 block or an "
                  "install line in SKILL.md")


# --- Library checks ------------------------------------------------------------------------------------
def library_checks(skills: list[Skill]) -> list[Finding]:
    findings: list[Finding] = []
    real = [s for s in skills if s.kind in ("skill", "synced")]
    by_name: dict[str, list[Skill]] = {}
    for s in real:
        by_name.setdefault(s.name, []).append(s)
    mirrored: set[frozenset[str]] = set()
    for name, group in sorted(by_name.items()):
        if len(group) < 2:
            continue
        locations = {s.location for s in group}
        paths = [s.rel(s.entry) for s in group]
        if {"claude", "agents"} <= locations and len(group) == 2:
            a, b = group
            mirrored.add(frozenset(paths))
            if _desc_key(a) != _desc_key(b):
                findings.append(Finding("G-STRUCT-09", "WARN", paths[0], 1,
                                        f"mirrored skill '{name}' has different descriptions in {paths[0]} and "
                                        f"{paths[1]}: keep one source of truth (a symlink) so they cannot drift"))
            else:
                findings.append(Finding("G-STRUCT-09", "INFO", paths[0], 1,
                                        f"skill '{name}' is copied in {paths[0]} and {paths[1]}: a symlink keeps it single"))
            continue
        findings.append(Finding("G-LIB-02", "WARN", paths[0], 1,
                                f"skill name '{name}' defined {len(group)} times ({', '.join(paths)}): one wins, "
                                "the other is dead weight or a source of confusion"))
    commands = {s.name: s for s in skills if s.kind == "command"}
    for name, command in sorted(commands.items()):
        if name in by_name:
            findings.append(Finding("G-LIB-02", "WARN", command.rel(command.entry), 1,
                                    f"the skill '{name}' takes precedence over this command of the same name: "
                                    "delete one of the two"))
    findings.extend(_similar_descriptions(real))
    findings.extend(_per_model(real))
    return findings


def _desc_key(skill: Skill) -> str:
    return re.sub(r"\s+", " ", skill.description).strip().lower()


def _similar_descriptions(real: list[Skill]) -> list[Finding]:
    findings: list[Finding] = []
    items = [(s, _desc_key(s)) for s in real if len(_desc_key(s)) >= MIN_DESC]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, da = items[i]
            b, db = items[j]
            if a.name == b.name:
                continue
            matcher = difflib.SequenceMatcher(None, da, db)
            if matcher.real_quick_ratio() < SIMILAR_DESC or matcher.quick_ratio() < SIMILAR_DESC:
                continue
            ratio = matcher.ratio()
            if ratio >= SIMILAR_DESC:
                findings.append(Finding("G-LIB-02", "INFO", a.rel(a.entry), 1,
                                        f"'{a.name}' and '{b.name}' have near-identical descriptions ({ratio:.0%}): "
                                        "they compete for the same requests. Merge them or sharpen the boundaries"))
    return findings


def _per_model(real: list[Skill]) -> list[Finding]:
    findings: list[Finding] = []
    groups: dict[str, list[Skill]] = {}
    for s in real:
        tokens = re.split(r"[-_.]", s.name.lower())
        if not any(t in MODEL_FAMILIES for t in tokens):
            continue
        base = "-".join(t for t in tokens if t not in MODEL_FAMILIES)
        groups.setdefault(base, []).append(s)
    for base, group in sorted(groups.items()):
        names = ", ".join(sorted(s.name for s in group))
        if len(group) >= 2:
            findings.append(Finding("G-MODEL-01", "WARN", group[0].rel(group[0].entry), 1,
                                    f"per-model copies of one skill ({names}): merge them into one skill and move "
                                    "the measured differences to references/models/<family>.md"))
        else:
            findings.append(Finding("G-MODEL-01", "INFO", group[0].rel(group[0].entry), 1,
                                    f"'{names}' names a model family: if it is a per-model variant, merge it into the "
                                    "base skill with a model appendix"))
    return findings


# --- Report --------------------------------------------------------------------------------------------
def audit(roots: list[Path], with_commands: bool = True, shared: bool = False) -> dict[str, object]:
    skills, walk_errors = discover(roots, with_commands)
    for skill in skills:
        audit_skill(skill, shared)
        walk_errors.extend(skill.unreadable)
    library = library_checks(skills)
    all_findings = [f for s in skills for f in s.findings] + library
    return {
        "roots": [r.as_posix() for r in roots],
        "skills": [
            {
                "path": s.rel(s.entry),
                "kind": s.kind,
                "location": s.location,
                "name": s.name,
                "lines": len(s.lines),
                "approx_tokens": len("\n".join(s.lines[s.body_start:])) // CHARS_PER_TOKEN,
                "findings": [f.as_dict() for f in sorted(s.findings, key=_order)],
            }
            for s in sorted(skills, key=lambda s: s.rel(s.entry))
        ],
        "library_findings": [f.as_dict() for f in sorted(library, key=_order)],
        "incomplete": walk_errors,
        "summary": {
            "skills": sum(1 for s in skills if s.kind != "command"),
            "commands": sum(1 for s in skills if s.kind == "command"),
            "synced": sum(1 for s in skills if s.kind == "synced"),
            "mirrored": _mirrored_count(skills),
            "locations": _location_counts(skills),
            "errors": sum(1 for f in all_findings if f.level == "ERROR"),
            "warnings": sum(1 for f in all_findings if f.level == "WARN"),
            "infos": sum(1 for f in all_findings if f.level == "INFO"),
        },
    }


def _location_counts(skills: list[Skill]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in skills:
        if s.kind != "command":
            counts[s.location] = counts.get(s.location, 0) + 1
    return dict(sorted(counts.items()))


def _mirrored_count(skills: list[Skill]) -> int:
    """Names that exist both in a .claude and in an .agents skills folder: one unit of work, two files."""
    claude = {s.name for s in skills if s.kind != "command" and s.location == "claude"}
    agents = {s.name for s in skills if s.kind != "command" and s.location == "agents"}
    return len(claude & agents)


def _order(f: Finding) -> tuple[int, str, str, int]:
    return (LEVEL_RANK[f.level], f.id, f.file, f.line)


def print_text(report: dict[str, object], min_level: str) -> None:
    limit = LEVEL_RANK[min_level]
    summary = report["summary"]
    where = ", ".join(f"{count} {name}" for name, count in summary["locations"].items())
    print(f"Skill audit of {', '.join(report['roots'])}: {summary['skills']} skills ({where}), "
          f"{summary['commands']} commands; {summary['mirrored']} mirrored, {summary['synced']} synced")
    for s in report["skills"]:
        shown = [f for f in s["findings"] if LEVEL_RANK[f["level"]] <= limit]
        status = "ok" if not s["findings"] else f"{len(s['findings'])} findings"
        print(f"\n{s['path']}  [{s['kind']}, {s['location']}]  {s['lines']} lines, ~{s['approx_tokens']} tokens  {status}")
        for f in shown:
            print(f"  {f['level']:5} {f['id']:12} {f['file']}:{f['line']}  {f['message']}")
    library = [f for f in report["library_findings"] if LEVEL_RANK[f["level"]] <= limit]
    if library:
        print("\nCollection")
        for f in library:
            location = f"{f['file']}:{f['line']}" if f["file"] else "-"
            print(f"  {f['level']:5} {f['id']:12} {location}  {f['message']}")
    print(f"\nErrors: {summary['errors']} | Warnings: {summary['warnings']} | Infos: {summary['infos']}")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252 and die on the first arrow
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path, help="project roots, skill folders or SKILL.md files")
    parser.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output on stdout")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    parser.add_argument("--shared", action="store_true",
                        help="treat every skill as shared with other agents or claude.ai (portable fields only)")
    parser.add_argument("--no-commands", action="store_true", help="skip .claude/commands files")
    parser.add_argument("--min-level", choices=("ERROR", "WARN", "INFO"), default="INFO",
                        help="hide lower levels in the text report (the JSON always carries everything)")
    args = parser.parse_args(argv)

    missing = [str(p) for p in args.paths if not p.exists()]
    if missing:
        print(f"error: path not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    try:
        report = audit(list(args.paths), with_commands=not args.no_commands, shared=args.shared)
    except Exception as exc:  # report the crash as a crash: a silent partial audit would read as clean
        print(f"execution error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report, args.min_level)
    if report["incomplete"]:
        # Folders that could not be read are skills that were never looked at: never report that as a pass.
        print("error: the inventory is incomplete, so this audit cannot be trusted:", file=sys.stderr)
        for message in report["incomplete"]:
            print(f"  {message}", file=sys.stderr)
        return 2
    summary = report["summary"]
    blocking = summary["errors"] + (summary["warnings"] if args.strict else 0)
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
