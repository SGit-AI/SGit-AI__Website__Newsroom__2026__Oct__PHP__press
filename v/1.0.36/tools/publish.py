#!/usr/bin/env python3
"""Publish the press as the version in VERSION: v/<version>/ (immutable), latest/, versions.json, index.html.

A version folder holds sites.json and the tools, and manifest.json with each file's sha256, so a site can pin the
press that wrote it and check it. A version already published is never changed: different content under the same
version stops. No clock: the same files give the same bytes.
"""
import hashlib, html, json, os, shutil, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PUBLISH = ['sites.json', 'assets.json', 'tools/partition.py', 'tools/site_gate.py', 'tools/site_release.sh', 'tools/assets_v1.py', 'tools/parity.py', 'tools/chain.sh', 'tools/build.sh', 'tools/sync_v1.py', 'tools/site_sync.py', 'sources.json',
           'tools/publish.py', 'tools/gate.py', 'tools/release.sh']


def published():
    """The tools, sites.json, and every source the press holds (assets/, served once for every site; build/, the build and
    the gate; rules/, what every session reads; vault-app/), so a version is the whole press as it was."""
    out = list(PUBLISH)
    for top in ('assets', 'build', 'rules', 'vault-app'):
        for d, dirs, fs in os.walk(os.path.join(ROOT, top)):
            dirs.sort(); dirs[:] = [x for x in dirs if x != '__pycache__']
            out += sorted(os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/') for f in fs if not f.endswith('.pyc'))
    return [f for f in out if os.path.exists(os.path.join(ROOT, f))]


HOME = 'https://press.php.oct.2026.newsroom.sgit.ai'


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def vkey(v):
    return tuple(int(x) for x in v.split('.'))


def build(dst, version):
    files = []
    for f in published():
        os.makedirs(os.path.dirname(os.path.join(dst, f)) or dst, exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, f), os.path.join(dst, f))
        files.append({'name': f, 'sha256': sha(os.path.join(ROOT, f)), 'bytes': os.path.getsize(os.path.join(ROOT, f))})
    m = {'press': version, 'url': f'{HOME}/v/{version}/', 'files': files}
    with open(os.path.join(dst, 'manifest.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(m, f, indent=1, sort_keys=True); f.write('\n')
    return m


def same_as(version):
    """True when what would be published is, file for file, what v<version> already holds (then there is nothing to publish)."""
    man = os.path.join(ROOT, 'v', version, 'manifest.json')
    if not os.path.exists(man):
        return False
    have = {f['name']: f['sha256'] for f in json.load(open(man, encoding='utf-8'))['files']}
    return have == {f: sha(os.path.join(ROOT, f)) for f in published()}


def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--same-as':
        sys.exit(0 if same_as(sys.argv[2]) else 1)
    version = open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip()
    vdir = os.path.join(ROOT, 'v', version)
    if os.path.isdir(vdir):
        tmp = os.path.join(ROOT, '.publish-check'); shutil.rmtree(tmp, ignore_errors=True)
        build(tmp, version)
        same = all(os.path.exists(os.path.join(vdir, f)) and sha(os.path.join(tmp, f)) == sha(os.path.join(vdir, f)) for f in published() + ['manifest.json'])
        shutil.rmtree(tmp)
        if not same:
            sys.exit(f'publish: v{version} is already published with other content; bump VERSION')
    build(vdir, version)
    shutil.rmtree(os.path.join(ROOT, 'latest'), ignore_errors=True)
    shutil.copytree(vdir, os.path.join(ROOT, 'latest'))
    vs = sorted((d for d in os.listdir(os.path.join(ROOT, 'v')) if os.path.isfile(os.path.join(ROOT, 'v', d, 'manifest.json'))), key=vkey, reverse=True)
    with open(os.path.join(ROOT, 'versions.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'press': 'php.oct.2026 newsroom', 'latest': vs[0], 'versions': vs}, f, indent=1); f.write('\n')
    cfg = json.load(open(os.path.join(ROOT, 'sites.json'), encoding='utf-8'))
    E = lambda s: html.escape(str(s), quote=True)
    rows = ''.join(f'<tr><td><a href="{E(c["home"])}/">{E(n)}</a></td><td>{E(c["serve_at"])}</td><td>{E("everything else" if c["sections"] == "*" else ", ".join(c["sections"]))}</td><td>{E(c["what"])}</td></tr>' for n, c in cfg['sites'].items())
    with open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PHP October 2026: the press</title>
<style>:root{{color-scheme:light dark}}body{{font:15px/1.5 system-ui,sans-serif;max-width:980px;margin:0 auto;padding:16px}}table{{border-collapse:collapse;width:100%;font-size:14px}}
td,th{{text-align:left;padding:.3rem .5rem;border-bottom:1px solid #8884;vertical-align:top}}.tw{{overflow-x:auto}}</style></head>
<body>
<h1>PHP October 2026: the press</h1>
<p>What typesets, proofs and publishes the newsroom's sites on the PHP flaws of October 2026. In pass one of the split it partitions the site's built pages into four sites, each with its own repository, gate and address; every old address still answers. Latest: <a href="v/{E(vs[0])}/manifest.json">v{E(vs[0])}</a>; every version: <a href="versions.json">versions.json</a>. Source: <a href="https://github.com/SGit-AI/sgit-ai__website__newsroom__2026__oct__php__press">sgit-ai__website__newsroom__2026__oct__php__press</a>.</p>
<h2>The sites</h2>
<div class="tw"><table><thead><tr><th>Site</th><th>Served at</th><th>Sections</th><th>What</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>The data is its own API, <a href="https://data.php.oct.2026.newsroom.sgit.ai/">data.php.oct.2026.newsroom.sgit.ai</a>; the team's records are in the team repository.</p>
</body></html>
''')
    print(f'published press v{version}')


if __name__ == '__main__':
    main()
