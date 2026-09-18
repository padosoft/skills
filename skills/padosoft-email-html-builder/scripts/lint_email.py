#!/usr/bin/env python3
"""
lint_email.py - Static linter for HTML email, following references/rules.md.

Usage:
    python3 lint_email.py email.html [--text email.txt] [--subject "Subject"]
                          [--production] [--transactional] [--json]

Exit code:
    0 = no MUST violated
    1 = at least one MUST violated
    2 = execution error (missing file, parse)

Standard library only: no dependencies, runnable in CI.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

# --------------------------------------------------------------------------------------
# Rule configuration
# --------------------------------------------------------------------------------------

#: CSS properties allowed inline in the <body> (R-100)
INLINE_WHITELIST: frozenset[str] = frozenset({
    "font-family", "font-size", "line-height", "font-weight", "font-style",
    "letter-spacing", "color", "text-decoration", "text-align",
})

#: Properties forbidden in the <style> block outside the media query (R-301)
STYLE_FORBIDDEN_SELECTORS: tuple[str, ...] = (
    r"(^|[}\s,])body\s*[{,]", r"(^|[}\s,])table\s*[{,]", r"(^|[}\s,])img\s*[{,]",
    r"(^|[}\s,])a\s*[{,]", r":root", r"prefers-color-scheme", r"\[data-ogs",
    r"u\s*\+\s*#body", r"@font-face", r"@import", r"\.preheader",
)
STYLE_FORBIDDEN_PROPS: tuple[str, ...] = (
    "border-collapse", "outline", "visibility", "-webkit-text-size-adjust",
    "-ms-text-size-adjust", "color-scheme",
)

FORBIDDEN_TAGS: frozenset[str] = frozenset({
    "script", "form", "input", "iframe", "object", "embed", "video", "audio",
    "svg", "link", "button", "select", "textarea", "h1",
})

INVISIBLE_FILLER = re.compile(r"(&#847;|&zwnj;|&#8203;|&#x200b;|&#x34f;)", re.I)
#: Placeholder text. The repo is in English, but the emails it lints are often Italian,
#: so both spellings stay in the pattern on purpose.
PLACEHOLDERS = re.compile(r"(example\.com|placehold\.co|\[Legal entity\]|\[Address\]|\[Ragione sociale\]|\[Indirizzo\]|\bTODO\b|\blorem ipsum\b|\bx{6,}\b)", re.I)
SHORTENERS = re.compile(r"https?://(bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|is\.gd|buff\.ly)/", re.I)
#: Subject trigger words, English and Italian: same reason as PLACEHOLDERS above.
SPAM_WORDS = re.compile(r"\b(gratis|urgente|100%|clicca qui|click here|free!!|guadagna|act now|earn money|\$\$\$)\b", re.I)
MAX_HTML_BYTES_MUST = 100_000
TARGET_HTML_BYTES = 40_000


# --------------------------------------------------------------------------------------
# Result model
# --------------------------------------------------------------------------------------

@dataclass
class Finding:
    rule: str
    level: str  # MUST | SHOULD
    message: str
    line: int | None = None


@dataclass
class Report:
    file: str
    bytes: int
    findings: list[Finding] = field(default_factory=list)

    def add(self, rule: str, level: str, message: str, line: int | None = None) -> None:
        self.findings.append(Finding(rule, level, message, line))

    @property
    def must_count(self) -> int:
        return sum(1 for f in self.findings if f.level == "MUST")


# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------

def parse_style(style: str) -> list[tuple[str, str]]:
    """Splits an inline style string into normalised (property, value) pairs."""
    pairs: list[tuple[str, str]] = []
    for decl in style.split(";"):
        if ":" not in decl:
            continue
        prop, value = decl.split(":", 1)
        prop = prop.strip().lower()
        if not prop:
            continue
        pairs.append((prop, value.strip()))
    return pairs


def hex_to_luminance(hex_color: str) -> float | None:
    """WCAG relative luminance of an #rgb/#rrggbb color; None when it cannot be parsed."""
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return None
    channels: list[float] = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(fg: str, bg: str) -> float | None:
    """WCAG contrast ratio between two hexadecimal colors."""
    l1, l2 = hex_to_luminance(fg), hex_to_luminance(bg)
    if l1 is None or l2 is None:
        return None
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


# --------------------------------------------------------------------------------------
# Structural parser
# --------------------------------------------------------------------------------------

class EmailParser(HTMLParser):
    """Visita il DOM tenendo traccia di bgcolor ereditato, tag aperti e anomalie."""

    VOID: frozenset[str] = frozenset({"img", "br", "meta", "hr", "input", "link", "col", "area", "base", "source", "wbr"})

    def __init__(self, report: Report) -> None:
        super().__init__(convert_charrefs=False)
        self.r = report
        self.stack: list[tuple[str, str | None]] = []  # (tag, effective bgcolor)
        self.in_body: bool = False
        self.in_style: bool = False
        self.style_blocks: list[str] = []
        self.body_attrs: dict[str, str] = {}
        self.html_attrs: dict[str, str] = {}
        self.has_title: bool = False
        self.in_title: bool = False
        self.title_text: str = ""
        self.meta: dict[str, str] = {}
        self.text_chunks: list[tuple[str, str | None, str | None, int]] = []  # (text, color, bg, line)
        self.color_stack: list[str | None] = []
        self.imgs: int = 0
        self.links: list[tuple[str, int]] = []
        self.heading_found: bool = False
        self.ids: set[str] = set()

    # -- helpers -------------------------------------------------------------------------
    def _current_bg(self) -> str | None:
        for _, bg in reversed(self.stack):
            if bg:
                return bg
        if self.body_attrs.get("bgcolor"):
            return self.body_attrs["bgcolor"]
        for prop, value in parse_style(self.body_attrs.get("style", "")):
            if prop in ("background-color", "background") and value.strip().startswith("#"):
                return value.split()[0].strip().rstrip(";")
        return None

    def _current_color(self) -> str | None:
        for c in reversed(self.color_stack):
            if c:
                return c
        return self.body_attrs.get("text")

    # -- callbacks -----------------------------------------------------------------------
    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs: dict[str, str] = {k.lower(): (v or "") for k, v in attrs_list}
        line, _ = self.getpos()

        if tag == "html":
            self.html_attrs = attrs
        if tag == "meta":
            key = (attrs.get("name") or attrs.get("http-equiv") or ("charset" if "charset" in attrs else "")).lower()
            if key:
                self.meta[key] = attrs.get("content", attrs.get("charset", ""))
        if tag == "title":
            self.in_title = True
        if tag == "style":
            self.in_style = True
        if tag == "body":
            self.in_body = True
            self.body_attrs = attrs

        # R-011 / R-007: forbidden tags
        if tag in FORBIDDEN_TAGS:
            rule = "R-007" if tag == "h1" else "R-011"
            self.r.add(rule, "MUST", f"Tag <{tag}> is forbidden", line)

        # R-010: duplicate ids
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.r.add("R-010", "MUST", f"id duplicato '{attrs['id']}'", line)
            self.ids.add(attrs["id"])

        # R-011: JS handlers
        for k in attrs:
            if k.startswith("on"):
                self.r.add("R-011", "MUST", f"JS attribute '{k}' is forbidden", line)

        # R-004: tables
        if tag == "table":
            for req, val in (("role", "presentation"), ("cellpadding", None), ("cellspacing", "0"), ("border", "0")):
                if req not in attrs:
                    self.r.add("R-004", "MUST", f"<table> without the {req} attribute", line)
                elif val is not None and attrs[req] != val:
                    self.r.add("R-004", "MUST", f"<table> {req}='{attrs[req]}' (expected '{val}')", line)

        # R-100/R-101: inline CSS in the body
        style = attrs.get("style", "")
        color_here: str | None = None
        bg_here: str | None = attrs.get("bgcolor")
        if self.in_body and style:
            props = parse_style(style)
            names = {p for p, _ in props}
            is_preheader = tag == "div" and names <= {"display", "mso-hide"} and "display" in names
            for prop, value in props:
                if prop.startswith("mso-"):
                    continue
                if prop == "color":
                    color_here = value.lower()
                # a background declared through CSS is already a violation (R-101), but it is
                # still needed as the effective background for the contrast calculation (R-501)
                if prop in ("background-color", "background") and value.strip().startswith("#"):
                    bg_here = value.split()[0].strip().rstrip(";")
                if prop in INLINE_WHITELIST:
                    continue
                if is_preheader:
                    continue
                self.r.add("R-101", "MUST", f"inline CSS '{prop}' forbidden on <{tag}> (use HTML attributes, see §4)", line)
            if is_preheader:
                if attrs.get("aria-hidden") != "true":
                    self.r.add("R-400", "MUST", "Preheader without aria-hidden=\"true\"", line)

        # R-600/R-601: images
        if tag == "img":
            self.imgs += 1
            src = attrs.get("src", "")
            for req in ("width", "height", "alt"):
                if req not in attrs:
                    self.r.add("R-600", "MUST", f"<img> without the {req} attribute", line)
            if attrs.get("border") != "0":
                self.r.add("R-600", "MUST", "<img> without border=\"0\"", line)
            if not src.startswith("https://"):
                self.r.add("R-600", "MUST", f"<img> src is not an absolute HTTPS URL: {src[:60]}", line)
            if " " in src:
                self.r.add("R-458", "MUST", "Image path contains spaces", line)
            if len(attrs.get("alt", "")) > 60:
                self.r.add("R-600", "SHOULD", "alt longer than 60 characters", line)
            parent = next((t for t in reversed(self.stack) if t[0] == "td"), None)
            if parent is None:
                self.r.add("R-601", "MUST", "<img> not contained in a <td>", line)

        if tag == "td" and "height" not in attrs:
            pass  # the R-601 check on the cell is done textually (see lint_text)

        # link
        if tag == "a":
            href = attrs.get("href", "")
            self.links.append((href, line))

        # R-007: heading
        if attrs.get("role") == "heading":
            self.heading_found = True

        if tag not in self.VOID:
            self.stack.append((tag, bg_here))
            self.color_stack.append(color_here)

    def handle_endtag(self, tag: str) -> None:
        line, _ = self.getpos()
        if tag == "style":
            self.in_style = False
        if tag == "title":
            self.in_title = False
        if tag in self.VOID:
            return
        # R-010: balancing (tolerant with non-structural inline tags)
        idx = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
        if idx is None:
            self.r.add("R-010", "MUST", f"</{tag}> without an opening tag", line)
            return
        if tag in ("table", "tr", "td") and idx != len(self.stack) - 1:
            opened = self.stack[-1][0]
            self.r.add("R-010", "MUST", f"</{tag}> chiude mentre <{opened}> e' ancora aperto", line)
        del self.stack[idx:]
        del self.color_stack[idx:]

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.style_blocks.append(data)
            return
        if self.in_title:
            self.title_text += data
        if self.in_body and data.strip() and data.strip() != "&nbsp;":
            line, _ = self.getpos()
            self.text_chunks.append((data.strip(), self._current_color(), self._current_bg(), line))

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")


# --------------------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------------------

def lint_text_level(html: str, r: Report, production: bool) -> None:
    """Controlli sul sorgente grezzo."""
    lines = html.splitlines()

    # R-050 weight
    if r.bytes >= MAX_HTML_BYTES_MUST:
        r.add("R-050", "MUST", f"HTML {r.bytes} bytes >= {MAX_HTML_BYTES_MUST}")
    elif r.bytes > TARGET_HTML_BYTES:
        r.add("R-050", "SHOULD", f"HTML {r.bytes} bytes > target {TARGET_HTML_BYTES}")

    # R-001 doctype / namespace
    if not html.lstrip().lower().startswith("<!doctype html>"):
        r.add("R-001", "MUST", "Missing <!DOCTYPE html> at the top")
    if 'xmlns:v="urn:schemas-microsoft-com:vml"' not in html or 'xmlns:o="urn:schemas-microsoft-com:office:office"' not in html:
        r.add("R-001", "MUST", "Missing xmlns:v / xmlns:o namespaces")

    # R-003
    if "OfficeDocumentSettings" not in html:
        r.add("R-003", "MUST", "Missing OfficeDocumentSettings in <!--[if mso]>")

    # R-402 ASCII
    for n, ln in enumerate(lines, 1):
        bad = [c for c in ln if ord(c) > 127]
        if bad:
            r.add("R-402", "MUST", f"Non-ASCII character {bad[0]!r} (use a numeric entity)", n)
            break

    # R-401 filler
    for n, ln in enumerate(lines, 1):
        if INVISIBLE_FILLER.search(ln):
            r.add("R-401", "MUST", "Invisible filler in the source (DOS_BODY_HIGH_NO_MID)", n)
            break

    # R-304
    for m in re.finditer(r"<!--(.*?)-->", html, re.S):
        if "<style" in m.group(1).lower():
            r.add("R-304", "MUST", "HTML comment contains '<style'", html[:m.start()].count("\n") + 1)

    # R-400 preheader
    if not re.search(r'<!--\[if !mso\]><!-->\s*<div[^>]*style="display:none; ?mso-hide:all;?"', html):
        r.add("R-400", "MUST", "Preheader missing or not in the format <!--[if !mso]><!--><div style=\"display:none; mso-hide:all;\">")

    # R-700/R-701 CTA
    if "v:roundrect" in html:
        vml = re.search(r'v:roundrect[^>]*style="[^"]*height:(\d+)px[^"]*width:(\d+)px', html)
        if vml:
            h, w = vml.group(1), vml.group(2)
            if not re.search(rf'<table[^>]*width="{w}"[^>]*>\s*<tr>\s*<td[^>]*height="{h}"', html):
                r.add("R-701", "MUST", f"VML {w}x{h} without a non-mso table with width=\"{w}\" and td height=\"{h}\"")
        if "<!--[if !mso]><!-->" not in html:
            r.add("R-700", "MUST", "VML CTA without the <!--[if !mso]><!--> branch")
    if re.search(r"\bstroke=\"t|strokecolor=", html):
        r.add("R-700", "SHOULD", "VML with a stroke: prefer stroke=\"f\"")

    # R-601 image cells with height
    for m in re.finditer(r"<td([^>]*)>\s*(?:<a[^>]*>\s*)?<img", html):
        if 'height="' not in m.group(1):
            r.add("R-601", "MUST", "Cell containing <img> without a height attribute", html[:m.start()].count("\n") + 1)
        if 'bgcolor="' not in m.group(1):
            r.add("R-601", "SHOULD", "Cell containing <img> without bgcolor", html[:m.start()].count("\n") + 1)
        if "font-size:0" not in m.group(1).replace(" ", ""):
            r.add("R-208", "MUST", "Image cell without font-size:0; line-height:0", html[:m.start()].count("\n") + 1)

    # R-801 fractional percentages
    for m in re.finditer(r'width="(\d+\.\d+)%"', html):
        r.add("R-801", "MUST", f"Fractional width {m.group(1)}%", html[:m.start()].count("\n") + 1)

    # R-409 shortener
    if SHORTENERS.search(html):
        r.add("R-409", "MUST", "URL shortener in the links")

    # R-901 placeholder
    ph = sorted({m.group(0) for m in PLACEHOLDERS.finditer(html)})
    if ph:
        r.add("R-901", "MUST" if production else "SHOULD", f"Placeholders present: {', '.join(ph)}")


def lint_style_block(css: str, r: Report) -> None:
    """R-300..R-303 sul contenuto del <style>."""
    if not css.strip():
        return
    flat = css.strip()
    for pat in STYLE_FORBIDDEN_SELECTORS:
        if re.search(pat, flat):
            r.add("R-301", "MUST", f"Forbidden selector/rule in <style>: /{pat}/")
    outside_media = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", flat)
    for prop in STYLE_FORBIDDEN_PROPS:
        if re.search(rf"(^|[;{{\s]){re.escape(prop)}\s*:", flat):
            r.add("R-301", "MUST", f"Forbidden property in <style>: {prop}")
    medias = re.findall(r"@media[^{]*", flat)
    if len(medias) > 1:
        r.add("R-300", "MUST", f"{len(medias)} media queries (1 allowed)")
    for mq in medias:
        if re.search(r"only|screen|\band\b", mq):
            r.add("R-302", "MUST", f"Media query with only/screen/and: '{mq.strip()}' (use @media (max-width:620px))")
    media_lines = [ln for ln in flat.splitlines() if "@media" in ln]
    for ln in media_lines:
        if ln.count("{") != ln.count("}"):
            r.add("R-303", "MUST", "Media query not on a single line")
    radius_lines = [ln for ln in outside_media.splitlines() if "border-radius" in ln]
    if len(radius_lines) > 1:
        r.add("R-303", "MUST", f"border-radius on {len(radius_lines)} lines (1 allowed)")
    other = [ln for ln in outside_media.splitlines() if ln.strip() and "border-radius" not in ln and "x-apple-data-detectors" not in ln]
    if other:
        r.add("R-300", "MUST", f"Extra rules in <style>: {other[0][:80]}")


def lint_dom(p: EmailParser, r: Report, transactional: bool = False) -> None:
    """Controlli sul modello DOM raccolto."""
    if not p.html_attrs.get("lang"):
        r.add("R-504", "MUST", "<html> without lang")
    if not p.title_text.strip():
        r.add("R-504", "MUST", "<title> empty")
    for req in ("viewport", "x-ua-compatible", "x-apple-disable-message-reformatting", "format-detection", "color-scheme", "supported-color-schemes"):
        if req not in p.meta:
            r.add("R-002" if "color" not in req else "R-500", "MUST", f"Meta '{req}' missing")
    cs = p.meta.get("color-scheme", "").replace(" ", "")
    if cs in ("lightdark", "darklight"):
        r.add("R-500", "MUST", "color-scheme 'light dark' forbidden without a complete dark theme")
    for req in ("bgcolor", "text", "link"):
        if req not in p.body_attrs:
            r.add("R-207" if req != "bgcolor" else "R-200", "MUST", f"<body> without the {req} attribute")
    for req in ("marginwidth", "marginheight"):
        if req not in p.body_attrs:
            r.add("R-206", "MUST", f"<body> without {req}")
    if len(p.style_blocks) > 0 and html_style_count(p) > 1:
        r.add("R-300", "MUST", "More than one <style> block")
    if not p.heading_found:
        r.add("R-007", "SHOULD", "No <td role=\"heading\" aria-level=\"1\">")

    # text contrast (R-403/R-501)
    seen: set[tuple[str, str]] = set()
    for text, color, bg, line in p.text_chunks:
        if not color or not bg:
            continue
        key = (color, bg)
        ratio = contrast_ratio(color, bg)
        if ratio is None or key in seen:
            continue
        seen.add(key)
        if ratio < 4.5:
            r.add("R-501", "MUST", f"Contrasto {ratio:.2f}:1 ({color} su {bg}) < 4.5 - '{text[:30]}'", line)

    # link (R-450, R-452, R-453, R-457, R-454)
    unsubscribe = False
    for href, line in p.links:
        low = href.lower()
        if "unsubscribe" in low or "disiscri" in low or "[unsubscribe]" in low:
            unsubscribe = True
        if low.startswith(("tel:", "mailto:", "[", "#")):
            if low.startswith("tel:") and " " in href:
                r.add("R-457", "MUST", f"tel: with spaces: {href}", line)
            continue
        if not low.startswith("https://"):
            r.add("R-450", "MUST", f"Link is not an absolute HTTPS URL: {href[:70]}", line)
        if re.search(r"https?://\d+\.\d+\.\d+\.\d+", low):
            r.add("R-409", "MUST", f"Link with a bare IP: {href[:70]}", line)
        if "utm_" in low and re.search(r"utm_[a-z]+=[^&]*(\s|%20)", href):
            r.add("R-452", "MUST", f"UTM with spaces: {href[:70]}", line)
    if not unsubscribe:
        # Purely transactional emails (order confirmation, password reset) do not require unsubscribe:
        # it is reported as SHOULD when the user declares the type with --transactional.
        level = "SHOULD" if transactional else "MUST"
        r.add("R-454", level, "No unsubscribe link detected"
              + (" (transactional: check that it really is exempt)" if transactional else ""))


def html_style_count(p: EmailParser) -> int:
    return len(p.style_blocks)


def lint_subject(subject: str, r: Report) -> None:
    n = len(subject)
    if n > 60:
        r.add("R-406", "MUST", f"Subject {n} characters > 60")
    elif not 35 <= n <= 50:
        r.add("R-406", "SHOULD", f"Subject {n} characters (35-50 is optimal)")
    letters = [c for c in subject if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.5:
        r.add("R-406", "MUST", "Subject mostly in UPPERCASE")
    if re.search(r"[!?$]{2,}", subject):
        r.add("R-406", "MUST", "Repeated punctuation in the subject")
    if SPAM_WORDS.search(subject):
        r.add("R-406", "MUST", f"Trigger word in the subject: {SPAM_WORDS.search(subject).group(0)}")


def lint_plaintext(text: str, p: EmailParser, r: Report) -> None:
    if not text.strip():
        r.add("R-404", "MUST", "text/plain part is empty")
        return
    html_links = {h.split("?")[0] for h, _ in p.links if h.startswith("https://")}
    missing = [h for h in html_links if h not in text]
    if missing:
        r.add("R-404", "SHOULD", f"{len(missing)} HTML links missing from the text/plain (e.g. {missing[0]})")


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def run(path: Path, text_path: Path | None, subject: str | None, production: bool,
        transactional: bool = False) -> Report:
    raw = path.read_bytes()
    html = raw.decode("utf-8", errors="replace")
    report = Report(file=str(path), bytes=len(raw))

    lint_text_level(html, report, production)

    parser = EmailParser(report)
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # the HTML parser is permissive: an exception means severely malformed input
        report.add("R-010", "MUST", f"Parse failed: {exc}")
        return report

    lint_style_block("\n".join(parser.style_blocks), report)
    lint_dom(parser, report, transactional)

    if subject is not None:
        lint_subject(subject, report)
    if text_path is not None:
        lint_plaintext(text_path.read_text(encoding="utf-8"), parser, report)
    return report


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path)
    ap.add_argument("--text", type=Path, default=None, help="text/plain file")
    ap.add_argument("--subject", default=None)
    ap.add_argument("--production", action="store_true", help="placeholder = MUST")
    ap.add_argument("--transactional", action="store_true",
                    help="purely transactional email: unsubscribe (R-454) drops to SHOULD")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)

    if not args.html.is_file():
        print(f"File not found: {args.html}", file=sys.stderr)
        return 2

    try:
        report = run(args.html, args.text, args.subject, args.production, args.transactional)
    except Exception as exc:
        print(f"Execution error: {exc}", file=sys.stderr)
        return 2

    # dedup (same rule+message)
    uniq: dict[tuple[str, str, str], Finding] = {}
    for f in report.findings:
        uniq.setdefault((f.rule, f.level, f.message), f)
    report.findings = sorted(uniq.values(), key=lambda f: (f.level != "MUST", f.rule, f.line or 0))

    if args.json:
        print(json.dumps({"file": report.file, "bytes": report.bytes, "must": report.must_count,
                          "findings": [asdict(f) for f in report.findings]}, ensure_ascii=False, indent=2))
    else:
        print(f"{report.file} - {report.bytes} bytes")
        for f in report.findings:
            loc = f":{f.line}" if f.line else ""
            print(f"  [{f.level:6}] {f.rule}{loc}  {f.message}")
        should = len(report.findings) - report.must_count
        print(f"\nMUST violated: {report.must_count} | SHOULD: {should} | result: {'FAIL' if report.must_count else 'PASS'}")
    return 1 if report.must_count else 0


if __name__ == "__main__":
    sys.exit(main())
