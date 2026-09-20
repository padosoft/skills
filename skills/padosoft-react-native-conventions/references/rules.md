# React Native rules (catalogue)

> **Origin.** These rules were distilled from the code-review history of two production React Native apps.
> Ninety of them were **textually identical in both repositories** — that is the filter applied here: what
> survived in two different products, not what sounded right once.
>
> **Why the IDs.** In the source repositories the rules were numbered `#1…#139`, and the numbering **drifted**:
> `#96` and `#100` name completely different rules in the two apps, and `#64` and `#71` name the same topic
> with a different API. A citation like "see rule #96" was ambiguous across repos. The `RN-AREA-NNN` ids here
> are stable and do not renumber when something is inserted.

Levels: **MUST** blocks the commit · **SHOULD** is the default, an exception is justified in the report.

---

## RN-UI — Components and design system

| ID | Lvl | Rule |
|---|---|---|
| RN-UI-001 | MUST | Use the shared text / button / pressable components, never the bare platform primitives |
| RN-UI-002 | MUST | Icons through the shared icon component with a name, never a direct icon-library import |
| RN-UI-003 | MUST | `expo-image`, never `Image` from react-native |
| RN-UI-004 | MUST | Styling through the utility-CSS layer, not inline style objects |
| RN-UI-005 | MUST | Press feedback comes from the shared component (`android_ripple`), never a manual `active:opacity-*` on top |
| RN-UI-006 | MUST | Never a custom accordion: use the shared one |
| RN-UI-007 | MUST | Prefer shared-component defaults; an inconsistent override is a bug in disguise |
| RN-UI-008 | MUST | Use the resolved `styles`, never the defaults object, in render |
| RN-UI-009 | MUST | Never a `Pressable` (or any View-based component) as a child of `<Text>` |
| RN-UI-010 | MUST | No `leading-none` on text inside button, chip, tab or badge — it clips descenders |
| RN-UI-011 | MUST | One component per file. No `native/` or `screen/` subfolders inside `screens/` — flat |
| RN-UI-012 | MUST | No IIFE `(() => {…})()` inside JSX — extract a memoised component |
| RN-UI-013 | MUST | Never duplicate inline rendering when a reusable component exists |
| RN-UI-014 | MUST | Never pass `className` to a variant helper — compose it outside |
| RN-UI-015 | MUST | Never override the full border radius token |
| RN-UI-016 | MUST | Static `accessibilityLabel` never hardcoded on a shared primitive |
| RN-UI-017 | MUST | `accessibilityLabel` on a non-interactive `View` requires `accessible` |
| RN-UI-018 | MUST | Text with interactive styling (underline, link-bold) always has a handler |
| RN-UI-019 | MUST | App-specific screens never in the shared core package; components never under the core `screens/` |
| RN-UI-020 | SHOULD | Keep the image zoom-transition wrapper on images that have one |

## RN-PERF — Performance and memoisation

| ID | Lvl | Rule |
|---|---|---|
| RN-PERF-001 | MUST | Every exported component wrapped in `memo()` **and** given `displayName` |
| RN-PERF-002 | MUST | `useCallback` on every function passed to a child or used as a handler |
| RN-PERF-003 | MUST | `useMemo` on derived computations |
| RN-PERF-004 | MUST | Dependency arrays contain **every** reactive value read: theme colours, router, `t`, refs, selector values, props |
| RN-PERF-005 | MUST | In a dependency array use the root object, never an optional path (`obj?.field`) |
| RN-PERF-006 | MUST | Never wrap a module-level constant in `useMemo` |
| RN-PERF-007 | MUST | Memoise string transformations performed in render |
| RN-PERF-008 | MUST | Never a list inside a slot of another list; object props of a list are stable references |
| RN-PERF-009 | MUST | Never enable a query at mount in a component rendered as a list item |
| RN-PERF-010 | SHOULD | Prefer a batch query to N+1 queries |
| RN-PERF-011 | MUST | Centralised cache times, no inline `staleTime`/`gcTime` |

## RN-STATE — Store

| ID | Lvl | Rule |
|---|---|---|
| RN-STATE-001 | MUST | Shallow selector on every store property read; array form preferred for multiple values |
| RN-STATE-002 | MUST | Register every new store field in the schema, or it is silently not persisted |
| RN-STATE-003 | MUST | `setState()` outside a component is not reactive and carries no action name — pure functions only |
| RN-STATE-004 | SHOULD | Prefer the store to direct key-value storage for system data |
| RN-STATE-005 | MUST | Capture **all** filter sources when saving a search state |
| RN-STATE-006 | MUST | Add default values before spreading in an update |
| RN-STATE-007 | MUST | Clamp a state index when the array behind it can shrink at runtime |
| RN-STATE-008 | MUST | When a new state replaces a default literal, audit every downstream consumer |
| RN-STATE-009 | MUST | A module-level counter detecting concurrent instances counts **active** instances (mount `++`, unmount `--`), never cumulative mounts |

## RN-QUERY — Data fetching

| ID | Lvl | Rule |
|---|---|---|
| RN-QUERY-001 | MUST | Query keys include **every** parameter the query function uses |
| RN-QUERY-002 | MUST | Never type `useQuery`/`useInfiniteQuery` manually; never rebuild the returned object |
| RN-QUERY-003 | MUST | Invalid parameters → `enabled`; never fake data, never nullable request params, never a key whose shape changes with validity |
| RN-QUERY-004 | MUST | Use the shared key builders, never hand-written key arrays |
| RN-QUERY-005 | MUST | Query hook options: a local non-exported interface, not an inline type |
| RN-QUERY-006 | **MUST** | **Never a key parameterised on state that a consumer of that query writes** — see the feedback-loop note below |
| RN-QUERY-007 | MUST | Never write a backend response into the cache without checking its shape; never dereference a response array in render without a tolerant selector |
| RN-QUERY-008 | MUST | A skeleton gated only on `isLoading` is wrong for a conditionally `enabled` query — gate on `!data` too |
| RN-QUERY-009 | MUST | Never derive a one-shot UI notice from a field persisted in a long-lived cache entry — consume it or keep it ephemeral |
| RN-QUERY-010 | SHOULD | Use the button's `loading` prop for mutation pending states |

**RN-QUERY-006, the feedback loop.** If an effect that consumes a query also writes a parameter of its key,
changing it switches to a different cache entry — a snapshot taken at a different time. Two disagreeing
snapshots make the effect an oscillator: it writes `b`, the key switches, `b`'s snapshot says `a`, and so on
synchronously (the cache answers immediately, even stale) until `Maximum update depth exceeded`. With
persistence the loop survives an app restart.
The shape: a countries query keyed per locale, consumed by an effect writing the locale. A language removed
and re-added on the backend leaves two entries holding different pictures.
**Fix:** one key **without** the parameter plus explicit invalidation when it changes — a sanctioned exception
to RN-QUERY-001, documented in a comment — with a **single root-level owner** of the invalidation listener,
never per-instance (N mounted consumers would fire N invalidations). Plus a ping-pong detector on the
automatic writer, recording the **context** of the decision: an inversion caused by the user genuinely
changing context is legitimate and must not be blocked.

## RN-RENDER — Rendering and lifecycle

| ID | Lvl | Rule |
|---|---|---|
| RN-RENDER-001 | MUST | Never `setState` or mutate a ref during render — use an effect |
| RN-RENDER-002 | MUST | Never call navigation (`replace`/`back`) during render |
| RN-RENDER-003 | MUST | An effect registering a subscription always returns its cleanup |
| RN-RENDER-004 | MUST | A side effect gated on X must not sit after an early return on an unrelated Y |
| RN-RENDER-005 | MUST | Gate rendering on nullable derived data while loading |
| RN-RENDER-006 | MUST | Render the error state of an async load **before** the placeholder/empty branches |
| RN-RENDER-007 | MUST | Never dereference an imperative native handle's `ref.current` without `?.` — it is nulled at unmount and a late event can still reach the last committed handler |
| RN-RENDER-008 | MUST | Never implement a custom error boundary — use the router's route-level one |
| RN-RENDER-009 | MUST | Treat items with an unresolved async value as **blocking** when computing a gating set for destructive actions |
| RN-RENDER-010 | MUST | Validate numeric route params with a finite-number check |
| RN-RENDER-011 | MUST | Never introduce a filter that can empty a list without revising the empty state |
| RN-RENDER-012 | MUST | Never remove the debounce from an input driving a query |
| RN-RENDER-013 | MUST | Show a toast when input validation fails |

## RN-LIST — Lists

| ID | Lvl | Rule |
|---|---|---|
| RN-LIST-001 | MUST | Never `array.map()` for dynamic lists — use the virtualised list |
| RN-LIST-002 | MUST | An infinite-scroll list is the primary scroll container, never nested in another |
| RN-LIST-003 | MUST | No `overrideItemLayout` together with paging |
| RN-LIST-004 | MUST | On a horizontal list, intrinsic-width cells switch off the default layout animation, or every recycle animates the width and the cells overlap |
| RN-LIST-005 | MUST | Horizontal list with paging or snapping: use the project's snapping props preset |

## RN-ANIM — Animation

| ID | Lvl | Rule |
|---|---|---|
| RN-ANIM-001 | **MUST** | **Never read a shared value right after assigning `withTiming`/`withSpring`** — it still holds the previous value |
| RN-ANIM-002 | MUST | Shared values through `.get()`/`.set()`, never direct `.value` access or mutation |
| RN-ANIM-003 | MUST | A layout animation is a mount cost across the whole surface — never on a constant-frame wrapper, never in a dense mount window |
| RN-ANIM-004 | SHOULD | Prefer native-driven animation |

**RN-ANIM-001.** `withTiming`/`withSpring`/`withDecay` return **immediately** and animate on the UI thread, so
right after the assignment the value is still the old one. Anything in the same callback that re-reads it to
derive state — a gesture `enabled` flag, an `isZoomed`/`isOpen` boolean, a bridge call to JS, a second
animation whose target depends on the first — sees the stale value. **The bug is silent: the animation plays,
so it looks right**, and only the derived state is wrong. Only synchronous assignments (a pinch handler
writing `sv.value` directly) are readable immediately. Pass the target you already know, or derive from the
completion callback.

## RN-NAV — Navigation

| ID | Lvl | Rule |
|---|---|---|
| RN-NAV-001 | MUST | Navigation through the router, never an imperative navigation API |
| RN-NAV-002 | MUST | A section that is not a tab in **every** app is reached by its own path, never an explicit tab-group href |
| RN-NAV-003 | MUST | A cross-cutting HOC is applied once on the screen definition, never repeated per route file |
| RN-NAV-004 | MUST | Never derive per-instance state from a global routing hook in components that stay mounted under tabs — anchor the scope to the owning route |
| RN-NAV-005 | MUST | The anchor option follows the **topology** of the destination |
| RN-NAV-006 | MUST | First screen of a nested stack: with a visible header back, the explicit back goes in the header-items slot, never in `headerLeft` |
| RN-NAV-007 | MUST | Safe-area wrapper only for non-scrollable content |

## RN-LAYOUT — Adaptive layout

| ID | Lvl | Rule |
|---|---|---|
| RN-LAYOUT-001 | MUST | Breakpoint convention: one prefix for tablet portrait, one for landscape |
| RN-LAYOUT-002 | MUST | **Structural** layout choices use the layout hooks, never CSS breakpoints |
| RN-LAYOUT-003 | MUST | The layout class is measured on the **window**, reactively — never a module constant, the device idiom or the aspect ratio |
| RN-LAYOUT-004 | MUST | Forms, onboarding and auth wrapped in the adaptive container on non-full-width screens |
| RN-LAYOUT-005 | MUST | Master-detail through the two-column layout plus a fallback detail route |
| RN-LAYOUT-006 | MUST | Font scaling on hero title and subtitle only, never body or UI chrome |
| RN-LAYOUT-007 | MUST | Never `Dimensions.get("window")` for layout decisions |
| RN-LAYOUT-008 | MUST | Sticky blurred footers through the shared component; padding depends on whether it sits inside or outside the tabs |

## RN-THEME — Colour and theming

| ID | Lvl | Rule |
|---|---|---|
| RN-THEME-001 | MUST | Use the `bg-X` / `text-X-foreground` pair, never a literal colour beside a token that inverts |
| RN-THEME-002 | MUST | Gate backend `*Color` fields on the dark flag when a `*ColorDark` counterpart exists |
| RN-THEME-003 | MUST | When a setting changes `contentFit`/layout, every dependent style is gated on the same value |

**RN-THEME-001, the signal to look for first:** a `dark:` override block that repeats the **same colour
classes** as the light one is almost always a bug — the two blocks exist precisely to differ. Either the
classes are already theme-aware (and the duplication is pointless) or one of the two is wrong.

## RN-I18N — Localisation

| ID | Lvl | Rule |
|---|---|---|
| RN-I18N-001 | MUST | Add keys in **every** supported language |
| RN-I18N-002 | MUST | A new locale bundle is registered in the locales tuple |
| RN-I18N-003 | MUST | Plural/context families always carry a **base** key next to the suffixed ones |
| RN-I18N-004 | MUST | Spanish `¿`/`¡` closed with `?`/`!` |
| RN-I18N-005 | MUST | Add the i18n key for the header of a new account route |
| RN-I18N-006 | MUST | Never a locale-sensitive formatter per call — build one object per (locale, options) and reuse it |
| RN-I18N-007 | MUST | Never a hardcoded locale in a date/number formatter — use the active language |

## RN-TS — TypeScript hygiene

| ID | Lvl | Rule |
|---|---|---|
| RN-TS-001 | MUST | Never `as` to assert what is already validated or already inferred |
| RN-TS-002 | MUST | If a package's types are missing, fix the package — never an `as` workaround |
| RN-TS-003 | MUST | No pass-through re-exports or alias types — update the imports at the point of use |
| RN-TS-004 | MUST | Barrel files use `export *`, never hand-maintained named exports |
| RN-TS-005 | MUST | Destructure custom props **before** spreading onto a native component |
| RN-TS-006 | MUST | Never add unused props or parameters |
| RN-TS-007 | MUST | Consistent naming, no typos in names |
| RN-TS-008 | MUST | Never a dynamic import without a documented reason |
| RN-TS-009 | MUST | Boolean API fields arriving as strings go through the dedicated type |
| RN-TS-010 | MUST | Never a transform producing a valid-empty value before a schema default |
| RN-TS-011 | MUST | Adding a strict field to a **shared** schema can break the other consumers — check them |
| RN-TS-012 | MUST | Never `??` to fall back between sources when the first can hold a non-nullish sentinel |
| RN-TS-013 | MUST | No comments above or beside imports at the top of a file |
| RN-TS-014 | MUST | Update comments when the behaviour they describe changes |

## RN-LOG — Logging

Three rules, all of which are instances of **`padosoft-logging-discipline`** — read that skill for the
reasoning and the per-stack mechanism:

| ID | Lvl | Rule |
|---|---|---|
| RN-LOG-001 | MUST | Never `console.*` — use the project logger |
| RN-LOG-002 | MUST | Never a full API request/response at `info` — `debug` |
| RN-LOG-003 | MUST | Never pass a raw `Error` to the logger — wrap it with the serializer |
| RN-LOG-004 | MUST | Never a constant error name when recording a handled crash — it collapses every error into one issue |
| RN-LOG-005 | MUST | Never report an OS-retained history without checking it belongs to the **installed** build |

## RN-DIAG — Diagnosing

| ID | Lvl | Rule |
|---|---|---|
| RN-DIAG-001 | MUST | "Maximum update depth exceeded" and every crash diagnosis: **classify before fixing**, and write each claim with its degree of evidence |
| RN-DIAG-002 | MUST | Static drift guards: strict at discovery, with verified premises and counter-evidence |

**RN-DIAG-001** is the rule that pays for itself. A render loop has several possible causes (RN-QUERY-006,
RN-RENDER-001, RN-ANIM-001, an unstable list prop); picking one and "fixing" it produces a change that looks
plausible and does nothing. Classify the cause, state what is proven and what is inferred, then fix.
