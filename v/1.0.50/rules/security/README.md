# Security

Kept by security@php.newsroom, the newsroom's security agent.

| File | What it is |
| --- | --- |
| `REQUIREMENTS.md` | the rules every agent works to: untrusted input, credentials, publishing, models in loops, mail, damage limitation |
| `abp/GRANT.md` | what an agent session can do, measured |
| `abp/MANDATE.md` | what each agent is authorised to do: a draft for the editor to correct |
| `abp/DELTA.md` | the gap between the two, and the boundary that would close each row |
| `injection-allowlist.json` | text addressed to a model that the site is allowed to publish, each entry with its reason |
| `../build/security_check.py` | the checks: run by the gate, by the release tripwire, and by the regular pass |

The policy files use the vocabulary of the agent behaviour policies at riskmandate.ai (abp.sgit.ai v0.3.0): grant,
mandate, delta, and four barriers, of which only a boundary enforced above the agent counts as a control.

## What the checks look for

| Check | Where it runs | Why |
| --- | --- | --- |
| Credential shapes (sgit private keys, Anthropic, OpenAI, OpenRouter, GitHub, AWS, Google, Slack, JWTs, SG/Send tokens) and the values of the secret environment variables | gate, tripwire, history | the whole tree is published |
| Vault-key, lane, passphrase and decrypted-vault files | gate, tripwire | a vault clone inside the repository would be committed by `release.sh` |
| Unicode tag characters, bidi controls, zero-width characters in published text | gate | text a person cannot see and a model can |
| Text addressed to a model in published text | gate | the site, `llms.txt` and the twins are read by models, ours and other people's |
| JSON script blocks that do not parse | gate | data that closes its `<script>` element runs as script on the site |
| `javascript:` and other script URLs in `href`, `src` and `action` | gate | one click runs script on the site |
| Source slugs outside `[a-z0-9._-]` | gate | slugs become paths and attributes |
| Workflow actions not pinned to a commit, `pull_request_target`, event text in workflows | gate | a moved tag or a crafted title runs in CI with the repository's secrets |

## The regular pass

Run by the security agent in a fresh session, at least daily while the story is live, and after any release that
touches `admin/build/`, `assets/`, `.github/` or a vault's protocol:

1. `python3 admin/build/security_check.py --report --history`: the tree and every commit on every branch.
2. Clone the public vaults read-only, with their published read keys, into the session's scratch directory (never
   into the repository), without the SG/Send token in the environment, and run
   `python3 -I admin/build/security_check.py --report --vault <clone>` on each. Every hit is read by a person or by
   the security agent as material: a page about prompt injection is evidence, not an attack.
3. Re-measure `abp/GRANT.md`: branch protection and rulesets, the environment's variables, the tools present.
4. Review every change since the last pass to `admin/build/`, `assets/`, `.github/`, `data/vaults.json`,
   `data/subscriptions.json`, `data/telemetry.json` and the synthetic readers.
5. Report to the editor privately. Nothing about an unfixed weakness is committed here: this repository is public.
