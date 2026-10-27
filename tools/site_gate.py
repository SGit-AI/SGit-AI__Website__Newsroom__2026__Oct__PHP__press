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
5. Every article in content/articles/ (site's) has the front matter the build needs, a plain name and slug, closed
   ```diff blocks, corrections as "<time> | <text>", the sources it cites in the data API and the figures it shows in
   the press (read by URL; skipped with a note offline), sliders of two pictures the same size.
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

# 5. the articles this site writes (content/articles/), checked at the writer's push: an article is drawn from its file
# (assets/live/article.js) and the next build gives it a frame, so what would stop that build stops here. The sources it
# cites must be in the data API's sources.json and its figures in the press, both read by URL (the versions press.json
# pins); offline, those two checks are skipped with a note, and CI runs them.
ART = os.path.join(ROOT, 'content', 'articles')
if os.path.isdir(ART):
    import struct, urllib.request
    ORIGINS = ('house', 'guest', 'update', 'interview')
    NEEDS = ('slug', 'title', 'dek', 'role', 'origin', 'author', 'written', 'as_of_version', 'vault_commit', 'data_as_of')
    IMG = r'/(assets/articles/[a-z0-9-]+/[a-z0-9-]+\.png)'
    def fetch(url, head=None):
        req = urllib.request.Request(url, headers={'Range': f'bytes=0-{head - 1}'} if head else {})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    remote, notes = {}, []
    def published(kind):
        """The data API's source slugs, or the press's files, read once; None when they cannot be read."""
        if kind not in remote:
            try:
                if kind == 'sources':
                    remote[kind] = {s['slug'] for s in json.loads(fetch(meta['data_base'] + 'sources.json')) if isinstance(s, dict) and 'slug' in s}
                else:
                    base = meta['assets'][:-len('assets/')]
                    remote[kind] = {f['name'] for f in json.loads(fetch(base + 'manifest.json'))['files']}
            except Exception as e:
                remote[kind] = None
                notes.append(f'{kind}: not read ({type(e).__name__}); skipped here, checked in CI')
        return remote[kind]
    slugs = {}
    for fn in sorted(os.listdir(ART)):
        if not fn.endswith('.md'):
            continue
        p = f'content/articles/{fn}'
        text = open(os.path.join(ART, fn), encoding='utf-8').read().replace('\r\n', '\n')
        if not re.fullmatch(r'[0-9a-z_.-]+\.md', fn):
            fails.append(f'{p}: the name must be lower case letters, digits, "-", "_" and "." (<date>__<role>__<slug>.md)')
        m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, flags=re.S)
        if not m:
            fails.append(f'{p}: no front matter (--- key: value lines ---, then the article)')
            continue
        fm = {}
        for line in m.group(1).splitlines():
            kv = re.match(r'^(\w+):\s*(.*)$', line)
            if kv:
                fm[kv.group(1)] = kv.group(2)
            elif line.strip():
                fails.append(f'{p}: front matter line is not "key: value": {line[:60]}')
        for k in NEEDS:
            if not fm.get(k):
                fails.append(f'{p}: front matter has no {k}')
        if fm.get('slug') and not re.fullmatch(r'[0-9a-z][0-9a-z-]*', fm['slug']):
            fails.append(f'{p}: slug "{fm["slug"]}" must be lower case letters, digits and "-"')
        if fm.get('slug') in slugs:
            fails.append(f'{p}: slug "{fm["slug"]}" is also {slugs[fm["slug"]]}\'s')
        slugs.setdefault(fm.get('slug'), p)
        if fm.get('origin') and fm['origin'] not in ORIGINS:
            fails.append(f'{p}: origin "{fm["origin"]}" is not one of {", ".join(ORIGINS)}')
        if fm.get('written') and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', fm['written']):
            fails.append(f'{p}: written "{fm["written"]}" is not a date (YYYY-MM-DD)')
        for k, v in fm.items():
            if re.fullmatch(r'correction\d+', k) and not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z \| \S', v):
                fails.append(f'{p}: {k} must be "<YYYY-MM-DDTHH:MMZ> | <what was corrected>"')
        body = m.group(2)
        if len(re.findall(r'^```diff\s*$', body, flags=re.M)) > len(re.findall(r'^```\s*$', body, flags=re.M)):
            fails.append(f'{p}: a ```diff block is not closed')
        cites = [x.strip() for g in re.findall(r'\[\[([^\]]+)\]\]', body) for x in g.split(',')]
        known = published('sources') if cites else set()
        for c in dict.fromkeys(cites):
            if known is not None and c not in known:
                fails.append(f'{p}: cites [[{c}]], which is not in the data API\'s sources.json (a fact names a captured source)')
        figs = re.findall(r'^!\[[^\]]+\]\(' + IMG, body, flags=re.M) + [x for t in re.findall(r'^!split\[[^\]]+\]\(' + IMG + r'\)\[[^\]]+\]\(' + IMG + r'\)', body, flags=re.M) for x in t]
        pairs = re.findall(r'^!slider\[[^\]]+\]\(' + IMG + r'\)\(' + IMG + r'\)', body, flags=re.M)
        files_there = published('assets') if (figs or pairs) else set()
        for f in dict.fromkeys(figs + [x for t in pairs for x in t]):
            if files_there is not None and f not in files_there:
                fails.append(f'{p}: shows /{f}, which the press does not publish (add it to the press\'s assets/articles/ first)')
        for a, b in pairs:
            if files_there is None or a not in files_there or b not in files_there:
                continue
            try:
                sizes = {struct.unpack('>II', fetch(meta['assets'] + x[len('assets/'):], head=24)[16:24]) for x in (a, b)}
                if len(sizes) > 1:
                    fails.append(f'{p}: the slider\'s /{a} and /{b} are not the same size')
            except Exception as e:
                notes.append(f'{p}: slider sizes not read ({type(e).__name__})')
    for n in notes:
        print('note:', n)

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
