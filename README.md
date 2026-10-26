# SGit-AI__Website__Newsroom__2026__Oct__PHP__press

The press of the newsroom's site on the two critical PHP flaws of October 2026 (php2shell): what typesets, proofs and
publishes its sites, served at **https://press.php.oct.2026.newsroom.sgit.ai/** with every version immutable under
`/v/<version>/`.

In pass one of the split it partitions the built site (still built in v1) into four sites, each its own repository:
`site` (the main UI), `refs` (the references), `updates` (the regular updates) and `team` (the newsroom's pages).
[`sites.json`](sites.json) says which sections each owns. `tools/partition.py` writes a site's pages and a redirect at
every address another site owns, and installs the site's gate (`tools/pages_gate.py`) and release
(`tools/pages_release.sh`). Every file has one source: the assets (v1's `assets/`, taken in by `tools/assets_v1.py`)
are published here once, under `/v/<version>/assets/`; the data by the data API; each page's links, its route
(`<meta name="p2s-route">`, read by `assets/route.js`) and its Content-Security-Policy name those hosts at pinned
versions. `tools/parity.py` checks that every page v1 builds is owned by one site and reads the same there. Every
release after 1.0.0 adds one to the last number. `tools/chain.sh` is the whole round in one command: the records
and the data written in team and data exported into v1, v1's release, the assets taken in, the data imported, the
four sites cut, parity, every release. In pass two the build library itself moves here. The rules for working here
are in [CLAUDE.md](CLAUDE.md).
