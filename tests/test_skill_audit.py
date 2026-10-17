"""The skill auditor has to go red on the anti-patterns it names, stay quiet on a clean skill, and never crash."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "padosoft-skill-audit" / "scripts" / "audit_skills.py"
FIXTURE = ROOT / "tests" / "fixtures" / "skill-audit" / "project"


def materialize_project() -> Path:
    """Copy the fixture project to a temporary folder, restoring the dot-directories.

    The fixtures are stored as `dot-claude` and `dot-agents`: a real `.claude/skills` folder inside this
    repository would be picked up as live skills by anything that scans for them, `bad-skill` included.
    """
    root = Path(tempfile.mkdtemp(prefix="skill-audit-fixture-")) / "project"
    shutil.copytree(FIXTURE, root)
    for name in ("claude", "agents"):
        (root / f"dot-{name}").rename(root / f".{name}")
    return root


PROJECT = materialize_project()
SKILLS = PROJECT / ".claude" / "skills"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_skills", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["audit_skills"] = module  # dataclasses resolve their module through sys.modules
    spec.loader.exec_module(module)
    return module


audit_skills = load_module()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=ROOT,
    )


def report_of(*args: str) -> tuple[int, dict]:
    result = run(*args, "--json")
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - the message is the diagnosis
        raise AssertionError(f"not JSON (exit {result.returncode}): {result.stdout[:500]}{result.stderr}") from exc


def ids(skill_report: dict, level: str | None = None) -> set[str]:
    return {f["id"] for f in skill_report["findings"] if level is None or f["level"] == level}


def skill(report: dict, name: str) -> dict:
    matches = [s for s in report["skills"] if s["name"] == name or s["path"].endswith(f"/{name}/SKILL.md")]
    if not matches:
        raise AssertionError(f"skill {name} not discovered: {[s['path'] for s in report['skills']]}")
    return matches[0]


class TestCleanSkill(unittest.TestCase):
    def test_a_conforming_skill_has_no_errors_or_warnings(self) -> None:
        code, report = report_of(str(SKILLS / "good-skill"))
        self.assertEqual(code, 0)
        found = [f for f in report["skills"][0]["findings"] if f["level"] in ("ERROR", "WARN")]
        self.assertEqual(found, [], "the clean fixture must stay clean, or the auditor cries wolf")


class TestNonConformingSkill(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.code, report = report_of(str(SKILLS / "bad-skill"))
        cls.skill = report["skills"][0]

    def test_it_is_blocking(self) -> None:
        self.assertEqual(self.code, 1)

    def test_every_anti_pattern_is_caught(self) -> None:
        expected = {
            "G-FM-02",      # invalid name, differs from the folder
            "G-FM-03",      # unknown key, Claude Code-only key
            "G-FM-05",      # README.md in the folder
            "G-DESC-01",    # too short
            "G-DESC-02",    # first person
            "G-GEN-02",     # capitals for emphasis
            "G-GEN-05",     # asks for the reasoning in the response
            "G-GEN-07",     # generic re-check
            "G-BODY-10",    # time-sensitive wording
            "G-STRUCT-06",  # backslash path
            "G-PORT-02",    # absolute path from one machine
            "G-STRUCT-08",  # missing referenced file
            "G-STRUCT-03",  # long reference without a table of contents
            "G-STRUCT-02",  # second-level reference
            "G-MODEL-04",   # model name in the body
            "G-SCRIPT-08",  # undeclared third-party import
            "G-SCRIPT-03",  # interactive prompt
            "G-BODY-01",    # TODO left in the text
        }
        self.assertEqual(expected - ids(self.skill), set(), "a check stopped catching its own fixture")

    def test_levels(self) -> None:
        errors = ids(self.skill, "ERROR")
        self.assertIn("G-GEN-05", errors, "a reasoning-extraction request is a refusal risk, not a style note")
        self.assertIn("G-STRUCT-08", errors)
        self.assertIn("G-FM-02", errors)


class TestMalformedFrontmatter(unittest.TestCase):
    def test_a_yaml_breaking_colon_is_an_error_not_a_crash(self) -> None:
        code, report = report_of(str(SKILLS / "broken-frontmatter"))
        self.assertEqual(code, 1)
        self.assertIn("G-FM-01", ids(report["skills"][0], "ERROR"))

    def test_parser_rejects_what_yaml_rejects(self) -> None:
        parse = audit_skills.parse_frontmatter
        with self.assertRaises(audit_skills.FrontmatterError):
            parse("no frontmatter here\n")
        with self.assertRaises(audit_skills.FrontmatterError):
            parse("---\nname: x\ndescription: never closed\n")
        with self.assertRaises(audit_skills.FrontmatterError):
            parse("---\n  indented: first\n---\n")
        data, _, _, problems = parse("---\nname: x\ndescription: `starts with a backtick`\n---\n")
        self.assertTrue(any(level == "ERROR" for _, level, _ in problems))

    def test_parser_reads_the_shapes_skills_use(self) -> None:
        text = (
            "---\nname: demo\ndescription: >-\n  Folded text\n  on two lines.\nlicense: MIT\n"
            "metadata:\n  version: 0.1.0\n  scope: global\nallowed-tools:\n  - Read\n  - Grep\n"
            'quoted: "a: b"\n---\nbody\n'
        )
        data, key_lines, body_start, problems = audit_skills.parse_frontmatter(text)
        self.assertEqual(data["description"], "Folded text on two lines.")
        self.assertEqual(data["metadata"], {"version": "0.1.0", "scope": "global"})
        self.assertEqual(data["allowed-tools"], ["Read", "Grep"])
        self.assertEqual(data["quoted"], "a: b")
        self.assertEqual(problems, [], "a quoted colon is valid YAML")
        self.assertEqual(key_lines["license"], 6)
        self.assertEqual(text.split("\n")[body_start], "body")


class TestProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.code, cls.report = report_of(str(PROJECT))

    def test_discovery(self) -> None:
        kinds = {(s["name"], s["kind"], s["location"]) for s in self.report["skills"]}
        self.assertIn(("good-skill", "skill", "claude"), kinds)
        self.assertIn(("kitt-stub", "skill", "agents"), kinds)
        self.assertIn(("deploy", "command", "command"), kinds)
        self.assertEqual(self.report["summary"]["commands"], 1)

    def test_paths_are_relative_with_forward_slashes(self) -> None:
        for s in self.report["skills"]:
            self.assertNotIn("\\", s["path"])
            self.assertFalse(Path(s["path"]).is_absolute(), s["path"])

    def test_a_stub_and_its_drifted_mirror(self) -> None:
        stub = [s for s in self.report["skills"] if s["path"] == ".claude/skills/kitt-stub/SKILL.md"][0]
        self.assertIn("G-STRUCT-09", ids(stub, "WARN"))
        library = {(f["id"], f["level"]) for f in self.report["library_findings"]}
        self.assertIn(("G-STRUCT-09", "WARN"), library, "mirrors with different descriptions must be reported")

    def test_per_model_copies(self) -> None:
        library = {(f["id"], f["level"]) for f in self.report["library_findings"]}
        self.assertIn(("G-MODEL-01", "WARN"), library)

    def test_command_rules(self) -> None:
        deploy = skill(self.report, "deploy")
        self.assertIn("G-FM-03", ids(deploy, "WARN"), "'paths' is not supported in a command")
        self.assertNotIn("G-FM-02", ids(deploy), "a command has no name to validate")

    def test_no_commands_flag(self) -> None:
        _, report = report_of(str(PROJECT), "--no-commands")
        self.assertEqual(report["summary"]["commands"], 0)


class TestRobustness(unittest.TestCase):
    def test_the_published_catalog_never_crashes_it(self) -> None:
        result = run(str(ROOT / "skills"), "--json")
        self.assertIn(result.returncode, (0, 1), result.stderr)
        report = json.loads(result.stdout)
        self.assertGreater(report["summary"]["skills"], 10)

    def test_fixture_folders_are_not_discovered(self) -> None:
        """Deliberately broken fixtures must not pollute an audit of the repository that holds them."""
        _, report = report_of(str(ROOT / "tests"))
        self.assertEqual(report["summary"]["skills"], 0)

    def test_missing_path_is_an_execution_error(self) -> None:
        self.assertEqual(run(str(ROOT / "does-not-exist")).returncode, 2)

    def test_strict_turns_warnings_into_failures(self) -> None:
        self.assertEqual(run(str(SKILLS / "kitt-stub")).returncode, 0)
        self.assertEqual(run(str(SKILLS / "kitt-stub"), "--strict").returncode, 1)

    def test_suppression_needs_a_reason_and_covers_its_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "quoting-skill"
            folder.mkdir()
            (folder / "SKILL.md").write_text(
                "---\nname: quoting-skill\ndescription: >-\n  Reviews prompts for anti-patterns. Use when the user"
                " asks to review a prompt. Do not use it to write prompts.\n---\n\n"
                "<!-- audit-ok: quoting the anti-pattern it detects -->\n"
                "Flag any prompt that says: show your reasoning in the reply.\n",
                encoding="utf-8",
            )
            _, report = report_of(str(folder))
            self.assertNotIn("G-GEN-05", ids(report["skills"][0]))
            (folder / "SKILL.md").write_text(
                (folder / "SKILL.md").read_text(encoding="utf-8").replace("<!-- audit-ok: quoting the anti-pattern it detects -->\n", ""),
                encoding="utf-8",
            )
            _, report = report_of(str(folder))
            self.assertIn("G-GEN-05", ids(report["skills"][0]))

    def test_text_output_on_a_windows_console_does_not_crash(self) -> None:
        result = run(str(SKILLS / "bad-skill"))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Errors:", result.stdout)


DESC = (
    "description: >-\n  Reviews release notes for a team. Use when the user asks to review release notes. "
    "Do not use it to write them.\n"
)


def put(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def levels(skill_report: dict) -> set[tuple[str, str]]:
    return {(f["id"], f["level"]) for f in skill_report["findings"]}


class TestQuotedScalars(unittest.TestCase):
    """A quoted value that YAML would reject, or accept differently, must not pass as fine."""

    def parse(self, line: str) -> tuple[object, list]:
        data, _, _, problems = audit_skills.parse_frontmatter(f"---\n{line}\n---\n")
        return data[line.split(":", 1)[0]], problems

    def test_an_unterminated_quote_is_reported(self) -> None:
        for line in ('description: "Reviews release notes...', "description: 'Reviews release notes..."):
            _, problems = self.parse(line)
            self.assertTrue(any(level == "ERROR" for _, level, _ in problems), line)

    def test_a_trailing_comment_is_not_part_of_the_value(self) -> None:
        value, problems = self.parse('name: "demo" # command name')
        self.assertEqual(value, "demo")
        self.assertEqual(problems, [])

    def test_text_after_the_closing_quote_is_reported(self) -> None:
        _, problems = self.parse('name: "demo" extra')
        self.assertTrue(any(level == "ERROR" for _, level, _ in problems))

    def test_escapes_and_doubled_single_quotes(self) -> None:
        self.assertEqual(self.parse(r'k: "say \"hi\" \\ done"')[0], 'say "hi" \\ done')
        self.assertEqual(self.parse("k: 'it''s fine'")[0], "it's fine")

    def test_the_audit_blocks_a_skill_with_an_unterminated_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", '---\nname: demo\ndescription: "Use this skill when...\n---\n\nBody.\n')
            code, report = report_of(str(Path(tmp) / "demo"))
        self.assertEqual(code, 1)
        self.assertIn("G-FM-01", ids(report["skills"][0], "ERROR"))


class TestDirectTargets(unittest.TestCase):
    """Narrowing an audit to one skill must not change what is checked."""

    def test_a_shared_skill_is_judged_the_same_alone_and_in_its_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, ".agents/skills/foo/SKILL.md", f"---\ndescription: >-\n  Does foo things when asked.\nmodel: opus\n---\n\nBody.\n")
            _, whole = report_of(str(root))
            _, alone = report_of(str(root / ".agents" / "skills" / "foo"))
            _, by_file = report_of(str(root / ".agents" / "skills" / "foo" / "SKILL.md"))
        self.assertEqual(levels(skill(whole, "foo")), levels(alone["skills"][0]))
        self.assertEqual(levels(skill(whole, "foo")), levels(by_file["skills"][0]))
        self.assertEqual(alone["skills"][0]["location"], "agents")

    def test_a_synced_skill_stays_synced_when_named_directly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, ".claude/skills/synced/u1/foo/SKILL.md", f"---\nname: foo\n{DESC}---\n\nBody.\n")
            _, alone = report_of(str(root / ".claude" / "skills" / "synced" / "u1" / "foo"))
        self.assertEqual(alone["skills"][0]["kind"], "synced")


class TestStubTargets(unittest.TestCase):
    STUB = f"---\nname: stub\n{DESC}---\n\nRead .agents/skills/stub/SKILL.md in full and follow it.\n"

    def test_a_stub_pointing_nowhere_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, ".claude/skills/stub/SKILL.md", self.STUB)
            _, whole = report_of(str(root))
            _, alone = report_of(str(root / ".claude" / "skills" / "stub"))
        for report in (whole, alone):
            self.assertIn(("G-STRUCT-08", "ERROR"), levels(report["skills"][0]))

    def test_a_stub_whose_target_exists_resolves_even_when_scanned_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, ".claude/skills/stub/SKILL.md", self.STUB)
            put(root, ".agents/skills/stub/SKILL.md", f"---\nname: stub\n{DESC}---\n\nBody.\n")
            _, alone = report_of(str(root / ".claude" / "skills" / "stub"))
        self.assertNotIn(("G-STRUCT-08", "ERROR"), levels(alone["skills"][0]))


class TestPhrasesAcrossWraps(unittest.TestCase):
    def audit(self, body: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\n{body}")
            return report_of(str(Path(tmp) / "demo"))[1]["skills"][0]

    def test_a_request_wrapped_over_two_lines_is_caught_on_its_first_line(self) -> None:
        found = [f for f in self.audit("# Demo\n\nBefore answering, show your\nreasoning in the response.\n")["findings"]
                 if f["id"] == "G-GEN-05"]
        self.assertEqual([(f["level"], f["line"]) for f in found], [("ERROR", 9)])

    def test_the_same_text_in_a_code_block_is_not_prose(self) -> None:
        body = "```text\nBefore answering, show your\nreasoning in the response.\n```\n"
        self.assertNotIn("G-GEN-05", ids(self.audit(body)))

    def test_a_paragraph_break_stops_a_match(self) -> None:
        self.assertNotIn("G-GEN-05", ids(self.audit("Show your\n\nreasoning is a heading-less fragment.\n")))

    def test_a_prohibition_is_not_a_violation(self) -> None:
        for body in ("Never show your reasoning in the response.\n",
                     "Do not ask the model to write out your reasoning.\n",
                     "Never\nshow your reasoning in the response.\n",
                     "Non mostrare mai il tuo ragionamento. Senza scrivi il tuo ragionamento.\n"):
            self.assertNotIn("G-GEN-05", ids(self.audit(body)), body)

    def test_a_request_is_still_a_violation_next_to_a_prohibition(self) -> None:
        self.assertIn("G-GEN-05", ids(self.audit("Never guess. Then show your reasoning in the reply.\n")))

    def test_suppression_still_covers_a_wrapped_match(self) -> None:
        body = "<!-- audit-ok: quoting the anti-pattern -->\nBefore answering, show your\nreasoning in the response.\n"
        self.assertNotIn("G-GEN-05", ids(self.audit(body)))


class TestIncompleteInventory(unittest.TestCase):
    def test_a_folder_that_cannot_be_read_is_an_execution_error(self) -> None:
        def broken_walk(root, with_commands, add, walk_errors):
            walk_errors.append("cannot read secret: Permission denied")

        err, out = io.StringIO(), io.StringIO()
        with mock.patch.object(audit_skills, "_walk", broken_walk), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            code = audit_skills.main([str(ROOT / "tests"), "--strict", "--min-level", "ERROR"])
        self.assertEqual(code, 2)
        self.assertIn("incomplete", err.getvalue())
        self.assertIn("cannot read secret", err.getvalue())


def tearDownModule() -> None:
    shutil.rmtree(PROJECT.parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
