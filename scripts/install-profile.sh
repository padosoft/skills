#!/usr/bin/env bash
# install-profile.sh - Installa le skill Padosoft di uno o piu' profili.
#
#   ./scripts/install-profile.sh core --global      # profilo core, per tutti i progetti
#   ./scripts/install-profile.sh laravel email      # due profili, nel progetto corrente
#   ./scripts/install-profile.sh --list             # profili disponibili
#   ./scripts/install-profile.sh core --dry-run     # mostra i comandi senza eseguirli
#
# Funziona anche senza clonare il repo:
#   curl -fsSL https://raw.githubusercontent.com/padosoft/skills/main/scripts/install-profile.sh | bash -s -- core --global
#
# Prerequisito: Node.js 18+ (per npx). Nessun account, nessuna configurazione.
set -euo pipefail

REPO="${PADOSOFT_SKILLS_REPO:-padosoft/skills}"
BRANCH="${PADOSOFT_SKILLS_BRANCH:-main}"
RAW="https://raw.githubusercontent.com/${REPO}/${BRANCH}/profiles.json"
PROFILES=(); GLOBAL=0; DRY=0; LIST=0

for arg in "$@"; do
  case "$arg" in
    -g|--global) GLOBAL=1 ;;
    --dry-run)   DRY=1 ;;
    --list)      LIST=1 ;;
    -h|--help)   sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)          echo "Opzione sconosciuta: $arg" >&2; exit 2 ;;
    *)           PROFILES+=("$arg") ;;
  esac
done

# Guard: serve npx
command -v npx >/dev/null || { echo "npx non trovato: installa Node.js 18+ (https://nodejs.org)" >&2; exit 2; }

# profiles.json: locale se siamo nel repo, altrimenti scaricato
LOCAL="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)/profiles.json"
if [[ -f "$LOCAL" ]]; then JSON="$(cat "$LOCAL")"; else
  command -v curl >/dev/null || { echo "curl non trovato e profiles.json non presente in locale" >&2; exit 2; }
  JSON="$(curl -fsSL "$RAW")"
fi

# parser minimale: nessuna dipendenza da jq
names_of() {  # $1 = profilo -> stampa i nomi delle skill, uno per riga
  printf '%s' "$JSON" | tr -d '\n' \
    | sed -n "s/.*\"profiles\"[[:space:]]*:[[:space:]]*{\(.*\)}[[:space:]]*,[[:space:]]*\"scope\".*/\1/p" \
    | tr '}' '\n' | grep -F "\"$1\"" \
    | grep -o '"[a-z0-9-]*"' | grep -v "^\"$1\"$" | tr -d '"'
}
all_profiles() {
  printf '%s' "$JSON" | tr -d '\n' \
    | sed -n 's/.*"profiles"[[:space:]]*:[[:space:]]*{\(.*\)}[[:space:]]*,[[:space:]]*"scope".*/\1/p' \
    | grep -o '"[a-z0-9-]*"[[:space:]]*:' | tr -d '":' | tr -d ' '
}

if [[ $LIST -eq 1 || ${#PROFILES[@]} -eq 0 ]]; then
  echo "Profili disponibili:"; for p in $(all_profiles); do echo "  - $p: $(names_of "$p" | tr '\n' ' ')"; done
  [[ ${#PROFILES[@]} -eq 0 ]] && { echo; echo "Uso: $0 <profilo> [profilo...] [--global] [--dry-run]"; exit 0; }
  exit 0
fi

SCOPE_FLAG=""; [[ $GLOBAL -eq 1 ]] && SCOPE_FLAG="-g"
FAILED=0
for profile in "${PROFILES[@]}"; do
  mapfile -t skills < <(names_of "$profile")
  if [[ ${#skills[@]} -eq 0 ]]; then
    echo "Profilo sconosciuto o vuoto: $profile (usa --list)" >&2; FAILED=1; continue
  fi
  echo "== profilo $profile ${SCOPE_FLAG:+(globale)}"
  for skill in "${skills[@]}"; do
    url="https://github.com/${REPO}/tree/${BRANCH}/skills/${skill}"
    if [[ $DRY -eq 1 ]]; then echo "npx skills add $SCOPE_FLAG $url"; else
      echo "-- $skill"; npx --yes skills add $SCOPE_FLAG "$url" || { echo "   installazione fallita: $skill" >&2; FAILED=1; }
    fi
  done
done
[[ $FAILED -eq 0 ]] && echo "Fatto. 'npx skills list' mostra cosa e' installato e dove."
exit $FAILED
