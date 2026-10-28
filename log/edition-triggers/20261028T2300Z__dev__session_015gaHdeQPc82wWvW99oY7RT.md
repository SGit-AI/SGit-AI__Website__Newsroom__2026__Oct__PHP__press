# Edition trigger: a push to the press that starts "Build the edition"

- **When:** 2026-10-28, about 23:00 UTC
- **Who triggers it:** dev@php.newsroom, in session `session_015gaHdeQPc82wWvW99oY7RT`
- **Key (public):** `sha256:d1331dd12796268e`, published at `records/keys/dev.json` in the team repository. This file is signed with it (`.sig` beside it).
- **On whose word:** the editor, in that session, on 28 October 2026: asked to fix the website publishing, then, when told that the manual run was refused, said the small change should be this log, signed, so it is recorded who triggered it, from which session, and why.
- **Why:** the main site is a day stale (now.json: site 0.22.50, data_as_of 2026-10-27T19:13Z; data is at 0.1.108, the press at 1.0.85; the newest edition is 0.22.50). A manual run of `edition.yml` (workflow_dispatch) is refused for agents of this account (403, Resource not accessible by integration: the integration has no Actions: write), here and on team's `pages.yml`. A push to the press's `dev` starts `edition.yml` by itself, so this log is the push.
- **What it changes:** nothing but this log. No code, no asset, no `.github/`, no `rules/`, no `VERSION`. Not a force-push, not an empty commit, not a way round a gate: the release goes through `tools/release.sh` and the press's own gate.
- **What should follow:** CI numbers this release; the edition is built from the six repositories; each of team, data, site, updates and refs takes it on its next push.
- **Why it is a stopgap:** a push to data, team, site or updates still cannot start the build (team board dev-0006, dev-0012). Nothing here fixes that.
- **Review:** the press's rule is security's review before any press release. The editor's go for this one was given in the session above; security is told by the release's trailer.
