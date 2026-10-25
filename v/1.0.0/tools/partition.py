#!/usr/bin/env python3
"""Partition v1's built site into one of the four sites (sites.json), and write it into that site's repository.

    python3 tools/partition.py --site refs --v1 ../sgit-ai__website__newsroom__2026__oct__php --into ../sgit-ai__website__newsroom__2026__oct__php__refs

Pass one of the split: v1 is still where every page is built (its release commits the output), so a site is v1's
committed output at one commit, cut by section:

- **its pages**: every page v1's build writes (admin/build/outputs.txt) whose first path segment the site owns;
- **the runtime**, copied to every site (the pages' Content-Security-Policy loads scripts and data only from their
  own host): assets/, data/, VERSION, the 404 router;
- **a redirect page** at the address of every page another site owns, so an old link, a link a script builds and a
  search engine's index all still land;
- **links that cross**: a relative link from one of its pages to a page another site owns becomes that page's
  absolute address, and a page's own canonical address names the site that now serves it.

It records, in the site's press.json, the press version, the v1 commit, every file it wrote with its sha256, and
every site's page list (the site's gate checks links across sites against those). Nothing reads a clock: the same v1
commit and the same press version write the same bytes. Files the site's repository keeps for itself (its README,
CLAUDE.md, tools/, and what sites.json lists as its own) are never touched.
"""
import argparse, hashlib, html, json, os, posixpath, re, shutil, subprocess, sys

PRESS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
KEEP = {'README.md', 'CLAUDE.md', 'LICENSE', '.gitignore', 'press.json', 'tools/', '.git/'}
OWN = {'team': ['records/', 'index.html']}  # what a site's repository writes itself, besides KEEP
LINK = re.compile(r'''(\s(?:href|src)=)(["'])([^"']*)\2''')
SKIP = ('http:', 'https:', '//', '#', 'data:', 'mailto:', 'javascript:', 'tel:', 'blob:')
BROKEN_IN_V1 = set()  # (page, link) pairs that do not resolve in v1 either: reported by the site's gate, not caused by the press


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


def matches(path, prefixes):
    return any(path == p or (p.endswith('/') and path.startswith(p)) for p in prefixes)


class Plan:
    def __init__(self, v1):
        self.v1 = v1
        self.cfg = json.load(open(os.path.join(PRESS, 'sites.json'), encoding='utf-8'))
        self.sites = self.cfg['sites']
        self.by_section = {s: name for name, c in self.sites.items() if c['sections'] != '*' for s in c['sections']}
        tracked = subprocess.run(['git', '-C', v1, 'ls-files', '-z'], capture_output=True, check=True).stdout.decode().split('\0')
        outputs = set(open(os.path.join(v1, 'admin', 'build', 'outputs.txt'), encoding='utf-8').read().split())
        self.runtime, self.files = [], {name: [] for name in self.sites}   # files: per site, its own pages and extras
        self.pages = {name: [] for name in self.sites}                     # per site, its own HTML pages
        self.sources = set()   # v1 files no site serves (its build, content, documents): linked on GitHub instead
        for f in sorted(t for t in tracked if t):
            if matches(f, self.cfg['never']['paths']):
                self.sources.add(f); continue
            if matches(f, self.cfg['runtime']['paths']):
                self.runtime.append(f); continue
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

    def target(self, page, url):
        """The v1 path a relative link from page points to, if it is a file v1 serves; else None."""
        p = url.split('#')[0].split('?')[0]
        if not p:
            return None
        t = posixpath.normpath(posixpath.join(posixpath.dirname(page), p))
        if t.startswith('..'):
            return None
        cands = ['index.html'] if t == '.' else ([t + '/index.html'] if p.endswith('/') else [t, t + '/index.html'])
        for c in cands:
            if c in self.served:
                return c
        return None


def rewrite(plan, site, page, text):
    """A page of `site`: cross-site relative links made absolute, its own address named for the site that serves it."""
    def sub(m):
        url = m.group(3)
        if url.startswith(SKIP) or url == '':
            return m.group(0)
        t = plan.target(page, url)
        if t is None:
            p = url.split('#')[0].split('?')[0]
            src = posixpath.normpath(posixpath.join(posixpath.dirname(page), p))
            if src in plan.sources:
                # a link to one of v1's source files (a review, a brief's markdown): v1 served its whole repository,
                # the new sites serve only pages, so the link goes to the file in v1's repository
                return f'{m.group(1)}{m.group(2)}https://github.com/{plan.cfg["v1"]["repository"]}/blob/dev/{src}{m.group(2)}'
            if p and not url.startswith(SKIP):
                BROKEN_IN_V1.add((page, url))
            return m.group(0)
        if t in plan.runtime_set:
            return m.group(0)
        o = plan.owner(t)
        if o == site:
            return m.group(0)
        tail = url[len(url.split('#')[0].split('?')[0]):]
        loc = t[:-len('index.html')] if t.endswith('/index.html') else ('' if t == 'index.html' else t)
        return f'{m.group(1)}{m.group(2)}{plan.home(o)}/{loc}{tail}{m.group(2)}'
    out = LINK.sub(sub, text)
    v1home, home = plan.cfg['v1']['home'], plan.home(site)
    if home != v1home:
        own = page[:-len('index.html')] if page.endswith('index.html') else page
        out = out.replace(f'{v1home}/{page}', f'{home}/{page}')
        if own and own != page:
            out = out.replace(f'{v1home}/{own}"', f'{home}/{own}"')
        md = page[:-5] + '.md'
        out = out.replace(f'{v1home}/{md}', f'{home}/{md}')
    return out


def stub(url, title):
    t = html.escape(title, quote=True); u = html.escape(url, quote=True)
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Moved: {t}</title><link rel="canonical" href="{u}"><meta http-equiv="refresh" content="0; url={u}"><meta name="robots" content="noindex">'
            f'</head><body><p>This page is now at <a href="{u}">{u}</a>.</p></body></html>\n')


def title_of(path):
    m = re.search(r'<title>(.*?)</title>', open(path, encoding='utf-8', errors='replace').read(), re.S)
    return html.unescape(re.sub(r'\s+', ' ', m.group(1)).strip()) if m else path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', required=True)
    ap.add_argument('--v1', required=True)
    ap.add_argument('--into', required=True)
    a = ap.parse_args()
    v1, into = os.path.abspath(a.v1), os.path.abspath(a.into)
    if subprocess.run(['git', '-C', v1, 'status', '--porcelain', '--untracked-files=no'], capture_output=True, text=True).stdout.strip():
        sys.exit('partition: the v1 clone has uncommitted changes; partition a released commit')
    plan = Plan(v1)
    if a.site not in plan.sites:
        sys.exit(f'partition: no site "{a.site}" in sites.json')
    site, cfg = a.site, plan.sites[a.site]
    keep = KEEP | set(OWN.get(site, []))
    # remove what the last partition wrote (its press.json lists it); the repository's own files stay
    old = os.path.join(into, 'press.json')
    if os.path.exists(old):
        for f in json.load(open(old, encoding='utf-8'))['files']:
            if not matches(f, keep) and os.path.exists(os.path.join(into, f)):
                os.remove(os.path.join(into, f))
    written = {}

    def put(rel, data):
        if matches(rel, keep):
            sys.exit(f'partition: {rel} is the repository\'s own file; sites.json or OWN is wrong')
        p = os.path.join(into, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f:
            f.write(data)
        written[rel] = hashlib.sha256(data).hexdigest()

    for f in plan.runtime + plan.files[site]:
        raw = open(os.path.join(v1, f), 'rb').read()
        if f in plan.files[site] and f.endswith(('.html', '.md')):
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
            put(p, stub(f'{plan.home(other)}/{loc}', title_of(os.path.join(v1, p))).encode('utf-8')); stubs += 1
    # this site's own addresses for search engines; a site still staged elsewhere asks not to be indexed yet
    host = cfg['serve_at']
    final = plan.home(site).split('//', 1)[1]
    locs = ''.join(f'<url><loc>{html.escape(plan.home(site))}/{html.escape(p[:-len("index.html")] if p.endswith("index.html") else p)}</loc></url>\n' for p in plan.pages[site])
    put('sitemap.xml', f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{locs}</urlset>\n'.encode())
    robots = 'User-agent: *\nDisallow: /\n' if host != final else f'User-agent: *\nAllow: /\nSitemap: {plan.home(site)}/sitemap.xml\n'
    put('robots.txt', robots.encode())
    put('CNAME', (host + '\n').encode())
    put('.nojekyll', b'')
    # the site's gate and release, installed from this press version
    for t in ('site_gate.py', 'site_release.sh'):
        dst = os.path.join(into, 'tools', t.replace('site_', 'pages_'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(PRESS, 'tools', t), dst)
        os.chmod(dst, 0o755)
    commit = subprocess.run(['git', '-C', v1, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    meta = {
        'press': open(os.path.join(PRESS, 'VERSION'), encoding='utf-8').read().strip(),
        'site': site, 'home': plan.home(site), 'serve_at': host, 'own': sorted(keep - {'.git/'}),
        'v1': {'repository': plan.cfg['v1']['repository'], 'commit': commit,
               'site_version': open(os.path.join(v1, 'VERSION'), encoding='utf-8').read().strip()},
        'counts': {'pages': len(plan.pages[site]), 'files': len(plan.files[site]), 'runtime': len(plan.runtime), 'redirects': stubs},
        'broken_in_v1': sorted([p, u] for p, u in BROKEN_IN_V1),
        'pages_by_site': {n: plan.pages[n] for n in plan.sites},
        'homes': {n: plan.home(n) for n in plan.sites},
        'files': dict(sorted(written.items())),
    }
    with open(os.path.join(into, 'press.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, sort_keys=True); f.write('\n')
    print(f'{site}: {len(plan.pages[site])} pages and {len(plan.files[site]) - len(plan.pages[site])} other files of its own, '
          f'{len(plan.runtime)} runtime files, {stubs} redirects, from v1 at {commit[:12]} (site v{meta["v1"]["site_version"]})')


if __name__ == '__main__':
    main()
