#!/usr/bin/env python3
"""Catalog consistency: every skill declares profile and scope, index and router aligned."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_catalog.py"
sys.path.insert(0, str(ROOT / "scripts"))
import build_catalog as bc  # noqa: E402


class TestFrontmatter(unittest.TestCase):
    def test_every_skill_declares_profile_and_scope(self) -> None:
        skills, problems = bc.load_skills()
        self.assertEqual(problems, [], "\n".join(problems))
        self.assertTrue(skills)
        for s in skills:
            with self.subTest(skill=s.name):
                self.assertTrue(s.profiles)
                self.assertIn(s.scope, bc.KNOWN_SCOPES)
                self.assertTrue(s.name.startswith("padosoft-"), "the name must carry the brand prefix")

    def test_global_skills_stay_few(self) -> None:
        """Every global skill costs context in EVERY session: the core profile stays small.

        The cap was raised from 5 to 8 when the third stack joined the catalog: a rule that three
        independent stacks reached on their own is not a per-stack convention, and the alternative
        to a global skill is the same content duplicated in every stack skill, free to diverge.
        The number is still a forcing function, not a budget to fill: raising it again is a
        deliberate decision in a PR, exactly like adding a profile.
        """
        skills, _ = bc.load_skills()
        globals_ = [s.name for s in skills if s.scope == "global"]
        self.assertLessEqual(len(globals_), 8, f"too many global skills: {globals_}")


class TestGeneratedFiles(unittest.TestCase):
    def test_catalog_and_profiles_up_to_date(self) -> None:
        res = subprocess.run([sys.executable, str(BUILD), "--check"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_profiles_json_matches_frontmatter(self) -> None:
        skills, _ = bc.load_skills()
        data = json.loads((ROOT / "profiles.json").read_text(encoding="utf-8"))
        for s in skills:
            for p in s.profiles:
                with self.subTest(skill=s.name, profile=p):
                    self.assertIn(s.name, data["profiles"][p])


class TestReadmeSection(unittest.TestCase):
    def test_readme_lists_every_skill(self) -> None:
        """The 'Available skills' section must mention every skill: it is the page a new dev reads."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        section = readme.split(bc.README_START, 1)[1].split(bc.README_END, 1)[0]
        skills, _ = bc.load_skills()
        for s in skills:
            with self.subTest(skill=s.name):
                self.assertIn(s.name, section)
                self.assertIn(s.scope, section)


class TestInstaller(unittest.TestCase):
    def test_dry_run_prints_one_command_per_skill(self) -> None:
        data = json.loads((ROOT / "profiles.json").read_text(encoding="utf-8"))
        profile, names = next(iter(data["profiles"].items()))
        res = subprocess.run(["bash", str(ROOT / "scripts" / "install-profile.sh"), profile, "--dry-run"],
                             capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(res.returncode, 0, res.stderr)
        for n in names:
            self.assertIn(n, res.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
