#!/usr/bin/env bash
# The telemetry run, end to end: pull both vaults, drain the lane into the private telemetry vault, classify the
# sessions and write the curated stats into the public stats vault, then commit and push both.
#
#   SG_SEND_ACCESS_TOKEN=... admin/build/telemetry_flow.sh <telemetry vault clone> <public stats vault clone>
#
# Both clones live outside this repository (CLAUDE.md). The site's copies (data/telemetry-report.json and
# data/telemetry-public.json) are written here too and go out with the next admin/build/release.sh.
# The in-browser drain (the telemetry vault's own Queue & drain page) updates the private vault only: an app cannot
# write to another vault, so the public stats wait for the next run of this script.
set -euo pipefail
DATA=${1:?telemetry vault clone}; PUB=${2:?public stats vault clone}
HERE=$(cd "$(dirname "$0")" && pwd); SITE=$(cd "$HERE/../.." && pwd)
: "${SG_SEND_ACCESS_TOKEN:?set SG_SEND_ACCESS_TOKEN}"
for v in "$DATA" "$PUB"; do (cd "$v" && sgit pull >/dev/null); done
out=$(python3 "$HERE/telemetry_drain.py" --vault "$DATA" --site "$SITE")
echo "$out"
n=$(echo "$out" | sed -n 's/^pending: //p')
pub=$(python3 "$HERE/telemetry_publish.py" --vault "$DATA" --public "$PUB" --site "$SITE")
echo "$pub"
at=$(date -u +%Y-%m-%dT%H:%MZ)
push() { (cd "$1" && if sgit status | grep -q 'Nothing to commit'; then echo "$2: nothing to commit"; else sgit commit -m "$3" >/dev/null && sgit push --token "$SG_SEND_ACCESS_TOKEN" | grep -E 'Push complete|Pushed' ; fi); }
push "$DATA" "telemetry vault" "dev@php.newsroom: drain $at: ${n:-0} events from the lane; report and classes regenerated"
push "$PUB" "public stats vault" "dev@php.newsroom: stats as of $at (drain of ${n:-0} events)"
