# Security policy

## Reporting a vulnerability

Write to **opensource@padosoft.com** with the subject `SECURITY email-html-builder`. We answer within 5
working days. Do not open public issues for security problems.

## Risk surface of this skill

- **Tokens.** `MAILTRAP_TOKEN` is passed only as an environment variable; `.env` is in `.gitignore` and must
  not be committed. The scripts never write the token to stdout or into generated files.
- **Sends.** The included scripts point at the Mailtrap **sandbox** (`sandbox.api.mailtrap.io`), which does
  not deliver to real recipients. A production send needs a different endpoint and a deliberate choice.
- **Execution.** The scripts use the Python standard library only, download nothing at runtime and never
  execute code contained in the analysed emails: the linter treats them as text.
- **Data.** Never commit emails with real personal data: use placeholders or fake data in the fixtures.
