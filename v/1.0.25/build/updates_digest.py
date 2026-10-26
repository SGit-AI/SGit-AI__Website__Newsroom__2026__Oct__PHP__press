#!/usr/bin/env python3
"""Draft an update: what changed on this site and in its evidence between two points in git.

For the conductor (and whoever holds the updates beat): it reads only the repository's own record, so an update says
what happened, not what an agent remembers. Brief: admin/content/briefs/2026-10-22__brief__the-conductor-and-the-updates.md;
how an update is written: admin/content/updates/README.md.

Run:  python3 admin/build/updates_digest.py --since <ref> [--until origin/dev]
      <ref> is any commit, tag or branch, or v<version> (the commit that released it). Prints markdown to stdout:
      the facts to write from, not the update itself. Read-only; standard library only.
"""
import argparse, json, re, subprocess, sys
from collections import Counter, OrderedDict

def git(*args, check=True):
    r = subprocess.run(['git'] + list(args), capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f'git {" ".join(args)}: {r.stderr.strip()}')
    return r.stdout

def at(ref, path, default=None):
    """A file's content at a ref, or default when it did not exist there."""
    r = subprocess.run(['git', 'show', f'{ref}:{path}'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else default

def jat(ref, path, default=None):
    t = at(ref, path)
    return json.loads(t) if t else default

def resolve(ref, until):
    """v0.4.2 means the commit on the main line where VERSION became 0.4.2."""
    if re.match(r'^v\d+\.\d+\.\d+$', ref):
        # all of history, not only the first parent: releases arrive through merges of agents' branches
        hits = [h for h in git('log', '--format=%H', until, '--', 'VERSION').split() if (at(h, 'VERSION') or '').strip() == ref[1:]]
        if not hits:
            sys.exit(f'no commit in {until} released {ref}')
        return hits[-1]  # the earliest: the commit that made the release
    return git('rev-parse', ref).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', required=True); ap.add_argument('--until', default='origin/dev')
    a = ap.parse_args()
    until = git('rev-parse', a.until).strip(); since = resolve(a.since, until)
    t0 = git('log', '-1', '--format=%cI', since).strip(); t1 = git('log', '-1', '--format=%cI', until).strip()
    out = [f'# Facts for an update: {a.since} ({since[:12]}, {t0}) to {a.until} ({until[:12]}, {t1})', '']

    # releases: the entries in data/versions.json that are new since `since`
    v0 = {v['version'] for v in (jat(since, 'data/versions.json', {}) or {}).get('versions', [])}
    rel = [v for v in (jat(until, 'data/versions.json', {}) or {}).get('versions', []) if v['version'] not in v0]
    out += [f'## Releases ({len(rel)})', ''] + [f'- v{v["version"]} ({v.get("date", "")}): {v["title"]}' for v in rel] + ['']

    # commits on the main line, grouped by the Agent: trailer (the convention in AGENTS.md)
    log = git('log', '--no-merges', '--format=%H%x1f%cI%x1f%s%x1f%b%x1e', f'{since}..{until}')
    by_agent, subjects = Counter(), OrderedDict()
    for rec in filter(str.strip, log.split('\x1e')):
        h, when, subj, body = (rec.strip('\n').split('\x1f') + ['', '', '', ''])[:4]
        m = re.search(r'^Agent:\s*(.+)$', body, re.M)
        who = m.group(1).strip() if m else 'unnamed'
        by_agent[who] += 1
        subjects.setdefault(who, []).append(f'{when[:16]}Z {subj[:160]}')
    out += [f'## Commits since, merges left out, by agent ({sum(by_agent.values())})', '']
    for who, n in by_agent.most_common():
        out.append(f'- **{who}**: {n}')
        out += [f'  - {s}' for s in subjects[who][:6]]
    out.append('')

    # board: rows opened, closed and changed
    b0 = {b['id'] + '|' + b['title']: b for b in (jat(since, 'data/admin.json', {}) or {}).get('board', [])}
    b1 = {b['id'] + '|' + b['title']: b for b in (jat(until, 'data/admin.json', {}) or {}).get('board', [])}
    opened = [b for k, b in b1.items() if k not in b0]
    closed = [b for k, b in b1.items() if k in b0 and b0[k].get('status') != 'done' and b.get('status') == 'done']
    waiting = [b for b in b1.values() if b.get('status') in ('open', 'waiting') and b.get('owner') in ('editor', 'vicky')]
    tot = Counter(b.get('status') for b in b1.values())
    out += [f'## Board: {len(opened)} new rows, {len(closed)} moved to done; now ' + ', '.join(f'{n} {k}' for k, n in tot.most_common()), '']
    out += [f'- new {b["id"]} [{b.get("status")}] ({b.get("owner")}): {b["title"][:160]}' for b in opened]
    out += [f'- closed {b["id"]} ({b.get("owner")}): {b["title"][:160]}' for b in closed]
    out += ['', f'## Waiting on the editor or the project manager ({len(waiting)})', '']
    out += [f'- {b["id"]} ({b.get("owner")}): {b["title"][:200]}' for b in waiting] + ['']

    # pages: the URLs llms.txt lists at each end
    urls = lambda t: set(re.findall(r'\]\((https?://[^)]+\.md)\)', t or ''))
    p0, p1 = urls(at(since, 'llms.txt', '')), urls(at(until, 'llms.txt', ''))
    added = sorted(u for u in p1 - p0 if '/sources/' not in u and '/actors/' not in u and '/facts/' not in u and '/versions/' not in u)
    out += [f'## Pages: {len(p1) - len(p0):+d} in llms.txt ({len(p1)} now); the new ones outside sources, parties, facts and histories', '']
    out += [f'- {u}' for u in added[:60]] + ([f'- and {len(added) - 60} more'] if len(added) > 60 else []) + ['']

    # writing: briefs, stories, external material, corrections
    files = lambda ref, d: set(git('ls-tree', '-r', '--name-only', ref, d, check=False).split())
    for d, label in (('admin/content/briefs', 'Briefs'), ('admin/content/articles', 'Stories'), ('admin/content/external', 'External material'), ('admin/content/updates', 'Updates')):
        new = sorted(files(until, d) - files(since, d))
        out += [f'## {label}: {len(new)} new', ''] + [f'- {f}' for f in new] + ['']
    c0 = set(re.findall(r'^## (.+)$', at(since, 'BRIEF-CORRECTIONS.md', '') or '', re.M))
    c1 = re.findall(r'^## (.+)$', at(until, 'BRIEF-CORRECTIONS.md', '') or '', re.M)
    newc = [c for c in c1 if c not in c0]
    out += [f'## Corrections: {len(newc)} new', ''] + [f'- {c}' for c in newc] + ['']

    # the evidence: counts at each end
    def counts(ref):
        v = jat(ref, 'data/vault.json', {}) or {}
        cl = jat(ref, 'data/claims.json', []) or []
        tl = jat(ref, 'data/timeline.json', []) or []
        return OrderedDict([('vault commit', (v.get('head') or {}).get('commit')), ('sources', v.get('sources')), ('captures', v.get('captures')),
                            ('latest capture', v.get('latest_capture')), ('claims', len(cl)), ('claims by status', dict(Counter(c.get('status') for c in cl))),
                            ('timeline events', len(tl))])
    c0_, c1_ = counts(since), counts(until)
    out += ['## The evidence', '', '| | then | now |', '|---|---|---|'] + [f'| {k} | {c0_[k]} | {c1_[k]} |' for k in c1_] + ['']
    ih = jat(until, 'data/inventory-history.json')
    if ih and ih.get('snapshots'):
        s = ih['snapshots'][-1]
        out += [f'- NCSC-NL inventory, latest read: {s["at"]}, commit {s["commit"]}: {s["rows"]} rows, {dict(s["by_status"])}', '']

    # coordination: pushed branches that dev has not carried in yet (as of the last fetch)
    branches = [b.strip() for b in git('branch', '-r', '--no-merged', until, check=False).splitlines() if b.strip() and '->' not in b]
    out += [f'## Branches not yet in {a.until} (as of the last git fetch): {len(branches)}', '']
    for b in branches:
        last = git('log', '-1', '--format=%cI %s', b, check=False).strip()
        ahead = git('rev-list', '--count', f'{until}..{b}', check=False).strip()
        out.append(f'- {b}: {ahead} commits ahead; last {last[:200]}')
    print('\n'.join(out))

if __name__ == '__main__':
    main()
