#!/usr/bin/env bash
# A site's release, installed by the press: take in dev, gate, commit, push. In that order, every time.
# Usage: tools/pages_release.sh "<one sentence: what changed and why>"
# The pages come from the press's partition of v1 (press.json says which commit); never edit them here.
# Never --no-verify, never a force-push, never main.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
MSG="${1:?release message required}"
BRANCH="${RELEASE_BRANCH:-dev}"
git fetch -q origin "$BRANCH" 2>/dev/null || true
if git rev-parse -q --verify "origin/$BRANCH" >/dev/null && ! git merge-base --is-ancestor "origin/$BRANCH" HEAD; then
  if ! git merge -q --ff-only "origin/$BRANCH" 2>/dev/null; then
    echo "release stopped: origin/$BRANCH has commits this clone does not; partition again on top of it"; exit 3
  fi
fi
python3 tools/pages_gate.py
if [ -f tools/gate.py ]; then python3 tools/gate.py; fi   # a repository with records of its own (team) checks them too
git add -A
if git diff --cached | grep -E -n 'sgit_private_(vault|read)_[0-9a-f]{12,}|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|\bsk-(or-v1-|proj-|ant-[a-z0-9]+-)?[A-Za-z0-9_]{32,}' ; then
  echo "tripwire: credential shape in the staged diff; release aborted"; exit 1
fi
if git diff --cached --quiet; then echo "nothing to release"; exit 0; fi
if [ -n "${RELEASE_TRAILER:-}" ]; then git commit -q -m "$MSG" -m "$RELEASE_TRAILER"; else git commit -q -m "$MSG"; fi
git push -q -u origin "HEAD:$BRANCH"
echo "pushed to $BRANCH"
