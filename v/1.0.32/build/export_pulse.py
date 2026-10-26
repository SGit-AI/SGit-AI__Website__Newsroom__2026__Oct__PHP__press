#!/usr/bin/env python3
"""Export the Pulse vault's public shape into data/pulse.json, for the separate /pulse/ section.

Usage: admin/build/export_pulse.py --from <clone of the Pulse vault (4klm5qlt)>

Pulse is pulse@newsroom's vault for the SGit newsroom: for each tracked vulnerability, a ladder of dated evidence of
exploitation and, beside it, counts of the attention it gets. It is not this site's evidence and covers more than PHP,
so the site keeps it in its own section and never mixes it into the PHP pages.

This copies no capture: no page text, no HTML, no screenshot, and no key. It writes the ladders' rungs with their
dates, the short quotes Pulse recorded for each rung with the capture path and sha256 they come from, the CVSS and
EPSS measurements, and the latest attention counts with how many feeds they were counted over. Deterministic: the
same vault head gives the same file, byte for byte.
"""
import argparse, glob, json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def load(v, p):
    with open(os.path.join(v, p), encoding='utf-8') as f:
        return json.load(f)


def cap(c):
    """A capture reference: where it is and its hash, never its content."""
    if not c:
        return None
    return {k: c.get(k) for k in ('vault', 'path', 'sha256', 'captured', 'url')}


def entry(e):
    return {'status': e.get('status'), 'date': e.get('date'), 'by': e.get('by'), 'quote': e.get('quote'),
            'basis': e.get('basis'), 'what_it_is': e.get('what_it_is'), 'capture': cap(e.get('capture'))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='vault', required=True)
    a = ap.parse_args()
    v = os.path.abspath(a.vault)
    log = subprocess.run(['sgit', 'history', 'log'], cwd=v, capture_output=True, text=True).stdout
    commits = [m.groups() for m in re.finditer(r'^\s*([0-9a-f]{12})(?: \(HEAD\))?\s+(.*?)\s{2,}[+~]', log, re.M)]
    if not commits:
        sys.exit('no commits read from sgit history log; is this a vault clone?')
    gap = load(v, 'index/gap.json')
    run = load(v, 'state/run.json')
    vulns = []
    for row in gap['rows']:
        cve = row['cve']
        d = os.path.join('vulns', cve)
        vuln, ladder, att = load(v, f'{d}/vuln.json'), load(v, f'{d}/ladder.json'), load(v, f'{d}/attention.json')
        rungs = []
        for k in sorted(ladder['rungs'], key=int):
            r = ladder['rungs'][k]
            rungs.append({'n': int(k), 'rung': r.get('rung') or gap['rungs'][k], 'status': r.get('status'), 'date': r.get('date'),
                          'last_checked': r.get('last_checked'), 'note': r.get('note'),
                          'evidence': [entry(e) for e in r.get('evidence', [])],
                          'reported_not_established': [entry(e) for e in r.get('reported_not_established', [])]})
        m = ladder.get('measurements', {})
        lat = att.get('latest', {})
        news = lat.get('news', {}) if isinstance(lat.get('news'), dict) else {}
        vulns.append({
            'cve': cve, 'vendor': vuln.get('vendor'), 'product': vuln.get('product'), 'flaw': vuln.get('flaw'),
            'kind_of_system': vuln.get('kind_of_system'), 'brand_name': vuln.get('brand_name'),
            'old_flaw_newly_listed': bool(vuln.get('old_flaw_newly_listed')), 'why_tracked': vuln.get('why_tracked'),
            'rungs_reached': row['evidence']['rungs_reached'], 'rungs': rungs,
            'cvss': [{k: c.get(k) for k in ('source', 'version', 'base_score')} for c in m.get('cvss', [])],
            'epss': {k: (m.get('epss') or {}).get(k) for k in ('score', 'percentile', 'date')} if m.get('epss') else None,
            'attention': {**{k: row['attention'].get(k) for k in ('news_items', 'news_items_en_us', 'feeds_checked', 'news_feeds_total', 'languages', 'countries', 'front_pages', 'agency_alerts', 'offline_advice')},
                          'window_since': lat.get('window_since'), 'about': news.get('about')},
        })
    out = {
        'about': 'The public shape of the Pulse vault (pulse@newsroom, for the SGit newsroom), exported by admin/build/export_pulse.py. Ladders, dates, attention counts and the short quotes Pulse recorded, each with the capture it comes from; no capture is copied and no key is kept here.',
        'vault_id': '4klm5qlt', 'agent': gap.get('agent'),
        'head': {'commit': commits[0][0], 'message': commits[0][1]}, 'commits': len(commits),
        'generated': gap.get('generated'), 'last_run': run.get('last_run'),
        'pulse_says': gap.get('about'), 'rungs': gap['rungs'], 'vulns': vulns,
    }
    p = os.path.join(ROOT, 'data', 'pulse.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write('\n')
    print(f'wrote data/pulse.json: vault head {out["head"]["commit"]}, {len(vulns)} vulnerabilities, last run {out["last_run"]}')


if __name__ == '__main__':
    main()
