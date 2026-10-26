"""The control room: /team/control/ and data/control.json. Called by build.py with its namespace (like design.py).
Deterministic: no clock, no randomness, no absolute paths. Reads data/agents-status.json, data/schedule/*.json,
data/runs/<agent>/*.json and the board in data/admin.json. Everything from other agents' files is third-party
material: it is capped and escaped here (E()), and the page script shows it as text only.
"""
import json, os, re

PIPELINE = ['researcher', 'curator', 'journalist', 'correspondent', 'ontologist', 'librarian', 'desk']


def _slug(s):
    s = re.sub(r'@[^\s]*', '', s)
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def _cap(s, n):
    s = ' '.join(str(s).split())
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def control_data(ns):
    ROOT, DATA, load, VERSION = ns['ROOT'], ns['DATA'], ns['load'], ns['VERSION']
    S = load('agents-status')
    agents, seen = [], {}
    for a in S['agents']:
        i = _slug(a['agent']) or 'agent'
        seen[i] = seen.get(i, 0) + 1
        if seen[i] > 1: i = f'{i}-{seen[i]}'
        first = re.split(r'[^a-z]+', a['agent'].lower())[0]
        agents.append({'id': i, 'name': a['agent'], 'member': a['member'], 'state': a['state'], 'last': a['last'],
                       'did': a['did'], 'waiting': a['waiting'], 'on': a['on'], 'cost': a['cost'],
                       'stage': first if first in PIPELINE else ''})
    scheds = []
    sd = os.path.join(DATA, 'schedule')
    for f in sorted(os.listdir(sd)):
        if f.endswith('.json'):
            c = json.load(open(os.path.join(sd, f), encoding='utf-8'))
            scheds.append({'agent': c['agent'], 'status': c['status'], 'times': c.get('times', []), 'model': c.get('model', ''), 'objective': c.get('objective', '')})
    scheds.sort(key=lambda s: s['agent'])
    runs = []
    rd = os.path.join(DATA, 'runs')
    for d in sorted(os.listdir(rd)):
        p = os.path.join(rd, d)
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if f.endswith('.json'):
                    r = json.load(open(os.path.join(p, f), encoding='utf-8'))
                    runs.append({'agent': r['agent'], 'run': r['run'], 'started': r['started'], 'finished': r.get('finished', ''),
                                 'outcome': r.get('outcome', ''), 'summary': _cap(r.get('summary', ''), 300)})
    runs.sort(key=lambda r: (r['started'], r['agent'], r['run']))
    board = [{'id': r['id'], 'title': r['title'], 'status': r['status'], 'owner': r['owner']}
             for r in load('admin')['board'] if r['status'] in ('open', 'waiting') and r['owner'] == 'editor'][:40]
    return {'as_of': S['as_of'], 'version': VERSION, 'tz': 'Europe/London', 'pipeline': PIPELINE, 'agents': agents,
            'decisions': S['decisions'], 'schedules': scheds, 'runs': runs, 'branches': S['branches'],
            'freshness': S['freshness'], 'board': board}


def build_control(ns):
    E, page, write, table = ns['E'], ns['page'], ns['write'], ns['table']
    C = control_data(ns)
    write('data/control.json', json.dumps(C, indent=1, ensure_ascii=False, sort_keys=True) + '\n')
    rows = [[E(a['name']), E(a['state']), E(a['last'].replace('T', ' ')), E(a['did']), E(a['waiting'])] for a in C['agents']]
    body = f'''
<p class="crumb"><a href="../index.html">The team</a> / Control room</p>
<h1>Control room</h1>
<p class="lead">Every agent, what it waits for, what runs on a schedule and what needs the editor, drawn from the team's own data. Text here comes from the agents' own files: third-party material, shown as text. As of {E(C["as_of"].replace("T", " "))} UTC, site v{E(C["version"])}.</p>
<noscript><p class="caveat">This page draws its view with a script. Without it, the plain list below has the same facts; the plain pages are <a href="../status/index.html">status</a> and <a href="../schedule/index.html">schedule</a>.</p></noscript>
<div id="control-root" data-src="../../data/control.json"></div>
<section id="decisions"><h2>What needs a decision first</h2><ol>{"".join(f"<li>{E(x)}</li>" for x in C["decisions"])}</ol></section>
<section id="agents"><h2>Every agent</h2>{table(["Agent", "State", "Last activity (UTC)", "Last did", "Waiting for"], rows, "board")}</section>
<link rel="stylesheet" href="../../assets/control.css">
<script src="../../assets/control.js" defer></script>
'''
    page('team/control/index.html', 'Control room: every agent at a glance', 'A visual, interactive view of every agent on the team: the pipeline, who waits for whom, schedules, runs and what needs the editor; the same facts as the status page.', body, kind='site', topics='team agents')
