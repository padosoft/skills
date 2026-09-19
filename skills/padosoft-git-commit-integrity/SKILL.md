---
name: padosoft-git-commit-integrity
description: >-
  Use this skill right after committing, and whenever something that works locally is missing or wrong
  everywhere else: a file you are certain you added is not in the repository, CI cannot find a module that
  exists on your machine, a colleague gets a whole-file diff from a one-line change, a review shows changes
  nobody made, or a generated file keeps coming back modified. It verifies what git actually recorded — `git
  add -A` skips ignored files in silence, and without a .gitattributes the line endings of whoever committed
  end up in the index — and gives the correct fix for each, which is never `git add -f`. Do not use it for
  merge conflicts, rebasing, branch strategy, or writing commit messages.
license: MIT
compatibility: >-
  Any git repository. The commands are plain git, no extra tooling.
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: core
  scope: global
  repository: https://github.com/padosoft/skills
  keywords: git, commit, gitignore, gitattributes, line endings, crlf, renormalize, ci
---

# Git commit integrity

**What git recorded is not always what you changed.** Two failures produce that gap, both invisible on the
machine that made the commit, both cheap to check and expensive to find later:

1. files you believe you committed and that are **not there**;
2. files that are there but **differ** from what you wrote.

---

## 1. After every commit: look at what went in

```bash
git show --stat HEAD
```

Compare the file count against the list of what you meant to change — new plus modified. **If the count does
not add up, investigate before pushing.**

This takes two seconds and is the only moment at which the next failure is cheap.

## 2. Files missing from the commit

**`git add -A` skips the files excluded by `.gitignore` in silence.** No error, no warning, exit code 0.

*The real case:* a generic `logs/` pattern, written for runtime logs, swallowed the **source** directory
`otel/logs/`. Build, server and tests were green locally — the files were simply absent from the commit, so
the endpoint did not exist for anyone else.

```bash
git status --short              # what is still outside, compared with what you expected
git check-ignore -v path/to/file    # prints the .gitignore line responsible
```

The fix is a **negation in `.gitignore`**, next to the rule that caused it:

```gitignore
logs/
!**/otel/logs/      # sources, not runtime logs
```

⚠️ **Not `git add -f`.** It puts this one file in and leaves the trap armed for every future file in the same
folder — including the one nobody will check.

## 3. Files that differ from what you wrote: line endings

```bash
git ls-files --eol | grep -E '^i/(crlf|mixed)'
```

`i/` is what is **in the repository**, `w/` what is in your working tree. The working tree can legitimately
differ per platform; the index should be uniform. Every line printed by that command is a file whose stored
content carries the line endings of whoever committed it.

Why it matters, in order of how much it costs:

- **A whole-file diff on a one-line change.** The review stops being a review: nobody reads 800 changed lines
  to find the one that moved. This is how a change to a sensitive file goes through unseen.
- **Phantom conflicts** between colleagues on different operating systems.
- **Generated files that come back modified** at every run, so `--check`-style CI steps fail with no real
  change.

The fix is two steps, and **the second is the one everybody forgets**:

```bash
# 1. declare the policy
cat > .gitattributes <<'EOF'
* text=auto eol=lf
*.ps1 text eol=crlf      # PowerShell wants CRLF in the working tree
*.png binary
EOF

# 2. apply it to what is ALREADY committed
git add --renormalize .
git commit -m "chore: normalise line endings in the index"
```

Without step 2 the file exists, everyone assumes they are protected, and the blobs committed **before** it
stay exactly as they were.

## 4. Generators write the platform newline

A script that writes a file with the language default produces CRLF on Windows and LF elsewhere, so the same
command run by two people yields two different diffs — and on a repo with `eol=lf` it fights `.gitattributes`
at every run.

Make the generator explicit:

```python
path.write_text(content, encoding="utf-8", newline="\n")   # Python: the default translates
```

The symptom to recognise: a generated file appears modified right after regenerating it, with no visible
change in the content.

---

## Gotchas

- **A green local build proves nothing about the commit.** Both failures above leave the working tree working
  perfectly; it is the *other* clone that breaks.
- **`.gitattributes` present ≠ index clean.** It only governs what is committed from then on. Check with
  `git ls-files --eol` rather than by looking for the file.
- **Renormalising produces a large and boring diff.** Do it when no pull request is open, or every one of
  them conflicts.
- **The `-f` reflex.** Every "I'll force it in just this once" leaves a rule that will swallow the next file
  in silence.
- **The check belongs before the push, not before the merge.** After the push the missing file is a CI
  failure for somebody else, and it is no longer clear whose.

## Checklist

- [ ] `git show --stat HEAD` run, file count matching the expected list
- [ ] Any missing file diagnosed with `git check-ignore -v`, fixed with a negation and not with `-f`
- [ ] `git ls-files --eol | grep -E '^i/(crlf|mixed)'` empty, or the repository has an open decision about it
- [ ] Generated files regenerated and unchanged on a second run

## Final report

```
Commit: <sha>  ·  <n> files (expected: <n>)
Missing: none | <file> → ignored by <.gitignore:line>, fixed with <negation>
Index line endings: clean | <n> non-LF blobs (<files>)
Next step: <…>
```
