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
git fetch -q origin "$BRANCH" 2>/dev/null || true
if git rev-parse -q --verify "origin/$BRANCH" >/dev/null && ! git merge-base --is-ancestor "origin/$BRANCH" HEAD; then
  git merge -q --ff-only "origin/$BRANCH" || { echo "release stopped: merge origin/$BRANCH by hand"; exit 3; }
fi
python3 tools/gate.py
OLD="$(cat VERSION)"; IFS=. read -r MA MI PA <<< "$OLD"
if [ -d "v/$OLD" ]; then PA=$((PA+1)); fi
NEW="$MA.$MI.$PA"; echo "$NEW" > VERSION
python3 tools/publish.py
python3 tools/gate.py
git add -A
if git diff --cached --quiet; then echo "nothing to release"; exit 0; fi
if [ -n "${RELEASE_TRAILER:-}" ]; then git commit -q -m "v$NEW: $MSG" -m "$RELEASE_TRAILER"; else git commit -q -m "v$NEW: $MSG"; fi
git push -q -u origin "HEAD:$BRANCH"
echo "pushed v$NEW to $BRANCH"
