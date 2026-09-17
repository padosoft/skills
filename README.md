# padosoft/skills

**Le Agent Skills di Padosoft: un repo, profili per stack, installazione in un comando.**

[![CI](https://github.com/padosoft/skills/actions/workflows/ci.yml/badge.svg)](https://github.com/padosoft/skills/actions/workflows/ci.yml)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-spec%20compliant-5A67D8)](https://agentskills.io/specification)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

Skill compatibili con Claude Code, Codex, Cursor, Copilot, Gemini CLI, OpenCode e gli altri client che
supportano il formato [Agent Skills](https://agentskills.io).

L'elenco completo delle skill, con cosa fanno, quando si attivano e dove vanno installate, è più sotto:
[**Skill disponibili**](#skill-disponibili). La versione tabellare per profilo è in [CATALOG.md](CATALOG.md).

---

## Sei un dev nuovo? Parti da qui

```bash
# 1. le skill trasversali, valide su ogni progetto (poche, per non pesare sul contesto)
curl -fsSL https://raw.githubusercontent.com/padosoft/skills/main/scripts/install-profile.sh | bash -s -- core --global

# 2. lo stack del progetto su cui stai lavorando (dalla cartella del progetto)
curl -fsSL https://raw.githubusercontent.com/padosoft/skills/main/scripts/install-profile.sh | bash -s -- laravel email
```

Il profilo `core` installa due skill trasversali: **il router**, che da quel momento ti dice da solo quali
skill mancano per il progetto che apri, e **lo skill creator**, che serve quando vorrai aggiungerne una nuova.
Se non sai quale profilo ti serve, installa `core` e chiedilo all'agente.

Windows (PowerShell):

```powershell
iwr -useb https://raw.githubusercontent.com/padosoft/skills/main/scripts/install-profile.ps1 | iex; Install-PadosoftSkills core -Global
```

## Skill disponibili

<!-- SKILLS:START - generato da scripts/build_catalog.py, non modificare a mano -->

_3 skill in catalogo. Sezione generata dal frontmatter: si aggiorna con `make catalog`._

| Skill | Profili | Scope | Versione |
|---|---|---|---|
| [`padosoft-skill-creator`](#skill-creator) | core | global | 0.1.0 |
| [`padosoft-skills-router`](#skills-router) | core | global | 0.1.0 |
| [`padosoft-email-html-builder`](#email-html-builder) | email | project | 1.1.0 |

### skill-creator

**`padosoft-skill-creator`** · profili: `core` · scope: `global` · versione: 0.1.0

**Quando si attiva** — Usa questa skill quando si crea, si modifica o si rivede una Agent Skill del repository padosoft/skills, quando l'utente vuole trasformare un workflow ricorrente, una checklist o delle linee guida in una skill riutilizzabile, oppure quando chiede dove va una skill (profilo, scope, pacchetto) o perche' la CI del repo fallisce su catalogo, profili o manifest: guida la creazione end-to-end con lo scaffolding, le convenzioni Padosoft e i controlli automatici. Non usarla per scrivere il contenuto tecnico del dominio (quello lo fa la skill che stai creando) ne' per installare skill esistenti (se ne occupa padosoft-skills-router).

**Dove va** — installata **globalmente** con il profilo `core`: vale su ogni progetto. Cartella: [`skills/padosoft-skill-creator`](skills/padosoft-skill-creator).

```bash
npx skills add https://github.com/padosoft/skills/tree/main/skills/padosoft-skill-creator
```

### skills-router

**`padosoft-skills-router`** · profili: `core` · scope: `global` · versione: 0.1.0

**Quando si attiva** — Usa questa skill quando l'utente chiede quali skill Padosoft esistono, quali installare per il progetto o lo stack corrente, come aggiornarle o rimuoverle, oppure quando stai per lavorare su uno stack aziendale (Laravel, Node/Hono/Workers, React Native/Expo, email HTML, API, pagamenti) e nessuna skill specifica per quello stack risulta installata: indirizza alla skill giusta e fornisce il comando di installazione esatto. Non sostituisce le skill di stack e non svolge il lavoro tecnico al posto loro.

**Dove va** — installata **globalmente** con il profilo `core`: vale su ogni progetto. Cartella: [`skills/padosoft-skills-router`](skills/padosoft-skills-router).

```bash
npx skills add https://github.com/padosoft/skills/tree/main/skills/padosoft-skills-router
```

### email-html-builder

**`padosoft-email-html-builder`** · profili: `email` · scope: `project` · versione: 1.1.0

**Quando si attiva** — Usa questa skill ogni volta che l'utente crea, corregge, converte o revisiona una email HTML (welcome, transazionale, newsletter, DEM, template ESP) o chiede di testarla su Mailtrap o MailUp, anche se non nomina esplicitamente "HTML", "template" o "deliverability": produce email a tabelle con CSS inline minimo, testo/plain allineato, List-Unsubscribe one-click, e le valida con un linter incluso fino a 0 errori, puntando a spam SpamAssassin <= 0.1 e HTML Check senza warning fuori baseline. Non usarla per copywriting senza codice, per configurare DNS/SPF/DKIM o per gestire liste e invii massivi.

**Dove va** — installata **nel progetto** che ne ha bisogno, non globalmente. Cartella: [`skills/padosoft-email-html-builder`](skills/padosoft-email-html-builder).

```bash
npx skills add https://github.com/padosoft/skills/tree/main/skills/padosoft-email-html-builder
```

<!-- SKILLS:END -->

## Profili

I profili sono dichiarati nel frontmatter di ogni skill e raccolti in [`profiles.json`](profiles.json),
generato dalla CI. La regola di convivenza:

| Ambito | Cosa installare | Perché |
|---|---|---|
| **Globale** (`--global`) | Solo il profilo `core` | Ogni skill globale carica nome e descrizione in **ogni** sessione: poche e trasversali |
| **Progetto** | Lo stack di quel repository (`laravel`, `node`, `react-native`, `email`, `api`, `payments`…) | Le skill viaggiano col progetto, non con la macchina |
| **Mai globale** | Skill di dominio stretto (es. protocolli POS) | Attiverebbero a sproposito ovunque |

Consiglio operativo: **committa `.claude/skills/` nel repository del progetto**. Chi clona trova le skill
giuste senza onboarding e senza sapere che questo repo esiste.

## Tutti i comandi

```bash
# per profilo
bash scripts/install-profile.sh --list                  # profili disponibili e cosa contengono
bash scripts/install-profile.sh core --global           # profilo core, installazione globale
bash scripts/install-profile.sh laravel email           # due profili, nel progetto corrente
bash scripts/install-profile.sh core --dry-run          # mostra i comandi senza eseguirli

# singola skill
npx skills add https://github.com/padosoft/skills/tree/main/skills/padosoft-email-html-builder

# tutto il catalogo (sconsigliato: installa anche ciò che non ti serve)
npx skills add padosoft/skills

# manutenzione
npx skills update                                       # aggiorna all'ultima versione pubblicata
npx skills list                                         # cosa è installato e dove
npx skills remove padosoft-email-html-builder           # disinstalla
```

Unico prerequisito: **Node.js 18+**. Nessun account, nessuna registrazione.

## Come plugin di Claude Code

Il repo è anche un **marketplace**: i pacchetti raggruppano le skill per profilo, così installi ciò che
serve e gli aggiornamenti li gestisce Claude.

```bash
claude plugin marketplace add padosoft/skills     # una volta sola
claude plugin install padosoft-core@padosoft      # skill trasversali
claude plugin install padosoft-email@padosoft     # pacchetto email
claude plugin marketplace update padosoft         # controlla e scarica aggiornamenti
```

In sessione valgono `/plugin marketplace add padosoft/skills`, `/plugin install padosoft-email@padosoft`
e `/reload-plugins`. Non installare la stessa skill via CLI **e** via plugin: l'agente la vedrebbe due volte.

## Claude app, Cowork, claude.ai

Il CLI non arriva nelle app: lì si carica uno zip della cartella della singola skill.

1. Comprimi `skills/<nome-skill>/`.
2. **Customize → Skills → "+" → Upload a skill**.
3. Serve l'esecuzione del codice attiva (Settings → Capabilities).

## Codex

Codex legge le skill da `.agents/skills/` nel repository e da `~/.agents/skills/` per l'utente, e rileva le
modifiche da solo. `npx skills add` scrive già nel percorso giusto; in alternativa si copia la cartella a mano.

## Struttura

```
skills/
├── .claude-plugin/marketplace.json     # i pacchetti installabili in Claude Code
├── plugins/                            # un manifest per pacchetto (core, email, …)
├── skills/
│   ├── padosoft-skills-router/         # catalogo vivo: dice quale skill serve e come installarla
│   ├── padosoft-skill-creator/         # meta-skill: scaffolding (new_skill.py), template, checklist di revisione
│   └── padosoft-email-html-builder/    # email HTML che passano Mailtrap e MailUp al primo invio
├── scripts/
│   ├── install-profile.sh|.ps1         # installer per profilo
│   ├── build_catalog.py                # genera CATALOG.md, profiles.json e il catalogo del router
│   └── validate_plugins.py             # coerenza dei manifest e copertura delle skill
├── tests/                              # test di catalogo, profili, installer e linter email
├── evals/                              # query di attivazione per le description
├── CATALOG.md · profiles.json          # generati: non si modificano a mano
└── Makefile                            # make all
```

## Creare una nuova skill

Le convenzioni non vanno ricordate a memoria: le applica [`padosoft-skill-creator`](skills/padosoft-skill-creator),
inclusa nel profilo `core`.

**Il modo veloce** — con `core` installato, in una sessione dell'agente:

> «Creiamo una skill per le convenzioni Laravel di Padosoft»

L'agente carica la meta-skill e ti guida: raccolta del know-how dalla fonte reale, scelta di profilo e scope,
scaffolding, stesura di `description` e corpo, eval, controlli. Il risultato è una skill che passa `make all`.

**Il modo manuale** — lo scaffolding da riga di comando:

```bash
python3 skills/padosoft-skill-creator/scripts/new_skill.py laravel-conventions \
  --profiles laravel api --scope project --title "Convenzioni Laravel Padosoft" --with-scripts
```

Crea `skills/padosoft-laravel-conventions/` con SKILL.md precompilato, `references/`, `evals/queries.json` e
lo scheletro di un validatore. Rifiuta profili inesistenti e `scope: global` senza il profilo `core`: le stesse
regole della CI, applicate prima che tu scriva una riga. Poi:

1. **Compila `description` e corpo.** La `description` decide se la skill si attiva: la meta-skill spiega come
   scriverla (situazioni concrete, confini espliciti) ed elenca gli errori che la rendono inutile.
2. **`make catalog`** rigenera `CATALOG.md`, `profiles.json` e il catalogo dentro il router.
3. **Aggiungi la skill a un pacchetto** in `plugins/`, altrimenti chi installa da Claude Code non la vede e la
   CI fallisce.
4. **`make all`** deve passare.
5. **Provala in una sessione nuova** su un compito reale: le correzioni che devi fare diventano i gotcha della
   skill. Una sola iterazione di questo tipo cambia molto il risultato.

Il frontmatter che decide la collocazione:

```yaml
metadata:
  profiles: laravel, api     # uno o più profili
  scope: project             # project oppure global (global implica il profilo core)
```

Prima della PR, la [checklist di revisione](skills/padosoft-skill-creator/references/checklist.md): elenca i
sintomi e la causa ("la skill non si attiva mai" → description scritta dal punto di vista della skill invece
che dell'utente; "l'agente ignora una regola" → sta nei reference invece che nei gotcha).

I criteri per scegliere profilo e scope — e cosa merita davvero di stare in `core` — sono in
[CONTRIBUTING.md](CONTRIBUTING.md). La CI non indovina nulla: verifica solo che ogni skill dichiari la sua
collocazione, che i file generati siano aggiornati e che nessuna skill resti fuori dai pacchetti.

## Licenza

[MIT](LICENSE) · [Padosoft](https://www.padosoft.com)
