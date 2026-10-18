# padosoft/skills

The company catalogue of Agent Skills: one folder per skill under `skills/`, grouped into plugins by profile. The repository is **public**, so nothing in it may carry the provenance of the work a rule was learned from (no customers, people, dates, hosts, error text copied verbatim). `make privacy` is the gate.

Contribution flow and the placement of a skill (profile and scope): `CONTRIBUTING.md`. The rules for writing a skill: `skills/padosoft-skill-audit/references/guidelines.md`.

## Before you push

`make all` runs privacy, validate, audit-self, test and lint-email: the same checks as CI. Without `make` (a Windows workstation), run the commands of the Makefile one by one with `python`; `python3` is the Microsoft Store alias there.

Never edit a generated file by hand: `CATALOG.md`, `profiles.json`, the catalogue inside the router skill and the indexes in the README all come from `python scripts/build_catalog.py`. Run it and commit its output.

## Rules that exist because they were broken

- **A plugin and its marketplace entry carry the same version.** Bump `plugins/<name>/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` together whenever a skill in that package changes. `scripts/validate_plugins.py` fails when they differ; the listing had drifted unnoticed before that check existed.
- **A reference file over 100 lines opens with a contents list whose links land on a heading (GitHub's anchors keep underscores), and no description contains `<` or `>`** (claude.ai and the Skills API reject them). CI runs the repository's own audit with `--strict`, so a warning fails the build.
- **A CHANGELOG entry is not a release.** After the merge, tag `main` with an annotated `vX.Y.Z` and publish the GitHub release with the entry as its notes. An entry with no tag is unfinished work.
- **Every command a skill quotes was run once** in a read-only form, and its output holds the fields the next step reads (G-FLOW-09).
- **Scripts are standard-library Python**, non-interactive, with `--help` and exit codes 0, 1 and 2.
- **A workflow that reads repository content and a workflow that writes (issues, comments, pushes) are different jobs**, the first with a read-only token, no persisted credentials and no copy of the checker taken from the checkout.

## After every pull request or session

Read the fixes you made and the lessons you hit (a red check, review findings, anything done twice, a trap in the environment) and ask of each whether a rule would have prevented it. If so, put the rule where it will be loaded: this file, `CONTRIBUTING.md`, the guidelines of `padosoft-skill-audit`, or a check in a script; a check is better than a sentence. State in the pull request body which rules changed, or that none did and why.

`padosoft-knowhow-harvest` (section 9) describes the loop. The periodic harvest of the lessons files of all repositories then promotes what several projects learned alike.

## Environment traps

- Python written inside a shell heredoc loses its backslash sequences (a newline escape becomes a real newline). Write such a script to a file and run the file.
- `test_catalog … test_dry_run` needs `/bin/bash`: it fails on a Windows workstation and passes on CI. It is not a regression.
- The symlink tests exercise real symlinks only on the Linux CI; locally they fall back to junctions.
- Request a Copilot review with the GraphQL `requestReviews` mutation, bot id `BOT_kgDOCnlnWA`, `union: true`, and confirm in the issue timeline that it landed.
