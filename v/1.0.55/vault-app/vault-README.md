# app/: the vault's own app

Opening this vault boots `index.html` (declared in `.vault/app.json`): an explorer for everything here, the sources, their captures, the claims, the timeline and the desk.

- `app/shots/<slug>/<capture>.thumb.webp` and `.web.webp` are reduced copies of each capture's `screenshot.png`. They are derived, rebuildable and never evidence: the record is the capture folder, whose hashes are in its `provenance.json`.
- `app/manifest.json` is what the last build saw (screenshot sizes, files per source).
- `app/versions/` holds one file per app version and `index.json`.
- The app is read-only. `.vault/app.json` grants `fs.read` and nothing else: it reads `sources/index.json`, `claims/`, `timeline/`, `memos/`, `notes/` and the source folders at runtime, so new rows from any agent show without a rebuild. Only thumbnails for new captures wait for the next build.

The app's source and build script live in the site repository, `SGit-AI__Website__Newsroom__2026__Oct__PHP`, under `vault-app/`; the build is `python3 vault-app/build.py --vault <clone>`. The build writes only into the clone; nothing from this vault is committed to that public repository.
