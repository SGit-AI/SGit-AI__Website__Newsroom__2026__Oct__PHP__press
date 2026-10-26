# vault-app: the evidence vault's own app

The source of the app that opens when the PHP2Shell evidence vault is opened. It explores what the agents capture: sources, captures (screenshots, text, provenance hashes), claims, the timeline, and the editor's memos and agents' notes.

- `src/index.html.tpl`: the app, one self-contained HTML file (`.tpl` so the site gate and Pages do not treat it as a page) (inline CSS and JS, no external resources). It reads `sources/index.json`, `claims/*.json`, `timeline/*.json`, `memos/`, `notes/` and each source folder through `window.sg.vfs`, so it shows what is in the vault now; a snapshot inlined at build time is the fallback outside the vault.
- `build.py --vault <clone>`: renders reduced screenshots into `app/shots/`, writes `app/manifest.json`, `app/versions/`, `.vault/app.json` and `index.html` **into the clone only**. Nothing from the vault is written here: this repository is public and the vault is private. Then `sgit commit` and `sgit push` in the clone.
- `versions/`: one file per app version and `index.json`; the build copies them into the vault and records the vault head it built on.
- `test/screens.mjs <clone> <out> [--no-bridge]`: serves the clone locally, stands in for the bridge, renders every view at desktop (light and dark) and phone widths, and fails on any page or console error or horizontal overflow.

Follows the vault-app contract (sgit.ai/docs/vault/vault-apps.html): no declarative resources against vault paths, images assigned from JS, no `fetch` of vault paths, no `location.hash` writes, `sg-app-ready` posted on render, minimal HUD, `fs.read` as the only grant.
