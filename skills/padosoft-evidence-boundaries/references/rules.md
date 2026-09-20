# Substitutions by domain

Read the section for the domain the claim sits in. Each row is the same shape: what is usually offered as
proof, and the part of the claim it leaves untouched.

These are worked instances of the table in §1 of SKILL.md. They are here rather than in the skill because
you only need the one domain you are reviewing.

---

## Storage, encryption and backup

| Offered as proof | Leaves unproven |
|---|---|
| A green run against a compatible or emulated implementation | the real provider's key identity, IAM policy, object-lock posture, replication |
| The API accepted an encryption option | that the provider applied that mode, with that key — read the object metadata back |
| A successful dump | that a restore works; the evidence is a **fresh read** from the restored copy |
| A restore duration field below the objective | the duration itself: derive elapsed time from trusted timestamps and reject disagreement |
| An injected or mocked storage client in a test | locking, serialisation and failure semantics of the real engine |
| Retention deletes the published row | every other persisted copy — staged, draft, cached — and the race between them |

A backup journey must run against a **disposable** target with its own credentials, fail closed when the
protected environment is missing, and say in writing that it is not point-in-time, key-management or
replication evidence.

## Identity and access

| Offered as proof | Leaves unproven |
|---|---|
| Discovery documents and token fixtures | that issuer, client, redirect URI, verifier, secret and userinfo endpoint work **together** — that needs a freshly issued one-time code |
| One successful login | rotation, logout, failover, provisioning, certificate rotation. State the boundary. |
| Issuer validation | endpoint validation — they are separate trust decisions |
| A userinfo response | authentication: it is a profile read, not a proof of the authentication event |
| A code verifier for a one-time-password algorithm | enrolment, secret storage, recovery codes, replay limits — a verifier is not a lifecycle |
| A policy flag saying multi-factor is required | that the policy boundary consumes the claim **before** the session is persisted |
| A provisioning endpoint that authenticates | tenant scoping: reject cross-tenant ids, and paginate **after** the tenant filter or counts and identities leak |
| A bearer token that verifies | its lifecycle: digest at rest, constant-time comparison, expiry, rotation, tenant binding |
| Filtering a list by tenant | that a write cannot cross tenants — the storage key itself must carry the authenticated scope |

Never verify a signed assertion format with hand-written pattern matching. Use a maintained verifier, then
enforce issuer, audience, time, replay and least privilege in a small deterministic boundary of your own.

## Telemetry and observability

| Offered as proof | Leaves unproven |
|---|---|
| Configuration files that lint and scan clean | that a scrape, an export, an alert evaluation or a dashboard query works |
| An exporter accepting a span | that the metrics endpoint can be scraped, or that anything was delivered |
| A successful scrape | delivery on the other transport — assert each leg separately |
| A unit test of the exporter | the wiring: exercise it through the real runner and drain before asserting |
| Reading one output stream of a collector | its confirmation, which may be on the other stream |

Telemetry is never the source of truth: exporters sample, drop and reorder. Bound the export queue, redact
before serialisation, give shutdown an explicit drain contract, and keep the durable record independent of
whether delivery succeeded.

## Queues, workers and effects

| Offered as proof | Leaves unproven |
|---|---|
| An in-memory queue test | migration locks, lease fencing, serialisation failures — run the journey on the real engine |
| A verified signature on an incoming event | idempotency: a valid retry still executes capture or fulfilment twice |
| Reclaiming a stale lease | that the previous holder had not already completed the external effect |
| Stopping a timer | that an in-flight request was cancelled; check the active flag after every await |
| Limiting worker concurrency | state isolation: two scenarios can still mutate the same fixture. Declare the policy and record it |
| An idempotency key | anything, unless it is qualified by the authorised scope **and** a canonical payload fingerprint |
| A conditional create statement | that a multi-step bootstrap is safe across replicas — share a transaction-scoped lock |

Claim the logical effect key **atomically before** running the effect; treat the same event as a duplicate,
and reject a different event reusing that key. A lost lease is ownership loss, not an ordinary failure: abort
the handler and report it as its own outcome rather than acknowledging or failing the job.

## Supply chain and release

| Offered as proof | Leaves unproven |
|---|---|
| Hardened runtime flags | the bytes: a mutable tag can change the executable between runs. Require an immutable digest and fail before dispatch |
| A tested sandbox package | that the shipped runner selects it — wire it at the host boundary |
| A signature on a manifest | the content the manifest points at |
| A parsed signing bundle | a trust decision: bind payload, certificate identity, issuer and transparency evidence, and fail closed without a policy |
| A verified integrity hash | who signed it — integrity is not authenticity |
| A clean dependency dashboard | a release gate: run the audit after every lockfile change, and re-run the bundle and the full suite after a toolchain upgrade |
| A library contract | operational use — expose it as a shipped command or it will be bypassed |

One repository can have more than one dependency perimeter, and shipped examples are part of the supply
chain.

## Money and settlement

| Offered as proof | Leaves unproven |
|---|---|
| A parsed provider status | reconciliation: status must be reconciled against amounts, not merely read |
| Equal amounts | inclusion — that this specific item is in that specific payout |
| Exposure to a dispute | settlement; they are separate lifecycles, as are recurring billing and disputes |
| A quote | the final figure, and quote amounts do not identify the cart they came from |
| An order identifier | fulfilment identity |
| A timeout from a provider | a negative result — the operation may have succeeded |
| Cart-time promotion validity | validity at commit: cart pricing is stale by definition, re-check at the boundary |
| A declared budget in a schema | enforcement: it must affect scheduling and the release state, and exhaustion at charge time is also a budget event |

Compare monetary values in minor units with an exact integer type, require a single currency, reject
duplicate instruments, and give financial timestamps a canonical timezone. A ledger is not a counter.

## Data protection

| Offered as proof | Leaves unproven |
|---|---|
| A sanitised logger | the response body: the outbound error is an independent disclosure path |
| Text redaction | binary artifacts — screenshots, documents and captured trace archives need their own classification |
| A digit-count rule for card numbers | anything good: it rewrites timestamped identifiers. Use the checksum the format has |
| Bounded field length | that the field is safe; length is not a secrecy control |
| An in-process metrics registry | that exposing it is safe — an unauthenticated scrape leaks whatever is in the labels |

Redaction must never mutate identity: a pass that can rewrite a correlation id or an audit hash breaks the
chain it exists to protect. See **`padosoft-logging-discipline`** for where the redaction goes per stack.
