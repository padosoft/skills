---
name: padosoft-laravel-conventions
description: >-
  Use this skill when writing or reviewing Laravel/PHP code — a controller, a FormRequest, a service, a job,
  a migration, an Eloquent query, a model event, a queued or bulk operation — and whenever a symptom shows
  up: a controller that grew into the business logic, an N+1 found in the logs, a bulk command that runs out
  of memory, a job that retries something it should not, a soft-deleted row reappearing in a count, a model
  event that fires on a mass update and does not. Baseline: Laravel 13+ / PHP 8.5+ for new work, with the
  differences on 10-12 called out. Do not use it for a security review (padosoft-laravel-security-review),
  for what goes in a log (padosoft-logging-discipline), or for infrastructure and deployment.
license: MIT
compatibility: >-
  Laravel 13+ / PHP 8.5+ as the baseline for new projects and modules. Almost everything holds on Laravel
  10-12 and PHP 8.2+; where it does not, the text says so.
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: laravel
  scope: project
  repository: https://github.com/padosoft/skills
  keywords: laravel, php, eloquent, service, dto, job, queue, migration, n+1, architecture
---

# Laravel conventions

Baseline for **new** projects and modules: **Laravel 13.x, PHP 8.5+**, Pint for formatting, Larastan/PHPStan
for static analysis, PHPUnit unless the repository already chose Pest.

On an existing Laravel 10-12 / PHP 8.2 codebase the rules below still apply — adopt the project's version,
and do not mix a new idiom with the legacy one halfway through a file.

---

## 1. The flow: FormRequest → DTO → Service → Resource

For any endpoint or form that is not trivial:

1. **`FormRequest`** validates and normalises the HTTP input;
2. the **controller** builds an explicit **DTO**;
3. the **service** (or action) runs the application logic;
4. the **controller** turns the outcome into a response, redirect or `JsonResource`.

What each step buys: the data contract stops being an untyped array crossing boundaries, the service is
testable without HTTP, and the controller has one job — translating.

**The controller never contains business logic.** The signal it has drifted: it queries, it decides, it
formats. Two of the three belong elsewhere.

Never pass `$request->all()` down: pass `validated()`, or better the DTO. An array that "came from the
request" has no shape anyone can rely on three files later.

## 2. Long or asynchronous work: DTO → Service → Job

- **DTO / value object** for the input;
- **service / action** for the logic;
- **job** for queued execution.

**The job orchestrates, it does not implement.** Retry, timeout, backoff and execution context live in the
job; the reusable logic lives in the service, so it can be called synchronously by a command or a test.

In a job, distinguish a **retryable** error from a **permanent** one. Retrying a validation failure burns the
queue; not retrying a timeout loses work. A permanent failure fails the job explicitly rather than throwing
something the queue will retry sixteen times.

## 3. Structure

```
Domain/<Module>/
├── Dto/                 explicit inputs
├── Http/Requests/       HTTP validation
├── Http/Controllers/
├── Services/  (or Actions/)
├── Jobs/
└── Routes/              if the module exposes its own endpoints
```

Symmetrical directories: controller, request, service and **test** follow each other. No bin directories —
`misc`, `common`, `utils`, `various` — and no omnivorous generic service. When a folder stops having one
responsibility, split it.

## 4. Eloquent and queries

- **N+1**: eager load, or write a dedicated query. It is the single most common performance defect, and it
  only shows up with production-sized data.
- Need one value? Do not hydrate a whole model — `value()`, `pluck()`, an aggregate.
- **Never `select *`** on a critical query over a large dataset.
- Before micro-optimising, **measure**: cardinality and the execution plan. An index added by intuition is
  often an index that is never used.
- **`chunkById` or `cursor` for bulk**, never `get()` followed by filtering in PHP. And push the filter into
  SQL: `whereNotIn` with chunked arrays beats loading everything and rejecting it in memory.
- **Soft deletes**: a query that must ignore them says so explicitly. A count that silently includes trashed
  rows is a number nobody can reproduce.

`chunkById` and not `chunk` when the loop **modifies** the rows it iterates: `chunk` pages by offset, so
updating rows shifts the window and silently skips records.

## 5. Migrations and schema

- One table, one responsibility. No column encoding two concepts.
- Indexes follow the **real read patterns**: if a hot query filters and sorts on the same fields, model the
  index on that.
- Think about cardinality, unique constraints and nullability deliberately — nullable by default is a
  decision nobody made.
- Foreign keys where the stack allows them.
- Derived or denormalised data: **document the source of truth** next to it, or the copy becomes the truth by
  accident.
- A migration is run once on production and lives forever in the history: make it idempotent where the
  project's convention requires it, and never edit one that has shipped.

## 6. Model events

They fire on **model** operations, not on query-builder mass operations: `Model::where(...)->update([...])`
does **not** fire `updating`/`updated`. That asymmetry is the bug — a rule enforced in an event silently does
not apply to the bulk path.

So: either the invariant lives somewhere both paths cross (a database constraint, an observer plus an
explicit call on the bulk path), or the bulk path is banned for that table and the ban is written down.

An event that dispatches a job must not assume the transaction committed: use the after-commit dispatch, or
the job runs against a row that is not there yet.

## 7. Types, null and errors

- **Type hints everywhere**: parameters, return types, properties. On PHP 8.5 there is no excuse left.
- Prefer an explicit object to a "magic" helper when it makes the contract clearer.
- **Do not use exceptions for expected user-validation flows** — that is what validation is for. Exceptions
  are for what should not happen.
- Translate infrastructure errors into application-level messages; what may and may not appear in them is in
  **`padosoft-laravel-security-review`** (`SEC-ERRLEAK-001`), and what goes in the log is in
  **`padosoft-logging-discipline`**.
- Null safety: a nullable that reaches a calculation makes a wrong number, not a crash. Decide at the
  boundary — reject it, default it, or make the type non-nullable — never three files downstream.

## 8. Code shape

Guard clauses and early return; avoid `else` when a return makes the flow obvious. Small methods, one main
responsibility. Complex branches move into private methods or dedicated services. Comment decisions,
constraints and trade-offs — not the obvious.

Anti-patterns, in the order they appear: a 150-line method with several responsibilities; business logic
mixed with I/O or rendering; a boolean flag that changes what a method fundamentally does; names like `data`,
`tmp`, `manager`, `utils` with no context.

## 9. Files and storage

Streams and chunks for large files, never the whole thing in memory. Validate type, size and destination
**before** copying. No whole-export concatenation in RAM. Clean up temporary files and intermediate
artefacts — including on the failure path, which is where they accumulate.

---

## Gotchas

- **`chunk` while updating skips rows.** Use `chunkById`.
- **Mass updates bypass model events** (§6), and so do mass deletes and `upsert`.
- **A `FormRequest` validating does not make `all()` safe**: it returns everything that was sent.
- **Eager loading inside a loop is still N+1**, just harder to see.
- **An index on a low-cardinality column often does nothing**; measure before adding.
- **A job retried after a partial write repeats the write.** Idempotency is designed in, not hoped for.
- **`dd()` and `dump()` in committed code** — see `padosoft-logging-discipline` §3, and do not delete
  someone else's silently: report it.

## Checklist

- [ ] Controller translates; logic in the service; DTO across boundaries
- [ ] Job orchestrates, service implements; retryable vs permanent distinguished
- [ ] No N+1; no `select *` on hot paths; bulk through `chunkById`/`cursor` with filters in SQL
- [ ] Soft-delete intent explicit in queries that care
- [ ] Migration: responsibility, indexes on real patterns, nullability decided, source of truth documented
- [ ] Bulk paths that bypass model events identified and handled
- [ ] Full type hints; nullability resolved at the boundary
- [ ] Pint and static analysis clean

## Final report

```
Change: <what>  ·  Laravel <version> / PHP <version>
Flow: FormRequest <file> → DTO <file> → Service <file> → Resource <file>
Queries: N+1 checked | bulk strategy <chunkById|cursor|none needed>
Migration: <yes/no — indexes, nullability, source of truth>
Model events: bulk path <not used | handled how>
Pint / static analysis: PASS | FAIL <detail>
```
