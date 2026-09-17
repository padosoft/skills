#!/usr/bin/env python3
"""
screenshot_email.py - Gate G2: screenshot di verifica di una email HTML.

Genera fino a 4 PNG: desktop 600px, mobile 375px, e le stesse viste senza il blocco <style>
(per verificare R-305: la mail deve restare leggibile anche quando il client lo rimuove).

Uso:
    python3 scripts/screenshot_email.py email.html [--out-dir shots] [--no-style] [--width-desktop 700]

Richiede Playwright con Chromium. Se non e' installato lo script esce con codice 3 e un messaggio
esplicito: in quel caso salta il gate G2 e dichiaralo nel report, non fingere di averlo eseguito.

Exit code: 0 ok | 2 errore di input | 3 Playwright non disponibile
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STYLE_BLOCK = re.compile(r"<style\b.*?</style>", re.S | re.I)


def strip_style(html: str) -> str:
    """Rimuove i blocchi <style> per simulare i client che li scartano (Gmail IMAP, Notes)."""
    return STYLE_BLOCK.sub("", html)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("shots"))
    ap.add_argument("--width-desktop", type=int, default=700)
    ap.add_argument("--width-mobile", type=int, default=375)
    ap.add_argument("--no-style", action="store_true", help="genera anche le varianti senza <style>")
    args = ap.parse_args()

    # Guard: input presente
    if not args.html.is_file():
        print(f"File non trovato: {args.html}", file=sys.stderr)
        return 2

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        print("Playwright non installato: salta il gate G2 e dichiaralo nel report "
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
            # executablePath non forzato: usa il Chromium gestito da Playwright
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
        print(f"Screenshot falliti: {exc}", file=sys.stderr)
        return 2

    for p in written:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
