# MANDATE: what each newsroom agent is authorised to do

> A starting point drafted by security@php.newsroom from the briefs and the roles page, for the editor to correct.
> Not measured and not agreed until the editor says so. The only part of this policy only he can supply.

**Status** draft, 2026-10-22. **Authority** the editor, Dinis Cruz.

## In one paragraph

The newsroom's agents read the open web and the vaults, write this repository, and release the site to `dev` through
`release.sh` when they have something to ship: that is the editor's standing direction ("please push to dev as you
have updates"). They publish only through the gate. They do not change the gate, the workflows or the security
files on their own, do not push to `main`, never rewrite history, never publish a secret, never send mail (one agent
does that, in its own deployment), and do not create anything that outlives their session without the editor's go.

## Wanted, for every agent

| Capability | Within |
| --- | --- |
| `read.file.project`, `write.file.project`, `write.repository.project` | this repository |
| `execute.process.host` | the session's container |
| `send.endpoint.allowed` | the proxy's list; the open web for capture |
| `write.repository.tenant` | `dev` (through `release.sh`) and the agent's own `claude/*` branch; never `main`, never a force-push |
| `create.record.world` | only what passes the gate, only through `release.sh` |
| `authenticate-as.credential.tenant` | the GitHub token for this repository; the SG/Send token for the vaults the agent's role writes |

## Wanted, by role

| Role | Also wanted |
| --- | --- |
| Collectors, the source watch (researcher@) | write to the evidence vault and the source watch; read keys elsewhere |
| Story site, librarian, journalist, historian, briefing writer, cartographer | read the vaults with read keys; no vault writes beyond their own notes |
| dev@ (drains) | the telemetry and subscriptions vault keys, held outside the repository |
| synthetic@ | its six vaults, in CI only; its model call has no tools |
| security@ | read keys for every vault it is given; writes only to the repository's security files, on a branch, released with the editor's go |
| agent@diniscruz.ai (another deployment) | `send.message.world`, only to confirmed addresses, only what the site published |

## Not wanted

| Capability | Note |
| --- | --- |
| `create.schedule.tenant` | not without the editor's go in the session |
| `read.record.history` | not another session's transcript; an agent's own is fine |
| `send.message.world` | no newsroom session sends mail, posts or messages outside the team |
| `write.repository.tenant` on `main`, force-push, branch deletion | never |
| Changing `validate.py`, `security_check.py`, `release.sh`, `.github/workflows/`, `admin/security/` | only on a branch, reviewed by security, released with the editor's go |

## Unstated, for the editor to decide

- What the SG/Send access token in agent sessions can reach (every vault on the server it can write to, or one?).
- Whether collectors (which read hostile pages) should hold the right to release the site at all.
- Whether `create.record.world` through Artifacts or new public vaults needs the same gate as the site.
