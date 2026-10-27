#!/usr/bin/env python3
"""The press as served, built from git tags at deploy (run by the deploy workflow; nothing here is committed).

    python3 tools/package.py --into _site

Every tag v<a>.<b>.<c> is a published press version: at that tag, the tools, sites.json and every asset, with
manifest.json and each file's sha256. CI owns the version (https://sharness.ai/articles/ci-owns-the-version.html): it
writes VERSION, tags the release commit and deploys this. A version published before 27 October 2026 is read from the tag
the last commit that held v/ in the tree (found from the history), as it was; a newer one is built from its tag's files.

The served tree:
- /latest/                  the newest version, plain: every page of the four sites loads its assets from here
- /v/<version>/manifest.json for every version: each file's name, sha256 and size
- /v/<version>/<file>       plain copies, for the newest KEEP_PLAIN versions (a page cut against one of them still loads)
- /blobs/<sha256>           each distinct file content once, across all versions, so any version can be read and checked
- /versions.json, /index.html
GitHub Pages serves no symlinks and caps a site at 1 GB, so older versions are kept by manifest and blob, not as folders.
No clock: the same tags give the same tree.
"""
import argparse, hashlib, html, io, json, os, shutil, subprocess, sys, tarfile, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
HOME = 'https://press.php.oct.2026.newsroom.sgit.ai'
KEEP_PLAIN = 5


def git(*a, binary=False):
    r = subprocess.run(['git', '-C', ROOT, *a], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode()


def archive():
    """The last commit that held v/ in the tree: the parent of the commit that removed it (27 October 2026). Every
    version published before CI owned the version is read from there, as it was. None in a repository that never had v/."""
    try:
        gone = git('log', '-1', '--diff-filter=D', '--format=%H', 'HEAD', '--', 'v/').strip()
        return git('rev-parse', gone + '^').strip() if gone else None
    except subprocess.CalledProcessError:
        return None


def before_ci(ref):
    """The versions published as folders before CI owned the version."""
    if not ref: return []
    try: return [x for x in git('ls-tree', '--name-only', f'{ref}:v').split() if x[:1].isdigit()]
    except subprocess.CalledProcessError: return []


def vkey(v):
    return tuple(int(x) for x in v.split('.'))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def extract(ref, paths, dst):
    try:
        data = git('archive', ref, *paths, binary=True)
    except subprocess.CalledProcessError:
        return False
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        t.extractall(dst, filter='data')
    return True


def published(top):
    """What a version holds (as tools/publish.py published it): sites.json, assets.json, sources.json, the tools, and every
    file under assets/, build/, rules/ and vault-app/."""
    out = [f for f in ('sites.json', 'assets.json', 'sources.json') if os.path.exists(os.path.join(top, f))]
    out += sorted('tools/' + f for f in os.listdir(os.path.join(top, 'tools')) if f.endswith(('.py', '.sh')))
    for sub in ('assets', 'build', 'rules', 'vault-app'):
        for d, dirs, fs in os.walk(os.path.join(top, sub)):
            dirs.sort(); dirs[:] = [x for x in dirs if x != '__pycache__']
            out += sorted(os.path.relpath(os.path.join(d, f), top).replace(os.sep, '/') for f in fs if not f.endswith('.pyc'))
    return out


def build_version(src, dst, v):
    files = []
    for f in published(src):
        os.makedirs(os.path.dirname(os.path.join(dst, f)), exist_ok=True)
        shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
        files.append({'name': f, 'sha256': sha(os.path.join(src, f)), 'bytes': os.path.getsize(os.path.join(src, f))})
    m = {'press': v, 'url': f'{HOME}/v/{v}/', 'files': files}
    with open(os.path.join(dst, 'manifest.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(m, fh, indent=1, sort_keys=True); fh.write('\n')
    return m


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--into', required=True)
    out = os.path.abspath(ap.parse_args().into)
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    arch = archive(); before = set(before_ci(arch))
    vs = sorted({t[1:] for t in git('tag', '-l', 'v[0-9]*.[0-9]*.[0-9]*').split()} | before, key=vkey)   # the folders published before CI, then CI's tags
    if not vs:
        sys.exit('package: no version tags yet')
    blobs = 0
    for i, v in enumerate(vs):
        tmp = tempfile.mkdtemp()
        try:
            vdir = os.path.join(tmp, '_v')
            if v in before and extract(arch, [f'v/{v}'], tmp):         # published before CI minted versions: as it was
                os.rename(os.path.join(tmp, 'v', v), vdir)
                m = json.load(open(os.path.join(vdir, 'manifest.json'), encoding='utf-8'))
            else:
                src = os.path.join(tmp, 'src'); os.makedirs(src)
                extract(f'v{v}', ['.'], src)
                m = build_version(src, vdir, v)
            for f in m['files']:
                b = os.path.join(out, 'blobs', f['sha256'])
                if not os.path.exists(b):
                    os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copyfile(os.path.join(vdir, f['name']), b); blobs += 1
            if i >= len(vs) - KEEP_PLAIN:
                shutil.copytree(vdir, os.path.join(out, 'v', v))
            else:
                os.makedirs(os.path.join(out, 'v', v)); shutil.copyfile(os.path.join(vdir, 'manifest.json'), os.path.join(out, 'v', v, 'manifest.json'))
            if i == len(vs) - 1:
                shutil.copytree(vdir, os.path.join(out, 'latest'))
        finally:
            shutil.rmtree(tmp)
    with open(os.path.join(out, 'versions.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump({'press': 'php.oct.2026 newsroom', 'latest': vs[-1], 'versions': list(reversed(vs))}, fh, indent=1); fh.write('\n')
    cfg = json.load(open(os.path.join(ROOT, 'sites.json'), encoding='utf-8'))
    E = lambda s: html.escape(str(s), quote=True)
    rows = ''.join(f'<tr><td><a href="{E(c["home"])}/">{E(n)}</a></td><td>{E(c["serve_at"])}</td><td>{E("everything else" if c["sections"] == "*" else ", ".join(c["sections"]))}</td></tr>' for n, c in cfg['sites'].items())
    with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>PHP October 2026: the press</title>
<style>:root{{color-scheme:light dark}}body{{font:15px/1.5 system-ui,sans-serif;max-width:980px;margin:0 auto;padding:16px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:.3rem .5rem;border-bottom:1px solid #8884}}</style></head>
<body><h1>PHP October 2026: the press</h1>
<p>The shared assets, the build and the gates of the newsroom's sites. Every page loads its assets from <a href="latest/manifest.json">/latest/</a> (v{E(vs[-1])}). Every version's manifest is at <code>/v/&lt;version&gt;/manifest.json</code>, and <code>/blobs/&lt;sha256&gt;</code> serves each of its files; the newest {KEEP_PLAIN} are also served plain. The history is <a href="versions.json">versions.json</a>; a version is a tag in <a href="https://github.com/SGit-AI/SGit-AI__Website__Newsroom__2026__Oct__PHP__press">the press's repository</a>, written by CI.</p>
<h2>The sites</h2><table><thead><tr><th>Site</th><th>Served at</th><th>Sections</th></tr></thead><tbody>{rows}</tbody></table></body></html>
''')
    for f in ('CNAME',):
        if os.path.exists(os.path.join(ROOT, f)):
            shutil.copyfile(os.path.join(ROOT, f), os.path.join(out, f))
    open(os.path.join(out, '.nojekyll'), 'w').close()
    size = sum(os.path.getsize(os.path.join(d, x)) for d, _, fs in os.walk(out) for x in fs)
    print(f'package: {len(vs)} press versions (v{vs[0]} to v{vs[-1]}), {blobs} blobs, {min(KEEP_PLAIN, len(vs))} plain, {size / 1e6:.0f} MB')


if __name__ == '__main__':
    main()
