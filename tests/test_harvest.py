"""The harvester has to see a change, forget nothing, and refuse a decision with no reason."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARVEST = ROOT / "scripts" / "harvest.py"


class HarvestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.source = base / "repo"
        (self.source / ".claude" / "rules").mkdir(parents=True)
        (self.source / "docs").mkdir(parents=True)
        (self.source / "docs" / "LESSON.md").write_text("# Lessons\n\nfirst\n", encoding="utf-8")
        (self.source / ".claude" / "rules" / "rule-a.md").write_text("# Rule A\n", encoding="utf-8")

        self.sources = base / "sources.json"
        self.sources.write_text(json.dumps({"sources": [
            {"id": "repo", "path": str(self.source)},
            {"id": "absent", "path": str(base / "nowhere")},
        ]}), encoding="utf-8")
        self.ledger = base / "ledger.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_harvest(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HARVEST), "--sources", str(self.sources),
             "--ledger", str(self.ledger), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)

    def scan(self, *args: str) -> dict:
        result = self.run_harvest("scan", "--json", *args)
        return json.loads(result.stdout)

    def test_a_first_scan_reports_everything_as_new(self) -> None:
        report = self.scan()
        states = {f["path"]: f["state"] for f in report["findings"]}
        self.assertEqual(states.get("docs/LESSON.md"), "new")
        self.assertEqual(states.get(".claude/rules/rule-a.md"), "new")

    def test_an_unreachable_source_is_a_problem_not_a_silent_skip(self) -> None:
        report = self.scan()
        self.assertTrue(any("absent" in p for p in report["problems"]),
                        "a source that cannot be read must be reported")

    def test_scan_never_writes_the_ledger(self) -> None:
        self.run_harvest("scan")
        self.assertFalse(self.ledger.exists(),
                         "a scan that dies half way must not mark anything as processed")

    def test_a_recorded_file_stops_being_reported_until_it_changes(self) -> None:
        self.run_harvest("record", "repo|docs/LESSON.md", "covered", "--skill", "padosoft-x")
        self.assertNotIn("docs/LESSON.md", [f["path"] for f in self.scan()["findings"]])

        (self.source / "docs" / "LESSON.md").write_text("# Lessons\n\nfirst\nsecond\n", encoding="utf-8")
        changed = [f for f in self.scan()["findings"] if f["path"] == "docs/LESSON.md"]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]["state"], "changed")
        self.assertEqual(changed[0]["outcome"], "covered", "the last decision must travel with the finding")

    def test_a_deleted_source_file_is_reported_as_gone(self) -> None:
        self.run_harvest("record", "repo|.claude/rules/rule-a.md", "covered", "--skill", "padosoft-x")
        (self.source / ".claude" / "rules" / "rule-a.md").unlink()
        gone = [f for f in self.scan()["findings"] if f["state"] == "gone"]
        self.assertEqual([f["path"] for f in gone], [".claude/rules/rule-a.md"])

    def test_a_decision_without_its_justification_is_refused(self) -> None:
        no_reason = self.run_harvest("record", "repo|docs/LESSON.md", "rejected")
        self.assertEqual(no_reason.returncode, 2, "'rejected' must require a reason")
        no_skill = self.run_harvest("record", "repo|docs/LESSON.md", "covered")
        self.assertEqual(no_skill.returncode, 2, "'covered' must require a skill")
        self.assertFalse(self.ledger.exists(), "a refused decision writes nothing")

    def test_status_counts_the_sources_feeding_each_skill(self) -> None:
        self.run_harvest("record", "repo|docs/LESSON.md", "covered", "--skill", "padosoft-x")
        self.run_harvest("record", "repo|.claude/rules/rule-a.md", "covered", "--skill", "padosoft-x")
        out = self.run_harvest("status").stdout
        self.assertIn("padosoft-x", out)
        self.assertIn("2", out.split("padosoft-x")[0].splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
