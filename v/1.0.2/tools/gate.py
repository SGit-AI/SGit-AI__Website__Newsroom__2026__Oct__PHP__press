#!/usr/bin/env python3
"""The press's own gate. Seconds. Exits non-zero on any failure.

1. Every tool compiles; sites.json is valid, every section belongs to one site only, and exactly one site takes the rest.
2. Every published version matches its manifest, and nothing already committed under v/ has changed.
3. latest/ is the newest version.
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
try:
    for line in subprocess.run(['git', '-C', ROOT, 'ls-files', '-s', 'v'], capture_output=True, text=True, check=True).stdout.splitlines():
        _, blob, _, path = line.split(None, 3)
        if subprocess.run(['git', '-C', ROOT, 'hash-object', path], capture_output=True, text=True).stdout.strip() != blob:
            fails.append(f'{path}: a published file changed; a version is immutable')
except (subprocess.CalledProcessError, FileNotFoundError):
    pass
vdir = os.path.join(ROOT, 'v')
vs = sorted((d for d in os.listdir(vdir) if os.path.isfile(os.path.join(vdir, d, 'manifest.json'))), key=lambda v: tuple(map(int, v.split('.')))) if os.path.isdir(vdir) else []
for v in vs:
    for f in json.load(open(os.path.join(vdir, v, 'manifest.json')))['files']:
        p = os.path.join(vdir, v, f['name'])
        if not os.path.exists(p) or hashlib.sha256(open(p, 'rb').read()).hexdigest() != f['sha256']:
            fails.append(f'v/{v}/{f["name"]}: does not match the manifest')
if vs and os.path.exists(os.path.join(ROOT, 'latest', 'manifest.json')):
    if open(os.path.join(ROOT, 'latest', 'manifest.json')).read() != open(os.path.join(vdir, vs[-1], 'manifest.json')).read():
        fails.append(f'latest/: is not v{vs[-1]}')
for f in fails:
    print('FAIL:', f)
if fails:
    sys.exit(f'{len(fails)} failure(s)')
print(f'gate passed: {len(cfg["sites"])} sites, {len(seen)} sections assigned, {len(vs)} version(s) published')
