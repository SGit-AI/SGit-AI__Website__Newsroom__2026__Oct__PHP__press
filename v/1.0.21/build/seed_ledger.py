#!/usr/bin/env python3
"""One-off: rebuild data/sections.json from the releases in git, so that every section's history starts where the site did.

For each release commit, oldest first, read the markdown twin of every versioned page and briefing and the facts in
data/claims.json, and record them in the ledger as reconstructed versions. Uses the build's own normalisation, so a
section that did not change between releases gets no new version. Run from anywhere: python3 admin/build/seed_ledger.py
"""
import importlib.util, json, os, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RELEASE_COMMITS = [('0.1.0', '3a1e5a3'), ('0.2.0', '050b8a0'), ('0.2.1', 'a1ac432'), ('0.2.2', 'f545cc9'), ('0.3.0', '1755f2e'), ('0.3.1', 'dbb0dcc')]

spec = importlib.util.spec_from_file_location('build', os.path.join(ROOT, 'admin', 'build', 'build.py'))
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
b.LEDGER['sections'] = b.OrderedDict()

def show(commit, path):
    r = subprocess.run(['git', '-C', ROOT, 'show', f'{commit}:{path}'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

dates = {v['version']: v['date'] for v in b.D['versions']['versions']}
for ver, commit in RELEASE_COMMITS:
    paths = list(b.PAGE_VERSIONED) + [f'briefings/{a["id"]}/index.html' for a in b.D['roles']['audiences']]
    for path in paths:
        md = show(commit, b.md_path(path))
        if md is None:
            continue
        if path.startswith('briefings/'):
            a = b.AUD.get(path.split('/')[1])
            b.ledger(b.section_id(path), f'Briefing: {a["name"]}', 'briefing', path, b.briefing_norm(md), scope=path.split('/')[1], site=ver, date=dates[ver], reconstructed=True)
        else:
            b.ledger(b.section_id(path), b.nav_title(path), 'page', path, b.norm_md(md), site=ver, date=dates[ver], reconstructed=True)
    claims = show(commit, 'data/claims.json')
    for c in json.loads(claims) if claims else []:
        b.ledger('fact-' + c['id'], c['claim'][:90], 'fact', f'facts/{c["id"]}/index.html', b.fact_text(c), scope='fact', site=ver, date=dates[ver], reconstructed=True)
b.save_ledger()
n = len(b.LEDGER['sections']); v = sum(len(s['versions']) for s in b.LEDGER['sections'].values())
print(f'seeded {n} sections, {v} versions from {len(RELEASE_COMMITS)} releases')
