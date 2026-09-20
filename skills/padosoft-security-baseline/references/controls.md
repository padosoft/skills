# Controls, by domain

Read the section for the domain you are working on. Each entry is a control plus **what makes it real** —
the part that is usually missing when the control is nominally present.

---

## 1. Access control and authorisation

- **Ownership derives from the authenticated identity**, never from a parameter, a header or a body field.
  An owner id that arrives in the request is an input, not a fact.
- **A presence check is not an authorisation check.** Validating that a record exists says nothing about who
  may touch it.
- **Beware the tautological check**: verifying a record against the very input it was fetched with always
  passes.
- **Nested sub-resources need an explicit ownership join.** Reaching a child by its own id, when the parent
  is what carries ownership, is the most common broken-object-level authorisation.
- **Multiple entry points to one resource share one gate.** A helper both paths call, not two
  implementations that agree today.
- **A guest branch gets the same rigour as the authenticated one.** It is usually written later and looser.
- **Authorisation is per action, not per resource.** Being allowed to read is not being allowed to cancel.
- **An empty authorisation hook is a hole with a name.** Generated request classes ship with a permissive
  stub; count how many are still empty.
- **Admin routes deny by default** and allow-list, rather than each route defending itself.
- **A test asserts that every route has authentication**, with a motivated allow-list for the deliberate
  exceptions — and rate limiting does **not** count as authentication. Match middleware names exactly: a
  substring match reports "covered" for anything whose name merely contains the right word.
- **Review privileges periodically.** Monthly, not weekly. The block that matters most is **permissions
  granted directly, outside roles** — a role review cannot see them. Also: empty roles, and orphan
  assignments where a reused identifier inherits access nobody granted.
- **Require re-authentication before privilege changes.** Editing users, roles or permissions is the action
  a stolen session is worth the most for.

## 2. Authentication and identity

Covered in depth by **`padosoft-auth-hardening`**. The headline controls: rate limiting keyed on **both**
account and address; uniform responses so nothing enumerates accounts; breached-password rejection at every
point a password is chosen; absolute session lifetime in addition to the sliding one; one revocation path
shared by every door that can change a password; second factor rolled out audit-first; notification on a
new sign-in context, computed so it does not fire on every browser update.

## 3. Injection

- **Parameterise everything**, and treat the raw-expression escape hatches of your query builder as the
  place to look first: ordering columns and directions taken from input, literals interpolated into a
  projection, dynamic table names.
- **An allow-list for sort column and direction**, never a string passed through.
- **Escaping is the default; the unescaped form is the exception** and deserves a standing inventory. That
  applies to the back-office and to transactional email too, not only to public pages.
- **Rich text authored in a back-office must render fully and execute nothing**: sanitise against an
  allow-list of elements and attributes, rather than escaping it into uselessness or trusting the author.
- **In the browser, build nodes rather than concatenating markup.** A value that arrives through a data
  attribute and is written as HTML is the same injection with a different name.
- **Run external commands with an argument array, never a composed string.**
- **Do not deserialise a payload you did not sign**, and restrict the classes that may be constructed. If a
  serialised value must survive a round trip through a client, sign it.
- **Spreadsheet formula injection in exports**: a value beginning with an operator becomes a formula in the
  recipient's spreadsheet. Neutralise at the single writing choke point, and note that machine-to-machine
  feeds are deliberately left alone — a quoting prefix breaks the parser downstream.
- **XML parsing with external entities disabled**, on every parser, including the ones inside import and
  marketplace integrations.
- **Header injection**: anywhere a header, a reply address or a redirect target is built from input.
- **Server-side request forgery** deserves its own guard at the single outbound choke point: reject
  non-HTTP schemes, loopback, private and carrier-grade ranges, the cloud metadata address, credentials in
  the URL, and control characters — **with name resolution enabled**, because without it a hostname that
  resolves to loopback walks straight through. Mark the call sites that accept untrusted URLs; a guard that
  is off by default protects nothing.

## 4. Cryptography and secrets

- **Capability tokens are keyed message authentication codes over the parameters**, not a hash of public
  values. Compare in constant time, and guard the type of what arrives — an array where a string was
  expected has defeated more than one comparison.
- **Secrets are not rows in an application settings table.** Where that is already the case, a redactor is
  the only barrier and it is one mistake wide; treat migrating to a key store as work, not as a preference.
- **Secrets never reach the browser**, never sit in the repository, and never appear in a log.
- **Secret scanning runs on the diff as a blocking check, and over the history as a report.** The history
  starts as a report on purpose: a job born red is disabled within a week, and then the diff is unprotected
  too. It becomes blocking after the triage.
- **Rotating the application key invalidates sessions, cookies, signed links and stored tokens.** Plan the
  four, then rotate.
- **Personal data encrypted at rest at the application level** is a separate decision from disk encryption,
  and the one that survives a database copy.
- **Transport encryption to the database, cache and mail server, verified** — a policy in warn-only mode
  means plaintext passes in production.
- **Key rotation has a schedule and a per-environment separation**, or the answer to "when did this last
  change" is "never".

## 5. Configuration

- **Security boundaries are not governed by settings**, and an empty setting never means "off".
- **The environment gate fails closed** — see **`padosoft-environment-gating`** for why the answers are
  three and not two.
- **Debug mode off in production, verified per deployment**, not per repository. A debug error page exposes
  the environment and the stack.
- **A content security policy that is actually restrictive**: no unsafe inline or eval, a per-response
  nonce, frame ancestors set with your legitimate embedders in mind, and a reporting endpoint. A permissive
  policy left commented in the file will be uncommented by somebody one day.
- **Strict transport security with a sensible default when unconfigured.** Preloading is effectively
  irreversible and is an operations decision, not a default.
- **The rest of the response headers set by one middleware**, and three things go wrong here: a header with
  a misspelled name or the wrong syntax is silently ignored by every browser; headers that reach only the
  happy path miss redirects, error pages, cached responses and other route groups; and a middleware that
  overwrites a header set deliberately elsewhere breaks something it never knew about.
- **Cookies**: secure, HTTP-only and an explicit same-site value written down rather than inherited.
  Encrypting the session invalidates every open session on deploy, so it is a release decision.
- **Cross-origin policy restrictive**, and never a wildcard origin together with credentials.
- **The administrative interface is not on the public internet** if it does not have to be.
- **Nothing is listable or fetchable that should not be**: environment files, version-control directories,
  logs, backups. Test it from outside with a request, not by reading the configuration.
- **Who emits what, between edge and origin, is written down once.** Both emitting a header is the split
  brain that produces a control nobody owns.

## 6. Software supply chain

- **Audit the lock file, not a dashboard.** The count differs, and the lock is what ships.
- **"Does it reach the bundle" is the criterion for front-end advisories**, not the dependency section it is
  declared in — under many bundlers a development dependency ends up in the shipped bundle.
- **Pin images and pipeline actions to an immutable digest.** Resolve the digest from the dereferenced
  commit: on an annotated tag the first result is the tag object, which the runner will not resolve.
- **Automated dependency updates on, major versions excluded from the automation.** A green build is not
  evidence that a major upgrade is correct.
- **A generated lock file from a bot is a notification.** Whoever lands it regenerates the lock in a stable
  environment.
- **Run the audit on the pull request and on a schedule.** An advisory published tomorrow concerns code
  nobody is touching; a pull-request-only audit never sees it.
- **Scan the container image** — operating system packages, libraries and embedded secrets — on changes and
  on a schedule. Ignore the unfixable, or you teach people to ignore the output.
- **Generate a bill of materials per release and keep it longer than the pipeline's default retention**,
  which is shorter than any audit horizon.
- **Private registry tokens have the narrowest scope that works**, and are not reused for a second purpose.

## 7. Build and delivery integrity

- **No direct pushes to the release branch; protection enforced by the platform**, not by convention.
- **An approval gate before production.** A deploy triggered by a tag push, with no reviewer, means whoever
  can tag can ship.
- **Short-lived federated credentials in the pipeline**, not long-lived cloud keys in variables.
- **Build secrets through a secret mount**, never written into an image layer.
- **Deploy by immutable digest.**
- **Every workflow declares its permissions explicitly.** A workflow that declares none inherits the
  repository default, which is usually far wider than it needs — and the most exposed one is whatever
  triggers on an event any outsider can cause, such as a comment.
- **Security tests run in the pipeline, with the selection computed rather than hard-coded**, so a new test
  is included by being written.
- **Signed commits** on protected branches, if the threat model includes a compromised contributor account.

## 8. Logging, detection and alerting

- **Authentication events recorded**: failures, lockouts, resets, revocations — with the account identified
  by a **keyed pseudonym rather than the address**, so a log kept for months does not become a second copy
  of the customer database. Distinguish "the account existed" from "it did not": that is what separates
  enumeration from brute force.
- **Custom sign-in paths emit the same events.** Framework listeners only see the framework's own path.
- **No credentials and no personal data in logs**, with the masking **tested on the nested case** — the
  silent failure is a masker that only looks at the top level.
- **Retention long enough for an investigation**, and confirm nothing else prunes it earlier, and that the
  volume holds **under attack**, which is when the file grows.
- **Concurrent writers never append directly to a shared file.** Buffer through a queue with a single
  consumer, or use a real locked append; a read-modify-write disguised as an append is quadratic and loses
  data — see **`padosoft-logging-discipline`**.
- **The audit trail is tamper-evident**: a keyed signature per record detects modification, and a sequence
  number from a counter held **outside the file** detects deletion and reordering. Use a key separate from
  the application key, so one compromise does not also grant the ability to rewrite the record of it.
- **Detection without alerting is not detection.** A scheduled check counts events in a window and notifies
  above a threshold, with anti-flood, and reads the log with a bounded tail so it does not fall over exactly
  when the file is large. Thresholds get tuned on real numbers; half-tuned alerting is silenced and then
  absent when it matters.
- **A runbook for when the alert fires**: contain before you understand, do not destroy the evidence while
  containing, severity levels, the first fifteen minutes for a leaked credential, and — the part usually
  missing — **who to call**, filled in by name.
- **A correlated request identifier end to end**, or reconstructing a session is manual.

## 9. Exceptional conditions

- **Technical errors never reach the user**, in layers: the handler, the message extractor, and a safety net
  that catches what got past both. Internal identifiers — class names, table names, paths — are technical.
- **Guards fail closed**: an error looking up a permission denies rather than allows.
- **Mutations that must not double-spend take a lock and check the affected row count.** Carts, stock,
  coupons, points and balances are the classic four — see **`padosoft-atomic-invariants`**.
- **Webhook replay must not duplicate an effect**, and **every** provider's signature must actually be
  verified — routes exempted from anti-forgery protection because they are "signed" are exempted whether or
  not the verification is there. See **`padosoft-durable-effects`**.
- **A mismatch produces the same response as a non-existent record**, or the difference is an oracle.
- **Timeouts and a circuit breaker on every external dependency**, and a written answer to what the checkout
  does when a gateway does not respond.

## 10. Rate limiting and anti-automation

- **Structural caps before the business logic**: body size, collection length, cursor size, response size,
  end-to-end deadline, recursion depth, concurrency.
- **Limits keyed on identity where there is one**, falling back to the address only for anonymous traffic —
  limiting the user rather than the address avoids blocking a whole office because of one of its members.
- **An availability control may fail open**, and that is the right choice for a limiter backed by a cache
  that is down; say so, and know that it makes the edge the only remaining brake.
- **An inventory of what is *not* limited.** The endpoint that was outside the throttled group is the one
  that gets found: bulk exports, search, geolocation lookups, anything expensive but legitimate.
- **Bot management and managed rules at the edge**, checked for exceptions added long ago for a false
  positive that nobody removed.

## 11. Business-logic abuse

Nothing automated finds these. This is where threat modelling earns its keep — perimeter, actors, entry
points and **trust boundaries**, then per threat an explicit decision: mitigate, accept, defer.

Two questions that find more than the standard list: *what if a component I trust is compromised?* and
*if this fails, does it fail open or closed?*

- **Prices, discounts and totals recomputed server side at commit**, never accepted from the payload.
- **Codes with enough entropy, and a per-code attempt limit** as well as a per-address one.
- **Credits and points accrue idempotently**, from an immutable ledger.
- **An order is confirmed only on a verified callback**, cross-checked against what was requested.
- **Differentiated responses are an oracle**: a 500 here, a 403 there and a 200 elsewhere tells the caller
  which case they hit. That includes a refusal that explains *why* — expired versus revoked is a fact you
  are handing over.
- **Twin endpoints protected asymmetrically** is the single most reliable place to find a hole.

## 12. Data protection and privacy

- **Collect only what the purpose requires**, and review the fields against the purpose periodically.
- **Automatic deletion at the end of retention**, with the coverage actually checked: orders, logs,
  abandoned carts, guests, mailing lists, staged uploads.
- **Erasure covers every location**: the database, the backups, the logs, the search index, and every
  third-party processor the data was sent to. An erasure that stops at the primary database is not one.
- **A repeatable export procedure** for a subject request.
- **Consent recorded with a timestamp and the version of the notice**, and revocable.
- **An inventory of processors** with the purpose and the location of the data.
- **Personal data sent to a model is a transfer to a third party.** Know what leaves.
- **Backups encrypted, and the restore tested** — an untested backup is not a backup, and this is also the
  ransomware control.
- **Development dumps anonymised**, especially where testing at production-like volume is required.

## 13. Uploads and files

- **The stored name is generated**, never the client's name placed into a path; check **every** dotted
  segment, not the last one.
- **The destination is chosen by the server.** A request that names its own storage target lets the client
  pick among every configured disk, including the ones served over the web.
- **Type and size validated, executable extensions refused.**
- **Malware scanning at the choke point, failing closed when enabled** — and enabling it without a reachable
  engine blocks every upload, so the flag and the engine ship together.
- **Files served from a separate origin or bucket, never from a path the application server can execute.**
- **Private downloads behind a signed URL with an expiry.**
- **Decompression bounded**: uncompressed size and record count, or an archive is a denial of service.
- **Staged uploads have a lifecycle.** The temporary area that nothing ever cleans becomes a permanent,
  unindexed, publicly-reachable archive.
- **Transfers stream rather than load.** Reading a file into memory to write it elsewhere is a memory spike
  proportional to whatever the user sent.

## 14. API surface

- **An inventory of routes, and which ones write without authentication.** Keep the exceptions in a file
  with a reason each, and report the orphans — an exception that outlives its route authorises silently
  when that name comes back.
- **Property-level authorisation both ways**: an allow-list for what may be written, and one for what is
  returned.
- **Responses from third parties validated structurally before use**, not merely error-handled.
- **Internal endpoints removed rather than gated.**

## 15. Browser surface

- **Integrity attributes on third-party scripts — but classify first.** An integrity hash on a URL that
  tracks a moving version makes the resource **vanish** on the provider's next release, with no server-side
  error: worse than not having it. Pinned resources get an integrity hash; unpinnable ones are covered by a
  host allow-list in the content policy instead. Watch for references that look pinned and are actually
  major-version ranges.
- **Frame ancestors set with your legitimate embedders in mind.**
- **Cross-document messages validate the sender's origin.**
- **Session binding to a client fingerprint** raises the cost of using a stolen cookie; measure what it
  actually rejects before claiming it.
- **Third-party tags are arbitrary code on your origin.** Whoever governs them for performance is not
  governing them for security.

## 16. Mobile surface

Everything follows from one premise: **the bundle is on every device and can be opened**. See
**`padosoft-mobile-security-review`**. Headline controls: no secrets or internal endpoints in the bundle;
tokens in the platform keychain rather than plain storage; certificate pinning where the network is hostile;
deep links validated as entry points; test and debug flags provably off in release; a way to force an
upgrade away from a version with a known flaw.

## 17. Infrastructure and edge

- **The origin accepts traffic only from the edge.** Everything else in this section is downstream of it.
- **The application's database user cannot drop or grant.** It bounds the damage of an injection.
- **Data stores not reachable from the internet**, and authenticated over an encrypted transport.
- **Backups encrypted, off-site, immutable, and restored as an exercise.**
- **Dangling DNS records removed** — many subdomains is a real takeover surface.
- **Mail authentication published and enforcing**, or your domain can be used to phish your own customers.
- **A patch service level for the operating system and every runtime.**
- **An inventory of what answers on the internet**, refreshed.
- **Recovery objectives declared and proved**, not stated.

## 18. Process and governance

- **The security rules are written down and applied in review.** This is the control most teams do not have,
  and it is what turns a fix into a floor.
- **Security changes carry a label**, so the whole set is answerable in one query — for an audit, for a
  customer, or for you. A fix that stays open is an exposure window.
- **Fixes land as small changes with a regression test**, not as one large pull request that nobody can
  review and that stays open for weeks.
- **Threat modelling before writing**, at least for anything touching money, identity or personal data.
- **Penetration testing on a defined cadence** — annually and on any architectural change — with the
  findings tracked to closure.
- **A published vulnerability disclosure contact** that is a monitored mailbox. A channel that does not
  answer is worse than none. If the file declares an expiry, compute it rather than writing a date nobody
  will remember to update.
- **An incident response runbook, written cold**, with roles, isolation steps, key rotation and the
  regulatory notification window.
- **Access revoked on offboarding**, everywhere: source control, cloud, edge, database, back-office.
- **Determine formally which compliance regimes apply.** The answer changes the obligations on logging,
  scanning and segmentation, and guessing it is not an answer.

## 19. AI and model surface

See **`padosoft-agent-host-boundaries`** for the host-side contract. The security-specific controls:

- **Content from the database is delivered to a model as delimited data, not as instructions**, with the
  delimiters neutralised — and nothing depends on the model respecting it. It is a mitigation, not a
  guarantee.
- **A tool must not be able to do more than the user who opened the session can do.**
- **Model output is untrusted input.** No query, column name, sort direction, URL, path or command comes
  from it, and its content is escaped exactly like any other user input.
- **A cost cap per user per day**, in addition to a rate limit.
- **Destructive tools require a dry run and a human confirmation.**
- **Every tool invocation logged**: who, what, when.
