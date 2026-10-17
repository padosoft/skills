#!/usr/bin/env python3
"""
check_freshness.py - Is the rulebook of padosoft-skill-audit still in line with its sources?

The rules in references/guidelines.md condense official pages that change: a new model gets its own
prompting guide, a best practice is reworded, Claude Code adds a frontmatter field. This script is the
cheap, deterministic half of keeping up. It does not judge what changed; it says *that* something changed
and which rules depend on it, so the research that follows reads only what drifted.

Checks, driven by references/sources.json:
  1. copy      - is this installed copy older than the one on the main branch of padosoft/skills?
  2. anchors   - is every sentence a rule rests on still on its source page?
  3. sections  - did a tracked page gain or lose section headings?
  4. models    - do the model pages name a model the rules do not cover yet?
  5. fields    - does the Claude Code frontmatter reference list fields the rules do not know?
  6. --model   - is the model running the audit one the rules cover?

Usage:
  python3 scripts/check_freshness.py
  python3 scripts/check_freshness.py --model "Claude Opus 5.5" --json
  python3 scripts/check_freshness.py --offline tests/fixtures/skill-freshness/aligned
  python3 scripts/check_freshness.py --rebaseline        # maintainers only, after updating the rules

Exit code: 0 aligned (or partial: some pages unreachable, listed) | 1 drift found |
           2 could not verify (no page readable, manifest or arguments)
"""
from __future__ import annotations

import argparse
import html
import http.client
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Every way a fetch can fail without being a bug here: no network, an HTTP error, a response cut short.
FETCH_ERRORS = (OSError, urllib.error.URLError, http.client.HTTPException, ValueError)
SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = SKILL_DIR / "references" / "sources.json"
DEFAULT_SKILL_MD = SKILL_DIR / "SKILL.md"
USER_AGENT = "padosoft-skill-audit (+https://github.com/padosoft/skills)"
# Documentation pages answer in well under a second; 20 s covers a slow link without hanging a CI job.
DEFAULT_TIMEOUT = 20

MODEL_RE = re.compile(r"\bClaude (Opus|Sonnet|Haiku|Fable|Mythos) (\d+(?:\.\d+)?)\b")
# A new family would not match MODEL_RE: catch "Claude <Name> <version>" for names that are not products.
FAMILY_RE = re.compile(r"\bClaude ([A-Z][a-z]+) (\d+(?:\.\d+)?)\b")
NOT_A_MODEL = {"Code", "Design", "Desktop", "Docs", "Tag", "Cowork", "Opus", "Sonnet", "Haiku", "Fable", "Mythos"}
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*#*\s*$")
FIELD_ROW_RE = re.compile(r"^\|\s*`([a-z][a-z0-9_-]*)`\s*\|")
VERSION_RE = re.compile(r"^\s+version:\s*['\"]?([0-9][0-9A-Za-z.\-]*)['\"]?\s*$", re.MULTILINE)
# "claude-opus-5-5", "Claude Opus 5.5", "claude-foo-9"; a bare "opus 5.5" is accepted for the known families.
RUNNING_MODEL_RE = re.compile(r"(?:claude[\s_-]+)?([a-z]+)[\s_-]+(\d+)(?:[.\s_-](\d+))?", re.IGNORECASE)
KNOWN_FAMILIES = {"opus", "sonnet", "haiku", "fable", "mythos"}


@dataclass
class Item:
    kind: str  # outdated-copy | missing-anchor | new-section | removed-section | new-model | new-field | removed-field | uncovered-model | unreachable
    source: str
    detail: str
    rules: list[str] = field(default_factory=list)


@dataclass
class Result:
    drift: list[Item] = field(default_factory=list)
    unreachable: list[Item] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    model: str = ""  # what was concluded about the running model: covered | uncovered | unrecognised | not given
    checked: int = 0

    @property
    def status(self) -> str:
        # One slow page must not make every audit "unverifiable": only drift, or no source read at all, count.
        if self.drift:
            return "drift"
        if self.checked == 0:
            return "unverifiable"
        return "partial" if self.unreachable else "aligned"


def normalize(text: str) -> str:
    """Compare meaning, not formatting: quotes, dashes, emphasis and line wrapping change without notice."""
    text = html.unescape(text)
    for old, new in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                     ("—", "-"), ("–", "-"), (" ", " ")):
        text = text.replace(old, new)
    text = re.sub(r"[`*_\\]", "", text)
    return re.sub(r"\s+", " ", text).lower().strip()


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    return html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))


FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")


def headings_of(markdown: str) -> list[str]:
    """H2/H3 headings outside fenced code: examples inside fences contain headings that are not the page's.

    A fence closes only on a delimiter of the same character, at least as long as the opening one, with
    nothing after it: a four-backtick example may hold a three-backtick block without ending early.
    """
    found: list[str] = []
    opened = ""
    for line in markdown.splitlines():
        fence = FENCE_RE.match(line)
        if fence:
            marker, rest = fence.group(1), fence.group(2)
            if not opened:
                opened = marker
                continue
            if marker[0] == opened[0] and len(marker) >= len(opened) and not rest.strip():
                opened = ""
            continue
        if opened:
            continue
        match = HEADING_RE.match(line)
        if match:
            found.append(normalize(match.group(2)))
    return found


def models_in(text: str) -> set[str]:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", html.unescape(text))  # a link is its visible label
    text = re.sub(r"[`*_]", "", text)  # emphasis and code markers are not part of a name
    text = re.sub(r"\s+", " ", text)  # a soft-wrapped "Claude Opus\n6" is the same name
    names = {f"{family} {version}" for family, version in MODEL_RE.findall(text)}
    names |= {f"{family} {version}" for family, version in FAMILY_RE.findall(text) if family not in NOT_A_MODEL}
    return names


def cc_fields_in(markdown: str, section: str) -> set[str]:
    """Field names from the first table under the given heading of the Claude Code skills reference."""
    lines = markdown.splitlines()
    start = next((i for i, line in enumerate(lines) if HEADING_RE.match(line) and section.lower() in line.lower()), None)
    if start is None:
        return set()
    fields: set[str] = set()
    for line in lines[start + 1:]:
        if HEADING_RE.match(line):
            break
        match = FIELD_ROW_RE.match(line)
        if match:
            fields.add(match.group(1))
    return fields


def running_model(name: str) -> str | None:
    """'claude-opus-5-5', 'Claude Opus 5.5', 'opus 5.5' -> 'Opus 5.5'. None when it is not a Claude model name.

    A name that starts with "claude" is parsed whatever the family, so a family that did not exist when the
    rules were written shows up as uncovered instead of being skipped.
    """
    is_claude = "claude" in name.lower()
    for match in RUNNING_MODEL_RE.finditer(name):
        family = match.group(1).lower()
        if family == "claude" or not (is_claude or family in KNOWN_FAMILIES):
            continue
        major, minor = match.group(2), match.group(3)
        label = family.capitalize()
        return f"{label} {major}.{minor}" if minor else f"{label} {major}"
    return None


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3])


def skill_version(text: str) -> str | None:
    """metadata.version from the frontmatter only: the body may quote other versions."""
    if not text.startswith("---"):
        return None
    match = VERSION_RE.search(text.split("\n---", 1)[0])
    return match.group(1) if match else None


class Fetcher:
    """Live pages over HTTPS, or files from a directory for tests and air-gapped runs."""

    def __init__(self, offline: Path | None, timeout: int) -> None:
        self.offline = offline
        self.timeout = timeout
        self.flattened: set[str] = set()  # keys served as HTML: converted to text, headings and tables are gone

    def get(self, key: str, url: str, timeout: int | None = None) -> str:
        if self.offline is not None:
            for suffix in (".md", ".html", ".txt"):
                candidate = self.offline / f"{key.lower()}{suffix}"
                if candidate.is_file():
                    text = candidate.read_text(encoding="utf-8", errors="replace")
                    if suffix == ".html":
                        self.flattened.add(key)
                        return html_to_text(text)
                    return text
            raise OSError(f"no offline copy for {key} in {self.offline}")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:  # noqa: S310 - fixed https URLs
            body = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")
        if "html" in content_type:
            self.flattened.add(key)
            return html_to_text(body)
        return body


def check(manifest: dict, fetcher: Fetcher, skill_md: Path | None, model: str | None) -> Result:
    result = Result()
    covered = set(manifest.get("covered_models", []))
    pages: dict[str, str | None] = {}

    def page(key: str, url: str, timeout: int | None = None) -> str | None:
        if key in pages:  # failures are cached too: a page is reported unreachable once, not once per check
            return pages[key]
        try:
            pages[key] = fetcher.get(key, url, timeout)
        except FETCH_ERRORS as exc:
            pages[key] = None
            result.unreachable.append(Item("unreachable", key, f"{url}: {exc}"))
            return None
        result.checked += 1
        return pages[key]

    upstream = manifest.get("upstream", {})
    if skill_md is not None and skill_md.is_file() and upstream.get("skill_md"):
        local = skill_version(skill_md.read_text(encoding="utf-8", errors="replace"))
        # Not a source of rules: a failure here (offline, or a copy not merged yet) is a note, not "unverifiable".
        try:
            remote_text = fetcher.get("upstream-skill", upstream["skill_md"])
        except FETCH_ERRORS as exc:
            remote_text = None
            result.notes.append(f"published copy not readable, copy check skipped: {exc}")
        remote = skill_version(remote_text) if remote_text else None
        if local and remote and version_tuple(remote) > version_tuple(local):
            hint = upstream.get("install", "update the skill")
            result.drift.append(Item("outdated-copy", "upstream", f"installed {local}, published {remote}: {hint}"))

    for source in manifest.get("sources", []):
        if not source.get("fetch", True):
            continue
        text = page(source["key"], source["url"], source.get("timeout"))
        if text is None:
            continue
        flat = normalize(text)
        for anchor in source.get("anchors", []):
            if normalize(anchor["text"]) not in flat:
                result.drift.append(Item("missing-anchor", source["key"], anchor["text"], anchor.get("rules", [])))
        if source.get("track_headings") and source["key"] in fetcher.flattened:
            result.notes.append(f"{source['key']}: served as HTML, so section headings were not compared")
        elif source.get("track_headings") and "headings" in source:
            current, baseline = set(headings_of(text)), set(source["headings"])
            for heading in sorted(current - baseline):
                result.drift.append(Item("new-section", source["key"], heading, source.get("rules", [])))
            for heading in sorted(baseline - current):
                result.drift.append(Item("removed-section", source["key"], heading, source.get("rules", [])))

    by_key = {s["key"]: s for s in manifest.get("sources", [])}
    for key in manifest.get("model_pages", []):
        text = pages.get(key) or (page(key, by_key[key]["url"]) if key in by_key else None)
        if text is None:
            continue
        found = models_in(text)
        if not found:
            # A maintenance page, a changed naming format: nothing to compare is not "nothing changed".
            result.drift.append(Item("unreadable-models", key, "no model name could be read from the page",
                                     ["G-GEN-01", "G-MODEL-05", "G-MODEL-07"]))
        for name in sorted(found - covered):
            result.drift.append(Item("new-model", key, name, ["G-GEN-01", "G-MODEL-05", "G-MODEL-07"]))

    fields_cfg = manifest.get("claude_code_fields")
    if fields_cfg and fields_cfg.get("source") in by_key:
        key = fields_cfg["source"]
        text = pages.get(key) or page(key, by_key[key]["url"])
        if text is not None and key in fetcher.flattened:
            result.notes.append(f"{key}: served as HTML, so the frontmatter field table was not compared")
        elif text is not None:
            found, known = cc_fields_in(text, fields_cfg.get("section", "Frontmatter reference")), set(fields_cfg.get("known", []))
            if not found:
                # Not "nothing changed": the table is gone or its format changed, and no field was checked.
                result.drift.append(Item("unreadable-fields", key, "no field names could be read from the "
                                         f"{fields_cfg.get('section', 'Frontmatter reference')!r} table", ["G-FM-03", "G-FM-04"]))
            for name in sorted(found - known):
                result.drift.append(Item("new-field", key, name, ["G-FM-03", "G-FM-04"]))
            for name in sorted(known - found if found else set()):
                result.drift.append(Item("removed-field", key, name, ["G-FM-03", "G-FM-04"]))

    if not model:
        result.model = "not given"
        return result
    normalized = running_model(model)
    if normalized is None:
        result.model = f"unrecognised ({model!r}): not a Claude model name, model check skipped"
    elif normalized in covered:
        result.model = f"{normalized}: covered"
    else:
        result.model = f"{normalized}: not covered"
        result.drift.append(Item("uncovered-model", "session", normalized, ["G-GEN-01", "G-MODEL-05"]))
    return result


def rebaseline(manifest: dict, fetcher: Fetcher) -> list[str]:
    """Maintainers only: record the live headings, models and fields as the reviewed baseline."""
    notes: list[str] = []
    by_key = {s["key"]: s for s in manifest.get("sources", [])}
    models: set[str] = set(manifest.get("covered_models", []))
    for source in manifest.get("sources", []):
        if not source.get("fetch", True):
            continue
        text = fetcher.get(source["key"], source["url"], source.get("timeout"))
        if source.get("track_headings") and source["key"] in fetcher.flattened:
            raise ValueError(f"{source['key']} was served as HTML, which has no headings to record: use a Markdown copy")
        if source.get("track_headings"):
            source["headings"] = headings_of(text)
            notes.append(f"{source['key']}: {len(source['headings'])} headings")
        if source["key"] in manifest.get("model_pages", []):
            models |= models_in(text)
    manifest["covered_models"] = sorted(models, key=lambda m: (m.split()[0], version_tuple(m)))
    fields_cfg = manifest.get("claude_code_fields")
    if fields_cfg and fields_cfg.get("source") in by_key:
        text = fetcher.get(fields_cfg["source"], by_key[fields_cfg["source"]]["url"])
        if fields_cfg["source"] in fetcher.flattened:
            raise ValueError(f"{fields_cfg['source']} was served as HTML, which has no field table to record")
        found = cc_fields_in(text, fields_cfg.get("section", "Frontmatter reference"))
        if not found:
            raise ValueError(f"no field names could be read from the {fields_cfg.get('section', 'Frontmatter reference')!r} "
                             "table, so there is no baseline to record")
        fields_cfg["known"] = sorted(found)
        notes.append(f"Claude Code fields: {len(found)}")
    notes.append(f"covered models: {len(manifest['covered_models'])}")
    return notes


def render(result: Result) -> str:
    labels = {
        "outdated-copy": "This copy is older than the published skill",
        "missing-anchor": "A sentence a rule rests on is no longer on its page",
        "new-section": "New section on a tracked page",
        "removed-section": "Section removed from a tracked page",
        "new-model": "Model not covered by the rules yet",
        "new-field": "New Claude Code frontmatter field",
        "removed-field": "Claude Code frontmatter field no longer documented",
        "unreadable-fields": "The Claude Code frontmatter table could not be read",
        "uncovered-model": "The running model is not covered by the rules",
        "unreadable-models": "A model page yielded no model name",
    }
    out: list[str] = []
    for item in result.drift:
        rules = f"  -> re-check {', '.join(item.rules)}" if item.rules else ""
        out.append(f"DRIFT [{item.source}] {labels.get(item.kind, item.kind)}: {item.detail}{rules}")
    for item in result.unreachable:
        out.append(f"UNREACHABLE [{item.source}] {item.detail}")
    for note in result.notes:
        out.append(f"NOTE {note}")
    rules = sorted({r for item in result.drift for r in item.rules})
    out.append("")
    out.append(f"Model: {result.model}")
    out.append(f"Sources checked: {result.checked} | drift: {len(result.drift)} | unreachable: {len(result.unreachable)}"
               f" | status: {result.status.upper()}")
    if rules:
        out.append(f"Rules to re-check: {', '.join(rules)}")
    if result.status == "drift":
        out.append("Next: references/refresh-procedure.md (research only what drifted).")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252 and crash on non-ASCII
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="default: references/sources.json")
    parser.add_argument("--skill-md", type=Path, default=DEFAULT_SKILL_MD, help="installed SKILL.md, for the copy check")
    parser.add_argument("--no-version-check", action="store_true", help="skip the installed-copy check")
    parser.add_argument("--model", help="the model running the audit, e.g. 'Claude Opus 5.5' or 'claude-opus-5-5'")
    parser.add_argument("--offline", type=Path, help="read pages from DIR/<key>.md|.html instead of the network")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"seconds per page (default {DEFAULT_TIMEOUT})")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--rebaseline", action="store_true",
                        help="maintainers: rewrite headings, covered models and known fields in the manifest")
    args = parser.parse_args(argv)

    if not args.manifest.is_file():
        print(f"Manifest not found: {args.manifest}. Pass --manifest PATH.", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Manifest unreadable: {exc}", file=sys.stderr)
        return 2
    if args.offline is not None and not args.offline.is_dir():
        print(f"--offline must be a directory: {args.offline}", file=sys.stderr)
        return 2
    fetcher = Fetcher(args.offline, args.timeout)

    if args.rebaseline:
        try:
            notes = rebaseline(manifest, fetcher)
        except FETCH_ERRORS as exc:
            print(f"Rebaseline aborted, manifest untouched: {exc}", file=sys.stderr)
            return 2
        args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("\n".join(notes))
        print(f"Written {args.manifest}. Review the diff: it records what you assert has been reviewed.")
        return 0

    skill_md = None if args.no_version_check else args.skill_md
    result = check(manifest, fetcher, skill_md, args.model)
    if args.json:
        payload = {
            "status": result.status,
            "model": result.model,
            "checked_sources": result.checked,
            "drift": [asdict(i) for i in result.drift],
            "unreachable": [asdict(i) for i in result.unreachable],
            "notes": result.notes,
            "rules_to_recheck": sorted({r for i in result.drift for r in i.rules}),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render(result))
    if result.status == "drift":
        return 1
    return 2 if result.status == "unverifiable" else 0  # "partial" is a pass: the unreachable pages are listed


if __name__ == "__main__":
    sys.exit(main())
