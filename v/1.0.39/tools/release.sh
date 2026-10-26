#!/usr/bin/env bash
# Release the press: take in dev, gate, bump, publish, gate again, commit, push.
# Usage: tools/release.sh "<one sentence: what changed and why>"
# The first release was 1.0.0; every release after it adds one to the last number (1.0.1, 1.0.2, ...), whatever it
# changes (the editor, 25 October 2026). Take v1's assets in first when they changed: tools/assets_v1.py --from <v1>.
# A change to the partition, the site gate or the site release reaches the sites only when each partitions again with
# the new version. Never --no-verify, never a force-push, never main. Security reviews every press release (CLAUDE.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
MSG="${1:?release message required}"; BRANCH="${RELEASE_BRANCH:-dev}"
git fetch -q origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" 2>/dev/null || true   # the tracking ref itself: a clone made for one branch does not move it on a plain fetch
if git rev-parse -q --verify "origin/$BRANCH" >/dev/null && ! git merge-base --is-ancestor "origin/$BRANCH" HEAD; then
  git merge -q --ff-only "origin/$BRANCH" || { echo "release stopped: merge origin/$BRANCH by hand"; exit 3; }
fi
python3 tools/gate.py
# Several writers release here within minutes of each other. The version is taken when the push succeeds: a rejected push
# undoes the commit and the minted version, takes in what landed, numbers again, publishes again. Five tries.
for attempt in 1 2 3 4 5; do
  OLD="$(cat VERSION)"; IFS=. read -r MA MI PA <<< "$OLD"
  if python3 tools/publish.py --same-as "$OLD"; then
    NEW="$OLD"; echo "nothing new to publish: v$OLD holds these files already"   # a change to the tools still commits
  else
    if [ -d "v/$OLD" ]; then PA=$((PA+1)); fi
    NEW="$MA.$MI.$PA"; echo "$NEW" > VERSION
    python3 tools/publish.py
    python3 tools/gate.py
  fi
  git add -A
  if git diff --cached | grep -E -n 'sgit_private_(vault|read)_[0-9a-f]{12,}|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|\bsk-(or-v1-|proj-|ant-[a-z0-9]+-)?[A-Za-z0-9_]{32,}' ; then
    echo "release stopped: a credential shape in the change"; exit 2
  fi
  if git diff --cached --quiet; then echo "nothing to release"; exit 0; fi
  if [ -n "${RELEASE_TRAILER:-}" ]; then git commit -q -m "v$NEW: $MSG" -m "$RELEASE_TRAILER"; else git commit -q -m "v$NEW: $MSG"; fi
  if git push -q -u origin "HEAD:$BRANCH" 2>/dev/null; then echo "pushed v$NEW to $BRANCH"; exit 0; fi
  echo "push rejected (someone released meanwhile): taking it in and numbering again ($attempt of 5)"
  git reset -q --soft HEAD~1; git reset -q               # the commit undone, nothing staged: the imported files stay as changes in the tree
  if [ "$NEW" != "$OLD" ]; then rm -rf "v/$NEW"; fi
  git checkout -q HEAD -- VERSION versions.json index.html latest 2>/dev/null || true
  git clean -fdq latest 2>/dev/null || true
  git fetch -q origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
  git merge -q --ff-only "origin/$BRANCH" || { echo "release stopped: your change and someone else's touch the same file; merge origin/$BRANCH by hand and run this again"; exit 3; }
done
echo "release stopped: five tries, five releases by others in between; run this again"; exit 3
