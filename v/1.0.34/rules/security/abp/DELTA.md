# DELTA: what a newsroom agent can do that nobody asked for

> Derived from `GRANT.md` and `MANDATE.md`. If this looks wrong, one of the two is. Kept by security@php.newsroom.

**Grant** 2026-10-22 · **mandate** draft 2026-10-22

## Four counts, none of them a score

| | Count | Meaning |
| --- | --- | --- |
| Grant | 16 | capabilities a session reaches |
| Wanted | 8 | in the mandate for every agent; all 8 are granted, so the shortfall is 0 |
| Excess | 8 | in the grant and not wanted |
| Wider than wanted | 2 | wanted, but the grant reaches past the mandate: `write.repository.tenant` (any branch, force-push) and `create.record.world` (past a gate the agent can edit) |
| **Unbounded excess** | **9** | the 7 excess rows with no boundary in the way, and the 2 wider-than-wanted rows: the only number anyone can move |

Five of the seven excess rows are the container's own (read, write and delete any file in it, read its tokens and
its transcripts). The container is disposable, so they matter through what is put in it: the tokens.

## Unbounded excess, and the boundary that would bound it

| Capability, beyond the mandate | Barrier today | The boundary that would move it | Who can set it |
| --- | --- | --- | --- |
| `write.repository.tenant` on `main`, force-push, deleting `dev` | ● none | a GitHub ruleset on `dev` and `main`: block force-pushes and deletion; `main` only through a pull request | the editor (admin) |
| `create.record.world` with a weakened gate (an agent edits `validate.py` or a workflow, then releases) | ◐ setting | a push ruleset restricting `admin/build/validate.py`, `admin/build/security_check.py`, `admin/build/release.sh`, `.github/workflows/**` and `admin/security/**`, with the editor as the only bypass; and the `github-pages` environment limited to deploying from `dev` | the editor (admin) |
| `create.schedule.tenant` | ◐ setting | the platform's permission settings for sessions; a workflow is bounded by the ruleset above | the editor |
| `read.credential.host` | ● none | none is possible inside the container; the bound is what is put in it: give each role's session only the tokens its mandate needs | the editor, per environment |
| `read.record.history` | ● none | as above: separate environments per role | the editor |
| `authenticate-as.credential.tenant` (SG/Send token beyond the role's vaults) | open question | a token per role, scoped to that role's vaults, if the server supports it | the SG/Send operator |

## Bounded excess (behind a boundary already)

| Capability | Boundary |
| --- | --- |
| `send.endpoint.allowed` beyond capture | the egress proxy |
| `create.schedule.host` | the container dies with the session |

## What the gate does, and does not, do

The gate (`validate.py` with `security_check.py`) and the release tripwire stop the mistakes an honest agent makes:
a credential in a file, a vault clone in the tree, data that breaks out of a page, a hidden instruction in published
text, an unpinned workflow action. They are settings, not boundaries. A steered agent that edits them gets past them;
only the rulesets above stop that, and the editor is the only one who can set them.
