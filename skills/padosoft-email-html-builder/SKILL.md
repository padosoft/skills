---
name: padosoft-email-html-builder
description: >-
  Usa questa skill ogni volta che l'utente crea, corregge, converte o revisiona una email HTML (welcome, transazionale, newsletter, DEM, template ESP) o chiede di testarla su Mailtrap o MailUp, anche se non nomina esplicitamente "HTML", "template" o "deliverability": produce email a tabelle con CSS inline minimo, testo/plain allineato, List-Unsubscribe one-click, e le valida con un linter incluso fino a 0 errori, puntando a spam SpamAssassin <= 0.1 e HTML Check senza warning fuori baseline. Non usarla per copywriting senza codice, per configurare DNS/SPF/DKIM o per gestire liste e invii massivi.
license: MIT
compatibility: >-
  Richiede Python 3.10+ per gli script inclusi (solo standard library). Facoltativi: un browser headless
  (Playwright/Chromium) per gli screenshot di verifica e un account Mailtrap per HTML Check e spam report.
metadata:
  version: 1.1.0
  author: Padosoft
  profiles: email
  scope: project
  repository: https://github.com/padosoft/skills
  keywords: email, html email, mailtrap, mailup, deliverability, spamassassin, outlook, responsive, accessibility
---

# Email HTML Builder

Produce email HTML **pronte per la produzione al primo colpo**: layout a tabelle con attributi HTML, CSS inline ridotto alla sola tipografia, un `<style>` minimo, parte text/plain allineata, header di disiscrizione one-click. Il risultato atteso su Mailtrap è **spam ≤ 0.1** e un **HTML Check con solo i warning ammessi** (§5). Su MailUp Check-up: **zero problemi**.

Le regole normative complete con ID `R-xxx` sono in `references/rules.md`. Il linter è `scripts/lint_email.py` e il template di riferimento `templates/reference-welcome-dark.html`. **Se questi file non sono disponibili, le regole essenziali qui sotto bastano e sono vincolanti.**

---

## 0. Script inclusi

| Script | Uso |
|---|---|
| `scripts/lint_email.py` | Validatore delle regole. `python3 scripts/lint_email.py email.html --text email.txt --subject "Oggetto" [--production] [--transactional] [--json]`. Exit 1 se ci sono MUST violati, 0 se pulito. |
| `scripts/build_payload.py` | Genera il payload JSON Mailtrap con `List-Unsubscribe` e One-Click. `--help` per le opzioni. |
| `scripts/send_mailtrap_sandbox.sh` / `.ps1` | Invio in sandbox. Variabili: `MAILTRAP_TOKEN`, `MAILTRAP_INBOX_ID`. |
| `scripts/screenshot_email.py` | Screenshot 600px e 375px, con e senza `<style>` (richiede Playwright; se manca, salta il gate G2 e dillo nel report). |
| `templates/reference-welcome-dark.html` | Template conforme da cui partire (0 MUST violati). |
| `references/rules.md` | Regole complete `R-xxx`. Leggilo quando un warning non e' nella baseline del §5 o quando serve la motivazione di una regola. |


---

## 1. Workflow obbligatorio

Esegui le fasi **in ordine**. Non consegnare prima che G1–G2 siano verdi. Se hai accesso a Mailtrap, fai girare anche G3–G6.

1. **Brief.** Ricava o chiedi (una sola volta, in blocco) cosa manca:
   - tipo di mail, brand, lingua e tema chiaro/scuro;
   - palette di 2–3 colori, contenuti, CTA e URL;
   - piattaforma di invio (MailUp, Mailtrap Sending, SES…) e sintassi dei campi dinamici;
   - dati legali per il footer.

   Se il brief è incompleto non bloccarti: usa segnaposto espliciti e elencali nel report.
2. **Design dei contenuti.** Prima di scrivere codice definisci:
   - oggetto: 35–50 caratteri;
   - preheader: 40–100 caratteri, complementare all'oggetto;
   - una sola CTA primaria;
   - rapporto testo/immagini ≥ 80/20;
   - quali blocchi usare (header, hero, card, vantaggi, social, footer).
3. **Codice.** Parti dallo scheletro del §3 (o da `templates/`). Applica **tutte** le regole MUST del §4.
4. **Text/plain.** Scrivi la versione solo testo con gli stessi contenuti e gli stessi link in chiaro.
5. **G1 Lint.** Lancia `python3 scripts/lint_email.py email.html --text email.txt --subject "…"` e porta i MUST violati a **0**. Se lo script non c'è, fai a mano la checklist del §6.
6. **G2 Render.** Fai screenshot con Playwright/Chromium a **600px** e **375px**, poi ripetili senza `<style>` e con le immagini bloccate. Nessuna rottura ammessa.
7. **Payload e invio test.**
   - `scripts/build_payload.py` genera il payload JSON (List-Unsubscribe incluso);
   - l'invio parte con `scripts/send_mailtrap_sandbox.{ps1,sh}` oppure con il connettore Mailtrap (`send-sandbox-email`);
   - su Windows usa **PowerShell**: `$env:VAR="…"` e non la sintassi `VAR=… cmd`.
8. **Senza Mailtrap** (nessun account o connettore): dichiara G3–G6 come *non eseguiti* nel report, non stimarli, ed esegui in compenso la checklist manuale del §6 oltre al linter. Consegna comunque.
9. **G3–G6 Verifica Mailtrap.** Usa `get-sandbox-message-html-analysis`, `get-sandbox-message-spam-score` e i report blacklist e text. Confronta con la baseline del §5: ogni voce fuori baseline è un difetto da correggere e rinviare. **Non dichiarare "falso positivo" un warning rimovibile.**
10. **G7 MailUp** (se è la piattaforma di invio): Check-up senza errori su link in blacklist, tracciamento attivo, disiscrizione presente, peso, campi dinamici con default, sommario, analytics, dominio di tracciamento personalizzato, spam e codice.
11. **Consegna.**
    - file `.html`, `.txt` e `payload.json`;
    - **report** con esito dei gate, warning residui motivati, segnaposto ancora da sostituire e deroghe SHOULD motivate;
    - numero di versione (`v1`, `v2`…) nell'oggetto di test.

---

## 2. Principio chiave (causa degli errori storici)

Il checker Mailtrap usa i dati di caniemail.com e **segnala ogni proprietà CSS presente, anche se c'è il fallback**. `bgcolor` accanto a `background-color` **non** toglie il warning: la proprietà CSS va **eliminata**.
→ **Layout con attributi HTML. CSS inline solo per la tipografia. `<style>` solo per angoli arrotondati e media query.**

---

## 3. Scheletro di riferimento

```html
<!DOCTYPE html>
<html lang="it" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no, url=no">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<title>Titolo</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
<style>
.r10{border-radius:10px}.r9{border-radius:9px}.r9t{border-radius:9px 9px 0 0}
@media (max-width:620px){.wrap{width:100%!important}.col{display:block!important;width:100%!important}.vgap{display:block!important;width:100%!important;height:16px!important}.gut{width:20px!important}.h1m{font-size:26px!important;line-height:32px!important}.txtm{font-size:16px!important;line-height:24px!important}.imgm{width:100%!important;height:auto!important}}
</style>
</head>
<body bgcolor="#04050a" text="#aab3c5" link="#2ff5d6" vlink="#2ff5d6" alink="#2ff5d6" marginwidth="0" marginheight="0" topmargin="0" leftmargin="0">
<!--[if !mso]><!--><div aria-hidden="true" style="display:none; mso-hide:all;">Preheader 40-100 caratteri, niente filler invisibile.</div><!--<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#04050a">
 <tr><td height="32" style="font-size:1px; line-height:32px;">&nbsp;</td></tr>
 <tr><td align="center" valign="top">
  <table role="presentation" width="632" class="wrap" align="center" cellpadding="0" cellspacing="0" border="0"><tr>
   <td width="16" style="font-size:1px; line-height:1px;">&nbsp;</td>
   <td align="center" valign="top">
    <table role="presentation" class="wrap" width="600" align="center" cellpadding="0" cellspacing="0" border="0">
     <!-- blocchi -->
    </table>
   </td>
   <td width="16" style="font-size:1px; line-height:1px;">&nbsp;</td>
  </tr></table>
 </td></tr>
 <tr><td height="32" style="font-size:1px; line-height:32px;">&nbsp;</td></tr>
</table>
</body>
</html>
```

### Pattern dei blocchi (copiali, non reinventarli)

**Spaziatura verticale e orizzontale** (al posto del padding):
```html
<tr><td height="24" style="font-size:1px; line-height:24px;">&nbsp;</td></tr>
<td class="gut" width="24" style="font-size:1px; line-height:1px;">&nbsp;</td>
```

**Card con bordo e angoli** (al posto di border e background-color):
```html
<table role="presentation" class="r10" width="100%" cellpadding="1" cellspacing="0" border="0" bgcolor="#1c2333"><tr><td>
  <table role="presentation" class="r9" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#0d1018">
    <tr><td colspan="3" height="24" style="font-size:1px; line-height:24px;">&nbsp;</td></tr>
    <tr><td width="20" style="font-size:1px; line-height:1px;">&nbsp;</td><td><!-- contenuto --></td><td width="20" style="font-size:1px; line-height:1px;">&nbsp;</td></tr>
    <tr><td colspan="3" height="24" style="font-size:1px; line-height:24px;">&nbsp;</td></tr>
  </table>
</td></tr></table>
```

**Titolo H1 accessibile** (niente `<h1>`):
```html
<td align="center" class="h1m" role="heading" aria-level="1" style="font-family:Arial, Helvetica, sans-serif; font-size:30px; line-height:38px; font-weight:700; color:#f2f4f8;">Titolo</td>
```

**CTA bulletproof** (VML e HTML con dimensioni **identiche**):
```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="https://…" style="height:48px; v-text-anchor:middle; width:220px;" arcsize="21%" fillcolor="#2ff5d6" stroke="f"><w:anchorlock/><center style="color:#04050a; font-family:Arial, Helvetica, sans-serif; font-size:15px; font-weight:bold;">Scopri i prodotti</center></v:roundrect>
<![endif]-->
<!--[if !mso]><!-->
<table role="presentation" class="r10" width="220" cellpadding="0" cellspacing="0" border="0" bgcolor="#2ff5d6"><tr>
<td align="center" height="48" style="font-family:Arial, Helvetica, sans-serif; font-size:15px; line-height:48px; font-weight:700;"><a href="https://…" target="_blank" style="color:#04050a; text-decoration:none;">Scopri i prodotti</a></td>
</tr></table>
<!--<![endif]-->
```

**Immagine in card** (la cella ha height e bgcolor, così resta intera con le immagini bloccate):
```html
<td align="center" valign="middle" height="120" class="r9t" bgcolor="#161b27" style="font-size:0; line-height:0;"><a href="https://…" target="_blank"><img src="https://cdn.brand.it/img/x@2x.jpg" width="174" height="120" border="0" alt="Descrizione breve" class="imgm"></a></td>
```

**Colonne che si impilano su mobile** (px interi, somma = contenitore):
```html
<tr><td class="col" width="176" valign="top">…</td><td class="vgap" width="12" style="font-size:1px; line-height:1px;">&nbsp;</td><td class="col" width="176" valign="top">…</td><td class="vgap" width="12" style="font-size:1px; line-height:1px;">&nbsp;</td><td class="col" width="176" valign="top">…</td></tr>
```

**Divisore:**
```html
<tr><td height="1" bgcolor="#1c2333" style="font-size:1px; line-height:1px;">&nbsp;</td></tr>
```

---

## 4. Regole MUST essenziali (ID in `references/rules.md`)

**Struttura e peso**
- Solo tabelle `role="presentation" cellpadding="0" cellspacing="0" border="0"`, contenitore da 600px, gutter esterno di 16px fatto con celle (R-004/005/006).
- Vietati `<h1>`, `<script>`, `<form>`, `<iframe>`, `<video>`, `<svg>`, `<link>`, `@import`, gli handler `on*`, i tag vuoti e i commenti superflui (R-007/008/009/011).
- HTML sotto i 100 KB (target 40 KB). Immagini ≤ 50 KB, GIF ≤ 100 KB con primo frame completo (R-050/052/604).

**CSS**
- Inline sono ammessi **solo** `font-family`, `font-size`, `line-height`, `font-weight`, `font-style`, `letter-spacing`, `color`, `text-decoration`, `text-align` e `mso-*` (R-100).
- **Vietati inline:** padding, margin, background, border, border-radius, width, height, max/min-*, display, opacity, overflow, visibility, outline, box-shadow, position, float, text-transform, table-layout (R-101). Unica eccezione il preheader (`display:none; mso-hide:all`).
- Sostituzioni obbligatorie (R-200…210):

  | Invece di | Usa |
  |---|---|
  | `background` | `bgcolor` |
  | padding | celle vuote con `height`/`width` |
  | border | tabella esterna `bgcolor` + `cellpadding="1"` |
  | width/height CSS | attributi `width`/`height` |
  | margini del body | `marginwidth`/`marginheight` |
  | colore di default | `text`/`link` sul `<body>` |
  | gap sotto le immagini | `font-size:0; line-height:0` sulla cella |
  | immagini di sfondo | colore pieno |

- `<style>` unico, con **una riga** di `border-radius` e **una riga** `@media (max-width:620px){…}`, senza `only screen and`. Niente reset, niente classi preheader, niente `prefers-color-scheme` o `:root` (R-300…303).
- Nessun commento che contenga la stringa `<style`. La mail deve restare leggibile anche senza il blocco style (R-304/305).

**Antispam e deliverability**
- **Marketing vs transazionale.** Le regole di disiscrizione (`R-405` header `List-Unsubscribe`, `R-454` link nel footer) valgono per mail **commerciali e bulk**. Per una transazionale pura (conferma ordine, reset password, spedizione) non sono richieste: usa `--transactional` nel linter, tieni comunque un link "Preferenze email" e dichiaralo nel report. Tutto il resto delle regole vale per entrambe.
- HTML **100% ASCII**: accenti come entità numeriche (`&#232;`) (R-402).
- **Mai filler invisibile** nel preheader (`&#847;`, `&zwnj;`, `&nbsp;` ripetuti): costa +2.4 punti SpamAssassin (R-401).
- Preheader senza `color`. Nessun testo con colore uguale o simile allo sfondo, separatori compresi (R-400/403).
- Text/plain allineato all'HTML. Header `List-Unsubscribe` e `List-Unsubscribe-Post: List-Unsubscribe=One-Click` (R-404/405).
- Oggetto 35–50 caratteri (max 60): niente MAIUSCOLO, niente `!!!`, parole trigger o più di un'emoji (R-406).
- Spam target ≤ 0.1, blacklist 0, niente shortener o IP nudi. Testo/immagini ≥ 80/20. Dominio del mittente con SPF+DKIM+DMARC, `Reply-To` presidiato (R-407…412).

**Link (MailUp Check-up)**
- Link HTTPS assoluti e funzionanti. Tracciamento attivo con **dominio di tracking personalizzato** (R-450/451).
- UTM `utm_source`, `utm_medium=email`, `utm_campaign`, senza spazi (R-452).
- Campi dinamici nella sintassi della piattaforma (MailUp `[campo]`) con valore di default. Nei link il protocollo va esplicito (`https://[campo]`) (R-453).
- Disiscrizione nel footer, al massimo 2 click (R-454). `tel:` senza spazi, path degli asset senza spazi (R-457/458).

**Design e accessibilità**
- `color-scheme` = `dark` **oppure** `light`, mai `light dark` senza un tema dark completo (R-500).
- Contrasto **calcolato** ≥ 4.5:1 per ogni testo normale, footer compreso (R-501).
- Font: titoli ≥ 22px, corpo ≥ 16px su mobile (classe `.txtm`), legale ≥ 12px, CTA ≥ 15px. Palette di 2–3 colori (R-502/503).
- `aria-hidden` su glifi e separatori. `lang` e `<title>` valorizzati. Ordine DOM = ordine visivo (R-504/505).
- `<img>` con `width`, `height`, `border="0"`, `alt` breve, src HTTPS dalla CDN del brand (niente placeholder). La cella ha `height` e `bgcolor`. Mai testo essenziale solo dentro un'immagine (R-600…603).
- CTA VML + HTML con dimensioni identiche, area ≥ 46×46px, una sola CTA primaria (R-700…703).
- Colonne in px interi (niente `33.33%`), nessuna asimmetria di spaziatura quando si impilano (R-800…802).

**Footer:** motivo di ricezione, ragione sociale, indirizzo, P.IVA, contatti, Annulla iscrizione, Preferenze, Privacy, copyright e social. In produzione **zero segnaposto** (R-900/901).

---

## 5. Baseline Mailtrap (unici warning ammessi)

| Rule | Motivo |
|---|---|
| `style` | Il blocco style serve per responsive e angoli |
| `@media`, `@media max-width` | Media query mobile |
| `width`/`display`/`height`/`font-size`/`line-height` dentro la media query | Colonne impilate e tipografia mobile |
| `border-radius` (1 riga) | Su Outlook gli angoli restano squadrati |
| `display` sul preheader | È l'unico modo per nasconderlo |

SpamAssassin in test: `MISSING_MID` 0.1 (il Message-ID lo aggiunge l'MTA di produzione) e `HTML_MESSAGE` 0.0. **Qualsiasi altra voce va corretta.**

Market Support di Mailtrap ≥ 95% (per Mailtrap ≥ 90% è accettabile, sotto l'85% va rifatta).

---

## 6. Checklist manuale (se il linter non c'è)

- [ ] Nessun `style=""` nel body con proprietà fuori whitelist, preheader a parte
- [ ] Ogni colore di sfondo è `bgcolor`, ogni spaziatura è una cella, ogni bordo è una tabella con `cellpadding="1"`
- [ ] `<style>` = 1 riga di radius + 1 riga `@media (max-width:620px)`
- [ ] `grep -P '[^\x00-\x7F]'` sull'HTML non trova nulla
- [ ] Nessun `&#847;`/`&zwnj;` nel sorgente
- [ ] `<body>` con `bgcolor`, `text`, `link`, `marginwidth`, `marginheight`
- [ ] Contrasti ≥ 4.5:1 calcolati (script o tool), footer e separatori compresi
- [ ] Ogni `<img>` ha width, height, border="0", alt, src HTTPS; la cella ha height e bgcolor
- [ ] CTA VML e HTML con la stessa larghezza e altezza
- [ ] Colonne in px interi con somma corretta
- [ ] Oggetto 35–50 caratteri, preheader 40–100
- [ ] Text/plain allineato, List-Unsubscribe e One-Click nel payload
- [ ] Link HTTPS con UTM e disiscrizione presenti
- [ ] Nessun segnaposto se è per la produzione

---

## 7. Formato del report di consegna

```
Versione: vN  |  Peso HTML: xx KB  |  Oggetto: "…" (nn car.)  |  Preheader: nn car.
G1 Lint: PASS (0 MUST, n SHOULD)      G2 Render: PASS (600/375/no-style/img-off)
G3 HTML Check: xx% — warning: [solo baseline | elenco extra + fix]
G4 Spam: 0.1 (MISSING_MID)            G5 Blacklist: 0      G6 HTML/Text: allineate
G7 MailUp Check-up: [esito | non eseguito]
Deroghe SHOULD motivate: …
Placeholder da sostituire: …
Prossimo passo: …
```

Segnala sempre in modo esplicito le incertezze, per esempio la sintassi del placeholder di disiscrizione della piattaforma da verificare sull'account.
