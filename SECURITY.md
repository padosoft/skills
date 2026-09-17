# Politica di sicurezza

## Segnalare una vulnerabilità

Scrivi a **opensource@padosoft.com** con oggetto `SECURITY email-html-builder`. Rispondiamo entro 5 giorni
lavorativi. Non aprire issue pubbliche per problemi di sicurezza.

## Superficie di rischio di questa skill

- **Token.** `MAILTRAP_TOKEN` si passa solo come variabile d'ambiente; `.env` è in `.gitignore` e non va
  committato. Gli script non scrivono mai il token su stdout né nei file generati.
- **Invii.** Gli script inclusi puntano alla **sandbox** Mailtrap (`sandbox.api.mailtrap.io`), che non recapita
  a destinatari reali. Per l'invio di produzione serve un endpoint diverso e una scelta consapevole.
- **Esecuzione.** Gli script usano solo la standard library Python, non scaricano nulla a runtime e non
  eseguono codice contenuto nelle email analizzate: il linter le tratta come testo.
- **Dati.** Non committare mai email con dati personali reali: usa segnaposto o dati fittizi nelle fixture.
