---
name: {{name}}
description: >-
  Use this skill when {{concrete situations where it is needed, even without the domain keywords}}:
  {{what it does, in one line}}. Do not use it for {{boundaries: what it does NOT cover}}.
license: MIT
compatibility: >-
  {{prerequisites: runtime, tools, access. Remove this key if there are none.}}
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: {{profiles}}
  scope: {{scope}}
  repository: https://github.com/padosoft/skills
  keywords: {{comma-separated keywords}}
---

<!-- PROVENANCE: the work this came from is input, never content. No dates, no customer or
     brand names, no people, no real tables/hosts/ids, no error messages copied verbatim.
     Before committing, this must be green:
       python3 skills/padosoft-skill-creator/scripts/check_provenance.py skills/{{name}}
     Delete this comment once the skill is written. -->

# {{Title}}

{{One or two lines: what the skill produces and what the expected result is, measurable if possible.}}

---

## 0. Included scripts

| Script | Use |
|---|---|
| `scripts/{{script}}.py` | {{what it does and the ready-to-run command}} |

## 1. Workflow

1. {{Step with the command or the criterion}}
2. {{…}}
3. **Verify**: {{command that validates the result}} — do not deliver until it passes.

## 2. Patterns

```{{language}}
{{copyable snippet}}
```

## 3. Gotchas

- {{fact that contradicts the reasonable assumption}}
- {{mistake already made and how to avoid it}}

## 4. Checklist

- [ ] {{check}}
- [ ] {{check}}

## 5. Final report

```
{{template of the report the agent must produce}}
```
