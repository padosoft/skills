# Eval di attivazione

Verificano che il campo `description` di `SKILL.md` attivi la skill sulle richieste giuste e non su quelle
adiacenti. Metodo: [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions).

- `eval_queries.json` — 20 query (10 positive, 10 negative), in italiano come l'uso reale, con near-miss
  volutamente insidiosi (landing page, SPF/DKIM, export MailUp, CSS di una pagina web).
- Criterio: una query positiva passa con tasso di attivazione > 0.5 su 3 run; una negativa passa sotto 0.5.
- Se modifichi `description`, rilancia le eval e riporta il tasso nella PR. Per evitare overfitting, tieni
  ~60% delle query come train e ~40% come validation, e scegli la versione con il miglior risultato sul
  validation set.
