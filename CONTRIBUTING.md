# Contribuire

Grazie: questa skill vive di casi reali. Una regola vale solo se qualcuno l'ha vista rompersi.

## Principi

1. **Evidenza prima dell'opinione.** Ogni regola nuova o modificata va con un report Mailtrap (HTML Check o
   spam), un Check-up MailUp, uno screenshot del client o un test riproducibile.
2. **Una regola, un ID.** Gli ID `R-xxx` sono stabili: non si riciclano. Se una regola decade, resta nel file
   marcata come deprecata, con la motivazione.
3. **Ogni regola bloccante deve essere verificabile dal linter** o, se non è automatizzabile, deve dirlo
   esplicitamente in `skills/padosoft-email-html-builder/references/rules.md`.
4. **Niente dipendenze esterne** negli script: solo standard library Python, così girano ovunque e in CI.

## Flusso

```bash
git clone https://github.com/padosoft/email-html-builder.git
cd email-html-builder
make all          # validate + test + lint del template
```

1. Apri una issue con il template *Proposta di regola* (o *Bug report*).
2. Fai un branch: `feat/r-123-nome-breve` oppure `fix/lint-falso-positivo`.
3. Modifica in ordine:
   - `skills/padosoft-email-html-builder/references/rules.md` — la regola normativa, con livello (MUST/SHOULD/MAY) e fonte;
   - `skills/padosoft-email-html-builder/scripts/lint_email.py` — il controllo;
   - `tests/` — un test che fallisce senza la fix;
   - `skills/padosoft-email-html-builder/SKILL.md` — solo se cambia il flusso o un pattern, mantenendolo sotto 500 righe;
   - `CHANGELOG.md`.
4. `make all` deve passare. La CI gira su Python 3.10, 3.12 e 3.13.
5. Apri la PR compilando la checklist.

## Aggiungere una regola: esempio

```python
# skills/padosoft-email-html-builder/scripts/lint_email.py
if re.search(r'<td[^>]*background=', html):
    r.add("R-210", "MUST", "Immagine di sfondo su <td>: usa bgcolor o VML per Outlook", line)
```

```python
# tests/test_lint_email.py
EXPECTED = [..., "R-210"]
```

## Dove collocare una skill: profilo e scope

La CI **non decide** questi due campi: li dichiara l'autore nel frontmatter, la CI verifica solo che ci siano,
che il profilo esista e che i file generati siano aggiornati. I criteri sono questi.

```yaml
metadata:
  profiles: laravel, api    # a quali stack serve
  scope: project            # project (default) oppure global
```

### `scope: global` — il filtro è severo

Una skill globale carica nome e descrizione in **ogni** sessione, su ogni progetto, per tutti. Vale la pena
solo se risponde sì a tutte e tre:

1. **Serve su qualunque stack?** Se dipende dal linguaggio o dal framework, non è globale.
2. **È corretta ovunque?** Se le sue regole valgono solo per certi progetti, farebbe danni altrove.
3. **Sarebbe un problema se mancasse?** Se il dev può installarla quando serve, lasciala a livello progetto.

Le skill globali stanno sempre nel profilo `core` e un test fa fallire la CI se superano cinque: è un tetto
volutamente basso, per costringere a scegliere.

### `profiles:` — a quale stack appartiene

- Un profilo per **stack tecnologico** (`laravel`, `node`, `react-native`) o per **dominio applicativo**
  (`email`, `api`, `payments`, `data`, `devops`).
- Una skill può stare in più profili, se serve davvero in entrambi: `padosoft-api-design` sta in `laravel` e
  in `node` perché in quei progetti la si usa sempre.
- **Non** creare un profilo per una singola skill: finché è una sola, sta nel profilo più vicino.
- I profili ammessi sono elencati in `KNOWN_PROFILES` dentro `scripts/build_catalog.py`. Aggiungerne uno è una
  modifica esplicita, che passa da una PR come tutto il resto.

### Poi

1. `make catalog` rigenera `CATALOG.md`, `profiles.json` e il catalogo dentro `padosoft-skills-router`.
2. Aggiungi la skill a un pacchetto in `plugins/`, altrimenti `validate_plugins.py` fallisce: una skill fuori
   da ogni pacchetto sarebbe invisibile a chi installa da Claude Code.
3. Aggiungi qualche query in `evals/` — comprese quelle che devono attivare **altre** skill: con molte skill
   installate, i falsi positivi sono il problema principale.
4. `make all` deve passare.

## Testare le attivazioni della skill

`evals/eval_queries.json` contiene query etichettate (`should_trigger` vero/falso) per verificare che il campo
`description` attivi la skill quando serve e non quando non serve — il metodo è descritto in
[Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions).
Se cambi la `description`, rilancia le eval e riporta il tasso di attivazione nella PR.

## Cosa non accettiamo

- Regole prese da articoli generici senza verifica sui checker.
- Modifiche che rendono il report "più pulito" nascondendo un problema reale invece di risolverlo.
- Dipendenze runtime negli script, o token e dati reali nei file committati.

## Codice di condotta

Vale il [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
Segnalazioni: opensource@padosoft.com.
