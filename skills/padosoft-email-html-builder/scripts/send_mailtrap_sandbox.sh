#!/usr/bin/env bash
# Invia payload.json alla sandbox Mailtrap. Uso: MAILTRAP_TOKEN=... MAILTRAP_INBOX_ID=... ./send_mailtrap_sandbox.sh [payload.json]
set -euo pipefail
: "${MAILTRAP_TOKEN:?Imposta MAILTRAP_TOKEN}"; : "${MAILTRAP_INBOX_ID:?Imposta MAILTRAP_INBOX_ID}"
PAYLOAD="${1:-$(cd "$(dirname "$0")" && pwd)/payload.json}"
[[ -f "$PAYLOAD" ]] || { echo "Payload non trovato: $PAYLOAD" >&2; exit 1; }
curl -sS --fail-with-body -X POST "https://sandbox.api.mailtrap.io/api/send/${MAILTRAP_INBOX_ID}" \
  -H "Authorization: Bearer ${MAILTRAP_TOKEN}" -H "Content-Type: application/json" --data-binary "@${PAYLOAD}"
echo
