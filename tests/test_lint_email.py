#!/usr/bin/env python3
"""Test del linter: il template di riferimento passa, la fixture con gli anti-pattern storici fallisce."""
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
        self.assertIn("MUST violati: 0", res.stdout)

    def test_template_production_flags_placeholders(self) -> None:
        # In produzione i segnaposto diventano bloccanti (R-901)
        res = lint(GOOD, "--production")
        self.assertEqual(res.returncode, 1)
        self.assertIn("R-901", res.stdout)


class TestAntiPatterns(unittest.TestCase):
    """Ogni regola qui corrisponde a un errore realmente emerso nelle versioni v1-v5."""

    EXPECTED = [
        "R-101",  # CSS inline di layout
        "R-301",  # reset e prefers-color-scheme nel <style>
        "R-302",  # @media only screen and
        "R-400",  # preheader non conforme
        "R-401",  # filler invisibile
        "R-402",  # carattere non ASCII
        "R-500",  # color-scheme light dark
        "R-501",  # contrasto insufficiente
        "R-600",  # img senza alt/height/border, src non https
        "R-801",  # larghezza 33.33%
        "R-409",  # url shortener
        "R-007",  # <h1>
        "R-206",  # body senza marginwidth
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
        res = lint(GOOD, "--subject", "OFFERTA GRATIS!!! CLICCA QUI SUBITO ORA")
        self.assertIn("R-406", res.stdout)
        self.assertEqual(res.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
