#!/usr/bin/env python3
"""Export the public metadata of the evidence vault into data/.

Usage: admin/build/export_vault.py --from <path to a clone of the evidence vault>

What it writes (all deterministic, sorted, no timestamps of its own):
  data/sources.json   every sources/<slug>/source.json, plus the sha256 of every file in every
                      capture folder and every raw/SHA256SUMS line. The captures themselves are
                      never copied: they are third-party pages held privately for the record.
  data/vault.json     the vault's HEAD commit, the count of sources, captures and hashed files,
                      and the agents that wrote to it.
  data/software.json  the NCSC-NL php2shell software inventory as parsed in the vault
                      (sources/ncsc-nl-php2shell/raw/software-list-<commit>.json), summarised by
                      status, with every row kept.
  data/vault-claims.json, data/vault-timeline.json
                      every claims/<agent>.json and timeline/<agent>.json, merged, each row
                      carrying the agent that wrote it.
"""
import argparse, hashlib, json, os, re, subprocess, sys

def read_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def sha256_of(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def vault_head(vault):
    try:
        out = subprocess.run(['sgit', 'history', 'log', '--oneline'], cwd=vault, capture_output=True, text=True, timeout=60).stdout
        m = re.search(r'^\s*([0-9a-f]{12})\s+\(HEAD\)\s+(.*)$', out, re.M)
        if m:
            return {'commit': m.group(1), 'subject': m.group(2).strip(), 'commits': len([l for l in out.splitlines() if l.strip()])}
    except Exception:
        pass
    return {'commit': None, 'subject': None, 'commits': None}

def export_sources(vault):
    rows, agents, n_caps, n_hashed = [], set(), 0, 0
    sdir = os.path.join(vault, 'sources')
    for slug in sorted(os.listdir(sdir)):
        d = os.path.join(sdir, slug)
        sj = os.path.join(d, 'source.json')
        if not os.path.isdir(d) or not os.path.exists(sj):
            continue
        row = read_json(sj)
        row['slug'] = slug
        agents.add(row.get('added_by') or '')
        caps = []
        cdir = os.path.join(d, 'captures')
        if os.path.isdir(cdir):
            for stamp in sorted(os.listdir(cdir)):
                cd = os.path.join(cdir, stamp)
                if not os.path.isdir(cd):
                    continue
                cap = {'stamp': stamp, 'files': {}}
                prov = os.path.join(cd, 'provenance.json')
                if os.path.exists(prov):
                    pj = read_json(prov)
                    for k in ('started_utc', 'status', 'final_url', 'error'):
                        if k in pj:
                            cap[k] = pj[k]
                for fn in sorted(os.listdir(cd)):
                    fp = os.path.join(cd, fn)
                    if os.path.isfile(fp):
                        cap['files'][fn] = {'sha256': sha256_of(fp), 'bytes': os.path.getsize(fp)}
                        n_hashed += 1
                caps.append(cap)
                n_caps += 1
        row['captures'] = caps
        raw = {}
        rdir = os.path.join(d, 'raw')
        sums = os.path.join(rdir, 'SHA256SUMS')
        if os.path.exists(sums):
            with open(sums, encoding='utf-8', errors='replace') as f:
                for line in f:
                    m = re.match(r'^([0-9a-f]{64})\s+\*?(.+)$', line.strip())
                    if m:
                        raw[m.group(2)] = m.group(1)
                        n_hashed += 1
        elif os.path.isdir(rdir):
            for root, _, files in os.walk(rdir):
                for fn in sorted(files):
                    fp = os.path.join(root, fn)
                    raw[os.path.relpath(fp, rdir)] = sha256_of(fp)
                    n_hashed += 1
        row['raw_sha256'] = dict(sorted(raw.items()))
        row['has_notes'] = os.path.exists(os.path.join(d, 'notes.md'))
        if row['has_notes']:
            with open(os.path.join(d, 'notes.md'), encoding='utf-8', errors='replace') as f:
                row['notes_md'] = f.read()
        rows.append(row)
    return rows, sorted(a for a in agents if a), n_caps, n_hashed

def export_per_agent(vault, sub):
    out = []
    d = os.path.join(vault, sub)
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.json'):
            continue
        agent = fn[:-5]
        for row in read_json(os.path.join(d, fn)):
            row = dict(row)
            row.setdefault('agent', agent)
            out.append(row)
    return out

def export_software(vault):
    rdir = os.path.join(vault, 'sources', 'ncsc-nl-php2shell', 'raw')
    if not os.path.isdir(rdir):
        return None
    cands = sorted(fn for fn in os.listdir(rdir) if fn.startswith('software-list-') and fn.endswith('.json'))
    if not cands:
        return None
    j = read_json(os.path.join(rdir, cands[-1]))
    rows = sorted(j.get('rows', []), key=lambda r: ((r.get('supplier') or '').lower(), (r.get('product') or '').lower()))
    def count(key):
        c = {}
        for r in rows:
            c[r.get(key) or 'none'] = c.get(r.get(key) or 'none', 0) + 1
        return dict(sorted(c.items()))
    return {'source': j.get('source'), 'commit': j.get('commit'), 'licence': j.get('licence'),
            'parsed_from': j.get('parsed_from'), 'file': cands[-1], 'count': len(rows),
            'by_status_109618': count('status_109618'), 'by_status_109619': count('status_109619'), 'rows': rows}

def write(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write('\n')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='vault', required=True)
    ap.add_argument('--out', default=os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
    a = ap.parse_args()
    vault, out = os.path.abspath(a.vault), os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    rows, agents, n_caps, n_hashed = export_sources(vault)
    head = vault_head(vault)
    stamps = sorted(c['stamp'] for r in rows for c in r['captures'] if c.get('stamp'))
    latest = stamps[-1] if stamps else None
    latest_iso = f'{latest[0:4]}-{latest[4:6]}-{latest[6:8]}T{latest[9:11]}:{latest[11:13]}Z' if latest else None
    write(os.path.join(out, 'sources.json'), rows)
    write(os.path.join(out, 'vault.json'), {
        'head': head, 'sources': len(rows), 'captures': n_caps, 'hashed_files': n_hashed,
        'primary': sum(1 for r in rows if r.get('primary')),
        'blocked': sum(1 for r in rows if r.get('status') in ('blocked', 'failed')),
        'agents': agents, 'opened': '2026-10-22T08:03Z', 'latest_capture': latest_iso,
        'note': 'The captures are third-party pages kept privately for the record and are not published. Only their hashes are.'})
    sw = export_software(vault)
    if sw:
        write(os.path.join(out, 'software.json'), sw)
    write(os.path.join(out, 'vault-claims.json'), export_per_agent(vault, 'claims'))
    write(os.path.join(out, 'vault-timeline.json'), export_per_agent(vault, 'timeline'))
    print(f'exported {len(rows)} sources, {n_caps} captures, {n_hashed} hashed files; vault HEAD {head["commit"]}')

if __name__ == '__main__':
    main()
