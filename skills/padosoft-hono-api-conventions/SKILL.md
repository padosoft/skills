---
name: padosoft-hono-api-conventions
description: >-
  Use this skill when writing or reviewing code in a Hono API on Bun — a new endpoint, a middleware, a
  repository or a SQL query — and whenever the user works on a controller/repository/query layer, types a
  Hono context, adds a paginated or localized list, or hits a symptom like "the type of c.get is any", "it
  returns null instead of an empty list", "page 1 skips records", "sometimes the translation is missing" or
  "the middleware types don't line up": it applies the three-layer architecture, the typed-context and
  middleware-factory patterns, and the recurring mistakes that cost the most. Do not use it for the security
  review of an endpoint (padosoft-api-security-review) nor for OpenAPI spec changes.
license: MIT
compatibility: >-
  Hono on Bun with TypeScript. The database patterns assume a driver with named placeholders (mysql2 style);
  the layering and typing rules hold with any driver.
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: node, api
  scope: project
  repository: https://github.com/padosoft/skills
  keywords: hono, bun, typescript, api, architecture, repository, sql, middleware, zod
---

# Hono API conventions

The conventions that a Hono/Bun API needs applied consistently, and the mistakes that keep coming back. The
goal: an endpoint that goes through review without the same five comments every time.

---

## 1. Three layers, one direction

**Controller → Repository → Query.** Each layer has exactly one job, and the dependency only ever points
downwards.

| Layer | Does | Never does |
|---|---|---|
| **Controller** (`src/controllers/`) | Reads the validated input (`c.req.valid("query"\|"json"\|"param")`), calls the repository, maps relations, returns `c.json(data, status)`, throws `ApiError` | SQL, business transformations |
| **Repository** (`src/repositories/`) | Calls the query, executes it, **transforms** the data, handles caching and transactions | Builds SQL strings, touches the HTTP context |
| **Query** (`src/query/`) | **Only** SQL building. Returns `[sql, params] as const` | Business logic, execution, transformation |

```ts
// src/query/loyalty/query.ts — returns the tuple, executes nothing
export function queryGetLevels(lang: string) {
    const sql = `SELECT id, COALESCE(t.descr, b.descr) AS descr
                 FROM levels b
                 LEFT JOIN languages l ON l.code = :lang
                 LEFT JOIN level_languages t ON t.level_ID = b.id AND t.languages_ID = l.id
                 ORDER BY b.id`;
    return [sql, { lang }] as const;
}

// src/repositories/loyalty/repository.ts — executes and transforms
export async function getLevelsRepo(lang: string) {
    const [sql, params] = queryGetLevels(lang);
    const [rows] = await client.execute<(RowDataPacket & Level)[]>(sql, params);
    return rows;                   // empty result → [], never null
}
```

Returning the tuple `as const` is what keeps the query layer pure and testable: a query test asserts on the
SQL string and the params, with no database.

## 2. Typed context, no assertions

Define **every** context variable in one central `Env` type, and let inference do the rest.

```ts
// src/types/env.ts
export interface AuthContext { customerId: number }
export interface Variables { auth?: AuthContext }
export interface Env { Variables: Variables }
```

```ts
// ❌ a hand-rolled shape, and a cast at every read
export function getCustomerId(c: { get: (k: string) => any }) { … }
return c.get("auth") as AuthContext | undefined;

// ✅ the real Context type, and the value is already typed
import type { Context } from "hono";
export function getCustomerId(c: Context<Env>) { return getAuth(c)?.customerId; }
return c.get("auth");
```

Every `as` on a context read means the `Variables` type is missing an entry. Fix the type, not the call site.

## 3. Middleware through the factory

```ts
// ❌ hand-typed handler: the Env generic is lost downstream
import type { MiddlewareHandler } from "hono";
export const authMiddleware = (): MiddlewareHandler<Env> => async (c, next) => { … };

// ✅ factory: the context stays typed inside the middleware and after it
import { createFactory } from "hono/factory";
const factory = createFactory<Env>();
export const authMiddleware = () => factory.createMiddleware(async (c, next) => {
    c.set("auth", { customerId });     // no assertion needed
    await next();
});
```

## 4. Environment variables through one module

```ts
import { env } from "bun";        // ❌ unvalidated, no types, fails at runtime
import { env } from "@/lib/env";  // ✅ schema-validated, fails fast at startup
```

The env module parses with a schema and **aborts on startup** when something is missing or inconsistent. A
missing variable has to break the boot, not the first request that needs it.

## 5. SQL: named placeholders and dynamic building

Named placeholders (`:name`) everywhere, never string interpolation — a SELECT literal is injection too
(`padosoft-api-security-review`, `API-SEC-SQL-001`).

```ts
// IN (…) — build the placeholders, and MERGE the params back
let params: Record<string, unknown> = { lang };
const [placeholders, arrayParams] = buildArrayPlaceholders("id", ids);   // ids is an ARRAY
sql += ` WHERE id IN (${placeholders})`;
params = { ...params, ...arrayParams };   // forget this → "Unknown parameter :id_0"
```

**Localize in SQL, not in the application.** `COALESCE(t.descr, b.descr)` beats
`row.descr_translated || row.descr`: one round trip, and the fallback is the same for everyone.

**Constrain the translation join inside its own `ON`** — the language filter on a second `LEFT JOIN` cannot
reduce rows, so you get N rows per source row: inflated pagination, and `rows[0]` picking a random row when
there is no `ORDER BY`. That is the "sometimes it doesn't translate" bug. Full explanation in
`padosoft-api-security-review` (`API-SEC-SQL-001`).

## 6. Transactions on multi-write

**A repository function that performs two or more writes (INSERT/UPDATE/DELETE) wraps them in a transaction
on a single connection.** Without it a partial failure leaves half the operation applied.

```ts
const conn = await client.getConnection();
try {
    await conn.beginTransaction();
    await conn.execute(sqlDelete, p1);
    await conn.execute(sqlInsert, p2);
    await conn.commit();
} catch (e) {
    await conn.rollback();
    throw e;
} finally {
    conn.release();
}
```

Pre-screen on the staged diff:

```bash
git diff --cached --name-only --diff-filter=ACMR | grep -E '^src/repositories/.*\.ts$' | while read f; do
  writes=$(grep -cE 'execute(<[^>]+>)?\(\s*["`]?\s*(INSERT|UPDATE|DELETE)' "$f")
  tx=$(grep -cE 'beginTransaction|getConnection' "$f")
  [ "${writes:-0}" -ge 2 ] && [ "${tx:-0}" -eq 0 ] && echo "⚠️  $f — $writes writes, no transaction"
done
```

A function whose name or docstring promises all-or-nothing semantics ("atomic", "bulk replace", "publish",
"transition") and has no transaction is a **critical** finding, not a warning. If the function only delegates
to another repository that already opens the transaction, it is fine.

## 7. Caching with a circuit breaker

Cache in the **repository**, never in the query or the controller. A cache is an optimization: when the cache
store is down the endpoint keeps answering from the database, so the cache client sits behind a circuit
breaker and a failed read is a miss, not a 500. Bound every in-memory cache with a size **and** a TTL.

## 8. Validation at the edge

The schema validates at the route, the controller reads the already-validated value. Never re-validate by
hand inside the controller, and never read `c.req.query()` raw when a validated schema exists.

**Lenient in the request, strict in the response.** An invalid optional parameter (a bad language code) is
treated as *absent* and resolved by the server fallback — never a 422 caused by that field alone. The same
field in a response or an entity stays strict: the documented contract does not bend.

---

## Gotchas

These are the ones that come back in review:

**1. `null` instead of an empty array.** The controller expects a list.

```ts
if (!rows.length) return null;   // ❌ callers crash on .map
if (!rows.length) return [];     // ✅
```

**2. Pagination offset.** `offset = page * perPage` makes page 1 skip the first page.

```ts
const offset = (page - 1) * perPage;   // ✅ page 1 → 0
```

**3. A CSV string passed where an array is expected.** `"1,7,9"` is one element, not three. Split and coerce
to numbers first.

**4. Params of a dynamic `IN` not merged** — see §5. The symptom is `Unknown parameter :id_0`.

**5. Language fallback in application code** instead of SQL `COALESCE` — see §5.

**6. A type assertion on the context** — see §2. It always means a missing `Variables` entry.

**7. `rows[0]` on a query that can return more than one row with no `ORDER BY`.** Which row arrives first is
the engine's choice, so the behaviour changes without the code changing.

---

## Checklist before committing

- [ ] Query returns `[sql, params] as const` and contains no business logic
- [ ] Repository returns `[]` and not `null`; transformations live here
- [ ] Controller does no SQL and throws `ApiError` instead of returning an error shape
- [ ] No `as` on a context read; `Variables` updated if one was needed
- [ ] Middleware built with the factory
- [ ] Named placeholders only; `IN` params merged; translation join constrained in its own `ON`
- [ ] Two or more writes in one repository function → transaction
- [ ] `env` imported from the validated module
- [ ] Offset computed as `(page - 1) * perPage`
- [ ] Linter and type check clean

## Final report

```
Endpoint/change: <what>
Layers: controller <file> · repository <file> · query <file>
Conventions: <n> respected, <n> deviations (with reason)
Gotchas checked: null-vs-[] · offset · IN merge · localization · context typing · transactions
Linter/types: PASS | FAIL <detail>
To decide: <…>
```
