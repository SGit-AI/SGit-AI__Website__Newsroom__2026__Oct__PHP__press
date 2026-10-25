#!/usr/bin/env bash
# Release the press: take in dev, gate, bump, publish, gate again, commit, push.
# Usage: tools/release.sh "<one sentence: what changed and why>" [patch|minor|major]
# A change to the partition, the site gate or the site release reaches the sites only when each partitions again with
# the new version. Never --no-verify, never a force-push, never main. Security reviews every press release (CLAUDE.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
MSG="${1:?release message required}"; PART="${2:-patch}"; BRANCH="${RELEASE_BRANCH:-dev}"
git fetch -q origin "$BRANCH" 2>/dev/null || true
if git rev-parse -q --verify "origin/$BRANCH" >/dev/null && ! git merge-base --is-ancestor "origin/$BRANCH" HEAD; then
  git merge -q --ff-only "origin/$BRANCH" || { echo "release stopped: merge origin/$BRANCH by hand"; exit 3; }
fi
python3 tools/gate.py
OLD="$(cat VERSION)"; IFS=. read -r MA MI PA <<< "$OLD"
if [ -d "v/$OLD" ]; then case "$PART" in major) MA=$((MA+1)); MI=0; PA=0;; minor) MI=$((MI+1)); PA=0;; *) PA=$((PA+1));; esac; fi
NEW="$MA.$MI.$PA"; echo "$NEW" > VERSION
python3 tools/publish.py
python3 tools/gate.py
git add -A
if git diff --cached --quiet; then echo "nothing to release"; exit 0; fi
if [ -n "${RELEASE_TRAILER:-}" ]; then git commit -q -m "v$NEW: $MSG" -m "$RELEASE_TRAILER"; else git commit -q -m "v$NEW: $MSG"; fi
git push -q -u origin "HEAD:$BRANCH"
echo "pushed v$NEW to $BRANCH"
