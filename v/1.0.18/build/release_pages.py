"""The pages each release changed, for the release history (admin/versions.html).

A page counts as changed when the content of its <main> differs from the previous release's, with the two site
version numbers masked: the header, the footer and the version stamp change on every page at every release and say
nothing about what the release did. Pages are compared as built and committed, so the list is what a reader would
have seen change. Stored in data/release-pages.json, one entry per release, written once and never recomputed:

    python3 admin/build/release_pages.py --all   fills every release that has a commit and no entry yet
    build.py, at a release's own build            the release being built, against the last release commit

Reads git; where git or the history is missing (a shallow checkout in CI, a copy of the tree), nothing is computed
and the stored entries stand.
"""
import html, json, os, re, subprocess, sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STORE = os.path.join(ROOT, 'data', 'release-pages.json')
RELEASE = re.compile(r'^v(\d+\.\d+\.\d+): ')
# pages that change at every release by construction, so they would head every list and say nothing
ALWAYS = re.compile(r'^(admin/versions\.html|admin/index\.html|admin/design/|versions/|whatsnew/|admin/board/|team/status/|team/runs/|feeds/|status/)')


def git(*args, inp=None):
    return subprocess.run(['git', '-C', ROOT, *args], input=inp, capture_output=True, check=True).stdout


def releases():
    """(version, commit) for every release commit on this branch, oldest first; the first commit per version."""
    out, seen = [], set()
    for line in git('log', '--reverse', '--format=%H %s').decode('utf-8', 'replace').splitlines():
        h, _, s = line.partition(' ')
        m = RELEASE.match(s)
        if m and m.group(1) not in seen:
            seen.add(m.group(1)); out.append((m.group(1), h))
    return out


def blobs(commit, paths):
    """{path: bytes} for the paths that exist at commit, in one git cat-file call."""
    if not paths:
        return {}
    out = git('cat-file', '--batch', inp=''.join(f'{commit}:{p}\n' for p in paths).encode())
    got, i = {}, 0
    for p in paths:
        j = out.index(b'\n', i); head = out[i:j].split()
        if head[-1] == b'missing':
            i = j + 1; continue
        n = int(head[2]); got[p] = out[j + 1:j + 1 + n]; i = j + 1 + n + 1
    return got


def main_text(page, versions):
    s = page.decode('utf-8', 'replace')
    a, b = s.find('<main'), s.rfind('</main>')
    s = s[a:b] if a >= 0 and b > a else s
    for v in versions:
        s = s.replace(v, 'VER')
    return s


def title(page):
    m = re.search(r'<title>(.*?)</title>', page.decode('utf-8', 'replace'), re.S)
    t = html.unescape(re.sub(r'\s+', ' ', m.group(1)).strip()) if m else ''
    return re.sub(r'\s*[|·–-]\s*PHP October 2026\s*$', '', t)


def words(text):
    """Visible words of a page's main content, as a multiset: tags dropped, numbers apart from words."""
    seen = re.sub(r'<(script|style|svg)\b.*?</\1>', ' ', text, flags=re.S)
    seen = html.unescape(re.sub(r'<[^>]+>', ' ', seen))
    toks = re.findall(r'[^\W\d_]+|\d+', seen.lower())
    return Counter(t for t in toks if not t.isdigit()), Counter(t for t in toks if t.isdigit())


def compare(old, new, versions):
    """old, new: {path: html bytes}. The new and changed pages, ranked: new pages first, then by how many visible
    words changed; pages where only numbers or markup changed (a counter, a link) after those; the always-changing
    hubs last."""
    rows = []
    for p, h in new.items():
        b = main_text(h, versions)
        if p not in old:
            rows.append({'path': p, 'title': title(h), 'new': True, 'words': sum(words(b)[0].values()), 'numbers': 0})
            continue
        a = main_text(old[p], versions)
        if a == b:
            continue
        (wa, na), (wb, nb) = words(a), words(b)
        rows.append({'path': p, 'title': title(h), 'new': False, 'words': sum(((wa - wb) + (wb - wa)).values()), 'numbers': sum(((na - nb) + (nb - na)).values())})
    # the always-changing hubs go last, by path only: their word counts include this store as read at the start of the
    # build (admin/versions.html shows it), so ranking them by words made the first and second build differ (board 175)
    rows.sort(key=lambda r: (1, False, False, 0, 0, r['path']) if ALWAYS.match(r['path']) else (0, not r['new'], r['words'] == 0, -r['words'], -r['numbers'], r['path']))
    return [{'path': r['path'], 'title': r['title'], 'new': r['new'], 'minor': not r['new'] and r['words'] == 0} for r in rows]


def html_paths(commit):
    return [p for p in git('ls-tree', '-r', '--name-only', commit).decode().splitlines() if p.endswith('.html')]


def load():
    try:
        return json.load(open(STORE))
    except FileNotFoundError:
        return {'about': __doc__.split('\n\n')[1].replace('\n', ' '), 'releases': {}}


def save(store):
    store['releases'] = dict(sorted(store['releases'].items(), key=lambda kv: [int(x) for x in kv[0].split('.')], reverse=True))
    with open(STORE, 'w', encoding='utf-8') as f:
        json.dump(store, f, indent=1, ensure_ascii=False); f.write('\n')


def fill_all():
    store, rels = load(), releases()
    for (v0, c0), (v1, c1) in zip(rels, rels[1:]):
        if v1 in store['releases']:
            continue
        changed = [p for p in git('diff', '--name-only', c0, c1, '--', '*.html').decode().splitlines()]
        old, new = blobs(c0, changed), blobs(c1, changed)
        store['releases'][v1] = {'against': v0, 'pages': compare(old, new, (v0, v1))}
        print(f'v{v1}: {len(store["releases"][v1]["pages"])} pages')
    save(store)


def for_build(version, written):
    """At a release's own build: the entry for version against the last release commit, if version has no commit yet.
    written: {path: html bytes} of every page this build wrote. Returns the store, changed or not."""
    store = load()
    try:
        rels = releases()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return store
    if not rels or any(v == version for v, _ in rels):
        return store
    v0, c0 = rels[-1]
    store['releases'][version] = {'against': v0, 'pages': compare(blobs(c0, sorted(written)), written, (v0, version))}
    save(store)
    return store


if __name__ == '__main__':
    if sys.argv[1:] == ['--all']:
        fill_all()
    else:
        sys.exit(__doc__)
