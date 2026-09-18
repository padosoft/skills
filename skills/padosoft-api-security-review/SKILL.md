---
name: padosoft-api-security-review
description: >-
  Use this skill before committing or reviewing any change to an HTTP API that touches routing, auth
  middleware, settings or config endpoints, logging and telemetry, SQL, error handling, response shaping,
  client IP, rate limits or an outbound fetch — and whenever the user asks for a security review, an audit,
  or says an endpoint "seems public", "returns too much" or "leaks something": it runs ten checks with ready
  grep pre-screens (auth on every mutating route, ownership from the authenticated id, no secrets or PII in
  responses, bound SQL, fail-safe env gates, resource caps, redacted logs, downstream injection, no trust
  from caller input, supply chain) and blocks the commit on each violation. Do not use it for infrastructure
  hardening (WAF, DNS, firewall) or for dependency CVE triage.
license: MIT
compatibility: >-
  Any HTTP API. The grep pre-screens assume a POSIX shell and a TypeScript/JavaScript codebase; the rules
  themselves are language-agnostic. Some notes are specific to Hono, and are marked as such.
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: api, node
  scope: project
  repository: https://github.com/padosoft/skills
  keywords: security, api, audit, auth, idor, secrets, sql injection, rate limit, owasp, review
---

# API security review

Ten checks to run **before committing** a change to an API, and when reviewing a PR. Each one carries the
mistake that produced it: these rules come from a security audit, from PR review findings and from one real
incident, not from a generic checklist.

The complete rules, with identifiers and rationale, are in [`references/rules.md`](references/rules.md).
Read it when a check fires and you need the full reasoning, or when you have to decide whether something is
a real exception.

---

## 0. How to run it

```bash
git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(ts|js|mjs)$'
# empty? then: git diff --name-only
```

Apply the relevant checks to those files. **For every violation: block the commit**, name the rule, propose
the fix. Skip a check that does not apply to the diff — do not report it as passed.

Severity: a violation of checks 1, 2, 3 or 5 is **critical** (it is how a real incident started). The others
block the commit but can be discussed.

---

## 1. Auth on every mutating route — `API-SEC-AUTH-001`

Every POST/PUT/PATCH/DELETE endpoint is authenticated, and every route group has an auth middleware.

```bash
# commented-out auth: this is exactly how three endpoint groups became public
grep -rnE '^\s*//\s*.*\.use\(\s*\w*[Aa]uth\w*' src/routes src/app
# wildcard auth inside a sub-app (see the flattening gotcha below)
grep -rnE '\.use\("\*",\s*\w*[Aa]uth' src/routes
```

- **A commented-out auth line is a critical bug**, never a temporary state.
- **Internal/debug endpoints are deleted, not gated.**
- **Authentication is not authorization.** A middleware that resolves "any valid user token" lets a customer
  through on a back-office endpoint. Staff-only routes need a **positive role check** after it.
- Prefer a **positive role allow-list** (`["SALES_ASSOCIATE","admin"]`) over a negative predicate ("has no
  customer row"): the negative form both under-blocks generic internal accounts and over-blocks hybrid users
  who are staff *and* customers.
- **Hono flattening gotcha:** when several sub-apps mount on the same prefix, `route.use("*", authMw)`
  **inside** a sub-app leaks to its siblings. Apply auth on the **exact path** where the app is composed.

## 2. Ownership from the authenticated id — `API-SEC-IDOR-001`

```bash
grep -rnE 'valid\("(query|json|param)"\)' src/controllers | grep -iE 'user|customer|client|order|receipt|return|device|lock|lease'
```

The owner id comes **only** from the authenticated context. Never trust an id from query/body/param for
ownership — scope the SQL to the authenticated id.

- A nested sub-resource with no owner column needs an **explicit ownership join**; "the parent was checked"
  is not a guarantee.
- An identifier is not a credential: a `device_id` or a `lease_token` proves nothing on its own. Bind the
  lease to `(token, expiry, resource, owner)` and verify it against the authenticated identity.
- On mutations: `SELECT … FOR UPDATE`, verify ownership **inside** the transaction, check `affectedRows`, and
  make a mismatch an **idempotent no-op / 404** — a distinguishable error turns the endpoint into an
  existence oracle.

## 3. No secrets or PII in responses — `API-SEC-SECRET-001`

```bash
grep -rnE 'FROM settings' src/query
grep -rniE 'select .*(password|secret|token|api_?key|private_key)' src/query
grep -rnE 'SELECT \*' src/query
```

**The incident this rule comes from:** an API key stored in the `settings` table was served by a public
`GET /v1/settings` and used for an unauthorized Cloudflare Worker deploy.

- Secrets do not live in a settings table. Until they move to a key store, the runtime filter is the only
  barrier — and no endpoint may bypass it.
- **Allow-list the response fields.** Never return whole rows; mask credential columns to `null`.
- A **permissive allow-list is a trap**: combine an exact deny-list *with* name and value detectors. Do not
  "allow everything not explicitly secret".
- Strip identity fields from public projections and honour "hidden" flags **fail-closed**.

If the project has a secret classifier, three ordering rules are load-bearing (each one is a bug that already
happened — the details are in `references/rules.md`):

1. **The inclusion allow-list runs before the value scan**, otherwise a legitimate key that merely *looks*
   like a secret gets filtered and the safety belt becomes the outage.
2. **A name exemption is anchored to its own dot-segment**, otherwise an innocuous word anywhere in the key
   disarms the match everywhere — fail-open, and silent.
3. **Exclusions match exactly**, never as substrings.

Filtering is **never silent**: log every removal once per key with the deciding rule.

## 4. Logs and telemetry without secrets or PII — `API-SEC-LOG-001`

```bash
grep -rniE 'logger\.(info|debug|warn|error)\(.*(token|cookie|authorization|password|session|email|JSON\.stringify\((headers|req|request|body|row))' src
grep -rnE 'console\.(log|error|warn|info|debug)\(' src --include=*.ts | grep -v '\.test\.ts'
```

Never log `Authorization`/Bearer, cookies, API secrets, tokens, passwords, auth bodies, or national id /
VAT / email. Log non-sensitive markers instead (`has_session_cookie=true`). No `console.*` in runtime paths.

Telemetry: never export a **raw** query string, a client IP read straight from a header, or a raw exception.
Sanitize the query (redact credential-like keys, email-shaped values, blobs), truncate the user agent, and
replace exceptions with a neutral error **after** the handler has built the response, so the real status and
payload survive.

## 5. Environment gates must be fail-SAFE — `API-SEC-ENV-001`

```bash
grep -rnE 'env\.NODE_ENV\s*(===|!==)\s*"(production|development)"' src
```

If the env schema defaults `NODE_ENV` to `"development"`, a production deploy that simply **omits** it makes
every `env.NODE_ENV !== "production"` gate **fail-open** — debug output and mock auth in production.

```ts
// WRONG — fail-open when NODE_ENV is unset in prod
if (env.NODE_ENV !== "production") returnDebugInfo();
// RIGHT — fail-closed, from raw process.env; unknown counts as production
export const isNonProdRuntime = new Set(["development", "test"]).has(process.env.NODE_ENV ?? "");
if (isNonProdRuntime) returnDebugInfo();
```

Mock auth must **abort startup** unless the raw `NODE_ENV` is exactly `development`/`test`.

## 6. Bound SQL — `API-SEC-SQL-001`

```bash
grep -rnE "(WHERE|SELECT|LIKE|VALUES|SET|ORDER BY)[^\n]*\$\{" src/query
grep -rnE "'\\\$\{" src/query          # a literal '${x}' is injection too
grep -rn 'client.query(' src           # use the parameterized execute
```

Always named bound params. **A SELECT literal is injection as well**: `'${lang}' as lang` is a hole.

Narrow exceptions: `LIMIT`/`OFFSET` only if they are schema-coerced numbers; column name and sort direction
only through an allow-list plus a ternary; `IN (…)` through a placeholder builder — and **merge** the params
it returns.

Adjacent correctness trap, same file: in a translation join, put the language filter **inside that join's own
`ON`**. On a second `LEFT JOIN` it cannot reduce rows — it only nulls the non-matching ones, so the query
returns N rows per source row. That inflates paginated responses *and* makes `rows[0]` without `ORDER BY`
return the translated row only sometimes: the bug filed as "sometimes it doesn't translate" that nobody
closes. With a single language both forms look identical, which is why it survives.

## 7. Structural resource caps — `API-SEC-LIMITS-001`

```bash
grep -rnE 'fetch\(' src | grep -viE 'signal|timeout|AbortSignal'
```

Every attacker-controlled collection, body, cursor, cache and outbound fetch needs an explicit cap **before**
the business logic runs. Reference values that worked: 16 MiB body, 100 items per batch (dedup first), 64 KiB
cursor with a mandatory expiry, 8 MiB response, 10s end-to-end fetch deadline held until the body is
consumed, bounded LRU + TTL for in-memory caches, recursion depth capped, stable `ORDER BY` with a max
`LIMIT` on paginated reads.

Per-identity rate limiting, if present:

- **Mount it after the route's auth**, so the bucket is the authenticated identity and not a shared NAT IP.
- Put the numbers in a **policy table**, not inline at the mount site: the policy name is part of the key, so
  a duplicate name silently merges two quotas.
- The PII-enumeration endpoint (a customer search) stays the strictest policy.
- A limiter that **fails open** when its store is down is a deliberate choice, not a bug: rate limiting is an
  availability control and authorization is upstream. Do not "fix" it to fail closed without a decision.
- Never log the identity value — log its *kind*. An IP is personal data.

## 8. Injection into downstream consumers — `API-SEC-OUTPUT-001`

```bash
grep -rniE 'javascript:|vbscript:|data:' src/services src/repositories
grep -rnE '\.csv|text/csv|writeCsv|toCsv|join\(","\)' src
```

A stored URL that will later be rendered or redirected to: reject `javascript:`, `data:`, `vbscript:`,
`file:`, protocol-relative `//host`, embedded credentials and CRLF — **on write and on read**. Rows already
in the database were written before the validation existed.

CSV: a cell starting with `=`, `+`, `-` or `@` (also after whitespace or a BOM) is executed as a formula by
spreadsheet apps. Use an RFC 4180 encoder that neutralizes formulas; never hand-concatenate CSV.

## 9. No trust from caller input — `API-SEC-TRUST-001`

```bash
grep -rniE 'header\(\s*["'"'"']?(x-session-token|is_logged_in|cf-connecting-ip|x-forwarded-for|x-real-ip|x-client-ip)' src
grep -rniE 'etag|if-none-match|304' src/middlewares
```

- Privileged claims (audience, embargo, "is logged in") are **signed**, not query params: HMAC-SHA256 over
  timestamp + method + exact URL, short anti-replay window, timing-safe compare, fail-closed with no secret.
- An explicit `Authorization` header takes **absolute precedence** and never downgrades to an ambient session
  cookie.
- Read the client IP through **one helper**, from the single header your edge actually sets, and validate the
  charset. Behind a proxy that forwards, the hop-by-hop headers are the *proxy's* address. Even the right
  header is spoofable unless the origin only accepts traffic from that edge (mTLS or IP allow-list) — so
  per-IP limits are an obstacle, not a barrier.
- Cache: default `private`/`no-store`; any `Authorization`/`Cookie` forces it. Evaluate `If-None-Match`
  **after** auth, never before — and derive the ETag from the body only once the handler has run.

## 10. Supply chain and build — `API-SEC-SUPPLY-001`

- Pin images and CI actions to a **digest/SHA**, never a floating tag.
- Build secrets through secret mounts; never write a token into a layer or a committed `.env`.
- Frozen, lockfile-exact production install.
- Distroless base, non-root, read-only runtime artifacts, deploy by immutable digest.
- Transport policy **fail-closed in production**: plaintext or unverified DB/cache/SMTP is rejected, not
  warned about.
- Do not add or widen a static-secret export in CI, and do not add a production deploy path with no approval
  gate.

---

## Gotchas

- **"It's behind the gateway" is not auth.** Every audit finding above was in a service someone believed was
  private.
- **A green test suite proves nothing here** if the tests are not mounted in CI. Check that the security
  tests actually run before trusting them.
- **Documentation that teaches the broken pattern reopens the defect.** When you fix instances of a pattern,
  fix the example in the project docs in the same PR, or the next query will reintroduce it.
- **Fix the form, not the instance.** Scan for the *shape* of the bug across the codebase (every `*_languages`
  join, every `fetch(` without a signal) rather than the one case the report named.
- **An exception is one line with a written reason**, in the allow-list — never a widened regex.

## Final report

```
Security review: <n> files  ·  <n> critical  ·  <n> blocking  ·  <n> notes
API-SEC-AUTH-001   PASS | FAIL <file:line — what and the fix>
API-SEC-IDOR-001   …
API-SEC-SECRET-001 …
API-SEC-LOG-001 · API-SEC-ENV-001 · API-SEC-SQL-001 · API-SEC-LIMITS-001
API-SEC-OUTPUT-001 · API-SEC-TRUST-001 · API-SEC-SUPPLY-001
Not applicable to this diff: <rules>
Verdict: BLOCKED | OK TO COMMIT
```
