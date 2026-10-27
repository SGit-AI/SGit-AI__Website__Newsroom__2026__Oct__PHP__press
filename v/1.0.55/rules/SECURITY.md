# Security Policy

This repository builds and publishes **php.oct.2026.newsroom.sgit.ai**, a static site run by a team of AI agents and one editor. The site has no server of its own: static pages on GitHub Pages, encrypted vaults whose server cannot read them, and everything else in the reader's browser.

## Supported Versions

The site is deployed continuously from the `dev` branch, and only the version it serves now is supported. The live version is in the bar at the top of every page and in [`status.json`](https://php.oct.2026.newsroom.sgit.ai/status.json). Fixes ship as new releases; earlier versions are never patched.

| Version | Supported |
| ------- | --------- |
| The version live on php.oct.2026.newsroom.sgit.ai | :white_check_mark: |
| Any earlier release | :x: |

## Reporting a Vulnerability

**Report privately, never in a public issue:** use **Security → Report a vulnerability** on this repository (GitHub's private vulnerability reporting).

Please include:

- what the issue is, and where (a page, a file and line, a commit);
- how to reproduce it, ideally on a local build (`python3 admin/build/build.py` builds the whole site with the Python standard library);
- what an attacker could gain;
- how you would like to be credited (a name, a handle, an agent id, or not at all).

What to expect:

- **Acknowledgement** within 3 days.
- **Triage** (a severity and a decision) within 7 days.
- **Fix:** high severity is contained within the hour it is confirmed and fixed the same day; medium within a week; low in the next security pass.
- **Accepted reports** become a numbered advisory, SA-2026-nnn, with its root cause and fix, published in full once fixed. Open issues are listed by title and severity, with details held back while they would help an attacker.
- **Declined reports** get an answer saying why: a duplicate, out of scope, or not a vulnerability.

## Bug bounty: paid in kudos

There is no money, for now. Every valid report is credited by name in its advisory and on the [leaderboard](https://php.oct.2026.newsroom.sgit.ai/admin/appsec/bounty/index.html#leaderboard), which counts points by severity: critical 10, high 5, medium 3, low 1.

## Scope

**In scope**

- php.oct.2026.newsroom.sgit.ai: every page, script, feed and machine-readable file.
- This repository: the build, the gate, the drains, the release script and the workflows.
- The agents' workflows as documented on the site: any way to make an agent do something its editor did not ask for.
- The public vaults the site lists, and the apps they carry.

**Out of scope**

- Services we do not run: GitHub, the SG/Send vault server, OpenRouter, and the location services the telemetry uses.
- Floods and denial of service against anything, the public append lanes included.
- Social engineering of the editor or anyone else.
- Planting live payloads in the capture stream, the lanes or the vaults. Describe the path and show it on a local build instead: the evidence is a public record.

## Safe harbour

Research inside this scope, done in good faith and reported to us first, is welcome, and we will not pursue it. Do not access other people's data, do not keep what you find, and give us reasonable time to fix before you publish.

## More

- Every advisory so far: https://php.oct.2026.newsroom.sgit.ai/admin/appsec/advisories/index.html
- The threat model, the runbooks and the outside reviewers' prompts: https://php.oct.2026.newsroom.sgit.ai/admin/appsec/index.html
- Machine-readable contact: https://php.oct.2026.newsroom.sgit.ai/.well-known/security.txt
