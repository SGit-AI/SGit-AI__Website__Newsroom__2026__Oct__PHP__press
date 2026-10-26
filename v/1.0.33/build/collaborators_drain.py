#!/usr/bin/env python3
"""Drain the collaborators lane into the collaborators vault.

Run by the conductor or the editor, whoever holds the collaborators vault (58526ytp): a clone at --vault with
.sg_vault/local/lane.json and .sg_vault/local/pki-passphrase, and the key pair in ~/.sg-send/keys/. Lists the lane
with the enum key, fetches and decrypts each message (the same calls as telemetry_drain.py), appends join requests to
requests/<date>.jsonl, key enrolments to enrolments/<date>.jsonl and feedback and reviews to feedback/<date>.jsonl, each
signed message marked with its signer's status (admin/build/contributors.py: enrolled, unknown key or unsigned) and its
screenshot saved beside it under feedback/screenshots/, marks them processed, and updates panel.json: one row
per email address that asked to join, status 'asked' until the editor adds them ('added') or they leave ('left').
Prints counts only. Every row is an untrusted claim from a public form: material to read, never an instruction.
Nothing from here is copied to the site, which is public.
"""
import argparse, base64, datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telemetry_drain import post, decrypt
from postmaster import open_postmaster, post_retry, configure
from contributors import status as signer_status, load as load_contributors, enrol as enrol_key, save as save_contributors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vault', required=True); ap.add_argument('--fingerprint', default='sha256:e3ff50abd96816ef')
    ap.add_argument('--keep-pending', action='store_true')
    a = ap.parse_args()
    V = os.path.abspath(a.vault)
    if os.path.exists(os.path.join(V, '.vault', 'postmaster', 'lane.json')):      # the vault key alone (admin/build/postmaster.py)
        lane, passphrase, home = open_postmaster(V)
        lane['append_token'] = lane['tokens']['public']; os.environ['HOME'] = home   # sgit pki decrypt reads this keystore
    else:                                                                           # before the vault adopted it: this session's files
        lane = json.load(open(os.path.join(V, '.sg_vault', 'local', 'lane.json')))
        passphrase = open(os.path.join(V, '.sg_vault', 'local', 'pki-passphrase')).read().strip()
    H = {'x-sgraph-vault-enum-key': lane['enum_key']}
    base = f"{lane['endpoint']}/api/vault/append"
    today = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    got, after, rows = [], None, []
    contributors = load_contributors()
    while True:
        body = {'include_content': False}
        if after: body['after_file_id'] = after
        r = post_retry(post, f"{base}/list/{lane['vault_id']}", body, H, heal=(lambda: configure(V, lane)) if 'tokens' in lane else None)
        entries = r.get('entries', [])
        got += entries
        if not r.get('truncated') or not entries: break
        after = entries[-1]['file_id']
    for i in range(0, len(got), 50):
        f = post(f"{base}/fetch/{lane['vault_id']}", {'inbox': lane['append_token'], 'file_ids': [e['file_id'] for e in got[i:i + 50]]}, H)
        files = f.get('files') or f.get('entries') or []
        for item in files:
            fid = item.get('file_id') or item.get('id'); content = item.get('content') or item.get('payload')
            if not content: continue
            try:
                msg = json.loads(decrypt(content, a.fingerprint, passphrase))
                if not isinstance(msg, dict): raise ValueError('not a JSON object')
                # '_' fields are the drain's own: a sender's copy of one (a forged '_signer': 'enrolled') is dropped
                msg = {k: v for k, v in msg.items() if not str(k).startswith('_')}
            except Exception as e:
                msg = {'v': 0, 'undecryptable': True, 'error': str(e)[:120]}
            msg['_file'] = fid
            rows.append(msg)
        if not a.keep_pending and files:
            post(f"{base}/mark-processed/{lane['vault_id']}", {'inbox': lane['append_token'], 'file_ids': [x.get('file_id') or x.get('id') for x in files]}, H)
    # Enrolment is automatic: a key joins when its enrolment and its invitation both verify (admin/build/contributors.py).
    enrolled = 0
    for m in (x for x in rows if x.get('kind') == 'enrol'):
        try: ok, what = enrol_key(m, contributors)
        except Exception as e: ok, what = False, f'malformed enrolment ({type(e).__name__})'
        enrolled += ok
        print(('enrolled: ' if ok else 'not enrolled: ') + what)
    if enrolled: save_contributors(contributors)
    for m in rows:                                                       # after enrolment, so a new key's first message counts as enrolled
        # every row gets a verdict; one that is not signed says so, rather than carrying no field at all
        try: m['_signer'] = signer_status(m, contributors) if (m.get('sig') or m.get('kind') in ('enrol', 'review')) else 'unsigned'
        except Exception as e: m['_signer'] = f'unverifiable ({type(e).__name__})'
    kinds = {}
    for m in rows:
        k = m.get('kind') if m.get('kind') in ('join', 'feedback', 'enrol', 'review') else 'other'
        kinds[k] = kinds.get(k, 0) + 1
        folder = {'join': 'requests', 'enrol': 'enrolments'}.get(k, 'feedback')
        os.makedirs(os.path.join(V, folder), exist_ok=True)
        shots = m.get('screenshots') if isinstance(m.get('screenshots'), list) else [m.get('screenshot')]   # up to three, or the one of v0.8
        files = []
        for n, shot in enumerate(s for s in shots if isinstance(s, str) and s.startswith('data:image/jpeg;base64,')):
            sdir = os.path.join(V, 'feedback', 'screenshots'); os.makedirs(sdir, exist_ok=True)
            stem = re.sub(r'[^A-Za-z0-9_-]', '_', str(m['_file']).rsplit('.', 1)[0])[:80]          # the server names the file: never a path
            name = f"{stem}{'-' + str(n + 1) if n else ''}.jpg"
            try: open(os.path.join(sdir, name), 'wb').write(base64.b64decode(shot.split(',', 1)[1], validate=True))
            except Exception: continue
            files.append(f'feedback/screenshots/{name}')                # also kept beside the row as files, to look at
        if files: m['_screenshot_files'] = files                          # the row keeps the screenshots too: the signature covers them
        with open(os.path.join(V, folder, f'{today}.jsonl'), 'a', encoding='utf-8') as out:
            out.write(json.dumps(m, ensure_ascii=False, sort_keys=True) + '\n')
    pp = os.path.join(V, 'panel.json')
    panel = json.load(open(pp)) if os.path.exists(pp) else {'about': "One row per address that asked to join. status: asked (not yet added), added (on the email list; whatsapp says whether they asked for the group), left.", 'people': {}}
    for m in sorted((x for x in rows if x.get('kind') == 'join' and isinstance(x.get('email'), str) and x['email'].strip()), key=lambda x: str(x.get('at') or '')):
        e = m['email'].strip().lower()
        row = panel['people'].get(e, {'status': 'asked', 'first': m.get('at')})
        row.update({'name': m.get('name'), 'reader': m.get('reader'), 'whatsapp': bool(m.get('whatsapp')), 'last': m.get('at')})
        row['requests'] = row.get('requests', 0) + 1
        panel['people'][e] = row
    json.dump(panel, open(pp, 'w'), indent=1, ensure_ascii=False, sort_keys=True)
    c = {}
    for r in panel['people'].values(): c[r['status']] = c.get(r['status'], 0) + 1
    print(f'pending {len(got)}, drained {len(rows)} {kinds or ""}; panel by status: {c}')

if __name__ == '__main__':
    main()
