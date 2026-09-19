---
name: padosoft-logging-discipline
description: >-
  Use this skill whenever code writes to a log or builds an error message for a user — a catch block, an
  exception handler, a logger call, telemetry, a debug line added while hunting a bug — and whenever the user
  says a log is noisy or useless, an error message shows SQL or a stack trace, a support ticket contains data
  it should not, or asks what is safe to log. It gives what must never reach a log or a screen, what to keep
  so the log stays diagnosable, and where the redaction goes in each stack, which is not the same place. Do
  not use it to choose a logging library or to configure log shipping, retention or dashboards.
license: MIT
compatibility: >-
  Language-agnostic. The worked mechanisms cover TypeScript/Node, React Native and Laravel/PHP; on another
  stack apply the invariant and find the local equivalent before copying any of them.
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: core
  scope: global
  repository: https://github.com/padosoft/skills
  keywords: logging, redaction, pii, secrets, exception, error handling, observability, monolog
---

# Logging discipline

Three codebases that do not share a line of code — a Bun/Hono API, a React Native app and a Laravel monolith —
arrived independently at the same rules. That is not a convention: it is a property of the problem.

**The invariants are the rule. The mechanism is per stack, and copying the wrong one does damage** (§8).

---

## 1. A driver exception is not a loggable object

This is the one that bit all three, and the damage was different every time:

| Stack | The object | What it carries | Where it went |
|---|---|---|---|
| Node + mysql2 | `err.sql` | the query **already formatted**, bound values substituted | into the logs: the hash of an auth token |
| Laravel + PDO | `QueryException::getMessage()` | SQLSTATE, production DB host, database name, the full INSERT | onto the **user's screen**, with their personal data |
| React Native | a raw `Error` | message and stack | into the logs, and every crash collapsed into one issue |

```ts
logger.error("db lookup failed:", err);     // ❌ err.sql goes with it
Log::error($e);                              // ❌ __toString() carries SQL and host
logger.error("[x]", err);                    // ❌ raw Error
```

**Never hand the exception object to the logger, and never put its native message in front of a user.**

⚠️ Grepping for the *name of the secret* does not find this. The two real leaking lines in the API were caught
only because their message happened to contain the word "token"; `logger.error("db lookup failed:", err)` is
the same bug and matches nothing. Check **what is handed to the logger**, not what the sentence says.

## 2. Keep the diagnosis, drop the data

Total redaction makes the log useless exactly when it is needed. The sharpest formulation of the line comes
from the Laravel side, and it generalises:

> Log the **parameterised** SQL (with the `?`), and describe the bindings as **type and length** —
> `['type' => 'string', 'len' => 31]`. The length is what tells you which `max:` is missing in the request.
> The value is not needed for that, ever.

Same idea everywhere else: keep what identifies the failure, drop what identifies the person.

| Keep | Drop |
|---|---|
| error code, errno, SQLSTATE, driver code | the bound values, the formatted query |
| table, column, constraint name | row contents |
| shape: type, length, count | the payload |
| a correlation id the user is also shown | tokens, cookies, `Authorization`, passwords |
| the *kind* of an identity (`operator`, `ip`) | the identity value — an IP is personal data |

## 3. Nothing ad hoc on stdout

| | Forbidden in runtime code | Use |
|---|---|---|
| TS / RN | `console.log/warn/error/debug` | the project logger |
| PHP | `dd()`, `dump()`, `var_dump()`, `print_r()`, `ds()`, `error_log()`, `xdebug_break()` | `Log::` |

A debug line added while hunting a bug is the most common way one of these ships. Grep the staged diff before
committing — and when you find one in someone else's code, **stop and report it, do not silently delete it**:
it may be load-bearing for a session that is still open.

## 4. Detail belongs at debug, not info

A full request/response, a query with its parameters, a whole entity: `debug`. `info` is the flow —
what happened, to what, with what outcome.

The test: *would this line still be worth reading in production at 3am, a thousand times an hour?* If not, it
is `debug`.

## 5. A safety net must say when it catches something

If a final layer sanitises what the layers above should have handled, **it logs a warning when it fires**. A
silent safety net turns into the only thing that works, and nobody ever learns that something upstream leaks.
It is a net, not an excuse to keep writing `$e->getMessage()`.

## 6. What the user sees, and how support gets from there to the log

A generic message plus a **reference code**, and the same code in the log line. The user gets nothing
technical; support gets the exact row. Never a stack trace, a class name, a filesystem path, a host, a table
or a column.

## 7. In local, you are not seeing production

Every redaction gated on the environment means the developer sees a different message than the user. That is
the right default — chasing a reference code while developing is a waste — but it has a cost: **nobody ever
looks at the production path**.

So the switch to force the production behaviour locally must exist, be documented next to the rule, and be
used before calling the work done. Turning it on is part of "done" for anything that changes error handling.

## 8. Where the redaction goes: per stack, and not interchangeable

| | Node / Bun · React Native | Laravel / PHP |
|---|---|---|
| **Applied** | **at the call site** — there is no central pipeline to hook | **centrally** — a Monolog processor on every channel |
| **Tool** | a redactor: `serializeError()`, `safeDbErrorDetails()` | `#[\SensitiveParameter]` (the language redacts the argument from stack traces), masking helpers |
| **Error → user** | error middleware gated on a fail-safe runtime check | source (exception handler) → extraction (`safeErrorMessage()`) → safety-net middleware |

**Do not port the mechanism across.** Applying the TypeScript pattern to Laravel means editing a hundred call
sites that a processor already covers; expecting a processor in Node means the redaction never happens,
because there is nothing to hook it into. Identify which of the two shapes the stack has **before** writing
the fix.

On a stack not in this table: the invariants in §1–§7 hold. Find where the local logging pipeline lets you
intervene once, and prefer that to touching every call site.

---

## Gotchas

- **The failure branch is the one people read.** It is what gets opened when something breaks, copied into a
  ticket and pasted into a chat. The branch least exercised in testing is the most exposed in practice.
- **A redaction regex that nobody maintains decays.** Whoever finds an uncovered pattern in a log extends it;
  that is part of the rule, not a favour.
- **Error-path code runs when the database is down.** If the sanitiser reads settings or translations, wrap it
  in try/catch with hardcoded defaults, or a DB error becomes a loop of errors.
- **A public identifier is not a secret.** Filtering an OAuth *client id* breaks login with nobody able to say
  why. Target the secret half of the pair.
- **Anti-flooding is part of the discipline.** A repeated error that sends an email per occurrence takes out
  the inbox and the signal with it. Cap it with a cooldown.

## Checklist

- [ ] No exception or error object handed whole to a logger
- [ ] No native exception message reaching a user; generic message + reference code
- [ ] Parameterised query and binding shapes in the log, never the values
- [ ] No `console.*` / `dd()` / `dump()` / `var_dump()` in runtime paths, staged diff included
- [ ] Full payloads at `debug`, flow at `info`
- [ ] Redaction applied where this stack wants it (§8), not where the other stack wants it
- [ ] Production error behaviour verified locally with the bypass off

## Final report

```
Logging review: <n> files
Exception objects logged: none | <file:line> → <redactor applied>
Technical detail reaching the user: none | <where>
console/dd/dump in runtime: none | <files>
Level: <n> lines moved from info to debug
Mechanism: call-site | central pipeline — matching this stack
Production behaviour verified locally: yes | no
```
