#!/usr/bin/env bash
# The build, out of v1 (step B of the split): the pages are built in a box the chain owns, from the six repositories'
# sources, and v1's repository takes nothing.
#
#   tools/build.sh "<one sentence: what changed and why>"      tools/build.sh --make   (the box alone, no build)
#
# The box is a plain clone of v1 as it was frozen (v0.22.22, 26 October 2026), kept beside the seven clones as
# sgit-ai__website__newsroom__2026__oct__php__box, with no remote: nothing in it is ever pushed. Before each build the
# chain exports every repository's sources into it (tools/sync_v1.py export in team, data and the press; pages_sync.py
# in site and updates); this script then does what v1's release did around the build, without the release: a new
# edition number (VERSION, and its entry in data/versions.json), the build (build/build.py as admin/build/build.py), the
# gate (validate.py), one local commit so the partition reads a clean tree. The edition's history (data/versions.json,
# data/release-pages.json) is an output: team's import keeps it under records/history/, and a box made afresh (a new
# session) starts from it, so the series continues. What a fresh box loses is the pages each edition changed, for the
# editions built in a session that is gone; the stored entries stand.
set -euo pipefail
MSG="${1:?message required, or --make}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"; cd "$(dirname "$HERE")"
V=sgit-ai__website__newsroom__2026__oct__php
BOX="${V}__box"
FROZEN="https://github.com/SGit-AI/SGit-AI__Website__Newsroom__2026__Oct__PHP.git"

if [ ! -d "$BOX/.git" ]; then
  echo "box: making it from v1 as frozen"
  if [ -d "$V/.git" ]; then git clone -q "$V" "$BOX"; else git clone -q "$FROZEN" "$BOX"; fi
  git -C "$BOX" remote remove origin                       # nothing leaves the box
  # the edition series continues from the team's records (the last v1 release, or the last build)
  H="${V}__team/records/history"
  if [ -f "$H/v1-versions.json" ]; then
    cp "$H/v1-versions.json" "$BOX/data/versions.json"
    [ -f "$H/v1-release-pages.json" ] && cp "$H/v1-release-pages.json" "$BOX/data/release-pages.json"
    python3 -c "import json,sys; open(sys.argv[2],'w').write(json.load(open(sys.argv[1]))['current']+'\n')" "$H/v1-versions.json" "$BOX/VERSION"
    git -C "$BOX" add -A && git -C "$BOX" commit -q --no-verify -m "box: the edition series from the team's records" || true
  fi
fi
[ "$MSG" = "--make" ] && { echo "box: $BOX, edition v$(cat "$BOX/VERSION")"; exit 0; }
cd "$BOX"
[ -z "$(git status --porcelain)" ] || { echo "box: the tree is not clean before the build; the exports should have been committed by the last build"; git status --porcelain | head -5; exit 3; }
OLD="$(cat VERSION)"; IFS=. read -r MA MI PA <<< "$OLD"; NEW="$MA.$MI.$((PA+1))"
# the edition: VERSION and its entry in data/versions.json (as v1's release wrote them)
python3 - "$NEW" "$MSG" <<'PY'
import json, sys, datetime
new, msg = sys.argv[1], sys.argv[2]
p = 'data/versions.json'; j = json.load(open(p))
vault = json.load(open('data/vault.json'))
j['current'] = new
j['versions'].insert(0, {'version': new, 'date': datetime.date.today().isoformat(), 'title': msg, 'summary': '', 'changes': [], 'vault_commit': vault['head']['commit'], 'reconstructed': False})
json.dump(j, open(p, 'w'), indent=1, ensure_ascii=False); open(p, 'a').write('\n')
open('VERSION', 'w').write(new + '\n')
PY
echo "box: v$OLD -> v$NEW"
python3 admin/build/build.py
python3 admin/build/validate.py
git add -A
if git diff --cached | grep -E -n 'sgit_private_(vault|read)_[0-9a-f]{12,}|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|\bsk-(or-v1-|proj-|ant-[a-z0-9]+-)?[A-Za-z0-9_]{32,}' | head -3; then
  echo "box: a credential shape in the build; stopped"; git reset -q; exit 1
fi
git commit -q --no-verify -m "v$NEW: $MSG" -m "${RELEASE_TRAILER:-Agent: the chain}"
echo "box: built v$NEW at $(git rev-parse --short HEAD) (local; nothing pushed)"
