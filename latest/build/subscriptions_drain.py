#!/usr/bin/env python3
"""Drain the subscriptions lane into the subscriptions vault.

Run by whoever holds the subscriptions vault (wgeiqabu): a clone at --vault with .sg_vault/local/lane.json and
.sg_vault/local/pki-passphrase, and the key pair in ~/.sg-send/keys/ (identity/private/ in the vault holds a
copy). Lists the lane with the enum key, fetches and decrypts each request (the same calls as
telemetry_drain.py), appends them to requests/<date>.jsonl, marks them processed, and updates subscribers.json:
one row per address with its latest request and status (requested, left; confirmed is set by the agent at
agent@diniscruz.ai when the address answers). Nothing from here is ever copied to the site, which is public.
"""
import argparse, datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telemetry_drain import post, decrypt
from newsroom_paths import data_file   # since the split: the data repository's files/, not ../../data/

# The lane's append token is public, so a request can come from anyone, written by hand rather than by the form.
# Everything in it is untrusted: only the fields the form sends survive, each checked against the site's own lists,
# and the note is kept as data for a person, marked untrusted so no agent reads it as instructions.
SITE = json.load(open(data_file('subscriptions.json')))
ZONES = {z[0] for z in SITE.get('zones', [])}
CADENCES = {c[0] for c in SITE.get('cadences', [])}
EMAIL = re.compile(r'[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+')
CTRL = re.compile(r'[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\U000e0000-\U000e007f]')
MAX_PER_ADDRESS = 3   # more requests than this for one address in one drain: held, so nobody is mailed on a flood

def clean(q):
    """The request as the form would have sent it, or a reason it is rejected."""
    email = q.get('email')
    if not isinstance(email, str) or len(email) > 254 or not EMAIL.fullmatch(email.strip()):
        return None, 'email is not a plain address'
    kind = q.get('kind') or 'subscribe'
    if kind not in ('subscribe', 'unsubscribe'): return None, 'unknown kind'
    out = {'email': email.strip().lower(), 'kind': kind, 'at': str(q.get('at') or '')[:40]}
    if kind == 'subscribe':
        zones = q.get('zones') or []
        if not isinstance(zones, list) or not zones or not set(zones) <= ZONES: return None, 'zones not on the site\'s list'
        if q.get('cadence') not in CADENCES: return None, 'cadence not on the site\'s list'
        out.update({'zones': sorted(set(zones)), 'cadence': q['cadence']})
    note = q.get('note')
    if isinstance(note, str) and note.strip():
        out['note_untrusted'] = CTRL.sub(' ', note)[:500]
    return out, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vault', required=True); ap.add_argument('--fingerprint', default='sha256:fccac5cde1503b62')
    ap.add_argument('--keep-pending', action='store_true')
    a = ap.parse_args()
    V = os.path.abspath(a.vault)
    lane = json.load(open(os.path.join(V, '.sg_vault', 'local', 'lane.json')))
    passphrase = open(os.path.join(V, '.sg_vault', 'local', 'pki-passphrase')).read().strip()
    H = {'x-sgraph-vault-enum-key': lane['enum_key']}
    base = f"{lane['endpoint']}/api/vault/append"
    today = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    os.makedirs(os.path.join(V, 'requests'), exist_ok=True)
    got, after, rows = [], None, []
    while True:
        body = {'include_content': False}
        if after: body['after_file_id'] = after
        r = post(f"{base}/list/{lane['vault_id']}", body, H)
        entries = r.get('entries', [])
        got += entries
        if not r.get('truncated') or not entries: break
        after = entries[-1]['file_id']
    for i in range(0, len(got), 50):
        batch = got[i:i + 50]
        f = post(f"{base}/fetch/{lane['vault_id']}", {'inbox': lane['append_token'], 'file_ids': [e['file_id'] for e in batch]}, H)
        files = f.get('files') or f.get('entries') or []
        for item in files:
            fid = item.get('file_id') or item.get('id'); content = item.get('content') or item.get('payload')
            if not content: continue
            try:
                req = json.loads(decrypt(content, a.fingerprint, passphrase))
            except Exception as e:
                req = {'v': 0, 'undecryptable': True, 'error': str(e)[:120]}
            req['_file'] = fid
            rows.append(req)
        if not a.keep_pending and files:
            post(f"{base}/mark-processed/{lane['vault_id']}", {'inbox': lane['append_token'], 'file_ids': [x.get('file_id') or x.get('id') for x in files]}, H)
    with open(os.path.join(V, 'requests', f'{today}.jsonl'), 'a', encoding='utf-8') as f:
        for q in rows: f.write(json.dumps(q, ensure_ascii=False, sort_keys=True) + '\n')
    sp = os.path.join(V, 'subscribers.json')
    subs = json.load(open(sp)) if os.path.exists(sp) else {'about': 'One row per address. status: requested (unconfirmed), confirmed (the address answered), left.', 'subscribers': {}}
    ok, per = [], {}
    for q in rows:
        c, why = clean(q) if not q.get('undecryptable') else (None, 'undecryptable')
        if c is None:
            q['_rejected'] = why
            continue
        per[c['email']] = per.get(c['email'], 0) + 1
        ok.append(c)
    for q in sorted(ok, key=lambda x: x.get('at') or ''):
        e = q['email']
        row = subs['subscribers'].get(e, {'status': 'requested', 'first': q.get('at')})
        if q.get('kind') == 'unsubscribe':
            row['status'] = 'left'
        else:
            row.update({'zones': q.get('zones'), 'cadence': q.get('cadence')})
            if row.get('status') == 'left': row['status'] = 'requested'
        row['last'] = q.get('at'); row['requests'] = row.get('requests', 0) + 1
        if per[e] > MAX_PER_ADDRESS:
            row['hold'] = f'{per[e]} requests in one drain: held for a person before anything is sent'
        subs['subscribers'][e] = row
    json.dump(subs, open(sp, 'w'), indent=1, ensure_ascii=False, sort_keys=True)
    c = {}
    for r in subs['subscribers'].values(): c[r['status']] = c.get(r['status'], 0) + 1
    print(f'pending {len(got)}, drained {len(rows)}; addresses by status: {c}')

if __name__ == '__main__':
    main()
