"""The freshness check has to go red on every kind of drift, offline, and the real manifest has to be coherent."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "padosoft-skill-audit"
SCRIPT = SKILL / "scripts" / "check_freshness.py"
MANIFEST = SKILL / "references" / "sources.json"
GUIDELINES = SKILL / "references" / "guidelines.md"

PAGE_RULES = """# Skill rules

## Keep it short

Keep the body “under 500 lines” for optimal performance.

```markdown
## A heading inside an example, not a section of the page
```

## Use forward slashes

Always use forward slashes in file paths.
"""

PAGE_MODELS = "Current models: Claude Opus 5.5 and Claude Sonnet 5.5.\n"

PAGE_FIELDS = """# Skills

### Frontmatter reference

| Field | Required | Description |
| :- | :- | :- |
| `name` | No | Command name |
| `description` | Recommended | What it does |

### Next section
"""


def skill_md(version: str) -> str:
    return f"---\nname: demo\ndescription: Demo.\nmetadata:\n  version: {version}\n---\n\n# Demo\n"


def manifest() -> dict:
    return {
        "schema": 1,
        "upstream": {"skill_md": "https://example.com/SKILL.md", "install": "reinstall the skill"},
        "covered_models": ["Opus 5.5", "Sonnet 5.5"],
        "model_pages": ["MODELS"],
        "claude_code_fields": {"source": "FIELDS", "section": "Frontmatter reference", "known": ["description", "name"]},
        "sources": [
            {
                "key": "RULES",
                "url": "https://example.com/rules.md",
                "track_headings": True,
                "rules": ["G-STRUCT-01", "G-STRUCT-06"],
                "anchors": [
                    {"text": 'Keep the body "under 500 lines"', "rules": ["G-STRUCT-01"]},
                    {"text": "Always use forward slashes in file paths", "rules": ["G-STRUCT-06"]},
                ],
                "headings": ["keep it short", "use forward slashes"],
            },
            {"key": "MODELS", "url": "https://example.com/models.md", "anchors": []},
            {"key": "FIELDS", "url": "https://example.com/fields.md", "anchors": []},
            {"key": "PDF", "url": "https://example.com/guide.pdf", "fetch": False, "anchors": []},
        ],
    }


class FreshnessFixture:
    """A manifest, an offline page directory and an installed SKILL.md, all in a temporary folder."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.pages = base / "pages"
        self.pages.mkdir()
        self.manifest_path = base / "sources.json"
        self.skill_md = base / "SKILL.md"
        self.data = manifest()
        self.write_pages(rules=PAGE_RULES, models=PAGE_MODELS, fields=PAGE_FIELDS, upstream=skill_md("0.1.0"))
        self.skill_md.write_text(skill_md("0.1.0"), encoding="utf-8")

    def write_pages(self, **pages: str) -> None:
        names = {"rules": "rules.md", "models": "models.md", "fields": "fields.md", "upstream": "upstream-skill.md"}
        for key, text in pages.items():
            (self.pages / names[key]).write_text(text, encoding="utf-8")

    def run(self, *extra: str) -> tuple[int, dict]:
        self.manifest_path.write_text(json.dumps(self.data), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--manifest", str(self.manifest_path), "--offline", str(self.pages),
             "--skill-md", str(self.skill_md), "--json", *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT,
        )
        if result.returncode == 2 and not result.stdout.strip():
            return 2, {"stderr": result.stderr}
        return result.returncode, json.loads(result.stdout)


class TestFreshnessCheck(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = FreshnessFixture(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def kinds(self, report: dict) -> set[str]:
        return {item["kind"] for item in report["drift"]}

    def test_aligned_sources_pass(self) -> None:
        """Curly quotes, emphasis and headings inside code fences must not read as drift."""
        code, report = self.fx.run()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["status"], "aligned")

    def test_a_missing_anchor_names_its_rules(self) -> None:
        self.fx.write_pages(rules=PAGE_RULES.replace("Always use forward slashes", "Prefer forward slashes"))
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        self.assertIn("missing-anchor", self.kinds(report))
        self.assertIn("G-STRUCT-06", report["rules_to_recheck"])
        self.assertNotIn("G-STRUCT-01", [r for i in report["drift"] if i["kind"] == "missing-anchor" for r in i["rules"]])

    def test_new_and_removed_sections(self) -> None:
        self.fx.write_pages(rules=PAGE_RULES.replace("## Use forward slashes", "## Paths across platforms"))
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        self.assertTrue({"new-section", "removed-section"} <= self.kinds(report), report)

    def test_a_new_model_is_drift(self) -> None:
        self.fx.write_pages(models=PAGE_MODELS + "Introducing Claude Opus 6.\n")
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        self.assertEqual([i["detail"] for i in report["drift"] if i["kind"] == "new-model"], ["Opus 6"])

    def test_a_new_model_family_is_drift(self) -> None:
        self.fx.write_pages(models=PAGE_MODELS + "Meet Claude Aria 1, a new family.\n")
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        self.assertIn("Aria 1", [i["detail"] for i in report["drift"]])

    def test_new_and_removed_frontmatter_fields(self) -> None:
        fields = PAGE_FIELDS.replace("| `description` |", "| `model-notes` | No | x |\n| `description` |")
        fields = fields.replace("| `name` | No | Command name |\n", "")
        self.fx.write_pages(fields=fields)
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        details = {(i["kind"], i["detail"]) for i in report["drift"]}
        self.assertIn(("new-field", "model-notes"), details)
        self.assertIn(("removed-field", "name"), details)

    def test_a_longer_fence_may_hold_a_shorter_one(self) -> None:
        """A four-backtick example with a three-backtick block inside must not expose its ## lines as sections."""
        example = ["````markdown", "Example:", "```", "code", "```", "## Not a section of the page", "````"]
        self.fx.write_pages(rules="\n".join([PAGE_RULES, *example, ""]))
        code, report = self.fx.run()
        self.assertEqual(code, 0, report)
        self.assertNotIn("new-section", self.kinds(report))

    def test_a_fence_closes_only_on_a_matching_delimiter(self) -> None:
        lines = ["```markdown", "~~~", "## Still inside", "```", "", "## A real new section"]
        self.fx.write_pages(rules="\n".join([PAGE_RULES, *lines, ""]))
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        details = [i["detail"] for i in report["drift"] if i["kind"] == "new-section"]
        self.assertEqual(details, ["a real new section"])

    def test_a_model_name_wrapped_over_two_lines_is_still_found(self) -> None:
        self.fx.write_pages(models=PAGE_MODELS + "Introducing Claude Opus\n6, our newest model.\n")
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        self.assertIn("Opus 6", [i["detail"] for i in report["drift"] if i["kind"] == "new-model"])

    def test_an_html_copy_is_compared_on_what_it_keeps_and_says_what_it_cannot(self) -> None:
        """Converting HTML to text drops headings and tables: that must be a note, never invented drift."""
        (self.fx.pages / "rules.md").unlink()
        (self.fx.pages / "rules.html").write_text(
            "<h2>Keep it short</h2><p>Keep the body “under 500 lines” for optimal performance.</p>"
            "<h2>Use forward slashes</h2><p>Always use forward slashes in file paths.</p>",
            encoding="utf-8",
        )
        code, report = self.fx.run()
        self.assertEqual(code, 0, report)
        self.assertNotIn("removed-section", self.kinds(report))
        self.assertTrue(any("HTML" in note for note in report["notes"]), report["notes"])

    def test_an_html_copy_still_catches_a_missing_anchor(self) -> None:
        (self.fx.pages / "rules.md").unlink()
        (self.fx.pages / "rules.html").write_text("<h2>Keep it short</h2><p>Nothing useful here.</p>", encoding="utf-8")
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        self.assertIn("missing-anchor", self.kinds(report))

    def test_rebaseline_refuses_a_source_that_has_no_structure_to_record(self) -> None:
        (self.fx.pages / "rules.md").unlink()
        (self.fx.pages / "rules.html").write_text("<h2>Keep it short</h2><p>text</p>", encoding="utf-8")
        self.fx.manifest_path.write_text(json.dumps(self.fx.data), encoding="utf-8")
        before = self.fx.manifest_path.read_text(encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--manifest", str(self.fx.manifest_path), "--offline", str(self.fx.pages),
             "--rebaseline"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("HTML", result.stderr)
        self.assertEqual(self.fx.manifest_path.read_text(encoding="utf-8"), before, "the manifest must be untouched")

    def test_markdown_formatting_does_not_hide_a_model_name(self) -> None:
        for text in ("Introducing Claude **Opus 6**.", "Introducing Claude Opus **6**.", "Introducing `Claude Opus 6`.",
                     "Introducing _Claude Opus 6_.", "Introducing [Claude Opus 6](https://example.com/opus-6)."):
            self.fx.write_pages(models=PAGE_MODELS + text)
            code, report = self.fx.run()
            self.assertEqual(code, 1, text)
            self.assertIn("Opus 6", [i["detail"] for i in report["drift"] if i["kind"] == "new-model"], text)

    def test_a_link_around_part_of_a_model_name_does_not_hide_it(self) -> None:
        for text in ("Introducing Claude [Opus 6](https://example.com/opus-6).", "Introducing [Claude](https://a.example) Opus 6.",
                     "Introducing Claude Opus [6](https://example.com/6)."):
            self.fx.write_pages(models=PAGE_MODELS + text)
            code, report = self.fx.run()
            self.assertEqual(code, 1, text)
            self.assertIn("Opus 6", [i["detail"] for i in report["drift"] if i["kind"] == "new-model"], text)

    def test_a_model_page_with_no_model_name_is_drift_not_silence(self) -> None:
        self.fx.write_pages(models="Scheduled maintenance. Please try again later.")
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        self.assertIn("unreadable-models", self.kinds(report))

    def test_rebaseline_refuses_a_field_table_it_cannot_read(self) -> None:
        self.fx.write_pages(fields=PAGE_FIELDS.replace("`", ""))
        self.fx.manifest_path.write_text(json.dumps(self.fx.data), encoding="utf-8")
        before = self.fx.manifest_path.read_text(encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--manifest", str(self.fx.manifest_path), "--offline", str(self.fx.pages),
             "--rebaseline"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("no baseline", result.stderr)
        self.assertEqual(self.fx.manifest_path.read_text(encoding="utf-8"), before, "the manifest must be untouched")

    def test_html_entities_do_not_hide_a_model_name(self) -> None:
        (self.fx.pages / "models.md").unlink()
        (self.fx.pages / "models.html").write_text(
            "<p>Current models: Claude&nbsp;Opus&nbsp;5.5 and Claude Sonnet 5.5. Introducing Claude&nbsp;Opus&#32;6.</p>",
            encoding="utf-8",
        )
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        self.assertEqual([i["detail"] for i in report["drift"] if i["kind"] == "new-model"], ["Opus 6"])

    def test_a_field_table_that_cannot_be_read_is_drift_not_silence(self) -> None:
        self.fx.write_pages(fields=PAGE_FIELDS.replace("`", ""))
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        self.assertIn("unreadable-fields", self.kinds(report))
        self.assertIn("G-FM-04", report["rules_to_recheck"])

    def test_an_outdated_copy_says_how_to_update(self) -> None:
        self.fx.write_pages(upstream=skill_md("0.2.0"))
        code, report = self.fx.run()
        self.assertEqual(code, 1)
        outdated = [i for i in report["drift"] if i["kind"] == "outdated-copy"]
        self.assertTrue(outdated and "reinstall the skill" in outdated[0]["detail"])

    def test_an_unpublished_copy_is_only_a_note(self) -> None:
        (self.fx.pages / "upstream-skill.md").unlink()
        code, report = self.fx.run()
        self.assertEqual(code, 0, report)
        self.assertTrue(report["notes"])

    def test_the_running_model_must_be_covered(self) -> None:
        code, _ = self.fx.run("--model", "claude-opus-5-5")
        self.assertEqual(code, 0)
        code, report = self.fx.run("--model", "Claude Haiku 5.5")
        self.assertEqual(code, 1)
        self.assertEqual([i["detail"] for i in report["drift"]], ["Haiku 5.5"])

    def test_a_model_from_an_unknown_family_is_uncovered_not_ignored(self) -> None:
        code, report = self.fx.run("--model", "claude-foo-9")
        self.assertEqual(code, 1)
        self.assertEqual([i["detail"] for i in report["drift"]], ["Foo 9"])

    def test_the_model_verdict_is_always_stated(self) -> None:
        self.assertIn("covered", self.fx.run("--model", "Claude Opus 5.5")[1]["model"])
        self.assertEqual(self.fx.run()[1]["model"], "not given")
        code, report = self.fx.run("--model", "gpt-4o")
        self.assertEqual(code, 0)
        self.assertIn("unrecognised", report["model"])

    def test_one_unreachable_page_is_partial_not_a_failure(self) -> None:
        (self.fx.pages / "models.md").unlink()
        code, report = self.fx.run()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["status"], "partial")
        self.assertEqual([i["source"] for i in report["unreachable"]], ["MODELS"])

    def test_no_readable_page_is_unverifiable(self) -> None:
        for page in self.fx.pages.iterdir():
            page.unlink()
        code, report = self.fx.run()
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "unverifiable")

    def test_rebaseline_records_the_reviewed_state(self) -> None:
        self.fx.write_pages(models=PAGE_MODELS + "Introducing Claude Opus 6.\n")
        self.fx.manifest_path.write_text(json.dumps(self.fx.data), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--manifest", str(self.fx.manifest_path), "--offline", str(self.fx.pages),
             "--rebaseline"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = json.loads(self.fx.manifest_path.read_text(encoding="utf-8"))
        self.assertIn("Opus 6", updated["covered_models"])

    def test_a_missing_manifest_is_an_execution_error(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--manifest", str(self.fx.base / "nope.json")],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--manifest", result.stderr)


class TestFetcherContentType(unittest.TestCase):
    """What the server says it sent decides how a page is read, whatever the address ended in."""

    @staticmethod
    def fetcher_module():
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_freshness_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        sys.modules["check_freshness_under_test"] = module
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def response(body: str, content_type: str):
        class Response:
            headers = {"Content-Type": content_type}

            def read(self) -> bytes:
                return body.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *exc) -> bool:
                return False

        return Response()

    def get(self, url: str, body: str, content_type: str):
        from unittest import mock

        module = self.fetcher_module()
        fetcher = module.Fetcher(None, 5)
        with mock.patch.object(module.urllib.request, "urlopen", return_value=self.response(body, content_type)):
            return fetcher.get("PAGE", url), fetcher

    def test_a_md_address_that_answers_html_is_converted_and_flagged(self) -> None:
        text, fetcher = self.get("https://example.com/page.md", "<h2>Title</h2><p>Claude&nbsp;Opus&nbsp;6</p>",
                                 "text/html; charset=utf-8")
        self.assertNotIn("<h2>", text)
        self.assertIn("Opus 6", self.fetcher_module().models_in(text))
        self.assertIn("PAGE", fetcher.flattened)

    def test_markdown_is_left_alone(self) -> None:
        text, fetcher = self.get("https://example.com/page.md", "## Title\n\nBody\n", "text/markdown; charset=utf-8")
        self.assertEqual(text, "## Title\n\nBody\n")
        self.assertNotIn("PAGE", fetcher.flattened)


class TestFetchFailures(unittest.TestCase):
    """A source that cannot be read, in any way, is reported as unreachable; the others are still checked."""

    @staticmethod
    def module():
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_freshness_failures", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        sys.modules["check_freshness_failures"] = module
        spec.loader.exec_module(module)
        return module

    def run_check(self, failure: Exception):
        import http.client

        module = self.module()

        class Fetcher:
            flattened: set = set()

            def get(self, key, url, timeout=None):
                if key == "BROKEN":
                    raise failure
                return "Keep the body under 500 lines for optimal performance."

        data = {
            "sources": [
                {"key": "OK", "url": "u1", "anchors": [{"text": "under 500 lines", "rules": ["G-STRUCT-01"]}]},
                {"key": "BROKEN", "url": "u2", "anchors": [{"text": "anything", "rules": ["G-STRUCT-02"]}]},
            ]
        }
        self.assertTrue(http.client)
        return module.check(data, Fetcher(), None, None)

    def test_a_truncated_response_is_unreachable_not_a_crash(self) -> None:
        import http.client

        result = self.run_check(http.client.IncompleteRead(b"partial"))
        self.assertEqual(result.status, "partial")
        self.assertEqual([i.source for i in result.unreachable], ["BROKEN"])
        self.assertEqual(result.checked, 1, "the healthy source is still checked")

    def test_other_http_protocol_errors_are_unreachable_too(self) -> None:
        import http.client

        for failure in (http.client.RemoteDisconnected("closed"), http.client.BadStatusLine("x"), ConnectionResetError()):
            self.assertEqual(self.run_check(failure).status, "partial", repr(failure))


class TestRealManifest(unittest.TestCase):
    """The shipped manifest must point at rules that exist, so a drift report is always actionable."""

    def test_every_rule_in_the_manifest_exists_in_the_guidelines(self) -> None:
        defined = set(re.findall(r"\*\*(G-[A-Z]+-\d{2})\*\*", GUIDELINES.read_text(encoding="utf-8")))
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        referenced = {r for s in data["sources"] for r in s.get("rules", [])}
        referenced |= {r for s in data["sources"] for a in s.get("anchors", []) for r in a.get("rules", [])}
        self.assertTrue(defined, "no rule IDs found in guidelines.md")
        self.assertEqual(referenced - defined, set(), "sources.json cites rules that guidelines.md does not define")

    def test_every_source_key_is_listed_in_the_guidelines(self) -> None:
        text = GUIDELINES.read_text(encoding="utf-8")
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        missing = [s["key"] for s in data["sources"] if f"`[{s['key']}]`" not in text]
        self.assertEqual(missing, [], "add these keys to the Sources table of guidelines.md")

    def test_every_anchor_is_tied_to_a_rule_and_baselines_exist(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertTrue(data["covered_models"], "run --rebaseline after reviewing the model guides")
        self.assertTrue(data["claude_code_fields"]["known"])
        for source in data["sources"]:
            for anchor in source.get("anchors", []):
                self.assertTrue(anchor.get("rules"), f"{source['key']}: anchor without rules: {anchor['text']}")
            if source.get("track_headings"):
                self.assertTrue(source.get("headings"), f"{source['key']}: tracked but no baseline headings")

    def test_rule_ids_are_unique(self) -> None:
        ids = re.findall(r"^- \*\*(G-[A-Z]+-\d{2})\*\*", GUIDELINES.read_text(encoding="utf-8"), re.MULTILINE)
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        self.assertEqual(duplicates, [], "a rule ID is defined twice")


if __name__ == "__main__":
    unittest.main()
