# Email delivery report

Version: **vN** · HTML weight: **xx KB** · Subject: "…" (nn chars) · Preheader: nn chars

| Gate | Tool | Result |
|---|---|---|
| G1 Lint | `scripts/lint_email.py` | PASS — 0 MUST, n SHOULD |
| G2 Render | screenshots 600/375, with and without `<style>`, images blocked | PASS |
| G3 HTML Check | Mailtrap | xx% Market Support — warnings: baseline only |
| G4 Spam | SpamAssassin | 0.1 (`MISSING_MID`) |
| G5 Blacklist | Mailtrap | 0 listings |
| G6 HTML/Text | Template Inspector | aligned |
| G7 Check-up | MailUp | 0 problems |
| G8 Links | crawl | n/n HTTP 200, valid UTM |

**Warnings outside the baseline:** none *(or: rule, client, reason, fix applied)*

**SHOULD exceptions with rationale:** …

**Placeholders to replace before production:** …

**Uncertainties to verify:** …

**Next step:** …
