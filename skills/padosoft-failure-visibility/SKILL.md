---
name: padosoft-failure-visibility
description: >-
  Use this skill whenever code can fail and the caller has to find out — a write to disk or storage, an
  external call, a catch block, an endpoint that returns a body, a fetcher, a renderer, a chart that reduces
  an array — and whenever the user says something "silently did nothing", data disappeared without an error,
  a request returned 200 but the page is empty, a job later died on something that was reported as accepted,
  or a retry loop never fires. It covers the two halves of the same bug: an ignored return value, and a
  success status served over a failure. Do not use it for what goes inside a log line
  (padosoft-logging-discipline) or for retry and timeout policy.
license: MIT
compatibility: >-
  Language-agnostic. The examples are PHP/Laravel and TypeScript/React because that is where the cases came
  from; the rule holds anywhere a call can fail.
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: core
  scope: global
  repository: https://github.com/padosoft/skills
  keywords: error handling, failure, status code, silent failure, exceptions, http, io
---

# Failure visibility

Two symptoms, one bug: **the caller cannot tell success from failure.**

1. A call that failed, whose return value nobody looked at.
2. A failure served with a success status, or an empty body, or a `null`.

Both leave a system that looks healthy while it loses work.

---

## 1. Never ignore the return value of a side-effecting call

Many APIs report failure by **returning a value**, not by throwing — especially file and storage APIs, and
HTTP clients configured not to throw.

```php
$ok = Storage::disk($disk)->put($target, $content);
if ($ok === false) {
    throw new RuntimeException("Unable to persist {$target} on disk {$disk}.");
}
```

*It happened:* a controller called `Storage::put(...)` without checking the return. The disk was configured
with `throw => false`, so a full disk returned `false`, **the controller answered `202 Accepted`**, and the
job that came later died with "file not found". From the client's side, ingestion silently dropped documents.

Applies to storage put/delete/copy/move/makeDirectory, `file_put_contents`, `copy`, `rename`, `unlink`,
`mkdir`, and any library call that returns `false` on failure.

**Never log and continue.** A log line is not a return path: the caller still believes it worked.

### Two related bans

- **The `@` silencer** — `@mkdir(...)` hides the error and the return value in one character.
- **World-writable permissions** — `0777` on a directory created for a cache or a test fixture is not a
  convenience, and it usually appears next to the silencer.

```php
if (! is_dir($dir) && ! mkdir($dir, 0755, true) && ! is_dir($dir)) {
    throw new RuntimeException("Unable to create {$dir}.");
}
```

The double check is deliberate: between the test and the creation another process may have created it, and
that is not a failure.

## 2. Map the failure to the right status, everywhere it is observed

An empty body on 200, an empty PDF on 200, `null` returned from a fetcher after a catch, `-Infinity` or `NaN`
in chart coordinates — the same bug in four costumes.

| Situation | Correct |
|---|---|
| The resource does not exist | 404 |
| It exists and cannot be read | 500 |
| A dependency is down | 503 |
| A fetcher caught an error | **rethrow** — swallowing it makes the client think it succeeded |
| A reducer over a possibly empty array | guard the empty case explicitly |

```ts
// ❌ the query layer now reports isError = false, and the UI shows an empty happy path
catch (e) { return null; }
// ✅
catch (e) { throw e; }
```

```ts
// ❌ -Infinity when data is empty
const max = Math.max(...data);
// ✅
const max = data.length ? Math.max(...data) : null;   // and render the empty state
```

## 3. The status comes from the exception TYPE, never from its message

```php
// ❌ brittle: any copy change flips the status code
if (str_starts_with($e->getMessage(), 'File missing')) return response('', 404);
// ✅
catch (FileMissingException) { return response()->json([...], 404); }
catch (StorageUnreadableException) { return response()->json([...], 500); }
```

A message is user-facing text: it gets reworded, translated, prefixed with a code. Control flow must not
depend on it. Where the type is not distinct enough, add one — that is what exception classes are for.

## 4. Empty is not the same as missing, and neither is the same as broken

Three different answers, three different renderings:

- **empty** — the operation worked, there is nothing: an explicit empty state, and 200 is correct;
- **missing** — 404;
- **broken** — 500/503, and the UI says so.

Collapsing them into one blank screen is what makes a defect unreportable: the user cannot describe what they
saw, because they saw nothing.

Watch for the edge that gets discarded by a truncating conversion: a single-line file whose line count reads
as "0 lines", a count cast to `int` that swallows a legitimate zero, a fallback to `''` when a library
returned a non-string.

---

## How to find it in a diff

```bash
# success status in what looks like an error branch
rg -n "response\(\)->json\([^)]*\],\s*200\)" app/Http/Controllers/
# fetchers swallowing errors
rg -n "catch[^{]*\{\s*return null" src/ frontend/src/
# unguarded reducers
rg -n "Math\.(max|min)\(\.\.\." src/ frontend/src/
# status driven by the message
rg -n "str_starts_with\(\\\$[a-z]+->getMessage" app/
# silencer and world-writable
rg -n "@(mkdir|file_put_contents|unlink|copy|rename)\(|0777" .
# storage writes whose result is discarded
rg -n "Storage::disk\([^)]*\)->(put|copy|move|delete)\(" app/ | rg -v "^\s*\\\$\w+\s*="
```

Every hit is a **candidate**, to confirm or discard — not an automatic finding.

## Gotchas

- **A caught exception that is logged and swallowed is the most expensive line in the file**, because it looks
  like handling. Handling means: recover, or translate into a failure the caller can see.
- **`throw => false` clients are a trap by design.** They exist so you can decide — which means you must.
- **A retry that never fires** is the second-order effect: the queue, the client or the user would have
  retried, and the false success took the option away.
- **The happy path is not the common path in production.** Disks fill, dependencies time out, files get
  deleted between the check and the read.
- **An empty state is a feature.** Without one, every failure mode renders identically.

## Checklist

- [ ] Every side-effecting call's return value checked, or the call genuinely throws
- [ ] No `@` silencer; no `0777`
- [ ] Failures mapped to 404 / 500 / 503 by **type**, not by message
- [ ] No fetcher returning `null` from a catch
- [ ] Reducers over arrays guarded for the empty case
- [ ] Empty, missing and broken render differently
- [ ] Tests that provoke the failure, not just the happy path

## Final report

```
Failure visibility: <n> files
Ignored return values: none | <file:line>
Success status over a failure: none | <file:line — what it should be>
Status driven by message: none | <file:line>
Empty / missing / broken collapsed: none | <where>
```
