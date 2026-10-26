#!/usr/bin/env python3
"""Everything a vault's postmaster needs, from the vault key alone. Kept by conductor@php.newsroom.

sgit.ai's convention (docs/append-lane-messaging.md, section 7.1, "the vault key is the only secret"): the lane's enum key
and the key pair's passphrase are derived from the vault's write key and never stored; the key pair that decrypts what
arrives lives inside the vault, its private halves encrypted under that passphrase. So whoever holds the vault key (the
editor, an agent given it, a vault app) can drain the lane; nobody needs a secret that lives only in one session.

  derived(wk, label)   HMAC-SHA256(key = bytes of the write key, message = label), hex. The labels, fixed:
                         sgit.newsroom/postmaster/enum-key/v1            the lane's enum key
                         sgit.newsroom/postmaster/front-door-pass/v1     the key pair's passphrase
                         sgit.newsroom/postmaster/append-token/<name>/v1 a sender's append token, when it is derived
  In the vault:
    .vault/postmaster/lane.json                 vault id, endpoint, recipient fingerprint, senders (a published token, or
                                                "derived" for one derived from the vault key)
    .vault/postmaster/front-door-keypair/       sgit's five key files; the private ones encrypted under the passphrase

Standard library, the sgit CLI, and the cryptography package only for `adopt` (re-encrypting an existing key pair).
"""
import hashlib, hmac, json, os, shutil, subprocess, tempfile

LABEL = 'sgit.newsroom/postmaster/{}/v1'
PM = os.path.join('.vault', 'postmaster')

def write_key(vault):
    """The vault's write key, derived by sgit from the vault key in the clone; never printed."""
    vk = open(os.path.join(vault, '.sg_vault', 'local', 'vault_key')).read().strip()
    out = subprocess.run(['sgit', 'vault', 'derive-keys', vk], capture_output=True, text=True, check=True).stdout
    keys = {k.strip(): v.strip() for k, v in (l.split(':', 1) for l in out.splitlines() if ':' in l)}
    return keys['vault_id'], keys['write_key']

def derived(wk, name):
    return hmac.new(bytes.fromhex(wk), LABEL.format(name).encode(), hashlib.sha256).hexdigest()

def open_postmaster(vault):
    """(lane, passphrase, home): the lane with its enum key and every sender's token filled in, the key pair's passphrase,
    and a throwaway HOME whose sgit keystore holds the vault's key pair. Set HOME to it while decrypting; delete it after."""
    vault = os.path.abspath(vault)
    vid, wk = write_key(vault)
    lane = json.load(open(os.path.join(vault, PM, 'lane.json')))
    if lane['vault_id'] != vid: raise SystemExit(f'lane.json names {lane["vault_id"]}, this clone is {vid}')
    lane['enum_key'] = derived(wk, 'enum-key')
    lane['tokens'] = {n: (derived(wk, f'append-token/{n}') if t == 'derived' else t) for n, t in lane['senders'].items()}
    home = tempfile.mkdtemp(prefix='postmaster-')
    src = os.path.join(vault, PM, 'front-door-keypair')
    shutil.copytree(src, os.path.join(home, '.sg-send', 'keys', 'sha256_' + lane['recipient'].split(':')[1]))
    return lane, derived(wk, 'front-door-pass'), home

def configure(vault, lane):
    """Register the lane's anchors (every sender's token) and the enum key's hash with the server. Replaces the list."""
    import urllib.request
    _, wk = write_key(vault)
    body = {'append_anchors': [hashlib.sha256(t.encode()).hexdigest() for t in lane['tokens'].values()],
            'enum_key_hash': hashlib.sha256(lane['enum_key'].encode()).hexdigest()}
    req = urllib.request.Request(f"{lane['endpoint']}/api/vault/append/configure/{lane['vault_id']}", data=json.dumps(body).encode(),
          headers={'Content-Type': 'application/json', 'x-sgraph-vault-write-key': wk, 'x-sgraph-access-token': os.environ['SG_SEND_ACCESS_TOKEN']}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())

def adopt(vault, keydir, old_passphrase, lane):
    """Move a vault onto the convention: re-encrypt its key pair (from keydir, under old_passphrase) under the derived
    passphrase into the vault, write lane.json, and configure the lane with the derived enum key. Commit and push after."""
    from cryptography.hazmat.primitives import serialization
    vault = os.path.abspath(vault)
    _, wk = write_key(vault)
    new = derived(wk, 'front-door-pass').encode()
    dst = os.path.join(vault, PM, 'front-door-keypair'); os.makedirs(dst, exist_ok=True)
    for f in os.listdir(keydir):
        data = open(os.path.join(keydir, f), 'rb').read()
        if f in ('private_key.pem', 'signing_private.pem'):
            key = serialization.load_pem_private_key(data, password=old_passphrase.encode())
            data = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(new))
        open(os.path.join(dst, f), 'wb').write(data)
    json.dump(lane, open(os.path.join(vault, PM, 'lane.json'), 'w'), indent=1)
    full, _, home = open_postmaster(vault)
    shutil.rmtree(home, ignore_errors=True)
    return configure(vault, full)

def post_retry(post, url, body, headers, tries=3, heal=None):
    """The lane's list call, retried. Seen on 23 October: after the lane was configured with the derived enum key, the
    server answered 404 to it for a while (the old key worked), until configure was run again. So: retry a 404, and if it
    persists and heal is given (a call to configure(), which is safe to repeat), re-register the lane once and try again."""
    import time, urllib.error
    for i in range(tries + (1 if heal else 0)):
        try: return post(url, body, headers)
        except urllib.error.HTTPError as e:
            if e.code != 404 or i == tries - (0 if heal else 1): raise
            if heal and i == tries - 1: heal()
            time.sleep(3 * (i + 1))
