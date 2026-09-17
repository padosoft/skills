---
name: padosoft-skill-creator
description: >-
  Usa questa skill quando si crea, si modifica o si rivede una Agent Skill del repository padosoft/skills,
  quando l'utente vuole trasformare un workflow ricorrente, una checklist o delle linee guida in una skill
  riutilizzabile, oppure quando chiede dove va una skill (profilo, scope, pacchetto) o perche' la CI del repo
  fallisce su catalogo, profili o manifest: guida la creazione end-to-end con lo scaffolding, le convenzioni
  Padosoft e i controlli automatici. Non usarla per scrivere il contenuto tecnico del dominio (quello lo fa
  la skill che stai creando) ne' per installare skill esistenti (se ne occupa padosoft-skills-router).
license: MIT
compatibility: >-
  Richiede Python 3.10+ (solo standard library) e il repository padosoft/skills clonato in locale per
  rigenerare catalogo e profili. Node.js 18+ solo per provare l'installazione con npx skills.
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: core
  scope: global
  repository: https://github.com/padosoft/skills
  keywords: skill, agent skills, scaffolding, SKILL.md, frontmatter, profili, catalogo, CI
---

# Padosoft Skill Creator

Crea skill che rispettano **la specifica Agent Skills** e **le convenzioni di `padosoft/skills`**, senza
doverle ricordare a memoria. Il risultato atteso: `make all` verde al primo colpo e la skill che si attiva
quando serve, non quando capita.

---

## 0. Cosa c'e' in questa skill

| File | Uso |
|---|---|
| `scripts/new_skill.py` | Scaffolding: crea `skills/<nome>/` con SKILL.md compilato, cartelle e file di eval. `--help` per le opzioni. |
| `templates/SKILL.template.md` | Lo scheletro usato dallo scaffolding, se serve partire a mano. |
| `references/checklist.md` | Checklist di revisione prima della PR e gli errori ricorrenti da evitare. |

Gli script di validazione **stanno nel repo**, non qui: **scripts/build_catalog.py**, **scripts/validate_plugins.py** e
**skills/padosoft-email-html-builder/scripts/validate_skill.py** (path del repo, non di questa skill).

---

## 1. Prima di scrivere: la skill serve davvero?

Rispondi a queste tre, in ordine. Se una risposta e' no, fermati e dillo all'utente.

1. **L'agente sbaglia senza queste istruzioni?** Se il modello se la cava gia' bene da solo, la skill aggiunge
   contesto e non qualita'. Provalo: stesso prompt senza skill, guarda l'output.
2. **Il know-how e' reale e verificabile?** Regole nate da errori concreti, report di tool, review, incidenti.
   Una skill sintetizzata da articoli generici produce consigli generici.
3. **E' un'unita' coerente?** Ne' troppo stretta (due skill che devono caricarsi insieme per un compito solo),
   ne' troppo larga (una skill che copre backend, deploy e monitoraggio).

Il materiale migliore: una sessione reale in cui il lavoro e' riuscito, con le correzioni che l'utente ha
dovuto fare. Quelle correzioni diventano i "gotcha", la parte piu' preziosa della skill.

---

## 2. Workflow

1. **Raccogli il know-how** dalla fonte reale: trascrizione della sessione, PR e review, runbook, report di
   tool, incidenti. Chiedi all'utente i file, non ricostruire a memoria.
2. **Decidi collocazione e nome** (§3). Il nome ha sempre il prefisso `padosoft-`.
3. **Scaffolding**:
   ```bash
   python3 skills/padosoft-skill-creator/scripts/new_skill.py laravel-conventions \
     --profiles laravel --scope project --title "Convenzioni Laravel Padosoft"
   ```
   Crea `skills/padosoft-laravel-conventions/` con SKILL.md precompilato, `references/`, `scripts/`,
   `evals/queries.json` e il frontmatter gia' corretto.
4. **Scrivi la `description`** (§4): e' il campo che decide se la skill si attiva. Dedicaci piu' tempo del resto.
5. **Scrivi il corpo** (§5): workflow numerato, pattern copiabili, gotcha, checklist. Sotto le 500 righe.
6. **Sposta i dettagli in `references/`** e di' **quando** leggerli (esempio: "apri il file degli errori API in references/ se il tool risponde 4xx").
7. **Aggiungi uno script** solo se l'agente rifarebbe la stessa logica ogni volta (§6).
8. **Rigenera e valida**:
   ```bash
   make catalog   # CATALOG.md, profiles.json, catalogo del router
   make all       # validate + test + lint
   ```
9. **Aggiungi la skill a un pacchetto** in `plugins/` (`padosoft-core`, `padosoft-email`, …): se resta scoperta,
   validate_plugins.py del repo fallisce.
10. **Prova sul campo**: sessione nuova, un compito reale, nessun suggerimento. Poi correggi cio' che e' andato
    storto e aggiungi la correzione ai gotcha. Una sola iterazione di questo tipo migliora molto la skill.
11. **CHANGELOG** e PR.

---

## 3. Collocazione: profilo, scope, nome

```yaml
metadata:
  profiles: laravel, api    # uno o piu' profili di KNOWN_PROFILES (scripts/build_catalog.py)
  scope: project            # project | global
```

- **`scope: global`** solo se passa il filtro a tre domande: serve su qualunque stack, e' corretta ovunque,
  e la sua assenza sarebbe un problema. Le globali stanno nel profilo `core` e un test le ferma a cinque.
- **`profiles`**: per stack (`laravel`, `node`, `react-native`) o per dominio (`email`, `api`, `payments`,
  `data`, `devops`). Piu' profili solo se la skill serve davvero in entrambi. Mai creare un profilo per una
  skill sola: aggiungerne uno significa modificare KNOWN_PROFILES in PR.
- **Nome**: `padosoft-<dominio>-<cosa-fa>`, minuscolo, trattini, uguale alla cartella. Descrittivo del compito,
  non del contenuto: `padosoft-laravel-conventions`, non `padosoft-laravel-docs`.

---

## 4. La `description`: il campo che conta

E' l'unica cosa che l'agente legge finche' non attiva la skill. Struttura che funziona:

```
Usa questa skill quando <situazioni concrete, anche senza le parole chiave del dominio>:
<cosa fa, in una riga>. Non usarla per <confini>.
```

Regole:

- **Imperativa**, rivolta all'agente: "Usa questa skill quando…", non "Questa skill fornisce…".
- **Elenca le situazioni**, comprese quelle in cui l'utente non nomina il dominio ("la mail si rompe su Outlook"
  invece di "email HTML").
- **Dichiara i confini**: cosa NON copre. Con molte skill installate e' cio' che evita le attivazioni sbagliate.
- Massimo **1024 caratteri**, di solito ne bastano 400-600.

Poi scrivi le eval in `evals/`: 8-10 query che devono attivarla e 8-10 che **non** devono, scegliendo come
negative i casi vicini (stesso dominio, compito diverso). Sono quelle che misurano davvero la qualita'.

---

## 5. Il corpo: cosa mettere e cosa no

**Metti:**

- Workflow numerato, con i gate ("non consegnare finche' X non e' verde").
- Pattern **copiabili**, non descritti a parole: snippet, comandi, template di output.
- **Gotcha**: i fatti che contraddicono le assunzioni ragionevoli. Vanno in SKILL.md, non nei reference: l'agente
  deve leggerli prima di sbatterci contro.
- Un default esplicito quando esistono piu' strade ("usa X; per il caso Y, Z").
- Il formato del report finale, come template.

**Non mettere:**

- Cio' che l'agente gia' sa (cos'e' un JWT, come funziona HTTP).
- Elenchi di alternative equivalenti senza un default.
- Ogni caso limite immaginabile: la sovra-specificazione fa piu' danni della sotto-specificazione.
- Prosa di contesto aziendale non operativa.

Taratura: **prescrittivo** dove l'operazione e' fragile o la sequenza conta ("esegui esattamente questo comando");
**permissivo** dove le strade valide sono molte, spiegando il perche' invece del come.

---

## 6. Script inclusi nella skill

Aggiungili solo se l'agente rifarebbe la stessa logica a ogni esecuzione, o se serve un validatore per il
ciclo correggi-verifica. Requisiti Padosoft:

- Solo **standard library** (Python 3.10+), così girano ovunque e in CI.
- **Nessun prompt interattivo**: tutto da flag o variabili d'ambiente.
- `--help` con esempi, **exit code distinti** (0 ok, 1 problemi, 2 errore di esecuzione), `--json` se l'output
  serve alla CI.
- Messaggi d'errore che dicono cosa fare, non solo cosa e' andato storto.
- Guard clause in testa, type hint completi, commenti sul perche'.

Documentali in una tabella all'inizio di SKILL.md, con il comando pronto.

---

## 7. Controlli automatici del repo

| Comando | Cosa verifica |
|---|---|
| `make catalog` | Rigenera `CATALOG.md`, `profiles.json` e il catalogo dentro il router |
| `make validate` | Frontmatter conforme alla specifica, catalogo allineato, manifest dei plugin coerenti |
| `make test` | Profilo e scope dichiarati, prefisso di brand, tetto delle skill globali, installer in dry-run |
| `make all` | Tutto, come in CI |

Se build_catalog.py --check fallisce, quasi sempre manca un `make catalog` dopo aver toccato il frontmatter.

---

## 8. Gotcha del formato (errori gia' fatti)

- **`name` diverso dalla cartella**: la skill non viene caricata. Devono coincidere, prefisso compreso.
- **Frontmatter con chiavi fuori specifica**: ammesse solo `name`, `description`, `license`, `compatibility`,
  `metadata`, `allowed-tools`. Tutto il resto va dentro `metadata`.
- **Riferimenti a file inesistenti**: validate_skill.py segnala ogni path della cartella scripts citato fra backtick
  che non esiste. Se citi uno script del repo, non della skill, non usare i backtick con path relativo.
- **SKILL.md oltre le 500 righe o i 5000 token**: sposta in `references/` e di' quando leggerli.
- **Skill non inclusa in nessun pacchetto** `plugins/`: invisibile a chi installa da Claude Code.
- **`scope: global` senza profilo `core`**: la CI lo blocca, ed e' giusto: le globali si contano.
- **Description che parla della skill invece che dell'utente**: si attiva a caso o non si attiva affatto.

---

## 9. Report finale

```
Skill: padosoft-<nome>  ·  profili: <…>  ·  scope: <…>  ·  versione: 0.1.0
Fonte del know-how: <sessione/PR/runbook/report>
make all: PASS (validate, N test, lint)
Pacchetto: plugins/<pacchetto>
Eval: <n> query (<p> positive, <n> negative) — attivazioni corrette <x>/<y>
Prova sul campo: <compito reale eseguito, iterazioni, correzioni aggiunte ai gotcha>
Da decidere/verificare: <…>
```
