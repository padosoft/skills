#!/usr/bin/env python3
"""
screenshot_email.py - Gate G2: verification screenshots of an HTML email.

Generates up to 4 PNGs: desktop 600px, mobile 375px, and the same views without the <style> block
(to verify R-305: the email must stay readable even when the client strips it).

Usage:
    python3 scripts/screenshot_email.py email.html [--out-dir shots] [--no-style] [--width-desktop 700]

Requires Playwright with Chromium. If it is not installed the script exits with code 3 and an explicit
message: in that case skip gate G2 and declare it in the report, do not pretend you ran it.

Exit code: 0 ok | 2 input error | 3 Playwright not available
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STYLE_BLOCK = re.compile(r"<style\b.*?</style>", re.S | re.I)


def strip_style(html: str) -> str:
    """Removes the <style> blocks to simulate the clients that drop them (Gmail IMAP, Notes)."""
    return STYLE_BLOCK.sub("", html)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("shots"))
    ap.add_argument("--width-desktop", type=int, default=700)
    ap.add_argument("--width-mobile", type=int, default=375)
    ap.add_argument("--no-style", action="store_true", help="also generate the variants without <style>")
    args = ap.parse_args()

    # Guard: input present
    if not args.html.is_file():
        print(f"File not found: {args.html}", file=sys.stderr)
        return 2

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        print("Playwright not installed: skip gate G2 and declare it in the report "
              "(`pip install playwright && playwright install chromium`).", file=sys.stderr)
        return 3

    html: str = args.html.read_text(encoding="utf-8")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    variants: list[tuple[str, str]] = [("base", html)]
    if args.no_style:
        variants.append(("nostyle", strip_style(html)))

    written: list[Path] = []
    try:
        with sync_playwright() as pw:
            # executablePath not forced: it uses the Chromium managed by Playwright
            browser = pw.chromium.launch()
            try:
                for label, markup in variants:
                    tmp = args.out_dir / f"_{label}.html"
                    tmp.write_text(markup, encoding="utf-8")
                    for name, width in (("desktop", args.width_desktop), ("mobile", args.width_mobile)):
                        page = browser.new_page(viewport={"width": width, "height": 900})
                        page.goto(tmp.resolve().as_uri())
                        page.wait_for_timeout(400)
                        out = args.out_dir / f"{args.html.stem}-{name}-{label}.png"
                        page.screenshot(path=str(out), full_page=True)
                        page.close()
                        written.append(out)
                    tmp.unlink(missing_ok=True)
            finally:
                browser.close()
    except Exception as exc:
        print(f"Screenshots failed: {exc}", file=sys.stderr)
        return 2

    for p in written:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
