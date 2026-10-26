#!/usr/bin/env bash
# The telemetry run, end to end: pull both vaults, drain the lane into the private telemetry vault, classify the
# sessions and write the curated stats into the public stats vault, then commit and push both.
#
#   SG_SEND_ACCESS_TOKEN=... build/telemetry_flow.sh <telemetry vault clone> <public stats vault clone>
#
# Both clones live outside the newsroom's repositories (CLAUDE.md). The site's copies (telemetry-report.json and
# telemetry-public.json) are written into the data repository's files/ (a clone beside the press, found by
# build/newsroom_paths.py, or NEWSROOM_DATA_FILES) and go out with that repository's tools/release.sh, which this
# script runs last when RELEASE_TRAILER is set. The data folder is found before the lane is touched: a run that cannot
# write the site's copies drains nothing.
# The in-browser drain (the telemetry vault's own Queue & drain page) updates the private vault only: an app cannot
# write to another vault, so the public stats wait for the next run of this script.
set -euo pipefail
DATA=${1:?telemetry vault clone}; PUB=${2:?public stats vault clone}
HERE=$(cd "$(dirname "$0")" && pwd)
: "${SG_SEND_ACCESS_TOKEN:?set SG_SEND_ACCESS_TOKEN}"
FILES=$(python3 "$HERE/newsroom_paths.py")              # exits, naming the folder, when there is no data clone
for v in "$DATA" "$PUB"; do (cd "$v" && sgit pull >/dev/null); done
out=$(python3 "$HERE/telemetry_drain.py" --vault "$DATA" --data "$FILES")
echo "$out"
n=$(echo "$out" | sed -n 's/^pending: //p')
at=$(date -u +%Y-%m-%dT%H:%MZ)
push() { (cd "$1" && if sgit status | grep -q 'Nothing to commit'; then echo "$2: nothing to commit"; else sgit commit -m "$3" >/dev/null && sgit push --token "$SG_SEND_ACCESS_TOKEN" | grep -E 'Push complete|Pushed' ; fi); }
push "$DATA" "telemetry vault" "dev@php.newsroom: drain $at: ${n:-0} events from the lane"   # the drained rows are safe in the vault before anything else runs
pub=$(python3 "$HERE/telemetry_publish.py" --vault "$DATA" --public "$PUB" --data "$FILES")
echo "$pub"
push "$DATA" "telemetry vault" "dev@php.newsroom: drain $at: report and classes regenerated"
push "$PUB" "public stats vault" "dev@php.newsroom: stats as of $at (drain of ${n:-0} events)"
if [ -n "${RELEASE_TRAILER:-}" ]; then
  (cd "$FILES/.." && tools/release.sh "telemetry: the public report and stats as of $at")
else
  echo "the site's copies are in $FILES; release them: (cd $FILES/.. && RELEASE_TRAILER='Agent: <you>' tools/release.sh \"telemetry as of $at\")"
fi
