#!/usr/bin/env python3
"""The gate. Exits non-zero on any failure. Run after build.py, from anywhere."""
import hashlib, json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SKIP_DIRS = {'.git', 'data', 'assets', '.sg_vault', 'build', 'content'}
fails, warns = [], []

def rel(p): return os.path.relpath(p, ROOT)

def html_files():
    out = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for f in files:
            if f.endswith('.html'):
                out.append(os.path.join(root, f))
    return sorted(out)

pages = html_files()
if not pages: fails.append('no pages built')
linked_to = set()
for p in pages:
    s = open(p, encoding='utf-8').read()
    d = os.path.dirname(p)
    # 1. internal links resolve; 2. collect inbound links
    for m in re.finditer(r'(?:href|src)="([^"#]+)(#[^"]*)?"', s):
        href = m.group(1)
        if re.match(r'^(https?:|mailto:|data:)', href):
            if re.search(r'<(script|link|img)[^>]*\b(src|href)="' + re.escape(href), s) and 'rel="license"' not in s[max(0, m.start() - 120):m.start()] and 'canonical' not in s[max(0, m.start() - 60):m.start()] and 'og:' not in s[max(0, m.start() - 60):m.start()]:
                tag = s[s.rfind('<', 0, m.start()):m.start()]
                if tag.startswith('<script') or tag.startswith('<link rel="stylesheet"') or tag.startswith('<img'):
                    fails.append(f'{rel(p)}: external resource {href}')
            continue
        target = os.path.normpath(os.path.join(d, href))
        if not os.path.exists(target):
            fails.append(f'{rel(p)}: broken link {href}')
        elif target.endswith('.html'):
            linked_to.add(target)
    # 3. markdown twin
    md = re.sub(r'\.html$', '.md', p)
    if not os.path.exists(md): fails.append(f'{rel(p)}: no markdown twin')
    # 6. em-dash in the site's prose (sources page exempt: third-party titles; the claims waiting for review show the vault
    # agents' notes verbatim, with the words they quote)
    if os.sep + 'sources' + os.sep not in p and not p.endswith(os.path.join('claims', 'review', 'index.html')) and os.sep + 'actors' + os.sep not in p and os.sep + 'facts' + os.sep not in p and os.sep + 'versions' + os.sep not in p and os.sep + 'interview' + os.sep not in p and not p.endswith(os.path.join('affected', 'software.html')) and not p.endswith(os.path.join('brief', 'index.html')) and not re.search(r'readings/[^/]+/index\.html$', p.replace(os.sep, '/')):
        body = re.sub(r'<q>.*?</q>', '', s, flags=re.S)
        body = re.sub(r'title="[^"]*"', '', body)
        if '—' in body:
            fails.append(f'{rel(p)}: em-dash in prose')
# 2. orphans
for p in pages:
    if p not in linked_to and not p.endswith('index.html') or (p.endswith('index.html') and p != os.path.join(ROOT, 'index.html') and p not in linked_to):
        fails.append(f'{rel(p)}: orphan (nothing links to it)')
# 3b. llms.txt lists every page
llms = open(os.path.join(ROOT, 'llms.txt'), encoding='utf-8').read() if os.path.exists(os.path.join(ROOT, 'llms.txt')) else ''
if not llms: fails.append('llms.txt missing')
for p in pages:
    if 'account/' in rel(p): continue
    if re.sub(r'\.html$', '.md', rel(p)) not in llms:
        fails.append(f'{rel(p)}: not in llms.txt')
# 4. citations and 9. data parses, statuses
def load(n):
    try:
        return json.load(open(os.path.join(ROOT, 'data', n + '.json'), encoding='utf-8'))
    except Exception as e:
        fails.append(f'data/{n}.json: {e}'); return None
sources = load('sources') or []
slugs = {s['slug'] for s in sources}
WORDS = {'confirmed', 'reported', 'disputed', 'contradicted', 'unverified'}
for n, key in (('claims', 'sources'), ('timeline', 'sources'), ('numbers', 'sources'), ('agencies', 'sources'), ('exploitation', 'sources'), ('actors', 'sources')):
    rows = load(n) or []
    for r in rows:
        for s in r.get(key, []):
            if s not in slugs: fails.append(f'data/{n}.json: {r.get("id") or r.get("at") or r.get("agency")} cites unknown slug {s}')
        if n == 'claims' and r.get('status') not in WORDS: fails.append(f'data/claims.json: {r.get("id")} has status {r.get("status")!r}')
        if n == 'numbers' and r.get('status') not in WORDS: fails.append(f'data/numbers.json: {r.get("id")} has status {r.get("status")!r}')
story = load('story') or {}
for k in story.get('known', []):
    for s in k.get('sources', []):
        if s not in slugs: fails.append(f'data/story.json: known cites unknown slug {s}')
for n in ('affected', 'roles', 'versions', 'billing', 'vault', 'software', 'graph', 'vault-claims', 'vault-timeline'):
    load(n)
aff = load('affected') or {}
for s in aff.get('ranges_sources', []) + aff.get('mitigations_sources', []) + sum([x.get('sources', []) for x in aff.get('sapis', [])], []):
    if s not in slugs: fails.append(f'data/affected.json cites unknown slug {s}')
# 4b. articles: front matter present, every [[slug]] in the manifest
adir = os.path.join(ROOT, 'admin', 'content', 'articles')
for fn in sorted(os.listdir(adir)) if os.path.isdir(adir) else []:
    if not fn.endswith('.md'): continue
    t = open(os.path.join(adir, fn), encoding='utf-8').read()
    fm = re.match(r'^---\n(.*?)\n---\n', t, flags=re.S)
    if fm and not re.search(r'^origin:\s*(house|guest|interview)\s*$', fm.group(1), flags=re.M): fails.append(f'articles/{fn}: origin must be house, guest or interview')
    for k in ('slug', 'title', 'dek', 'role', 'author', 'written', 'as_of_version', 'vault_commit', 'data_as_of'):
        if not fm or not re.search(r'^' + k + r':\s*\S', fm.group(1), flags=re.M): fails.append(f'articles/{fn}: front matter has no {k}')
    for g in re.findall(r'\[\[([^\]]+)\]\]', t):
        for s in g.split(','):
            if s.strip() not in slugs: fails.append(f'articles/{fn}: cites unknown slug {s.strip()}')
# 4b2. second readings: every row's sources and claims exist, and the other model's text is on disk
rd = load('readings') or {}
cids = {c['id'] for c in (load('claims') or [])}
for r in rd.get('readings', []):
    if not os.path.exists(os.path.join(ROOT, r.get('file', ''))): fails.append(f'data/readings.json: {r.get("id")} file {r.get("file")} missing')
    for x in r.get('rows', []):
        for s in x.get('sources', []):
            if s not in slugs: fails.append(f'data/readings.json: {r.get("id")} / {x.get("point")} cites unknown slug {s}')
        for c in x.get('claims', []):
            if c not in cids: fails.append(f'data/readings.json: {r.get("id")} / {x.get("point")} names unknown claim {c}')
# 4d. patching: every downstream row is a real inventory row with the status shown; status.json is built and parses
pt = load('patching') or {}
inv = {(r['supplier'], r['product']): r.get('status_109618') for r in (load('software') or {}).get('rows', [])}
prow = [d for l in pt.get('ladder', []) for d in l.get('downstream', [])] + [r for m in pt.get('models', []) for r in m.get('rows', [])]
for sup, prod, st in prow:
    if (sup, prod) not in inv: fails.append(f'data/patching.json: no inventory row {sup!r} / {prod!r}')
    elif inv[(sup, prod)] != st: fails.append(f'data/patching.json: {prod!r} is {st!r} here but {inv[(sup, prod)]!r} in the inventory')
for x in pt.get('ladder', []) + pt.get('side_effects', []) + pt.get('why_not_every_version', []):
    for s in x.get('sources', []):
        if s not in slugs: fails.append(f'data/patching.json cites unknown slug {s}')
try:
    json.load(open(os.path.join(ROOT, 'status.json'), encoding='utf-8'))
except Exception as e:
    fails.append(f'status.json: {e}')
# 4e. signals: every layer, family and barrier cites only manifest slugs
sg = load('signals') or {}
for x in sg.get('ladder', []) + sg.get('families', []) + sg.get('barriers', []):
    for s in x.get('sources', []):
        if s not in slugs: fails.append(f'data/signals.json: {x.get("id")} cites unknown slug {s}')
# 4c. layers: every data file is classified exactly once
layers = load('layers') or {}
classified = [f['path'] for f in layers.get('files', [])]
ids = {l['id'] for l in layers.get('layers', [])}
for f in layers.get('files', []):
    if f.get('layer') not in ids: fails.append(f'data/layers.json: {f["path"]} has layer {f.get("layer")!r}')
for fn in sorted(os.listdir(os.path.join(ROOT, 'data'))):
    if fn.endswith('.json') and classified.count('data/' + fn) != 1: fails.append(f'data/{fn}: listed {classified.count("data/" + fn)} times in data/layers.json, not once')
qs = load('questions') or {}
for q in qs.get('questions', []):
    for a in q.get('answer', []):
        for s in a.get('sources', []):
            if s not in slugs: fails.append(f'data/questions.json: {q.get("id")} cites unknown slug {s}')
    for pth in q.get('see', []):
        if not os.path.exists(os.path.join(ROOT, pth.split('#')[0])): fails.append(f'data/questions.json: {q.get("id")} points at missing page {pth}')
    if not q.get('see'): fails.append(f'data/questions.json: {q.get("id")} points at no page')
# 4b. the readers: plain-English facts cite known slugs; every persona path and glossary link points at a page that exists
plain = load('plain') or {}
for c in plain.get('cards', []) + plain.get('moments', []):
    for s in c.get('sources', []):
        if s not in slugs: fails.append(f'data/plain.json: {c.get("q") or c.get("when")} cites unknown slug {s}')
    if not os.path.exists(os.path.join(ROOT, c['href'].split('#')[0])): fails.append(f'data/plain.json: link to missing page {c["href"]}')
personas = load('personas') or {}
aud = {a['id'] for a in (load('roles') or {}).get('audiences', [])}
for pr in personas.get('personas', []):
    if pr['id'] not in aud: fails.append(f'data/personas.json: {pr["id"]} has no briefing audience in roles.json')
    for x in pr.get('path', []):
        if not os.path.exists(os.path.join(ROOT, x)): fails.append(f'data/personas.json: {pr["id"]} path points at missing page {x}')
for t in (load('glossary') or {}).get('terms', []):
    if not os.path.exists(os.path.join(ROOT, t['more'].split('#')[0])): fails.append(f'data/glossary.json: {t["id"]} links to missing page {t["more"]}')
# 4c. search engines: the sitemap lists every public page, robots.txt points at it, the feed and the social card exist
sm = open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read() if os.path.exists(os.path.join(ROOT, 'sitemap.xml')) else ''
if not sm: fails.append('sitemap.xml missing')
for p in pages:
    r = rel(p).replace(os.sep, '/')
    if r.startswith('account/top'): continue
    if f'/{r}</loc>' not in sm: fails.append(f'{r}: not in sitemap.xml')
if 'Sitemap:' not in (open(os.path.join(ROOT, 'robots.txt')).read() if os.path.exists(os.path.join(ROOT, 'robots.txt')) else ''): fails.append('robots.txt missing or has no Sitemap line')
for f in ('feed.xml', 'assets/og-card.png', 'data/sections.json'):
    if not os.path.exists(os.path.join(ROOT, f)): fails.append(f'missing {f}')
arcs = load('arcs') or {}
claim_ids = {c['id'] for c in (load('claims') or [])}
review_ids = {n['id'] for n in (load('review') or {}).get('nodes', [])}
risk_ids = {r['id'] for r in arcs.get('risks', [])}
persona_ids = {p['id'] for p in (load('personas') or {}).get('personas', [])}
for r in arcs.get('risks', []):
    for c in r.get('claims', []):
        if c not in claim_ids: fails.append(f'data/arcs.json: risk {r["id"]} rests on unknown claim {c}')
for a in arcs.get('arcs', []):
    for r in a.get('risks', []):
        if r not in risk_ids: fails.append(f'data/arcs.json: arc {a["id"]} carries unknown risk {r}')
    for c in a.get('claims', []):
        if c not in claim_ids: fails.append(f'data/arcs.json: arc {a["id"]} rests on unknown claim {c}')
    if not os.path.exists(os.path.join(ROOT, a.get('page', ''))): fails.append(f'data/arcs.json: arc {a["id"]} points at missing page {a.get("page")}')
for pid, rs in arcs.get('faces', {}).items():
    if pid not in persona_ids: fails.append(f'data/arcs.json: unknown stakeholder {pid}')
    for r in rs:
        if r not in risk_ids: fails.append(f'data/arcs.json: {pid} faces unknown risk {r}')
for key in ('claim_to_flaw', 'claim_to_fix'):
    for c, ts in arcs.get(key, {}).items():
        if c not in claim_ids: fails.append(f'data/arcs.json: {key} names unknown claim {c}')
        for t in ts:
            if t not in review_ids: fails.append(f'data/arcs.json: {key} {c} names unknown review node {t}')
fr = load('fractal') or {}
fr_ids = {n['id'] for n in fr.get('nodes', [])}
for e in fr.get('edges', []):
    if e['from'] not in fr_ids or e['to'] not in fr_ids: fails.append(f'data/fractal.json: edge {e["from"]} -> {e["to"]} has a missing end')
# 4h. every member's policy (admin/content/agents/*/policy.json, librarian@php.newsroom): well formed, no two members
# claim the same file or page (fails), every source file and page has an owner (warns: the librarian's daily pass maps
# new files, so an agent's release is never blocked by a file its policy does not list yet)
try:
    sys.path.insert(0, os.path.join(ROOT, 'admin', 'build'))
    import agents as _agt
    _P = _agt.load_policies()
    for _a, _p in _P.items():
        for _k in ('schema', 'agent', 'address', 'kind', 'status', 'mandate', 'scope'):
            if _k not in _p: fails.append(f'admin/content/agents/{_a}/policy.json: no {_k}')
        if _p.get('agent') != _a: fails.append(f'admin/content/agents/{_a}/policy.json: agent is {_p.get("agent")!r}, folder is {_a!r}')
        if _p.get('status') not in ('draft', 'agreed'): fails.append(f'admin/content/agents/{_a}/policy.json: status {_p.get("status")!r}')
        if _p.get('status') == 'agreed' and not _p.get('agreed_by'): fails.append(f'admin/content/agents/{_a}/policy.json: agreed with no agreed_by')
        _G = {r['capability'] for r in _agt.grant_rows()}
        for _w in _p.get('mandate', {}).get('wanted', []):
            if _p.get('grant') and _w['capability'] not in _G: fails.append(f'admin/content/agents/{_a}/policy.json: wants {_w["capability"]}, which is not in the grant')
    for _o in _agt.overlaps(_P):
        fails.append(f'admin/content/agents: {_o["a"]} and {_o["b"]} both claim {_o["kind"]} {_o["files"][0]} ({_o["pattern_a"]} / {_o["pattern_b"]})')
    for _u in _agt.unowned(_P):
        warns.append(f'{_u}: no member owns this file yet (admin/content/agents/*/policy.json scope.writes)')
    for _x in _agt.dangling_appends(_P):
        fails.append(f'admin/content/agents/{_x["agent"]}/policy.json: appends to {_x["target"]}, which no member writes')
    _pages = [os.path.relpath(p_, ROOT) for p_ in pages]
    for _pg in _pages:
        if not any(_agt.match(_w, _pg) for _q in _P.values() for _w in _q['scope']['pages']):
            warns.append(f'{_pg}: no member owns this page yet (scope.pages)')
except Exception as _e:
    fails.append(f'admin/build/agents.py: {_e}')
# 5. determinism: rebuild into a temp copy and compare hashes
def tree_hash():
    h = hashlib.sha256()
    for p in pages + sorted(re.sub(r'\.html$', '.md', p) for p in pages) + [os.path.join(ROOT, 'llms.txt'), os.path.join(ROOT, 'data', 'graph.json'), os.path.join(ROOT, 'data', 'sections.json'), os.path.join(ROOT, 'sitemap.xml'), os.path.join(ROOT, 'feed.xml')]:
        if os.path.exists(p):
            h.update(rel(p).encode()); h.update(open(p, 'rb').read())
    return h.hexdigest()
before = tree_hash()
r = subprocess.run([sys.executable, os.path.join(ROOT, 'admin', 'build', 'build.py')], capture_output=True, text=True)
if r.returncode != 0: fails.append('rebuild failed: ' + r.stderr[-500:])
elif tree_hash() != before: fails.append('build is not deterministic: a second run changed the output')
# 7. security (admin/build/security_check.py, kept by security@php.newsroom): credential shapes and secret values,
# vault-key and decrypted-vault files, hidden characters and text addressed to a model, JSON script blocks that their
# data could close, javascript: URLs, slug shapes, workflows pinned to commits
sys.path.insert(0, os.path.join(ROOT, 'admin', 'build'))
import security_check
fails += security_check.tree_fails(ROOT)
# 8. no external script/style/img (checked above); also check the vendored meter is present
for f in ('assets/review-nav.js', 'data/review.json', 'review/code/files.json', 'assets/themes/themes.css', 'assets/themes/themes.js', 'assets/themes/site-tokens.css', 'assets/telemetry.js', 'data/telemetry.json', 'data/admin.json', 'assets/components/sg-meter/v1/v1.3/v1.3.1/sg-meter.js', 'assets/components/base/v1/v1.0/v1.0.0/sg-component.js', 'assets/site.css', 'assets/site.js', 'CNAME', '.nojekyll', 'VERSION', '.github/workflows/pages.yml', 'assets/personas.js'):
    if not os.path.exists(os.path.join(ROOT, f)): fails.append(f'missing {f}')
# version consistency
ver = open(os.path.join(ROOT, 'VERSION')).read().strip()
vs = load('versions') or {}
if vs.get('current') != ver: fails.append(f'VERSION {ver} but data/versions.json current is {vs.get("current")}')
if not any(v.get('version') == ver for v in vs.get('versions', [])): fails.append(f'no release entry for v{ver}')
for w in warns: print('warn:', w)
if fails:
    for f in fails: print('FAIL:', f)
    print(f'{len(fails)} failures across {len(pages)} pages'); sys.exit(1)
print(f'gate passed: {len(pages)} pages, {len(slugs)} sources, deterministic, no credential shapes, v{ver}')
