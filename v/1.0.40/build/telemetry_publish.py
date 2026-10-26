#!/usr/bin/env python3
"""After a drain: classify every session, write the classes into the private telemetry vault, and write the curated,
public stats into the public stats vault (and into this site, which draws them on /admin/telemetry/).

  python3 admin/build/telemetry_publish.py --vault <telemetry vault clone> --public <public stats vault clone> [--site .]

Run by admin/build/telemetry_flow.sh, which pulls, drains, publishes and pushes both vaults. Standard library only.

What leaves the private vault, and what does not. Published: counts per UTC hour and per day for four groups (readers;
the editor, team and power users together, so no one person's hours are public; synthetic visitors; crawlers), and,
over readers only, counts by country, device, language, site version, page and referrer host (a host with fewer than
three sessions is folded into "other"). Never published: a row, a session id, a time finer than the hour, a city or a
region, a time zone, or any count that mixes those.
"""
import argparse, collections, datetime, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import telemetry_classes as TC

GROUPS = [('readers', ['reader']), ('us', ['editor', 'power-user']), ('synthetic', ['synthetic']), ('crawlers', ['crawler'])]
GROUP_LABELS = {'readers': 'Readers', 'us': 'The editor, team and power users', 'synthetic': 'Synthetic: agents, tests, headless browsers', 'crawlers': 'Crawlers: search engines'}
MIN_REF_SESSIONS = 3


def load_rows(vault):
    rows = []
    for fn in sorted(glob.glob(os.path.join(vault, 'drain', '*.jsonl'))):
        for line in open(fn, encoding='utf-8'):
            try: rows.append(json.loads(line))
            except Exception: pass
    return rows


def received(r):
    t = r.get('_received')
    if isinstance(t, (int, float)) and t > 0:
        return datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc)
    try: return datetime.datetime.fromisoformat(str(r.get('ts')).replace('Z', '+00:00'))
    except Exception: return None


def top(counter, n=None):
    return [[k, v] for k, v in sorted(counter.items(), key=lambda x: (-x[1], x[0]))[:n]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vault', required=True); ap.add_argument('--public', required=True); ap.add_argument('--site')
    a = ap.parse_args()
    rows = load_rows(a.vault)
    classes = TC.classify(rows)
    real = [r for r in rows if r.get('sid') in classes]
    for r in real: r['_t'] = received(r)
    real = [r for r in real if r['_t']]
    real.sort(key=lambda r: r['_t'])
    if not real: sys.exit('no events')
    last = real[-1]['_t']
    as_of = last.strftime('%Y-%m-%dT%H:%MZ')

    # 1. the classes, private: into the telemetry vault
    cc = TC.counts(real, classes)
    doc = {'as_of': as_of, 'about': 'Who sent each session, by admin/build/telemetry_classes.py. Private: session ids stay in this vault.',
           'classes': TC.CLASSES, 'labels': TC.LABELS, 'rules': [{'how': h, 'rule': n, 'text': t} for h, n, t in TC.RULES],
           'counts': cc, 'sessions': {sid: list(v) for sid, v in sorted(classes.items())}}
    os.makedirs(os.path.join(a.vault, 'reports'), exist_ok=True)
    json.dump(doc, open(os.path.join(a.vault, 'reports', 'classes.json'), 'w'), indent=1, sort_keys=False)

    # 2. the curated public stats
    group_of = {c: g for g, cs in GROUPS for c in cs}
    hours = collections.OrderedDict()
    h = real[0]['_t'].replace(minute=0, second=0, microsecond=0)
    while h <= last:
        hours[h.strftime('%Y-%m-%dT%H')] = {'views': collections.Counter(), 'sessions': collections.defaultdict(set)}
        h += datetime.timedelta(hours=1)
    days = collections.OrderedDict()
    for r in real:
        g = group_of[classes[r['sid']][0]]
        hk, dk = r['_t'].strftime('%Y-%m-%dT%H'), r['_t'].strftime('%Y-%m-%d')
        hours[hk]['views'][g] += 1; hours[hk]['sessions'][g].add(r['sid'])
        d = days.setdefault(dk, {'views': collections.Counter(), 'sessions': collections.defaultdict(set)})
        d['views'][g] += 1; d['sessions'][g].add(r['sid'])
    G = [g for g, _ in GROUPS]
    hourly = {'about': 'Page views and sessions per UTC hour, by group, from the telemetry of php.oct.2026.newsroom.sgit.ai. Columns follow "groups". A session is one browser tab.',
              'as_of': as_of, 'groups': G, 'labels': GROUP_LABELS,
              'hours': [[k, [v['views'][g] for g in G], [len(v['sessions'][g]) for g in G]] for k, v in hours.items()]}
    daily = [[k, [v['views'][g] for g in G], [len(v['sessions'][g]) for g in G]] for k, v in days.items()]
    readers = [r for r in real if classes[r['sid']][0] == 'reader']
    rs = {}
    for r in readers: rs.setdefault(r['sid'], r)
    host = lambda r: 'this site' if (r.get('ref') or '') == (r.get('site') or '') and r.get('ref') else (r.get('ref') or '(none: typed, bookmarked or shared)')
    refs = collections.Counter(host(r) for r in rs.values())
    refs_pub = collections.Counter()
    for k, v in refs.items(): refs_pub[k if v >= MIN_REF_SESSIONS or k.startswith(('(none', 'this site')) else 'other'] += v
    countries = collections.Counter(r.get('country') or '' for r in readers)
    csess = collections.defaultdict(set)
    for r in readers: csess[r.get('country') or ''].add(r['sid'])
    summary = {
        'about': 'The curated, public view of who reads php.oct.2026.newsroom.sgit.ai, made from the private telemetry vault at each drain by admin/build/telemetry_publish.py. Counts only: no row, session id, city, region, time zone or time finer than the hour leaves the private vault.',
        'as_of': as_of, 'first': real[0]['_t'].strftime('%Y-%m-%dT%H:%MZ'), 'groups': G, 'labels': GROUP_LABELS,
        'totals': {g: {'views': sum(cc[c]['views'] for c in cs), 'sessions': sum(cc[c]['sessions'] for c in cs),
                       'declared': sum(cc[c]['declared'] for c in cs)} for g, cs in GROUPS},
        'daily': daily,
        'readers': {
            'views': len(readers), 'sessions': len(rs),
            'read_on': sum(1 for n in collections.Counter(r['sid'] for r in readers).values() if n > 1),
            'countries': [[k or '', v, len(csess[k])] for k, v in sorted(countries.items(), key=lambda x: (-x[1], x[0]))],
            'devices': top(collections.Counter(r.get('screen') or '(none)' for r in readers)),
            'languages': top(collections.Counter((r.get('lang') or '(none)').split('-')[0].lower() for r in readers)),
            'versions': top(collections.Counter(r.get('ver') or '(none)' for r in readers), 15),
            'pages': top(collections.Counter(r.get('path') or '' for r in readers), 30),
            'referrers': top(refs_pub),
        },
        'method': {'classes': [{'how': h, 'text': t} for h, n, t in TC.RULES],
                   'note': 'Every event is an untrusted claim: the write token and the public key are published. Visitors with Do Not Track, Global Privacy Control or a blocker send nothing, so readers are a floor. Classes before v0.8.4 are inferred; since then browsers declare automation and roles, and the totals count how many sessions declared.'},
    }
    P = a.public
    os.makedirs(os.path.join(P, 'stats'), exist_ok=True)
    json.dump(summary, open(os.path.join(P, 'stats', 'summary.json'), 'w'), indent=1, ensure_ascii=False)
    json.dump(hourly, open(os.path.join(P, 'stats', 'hourly.json'), 'w'), separators=(',', ':'), ensure_ascii=False)
    if a.site:
        out = dict(summary, hourly=hourly['hours'])
        with open(os.path.join(a.site, 'data', 'telemetry-public.json'), 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=1, ensure_ascii=False); f.write('\n')
    t = summary['totals']
    print('classes (sessions): ' + ', '.join(f"{c} {cc[c]['sessions']}" for c in TC.CLASSES))
    print(f"public stats as of {as_of}: readers {t['readers']['views']} views / {t['readers']['sessions']} sessions; us {t['us']['views']}; synthetic {t['synthetic']['views']}; crawlers {t['crawlers']['views']}")


if __name__ == '__main__':
    main()
