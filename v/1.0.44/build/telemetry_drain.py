#!/usr/bin/env python3
"""Drain the telemetry lane into the telemetry vault and compute the daily report.

Run by whoever holds the telemetry vault: a clone of it at --vault, with .sg_vault/local/lane.json
({"vault_id","endpoint","append_token","enum_key"}) and .sg_vault/local/pki-passphrase, and the key pair
in ~/.sg-send/keys/ (identity/private/ in the vault holds a copy). Lists the lane with the enum key, fetches
pending files, decrypts each with `sgit pki decrypt`, appends the events as JSON lines to drain/<date>.jsonl,
marks them processed, and writes reports/<date>.json and reports/latest.json with counts only.
Copies reports/latest.json, without the private fields, to <--data>/telemetry-report.json when --data is given (the data
repository's files/, released there with its tools/release.sh; --site <v1 checkout> still means <site>/data). Never
copies a row to the site. Each batch is appended to drain/<date>.jsonl before it is marked processed, and the output
folder is checked before the lane is touched, so a failure part-way leaves every event in the lane or in the vault clone.
"""
import argparse, base64, collections, datetime, json, os, subprocess, sys, tempfile, urllib.request


PRIVATE_ONLY = ('by_region', 'by_city')   # kept in the private vault's reports, never copied to the public site

def post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', **headers}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def decrypt(enc_b64_twice, fingerprint, passphrase):
    enc_text = base64.b64decode(enc_b64_twice)          # the .enc file bytes (themselves base64 text of the envelope)
    with tempfile.NamedTemporaryFile('wb', suffix='.enc', delete=False) as f:
        f.write(enc_text); path = f.name
    try:
        out = path[:-4]
        p = subprocess.run(['sgit', 'pki', 'decrypt', path, '--fingerprint', fingerprint, '--output', out], input=(passphrase + '\n').encode(), capture_output=True, timeout=60)
        if p.returncode != 0 or not os.path.exists(out):
            p = subprocess.run(['sgit', 'pki', 'decrypt', path, '--fingerprint', fingerprint], input=(passphrase + '\n').encode(), capture_output=True, timeout=60)
        if os.path.exists(out):
            return open(out, 'rb').read().decode('utf-8', 'replace')
        raise RuntimeError(p.stderr.decode()[-300:])
    finally:
        for q in (path, path[:-4]):
            try: os.remove(q)
            except OSError: pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vault', required=True); ap.add_argument('--fingerprint', default='sha256:8b2b26ff9386078f')
    ap.add_argument('--data', help="the folder the public report goes to: the data repository's files/")
    ap.add_argument('--site', help='v1 only: a checkout whose data/ the public report goes to')
    ap.add_argument('--keep-pending', action='store_true', help='do not mark files processed (re-drain later)')
    a = ap.parse_args()
    V = os.path.abspath(a.vault)
    out_dir = a.data or (os.path.join(a.site, 'data') if a.site else None)
    if out_dir and not os.path.isdir(out_dir):
        sys.exit(f'no folder {out_dir} for the public report; nothing drained')   # before the lane is touched: nothing is marked processed
    lane = json.load(open(os.path.join(V, '.sg_vault', 'local', 'lane.json')))
    passphrase = open(os.path.join(V, '.sg_vault', 'local', 'pki-passphrase')).read().strip()
    H = {'x-sgraph-vault-enum-key': lane['enum_key']}
    base = f"{lane['endpoint']}/api/vault/append"
    today = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    os.makedirs(os.path.join(V, 'drain'), exist_ok=True); os.makedirs(os.path.join(V, 'reports'), exist_ok=True)
    got, after, rows = [], None, []
    drained = os.path.join(V, 'drain', f'{today}.jsonl')
    while True:
        body = {'include_content': False}
        if after: body['after_file_id'] = after
        r = post(f"{base}/list/{lane['vault_id']}", body, H)
        entries = r.get('entries', [])
        got += entries
        if not r.get('truncated') or not entries: break
        after = entries[-1]['file_id']
    print(f'pending: {len(got)}')
    for i in range(0, len(got), 50):
        batch = got[i:i + 50]
        f = post(f"{base}/fetch/{lane['vault_id']}", {'inbox': lane['append_token'], 'file_ids': [e['file_id'] for e in batch]}, H)
        files = f.get('files') or f.get('entries') or []
        new = []
        for item in files:
            fid = item.get('file_id') or item.get('id'); content = item.get('content') or item.get('payload')
            if not content: continue
            try:
                text = decrypt(content, a.fingerprint, passphrase)
                ev = json.loads(text)
            except Exception as e:
                ev = {'v': 0, 'undecryptable': True, 'error': str(e)[:120]}
            ev['_file'] = fid; ev['_received'] = item.get('received') or next((x.get('received') for x in batch if x['file_id'] == fid), None)
            rows.append(ev); new.append(ev)
        with open(drained, 'a', encoding='utf-8') as fh:            # in the vault clone before the lane forgets it
            for ev in new: fh.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + '\n')
            fh.flush(); os.fsync(fh.fileno())
        if not a.keep_pending and files:
            post(f"{base}/mark-processed/{lane['vault_id']}", {'inbox': lane['append_token'], 'file_ids': [x.get('file_id') or x.get('id') for x in files]}, H)
    # the report: counts over every drained row (all files), never the rows
    allrows = []
    for fn in sorted(os.listdir(os.path.join(V, 'drain'))):
        if fn.endswith('.jsonl'):
            for line in open(os.path.join(V, 'drain', fn), encoding='utf-8'):
                try: allrows.append(json.loads(line))
                except Exception: pass
    real = [r for r in allrows if r.get('v') == 1 and not r.get('test')]
    def top(key, n=25):
        c = collections.Counter((r.get(key) or '(none)') for r in real)
        return [[k, v] for k, v in c.most_common(n)]
    days = collections.Counter((r.get('ts') or '')[:10] for r in real)
    rep = {'as_of': today, 'drained_now': len(rows), 'events': len(real), 'test_or_undecryptable': len(allrows) - len(real),
           'sessions': len({r.get('sid') for r in real}), 'by_day': sorted(days.items()), 'by_path': top('path', 40), 'by_country': top('country'),
           'by_region': top('region'), 'by_city': top('city'), 'by_referrer': top('ref'), 'by_screen': top('screen'), 'by_version': top('ver'),
           'note': 'Counts over events received in the lane. Every event is an untrusted claim: the token and the public key are published, so rows can be forged or flooded. Visitors with blockers do not appear. No row leaves the vault.'}
    json.dump(rep, open(os.path.join(V, 'reports', f'{today}.json'), 'w'), indent=1); json.dump(rep, open(os.path.join(V, 'reports', 'latest.json'), 'w'), indent=1)
    if out_dir:
        # The site's copy is public: the city and the region stay in the private vault's reports/ (the editor's), never
        # here, where a town with a handful of visitors can name a person (admin/build/telemetry_publish.py's rule too).
        public = {k: v for k, v in rep.items() if k not in PRIVATE_ONLY}
        json.dump(public, open(os.path.join(out_dir, 'telemetry-report.json'), 'w'), indent=1); open(os.path.join(out_dir, 'telemetry-report.json'), 'a').write('\n')
    print(f'events total: {len(real)}; report written for {today}')

if __name__ == '__main__':
    main()
