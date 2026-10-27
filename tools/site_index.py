#!/usr/bin/env python3
"""The indexes a site's deploy writes beside its pages, never committed: what the live views read to find an item newer
than the site's last build (the brief on centers of gravity, 27 October 2026). Installed in every site by the press
(tools/partition.py) as tools/pages_index.py; run by the site's deploy on the release commit's tree:

    python3 tools/pages_index.py --into _site

content/index/articles.json   every article in content/articles/: its slug, its file and its front matter's title, dek,
                              role, origin, author and written date, newest first. assets/live/article.js finds a new
                              article's file here (articles/view/#<slug>, which a new article's address opens).

A site with no content/articles/ writes nothing. A file whose front matter is unreadable, or whose slug or name is not
plain, is left out and named on stderr: the site's gate is where an article is refused, not its deploy.
"""
import argparse, json, os, re, sys

FIELDS = ('title', 'dek', 'role', 'origin', 'author', 'written')


def front(path):
    m = re.match(r'^---\n(.*?)\n---\n', open(path, encoding='utf-8').read().replace('\r\n', '\n'), flags=re.S)
    if not m:
        return None
    return {k: v for k, v in (re.match(r'^(\w+):\s*(.*)$', l).groups() for l in m.group(1).splitlines() if re.match(r'^\w+:', l))}


def articles(root):
    d = os.path.join(root, 'content', 'articles')
    out = []
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fn.endswith('.md'):
            continue
        meta = front(os.path.join(d, fn)) if re.fullmatch(r'[0-9a-z_.-]+\.md', fn) else None
        if not meta or not re.fullmatch(r'[0-9a-z][0-9a-z-]*', meta.get('slug', '')) or not meta.get('title'):
            print(f'index: left out content/articles/{fn}: no plain name, slug or title', file=sys.stderr)
            continue
        out.append(dict({'slug': meta['slug'], 'file': fn}, **{k: meta.get(k, '') for k in FIELDS}))
    return sorted(out, key=lambda a: (a['written'], a['file']), reverse=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--into', required=True, help='the served tree (the deploy\'s _site)')
    ap.add_argument('--root', default='.', help='the site\'s checkout (default: here)')
    a = ap.parse_args()
    arts = articles(a.root)
    if not arts:
        return
    os.makedirs(os.path.join(a.into, 'content', 'index'), exist_ok=True)
    with open(os.path.join(a.into, 'content', 'index', 'articles.json'), 'w', encoding='utf-8') as f:
        json.dump({'about': 'Every article in content/articles/, newest first; written by the deploy (tools/pages_index.py), never committed.',
                   'articles': arts}, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(f'index: {len(arts)} articles')


if __name__ == '__main__':
    main()
