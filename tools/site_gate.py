#!/usr/bin/env python3
"""A site's pages gate (tools/pages_gate.py), installed by the press (press.json names the version). Seconds. Exits non-zero on any failure.

1. Every file the press wrote is here, with the sha256 press.json records; nothing else is here but the repository's
   own files (README, CLAUDE.md, LICENSE, .gitignore, .github/, and what press.json lists as its own); the gate and
   release the press installed are checked like every other file, and nothing else may be under tools/.
2. Every relative link and source in every page, and every relative link in every markdown twin, resolves to a file
   in this repository.
3. Every link to another of the newsroom's sites names a page that site serves, every link to the press an asset its
   pinned version publishes, every link to the data API a file its pinned version publishes (press.json lists them).
4. CNAME names where this site is served; no credential shapes in any page, script or data file.
"""
import hashlib, json, os, posixpath, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LINK = re.compile(r'''\s(?:href|src)=(["'])((?:(?!\1).)*)\1''')
MDLINK = re.compile(r'\]\(([^)\s]+)\)')   # a markdown twin's links
SKIP = ('http:', 'https:', '//', '#', 'data:', 'mailto:', 'javascript:', 'tel:', 'blob:')
CREDENTIAL = re.compile(r'sgit_private_(vault|read)_[0-9a-f]{12,}|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|\bsk-(or-v1-|proj-|ant-[a-z0-9]+-)?[A-Za-z0-9_]{32,}')
fails = []
meta = json.load(open(os.path.join(ROOT, 'press.json'), encoding='utf-8'))
files = meta['files']


def own(p):
    return any(p == o or (o.endswith('/') and p.startswith(o)) for o in meta['own'])


# 1. what the press wrote, and nothing else
present = set()
for d, dirs, fs in os.walk(ROOT):
    dirs[:] = [x for x in dirs if x != '.git' and x != '__pycache__']
    for f in fs:
        present.add(os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/'))
for p, h in files.items():
    if p not in present:
        fails.append(f'{p}: listed in press.json, missing')
    elif hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest() != h:
        fails.append(f'{p}: changed since the press wrote it; partition again from v1 (an edit here is lost)')
for p in sorted(present - set(files)):
    if not own(p):
        fails.append(f'{p}: not written by the press and not one of this repository\'s own files')

# 2 and 3. links
pages = {s: set(ps) for s, ps in meta['pages_by_site'].items()}
assets, data_files = set(meta.get('press_assets', [])), set(meta.get('data_files', []))
homes = meta['homes']
broken = 0
known = {(p, u) for p, u in meta.get('broken_in_v1', [])}
for p in sorted(files):
    if not p.endswith(('.html', '.md')):
        continue
    text = open(os.path.join(ROOT, p), encoding='utf-8', errors='replace').read()
    for url in ([u for _, u in LINK.findall(text)] if p.endswith('.html') else MDLINK.findall(text)):
        path = url.split('#')[0].split('?')[0]
        if not path:
            continue
        if url.startswith(('https://', 'http://')):
            # the one source of assets and data: the press version and the data version press.json pins
            if url.startswith(meta.get('assets', '\0')):
                if path[len(meta['assets']):] not in assets:
                    fails.append(f'{p}: links to {url}, which press v{meta["press"]} does not publish')
                continue
            if url.startswith(meta.get('data_base', '\0')):
                if path[len(meta['data_base']):] not in data_files:
                    fails.append(f'{p}: links to {url}, which data v{meta["data"]} does not publish')
                continue
            for s, h in homes.items():
                if s != meta['site'] and url.startswith(h + '/') and h != meta['home']:
                    t = path[len(h) + 1:]
                    cands = [t + 'index.html'] if (t.endswith('/') or t == '') else [t, t + '/index.html']
                    # the main site answers every v1 address (its own pages, a redirect for every other site's, the
                    # runtime), so a link to it only has to name something v1 served
                    serves = set().union(*pages.values()) | set(files) if h == meta['homes'].get('site') else pages[s]
                    serves = set(serves) | {'VERSION'}   # every site serves its VERSION, written by its own CI
                    if not any(c in serves for c in cands) and not t.endswith(('.md', '.json', '.xml', '.txt')):
                        fails.append(f'{p}: links to {url}, which {s} does not serve')
            continue
        if url.startswith(SKIP):
            continue
        t = posixpath.normpath(path.lstrip('/') or '.') if path.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(p), path))
        cands = ['index.html'] if t == '.' else ([t + '/index.html'] if path.endswith('/') else [t, t + '/index.html'])
        if not any(c in present for c in cands):
            if (p, url) in known:
                continue
            broken += 1
            if broken <= 20:
                fails.append(f'{p}: links to {url}, which is not here')
if broken > 20:
    fails.append(f'and {broken - 20} more links to files that are not here')

# 4. where it is served, and no credentials
cname = open(os.path.join(ROOT, 'CNAME'), encoding='utf-8').read().strip() if 'CNAME' in present else ''
if cname != meta['serve_at']:
    fails.append(f'CNAME: "{cname}", press.json says {meta["serve_at"]}')
for p in sorted(files):
    if p.endswith(('.html', '.js', '.json', '.md', '.txt', '.xml', '.py', '.sh')):
        if CREDENTIAL.search(open(os.path.join(ROOT, p), encoding='utf-8', errors='replace').read()):
            fails.append(f'{p}: a credential shape')

for f in fails:
    print('FAIL:', f)
if fails:
    sys.exit(f'{len(fails)} failure(s)')
if known:
    print(f'note: {len(known)} link(s) that do not resolve in v1 either (press.json broken_in_v1); fix them at their source in v1')
c = meta['counts']
print(f'gate passed: {meta["site"]}, {c["pages"]} pages of its own, {c["redirects"]} redirects, {c["runtime"]} runtime files; '
      f'assets from press v{meta["press"]}, data from v{meta.get("data")}; v1 at {meta["v1"]["commit"][:12]} (site v{meta["v1"]["site_version"]})')
