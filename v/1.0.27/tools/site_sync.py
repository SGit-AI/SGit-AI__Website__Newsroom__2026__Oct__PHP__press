#!/usr/bin/env python3
"""A site's sources, both ways with v1, while v1 still builds the pages (installed by the press as tools/pages_sync.py).

    python3 tools/pages_sync.py import --from ../sgit-ai__website__newsroom__2026__oct__php   # v1 -> here, never over a change made here
    python3 tools/pages_sync.py export --into ../sgit-ai__website__newsroom__2026__oct__php   # here -> v1, what changed here since the last import

press.json 'sources' maps each folder of this repository's own sources to its v1 path (from sites.json): the site's
`content/` is v1's `admin/content/articles/`, and so on. The rule: **what is written here wins.** sources.json keeps
the sha256 of every file the last import wrote; a file whose sha256 differs was written here since, so the import
leaves it alone and the export carries it into v1, where its gate, build and release take it to the pages. A file not in
the record is new here: kept, exported. After v1 releases, the next import records the same bytes, and the two agree.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RECORD = os.path.join(ROOT, 'sources.json')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def files_under(top):
    out = []
    for d, dirs, fs in os.walk(top):
        dirs.sort()
        for f in sorted(fs):
            out.append(os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/'))
    return out


def sources():
    meta = json.load(open(os.path.join(ROOT, 'press.json'), encoding='utf-8'))
    return meta.get('sources') or {}


def record():
    return json.load(open(RECORD, encoding='utf-8')) if os.path.exists(RECORD) else {}


def changed_here(rec, src):
    known = rec.get('files', {})
    if not known:   # no record yet (the first import): nothing counts as written here
        return []
    out = []
    for here in src:
        top = os.path.join(ROOT, here.rstrip('/'))
        if not os.path.isdir(top):
            continue
        for p in files_under(top):
            if known.get(p) != sha(os.path.join(ROOT, p)):
                out.append(p)
    return out


def do_import(v1):
    src = sources()
    if not src:
        print('import: this site has no sources of its own (press.json "sources"); nothing to do'); return
    v1paths = [s.rstrip('/') for s in src.values()]
    if subprocess.run(['git', '-C', v1, 'status', '--porcelain', '--', *v1paths], capture_output=True, text=True).stdout.strip():
        sys.exit('import: the v1 clone has uncommitted changes under the sources; import from a released commit')
    rec = record(); keep = set(changed_here(rec, src)); kept, wrote = [], {}
    for here, there in src.items():
        top = os.path.join(v1, there.rstrip('/'))
        if not os.path.isdir(top):
            sys.exit(f'import: {there} is not in v1')
        for d, dirs, fs in os.walk(top):
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), top).replace(os.sep, '/')
                dst_rel = here + rel; dst = os.path.join(ROOT, dst_rel)
                if dst_rel in keep:
                    kept.append(dst_rel); wrote[dst_rel] = sha(dst); continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(d, f), dst); wrote[dst_rel] = sha(dst)
    gone = 0
    for p, h in rec.get('files', {}).items():
        q = os.path.join(ROOT, p)
        if p not in wrote and os.path.exists(q) and sha(q) == h:
            os.remove(q); gone += 1
    for here in src:                                  # written here, never imported: its own
        top = os.path.join(ROOT, here.rstrip('/'))
        for p in (files_under(top) if os.path.isdir(top) else []):
            if p not in wrote:
                wrote[p] = sha(os.path.join(ROOT, p))
    commit = subprocess.run(['git', '-C', v1, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    with open(RECORD, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'from': {'commit': commit, 'site_version': open(os.path.join(v1, 'VERSION'), encoding='utf-8').read().strip()},
                   'sources': src, 'kept': sorted(kept), 'files': dict(sorted(wrote.items()))}, f, indent=1, ensure_ascii=False); f.write('\n')
    print(f'imported {len(wrote)} source file(s) from v1 at {commit[:12]}; {len(kept)} written here since kept (export them), {gone} gone')
    for p in kept[:20]:
        print(f'  kept: {p}')


def do_export(v1):
    src = sources(); rec = record()
    if src and not rec.get('files'):
        sys.exit('export: no import record yet; import first')
    out = []
    for p in changed_here(rec, src):
        here = next(h for h in src if p.startswith(h))
        dst = os.path.join(v1, src[here] + p[len(here):]); os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, p), dst); out.append(src[here] + p[len(here):])
    print(f'exported to v1: {len(out)} file(s)' + ('; release v1, then import again' if out else ''))
    for t in out[:20]:
        print(f'  {t}')


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
