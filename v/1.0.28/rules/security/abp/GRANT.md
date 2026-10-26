# GRANT: everything a newsroom agent session can do

> Measured from the deployment, not from what anyone asked for. Vocabulary: abp.sgit.ai v0.3.0, as used by
> riskmandate.ai. Irreversible rows first. Kept by security@php.newsroom; re-measured on every security pass.

**Deployment** an agent of this newsroom in Claude Code on the web: an ephemeral cloud container, this repository
attached, an egress proxy above it, the platform's harness tools, and the environment's variables.
**Shape** `anthropic/claude-code-remote/ccr-container`, the same shape as the riskmandate.ai template vault
`claude-code-web`, widened by what this newsroom adds. **As at** 2026-10-22, measured in the session that wrote it.

| Reach | Here means |
| --- | --- |
| host | the session's container: disposable, the vendor's |
| project | this repository's working tree |
| tenant | this repository on GitHub, the SG/Send vault server, the platform's session tools |
| world | the live site, readers' browsers and other people's models (through `llms.txt` and the twins) |

## The rows

| Capability | What it is here | Barrier | Undo | Evidence |
| --- | --- | --- | --- | --- |
| `create.record.world` | Publish under the newsroom's name: a push to `dev` deploys the site within minutes; `llms.txt` and the twins are read by other people's models | ◐ setting: the gate and `release.sh`, which live in the repository the agent can edit | no: caches, search engines and readers' models keep what was published | observed: `pages.yml` deploys every push to `dev` |
| `write.repository.tenant` | Push to any branch, `dev` and `main` included | ● none: neither branch is protected; no ruleset | with-effort | observed: GitHub API, `protected: false` on both, 2026-10-22 |
| `authenticate-as.credential.tenant` | Act with the session's tokens: the GitHub app token (this repository only), the SG/Send access token (create vaults, write to vaults it holds keys for), cloud tokens through the proxy | ○ boundary for GitHub (scoped by the platform); open question for SG/Send (what one token can reach) | no | observed: variables present; GitHub scope self-reported by the platform |
| `read.credential.host` | Read the tokens in its own environment and any key in a clone it made | ● none | no | observed |
| `read.record.history` | Read the session's own earlier tool output and transcripts | ● none | no | observed |
| `send.endpoint.allowed` | Reach the hosts the proxy allows: the open web for capture, PyPI, GitHub, the vault server | ○ boundary: the egress proxy, set above the container | no | observed: fetched riskmandate.ai, github.com, pypi.org, dev.send.sgraph.ai |
| `write.budget.tenant` | Spend: model tokens in the session, vault storage, and (in CI) the Anthropic key of the synthetic readers | ○ boundary for the session (the platform's limits); ◐ setting for CI (the secret's own limits) | no | derived |
| `delete.file.host` | Delete anything in the container, the clone included | ● none | no (the container is disposable; the remote is not touched) | observed |
| `execute.process.host` | Run programs as root in the container | ● none | with-effort | observed |
| `write.file.host` | Change any file in the container | ● none | with-effort | observed |
| `write.file.project` | Change the working tree | ● none | with-effort | observed |
| `write.repository.project` | Commit | ● none | with-effort | observed |
| `read.file.host` | Read any file in the container | ● none | yes | observed |
| `read.file.project` | Read the working tree | ● none | yes | observed |
| `create.schedule.tenant` | Create what outlives the session: scheduled tasks, new sessions, messages to other sessions, workflows (by committing one) | ◐ setting: the platform's tools are the operator's to list and delete; a committed workflow is bounded only by the repository's secrets | yes | observed: the tools are present in the session |
| `create.schedule.host` | A cron in the container | ○ boundary: dies with the container | yes | derived from the template |

## Not reachable from this shape

| What | Why |
| --- | --- |
| Other repositories | the platform scopes the GitHub token to this repository per session |
| The private vaults' contents (telemetry, subscriptions, coverage, the six synthetic readers) | their keys are not in the repository or the environment; a session holds one only if the editor hands it over |
| Sending mail | only agent@diniscruz.ai sends, in its own deployment |
| The editor's machine and accounts | the container has no path to them |

## The barriers, and the test

| | Barrier | Is it a control |
| --- | --- | --- |
| ● | none: nothing in the way | no |
| ◉ | expectation: a rule in prose (`admin/security/REQUIREMENTS.md`, the briefs) | no |
| ◐ | setting: something the agent's own access can change (the gate, `release.sh`, `.gitignore`, hooks) | no |
| ○ | boundary: enforced above the agent (the proxy, the token's scope, a branch ruleset, an environment rule) | **yes** |

> A control bounds a grant only if it is enforced by something the grant does not include.

The gate is the newsroom's main defence and it is a setting: an agent that can push can also edit
`validate.py`. It stops mistakes, not a steered agent. Only a boundary at GitHub stops that (see `DELTA.md`).
