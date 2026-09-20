"""The provenance gate has to be able to go red, and the published skills have to be clean."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "skills" / "padosoft-skill-creator" / "scripts" / "check_provenance.py"
FIXTURE = ROOT / "tests" / "fixtures" / "provenance-leak.md"

EXPECTED_RULES = {
    "date",
    "email",
    "credential",
    "private-host",
    "ip-address",
    "personal-id",
    "identifier",
    "local-path",
    "narration",
    "incident-topic",
}


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCANNER), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=ROOT,
    )


class TestProvenanceGate(unittest.TestCase):
    def test_the_fixture_fails_for_every_rule(self) -> None:
        """A gate that has only ever been green has not been tested."""
        result = run(str(FIXTURE), "--json")
        self.assertEqual(result.returncode, 1, f"the fixture must be rejected\n{result.stdout}{result.stderr}")
        report = json.loads(result.stdout)
        found = {f["rule_id"] for f in report["findings"]}
        self.assertEqual(EXPECTED_RULES, found & EXPECTED_RULES, "a rule stopped catching its own fixture line")

    def test_suppression_needs_a_reason_and_covers_one_line(self) -> None:
        result = run(str(FIXTURE), "--json")
        report = json.loads(result.stdout)
        self.assertGreaterEqual(report["suppressed"], 1, "the marked line should be suppressed")
        excerpts = " ".join(f["excerpt"] for f in report["findings"])
        self.assertNotIn("10.0.14.23", excerpts, "the suppressed line must not be reported")
        self.assertIn("10.0.14.22", excerpts, "suppression must not leak onto other lines")

    def test_topic_ok_drops_only_the_vocabulary_rule(self) -> None:
        result = run(str(FIXTURE), "--topic-ok", "--json")
        found = {f["rule_id"] for f in json.loads(result.stdout)["findings"]}
        self.assertNotIn("incident-topic", found)
        self.assertIn("date", found, "--topic-ok must not disable anything else")

    def test_published_skills_carry_no_provenance(self) -> None:
        result = run(str(ROOT / "skills"))
        self.assertEqual(result.returncode, 0, f"a skill carries provenance:\n{result.stdout}")

    def test_a_missing_path_is_a_usage_error_not_a_pass(self) -> None:
        result = run(str(ROOT / "does-not-exist"))
        self.assertEqual(result.returncode, 2, "an unscannable target must not look clean")


if __name__ == "__main__":
    unittest.main()
