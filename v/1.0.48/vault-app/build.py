#!/usr/bin/env python3
"""Build the evidence-vault app into a clone of the vault.

    python3 vault-app/build.py --vault <path to an sgit clone of the evidence vault>

Writes, inside the clone only (never into this repository, which is public):
  index.html                the app: src/index.html.tpl with a snapshot of the vault inlined as its fallback
  .vault/app.json           the manifest (minimal chrome, read-only: no grants)
  app/manifest.json         what the build saw: screenshots and their derived sizes, files per source
  app/shots/<slug>/<capture>.thumb.webp   480x300, the top of the page
  app/shots/<slug>/<capture>.web.webp     1100 wide, at most 6000 tall, for the in-app viewer
  app/versions/index.json   and one file per version, from vault-app/versions/
  app/README.md             what app/ is

Derived images are additive and keyed by capture, so a rebuild only renders new captures.
The app reads sources/index.json, claims/ and timeline/ live through the bridge, so captures and
claims added after a build still show; only their thumbnails wait for the next build.
Standard library plus Pillow.
"""
import argparse, hashlib, json, os, re, subprocess, sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
THUMB = (480, 300)
WEB_W, WEB_MAX_H = 1100, 6000
MARKER = 'const SNAPSHOT = /*__SNAPSHOT__*/null;'


def render_shot(job):
    src, thumb, web = job
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(src) as im:
        im = im.convert('RGB')
        ow, oh = im.size
        if not thumb.exists():
            crop_h = min(oh, round(ow * THUMB[1] / THUMB[0]))
            im.crop((0, 0, ow, crop_h)).resize(THUMB, Image.LANCZOS).save(thumb, 'WEBP', quality=72, method=6)
        if not web.exists():
            h = round(oh * WEB_W / ow)
            crop_src_h = oh if h <= WEB_MAX_H else round(WEB_MAX_H * ow / WEB_W)
            out = im.crop((0, 0, ow, crop_src_h)).resize((WEB_W, min(h, WEB_MAX_H)), Image.LANCZOS)
            out.save(web, 'WEBP', quality=70, method=4)
    return str(src), ow, oh


def vault_head(vault):
    try:
        out = subprocess.run(['sgit', 'history', 'log'], cwd=vault, capture_output=True, text=True, timeout=120).stdout
        m = re.search(r'^\s*([0-9a-f]{12})\s+\(HEAD\)', out, re.M)
        return m.group(1) if m else None
    except Exception:
        return None


def read_json(p, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vault', required=True)
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    args = ap.parse_args()
    vault = Path(args.vault).resolve()
    if not (vault / '.sg_vault').exists() or not (vault / 'sources').exists():
        sys.exit(f'{vault} is not a clone of the evidence vault')

    versions = read_json(HERE / 'versions' / 'index.json', None)
    if not versions:
        sys.exit('vault-app/versions/index.json is missing')
    version = versions['current']
    head = vault_head(vault)
    built = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')

    # 1. screenshots -> thumb + web
    shots_dir = vault / 'app' / 'shots'
    jobs = []
    for png in sorted(vault.glob('sources/*/captures/*/screenshot.png')):
        slug, cap = png.parts[-4], png.parts[-2]
        d = shots_dir / slug
        d.mkdir(parents=True, exist_ok=True)
        jobs.append((png, d / f'{cap}.thumb.webp', d / f'{cap}.web.webp'))
    dims = {}
    dims_cache = read_json(vault / 'app' / 'manifest.json', {}).get('shots', {})
    todo = []
    for png, th, web in jobs:
        slug, cap = png.parts[-4], png.parts[-2]
        cached = dims_cache.get(slug, {}).get(cap)
        if th.exists() and web.exists() and cached:
            dims[(slug, cap)] = (cached['ow'], cached['oh'])
        else:
            todo.append((png, th, web))
    print(f'screenshots: {len(jobs)}, to render: {len(todo)}')
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for src, ow, oh in ex.map(render_shot, todo):
            p = Path(src)
            dims[(p.parts[-4], p.parts[-2])] = (ow, oh)

    shots = {}
    for png, th, web in jobs:
        slug, cap = png.parts[-4], png.parts[-2]
        ow, oh = dims[(slug, cap)]
        wh = min(round(oh * WEB_W / ow), WEB_MAX_H)
        shots.setdefault(slug, {})[cap] = {
            'thumb': th.relative_to(vault).as_posix(), 'web': web.relative_to(vault).as_posix(),
            'ow': ow, 'oh': oh, 'ww': WEB_W, 'wh': wh, 'cut': round(oh * WEB_W / ow) > WEB_MAX_H}

    # 2. files per source, with sizes (the app lists them; live listing replaces this when the bridge allows)
    files = {}
    for sdir in sorted(p for p in (vault / 'sources').iterdir() if p.is_dir()):
        rows = []
        for f in sorted(sdir.rglob('*')):
            if f.is_file():
                rows.append([f.relative_to(sdir).as_posix(), f.stat().st_size])
        files[sdir.name] = rows

    manifest = {'app_version': version, 'built_utc': built, 'vault_head': head,
                'shots': shots, 'files': files}
    (vault / 'app').mkdir(exist_ok=True)
    (vault / 'app' / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')) + '\n')

    # 3. versions
    vdir = vault / 'app' / 'versions'
    vdir.mkdir(parents=True, exist_ok=True)
    for f in (HERE / 'versions').glob('*.json'):
        data = read_json(f, {})
        if f.name != 'index.json' and data.get('version') == version:
            data.setdefault('vault_head_at_build', head)
            data['built_utc'] = built
        (vdir / f.name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')

    # 4. the snapshot inlined as the fallback: everything small the app reads live
    def folder(name, pattern):
        return {p.relative_to(vault).as_posix(): read_json(p, []) for p in sorted((vault / name).glob(pattern))}

    def texts(name, pattern):
        return {p.relative_to(vault).as_posix(): p.read_text(encoding='utf-8', errors='replace')
                for p in sorted((vault / name).glob(pattern))}

    notes = {}
    for p in sorted(vault.glob('sources/*/notes.md')):
        notes[p.parts[-2]] = p.read_text(encoding='utf-8', errors='replace')
    snapshot = {
        'taken_utc': built, 'vault_head': head,
        'readme': (vault / 'README.md').read_text(encoding='utf-8') if (vault / 'README.md').exists() else '',
        'sources': read_json(vault / 'sources' / 'index.json', []),
        'claims': folder('claims', '*.json'),
        'timeline': folder('timeline', '*.json'),
        'memos': texts('memos', '*'),
        'notes': texts('notes', '*.md'),
        'source_notes': notes,
        'manifest': manifest,
        'versions': versions,
        'version_files': {f.name: read_json(f, {}) for f in sorted(vdir.glob('*.json')) if f.name != 'index.json'},
    }
    compact = json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'))
    compact = compact.replace('</', '<\\/')  # never close the inline <script> early
    assert '\n' not in compact

    tpl = (HERE / 'src' / 'index.html.tpl').read_text(encoding='utf-8')
    if tpl.count(MARKER) != 1:
        sys.exit('the snapshot marker must appear exactly once in src/index.html.tpl')
    html = tpl.replace(MARKER, 'const SNAPSHOT = /*__SNAPSHOT__*/' + compact + ';')
    html = html.replace('__APP_VERSION__', version)
    (vault / 'index.html').write_text(html, encoding='utf-8')

    app_json = {
        'entry': 'index.html', 'present': True, 'auto_open': True,
        'title': 'PHP2Shell evidence vault',
        'hud': {'mode': 'minimal'},
        'permissions': {'fs': {'read': True}},
    }
    (vault / '.vault').mkdir(exist_ok=True)
    (vault / '.vault' / 'app.json').write_text(json.dumps(app_json, indent=1) + '\n')
    (vault / 'app' / 'README.md').write_text((HERE / 'vault-README.md').read_text(encoding='utf-8'))

    size = len(html.encode('utf-8'))
    print(f'index.html {size/1024:.0f} KB (snapshot {len(compact)/1024:.0f} KB), {len(shots)} sources with screenshots, '
          f'version {version}, vault head {head}, sha256 {hashlib.sha256(html.encode()).hexdigest()[:12]}')


if __name__ == '__main__':
    main()
