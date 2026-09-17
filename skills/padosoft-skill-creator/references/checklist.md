# Checklist di revisione di una skill

Da usare prima della PR, e in review. Se una voce non passa, la skill non e' pronta.

## Attivazione

- [ ] La `description` inizia con "Usa questa skill quando…" e elenca **situazioni**, non funzionalita'
- [ ] Include almeno un caso in cui l'utente **non nomina** il dominio
- [ ] Dichiara i confini: "Non usarla per…"
- [ ] Sotto i 1024 caratteri
- [ ] `evals/queries.json` ha almeno 8 positive e 8 negative, con near-miss veri (stesso dominio, compito diverso)
- [ ] Nessuna sovrapposizione con una skill esistente: se c'e', o si uniscono o si separano i confini nelle due description

## Contenuto

- [ ] SKILL.md sotto le 500 righe e i ~5000 token
- [ ] Workflow numerato con almeno un gate di verifica
- [ ] Almeno un pattern copiabile (snippet o comando), non solo descrizioni
- [ ] Sezione gotcha con fatti che contraddicono le assunzioni ragionevoli
- [ ] Un default esplicito dove esistono piu' strade
- [ ] Template del report finale
- [ ] Niente spiegazioni di cose che l'agente sa gia'
- [ ] I dettagli stanno in `references/`, e SKILL.md dice **quando** leggerli

## Formato

- [ ] `name` uguale alla cartella, con prefisso `padosoft-`
- [ ] Frontmatter solo con chiavi ammesse (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`)
- [ ] `metadata.profiles` e `metadata.scope` presenti e coerenti (`global` implica `core`)
- [ ] Ogni path citato fra backtick esiste dentro la skill
- [ ] Script: solo standard library, `--help`, exit code distinti, nessun prompt interattivo

## Integrazione nel repo

- [ ] La skill e' inclusa in un pacchetto sotto `plugins/`
- [ ] `make catalog` eseguito dopo l'ultima modifica al frontmatter
- [ ] `make all` verde
- [ ] CHANGELOG aggiornato
- [ ] Provata in una sessione nuova su un compito reale, con le correzioni riportate nei gotcha

## Errori ricorrenti

| Sintomo | Causa quasi sempre |
|---|---|
| La skill non si attiva mai | Description scritta dal punto di vista della skill, non dell'utente |
| Si attiva a sproposito | Mancano i confini ("Non usarla per…") o il dominio e' descritto troppo in astratto |
| L'agente ignora una regola | La regola e' in `references/` invece che nei gotcha di SKILL.md |
| L'agente prova tre strade prima di trovarne una | Nessun default dichiarato |
| CI rossa su `build_catalog.py --check` | Manca `make catalog` dopo aver toccato il frontmatter |
| CI rossa su `validate_plugins.py` | La skill non e' in nessun pacchetto di `plugins/` |
