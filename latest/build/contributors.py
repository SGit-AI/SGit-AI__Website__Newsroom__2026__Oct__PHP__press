#!/usr/bin/env python3
"""Checking what a contributor signed: the same canonical bytes the browser signs (assets/feedback/identity.js), and
`sgit pki verify` to check the signature. Kept by conductor@php.newsroom; the brief is
admin/content/briefs/2026-10-22__brief__feedback-keys-and-review.md.

A message carries its signer's public bundle; verify() checks that the bundle's signing key is the one its fingerprint
names, that `from` is that fingerprint, and that the signature over canon(message without sig) + "\\n" is good. That proves
which key wrote it. Whether that key belongs to a contributor is data/contributors.json's question (status()).
Standard library and the sgit CLI only.
"""
import base64, datetime, hashlib, json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newsroom_paths import data_file   # since the split: the data repository's files/, not ../../data/

def canon(v):
    """pki.sgit.ai's canonical JSON, as JavaScript writes it: keys sorted, no whitespace, non-ASCII left as it is."""
    if isinstance(v, float): raise ValueError('a signed message carries no non-integer numbers')
    if isinstance(v, list): return '[' + ','.join(canon(x) for x in v) + ']'
    if isinstance(v, dict): return '{' + ','.join(json.dumps(k, ensure_ascii=False) + ':' + canon(v[k]) for k in sorted(v)) + '}'
    return json.dumps(v, ensure_ascii=False)

def fingerprint(pem_text):
    """sgit's fingerprint of a public key: sha256: and the first 16 hex of the SHA-256 of its SPKI bytes."""
    body = ''.join(l for l in pem_text.strip().splitlines() if not l.startswith('-----'))
    return 'sha256:' + hashlib.sha256(base64.b64decode(body)).hexdigest()[:16]

def verify(msg, bundle=None):
    """(True, '') when the message is signed by the key in its own bundle (or the bundle given); (False, why) otherwise."""
    b, sig, frm = bundle or msg.get('bundle') or {}, msg.get('sig'), msg.get('from')
    if not sig or not frm: return False, 'unsigned'
    if not b.get('sign') or fingerprint(b['sign']) != b.get('signing_fingerprint') or frm != b.get('signing_fingerprint'):
        return False, 'the bundle does not match the signer'
    body = {k: v for k, v in msg.items() if k != 'sig' and not k.startswith('_')}   # '_' fields are the drain's, added after signing
    with tempfile.TemporaryDirectory() as d:
        home = os.path.join(d, 'home'); os.makedirs(home)
        env = dict(os.environ, HOME=home)                                   # a throwaway keystore: importing never touches the real one
        bp, mp, sp = (os.path.join(d, n) for n in ('bundle.json', 'msg.bin', 'msg.bin.sig'))
        json.dump(b, open(bp, 'w'))
        open(mp, 'wb').write((canon(body) + '\n').encode())
        json.dump({'signature': sig, 'fingerprint': frm}, open(sp, 'w'))
        subprocess.run(['sgit', 'pki', 'import', bp], env=env, capture_output=True, timeout=60)
        r = subprocess.run(['sgit', 'pki', 'verify', '--json', mp, sp], env=env, capture_output=True, text=True, timeout=60)
    try: res = json.loads(r.stdout or '{}')
    except ValueError: res = {}
    return (True, '') if res.get('valid') is True else (False, str(res.get('error') or r.stderr or 'the signature does not verify').strip()[-200:])

def load():
    return json.load(open(data_file('contributors.json'), encoding='utf-8'))

def status(msg, data=None):
    """'enrolled' (a known contributor's key), 'unknown key' (signed, not enrolled), or 'unsigned' / why it failed."""
    ok, why = verify(msg)
    if not ok: return why
    keys = {k['signing_fingerprint']: k for k in (data or load())['keys']}
    return 'enrolled' if msg['from'] in keys else 'unknown key'

def save(data):
    p = data_file('contributors.json')
    json.dump(data, open(p, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); open(p, 'a').write('\n')

def enrol(m, data, today=None):
    """Enrol the key in one drained enrolment, or say why not. Two shapes of invitation: a signed one made in the browser
    (m['invite'], signed by an enrolled key whose role may invite) and the conductor's bootstrap (m['code'], whose
    SHA-256 is an open invitation). Each enrols at most rules.devices_per_invitation devices, until it expires.
    Returns (True, what happened) and changes data, or (False, why)."""
    today = today or datetime.date.today().isoformat()
    fp, rules = m.get('from'), data['rules']
    if any(k['signing_fingerprint'] == fp for k in data['keys']): return False, f'{fp} is already enrolled'
    ok, why = verify(m)
    if not ok: return False, f'{fp}: the enrolment is not signed by its key ({why})'
    inv = m.get('invite')
    if inv:
        signer = next((k for k in data['keys'] if k['signing_fingerprint'] == inv.get('from')), None)
        if not signer or signer['role'] not in rules.get('may_invite', ['editor']): return False, f'{fp}: the invitation is not from a key that may invite'
        ok, why = verify(inv, signer['bundle'])
        if not ok: return False, f'{fp}: the invitation\'s signature does not verify ({why})'
        # Everything the invitation claims is checked before any row is kept: a refused invitation leaves nothing
        # behind that a later one with the same nonce could inherit (security advisory SA-2026-020).
        if inv.get('role') not in {r for r, _ in data['roles']} or inv.get('role') == 'editor': return False, f'{fp}: an invitation cannot give the role {inv.get("role")}'
        if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,30}', str(inv.get('handle', ''))) or inv.get('handle') == 'editor': return False, f'{fp}: the invitation\'s handle is not one an invitation may give'
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(inv.get('exp', ''))) or inv['exp'] > (datetime.date.fromisoformat(today) + datetime.timedelta(days=31)).isoformat():
            return False, f'{fp}: the invitation\'s expiry is not a date within a month'
        h = hashlib.sha256(('invite|' + str(inv.get('nonce'))).encode()).hexdigest()
        row = next((i for i in data['invitations'] if i['hash'] == h), None)
        if row and (row['role'] != inv['role'] or row['handle'] != inv['handle']): return False, f'{fp}: the invitation does not match the one first seen with its nonce'
        if not row:
            row = {'hash': h, 'handle': inv['handle'], 'role': inv['role'], 'made': '', 'expires': inv['exp'], 'used': 0, 'by': signer['handle']}
            data['invitations'].append(row)
    else:
        row = next((i for i in data['invitations'] if i['hash'] == hashlib.sha256(str(m.get('code', '')).encode()).hexdigest()), None)
        if not row: return False, f'{fp}: its code is not an invitation'
    if row['expires'] < today: return False, f'{fp}: the invitation for {row["handle"]} expired on {row["expires"]}'
    if row['used'] >= rules['devices_per_invitation']: return False, f'{fp}: the invitation for {row["handle"]} has enrolled its devices'
    row['used'] += 1
    data['keys'].append({'handle': row['handle'], 'role': row['role'], 'signing_fingerprint': fp, 'fingerprint': m['bundle']['fingerprint'],
                         'device': str(m.get('device', ''))[:20], 'enrolled': today, 'invited_by': row.get('by', 'conductor'), 'bundle': m['bundle']})
    return True, f'enrolled {row["handle"]} ({row["role"]}): {fp} on a {m.get("device", "device")}'
