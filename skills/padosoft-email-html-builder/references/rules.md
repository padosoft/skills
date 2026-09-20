# Email HTML — Rules (normative)

> **Levels** — **MUST**: blocking, the email does not ship. **SHOULD**: the default, an exception has to be justified in the report. **MAY**: optional.
> Every rule has a stable ID (`R-xxx`) quoted by the `scripts/lint_email.py` linter and in the delivery report.
> **Sources** — [MT] Mailtrap (HTML Check on caniemail.com data, SpamAssassin, Blacklist, Template Inspector, best-practice blog) · [MU] MailUp (Check-up/Controlla, HTML editor manual, email design checklist, "10 HTML mistakes") · [GY] Gmail/Yahoo bulk sender requirements · [WCAG] 2.2 AA · [XP] mistakes found across five revisions of a real welcome template, verified on Mailtrap.
> Where the sources disagree, the **most restrictive rule verified in the field** wins ([XP] > [MT] > [MU]); the divergence is noted.

---

## 0. Principles

1. **The Mailtrap HTML checker reports every property present, it does not evaluate fallbacks** [MT][XP]. `bgcolor` next to `background-color` does NOT clear the warning: the property has to be **removed**.
2. **Layout = HTML attributes. CSS = inline typography only + progressive enhancement in the `<style>`.**
3. *"Be conservative in what you send"* [MU]: code that is robust on the worst clients (the Outlook Word engine) comes before modern solutions.
4. **Two quality gates**: Mailtrap (Market Support, SpamAssassin, Blacklist, HTML/Text) **and** MailUp Check-up (links, unsubscribe, weight, dynamic fields, tracking, spam, code). An email is ready only when it passes both.

---

## 1. Document structure

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-001 | MUST | `<!DOCTYPE html>`, `<html lang="xx">` with `xmlns:v` and `xmlns:o`. | MT, XP |
| R-002 | MUST | `<meta charset="utf-8">`, `viewport`, `X-UA-Compatible`, `x-apple-disable-message-reformatting`, `format-detection` (telephone/date/address/email/url = no). | MT, MU |
| R-003 | MUST | `<!--[if mso]>` with `OfficeDocumentSettings` (`AllowPNG`, `PixelsPerInch 96`). | MT |
| R-004 | MUST | Layout with **tables only**, `role="presentation" cellpadding="0" cellspacing="0" border="0"`. Layout divs, flex, grid, float and position are forbidden. | MT, MU |
| R-005 | MUST | Three-level structure [MU]: outer table `width="100%"` → container `width="600"` `align="center"` → content tables `width="100%"`. Modular blocks = independent nested tables. | MU |
| R-006 | MUST | 16px outer side gutter built with **spacer cells** (never padding). | XP |
| R-007 | MUST | Main heading as `<td role="heading" aria-level="1">` (not `<h1>`: its `margin` is reported on Outlook). Divergence: [MT] suggests `<h1>`; [XP] wins. | XP |
| R-008 | MUST | No empty or orphaned tags (`<font></font>`, `<span></span>`, `<p></p>`), no redundant attribute duplicating another. | MU |
| R-009 | SHOULD | HTML comments kept to a minimum (they add weight): only MSO conditionals and short section markers. | MU |
| R-010 | MUST | Well-formed HTML (balanced tags, quoted attributes, no duplicate IDs). W3C validation: the only acceptable errors are the intentional legacy attributes (`bgcolor`, `align`, `valign`, `width`, `height`, `border`, `cellpadding`, `cellspacing`, `marginwidth`…). | MU |
| R-011 | MUST | Forbidden: `<script>`, `<form>`, `<input>`, `<iframe>`, `<object>`, `<embed>`, `<video>`, `<audio>`, inline `<svg>`, `<link rel=stylesheet>`, `@import`, mandatory web fonts, `position`, JavaScript in attributes (`on*`). | MT, MU |

## 2. Weight

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-050 | MUST | HTML < **100 KB** (spam filter threshold [MT]; Gmail clipping ≈ 102 KB). **Target < 40 KB.** | MT, MU |
| R-051 | SHOULD | Minify at build time (strip whitespace and non-conditional comments) on the sending copy only; the source stays readable. | MT, MU |
| R-052 | MUST | A single image ≤ **50 KB** (JPG/PNG, 72 dpi); animated GIF ≤ **100 KB**; all images ≤ 500 KB. | MU |

## 3. Inline CSS — closed whitelist

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-100 | MUST | In the `style=""` of `<body>` elements, **only** these are allowed: `font-family`, `font-size`, `line-height`, `font-weight`, `font-style`, `letter-spacing`, `color`, `text-decoration`, `text-align`, `mso-*`. | XP |
| R-101 | MUST | **Forbidden inline**: `padding*`, `margin*`, `background*`, `border*`, `border-radius`, `width`, `height`, `max-*`, `min-*`, `display`, `opacity`, `overflow`, `visibility`, `outline`, `box-shadow`, `position`, `float`, `text-transform`, `table-layout`. | XP |
| R-102 | MUST | The only exception: the preheader with `style="display:none; mso-hide:all;"` (R-400). | XP |
| R-103 | MUST | Exception: the `style` of the VML `<v:*>` elements inside `<!--[if mso]>` (the checker does not analyse them). | XP |
| R-104 | MUST | Uppercase written in the text, not produced with `text-transform`. | XP |
| R-105 | MUST | Web-safe font stack with fallbacks: `Arial, Helvetica, sans-serif` / `Georgia, 'Times New Roman', serif` / `'Courier New', Courier, monospace`. Web fonts only as the first entry of the stack, never essential. Divergence: [MU] suggests inline `table-layout:fixed`; the fixed `width` attribute replaces it (R-801). | MT, MU |

## 4. Mandatory substitutions (CSS → attributes)

| ID | Lvl | Instead of… | Use… |
|---|---|---|---|
| R-200 | MUST | `background-color` | the `bgcolor="#rrggbb"` attribute on `table`/`td`/`body`. |
| R-201 | MUST | vertical padding | `<tr><td height="N" style="font-size:1px; line-height:Npx;">&nbsp;</td></tr>` (`colspan` when needed). |
| R-202 | MUST | horizontal padding | `<td width="N" style="font-size:1px; line-height:1px;">&nbsp;</td>`; `class="gut"` if it shrinks on mobile. |
| R-203 | MUST | `border:1px solid C` | an outer table `bgcolor="C" cellpadding="1"` wrapping the card table. |
| R-204 | MUST | a `border-top` divider | `<td height="1" bgcolor="C" style="font-size:1px; line-height:1px;">&nbsp;</td>`. |
| R-205 | MUST | CSS `width`/`height` | the `width` / `height` attributes. |
| R-206 | MUST | body margins | `marginwidth="0" marginheight="0" topmargin="0" leftmargin="0"`. |
| R-207 | MUST | default text color | `<body bgcolor text link vlink alink>` (avoids `HTML_FONT_LOW_CONTRAST` on `&nbsp;` cells). |
| R-208 | MUST | the gap under an image | container cell with `style="font-size:0; line-height:0;"`. |
| R-209 | SHOULD | inline `border-radius` | a class in the `<style>` (R-300); square corners on Outlook are accepted. |
| R-210 | MUST | CSS background images | a solid `bgcolor`; if unavoidable: the `background=""` attribute + VML `v:rect` for Outlook. [MT]: avoid them. |

## 5. The `<style>` block — minimal, compact

| ID | Lvl | Rule |
|---|---|---|
| R-300 | MUST | **One single** `<style>` in `<head>`, containing **only**: (a) 1 line of `border-radius` classes; (b) 1 mobile media query on 1 line; (c) optionally 1 line for auto-detected links `a[x-apple-data-detectors]` **only if** the template contains numbers/addresses/dates. |
| R-301 | MUST | Forbidden in the `<style>`: resets on `body`/`table`/`img`/`a`, preheader classes, `border-collapse`, `outline`, `visibility`, `-webkit-text-size-adjust`/`-ms-*`, `:root`, CSS `color-scheme`, `prefers-color-scheme`, `[data-ogsc]`, `u + #body`, `@font-face`, `@import`. |
| R-302 | MUST | `@media (max-width:620px){…}` — **without** `only screen and`. |
| R-303 | MUST | All the `border-radius` rules on **one line**; the media query on **one line** (the checker counts per line). |
| R-304 | MUST | No comment containing the literal string `<style`. |
| R-305 | MUST | Without the `<style>` the email stays **intact and readable** at 600px. |

Reference media query (standard classes):

```css
@media (max-width:620px){.wrap{width:100%!important}.col{display:block!important;width:100%!important}.vgap{display:block!important;width:100%!important;height:16px!important}.gut{width:20px!important}.h1m{font-size:26px!important;line-height:32px!important}.txtm{font-size:16px!important;line-height:24px!important}.imgm{width:100%!important;height:auto!important}}
```

## 6. Subject, preheader, charset, antispam

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-400 | MUST | Preheader `<!--[if !mso]><!--><div aria-hidden="true" style="display:none; mso-hide:all;">…</div><!--<![endif]-->`, **40–100 characters**, key information first, complementary to (not a repetition of) the subject, **without `color`**. | MT, MU, XP |
| R-401 | MUST | Invisible filler is **forbidden** (`&#847;`, `&zwnj;`, repeated `&nbsp;`, `&#8203;`): SpamAssassin decodes it → `DOS_BODY_HIGH_NO_MID` +2.4. | XP |
| R-402 | MUST | HTML **100% ASCII**: non-ASCII characters as numeric entities (`è`→`&#232;`, `·`→`&#183;`). | XP |
| R-403 | MUST | No text in a color equal or close to the background (`HTML_FONT_LOW_CONTRAST`), preheader and separators included. | XP |
| R-404 | MUST | A `text/plain` part always present and **aligned** with the HTML (same content, same links in clear text) — the "HTML/Text alignment" check of the Template Inspector. | MT |
| R-405 | MUST* | *Commercial/bulk email only; purely transactional messages are exempt.* `List-Unsubscribe: <https://…>, <mailto:…>` header + `List-Unsubscribe-Post: List-Unsubscribe=One-Click` (RFC 8058). | GY |
| R-406 | MUST | Subject: **35–50 characters** (hard max 60), specific, no ALL CAPS, no `!!!`/`$$$`, at most 1 emoji, no trigger words ("FREE", "URGENT", "100%", "click here"). Non-ASCII characters in the subject over SMTP: Quoted-Printable encoding (`=?utf-8?Q?…?=`), not Base64. | MT, MU |
| R-407 | MUST | Mailtrap SpamAssassin: **target ≤ 0.1** (in testing through the API only `MISSING_MID` 0.1 is allowed — the Message-ID is added by the MTA). Delivery blocking threshold: **≥ 1.0**. Mailtrap's "good" threshold < 5, marketing < 3: those are not targets, they are limits. | MT, XP |
| R-408 | MUST | Mailtrap blacklist report: **0 listings** for the sender IP and domain and for every linked domain; MailUp Check-up: no blacklisted link. | MT, MU |
| R-409 | MUST | No URL shortener (bit.ly and similar), no bare IP in links, link text consistent with the destination (no "www.example.com" pointing somewhere else). | MT, MU |
| R-410 | MUST | Text/image ratio **≥ 80/20** [MT] (absolute minimum 60/40 [MU]); never an "image only" email; the main message and the CTA in HTML text. | MT, MU |
| R-411 | SHOULD | Body text ≤ 1,000 characters for short promotional/transactional emails; short paragraphs; message and CTA above the fold. | MT |
| R-412 | MUST | Sender: authenticated domain with **SPF + DKIM + DMARC** (aligned), no `noreply@` when avoidable → use a monitored `Reply-To`. Sender name = the brand or "Person · Brand". | MT, GY |

## 7. Links, tracking, dynamic fields (MailUp Check-up)

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-450 | MUST | All links **absolute HTTPS** and working (HTTP 200 after redirects), none pointing at `example.com`/`localhost`/staging. | MT, MU |
| R-451 | MUST | Link tracking **enabled** and a **custom tracking domain** (brand CNAME) on the sending platform. | MU |
| R-452 | MUST | UTM on every link to the site: `utm_source`, `utm_medium=email`, `utm_campaign` required (`utm_content` for CTA/block); **no spaces** in the values (use `-` or `_`), lowercase. | MU |
| R-453 | MUST | Dynamic fields in the platform syntax (MailUp: `[fieldname]`), **enabled** and with a **default value** (e.g. "Hi [name]" → default "Hi"). In links: explicit protocol `href="https://[field]"`, otherwise the link is treated as local. | MU |
| R-454 | MUST* | *Commercial/bulk email only (see R-405); for transactional ones the linter downgrades it with `--transactional`.* An **unsubscribe** link, present and working, reachable in ≤ 2 clicks, in the footer, using the native placeholder/mechanism of the platform (MailUp: the list footer unsubscribe link — *placeholder syntax to be verified on the account*). | MU, MT, GY |
| R-455 | SHOULD | Summary/preview set on the platform (MailUp: max 100 characters), consistent with the preheader. | MU |
| R-456 | SHOULD | Consistent web analytics code (UTM or platform parameters), never two conflicting trackings. | MU |
| R-457 | MUST | Phone numbers as `href="tel:+39…"` without spaces; email addresses as `mailto:`. | MU |
| R-458 | MUST | Image/asset paths without spaces (e.g. `/img/welcome/`, not `/Image files/`) — spaces break Gmail. | MU |

## 8. Colors, dark mode, accessibility, typography

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-500 | MUST | Dark template: `<meta name="color-scheme" content="dark">` + `supported-color-schemes` = `dark`. Light one: `light`. **Never** `light dark` without a complete, tested dark theme. | XP |
| R-501 | MUST | WCAG AA contrast ≥ **4.5:1** for normal text (footer included), ≥ **3:1** for text ≥ 24px or ≥ 18.66px bold. Calculated, not estimated. | WCAG, XP |
| R-502 | MUST | Typography: headings ≥ **22px**, body ≥ **16px on mobile** (desktop ≥ 14px, through the `.txtm` class), card text ≥ 13px, legal ≥ 12px, CTA ≥ 15px, `line-height` ≥ 1.4. | MU, WCAG |
| R-503 | MUST | A palette of 2–3 functional colors (brand, accent/CTA, neutrals); every color has a role. | MU |
| R-504 | MUST | Decorative glyphs and separators `aria-hidden="true"`; `lang` and `<title>` filled in. | MT, WCAG |
| R-505 | MUST | DOM reading order = visual order (verifiable by removing the CSS). | WCAG |

## 9. Images

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-600 | MUST | Every `<img>`: absolute HTTPS `src`, `width` and `height` as **attributes**, `border="0"`, a **short** descriptive `alt` (≤ 60 characters; `alt=""` only when decorative). `title` optional [MU]. | MT, MU |
| R-601 | MUST | The image **cell** has `height="N"` and `bgcolor`: with images blocked (the Outlook default) the card keeps its shape and the alt stays readable. | XP |
| R-602 | MUST | @2x assets (e.g. 348×240 displayed at 174×120), JPG for photos / PNG for graphics, ≤ 50 KB (R-052), on the **brand CDN** (no `placehold.co` → `URIBL_BLOCKED`). | MU, MT, XP |
| R-603 | MUST | Never put essential text (price, discount code, CTA, dates) in an image only. | MT, MU |
| R-604 | MUST | Animated GIFs: a **complete, self-sufficient first frame** (Outlook 2007–2019 shows only that one); use them sparingly. | MU, MT |
| R-605 | SHOULD | Logo at the top, clickable through to the home page with UTM. | MT |

## 10. Bulletproof CTA

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-700 | MUST | Double rendering: `<!--[if mso]><v:roundrect … arcsize fillcolor stroke="f"><w:anchorlock/><center>…</center></v:roundrect><![endif]-->` + `<!--[if !mso]><!-->` table with `bgcolor` `width` `class="r10"` and `<td height="48" style="line-height:48px">`. | MT, MU, XP |
| R-701 | MUST | VML dimensions **identical** to the non-mso table. | XP |
| R-702 | MUST | Clickable area ≥ **46×46 px** (220×48 recommended); never `padding`/`display:block` on the `<a>`. | MT, XP |
| R-703 | SHOULD | One primary CTA per email, verb + object ("Browse the products"), visible above the fold; text/shape/color are A/B test candidates. | MU, MT |

## 11. Responsive

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-800 | MUST | **Mobile-first design** approach, single column preferred; multi-column only with `<td class="col" width="N">` + `<td class="vgap" width="12">` spacers. | MU, MT |
| R-801 | MUST | Column widths in **whole px**, summing to the container. Fractional percentages (`33.33%`) are forbidden. Divergence: [MU] suggests 47% instead of 50%; fixed px solve the same risk without rounding. | XP |
| R-802 | MUST | No spacing asymmetry when the columns stack. | XP |

## 12. Footer and compliance

| ID | Lvl | Rule | Source |
|---|---|---|---|
| R-900 | MUST | Footer: reason for receiving, legal entity, physical address, VAT number (IT), contacts, **Unsubscribe**, **Preferences**, **Privacy policy**, copyright, social. | MU, MT, GY |
| R-901 | MUST | In production, **zero placeholders** (`[Legal entity]`, `example.com`, `placehold.co`, `TODO`, `lorem`). In a draft: listed in the report. | XP |
| R-902 | MUST | Only recipients who consented (GDPR); no purchased lists; bounce rate < 2%, spam complaints < 0.1% (Gmail/Yahoo hard cap 0.3%). | MT, GY |

## 13. Acceptance gates (Definition of Done)

| Gate | Tool | Threshold |
|---|---|---|
| G1 Static lint | `scripts/lint_email.py` | 0 MUST violated |
| G2 Render | screenshots 600px desktop + 375px mobile, with and without `<style>`, with images blocked | no breakage |
| G3 HTML Check | Mailtrap HTML Check | Market Support **≥ 95%** (Mailtrap: ≥ 90% acceptable, < 85% has to be redone); only the §14 baseline warnings |
| G4 Spam | Mailtrap SpamAssassin | **≤ 0.1** in testing |
| G5 Blacklist | Mailtrap Blacklist report | 0 listings |
| G6 HTML/Text | Mailtrap Template Inspector | versions aligned |
| G7 Check-up | MailUp Controlla | 0 serious problems, 0 potential ones (blacklisted links, tracking, unsubscribe, weight, dynamic fields, summary, analytics, tracking domain, spam, code) |
| G8 Links | link crawl | 100% HTTP 200, valid UTM |

## 14. Accepted residual warnings (Mailtrap HTML Check baseline)

| Mailtrap rule | Reason |
|---|---|
| `style` | The `<style>` is needed for responsive and corners (R-300). |
| `@media`, `@media max-width` | Mobile media query (R-302). |
| `width`/`display`/`height`/`font-size`/`line-height` inside the media query | Stacking and mobile typography. |
| `border-radius` (1 line) | Square corners on Outlook/Windows Mail. |
| `display` on the preheader | The only way to hide it (R-400). |

Any other entry is a defect.

## 15. Historical anti-patterns [XP]

| Ver. | Mistake | Rule |
|---|---|---|
| v1 | `color-scheme: light dark` on a dark template | R-500 |
| v1 | Preheader colored like the background → `HTML_FONT_LOW_CONTRAST` | R-400, R-403 |
| v1 | Low-contrast `·` separators | R-403, R-501 |
| v1 | Footer at 3.4:1, 11px | R-501, R-502 |
| v1 | `width="33.33%"`, asymmetric padding | R-801, R-802 |
| v1 | VML 220px vs HTML with 34px padding | R-701 |
| v1 | Textual `[image: X]` placeholders, `example.com` | R-600, R-901 |
| v1–v3 | Inline `background-color`/`padding`/`border` "with fallback" → ~50 warnings | R-101, §4 |
| v2 | Filler `&#847;&zwnj;&nbsp;` → +2.4 spam | R-401 |
| v2 | `<h1 style="margin:0">` | R-007 |
| v3 | Inline `width/height/border-radius` on `<img>` | R-205, R-600 |
| v4 | `<style>` with a reset and a preheader class → ~35 warnings | R-300, R-301 |
| v4 | `@media only screen and (…)` | R-302 |
| v4 | `&nbsp;` cells without a default text color | R-207 |
| v5 | Image cell without `height` → card collapsed with images blocked | R-601 |
