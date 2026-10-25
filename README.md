# SGit-AI__Website__Newsroom__2026__Oct__PHP__press

The press of the newsroom's site on the two critical PHP flaws of October 2026 (php2shell): what typesets, proofs and
publishes its sites, served at **https://press.php.oct.2026.newsroom.sgit.ai/** with every version immutable under
`/v/<version>/`.

In pass one of the split it partitions the built site (still built in v1) into four sites, each its own repository:
`site` (the main UI), `refs` (the references), `updates` (the regular updates) and `team` (the newsroom's pages).
[`sites.json`](sites.json) says which sections each owns. `tools/partition.py` writes a site's pages, a redirect at
every address another site owns, and the runtime its pages load; it installs the site's gate (`tools/pages_gate.py`)
and release (`tools/pages_release.sh`). In pass two the build library itself moves here. The rules for working here
are in [CLAUDE.md](CLAUDE.md).
