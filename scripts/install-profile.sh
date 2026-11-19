#!/usr/bin/env bash
# install-profile.sh - Installs the Padosoft skills of one or more profiles.
#
#   ./scripts/install-profile.sh core --global      # core profile, for every project
#   ./scripts/install-profile.sh laravel email      # two profiles, in the current project
#   ./scripts/install-profile.sh --list             # available profiles
#   ./scripts/install-profile.sh core --dry-run     # print the commands without running them
#   ./scripts/install-profile.sh core -g --agent claude-code   # no questions asked (-y implied)
#   ./scripts/install-profile.sh core -g --agent '*'           # every detected agent
#
# Works without cloning the repo too:
#   curl -fsSL https://raw.githubusercontent.com/padosoft/skills/main/scripts/install-profile.sh | bash -s -- core --global
#
# Piped from curl, stdin is the script itself: the agent question is then asked on the terminal
# (/dev/tty); without a terminal, pass --agent.
#
# Requirement: Node.js 18+ (for npx). No account, no configuration.
set -euo pipefail

REPO="${PADOSOFT_SKILLS_REPO:-padosoft/skills}"
BRANCH="${PADOSOFT_SKILLS_BRANCH:-main}"
RAW="https://raw.githubusercontent.com/${REPO}/${BRANCH}/profiles.json"
PROFILES=(); GLOBAL=0; DRY=0; LIST=0

AGENT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -g|--global) GLOBAL=1 ;;
    --dry-run)   DRY=1 ;;
    --list)      LIST=1 ;;
    -a|--agent)  [[ $# -ge 2 ]] || { echo "--agent needs a value (a name or '*')" >&2; exit 2; }
                 AGENT="$2"; shift ;;
    -h|--help)   sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)          echo "Unknown option: $1" >&2; exit 2 ;;
    *)           PROFILES+=("$1") ;;
  esac
  shift
done

# Guard: npx is required
command -v npx >/dev/null || { echo "npx not found: install Node.js 18+ (https://nodejs.org)" >&2; exit 2; }

# profiles.json: the local copy when running from the repo, otherwise downloaded
LOCAL="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)/profiles.json"
if [[ -f "$LOCAL" ]]; then JSON="$(cat "$LOCAL")"; else
  command -v curl >/dev/null || { echo "curl not found and profiles.json missing locally" >&2; exit 2; }
  JSON="$(curl -fsSL "$RAW")"
fi

# minimal parser: no dependency on jq
profiles_block() {  # the content of the "profiles" object, collapsed onto one line
  printf '%s' "$JSON" | tr -d '\n' \
    | sed -n 's/.*"profiles"[[:space:]]*:[[:space:]]*{\(.*\)}[[:space:]]*,[[:space:]]*"scope".*/\1/p'
}
names_of() {  # $1 = profile -> prints the skill names, one per line
  # The array of the requested profile only: the whole block is a single line, so matching
  # the profile name alone would pick up every other profile's skills as well.
  profiles_block \
    | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\[\([^]]*\)\].*/\1/p" \
    | grep -o '"[^"]*"' | tr -d '"'
}
all_profiles() {
  profiles_block | grep -o '"[a-z0-9-]*"[[:space:]]*:[[:space:]]*\[' | sed 's/^"\([^"]*\)".*/\1/'
}

if [[ $LIST -eq 1 || ${#PROFILES[@]} -eq 0 ]]; then
  echo "Available profiles:"; for p in $(all_profiles); do echo "  - $p: $(names_of "$p" | tr '\n' ' ')"; done
  [[ ${#PROFILES[@]} -eq 0 ]] && { echo; echo "Usage: $0 <profile> [profile...] [--global] [--dry-run]"; exit 0; }
  exit 0
fi

SCOPE_FLAG=""; [[ $GLOBAL -eq 1 ]] && SCOPE_FLAG="-g"
# npx must never read this script's stdin (a pipe under curl | bash).
# With --agent nothing is asked; otherwise the question goes to the real terminal.
AGENT_ARGS=(); INPUT=/dev/null
if [[ -n "$AGENT" ]]; then AGENT_ARGS=(--agent "$AGENT" -y)
elif [[ $DRY -eq 0 ]]; then
  if { : </dev/tty; } 2>/dev/null; then INPUT=/dev/tty
  else echo "No terminal for the agent question: pass --agent <name> (or --agent '*')." >&2; exit 2; fi
fi
FAILED=0
for profile in "${PROFILES[@]}"; do
  # No mapfile: it needs bash 4+, and macOS ships bash 3.2.
  skills=()
  while IFS= read -r line; do
    line="${line%$'\r'}"   # CRLF-safe (Windows checkouts)
    [[ -n "$line" ]] && skills+=("$line")
  done < <(names_of "$profile")
  if [[ ${#skills[@]} -eq 0 ]]; then
    echo "Unknown or empty profile: $profile (use --list)" >&2; FAILED=1; continue
  fi
  echo "== profile $profile ${SCOPE_FLAG:+(global)}"
  for skill in "${skills[@]}"; do
    url="https://github.com/${REPO}/tree/${BRANCH}/skills/${skill}"
    if [[ $DRY -eq 1 ]]; then echo "npx skills add $SCOPE_FLAG ${AGENT_ARGS[*]:-} $url"; else
      echo "-- $skill"
      npx --yes skills add $SCOPE_FLAG ${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"} "$url" <"$INPUT" || { echo "   installation failed: $skill" >&2; FAILED=1; }
    fi
  done
done
[[ $FAILED -eq 0 ]] && echo "Done. 'npx skills list' shows what is installed and where."
exit $FAILED
