# Email HTML — Rules (normative)

> **Livelli** — **MUST**: bloccante, la mail non si consegna. **SHOULD**: default, una deroga va motivata nel report. **MAY**: opzionale.
> Ogni regola ha un ID stabile (`R-xxx`) citato dal linter `scripts/lint_email.py` e nel report di consegna.
> **Fonti** — [MT] Mailtrap (HTML Check su dati caniemail.com, SpamAssassin, Blacklist, Template Inspector, blog best practice) · [MU] MailUp (Check-up/Controlla, manuale editor HTML, checklist email design, "10 errori HTML") · [GY] requisiti bulk sender Gmail/Yahoo · [WCAG] 2.2 AA · [XP] errori reali v1→v5 del template "Benvenuto Luisaviaroma" verificati su Mailtrap.
> Dove le fonti divergono, prevale la regola **più restrittiva e verificata sul campo** ([XP] > [MT] > [MU]); la divergenza è annotata.

---

## 0. Principi

1. **Il checker HTML Mailtrap segnala ogni proprietà presente, non valuta i fallback** [MT][XP]. `bgcolor` accanto a `background-color` NON azzera il warning: la proprietà va **rimossa**.
2. **Layout = attributi HTML. CSS = solo tipografia inline + progressive enhancement nel `<style>`.**
3. *"Be conservative in what you send"* [MU]: codice robusto sui client peggiori (Outlook Word engine) prima delle soluzioni moderne.
4. **Doppio gate di qualità**: Mailtrap (Market Support, SpamAssassin, Blacklist, HTML/Text) **e** MailUp Check-up (link, disiscrizione, peso, campi dinamici, tracking, spam, codice). Una mail è pronta solo se passa entrambi.

---

## 1. Struttura documento

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-001 | MUST | `<!DOCTYPE html>`, `<html lang="xx">` con `xmlns:v` e `xmlns:o`. | MT, XP |
| R-002 | MUST | `<meta charset="utf-8">`, `viewport`, `X-UA-Compatible`, `x-apple-disable-message-reformatting`, `format-detection` (telephone/date/address/email/url = no). | MT, MU |
| R-003 | MUST | `<!--[if mso]>` con `OfficeDocumentSettings` (`AllowPNG`, `PixelsPerInch 96`). | MT |
| R-004 | MUST | Layout **solo tabelle** `role="presentation" cellpadding="0" cellspacing="0" border="0"`. Vietati div di layout, flex, grid, float, position. | MT, MU |
| R-005 | MUST | Struttura a 3 livelli [MU]: tabella esterna `width="100%"` → contenitore `width="600"` `align="center"` → tabelle contenuto `width="100%"`. Blocchi modulari = tabelle annidate indipendenti. | MU |
| R-006 | MUST | Gutter laterale esterno 16px con **celle spaziatrici** (mai padding). | XP |
| R-007 | MUST | Titolo principale `<td role="heading" aria-level="1">` (non `<h1>`: `margin` segnalato su Outlook). Divergenza: [MT] suggerisce `<h1>`; prevale [XP]. | XP |
| R-008 | MUST | Nessun tag vuoto/abbandonato (`<font></font>`, `<span></span>`, `<p></p>`), nessun attributo ridondante che duplica un altro. | MU |
| R-009 | SHOULD | Commenti HTML ridotti al minimo (pesano): solo condizionali MSO e marcatori di sezione brevi. | MU |
| R-010 | MUST | HTML ben formato (tag bilanciati, attributi quotati, nessun ID duplicato). Validazione W3C: gli errori ammessi sono solo gli attributi legacy intenzionali (`bgcolor`, `align`, `valign`, `width`, `height`, `border`, `cellpadding`, `cellspacing`, `marginwidth`…). | MU |
| R-011 | MUST | Vietati: `<script>`, `<form>`, `<input>`, `<iframe>`, `<object>`, `<embed>`, `<video>`, `<audio>`, `<svg>` inline, `<link rel=stylesheet>`, `@import`, web font obbligatori, `position`, JavaScript negli attributi (`on*`). | MT, MU |

## 2. Peso

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-050 | MUST | HTML < **100 KB** (soglia filtri spam [MT]; clipping Gmail ≈ 102 KB). **Target < 40 KB.** | MT, MU |
| R-051 | SHOULD | Minificare in build (rimuovere spazi/commenti non condizionali) solo sulla copia di invio; il sorgente resta leggibile. | MT, MU |
| R-052 | MUST | Singola immagine ≤ **50 KB** (JPG/PNG, 72 dpi); GIF animata ≤ **100 KB**; totale immagini ≤ 500 KB. | MU |

## 3. CSS inline — whitelist chiusa

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-100 | MUST | Nel `style=""` degli elementi del `<body>` sono ammesse **solo**: `font-family`, `font-size`, `line-height`, `font-weight`, `font-style`, `letter-spacing`, `color`, `text-decoration`, `text-align`, `mso-*`. | XP |
| R-101 | MUST | **Vietati inline**: `padding*`, `margin*`, `background*`, `border*`, `border-radius`, `width`, `height`, `max-*`, `min-*`, `display`, `opacity`, `overflow`, `visibility`, `outline`, `box-shadow`, `position`, `float`, `text-transform`, `table-layout`. | XP |
| R-102 | MUST | Unica eccezione: il preheader con `style="display:none; mso-hide:all;"` (R-400). | XP |
| R-103 | MUST | Eccezione: `style` dei VML `<v:*>` dentro `<!--[if mso]>` (il checker non li analizza). | XP |
| R-104 | MUST | Maiuscolo scritto nel testo, non con `text-transform`. | XP |
| R-105 | MUST | Font stack web-safe con fallback: `Arial, Helvetica, sans-serif` / `Georgia, 'Times New Roman', serif` / `'Courier New', Courier, monospace`. Web font solo come primo elemento dello stack, mai indispensabili. Divergenza: [MU] suggerisce `table-layout:fixed` inline; lo sostituisce l'attributo `width` fisso (R-801). | MT, MU |

## 4. Sostituzioni obbligatorie (CSS → attributi)

| ID | Liv. | Invece di… | Usa… |
|---|---|---|---|
| R-200 | MUST | `background-color` | attributo `bgcolor="#rrggbb"` su `table`/`td`/`body`. |
| R-201 | MUST | padding verticale | `<tr><td height="N" style="font-size:1px; line-height:Npx;">&nbsp;</td></tr>` (`colspan` se serve). |
| R-202 | MUST | padding orizzontale | `<td width="N" style="font-size:1px; line-height:1px;">&nbsp;</td>`; `class="gut"` se si riduce su mobile. |
| R-203 | MUST | `border:1px solid C` | tabella esterna `bgcolor="C" cellpadding="1"` contenente la tabella card. |
| R-204 | MUST | divisore `border-top` | `<td height="1" bgcolor="C" style="font-size:1px; line-height:1px;">&nbsp;</td>`. |
| R-205 | MUST | `width`/`height` CSS | attributi `width` / `height`. |
| R-206 | MUST | margini body | `marginwidth="0" marginheight="0" topmargin="0" leftmargin="0"`. |
| R-207 | MUST | colore testo default | `<body bgcolor text link vlink alink>` (evita `HTML_FONT_LOW_CONTRAST` sulle celle `&nbsp;`). |
| R-208 | MUST | gap sotto immagine | cella contenitore `style="font-size:0; line-height:0;"`. |
| R-209 | SHOULD | `border-radius` inline | classe nel `<style>` (R-300); angoli retti su Outlook accettati. |
| R-210 | MUST | immagini di sfondo CSS | colore pieno `bgcolor`; se indispensabile: `background=""` attributo + VML `v:rect` per Outlook. [MT]: evitarle. |

## 5. Blocco `<style>` — minimo, compatto

| ID | Liv. | Regola |
|---|---|---|
| R-300 | MUST | **Un solo** `<style>` in `<head>`, contenente **solo**: (a) 1 riga di classi `border-radius`; (b) 1 media query mobile su 1 riga; (c) opzionale 1 riga per link auto-rilevati `a[x-apple-data-detectors]` **solo se** il template contiene numeri/indirizzi/date. |
| R-301 | MUST | Vietati nel `<style>`: reset su `body`/`table`/`img`/`a`, classi preheader, `border-collapse`, `outline`, `visibility`, `-webkit-text-size-adjust`/`-ms-*`, `:root`, `color-scheme` CSS, `prefers-color-scheme`, `[data-ogsc]`, `u + #body`, `@font-face`, `@import`. |
| R-302 | MUST | `@media (max-width:620px){…}` — **senza** `only screen and`. |
| R-303 | MUST | Tutte le regole `border-radius` su **una riga**; la media query su **una riga** (il checker conta per riga). |
| R-304 | MUST | Nessun commento contenente la stringa letterale `<style`. |
| R-305 | MUST | Senza `<style>` la mail resta **integra e leggibile** a 600px. |

Media query di riferimento (classi standard):

```css
@media (max-width:620px){.wrap{width:100%!important}.col{display:block!important;width:100%!important}.vgap{display:block!important;width:100%!important;height:16px!important}.gut{width:20px!important}.h1m{font-size:26px!important;line-height:32px!important}.txtm{font-size:16px!important;line-height:24px!important}.imgm{width:100%!important;height:auto!important}}
```

## 6. Oggetto, preheader, charset, antispam

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-400 | MUST | Preheader `<!--[if !mso]><!--><div aria-hidden="true" style="display:none; mso-hide:all;">…</div><!--<![endif]-->`, **40–100 caratteri**, informazione chiave in testa, complementare (non ripetizione) all'oggetto, **senza `color`**. | MT, MU, XP |
| R-401 | MUST | **Vietato** filler invisibile (`&#847;`, `&zwnj;`, `&nbsp;` ripetuti, `&#8203;`): SpamAssassin decodifica → `DOS_BODY_HIGH_NO_MID` +2.4. | XP |
| R-402 | MUST | HTML **100% ASCII**: non-ASCII come entità numeriche (`è`→`&#232;`, `·`→`&#183;`). | XP |
| R-403 | MUST | Nessun testo di colore uguale/simile allo sfondo (`HTML_FONT_LOW_CONTRAST`), inclusi preheader e separatori. | XP |
| R-404 | MUST | Parte `text/plain` sempre presente e **allineata** all'HTML (stessi contenuti, stessi link in chiaro) — controllo "HTML/Text alignment" del Template Inspector. | MT |
| R-405 | MUST* | *Solo mail commerciali/bulk; le transazionali pure ne sono esenti.* Header `List-Unsubscribe: <https://…>, <mailto:…>` + `List-Unsubscribe-Post: List-Unsubscribe=One-Click` (RFC 8058). | GY |
| R-406 | MUST | Oggetto: **35–50 caratteri** (hard max 60), specifico, niente ALL CAPS, niente `!!!`/`$$$`, max 1 emoji, niente parole trigger ("GRATIS", "URGENTE", "100%", "clicca qui"). Caratteri non ASCII nell'oggetto via SMTP: encoding Quoted-Printable (`=?utf-8?Q?…?=`), non Base64. | MT, MU |
| R-407 | MUST | SpamAssassin Mailtrap: **target ≤ 0.1** (in test via API è ammesso solo `MISSING_MID` 0.1 — il Message-ID lo aggiunge l'MTA). Soglia di blocco consegna: **≥ 1.0**. Soglia Mailtrap "buono" < 5, marketing < 3: non sono target, sono limiti. | MT, XP |
| R-408 | MUST | Blacklist report Mailtrap: **0 listing** per IP e dominio mittente e per ogni dominio linkato; MailUp Check-up: nessun link in blacklist. | MT, MU |
| R-409 | MUST | Nessun URL shortener (bit.ly ecc.), nessun IP nudo nei link, testo del link coerente con la destinazione (no "www.brand.it" che punta altrove). | MT, MU |
| R-410 | MUST | Rapporto testo/immagini **≥ 80/20** [MT] (minimo assoluto 60/40 [MU]); mai mail "solo immagine"; messaggio principale e CTA in testo HTML. | MT, MU |
| R-411 | SHOULD | Corpo testuale ≤ 1.000 caratteri per mail promozionali/transazionali brevi; paragrafi corti; messaggio e CTA above the fold. | MT |
| R-412 | MUST | Mittente: dominio autenticato **SPF + DKIM + DMARC** (allineati), niente `noreply@` se evitabile → usare `Reply-To` presidiato. Nome mittente = brand o "Persona · Brand". | MT, GY |

## 7. Link, tracking, campi dinamici (MailUp Check-up)

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-450 | MUST | Tutti i link **assoluti HTTPS**, funzionanti (HTTP 200 dopo redirect), nessuno verso `example.com`/`localhost`/staging. | MT, MU |
| R-451 | MUST | Tracciamento link **attivo** e **dominio di tracciamento personalizzato** (CNAME del brand) sulla piattaforma di invio. | MU |
| R-452 | MUST | UTM su ogni link al sito: `utm_source`, `utm_medium=email`, `utm_campaign` obbligatori (`utm_content` per CTA/blocco); **nessuno spazio** nei valori (usa `-` o `_`), minuscolo. | MU |
| R-453 | MUST | Campi dinamici nella sintassi della piattaforma (MailUp: `[nomecampo]`), **attivati** e con **valore di default** (es. "Ciao [nome]" → default "Ciao"). Nei link: protocollo esplicito `href="https://[campo]"`, altrimenti link locale. | MU |
| R-454 | MUST* | *Solo mail commerciali/bulk (vedi R-405); per le transazionali il linter lo declassa con `--transactional`.* Link di **disiscrizione** presente e funzionante, raggiungibile in ≤ 2 click, nel footer, usando il placeholder/meccanismo nativo della piattaforma (MailUp: link di disiscrizione del footer lista — *sintassi placeholder da verificare sull'account*). | MU, MT, GY |
| R-455 | SHOULD | Sommario/anteprima impostato sulla piattaforma (MailUp: max 100 caratteri) coerente col preheader. | MU |
| R-456 | SHOULD | Codice web analytics coerente (UTM o parametri piattaforma), mai doppio tracciamento conflittuale. | MU |
| R-457 | MUST | Numeri di telefono `href="tel:+39…"` senza spazi; email `mailto:`. | MU |
| R-458 | MUST | Path immagini/asset senza spazi (es. `/img/benvenuto/` non `/File immagini/`) — spazi rompono Gmail. | MU |

## 8. Colori, dark mode, accessibilità, tipografia

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-500 | MUST | Template scuro: `<meta name="color-scheme" content="dark">` + `supported-color-schemes` = `dark`. Chiaro: `light`. **Mai** `light dark` senza tema dark completo testato. | XP |
| R-501 | MUST | Contrasto WCAG AA ≥ **4.5:1** testo normale (incluso footer), ≥ **3:1** testo ≥ 24px o ≥ 18.66px bold. Calcolato, non stimato. | WCAG, XP |
| R-502 | MUST | Tipografia: titoli ≥ **22px**, corpo ≥ **16px su mobile** (desktop ≥ 14px, via classe `.txtm`), testi card ≥ 13px, legale ≥ 12px, CTA ≥ 15px, `line-height` ≥ 1.4. | MU, WCAG |
| R-503 | MUST | Palette 2–3 colori funzionali (brand, accento/CTA, neutri); ogni colore ha un ruolo. | MU |
| R-504 | MUST | Glifi decorativi e separatori `aria-hidden="true"`; `lang` e `<title>` valorizzati. | MT, WCAG |
| R-505 | MUST | Ordine di lettura DOM = ordine visivo (verificabile rimuovendo il CSS). | WCAG |

## 9. Immagini

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-600 | MUST | Ogni `<img>`: `src` assoluto HTTPS, `width` e `height` **attributi**, `border="0"`, `alt` descrittivo **breve** (≤ 60 caratteri; `alt=""` solo se decorativa). `title` opzionale [MU]. | MT, MU |
| R-601 | MUST | La **cella** dell'immagine ha `height="N"` e `bgcolor`: con immagini bloccate (default Outlook) la card mantiene forma e l'alt resta leggibile. | XP |
| R-602 | MUST | Asset @2x (es. 348×240 mostrati a 174×120), JPG per foto / PNG per grafica, ≤ 50 KB (R-052), su **CDN del brand** (niente `placehold.co` → `URIBL_BLOCKED`). | MU, MT, XP |
| R-603 | MUST | Mai testo essenziale (prezzo, codice sconto, CTA, date) solo in immagine. | MT, MU |
| R-604 | MUST | GIF animate: **primo frame completo** e autosufficiente (Outlook 2007–2019 mostra solo quello); uso parsimonioso. | MU, MT |
| R-605 | SHOULD | Logo in testa, cliccabile verso la home con UTM. | MT |

## 10. CTA bulletproof

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-700 | MUST | Doppio rendering: `<!--[if mso]><v:roundrect … arcsize fillcolor stroke="f"><w:anchorlock/><center>…</center></v:roundrect><![endif]-->` + `<!--[if !mso]><!-->` tabella `bgcolor` `width` `class="r10"` con `<td height="48" style="line-height:48px">`. | MT, MU, XP |
| R-701 | MUST | Dimensioni VML **identiche** alla tabella non-mso. | XP |
| R-702 | MUST | Area cliccabile ≥ **46×46 px** (consigliato 220×48); mai `padding`/`display:block` sull'`<a>`. | MT, XP |
| R-703 | SHOULD | 1 CTA primaria per mail, verbo + oggetto ("Scopri i prodotti"), visibile above the fold; testo/forma/colore candidati ad A/B test. | MU, MT |

## 11. Responsive

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-800 | MUST | Approccio **mobile-first nel design**, single-column preferito; multi-colonna solo con `<td class="col" width="N">` + spaziatori `<td class="vgap" width="12">`. | MU, MT |
| R-801 | MUST | Larghezze colonne in **px interi** con somma = contenitore. Vietate percentuali frazionarie (`33.33%`). Divergenza: [MU] suggerisce 47% invece di 50%; i px fissi risolvono lo stesso rischio senza arrotondamenti. | XP |
| R-802 | MUST | Nessuna asimmetria di spaziatura quando le colonne si impilano. | XP |

## 12. Footer e compliance

| ID | Liv. | Regola | Fonte |
|---|---|---|---|
| R-900 | MUST | Footer: motivo di ricezione, ragione sociale, indirizzo fisico, P.IVA (IT), contatti, **Annulla iscrizione**, **Preferenze**, **Privacy policy**, copyright, social. | MU, MT, GY |
| R-901 | MUST | In produzione **zero placeholder** (`[Ragione sociale]`, `example.com`, `placehold.co`, `TODO`, `lorem`). In bozza: elencati nel report. | XP |
| R-902 | MUST | Solo destinatari con consenso (GDPR); nessuna lista acquistata; bounce rate < 2%, spam complaint < 0.1% (hard cap Gmail/Yahoo 0.3%). | MT, GY |

## 13. Gate di accettazione (Definition of Done)

| Gate | Strumento | Soglia |
|---|---|---|
| G1 Lint statico | `scripts/lint_email.py` | 0 MUST violati |
| G2 Render | screenshot 600px desktop + 375px mobile, con e senza `<style>`, con immagini bloccate | nessuna rottura |
| G3 HTML Check | Mailtrap HTML Check | Market Support **≥ 95%** (Mailtrap: ≥ 90% accettabile, < 85% da rifare); solo warning della baseline §14 |
| G4 Spam | Mailtrap SpamAssassin | **≤ 0.1** in test |
| G5 Blacklist | Mailtrap Blacklist report | 0 listing |
| G6 HTML/Text | Mailtrap Template Inspector | versioni allineate |
| G7 Check-up | MailUp Controlla | 0 problemi gravi, 0 potenziali (link blacklist, tracking, disiscrizione, peso, campi dinamici, sommario, analytics, dominio tracking, spam, codice) |
| G8 Link | crawl link | 100% HTTP 200, UTM validi |

## 14. Warning residui ammessi (baseline Mailtrap HTML Check)

| Rule Mailtrap | Motivo |
|---|---|
| `style` | `<style>` necessario per responsive e angoli (R-300). |
| `@media`, `@media max-width` | Media query mobile (R-302). |
| `width`/`display`/`height`/`font-size`/`line-height` dentro la media query | Stacking e tipografia mobile. |
| `border-radius` (1 riga) | Angoli retti su Outlook/Windows Mail. |
| `display` sul preheader | Unico modo per nasconderlo (R-400). |

Qualsiasi altra voce è un difetto.

## 15. Anti-pattern storici [XP]

| Ver. | Errore | Regola |
|---|---|---|
| v1 | `color-scheme: light dark` su template scuro | R-500 |
| v1 | Preheader colorato come lo sfondo → `HTML_FONT_LOW_CONTRAST` | R-400, R-403 |
| v1 | Separatori `·` a basso contrasto | R-403, R-501 |
| v1 | Footer 3.4:1, 11px | R-501, R-502 |
| v1 | `width="33.33%"`, padding asimmetrici | R-801, R-802 |
| v1 | VML 220px vs HTML con padding 34px | R-701 |
| v1 | Placeholder `[immagine: X]` testuali, `example.com` | R-600, R-901 |
| v1–v3 | `background-color`/`padding`/`border` inline "con fallback" → ~50 warning | R-101, §4 |
| v2 | Filler `&#847;&zwnj;&nbsp;` → +2.4 spam | R-401 |
| v2 | `<h1 style="margin:0">` | R-007 |
| v3 | `width/height/border-radius` inline su `<img>` | R-205, R-600 |
| v4 | `<style>` con reset e classe preheader → ~35 warning | R-300, R-301 |
| v4 | `@media only screen and (…)` | R-302 |
| v4 | Celle `&nbsp;` senza colore testo default | R-207 |
| v5 | Cella immagine senza `height` → card collassata a immagini bloccate | R-601 |
