# Fixture: every shape the provenance scanner must catch

Synthetic. Nothing here refers to a real person, company, host or record — the
point is only that `check_provenance.py` goes red on each line. If a line stops
being caught, the corresponding rule has regressed.

- date — the rollout finished on 2026-07-29 and the check was added after
- email — raised by mario.rossi@acme-spa.example-not-allowed.it
- credential — `AWS_ACCESS_KEY_ID=AKIAZZ7Q4K2LMNOPQRST`
- private-host — the job connects to db01.internal before the migration
- ip-address — the worker still points at 10.0.14.22
- personal-id — the row carried RSSMRA85T10A562S in a log line
- identifier — reproduced on order 4488213
- local-path — the script was written against C:\Users\lpadovani\projects
- narration — our client reported it twice the same week
- incident-topic — written up in the post-mortem afterwards

Suppression needs a reason, and it only covers the line it sits on:

<!-- provenance-ok: the fixture's own example, kept deliberately -->
- suppressed — contact 10.0.14.23 for the details
