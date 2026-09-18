#!/usr/bin/env python3
"""
build_payload.py - Builds the JSON for the Mailtrap Sending/Sandbox API from HTML + text + metadata.

Usage:
  python3 build_payload.py --html email.html --text email.txt --subject "Subject" \
      --from-email noreply@brand.it --from-name "Brand" --to test@brand.it \
      --unsubscribe-url https://brand.it/unsubscribe [--unsubscribe-mailto unsubscribe@brand.it] \
      [--category welcome] [--out payload.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, required=True)
    ap.add_argument("--text", type=Path, required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--from-email", required=True)
    ap.add_argument("--from-name", required=True)
    ap.add_argument("--to", required=True)
    ap.add_argument("--unsubscribe-url", required=True)
    ap.add_argument("--unsubscribe-mailto", default=None)
    ap.add_argument("--category", default="test")
    ap.add_argument("--out", type=Path, default=Path("payload.json"))
    a = ap.parse_args()

    # Guard: files present
    for p in (a.html, a.text):
        if not p.is_file():
            print(f"File not found: {p}", file=sys.stderr)
            return 2

    html: str = a.html.read_text(encoding="utf-8")
    text: str = a.text.read_text(encoding="utf-8")

    # Guard: R-404 text/plain not empty
    if not text.strip():
        print("text/plain empty (R-404)", file=sys.stderr)
        return 1

    # R-405: List-Unsubscribe one-click (RFC 8058)
    lu: str = f"<{a.unsubscribe_url}>"
    if a.unsubscribe_mailto:
        lu += f", <mailto:{a.unsubscribe_mailto}>"

    payload: dict = {
        "from": {"email": a.from_email, "name": a.from_name},
        "to": [{"email": a.to}],
        "subject": a.subject,
        "category": a.category,
        "text": text,
        "html": html,
        "headers": {"List-Unsubscribe": lu, "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
    }
    # ensure_ascii=True: the JSON stays ASCII, accented characters in text/plain travel as \uXXXX
    a.out.write_text(json.dumps(payload, ensure_ascii=True, indent=1), encoding="utf-8")
    print(f"Payload written: {a.out} ({a.out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
