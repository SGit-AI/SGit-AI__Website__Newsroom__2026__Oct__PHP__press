#!/usr/bin/env python3
"""Invitations to sign feedback on this site, and enrolling the keys they make. Run by the conductor or the editor, in a
session, never by the build. Kept by conductor@php.newsroom; the brief is
admin/content/briefs/2026-10-22__brief__feedback-keys-and-review.md.

  The people who invite do it in the browser, on /join/invite/, with an enrolled key: that needs nothing here. This
  tool is the conductor's bootstrap, for the editor's first key, and a way to re-run enrolment.

  new --handle <h> --role <editor|team|power-user> --out <dir outside the repository>
        a random code; only its SHA-256 goes into data/contributors.json. Writes <dir>/invite-<handle>.txt (the link)
        and <dir>/invite-<handle>.svg (its QR code). The link is the credential until it is used: send it to one person.
  enrol --vault <clone of the collaborators vault>
        after collaborators_drain.py: every enrolment in enrolments/*.jsonl whose signature verifies and whose code is
        an open, unexpired invitation with devices left is added to data/contributors.json (handle, role, fingerprints,
        device, date). Prints what it did; never prints a code.
  list  the invitations (hashes only) and the enrolled keys.
"""
import argparse, datetime, glob, hashlib, json, os, re, secrets, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contributors import enrol as enrol_key
from newsroom_paths import data_file, is_published

P = data_file('contributors.json')   # the data repository's files/; release it there with its tools/release.sh
BASE = 'https://php.oct.2026.newsroom.sgit.ai/join/'

def save(d):
    json.dump(d, open(P, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); open(P, 'a').write('\n')

def new(a):
    out = os.path.abspath(a.out)
    if is_published(out): sys.exit('refusing: --out is inside one of the newsroom\'s repositories, and everything there is published')
    d = json.load(open(P, encoding='utf-8'))
    if a.role not in {r for r, _ in d['roles']}: sys.exit(f'role must be one of {[r for r, _ in d["roles"]]}')
    code = secrets.token_hex(16)
    today = datetime.date.today()
    d['invitations'].append({'hash': hashlib.sha256(code.encode()).hexdigest(), 'handle': a.handle, 'role': a.role,
                             'made': today.isoformat(), 'expires': (today + datetime.timedelta(days=d['rules']['invitation_days'])).isoformat(), 'used': 0})
    save(d)
    link = f'{BASE}#j1.{code}.{a.handle}'
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, f'invite-{a.handle}.txt'), 'w').write(link + '\n')
    try:
        import qrcode, qrcode.image.svg
        qrcode.make(link, image_factory=qrcode.image.svg.SvgPathImage).save(os.path.join(out, f'invite-{a.handle}.svg'))
        qr = 'and its QR code'
    except ImportError:
        qr = '(no QR: pip install qrcode)'
    print(f'invitation for {a.handle} ({a.role}): the link {qr} are in {out}; data/contributors.json has its hash only')

def enrol(a):
    """Re-run enrolment over every drained enrolment (the drain already does it as messages arrive)."""
    d, added = json.load(open(P, encoding='utf-8')), 0
    for f in sorted(glob.glob(os.path.join(os.path.abspath(a.vault), 'enrolments', '*.jsonl'))):
        for line in open(f, encoding='utf-8'):
            ok, what = enrol_key(json.loads(line), d)
            added += ok; print(what)
    save(d)
    print(f'{added} key(s) enrolled; {len(d["keys"])} in all')

def lst(a):
    d = json.load(open(P, encoding='utf-8'))
    for i in d['invitations']: print(f'invitation {i["handle"]:<16} {i["role"]:<11} made {i["made"]} expires {i["expires"]} used {i["used"]}')
    for k in d['keys']: print(f'key        {k["handle"]:<16} {k["role"]:<11} {k["signing_fingerprint"]} {k["device"]} enrolled {k["enrolled"]}')

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
    n = sub.add_parser('new'); n.add_argument('--handle', required=True); n.add_argument('--role', required=True); n.add_argument('--out', required=True)
    e = sub.add_parser('enrol'); e.add_argument('--vault', required=True)
    sub.add_parser('list')
    a = ap.parse_args()
    if a.cmd == 'new' and not re.fullmatch(r'[a-z0-9-]{1,40}', a.handle): sys.exit('a handle is 1 to 40 lowercase letters, digits and hyphens')
    {'new': new, 'enrol': enrol, 'list': lst}[a.cmd](a)

if __name__ == '__main__':
    main()
