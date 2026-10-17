#!/usr/bin/env python3
"""collect.py - List merged pull requests since a tag, as JSON. Fixture for the audit tests.

Usage: python3 scripts/collect.py --since TAG
Exit code: 0 ok | 2 execution error
"""
from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", required=True)
    args = parser.parse_args()
    print(json.dumps({"since": args.since, "pull_requests": []}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
