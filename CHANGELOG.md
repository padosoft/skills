# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate qui.
Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) e il versionamento è
[SemVer](https://semver.org/lang/it/): *major* quando una regola MUST nuova può invalidare template esistenti.

## [2.0.0] - 2026-09-17

### Modificato
- **Il repository diventa `padosoft/skills`**, monorepo delle skill aziendali. La skill email vive in
  `skills/padosoft-email-html-builder/` e non cambia nome: chi l'ha installata non deve fare nulla.
- Marketplace Claude Code **multi-pacchetto**: `padosoft-core` e `padosoft-email` in `plugins/`, così si
  installa il pacchetto dello stack invece dell'intero catalogo.

### Aggiunto
- README: sezione **Skill disponibili** generata dal frontmatter, con una scheda per skill (cosa fa, quando si
  attiva, profili, scope, versione, comando di installazione); `build_catalog.py --check` la verifica come gli
  altri file generati, e un test controlla che nessuna skill resti fuori.
- `skills/padosoft-skill-creator/` — la meta-skill: come si scrive una skill Padosoft (collocazione, description,
  corpo, script, controlli), con `scripts/new_skill.py` per lo scaffolding, il template di SKILL.md e la
  checklist di revisione con gli errori ricorrenti.
- `skills/padosoft-skills-router/` — skill globale che fa da catalogo vivo: dice quale skill serve per il
  progetto aperto e con quale comando installarla.
- `scripts/build_catalog.py` — genera `CATALOG.md`, `profiles.json` e la sezione catalogo del router dal
  frontmatter (`metadata.profiles`, `metadata.scope`); con `--check` fallisce se qualcosa non è allineato.
- `scripts/install-profile.sh` e `.ps1` — installazione per profilo, anche via `curl | bash` senza clonare.
- `scripts/validate_plugins.py` — coerenza dei manifest e copertura: nessuna skill può restare fuori dai pacchetti.
- `tests/test_catalog.py` — ogni skill dichiara profilo e scope, prefisso di brand, tetto di 5 skill globali,
  file generati aggiornati, installer funzionante in dry-run.
- CONTRIBUTING: i criteri per scegliere profilo e scope, con il filtro a tre domande per `scope: global`.

## [1.1.0] - 2026-09-17

### Aggiunto
- **Manifest di plugin per Claude Code**: `.claude-plugin/plugin.json` e `.claude-plugin/marketplace.json`.
  Il repository fa da marketplace di se stesso, quindi Claude Code gestisce installazione e aggiornamenti
  (`claude plugin marketplace add padosoft/email-html-builder`).
- README: sezioni dedicate a Claude Code come plugin e a Codex (`~/.agents/skills/`).

### Modificato
- **Layout del repository in stile Vercel**: la skill vive in `skills/padosoft-email-html-builder/`, il percorso
  canonico cercato dal CLI `npx skills`. Il repo puo' ora ospitare piu' skill.
- **Nome con prefisso di brand**: `padosoft-email-html-builder`, per evitare collisioni nell'ecosistema.
- Makefile e CI aggiornati ai nuovi percorsi; `make validate` valida ogni skill presente in `skills/`.
- README riscritto attorno a `npx skills add padosoft/email-html-builder`.

## [1.0.1] - 2026-09-17

### Corretto
- `lint_email.py`: il rilevamento dei segnaposto usava `TODO` senza word boundary e segnalava falsi positivi
  su parole che lo contengono (`METODO_PAGAMENTO`). Ora usa `\bTODO\b` (stesso trattamento per `lorem ipsum`).

### Modificato
- `R-405`/`R-454`: la disiscrizione e' richiesta per le mail commerciali e bulk; le transazionali pure sono
  esenti. Nuovo flag `--transactional` che declassa `R-454` a SHOULD.
- `SKILL.md`: aggiunta la distinzione marketing/transazionale e il percorso "senza Mailtrap" (gate G3-G6
  dichiarati non eseguiti invece che stimati).

## [1.0.0] - 2026-09-17

### Aggiunto
- `SKILL.md`: workflow in 10 fasi con 8 gate di accettazione, pattern HTML riusabili, baseline dei warning
  ammessi e formato del report di consegna.
- `references/rules.md`: ~110 regole `R-xxx` con livello e fonte (Mailtrap, MailUp, Gmail/Yahoo, WCAG,
  errori reali v1→v5), più la tabella degli anti-pattern storici.
- `scripts/lint_email.py`: linter statico senza dipendenze, con contrasto WCAG calcolato, `--json` e
  `--production`; exit 1 sui MUST violati.
- `scripts/validate_skill.py`: validatore della specifica Agent Skills (frontmatter, naming, budget di
  progressive disclosure, riferimenti relativi, bit di esecuzione).
- `scripts/build_payload.py`, `scripts/send_mailtrap_sandbox.sh|.ps1`: payload Mailtrap con
  `List-Unsubscribe` one-click e invio in sandbox.
- `scripts/screenshot_email.py`: gate G2, viste 600/375 px con e senza `<style>`.
- `templates/reference-welcome-dark.html`: template conforme (0 MUST violati).
- `tests/`: unittest del linter con fixture che riproduce tutti gli anti-pattern storici.
- `evals/eval_queries.json`: 20 query per testare l'attivazione della skill.
- CI GitHub Actions su Python 3.10/3.12/3.13.

### Note
- La sintassi esatta del segnaposto di disiscrizione di MailUp non è stata verificata sulla console:
  la regola `R-454` chiede di confermarla sull'account prima della produzione.
