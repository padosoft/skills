# Prompt: audit and update a project's skills

For agents and projects where `padosoft-skill-audit` is not installed (or to paste into any chat). The
workflow lives in the skill, in one place; this prompt only gets the agent to it and sets the options.
Replace the values in angle brackets.

---

```text
I want you to audit the Agent Skills of this project against the current authoring rules for Claude models
(Opus 5.5, Sonnet 5.5, Haiku 5.5 and the later ones), and bring the ones that fall short up to date.

Mode: <report | apply>   (report: findings only, change nothing. apply: report first, then edit what I approve)
Scope: <the whole repository | the folder or skill: ...>

How to do it:
1. Use the skill `padosoft-skill-audit`. If it is not installed, install it with
   `npx skills add https://github.com/padosoft/skills/tree/main/skills/padosoft-skill-audit`
   (or fetch https://raw.githubusercontent.com/padosoft/skills/main/skills/padosoft-skill-audit/SKILL.md
   and its `references/`, `scripts/` folders), then follow it from Phase 0.
2. Phase 0 checks that the rules are still in line with Anthropic's official pages. If it reports drift,
   tell me what drifted and ask whether to research it now.
3. Read this project's CLAUDE.md / AGENTS.md first and follow its rules for branches, commits, generated
   files and AI instruction files. In report mode do not create branches or commits.
4. Keep what is specific to this project: commands, paths, schemas, business rules, gotchas, constraints.
   Cut only what the model already knows or what the rules say to cut. Keep each skill's language and what
   it does.
5. Do not push or open a pull request unless I ask. Do not touch skills synced from claude.ai.

At the end give me the report in the skill's format: what was verified, what was not, and anything I need
to decide (skills to retire, hooks to add, rules to send upstream to padosoft/skills).
```

---

## Notes for whoever maintains this prompt

- The prompt is deliberately short: duplicating the workflow here would let the two copies drift apart.
- Where the skill cannot be installed (an agent without the Agent Skills format), pasting `SKILL.md` and
  `references/guidelines.md` into the conversation, and running the two scripts by hand, gives the same
  result.
- `<report | apply>` defaults to report in the skill. Say `apply` only when you want edits.
