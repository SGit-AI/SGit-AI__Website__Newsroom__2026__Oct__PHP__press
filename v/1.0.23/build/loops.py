"""Every loop: /views/loops/, the pipeline from the researcher to the correspondent, one row per full loop.

Called by build.py with its namespace (like control.py and design.py). Deterministic: no clock, no randomness.
Reads data/loops.json (written by admin/build/export_loops.py at each correspondent wake: the evidence vault's
commits, every release, the repository's size, the next wakes), data/runs/<role>/*.json, data/schedule/<role>.json,
data/vault.json, data/source-watch.json, data/claim-review.json and data/desk.json. Every string from those files
reaches HTML through E(); the charts are inline SVG built from numbers and escaped labels, with no script.

A loop is one evidence vault head taken all the way: captured by the researcher, promoted by the curator into the
evidence vault, published by the journalist, and reviewed by the correspondent. It is counted once, at the head the
correspondent reviewed; more releases of the same head, or more reviews of it, are duplicates within that loop.
Before 24 October one Opus session published and reviewed in the same release: those loops are marked so.
Written by correspondent@php.newsroom, 25 October 2026, at the editor's request.
"""
import glob, json, os, re
from datetime import datetime, timedelta, timezone

ROLES = [('researcher', 'Researcher', 'var(--g-act)'), ('curator', 'Curator', 'var(--g-understand)'),
         ('journalist', 'Journalist', 'var(--g-communicate)'), ('correspondent', 'Correspondent', 'var(--g-decide)')]
COLOUR = {r: c for r, _, c in ROLES}
PRE = ('claude-journalist', 'correspondent@php.newsroom')  # agents that published and reviewed in one session


def _t(s):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})', s or '')
    return datetime(*map(int, m.groups()), tzinfo=timezone.utc) if m else None


def _short(s):
    t = _t(s)
    return t.strftime('%-d %b %H:%M UTC') if t else '–'


def _dur(a, b):
    ta, tb = _t(a), _t(b)
    if not (ta and tb) or tb < ta:
        return None
    return int((tb - ta).total_seconds() // 60)


def _hm(m):
    return '–' if m is None else (f'{m // 60} h {m % 60:02d} min' if m >= 60 else f'{m} min')


def _runs(root, role):
    out = []
    for f in sorted(glob.glob(os.path.join(root, 'data', 'runs', role, '*.json'))):
        try:
            out.append(json.load(open(f, encoding='utf-8')))
        except ValueError:
            pass
    return out


def loops_data(ns):
    ROOT = ns['ROOT']
    L = json.load(open(os.path.join(ROOT, 'data', 'loops.json'), encoding='utf-8'))
    vault, rel = L['vault'], L['releases']
    idx = {v['id']: i for i, v in enumerate(vault)}
    live = {}
    for r in rel:
        h = r.get('vault_head')
        if h and h not in live:
            live[h] = r
    dup = {}
    for r in rel:
        dup[r.get('vault_head')] = dup.get(r.get('vault_head'), 0) + 1
    # the head each correspondent run reviewed: the head the site served when the run started
    reviews = {}
    for run in _runs(ROOT, 'correspondent'):
        served = [r for r in rel if r['at'] <= (run.get('started') or '')[:16] + 'Z' and r.get('vault_head')]
        if served:
            reviews.setdefault(served[-1]['vault_head'], []).append(run)
    loops, prev = [], -1
    for h in sorted(live, key=lambda h: idx.get(h, -1)):
        if h not in idx:
            continue
        r, i = live[h], idx[h]
        commits = vault[prev + 1:i + 1]
        prev = i
        cur = [c for c in commits if c.get('by', '').startswith('curator')]
        queues = sorted({c['queue_at'] for c in cur if c.get('queue_at')})  # the researcher's own times; a curator wake time is not one
        rv = sorted(reviews.get(h, []), key=lambda x: x.get('started', ''))
        if r['agent'].startswith('journalist'):
            kind = 'pipeline'
            by_review, at_review = (('correspondent@php.newsroom', rv[0].get('finished') or rv[0].get('started')) if rv else (None, None))
        elif r['agent'] in PRE:
            kind, by_review, at_review = 'one session', 'the Opus journalist, in the same release', r['at']
        else:
            kind, by_review, at_review = 'before the pipeline', None, None
        start = queues[0] if queues else (cur[0]['at'] if cur else commits[0].get('at'))
        loops.append({
            'head': h, 'kind': kind, 'commits': len(commits), 'curator_commits': len(cur),
            'by': sorted({c.get('by') or 'merge' for c in commits}),
            'sources': sum(c.get('sources', 0) for c in commits), 'snapshots': sum(c.get('snapshots', 0) for c in commits),
            'claims': sum(c.get('claims', 0) for c in commits), 'queues': queues, 'start': start,
            'curated_first': commits[0].get('at'), 'curated': vault[i].get('at'), 'live': r['at'], 'live_version': r['version'],
            'live_by': r['agent'] or 'not named', 'releases_of_head': dup.get(h, 0), 'latest_capture': r.get('latest_capture'),
            'served_sources': r.get('sources'), 'reviewed': at_review, 'reviewed_by': by_review, 'reviews': len(rv),
            'closed': at_review is not None,
            'lat': {'research': _dur(start, vault[i].get('at')) if queues else None, 'publish': _dur(vault[i].get('at'), r['at']),
                    'review': _dur(r['at'], at_review) if kind == 'pipeline' else None, 'total': _dur(start, at_review or None)},
        })
    head_live = max(live, key=lambda h: idx.get(h, -1)) if live else None
    unpublished = vault[idx[head_live] + 1:] if head_live in idx else []
    open_loop = None
    if unpublished:
        open_loop = {'stage': 'curated, not yet published', 'commits': len(unpublished), 'since': unpublished[0].get('at'), 'head': unpublished[-1]['id']}
    elif loops and loops[-1]['kind'] == 'pipeline' and not loops[-1]['closed']:
        open_loop = {'stage': 'published, not yet reviewed', 'commits': 0, 'since': loops[-1]['live'], 'head': loops[-1]['head']}
    return L, loops, open_loop


def _swimlane(E, L, loops, runs):
    """A time chart: one lane per role, what happened (filled) and what is scheduled next (hollow)."""
    end = _t(L['exported_at']) + timedelta(hours=22)
    start = end - timedelta(hours=60)
    W, X0, LH, TOP = 1000, 118, 46, 30
    lanes = ROLES + [('release', 'Releases to dev', 'var(--dim)')]
    H = TOP + LH * len(lanes) + 26

    def x(s):
        t = _t(s)
        if not t or t < start or t > end:
            return None
        return X0 + (W - X0 - 10) * (t - start).total_seconds() / (end - start).total_seconds()
    g = []
    t = start.replace(minute=0) + timedelta(hours=(6 - start.hour % 6) % 6)
    while t <= end:
        xx = x(t.strftime('%Y-%m-%dT%H:%MZ'))
        if xx is not None:
            g.append(f'<line x1="{xx:.1f}" y1="{TOP - 6}" x2="{xx:.1f}" y2="{H - 22}" style="stroke:var(--line)" />'
                     f'<text x="{xx:.1f}" y="{H - 8}" text-anchor="middle" font-size="11" style="fill:var(--dim)">{E(t.strftime("%-d %b %H:%M"))}</text>')
        t += timedelta(hours=6)
    now = x(L['exported_at'])
    if now is not None:
        g.append(f'<line x1="{now:.1f}" y1="{TOP - 14}" x2="{now:.1f}" y2="{H - 22}" style="stroke:var(--accent);stroke-dasharray:4 3" />'
                 f'<text x="{now + 4:.1f}" y="{TOP - 16}" font-size="11" style="fill:var(--accent)">exported {E(_short(L["exported_at"]))}</text>')
    y = {}
    for n, (role, label, col) in enumerate(lanes):
        yy = TOP + LH * n + LH / 2
        y[role] = yy
        g.append(f'<text x="6" y="{yy + 4:.0f}" font-size="12" font-weight="600" style="fill:{col}">{E(label)}</text>'
                 f'<line x1="{X0}" y1="{yy:.0f}" x2="{W - 10}" y2="{yy:.0f}" style="stroke:var(--line)" />')

    def dot(role, s, title, hollow=False, r=5):
        xx = x(s)
        if xx is None:
            return
        col = COLOUR.get(role, 'var(--dim)')
        st = f'fill:var(--panel);stroke:{col};stroke-width:2' if hollow else f'fill:{col}'
        g.append(f'<circle cx="{xx:.1f}" cy="{y[role]:.0f}" r="{r}" style="{st}"><title>{E(title)}</title></circle>')
    # loop connectors first, under the dots
    for lp in loops:
        pts = [(x(lp['queues'][0]) if lp['queues'] else None, y['researcher']), (x(lp['curated']), y['curator']),
               (x(lp['live']), y['journalist']), (x(lp['reviewed']) if lp['kind'] == 'pipeline' else None, y['correspondent'])]
        pts = [(a, b) for a, b in pts if a is not None]
        if len(pts) > 1:
            g.insert(0, f'<polyline points="{" ".join(f"{a:.1f},{b:.0f}" for a, b in pts)}" style="fill:none;stroke:var(--accent);stroke-width:2;opacity:.45" />')
    for c in L['vault']:
        if c.get('queue_at'):
            dot('researcher', c['queue_at'], f'source-watch queue of {_short(c["queue_at"])}, named by the curator')
        if c.get('by', '').startswith('curator'):
            dot('curator', c['at'], f'{c["id"]}: {c.get("sources", 0)} sources, {c.get("claims", 0)} claims')
    for r in L['releases']:
        xx = x(r['at'])
        if xx is not None:
            g.append(f'<line x1="{xx:.1f}" y1="{y["release"] - 7:.0f}" x2="{xx:.1f}" y2="{y["release"] + 7:.0f}" style="stroke:var(--dim);stroke-width:1.5"><title>v{E(r["version"])} {E(_short(r["at"]))} {E(r["agent"])}</title></line>')
    for lp in loops:
        if lp['kind'] != 'before the pipeline':
            dot('journalist', lp['live'], f'v{lp["live_version"]}: evidence {lp["head"]} live, by {lp["live_by"]}')
        if lp['kind'] == 'pipeline' and lp['reviewed']:
            dot('correspondent', lp['reviewed'], f'reviewed {lp["head"]}')
    for role in ('journalist', 'correspondent'):
        for run in runs.get(role, []):
            dot(role, run.get('started'), f'{role} run {run.get("run")}: {run.get("outcome")}', r=3)
    for role, _, _ in ROLES:
        for s in L['next'].get(role, {}).get('next', []):
            dot(role, s, f'{role}: next scheduled wake {_short(s)} ({L["next"][role]["status"]})', hollow=True)
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="When each role ran and when it runs next" style="width:100%;height:auto;min-width:640px">{"".join(g)}</svg>')


def _flow(E, L, D, runs):
    """The pipeline as a picture: who, model, reads, writes, when."""
    n = L['next']
    vs = D['vault']
    sw = D['source-watch']
    rows = [
        ('researcher', 'Researcher', n.get('researcher', {}), 'reads the live websites', f'the source-watch vault 7r83qic5 ({sw.get("pages")} pages, {sw.get("snapshots")} snapshots at its last export)'),
        ('curator', 'Curator', n.get('curator', {}), 'reads only the source watch, each capture', f'the evidence vault 3ytzxm3g ({vs["sources"]} sources, {vs["captures"]} captures, {len(L["vault"])} commits)'),
        ('journalist', 'Journalist', n.get('journalist', {}), 'reads only the evidence vault', 'the site: export, verdicts, compromise and as-of lines, a release to dev'),
        ('correspondent', 'Correspondent', n.get('correspondent', {}), 'reads what went live, against the captures', 'corrections (catches), the state of affairs, readers\' answers, the rules'),
    ]
    W, BH, GAP = 640, 74, 34
    H = len(rows) * (BH + GAP) + 60
    g = ['<defs><marker id="lp-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" style="fill:var(--dim)" /></marker></defs>']
    for k, (role, label, card, reads, writes) in enumerate(rows):
        y0 = 10 + k * (BH + GAP)
        col = COLOUR[role]
        times = ', '.join(card.get('times_london', []))
        g.append(f'<rect x="4" y="{y0}" width="{W - 8}" height="{BH}" rx="9" style="fill:var(--panel);stroke:{col};stroke-width:2" />'
                 f'<rect x="4" y="{y0}" width="10" height="{BH}" rx="4" style="fill:{col}" />'
                 f'<text x="26" y="{y0 + 22}" font-size="16" font-weight="700" style="fill:{col}">{k + 1}. {E(label)}</text>'
                 f'<text x="{W - 14}" y="{y0 + 22}" font-size="12" text-anchor="end" style="fill:var(--dim)">{E(card.get("model", ""))} · {E(card.get("status", ""))} · {E(times)} London</text>'
                 f'<text x="26" y="{y0 + 44}" font-size="13" style="fill:currentColor">Reads: {E(reads)}</text>'
                 f'<text x="26" y="{y0 + 63}" font-size="13" style="fill:currentColor">Writes: {E(writes[:96])}</text>')
        g.append(f'<line x1="{W / 2}" y1="{y0 + BH + 2}" x2="{W / 2}" y2="{y0 + BH + GAP - 4}" style="stroke:var(--dim);stroke-width:2" marker-end="url(#lp-arrow)" />')
    y0 = 10 + len(rows) * (BH + GAP)
    g.append(f'<rect x="4" y="{y0}" width="{W - 8}" height="44" rx="9" style="fill:none;stroke:var(--g-study);stroke-dasharray:5 4" />'
             f'<text x="26" y="{y0 + 27}" font-size="13" style="fill:var(--g-study)">Then: the ontologist, the librarian and the desk update the graphs.</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="The pipeline: four roles in order" style="width:100%;max-width:760px;height:auto;color:var(--ink, inherit)">{"".join(g)}</svg>'


def _latency(E, loops):
    rows = [lp for lp in loops if lp['kind'] != 'before the pipeline'][-8:]
    if not rows:
        return ''
    segs = [('research', 'captured → curated', 'var(--g-act)'), ('publish', 'curated → live', 'var(--g-communicate)'), ('review', 'live → reviewed', 'var(--g-decide)')]
    mx = max(sum(lp['lat'][k] or 0 for k, _, _ in segs) for lp in rows) or 1
    W, X0, BH = 640, 112, 22
    H = len(rows) * (BH + 10) + 40
    g = []
    for n, lp in enumerate(rows):
        y0 = 8 + n * (BH + 10)
        g.append(f'<text x="4" y="{y0 + 15}" font-size="12" style="fill:var(--dim)"><tspan font-family="monospace">{E(lp["head"][:8])}</tspan></text>')
        xx = X0
        for k, label, col in segs:
            m = lp['lat'][k]
            if not m:
                continue
            w = (W - X0 - 70) * m / mx
            g.append(f'<rect x="{xx:.1f}" y="{y0}" width="{max(w, 1.5):.1f}" height="{BH}" style="fill:{col}"><title>{E(label)}: {E(_hm(m))}</title></rect>')
            xx += w
        tot = sum(lp['lat'][k] or 0 for k, _, _ in segs)
        g.append(f'<text x="{xx + 6:.1f}" y="{y0 + 15}" font-size="12" style="fill:currentColor">{E(_hm(tot))}{"" if lp["kind"] == "pipeline" else " *"}</text>')
    yl = H - 16
    lx = X0
    for _, label, col in segs:
        g.append(f'<rect x="{lx}" y="{yl - 10}" width="12" height="12" style="fill:{col}" /><text x="{lx + 16}" y="{yl}" font-size="12" style="fill:var(--dim)">{E(label)}</text>')
        lx += 160
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="How long each loop took, by stage" style="width:100%;max-width:760px;height:auto">{"".join(g)}</svg>'


def _growth(E, L):
    """Sources served by the site, release by release."""
    pts = [(r['at'], r['sources']) for r in L['releases'] if r.get('sources')]
    if len(pts) < 2:
        return ''
    t0, t1 = _t(pts[0][0]), _t(pts[-1][0])
    mx = max(s for _, s in pts)
    W, H, X0, Y0 = 640, 200, 44, 170
    span = (t1 - t0).total_seconds() or 1

    def xy(a, s):
        return X0 + (W - X0 - 10) * (_t(a) - t0).total_seconds() / span, Y0 - (Y0 - 14) * s / mx
    path, last = [], None
    for a, s in pts:
        px, py = xy(a, s)
        if last is not None:
            path.append(f'L{px:.1f},{last:.1f}')
        path.append(f'{"M" if not path else "L"}{px:.1f},{py:.1f}')
        last = py
    g = [f'<line x1="{X0}" y1="{Y0}" x2="{W - 10}" y2="{Y0}" style="stroke:var(--line)" />',
         f'<text x="{X0 - 6}" y="{Y0}" font-size="11" text-anchor="end" style="fill:var(--dim)">0</text>',
         f'<text x="{X0 - 6}" y="18" font-size="11" text-anchor="end" style="fill:var(--dim)">{mx}</text>',
         f'<path d="{" ".join(path)}" style="fill:none;stroke:var(--g-understand);stroke-width:2.5" />',
         f'<text x="{X0}" y="{H - 6}" font-size="11" style="fill:var(--dim)">{E(_short(pts[0][0]))}</text>',
         f'<text x="{W - 10}" y="{H - 6}" font-size="11" text-anchor="end" style="fill:var(--dim)">{E(_short(pts[-1][0]))}</text>']
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Sources the site served, release by release" style="width:100%;max-width:760px;height:auto">{"".join(g)}</svg>'


def last_run(ns):
    """The latest finished run record of any agent: when an agent last worked on the site."""
    best = ('', '')
    for f in glob.glob(os.path.join(ns['ROOT'], 'data', 'runs', '*', '*.json')):
        try:
            r = json.load(open(f, encoding='utf-8'))
        except ValueError:
            continue
        t = r.get('finished') or r.get('started') or ''
        if t > best[0]:
            best = (t, r.get('agent', ''))
    return best


def build_loops(ns):
    E, U, page, section, table, stat, D = ns['E'], ns['U'], ns['page'], ns['section'], ns['table'], ns['stat'], ns['D']
    ROOT = ns['ROOT']
    path = 'views/loops/index.html'
    L, loops, open_loop = loops_data(ns)
    runs = {r: _runs(ROOT, r) for r, _, _ in ROLES}
    full = [lp for lp in loops if lp['closed']]
    pipe = [lp for lp in loops if lp['kind'] == 'pipeline']
    last = full[-1] if full else None
    nx = L['next']

    def first_after(role, t):
        return next((s for s in nx.get(role, {}).get('next', []) if s > (t or '')), None)
    # the next loop, if every role wakes on its card: researcher, then curator, journalist, correspondent in turn
    chain, t = [], L['exported_at']
    for role, label, _ in ROLES:
        t = first_after(role, t)
        chain.append((role, label, t))

    def card(title, rows, tone=''):
        return f'<div class="card lp-card {tone}"><p class="eyebrow">{E(title)}</p><dl class="lp-dl">{"".join(f"<dt>{E(a)}</dt><dd>{b}</dd>" for a, b in rows)}</dl></div>'
    cards = []
    if last:
        cards.append(card('The last full loop', [
            ('Evidence head', f'<code>{E(last["head"])}</code>, latest capture {E(_short(last["latest_capture"]))}'),
            ('Researcher', E(', '.join(_short(q) for q in last['queues']) or 'not named') + ' (queue times the curator names)'),
            ('Curator', f'{last["curator_commits"]} commits, {last["sources"]} sources, {last["claims"]} claims; head {E(_short(last["curated"]))}'),
            ('Journalist', f'live in v{E(last["live_version"])} at {E(_short(last["live"]))} by {E(last["live_by"])}'),
            ('Correspondent', f'{E(_short(last["reviewed"]))} by {E(last["reviewed_by"] or "–")}'),
            ('Took', E(_hm(last['lat']['total']))),
        ], 'lp-done'))
    if open_loop:
        cards.append(card('In progress', [('Stage', E(open_loop['stage'])), ('Since', E(_short(open_loop['since']))),
                                          ('Head', f'<code>{E(open_loop["head"])}</code>'), ('Vault commits waiting', E(str(open_loop['commits'])))], 'lp-open'))
    else:
        cards.append(card('In progress', [('Stage', 'nothing waiting: the evidence vault head is live and reviewed'),
                                          ('Vault read', E(_short(L.get('vault_read_at'))))], 'lp-open'))
    cards.append(card('The next loop, if every role wakes on its card', [
        (label, f'{E(_short(at))} <span class="small">({E(nx.get(role, {}).get("status", "no card"))})</span>') for role, label, at in chain], 'lp-next'))

    lrows = []
    for n, lp in reversed(list(enumerate(loops, 1))):
        status = ('<span class="st st-confirmed">full loop</span>' if lp['kind'] == 'pipeline' and lp['closed'] else
                  '<span class="st st-reported">published, not reviewed</span>' if lp['kind'] == 'pipeline' else
                  '<span class="st st-unverified">one session</span>' if lp['kind'] == 'one session' else '<span class="st st-unverified">before the pipeline</span>')
        lrows.append([str(n), f'<code>{E(lp["head"])}</code><div class="small">capture to {E(_short(lp["latest_capture"]))}; {E(str(lp["served_sources"] or "–"))} sources</div>',
                      E(', '.join(_short(q) for q in lp['queues']) or '–'),
                      f'{lp["commits"]} commits ({E(", ".join(lp["by"]))})<div class="small">+{lp["sources"]} sources, +{lp["snapshots"]} snapshots, {lp["claims"]} claims; head {E(_short(lp["curated"]))}</div>',
                      f'v{E(lp["live_version"])}, {E(_short(lp["live"]))}<div class="small">{E(lp["live_by"])}; {lp["releases_of_head"]} releases at this head (later ones are other work)</div>',
                      (f'{E(_short(lp["reviewed"]))}<div class="small">{E(lp["reviewed_by"] or "")}{"; " + str(lp["reviews"]) + " reviews" if lp["reviews"] > 1 else ""}</div>' if lp['reviewed'] else '–'),
                      E(_hm(lp['lat']['total'])), status])
    loops_table = table(['#', 'Evidence head', 'Researcher (queue)', 'Curator', 'Journalist (live)', 'Correspondent (review)', 'Took', 'Status'], lrows, 't lp-t')

    # blind spots, computed from what this repository can and cannot see
    blind = []
    for role in ('researcher', 'curator'):
        if not runs.get(role):
            blind.append(f'The {role} writes no run record to this repository (data/runs/{role}/ is empty): its wakes are seen only through '
                         + ('the queue times the curator names in its vault commits.' if role == 'researcher' else 'the evidence vault\'s commits, read at each correspondent wake.'))
    sw_last = max((r.get('finished') or '' for r in D['source-watch'].get('runs', [])), default='')
    if sw_last and sw_last < L['exported_at'][:10]:
        blind.append(f'The source watch\'s own export (data/source-watch.json) was last read {_short(sw_last)}; its pack vault\'s read key is not published, so its pages and snapshots here are that day\'s.')
    for role in ('journalist', 'correspondent'):
        st = nx.get(role, {}).get('status')
        if st != 'active':
            blind.append(f'The {role}\'s card is "{st}": no scheduled task runs it yet, so a loop closes only when a session is started by hand.')
    skipped = [c for c in L['vault'] if c.get('by', '').startswith('curator') and c['id'] not in {lp['head'] for lp in loops}]
    if skipped:
        blind.append(f'{len(skipped)} curator commits never went live on their own: each was folded into a later export (normal, but a head reviewed is not every commit read).')
    if pipe and not pipe[-1]['closed']:
        blind.append(f'The latest published head, {pipe[-1]["head"]}, has no correspondent review yet.')
    blind.append('Times of the researcher are the queue times the curator writes, not the researcher\'s own clock; a wake that found nothing to queue leaves no trace here.')
    blind.append('Run records say when a wake started and finished; a wake that did nothing need not commit (AGENTS.md, section 7), so quiet wakes are invisible.')

    vs, sw, R, cr = D['vault'], D['source-watch'], L['repo'], D['claim-review']
    verdicts = {}
    for r in cr['reviews']:
        verdicts[r['verdict']] = verdicts.get(r['verdict'], 0) + 1
    stats_e = ''.join([stat(vs['sources'], 'sources in the evidence vault', 'sources/index.html', 2), stat(vs['captures'], 'captures (saved pages)', None, 2),
                       stat(vs['hashed_files'], 'files with a sha256', None, 2), stat(len(L['vault']), 'evidence vault commits', None, 2),
                       stat(sw.get('pages', '–'), f'pages the source watch tracks (as of {_short(sw_last)})', 'vaults/source-watch/index.html', 2),
                       stat(sw.get('snapshots', '–'), 'source-watch snapshots (same date)', None, 2)])
    stats_r = ''.join([stat(len(D['vault-claims']), 'claims in the evidence vault', 'claims/review/index.html', 2),
                       stat(len(cr['reviews']), 'verdicts: ' + ', '.join(f'{v} {k}' for k, v in sorted(verdicts.items())), 'claims/review/index.html', 2),
                       stat(len(D['desk'].get('catches', [])), 'corrections by the correspondent (catches)', 'views/desk/index.html', 2),
                       stat(sum(len(v) for v in runs.values()), 'run records of the four roles', 'team/schedule/index.html', 2)])
    stats_s = ''.join([stat(len(L['releases']), 'releases to dev', 'admin/versions.html', 2), stat(R['commits'], 'commits on dev', None, 2),
                       stat(R['pages'], 'HTML pages', None, 2), stat(R['twins'], 'markdown twins', None, 2),
                       stat(f'{R["bytes"] / 1e6:.0f} MB', f'in {R["files"]} tracked files', None, 2),
                       stat(f'{R["data_bytes"] / 1e6:.1f} MB', f'of data, {R["data_files"]} JSON files', None, 2), stat(R['build_lines'], 'lines in build.py', None, 2)])
    rr = []
    for role, label, _ in ROLES:
        rs = runs.get(role, [])
        lr = rs[-1] if rs else None
        rr.append([E(label), E(nx.get(role, {}).get('status', 'no card')), E(nx.get(role, {}).get('model', '')),
                   E(', '.join(nx.get(role, {}).get('times_london', []))), str(len(rs)),
                   (f'{E(_short(lr.get("started")))}, {E(lr.get("outcome", ""))}' if lr else '–'),
                   E(', '.join(_short(s) for s in nx.get(role, {}).get('next', [])[:3]))])
    body = f'''
<h1>Every loop: from the researcher to the correspondent</h1>
<p class="lead">How this site keeps up with the evidence, in the open. Four roles take each piece of evidence in turn: the researcher saves the live websites, the curator promotes what matters into the evidence vault, the journalist publishes it to this site, and the correspondent reviews what went live and corrects it. One loop is one evidence head taken all the way round; when the correspondent has reviewed it, the loop is full. This page shows the last full loop, the one in progress, the next one due, every loop so far, and what the record cannot see.</p>
<div class="lp-cards">{"".join(cards)}</div>
{section("flow", "Who does what", f'<figure class="lp-fig">{_flow(E, L, D, runs)}<figcaption>Each role reads only the one before it. Times are London time, from each role\'s card in <code>data/schedule/</code>; the status says whether a scheduled task runs it.</figcaption></figure>')}
{section("time", "The last sixty hours, and the next day", f'<figure class="lp-fig lp-scroll">{_swimlane(E, L, loops, runs)}</figure><p class="small">Filled: what happened (the researcher\'s queue times as the curator names them, the curator\'s vault commits, the releases that put a new evidence head live, the correspondent\'s reviews, and every run record). Hollow: the next scheduled wakes. The faint line joins the stages of one loop. All times UTC; London left summer time on 25 October, so from then London is UTC.</p>')}
{section("loops", f"Every loop ({len(loops)}; {len([lp for lp in loops if lp['kind'] == 'pipeline' and lp['closed']])} full under the four-role pipeline)", loops_table + '<p class="small">A head released again, or reviewed again, is a duplicate within its loop, counted in the row, not a new loop. Loops 1 and 2 came from the first collectors; loops marked "one session" were published and reviewed by the same Opus session before the pipeline was decided on 24 October.</p>')}
{section("speed", "How long a loop takes", f'<figure class="lp-fig">{_latency(E, loops)}<figcaption>Minutes from the source-watch queue the curator names to the curated head, to the release that put it live, to the correspondent\'s review. * one session: no separate review.</figcaption></figure>')}
{section("roles", "The four roles: cards and runs", table(["Role", "Card", "Model", "Wakes (London)", "Run records", "Last run", "Next wakes (UTC)"], rr, "t lp-t"))}
{section("blind", "What this record cannot see", "<ul>" + "".join(f"<li>{E(b)}</li>" for b in blind) + "</ul>")}
{section("numbers", "The numbers", f'<h3>Evidence</h3><div class="stats">{stats_e}</div><figure class="lp-fig">{_growth(E, L)}<figcaption>Sources the site served, release by release.</figcaption></figure><h3>Review</h3><div class="stats">{stats_r}</div><h3>The site and its repository</h3><div class="stats">{stats_s}</div>')}
<p class="small">Built from <a href="../../data/loops.json">data/loops.json</a> (exported {E(_short(L["exported_at"]))} by <code>admin/build/export_loops.py</code>; the evidence vault read {E(_short(L.get("vault_read_at")))}), <code>data/runs/</code> and <code>data/schedule/</code>. The correspondent re-exports it at every wake. See also <a href="../desk/index.html">the desk</a> (what is still stale) and <a href="../../team/schedule/index.html">every schedule</a>.</p>
'''
    page(path, 'Every loop: from the researcher to the correspondent',
         f'The pipeline that keeps this site current, loop by loop: {len(loops)} loops, the last full one {"at " + _short(last["reviewed"]) if last else "not yet"}, the next one due, and what the record cannot see.', body)
