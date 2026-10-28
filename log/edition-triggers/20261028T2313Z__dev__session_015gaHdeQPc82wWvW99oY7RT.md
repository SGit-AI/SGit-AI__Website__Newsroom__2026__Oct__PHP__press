# Edition trigger 2: a push to the press that starts "Build the edition" again

- **When:** 2026-10-28T23:13:58Z
- **Who triggers it:** dev@php.newsroom, in session `session_015gaHdeQPc82wWvW99oY7RT`
- **Key (public):** `sha256:d1331dd12796268e` (team `records/keys/dev.json`); this file is signed with it (`.sig` beside it).
- **On whose word:** the editor, in that session, on 28 October 2026: to fix the two files that failed the gate (permission to override their owners) and to start the build again with a log like the first.
- **Why:** the first build, started by press 10e6e78 (`log/edition-triggers/20261028T2300Z__dev__session_015gaHdeQPc82wWvW99oY7RT.md`), failed the gate on two files that are not the press's: security's `scan.py` line 6 (raw bidi characters) and observability's `harness.html` (built as a page). Both are fixed in team's `dev` (boards dev-0014, dev-0015, done), so the build reads them fixed. The site is still a day stale (now.json site 0.22.50, data_as_of 2026-10-27T19:13Z).
- **What it changes:** nothing but this log. No code, asset, `.github/`, `rules/` or `VERSION`. Not a force-push and not an empty commit.
- **What should follow:** the edition is built and published; each of team, data, site, updates and refs takes it on its next push.
- **Rule:** this is how any agent gets the main site updated: its own repository first, then a signed log here saying who, what and why (team board dev-0016).
