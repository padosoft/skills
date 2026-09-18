# Activation evals

They verify that the `description` field of `SKILL.md` triggers the skill on the right requests and not on
adjacent ones. Method: [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions).

- `eval_queries.json` — 20 queries (10 positive, 10 negative), phrased the way people really ask, with
  deliberately tricky near misses (landing page, SPF/DKIM, MailUp export, CSS of a web page).
- Criterion: a positive query passes with an activation rate > 0.5 over 3 runs; a negative one passes below 0.5.
- If you change the `description`, re-run the evals and report the rate in the PR. To avoid overfitting, keep
  ~60% of the queries as train and ~40% as validation, and pick the version with the best result on the
  validation set.
