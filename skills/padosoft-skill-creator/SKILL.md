---
name: padosoft-skill-creator
description: >-
  Use this skill when creating, editing or reviewing an Agent Skill of the padosoft/skills repository,
  when the user wants to turn a recurring workflow, a checklist or a set of guidelines into a reusable
  skill, or when they ask where a skill belongs (profile, scope, package) or why the repo CI is failing on
  catalog, profiles or manifests: it guides the whole creation with scaffolding, the Padosoft conventions
  and the automated checks. Do not use it to write the technical domain content (that is the job of the
  skill you are creating) nor to install existing skills (padosoft-skills-router handles that).
license: MIT
compatibility: >-
  Requires Python 3.10+ (standard library only) and the padosoft/skills repository cloned locally to
  regenerate catalog and profiles. Node.js 18+ only to try the installation with npx skills.
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: core
  scope: global
  repository: https://github.com/padosoft/skills
  keywords: skill, agent skills, scaffolding, SKILL.md, frontmatter, profiles, catalog, CI
---

# Padosoft Skill Creator

Creates skills that follow **the Agent Skills specification** and **the `padosoft/skills` conventions**,
without having to remember them. The expected outcome: `make all` green on the first try, and a skill that
triggers when it is needed, not at random.

---

## 0. What is in this skill

| File | Use |
|---|---|
| `scripts/new_skill.py` | Scaffolding: creates `skills/<name>/` with a filled-in SKILL.md, folders and eval files. `--help` for the options. |
| `templates/SKILL.template.md` | The skeleton used by the scaffolding, if you need to start by hand. |
| `references/checklist.md` | Review checklist before the PR, and the recurring mistakes to avoid. |

The validation scripts **live in the repo**, not here: **scripts/build_catalog.py**, **scripts/validate_plugins.py** and
**skills/padosoft-email-html-builder/scripts/validate_skill.py** (repo paths, not paths of this skill).

---

## 1. Before writing: is the skill really needed?

Answer these three, in order. If any answer is no, stop and say so to the user.

1. **Does the agent get it wrong without these instructions?** If the model already does fine on its own, the
   skill adds context and not quality. Test it: same prompt without the skill, look at the output.
2. **Is the know-how real and verifiable?** Rules born from concrete mistakes, tool reports, reviews, incidents.
   A skill synthesised from generic articles produces generic advice.
3. **Is it one coherent unit?** Neither too narrow (two skills that must load together for a single task),
   nor too broad (one skill covering backend, deploy and monitoring).

The best material: a real session where the work succeeded, together with the corrections the user had to
make. Those corrections become the "gotchas", the most valuable part of the skill.

---

## 2. Workflow

1. **Collect the know-how** from the real source: session transcript, PRs and reviews, runbooks, tool
   reports, incidents. Ask the user for the files, do not reconstruct them from memory.
2. **Decide placement and name** (§3). The name always carries the `padosoft-` prefix.
3. **Scaffolding**:
   ```bash
   python3 skills/padosoft-skill-creator/scripts/new_skill.py laravel-conventions \
     --profiles laravel --scope project --title "Padosoft Laravel conventions"
   ```
   Creates `skills/padosoft-laravel-conventions/` with a pre-filled SKILL.md, `references/`, `scripts/`,
   `evals/queries.json` and the frontmatter already correct.
4. **Write the `description`** (§4): it is the field that decides whether the skill triggers. Spend more time
   on it than on anything else.
5. **Write the body** (§5): numbered workflow, copyable patterns, gotchas, checklist. Under 500 lines.
6. **Move the details into `references/`** and say **when** to read them (for example: "open the API errors
   file in references/ if the tool answers 4xx").
7. **Add a script** only if the agent would redo the same logic every time (§6).
8. **Regenerate and validate**:
   ```bash
   make catalog   # CATALOG.md, profiles.json, the router catalog
   make all       # validate + test + lint
   ```
9. **Add the skill to a package** in `plugins/` (`padosoft-core`, `padosoft-email`, …): if it stays uncovered,
   the repo's validate_plugins.py fails.
10. **Try it in the field**: fresh session, a real task, no hints. Then fix what went wrong and add the fix to
    the gotchas. A single iteration of this kind improves the skill a lot.
11. **CHANGELOG** and PR.

---

## 3. Placement: profile, scope, name

```yaml
metadata:
  profiles: laravel, api    # one or more profiles from KNOWN_PROFILES (scripts/build_catalog.py)
  scope: project            # project | global
```

- **`scope: global`** only if it passes the three-question filter: it is useful on any stack, it is correct
  everywhere, and its absence would be a problem. Global skills live in the `core` profile and a test caps
  them at eight. The strongest evidence for a global skill is **independent convergence**: the same rule
  reached on its own by stacks that share no code. Write it as invariants plus a per-stack table, because the
  principle travels and the mechanism usually does not.
- **`profiles`**: by stack (`laravel`, `node`, `react-native`) or by domain (`email`, `api`, `payments`,
  `data`, `devops`). Multiple profiles only if the skill is genuinely needed in both. Never create a profile
  for a single skill: adding one means changing KNOWN_PROFILES in a PR.
- **Name**: `padosoft-<domain>-<what-it-does>`, lowercase, hyphens, identical to the folder. Descriptive of
  the task, not of the content: `padosoft-laravel-conventions`, not `padosoft-laravel-docs`.

---

## 4. The `description`: the field that matters

It is the only thing the agent reads until the skill triggers. A structure that works:

```
Use this skill when <concrete situations, even without the domain keywords>:
<what it does, in one line>. Do not use it for <boundaries>.
```

Rules:

- **Imperative**, addressed to the agent: "Use this skill when…", not "This skill provides…".
- **List the situations**, including those where the user does not name the domain ("the email breaks on
  Outlook" instead of "HTML email").
- **State the boundaries**: what it does NOT cover. With many skills installed, this is what prevents wrong
  activations.
- At most **1024 characters**; 400-600 are usually enough.

Then write the evals in `evals/`: 8-10 queries that must trigger it and 8-10 that must **not**, picking near
misses as the negatives (same domain, different task). Those are what actually measures quality.

---

## 5. The body: what to put in and what to leave out

**Put in:**

- A numbered workflow, with its gates ("do not deliver until X is green").
- **Copyable** patterns, not described in prose: snippets, commands, output templates.
- **Gotchas**: the facts that contradict reasonable assumptions. They belong in SKILL.md, not in the
  references: the agent has to read them before hitting them.
- An explicit default when several roads exist ("use X; for case Y, Z").
- The format of the final report, as a template.

**Leave out:**

- What the agent already knows (what a JWT is, how HTTP works).
- Lists of equivalent alternatives with no default.
- Every imaginable edge case: over-specification does more damage than under-specification.
- Non-operational company context prose.

Calibration: **prescriptive** where the operation is fragile or the sequence matters ("run exactly this
command"); **permissive** where many valid roads exist, explaining the why instead of the how.

---

## 6. Scripts shipped with the skill

Add them only if the agent would redo the same logic on every run, or if a validator is needed for the
fix-and-check loop. Padosoft requirements:

- **Standard library** only (Python 3.10+), so they run everywhere and in CI.
- **No interactive prompts**: everything through flags or environment variables.
- `--help` with examples, **distinct exit codes** (0 ok, 1 problems, 2 execution error), `--json` if the
  output is meant for CI.
- Error messages that say what to do, not just what went wrong.
- Guard clauses at the top, complete type hints, comments about the why.

Document them in a table at the top of SKILL.md, with the command ready to run.

---

## 7. The repo's automated checks

| Command | What it verifies |
|---|---|
| `make catalog` | Regenerates `CATALOG.md`, `profiles.json` and the catalog inside the router |
| `make validate` | Frontmatter compliant with the spec, catalog aligned, plugin manifests consistent |
| `make test` | Profile and scope declared, brand prefix, cap on global skills, installer in dry-run |
| `make all` | Everything, as in CI |

If build_catalog.py --check fails, almost always a `make catalog` is missing after touching the frontmatter.

---

## 8. Format gotchas (mistakes already made)

- **`name` different from the folder**: the skill is not loaded. They must match, prefix included.
- **Frontmatter with out-of-spec keys**: only `name`, `description`, `license`, `compatibility`, `metadata`
  and `allowed-tools` are allowed. Everything else goes inside `metadata`.
- **References to files that do not exist**: validate_skill.py reports every path of the scripts folder
  quoted in backticks that is missing. If you quote a script of the repo rather than of the skill, do not use
  backticks with a relative path.
- **SKILL.md over 500 lines or 5000 tokens**: move content into `references/` and say when to read it.
- **Skill not included in any `plugins/` package**: invisible to whoever installs from Claude Code.
- **`scope: global` without the `core` profile**: CI blocks it, and rightly so: global skills are counted.
- **A description that talks about the skill instead of the user**: it triggers at random, or never.

---

## 9. Final report

```
Skill: padosoft-<name>  ·  profiles: <…>  ·  scope: <…>  ·  version: 0.1.0
Know-how source: <session/PR/runbook/report>
make all: PASS (validate, N tests, lint)
Package: plugins/<package>
Evals: <n> queries (<p> positive, <n> negative) — correct activations <x>/<y>
Field test: <real task performed, iterations, fixes added to the gotchas>
To decide/verify: <…>
```
