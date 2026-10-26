#!/usr/bin/env python3
"""Drain the conductor's lane into the conductor vault's inbox/.

Run by the conductor at the open and the close of every run: a clone of the conductor vault (5iwos28w) at --vault,
with .sg_vault/local/lanes.json ({"vault_id","endpoint","enum_key","tokens": {member: append_token}}) and
.sg_vault/local/pki-passphrase, and the conductor's key pair in ~/.sg-send/keys/. Every member has its own token,
so each lane is one sender: the drain lists and fetches lane by lane, decrypts each message with `sgit pki decrypt`,
writes it to inbox/<member>/<file id>.eml (or .txt when it carries no header block), marks it processed, and prints
what arrived from whom. Commit and push the vault afterwards; nothing here is copied to the site.
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telemetry_drain import post, decrypt
from postmaster import open_postmaster, post_retry, configure

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vault', required=True); ap.add_argument('--fingerprint', default='sha256:742d442b1c5b07bd')
    ap.add_argument('--keep-pending', action='store_true')
    a = ap.parse_args()
    V = os.path.abspath(a.vault)
    if os.path.exists(os.path.join(V, '.vault', 'postmaster', 'lane.json')):      # the vault key alone (admin/build/postmaster.py)
        lanes, passphrase, home = open_postmaster(V); os.environ['HOME'] = home    # sgit pki decrypt reads this keystore
    else:                                                                           # before the vault adopted it: this session's files
        lanes = json.load(open(os.path.join(V, '.sg_vault', 'local', 'lanes.json')))
        passphrase = open(os.path.join(V, '.sg_vault', 'local', 'pki-passphrase')).read().strip()
    H = {'x-sgraph-vault-enum-key': lanes['enum_key']}
    base = f"{lanes['endpoint']}/api/vault/append"
    by_token = {t: m for m, t in lanes['tokens'].items()}
    got = []
    after = None
    while True:
        body = {'include_content': False}
        if after: body['after_file_id'] = after
        r = post_retry(post, f"{base}/list/{lanes['vault_id']}", body, H, heal=(lambda: configure(V, lanes)) if 'tokens' in lanes else None)
        entries = r.get('entries', [])
        got += entries
        if not r.get('truncated') or not entries: break
        after = entries[-1]['file_id']
    lanes_seen = {}
    for e in got:
        lanes_seen.setdefault(e.get('inbox') or e.get('append_token') or e.get('lane'), []).append(e['file_id'])
    counts = {}
    for token, fids in lanes_seen.items():
        member = by_token.get(token, 'unknown')
        for i in range(0, len(fids), 50):
            f = post(f"{base}/fetch/{lanes['vault_id']}", {'inbox': token, 'file_ids': fids[i:i + 50]}, H)
            files = f.get('files') or f.get('entries') or []
            for item in files:
                fid = item.get('file_id') or item.get('id'); content = item.get('content') or item.get('payload')
                if not content: continue
                try:
                    text = decrypt(content, a.fingerprint, passphrase)
                except Exception as ex:
                    text = f'undecryptable: {str(ex)[:120]}\n'
                ext = '.eml' if text.lstrip().lower().startswith(('from:', 'to:', 'date:', 'subject:')) else '.txt'
                # the server names the member and the file: neither is ever allowed to be a path (SA-2026-022)
                d = os.path.join(V, 'inbox', re.sub(r'[^A-Za-z0-9_-]', '_', str(member))[:40])
                os.makedirs(d, exist_ok=True)
                stem = re.sub(r'[^A-Za-z0-9_-]', '_', str(fid).rsplit('.', 1)[0])[:80]
                open(os.path.join(d, stem + ext), 'w', encoding='utf-8').write(text)
                counts[member] = counts.get(member, 0) + 1
            if not a.keep_pending and files:
                post(f"{base}/mark-processed/{lanes['vault_id']}", {'inbox': token, 'file_ids': [x.get('file_id') or x.get('id') for x in files]}, H)
    print(f'pending {len(got)}; drained by member: {counts or "nothing"}')

if __name__ == '__main__':
    main()
