# Skill review checklist

To be used before the PR, and during review. If an item does not pass, the skill is not ready.

## Provenance — the item that is never waived

- [ ] `check_provenance.py` green on the skill **and** on its references, evals and scripts
- [ ] No date, release or sprint anywhere
- [ ] No customer, brand or product code name — a denylist is configured, and is **not** in the repository
- [ ] No person: name, initials, address, handle
- [ ] No real table, column, host, queue, bucket, or path from the machine it was written on
- [ ] No identifier anyone could look up: row, order, ticket
- [ ] No error message copied verbatim — its shape, not its text
- [ ] A reader cannot work out which project or which customer this came from
- [ ] The commit message that carries it is clean too

## Activation

- [ ] The `description` starts with "Use this skill when…" and lists **situations**, not features
- [ ] It includes at least one case where the user **does not name** the domain
- [ ] It states the boundaries: "Do not use it for…"
- [ ] Under 1024 characters
- [ ] `evals/queries.json` has at least 8 positives and 8 negatives, with real near misses (same domain, different task)
- [ ] No overlap with an existing skill: if there is one, either merge them or separate the boundaries in the two descriptions

## Content

- [ ] SKILL.md under 500 lines and ~5000 tokens
- [ ] A numbered workflow with at least one verification gate
- [ ] At least one copyable pattern (snippet or command), not just descriptions
- [ ] A gotchas section with facts that contradict reasonable assumptions
- [ ] An explicit default where several roads exist
- [ ] A template for the final report
- [ ] No explanations of things the agent already knows
- [ ] The details live in `references/`, and SKILL.md says **when** to read them

## Format

- [ ] `name` identical to the folder, with the `padosoft-` prefix
- [ ] Frontmatter with allowed keys only (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`)
- [ ] `metadata.profiles` and `metadata.scope` present and consistent (`global` implies `core`)
- [ ] Every path quoted in backticks exists inside the skill
- [ ] Scripts: standard library only, `--help`, distinct exit codes, no interactive prompts

## Integration into the repo

- [ ] The skill is included in a package under `plugins/`
- [ ] `make catalog` run after the last change to the frontmatter
- [ ] `make all` green
- [ ] CHANGELOG updated
- [ ] Tried in a fresh session on a real task, with the corrections carried into the gotchas

## Recurring mistakes

| Symptom | Almost always caused by |
|---|---|
| The skill never triggers | A description written from the skill's point of view, not the user's |
| It triggers out of place | The boundaries are missing ("Do not use it for…") or the domain is described too abstractly |
| The agent ignores a rule | The rule sits in `references/` instead of the gotchas in SKILL.md |
| The agent tries three roads before finding one | No default declared |
| CI red on `build_catalog.py --check` | `make catalog` missing after touching the frontmatter |
| CI red on `validate_plugins.py` | The skill is in no package under `plugins/` |
