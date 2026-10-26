#!/usr/bin/env bash
# The chain: what carries the agents' writes to the sites. Since step B of the split (26 October 2026) nothing depends
# on v1's repository: the pages are built in a box the chain owns (tools/build.sh), from the six repositories' sources.
#
#   tools/chain.sh "<one sentence: what changed and why>"
#
# Run from a folder that holds the six clones side by side (sgit-ai__website__newsroom__2026__oct__php__press, __data,
# __team, __site, __refs, __updates; the box, __box, is made beside them from v1 as frozen), with RELEASE_TRAILER set as
# every release wants it. In order:
#   1. export: what was written in the six since their last import goes into the box (team's records, data's files, the
#      press's assets, build and rules, site's and updates' content: each repository's sync, export);
#   2. the box builds: a new edition, the build, the gate, one local commit (tools/build.sh);
#   3. the press imports what the build derives (the line's config and copy, outputs.txt) and releases (no version when nothing changed);
#   4. data imports the derived data files and releases (no version when the files are the same);
#   5. team imports the derived records (the control room, the edition's history);
#   6. the four sites are cut against the press and data versions, gated, checked for parity; site and updates import;
#      every site released.
# Every step is that repository's own tool with its own gate; the chain only orders them and stops at the first failure.
# Never --no-verify on a release, never a force-push, never main, never a push to v1.
set -euo pipefail
MSG="${1:?message required}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"; cd "$(dirname "$HERE")"
V=sgit-ai__website__newsroom__2026__oct__php
BOX="${V}__box"
for r in "${V}__press" "${V}__data" "${V}__team" "${V}__site" "${V}__refs" "${V}__updates"; do
  [ -d "$r/.git" ] || { echo "chain: $r is not cloned beside the press"; exit 2; }
done
: "${RELEASE_TRAILER:?set RELEASE_TRAILER (Agent: <you>, and the rest)}"
[ -d "$BOX/.git" ] || "${V}__press/tools/build.sh" --make

echo "== 0. take in what the agents released in the six since the last round"
for r in press data team site refs updates; do
  d="${V}__$r"
  [ -z "$(git -C "$d" status --porcelain)" ] || { echo "chain: $d has uncommitted changes; the last round did not finish, or someone edited it here"; exit 3; }
  git -C "$d" fetch -q origin "+refs/heads/dev:refs/remotes/origin/dev"
  git -C "$d" merge -q --ff-only origin/dev || { echo "chain: $d cannot take in origin/dev fast-forward; merge it by hand"; exit 3; }
done
[ -z "$(git -C "$BOX" status --porcelain)" ] || { echo "chain: the box is not clean; a round stopped between its exports and its build (git -C $BOX checkout -- . && git -C $BOX clean -fd puts it back)"; exit 3; }

echo "== 1. export what was written in the six into the box"
(cd "${V}__team" && python3 tools/sync_v1.py export --into "../$BOX")
(cd "${V}__data" && python3 tools/sync_v1.py export --into "../$BOX")
(cd "${V}__press" && python3 tools/sync_v1.py export --into "../$BOX")
for s in site updates; do (cd "${V}__$s" && [ -f tools/pages_sync.py ] && python3 tools/pages_sync.py export --into "../$BOX" || true); done

echo "== 2. the box builds"
"${V}__press/tools/build.sh" "$MSG"
VV="$(cat "$BOX/VERSION")"

echo "== 3. the press imports what the build derives, and releases"
(cd "${V}__press" && python3 tools/sync_v1.py import --from "../$BOX" && tools/release.sh "the sources at edition v$VV")

echo "== 4. data imports and releases"
(cd "${V}__data" && python3 tools/sync_v1.py import --from "../$BOX" && tools/release.sh "edition v$VV")

echo "== 5. team imports"
(cd "${V}__team" && python3 tools/sync_v1.py import --from "../$BOX")

echo "== 6. the four sites"
for s in site refs updates team; do
  python3 "${V}__press/tools/partition.py" --site "$s" --v1 "$BOX" --data "${V}__data" --into "${V}__$s"
done
python3 "${V}__press/tools/parity.py" --v1 "$BOX" --sites "${V}__site" "${V}__refs" "${V}__updates" "${V}__team"
for s in site updates; do (cd "${V}__$s" && python3 tools/pages_sync.py import --from "../$BOX"); done
(cd "${V}__team" && tools/release.sh "edition v$VV: $MSG")
for s in site refs updates; do
  (cd "${V}__$s" && tools/pages_release.sh "edition v$VV: $MSG")
done
echo "chain done: edition v$VV, press v$(cat "${V}__press/VERSION"), data v$(cat "${V}__data/VERSION")"
