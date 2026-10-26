#!/usr/bin/env python3
"""The NCSC-NL php2shell inventory, read commit by commit from a clone of github.com/NCSC-NL/php2shell.

Writes data/inventory-history.json: for every commit that changed software/, the counts per status, and every
row whose status changed between consecutive commits. Deterministic: the input is a git history, which is
content-addressed, so the same clone gives the same file. The vault holds the inventory at one commit
(cca173c64ec5); this reads the commits around it, and checks itself against that one.

Run: python3 admin/build/inventory_history.py --repo <clone of NCSC-NL/php2shell>
"""
import argparse, json, os, re, subprocess, sys
from collections import Counter, OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
VAULT_COMMIT = 'cca173c64ec5'   # the commit the evidence vault captured; data/software.json is parsed from it
STATUSES = ['Fix', 'Vulnerable', 'Investigation', 'Not vuln']
# rows present in the inventory at VAULT_COMMIT that the vault's parse did not export (BRIEF-CORRECTIONS.md, v0.4.2)
KNOWN_MISSED_BY_VAULT = {('iBabs', 'iBabs bestuursportaal')}

# What kind of row it is, read from the inventory's own 'CVE assessment:' line by these rules, in order. The first
# match wins. The rules are this site's reading; the words they match are the inventory's.
CLASSES = [
    ('inherited', 'Affected because it runs on affected PHP', r'Affected when deployed on an affected web-serving PHP runtime'),
    ('security-vendor', 'From a security or network vendor (matched on the supplier)', r'^(Palo Alto Networks|Fortinet|Cisco|F5|Sophos|SonicWall|Barracuda|Check Point|Juniper Networks|Citrix|WatchGuard|Zyxel)\b'),
    ('vendor-advisory', 'Named in a vendor advisory', r'(advisory|PSIRT|QSA-|lists (these|this|all)|confirms that all|Affected: all|Affected package streams|Affected family|Trusted-party reporting|Vendor advisory names)'),
    ('fixed', 'A fixed build or release', r'(Fixed|Patched|fix|patched)'),
    ('runtime', 'Ships or hosts PHP itself', r'(Hosted PHP option|PHP relationship confirmed.*(package|runtime|image|SAPI)|Optional PHP path)'),
    ('application', 'Runs on PHP; whether it is exposed is not yet assessed', r'PHP relationship confirmed'),
    ('dev', 'Development, CI or admin tooling', r'Dev/CI/admin scope'),
    ('library', 'A library: only the caller\'s PHP matters', r'Caller PHP runtime only'),
    ('other-scope', 'Another engine, the browser, or history', r'(PHP Wasm scope|Independent engine|Historical scope)'),
    ('evidence-thin', 'Only a requirement or an SBOM says it uses PHP', r'(requirement or (GitHub )?SBOM evidence only)'),
]

def classify(supplier, product, notes):
    text = product + ' ' + (notes or '')
    for cid, _, rx in CLASSES:
        if re.search(rx, supplier if cid == 'security-vendor' else text):
            return cid
    return 'unclassified'

def git(repo, *args):
    return subprocess.run(['git', '-C', repo] + list(args), capture_output=True, text=True, check=True).stdout

def rows_at(repo, commit):
    """Every product row in software/software_list_*.md at a commit, as (supplier, product, status_109618, status_109619)."""
    files = [f for f in git(repo, 'ls-tree', '--name-only', commit, 'software/').split() if re.match(r'software/software_list_[^/]+\.md$', f)]
    out = []
    for f in sorted(files):
        if f == 'software/software_list.md':
            continue  # the index page, no rows
        for line in git(repo, 'show', f'{commit}:{f}').splitlines():
            if not line.startswith('|') or line.startswith('|:') or line.startswith('| Supplier'):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) < 5:
                continue
            out.append((cells[0], cells[1], cells[3] or 'none', cells[4] or 'none', cells[5] if len(cells) > 5 else ''))
    return out

def utc(iso):
    """git's %cI (with offset) to a UTC minute, the form the rest of the site uses."""
    from datetime import datetime, timezone
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--repo', required=True); a = ap.parse_args()
    # walk the main line, merges included (the vault's commit is a merge), keeping each commit that changed software/
    log = git(a.repo, 'log', '--first-parent', '--reverse', '--format=%H %cI').split('\n')
    snaps, changes, prev, last_tree = [], [], {}, None
    for line in filter(None, log):
        sha, when = line.split(' ', 1)
        try:
            tree = git(a.repo, 'rev-parse', f'{sha}:software').strip()
        except subprocess.CalledProcessError:
            continue  # before the list existed
        if tree == last_tree:
            continue
        last_tree = tree
        rows = rows_at(a.repo, sha)
        cur = {(s, p): st for s, p, st, _, _ in rows}
        c = Counter(st for st in cur.values())
        snaps.append(OrderedDict([('commit', sha[:12]), ('at', utc(when)), ('rows', len(cur)),
                                  ('by_status', OrderedDict((k, c.get(k, 0)) for k in STATUSES + ['none'] if c.get(k, 0) or k in STATUSES))]))
        for key, st in sorted(cur.items()):
            before = prev.get(key)
            if before is not None and before != st:
                changes.append(OrderedDict([('supplier', key[0]), ('product', key[1]), ('from', before), ('to', st), ('commit', sha[:12]), ('at', utc(when))]))
            elif before is None and prev:
                changes.append(OrderedDict([('supplier', key[0]), ('product', key[1]), ('from', 'added'), ('to', st), ('commit', sha[:12]), ('at', utc(when))]))
        prev = cur
    # the self-check: at the vault's commit, this parser must agree with data/software.json row for row, except for
    # rows the vault's own parse is known to have missed (a correction, published in BRIEF-CORRECTIONS.md)
    sw = json.load(open(os.path.join(ROOT, 'data', 'software.json'), encoding='utf-8'))
    at = next((s for s in snaps if s['commit'].startswith(VAULT_COMMIT)), None)
    if not at:
        sys.exit(f'self-check failed: {VAULT_COMMIT} is not on the main line of this clone')
    mine = {(s, p): st for s, p, st, _, _ in rows_at(a.repo, VAULT_COMMIT)}
    vault = {(r['supplier'], r['product']): (r.get('status_109618') or 'none') for r in sw['rows']}
    extra, missing = set(mine) - set(vault), set(vault) - set(mine)
    differ = {k for k in set(mine) & set(vault) if mine[k] != vault[k]}
    if missing or differ or extra - KNOWN_MISSED_BY_VAULT:
        sys.exit(f'self-check failed at {VAULT_COMMIT}: only here {sorted(extra - KNOWN_MISSED_BY_VAULT)}, only in the vault {sorted(missing)}, status differs {sorted(differ)}')
    head = git(a.repo, 'rev-parse', 'HEAD').strip()
    out = OrderedDict([('source', 'https://github.com/NCSC-NL/php2shell'), ('licence', 'EUPL-1.2'), ('head', head[:12]),
                       ('read_from', 'a git clone; every count is from software/software_list_*.md at the commit named'),
                       ('vault_commit', VAULT_COMMIT), ('self_check', f'at {VAULT_COMMIT} this parser agrees with data/software.json on all {sw["count"]} rows the vault exported, status for status; it also finds {len(extra)} row the vault missed: ' + '; '.join(f'{k[0]} / {k[1]} ({mine[k]})' for k in sorted(extra))),
                       ('classes', [OrderedDict([('id', c), ('name', n), ('rule', r)]) for c, n, r in CLASSES] + [OrderedDict([('id', 'unclassified'), ('name', 'No rule matched'), ('rule', '')])]),
                       ('head_rows', [[s_, p_, st, classify(s_, p_, n_)] for s_, p_, st, _, n_ in sorted(rows_at(a.repo, head), key=lambda r: (r[0].lower(), r[1].lower()))]),
                       ('snapshots', snaps), ('changes', changes)])
    with open(os.path.join(ROOT, 'data', 'inventory-history.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1, ensure_ascii=False); f.write('\n')
    print(f'{len(snaps)} snapshots, {len(changes)} row changes, head {head[:12]}; self-check passed at {VAULT_COMMIT}')

if __name__ == '__main__':
    main()
