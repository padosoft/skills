# Catalogo delle skill Padosoft

Questo file e' **generato**: si aggiorna leggendo il frontmatter di ogni `SKILL.md`.
Per cambiare profilo o scope di una skill si modifica il suo frontmatter, non questo file.

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
