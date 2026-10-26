"""What changed in the risk graph, release by release (CI-003.8), for /grc/changes/.

Every release commits the graph the build wrote, data/grc-graph.json. For each release whose graph differs from the
release before, data/grc-history.json keeps what changed: the nodes and edges added and removed, the edges whose basis
changed (inferred to confirmed, say), and the gaps opened and closed. The gaps are computed with today's rules
(data/grc-gaps.json) over each release's graph, so two releases are always compared by the same yardstick. Any two
releases can then be compared by replaying the changes between them, which the page does in the reader's browser.

    python3 admin/build/grc_history.py --all   fills every release that has a commit and no entry yet
    build.py, at a release's own build         the release being built, against the last release commit

Like release_pages.py: reads git; where git or the history is missing, nothing is computed and the stored entries stand.
"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
from release_pages import ROOT, git, releases  # noqa: E402

STORE = os.path.join(ROOT, 'data', 'grc-history.json')
GRAPH = 'data/grc-graph.json'


def reach(adj, start, kinds, verbs, within):
    """Breadth-first from start, in either direction, up to `within` steps (through `verbs` only, if named). The first
    node of one of `kinds` found, or None. The same walk as the gaps page (build.py's grc_reach)."""
    frontier, seen = [start], {start}
    for _ in range(within):
        nxt = []
        for x in frontier:
            for verb, y, kind in adj.get(x, ()):
                if y in seen or (verbs and verb not in verbs):
                    continue
                if kind in kinds:
                    return y
                seen.add(y); nxt.append(y)
        frontier = nxt
    return None


def gap_hits(nodes, edges, rules):
    """{rule id: sorted ids in the gap}; an edge rule lists edge keys 'from rel to'."""
    N = {n['id']: n for n in nodes}
    adj = {}
    for e in edges:
        if e['from'] in N and e['to'] in N:
            adj.setdefault(e['from'], []).append((e['rel'], e['to'], N[e['to']]['kind']))
            adj.setdefault(e['to'], []).append((e['rel'], e['from'], N[e['from']]['kind']))
    out = {}
    for rule in rules:
        if rule['of'] == 'edge':
            out[rule['id']] = sorted(key(e) for e in edges if basis(e) == rule['basis'])
            continue
        kinds = set(rule['reach'] if isinstance(rule['reach'], list) else [rule['reach']])
        verbs = set(rule.get('verbs') or [])
        out[rule['id']] = sorted(n['id'] for n in nodes if n['kind'] == rule['of'] and reach(adj, n['id'], kinds, verbs, rule['within']) is None)
    return out


def key(e):
    return f'{e["from"]} {e["rel"]} {e["to"]}'


def basis(e):
    # graphs before v0.10.13 carried no basis on an edge; that is 'unrecorded', not a basis that changed
    return (e.get('basis') or {}).get('kind', 'unrecorded')


def change(old, new, rules, version, against):
    """The entry for one release: what changed from old to new (graphs as dicts), or None if nothing did."""
    on = {n['id']: n for n in old['nodes']} if old else {}
    nn = {n['id']: n for n in new['nodes']}
    oe = {key(e): basis(e) for e in old['edges']} if old else {}
    ne = {key(e): basis(e) for e in new['edges']}
    og = gap_hits(old['nodes'], old['edges'], rules) if old else {r['id']: [] for r in rules}
    ng = gap_hits(new['nodes'], new['edges'], rules)
    edge_rules = {r['id'] for r in rules if r['of'] == 'edge'}
    d = {
        'version': version, 'against': against,
        'nodes_added': sorted(set(nn) - set(on)), 'nodes_removed': sorted(set(on) - set(nn)),
        'edges_added': [[k, ne[k]] for k in sorted(set(ne) - set(oe))], 'edges_removed': sorted(set(oe) - set(ne)),
        'basis_changed': [[k, oe[k], ne[k]] for k in sorted(set(oe) & set(ne)) if oe[k] != ne[k] and oe[k] != 'unrecorded'],
        'basis_recorded': [[k, ne[k]] for k in sorted(set(oe) & set(ne)) if oe[k] == 'unrecorded' and ne[k] != 'unrecorded'],
        'gaps_opened': {r: sorted(set(ng[r]) - set(og.get(r, []))) for r in ng if r not in edge_rules},
        'gaps_closed': {r: sorted(set(og.get(r, [])) - set(ng[r])) for r in ng if r not in edge_rules},
        'totals': {'nodes': len(nn), 'edges': len(ne), 'gaps': {r: len(v) for r, v in ng.items()},
                   'basis': {k: sum(1 for b in ne.values() if b == k) for k in sorted(set(ne.values()))}},
    }
    d['gaps_opened'] = {r: v for r, v in d['gaps_opened'].items() if v}
    d['gaps_closed'] = {r: v for r, v in d['gaps_closed'].items() if v}
    moved = any(d[k] for k in ('nodes_added', 'nodes_removed', 'edges_added', 'edges_removed', 'basis_changed', 'basis_recorded', 'gaps_opened', 'gaps_closed'))
    return d if moved else None


def labels_of(store, graph):
    for n in graph['nodes']:
        store['labels'][n['id']] = [n['kind'], n['label']]


def load():
    try:
        return json.load(open(STORE, encoding='utf-8'))
    except FileNotFoundError:
        return {'about': __doc__.split('\n\n')[1].replace('\n', ' '), 'releases': [], 'labels': {}}


def save(store):
    store['releases'].sort(key=lambda r: [int(x) for x in r['version'].split('.')])
    store['labels'] = dict(sorted(store['labels'].items()))
    with open(STORE, 'w', encoding='utf-8') as f:
        json.dump(store, f, indent=None, ensure_ascii=False, separators=(',', ':')); f.write('\n')


def graph_at(commit):
    try:
        return json.loads(git('show', f'{commit}:{GRAPH}'))
    except subprocess.CalledProcessError:
        return None


def rules():
    return json.load(open(os.path.join(ROOT, 'data', 'grc-gaps.json'), encoding='utf-8'))['rules']


def fill_all():
    store, R = load(), rules()
    done = {r['version'] for r in store['releases']} | set(store.get('unchanged', []))
    prev, prev_v = None, None
    for v, c in releases():
        g = graph_at(c)
        if g is None:
            continue
        if v not in done:
            entry = change(prev, g, R, v, prev_v)
            if entry:
                store['releases'].append(entry); print(f'v{v}: graph changed')
            else:
                store.setdefault('unchanged', []).append(v)
        labels_of(store, g)
        prev, prev_v = g, v
    store['unchanged'] = sorted(set(store.get('unchanged', [])), key=lambda v: [int(x) for x in v.split('.')])
    save(store)


def for_build(version, graph):
    """At a release's own build: the entry for version against the last release commit's graph, if version has no
    commit yet. Returns the store, changed or not."""
    store = load()
    try:
        rels = releases()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return store
    if not rels or any(v == version for v, _ in rels):
        return store
    v0, c0 = rels[-1]
    store['releases'] = [r for r in store['releases'] if r['version'] != version]
    store['unchanged'] = [v for v in store.get('unchanged', []) if v != version]
    entry = change(graph_at(c0), graph, rules(), version, v0)
    if entry:
        store['releases'].append(entry)
    else:
        store['unchanged'].append(version)
    labels_of(store, graph)
    save(store)
    return store


if __name__ == '__main__':
    if sys.argv[1:] == ['--all']:
        fill_all()
    else:
        sys.exit(__doc__)
