#!/usr/bin/env python3
"""Linter tests: the reference template passes, the fixture with the historical anti-patterns fails."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "padosoft-email-html-builder"
LINT = SKILL / "scripts" / "lint_email.py"
GOOD = SKILL / "templates" / "reference-welcome-dark.html"
BAD = ROOT / "tests" / "fixtures" / "bad-email.html"


def lint(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(LINT), str(path), *extra],
                          capture_output=True, text=True, check=False)


class TestReferenceTemplate(unittest.TestCase):
    def test_template_passes(self) -> None:
        res = lint(GOOD)
        self.assertEqual(res.returncode, 0, res.stdout)
        self.assertIn("MUST violated: 0", res.stdout)

    def test_template_production_flags_placeholders(self) -> None:
        # In production the placeholders become blocking (R-901)
        res = lint(GOOD, "--production")
        self.assertEqual(res.returncode, 1)
        self.assertIn("R-901", res.stdout)


class TestAntiPatterns(unittest.TestCase):
    """Every rule here matches a mistake that actually came up in versions v1-v5."""

    EXPECTED = [
        "R-101",  # inline layout CSS
        "R-301",  # reset and prefers-color-scheme in <style>
        "R-302",  # @media only screen and
        "R-400",  # non-compliant preheader
        "R-401",  # invisible filler
        "R-402",  # non-ASCII character
        "R-500",  # color-scheme light dark
        "R-501",  # insufficient contrast
        "R-600",  # img without alt/height/border, non-https src
        "R-801",  # width 33.33%
        "R-409",  # url shortener
        "R-007",  # <h1>
        "R-206",  # body without marginwidth
    ]

    @classmethod
    def setUpClass(cls) -> None:
        cls.res = lint(BAD)

    def test_fails(self) -> None:
        self.assertEqual(self.res.returncode, 1)

    def test_expected_rules_detected(self) -> None:
        for rule in self.EXPECTED:
            with self.subTest(rule=rule):
                self.assertIn(rule, self.res.stdout)


class TestSubject(unittest.TestCase):
    def test_all_caps_subject_blocks(self) -> None:
        res = lint(GOOD, "--subject", "FREE OFFER!!! CLICK HERE RIGHT NOW ACT NOW")
        self.assertIn("R-406", res.stdout)
        self.assertEqual(res.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
