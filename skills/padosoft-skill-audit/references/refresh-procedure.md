# Refreshing the rulebook when the sources drift

Read this only when `scripts/check_freshness.py` exits 1 and the user chose to research now. The aim is to
read **only what drifted**, decide what it means for the rules, use it for the audit at hand, and send it
back to the shared rulebook so it is fixed once for everyone.

## Contents

1. [What the drift report gives you](#1-what-the-drift-report-gives-you)
2. [Research only the drifted pages](#2-research-only-the-drifted-pages)
3. [Write the delta](#3-write-the-delta)
4. [Use it for this audit](#4-use-it-for-this-audit)
5. [Send it upstream](#5-send-it-upstream)
6. [Never do this](#6-never-do-this)

## 1. What the drift report gives you

Each drift line has a kind, a source key and the rule IDs to re-check.

| Kind | What changed | What to read |
|---|---|---|
| `missing-anchor` | A sentence a rule rests on is no longer on its page, so the page was reworded, moved or the rule was withdrawn | The page, around where the sentence was; the rule in `guidelines.md` |
| `new-section` / `removed-section` | The page gained or lost a heading | The new section in full; for a removal, whether its content moved elsewhere |
| `new-model` | A model name appears that the rules do not cover | That model's prompting guide, and the models overview |
| `uncovered-model` | The model running the audit is not covered | Same, for that model |
| `new-field` / `removed-field` | The Claude Code frontmatter reference lists a field the rules do not know, or dropped one | The row for the field, and the section that explains it |
| `outdated-copy` | A newer version of this skill is published | Update the skill first (`npx skills add …`) and re-run Phase 0: the fix may already be there |

A `missing-anchor` is not always a change of substance. The anchors are one sentence each, so a reworded
paragraph trips them. The research below decides which it is.

## 2. Research only the drifted pages

1. Fetch each drifted page from the URL in `references/sources.json`. The documentation sites serve a
   Markdown version when `.md` is appended to the page address, which is shorter and cleaner to read.
2. For each drift line, find the relevant passage and read it in full, with the paragraphs around it.
3. For a **new model**, read its prompting guide and answer four questions: does it change any rule in
   `guidelines.md` (the generic sections, §2); does it need a row in the model table of G-MODEL-05; does it
   add an instruction that skills should avoid (§17); does it change how effort, thinking or verification
   behave (G-GEN-07, G-MODEL-03). Take the official wording and sample paragraphs verbatim.
4. If a page cannot be fetched, say so. Do not fill the gap from memory: the freshness check exists
   because memory goes stale.
5. Prefer official pages. A blog post or video that claims "Anthropic changed X" is a lead to look for the
   official statement, not evidence; if you cannot find the official source, record the claim as unverified.

## 3. Write the delta

A short list, one entry per affected rule, in this shape:

```
Rule: G-GEN-07   Status: changed | new | withdrawn | unchanged (anchor reworded)
Source: [OPUS6] <section> — "<the exact sentence>"
What changes: <one or two sentences>
New rule text: <the rule as it should read in guidelines.md, with level and source key>
```

Include new rules with a proposed ID in the right area (the next free number; IDs are never recycled) and
any new source with its URL and two or three anchor sentences. Keep quotes short and exact.

## 4. Use it for this audit

Apply the delta on top of `guidelines.md` for the rest of the run, and say so in the report:
"rules as of the repository version, plus the delta below". Where the delta and the written rule disagree,
the delta wins, because it comes from the newer source. Do not edit the installed copy of `guidelines.md`:
the next update of the skill overwrites it, and projects would end up with different rulebooks.

## 5. Send it upstream

The shared rulebook lives in `padosoft/skills`. The fix is one pull request there, not one per project.

1. With the user's confirmation — it is an action visible to others — open an issue or a pull request on
   `padosoft/skills` with the delta. A pull request changes, in this order:
   - `skills/padosoft-skill-audit/references/guidelines.md` (rules, §17 if something became obsolete);
   - `skills/padosoft-skill-audit/references/sources.json` (new sources and anchors; then
     `python3 scripts/check_freshness.py --rebaseline` so headings, models and fields record what was
     reviewed);
   - `scripts/audit_skills.py` and its tests, if a rule is mechanically checkable;
   - `CHANGELOG.md`, the skill's `metadata.version`, and the plugin version, as in `CONTRIBUTING.md`.
2. `make all` (or its steps, one by one on Windows) must pass; `tests/test_skill_freshness.py` checks that
   every rule cited in `sources.json` exists in `guidelines.md`.
3. If the user cannot open a pull request, give them the delta as a ready-to-paste issue body.

`--rebaseline` writes to `sources.json` what the live pages say now. Run it only after the rules have been
brought in line with those pages, because it makes the next check pass.

## 6. Never do this

- Re-baseline to make the warning go away without reading what changed.
- Add a rule from a secondary source with no official statement behind it.
- Edit the rulebook inside an installed copy, or paste the research into the project being audited.
- Treat a reworded anchor as a withdrawn rule, or the reverse, without reading the passage.
- Open the upstream issue or pull request without the user's confirmation.
