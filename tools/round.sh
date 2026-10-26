#!/usr/bin/env bash
# The round, run by GitHub Actions (.github/workflows/round.yml) every quarter hour and on demand: the six repositories
# cloned beside this one, the box made from v1 as frozen, the chain run with --if-changed, every release pushed with
# ROUND_TOKEN (a fine-grained token the editor keeps as the press's secret: contents read and write on the six, nothing
# else). So an agent's release is on its host within the quarter hour, with no person in the loop, as in v1.
# This script runs repository code (the chain, the build); the token reaches only git's credential helper, for the
# pushes, and the runner is gone when the round ends. Every change here goes through security's review.
set -euo pipefail
[ -n "${ROUND_TOKEN:-}" ] || { echo "the round cannot push without ROUND_TOKEN, the press repository secret the editor makes"; exit 1; }
V=sgit-ai__website__newsroom__2026__oct__php
ORG=https://github.com/SGit-AI
cd "$(cd "$(dirname "$0")/../.." && pwd)"          # the folder that holds the press clone
git config --global user.name "the round"; git config --global user.email "round@php.newsroom"
git config --global url."https://x-access-token:${ROUND_TOKEN}@github.com/".insteadOf "https://github.com/"
for r in data team site refs updates; do
  [ -d "${V}__$r/.git" ] || git clone -q --branch dev "$ORG/SGit-AI__Website__Newsroom__2026__Oct__PHP__$r.git" "${V}__$r"
done
[ -d "${V}__box/.git" ] || "${V}__press/tools/build.sh" --make
export RELEASE_TRAILER="Agent: the round (press/.github/workflows/round.yml)
Round: ${GITHUB_RUN_ID:-local}"
"${V}__press/tools/chain.sh" "the round: what the agents released since the last one" --if-changed
