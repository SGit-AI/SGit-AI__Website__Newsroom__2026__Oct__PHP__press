#!/usr/bin/env bash
# The chain: what carries the agents' writes to the sites while v1 still builds the pages (step A of the split).
#
#   tools/chain.sh "<one sentence: what changed and why>"
#
# Run from a folder that holds all seven clones side by side (sgit-ai__website__newsroom__2026__oct__php and its six
# __press, __data, __team, __site, __refs, __updates), with RELEASE_TRAILER set as every release wants it. In order:
#   1. export: what was written in the six since their last import goes into v1 (team's records, data's files, the press's
#      assets, build and rules, site's and updates' content: each repository's sync, export);
#   2. v1 releases (its build, its gate, its push), if anything changed;
#   3. the press imports v1's assets, build and rules (never over a change made there) and releases (no version when nothing changed);
#   4. data imports from v1 and releases (no version when the files are the same);
#   5. team imports from v1 (never over a change made there);
#   6. the four sites are cut against the press and data versions, gated, checked for parity; site and updates import their
#      content; every site released.
# Every step is that repository's own tool with its own gate; the chain only orders them and stops at the first failure.
# Never --no-verify, never a force-push, never main.
set -euo pipefail
MSG="${1:?message required}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"; cd "$(dirname "$HERE")"
V=sgit-ai__website__newsroom__2026__oct__php
for r in "$V" "${V}__press" "${V}__data" "${V}__team" "${V}__site" "${V}__refs" "${V}__updates"; do
  [ -d "$r/.git" ] || { echo "chain: $r is not cloned beside the press"; exit 2; }
done
: "${RELEASE_TRAILER:?set RELEASE_TRAILER (Agent: <you>, and the rest)}"

echo "== 1. export what was written in the six into v1: team's records, data's files, the press's assets, build and rules, site's and updates' content"
(cd "${V}__team" && python3 tools/sync_v1.py export --into "../$V")
(cd "${V}__data" && python3 tools/sync_v1.py export --into "../$V")
(cd "${V}__press" && python3 tools/sync_v1.py export --into "../$V")
for s in site updates; do (cd "${V}__$s" && [ -f tools/pages_sync.py ] && python3 tools/pages_sync.py export --into "../$V" || true); done

echo "== 2. v1 releases"
if [ -n "$(git -C "$V" status --porcelain)" ]; then
  (cd "$V" && admin/build/release.sh "$MSG")
else
  echo "v1: nothing to release"
fi
VV="$(cat "$V/VERSION")"

echo "== 3. the press imports (assets, build, rules) and releases"
(cd "${V}__press" && python3 tools/sync_v1.py import --from "../$V" && tools/release.sh "v1's sources at v$VV")

echo "== 4. data imports and releases"
(cd "${V}__data" && python3 tools/sync_v1.py import --from "../$V" && tools/release.sh "imported from v1 v$VV")

echo "== 5. team imports"
(cd "${V}__team" && python3 tools/sync_v1.py import --from "../$V")

echo "== 6. the four sites"
for s in site refs updates team; do
  python3 "${V}__press/tools/partition.py" --site "$s" --v1 "$V" --data "${V}__data" --into "${V}__$s"
done
python3 "${V}__press/tools/parity.py" --v1 "$V" --sites "${V}__site" "${V}__refs" "${V}__updates" "${V}__team"
for s in site updates; do (cd "${V}__$s" && python3 tools/pages_sync.py import --from "../$V"); done
(cd "${V}__team" && tools/release.sh "cut from v1 v$VV: $MSG")
for s in site refs updates; do
  (cd "${V}__$s" && tools/pages_release.sh "cut from v1 v$VV: $MSG")
done
echo "chain done: v1 v$VV, press v$(cat "${V}__press/VERSION"), data v$(cat "${V}__data/VERSION")"
