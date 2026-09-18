# Contributing

Thanks: these skills live on real cases. A rule is only worth having if somebody has seen it break.

## Principles

1. **Evidence before opinion.** Every new or changed rule comes with a Mailtrap report (HTML Check or spam),
   a MailUp Check-up, a client screenshot or a reproducible test.
2. **One rule, one ID.** The `R-xxx` IDs are stable: they are never recycled. If a rule is retired, it stays
   in the file marked as deprecated, with the rationale.
3. **Every blocking rule must be verifiable by the linter** or, when it cannot be automated, it must say so
   explicitly in `skills/padosoft-email-html-builder/references/rules.md`.
4. **No external dependencies** in the scripts: Python standard library only, so they run everywhere and in CI.

## Flow

```bash
git clone https://github.com/padosoft/skills.git
cd skills
make all          # validate + test + lint of the template
```

1. Open an issue with the *Rule proposal* template (or *Bug report*).
2. Create a branch: `feat/r-123-short-name` or `fix/lint-false-positive`.
3. Change things in this order:
   - `skills/padosoft-email-html-builder/references/rules.md` — the normative rule, with its level (MUST/SHOULD/MAY) and source;
   - `skills/padosoft-email-html-builder/scripts/lint_email.py` — the check;
   - `tests/` — a test that fails without the fix;
   - `skills/padosoft-email-html-builder/SKILL.md` — only if the flow or a pattern changes, keeping it under 500 lines;
   - `CHANGELOG.md`.
4. `make all` has to pass. CI runs on Python 3.10, 3.12 and 3.13.
5. Open the PR and fill in the checklist.

## Adding a rule: an example

```python
# skills/padosoft-email-html-builder/scripts/lint_email.py
if re.search(r'<td[^>]*background=', html):
    r.add("R-210", "MUST", "Background image on <td>: use bgcolor or VML for Outlook", line)
```

```python
# tests/test_lint_email.py
EXPECTED = [..., "R-210"]
```

## Where a skill belongs: profile and scope

CI **does not decide** these two fields: the author declares them in the frontmatter, and CI only verifies
that they are there, that the profile exists and that the generated files are up to date. These are the
criteria.

```yaml
metadata:
  profiles: laravel, api    # which stacks need it
  scope: project            # project (default) or global
```

### `scope: global` — a strict filter

A global skill loads its name and description into **every** session, on every project, for everyone. It is
only worth it if the answer is yes to all three:

1. **Is it useful on any stack?** If it depends on the language or the framework, it is not global.
2. **Is it correct everywhere?** If its rules only hold for certain projects, it would do damage elsewhere.
3. **Would its absence be a problem?** If a dev can install it when needed, leave it at project level.

Global skills always live in the `core` profile, and a test fails CI if they go above five: the cap is
deliberately low, to force a choice.

### `profiles:` — which stack it belongs to

- One profile per **technology stack** (`laravel`, `node`, `react-native`) or per **application domain**
  (`email`, `api`, `payments`, `data`, `devops`).
- A skill can live in several profiles, when it is genuinely needed in both: `padosoft-api-design` lives in
  `laravel` and in `node` because it is always used in those projects.
- Do **not** create a profile for a single skill: as long as there is only one, it belongs to the closest
  existing profile.
- The allowed profiles are listed in `KNOWN_PROFILES` inside `scripts/build_catalog.py`. Adding one is an
  explicit change, and it goes through a PR like everything else.

### Then

1. `make catalog` regenerates `CATALOG.md`, `profiles.json` and the catalog inside `padosoft-skills-router`.
2. Add the skill to a package in `plugins/`, otherwise `validate_plugins.py` fails: a skill outside every
   package would be invisible to whoever installs from Claude Code.
3. Add a few queries to `evals/` — including ones that must trigger **other** skills: with many skills
   installed, false positives are the main problem.
4. `make all` has to pass.

## Testing the skill activations

`evals/eval_queries.json` holds labelled queries (`should_trigger` true/false) to verify that the
`description` field triggers the skill when it should and not when it should not — the method is described in
[Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions).
If you change the `description`, re-run the evals and report the activation rate in the PR.

## What we do not accept

- Rules taken from generic articles without verification against the checkers.
- Changes that make the report "cleaner" by hiding a real problem instead of solving it.
- Runtime dependencies in the scripts, or real tokens and data in committed files.

## Code of conduct

The [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) applies.
Reports: opensource@padosoft.com.
