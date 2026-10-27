#!/usr/bin/env python3
"""The press's own gate. Seconds. Exits non-zero on any failure.

1. Every tool compiles; sites.json is valid, every section belongs to one site only, and exactly one site takes the rest.
2. The version CI will publish builds from this tree (tools/package.py's list: sites.json, the tools, assets/, build/,
   rules/, vault-app/), every file readable. CI owns the version: VERSION and the tags are written by CI after this gate,
   and every published version is served from its tag or from the last commit that held v/ (tools/package.py).
"""
import hashlib, json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
fails = []
for f in sorted(os.listdir(os.path.join(ROOT, 'tools'))):
    if f.endswith('.py'):
        try:
            compile(open(os.path.join(ROOT, 'tools', f), encoding='utf-8').read(), f'tools/{f}', 'exec')
        except SyntaxError as e:
            fails.append(f'tools/{f}: {e}')
cfg = json.load(open(os.path.join(ROOT, 'sites.json'), encoding='utf-8'))
seen, rest = {}, [n for n, c in cfg['sites'].items() if c['sections'] == '*']
if len(rest) != 1:
    fails.append(f'sites.json: {len(rest)} sites take the remaining sections; exactly one must')
for n, c in cfg['sites'].items():
    for k in ('repository', 'home', 'serve_at', 'what', 'sections'):
        if k not in c:
            fails.append(f'sites.json: {n} has no "{k}"')
    if c['sections'] != '*':
        for s in c['sections']:
            if s in seen:
                fails.append(f'sites.json: section "{s}" belongs to {seen[s]} and {n}')
            seen[s] = n
# 2. what CI will publish at the tag it writes after this gate
import importlib.util
_spec = importlib.util.spec_from_file_location('package', os.path.join(ROOT, 'tools', 'package.py'))
_pkg = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_pkg)
nxt = _pkg.published(ROOT)
for f in nxt:
    if not os.path.isfile(os.path.join(ROOT, f)):
        fails.append(f'{f}: listed for the next version but not a file')
if 'sites.json' not in nxt or not any(f.startswith('assets/') for f in nxt):
    fails.append('the next version would hold no sites.json or no assets')
# every HTML page the press serves (a deck, a figure page under assets/) carries a Content-Security-Policy, as every page
# of the sites does; refused here, at the writer's own release, not later in the build every other writer waits on
import re as _re
for d, dirs, fs in os.walk(os.path.join(ROOT, 'assets')):
    for f in fs:
        if f.endswith(('.html', '.htm')):
            p = os.path.join(d, f)
            if not _re.search(r'<meta http-equiv="Content-Security-Policy" content="', open(p, encoding='utf-8', errors='replace').read()):
                fails.append(f'{os.path.relpath(p, ROOT)}: no Content-Security-Policy (add <meta http-equiv="Content-Security-Policy" ...> after <meta charset>; a self-contained page: default-src \'none\'; style-src \'unsafe-inline\'; img-src \'self\' data:)')

for f in fails:
    print('FAIL:', f)
if fails:
    sys.exit(f'{len(fails)} failure(s)')
print(f'gate passed: {len(cfg["sites"])} sites, {len(seen)} sections assigned; the next version holds {len(nxt)} files (CI numbers it)')
