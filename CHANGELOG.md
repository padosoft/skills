# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versioning follows
[SemVer](https://semver.org/): *major* when a new MUST rule can invalidate existing templates.

## [Unreleased]

### Added
- `padosoft-git-commit-integrity` (`core`, **global**) — what git actually recorded, as opposed to what you
  changed. Two failures, both invisible on the machine that made the commit: files missing because `git add -A`
  skips ignored paths in silence (the real case: a generic `logs/` pattern swallowed the source directory
  `otel/logs/`, with build and tests green locally), and files whose stored line endings are those of whoever
  committed them. The fixes that are not obvious: a negation in `.gitignore` rather than `git add -f`, which
  leaves the trap armed for the next file; and `git add --renormalize .` after adding a `.gitattributes`,
  without which the already-committed blobs stay as they were while everyone assumes they are protected.
  Third global skill, on a cap of five.

## [1.1.0] - 2026-09-19

### Added
- **Four skills extracted from two production projects** (a Bun/Hono API and its spec-first OpenAPI
  repository), generalised and translated to English. The know-how comes from a 2026-07 security audit, the
  findings of a hardening PR and one real incident, not from generic checklists.
  - `padosoft-api-security-review` (`api`, `node`) — ten checks with grep pre-screens: auth on every mutating
    route, ownership from the authenticated id, no secrets or PII in responses, redacted logs and telemetry,
    fail-safe environment gates, bound SQL, resource caps, downstream injection, no trust from caller input,
    supply chain. The full rules with their origin are in `references/rules.md`.
  - `padosoft-hono-api-conventions` (`node`, `api`) — the three-layer Controller → Repository → Query
    architecture, typed context and middleware factory, transactions on multi-write, and the seven recurring
    mistakes.
  - `padosoft-openapi-spec-workflow` (`api`, `node`) — what must stay in sync when a shared contract changes
    (schema, mocks and per-tenant overrides, endpoint, client, tests), changesets, and the verification loop.
  - `padosoft-pr-review-triage` (`devops`) — triage of automated review comments (Copilot, Codex,
    CodeRabbit): categorise, get approval before touching code, fix, reply, and propose a rule when the bot
    found what the project checks missed.
- Two marketplace packages: `padosoft-api` and `padosoft-devops`.

### Fixed (field test against the source project)

The four skills were run against the codebase they were extracted from. What the pre-screens actually do on
real code, rather than on the example in the rule:

- `api-security-review` check 4 **missed the class of bug it was written for**. The two real leaking lines
  were matched only because their message happened to contain the word "token"; the identical call with the
  message "db lookup failed" was invisible. A driver error object carries the already-formatted query with
  the bound values substituted, so the leak is in the *object*, not in the sentence. Added a second
  pre-screen for objects handed to a logger, narrowed to catch blocks around database calls, plus the
  redaction helper that keeps `code`/`errno` instead of redacting everything.
- `api-security-review` check 5 **flagged the reference implementation of its own fix**: the pattern matched
  `process.env.NODE_ENV`, which is the correct raw read the rule prescribes. 1 false positive → 0.
- `api-security-review` check 6 returned **89 hits on a clean codebase**, roughly half of them the generated
  placeholders and offsets the rule itself authorises. Excluded them (89 → 42) and documented what a
  compliant hit looks like, so it is dismissed in one pass instead of re-investigated on every commit.
- `hono-api-conventions` transaction screen grepped for `execute("INSERT`, which **never matches** a
  three-layer architecture: the SQL arrives from the query layer as a variable. It reported zero on a
  codebase with writes in 13 repository files — a green check that never looked. Rewritten to recognise the
  write through the query it imports; it now surfaces 10 candidate files and correctly skips the ones that
  already use transactions.
- Documented that a pre-screen is a screen and not a verdict, with the compliant patterns to recognise:
  allow-listed sort columns, `SELECT *` in a derived table, a wildcard *optional* auth on its own prefix, and
  `LIMIT`/`OFFSET` interpolated deliberately because the driver does not bind them.

### Fixed
- `scripts/build_catalog.py` wrote the generated files with the platform default newline, so every
  `make catalog` on Windows rewrote CATALOG.md, profiles.json, README.md and the router SKILL.md with CRLF,
  against `.gitattributes`. All four writes now pass an explicit LF newline.

> Le voci `2.x` qui sotto sono il versionamento **ereditato dalla skill email**, precedente al
> tag del repository. Le release del repo partono da `v1.0.0`.

## [2.1.0] - 2026-09-18

### Changed
- **The whole repository is now in English** — README, CATALOG, CONTRIBUTING, SECURITY, skills, scripts,
  tests, evals and CI. The skills are meant to be usable outside Padosoft, so the language people read them
  in is English. Skill names, profiles and scopes are unchanged: nothing to reinstall.

### Fixed
- `scripts/install-profile.ps1`: the one-liner `irm … | iex; Install-PadosoftSkills core -Global` failed with
  *"Cannot bind argument to parameter 'Path' because it is an empty string"*. `$PSScriptRoot` is empty when
  the script is piped into `iex`, and `Split-Path` was called on it before the guard that checks it. The
  local `profiles.json` lookup is now guarded, so it falls back to the remote copy as intended. The loop
  variables that shadowed the `$profile` and `$args` automatic variables were renamed at the same time.

### Added
- Cover banner in the README (`assets/padosoft_skills_banner.png`).

## [2.0.0] - 2026-09-17

### Changed
- **The repository becomes `padosoft/skills`**, a monorepo of the company skills. The email skill lives in
  `skills/padosoft-email-html-builder/` and keeps its name: whoever installed it has nothing to do.
- **Multi-package** Claude Code marketplace: `padosoft-core` and `padosoft-email` in `plugins/`, so you
  install the package for your stack instead of the whole catalog.

### Added
- README: an **Available skills** section generated from the frontmatter, with one card per skill (what it
  does, when it triggers, profiles, scope, version, install command); `build_catalog.py --check` verifies it
  like the other generated files, and a test checks that no skill is left out.
- `skills/padosoft-skill-creator/` — the meta-skill: how to write a Padosoft skill (placement, description,
  body, scripts, checks), with `scripts/new_skill.py` for the scaffolding, the SKILL.md template and the
  review checklist with the recurring mistakes.
- `skills/padosoft-skills-router/` — a global skill acting as a living catalog: it says which skill is needed
  for the project you opened and which command installs it.
- `scripts/build_catalog.py` — generates `CATALOG.md`, `profiles.json` and the router's catalog section from
  the frontmatter (`metadata.profiles`, `metadata.scope`); with `--check` it fails when something is stale.
- `scripts/install-profile.sh` and `.ps1` — installation by profile, including through `curl | bash` without
  cloning.
- `scripts/validate_plugins.py` — manifest consistency and coverage: no skill can stay outside the packages.
- `tests/test_catalog.py` — every skill declares profile and scope, brand prefix, a cap of 5 global skills,
  generated files up to date, installer working in dry-run.
- CONTRIBUTING: the criteria for choosing profile and scope, with the three-question filter for `scope: global`.

## [1.1.0] - 2026-09-17

### Added
- **Claude Code plugin manifests**: `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
  The repository acts as a marketplace of itself, so Claude Code handles installation and updates
  (`claude plugin marketplace add padosoft/email-html-builder`).
- README: sections dedicated to Claude Code as a plugin and to Codex (`~/.agents/skills/`).

### Changed
- **Vercel-style repository layout**: the skill lives in `skills/padosoft-email-html-builder/`, the canonical
  path the `npx skills` CLI looks for. The repo can now host several skills.
- **Name with a brand prefix**: `padosoft-email-html-builder`, to avoid collisions in the ecosystem.
- Makefile and CI updated to the new paths; `make validate` validates every skill present in `skills/`.
- README rewritten around `npx skills add padosoft/email-html-builder`.

## [1.0.1] - 2026-09-17

### Fixed
- `lint_email.py`: placeholder detection used `TODO` without a word boundary and reported false positives on
  words containing it (`METODO_PAGAMENTO`). It now uses `\bTODO\b` (same treatment for `lorem ipsum`).

### Changed
- `R-405`/`R-454`: unsubscribe is required for commercial and bulk email; purely transactional messages are
  exempt. New `--transactional` flag that downgrades `R-454` to SHOULD.
- `SKILL.md`: added the marketing/transactional distinction and the "without Mailtrap" path (gates G3-G6
  declared as not run instead of estimated).

## [1.0.0] - 2026-09-17

### Added
- `SKILL.md`: a 10-phase workflow with 8 acceptance gates, reusable HTML patterns, the baseline of allowed
  warnings and the delivery report format.
- `references/rules.md`: ~110 `R-xxx` rules with level and source (Mailtrap, MailUp, Gmail/Yahoo, WCAG, real
  mistakes v1→v5), plus the table of historical anti-patterns.
- `scripts/lint_email.py`: a dependency-free static linter, with calculated WCAG contrast, `--json` and
  `--production`; exit 1 on violated MUSTs.
- `scripts/validate_skill.py`: validator for the Agent Skills specification (frontmatter, naming, progressive
  disclosure budget, relative references, execute bits).
- `scripts/build_payload.py`, `scripts/send_mailtrap_sandbox.sh|.ps1`: Mailtrap payload with one-click
  `List-Unsubscribe` and sandbox sending.
- `scripts/screenshot_email.py`: gate G2, 600/375 px views with and without `<style>`.
- `templates/reference-welcome-dark.html`: a compliant template (0 MUST violated).
- `tests/`: unittests for the linter with a fixture that reproduces every historical anti-pattern.
- `evals/eval_queries.json`: 20 queries to test the skill activation.
- GitHub Actions CI on Python 3.10/3.12/3.13.

### Notes
- The exact syntax of the MailUp unsubscribe placeholder has not been verified on the console: rule `R-454`
  asks to confirm it on the account before going to production.
