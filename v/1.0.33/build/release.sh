#!/usr/bin/env bash
# Take in origin, bump, build, validate, tripwire, push, verify live. In that order, every time.
# Usage: admin/build/release.sh "<one sentence: what changed and why>" [patch|minor|major]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
MSG="${1:?release message required}"; PART="${2:-patch}"
BRANCH="${RELEASE_BRANCH:-dev}"
# Several agents release to the same branch. Before the bump, take in whatever landed there, so the release is
# one commit on top of origin/$BRANCH; and if the push loses a race, undo the bump, take in the newcomer and
# release again on top of it. Conflicts in files the build writes (listed in admin/build/outputs.txt) and in
# VERSION and data/versions.json resolve to origin's side, because the next steps rebuild and re-bump them.
# A conflict in any source file stops the release with the working changes intact: merge that by hand.
OUTPUTS=admin/build/outputs.txt
integrate() {
  git fetch -q origin "$BRANCH"
  if git merge-base --is-ancestor "origin/$BRANCH" HEAD; then return 0; fi
  local base bad="" f
  base="$(git rev-parse HEAD)"
  git add -A
  git commit -q --no-verify --allow-empty -m "release: local work, folded into the release commit"
  if ! git merge -q --no-verify --no-edit "origin/$BRANCH" >/dev/null 2>&1; then
    local gen
    gen="$( { cat "$OUTPUTS" 2>/dev/null || true; git show "origin/$BRANCH:$OUTPUTS" 2>/dev/null || true; printf 'VERSION\ndata/versions.json\n'; } | sort -u)"
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      if grep -qxF -- "$f" <<< "$gen"; then
        if git cat-file -e "origin/$BRANCH:$f" 2>/dev/null; then git checkout -q --theirs -- "$f"; git add -- "$f"; else git rm -q -- "$f"; fi
      else bad="$bad $f"; fi
    done < <(git diff --name-only --diff-filter=U)
    if [ -n "$bad" ]; then
      git merge --abort; git reset -q --mixed "$base"
      echo "release stopped: origin/$BRANCH changed source files that you changed too:$bad"
      echo "your work is uncommitted, as it was; merge origin/$BRANCH by hand (git stash; git merge origin/$BRANCH; git stash pop), then run this again"
      exit 3
    fi
    git commit -q --no-verify --no-edit
  fi
  git reset -q --soft "origin/$BRANCH"
  echo "took in origin/$BRANCH at $(git rev-parse --short "origin/$BRANCH")"
}
for attempt in 1 2 3 4 5; do
# 0. take in what other agents released since this clone last looked
integrate
OLD="$(cat VERSION)"; IFS=. read -r MA MI PA <<< "$OLD"
case "$PART" in major) MA=$((MA+1)); MI=0; PA=0;; minor) MI=$((MI+1)); PA=0;; *) PA=$((PA+1));; esac
NEW="$MA.$MI.$PA"
# 1. bump: VERSION and a release entry in data/versions.json (the entry's title is the message)
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
echo "v$OLD -> v$NEW"
# 2. build  3. validate
python3 admin/build/build.py
python3 admin/build/validate.py
# 4. tripwire on the staged diff (credential shapes, including the secret part of any locally held vault key)
git add -A
if git diff --cached | grep -E -n 'sgit_private_(vault|read)_[0-9a-f]{12,}|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}' ; then
  echo "tripwire: credential shape in the staged diff; release aborted"; exit 1
fi
python3 admin/build/security_check.py --staged || { echo "tripwire: security check failed on the staged diff; release aborted"; exit 1; }
if [ -d .sg_vault/local ]; then
  for k in $(grep -rhoE '[a-z0-9]{8,}:[a-z0-9]{8}' .sg_vault/local 2>/dev/null | cut -d: -f1 | sort -u); do
    if git diff --cached | grep -q "$k"; then echo "tripwire: a locally held key's secret part is in the diff"; exit 1; fi
  done
fi
# 5. commit and push; a rejected push means another release landed first: undo the bump, take that in, go again
if [ -n "${RELEASE_TRAILER:-}" ]; then git commit -q -m "v$NEW: $MSG" -m "$RELEASE_TRAILER"; else git commit -q -m "v$NEW: $MSG"; fi
if git push -q -u origin "HEAD:$BRANCH"; then echo "pushed v$NEW to $BRANCH"; break; fi
if [ "$attempt" = 5 ]; then echo "push rejected five times; the release commit is local and nothing was pushed"; exit 4; fi
echo "push rejected: $BRANCH moved while v$NEW was building; taking that in and releasing again on top"
git reset -q --soft HEAD~1
git checkout -q HEAD -- VERSION data/versions.json
sleep $((attempt * 3))
done
# 6. verify live: poll the site for the version in the top bar
URL="https://$(cat CNAME)/index.html"
# Live means this version OR LATER: several agents release to dev, and another may ship on top of
# this one inside the polling window. sort -V orders versions; the live one must not sort below ours.
for i in $(seq 1 40); do
  LIVE=$(curl -fsS --max-time 20 "$URL?r=$i" 2>/dev/null | grep -o 'class="ver"[^>]*>v[0-9][0-9.]*<' | head -1 | grep -o '>v[0-9][0-9.]*<' | tr -d '>v<')
  if [ -n "$LIVE" ] && [ "$(printf '%s\n%s\n' "$NEW" "$LIVE" | sort -V | head -1)" = "$NEW" ]; then
    if [ "$LIVE" = "$NEW" ]; then echo "live: $URL serves v$NEW"; else echo "live: $URL serves v$LIVE, which includes v$NEW (another release landed on top)"; fi
    exit 0
  fi
  sleep 15
done
echo "NOT VERIFIED: $URL does not serve v$NEW after 10 minutes. The push succeeded; the release is not done."; exit 2
