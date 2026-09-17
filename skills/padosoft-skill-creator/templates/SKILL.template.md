---
name: {{name}}
description: >-
  Usa questa skill quando {{situazioni concrete in cui serve, anche senza le parole chiave del dominio}}:
  {{cosa fa in una riga}}. Non usarla per {{confini: cosa NON copre}}.
license: MIT
compatibility: >-
  {{prerequisiti: runtime, tool, accessi. Togli questa chiave se non ce ne sono.}}
metadata:
  version: 0.1.0
  author: Padosoft
  profiles: {{profili}}
  scope: {{scope}}
  repository: https://github.com/padosoft/skills
  keywords: {{parole chiave separate da virgola}}
---

# {{Titolo}}

{{Una o due righe: cosa produce la skill e qual e' il risultato atteso, misurabile se possibile.}}

---

## 0. Script inclusi

| Script | Uso |
|---|---|
| `scripts/{{script}}.py` | {{cosa fa e comando pronto}} |

## 1. Workflow

1. {{Passo con il comando o il criterio}}
2. {{…}}
3. **Verifica**: {{comando che valida il risultato}} — non consegnare finche' non passa.

## 2. Pattern

```{{linguaggio}}
{{snippet copiabile}}
```

## 3. Gotcha

- {{fatto che contraddice l'assunzione ragionevole}}
- {{errore gia' commesso e come evitarlo}}

## 4. Checklist

- [ ] {{controllo}}
- [ ] {{controllo}}

## 5. Report finale

```
{{template del report che l'agente deve produrre}}
```
