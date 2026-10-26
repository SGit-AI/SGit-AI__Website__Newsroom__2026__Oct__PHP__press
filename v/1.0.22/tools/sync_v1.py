#!/usr/bin/env python3
"""The press's sources, both ways with v1, while v1 still builds the pages (step A of the split).

    python3 tools/sync_v1.py import --from ../sgit-ai__website__newsroom__2026__oct__php   # v1 -> here, never over a change made here
    python3 tools/sync_v1.py export --into ../sgit-ai__website__newsroom__2026__oct__php   # here -> v1, what changed here since the last import

What the press holds of v1's sources: `assets/` (every script, stylesheet, image and component; published under
/v/<version>/assets/), `build/` (v1's admin/build/: the build, the gate, the exporters), `rules/` (the newsroom's rules
that every session reads: admin/security/, CLAUDE.md, AGENTS.md, SECURITY.md, .claude/) and `vault-app/`. The rule:
**what is written here wins.** sources.json keeps the sha256 of every file the last import wrote; a file whose sha256
differs was written here since, so the import leaves it alone and the export carries it into v1, where its gate, build
and release take it to the pages. A file v1's build itself writes (admin/build/outputs.txt: the line's config and copy,
outputs.txt) is never exported: the import brings it back. assets.json records the v1 commit the assets match.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RECORD = os.path.join(ROOT, 'sources.json')
# here -> v1
SOURCES = {'assets/': 'assets/', 'build/': 'admin/build/', 'rules/security/': 'admin/security/', 'rules/claude/': '.claude/',
           'rules/CLAUDE.md': 'CLAUDE.md', 'rules/AGENTS.md': 'AGENTS.md', 'rules/SECURITY.md': 'SECURITY.md', 'vault-app/': 'vault-app/'}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def git(v1, *a):
    return subprocess.run(['git', '-C', v1, *a], capture_output=True, text=True, check=True).stdout.strip()


def files_under(top):
    out = []
    for d, dirs, fs in os.walk(top):
        dirs.sort()
        for f in sorted(fs):
            out.append(os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/'))
    return out


def here_files():
    out = []
    for here in SOURCES:
        p = os.path.join(ROOT, here.rstrip('/'))
        if here.endswith('/'):
            out += files_under(p) if os.path.isdir(p) else []
        elif os.path.exists(p):
            out.append(here)
    return out


def v1_of(here_rel):
    for h, t in SOURCES.items():
        if h.endswith('/') and here_rel.startswith(h):
            return t + here_rel[len(h):]
        if here_rel == h:
            return t
    return None


def record():
    return json.load(open(RECORD, encoding='utf-8')) if os.path.exists(RECORD) else {}


def changed_here(rec):
    known = rec.get('files', {})
    if not known:   # no record yet (the first import): nothing counts as written here
        return []
    return [p for p in here_files() if known.get(p) != sha(os.path.join(ROOT, p))]


def do_import(v1):
    tracked = set(git(v1, 'ls-files', *[t.rstrip('/') for t in SOURCES.values()]).split('\n'))
    if git(v1, 'status', '--porcelain', '--', *[t.rstrip('/') for t in SOURCES.values()]):
        sys.exit('import: the v1 clone has uncommitted changes under the sources; import from a released commit')
    rec = record(); keep = set(changed_here(rec)); kept, wrote = [], {}
    for here, there in SOURCES.items():
        for t in sorted(tracked):
            if (there.endswith('/') and t.startswith(there)) or t == there:
                dst_rel = here + t[len(there):] if there.endswith('/') else here
                dst = os.path.join(ROOT, dst_rel)
                if dst_rel in keep:
                    kept.append(dst_rel); wrote[dst_rel] = sha(dst); continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(v1, t), dst); wrote[dst_rel] = sha(dst)
    gone = 0
    for p, h in rec.get('files', {}).items():
        q = os.path.join(ROOT, p)
        if p not in wrote and os.path.exists(q) and sha(q) == h:
            os.remove(q); gone += 1
    for p in here_files():
        if p not in wrote:
            wrote[p] = sha(os.path.join(ROOT, p))
    commit = git(v1, 'rev-parse', 'HEAD'); version = open(os.path.join(v1, 'VERSION'), encoding='utf-8').read().strip()
    with open(RECORD, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'from': {'repository': 'SGit-AI/sgit-ai__website__newsroom__2026__oct__php', 'commit': commit, 'site_version': version},
                   'sources': SOURCES, 'kept': sorted(kept), 'files': dict(sorted(wrote.items()))}, f, indent=1, ensure_ascii=False); f.write('\n')
    with open(os.path.join(ROOT, 'assets.json'), 'w', encoding='utf-8', newline='\n') as f:   # what the partition checks the press against
        json.dump({'from': {'repository': 'SGit-AI/sgit-ai__website__newsroom__2026__oct__php', 'commit': commit, 'site_version': version},
                   'files': sum(1 for p in wrote if p.startswith('assets/'))}, f, indent=1); f.write('\n')
    print(f'imported {len(wrote)} source file(s) from v1 at {commit[:12]} (site v{version}); {len(kept)} written here since kept (export them), {gone} gone')
    for p in kept[:20]:
        print(f'  kept: {p}')


def do_export(v1):
    rec = record()
    if not rec.get('files'):
        sys.exit('export: no import record yet; import first')
    built = set(open(os.path.join(v1, 'admin', 'build', 'outputs.txt'), encoding='utf-8').read().split()) | {'admin/build/outputs.txt'}
    out, derived = [], []
    for p in changed_here(rec):
        t = v1_of(p)
        if t in built:
            derived.append(p); continue
        dst = os.path.join(v1, t); os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, p), dst); out.append(t)
    print(f'exported to v1: {len(out)} file(s)' + ('; release v1, then import again' if out else ''))
    for t in out[:20]:
        print(f'  {t}')
    for p in derived:
        print(f'  not exported, v1 builds it: {p}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=['import', 'export'])
    ap.add_argument('--from', dest='src'); ap.add_argument('--into', dest='dst')
    a = ap.parse_args()
    if a.what == 'import':
        if not a.src: sys.exit('import needs --from')
        do_import(os.path.abspath(a.src))
    else:
        if not a.dst: sys.exit('export needs --into')
        do_export(os.path.abspath(a.dst))


if __name__ == '__main__':
    main()
