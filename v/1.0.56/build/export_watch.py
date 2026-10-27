#!/usr/bin/env python3
"""Export the source-watch vault's public shape into data/source-watch.json, for /vaults/source-watch/.

Usage: admin/build/export_watch.py --from <clone of the source-watch vault, 7r83qic5>

The vault is a pack vault, cloned with sgit-ai 0.24.0 or later by a session that holds its key; its read key is not
published until the vault UI opens pack vaults. This site copies none of its captures: no text, no
screenshot, no HTML. It writes counts, the vocabularies, the runs and the tips' headlines, each read from the
vault's own index and taxonomy files, with the vault head they were read at. Deterministic: the same vault head
gives the same file, byte for byte.
"""
import argparse, glob, json, os, re, subprocess, sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def load(v, p):
    with open(os.path.join(v, p), encoding='utf-8') as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='vault', required=True)
    a = ap.parse_args()
    v = os.path.abspath(a.vault)
    log = subprocess.run(['sgit', 'history', 'log'], cwd=v, capture_output=True, text=True).stdout
    commits = [m.groups() for m in re.finditer(r'^\s*([0-9a-f]{12})(?: \(HEAD\))?\s+(.*?)\s{2,}\+', log, re.M)]
    if not commits:
        sys.exit('no commits read from sgit history log; is this a vault clone?')
    counts = load(v, 'index/counts.json')
    pubs = [load(v, p) for p in sorted(glob.glob(os.path.join(v, 'sources/*/*/*/publisher.json')))]
    runs = []
    for p in sorted(glob.glob(os.path.join(v, 'runs/*/*/*/*/run.json'))):
        r = json.load(open(p, encoding='utf-8'))
        runs.append({k: r.get(k) for k in ('run', 'agent', 'started', 'finished', 'pages_due', 'pages_total', 'changed', 'access')})
    tips = []
    for p in sorted(glob.glob(os.path.join(v, 'tips/*/*.json'))):
        t = json.load(open(p, encoding='utf-8'))
        tips.append({'id': t['id'], 'received': t.get('received'), 'status': t.get('status'), 'says': t.get('says'),
                     'watched_as': t.get('watched_as', []), 'to_check': t.get('to_check', [])})
    snaps = [d for d in glob.glob(os.path.join(v, 'raw/*/*/*/*/*')) if os.path.isdir(d) and os.path.basename(d) != 'checks']
    verbs = load(v, 'taxonomy/verbs.json')
    world = load(v, 'index/world.json')
    out = {
        'about': 'The public shape of the source watch, exported by admin/build/export_watch.py. Counts and vocabularies only: no capture is copied.',
        'vault_id': '7r83qic5',  # a pack vault (sgit-ai 0.24.0 or later); its read key is not published yet
        'head': {'commit': commits[0][0], 'message': commits[0][1]},
        'commits': [{'commit': c, 'message': m} for c, m in commits],
        'pages': counts['pages'], 'publishers': counts['publishers'],
        'country': counts['country'], 'sector': counts['sector'], 'lang': counts['lang'], 'access': counts['access'],
        'tiers': dict(sorted(Counter(p.get('tier') for p in pubs).items())),
        'snapshots': len(snaps),
        'graphs': len(glob.glob(os.path.join(v, 'graph/*/*/*/*/*.json'))),
        'files': sum(1 for p in glob.glob(os.path.join(v, '**/*'), recursive=True) if os.path.isfile(p)),
        'world_graph': {'nodes': len(world['nodes']), 'edges': len(world['edges'])},
        'access_classes': load(v, 'taxonomy/access.json')['statuses'],
        'sectors': [{'id': s['id'], 'name': s['name']} for s in load(v, 'taxonomy/sectors.json')['sectors']],
        'altitudes': verbs.get('altitudes', {}),
        'verbs': len(verbs.get('verbs', [])),
        'runs': runs,
        'tips': tips,
        'tools': sorted(os.path.basename(p) for p in glob.glob(os.path.join(v, 'tools/*')) if os.path.isfile(p)),
    }
    p = os.path.join(ROOT, 'data', 'source-watch.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write('\n')
    print(f'wrote {os.path.relpath(p, ROOT)}: vault head {out["head"]["commit"]}, {out["pages"]} pages, {out["publishers"]} publishers, {out["snapshots"]} snapshots, {len(runs)} runs, {len(tips)} tips')


if __name__ == '__main__':
    main()
