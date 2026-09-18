# API security rules (normative)

> **Levels** — **MUST**: blocking, the commit does not go through. **SHOULD**: the default, an exception is
> justified in the report.
> Every rule has a stable identifier quoted by the checks in `SKILL.md`.
> **Origin** — these rules were extracted from a production API: a 2026-07 security audit, the findings of a
> hardening PR, and one real incident. Where a rule says "this is how X happened", it happened.

Read a section when its check fires and you need the reasoning, or when you have to decide whether a case is
a genuine exception.

---

## API-SEC-AUTH-001 — Auth on every route, role guard, RBAC

**MUST.** Every mutating endpoint (POST/PUT/PATCH/DELETE) is authenticated, and every route group has an auth
middleware.

*Origin: an audit found a whole authoring surface, a returns list and a customer search publicly reachable.
The cause in each case was an auth middleware **commented out** and never restored.*

- A commented-out auth line is a **critical** bug. There is no "temporarily disabled".
- Internal endpoints (spec dumps, debug routes) are **deleted, not gated**.
- Pick the middleware by audience: back-office/authoring vs customer-facing data.

**Authentication is not authorization.** A middleware that resolves any valid user token authenticates a
customer just as well as an employee, when both are rows of the same users table. Staff-only endpoints need a
**positive role check** mounted after it:

```ts
app.use(`${receiptsRoutes.path}/*`, operatorAuthMiddleware());
app.use(`${receiptsRoutes.path}/*`, requireOperatorRoleMiddleware(["SALES_ASSOCIATE", "admin"]));
```

Do **not** use a negative predicate ("the user has no customer row") as the staff gate: it under-blocks
generic internal accounts and over-blocks **hybrid operators** — staff who are also customers. That is why
the negative form was replaced by the role allow-list. The role lookup re-checks the link atomically and
**fails closed (503)** on a database error.

**Sub-app flattening (Hono).** When several sub-apps mount on the same prefix, `route.use("*", authMw)`
*inside* a sub-app is flattened by the framework and the wildcard leaks to its siblings. Apply auth on the
**exact path**, where the app is composed.

**RBAC.** Never "holds any `namespace.*` permission ⇒ may do anything in that namespace". Use a per-**action**
fail-closed matrix: editor ≠ approver, reviewer ≠ editor. State transitions atomic; a forced lock takeover is
admin-only.

**Anti-patterns:** a commented `.use(auth…)`; a mutating route in a group with no auth; a negative-predicate
staff gate; `use("*")` inside a sub-app on a shared prefix; an internal endpoint gated instead of removed.

---

## API-SEC-IDOR-001 — Ownership from the authenticated id only

**MUST.** Derive the owner id **only** from the authenticated context. Never trust a customer/order/receipt/
device id taken from query, body or param for ownership; scope the SQL to the authenticated id.

*Origin: a public returns endpoint (IDOR), plus nested-resource and device-binding findings in review.*

```ts
// WRONG — the target comes from the request
const customerId = c.req.valid("query").customer_id;
// RIGHT — from the authenticated context, and the WHERE is scoped by it
const customerId = getCustomerId(c);
if (!customerId) throw new ApiError(401, { code: "UNAUTHORIZED" });
```

- **Nested sub-resources.** A child row with no owner column needs an explicit ownership join back to the
  authenticated id. Do not assume "the parent was checked".
- **An identifier is not a credential.** A `device_id` does not authorize a mutation on that device.
- **Lease/lock tokens are not authorization.** Bind the token to `(token, expiry, resource, owner)` in one
  query and verify it against the authenticated identity. Possession alone grants nothing.
- **Mutations:** `SELECT … FOR UPDATE`, verify ownership inside the transaction, check `affectedRows`, and
  return an **idempotent no-op / 404** on mismatch. A distinguishable error is an existence oracle.

---

## API-SEC-SECRET-001 — No secrets in settings or responses

**MUST.**

*Origin: the real incident. An API key stored in a database settings table was served by a public settings
endpoint and used for an unauthorized Cloudflare Worker deploy.*

1. **Never store secrets, API keys or tokens in a database settings table.** The structural fix is a
   centralized key store. Until it lands, the runtime redactor is the only barrier.
2. **Public settings endpoints must pass through the secret filter. Never bypass it.**
3. **Allow-list response fields.** Never `SELECT *` to the client; mask credential columns to `null`.
4. **A permissive key allow-list is a trap.** Combine an exact deny-list **with** name and value detectors.
   Do not "allow everything not explicitly secret".

### The classifier: order of evaluation

`classify(key, value?)` returns `{ secret, rule, detail }`; the first layer that answers wins.

| # | Layer | Meaning |
|---|---|---|
| 1 | `KEY_ALLOWLIST` | **Inclusions**: a real client consumes this key. Never removed, even if name *and* value look like a secret |
| 2 | `EXCLUDED_KEYS` | Exact deny-list, audited, one comment per non-obvious entry |
| 3 | `NOT_SECRET_KEYS` | **Exclusions**: sensitive-sounding name, public config. **Exact match** |
| 4 | Name heuristic | Evaluated **per dot-segment**; the exemption applies only to the segment that matched |
| 5 | `detectSecret(value)` | Value scan: `ghp_`/`github_pat_`, `AKIA`/`ASIA`, `AIza`, `GOCSPX-`, `xox*`, PEM, JWT, webhook URLs |

Three bugs are encoded in that ordering, each of which already happened:

- **The allow-list runs before the value scan.** A legitimate Maps key holds a value in `AIza…` format:
  scan-first would filter it and break Maps in production. An inclusion must beat every detector, or the
  safety belt becomes the outage.
- **The name exemption is anchored to its segment.** As a `test()` over the whole key, an innocuous word
  anywhere disarmed the match everywhere: `shop.tax.account_id.api_key` passed because `account_id` exempted
  an `api_key` living in a different segment. Fail-open, and silent.
- **Exclusions match exactly.** A substring exclusion exempts keys that have nothing to do with the word.

**Filtering is never silent.** Log every removal once per key (capped set) with the deciding rule, so a
legitimate key caught by the filter shows up in the log instead of as a mysteriously broken client. A
heuristic-only filter was once reverted precisely because it removed live configuration with no trace.

**Cross-repo drift.** If another service owns the authoritative list of sensitive keys, vendor that list into
a test that fails when one gets through. In practice it caught 14, among them an HTTP Basic password, a
payment signature and five webhook URLs.

**Do not add a value pattern for a public identifier** — an OAuth *client id* lives in the browser by design;
filtering it breaks login with nobody able to say why. Target the secret half of the pair.

**Do not remove a row from the deny-list because "a client needs it".** It moves to the inclusion allow-list,
with the motivation. The row stays classified as secret.

**PII in public projections.** Strip identity fields; honour "do not show on web" flags **fail-closed**.

---

## API-SEC-LOG-001 — Logging, telemetry and error leak

**MUST.** Never log `Authorization`/Bearer, cookies/session, API secrets, tokens, passwords, or auth
request/response bodies. Log non-sensitive markers instead (`has_session_cookie=true`). Never log national id,
VAT number, email or whole customer rows.

*Origin: the auth middleware logged the session cookie, the API secret, the bearer token and the upstream
body; the error handler leaked internals; telemetry exported raw query strings, IP/UA and raw exceptions.*

No `console.*` in runtime paths. Query debugging stays gated to non-production.

**Telemetry.** Total redaction makes telemetry useless for debugging, so the workable policy is:

- **Query string**: exported with only the sensitive values redacted (credential/PII keys, known secret
  shapes, email-like values, blobs over ~128 chars). Never a raw query string.
- **User agent**: exported, truncated.
- **Client IP**: exported through the one helper (`API-SEC-TRUST-001`), never a header read directly.
- **Fragment**: never exported.
- **Exceptions**: replaced with a neutral error **after** the handler has built the response, so the real
  status and payload survive. Never raw messages or stacks.

**The error handler must not leak internals in production**: search-engine details, stacks and raw
`err.message` stay behind the non-production gate. The client gets a generic message and a trace id — never a
stack, a cloud diagnostic, or a driver error.

---

## API-SEC-ENV-001 — Environment gates must be fail-SAFE

**MUST.** Never gate security on the *parsed* `NODE_ENV`.

*Origin: mock auth enabled with no environment cross-check, plus two fail-open gates found in review.*

If the schema declares `NODE_ENV: z.…default("development")`, a production deploy that **omits** the variable
resolves it to `"development"`, and every gate written as `env.NODE_ENV === "production"` is **fail-open**.

```ts
export const isNonProdRuntime = new Set(["development", "test"]).has(process.env.NODE_ENV ?? "");
export const isDevRuntime = process.env.NODE_ENV === "development";
const isProd = !isNonProdRuntime;   // missing/unknown counts as production
```

Mock auth must **abort startup** unless the raw value is exactly `development`/`test`.

---

## API-SEC-SQL-001 — Bound SQL

**MUST.** Always named bound params. **Never interpolate a request string into SQL text** — not in the
`WHERE`, and **not as a SELECT literal**: `'${x}' as col` *is* injection.

*Origin: two endpoints interpolated a language parameter as a SELECT literal.*

Narrow exceptions: `LIMIT`/`OFFSET` only from schema-coerced numbers; column name and sort direction only via
an allow-list plus a ternary; `IN (…)` via a placeholder builder, converting CSV to an array first and
**merging** the returned params. Never the non-parameterized query method.

### Translation joins: constrain inside the join's own `ON`

```sql
-- WRONG — the language filter sits on a SECOND LEFT JOIN, which cannot reduce rows
LEFT JOIN province_languages pl ON province.id = pl.province_ID
LEFT JOIN languages lp ON pl.languages_ID = lp.id AND lp.code = :lang

-- RIGHT — languages first, then the translation join constrained on BOTH ids
LEFT JOIN languages lp ON lp.code = :lang
LEFT JOIN province_languages pl ON province.id = pl.province_ID AND pl.languages_ID = lp.id
```

Two effects, and the second costs more:

1. **Response amplification** — adjacent to `API-SEC-LIMITS-001`. One query returned 25 rows per postcode
   with 5 languages, and `LIMIT`/`OFFSET` paginated over the inflated rows.
2. **Correctness on lookup-by-id.** The query returns N rows of which exactly one carries the translation;
   the repository does `rows[0]` and there is no `ORDER BY`, so which row arrives first is the engine's
   choice. The translation appears and disappears with nothing changed — the defect filed as "sometimes it
   doesn't translate" that never gets closed. With a single language both forms behave identically, which is
   why it survives.

Fix it by **scanning for the form** — every join onto a translations table — not by chasing the one instance
a report named. Guard it with a test that **discovers** the joins by reading the source, that fails if the
parser stops finding joins at all (green without having checked anything is not a pass), and that fails if a
declared exception points at a join that no longer exists.

⚠️ If the project documentation teaches the broken form as the example to follow, rewrite it in the same PR.
Fixing instances while leaving the documentation that teaches them reopens the defect on the next query.

---

## API-SEC-LIMITS-001 — Structural resource caps

**MUST.** Every attacker-controlled collection, body, cursor, cache and outbound fetch has an explicit cap
**before** the business logic runs.

*Origin: the largest single cluster of review findings, plus an audit item for missing rate limiting.*

Canonical values that worked: 16 MiB global body; 100 items per batch after dedup; 20 groups × 100 values ×
500 total on batch endpoints; 64 KiB cursor with mandatory expiry; 8 MiB response; 10s end-to-end fetch
deadline **held until body consumption**, not just headers; LRU 250 entries / TTL 15 min for in-memory
caches; recursion depth 32 authoring / 8 runtime to prevent stack exhaustion and pool starvation; FIFO
semaphore max 4; DB pool 10; stable `ORDER BY` with a max `LIMIT`/`OFFSET` on paginated reads.

**Per-identity rate limiting.** The caps above are per-request: they make each single call harmless and leave
the aggregate unbounded.

- **Mount the limiter after the route's auth**, so the bucket is the authenticated identity, not a shared NAT
  IP. Identity priority: operator id → customer id → client IP → a shared `unknown` bucket. The first two are
  not spoofable, they come from the token.
- **Policies live in a table**, not inline at the mount site: the policy name is part of the store key, so a
  duplicate name silently merges two quotas. Test for it.
- The **customer-search** endpoint stays the strictest policy: it is the PII enumeration surface.
- **The limiter fails OPEN when its store is unavailable.** Deliberate, and not a contradiction of
  `API-SEC-ENV-001`: rate limiting is an availability control, and failing it closed turns a cache blip into
  a full outage. Authorization is upstream and does not depend on it. Do not "fix" this without a decision.
- The enable flag defaults to **true**; only an explicit `false` disables it.
- **Never log the identity value** — log its *kind*. An IP is personal data.

Known and accepted: a fixed window allows a 2× burst across the boundary.

**Outbound fetch**: every call to an external host needs an abort signal/timeout and a response-size cap.

---

## API-SEC-OUTPUT-001 — Injection into downstream consumers

**MUST.**

*Origin: stored-XSS URLs and CSV formula injection, both found in review.*

**Stored active URLs.** A URL persisted and later rendered or redirected to must reject `javascript:`,
`data:`, `vbscript:`, `file:`, protocol-relative `//host`, embedded credentials and CRLF. Validate on
**write and read** — rows already in the database were written before the validation existed, so they are
neutralized at render time, not trusted.

```ts
const u = new URL(value);
if (u.protocol !== "http:" && u.protocol !== "https:") reject();
if (u.username || u.password) reject();
if (/[\r\n]/.test(value)) reject();
```

**CSV formula injection.** A cell whose value starts with `=`, `+`, `-` or `@` — including after leading
whitespace or a BOM — is executed as a formula by spreadsheet applications. Use an RFC 4180 encoder that
neutralizes formulas on every cell derived from user or database data. Never hand-concatenate CSV.

---

## API-SEC-TRUST-001 — No trust from caller input

**MUST.** Never derive a trust decision from a caller-supplied header or param. Login state comes from
server-side auth; privileged claims are signed.

**Signed claims.** Audience, embargo, "is logged in", timestamps must not be caller-controlled query params.
Sign them: HMAC-SHA256 over timestamp + method + exact URL, ~300s anti-replay window, timing-safe compare,
**fail-closed** when the signing secret is absent (≥32 chars).

**Authorization precedence.** An explicit `Authorization` header takes absolute precedence and must never
downgrade to an ambient session cookie (cookie tossing). The session cookie name is configured exactly;
duplicates and wildcards are rejected; the identity cache is keyed by cookie name too; failures return a
uniform 401.

**Client IP.** Read it through one helper, from the single header your edge actually sets. Behind a CDN the
hop-by-hop header holds the *proxy's* address, not the client's. Validate against a charset allow-list.
⚠️ Even the correct header is spoofable if a request reaches the origin bypassing the edge — trust it for
audit, rate limiting and abuse **only** if the origin is locked to that edge (authenticated origin pull /
mTLS or an IP allow-list). Until then, per-IP limiting is an obstacle, not a barrier.

**Cache / ETag after auth.** Default `private`/`no-store`. A narrow allow-list of anonymous GETs is matched on
**segment boundaries**, not broad prefixes. Any `Authorization`/`Cookie` forces `private`/`no-store`. Derive
the ETag from the body **only after** handler and middleware ran — never evaluate `If-None-Match` ahead of
auth. Exclude geo-dependent responses from a shared cache.

---

## API-SEC-SUPPLY-001 — Supply chain, container, CI/CD

**MUST.**

1. **Pin images and CI actions to a digest/SHA**, never a floating tag: mutable bases allow silent behaviour
   changes.
2. **Build secret mounts**, never a token written into a build layer or a committed `.env`.
3. **Frozen production install**, lockfile-exact, no implicit resolution at build time.
4. **Pin downloaded models/assets by commit + per-file size and SHA-256**, with an offline smoke test; a
   remote fallback only under an explicitly dev/test runtime.
5. **Distroless base, non-root, read-only runtime artifacts, deploy by immutable digest.**
6. **Transport policy fail-closed in production**: plaintext or unverified DB/cache/SMTP is rejected, not
   warned about.

**CI/CD.** Do not export static cloud keys into the job output, and do not add a production deploy path with
no approval gate. Target state: OIDC instead of static keys, an environment with required reviewers, and
SAST / dependency / image / secret scans.

---

## API-SEC-LLM-001 — AI and LLM surface

**SHOULD**, until the service actually talks to a model — then **MUST**.

Write this one **before** the need. The decisions that make an AI surface safe (where authorization lives,
what the model may touch, what it may never touch) are cheap up front and expensive to retrofit, and the
first PR that adds a model is exactly when nobody has time to think about them.

Every rule above applies unchanged to an AI endpoint. In addition:

- **Authorization never lives in the prompt.** The model may propose an action; the server authorizes it with
  the same checks it would apply to a direct call (`API-SEC-AUTH-001`, `API-SEC-IDOR-001`).
- **Model output is untrusted input** for whatever consumes it: a URL it produced goes through
  `API-SEC-OUTPUT-001`, a query it suggests through `API-SEC-SQL-001`.
- **Tool/function handlers are endpoints.** Cap them (`API-SEC-LIMITS-001`), scope them to the authenticated
  identity, and never expose one that the caller could not invoke directly.
- **Prompts and completions are logs**: they carry PII and secrets (`API-SEC-LOG-001`). Redact before
  storing, and do not ship them to a third party without a decision.
