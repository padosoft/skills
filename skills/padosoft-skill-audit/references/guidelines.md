# Skill authoring guidelines for the current Claude models

The rulebook `padosoft-skill-audit` checks skills against, and the reference to write new ones by. It
condenses Anthropic's official guidance for the current model generation (Opus, Sonnet, Haiku and Fable),
the Agent Skills open standard, and the Claude Code skills reference, with the source of every rule.

## Contents

1. [How to read this document](#1-how-to-read-this-document)
2. [What changed with the current models](#2-what-changed-with-the-current-models) — `G-GEN`
3. [Frontmatter](#3-frontmatter) — `G-FM`
4. [The description is the trigger](#4-the-description-is-the-trigger) — `G-DESC`
5. [The body](#5-the-body) — `G-BODY`
6. [Degrees of freedom](#6-degrees-of-freedom) — `G-FREE`
7. [Structure and progressive disclosure](#7-structure-and-progressive-disclosure) — `G-STRUCT`
8. [Workflows, checklists and feedback loops](#8-workflows-checklists-and-feedback-loops) — `G-FLOW`
9. [Scripts](#9-scripts) — `G-SCRIPT`
10. [Dependencies and portability](#10-dependencies-and-portability) — `G-PORT`
11. [Invocation and safety](#11-invocation-and-safety) — `G-SAFE`
12. [One skill, many models](#12-one-skill-many-models) — `G-MODEL`
13. [The collection as a whole](#13-the-collection-as-a-whole) — `G-LIB`
14. [Evaluation and iteration](#14-evaluation-and-iteration) — `G-EVAL`
15. [Keeping these rules current](#15-keeping-these-rules-current) — `G-FRESH`
16. [Anti-patterns at a glance](#16-anti-patterns-at-a-glance)
17. [Old patterns](#17-old-patterns)
18. [Common claims, checked](#18-common-claims-checked)
19. [Final checklist](#19-final-checklist)
20. [Sources](#20-sources)

---

## 1. How to read this document

Every rule has a stable ID (`G-AREA-NN`), a level and its source:

- **required** — breaking it makes the skill fail to load, fail to upload, trigger badly, or get refused.
- **recommended** — the default; deviate only with a reason you can state.
- **optional** — worth doing when the situation calls for it.

Source keys in square brackets (`[BP]`, `[CC]`…) are expanded in [§20](#20-sources). IDs are never recycled:
a retired rule moves to [§17](#17-old-patterns) with the reason. `scripts/audit_skills.py` reports findings
with these same IDs, and `references/sources.json` maps each official page to the rules that depend on it,
so a change upstream points straight at the rules to re-check ([§15](#15-keeping-these-rules-current)).

The single most important idea: **a skill adds what the model does not already know, at the level of
control the step needs, and nothing else.** Most of the rules below are consequences of it.

---

## 2. What changed with the current models

The newest models follow instructions closely and reason well without help. Skills written to push older
models harder now push these ones too far.

- **G-GEN-01** (required) — **Write less, not more.** Skills developed for earlier models are often too
  prescriptive for the current ones and can degrade output quality: review them and remove instructions the
  model already follows by default, but test before deleting (§14). `[FABLE5]` `[SC]`
- **G-GEN-02** (required) — **No aggressive emphasis.** `CRITICAL: You MUST use this tool when…` makes the
  current models overtrigger; `Use this tool when…` is enough. A sentence in capitals is a yellow flag: either
  the reason is missing (G-GEN-03) or the rule is a hard invariant that belongs in a hook or a script
  (G-FREE-02), not in louder text. `[PROMPT]` `[SC]`
- **G-GEN-03** (recommended) — **Give the reason with the rule.** "Your output is read aloud by a
  text-to-speech engine, so never use ellipses" beats "NEVER use ellipses": the model generalises from the
  why to cases the rule did not list. `[PROMPT]` `[AS-EVAL]`
- **G-GEN-04** (recommended) — **Say what to do, not only what to avoid.** Positive instructions steer
  better than prohibitions ("write flowing paragraphs" rather than "do not use markdown"). `[PROMPT]`
- **G-GEN-05** (required) — **Never ask the model to write out its reasoning in the response.** Prompts,
  skills and tool descriptions that ask the model to echo, transcribe or show its internal reasoning (for
  example "show your step-by-step thinking", "write your reasoning in `<thinking>` tags") can be declined
  with the `reasoning_extraction` refusal on the current Opus and Fable models. Ask for a short explanation
  of the answer or a summary of the actions taken instead. `[OPUS5]` `[OPUS55]` `[FABLE5]`
- **G-GEN-06** (recommended) — **Do not script the thinking.** "Prefer general instructions over
  prescriptive steps": a hand-written reasoning recipe usually reasons worse than the model does on its own.
  Thinking depth is set by the effort level, not by "think carefully before answering". In Claude Code a
  skill that needs depth can say `ultrathink` or set `effort` (G-FM-04). `[PROMPT]` `[CC]`
- **G-GEN-07** (required) — **Verification: objective checks yes, generic re-checks no.** A workflow step
  that runs a validator, a test suite or a build stays (G-FLOW-04). Meta-instructions such as "double-check
  your answer", "re-verify before responding", "use a subagent to verify" cause over-verification on the
  current Opus models, which already check their own work; remove them. Where a smaller model or a low
  effort level skips checks, add the stronger wording only for that case (§12). `[OPUS5]` `[OPUS55]`
  `[SONNET55]` `[HAIKU55]`
- **G-GEN-08** (recommended) — **State the scope and the done condition.** The current models can add
  unrequested tests, docs or refactors, or widen a task. For a narrow task skill, say what the deliverable
  is and when to stop ("when the work asked for is done and checked, stop and report; mention extra ideas at
  the end instead of doing them"). `[OPUS5]` `[SONNET55]` `[FABLE5]`
- **G-GEN-09** (recommended) — **Do not push delegation.** The current models delegate to subagents
  readily. A skill should not ask for subagents on small or verification work; if delegation is part of the
  method, say when it is warranted (independent, sizeable, parallel tracks). `[OPUS5]` `[PROMPT]`
- **G-GEN-10** (optional) — **Calibrate written deliverables.** Documents the model writes to disk tend to
  run long; for skills that produce reports, ask to "cover the substance without filler sections or
  redundant summaries". `[OPUS5]`
- **G-GEN-11** (recommended) — **Do not fight the harness.** Remove instructions that duplicate what the
  harness already does or that talk about the context budget ("you are running out of context, wrap up"):
  they cause early stops. `[PROMPT]` `[FABLE5]`
- **G-GEN-12** (recommended) — **Review skills ask for coverage, not restraint.** "Only report high-severity
  issues", "be conservative", "don't nitpick" are now followed literally: the model finds the bug and then
  does not report it. Ask for every finding with its confidence and severity and filter in a later step, or
  state a concrete bar ("report anything that could cause incorrect behaviour or a failing test; omit pure
  style"). `[OPUS5]` `[SONNET5]`

---

## 3. Frontmatter

- **G-FM-01** (required) — The file is named exactly `SKILL.md` and starts with `---` on line 1, followed by
  valid YAML. If the YAML does not parse, Claude Code loads the body with no fields: the `/name` command
  still works, but the description is gone and the skill never triggers on its own. `[CC]` `[GUIDE]`
- **G-FM-02** (required) — `name`: 1-64 characters, lowercase letters, digits and hyphens, no leading,
  trailing or double hyphen, identical to the folder name, no XML, and not containing the reserved words
  `anthropic` or `claude`. `[BP]` `[AS-SPEC]`
- **G-FM-03** (required for shared skills) — **Portable fields** are `name`, `description`, `license`,
  `compatibility` (≤ 500 characters), `metadata` (string-to-string map) and `allowed-tools`. Uploads to
  claude.ai and the Skills API reject any other key with a hard error; other agents ignore them. A skill
  shared across agents or surfaces keeps to these and puts anything else under `metadata`. `[CC]`
  `[AS-SPEC]`
- **G-FM-04** (recommended) — **Claude Code-only fields**, for skills that live only in Claude Code. Use
  them deliberately:

  | Field | Use it for |
  |---|---|
  | `when_to_use` | extra trigger context, appended to the description (shares its 1,536-character cap) |
  | `argument-hint`, `arguments` | autocomplete hint; named positional arguments for `$name` |
  | `disable-model-invocation: true` | manual-only skills with side effects (deploy, send, commit); also removes the description from context |
  | `user-invocable: false` | background knowledge the model loads but nobody types as a command |
  | `allowed-tools` | tools usable **without a prompt** for the invoking turn; it grants, it does not restrict |
  | `disallowed-tools` | tools removed while the skill is active |
  | `model`, `effort` | pin a model or effort level for the turn (G-MODEL-03) |
  | `context: fork`, `agent`, `background` | run as a forked subagent; only for skills with an explicit task (G-SAFE-03) |
  | `hooks` | hooks registered when the skill is invoked, kept for the session (G-FREE-02) |
  | `paths` | glob patterns: auto-load only when matching files are involved |
  | `shell` | `bash` or `powershell` for the `` !`cmd` `` blocks |

  `[CC]`
- **G-FM-05** (recommended) — No `README.md` inside the skill folder: documentation goes in `SKILL.md` or
  `references/`. A repository-level README for humans is fine. `[GUIDE]`
- **G-FM-06** (optional) — Record what the skill was tested on in `compatibility`, for example "Tested on
  the current Claude Opus, Sonnet and Haiku; Haiku reads references/models/haiku.md". `[AS-SPEC]`
  `[GUIDE]`

---

## 4. The description is the trigger

Until the skill loads, the description is the only thing the model reads about it.

- **G-DESC-01** (required) — **What it does and when to use it, key use case first.** Maximum 1,024
  characters by the specification; Claude Code truncates `description` + `when_to_use` at 1,536 in the
  listing. A few sentences, roughly 400-600 characters, are usually right. `[BP]` `[CC]` `[AS-SPEC]`
- **G-DESC-02** (required) — **Point of view.** Third person for what it does ("Extracts tables from PDF
  files…") or an imperative addressed to the agent ("Use this skill when…"). Never first or second person
  ("I can help you…", "You can use this to…"): the description is injected into the system prompt, and a
  shifting point of view hurts discovery. `[BP]` `[AS-DESC]`
- **G-DESC-03** (recommended) — **The user's intent, in the user's words.** List the situations, including
  the ones where the user never names the domain ("the email breaks in Outlook" rather than "HTML email").
  Use the language your users actually write in; if the team asks in Italian, Italian trigger terms belong
  in the description. `[AS-DESC]` `[GUIDE]`
- **G-DESC-04** (recommended) — **A little pushy, never shouting.** Models tend to undertrigger skills, so
  name the contexts explicitly ("…even if they don't mention CSV"), without capitals or MUST (G-GEN-02).
  `[SC]` `[AS-DESC]`
- **G-DESC-05** (required for collections) — **State the boundaries.** Say what the skill does not cover
  and name the sibling skill that does ("Do not use it for X — that is `other-skill`"). With many skills
  installed, the negative trigger is what prevents wrong activations. `[GUIDE]` `[AS-DESC]`
- **G-DESC-06** (recommended) — **No keyword soup, no overfitting.** Do not append the words of every query
  that failed to trigger: describe the category they belong to. A short `Trigger "…", "…"` tail after real
  sentences is acceptable; a description made only of keywords is not. `[AS-DESC]`
- **G-DESC-07** (required) — No XML angle brackets in `name` or `description` (they end up in the system
  prompt). `[BP]` `[GUIDE]`
- **G-DESC-08** (recommended) — **Every description costs context on every turn.** Claude Code gives the
  listing about 1% of the context window and drops the descriptions of the least-used skills first when it
  overflows. Manual-only skills with `disable-model-invocation: true` do not occupy the listing at all.
  `[CC]`

---

## 5. The body

- **G-BODY-01** (required) — **Only what the model lacks.** Project facts, conventions, non-obvious edge
  cases, the specific tool or API to use. Not what a PDF is or how HTTP works. For every paragraph ask:
  *would the agent get this wrong without it?* If not, cut it; if unsure, test it. `[BP]` `[AS-BP]`
- **G-BODY-02** (required) — **The most important instructions go first.** After a compaction Claude Code
  re-attaches only the first 5,000 tokens of each invoked skill, within a combined 25,000 tokens filled from
  the most recently invoked: what sits at the bottom of a long skill can disappear. `[CC]`
- **G-BODY-03** (recommended) — **Standing instructions.** The skill content is loaded once and not re-read
  on later turns, so guidance that applies to the whole task is phrased for the whole task ("run the tests
  after every edit", not "run the tests"). `[CC]`
- **G-BODY-04** (recommended) — **A gotchas section in `SKILL.md`.** The most valuable content of most
  skills: concrete facts that contradict a reasonable assumption ("the `/health` endpoint returns 200 even
  when the database is down; use `/ready`"). Every correction you had to make by hand becomes a gotcha. Keep
  them in `SKILL.md`, where the agent reads them before it meets the situation. `[AS-BP]`
- **G-BODY-05** (recommended) — **Defaults, not menus.** One default plus an escape hatch ("use pdfplumber;
  for scanned PDFs, pdf2image with pytesseract"), never a list of equal alternatives. `[BP]` `[AS-BP]`
- **G-BODY-06** (recommended) — **Procedures, not answers.** Teach how to approach a class of problems,
  not the answer to one instance. Specific details (templates, constraints, tool names) are fine inside a
  method that generalises. `[AS-BP]`
- **G-BODY-07** (recommended) — **One term per concept**, throughout the skill and its references. `[BP]`
- **G-BODY-08** (recommended) — **Examples where style or format matters**: two or three concrete
  input/output pairs, diverse enough not to teach an accidental pattern, wrapped in `<example>` tags when
  they sit among instructions. `[BP]` `[PROMPT]`
- **G-BODY-09** (recommended) — **Templates say how strict they are**: "use exactly this structure" for
  machine-read output, "a sensible default, adapt as needed" otherwise. `[BP]`
- **G-BODY-10** (required) — **No time-sensitive information.** "Before version X, do Y" rots. Keep the
  current method in the body and the legacy one under an *Old patterns* heading. `[BP]`
- **G-BODY-11** (recommended) — **One rule, one place.** Repeating a rule in five places "to be safe" is
  the old emphasis habit (§17) and makes later edits diverge. Within a skill and across skills. `[AS-BP]`
- **G-BODY-12** (recommended) — **Composable.** Do not assume the skill is the only one loaded; do not
  restate other skills' rules or override general behaviour without saying so. `[GUIDE]`
- **G-BODY-13** (recommended) — **Say how far an instruction reaches.** The current models, Sonnet in
  particular at lower effort, follow instructions literally and do not silently extend a rule from one item
  to the next: "apply this to every section, not just the first one". `[SONNET5]`

---

## 6. Degrees of freedom

- **G-FREE-01** (required) — **Calibrate every step on its own.** Ask: *if the model did this step
  differently, what would happen?*

  | Answer | Freedom | Form |
  |---|---|---|
  | nothing bad, many valid ways | high | goal and criteria, explained with the why |
  | quality varies, a preferred pattern exists | medium | a template or pseudocode with parameters |
  | money, data, customers or something irreversible is at stake | low | an exact command or script: "run exactly this" |

  Most skills mix the three; a skill that is uniformly rigid loses quality where judgment helps, and one
  that is uniformly loose fails where it cannot afford to. `[BP]` `[AS-BP]`
- **G-FREE-02** (required) — **Hard invariants are not text.** A rule that must hold every time goes into
  a hook (in Claude Code, the skill's `hooks` field or the settings), a permission rule, or a script gate.
  Text, even in capitals, is followed almost always, not always; a hook runs on every event. `[CC]`
- **G-FREE-03** (recommended) — **Side effects are manual.** Deploying, sending, publishing, committing or
  paying: manual invocation (`disable-model-invocation: true` in Claude Code) and an explicit confirmation
  step in the workflow. `[CC]`
- **G-FREE-04** (recommended) — **Deterministic work is a script.** Calculations, validations, format
  conversions: a tested script is more reliable than generated code and costs no context to run. `[BP]`
  `[GUIDE]`

---

## 7. Structure and progressive disclosure

- **G-STRUCT-01** (required) — `SKILL.md` under 500 lines and roughly 5,000 tokens. Past that, move
  detail into `references/`. `[BP]` `[AS-SPEC]`
- **G-STRUCT-02** (required) — **References one level deep.** Every bundled file is linked directly from
  `SKILL.md`; a reference that sends to another reference gets read partially, often with a `head`-style
  preview. `[BP]`
- **G-STRUCT-03** (required) — **A table of contents at the top of any file over 100 lines**, so a partial
  read still shows the full scope and the agent can jump to the right section. `[BP]` Its links must land:
  an anchor is the heading lowercased, punctuation dropped, underscores and hyphens kept, a repeated heading
  numbered `-1`, `-2`; the audit reports a link to a heading that is not there.
- **G-STRUCT-04** (recommended) — **Say when to read each file**: "read `references/api-errors.md` if the
  API returns a 4xx" is useful, "see references/ for details" is not. `[AS-BP]` `[SC]`
- **G-STRUCT-05** (recommended) — Organise by domain or variant (`references/finance.md`,
  `references/sales.md`), with descriptive file names, in the conventional folders `scripts/`,
  `references/`, `assets/`. `[BP]` `[AS-SPEC]`
- **G-STRUCT-06** (required) — **Forward slashes, relative to the skill root.** Backslash paths break on
  Unix. In Claude Code, `${CLAUDE_SKILL_DIR}` resolves the skill's folder for bundled scripts. `[BP]` `[CC]`
- **G-STRUCT-07** (recommended) — **Execute or read: say which.** "Run `scripts/analyze.py`" versus "see
  `scripts/analyze.py` for the algorithm". Executed scripts cost only their output. `[BP]`
- **G-STRUCT-08** (required) — **No dead links, no orphans.** Every referenced file exists; every bundled
  file is reachable from `SKILL.md` or deleted. `[BP]`
- **G-STRUCT-09** (recommended) — **One source of truth for mirrored skills.** When a skill is shared with
  another agent (for example kept in `.agents/skills` and exposed in `.claude/skills`), prefer a symlink or
  a single canonical file. A stub that says "read the other SKILL.md in full" adds a reference level and its
  description drifts from the original. `[BP]` `[CC]`

---

## 8. Workflows, checklists and feedback loops

- **G-FLOW-01** (recommended) — **Number the steps only where order or completeness matters**; elsewhere
  state the goal and let the model choose the route (G-FREE-01). `[PROMPT]` `[BP]`
- **G-FLOW-02** (recommended) — **A copyable checklist for long, multi-step work**, which the agent copies
  into its reply and ticks as it goes. `[BP]`
- **G-FLOW-03** (required for checklists) — **Every check says where to go back.** "If validation fails,
  return to step 2", plus what *done* means for the step. A checklist without the way back gets ticked
  anyway. `[BP]`
- **G-FLOW-04** (recommended) — **A feedback loop with an objective yardstick**: run the validator, fix,
  repeat until it passes. The yardstick can be a script, the test suite, a build, or a reference document
  (a style guide, a checklist) the agent compares its work against. `[BP]` `[AS-BP]`
- **G-FLOW-05** (recommended) — **Plan, validate, execute** for batch, destructive or high-stakes work:
  write the plan to an intermediate file, validate it with a script against the source of truth, only then
  apply it. `[BP]` `[AS-BP]`
- **G-FLOW-06** (recommended) — **Ground every progress claim** in a tool result from the session; say
  plainly what was not verified. `[FABLE5]`
- **G-FLOW-07** (optional) — **Conditional workflows** route at decision points ("creating a new document
  → creation workflow; editing → editing workflow"); a large branch moves to its own reference file. `[BP]`
- **G-FLOW-08** (optional) — **The skill improves with a human gate.** When a run fails for a reason that
  will recur, the skill proposes the new gotcha or rule; a person approves it before it is added. `[AS-BP]`
  `[GUIDE]`
- **G-FLOW-09** (recommended) — **Run every command a skill quotes, once, in a read-only form, before it
  ships.** A command written from memory, or adapted from another tool, can look right and fail at the first
  real use: a field the tool's structured output does not have, a flag that belongs to another subcommand, a
  filter written for an array applied to an object. The agent is then sent down a path that quietly returns
  nothing, or one that does the opposite of its heading (an approval under "read the suggestion"). Compare
  the real output with the fields the next step reads. `[BP]`

---

## 9. Scripts

- **G-SCRIPT-01** (required) — **Solve, don't punt**: handle the error conditions in the script instead of
  failing and leaving the model to guess. `[BP]`
- **G-SCRIPT-02** (recommended) — **No unexplained constants**: every timeout, limit and retry count says
  why it has that value. `[BP]`
- **G-SCRIPT-03** (required) — **Non-interactive**: input through flags, environment variables or stdin.
  An agent shell cannot answer a prompt; the script hangs. `[AS-SCRIPTS]`
- **G-SCRIPT-04** (recommended) — `--help` with a description, the flags and examples; it is how the agent
  learns the interface. `[AS-SCRIPTS]`
- **G-SCRIPT-05** (recommended) — **Structured output on stdout** (JSON, CSV), diagnostics on stderr, and
  a predictable size: summarise by default, offer `--offset` or `--output` for more. Harnesses truncate long
  tool output. `[AS-SCRIPTS]`
- **G-SCRIPT-06** (recommended) — **Errors that let the agent fix the call**: what was wrong, what was
  expected, what to try ("Field 'signature_date' not found. Available: customer_name, order_total").
  `[AS-SCRIPTS]` `[BP]`
- **G-SCRIPT-07** (recommended) — **Idempotent, with safe defaults**: "create if missing" rather than
  "fail on duplicate", `--dry-run` for anything that changes state, explicit `--force` for destructive
  operations, distinct and documented exit codes. `[AS-SCRIPTS]`
- **G-SCRIPT-08** (required) — **Dependencies declared**: the standard library when possible; otherwise
  inline metadata (PEP 723 for Python, pinned versions) or an install command in `SKILL.md`. `[BP]`
  `[AS-SCRIPTS]`
- **G-SCRIPT-09** (recommended) — **Bundle the repeated work**: if every run reinvents the same helper,
  write it once in `scripts/` and tell the skill to use it. `[SC]` `[AS-BP]`

---

## 10. Dependencies and portability

Think of who will run the skill: a colleague, a customer, a CI runner, another agent.

- **G-PORT-01** (required) — **A requirements section** with each package and the command that installs
  it, and the `compatibility` field for runtime requirements ("Requires Python 3.10+ and git"). `[BP]`
  `[AS-SPEC]`
- **G-PORT-02** (required) — **No paths that exist only on the author's machine.** Repository-relative
  paths, or `~/` when the home directory genuinely matters. `[BP]`
- **G-PORT-03** (recommended) — **Know the runtime.** claude.ai can install packages from npm and PyPI;
  the Claude API code execution environment has no network and no runtime installs; Claude Code runs on the
  user's machine, where the OS and shell vary (on Windows `python3` may be a store alias: document
  `python` or `py -3`; Claude Code's `shell: powershell` exists for a reason). `[BP]` `[CC]`
- **G-PORT-04** (required) — **MCP tools fully qualified**: `ServerName:tool_name` in portable skills
  (Claude Code names them `mcp__server__tool`). An unqualified name fails when several servers are
  connected. `[BP]`
- **G-PORT-05** (recommended) — **Cross-agent skills stay on the open standard.** Claude Code-only fields
  (G-FM-04) and substitutions (`${CLAUDE_SKILL_DIR}`, `${CLAUDE_EFFORT}`, `` !`cmd` ``) are ignored or left
  literal by other agents. Keep them out of shared skills, or write so that a literal placeholder still reads
  correctly ("`${CLAUDE_SKILL_DIR}` is this skill's folder"). `[AS-SPEC]` `[CC]`
- **G-PORT-06** (recommended) — **Shell snippets in the skill text must survive argument substitution.**
  In Claude Code, `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N` (0-based) and `$name` (declared in `arguments`) are
  replaced in the skill content before the model reads it, so an `awk '{print $2}'` or a shell function's `$1`
  can arrive rewritten, and so can a shell variable that shares its name with a declared argument. Using a
  declared `$name` on purpose is how the placeholder is meant to work. Use `cut`, `sed` capture groups or a
  script under `scripts/` (a script file is executed as it is), and check the loaded text when in doubt.
  `[CC]`

---

## 11. Invocation and safety

- **G-SAFE-01** (recommended) — **Choose who can invoke it**: both (default), the user only
  (`disable-model-invocation: true`, for side effects), or the model only (`user-invocable: false`, for
  background knowledge). `[CC]`
- **G-SAFE-02** (required) — **`allowed-tools` grants, it does not restrict.** It lets the listed tools run
  without a prompt during the invoking turn; a repository skill can grant itself broad access, so review it
  like code. To take tools away, use `disallowed-tools`. `[CC]`
- **G-SAFE-03** (required) — **`context: fork` only with an explicit task.** The forked subagent does not
  see the conversation; a skill of guidelines without a task returns nothing useful there. `[CC]`
- **G-SAFE-04** (recommended) — **Dynamic context runs first.** `` !`cmd` `` runs before the model sees
  the skill; a non-zero exit aborts the whole invocation (append `|| true` to commands that may fail), and
  the command goes through the permission rules. `[CC]`
- **G-SAFE-05** (required) — **No surprises.** A skill's contents should not surprise the user in their
  intent if described: no hidden behaviour, no exfiltration, no exploit code. `[SC]`
- **G-SAFE-06** (recommended) — **Third-party skills are code**: read every file before installing or
  running one. `[CC]` `[SC]`
- **G-SAFE-07** (recommended) — **Untrusted content stays data.** A skill that acts on fetched material
  (email, web pages, tickets, pasted text) tells the model to treat instructions inside it as content, not
  as orders. `[OPUS55]`

---

## 12. One skill, many models

A skill runs on whatever model the session uses, and sometimes on several within one session (a Haiku
subagent, an Opus main thread). The answer to "Haiku needs more help than Opus" is **not** a skill per
model.

- **G-MODEL-01** (required) — **One skill per job, never one per model.** Per-model copies duplicate the
  triggers (the model sees two near-identical descriptions), double the listing cost, and drift the day one
  copy is fixed and the other is not. `[BP]` `[AS-BP]`
- **G-MODEL-02** (required) — **The base works on every model you target.** Goal, constraints with their
  reasons, gotchas, numbered steps only where order matters, objective validators. "If you plan to use your
  Skill across multiple models, aim for instructions that work well with all of them." `[BP]`
- **G-MODEL-03** (recommended) — **Deterministic levers before text** (Claude Code only, so not in shared
  skills, G-PORT-05):
  - `model:` and `effort:` in the frontmatter pin the model or effort for the turn the skill runs in — the
    right tool when a skill must run on a given model, rather than describing how to behave on each;
  - `context: fork` with an `agent` whose definition sets `model` runs the skill on a chosen subagent model;
  - `${CLAUDE_EFFORT}` in the body renders the active effort level, so a line such as "Current effort:
    `${CLAUDE_EFFORT}`; at low effort, still run step 5" is evaluated with the real value.

  There is no substitution exposing the active model. `[CC]`
- **G-MODEL-04** (recommended) — **Model appendices, loaded on demand.** When an evaluation shows a measured
  gap on one model family, put the extra guidance in `references/models/<family>.md` and route to it from a
  short section near the top of `SKILL.md`:

  ```markdown
  ## Model notes
  If you are running as Claude Haiku, read `references/models/haiku.md` before step 1.
  If you are running as Claude Sonnet at low or medium effort, read `references/models/sonnet.md` before step 1.
  On any other model, or if you cannot tell, the instructions below are complete as they are.
  ```

  The rules of the pattern:
  - appendices **add, never contradict**: the base must be complete without them;
  - one file per family that needs one, linked directly from `SKILL.md` (G-STRUCT-02); no file for a family
    that needs nothing;
  - the model knows which model it is from the harness system prompt (Claude Code states it); on surfaces
    where it may not, the fallback line keeps the skill correct;
  - only measured gaps go in an appendix, never anticipated ones (G-EVAL-01). `[BP]` `[CC]`
- **G-MODEL-05** (recommended) — **What typically belongs in each appendix**, from the official model
  guides:

  | Family | Typical content |
  |---|---|
  | Haiku | worked examples and an explicit decision table for judgment-heavy steps; scripts for fragile steps; with long prompts at low effort it can stop early, skip a search or skip a check, so add the *keep working* and *real check* paragraphs below; give it the current date if it searches |
  | Sonnet | at low and medium effort it can check in before finishing a coding task (*keep working*); at low effort it can report a change without running a check (*real check*); it adds tests and docs nobody asked for (*scope*) |
  | Opus | usually nothing. If the base carries generic verification or delegation instructions, remove them from the base (G-GEN-07, G-GEN-09) rather than overriding them here; for narrow tasks, the *scope* paragraph |
  | Fable | usually nothing; for long autonomous runs, grounded progress claims (G-FLOW-06) |

  The paragraphs, as published in the official guides:

  > **Keep working** — "Keep working until everything the user asked for is done, and only stop to ask when
  > you can't go on without the user or before a risky step."
  >
  > **Scope** — "When the work the user asked for is done and checked, stop and report. Don't add features,
  > tests, files, docs or refactors that weren't asked for. If you think one would help, mention it at the
  > end instead of doing it."
  >
  > **Real check** — "When you change code that can be run, built, or type-checked, run a real check that
  > exercises the change before reporting it done: the project's tests, type-checker, or build, or the
  > changed command itself. A syntax-only check, or a check command that failed to start, does not count;
  > […] Only if no real check can run here, say which one you did not run and why instead of reporting the
  > change as done."

  `[SONNET55]` `[HAIKU55]` `[OPUS5]` `[OPUS55]` `[FABLE5]`
- **G-MODEL-06** (recommended) — **Test the matrix you rely on**: every model and effort level the skill
  will run on (G-EVAL-06), and record the result in `compatibility` (G-FM-06). `[BP]`
- **G-MODEL-07** (required) — **Re-test when a model changes.** A new model can make an appendix, or the
  whole skill, unnecessary; it can also regress. `[BLOG-SC]`

---

## 13. The collection as a whole

- **G-LIB-01** (recommended) — **Coherent units.** Not so narrow that two skills must load together for
  one task, not so broad that the skill cannot trigger precisely. `[AS-BP]`
- **G-LIB-02** (required) — **No overlapping triggers.** Two skills whose descriptions claim the same
  requests make both activate worse: merge them or sharpen the boundaries (G-DESC-05). `[GUIDE]`
  `[AS-DESC]`
- **G-LIB-03** (recommended) — **Consistent names**: a gerund (`processing-pdfs`) or a noun phrase
  (`pdf-processing`), the same pattern across the collection; never `helper`, `utils`, `tools`. `[BP]`
- **G-LIB-04** (recommended) — **Retire what the model no longer needs.** "Capability uplift" skills
  become unnecessary as models improve; "encoded preference" skills (your process) last longer. When the
  base model passes a skill's evals without it, propose retiring the skill — do not delete silently. In
  Claude Code `/skill-doctor` shows each skill's context cost and usage. `[BLOG-SC]` `[CC]`
- **G-LIB-05** (recommended) — **Mind the number of enabled skills.** Anthropic's guide flags degradation
  from somewhere around 20-50 skills enabled at once; in Claude Code, low-priority skills can be listed by
  name only (`skillOverrides: "name-only"`). `[GUIDE]` `[CC]`
- **G-LIB-06** (recommended) — **The right home for each kind of guidance**: facts needed in every session
  in CLAUDE.md or AGENTS.md; procedures and reference material loaded on demand in a skill; rules that must
  always hold in a hook. `[CC]`

---

## 14. Evaluation and iteration

- **G-EVAL-01** (required) — **Evaluate before you write a lot.** Run representative tasks without the
  skill, note the failures, build at least three scenarios that capture them, then write the minimum that
  makes them pass. Evaluations are the source of truth for whether a skill helps. `[BP]`
- **G-EVAL-02** (recommended) — **Output evals**: `evals/evals.json` with a realistic prompt, the expected
  output, input files and objective assertions. Run each case with the skill and without it (or with the
  previous version), each in a clean context; grade every assertion with quoted evidence; compare pass
  rate, time and tokens; for holistic quality, a blind A/B comparison. `[AS-EVAL]` `[BLOG-SC]`
- **G-EVAL-03** (recommended) — **Trigger evals**: about 20 realistic queries, 8-10 that should trigger
  and 8-10 near misses that should not, each run 3 times; a query passes on the right side of a 0.5 trigger
  rate. Optimise on ~60% of the queries and choose the best version on the other ~40%; five iterations are
  usually enough. `[AS-DESC]`
- **G-EVAL-04** (required) — **Test in fresh sessions.** Leftover context from writing the skill hides the
  gaps in what is written. Work with one instance to write the skill and a fresh one to use it. `[CC]`
  `[BP]`
- **G-EVAL-05** (recommended) — **Watch how the skill is navigated**: files read in an unexpected order,
  links not followed, a reference read every time (it belongs in `SKILL.md`), a file never opened (cut it or
  signal it better). `[BP]`
- **G-EVAL-06** (recommended) — **Test on every model you will use.** Haiku: is there enough guidance?
  Sonnet: is it clear and efficient? Opus: does it avoid over-explaining? `[BP]`
- **G-EVAL-07** (recommended) — **Read the transcripts, not only the outputs.** Instructions that waste
  time get removed; when pass rates plateau while you add rules, try removing rules instead; generalise from
  feedback rather than patching single cases. `[AS-EVAL]` `[SC]`
- **G-EVAL-08** (optional) — **Tooling.** The `skill-creator` plugin (evals, benchmark, blind comparator,
  description tuning); `claude plugin eval` for plugin skills; `claude plugin validate .claude/skills` for
  frontmatter that does not parse; `skills-ref validate` for the open standard; `/context`, `/doctor`,
  `/skill-doctor` and `--debug` in Claude Code. The quickest check of a description: ask "when would you use
  the X skill?" and compare the answer with what you meant. `[CC]` `[AS-SPEC]` `[GUIDE]`

---

## 15. Keeping these rules current

- **G-FRESH-01** (required) — **The rules carry their sources.** `references/sources.json` lists every
  official page with the rule IDs that depend on it, a few anchor sentences each rule rests on, and the
  models whose guidance has been absorbed. `scripts/check_freshness.py` checks them before every audit, and
  the repository runs it weekly. `[CC]` `[PROMPT]`
- **G-FRESH-02** (required) — **On drift, research only what drifted**, write the delta with quotes, apply
  it to the run at hand, and propose the update to this repository. Never edit an installed copy of the
  rules in place: the next update overwrites it, and every project ends up with a different rulebook. The
  procedure is in `references/refresh-procedure.md`.

---

## 16. Anti-patterns at a glance

| Anti-pattern | Rule |
|---|---|
| `CRITICAL`/`MUST`/`NEVER` in capitals for emphasis | G-GEN-02 |
| "Show your reasoning", "think step by step and write it out" | G-GEN-05, G-GEN-06 |
| "Double-check everything", "verify with a subagent" as a blanket instruction | G-GEN-07 |
| Explaining what the model already knows | G-BODY-01 |
| The key rule at the bottom of a 600-line `SKILL.md` | G-BODY-02, G-STRUCT-01 |
| A menu of equivalent tools with no default | G-BODY-05 |
| "Before version X do Y" in the body | G-BODY-10 |
| A must-hold rule written only as text | G-FREE-02 |
| A deploy or send skill the model can invoke on its own | G-FREE-03 |
| Reference chains, long files without a table of contents | G-STRUCT-02, G-STRUCT-03 |
| Backslash paths, or the author's own home directory, written into a skill | G-STRUCT-06, G-PORT-02 |
| A stub that says "read the other SKILL.md in full" | G-STRUCT-09 |
| A checklist without the way back | G-FLOW-03 |
| A command in the steps that nobody ran: wrong field, wrong flag, or the opposite action | G-FLOW-09 |
| A script that prompts, or fails without saying how to fix it | G-SCRIPT-03, G-SCRIPT-06 |
| "Use the pdf library" with no install line | G-PORT-01 |
| `awk '{print $2}'` or a `$1` in a shell snippet of the skill text | G-PORT-06 |
| `argument-hint` or `model` in a skill uploaded to claude.ai | G-FM-03 |
| `allowed-tools` used to "restrict" a skill | G-SAFE-02 |
| `my-skill-haiku` next to `my-skill-opus` | G-MODEL-01 |
| Two skills whose descriptions claim the same requests | G-LIB-02 |
| A description in first person, or made only of keywords | G-DESC-02, G-DESC-06 |

---

## 17. Old patterns

Advice that was right for earlier models and is now superseded. Kept here so nobody re-adds it.

- **`## Important` / `## Critical` headers and repeated key points** to make rules stick. Superseded by
  G-GEN-02 and G-BODY-11: plain wording with the reason, and a hook for what must always hold.
- **"Performance notes: take your time, quality matters more than speed, do not skip validation."** An
  anti-laziness prompt for older models (and even then more effective in the user prompt than in a skill).
  Superseded by the effort setting and by concrete gates (G-FLOW-03, G-FLOW-04).
- **"Think step by step" / "explain your reasoning before answering"** inside skills. Superseded by
  adaptive thinking (G-GEN-06), and now a refusal risk (G-GEN-05).
- **"If in doubt, use [tool]" / "Default to using [tool]."** Written for models that undertriggered tools;
  the current ones overtrigger on it. Use "use [tool] when it would help with …". `[PROMPT]`
- **A final verification step or a verifier subagent for every task.** Superseded by G-GEN-07: objective
  validators where they exist, fresh-context verifiers only for long autonomous runs.
- **`allowed-tools` described as a restriction.** It pre-approves tools; it never restricted them
  (G-SAFE-02).
- **A copy of the skill per model.** Superseded by G-MODEL-01 to G-MODEL-04.
- **Thinking budgets and `budget_tokens` in skill text.** Thinking is adaptive and controlled by effort;
  a skill has nothing to say about it beyond G-MODEL-03.
- **Forced status scaffolding** ("after every 3 tool calls, summarise progress") and its opposite ("hold
  all findings for the final response"). The current models report progress on their own; describe the
  updates you want instead of forcing or suppressing them. `[SONNET5]` `[FABLE51]`
- **Blanket anti-formatting rules** ("never use bullets or bold") written to restrain older models. The
  newest ones format less by default and such rules can strip structure the content needs; say when a given
  format is appropriate instead. `[FABLE51]`
- **"Only report what matters" in review skills.** Superseded by G-GEN-12.

---

## 18. Common claims, checked

Rules that circulate in tutorials and videos, compared with the sources.

| Claim | Verdict |
|---|---|
| Files over 100 lines need a table of contents at the top | **Confirmed** (G-STRUCT-03). The cause is partial reads of referenced files, which is why the rule is about references; Anthropic's skill-creator uses a 300-line threshold, this rulebook keeps the stricter 100 |
| "Claude reads only the first 100 lines of every file" | **Overstated.** It may preview a referenced file partially, especially through nested references; it does not truncate every file |
| Give Claude the right degree of freedom: high, medium, low | **Confirmed** (G-FREE-01), with one addition: what must never break goes in a hook (G-FREE-02) |
| Test the skill on the model you use; newer models need fewer instructions | **Confirmed** (G-EVAL-06, G-GEN-01). The "too prescriptive" statement comes from the official Fable guide, not from the skill best-practices page |
| Keep `SKILL.md` under 500 lines as an index, references one level deep | **Confirmed** (G-STRUCT-01, G-STRUCT-02) |
| After a long chat only the start of each skill survives | **Confirmed** (G-BODY-02): the first 5,000 tokens per skill, 25,000 in total, after compaction |
| A checklist with "where to go back" for long tasks | **Confirmed** (G-FLOW-02, G-FLOW-03) |
| End with Claude checking its own work and looping until it passes | **Confirmed with a caveat** (G-FLOW-04, G-GEN-07): with an objective yardstick, yes; a generic "re-check your work" causes over-verification on the current Opus models |
| Two or three examples of good output | **Confirmed** (G-BODY-08) |
| Declare the packages and how to install them; use forward slashes | **Confirmed** (G-PORT-01, G-STRUCT-06) |

---

## 19. Final checklist

Copy it into the review and tick each line; a failed line names the rule to go back to.

```
Skill: <name>
- [ ] Frontmatter parses; name valid and equal to the folder; only the fields the target surfaces accept   (G-FM-01..03)
- [ ] Description: what + when, key use case first, user words, boundaries, no first person, no keyword soup (G-DESC-01..06)
- [ ] Nothing the model already knows; gotchas present; most important rules at the top                    (G-BODY-01, -02, -04)
- [ ] No capitals for emphasis; reasons given; positive wording                                             (G-GEN-02..04)
- [ ] No request to write out reasoning; no generic re-check or delegation instructions                    (G-GEN-05, -07, -09)
- [ ] Each step at the right freedom; must-hold rules in hooks or scripts; side effects manual             (G-FREE-01..03)
- [ ] SKILL.md < 500 lines; references one level deep; ToC on files > 100 lines; no dead links or orphans  (G-STRUCT-01..03, -08)
- [ ] Checklists say where to go back; validators are objective                                            (G-FLOW-03, -04)
- [ ] Every command the steps quote was run once, and its output holds the fields the next step reads     (G-FLOW-09)
- [ ] Scripts: non-interactive, --help, structured output, helpful errors, dependencies declared           (G-SCRIPT-03..08)
- [ ] Requirements and install commands stated; no machine-specific paths; MCP tools qualified             (G-PORT-01, -02, -04)
- [ ] One skill for all models; model appendices only for measured gaps, additive, with a fallback line    (G-MODEL-01..04)
- [ ] No overlapping triggers with sibling skills                                                          (G-LIB-02)
- [ ] Evals: baseline without the skill, trigger queries with near misses, tested on each target model     (G-EVAL-01..06)
```

---

## 20. Sources

Official guidance first; the open standard second; community material only as a cross-check.

| Key | Source | What it covers |
|---|---|---|
| `[BP]` | [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | conciseness, degrees of freedom, testing per model, naming, descriptions, progressive disclosure, workflows, feedback loops, scripts, final checklist |
| `[CC]` | [Claude Code: skills](https://code.claude.com/docs/en/skills) | locations, every frontmatter field, substitutions, dynamic context, listing budget, compaction, hooks, fork, troubleshooting |
| `[PROMPT]` | [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) | techniques for all current models, aggressive language, thinking, subagents, migration |
| `[OPUS55]` | [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) | effort, thinking always on, progress updates, pasted content |
| `[OPUS5]` | [Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) | over-verification, scope, subagent spawning, reasoning in the response |
| `[SONNET55]` | [Prompting Claude Sonnet 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5) | initiative and scope, verification at low effort, unrequested additions |
| `[HAIKU55]` | [Prompting Claude Haiku 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5) | early stopping in long prompts, verification, search |
| `[SONNET5]` | [Prompting Claude Sonnet 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5) | literal instruction following, review recall, forced status updates |
| `[FABLE5]` | [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5) | "skills developed for prior models are often too prescriptive", reasoning extraction, grounded progress |
| `[FABLE51]` | [Prompting Claude Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1) | instructions to remove: anti-formatting rules, suppressed narration; scope of open-ended work |
| `[MODELS]` | [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview) | the current model line-up, used by the freshness check |
| `[GUIDE]` | [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) | use-case categories, description formula, negative triggers, troubleshooting, patterns |
| `[AS-SPEC]` | [Agent Skills specification](https://agentskills.io/specification) | the portable format, field constraints, progressive disclosure budgets |
| `[AS-BP]` | [Best practices for skill creators](https://agentskills.io/skill-creation/best-practices) | gotchas, defaults, procedures, calibrating control |
| `[AS-DESC]` | [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) | trigger evals, near misses, train/validation split |
| `[AS-EVAL]` | [Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills) | evals.json, baselines, grading, benchmarks, iteration |
| `[AS-SCRIPTS]` | [Using scripts in skills](https://agentskills.io/skill-creation/using-scripts) | script interfaces for agents |
| `[SC]` | [anthropics/skills — skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) | pushy descriptions, the "yellow flag" on capitals, lean prompts, lack of surprise |
| `[BLOG-SC]` | [Improving skill-creator: test, measure, and refine](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills) | capability uplift vs encoded preference, re-testing as models change |
