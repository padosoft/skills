---
name: padosoft-skills-router
description: >-
  Usa questa skill quando l'utente chiede quali skill Padosoft esistono, quali installare per il progetto
  o lo stack corrente, come aggiornarle o rimuoverle, oppure quando stai per lavorare su uno stack aziendale
  (Laravel, Node/Hono/Workers, React Native/Expo, email HTML, API, pagamenti) e nessuna skill specifica per
  quello stack risulta installata: indirizza alla skill giusta e fornisce il comando di installazione esatto.
  Non sostituisce le skill di stack e non svolge il lavoro tecnico al posto loro.
license: MIT
compatibility: >-
  Richiede Node.js 18+ per i comandi npx skills. Nessuna dipendenza aggiuntiva.
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: core
  scope: global
  repository: https://github.com/padosoft/skills
  keywords: skills, catalogo, onboarding, installazione, padosoft
---

# Padosoft Skills Router

Indice delle skill aziendali. Serve a una cosa sola: **capire quale skill serve adesso e dire come installarla**.

## Quando intervenire

1. L'utente chiede quali skill ci sono, quali installare, o come aggiornarle.
2. Stai per lavorare su uno stack aziendale e **non** vedi installata la skill che lo copre: segnalalo in una riga,
   proponi il comando, e prosegui comunque col lavoro se l'utente non la installa.
3. Un nuovo progetto viene inizializzato: proponi il profilo adatto a ciò che vedi nel repository
   (`composer.json` con Laravel → profilo `laravel`; `app.json`/Expo → `react-native`; template email → `email`).

Non intervenire quando la skill di stack è già attiva: in quel caso il lavoro è suo, non tuo.

## Comandi

```bash
# per profilo (consigliato) - non richiede di clonare il repo
curl -fsSL https://raw.githubusercontent.com/padosoft/skills/main/scripts/install-profile.sh | bash -s -- core --global
curl -fsSL https://raw.githubusercontent.com/padosoft/skills/main/scripts/install-profile.sh | bash -s -- laravel email

# dentro il repo clonato: bash scripts/install-profile.sh core --global

# singola skill, aggiornamento, elenco
npx skills add https://github.com/padosoft/skills/tree/main/skills/<nome-skill>
npx skills update
npx skills list
```

Regola d'uso: **globale** solo il profilo `core`; lo stack si installa **nel progetto** e si committa, così chi
clona se lo ritrova senza onboarding.

## Catalogo

<!-- CATALOG:START - generato da scripts/build_catalog.py, non modificare a mano -->

_3 skill · indice generato automaticamente, non modificare a mano._

| Skill | Profili | Scope | Cosa fa |
|---|---|---|---|
| [`padosoft-email-html-builder`](https://github.com/padosoft/skills/tree/main/skills/padosoft-email-html-builder) | email | project | Usa questa skill ogni volta che l'utente crea, corregge, converte o revisiona una email HTML (welcome, transazionale, newsletter, DEM, template ESP) o chiede di… |
| [`padosoft-skill-creator`](https://github.com/padosoft/skills/tree/main/skills/padosoft-skill-creator) | core | global | Usa questa skill quando si crea, si modifica o si rivede una Agent Skill del repository padosoft/skills, quando l'utente vuole trasformare un workflow ricorrent… |
| [`padosoft-skills-router`](https://github.com/padosoft/skills/tree/main/skills/padosoft-skills-router) | core | global | Usa questa skill quando l'utente chiede quali skill Padosoft esistono, quali installare per il progetto o lo stack corrente, come aggiornarle o rimuoverle, oppu… |

## Profili

- **core** — `padosoft-skill-creator`, `padosoft-skills-router`
- **email** — `padosoft-email-html-builder`

## Installazione per profilo

```bash
./scripts/install-profile.sh core --global      # trasversali, su tutti i progetti
./scripts/install-profile.sh laravel email      # lo stack di questo progetto
```

## Installazione di una singola skill

```bash
npx skills add https://github.com/padosoft/skills/tree/main/skills/padosoft-email-html-builder
npx skills add https://github.com/padosoft/skills/tree/main/skills/padosoft-skill-creator
npx skills add https://github.com/padosoft/skills/tree/main/skills/padosoft-skills-router
```

<!-- CATALOG:END -->

## Cosa NON fare

- Non installare nulla senza dirlo all'utente: proponi il comando, decide lui.
- Non proporre l'intero repository (`npx skills add padosoft/skills`) se non è quello che l'utente vuole:
  installerebbe tutte le skill, comprese quelle irrilevanti per il progetto.
- Non duplicare l'installazione: se una skill è già presente via plugin di Claude Code, non aggiungerla anche via CLI.
