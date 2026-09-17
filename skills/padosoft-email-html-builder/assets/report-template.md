# Report di consegna email

Versione: **vN** · Peso HTML: **xx KB** · Oggetto: "…" (nn car.) · Preheader: nn car.

| Gate | Strumento | Esito |
|---|---|---|
| G1 Lint | `scripts/lint_email.py` | PASS — 0 MUST, n SHOULD |
| G2 Render | screenshot 600/375, con e senza `<style>`, immagini bloccate | PASS |
| G3 HTML Check | Mailtrap | xx% Market Support — warning: solo baseline |
| G4 Spam | SpamAssassin | 0.1 (`MISSING_MID`) |
| G5 Blacklist | Mailtrap | 0 listing |
| G6 HTML/Text | Template Inspector | allineate |
| G7 Check-up | MailUp | 0 problemi |
| G8 Link | crawl | n/n HTTP 200, UTM validi |

**Warning fuori baseline:** nessuno *(oppure: regola, client, motivo, fix applicata)*

**Deroghe SHOULD motivate:** …

**Placeholder da sostituire prima della produzione:** …

**Incertezze da verificare:** …

**Prossimo passo:** …
