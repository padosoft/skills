# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versioning follows
[SemVer](https://semver.org/): *major* when a new MUST rule can invalidate existing templates.

## [1.7.0] - 2026-09-20

### Added

- **A provenance gate, and it is mandatory.** `padosoft-skill-creator` gains §2 — *provenance is input,
  never output* — plus `scripts/check_provenance.py`, which fails on the shapes that can only come from a
  real event: a calendar date, an address, a credential, a private host or IP, a personal or fiscal
  identifier, a long row/order id, an absolute path from somebody's machine, narration ("our client
  reported"), and any term on a project denylist. `make privacy` runs it over every skill; CI runs it before
  anything else; `tests/fixtures/provenance-leak.md` proves it can go red, one line per rule.

  The reasoning: a rule in a document is advice to whichever agent happens to read it. A rule that must hold
  for every contributor, under any agent, has to be a check that fails. The scanner matches *shapes* rather
  than topics, so it does not cry wolf on a skill that legitimately discusses security — and `--topic-ok`
  exists for one that is genuinely about incident response.

  **The denylist is deliberately not in the repository.** It names the customers, brands and people it
  protects, so committing it publishes exactly what it defends. It lives outside the tree
  (`PROVENANCE_DENYLIST`), and in CI it is written from a secret.

- **`padosoft-evidence-boundaries`** (`core`, **global**) — *name the claim, then name what would prove it.*
  Almost every false "done" has one shape: a claim about the expensive thing, and a **cheaper artifact**
  accepted as proof of it. The artifact is real and honestly produced; it just does not demonstrate the
  claim. A green run against an emulator proves the request shape, not the provider's key identity or
  retention. A static topology check proves the transitions are *declared*, not that anything reached them.
  An accepted write request proves the option was transmitted, not applied. A signature on a manifest does
  not cover what the manifest points at. A successful dump is not a restore. And a skipped optional check
  proves less than nothing, because it is the only one that looks exactly like success.

  Six questions turn an artifact into evidence (who produced it, what it is bound to, is it re-verified at
  read time, what is the boundary of the claim, does it fail closed, could all of it be true and the system
  still be broken), plus the rule that merging a cheap gate with an expensive one does not average their
  strength — the weaker one becomes the verdict. `references/rules.md` carries the substitutions by domain:
  storage and encryption, identity and access, telemetry, queues and effects, supply chain, money, data
  protection.

  Promoted global on the spot: this is the single most repeated lesson in a large QA-framework ledger —
  roughly one entry in five — and it converges with `padosoft-test-integrity` ("a test that cannot fail"),
  `padosoft-ci-workflow-gates` ("a gate that cannot fail") and `padosoft-docs-match-code`. Four independent
  sources, same defect class at four different altitudes.

### Changed

- **`padosoft-logging-discipline`** — a fourth independent source, and two new sections. **The redactor is
  software and has its own defects**: one too eager destroys the evidence (a rule keyed on the word "token"
  turns a numeric usage counter into `[REDACTED]`; a "13 to 19 digits" card rule rewrites timestamped
  identifiers), one too narrow leaks — and a redaction pass that can mutate a correlation id or an audit
  hash breaks the chain it exists to protect. **The log is not the only way data gets out**: sanitising the
  logger and stopping there leaves the API's own error response as an independent disclosure path, carrying
  connection strings, tokens and identifiers from the row that failed. Metrics labels are an outbound
  boundary too, and telemetry is never the source of truth.

### Fixed

- The gate found real provenance on its first run: a live sandbox inbox id in a published example, and three
  addresses on a domain that is not reserved for documentation. Replaced with placeholders and `example.com`.

## [1.6.0] - 2026-09-20

### Added

Two skills and three extensions, from the durable lessons file of a governance-heavy project — roughly sixty
entries, each recorded only after the fix and the regression that prevents it. The domains that came out of
it: automated review loops, CI gates, gate validators, negative fixtures, cross-platform scripting, and how
a state file rots.

- `padosoft-ci-workflow-gates` (`devops`) — **a gate that cannot fail is not a gate**. A manifest that omits
  its own workflow stays green after half the contract is deleted; a security scan that *skips* what it
  cannot process is decoration; a detector as strict as its parser cannot see the malformed input it exists
  to catch. Plus the trigger semantics that silently replace your defaults (declaring `pull_request.types`
  drops the rest; a label-gated job is inert if the trigger does not subscribe to the label event; a required
  check cannot run on a merge commit that does not exist yet), inspecting annotations and not only
  conclusions, fast/extended cost tiers, and the edges rulesets leave open.
- `padosoft-cross-platform-scripting` (`devops`) — the ways a Windows workstation and a Linux runner disagree
  **silently**: an exit-code variable that persists from a handled failure, parsing a tool's human error
  renderer, display-form path listings that make a file unreachable so the scanner reports clean, case
  semantics that belong to the filesystem, hidden files needing an explicit flag, and an interpreter that
  exists but cannot run the syntax.

### Changed

- `padosoft-pr-review-triage` — how to know a bot reviewer is actually done: a request event is not a review,
  a submitted review can contain no analysis, "no new comments" can still list suppressed actionable
  findings, and the thread query has to be paginated to exhaustion or it silently returns one page.
- `padosoft-test-integrity` — **a negative fixture is only valid if it fails for the named reason**. Observe
  the expected red and read the message; bound fixture mutations; compare expected diagnostics literally
  rather than by regex. Fourth independent source for this skill.
- `padosoft-docs-match-code` — state files rot by time rather than by drift: write memory as a dated
  historical observation, record the state *after* the action, keep it collaborator- and machine-neutral.

## [1.5.0] - 2026-09-20

### Removed — no incident or customer provenance in a public catalog

The catalog is public and indexed in the Agent Skills directory, so it must not carry anything that
identifies a customer, a person or an incident that actually happened. An incident narrative tells a reader
which weakness a company really had; a customer name in an example template publishes a commercial
relationship.

Removed from skills, references, the changelog and the four GitHub release notes: a customer brand in the
reference email template and its sources line, a verbatim error message with table, column, row id and
personal-data placeholders, the account of a credential incident, a person's initials and a date in an
example comment, the reference to a specific audit and its outcome, and every first-person attribution
phrase that framed a rule as something that befell us.

**Not one rule, severity or pre-screen was removed.** Only the framing changed, from "this happened to us" to
"this is the shape of the defect" — and it usually reads better, because it describes the class instead of
the anecdote. The error-leak rule, for instance, now explains *why* that message carries host, schema and
written values, which is what lets someone recognise it on a different project.

### Added

- `padosoft-admin-interface` (`laravel`) — the back-office pattern: the server pipeline
  (enum → DTO → request → query service → metrics service → controller → route → export), the data contract
  that passes endpoints and caps from the server instead of hardcoding them in the client, the client module
  split, and **the four states** — initial, loading, success, error — of which a missing one is a broken
  screen. Drawn from an admin-interface family used across several products and expressed for a React client
  over a Laravel API.
- `padosoft-atomic-invariants` (`core`, **global**) — either the invariant is recorded in the same atomic
  step that checked it, or it does not exist. Check-then-act, locks released before the write, conditional
  updates whose row count is discarded, and when a unique constraint has to back the rule. Reached
  independently on two stacks, which is what earned the promotion.
- `padosoft-docs-match-code` (`core`, **global**) — every fact quoted from the code (column, env var,
  command flag, route, path) verified against the code before merging, generators and pointers preferred to
  copies, and agent instruction files treated as documentation with a shorter fuse: when one goes stale the
  agent follows it confidently, which is worse than having none.

### Changed

- **The cap on global skills is gone.** It was five, then eight, and then it started arguing against
  evidence. The rule that replaces it is **independent convergence**: when stacks that share no code reach
  the same rule on their own, it is promoted whatever the count. What CI still enforces is structural — a
  global skill is in `core`, and its description states its boundaries, because a description loaded in every
  session that never says what it is *not* for is what produces wrong activations.
- **The Laravel skills are no longer tied to a framework or language version.** They said "Laravel 13+ /
  PHP 8.5+ baseline"; they now say what they always meant: these are rules about how an application is
  shaped, earned on codebases several major versions apart. A rule that only held on one version would not
  be a rule, it would be a release note. Where a version genuinely moved something — the exception handler,
  middleware registration — what moved was the *file*, and the text says so.
- `scripts/new_skill.py` scaffolds `references/rules.md` instead of a stub named after the skill, which had
  twice been committed empty beside the real one.

## [1.4.0] - 2026-09-20

### Added

Five skills from seven Laravel repositories. The catalog goes from 12 to 17 skills on 7 profiles, and the
`core` profile gains two globals.

**Laravel stack** (`laravel` profile, new marketplace package `padosoft-laravel`). Baseline **Laravel 13+ /
PHP 8.5+** for new work, with the Laravel 10-12 differences called out inline, because the oldest repository
in the group is still on 12.

- `padosoft-laravel-conventions` — FormRequest -> DTO -> Service -> Resource, jobs that orchestrate while
  services implement, Eloquent and query work, migrations, and the asymmetry that costs most: **model events
  do not fire on query-builder mass operations**, so a rule enforced in an observer silently does not apply
  to the bulk path.
- `padosoft-laravel-security-review` — the third sibling of the API and mobile ones: ten checks with
  pre-screens (mass assignment, unescaped Blade, raw SQL, uploads, CSRF, command injection, open redirect,
  hardcoded secrets, IDOR, unsafe deserialisation), plus ownership scoping, append-only audit trails, the
  "the invariant is recorded or it does not exist" rule for single-use checks, and `SEC-ERRLEAK-001`.
- `padosoft-laravel-scaffolding` — the wiring a new endpoint, service, CRUD or job needs. The three steps
  that fail silently: a route outside the right group keeps answering without the group's middleware, a
  policy that is never `authorize()`d is not a control, and a job dispatched to a queue with no worker
  returns 202 forever.

**Two new global skills**, and the cap was raised from five to eight to take them.

- `padosoft-failure-visibility` — the two halves of one bug, the caller cannot tell success from failure: an
  ignored return value, and a success status served over a failure. The shape it takes: a controller calls
  `Storage::put` without checking the return, the disk is configured not to throw, a full disk returns
  `false`, the controller answers **202 Accepted**, and the job that comes later dies on a missing file —
  ingestion silently drops documents.
- `padosoft-test-integrity` — the ways a test passes without testing anything: a name promising a transition
  with a body that never performs it, an ordering assertion with `toBeGreaterThanOrEqual` that passes under
  either order, global state mutated and never restored (which is where "flaky, it's CI" comes from), a
  failure-path test that stubs the error and never triggers it.

Both were extracted from skills that were already cross-stack in the source, with PHP and TSX examples in the
same file, and both were born from findings on real pull requests.

### Changed
- The global cap moved from 5 to 8, in `tests/test_catalog.py` and in CONTRIBUTING, with the reason written
  next to the number: when three stacks that share no code reach the same rule on their own, the alternative
  to one global skill is the same content copied into every stack skill, free to diverge. It stays a forcing
  function — raising it again is a deliberate decision in a PR, like adding a profile.
- `padosoft-skill-creator` now names **independent convergence** as the strongest evidence for a global
  skill, and says to write one as invariants plus a per-stack table, because the principle travels and the
  mechanism usually does not.

### Note on what was left out
The seven repositories carry far more than this: an admin-interface family, Playwright end-to-end tooling,
branching and release conventions, and AI-surface rules. They were left for a later pass, either because they
are tied to one product's tooling or because they overlap with skills the catalog already has.

## [1.3.0] - 2026-09-19

### Added

Four skills extracted from two production React Native apps and, for the logging one, from a Laravel monolith
as well. The catalog goes from 8 to 12 skills on 6 profiles.

- `padosoft-react-native-conventions` (`react-native`) — the conventions and recurring mistakes distilled from
  the code-review history of two apps. The filter was mechanical: of 139 and 101 numbered rules, **90 were
  textually identical in both repositories**, and those are the ones promoted. They now carry stable
  `RN-AREA-NNN` ids, because the source numbering had drifted — `#96` and `#100` named completely different
  rules in the two apps, so a citation across repos was ambiguous.
- `padosoft-mobile-security-review` (`react-native`) — the eight `MOBILE-SEC-*` rules, sibling of the API one:
  the bundle is decompilable and `EXPO_PUBLIC_*` is inlined at build time, tokens in the system enclave and
  never in plain application storage, WebView hardening, deep-link validation, TLS and pinning, dev gates on
  the build-time flag, and the AI/LLM surface written before there is one. Includes the discipline of stating
  a severity **conditionally** when the enforcement lives outside the repository.
- `padosoft-rn-screen-scaffolding` (`react-native`) — every file a new screen, component or query hook has to
  touch. What breaks is never the code, it is the registration: i18n keys, namespace, barrels and the route
  file in *every* app of the monorepo, each of which fails silently.
- `padosoft-logging-discipline` (`core`, **global**, fourth of five) — see below.
- Marketplace package `padosoft-react-native`.

### Changed
- `padosoft-api-security-review` now defers to `padosoft-logging-discipline` for the logging invariants
  instead of restating them, keeping only what is specific to an HTTP API.

### The logging skill, and why it is global

Three codebases that share no code — a Bun/Hono API, a React Native app and a Laravel monolith — arrived
independently at the same rules. The core finding is one bug, three times:

| Stack | The object | What it carried | Where it went |
|---|---|---|---|
| Node + mysql2 | `err.sql` | the query already formatted, bound values substituted | into the logs: the hash of an auth token |
| Laravel + PDO | `QueryException::getMessage()` | SQLSTATE, production DB host, database name, the full INSERT | onto the **user's screen**, with their personal data |
| React Native | a raw `Error` | message and stack | into the logs, every crash collapsed into one issue |

The skill states the invariants — a driver exception is not a loggable object; keep the diagnosis and drop the
data; nothing ad hoc on stdout; detail at `debug`; a safety net must report when it fires; in local you are
not seeing production — and then gives the mechanism **per stack**, because it is not the same place: at the
call site in Node and React Native, centrally in a Monolog processor plus `#[\SensitiveParameter]` in
Laravel. Porting one onto the other either edits a hundred call sites a processor already covers, or waits for
a pipeline that does not exist.

The Laravel material also improved the API skill's formulation: log the **parameterised** SQL and describe the
bindings as type and length — the length is what tells you which validation limit is missing, the value never
is.

## [1.2.0] - 2026-09-19

### Added
- `padosoft-git-commit-integrity` (`core`, **global**) — what git actually recorded, as opposed to what you
  changed. Two failures, both invisible on the machine that made the commit: files missing because `git add -A`
  skips ignored paths in silence (the shape: a generic `logs/` pattern swallows a source directory that
  happens to be called `logs/`, with build and tests green locally), and files whose stored line endings are
  those of whoever committed them. The fixes that are not obvious: a negation in `.gitignore` rather than `git add -f`, which
  leaves the trap armed for the next file; and `git add --renormalize .` after adding a `.gitattributes`,
  without which the already-committed blobs stay as they were while everyone assumes they are protected.
  Third global skill, on a cap of five.

## [1.1.0] - 2026-09-19

### Added
- **Four skills extracted from two production projects** (a Bun/Hono API and its spec-first OpenAPI
  repository), generalised and translated to English. The know-how comes from a 2026-07 security audit, the
  findings of hardening work, not from generic checklists.
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
