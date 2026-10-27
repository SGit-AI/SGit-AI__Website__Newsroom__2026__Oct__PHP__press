#!/usr/bin/env python3
"""Export the pipeline's own record (researcher, curator, journalist, correspondent) into data/loops.json.

Usage: admin/build/export_loops.py [--vault <clone of the evidence vault>] [--sgit <path to sgit>]

The build never reads git history or a vault (CI clones shallow and holds no vault), so the times the
loops page needs are gathered here, by the correspondent at each wake, and committed as data:

  vault      every commit of the evidence vault (nnd3i8iw, a pack vault, since 27 October 2026; 3ytzxm3g before, decommissioned): when, by whom, what it promoted, and the
             source-watch queue time the curator names (the only trace of the researcher's runs that
             this repository can see). Kept from the previous export when --vault is not given.
  releases   every release on origin/dev: version, time, the Agent line, and the evidence vault head and
             latest capture that release served (read from data/vault.json at that commit).
  repo       the size of the repository: commits, tracked files, bytes, pages.
  next       the next wake of each scheduled role after this export, in UTC, from data/schedule/<role>.json
             in London time (zoneinfo, so the clock change is honoured).

Standard library only. Written by correspondent@php.newsroom, 25 October 2026, at the editor's request.
"""
import argparse, datetime as dt, json, os, re, subprocess, sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'data', 'loops.json')
ROLES = ['researcher', 'curator', 'journalist', 'correspondent']
MONTHS = {m: i + 1 for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}
LONDON = ZoneInfo('Europe/London')

def git(*a):
    return subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout

def utc(t):
    return t.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')

def day_time(s, year, tz):
    """'24 Oct 16:52' in tz as a UTC minute."""
    m = re.match(r'(\d{1,2}) (\w{3}) (\d{2}):(\d{2})', s)
    if not m or m.group(2) not in MONTHS:
        return None
    return utc(dt.datetime(year, MONTHS[m.group(2)], int(m.group(1)), int(m.group(3)), int(m.group(4)), tzinfo=tz))

def vault_commits(clone, sgit):
    ids = [l.split()[0] for l in subprocess.run([sgit, 'history', 'log', '--oneline'], cwd=clone, capture_output=True, text=True, check=True).stdout.splitlines() if l.strip()]
    first, last = ids[-1], ids[0]
    log = json.loads(subprocess.run([sgit, 'history', 'log', '--json', f'{first}..{last}'], cwd=clone, capture_output=True, text=True, check=True).stdout)
    entries = sorted(log['commits'], key=lambda c: c['timestamp_ms'])
    short = list(reversed(ids))
    if len(short) != len(entries) + 1:
        sys.exit(f'export_loops: {len(short)} commits in the log, {len(entries)} in the range: refusing to guess')
    out = []
    for cid, c in zip(short, [None] + entries):
        if c is None:
            out.append({'id': cid, 'at': None, 'by': 'first commit', 'subject': 'the first commit', 'files_added': 0})
            continue
        msg = c['message'] or ''
        at = dt.datetime.strptime(c['timestamp_iso'][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=dt.timezone.utc)
        by = msg.split(':', 1)[0].strip() if ':' in msg[:60] else ''
        row = {'id': cid, 'at': utc(at), 'by': by, 'subject': msg[:240], 'files_added': len(c.get('files_added', [])),
               'files_modified': len(c.get('files_modified', []))}
        n = re.search(r'promote (\d+) (?:more )?sources', msg)
        row['sources'] = int(n.group(1)) if n else 0
        n = re.search(r'add (\d+) newer snapshots', msg)
        row['snapshots'] = int(n.group(1)) if n else 0
        n = re.search(r'(\d+) (?:new )?claims', msg)
        row['claims'] = int(n.group(1)) if n else 0
        q = re.search(r'(\d{1,2} \w{3} \d{2}:\d{2}) UTC queue', msg)
        row['queue_at'] = day_time(q.group(1), at.year, dt.timezone.utc) if q else None
        w = re.search(r'scheduled wake of (\d{1,2} \w{3} \d{2}:\d{2})', msg)
        row['wake_at'] = day_time(w.group(1), at.year, LONDON) if w else None
        out.append(row)
    return out

def releases():
    out = []
    for line in git('log', 'origin/dev', '--reverse', '--format=%H%x09%cI%x09%s').splitlines():
        h, when, subj = line.split('\t', 2)
        m = re.match(r'v(\d+\.\d+\.\d+): ', subj)
        if not m:
            continue
        body = git('log', '-1', '--format=%b', h)
        agent = re.search(r'^Agent: (\S+)', body, re.M)
        try:
            v = json.loads(git('show', f'{h}:data/vault.json'))
        except subprocess.CalledProcessError:
            v = {}
        out.append({'version': m.group(1), 'at': utc(dt.datetime.fromisoformat(when)), 'agent': agent.group(1) if agent else '',
                    'commit': h[:9], 'vault_head': (v.get('head') or {}).get('commit'), 'latest_capture': v.get('latest_capture'),
                    'sources': v.get('sources')})
    return out

def repo():
    files = git('ls-files', '-z').split('\0')
    files = [f for f in files if f]
    size = sum(os.path.getsize(os.path.join(ROOT, f)) for f in files if os.path.isfile(os.path.join(ROOT, f)))
    data = [f for f in files if f.startswith('data/') and f.endswith('.json')]
    return {'commits': int(git('rev-list', '--count', 'origin/dev').strip()), 'files': len(files), 'bytes': size,
            'pages': sum(1 for f in files if f.endswith('.html')), 'twins': sum(1 for f in files if f.endswith('.md') and not f.startswith('admin/')),
            'data_files': len(data), 'data_bytes': sum(os.path.getsize(os.path.join(ROOT, f)) for f in data),
            'build_lines': sum(1 for _ in open(os.path.join(ROOT, 'admin/build/build.py'), encoding='utf-8'))}

def next_wakes(now):
    out = {}
    for role in ROLES:
        p = os.path.join(ROOT, 'data', 'schedule', f'{role}.json')
        if not os.path.exists(p):
            continue
        card = json.load(open(p, encoding='utf-8'))
        local = now.astimezone(LONDON)
        times = []
        for d in range(0, 3):
            day = (local + dt.timedelta(days=d)).date()
            for t in card.get('times', []):
                hh, mm = map(int, t.split(':'))
                at = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=LONDON)
                if at > now:
                    times.append(utc(at))
        out[role] = {'status': card.get('status', ''), 'model': card.get('model', ''), 'times_london': card.get('times', []), 'next': sorted(times)[:6]}
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vault', help='a clone of the evidence vault (read-only is enough)')
    ap.add_argument('--sgit', default='sgit')
    a = ap.parse_args()
    old = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    now = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    d = {
        'about': 'The pipeline\'s own record, exported by admin/build/export_loops.py (correspondent@php.newsroom) at each correspondent wake: the evidence vault\'s commits, every release, the repository\'s size and the next scheduled wakes. /views/loops/ is built from it, with data/runs/ and data/schedule/.',
        'exported_at': utc(now),
        'vault': vault_commits(a.vault, a.sgit) if a.vault else old.get('vault', []),
        'vault_read_at': utc(now) if a.vault else old.get('vault_read_at'),
        'releases': releases(),
        'repo': repo(),
        'next': next_wakes(now),
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(json.dumps(d, indent=1, ensure_ascii=False) + '\n')
    print(f'pipeline: {len(d["vault"])} vault commits, {len(d["releases"])} releases, {d["repo"]["commits"]} commits, exported {d["exported_at"]}')

if __name__ == '__main__':
    main()
