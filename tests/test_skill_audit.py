"""The skill auditor has to go red on the anti-patterns it names, stay quiet on a clean skill, and never crash."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
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


def link_directory(link: Path, target: Path) -> bool:
    """A symlink, or on Windows without the privilege a junction (which needs none). False when neither works."""
    try:
        link.symlink_to(target, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass
    if sys.platform != "win32":
        return False
    done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
    return done.returncode == 0


class TestYamlEdgeCases(unittest.TestCase):
    def parse(self, text: str):
        return audit_skills.parse_frontmatter(f"---\n{text}\n---\n")

    def test_a_comment_is_not_judged_as_part_of_the_value(self) -> None:
        for line, expected in (("name: demo # note: command name", "demo"),
                               ("description: Reviews notes # Note: internal use", "Reviews notes")):
            data, _, _, problems = self.parse(line)
            self.assertEqual(data[line.split(":", 1)[0]], expected)
            self.assertFalse(any(level == "ERROR" for _, level, _ in problems), problems)

    def test_a_colon_in_the_value_before_any_comment_is_still_an_error(self) -> None:
        _, _, _, problems = self.parse("description: Reviews notes: carefully")
        self.assertTrue(any(level == "ERROR" for _, level, _ in problems))

    def test_a_key_needs_a_space_after_its_colon(self) -> None:
        with self.assertRaises(audit_skills.FrontmatterError):
            self.parse("name:demo")
        data, *_ = self.parse("name:\n")  # an empty value is fine
        self.assertEqual(data["name"], "")

    def test_a_comment_only_value_is_empty(self) -> None:
        data, *_ = self.parse("metadata: # versioning\n  version: 1")
        self.assertEqual(data["metadata"], {"version": "1"})


class TestTypes(unittest.TestCase):
    def audit(self, frontmatter: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\n{frontmatter}\n---\n\nBody.\n")
            return report_of(str(Path(tmp) / "demo"))

    def test_a_list_or_mapping_description_is_an_error(self) -> None:
        for frontmatter in ("name: demo\ndescription:\n  - Reviews release notes when asked",
                            "name: demo\ndescription:\n  text: Reviews release notes"):
            code, report = self.audit(frontmatter)
            self.assertEqual(code, 1, frontmatter)
            self.assertIn("G-DESC-01", ids(report["skills"][0], "ERROR"), frontmatter)

    def test_a_list_name_is_an_error(self) -> None:
        code, report = self.audit(f"name:\n  - demo\n{DESC}")
        self.assertEqual(code, 1)
        self.assertIn("G-FM-02", ids(report["skills"][0], "ERROR"))


class TestAliasesAndSyncedRoots(unittest.TestCase):
    def test_a_symlinked_skill_is_judged_the_same_whatever_order_the_roots_come_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, ".agents/skills/demo/SKILL.md", f"---\ndescription: >-\n  Does demo things when asked.\nmodel: opus\n---\n\nBody.\n")
            (root / ".claude" / "skills").mkdir(parents=True)
            if not link_directory(root / ".claude" / "skills" / "demo", root / ".agents" / "skills" / "demo"):
                self.skipTest("neither symlinks nor junctions are available here")
            first = report_of(str(root / ".claude"), str(root / ".agents"))[1]
            second = report_of(str(root / ".agents"), str(root / ".claude"))[1]
        self.assertEqual(len(first["skills"]), 1)
        self.assertEqual(levels(first["skills"][0]), levels(second["skills"][0]))
        self.assertIn(("G-FM-02", "ERROR"), levels(first["skills"][0]), "shared exposure must make a missing name blocking")

    def test_synced_skills_are_found_from_a_narrowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, ".claude/skills/synced/u1/foo/SKILL.md", f"---\nname: foo\n{DESC}---\n\nBody.\n")
            for narrowed in (root / ".claude" / "skills" / "synced", root / ".claude" / "skills" / "synced" / "u1",
                             root / ".claude" / "skills"):
                _, report = report_of(str(narrowed))
                self.assertEqual([(s["name"], s["kind"]) for s in report["skills"]], [("foo", "synced")], str(narrowed))


class TestCommandPaths(unittest.TestCase):
    def audit(self, body: str, with_script: bool = False) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\n{body}")
            if with_script:
                put(Path(tmp), "demo/scripts/run.py", "print('ok')\n")
            return report_of(str(Path(tmp) / "demo"))[1]["skills"][0]

    def missing(self, skill_report: dict) -> list[str]:
        return [f["message"] for f in skill_report["findings"] if f["id"] == "G-STRUCT-08" and f["level"] == "ERROR"]

    def test_a_dead_script_is_caught_whatever_surrounds_it(self) -> None:
        for body in ("Run `scripts/run.py --since TAG` first.\n",
                     "Run `python3 scripts/run.py` first.\n",
                     "Run `python3 \"${CLAUDE_SKILL_DIR}/scripts/run.py\" --json` first.\n",
                     "```bash\npython3 scripts/run.py --json\n```\n",
                     "```sh\n  bash ./scripts/run.sh\n```\n"):
            self.assertTrue(self.missing(self.audit(body)), body)

    def test_an_existing_script_is_not_flagged_and_not_an_orphan(self) -> None:
        for body in ("Run `scripts/run.py --since TAG` first.\n", "```bash\npython3 scripts/run.py\n```\n"):
            report = self.audit(body, with_script=True)
            self.assertEqual(self.missing(report), [], body)
            self.assertFalse([f for f in report["findings"] if "never mentioned" in f["message"]], body)

    def test_output_blocks_and_comments_are_not_commands(self) -> None:
        self.assertEqual(self.missing(self.audit("```text\nscripts/run.py failed\n```\n")), [])
        self.assertEqual(self.missing(self.audit("```bash\n# scripts/run.py is optional\n```\n")), [])


class TestUrlsAreNotStubs(unittest.TestCase):
    def test_a_link_to_an_online_skill_is_not_a_missing_local_stub(self) -> None:
        body = ("Read [the upstream skill](https://raw.githubusercontent.com/o/r/main/skills/x/SKILL.md) "
                "before you start.\n")
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\n{body}")
            found = report_of(str(Path(tmp) / "demo"))[1]["skills"][0]
        self.assertFalse([f for f in found["findings"] if f["id"] in ("G-STRUCT-08", "G-STRUCT-09")], found["findings"])

    def test_a_local_stub_next_to_a_url_is_still_checked(self) -> None:
        body = "Read https://example.com/SKILL.md, then read .agents/skills/demo/SKILL.md in full.\n"
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), ".claude/skills/demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\n{body}")
            found = report_of(str(Path(tmp) / ".claude" / "skills" / "demo"))[1]["skills"][0]
        self.assertIn(("G-STRUCT-08", "ERROR"), levels(found))


class TestFlowCollections(unittest.TestCase):
    def parse(self, text: str):
        return audit_skills.parse_frontmatter(f"---\n{text}\n---\n")

    def test_flow_collections_keep_their_type(self) -> None:
        data, _, _, problems = self.parse("allowed-tools: [Read, Grep]\nmetadata: {version: 1, scope: global}")
        self.assertEqual(data["allowed-tools"], ["Read", "Grep"])
        self.assertEqual(data["metadata"], {"version": "1", "scope": "global"})
        self.assertEqual(problems, [])

    def test_commas_inside_quotes_or_nesting_do_not_split(self) -> None:
        data, *_ = self.parse('tools: ["a, b", c, [d, e]]')
        self.assertEqual(data["tools"], ["a, b", "c", "[d, e]"])

    def test_an_unclosed_collection_is_an_error(self) -> None:
        _, _, _, problems = self.parse("description: [Reviews release notes")
        self.assertTrue(any(level == "ERROR" for _, level, _ in problems))

    def test_a_flow_list_description_is_not_a_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md",
                "---\nname: demo\ndescription: [Reviews release notes when requested. Do not use for commits.]\n---\n\nBody.\n")
            code, report = report_of(str(Path(tmp) / "demo"))
        self.assertEqual(code, 1)
        self.assertIn("G-DESC-01", ids(report["skills"][0], "ERROR"))


class TestProjectScriptsAreNotBundledOnes(unittest.TestCase):
    BODY = "Run `python3 scripts/run.py --json` first.\n"

    def audit(self, project_script: bool, bundled_script: bool) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            put(root, "skills/demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\n{self.BODY}")
            if project_script:
                put(root, "scripts/run.py", "print('project')\n")
            if bundled_script:
                put(root, "skills/demo/scripts/run.py", "print('bundled')\n")
            return report_of(str(root / "skills" / "demo"))[1]["skills"][0]

    def test_a_project_file_with_the_same_name_does_not_hide_a_missing_bundled_one(self) -> None:
        found = self.audit(project_script=True, bundled_script=False)
        self.assertNotIn(("G-STRUCT-08", "ERROR"), levels(found))
        self.assertIn(("G-STRUCT-08", "INFO"), levels(found), "it must say the file is the project's, not the skill's")

    def test_nothing_anywhere_is_an_error(self) -> None:
        self.assertIn(("G-STRUCT-08", "ERROR"), levels(self.audit(project_script=False, bundled_script=False)))

    def test_a_bundled_script_is_found_quietly(self) -> None:
        found = self.audit(project_script=True, bundled_script=True)
        self.assertEqual([f for f in found["findings"] if f["id"] == "G-STRUCT-08"], [])


class TestIncompleteBundles(unittest.TestCase):
    def test_a_bundled_folder_that_cannot_be_listed_is_an_execution_error(self) -> None:
        real_walk = os.walk

        def denying_walk(top, onerror=None, **kwargs):
            if Path(top).name == "demo" and onerror is not None:
                onerror(PermissionError(13, "Permission denied", str(Path(top) / "references")))
            return real_walk(top, onerror=onerror, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nBody.\n")
            err, out = io.StringIO(), io.StringIO()
            with mock.patch.object(audit_skills.os, "walk", denying_walk), \
                    contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                code = audit_skills.main([str(Path(tmp) / "demo")])
        self.assertEqual(code, 2)
        self.assertIn("incomplete", err.getvalue())
        self.assertIn("references", err.getvalue())


class TestLinkedContainers(unittest.TestCase):
    def test_a_skills_folder_that_is_a_link_is_found_by_a_project_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, "shared/skills/demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nBody.\n")
            (root / "project" / ".claude").mkdir(parents=True)
            if not link_directory(root / "project" / ".claude" / "skills", root / "shared" / "skills"):
                self.skipTest("neither symlinks nor junctions are available here")
            whole = report_of(str(root / "project"))[1]
            narrowed = report_of(str(root / "project" / ".claude" / "skills"))[1]
        self.assertEqual([s["name"] for s in whole["skills"]], ["demo"])
        self.assertEqual([s["name"] for s in narrowed["skills"]], ["demo"])

    def test_a_link_cycle_ends(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, ".claude/skills/demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nBody.\n")
            if not link_directory(root / ".claude" / "skills" / "loop", root / ".claude" / "skills"):
                self.skipTest("neither symlinks nor junctions are available here")
            code, report = report_of(str(root))
        self.assertIn(code, (0, 1))
        self.assertEqual([s["name"] for s in report["skills"]], ["demo"])


class TestNonTextScalars(unittest.TestCase):
    def audit(self, frontmatter: str) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\n{frontmatter}\n---\n\nBody.\n")
            return report_of(str(Path(tmp) / "demo"))

    def test_null_boolean_and_number_are_not_text(self) -> None:
        for value in ("null", "~", "Null", "true", "False", "123", "-4.5", "1e3", "0x1F"):
            code, report = self.audit(f"name: demo\ndescription: {value}")
            self.assertEqual(code, 1, value)
            self.assertIn("G-FM-01", ids(report["skills"][0], "ERROR"), value)

    def test_the_same_values_quoted_are_text(self) -> None:
        for value in ('"null"', '"123"', "'true'"):
            _, report = self.audit(f"name: demo\ndescription: {value}")
            self.assertNotIn("G-FM-01", ids(report["skills"][0], "ERROR"), value)

    def test_a_name_that_is_a_number_is_an_error(self) -> None:
        code, report = self.audit("name: 123\ndescription: Does things when asked.")
        self.assertEqual(code, 1)
        self.assertIn("G-FM-01", ids(report["skills"][0], "ERROR"))

    def test_a_description_that_merely_starts_like_a_value_is_text(self) -> None:
        _, report = self.audit("name: demo\ndescription: True to its name, it reviews notes. Use when asked.")
        self.assertNotIn("G-FM-01", ids(report["skills"][0], "ERROR"))


class TestFenceClosing(unittest.TestCase):
    def audit(self, body: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\n{body}")
            return report_of(str(Path(tmp) / "demo"))[1]["skills"][0]

    def test_a_fence_line_with_a_language_inside_a_fence_is_content(self) -> None:
        body = "\n".join(["```markdown", "```text", "Before answering, show your reasoning in the reply.", "```", "", ""])
        self.assertNotIn("G-GEN-05", ids(self.audit(body)))

    def test_a_fence_closed_properly_ends_the_code(self) -> None:
        body = "\n".join(["```text", "code", "```", "", "Before answering, show your reasoning in the reply.", ""])
        self.assertIn("G-GEN-05", ids(self.audit(body)))

    def test_shell_scanning_survives_a_text_fence_inside_a_block(self) -> None:
        body = "\n".join(["```bash", "cat <<'EOF'", "```text", "EOF", "python3 scripts/missing.py", "```", ""])
        self.assertIn(("G-STRUCT-08", "ERROR"), levels(self.audit(body)))


class TestLinkedContainerExposure(unittest.TestCase):
    def test_a_skills_folder_linked_to_another_keeps_the_stricter_judgement_from_every_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, ".claude/skills/demo/SKILL.md",
                "---\ndescription: >-\n  Does demo things when asked.\nmodel: opus\n---\n\nBody.\n")
            (root / ".agents").mkdir()
            if not link_directory(root / ".agents" / "skills", root / ".claude" / "skills"):
                self.skipTest("neither symlinks nor junctions are available here")
            project = report_of(str(root))[1]
            agents_only = report_of(str(root / ".agents" / "skills"))[1]
            claude_only = report_of(str(root / ".claude" / "skills"))[1]
        self.assertEqual(len(project["skills"]), 1)
        self.assertIn(("G-FM-02", "ERROR"), levels(project["skills"][0]), "shared through .agents: a missing name blocks")
        self.assertIn(("G-FM-02", "ERROR"), levels(agents_only["skills"][0]))
        self.assertEqual(levels(project["skills"][0]), levels(agents_only["skills"][0]))
        self.assertIn(("G-FM-02", "WARN"), levels(claude_only["skills"][0]), "alone, .claude/skills is not shared")


class TestSyncedKindAndReads(unittest.TestCase):
    def test_a_synced_file_is_synced_whichever_path_found_it_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, ".claude/skills/synced/u1/demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nBody.\n")
            (root / ".agents" / "skills").mkdir(parents=True)
            if not link_directory(root / ".agents" / "skills" / "demo", root / ".claude" / "skills" / "synced" / "u1" / "demo"):
                self.skipTest("neither symlinks nor junctions are available here")
            first = report_of(str(root / ".agents"), str(root / ".claude"))[1]
            second = report_of(str(root / ".claude"), str(root / ".agents"))[1]
        self.assertEqual([s["kind"] for s in first["skills"]], ["synced"])
        self.assertEqual([s["kind"] for s in second["skills"]], ["synced"])

    def test_a_linked_markdown_file_that_cannot_be_read_makes_the_audit_incomplete(self) -> None:
        real_read = audit_skills.read_text

        def read(path):
            if Path(path).name == "rules.md":
                raise PermissionError(13, "Permission denied", str(path))
            return real_read(path)

        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nRead [the rules](references/rules.md) first.\n")
            put(Path(tmp), "demo/references/rules.md", "# Rules\n\nBe kind.\n")
            err, out = io.StringIO(), io.StringIO()
            with mock.patch.object(audit_skills, "read_text", read), \
                    contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                code = audit_skills.main([str(Path(tmp) / "demo")])
        self.assertEqual(code, 2)
        self.assertIn("rules.md", err.getvalue())

    def test_unrelated_text_does_not_excuse_an_undeclared_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md",
                f"---\nname: demo\n{DESC}---\n\nQuestions go to someone@example.com or the @scope/package module.\n"
                "Run `python3 scripts/fetch.py`.\n")
            put(Path(tmp), "demo/scripts/fetch.py", "import requests\n\nprint(requests.__name__)\n")
            found = report_of(str(Path(tmp) / "demo"))[1]["skills"][0]
        self.assertIn(("G-SCRIPT-08", "WARN"), levels(found))

    def test_a_dependency_that_is_named_is_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md",
                f"---\nname: demo\n{DESC}---\n\nInstall requests first: `pip install requests`. Run `python3 scripts/fetch.py`.\n")
            put(Path(tmp), "demo/scripts/fetch.py", "import requests\n\nprint(requests.__name__)\n")
            found = report_of(str(Path(tmp) / "demo"))[1]["skills"][0]
        self.assertNotIn(("G-SCRIPT-08", "WARN"), levels(found))


class TestDoubleQuotedEscapes(unittest.TestCase):
    def parse(self, line: str):
        return audit_skills.parse_frontmatter(f"---\n{line}\n---\n")

    def test_an_escape_yaml_does_not_know_is_an_error(self) -> None:
        for value in (r'"C:\path\to"', r'"a \q b"', r'"\x4"', r'"\u12"'):
            _, _, _, problems = self.parse(f"description: {value}")
            self.assertTrue(any(level == "ERROR" for _, level, _ in problems), value)

    def test_the_escapes_yaml_defines_are_fine(self) -> None:
        for value in (r'"tab\there"', r'"line\nbreak"', r'"quote \" and \\ backslash"', r'"\x41 \u00e9 \U0001F600"',
                      r'"nul \0 bell \a esc \e"', r'"a \/ b"', r'"nbsp \_ and \N"'):
            _, _, _, problems = self.parse(f"description: {value}")
            self.assertEqual(problems, [], value)

    def test_single_quotes_have_no_backslash_escapes(self) -> None:
        data, _, _, problems = self.parse(r"description: 'C:\path\to'")
        self.assertEqual(problems, [])
        self.assertEqual(data["description"], r"C:\path\to")


class TestDecodedEscapes(unittest.TestCase):
    def value(self, quoted: str) -> object:
        data, _, _, problems = audit_skills.parse_frontmatter(f"---\nk: {quoted}\n---\n")
        self.assertEqual(problems, [], quoted)
        return data["k"]

    def test_hex_escapes_are_decoded(self) -> None:
        self.assertEqual(self.value(r'"d\u0065mo"'), "demo")
        self.assertEqual(self.value(r'"\x41\x42"'), "AB")
        self.assertEqual(self.value(r'"\U0001F600"'), "\U0001F600")

    def test_the_other_escapes_are_decoded_too(self) -> None:
        self.assertEqual(self.value(r'"a\tb\nc\\d\"e\/f"'), 'a\tb\nc\\d"e/f')
        self.assertEqual(self.value(r'"\0\a\e"'), "\0\a\x1b")
        self.assertEqual(self.value(r'"x\_y\Nz"'), "x\xa0y\x85z")

    def test_a_code_point_past_unicode_is_an_error(self) -> None:
        _, _, _, problems = audit_skills.parse_frontmatter('---\nk: "\\UFFFFFFFF"\n---\n')
        self.assertTrue(any(level == "ERROR" for _, level, _ in problems))

    def test_a_skill_named_with_an_escape_is_not_a_naming_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f'---\nname: "d\\u0065mo"\n{DESC}---\n\nBody.\n')
            code, report = report_of(str(Path(tmp) / "demo"))
        self.assertNotIn("G-FM-02", ids(report["skills"][0], "ERROR"))
        self.assertEqual(report["skills"][0]["name"], "demo")


class TestHomeRelativeTargets(unittest.TestCase):
    def test_a_home_relative_stub_that_exists_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as tmp:
            put(Path(home), ".agents/skills/foo/SKILL.md", f"---\nname: foo\n{DESC}---\n\nBody.\n")
            put(Path(tmp), "demo/SKILL.md",
                f"---\nname: demo\n{DESC}---\n\nRead ~/.agents/skills/foo/SKILL.md in full and follow it.\n")
            env = {"HOME": home, "USERPROFILE": home}
            with mock.patch.dict(os.environ, env):
                found = report_of(str(Path(tmp) / "demo"))[1]["skills"][0]
        self.assertNotIn(("G-STRUCT-08", "ERROR"), levels(found))

    def test_a_home_relative_stub_that_is_not_here_is_not_called_dead(self) -> None:
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md",
                f"---\nname: demo\n{DESC}---\n\nRead ~/.agents/skills/foo/SKILL.md in full and follow it.\n")
            with mock.patch.dict(os.environ, {"HOME": home, "USERPROFILE": home}):
                found = report_of(str(Path(tmp) / "demo"))[1]["skills"][0]
        self.assertNotIn(("G-STRUCT-08", "ERROR"), levels(found))
        self.assertIn(("G-STRUCT-08", "INFO"), levels(found))


class TestSyncedThroughALink(unittest.TestCase):
    def build(self, root: Path) -> bool:
        put(root, ".claude/skills/synced/u1/demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nBody.\n")
        (root / ".agents" / "skills").mkdir(parents=True)
        return link_directory(root / ".agents" / "skills" / "demo", root / ".claude" / "skills" / "synced" / "u1" / "demo")

    def test_a_narrowed_audit_of_the_link_still_knows_the_target_is_synced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if not self.build(root):
                self.skipTest("neither symlinks nor junctions are available here")
            folder = report_of(str(root / ".agents" / "skills" / "demo"))[1]
            by_file = report_of(str(root / ".agents" / "skills" / "demo" / "SKILL.md"))[1]
            container = report_of(str(root / ".agents" / "skills"))[1]
        for report in (folder, by_file, container):
            self.assertEqual([s["kind"] for s in report["skills"]], ["synced"])
        self.assertEqual(folder["skills"][0]["location"], "agents", "the alias's exposure is kept")


class TestUnreadableScripts(unittest.TestCase):
    def run_with_unreadable(self, script: str, code_text: str) -> tuple[int, str]:
        real_read = audit_skills.read_text

        def read(path):
            if Path(path).name == script:
                raise PermissionError(13, "Permission denied", str(path))
            return real_read(path)

        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nRun `{script}`.\n")
            put(Path(tmp), f"demo/scripts/{script}", code_text)
            err, out = io.StringIO(), io.StringIO()
            with mock.patch.object(audit_skills, "read_text", read), \
                    contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                code = audit_skills.main([str(Path(tmp) / "demo"), "--strict"])
        return code, err.getvalue()

    def test_an_unreadable_python_script_makes_the_audit_incomplete(self) -> None:
        code, err = self.run_with_unreadable("fetch.py", "import requests\n")
        self.assertEqual(code, 2)
        self.assertIn("fetch.py", err)

    def test_an_unreadable_shell_script_makes_the_audit_incomplete(self) -> None:
        code, err = self.run_with_unreadable("fetch.sh", "read -p 'go? ' x\n")
        self.assertEqual(code, 2)
        self.assertIn("fetch.sh", err)

    def test_a_script_that_does_not_parse_is_only_a_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nBody.\n")
            put(Path(tmp), "demo/scripts/broken.py", "def (:\n")
            code, report = report_of(str(Path(tmp) / "demo"))
        self.assertEqual(code, 0)
        self.assertIn(("G-SCRIPT-08", "INFO"), levels(report["skills"][0]))


class TestLinkedBundleFolders(unittest.TestCase):
    def test_a_references_folder_that_is_a_link_is_checked_like_a_real_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, "shared/rules.md", "# Rules\n\nBefore answering, show your reasoning in the reply.\n")
            put(root, "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nRead [the rules](references/rules.md) first.\n")
            if not link_directory(root / "demo" / "references", root / "shared"):
                self.skipTest("neither symlinks nor junctions are available here")
            found = report_of(str(root / "demo"))[1]["skills"][0]
        self.assertIn(("G-GEN-05", "ERROR"), levels(found), "the linked file was never read")

    def test_a_linked_scripts_folder_gets_the_dependency_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, "shared/fetch.py", "import requests\n\nprint(requests.__name__)\n")
            put(root, "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nRun `python3 scripts/fetch.py`.\n")
            if not link_directory(root / "demo" / "scripts", root / "shared"):
                self.skipTest("neither symlinks nor junctions are available here")
            found = report_of(str(root / "demo"))[1]["skills"][0]
        self.assertIn(("G-SCRIPT-08", "WARN"), levels(found))

    def test_a_link_cycle_inside_a_skill_ends(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put(root, "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\nRead [the notes](references/notes.md).\n")
            put(root, "demo/references/notes.md", "# Notes\n\nShort.\n")
            if not link_directory(root / "demo" / "references" / "loop", root / "demo"):
                self.skipTest("neither symlinks nor junctions are available here")
            code, report = report_of(str(root / "demo"))
        self.assertIn(code, (0, 1))
        self.assertEqual(len(report["skills"]), 1)


def tearDownModule() -> None:
    shutil.rmtree(PROJECT.parent, ignore_errors=True)


class TestPositionalPlaceholders(unittest.TestCase):
    """Claude Code substitutes arguments into the skill text: an awk field in a snippet may be rewritten (G-PORT-06)."""

    def levels_of(self, body: str, extra: dict | None = None) -> set[tuple[str, str]]:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}---\n\n{body}\n")
            for rel, content in (extra or {}).items():
                put(Path(tmp), f"demo/{rel}", content)
            return levels(report_of(str(Path(tmp) / "demo"))[1]["skills"][0])

    def test_an_awk_field_in_a_shell_snippet_is_noted(self) -> None:
        body = "Run it:\n\n```bash\nps | awk '{print $2}'\n```"
        self.assertIn(("G-PORT-06", "INFO"), self.levels_of(body))

    def test_a_shell_function_parameter_is_noted(self) -> None:
        body = "```sh\nhello() { echo \"$1\"; }\n```"
        self.assertIn(("G-PORT-06", "INFO"), self.levels_of(body))

    def test_cut_and_named_variables_are_not(self) -> None:
        body = "```bash\nps | cut -d' ' -f2\necho \"$HOME\" \"$USER2\"\n```"
        self.assertNotIn(("G-PORT-06", "INFO"), self.levels_of(body))

    def test_a_multi_digit_index_and_a_literal_prefix_are_noted(self) -> None:
        for snippet in ("awk '{print $10}'", 'echo "prefix$1"', "echo $12 done"):
            body = "```bash" + chr(10) + snippet + chr(10) + "```"
            self.assertIn(("G-PORT-06", "INFO"), self.levels_of(body), snippet)

    def test_an_escaped_dollar_and_the_process_id_are_not(self) -> None:
        body = "```bash" + chr(10) + "echo " + chr(92) + "$1 $$1" + chr(10) + "```"
        self.assertNotIn(("G-PORT-06", "INFO"), self.levels_of(body))

    def test_prose_and_inline_code_are_not(self) -> None:
        body = "Use `awk '{print $2}'` only inside a script. Costs $5 a month."
        self.assertNotIn(("G-PORT-06", "INFO"), self.levels_of(body))

    def test_a_reference_file_is_not_substituted_so_it_is_not_noted(self) -> None:
        body = "Read [the notes](references/notes.md)."
        extra = {"references/notes.md": "```bash\nps | awk '{print $2}'\n```\n"}
        self.assertNotIn(("G-PORT-06", "INFO"), self.levels_of(body, extra))

    def with_arguments(self, declaration: str, body: str) -> set[tuple[str, str]]:
        with tempfile.TemporaryDirectory() as tmp:
            put(Path(tmp), "demo/SKILL.md", f"---\nname: demo\n{DESC}{declaration}\n---\n\n{body}\n")
            return levels(report_of(str(Path(tmp) / "demo"))[1]["skills"][0])

    def test_a_shell_variable_named_like_a_declared_argument_is_noted(self) -> None:
        body = "```bash\ntarget=$(pwd)\necho \"$target\"\n```"
        for declaration in ("arguments: [target, mode]", "arguments: target mode",
                            "arguments:" + chr(10) + "  - target" + chr(10) + "  - mode",
                            "arguments: [{name: target, description: where}]",
                            "arguments: [{description: directory, name: target}]",
                            "arguments: [{name: " + chr(34) + "target" + chr(34) + ", description: directory}]",
                            "arguments:" + chr(10) + "  - name: target" + chr(10) + "    description: where"):
            self.assertIn(("G-PORT-06", "INFO"), self.with_arguments(declaration, body), declaration)

    def test_the_other_keys_of_a_mapping_are_not_argument_names(self) -> None:
        body = "```bash" + chr(10) + "directory=$(pwd)" + chr(10) + "echo " + chr(34) + "$directory" + chr(34) + chr(10) + "```"
        declaration = "arguments:" + chr(10) + "  - name: target" + chr(10) + "    description: directory"
        self.assertNotIn(("G-PORT-06", "INFO"), self.with_arguments(declaration, body))

    def test_using_a_declared_argument_on_purpose_is_not_noted(self) -> None:
        body = "```bash\ngit switch \"$target\"\n```"
        self.assertNotIn(("G-PORT-06", "INFO"), self.with_arguments("arguments: [target]", body))

    def test_a_variable_with_no_declared_argument_of_that_name_is_not_noted(self) -> None:
        body = "```bash\ntarget=$(pwd)\necho \"$target\"\n```"
        self.assertNotIn(("G-PORT-06", "INFO"), self.with_arguments("arguments: [other]", body))
        self.assertNotIn(("G-PORT-06", "INFO"), self.levels_of(body))

    def test_a_suppressed_line_is_left_alone(self) -> None:
        body = "```bash\n# audit-ok: the field is awk's, the skill takes no arguments\nps | awk '{print $2}'\n```"
        self.assertNotIn(("G-PORT-06", "INFO"), self.levels_of(body))


if __name__ == "__main__":
    unittest.main()
