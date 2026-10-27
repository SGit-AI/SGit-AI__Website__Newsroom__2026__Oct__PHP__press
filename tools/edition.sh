#!/usr/bin/env bash
# An edition, built in CI (board dev-0005, the editor, 27 October 2026): what dev's chain (tools/chain.sh) did by hand in
# dev's session, done by the press's workflow (.github/workflows/edition.yml), so that any owner's release reaches the
# pages without anyone running a round.
#
#   tools/edition.sh <out>            run from the folder that holds the press's checkout (named as the chain names it)
#
# Reads only public repositories, and writes nothing to any of them: every repository's change from the edition is a
# patch in <out>, and each repository's own deploy (its .github/workflows/pages.yml) takes the newest edition's patch on
# its schedule, gated by its own gate, as a commit of its own CI. In order:
#   0. the inputs: data, team, site, refs and updates cloned at dev; the press is this checkout. Each one's key is its
#      newest commit not written by CI (an edition taken, a version numbered), so taking an edition never starts another.
#      Nothing new since the last edition: nothing is built (unless EDITION_FORCE=1).
#   1. the box: the last edition's box (box.tar.gz, from the press's newest edition release), with one commit, the
#      edition before, for release_pages.py to compare against. No edition yet, or none readable: a box made afresh from
#      v1 as frozen (without its history), every repository's sources exported in full, and the state the build carries
#      from edition to edition (the ledger, the items, the histories) seeded from where the chain kept it, data and team.
#   2. the chain's steps 1 to 6, the same tools: export, build (tools/build.sh), the imports, the four partitions,
#      parity; and every repository's gate on its result.
#   3. <out>: one patch per repository that changed (<name>.patch, against the head named in edition.json), the box
#      (box.tar.gz) and edition.json (the edition, its message, every input's head and key).
set -euo pipefail
OUT="$(mkdir -p "${1:?usage: tools/edition.sh <out>}" && cd "$1" && pwd)"
HERE="$(cd "$(dirname "$0")/.." && pwd)"; W="$(dirname "$HERE")"; cd "$W"
V=sgit-ai__website__newsroom__2026__oct__php
ORG=https://github.com/SGit-AI/SGit-AI__Website__Newsroom__2026__Oct__PHP
PRESS_REPO="${EDITION_PRESS_REPO:-SGit-AI/SGit-AI__Website__Newsroom__2026__Oct__PHP__press}"
BOX="${V}__box"
export GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-the edition}" GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-edition@php.newsroom}"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
export RELEASE_TRAILER="${RELEASE_TRAILER:-Agent: the edition, built by the press CI}"
[ "$(basename "$HERE")" = "${V}__press" ] || { echo "edition: the press must be checked out as ${V}__press"; exit 2; }

echo "== 0. the inputs"
for r in data team site refs updates; do
  [ -d "${V}__$r/.git" ] || git clone -q --depth 80 --branch dev "${ORG}__$r.git" "${V}__$r"
done
python3 - "$OUT/inputs.json" "$W" "$V" <<'PY'
import json, subprocess, sys
out, w, v = sys.argv[1:]
def git(d, *a): return subprocess.run(['git', '-C', f'{w}/{v}__{d}', *a], capture_output=True, text=True, check=True).stdout.strip()
res = {}
for r in ('press', 'data', 'team', 'site', 'refs', 'updates'):
    k = next((l.split('\t')[0] for l in git(r, 'log', '--format=%H\t%an\t%s').splitlines() if l.split('\t')[1] != 'GitHub Actions'), git(r, 'rev-parse', 'HEAD'))
    res[r] = {'head': git(r, 'rev-parse', 'HEAD'), 'key': k, 'subject': git(r, 'log', '-1', '--format=%s', k)}
json.dump(res, open(out, 'w'), indent=1)
PY
PREV="$OUT/.previous"; mkdir -p "$PREV"
if [ -n "${EDITION_PREVIOUS:-}" ]; then   # a test: the edition before, from a folder
  cp "$EDITION_PREVIOUS/edition.json" "$EDITION_PREVIOUS/box.tar.gz" "$PREV/"
elif [ "${EDITION_FRESH:-0}" != 1 ] && command -v gh >/dev/null && gh release download --repo "$PRESS_REPO" --pattern edition.json --pattern box.tar.gz --dir "$PREV" --clobber 2>/dev/null; then
  echo "the edition before: $(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['edition'])" "$PREV/edition.json")"
else
  rm -f "$PREV"/*; echo "no edition before (or EDITION_FRESH=1): the box is made afresh"
fi
python3 - "$OUT/inputs.json" "$PREV/edition.json" "$OUT/.message" <<'PY'
import json, os, sys
now = json.load(open(sys.argv[1]))
was = json.load(open(sys.argv[2]))['inputs'] if os.path.exists(sys.argv[2]) else {}
moved = [f'{r}: {now[r]["subject"]}' for r in now if was.get(r, {}).get('key') != now[r]['key']]
open(sys.argv[3], 'w').write('; '.join(moved) if was else 'the first edition built in CI')
PY
MSG="$(cat "$OUT/.message")"; rm -f "$OUT/.message"
if [ -f "$PREV/edition.json" ] && [ "$MSG" = "" ] && [ "${EDITION_FORCE:-0}" != 1 ]; then
  echo "edition: nothing released by anyone since the last edition; nothing to build"; : > "$OUT/nothing"; exit 0
fi
echo "what moved: $MSG"

echo "== 1. the box"
rm -rf "$BOX"
FRESH=1
if [ -f "$PREV/box.tar.gz" ]; then
  mkdir "$BOX" && tar --no-same-owner -xzf "$PREV/box.tar.gz" -C "$BOX"
  git -C "$BOX" init -q -b main && git -C "$BOX" add -A
  git -C "$BOX" commit -q --no-verify -m "v$(cat "$BOX/VERSION"): the edition before (the box as the last edition left it)"
  FRESH=0
else
  # v1 as frozen, without its history: with no release commit before it, release_pages.py and grc_history.py compute
  # nothing for this one edition and their stored entries stand (with v1's history they would compare it with v0.22.22)
  git clone -q --depth 1 "${ORG}.git" "$BOX" && rm -rf "$BOX/.git"
  git -C "$BOX" init -q -b main
  python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['current'])" "${V}__team/records/history/v1-versions.json" > "$BOX/VERSION"
  git -C "$BOX" add -A && git -C "$BOX" commit -q --no-verify -m "the box, made afresh from v1 as frozen (no release before it)"
fi
# a box made afresh: every repository's sources count as written since their last import (each sync's record is read
# with no sum matching), so the export carries all of them; the records themselves are put back after
records=( "press sources.json" "data tools/imported.json" "team records/imported.json" "site sources.json" "updates sources.json" )
if [ "$FRESH" = 1 ]; then
  for rf in "${records[@]}"; do set -- $rf; f="${V}__$1/$2"; [ -f "$f" ] && python3 -c "
import json, sys
p = sys.argv[1]; d = json.load(open(p)); f = d.get('files') or {}
d['files'] = {k: 'everything' for k in f} or {'(made afresh)': 'everything'}
json.dump(d, open(p, 'w'))" "$f"; done
fi

echo "== 2. export"
(cd "${V}__team" && python3 tools/sync_v1.py export --into "../$BOX")
(cd "${V}__data" && python3 tools/sync_v1.py export --into "../$BOX")
(cd "${V}__press" && python3 tools/sync_v1.py export --into "../$BOX")
for s in site updates; do (cd "${V}__$s" && [ -f tools/pages_sync.py ] && python3 tools/pages_sync.py export --into "../$BOX" || true); done
if [ "$FRESH" = 1 ]; then
  for rf in "${records[@]}"; do set -- $rf; [ -f "${V}__$1/$2" ] && git -C "${V}__$1" checkout -q -- "$2"; done
  # the state the build carries: what the chain imported into data and team, back where the build reads it
  python3 - "$W" "$V" <<'PY'
import os, shutil, sys
w, v = sys.argv[1:]
box, data, team = f'{w}/{v}__box', f'{w}/{v}__data/files', f'{w}/{v}__team/records'
built = [l.strip() for l in open(f'{box}/admin/build/outputs.txt') if l.strip().startswith('data/')]
n = 0
for p in built:
    src = os.path.join(data, p[len('data/'):])
    if os.path.isfile(src):
        os.makedirs(os.path.dirname(f'{box}/{p}'), exist_ok=True); shutil.copyfile(src, f'{box}/{p}'); n += 1
for here, there in (('history/v1-versions.json', 'data/versions.json'), ('history/v1-release-pages.json', 'data/release-pages.json'), ('data/control.json', 'data/control.json')):
    if os.path.isfile(f'{team}/{here}'):
        shutil.copyfile(f'{team}/{here}', f'{box}/{there}'); n += 1
print(f'seeded {n} file(s) of the build\'s state from data and team')
PY
fi

echo "== 3. build"
"${V}__press/tools/build.sh" "$MSG"
VV="$(cat "$BOX/VERSION")"

echo "== 4. the imports, the partitions, the gates"
(cd "${V}__press" && python3 tools/sync_v1.py import --from "../$BOX")
(cd "${V}__data" && python3 tools/sync_v1.py import --from "../$BOX" && python3 tools/gate.py)
(cd "${V}__team" && python3 tools/sync_v1.py import --from "../$BOX")
for s in site refs updates team; do
  python3 "${V}__press/tools/partition.py" --site "$s" --v1 "$BOX" --data "${V}__data" --into "${V}__$s"
done
python3 "${V}__press/tools/parity.py" --v1 "$BOX" --sites "${V}__site" "${V}__refs" "${V}__updates" "${V}__team"
for s in site updates; do (cd "${V}__$s" && python3 tools/pages_sync.py import --from "../$BOX"); done
(cd "${V}__team" && python3 tools/front.py >/dev/null && python3 tools/gate.py && python3 tools/pages_gate.py)
for s in site refs updates; do (cd "${V}__$s" && python3 tools/pages_gate.py); done
(cd "${V}__press" && python3 tools/gate.py)

echo "== 5. the edition"
for r in press data team site refs updates; do
  d="${V}__$r"; git -C "$d" add -A
  if ! git -C "$d" diff --cached --quiet; then git -C "$d" diff --cached --binary > "$OUT/$r.patch"; fi
  git -C "$d" reset -q
done
tar -czf "$OUT/box.tar.gz" -C "$BOX" --exclude=.git .
python3 - "$OUT" "$VV" "$MSG" <<'PY'
import datetime, json, os, sys
out, vv, msg = sys.argv[1:]
inputs = json.load(open(f'{out}/inputs.json'))
json.dump({'edition': vv, 'message': msg, 'built_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
           'run': os.environ.get('GITHUB_RUN_ID', ''), 'inputs': inputs,
           'patches': {r: inputs[r]['head'] for r in inputs if os.path.exists(f'{out}/{r}.patch')}},
          open(f'{out}/edition.json', 'w'), indent=1)
PY
rm -rf "$PREV" "$OUT/inputs.json"
ls -la "$OUT"
echo "edition v$VV built: $MSG"
