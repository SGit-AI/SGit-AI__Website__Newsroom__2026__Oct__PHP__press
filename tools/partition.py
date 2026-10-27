#!/usr/bin/env python3
"""Partition v1's built site into one of the four sites (sites.json), and write it into that site's repository.

    python3 tools/partition.py --site refs --v1 ../sgit-ai__website__newsroom__2026__oct__php \\
        --data ../sgit-ai__website__newsroom__2026__oct__php__data --into ../sgit-ai__website__newsroom__2026__oct__php__refs

v1 is still where every page is built (its release commits the output), so a site is v1's committed output at one
commit, cut by section, with one source for every file (the editor, 25 October 2026):

- **its pages**: every page v1's build writes (admin/build/outputs.txt) whose first path segment the site owns;
- **assets/ from the press** and **data/ from the data API**, never copied: every page's links name them at the
  pinned versions (the press version that publishes this v1 commit's assets, the data version imported from it), its
  route (<meta name="p2s-route">, read by assets/route.js) sends what its scripts build there too, and its
  Content-Security-Policy allows those hosts and the other sites;
- **a redirect page** at the address of every page another site owns, so an old link and a search engine's index land;
- **its own runtime**: VERSION, the 404 router, .well-known/;
- links to v1's sources (a review's markdown, a data file the API does not publish) go to the file on GitHub.

It refuses to cut unless the press version holds exactly this v1 commit's assets and the data version exists. It
records, in the site's press.json, the versions, the v1 commit, every file it wrote with its sha256, and every site's
pages, the press's assets and the data's files (the site's gate checks every link against those). No clock: the same
inputs write the same bytes. The repository's own files (README, CLAUDE.md, LICENSE, .gitignore, .github/, press.json, and
the 'own' list of its entry in sites.json) are never touched; the gate and release the press installs under tools/ are
in press.json with their sha256 like every other file it writes.
"""
import argparse, hashlib, html, json, os, posixpath, re, shutil, subprocess, sys

PRESS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
KEEP = {'README.md', 'CLAUDE.md', 'LICENSE', '.gitignore', 'press.json', 'tools/', '.git/', '.github/', 'VERSION'}   # VERSION: written by the site's own CI, never by the partition   # .github/: a deploy workflow, through security
LINK = re.compile(r'''(\s(?:href|src)=)(["'])((?:(?!\2).)*)\2''')
MDLINK = re.compile(r'(\]\()([^)\s]+)(\))')   # a markdown link's target, in a page's markdown twin
CSP = re.compile(r'''(<meta http-equiv="Content-Security-Policy" content=")([^"]*)(")''')
SKIP = ('http:', 'https:', '//', '#', 'data:', 'mailto:', 'javascript:', 'tel:', 'blob:')
BROKEN_IN_V1 = set()  # (page, link) pairs that do not resolve in v1 either: reported by the site's gate, not caused by the press
TO_GITHUB = set()     # (page, path) pairs linked to v1's repository on GitHub: a source, or a data file the API does not publish


def data_published(data_root):
    """The names data serves at /latest/: every catalogue file (a folder entry: every file in it), its schema, the manifest."""
    cat = json.load(open(os.path.join(data_root, 'tools', 'catalogue.json'), encoding='utf-8'))['files']
    out = ['manifest.json']
    for c in cat:
        n = c['name']
        if n.endswith('/'):
            top = os.path.join(data_root, 'files', n.rstrip('/'))
            for d, dirs, fs in os.walk(top):
                out += [n + os.path.relpath(os.path.join(d, f), top).replace(os.sep, '/') for f in fs]
        else:
            out.append(n)
            sch = n.replace('.json', '.schema.json')
            if os.path.exists(os.path.join(data_root, 'schemas', sch)):
                out.append('schemas/' + sch)
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


def matches(path, prefixes):
    return any(path == p or (p.endswith('/') and path.startswith(p)) for p in prefixes)


class Plan:
    def __init__(self, v1, press_version, data_root, data_version):
        self.v1 = v1
        self.cfg = json.load(open(os.path.join(PRESS, 'sites.json'), encoding='utf-8'))
        self.sites = self.cfg['sites']
        self.by_section = {s: name for name, c in self.sites.items() if c['sections'] != '*' for s in c['sections']}
        el = self.cfg['elsewhere']
        self.assets_base = el['assets/']['home'] + el['assets/']['path'].format(press=press_version)
        self.data_base = el['data/']['home'] + el['data/']['path'].format(data=data_version)
        tracked = subprocess.run(['git', '-C', v1, 'ls-files', '-z'], capture_output=True, check=True).stdout.decode().split('\0')
        outputs = set(open(os.path.join(v1, 'admin', 'build', 'outputs.txt'), encoding='utf-8').read().split())
        self.v1_assets = {f[len('assets/'):]: sha256(os.path.join(v1, f)) for f in tracked if f.startswith('assets/')}
        # the pages load the press's assets and data's files from /latest/ (the editor, 27 October 2026): what this press
        # clone holds under assets/ is what the press serves at its next deploy, and data's catalogue is what data serves
        press_assets = {}
        for d, dirs, fs in os.walk(os.path.join(PRESS, 'assets')):
            dirs.sort()
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), os.path.join(PRESS, 'assets')).replace(os.sep, '/')
                press_assets[rel] = sha256(os.path.join(d, f))
        missing = sorted(set(self.v1_assets) - set(press_assets))
        if missing:   # a page would load an asset the pinned press version does not serve
            sys.exit(f'partition: press v{press_version} does not serve {len(missing)} asset(s) the pages load (e.g. {missing[:3]}); release the press first')
        # an asset the press holds a newer copy of (an owner released it while the box was building): the pages load the
        # newer one, which is what its owner released it for; said, not refused
        self.newer_assets = sorted(n for n in self.v1_assets if press_assets.get(n) != self.v1_assets[n])
        if self.newer_assets:
            print(f'partition: note: press v{press_version} holds a newer copy of {len(self.newer_assets)} asset(s) than the build used (e.g. {self.newer_assets[:3]}); the pages load those')
        self.data_files = set(data_published(data_root))
        self.runtime, self.files = [], {name: [] for name in self.sites}   # files: per site, its own pages and extras
        self.pages = {name: [] for name in self.sites}                     # per site, its own HTML pages
        self.sources = set()   # v1 files no site serves (its build, content, documents): linked on GitHub instead
        for f in sorted(t for t in tracked if t):
            if matches(f, self.cfg['runtime']['paths']):
                self.runtime.append(f); continue
            if matches(f, self.cfg['never']['paths']):
                self.sources.add(f); continue
            o = self.owner(f)
            self.files[o].append(f)
            if f.endswith('.html') and f in outputs:
                self.pages[o].append(f)
        self.served = set(self.runtime) | {f for fs in self.files.values() for f in fs}
        self.runtime_set = set(self.runtime)

    def owner(self, path):
        return self.by_section.get(path.split('/')[0] if '/' in path else '', 'site')

    def home(self, name):
        return self.sites[name]['home']

    def github(self, path):
        return f'https://github.com/{self.cfg["v1"]["repository"]}/blob/dev/{path}'

    def resolve(self, page, url):
        """What a relative link from page names: ('page', path), ('asset'|'data', name), ('source', path), or None."""
        p = url.split('#')[0].split('?')[0]
        if not p:
            return None
        t = posixpath.normpath(p.lstrip('/') or '.') if p.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(page), p))
        if t.startswith('..'):
            return None
        if t.startswith('assets/') and t[len('assets/'):] in self.v1_assets:
            return ('asset', t[len('assets/'):])
        if t.startswith('data/'):
            n = t[len('data/'):]
            return ('data', n) if n in self.data_files else ('source', t)
        cands = ['index.html'] if t == '.' else ([t + '/index.html'] if p.endswith('/') else [t, t + '/index.html'])
        for c in cands:
            if c in self.served:
                return ('page', c)
        if t in self.sources:
            return ('source', t)
        return None

    def route(self, site):
        sections = {s: self.home(n) for s, n in self.by_section.items()}
        sections.update({r.split('/')[0]: self.home(site) for r in self.cfg['runtime']['paths']})   # every site answers its own VERSION, 404, .well-known
        sections.update({o.rstrip('/'): self.home(n) for n, c in self.sites.items() for o in c.get('own', [])
                         if o.endswith('/') and '/' not in o.rstrip('/')})   # a folder a site writes itself (team's records/) is served by that site
        return json.dumps({'self': self.home(site), 'assets': self.assets_base, 'data': self.data_base,
                           'sections': dict(sorted(sections.items())), 'rest': self.home('site')},
                          separators=(',', ':'), sort_keys=True)

    def csp(self, policy):
        """The page's policy, allowing the press (scripts, styles, images, fonts), the data API and the other sites (requests)."""
        press = self.cfg['elsewhere']['assets/']['home']; data = self.cfg['elsewhere']['data/']['home']
        sites = sorted({c['home'] for c in self.sites.values()} | {'https://' + c['serve_at'] for c in self.sites.values()})
        add = {'script-src': [press], 'style-src': [press], 'img-src': [press], 'font-src': [press], 'manifest-src': [press],
               'media-src': [press], 'connect-src': [press, data] + sites}
        out, seen = [], set()
        for d in [x.strip() for x in policy.split(';') if x.strip()]:
            name = d.split()[0]; seen.add(name)
            extra = [h for h in add.get(name, []) if h not in d.split()]
            out.append(' '.join([d] + extra))
        if 'default-src' in seen:   # a directive the page leaves to default-src would block the host: say it, with 'self'
            out += [' '.join([name, "'self'"] + hosts) for name, hosts in add.items() if name not in seen]
        return '; '.join(out)


def rewrite(plan, site, page, text):
    """A page of `site`, cut: its links, its policy, its route, and its own address named for the site that serves it."""
    tail_of = lambda u: u[len(u.split('#')[0].split('?')[0]):]

    def target(url):
        """Where a link of this page goes now, or None to leave it as written."""
        if url == '' or url.startswith(SKIP):
            return None
        r = plan.resolve(page, url)
        if r is None:
            BROKEN_IN_V1.add((page, url)); return None
        kind, t = r
        if kind == 'asset':
            return f'{plan.assets_base}{t}{tail_of(url)}'
        if kind == 'data':
            return f'{plan.data_base}{t}{tail_of(url)}'
        if kind == 'source':
            TO_GITHUB.add((page, t)); return plan.github(t)
        if t in plan.runtime_set:
            return None
        o = plan.owner(t)
        if o == site:
            return None
        loc = t[:-len('index.html')] if t.endswith('/index.html') else ('' if t == 'index.html' else t)
        return f'{plan.home(o)}/{loc}{tail_of(url)}'

    def sub(m):   # an href or src in HTML
        new = target(m.group(3))
        return m.group(0) if new is None else f'{m.group(1)}{m.group(2)}{new}{m.group(2)}'

    def mdsub(m):   # a link in the page's markdown twin
        new = target(m.group(2))
        return m.group(0) if new is None else f'{m.group(1)}{new}{m.group(3)}'
    out = LINK.sub(sub, text)
    if page.endswith('.md'):
        out = MDLINK.sub(mdsub, out)
    v1home = plan.cfg['v1']['home']
    # absolute addresses of v1's assets and data (an image in the page's metadata, a link in a markdown twin)
    out = out.replace(v1home + '/assets/', plan.assets_base)
    out = re.sub(re.escape(v1home) + r'/data/([A-Za-z0-9_./-]*[A-Za-z0-9_/-])', lambda m: plan.data_base + m.group(1) if m.group(1) in plan.data_files else plan.github('data/' + m.group(1)), out)
    if page.endswith('.html'):
        out = CSP.sub(lambda m: m.group(1) + plan.csp(html.unescape(m.group(2))).replace('"', '&quot;') + m.group(3), out, count=1)
        meta = f'<meta name="p2s-route" content="{html.escape(plan.route(site), quote=True)}">'
        if 'assets/route.js' not in text:
            meta += f'\n<script src="{plan.assets_base}route.js"></script>'
        out = re.sub(r'(<meta charset="[^"]*">)', lambda m: m.group(1) + '\n' + meta, out, count=1)
    home = plan.home(site)
    if home != v1home:
        out = out.replace(f'{v1home}/{page}', f'{home}/{page}')
        own = page[:-len('index.html')] if page.endswith('index.html') else page
        if own and own != page:
            out = out.replace(f'{v1home}/{own}"', f'{home}/{own}"')
        if page.endswith('.html'):
            md = page[:-5] + '.md'
            out = out.replace(f'{v1home}/{md}', f'{home}/{md}')
        else:
            out = out.replace(f'{v1home}/{page[:-3]}.html', f'{home}/{page[:-3]}.html')
    return out


def stub(url, title):
    t = html.escape(title, quote=True); u = html.escape(url, quote=True)
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Moved: {t}</title><link rel="canonical" href="{u}"><meta http-equiv="refresh" content="0; url={u}"><meta name="robots" content="noindex">'
            f'</head><body><p>This page is now at <a href="{u}">{u}</a>.</p></body></html>\n')


def title_of(v1, rel):
    m = re.search(r'<title>(.*?)</title>', open(os.path.join(v1, rel), encoding='utf-8', errors='replace').read(), re.S)
    return html.unescape(re.sub(r'\s+', ' ', m.group(1)).strip()) if m else rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', required=True)
    ap.add_argument('--v1', required=True)
    ap.add_argument('--data', required=True, help='a clone of the data repository')
    ap.add_argument('--into', required=True)
    ap.add_argument('--press-version', default=None, help="default: this press's VERSION")
    ap.add_argument('--data-version', default=None, help="default: the data clone's VERSION")
    a = ap.parse_args()
    v1, into, data_root = os.path.abspath(a.v1), os.path.abspath(a.into), os.path.abspath(a.data)
    if subprocess.run(['git', '-C', v1, 'status', '--porcelain', '--untracked-files=no'], capture_output=True, text=True).stdout.strip():
        sys.exit('partition: the v1 clone has uncommitted changes; partition a released commit')
    pv = a.press_version or open(os.path.join(PRESS, 'VERSION'), encoding='utf-8').read().strip()
    dv = a.data_version or open(os.path.join(data_root, 'VERSION'), encoding='utf-8').read().strip()
    plan = Plan(v1, pv, data_root, dv)
    if a.site not in plan.sites:
        sys.exit(f'partition: no site "{a.site}" in sites.json')
    site, cfg = a.site, plan.sites[a.site]
    keep = KEEP | set(cfg.get('own', []))
    old = os.path.join(into, 'press.json')
    if os.path.exists(old):
        for f in json.load(open(old, encoding='utf-8'))['files']:
            if not matches(f, keep) and os.path.exists(os.path.join(into, f)):
                os.remove(os.path.join(into, f))
        for d, dirs, fs in os.walk(into, topdown=False):   # folders the last cut left empty
            if '/.git' not in d and d != into and not os.listdir(d):
                os.rmdir(d)
    written = {}

    def put(rel, data):
        if matches(rel, keep) and not rel.startswith('tools/pages_'):
            sys.exit(f"partition: {rel} is the repository's own file; sites.json or OWN is wrong")
        p = os.path.join(into, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f:
            f.write(data)
        written[rel] = hashlib.sha256(data).hexdigest()

    for f in plan.runtime + plan.files[site]:
        if f == 'VERSION':
            continue   # each site's CI writes its own VERSION (CI owns the version); the route still sends VERSION here
        raw = open(os.path.join(v1, f), 'rb').read()
        if f.endswith(('.html', '.md')) and (f in plan.files[site] or f in ('404.html', '404.md')):
            raw = rewrite(plan, site, f, raw.decode('utf-8')).encode('utf-8')
        put(f, raw)
    stubs = 0
    for other in plan.sites:
        if other == site:
            continue
        for p in plan.pages[other]:
            if p in written or matches(p, keep):
                continue   # a page of this site's own, or one of the repository's own files (the team's front page)
            loc = p[:-len('index.html')] if p.endswith('/index.html') else p
            put(p, stub(f'{plan.home(other)}/{loc}', title_of(v1, p)).encode('utf-8')); stubs += 1
    host = cfg['serve_at']
    final = plan.home(site).split('//', 1)[1]
    locs = ''.join(f'<url><loc>{html.escape(plan.home(site))}/{html.escape(p[:-len("index.html")] if p.endswith("index.html") else p)}</loc></url>\n' for p in plan.pages[site])
    put('sitemap.xml', f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{locs}</urlset>\n'.encode())
    robots = 'User-agent: *\nDisallow: /\n' if host != final else f'User-agent: *\nAllow: /\nSitemap: {plan.home(site)}/sitemap.xml\n'
    put('robots.txt', robots.encode())
    put('CNAME', (host + '\n').encode())
    put('.nojekyll', b'')
    for t in ('site_gate.py', 'site_release.sh', 'site_sync.py'):   # the site's gate, release and sync, with their sha256 in press.json like every file
        dst = 'tools/' + t.replace('site_', 'pages_')
        put(dst, open(os.path.join(PRESS, 'tools', t), 'rb').read())
        os.chmod(os.path.join(into, dst), 0o755)
    commit = subprocess.run(['git', '-C', v1, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    meta = {
        'press': pv, 'data': dv, 'assets': plan.assets_base, 'data_base': plan.data_base,
        'site': site, 'home': plan.home(site), 'serve_at': host, 'own': sorted(keep - {'.git/', 'tools/'}), 'sources': cfg.get('sources', {}),   # under tools/, only what the press installed and the 'own' list
        'v1': {'repository': plan.cfg['v1']['repository'], 'commit': commit,
               'site_version': open(os.path.join(v1, 'VERSION'), encoding='utf-8').read().strip()},
        'counts': {'pages': len(plan.pages[site]), 'files': len(plan.files[site]), 'runtime': len(plan.runtime), 'redirects': stubs,
                   'to_github': len(TO_GITHUB)},
        'broken_in_v1': sorted([p, u] for p, u in BROKEN_IN_V1),
        'pages_by_site': {n: plan.pages[n] for n in plan.sites},
        'homes': {n: plan.home(n) for n in plan.sites},
        'press_assets': sorted(plan.v1_assets),
        'data_files': sorted(plan.data_files),
        'files': dict(sorted(written.items())),
    }
    with open(os.path.join(into, 'press.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, sort_keys=True); f.write('\n')
    print(f'{site}: {len(plan.pages[site])} pages and {len(plan.files[site]) - len(plan.pages[site])} other files of its own, '
          f'{len(plan.runtime)} runtime files, {stubs} redirects; assets from press v{pv}, data from v{dv}; v1 at {commit[:12]} (site v{meta["v1"]["site_version"]})')


if __name__ == '__main__':
    main()
