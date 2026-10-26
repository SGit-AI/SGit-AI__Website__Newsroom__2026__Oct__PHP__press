#!/usr/bin/env python3
"""Parity: does every page v1 builds read the same on the site that serves it now? (The plan, step 1.8.)

    python3 tools/parity.py --v1 ../sgit-ai__website__newsroom__2026__oct__php --sites ../sgit-ai__website__newsroom__2026__oct__php__{site,refs,updates,team}

For every HTML page in v1's build output (admin/build/outputs.txt): exactly one site owns it (the others redirect), and its
visible text there is v1's, word for word (an address of the newsroom's own shown as text may name another of its hosts);
its links may differ only in where they point (the press, the data API, another site, v1 on GitHub). It prints the counts and lists every page whose text differs, and exits 1 if any does or any page is
owned by no site or by two. No clock, no network.
"""
import argparse, html, json, os, re, sys

TAGS = re.compile(r'<(script|style)\b.*?</\1>|<!--.*?-->|<[^>]+>', re.S)
HEAD = re.compile(r'<head\b.*?</head>', re.S)


HOSTS = re.compile(r'https://(?:[a-z]+\.)?php\.oct\.2026\.newsroom\.sgit\.ai')   # an address shown as text moves with its page


def text_of(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    t = HEAD.sub('', t)
    return HOSTS.sub('https://<site>', re.sub(r'\s+', ' ', html.unescape(TAGS.sub(' ', t))).strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--v1', required=True)
    ap.add_argument('--sites', nargs='+', required=True)
    a = ap.parse_args()
    v1 = os.path.abspath(a.v1)
    outputs = [f for f in open(os.path.join(v1, 'admin', 'build', 'outputs.txt'), encoding='utf-8').read().split() if f.endswith('.html')]
    metas = {}
    for d in a.sites:
        m = json.load(open(os.path.join(d, 'press.json'), encoding='utf-8'))
        metas[m['site']] = (os.path.abspath(d), m)
    commits = {m['v1']['commit'] for _, m in metas.values()}
    if len(commits) != 1:
        sys.exit(f'parity: the sites are cut from different v1 commits: {sorted(c[:12] for c in commits)}')
    owners, differ, runtime = {}, [], 0
    for f in outputs:
        own = [s for s, (d, m) in metas.items() if f in m['pages_by_site'].get(s, [])]
        if not own:
            if all(f in m['files'] for _, m in metas.values()):
                runtime += 1; continue          # the 404 router: every site keeps its own
            owners[f] = []; continue
        owners[f] = own
        if len(own) != 1:
            continue
        d, m = metas[own[0]]
        if text_of(os.path.join(v1, f)) != text_of(os.path.join(d, f)):
            differ.append((own[0], f))
    none = [f for f, o in owners.items() if not o]
    twice = [f for f, o in owners.items() if len(o) > 1]
    by_site = {s: sum(1 for o in owners.values() if o == [s]) for s in metas}
    print(f'parity: {len(outputs)} pages in v1 at {next(iter(commits))[:12]}; owned once: {sum(1 for o in owners.values() if len(o) == 1)} '
          f'({", ".join(f"{s} {n}" for s, n in by_site.items())}); runtime on every site: {runtime}; owned by none: {len(none)}; by two: {len(twice)}')
    print(f'parity: text the same as v1: {sum(1 for o in owners.values() if len(o) == 1) - len(differ)}; different: {len(differ)}')
    for s, f in differ[:50]:
        print(f'  differs: {s}: {f}')
    for f in none[:20]:
        print(f'  no owner: {f}')
    for f in twice[:20]:
        print(f'  two owners: {f}')
    sys.exit(1 if differ or none or twice else 0)


if __name__ == '__main__':
    main()
