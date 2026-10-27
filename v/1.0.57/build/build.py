#!/usr/bin/env python3
"""Build php.oct-2026.story.sgit.ai from data/ into the repository root.

Deterministic: the same data/ and VERSION produce byte-identical output. There is no clock in
this file. Every page gets a markdown twin at the same path, and llms.txt lists every page.
Run: python3 admin/build/build.py        (from the repository root or anywhere)
"""
import html, json, math, os, re, sys
from collections import Counter, OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA = os.path.join(ROOT, 'data')
SITE = 'php.oct.2026.newsroom.sgit.ai'
SITE_NAME = 'PHP October 2026'
BASE_URL = 'https://' + SITE
REPO_URL = 'https://github.com/SGit-AI/SGit-AI__Website__Newsroom__2026__Oct__PHP'
NEWSROOM = 'https://newsroom.sgit.ai/php-flaws/index.html'

def load(name):
    with open(os.path.join(DATA, name + '.json'), encoding='utf-8') as f:
        return json.load(f)

VERSION = open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip()
_rp = os.path.join(ROOT, 'data', 'release-pages.json')
RELEASE_PAGES = json.load(open(_rp, encoding='utf-8'))['releases'] if os.path.exists(_rp) else {}  # version -> the pages it changed
SHOWN_PAGES = 8  # links per release on admin/versions.html; the rest behind a toggle
D = {k: load(k) for k in ('story', 'claims', 'timeline', 'numbers', 'agencies', 'affected', 'exploitation',
                          'actors', 'roles', 'versions', 'billing', 'sources', 'vault', 'software',
                          'vault-claims', 'vault-timeline', 'code', 'history', 'impact', 'defence',
                          'personas', 'glossary', 'plain', 'interview', 'seo',
                          'admin', 'telemetry', 'review', 'layers', 'questions', 'readings', 'patching', 'pipeline', 'vaults', 'source-watch', 'feed-sources', 'inventory-history', 'signals', 'subscriptions', 'compromise', 'stack', 'state', 'pack-mode', 'claim-review', 'desk', 'arcs', 'personas')}
TREP = load('telemetry-report') if os.path.exists(os.path.join(DATA, 'telemetry-report.json')) else None
TPUB = load('telemetry-public') if os.path.exists(os.path.join(DATA, 'telemetry-public.json')) else None
WORLD = load('world')
SYN = load('synthetic') if os.path.exists(os.path.join(DATA, 'synthetic.json')) else None
SOURCES = OrderedDict((s['slug'], s) for s in D['sources'])
STORY = D['story']
if D['vault'].get('latest_capture'):
    STORY['data_as_of'] = D['vault']['latest_capture']  # the time of the latest capture in the vault, never a clock

def _minute(t):
    """2026-10-23T12:39:02Z or 2026-10-23T12:39Z as 2026-10-23T12:39Z; anything else as None."""
    m = re.match(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})', t or '')
    return m.group(1) + 'Z' if m else None

# What 'last checked' means: the newest of the three places this site reads the story from, each with its own time.
# The evidence vault's latest capture stays data_as_of (claims, articles and status.json are built from it).
CHECKS = [c for c in [
    ('the evidence vault', 'latest capture', _minute(STORY['data_as_of']), 'sources/index.html'),
    ('the source watch', 'latest run', max(filter(None, (_minute(r.get('finished')) for r in D['source-watch']['runs'])), default=None), 'vaults/source-watch/index.html'),
    ('the NCSC-NL inventory', 'latest change read', _minute(D['inventory-history']['snapshots'][-1]['at']), 'patching/inventory/index.html'),
] if c[2]]
STORY['checked_at'] = max(c[2] for c in CHECKS)
# When an agent last worked on the site: the newest run record (admin/build/loops.py), shown beside the evidence time.
LAST_RUN = __import__('loops').last_run(globals())

def checks_title():
    return '; '.join(f'{w}: {k} {human_time(t)}' for w, k, t, _ in CHECKS)

E = html.escape

def J(o, **kw):
    """JSON for inside a <script> element: '<', '>' and '&' as \\u escapes, so no string in the data can close the element."""
    return json.dumps(o, **kw).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

def U(u, fallback='#'):
    """An href from data, escaped. Only http(s), mailto and scheme-less (relative or fragment) URLs pass; javascript:, data: and the rest become the fallback."""
    u = str(u or '').strip()
    if re.match(r'(https?://|mailto:)', u, re.I) or (u and ':' not in re.split(r'[/?#]', u, maxsplit=1)[0]):
        return E(u)
    return E(fallback)

ARTICLES_DIR = os.path.join(ROOT, 'admin', 'content', 'articles')

def load_articles():
    """Every article in admin/content/articles/: a front matter block of key: value lines, then markdown. Newest first."""
    out = []
    for fn in sorted(os.listdir(ARTICLES_DIR)) if os.path.isdir(ARTICLES_DIR) else []:
        if not fn.endswith('.md'):
            continue
        text = open(os.path.join(ARTICLES_DIR, fn), encoding='utf-8').read()
        m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, flags=re.S)
        if not m:
            sys.exit(f'article {fn}: no front matter')
        meta = dict(re.match(r'^(\w+):\s*(.*)$', l).groups() for l in m.group(1).splitlines() if l.strip())
        meta['file'], meta['text'] = fn, m.group(2)
        meta['cites'] = list(OrderedDict.fromkeys(x.strip() for g in re.findall(r'\[\[([^\]]+)\]\]', meta['text']) for x in g.split(',')))
        out.append(meta)
    return sorted(out, key=lambda a: (a['written'], a['file']), reverse=True)

ARTICLES = load_articles()

# the updates (admin/content/updates/), loaded here because the menu lists the latest ones
UPDATES_DIR = os.path.join(ROOT, 'admin', 'content', 'updates')
UPDATE_KINDS = OrderedDict([('flash', 'Flash'), ('hourly', 'Hourly'), ('daily', 'Daily')])

def load_updates():
    out = []
    for fn in sorted(os.listdir(UPDATES_DIR)) if os.path.isdir(UPDATES_DIR) else []:
        if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{4}Z__[a-z]+\.md$', fn):
            continue  # README.md and anything else that is not an update
        m = re.match(r'^---\n(.*?)\n---\n(.*)$', open(os.path.join(UPDATES_DIR, fn), encoding='utf-8').read(), flags=re.S)
        if not m:
            sys.exit(f'update {fn}: no front matter')
        meta = dict(re.match(r'^(\w+):\s*(.*)$', l).groups() for l in m.group(1).splitlines() if l.strip())
        for k in ('id', 'at', 'kind', 'title', 'summary', 'covers_from', 'covers_to', 'author'):
            if not meta.get(k):
                sys.exit(f'update {fn}: front matter has no {k}')
        if meta['kind'] not in UPDATE_KINDS:
            sys.exit(f'update {fn}: kind must be one of {", ".join(UPDATE_KINDS)}')
        meta['file'], meta['text'] = fn, m.group(2)
        out.append(meta)
    return sorted(out, key=lambda u: u['at'], reverse=True)

UPDATES = load_updates()

# The two halves of the site, and what each page is. Research: material collected from outside and what this
# site derives from it. Stories: written here, signed and dated. Every page carries one of these at its top.
ZONES = OrderedDict([('Updates', 'Updates'), ('Start here', 'For you'), ('Questions', 'For you'), ('Briefings', 'For you'), ('Yours', 'For you'), ('The incident', 'Research'),
                     ('The analysis', 'Research'), ('The evidence', 'Research'), ('GRC', 'Research'), ('Views', 'Stories'), ('Stories', 'Stories'), ('About', 'Site'), ('Elsewhere', 'Elsewhere')])
ORIGINS = {
    'house': {'short': 'House', 'label': 'Story', 'text': 'written here by this site, signed and dated'},
    'guest': {'short': 'Guest', 'label': 'Story, guest', 'text': 'written by a guest writer, published here under their name'},
    'update': {'short': 'Update', 'label': 'Update', 'text': 'written here for the conductor from the repository\'s record and the evidence; dated, kept as written'},
    'interview': {'short': 'Interview', 'label': 'Story, interview', 'text': 'an interview conducted for this site, the answers in the interviewee\'s own words'},
}
AUTHOR_ROLES = OrderedDict([('journalist', 'Journalist'), ('historian', 'Historian'), ('journalist-historian', 'Journalist and historian'), ('cyber', 'Cyber desk'), ('dev', 'Dev desk')])

# ----------------------------------------------------------------------------- small helpers

STATUS_WORDS = OrderedDict([
    ('confirmed', 'two or more primary sources agree, or the fact was counted from a captured file'),
    ('reported', 'one party says so, and it has not been contradicted'),
    ('disputed', 'the sources disagree, and both readings are shown'),
    ('contradicted', 'a primary source says otherwise'),
    ('unverified', 'even the reporting outlet could not check it'),
])

def pill(status):
    w = re.match(r'[a-z]*', (status or '').lower()).group(0)  # the leading word, without the ';' or ':' that may follow it
    cls = w if w in STATUS_WORDS else 'other'
    m = re.match(r'^(\w+)([;:,]?\s+[(;:]?.*)$', status or '') if cls != 'other' else None
    if m and len(status) > 24:  # a status word with a qualifier: the word is the pill, the qualifier wraps beside it
        return f'<span class="st st-{cls}">{E(m.group(1))}</span> <span class="small">{E(m.group(2).strip(" ;:,"))}</span>'
    return f'<span class="st st-{cls}">{E(status)}</span>'

def src_links(slugs, depth):
    out = []
    for s in slugs:
        if s in SOURCES:
            row = SOURCES[s]
            out.append(f'<a class="src" href="{"../" * depth}sources/{E(s)}/index.html" title="{E(row.get("title") or row.get("publisher") or s)}">{E(short_name(row))}</a>')
        else:
            out.append(f'<span class="src src-missing" title="not in the manifest">{E(s)}</span>')
    return ' '.join(out)

def short_name(row):
    pub = row.get('publisher') or row['slug']
    pub = re.sub(r'\s*\(.*?\)\s*', ' ', pub).strip()
    pub = pub.replace('US Cybersecurity and Infrastructure Security Agency', 'CISA')
    pub = pub.replace('UK National Cyber Security Centre', 'NCSC UK').replace('US National Security Agency', 'NSA')
    pub = pub.replace('NIST National Vulnerability Database', 'NVD').replace('Canadian Centre for Cyber Security', 'CCCS')
    pub = pub.replace('Swiss Federal Office for Cyber Security', 'BACS').replace('CERT-FR', 'CERT-FR')
    pub = pub.replace('The PHP Foundation', 'PHP Foundation').replace('PHP Group', 'php.net')
    pub = pub.replace('NCSC-NL', 'NCSC-NL').replace('oss-security list', 'oss-security')
    pub = pub.replace('php/php-src on GitHub', 'php-src').replace('OpenAI Developer Community', 'OpenAI forum')
    pub = pub.replace('CVE Program', 'CVE record').replace('ENISA / EU CSIRTs Network', 'ENISA CNW')
    pub = pub.replace('NSA Cybersecurity', 'NSA Cyber').replace("ASD's ACSC", 'ACSC')
    pub = pub.replace('Alexandre Daubois', 'Daubois').replace('The Hacker News', 'THN').replace('Techzine Global', 'Techzine')
    kind = row.get('kind')
    if kind == 'social' and re.match(r'https?://(www\.)?(x|twitter)\.com/', row.get('url') or ''):
        pub += ' on X'
    pub = re.sub(r'\s+,', ',', pub)
    return pub if len(pub) <= 34 else pub[:34].rsplit(' ', 1)[0].rstrip(',') + '…'

def fmt_at(at):
    """A date or ISO instant as the timeline shows it."""
    if not at:
        return ''
    m = re.match(r'^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::(\d{2}))?Z$', at)
    if m:
        return f'{m.group(1)} {m.group(2)}{":" + m.group(3) if m.group(3) else ""} UTC'
    return at

def md_escape_cell(s):
    return s.replace('|', '\\|').replace('\n', ' ')

# ----------------------------------------------------------------------------- html -> markdown

def to_markdown(fragment):
    """A small, deterministic HTML to Markdown conversion for the .md twins."""
    s = fragment
    s = re.sub(r'<svg.*?</svg>', '', s, flags=re.S)
    s = re.sub(r'<script\b.*?</script\b[^>]*>', '', s, flags=re.S | re.I)
    s = re.sub(r'<sg-meter[^>]*></sg-meter>', '', s)
    # tables
    def table(m):
        t = m.group(0)
        rows = re.findall(r'<tr.*?</tr>', t, flags=re.S)
        out, first = [], True
        for r in rows:
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', r, flags=re.S)
            cells = [md_escape_cell(inline(c)).strip() for c in cells]
            out.append('| ' + ' | '.join(cells) + ' |')
            if first:
                out.append('|' + '---|' * len(cells))
                first = False
        return '\n' + '\n'.join(out) + '\n'
    def inline(x):
        x = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: f'[{strip(m.group(2))}]({m.group(1)})', x, flags=re.S)
        x = re.sub(r'<(b|strong)>(.*?)</\1>', r'**\2**', x, flags=re.S)
        x = re.sub(r'<(i|em|q)>(.*?)</\1>', r'*\2*', x, flags=re.S)
        x = re.sub(r'<code>(.*?)</code>', r'`\1`', x, flags=re.S)
        x = re.sub(r'<br\s*/?>', ' ', x)
        return strip(x)
    def strip(x):
        x = re.sub(r'<[^>]+>', '', x)
        return html.unescape(re.sub(r'\s+', ' ', x))
    s = re.sub(r'<table.*?</table>', table, s, flags=re.S)
    s = re.sub(r'<h1[^>]*>(.*?)</h1>', lambda m: '\n# ' + inline(m.group(1)) + '\n', s, flags=re.S)
    s = re.sub(r'<h2[^>]*>(.*?)</h2>', lambda m: '\n## ' + inline(m.group(1)) + '\n', s, flags=re.S)
    s = re.sub(r'<h3[^>]*>(.*?)</h3>', lambda m: '\n### ' + inline(m.group(1)) + '\n', s, flags=re.S)
    s = re.sub(r'<h4[^>]*>(.*?)</h4>', lambda m: '\n#### ' + inline(m.group(1)) + '\n', s, flags=re.S)
    s = re.sub(r'<li[^>]*>(.*?)</li>', lambda m: '- ' + inline(m.group(1)) + '\n', s, flags=re.S)
    def _img(m):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        return '\n![' + html.unescape(attrs.get('alt', '')) + '](' + attrs.get('src', '') + ')\n' if attrs.get('src') else ''
    s = re.sub(r'<img\b[^>]*>', _img, s)
    s = re.sub(r'<(p|dt|dd|figcaption)[^>]*>(.*?)</\1>', lambda m: '\n' + inline(m.group(2)) + '\n', s, flags=re.S)
    s = re.sub(r'<pre([^>]*)>(.*?)</pre>', lambda m: '\n```' + (re.search(r'data-lang="([a-z]+)"', m.group(1)) or [None, ''])[1] + '\n' + html.unescape(re.sub(r'<[^>]+>', '', m.group(2))) + '\n```\n', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    s = re.sub(r'[ \t]+\n', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip() + '\n'

# ----------------------------------------------------------------------------- layout

NAV = [
    ('Updates', [('updates/index.html', 'Every update, newest first')] + [(f'updates/{u["id"]}/index.html', f'{UPDATE_KINDS[u["kind"]]}: {int(u["at"][8:10])} {"Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[int(u["at"][5:7]) - 1]} {u["at"][11:16]} UTC') for u in UPDATES[:6]] + [('updates/readme/index.html', 'How an update is written')]),
    ('Start here', [('start/index.html', 'Who are you? Pick a reader'), ('ops/index.html', 'Operations view: patch and defend'), ('analysis/index.html', 'Analysis view: weigh the evidence'), ('explained/index.html', 'Explained from the start'), ('glossary/index.html', 'Glossary: every term, in plain English')]),
    ('Questions', [('questions/index.html', 'Questions readers ask')] + [(f'questions/{q["id"]}/index.html', q['q']) for q in D['questions']['questions']]),
    ('Briefings', [(f'briefings/{a["id"]}/index.html', a['name']) for a in D['roles']['audiences']]),
    ('Yours', [('collaborators/index.html', 'Power users: start here'), ('join/index.html', 'Join: a key for feedback'), ('feedback/index.html', 'Feedback from collaborators'), ('join/invite/index.html', 'Invite someone'), ('now/index.html', 'Now: the phone app'), ('you/index.html', 'Your desk: new, changed, notes'), ('stack/index.html', 'Your stack: the blast radius'), ('reader/index.html', 'The feed viewer'), ('feeds/index.html', 'Feeds (RSS)'), ('subscribe/index.html', 'Subscribe by email')]),
    ('The incident', [('index.html', 'Front page'), ('whatsnew/index.html', "What's new"), ('summary/index.html', 'The specialist summary'), ('flaws/index.html', 'The two flaws'), ('code/index.html', 'The code'), ('timeline/index.html', 'Timeline'),
                   ('discovery/index.html', 'Who found it'), ('leak/index.html', 'How disclosure broke'),
                   ('exploitation/index.html', 'Exploitation signals'), ('compromise/index.html', 'No named compromise: the evidence'), ('review/index.html', 'The fix, mapped to the code'), ('review/ui/index.html', 'Walk the graph'), ('impact/index.html', 'Impact: offline vs compromised'),
                   ('defence/index.html', 'Detection and defence'), ('context/index.html', 'In context: 2008 to 2026'), ('playbook/index.html', 'If you run PHP'), ('patching/index.html', 'Patching: who gets a fix'), ('patching/inventory/index.html', 'The inventory, hour by hour'), ('signals/index.html', 'The second stories: signals')]),
    ('The analysis', [('claims/index.html', 'Every claim'), ('claims/review/index.html', 'Claims waiting for review'), ('factcheck/index.html', 'Fact-check: how sure we are'), ('outreach/index.html', 'Corrections we have asked for'), ('numbers/index.html', 'The numbers'), ('agencies/index.html', 'The agencies'),
                      ('affected/index.html', 'Affected systems'), ('actors/index.html', 'Who says what'), ('graph/index.html', 'As a graph'), ('graph/parties/index.html', 'Every party'), ('wikipedia/index.html', 'Wikipedia, as a graph'), ('wikipedia/php2shell/index.html', 'Wikipedia: the PHP2Shell article'), ('wikipedia/php2shell/statements/index.html', 'Wikipedia: every statement'), ('wikipedia/php2shell/references/index.html', 'Wikipedia: every reference'), ('wikipedia/php2shell/history/index.html', 'Wikipedia: every edit'), ('wikipedia/php2shell/evolution/index.html', 'Wikipedia: the evolution'), ('wikipedia/php2shell/talk/index.html', 'Wikipedia: the talk page'), ('wikipedia/php2shell/review/index.html', 'Wikipedia: a reviewer\'s reading'), ('wikipedia/for-editors/index.html', 'Wikipedia: for its editors'), ('fractal/index.html', 'From a line of code to a stakeholder'), ('fractal/ui/index.html', 'Walk the whole graph'),
                      ('readings/index.html', 'From outside: other models and sites')] + [(f'readings/{r["id"]}/index.html', f'{r["model"]}\'s notes, in full') for r in D['readings']['readings']]),
    ('The evidence', [('sources/index.html', 'Every source'), ('affected/software.html', 'Software inventory'), ('admin/vault/index.html', 'The vault, opened'),
                      ('layers/index.html', 'Evidence, derived, authored'),
                      ('pipeline/index.html', 'The fact pipeline'), ('versions/index.html', 'How the story changed'),
                      ('vaults/index.html', 'Every vault behind this site')] + [(x['page'], x['name']) for x in D['vaults']['vaults'] if x.get('nav', True)]),
    ('GRC', [('grc/index.html', 'GRC: risks, owners, standards'), ('grc/risks/index.html', 'The risk register'), ('grc/stakeholders/index.html', 'Stakeholders and their registers'),
             ('grc/frameworks/index.html', 'Frameworks: GDPR, NIS2, CRA, ISO, NIST'), ('grc/graph/index.html', 'The risk graph'), ('grc/explore/index.html', 'Explore the graph: from any node'), ('grc/gaps/index.html', 'What the graph is missing'), ('grc/changes/index.html', 'What changed in the graph'), ('grc/network/index.html', 'From the sgit network')]),
    ('Views', [('views/index.html', 'Views: the journalist\'s reading'), ('views/state/index.html', 'The state of affairs, now'), ('views/state/history/index.html', 'Every version, and what changed'), ('views/desk/index.html', "The journalist's desk: what is still stale"), ('views/loops/index.html', 'Every loop: researcher to correspondent')]),
    ('Stories', [('articles/index.html', 'All stories, written here')] + [(f'articles/{a["slug"]}/index.html', f'{ORIGINS[a["origin"]]["short"]} · {AUTHOR_ROLES.get(a["role"], a["role"])}: {a["title"].split(":")[0].split("?")[0]}') for a in ARTICLES] + [('interview/index.html', 'Interview: the editor')]),
    ('About', [('method/index.html', 'The method'), ('admin/design/index.html', 'Design: the redesign, in mockups'), ('team/index.html', 'The team'), ('billing/index.html', 'The billing model'),
               ('account/index.html', 'Your reading account'), ('brief/index.html', 'The brief'),
               ('corrections/index.html', 'Corrections'), ('admin/versions.html', 'Release history'), ('status/index.html', 'Pipeline: what is deploying'), ('admin/index.html', 'Admin & engineering'), ('admin/agents/index.html', 'Guidance for agents'), ('graph/component/index.html', 'The graph component'),
               ('admin/status-json/index.html', 'status.json: the feed for other sites'), ('admin/board/index.html', 'The board'), ('admin/roles/index.html', 'Roles'), ('admin/appsec/index.html', 'Application security'),] + ([('admin/keys/index.html', 'Keys and secrets')] if os.path.exists(os.path.join(DATA, 'keys.json')) else []) + [ ('admin/briefs/index.html', 'Briefs'), ('admin/pack-mode/index.html', 'Pack mode, measured'), ('admin/telemetry/index.html', 'Who reads this site'), ('admin/synthetic/index.html', 'Synthetic readers'), ('admin/agents/roles/index.html', 'Every member: who owns what'), ('admin/agents/rounds/index.html', 'Every round: what each member did')]),
    ('Elsewhere', [('pulse/index.html', 'What else is going on: Pulse')])
]

PAGES = []  # (path, title, description) in order, for llms.txt

# Pricing (data/billing.json, pricing): a page's kind is its content type; a type that decays gets its freshness tier
# appended in the reader's browser, from the page's date, before the meter reads it. The build stays clock-free.
PRICE_TYPES = {t['type']: t for t in D['billing']['pricing']['types']}
_tiers = D['billing']['pricing']['tiers']
FRESHNESS_JS = ('<script>(function(m){var a=(Date.now()-Date.parse(m.getAttribute("date")))/864e5;m.setAttribute("kind",m.getAttribute("kind")+"_"+('
                + ''.join(f'a<={t["max_days"]}?"{t["tier"]}":' for t in _tiers if t['max_days'] is not None)
                + f'"{_tiers[-1]["tier"]}"))}})(document.currentScript.previousElementSibling)</script>')

def layout(path, title, description, body, kind='site', date=None, topics='', ld_type='Article', origin=None, byline=None):
    depth = path.count('/')
    up = '../' * depth
    PAGES.append((path, title, description, kind))
    here = path
    nav_items = [__import__('design').menu_html(globals(), here, up)]  # the task menu (admin/build/design.py); the dials pick what of it shows
    if path.startswith('admin/'):
        body = (__import__('design').console_overview(globals()) if path == 'admin/index.html' else '') + body
        body = f'<div class="v2"><div class="console-live">{__import__('design').console_side(globals(), path, up)}<div class="cmain">{body}</div></div></div>'
    cfg = D['billing']['runs']
    meter_cfg = {
        'storageKey': cfg['storageKey'], 'start': cfg['start'], 'symbol': cfg['symbol'],
        'prices': cfg['prices'],
        'newDays': cfg['newDays'], 'minDepth': cfg['minDepth'], 'topup': cfg['topup'],
        'links': {'account': 'account/index.html', 'topup': 'account/top-up.html'},
        'links2': {'newsroom': 'account/index.html', 'personas': 'account/index.html'},
        'root': up,
    }
    meter_json = J(meter_cfg, sort_keys=True, separators=(',', ':'))
    page_meter = '' if PRICE_TYPES[kind]['base'] == 0 else f'<sg-meter view="page" quiet kind="{E(kind)}" date="{E(date or STORY["data_as_of"][:10])}" topics="{E(topics)}" title="{E(title)}"></sg-meter>' + (FRESHNESS_JS if PRICE_TYPES[kind]['decays'] else '')
    ld = {
        '@context': 'https://schema.org', '@type': ld_type, 'headline': title, 'description': description,
        'url': f'{BASE_URL}/{path}', 'isPartOf': {'@type': 'WebSite', 'name': SITE_NAME, 'url': BASE_URL},
        'license': 'https://creativecommons.org/licenses/by/4.0/', 'dateModified': STORY['data_as_of'][:10],
        'version': VERSION, 'inLanguage': 'en', 'image': f'{BASE_URL}/{SEO.get("image", "assets/og-card.png")}',
        'datePublished': SEO.get('date_published', '2026-10-22'), 'mainEntityOfPage': f'{BASE_URL}/{path}',
        'author': {'@type': 'Person', 'name': SEO.get('author', 'Dinis Cruz')},
        'publisher': {'@type': 'Organization', 'name': SEO.get('publisher', 'SGit Newsroom'), 'url': SEO.get('publisher_url', 'https://newsroom.sgit.ai/')},
    }
    verify = f'\n<meta name="google-site-verification" content="{E(SEO["google_site_verification"])}">' if SEO.get('google_site_verification') else ''
    crumbs = [{'@type': 'ListItem', 'position': 1, 'name': SITE_NAME, 'item': f'{BASE_URL}/index.html'}]
    for label, items in NAV:
        if any(p == path for p, _ in items) and path != 'index.html':
            crumbs.append({'@type': 'ListItem', 'position': 2, 'name': label, 'item': f'{BASE_URL}/{items[0][0]}'})
            break
    if path != 'index.html':
        crumbs.append({'@type': 'ListItem', 'position': len(crumbs) + 1, 'name': title, 'item': f'{BASE_URL}/{path}'})
    ld = [ld, {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': crumbs}]
    if path == 'index.html':
        ld.append({'@context': 'https://schema.org', '@type': 'WebSite', 'name': SITE_NAME, 'url': BASE_URL + '/', 'description': STORY['description'], 'inLanguage': 'en'})
    return f'''<!doctype html>
<html lang="en" data-root="{up}" data-path="{path}" data-ver="{VERSION}"{' data-track-home' if path in ('index.html', 'ops/index.html', 'analysis/index.html') else ''}{__import__('design').line_html_attrs(globals())}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)} &middot; {SITE_NAME}</title>
<meta name="description" content="{E(description)}">
<link rel="canonical" href="{BASE_URL}/{path}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:url" content="{BASE_URL}/{path}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(description)}">
<meta name="twitter:card" content="summary_large_image">
<meta property="og:image" content="{BASE_URL}/{SEO.get('image', 'assets/og-card.png')}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="en_GB">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta name="author" content="{E(SEO.get('author', ''))}">{verify}
<link rel="alternate" type="application/atom+xml" title="{SITE_NAME}: what's new" href="{up}feed.xml">
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">
<link rel="icon" href="data:,">
<link rel="alternate" type="text/markdown" href="{up}{md_path(path)}">
{feed_links(path)}
<link rel="stylesheet" href="{up}assets/site.css">
<link rel="stylesheet" href="{up}assets/themes/themes.css">
<link rel="stylesheet" href="{up}assets/themes/site-tokens.css">
<link rel="stylesheet" href="{up}assets/design/v2-live.css">
{__import__('design').line_head(up)}<script type="application/ld+json">{J(ld, ensure_ascii=False)}</script>
<script type="application/json" id="sg-meter-config">{meter_json}</script>
<script type="module" src="{up}assets/components/sg-meter/v1/v1.3/v1.3.1/sg-meter.js"></script>
<script src="{up}assets/personas.js" defer></script>
<script src="{up}assets/site.js" defer></script>
<script src="{up}assets/reader-state.js" defer></script>
<script src="{up}assets/site-tools.js" defer></script>
<script src="{up}assets/telemetry.js" defer></script>
{__import__('design').line_scripts(up)}
</head>
<body>
<nav class="site"><div class="row">
  <script src="{up}assets/themes/themes.js"></script>
  <a class="brand" href="{up}index.html">PHP October<span> 2026</span></a>
  <a class="ver" href="{up}admin/versions.html#v{E(VERSION)}" title="Site release history: what v{E(VERSION)} changed">v{E(VERSION)}</a>
  <span class="status" title="{E(checks_title())}">{E(STORY["status"])} &middot; evidence to {E(human_time(STORY["checked_at"]))} &middot; <a href="{up}views/loops/index.html" style="color:inherit">last agent run {E(human_time(LAST_RUN[0]))}</a></span>
  <span class="crumbs"><a href="https://newsroom.sgit.ai/">newsroom</a> / <a href="https://2026.newsroom.sgit.ai/">2026</a> / <a href="https://oct.2026.newsroom.sgit.ai/">October</a> / <b>PHP</b></span>
  <div class="tools"><div class="theme-pick"></div><sg-meter view="balance"></sg-meter></div>
  <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav-items" aria-label="Menu">Menu</button>
  <div class="nav-items" id="nav-items">{''.join(nav_items)}</div>
</div></nav>
{__import__('design').LINE_BAND}
<main>
{origin_strip(path, kind, origin, byline)[0]}
{body}
{__import__('design').views_row(globals(), path, up)}
{page_meter}
</main>
<footer class="site">
  <div class="row">
    <p><b>{SITE_NAME}</b> ({SITE}) tracks PHP news for one month. This month that is one story, the two critical PHP security flaws, followed as evidence: every claim with a status and its sources, every source captured, dated and hashed into a private vault. Built and run by one editor and a team of software agents; <a href="{up}team/index.html">the roles</a> and <a href="{up}method/index.html">the method</a> are public, and the site is rebuilt from the vault, never written by hand. One of the SGit Newsroom's story sites: up from here are <a href="https://oct.2026.newsroom.sgit.ai/">October 2026</a>, <a href="https://2026.newsroom.sgit.ai/">the year</a> and <a href="https://newsroom.sgit.ai/">the newsroom</a>, whose own section on the story is <a href="{NEWSROOM}">here</a>. Part of the <a href="https://sgit.ai/network/index.html">sgit.ai network</a>.</p>
    <p class="disc">&#9888; Participant disclosure: published by the sgit project, which builds the vault and metering stack this site runs on. Content CC BY 4.0 for this site's own text, tables and data; quoted words are their authors', linked; no third-party page is reproduced. Code Apache-2.0.</p>
    <p class="small">&#9673; This page sends one anonymous usage event (page, referrer host, a coarse location your browser looks up itself; no IP stored by us, no cookie) to a write-only vault lane; <a href="{up}admin/telemetry/index.html">what is sent and what is counted</a>. Honoured: Do Not Track and Global Privacy Control.</p>
    <p class="small">site v{E(VERSION)} &middot; evidence vault commit {E(D["vault"]["head"]["commit"] or "unknown")} &middot; <a href="{up}admin/index.html">engineering</a> &middot; <a href="{up}{md_path(path)}">this page as markdown</a> &middot; <a href="{up}llms.txt">llms.txt</a> &middot; <a href="{REPO_URL}">GitHub</a></p>
  </div>
</footer>
</body>
</html>
'''

def origin_strip(path, kind, origin=None, byline=None):
    """What this page is: research, external material, a story (house, guest, interview) or about the site. (html, markdown line)"""
    up = '../' * path.count('/')
    if origin in ORIGINS:
        o = ORIGINS[origin]; cls, label, text = 'story', o['label'], o['text'] + (f'. {byline}' if byline else '')
    elif origin == 'external' or path.startswith('readings/') and path != 'readings/index.html':
        cls, label, text = 'external', 'Research, external', 'material from outside, published as received and credited; not written here'
    elif path.startswith('pulse/'):
        cls, label, text = 'elsewhere', 'Elsewhere, a separate section', 'not about PHP: another agent\'s vault, the SGit newsroom\'s Pulse, shown apart from this site\'s evidence'
    elif kind in ('site', 'account') or path.startswith(('admin/', 'account/')):
        cls, label, text = 'site', 'About this site', 'how the site works, kept by the agents that run it'
    else:
        cls, label, text = 'research', 'Research', 'collected from outside sources and what this site derives from them; every fact links to a saved copy of its source'
    html_line = f'<p class="origin o-{cls}"><b>{E(label)}</b> <span>{E(text)}</span> <a href="{up}layers/index.html">Research or story?</a></p>'
    return html_line, f'{label}: {text}.'

def md_path(path):
    return re.sub(r'\.html$', '.md', path)

HTML_OUT = {}  # path -> every page as written, for the pages a release changed (admin/build/release_pages.py)
OUTPUTS = set()  # every file this build writes; admin/build/outputs.txt, read by release.sh to resolve merges

def write(path, content):
    full = os.path.realpath(os.path.join(ROOT, path))
    if not full.startswith(os.path.realpath(ROOT) + os.sep) or any(p.startswith('.') for p in os.path.relpath(full, os.path.realpath(ROOT)).split(os.sep)):
        raise SystemExit(f'build: refusing to write outside the site tree: {path!r}')
    OUTPUTS.add(path)
    if path.endswith('.html'):
        content = __import__('csp').with_csp(path, content)          # admin/build/csp.py: every page carries its policy
        HTML_OUT[path] = content.encode('utf-8')
    os.makedirs(os.path.dirname(full) or ROOT, exist_ok=True)
    with open(full, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)

def page(path, title, description, body, **kw):
    plain = D['plain']['pages'].get(path)
    if plain:
        body = body.replace('</h1>', f'</h1>\n<aside class="plainbox"><b>In plain English</b> {E(plain)}</aside>', 1)
    WORDS[path] = len(re.sub(r'<[^>]+>', ' ', re.sub(r'<(svg|script|table).*?</\1>', ' ', body, flags=re.S)).split())
    md_text = f'# {title}\n\n{description}\n\n' + to_markdown(body)
    sec = ledger_for_page(path, md_text)
    hbody = body
    if sec:
        badge = vbadge(section_id(path), path.count('/'), 'This briefing' if path.startswith('briefings/') else 'This page')
        hbody = body.replace('</h1>', '</h1>\n' + badge, 1)
    html_out = layout(path, title, description, gloss(hbody, path), **kw)
    write(path, html_out)
    md_text = md_text.replace('\n\n', '\n\n> ' + origin_strip(path, kw.get('kind', 'site'), kw.get('origin'), kw.get('byline'))[1] + '\n\n', 1)
    write(md_path(path), md_text + f'\n\n---\nsite v{VERSION} · data as of {STORY["data_as_of"]} · vault commit {D["vault"]["head"]["commit"]} · {BASE_URL}/{path}\n')

def table(headers, rows, cls='t'):
    th = ''.join(f'<th>{h}</th>' for h in headers)
    tr = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

def section(id, title, inner, lead=None):
    return f'<section id="{id}"><h2>{title}</h2>{("<p class=lead>" + lead + "</p>") if lead else ""}{inner}</section>'

def stat(n, label, href=None, depth=0):
    inner = f'<b>{E(str(n))}</b><span>{label}</span>'
    return f'<a class="stat" href="{"../" * depth}{U(href)}">{inner}</a>' if href else f'<div class="stat">{inner}</div>'

def weight(c):
    prim = sum(1 for s in c['sources'] if s in SOURCES and SOURCES[s].get('primary'))
    blocked = sum(1 for s in c['sources'] if s in SOURCES and SOURCES[s].get('status') in ('blocked', 'failed'))
    return prim, len(c['sources']), blocked

def claim_rows(claims, depth):
    rows = []
    for c in claims:
        note = f'<div class="note">{E(c["note"])}</div>' if c.get('note') else ''
        p, n, b = weight(c)
        wt = f'<span class="wt" title="primary sources among the sources cited; blocked captures">{p}/{n}' + (f' <small>({b} blocked)</small>' if b else '') + '</span>'
        rows.append([f'{it_ledger("fact-" + c["id"])}<span id="{E(c["id"])}">{E(c["claim"])}</span>{note} <a class="flink" href="{"../" * depth}facts/{E(c["id"])}/index.html">fact timeline &rarr;</a>', E(c['by']), pill(c['status']), assure(c['id']), wt, src_links(c['sources'], depth)])
    return table(['Claim', 'Who says it', 'Status', f'<a href="{"../" * depth}factcheck/index.html">Fact-check</a>', 'Primary', 'Sources'], rows, 'claims')

def status_legend(depth=0):
    items = ''.join(f'<li>{pill(k)} {E(v)}</li>' for k, v in STATUS_WORDS.items())
    return f'<ul class="legend">{items}<li><span class="wt">p/n</span> primary sources among the n cited; a blocked capture is counted and marked</li></ul>'

def counts():
    c = Counter(x['status'] for x in D['claims'])
    return {'claims': len(D['claims']), 'by_status': c, 'events': len(D['timeline']), 'agencies': len(D['agencies']),
            'numbers': len(D['numbers']), 'signals': len(D['exploitation']), 'sources': D['vault']['sources'],
            'captures': D['vault']['captures'], 'hashed': D['vault']['hashed_files'], 'primary': D['vault']['primary'],
            'blocked': D['vault']['blocked'], 'software': D['software']['count'] if D.get('software') else 0}

C = counts()

# ----------------------------------------------------------------------------- readers: personas, glossary, reading time

WORDS = {}    # path -> words in the page body; filled by page(), read on the second pass
GLOSSED = {}  # path -> glossary ids linked on that page, in order of first use
TERMS = [t for t in D['glossary']['terms']]
TERM = {t['id']: t for t in TERMS}
GLOSS_RX = [(t, [re.compile(m) for m in t['match']]) for t in TERMS if t['match']]
PERSONAS = OrderedDict((p['id'], p) for p in D['personas']['personas'])
GROUPS = OrderedDict((g['id'], g) for g in D['personas']['groups'])
DEPTHS = D['personas']['depths']
AUD = {a['id']: a for a in D['roles']['audiences']}
FLAGSHIP = {'CVE-2026-109618': 'the out-of-memory flaw', 'CVE-2026-109619': 'the stale global state flaw'}
GLOSS_SKIP = {'a', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'svg', 'script', 'style', 'th', 'button', 'summary', 'title', 'label'}
CVE_RX = re.compile(r'\bCVE-\d{4}-\d{4,7}\b')

def minutes(path):
    return max(1, round(WORDS.get(path, 0) / 230))

def nav_title(path):
    if path.startswith('briefings/'):
        return 'Your briefing'
    for _, items in NAV:
        for p, t in items:
            if p == path:
                return t
    return path

def gloss(body, path):
    """Link the first use of every glossary term on the page, and every CVE ID, in text outside links, code and headings."""
    if path.startswith('glossary/'):
        return body
    up = '../' * path.count('/')
    used, out, skip = [], [], 0
    for tok in re.split(r'(<[^>]+>)', body):
        if tok.startswith('<'):
            m = re.match(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)', tok)
            if m and m.group(2).lower() in GLOSS_SKIP and not tok.endswith('/>'):
                skip = max(0, skip + (-1 if m.group(1) else 1))
            out.append(tok)
            continue
        if skip or not tok.strip():
            out.append(tok)
            continue
        spans = []
        for m in CVE_RX.finditer(tok):
            cve = m.group(0)
            if cve in FLAGSHIP:
                href = ('' if path == 'flaws/index.html' else f'{up}flaws/index.html') + f'#{cve}'
                tip = f'{cve}: {FLAGSHIP[cve]}, one of the two php2shell flaws. CVSS 9.2, critical. Fixed 21 October 2026.'
            elif 'cve-' + cve.lower() in SOURCES:
                href, tip = f'{up}sources/cve-{cve.lower()}/index.html', f'{cve}: an earlier flaw; its official record, as captured into the vault.'
            else:
                href, tip = f'https://www.cve.org/CVERecord?id={cve}', f'{cve}: its official record at cve.org.'
            ext = ' rel="noopener"' if href.startswith('http') else ''
            spans.append((m.start(), m.end(), f'<a class="cve-link" href="{href}"{ext} data-term="{cve}" data-tip="{E(tip)}">{cve}</a>'))
        for t, rxs in GLOSS_RX:
            if t['id'] in used:
                continue
            for rx in rxs:
                hit = next((m for m in rx.finditer(tok) if not any(a < m.end() and m.start() < b for a, b, _ in spans)), None)
                if hit:
                    spans.append((hit.start(), hit.end(), f'<a class="term" href="{up}glossary/index.html#{t["id"]}" data-term="{E(t["term"])}" data-tip="{E(t["short"])}">{hit.group(0)}</a>'))
                    used.append(t['id'])
                    break
        spans.sort()
        last, buf = 0, []
        for a, b, rep in spans:
            buf.append(tok[last:a]); buf.append(rep); last = b
        buf.append(tok[last:])
        out.append(''.join(buf))
    GLOSSED[path] = used
    return ''.join(out)

def avatar(p):
    return f'<span class="av av-{E(p["group"])}" aria-hidden="true">{E(p["person"][0])}</span>'

def depth_badge(d):
    d = str(d)
    return f'<span class="depth depth-{d}" title="{E(DEPTHS[d]["text"])}"><i></i><i></i><i></i>{E(DEPTHS[d]["label"])}</span>'

def path_minutes(p):
    return sum(minutes(x) for x in p['path'])

def door(p, depth=0):
    a = AUD[p['id']]
    return (f'<a class="door door-{E(p["group"])}" href="{"../" * depth}briefings/{E(p["id"])}/index.html" data-persona="{E(p["id"])}">'
            f'<span class="dh">{avatar(p)}<span><b>{E(p["label"])}</b><small>{E(p["person"])} &middot; {depth_badge(p["depth"])}</small></span></span>'
            f'<span class="dq">{E(a["question"])}</span>'
            f'<span class="dm">{len(p["path"])} reads &middot; about {path_minutes(p)} min <span class="go">Start &rarr;</span></span></a>')

def persona_doors(depth=0):
    out = ''
    for gid, g in GROUPS.items():
        ps = [p for p in PERSONAS.values() if p['group'] == gid]
        out += f'<div class="dgroup dgroup-{E(gid)}"><h3>{E(g["label"])}</h3><p class="small">{E(g["text"])}</p><div class="doors">{"".join(door(p, depth) for p in ps)}</div></div>'
    return f'<div class="dgroups">{out}</div>'

def reading_path(p, depth):
    items = ''.join(f'<li><a href="{"../" * depth}{E(x)}">{E(nav_title(x))}</a> <span class="small">{minutes(x)} min</span></li>' for x in p['path'])
    return f'<ol class="rpath">{items}</ol><p class="small">About {path_minutes(p)} minutes in all. Choose <i>read as {E(p["person"])}</i> and the bar under the menu keeps your place on every page.</p>'

def words_met(p, depth, limit=14):
    seen = []
    for x in p['path']:
        for t in GLOSSED.get(x, []):
            if t not in seen:
                seen.append(t)
    chips = ''.join(f'<a class="chip" href="{"../" * depth}glossary/index.html#{E(t)}" title="{E(TERM[t]["short"])}">{E(TERM[t]["term"])}</a>' for t in seen[:limit])
    return f'<p class="chips">{chips}</p>' if chips else ''

# ----------------------------------------------------------------------------- pages

def human_time(at):
    """2026-10-22T11:34Z as 22 October 2026, 11:34 UTC."""
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}:\d{2})', at or '')
    if not m:
        return at
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    return f'{int(m.group(3))} {months[int(m.group(2)) - 1]} {m.group(1)}, {m.group(4)} UTC'

PLAIN_STATUS = {'confirmed': 'Confirmed', 'reported': 'Reported', 'disputed': 'Disputed', 'contradicted': 'Contradicted', 'unverified': 'Unverified'}

def build_index():
    s, pl, im = STORY, D['plain'], D['impact']
    when = human_time(s['data_as_of'])
    checked = ' &middot; '.join(f'<a href="{E(href)}">{E(w)}</a>, {E(k)} {E(human_time(t))}' for w, k, t, href in CHECKS)
    fixed = ', '.join(D['affected']['fixed'][:-1]) + ' or ' + D['affected']['fixed'][-1]
    tiles = [
        ('ok', 'Is there a fix?', 'Yes', f'install PHP {fixed}', 'playbook/index.html'),
        ('bad', 'How serious?', 'Critical', '9.2 out of 10, both flaws', 'flaws/index.html'),
        ('warn', 'Does it reach you?', 'Check your stack', 'describe what you run and see what an attacker could reach in it', 'stack/index.html'),
        ('warn', 'Are attackers trying?', 'Yes', 'millions of attempts, seen by one internet security company', 'exploitation/index.html'),
        ('info', 'Anyone confirmed hacked?', 'Not yet', 'no organisation, as of the latest check', 'impact/index.html'),
        ('warn', 'Websites taken offline', f'{len(im["offline"])} reports', 'some one site, some a whole government; as a precaution', 'impact/index.html'),
        ('info', "On the US 'used in attacks' list?", 'Not yet', "the US government's official list of flaws known to be used by attackers", 'exploitation/index.html#kev'),
        ('bad', 'What do governments say?', 'Update now', f'or take the website offline if you cannot; {C["agencies"]} agencies compared', 'agencies/index.html'),
    ]
    board = ''.join(f'<a class="tile tile-{t}" href="{h}"><span class="tl">{E(l)}</span><b>{E(v)}</b><span class="tn">{E(n)}</span></a>' for t, l, v, n, h in tiles)
    now = ''.join(f'<li>{E(x["text"])} <span class="refs">{src_links(x["sources"], 0)}</span></li>' for x in pl['now'])
    facts = ''.join(f'<li><span class="fs">{pill(f["status"])}</span><div><p>{E(f["text"])}</p><p class="ff"><span class="refs">{src_links(f["sources"], 0)}</span> <a href="{U(f["href"])}">More &rarr;</a></p></div></li>' for f in pl['facts'])
    unknown = ''.join(f'<li><a href="{U(u["href"])}">{E(u["text"])}</a></li>' for u in pl['unknown'])
    latest = ''.join(f'<li><span class="when">{E(x["when"])}</span><span>{E(x["text"])} <span class="refs">{src_links(x["sources"], 0)}</span></span></li>' for x in pl['latest'])
    moments = ''.join(f'<li class="m m-{E(m["tone"])}"><a href="{E(m["href"])}"><span class="mw">{E(m["when"])}</span><span class="mt">{E(m["what"])}</span></a><span class="refs">{src_links(m["sources"], 0)}</span></li>' for m in pl['moments'])
    legend = ''.join(f'<li>{pill(k)} {E(v)}</li>' for k, v in [('confirmed', 'two or more original sources agree'), ('reported', 'one party says so; nobody has contradicted it'), ('disputed', 'sources disagree'), ('unverified', 'nobody has been able to check it')])
    evidence = ''.join([
        stat(C['sources'], 'web pages saved as evidence, each with the time it was saved', 'sources/index.html'),
        stat(C['claims'], f'statements checked: {C["by_status"]["confirmed"]} confirmed, {C["by_status"]["disputed"] + C["by_status"]["contradicted"]} disputed, {C["by_status"]["unverified"]} unverified', 'claims/index.html'),
        stat(C['events'], 'dated events, from 2024 to today', 'timeline/index.html'),
        stat(C['agencies'], "government agencies' advice compared", 'agencies/index.html'),
    ])
    def fsec(sid, title, text):
        ledger('front-' + sid, 'Front page: ' + title, 'front', 'index.html', text, scope='front')
        return vbadge('front-' + sid, 0, 'This section')
    b_now = fsec('now', 'right now', '\n'.join(f'{x["text"]} [{", ".join(x["sources"])}]' for x in pl['now']))
    b_glance = fsec('glance', 'at a glance', '\n'.join(f'{l}: {v} ({n})' for t, l, v, n, h in tiles))
    b_facts = fsec('facts', 'the core facts', '\n'.join(f'{f["status"]}: {f["text"]} [{", ".join(f["sources"])}]' for f in pl['facts']))
    b_unknown = fsec('unknown', 'what nobody knows yet', '\n'.join(u['text'] for u in pl['unknown']))
    b_latest = fsec('latest', 'latest', '\n'.join(f'{x["when"]}: {x["text"]} [{", ".join(x["sources"])}]' for x in pl['latest']))
    who_lead = f'The same evidence, put in order for {len(PERSONAS)} kinds of reader. Each starts with a thirty-second answer in plain words. <a href="start/index.html">How the readers are mapped</a>.'
    DZ = __import__('design')
    tone = {'ok': 'good', 'bad': 'alert', 'warn': 'warn', 'info': 'info'}
    kpis = ''.join(DZ.kpi(globals(), tone.get(t, 'info'), l, v, n, h) for t, l, v, n, h in tiles)
    stance = Counter()
    for a in D['agencies']:
        o = a['offline']
        stance['Take offline' if o == 'yes' else 'Isolate or restrict' if o.startswith('isolate') or o == 'restrict from abroad' else 'Offline after other steps' if o in ('after mitigations', 'consider') else 'No offline advice' if o == 'none' else 'Not readable'] += 1
    sorder = [('Take offline', 'var(--alert)'), ('Isolate or restrict', 'var(--warn)'), ('Offline after other steps', '#d6a556'), ('No offline advice', 'var(--info)'), ('Not readable', 'var(--line-2)')]
    sbar = ''.join(f'<div style="flex:{stance[k]};background:{c}" title="{stance[k]} {E(k)}"></div>' for k, c in sorder if stance[k])
    slegend = ''.join(f'<li><i style="background:{c}"></i>{stance[k]} {E(k.lower())}</li>' for k, c in sorder if stance[k])
    journey = ''.join(f'<a class="jst {tone.get(m["tone"], "")}" href="{U(m["href"])}" style="text-decoration:none;color:inherit"><div class="w">{E(m["when"])}</div><div class="x">{E(m["what"])}</div></a>' for m in pl['moments'])
    tracks = D['personas'].get('tracks', {})
    trackcards = ''.join(f'<a class="card" href="{U(t["home"])}" style="text-decoration:none;color:inherit"><p class="eyebrow">{E(t["label"])}</p><p style="margin:.3rem 0 .5rem;color:var(--ink-2)">{E(t["text"])}</p><div class="chips">' + ''.join(f'<span class="chip">{E(pp["label"])}</span>' for pp in PERSONAS.values() if pp.get('track') == k) + '</div></a>' for k, t in tracks.items())
    body = f"""<div class="v2">
<section class="band"><div class="shell hero">
  <div><p class="eyebrow"><span class="live">{E(s["status"])}</span> &nbsp;&middot;&nbsp; PHP news, October 2026 &nbsp;&middot;&nbsp; <a href="#checked" style="color:inherit">latest evidence {E(human_time(s["checked_at"]))}</a> &nbsp;&middot;&nbsp; <a href="views/loops/index.html" style="color:inherit">last agent run {E(human_time(LAST_RUN[0]))}</a></p>
    <h1 class="display">{E(pl["headline"])}</h1>
    <p class="lede">{E(pl["deck"])}</p>
    <div class="chips" style="margin-top:1rem"><a class="iconbtn" href="#now">What is happening now</a><a class="chip" style="background:transparent;color:var(--band-ink);border-color:rgba(255,255,255,.3);padding:.45rem .9rem" href="explained/index.html">Explain it from the start</a><a class="chip" style="background:transparent;color:var(--band-ink);border-color:rgba(255,255,255,.3);padding:.45rem .9rem" href="stack/index.html">Check your stack</a><a class="chip" style="background:transparent;color:var(--band-ink);border-color:rgba(255,255,255,.3);padding:.45rem .9rem" href="now/index.html">On your phone</a></div>
    <p class="small" style="color:var(--band-muted);margin-top:1rem">{E(pl["aka"])}</p></div>
  {DZ.answer_card(globals(), 'board')}
</div></section>
<section class="block" id="state"><div class="tiles">{kpis}</div>{b_glance}</section>
<section class="block"><div class="grid cols-12">
  <div class="span-8 grid" style="align-content:start">
    <div class="card" id="now"><div class="block-head"><h2 class="h2">Right now</h2><span class="small">as of {E(when)}, the latest page this site saved</span></div><ul class="nowlist" style="margin:0">{now}</ul>{b_now}</div>
    <div class="card" id="facts"><div class="block-head"><h2 class="h2">The core facts, and the evidence for each</h2></div><ul class="legend" style="margin:0 0 .6rem">{legend}</ul><ol class="facts">{facts}</ol>{b_facts}</div>
  </div>
  <div class="span-4 grid" style="align-content:start">
    <div class="card" id="latest"><div class="block-head"><h2 class="h2">Latest</h2><a class="small" href="whatsnew/index.html">what changed on the site</a></div><ol class="latest" style="margin:0">{latest}</ol><p class="small" style="margin-bottom:0"><a href="timeline/index.html">Everything, in order &rarr;</a></p>{b_latest}</div>
    <div class="card" id="unknown"><h2 class="h2" style="margin-bottom:.4rem">What nobody knows yet</h2><ul class="unknown" style="margin:0">{unknown}</ul>{b_unknown}</div>
    <div class="card flat" style="background:var(--brand-soft);border-color:transparent"><h3>Ask about it</h3><p class="small" style="color:var(--ink-2)">Answers cite the evidence on this site.</p><a class="iconbtn" href="questions/index.html">Questions readers ask</a></div>
  </div></div></section>
<section class="block"><div class="grid cols-12">
  <div class="card span-7" id="moments">{item('home-moments', 'front', 'research', 'How it unfolded: five moments', 'index.html#moments', moments, REL_DATE.get(VERSION, ''))}<div class="block-head"><h2 class="h2">How it unfolded</h2><a class="small" href="timeline/index.html">The full timeline</a></div><div class="journey">{journey}</div></div>
  <div class="card span-5"><div class="block-head"><h2 class="h2">What governments advise</h2><span class="small">{len(D["agencies"])} agencies</span></div><p style="margin:.2rem 0 .8rem;color:var(--ink-2)">All say install the fix. They split on what to do if you cannot.</p><div style="display:flex;height:22px;border-radius:7px;overflow:hidden;gap:2px">{sbar}</div><ul class="legend">{slegend}</ul><p class="small" style="margin-bottom:0"><a href="agencies/index.html">Every agency, in its own words &rarr;</a></p></div>
</div></section>
<section class="block" id="views"><div class="block-head"><h2 class="h2">Three ways to read this site</h2><span class="small">choose who you are in the bar above; the site takes you to yours</span></div><div class="tiles" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))">{trackcards}</div></section>
<section class="block" id="who">{item('home-who', 'front', 'for-you', 'The briefing for you: fifteen readers', 'index.html#who', re.sub(r'\d+', '#', persona_doors()), REL_DATE.get(VERSION, ''))}<div class="block-head"><h2 class="h2">The briefing for you</h2><span class="small"><a href="start/index.html">How the readers are mapped</a></span></div>{persona_doors()}</section>
<section class="block" id="stories">{item('home-stories', 'front', 'stories', 'Stories: written here', 'index.html#stories', re.sub(r'\d+', '#', stories_row()), REL_DATE.get(VERSION, ''))}<div class="block-head"><h2 class="h2">Stories: written here</h2><span class="small">signed, dated and kept as written; everything above is research</span></div>{stories_row()}</section>
<aside class="origin o-elsewhere"><b>What else is going on</b> <span>Other vulnerabilities in the news this month, with the evidence that each is exploited beside the attention it gets: the SGit newsroom's Pulse, in a separate section, not about PHP.</span> <a href="pulse/index.html">Pulse &rarr;</a></aside>
<section class="block" id="evidence">{item('home-how', 'front', 'site', 'How this site knows', 'index.html#evidence', 'how this site knows: saved, fingerprinted, agents for one editor', REL_DATE.get(VERSION, ''))}<div class="card"><h2 class="h2" style="margin-bottom:.6rem">How this site knows</h2><div class="stats">{evidence}</div><p>Every page this site relies on was saved at the moment it was read, with a fingerprint that proves it has not been altered since, so a fact can be checked even if the original page changes or disappears. Nothing here is advice for your own systems; for that, read <a href="https://www.php.net/archive/2026.php#2026-10-21-5" rel="noopener">the PHP project's announcement</a> and your national cyber agency. The site is put together by software agents working for one editor, Dinis Cruz; <a href="method/index.html">how it works</a>.</p><p id="checked" class="small">Latest evidence: {checked}. Last agent run: {E(human_time(LAST_RUN[0]))} ({E(LAST_RUN[1])}); <a href="views/loops/index.html">how the site is kept current, loop by loop</a>. Already know the vocabulary? <a href="summary/index.html">The specialist summary</a> has the technical version of this page.</p></div></section>
</div>{DZ.answers_json(globals())}
"""
    page('index.html', s['title'], s['description'], body, kind='story', topics='php october 2026 overview', ld_type='NewsArticle')

def build_summary():
    s = STORY
    known = ''.join(f'<li>{k["html"]} <span class="refs">{src_links(k["sources"], 1)}</span></li>' for k in s['known'])
    openq = ''.join(f'<li>{o["html"]}</li>' for o in s['open'])
    stats = ''.join([
        stat(C['sources'], 'sources in the evidence vault', 'sources/index.html', 1),
        stat(C['captures'], 'dated captures, each file hashed', 'sources/index.html', 1),
        stat(C['claims'], f'claims with a status: {C["by_status"]["confirmed"]} confirmed, {C["by_status"]["disputed"] + C["by_status"]["contradicted"]} disputed or contradicted, {C["by_status"]["unverified"]} unverified', 'claims/index.html', 1),
        stat(C['events'], 'dated events on the timeline', 'timeline/index.html', 1),
        stat(C['agencies'], 'national agencies compared', 'agencies/index.html', 1),
        stat(len(D['impact']['offline']), 'operators reported offline, 0 confirmed compromises', 'impact/index.html', 1),
        stat(C['software'], 'products in the NCSC-NL inventory', 'affected/software.html', 1),
    ])
    latest = sorted([t for t in D['timeline'] if t['at'] >= '2026-10-20'], key=lambda t: t['at'])[-8:]
    latest_rows = [[f'<span class="when">{E(fmt_at(t["at"]))}</span>', E(t['event']), src_links(t['sources'], 1)] for t in latest]
    numrow = ''.join(f'<a class="num" href="../numbers/index.html#{E(n["id"])}"><b>{E(n["value"])}</b><span>{E(n["of"])}</span>{pill(n["status"])}</a>' for n in D['numbers'][:6])
    body = f'''
<p class="kicker">The story &middot; for specialists</p>
<h1>The specialist summary: php2shell, CVE-2026-109618 and CVE-2026-109619</h1>
<p class="lead">{s["lead_html"]}</p>
<div class="stats">{stats}</div>
<p class="caveat">{s["caveat_html"]}</p>
{section("numbers", "Six numbers, and what each one measures", f'<div class="nums">{numrow}</div><p>The figures in circulation range from 2.6 million hosts to 70% of the Internet. They are not contradictory so much as incommensurable: each measures a different thing. <a href="../numbers/index.html">The numbers page</a> says what each one counts, who said it, and whether anyone has checked it.</p>')}
{section("known", "What is established", f'<ul class="known">{known}</ul>')}
{section("open", "What is not", f'<ul class="open">{openq}</ul>', "Open questions, stated rather than papered over. Each one names what would close it.")}
{section("latest", "The last 48 hours", table(["When (UTC)", "What", "Source"], latest_rows, "tl") + '<p><a href="../timeline/index.html">The whole timeline &rarr;</a> runs from the 2024 audit to the latest capture, with every time stated as its source states it and every conversion marked.</p>')}
{section("how", "How this site works", '<p>Every source is captured into a private, encrypted vault, each file hashed at capture time; every claim carries one of five status words and the sources that earn it; the site is a deterministic build of the vault, and a gate refuses a broken link, an unsourced claim or a credential. <a href="../method/index.html">The method</a>, <a href="../team/index.html">the team</a> and <a href="../billing/index.html">the billing model</a> are published.</p>')}
'''
    page('summary/index.html', 'The specialist summary: CVE-2026-109618 and CVE-2026-109619', 'The technical summary of the two PHP flaws of October 2026: what is established with its sources, the six scale figures, the open questions and the last 48 hours.', body, kind='story', topics='php2shell summary')

def build_flaws():
    a = D['affected']
    cves = [
        {'id': 'CVE-2026-109618', 'ghsa': 'GHSA-w8hw-w9fx-j79w', 'title': 'RCE via OOM corruption', 'src': ['cve-cve-2026-109618', 'github-ghsa-w8hw-w9fx-j79w', 'nvd-cve-2026-109618', 'openwall-oss-security-2026-10-21-6'],
         'desc': 'PHP uses longjmp() for out-of-memory (OOM) errors to exit the current context and abort handling of the request. Some contexts may not properly account for this scenario and leave request memory in an uninitialized state before performing an allocation. The subsequent request cleanup procedure may read or branch on this memory. Multiple OOM strategies can consistently trigger this condition and lead to remote code execution (RCE).',
         'reserved': '2026-10-12T21:03:58Z', 'published': '2026-10-21T13:48:34Z', 'ghsa_at': '2026-10-21T13:34:25Z',
         'demo': 'Complete RCE validated over HTTP against mod_php with default input and memory limits, before any application code runs. FPM: susceptible by source analysis; the GitHub advisory says no complete FPM exploit has been demonstrated. FrankenPHP likely susceptible; LSAPI likely but unvalidated.',
         'fix': 'Removes longjmp() for OOM. A delayed, graceful soft OOM at the next VM safe point, plus a hard OOM via _exit() at a higher threshold.'},
        {'id': 'CVE-2026-109619', 'ghsa': 'GHSA-6wmf-4rv5-p3rp', 'title': 'RCE via stale global state', 'src': ['cve-cve-2026-109619', 'github-ghsa-6wmf-4rv5-p3rp', 'nvd-cve-2026-109619', 'openwall-oss-security-2026-10-21-7'],
         'desc': 'PHP has various global state that temporarily points into request memory. In some scenarios, global state may not be correctly reset, or may be repopulated after being reset. The global state may then refer to request memory even after it has been freed. Subsequent requests may read or branch on this stale state before it is fully initialized. Multiple strategies can trigger this condition and produce remote code execution (RCE).',
         'reserved': '2026-10-12T21:04:00Z', 'published': '2026-10-21T13:54:43Z', 'ghsa_at': '2026-10-21T13:34:13Z',
         'demo': 'A use-after-free of worker global state across requests: a producer request and a consumer request on the same worker. Confirmed on the PHP 8.5 fatal-error-backtrace path (the basis of the mod_php exploit) and the session upload progress path, which is enabled by default and needs no session_start(); the session path was validated against mod_php and FPM.',
         'fix': 'Part of the same change, "Avoid state corruption via bailout": global state is reset so it cannot refer to freed request memory.'},
    ]
    cards = ''
    for c in cves:
        cards += f'''<article class="cve" id="{E(c["id"])}">
<h3>{E(c["id"])}: {E(c["title"])}</h3>
<p class="meta">{E(c["ghsa"])} &middot; CVSS v4.0 <b>9.2</b> &middot; CWE-416, 755, 824, 1325, 1419 &middot; reserved {E(fmt_at(c["reserved"]))} &middot; advisory {E(fmt_at(c["ghsa_at"]))} &middot; CVE record {E(fmt_at(c["published"]))}</p>
<p class="verb"><b>The record's description, verbatim.</b> <q>{E(c["desc"])}</q></p>
<p><b>What was demonstrated.</b> {E(c["demo"])}</p>
<p><b>The fix.</b> {E(c["fix"])}</p>
<p class="refs">{src_links(c["src"], 1)}</p>
</article>'''
    vector = 'CVSS:4.0/AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N'
    sapis = table(['SAPI', 'Risk', 'What the primary sources say', 'Sources'], [[E(s['sapi']), E(s['risk']), E(s['text']), src_links(s['sources'], 1)] for s in a['sapis']])
    blast = '''
<p>Remote code execution <i>as the web worker</i> is the floor, not the ceiling, and not yet a breach. What an attacker gets is whatever that worker can reach: the application's source and configuration, the database credentials in it, the session store, the files the worker can read or write, the outbound network it can open, and anything that trusts requests from that host. What they do not automatically get is the database server's other schemas, the credentials that were never on that host, or a system behind an allow-list the worker is not on. The blast radius of one compromised PHP worker is therefore a property of the system around it, and that is the first thing to map. The questions, with where the answer usually lives:</p>
<ul>
<li><b>What runs there?</b> A brochure site with no login, a shop with payment data, an intranet with single sign-on, a mail client, an admin panel. The same bug has a different consequence in each. (The NCSC-NL inventory is a start; your asset register is the real answer.)</li>
<li><b>What credentials sit on the host?</b> Database passwords, API keys, cloud instance roles, SSH keys in a deploy user's home. A key that cannot be used from anywhere else is a much smaller loss than one that can.</li>
<li><b>What can the worker reach outbound?</b> Egress rules decide whether a shell becomes a download of tooling, a callback, or a pivot.</li>
<li><b>What trusts the host?</b> Internal services that accept any request from the web tier, shared file systems, backup agents.</li>
<li><b>What would you see?</b> CISA's signal is concrete: PHP worker processes launching shells or downloading tools. JPCERT warns that with several exploit paths, one detection rule can miss an attack and a clean log does not prove a clean system.</li>
<li><b>How fast can you pull the plug?</b> Taking a system offline is the last step in every agency's list, but the ability to do it in minutes, cleanly, is a property worth having before the next one of these.</li>
</ul>
<p class="refs">''' + src_links(['cisa-alert-php-20261021', 'jpcert-at260033', 'github-ghsa-6wmf-4rv5-p3rp', 'ncsc-nl-php2shell-software-list'], 1) + '</p>'
    body = f'''
<h1>The two flaws</h1>
<p class="lead">Two bugs in the PHP engine, the same severity, the same fix, the same four releases. Both are memory-safety failures in how PHP recovers from an error, and both can be reached by an unauthenticated HTTP request. This page keeps to what the primary records say and marks where they differ.</p>
<p class="kv"><b>Fixed in</b> PHP {", ".join(a["fixed"])} &middot; <b>Vector</b> <code>{vector}</code> &middot; <b>Nickname</b> php2shell (NSA: PHP2Shell) &middot; <b>CNA</b> PHP Group</p>
{cards}
{section("sapis", "Which deployments", sapis, "The flaw is in the engine, so what matters is how PHP is wired to the web server. php.net ranks mod_php highest.")}
{section("blast", "What a compromise would mean: the blast radius", blast, "This section is the site's own analysis, written from the sources it cites. It is a way of asking the question, not an assessment of any system.")}
{section("versions", "Affected and fixed versions", table(['Branch', 'Affected', 'Fixed', 'In the CVE record'], [[E(r['branch']), E(r['affected']), E(r['fixed']), 'yes' if r['in_cve'] else '<b>no</b>'] for r in a['ranges']]) + f'<p>{E(a["ranges_note"])}</p><p class="refs">{src_links(a["ranges_sources"], 1)}</p>')}
{section("mitigations", "The temporary mitigations, and what each one does not do", table(['For', 'Setting', 'Caveat, from the same source'], [[E(m['for']), E(m['what']), E(m['caveat'])] for m in a['mitigations']]) + f'<p>php.net: <q>while only an update is a complete solution, the following measures reduce exposure to specific attack paths but do not make an installation safe.</q> <span class="refs">{src_links(a["mitigations_sources"], 1)}</span></p>')}
<p>The engineering steps, in order, are on <a href="../playbook/index.html">If you run PHP</a>. The disagreement between the two primary accounts of FPM is <a href="../claims/index.html#rce-fpm">claim rce-fpm</a>.</p>
'''
    page('flaws/index.html', 'The two flaws: CVE-2026-109618 and CVE-2026-109619', 'What the CVE records, the GitHub advisories and the PHP security team say about php2shell: the bug classes, what was demonstrated, which deployments, which versions, the fix and the temporary mitigations, with the blast-radius questions.', body, kind='story', topics='php2shell technical cve')

def build_timeline():
    phases = OrderedDict([('origin', 'Origins, 2024 to mid-2026'), ('discovery', 'Discovery, August 2026'), ('coordination', 'Coordinated disclosure, August to 19 October'),
                          ('leak', 'The leak, 17 to 21 October'), ('release', 'The release, 21 October 13:30 to 14:44 UTC'), ('response', 'The response, 20 to 22 October'),
                          ('aftermath', 'Aftermath, 21 to 22 October'), ('method', 'This site')])
    evs = sorted(D['timeline'], key=lambda t: (t['at'], t['event']))
    out = ''
    for ph, title in phases.items():
        rows = [[f'{it_event(t)}<span class="when">{E(fmt_at(t["at"]))}</span>', E(t['event']) + (f'<div class="note">{E(t["note"])}</div>' if t.get('note') else ''), pill(t['confidence']), src_links(t['sources'], 1)] for t in evs if t.get('phase') == ph]
        if rows:
            out += section('ph-' + ph, title, table(['When', 'What', 'Time is', 'Sources'], rows, 'tl'))
    legend = '<ul class="legend"><li>' + pill('stated') + ' the source states this date or time</li><li>' + pill('inferred') + ' this site worked it out, and the note says how</li><li>' + pill('disputed') + ' the sources give different times</li></ul>'
    body = f'''
<h1>The timeline</h1>
<p class="lead">{C["events"]} events from the 2024 audit to the latest capture, each dated as its source states it. Times are UTC; where this site converted from a local time, or inferred a date from a phrase such as <q>two days ago</q>, the row says so. A row that lists several sources is one that at least two accounts carry; a row with one source is that party's account.</p>
{legend}
{out}
<p>The sequence as a graph of who said what first is on <a href="../discovery/index.html">Who found it</a>; the leak alone is on <a href="../leak/index.html">How disclosure broke</a>.</p>
'''
    page('timeline/index.html', 'The timeline, 2024 to the latest capture', f'{C["events"]} dated events in the php2shell story, from the 2024 audit through discovery, coordinated disclosure, the leak, the release and the response, every one tied to a captured source.', body, kind='story', topics='php2shell timeline')

def build_claims():
    topics = OrderedDict([('technical', 'The flaws themselves'), ('scale', 'How big it is'), ('discovery', 'Who found it, and how'), ('leak', 'The leak'),
                          ('timing', 'When things happened'), ('exploitation', 'Exploitation'), ('advice', 'What the agencies advise'), ('impact', 'What was taken offline')])
    out = ''
    for t, title in topics.items():
        cs = [c for c in D['claims'] if c['topic'] == t]
        if cs:
            out += section('t-' + t, title, claim_rows(cs, 1))
    counts = ', '.join(f'{C["by_status"][k]} {k}' for k in STATUS_WORDS if C['by_status'][k])
    body = f'''
<h1>Every claim, and who makes it</h1>
<p class="lead">{C["claims"]} claims: {counts}. A claim is a sentence somebody said, with the party that said it, the captured sources it comes from, and one of five words for how far it can be trusted. The words are defined here, once, and the build refuses a claim whose sources are not in the manifest.</p>
{status_legend()}
{out}
<p>The newsroom's own twelve claims, seeded from the BBC live page on the morning of 22 October, are in the vault as <code>claims/claude-newsroom-lead.json</code> and are superseded by the rows above, which trace each of them to primary sources. The raw rows are in <a href="../data/claims.json">data/claims.json</a>.</p>
'''
    page('claims/index.html', 'Every claim, with its status and sources', f'{C["claims"]} claims about php2shell, each with who makes it, a status (confirmed, reported, disputed, contradicted or unverified) and the captured sources behind it.', body, kind='analysis', topics='php2shell claims provenance')

def build_claim_review():
    """Every claim in the vault's per-agent files that is not in the site's claim table, with the journalist's verdict, or 'not yet reviewed'."""
    site_ids = {c['id'] for c in D['claims']}
    rv = {r['id']: r for r in D['claim-review']['reviews']}
    vc = D['vault-claims']
    for i in rv:
        if i not in {c['id'] for c in vc}:
            sys.exit(f'data/claim-review.json: {i} is not a claim in data/vault-claims.json')
    pending = [c for c in vc if c['id'] not in site_ids]
    groups = OrderedDict([('held back', [])] + [(k, []) for k in D['claim-review']['verdicts'] if k != 'held back'] + [('not yet reviewed', [])])
    for c in pending:
        groups[rv[c['id']]['verdict'] if c['id'] in rv else 'not yet reviewed'].append(c)
    words = D['claim-review']['verdicts']
    def rows(cs):
        out = []
        for c in cs:
            r = rv.get(c['id'])
            verdict = (f'<b>{E(r["verdict"])}</b><div class="note">{E(r["reason"])}</div>' + (f'<div class="refs">{src_links(r["sources"], 2)}</div>' if r.get('sources') else '')
                       + (f'<div class="small"><a href="../../{E(r["where"])}">where it was reviewed</a>, {E(r["reviewed"])}, {E(r["by"])}</div>' if r.get('where') else '')) if r else '<span class="small">not yet reviewed</span>'
            out.append([f'<span id="{E(c["id"])}"><b>{E(c["claim"])}</b></span><div class="small"><code>{E(c["id"])}</code> &middot; {E(c.get("topic") or "")}</div>',
                        E(c.get('by') or ''), pill(c['status']), f'{E(c.get("note") or "")}<div class="small">{E(c.get("agent") or "")}</div>', src_links(c['sources'], 2), verdict])
        return table(['Claim, as the agent recorded it', 'Said by', 'Agent\'s status', 'Agent\'s note', 'Sources', 'Journalist\'s review'], out, 'rv')
    agents = Counter(c.get('agent') for c in pending)
    body = f'''
<h1>Claims waiting for review</h1>
<p class="lead">{len(pending)} claims recorded in the evidence vault by its agents are not in the site's <a href="../index.html">claim table</a> yet: {", ".join(f"{n} from {E(a)}" for a, n in agents.most_common())}. They are listed here so that they can be reviewed, not because they are established. Each is the agent's reading of a captured page, in the agent's words; for a page in another language the English is the agent's translation. The status beside each is the agent's, not the site's.</p>
<p>The journalist has reviewed {len(rv)} of them: {", ".join(f"{len(v)} {k}" for k, v in groups.items() if v and k != "not yet reviewed")}. What the review words mean: {"; ".join(f"<b>{E(k)}</b>, {E(v)}" for k, v in words.items())}. A claim with no review is marked so, and a new export of the vault adds new claims here without anyone editing this page. The rows are <a href="../../data/vault-claims.json">data/vault-claims.json</a>; the reviews are <a href="../../data/claim-review.json">data/claim-review.json</a>.</p>
{"".join(section("g-" + k.replace(" ", "-"), f"{k[0].upper() + k[1:]} ({len(v)})", rows(v)) for k, v in groups.items() if v)}
'''
    page('claims/review/index.html', 'Claims waiting for review', f'{len(pending)} claims from the evidence vault that are not in the site claim table yet, each with the agent that recorded it, its sources, and the journalist\'s verdict or "not yet reviewed".', body, kind='analysis', topics='php2shell claims review provenance')

def build_numbers():
    rows = []
    for n in D['numbers']:
        rows.append([f'<b id="{E(n["id"])}">{E(n["value"])}</b><br><span class="small">{E(n["of"])}</span>', E(n['measures']), E(n['who']), pill(n['status']), E(n['note']), src_links(n['sources'], 1)])
    body = f'''
<h1>The numbers, and what each one measures</h1>
<p class="lead">The editor's starting point for this site was a figure that did not add up: <q>70% of the internet</q>. It turns out to be a headline's restatement of a share-of-websites statistic that nobody on this beat sources, sitting next to a host count a thousand times smaller and a national count a thousand times smaller again. None of them is wrong on its own terms. The table says what each one counts.</p>
{table(['Figure', 'What it measures', 'Who said it', 'Status', 'Note', 'Sources'], rows, 'nums-t')}
{section("why", "Why they differ by four orders of magnitude", '''
<ul>
<li><b>A share of websites that use PHP</b> (about 70%) is the population a survey counts by looking at response headers and page markup across a sample of the web. It includes every site on a shared host that patched hours ago, every site behind a CDN, and every site that has not been touched since 2019. It is an upper bound on exposure.</li>
<li><b>Internet-facing hosts that expose PHP</b> (2.6 million, one scanner's count) is a count of machines, not sites. One host serves many sites; most sites sit behind hosts that do not announce PHP at all. It is a lower bound on the machines an attacker could reach directly.</li>
<li><b>Websites that could be affected</b> (30 million) has no stated basis. It may be a fraction of a websites total; it may be a guess.</li>
<li><b>Resources potentially affected in one country</b> (about 6,000 in Latvia) is the only figure from a body that could inventory what it counts. Scaled naively by population it would put the EU in the low millions, which is a different number from any of the above and is not offered here as one.</li>
<li><b>Products in an inventory</b> (674) counts software, not deployments: one row is WordPress, another is a Linux distribution's package.</li>
</ul>
<p>The number a reader actually wants, how many systems were exploitable at a given hour and how many were exploited, does not exist in any captured source. What exists is a set of signals, on <a href="../exploitation/index.html">the exploitation page</a>.</p>''')}
'''
    page('numbers/index.html', 'The numbers: 70%, 30 million, 2.6 million, 6,000, 674', 'Every scale figure in circulation about php2shell, with what it measures, who said it, whether anyone checked it, and why they differ by four orders of magnitude.', body, kind='analysis', topics='php2shell numbers scale')

def build_agencies():
    ag = D['agencies']
    offl = Counter(a['offline'] for a in ag)
    rows = [[f'<b>{E(a["agency"])}</b><br><span class="small">{E(a["country"])}</span>', E(a['published']), f'{pill(a["offline"])}<div class="note">{E(a["offline_text"])}</div>', E(a['exploitation']), E(a['note']), src_links(a['sources'], 1)] for a in ag]
    summary = ', '.join(f'{n} say <i>{E(k)}</i>' for k, n in sorted(offl.items(), key=lambda kv: -kv[1]))
    spectrum_c, cards_c = __import__('design').agency_parts(globals(), '../')
    body = f'''
<h1>The agencies, side by side</h1>
<div class="v2"><div class="card flat" style="background:var(--band);color:var(--band-ink);border:0;margin:.4rem 0 1.2rem"><p class="eyebrow" style="color:var(--band-muted);margin:0 0 .3rem">In one line</p><p style="font-size:1.15rem;margin:0">All {len(ag)} say install the fix. They split on what to do with a system you cannot patch today: the US says take it offline, the UK makes that the fourth step, Europe says isolate, and Australia, Japan and the Netherlands say nothing about it.</p></div>
{spectrum_c}
<div class="block-head" style="margin-top:1.6rem"><h2 class="h2">Agency by agency</h2><span class="small">each in its own words, with its saved sources</span></div>{cards_c}
<h2 class="h2" style="margin-top:1.8rem">The evidence table</h2></div>
<p class="lead">{len(ag)} national and supranational bodies, each read from its own page. The question that divides them is not whether to patch (all say patch) but what to do with a system that cannot be patched now. Of {len(ag)}: {summary}. Two could not be read because their sites block automated browsers; the block is recorded.</p>
<p>The BBC's morning framing, <q>the UK's NCSC, the NSA and their counterparts in the EU and Australia advise taking systems offline</q>, holds for the NSA and CISA, is a simplification of the NCSC's fourth of six steps, and is not supported by the Australian page at all. The sentence the BBC quotes from the NCSC is not on the NCSC page as captured; its opening matches the Canadian text.</p>
{table(['Agency', 'Published', 'Offline?', 'Exploitation', 'Note', 'Sources'], rows, 'ag')}
<p>Each agency's full text is in its capture; the sentences here are the ones the collectors copied verbatim into their notes. Translations from French, Italian, Latvian and Japanese are this site's and are marked as such in the notes.</p>
'''
    page('agencies/index.html', 'What sixteen agencies actually advise', 'The NSA, CISA, the UK NCSC, CERT-EU, ENISA, CERT-FR, Canada, Australia, New Zealand, the Netherlands, Italy, Switzerland, Latvia, Japan, Spain and Portugal on php2shell: who says take it offline, who says isolate, who says patch and nothing more, and who has seen exploitation.', body, kind='analysis', topics='php2shell agencies advisories')

def build_affected():
    a, sw = D['affected'], D['software']
    st18, st19 = sw['by_status_109618'], sw['by_status_109619']
    sup = Counter((r.get('supplier') or '').strip() for r in sw['rows'])
    top = sorted(sup.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    vuln = [r for r in sw['rows'] if r.get('status_109618') == 'Vulnerable' or r.get('status_109619') == 'Vulnerable']
    fixed = [r for r in sw['rows'] if r.get('status_109618') == 'Fix' and r.get('status_109619') == 'Fix']
    body = f'''
<h1>Affected systems</h1>
<p class="lead">Three layers: the PHP versions, the ways PHP is attached to a web server, and the software that runs on top. The first two come from the PHP project. The third comes from NCSC-NL's public inventory, which this site counts rather than quotes: {sw["count"]} products at commit <code>{E(sw["commit"] or "")}</code>, of which {st18.get("Vulnerable", 0)} are marked vulnerable to CVE-2026-109618, {st18.get("Fix", 0)} fixed, {st18.get("Investigation", 0)} under investigation and {st18.get("Not vuln", 0)} not vulnerable.</p>
{section("versions", "Versions", table(['Branch', 'Affected', 'Fixed', 'In the CVE record'], [[E(r['branch']), E(r['affected']), E(r['fixed']), 'yes' if r['in_cve'] else '<b>no</b>'] for r in a['ranges']]) + f'<p>{E(a["ranges_note"])} <span class="refs">{src_links(a["ranges_sources"], 1)}</span></p>')}
{section("sapis", "Deployments", table(['SAPI', 'Risk', 'What the primary sources say', 'Sources'], [[E(s['sapi']), E(s['risk']), E(s['text']), src_links(s['sources'], 1)] for s in a['sapis']]))}
{section("apps", "Applications", f'<p>{E(a["applications_confirmed"]["text"])} <span class="refs">{src_links(a["applications_confirmed"]["sources"], 1)}</span></p>')}
{section("inventory", "The NCSC-NL inventory, counted", table(['Status', 'CVE-2026-109618', 'CVE-2026-109619'], [[E(k), E(str(st18.get(k, 0))), E(str(st19.get(k, 0)))] for k in ['Vulnerable', 'Fix', 'Investigation', 'Not vuln', 'none']]) + f'''
<p>NCSC-NL generates the list from an SPDX 3 inventory with VEX statements and says an entry is an investigation lead until a vendor or upstream backs it. {len(fixed)} products carry a fix for both CVEs; {len(vuln)} are marked vulnerable to at least one. The suppliers with the most entries:</p>''' + table(['Supplier', 'Entries'], [[E(s), E(str(n))] for s, n in top]) + f'<p><a href="software.html">The full inventory, all {sw["count"]} rows &rarr;</a> The parsed file is in the vault as <code>{E(sw["file"])}</code>; the repository bundle and tree at the same commit are there too. <span class="refs">{src_links(["ncsc-nl-php2shell-software-list", "ncsc-nl-php2shell"], 1)}</span></p>')}
'''
    page('affected/index.html', 'Affected systems: versions, deployments, applications, inventory', f'Which PHP versions and SAPIs php2shell affects, which applications had RCE demonstrated, and the NCSC-NL inventory of {sw["count"]} products counted by status.', body, kind='analysis', topics='php2shell affected inventory')
    rows = []
    for r in sw['rows']:
        links = ' '.join(f'<a href="{E(u)}" rel="noopener nofollow">{E(re.sub(r"^https?://(www\.)?", "", u).split("/")[0])}</a>' for u in (r.get('links') or [])[:3])
        rows.append([E(r.get('supplier') or ''), E(r.get('product') or ''), E(r.get('version') or ''), pill(r.get('status_109618') or 'none'), pill(r.get('status_109619') or 'none'), E((r.get('notes') or '').split('\n')[0][:220]), links])
    body = f'''
<h1>The NCSC-NL software inventory</h1>
<p class="lead">All {sw["count"]} rows of NCSC-NL's php2shell inventory at commit <code>{E(sw["commit"] or "")}</code>, as parsed into the vault. Status is NCSC-NL's per CVE; the note is the first line of theirs. Licence EUPL-1.2. This page is generated from the parsed file and changes only when the vault does. <span class="refs">{src_links(["ncsc-nl-php2shell-software-list", "ncsc-nl-php2shell"], 1)}</span></p>
{table(['Supplier', 'Product', 'Version', '109618', '109619', 'NCSC-NL note', 'Links'], rows, 'sw')}
'''
    page('affected/software.html', f'The NCSC-NL inventory: {sw["count"]} products', f'Every row of the NCSC-NL php2shell software inventory at commit {sw["commit"]}, with its status per CVE.', body, kind='evidence', topics='php2shell inventory')

def build_exploitation():
    rows = [[E(fmt_at(x['when'])), E(x['who']), E(x['what']), E(x['kind']), pill(x['status']), src_links(x['sources'], 1)] for x in sorted(D['exploitation'], key=lambda x: x['when'])]
    body = f'''
<h1>Exploitation: the signals, in order</h1>
<p class="lead">A remote code execution bug is not an invisibility cloak. If millions of systems were being exploited, the signals would be everywhere: honeypots, WAF logs, national CERTs, the KEV catalog. What the captured sources carry is {len(D["exploitation"])} signals, from one honeypot hit four days before disclosure to one agency's unattributed <q>reports of active exploitation</q>, and no confirmed compromise of a named system. That is the state as of the latest capture, and this page will change.</p>
{table(['When (UTC)', 'Who', 'What', 'Kind', 'Status', 'Sources'], rows, 'ex')}
{section("look", "What exploitation would look like", '''
<ul>
<li><b>On the host:</b> CISA's signal is <q>PHP worker processes launching shells or downloading tools</q>. The exploit runs as the web worker, so a worker spawning <code>sh</code>, <code>curl</code> or <code>wget</code>, or writing outside its document root, is the thing to alert on.</li>
<li><b>In the request log:</b> CERT-FR's workaround is to block or monitor multipart requests, because the confirmed session path rides on session upload progress; php.net's limits are on decoded request size, field count, multipart part count, header count and nesting depth. Unusual values of those are the request-side signal for the OOM path.</li>
<li><b>What a clean log does not prove:</b> JPCERT warns that with several exploit paths, one detection rule can miss an attack and the absence of traces does not prove the absence of compromise. The UK NCSC says a system that cannot be patched or disabled should be assessed for backdoors.</li>
<li><b>Upstream:</b> Cloudflare says its rules blocked the traffic it saw and that attackers mutated payloads; a WAF is a signal source as well as a control, and the Swiss agency's caveat is that it is not a sufficient control on its own.</li>
</ul>
<p class="refs">''' + src_links(['cisa-alert-php-20261021', 'certfr-2026-ale-014', 'php-net-advisory', 'jpcert-at260033', 'ncsc-news-php', 'cloudflare-blog-php2shell-waf', 'ch-bacs-warnung-php'], 1) + '</p>')}
{section("kev", "The Known Exploited Vulnerabilities catalog", f'<p>CISA adds a CVE to KEV when it has reliable evidence of exploitation in the wild. At catalog version 2026.10.21, released 2026-10-21 14:04:39 UTC and fetched 2026-10-22 08:15 UTC, neither CVE-2026-109618 nor CVE-2026-109619 is listed; the catalog has 1,754 entries and its newest additions are dated 20 October. CISA\'s vulnerability-enrichment assessment on both CVE records at 14:34 UTC says exploitation <i>none</i>. This is a point-in-time negative finding; the vault keeps the file and its hash so that the time can be proven later. <span class="refs">{src_links(["cisa-kev-json", "cisa-kev-catalog", "cve-cve-2026-109618"], 1)}</span></p>')}
'''
    page('exploitation/index.html', 'Exploitation signals, in order', 'Every signal of php2shell exploitation in the captured sources, from an Amazon honeypot hit on 17 October to the KEV catalog, with what exploitation would look like on a host.', body, kind='story', topics='php2shell exploitation detection')

KIND_INK = {'attempts': 'var(--warm)', 'vendor-exploitation': 'var(--bad-ink)', 'no-success-known': 'var(--ok-ink)',
            'named-organisation': 'var(--accent)', 'allegation': 'var(--dim)', 'official-signal': 'var(--accent-dk)'}

def build_compromise():
    """One statement and the evidence behind it, row by row, with what each kind of evidence can and cannot show.
    Drawn from data/compromise.json; maps evidence, makes no assessment of risk."""
    C = D['compromise']; rows, kinds = C['rows'], C['kinds']
    kname = {k['id']: k['name'] for k in kinds}
    def where(r):
        out = src_links(r['sources'], 1) if r.get('sources') else ''
        if r.get('watch'):
            out += f' <span class="note">source watch: <code>{E(r["watch"])}</code></span>'
        return out
    # 1. the evidence by kind, as bars
    counts = [(k, sum(1 for r in rows if r['kind'] == k['id'])) for k in kinds]
    mx = max(n for _, n in counts) or 1; W, bh = 640, 26
    bars = ''.join(f'<text x="0" y="{i*bh+17}" style="font-size:12px;fill:var(--fg)">{E(k["name"])}</text>'
                   f'<rect x="280" y="{i*bh+5}" width="{int(320*n/mx)}" height="16" rx="3" style="fill:{KIND_INK[k["id"]]}"/>'
                   f'<text x="{288+int(320*n/mx)}" y="{i*bh+18}" style="font-size:12px;font-weight:700;fill:var(--fg)">{n}</text>' for i, (k, n) in enumerate(counts))
    chart_kinds = (f'<figure class="graph"><svg viewBox="0 0 {W} {len(counts)*bh+8}" width="100%" role="img" aria-label="Statements on this page by kind">{bars}</svg>'
                   f'<figcaption>{len(rows)} statements on this page, by what kind of evidence they are. A count of statements, not of events: one party can report millions of attempts in one statement.</figcaption></figure>')
    # 2. the timeline, one lane per kind
    import datetime as _dt
    def t(w):
        w = w if 'T' in w else w + 'T12:00Z'
        return _dt.datetime.strptime(w.replace('Z', ''), '%Y-%m-%dT%H:%M')
    t0, t1 = _dt.datetime(2026, 10, 17), _dt.datetime(2026, 10, 23)
    X0, X1, lane = 200, 630, 28
    def x(w): return X0 + (X1 - X0) * (t(w) - t0).total_seconds() / (t1 - t0).total_seconds()
    ticks = ''.join(f'<line x1="{x(f"2026-10-{d}T00:00Z"):.0f}" x2="{x(f"2026-10-{d}T00:00Z"):.0f}" y1="10" y2="{len(kinds)*lane}" style="stroke:var(--line);stroke-width:1"/>'
                    f'<text x="{x(f"2026-10-{d}T00:00Z")+3:.0f}" y="{len(kinds)*lane+18}" style="font-size:10px;fill:var(--dim)">{d} Oct</text>' for d in range(17, 23))
    asof = f'<line x1="{x(C["as_of"]):.0f}" x2="{x(C["as_of"]):.0f}" y1="10" y2="{len(kinds)*lane}" style="stroke:var(--fg);stroke-dasharray:3 3"/><text x="{x(C["as_of"])-4:.0f}" y="8" text-anchor="end" style="font-size:10px;font-weight:700;fill:var(--fg)">as of 22 Oct 20:50</text>'
    lanes = ''.join(f'<text x="0" y="{i*lane+22}" style="font-size:11px;fill:var(--fg)">{E(k["name"])}</text>' for i, k in enumerate(kinds))
    li = {k['id']: i for i, k in enumerate(kinds)}
    dots = ''.join(f'<circle cx="{x(r["when"]):.1f}" cy="{li[r["kind"]]*lane+18}" r="5" style="fill:{KIND_INK[r["kind"]]};fill-opacity:.8"><title>{E(r["when"])} · {E(r["who"])}</title></circle>' for r in rows)
    chart_time = (f'<figure class="graph"><svg viewBox="0 0 640 {len(kinds)*lane+26}" width="100%" role="img" aria-label="The statements over time, one lane per kind">{ticks}{lanes}{dots}{asof}</svg>'
                  f'<figcaption>Each dot is one statement on this page, placed at the time the source gives (noon where it gives only a date). Hover a dot for who said it.</figcaption></figure>')
    # 3. the layers, as an infographic (not to scale)
    L = C['layers']; lh = 52
    shapes = ''.join(f'<rect x="{10+i*25}" y="{i*lh}" width="{620-i*50}" height="{lh-8}" rx="4" style="fill:var(--panel);stroke:{["var(--warm)","var(--bad-ink)","var(--accent)","var(--fg)"][i]};stroke-width:2"/>'
                     f'<text x="320" y="{i*lh+19}" text-anchor="middle" style="font-size:13px;font-weight:700;fill:var(--fg)">{E(l["value"])} · {E(l["label"])}</text>'
                     f'<text x="320" y="{i*lh+35}" text-anchor="middle" style="font-size:10.5px;fill:var(--dim)">{E(l["note"])}</text>' for i, l in enumerate(L))
    chart_layers = (f'<figure class="graph"><svg viewBox="0 0 640 {len(L)*lh}" width="100%" role="img" aria-label="From attempts to a named compromise: what each layer of evidence holds">{shapes}</svg>'
                    f'<figcaption>Not to scale. Each layer is a different kind of statement, and a statement in one layer does not move a case into the next: an attempt is not a compromise, and a vendor\'s report without a victim is not a victim\'s statement. The bottom layer is the statement this page is about.</figcaption></figure>')
    searched = '<div class="stats">' + ''.join(stat(f'{s["count"]:,}', f'{E(s["what"])}: {E(s["unit"])}<br><small>{E(s["detail"])}</small>') for s in C['searched']) + '</div>'
    kind_tables = ''
    for k in kinds:
        rs = [r for r in rows if r['kind'] == k['id']]
        if not rs: continue
        head = ['When', 'Who', 'What they said'] + (['Reading'] if k['id'] == 'named-organisation' else []) + ['Where it is held']
        body_rows = [[E(fmt_at(r['when'])), f'<b>{E(r["who"])}</b>', E(r['says'])] + ([E(r.get('reading', ''))] if k['id'] == 'named-organisation' else []) + [where(r)] for r in sorted(rs, key=lambda r: r['when'])]
        kind_tables += section('k-' + k['id'], f'{E(k["name"])} <small>({len(rs)})</small>', table(head, body_rows),
                               f'This kind of statement can show {E(k["can"])}. It cannot show {E(k["cannot"])}.')
    body = f"""
<h1>{E(C["statement"])}</h1>
<p class="lead">This page holds the evidence behind one statement, as of <b>{E(fmt_at(C["as_of"]))}</b>: every statement found about attacks on, or compromises of, real systems through php2shell, sorted by what kind of evidence it is, with the words of the party that made it and where its capture is held. It makes no assessment of risk. The statement's status is <b>{E(C["status"])}</b>: {E(C["status_note"])} It is <a href="../claims/index.html#{E(C["claim"])}">claim {E(C["claim"])}</a>.</p>
{section("searched", "What was searched", searched, "Where the statement was checked. A statement that something does not exist is only as good as the search behind it.")}
{section("layers", "From attempts to a named compromise", chart_layers)}
{section("kinds", "The evidence, by kind", chart_kinds + chart_time)}
{kind_tables}
{section("change", "What would change the statement", "<ul>" + "".join(f"<li>{E(w)}</li>" for w in C["would_change_it"]) + "</ul><p>The source watch checks the official lists and the named organisations' pages every 30 minutes; this page is rebuilt from data/compromise.json when the evidence changes.</p>")}
{section("ledger", "The disagreements, recorded", "<p>Where sources disagree, the disagreement is a record of its own in the source watch's contradiction ledger, with both statements and their captures: " + ", ".join(f"<code>contradictions/{E(c)}.json</code>" for c in C["contradictions"]) + ".</p>")}
{section("how", "How this page is made", '<p>Every row is in <a href="../data/compromise.json">data/compromise.json</a>. Rows with sources cite captures in the evidence vault, which the build checks. Rows marked <i>source watch</i> cite a dated snapshot folder in the source-watch vault (<a href="../vaults/source-watch/index.html">7r83qic5</a>); they move into the evidence vault as the evidence curator promotes them. Statements read in another language carry the reader&rsquo;s English translation beside the verbatim original in the watch&rsquo;s <code>translations/</code> files. The charts are drawn from the same rows when the site is built.</p>')}
"""
    page('compromise/index.html', 'No named organisation has said it was compromised through php2shell: the evidence', f'The evidence behind one statement, as of {fmt_at(C["as_of"])}: attempts, vendor reports, statements that no success is known, named organisations, allegations and official lists, each with its source.', body, kind='story', topics='php2shell exploitation compromise evidence')

def build_pack_mode():
    """sgit's pack mode, measured on the source watch: one vault as a normal vault and as a pack vault, from
    data/pack-mode.json. Every number is a timed command or a log line from the researcher's session."""
    P = D['pack-mode']; V = P['vault']
    NORMAL, PACK = 'var(--warm)', 'var(--accent-dk)'
    def secs(s):
        return '' if s is None else (f'{s:.2f} s' if s < 1 else f'{s:.0f} s' if s < 120 else f'{s // 60:.0f} min {s % 60:.0f} s')
    # 1. like for like, one small chart per operation, each on its own scale (labelled), normal above pack
    W, X0, X1 = 640, 150, 560
    panels = ''
    for i, c in enumerate(P['compare']):
        mx = max(c['normal_s'], c['pack_s']); y = i * 92
        bars = ''
        for j, (name, s, ink, note) in enumerate([(f'normal ({P["normal"]["id"]})', c['normal_s'], NORMAL, c['normal_note']), (f'pack ({P["pack"]["id"]})', c['pack_s'], PACK, c['pack_note'])]):
            w = max(3, (X1 - X0) * s / mx); yy = y + 26 + j * 28
            bars += (f'<text x="{X0 - 8}" y="{yy + 14}" text-anchor="end" style="font-size:12px;fill:var(--fg)">{E(name)}</text>'
                     f'<rect x="{X0}" y="{yy}" width="{w:.1f}" height="20" rx="4" style="fill:{ink}"><title>{E(note)}</title></rect>'
                     f'<text x="{X0 + w + 6:.1f}" y="{yy + 14}" style="font-size:12px;font-weight:700;fill:var(--fg)">{E(c["normal_failed"] if j == 0 and c.get("normal_failed") else secs(s))}</text>')
        ratio = c['normal_s'] / c['pack_s']
        verdict = 'the normal vault timed out' if c.get('normal_failed') else f'pack is {ratio:.0f}&#215; faster'
        panels += (f'<text x="0" y="{y + 15}" style="font-size:13px;font-weight:700;fill:var(--fg)">{E(c["op"])}</text>'
                   f'<text x="{W}" y="{y + 15}" text-anchor="end" style="font-size:12px;fill:var(--dim)">{verdict}</text>{bars}')
    chart_compare = (f'<figure class="graph"><svg viewBox="0 0 {W} {len(P["compare"]) * 92}" width="100%" role="img" aria-label="Normal vault against pack vault, three operations">{panels}</svg>'
                     f'<figcaption>The same vault, the same server, the same sandbox. Each operation has its own scale: read the labels, not the bar lengths across panels. Hover a bar for what exactly was run.</figcaption></figure>')
    # 2. one pass's push to the normal vault, attempt by attempt
    def mins(hm):
        h, m = hm.split(':'); return int(h) * 60 + int(m)
    A = P['attempts']; t0, t1 = mins('16:30'), mins('19:20'); AX0, AX1, lane = 120, 630, 19
    def ax(hm): return AX0 + (AX1 - AX0) * (mins(hm) - t0) / (t1 - t0)
    ticks = ''.join(f'<line x1="{ax(h):.1f}" x2="{ax(h):.1f}" y1="0" y2="{len(A) * lane}" style="stroke:var(--line);stroke-width:1"/>'
                    f'<text x="{ax(h):.1f}" y="{len(A) * lane + 14}" text-anchor="middle" style="font-size:10px;fill:var(--dim)">{h}</text>' for h in ('16:30', '17:00', '17:30', '18:00', '18:30', '19:00'))
    rows_svg = ''
    for i, a in enumerate(A):
        ok = a['outcome'] == 'pushed'; x0 = ax(a['start']); w = max(3, ax(a['end']) - x0)
        rows_svg += (f'<text x="0" y="{i * lane + 13}" style="font-size:11px;fill:var(--fg)">{i + 1}. {E(a["start"])}{" pushed" if ok else ""}</text>'
                     f'<rect x="{x0:.1f}" y="{i * lane + 3}" width="{w:.1f}" height="13" rx="3" style="fill:{"var(--ok-ink)" if ok else "var(--bad-ink)"};fill-opacity:{1 if ok else .7}"><title>{E(a["start"])} to {E(a["end"])} UTC: {E(a["why"])}</title></rect>')
    chart_attempts = (f'<figure class="graph"><svg viewBox="0 0 640 {len(A) * lane + 20}" width="100%" role="img" aria-label="{E(P["attempts_title"])}">{ticks}{rows_svg}</svg>'
                      f'<figcaption>{E(P["attempts_title"])}: {len(A) - 1} failed attempts, then one that took 4 minutes 29 seconds. Hover a bar for the error. {E(P["attempts_note"])}</figcaption></figure>')
    # 3. what each commit adds: the push a normal vault has to make, object by object
    Cm = P['commits']; mx = max(c['blobs'] for c in Cm); bw = 600 / len(Cm)
    cols = ''.join(f'<rect x="{20 + i * bw + 3:.1f}" y="{200 - 180 * c["blobs"] / mx:.1f}" width="{bw - 6:.1f}" height="{max(1, 180 * c["blobs"] / mx):.1f}" rx="3" style="fill:{PACK if c["what"] == "pass" else "var(--dim)"}"><title>{E(c["when"])}, {E(c["what"])}: {c["blobs"]:,} file objects</title></rect>'
                   + (f'<text x="{20 + i * bw + bw / 2:.1f}" y="{194 - 180 * c["blobs"] / mx:.1f}" text-anchor="middle" style="font-size:10px;font-weight:700;fill:var(--fg)">{c["blobs"]:,}</text>' if c['blobs'] > 2000 else '') for i, c in enumerate(Cm))
    chart_commits = (f'<figure class="graph"><svg viewBox="0 0 640 222" width="100%" role="img" aria-label="File objects added by each commit to the source watch">'
                     f'<line x1="20" x2="620" y1="200" y2="200" style="stroke:var(--line2)"/>{cols}'
                     f'<text x="20" y="216" style="font-size:10px;fill:var(--dim)">22 Oct 14:20</text><text x="620" y="216" text-anchor="end" style="font-size:10px;fill:var(--dim)">23 Oct 16:31</text></svg>'
                     f'<figcaption>File objects added by each of the watch&rsquo;s {len(Cm)} commits, in order; the full passes are in colour, labelled. Each one a normal vault uploads as its own request; a pack vault uploads the commit as one zip. Hover a column for the commit.</figcaption></figure>')
    stats_html = '<div class="stats">' + ''.join(stat(v, l) for v, l in [
        (f'{P["compare"][0]["normal_s"] / P["compare"][0]["pack_s"]:.1f}×', 'faster fresh clone<br><small>827 s against 95 s</small>'),
        ('96 s', f'to push the whole history<br><small>{V["objects"]:,} objects, {V["snapshot_mb"]:,} MB, one go</small>'),
        ('4', 'requests for a fresh clone<br><small>one snapshot, whatever the history</small>'),
        (f'{V["ratio"]}×', f'smaller on the server<br><small>{V["mb_normal"]:,} MB to {V["mb_pack"]:,} MB</small>')]) + '</div>'
    compare_tbl = table(['Operation', f'Normal vault ({E(P["normal"]["client"])})', f'Pack vault ({E(P["pack"]["client"])})'],
                        [[E(c['op']), f'<b>{E(c.get("normal_failed") or secs(c["normal_s"]))}</b><br><small>{E(c["normal_note"])}</small>', f'<b>{E(secs(c["pack_s"]))}</b><br><small>{E(c["pack_note"])}</small>'] for c in P['compare']])
    pack_tbl = table(['On the pack vault', 'Time', 'What'], [[E(p['op']), E(secs(p['s'])) or '&mdash;', E(p['note'])] for p in P['pack_only']])
    attempts_tbl = table(['#', 'Start (UTC)', 'End', 'Outcome', 'What happened'], [[str(i + 1), E(a['start']), E(a['end']), f'<b>{E(a["outcome"])}</b>', E(a['why'])] for i, a in enumerate(P['attempts'])])
    commits_tbl = table(['When', 'Commit', 'File objects'], [[E(c['when']), E(c['what']), f'{c["blobs"]:,}'] for c in P['commits']])
    p22 = table(['Push, 22 October', 'File objects', 'Outcome'], [[E(p['what']), f'{p["objects"]:,}', E(p['outcome'])] for p in P['pushes_22oct']])
    body = f"""
<h1>Pack mode, measured on the source watch</h1>
<p class="lead">The source watch is the newsroom&rsquo;s biggest vault: {V["commits"]} commits, {V["files"]:,} files, {V["objects"]:,} objects, {V["mb_normal"]:,} MB, growing by about 5,000 objects a pass. On 23 October it was copied, with <code>sgit pack import</code>, into a pack vault (<code>{E(P["pack"]["id"])}</code>), pushed, cloned fresh and checked file for file. The same operations were then run against both. The pack vault cloned in 95 seconds where the normal vault took 13 minutes 47 seconds, and pushed its whole history in 96 seconds, while one pass&rsquo;s push to the normal vault took 2 hours 42 minutes and 12 attempts. How to move a vault is in <a href="../briefs/index.html#2026-10-23__brief__moving-a-vault-to-pack-mode">the brief</a>.</p>
{stats_html}
{section("compare", "The same operations, side by side", chart_compare + compare_tbl)}
{section("wall", "Why the normal vault got slower: the server can no longer list it", f"<p>A normal vault stores every object as its own file on the server, and several operations start by asking the server for the list of them. For the watch, that list now holds over 60,000 entries, and the server&rsquo;s gateway gives up first: listing <code>bare/data/</code> for <code>{E(P['normal']['id'])}</code> returned <b>504 Gateway Timeout after 90.8 seconds</b>, while the same call for the pack vault answered in 0.73 seconds. A clone then falls back to walking the history and fetching objects as it finds them, which is why it took 827 seconds. A push that cannot list the vault fails outright: five of the attempts below. It will only get worse as the watch grows.</p>")}
{section("push", "One pass, pushed to the normal vault", chart_attempts + attempts_tbl + "<p>The day before, on 22 October, pushes of 1,000 to 6,000 objects failed the same ways: connections reset or closed by the remote end, a 401 in the middle of a retry, and refusals to retry while files were uncommitted.</p>" + p22)}
{section("growth", "Every pass is a bigger push", chart_commits + commits_tbl)}
{section("pack", "What the pack vault did, and how it was checked", pack_tbl + "<ul>" + "".join(f"<li>{E(c)}</li>" for c in P["check"]) + "</ul>")}
{section("limits", "What pack mode does not fix", "<ul>" + "".join(f"<li>{E(n)}</li>" for n in P["not_fixed"]) + "</ul>")}
{section("how", "How this page is made", f'<p>Every number is in <a href="../../data/pack-mode.json">data/pack-mode.json</a>, from a timed command or a log line in researcher@php.newsroom&rsquo;s session on {E(P["measured"])}, from a cloud sandbox to dev.send.sgraph.ai. One run of each, not a median: network times from a sandbox vary between runs, and the CLI team&rsquo;s own medians are on <a href="https://cli.sgit.ai/docs/update-to-0-24-0.html">cli.sgit.ai</a>. The charts are drawn from the same file when the site is built. The live watch stays <code>{E(P["normal"]["id"])}</code> until the editor decides; the pack vault is registered on <a href="../../team/vaults/index.html">the vaults page</a>.</p>')}
"""
    page('admin/pack-mode/index.html', 'Pack mode, measured on the source watch', 'One vault as a normal sgit vault and as a pack vault: a fresh clone in 95 s against 13 min 47 s, the whole history pushed in 96 s, and why the normal vault has hit a wall.', body, kind='site')

def build_discovery():
    cols = [
        ('Calif', ['2026-07-30 audit begins under Patch the Planet', '2026-08-01 multiple paths to RCE found', '2026-08-05 hash commitment posted on X', '2026-08-11 first bug reported to PHP', '2026-08-14 RCE PoC shared; confirmed 08-15', '2026-08-21 second bug reported'], ['calif-php2shell', 'x-lcfr-hax-hash-tweet']),
        ('OpenAI', ['2026-08-11 same root cause reported, same day as Calif (per the Foundation)', '2026-09-18 further attack vectors', 'coalition of maintainers, researchers and providers over two months', 'credit: amyb-oai on both advisories'], ['php-foundation-blog-security-release', 'x-openai-php2shell', 'github-ghsa-w8hw-w9fx-j79w']),
        ('Wiz', ['2026-08-19 first vulnerability found (Wiz Atlas, Gemini 4 Argon, GPT-5.6 Sol)', '2026-08-20 RCE confirmed on Drupal', '2026-08-21 RCE confirmed on WordPress', '2026-08-24 reported to PHP', '2026-09-21 PHP acknowledges', 'credit: sagitzadik-wiz'], ['wiz-blog-php2shell']),
        ('Before them', ['2024 Quarkslab audit (OSTIF, Sovereign Tech Agency) surfaces the OOM issue', '2024 a Foundation-contracted developer finds first signs; exploit theorised, no vector', 'credit: tomash-areion on both advisories, named nowhere else'], ['php-foundation-blog-security-release', 'calif-php2shell', 'github-ghsa-6wmf-4rv5-p3rp']),
    ]
    grid = ''.join(f'<div class="col"><h3>{E(name)}</h3><ul>{"".join(f"<li>{E(i)}</li>" for i in items)}</ul><p class="refs">{src_links(srcs, 1)}</p></div>' for name, items, srcs in cols)
    cl = [c for c in D['claims'] if c['topic'] == 'discovery']
    body = f'''
<h1>Who found it, and how</h1>
<p class="lead">Three research parties say they found php2shell, and all three say AI helped. Their own timelines, placed side by side, do not conflict on dates: Calif first (1 to 11 August), OpenAI the same day as Calif's report, Wiz independently eight days later. They conflict on framing: Wiz's <q>Wiz Research uncovers</q>, OpenAI's <q>frontier AI was able to find this vulnerability ahead of attackers</q>, and a Community Note on OpenAI's post pointing at Calif's August hash.</p>
<div class="cols">{grid}</div>
{section("ai", "What the AI did", '''
<p>The honest answer from the captured sources is: not enough is said. Calif says <q>No special harness, or access to models that weren't generally available to everyone were used in the initial bug discovery</q> and that the researcher <q>asked my LLM companion for help</q>; it names no model. Wiz names three tools and quotes Google DeepMind's head of Gemini security: <q>a single researcher completed in a week what previously would have taken a world-class team months of work.</q> OpenAI's blog, which reportedly names GPT-5.6 Sol, is behind a bot challenge from this capture environment. The PHP Foundation adds that the project was separately scanned with Anthropic's Claude Mythos through Alpha-Omega and that OpenAI's Daybreak Red validated reports and exploits.</p>
<p>What is established is the shape: a bug class seen in 2024 and left because nobody could prove exploitation, then three groups with model assistance finding working exploits within three weeks of each other in August 2026. The BBC's quote, <q>a complex chain of steps, at the edge of what human researchers could practically achieve</q>, is not on any captured researcher page.</p>
<p class="refs">''' + src_links(['calif-php2shell', 'wiz-blog-php2shell', 'openai-blog-coordinated-disclosure', 'php-foundation-blog-security-release', 'bbc-live-ckgel5xp2xv9t'], 1) + '</p>')}
{section("claims", "The claims on discovery", claim_rows(cl, 1))}
'''
    page('discovery/index.html', 'Who found php2shell, and what the AI did', 'Calif, OpenAI and Wiz each claim the discovery of php2shell; their own timelines side by side, the 2024 audit that saw it first, the credits on the advisories, and what the sources do and do not say about the models.', body, kind='story', topics='php2shell discovery ai')

def build_leak():
    evs = sorted([t for t in D['timeline'] if t.get('phase') in ('leak', 'release') or t['at'].startswith('2026-10-20')], key=lambda t: t['at'])
    rows = [[f'<span class="when">{E(fmt_at(t["at"]))}</span>', E(t['event']) + (f'<div class="note">{E(t["note"])}</div>' if t.get('note') else ''), pill(t['confidence']), src_links(t['sources'], 1)] for t in evs]
    cl = [c for c in D['claims'] if c['topic'] in ('leak', 'timing')]
    body = f'''
<h1>How the disclosure broke</h1>
<p class="lead">The plan was 22 October at 14:00 UTC. From about 15:00 UTC on 20 October the CVE IDs were loose with a wrong score; by 19:30 the project had pre-announced a release a day early; by 20:00 one of the reporters had published a demonstration video; by 23:00 mitigation advice was going to critical-infrastructure providers; by 02:00 on the 21st Amazon was seeing proof-of-concept attempts; by 03:02 Cloudflare's rules were live; by 07:41 Chainguard had shipped patched images; by 08:36 a sensor network had its first hit. The release went out at 13:34 UTC. Every one of those times is from a party's own account, and the parties disagree on what was leaked and by whom.</p>
{table(['When (UTC)', 'What', 'Time is', 'Sources'], rows, 'tl')}
{section("accounts", "Three accounts of what leaked", '''
<ul>
<li><b>The PHP Foundation:</b> the CVE IDs, a wrong release time and a wrong CVSS; <q>No technical details leaked.</q> Then Calif's video, then possibly the mitigation advice, then Chainguard's images.</li>
<li><b>Alexandre Daubois (PHP security team, writing personally):</b> an anonymous Hacker News post citing a reliable source, screenshots of it, a screenshot of the <q>PHP2Shell tool</q> credited to Calif.io <q>alongside the advisory</q>, a short exploitation video, and watchTowr confirming both CVE numbers in public.</li>
<li><b>The Hacker News:</b> <q>details about the CVE identifiers and a proof-of-concept (PoC) exploit leaked ahead of time</q>, and Amazon's evidence that somebody was trying an exploit four days before any of this.</li>
</ul>
<p>Calif's own write-up has a timeline that ends <q>October 21 Patched versions released</q> and does not mention a leak, a deleted video, or the Foundation's account. Chainguard's reply is behind a bot challenge; the search snippet says it does not dispute the time and denies leaking. The vault records both blocks.</p>
<p class="refs">''' + src_links(['php-foundation-blog-security-release', 'daubois-blog-php2shell-rumors', 'thehackernews-php2shell-4days', 'calif-php2shell', 'techzine-php-chainguard'], 1) + '</p>')}
{section("claims", "The claims on the leak and on timing", claim_rows(cl, 1))}
'''
    page('leak/index.html', 'How the coordinated disclosure broke', 'Hour by hour from the first circulation of the CVE IDs on 20 October to the release on 21 October: the pre-announcement, the deleted video, the early WAF rules, the embargo break, the first attempts, and the three accounts that disagree on what leaked.', body, kind='story', topics='php2shell leak disclosure')

def build_playbook():
    steps = [
        ('0', 'Know what you run', 'Inventory every system with PHP serving web requests, including the ones you did not build: appliances, vendor products, hosting panels, the thing marketing bought. Do not limit discovery to old versions. Note the SAPI (mod_php, FPM, cgi, FrankenPHP, LiteSpeed) and the PHP branch.', ['ncsc-news-php', 'cisa-alert-php-20261021', 'nsa-press-php-4630238', 'ncsc-nl-php2shell-software-list']),
        ('1', 'Patch, internet-facing first', 'Update to 8.5.12, 8.4.27, 8.3.36 or 8.2.35, or your distribution\'s backported package. Restart every worker; rebuild containers. For 7.4, 8.0 and 8.1 there is a source backport branch and no release: plan the migration now. Some third-party repositories (remirepo) had no packages on release day.', ['php-net-advisory', 'ch-bacs-warnung-php', 'github-php-src-branch-7.4-backport', 'certeu-sa-2026-018']),
        ('2', 'If you cannot patch today, apply the temporary mitigations', 'memory_limit=-1 where applications cannot override it; low post_max_size with proxy-level request limits; a cgroup memory limit instead of RLIMIT; session.upload_progress.enabled=0 then restart every worker; on 8.5 fatal_error_backtraces=0; pm.max_requests=1 on FPM. Each blocks a known path and none makes the installation safe.', ['php-net-advisory', 'github-ghsa-6wmf-4rv5-p3rp', 'ncsc-nl-php2shell']),
        ('3', 'Put something in front', 'A WAF may provide some protection (CISA); it is not sufficient on its own (Swiss BACS); it blocked what Cloudflare saw while attackers mutated payloads. CERT-FR\'s edge workaround is to block or monitor multipart Content-Type requests. Restrict access to the people and systems that need it.', ['cisa-alert-php-20261021', 'ch-bacs-warnung-php', 'cloudflare-blog-php2shell-waf', 'certfr-2026-ale-014']),
        ('4', 'Isolate or take offline', 'Where none of the above is feasible in time: CERT-EU, Canada and France say isolate internet-facing applications from public networks; the NSA and CISA say take the system offline until fully mitigated; the UK NCSC puts this fourth; Latvia geo-blocked state services from abroad for days. Decide who can make that call and how fast it can be executed, and write it down before you need it.', ['certeu-sa-2026-018', 'cccs-al26-026', 'certfr-2026-ale-014', 'nsa-x-2112903220209098897', 'cisa-alert-php-20261021', 'ncsc-news-php', 'certlv-php-preventive']),
        ('5', 'Look for compromise', 'PHP workers launching shells or downloading tools; unexpected files under the web root; outbound connections from the web tier; anomalous multipart or oversized requests. A clean log does not prove a clean system (JPCERT); a system that could not be patched or disabled promptly should be assessed for backdoors (NCSC UK).', ['cisa-alert-php-20261021', 'jpcert-at260033', 'ncsc-news-php', 'ncsc-nz-alert-php']),
        ('6', 'Verify, then keep watching', 'Confirm the running version after the restart, not the package version before it. Check vendors that bundle PHP for their own fixes. Watch for a follow-up release: a report that the 8.5.12 fix may be incomplete reached oss-security within two hours and has not been answered on-list.', ['ch-bacs-warnung-php', 'ncsc-nl-php2shell', 'openwall-oss-security-109619-thread']),
    ]
    rows = ''.join(f'<li><span class="n">{E(n)}</span><div><h3>{E(t)}</h3><p>{E(w)}</p><p class="refs">{src_links(s, 1)}</p></div></li>' for n, t, w, s in steps)
    body = f'''
<h1>If you run PHP</h1>
<p class="lead">Every agency's advice, merged into one ordered list, with the sentence each step comes from. This is a guide to what the sources say, assembled by agents and not reviewed by your security team; the php.net advisory is the authority and your national agency is the one that applies to you. Taking a system offline is the last step on every list, and the one list where it comes earlier is the one that says <q>isolate, then migrate</q>.</p>
<p>To do step 0 and see what steps 1 to 4 mean for your own systems, describe them in <a href="../stack/index.html">your stack</a>: it checks each PHP runtime against both flaws and shows what an attacker who reaches one could touch.</p>
<ol class="steps">{rows}</ol>
{section("plug", "Pulling the plug, as a capability", '''<p>Four agencies told organisations to be ready to take systems offline within hours. How long it takes you to do that for one system, cleanly, with a holding page and a way back, is a measurable property of your stack, and it is the property this incident tested. A system that can be removed from the internet in minutes without data loss is one you can afford to leave running until the patch is tested; a system that cannot is one you take offline early, because you will not be able to later. The site's own position is that the decision belongs to a named person and the execution belongs to a rehearsed runbook, and that the inventory in step 0 is where both start.</p>''')}
<p>The technical detail behind each step is on <a href="../flaws/index.html">the two flaws</a>; which versions and products are in scope is on <a href="../affected/index.html">affected systems</a>; what the agencies said, agency by agency, is on <a href="../agencies/index.html">the agencies</a>.</p>
'''
    page('playbook/index.html', 'If you run PHP: the steps, in order, with their sources', 'Inventory, patch, mitigate, shield, isolate or take offline, look for compromise, verify: every agency\'s php2shell advice merged into one ordered list with the sentence each step comes from.', body, kind='story', topics='php2shell playbook mitigation')

def build_briefings():
    aud = D['roles']['audiences']
    sel = {
        'everyone': dict(topics=['impact', 'exploitation', 'scale'], intro='You do not need to know anything about computers to follow this. Below are the five things worth knowing, then the evidence behind them, folded away until you want it.', ask=['<b>PHP is not on your phone or laptop.</b> It runs on the servers that build websites. This is a problem for the organisations that run those websites, and it is theirs to fix.', '<b>Nothing to install, nothing to change</b> on your own devices because of this. Be wary of any message that says otherwise and asks you to click or download something: scammers use headlines like this one.', '<b>If a website you use was down on 21 or 22 October, it was most likely a precaution.</b> Dutch government services such as DigiD were taken offline on purpose, as a precaution; that is a decision, not a sign of a break-in.', '<b>Nobody has confirmed being hacked through this yet.</b> Attackers have been trying, in large numbers, and that may change; this site will say so when the evidence does.', '<b>The big numbers in the headlines are not what they sound like.</b> 70% is roughly the share of websites built with PHP, not a share of the Internet that is broken. <a href="../../numbers/index.html">The numbers page</a> explains each one.']),
        'site-owner': dict(topics=['technical', 'advice', 'exploitation'], intro='You do not need to understand the bug to deal with it. What you need is to know whose job the update is, and the exact question to ask. This page gives you both.', ask=['<b>Find out whether your site runs on PHP.</b> WordPress, WooCommerce, Drupal, Joomla, Magento, PrestaShop, Moodle and most hosting control panels do. If you are not sure, ask whoever built the site.', '<b>Updating WordPress, plugins or themes does not fix this.</b> The flaw is in PHP itself, one layer down. It has to be fixed on the server.', '<b>If someone hosts the site for you</b>, send them this, in writing: <i>Has PHP on the server running my site been updated to 8.5.12, 8.4.27, 8.3.36 or 8.2.35, or to your distribution\'s fixed package, and have the PHP processes been restarted since? If my site is on PHP 8.1 or older, what is your plan?</i> Keep the reply.', '<b>If you run the server yourself</b>, update PHP today and restart it. The <a href="../../playbook/index.html">step-by-step list</a> has the temporary settings for a server you cannot update straight away.', '<b>If your site is on PHP 8.1 or older</b>, there is no ready-made fix. Ask your developer or host about moving to a supported version now; it is overdue anyway.', '<b>Keep calm about being hacked.</b> No organisation has confirmed a break-in as of the latest capture. If your host updated promptly, you are in the same position as almost everyone else.']),
        'pm': dict(topics=['advice', 'impact', 'timing'], intro='This is a platform event, not an application bug, so it lands on every team that ships anything running on PHP at once. Plan for it the way you would plan for a datacentre move: an inventory, an owner per system, a date, a test.', ask=['<b>Get the list.</b> Which systems run PHP, who owns each, and which are on the internet. Vendor products and hosting panels count. Without the list nothing else can be scheduled.', '<b>Get a date per system.</b> Updating PHP means installing the fixed version, restarting, rebuilding containers and re-testing. Internet-facing systems first.', '<b>Budget for regression testing.</b> The fix changes how PHP behaves when it runs short of memory: a system that used to limp along may now stop cleanly. Load tests are worth running before the release, not after.', '<b>Plan for precautionary downtime.</b> Agencies advise isolating or taking offline what cannot be updated in time. Agree with stakeholders now who can make that call, how long it may last, and what users see meanwhile.', '<b>Treat PHP 8.1 and older as a project.</b> There is no ready-made release for them. Moving to a supported version is a migration with its own scope and schedule.', '<b>Expect a second round.</b> A report that the first fix may be incomplete is open. Keep a slot free in the next fortnight.']),
        'board': dict(topics=['scale', 'exploitation', 'advice', 'impact'], intro='Three decisions sit with you: whether the organisation is exposed, what it costs to find out, and who may pull a system. The facts below are the ones those decisions turn on. Everything marked <i>reported</i> is one party\'s word; nothing below is a confirmed compromise anywhere.', ask=['Do we have an inventory of every system serving PHP, including vendor products? If not, that is the first spend.', 'Has every internet-facing system been patched and restarted, and has the running version been checked after the restart?', 'Who is authorised to take a system offline, how long does it take, and has it been rehearsed?', 'What would a compromise of our most exposed PHP system reach: which data, which credentials, which other systems?', 'What is our evidence that we were not exploited between the leak on 20 October and our patch?']),
        'security': dict(topics=['technical', 'exploitation', 'advice', 'scale'], intro='Patch order, mitigations, signals and the offline decision. The claims are grouped so that the ones your runbook depends on come first.', ask=['Internet-facing mod_php first, then FPM, then everything else; 7.4 to 8.1 need a migration plan, not a package.', 'Apply the temporary mitigations where patching slips, and record that each one blocks a known path only.', 'Alert on PHP workers spawning shells or fetching tools; log multipart and oversized requests at the edge.', 'Decide the isolate-or-offline threshold now and name who calls it.', 'Re-check KEV and oss-security daily: the exploitation picture and the incomplete-fix question will both move.']),
        'engineer': dict(topics=['technical'], intro='Versions, SAPIs, settings and what each does. The claims are the primary records\' own words where they exist.', ask=['Target 8.5.12, 8.4.27, 8.3.36 or 8.2.35; restart every worker; rebuild images.', 'memory_limit=-1 via php_admin_value; post_max_size 8M or 32M; cgroup limits not RLIMIT; session.upload_progress.enabled=0 in php.ini or the pool, never ini_set; fatal_error_backtraces=0 on 8.5; pm.max_requests=1.', 'The CVE record calls 7.4 to 8.1 unaffected by omission; the backport branches say otherwise. Do not trust a scanner on this.', 'The 8.5.12 fix may have a follow-up; watch php.net and oss-security.', 'Verify the running version with phpinfo or php -v inside the container, after the restart.']),
        'journalist': dict(topics=['scale', 'discovery', 'leak', 'timing', 'advice'], intro='Which numbers hold up, who said what first, which quotes are on the page they are attributed to, and what nobody has verified. Every row links to the captured source so the quote can be checked against the bytes.', ask=['The 70% figure is a share of websites that use PHP, restated as a share of the Internet; no page on this beat sources it.', 'The release was 21 October 13:34 to 14:06 UTC, not 22 October; the php.net changelog still says 22.', 'The sentence the BBC attributes to the NCSC is not on the NCSC page as captured; the opening matches Canada\'s text.', 'Australia\'s agency gives no offline advice; the EU\'s says isolate.', 'Three parties claim discovery; their own dates do not conflict, their framing does. The Foundation says Calif and OpenAI reported the same root cause on the same day.']),
        'researcher': dict(topics=['technical', 'discovery', 'leak'], intro='Bug classes, what was demonstrated against what, credits, and the open technical questions.', ask=['Two classes: OOM longjmp leaving request memory uninitialised (CWE-416/755/824/1325/1419), and worker global state pointing at freed request memory across requests.', 'mod_php exploited pre-application with default limits; FPM via session upload progress for 109619; FPM for 109618 disputed between the GHSA and the Foundation blog.', 'Credits on both GHSAs: lcfr-hax, sagitzadik-wiz, amyb-oai, tomash-areion. The last is unexplained.', 'Open: the Fediverse report of a third bug or incomplete fix; Calif\'s hash pre-image; whether the embedded demo is the deleted video.', 'The fix changes the engine: soft OOM at a VM safe point, hard OOM via _exit(). Expect behavioural differences under memory pressure.']),
        'ciso': dict(topics=['exploitation', 'impact', 'advice', 'scale', 'technical'], intro='Exposure, evidence of non-compromise, and the board message. Three facts carry this briefing: the bug is in the runtime so your application code is not the question; attempts are in the millions at one CDN but no named victim is confirmed anywhere; and every agency says patch first, with offline as the fallback not the reflex.', ask=['Exposure is a list, not a percentage: every internet-facing system serving PHP, with SAPI, version and what sits behind it. Vendor appliances and hosting panels count.', 'Evidence of non-compromise means log review from 17 October (Amazon\'s earliest attempt), not from the 21st, and host checks for shells spawned by PHP workers, not just WAF hits.', 'The board line: a critical runtime flaw, patched on day one where we could, isolated where we could not, no evidence of compromise as of today, review continuing. Do not quote 70%.', 'Edge rules were live hours before disclosure; if you are behind a major CDN you had a stopgap you did not have to ask for. It is not a control you can rely on.', 'Expect a follow-up release: a report that the first fix is incomplete reached the security list within two hours.']),
        'cto': dict(topics=['technical', 'advice', 'timing'], intro='What the patch changes, what it breaks, and what to change afterwards. The fix is a redesign of how PHP handles running out of memory, so behaviour under memory pressure changes, and it touched 389 files.', ask=['Patch order: mod_php on the internet first; FPM next; everything else after. Restart every worker, rebuild every image, then verify the running version inside the container.', 'The new memory_hard_limit_percent and max_multipart_body_parts settings exist now; the defaults are conservative, and a system that used to survive on the edge of memory_limit may now _exit instead.', '7.4, 8.0 and 8.1 have a source backport and no release: that is a migration you are now doing, not a patch.', 'The engineering lesson is time-to-pull-the-plug: how long it takes to take one system off the internet cleanly, with a holding page and a way back, is a property of your platform and it was measured this week whether you wanted it or not.', 'What to change: an inventory that answers "where is PHP" in minutes; worker-process monitoring (a PHP worker spawning a shell is the signal); a rehearsed isolate runbook with a named owner.']),
        'cfo': dict(topics=['impact', 'scale', 'exploitation'], intro='The financial question has two sides and the evidence is lopsided: downtime is documented and measurable; breach is claimed and unconfirmed. Insurers are already treating this as an aggregation event.', ask=['Cost of acting: operators that pulled sites report hours to a day offline; one operator served 94% of its page views from cache through a 13-hour shutdown. Engineering time to patch, restart and verify is the main cost for most.', 'Cost of not acting: an unauthenticated code-execution flaw in the web tier; what it reaches is whatever that tier can reach, which is a question for the CISO\'s inventory, not for a percentage.', 'Insurance: Insurance Business reports underwriters watching for an aggregation event and asks whether business-interruption cover responds to a precautionary shutdown with no breach; that depends on wording and waiting periods. Ask the broker now, in writing.', 'Figures you will hear and should not use in a forecast: 70% of the Internet (a share of websites restated), 30 million websites (no basis), 22.6 million systems (method not given). Use your own inventory count.', 'No named organisation has confirmed a compromise as of the latest capture. That is a statement about evidence, not about safety.']),
        'appsec': dict(topics=['technical', 'advice', 'exploitation'], intro='Scope, settings and the pipeline change. The bug is below your applications: any PHP endpoint that reaches the runtime is a candidate, and the demonstrated paths run before application code.', ask=['In scope: every application on an affected runtime, including the ones with no uploads and no sessions; the session upload-progress path is on by default and needs no session_start().', 'Settings that bound the known paths, in the order of least breakage: session.upload_progress.enabled=0 (server-level, not ini_set); post_max_size low; max_input_nesting_level low; max_multipart_body_parts on patched builds; fatal_error_backtraces=0 on 8.5; pm.max_requests on FPM. None is a fix.', 'The runtime version in production is now an application-security finding: add it to the SBOM, fail the pipeline on an unfixed PHP, and check the running version after deploy, not the package version before.', 'Detection belongs at the edge and on the host, not in the app: the request shape (upload-progress field plus many array parts, oversized multipart bodies) and the process tree (a worker spawning a shell).', 'The public proof-of-concept code does not work as published, per VulnCheck and a lab reproduction; a scanner that fires on it is testing the wrong thing.']),
        'developer': dict(topics=['technical'], intro='Your code is not the problem and cannot be the fix. The flaw is in the C engine that runs it. What you can do is check the box you deploy to and avoid making the engine\'s job harder.', ask=['Check the running version where the code runs: php -v inside the container or phpinfo() on the box, after the restart. The package list is not the answer.', 'Fixed: 8.5.12, 8.4.27, 8.3.36, 8.2.35. If your target is 8.1 or older there is no release; tell whoever owns the platform today.', 'Nothing in userland blocks the demonstrated paths: ini_set() runs too late, .user.ini runs too late, auto_prepend_file runs too late. The settings have to be in php.ini, the pool or the server config.', 'Fix attacker-reachable fatal errors and timeouts in your own code anyway: the advisory lists them as one of the paths for the stale-state bug.', 'After the patch, out-of-memory behaves differently: a delayed fatal at the next safe point instead of an abort, and a hard limit that ends the process. Code that caught the old behaviour in tests will see a change.']),
        'comms': dict(topics=['scale', 'impact', 'discovery', 'advice'], intro='What is true, what is not, and what you will be asked. The story most readers saw on the morning of 22 October carried three things this site could not confirm, and the questions will come from that story.', ask=['True and safe to say: two critical flaws in PHP itself, patched on 21 October; the organisation patched or isolated its systems; no evidence of compromise as of today, review continuing.', 'Not safe to say: "70% of the Internet" (a headline restating a share of websites), "the most severe ever" (a vendor\'s phrase), "exploited everywhere" (attempts against honeypots and CDNs, no named victim), "found by AI" without "by researchers using".', 'The questions: Were you hit? (answer with the evidence window: logs reviewed from 17 October.) Did you take sites down? (precaution, not incident, as Oxford City Council put it.) Why did it take so long? (the fix was authored on 18 October and released under a coordinated plan that leaked.)', 'Attribution: three research teams and the PHP Foundation each tell the discovery story differently; do not pick one. The flaw was seen in 2024 and not fixed because exploitation could not be shown.', 'Point at primary sources: php.net\'s advisory and your national agency. Do not link a vendor blog as the authority.']),
        'dpo': dict(topics=['impact', 'exploitation', 'advice', 'technical'], intro='Four questions, in order: is personal data on a system that was exposed, has anything happened to it, does that make it a personal data breach, and what goes on the record. A vulnerability is not a breach, and an outage you chose is not one either; a sign that someone ran code on a system holding personal data is where the assessment starts. Written by the GRC desk; the full register is at <a href="../../grc/index.html">GRC</a>.', ask=['<b>Find the personal data first.</b> Ask the CTO or security lead for the list of internet-facing PHP systems (vendor products and hosting panels count), and mark which hold or reach personal data: accounts, orders, case files, the database the application logs into. Code execution on the server gives an attacker what the PHP process can read, usually including the database credentials in its configuration.', '<b>Exposed is not breached.</b> An unpatched system is a risk under Article 32 to treat and record, not a breach under Article 33. As of the last check, no named organisation has said it was compromised through php2shell; attempts are widely reported and two vendors report successful exploitation without naming a victim. <a href="../../compromise/index.html">What that statement rests on</a>.', '<b>When the 72-hour clock starts.</b> Under Article 33 it runs from when you become aware, with reasonable certainty, that personal data was affected: a web shell, a PHP worker spawning a shell, an unexplained database export on a system holding personal data. Ask the security lead to tell you the hour that happens, not the day after, and start the assessment then.', '<b>A precautionary shutdown is a decision, not a breach.</b> Taking a service offline on purpose to protect it is not an accidental or unlawful loss of availability. Record who decided, when, for how long, and that no personal data was lost.', '<b>Ask your processors in writing.</b> A host or managed platform is a processor under Article 28 and must tell you of a breach without undue delay (Article 33(2)). Ask each one: have you updated PHP on the systems that process our data, since when, have you seen any sign of compromise, and will you tell us within hours if you do? Keep the replies.', '<b>Document either way.</b> Article 33(5) asks you to record every breach; accountability under Article 5(2) asks you to show your reasoning when you decide something is not one. Record: the systems and the personal data on each, the date each was patched or isolated, the log review window (from 17 October, the earliest reported attempt, not from the 21st), what was found, and the decision with its reasons and who made it.', '<b>If it becomes a breach.</b> Notify the supervisory authority within 72 hours unless the breach is unlikely to result in a risk to people (Article 33), and tell the people affected without undue delay if the risk to them is high (Article 34). Coordinate with whoever owns the NIS2 or DORA report: the same incident can start a 24-hour clock there.']),
        'analyst': dict(topics=['discovery', 'leak', 'timing', 'scale', 'exploitation'], intro='What this incident says about coordinated disclosure once models can find bugs, and once a leak can become a proof of concept faster than a patch can ship. The claims below are the evidence; the reading is the site\'s.', ask=['The window between leak and release was 22.5 hours and the window between first honeypot hit and release was four days. Both are shorter than the two months the fix took.', 'Three AI-assisted teams converged on a bug class seen and shelved in 2024. The constraint that failed in 2024 was proving exploitability, and that is what models now appear to lower the cost of.', 'The defensive side moved early too: WAF rules 9 hours ahead, images 6 hours ahead (against the embargo), agencies within the hour. The system is faster in both directions.', 'The public numbers were not produced for decision-making and should not be used for it; the one agency that counted got about 6,000 in a country of 1.9 million people.', 'Agencies diverged on the hardest question, offline or not, along lines that look institutional rather than technical.']),
    }
    for a in aud:
        s = sel[a['id']]
        p = PERSONAS[a['id']]
        BRIEF_TOPICS[a['id']] = s['topics']
        cl = [c for c in D['claims'] if c['topic'] in s['topics']]
        order = {t: i for i, t in enumerate(s['topics'])}
        cl.sort(key=lambda c: (order[c['topic']], list(STATUS_WORDS).index(c['status']) if c['status'] in STATUS_WORDS else 9))
        asks = ''.join(f'<li>{x}</li>' for x in s['ask'])
        openq = ''.join(f'<li>{o["html"]}</li>' for o in STORY['open'][:5])
        needs = ''.join(f'<li>{E(x)}</li>' for x in p['needs'])
        skips = ''.join(f'<li>{E(x)}</li>' for x in p['skip'])
        facts = status_legend() + claim_rows(cl, 2)
        if p['depth'] == 1:
            facts = f'<details class="evidence"><summary>Show the {len(cl)} claims behind this briefing, each with its status and sources</summary>{facts}</details><p class="small">Every sentence above rests on these rows. They are folded away because they are written in the sources\' own vocabulary; the glossary explains each term.</p>'
        others = ' &middot; '.join(f'<a href="../{b["id"]}/index.html">{E(PERSONAS[b["id"]]["label"])}</a>' for b in aud if b['id'] != a['id'])
        body = f'''
<p class="kicker">Briefing for {E(p["person"])}, {E(p["label"].lower())} &middot; {depth_badge(p["depth"])} &middot; from the same {C["claims"]} claims, selected and ordered for one reader</p>
<h1>{E(a["question"])}</h1>
<div class="answer">{avatar(p)}<div><p class="kicker">The answer in thirty seconds</p><p>{E(p["answer"])}</p><p><a class="cta cta-pri" href="../../{E(p["path"][1])}" data-persona="{E(p["id"])}">Read the site as {E(p["person"])} &rarr;</a></p></div></div>
<p class="lead">{s["intro"]}</p>
{section("decide", "What to decide or do", f'<ul class="asks">{asks}</ul>')}
{section("path", "Your reading path", reading_path(p, 2) + '<div class="cols2"><div><h3>What this briefing covers</h3><ul>' + needs + '</ul></div><div><h3>What you can skip</h3><ul>' + skips + '</ul></div></div>')}
{section("words", "Words you will meet", words_met(p, 2) + '<p class="small">Each is underlined where it first appears; hover or tap for a one-line definition, or open <a href="../../glossary/index.html">the glossary</a>.</p>')}
{section("facts", "The facts this rests on", facts)}
{section("open", "What is still open", f'<ul class="open">{openq}</ul>')}
<p>The full set of claims is on <a href="../../claims/index.html">every claim</a>; the ordered steps for a vulnerable system are on <a href="../../playbook/index.html">if you run PHP</a>. Other readers: {others}.</p>
'''
        who = a['name'][0].lower() + a['name'][1:] if a['name'][1:2].islower() else a['name']  # keep CFO, PHP, AppSec as written
        who = ('an ' if who[0] in 'aeiou' else 'a ') + who
        page(f'briefings/{a["id"]}/index.html', f'Briefing for {who}: {a["question"]}', f'The php2shell story for {who}: a thirty-second answer, what to decide, a reading path, the claims it rests on with their status and sources, and what is still open.', body, kind='briefing', topics=f'php2shell briefing {a["id"]}')

def build_sources():
    kinds = Counter(s.get('kind') for s in D['sources'])
    rows = ''
    for s in D['sources']:
        caps = ''
        for c in s['captures']:
            files = ''.join(f'<li><code>{E(fn)}</code> <span class="h">{E(f["sha256"])}</span> <span class="small">{f["bytes"]:,} bytes</span></li>' for fn, f in sorted(c['files'].items()))
            err = f' <span class="small">error: {E(str(c["error"]))}</span>' if c.get('error') else ''
            caps += f'<details><summary>capture <code>{E(c["stamp"])}</code> &middot; HTTP {E(str(c.get("status")))} &middot; {E(str(c.get("final_url") or ""))}{err}</summary><ul class="files">{files}</ul></details>'
        raw = ''
        if s.get('raw_sha256'):
            raw = '<details><summary>raw, ' + str(len(s['raw_sha256'])) + ' files with SHA256SUMS</summary><ul class="files">' + ''.join(f'<li><code>{E(fn)}</code> <span class="h">{E(h)}</span></li>' for fn, h in s['raw_sha256'].items()) + '</ul></details>'
        rows += f'''<article class="source" id="{E(s["slug"])}">{it_source(s)}
<h3><a href="{E(s["slug"])}/index.html">{E(s.get("title") or s["slug"])}</a> <a class="small" href="{U(s["url"])}" rel="noopener nofollow">original &#8599;</a></h3>
<p class="meta"><b>{E(s.get("publisher") or "")}</b> &middot; {E(s.get("kind") or "")} &middot; {"primary" if s.get("primary") else "secondary"} &middot; {pill(s.get("status") or "")} &middot; published {E(str(s.get("published") or "not stated"))} &middot; added by <code>{E(s.get("added_by") or "")}</code> &middot; <code>{E(s["slug"])}</code></p>
<p class="small">{E(s.get("notes") or "")}</p>
{caps}{raw}
</article>'''
    kinds_t = table(['Kind', 'Sources'], [[E(k or 'other'), E(str(n))] for k, n in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0]))])
    body = f'''
<h1>Every source, every capture, every hash</h1>
<p class="lead">{C["sources"]} sources, {C["primary"]} of them primary, {C["captures"]} dated captures and {C["hashed"]} hashed files, from the evidence vault at commit <code>{E(D["vault"]["head"]["commit"] or "")}</code>. {C["blocked"]} sources could not be read because the site blocked an automated browser; the block, with the challenge page's hash, is the record. The captures are third-party pages held privately and are not republished; this page links to the originals and lists the SHA-256 of every captured file, so that anyone the vault is later opened to can check that the bytes are the ones the agents saw, at the minute they saw them.</p>
{kinds_t}
<p>Each capture holds <code>page.html</code> (as served), <code>rendered.html</code> (after scripts ran), <code>text.txt</code>, <code>screenshot.png</code>, <code>headers.json</code> and <code>provenance.json</code>. A <code>raw/</code> folder holds anything fetched another way, with its own checksum file. The manifest this page is built from is <a href="../data/sources.json">data/sources.json</a>.</p>
<div class="sources">{rows}</div>
'''
    page('sources/index.html', f'Every source: {C["sources"]} pages, {C["captures"]} captures, {C["hashed"]} hashes', f'The manifest of the php2shell evidence vault: every captured source with its publisher, kind, publication time, capture times, HTTP status and the SHA-256 of every captured file.', body, kind='evidence', topics='php2shell sources evidence')

# build_graph() is in the ontologist's block at the end of this file.

def build_method():
    v = D['vault']
    body = f'''
<h1>The method: capture, hash, claim, build, gate</h1>
<p class="lead">This site is the newsroom's <a href="{NEWSROOM}">PHP flaws section</a> taken to its conclusion: a site whose every sentence can be traced to bytes, rebuilt by a script from the vault, with no step a reader has to take on trust. It is also a test of the stack sgit.ai is building, and says so in its footer.</p>
{section("vault", "The evidence vault", f'''<p>A private, encrypted sgit vault, opened at {E(v["opened"])}, written to by {len(v["agents"])} agents and the editor. It holds {v["sources"]} sources and {v["captures"]} captures at commit <code>{E(v["head"]["commit"] or "")}</code>. Its protocol, in its own README: capture, don't paraphrase; captures are additive, never edited or deleted; one <code>source.json</code> and one <code>notes.md</code> per source, so agents never conflict on a shared manifest; claims and timeline rows in one file per agent; primary sources first, then news, then social posts, which get captured early because they get deleted; a blocked fetch is recorded with the block, so another agent can retry; and no keys or tokens in any file. The vault is private because it holds verbatim third-party pages for the record; this site publishes their hashes, their URLs and short quotations, and never the pages.</p>''')}
{section("status", "Five words for how far a claim can be trusted", status_legend() + '<p>A claim never gets a better word than its sources give it. A verbatim quote is marked as such and attributed to the page it is on; a quote attributed by one outlet to another party stays <i>reported</i> until the other party\'s page is captured and found to carry it. The one case so far where that check failed, the BBC\'s NCSC sentence, is on <a href="../agencies/index.html">the agencies page</a>.</p>')}
{section("determinism", "Deterministic, and why that matters", '''<p>The build reads <code>data/</code> and <code>VERSION</code> and writes every page. It has no clock, no random number and no network: run it twice and the output is byte-identical, which the gate checks. That means a page can be reproduced from the data at any version, a diff between two versions is a diff in the data, and a reader who doubts a page can rebuild it. Times on pages are the sources' times; the only date the site adds is the time of the latest capture, which is itself read from the vault.</p>
<ol>
<li><code>admin/build/export_vault.py --from &lt;vault clone&gt;</code> reads the vault and writes the manifest with every hash, the merged per-agent claims and timeline, the vault's HEAD and the software inventory counts. Never the captures.</li>
<li><code>admin/build/build.py</code> builds every page, its markdown twin, <code>data/graph.json</code> and <code>llms.txt</code>.</li>
<li><code>admin/build/validate.py</code> is the gate: every internal link resolves; every page is linked from somewhere and has a markdown twin and an llms.txt line; every claim and event cites a slug in the manifest; the build is byte-identical when run again; no em-dash in the site's prose; no credential shape anywhere in the tree.</li>
<li><code>admin/build/release.sh</code> bumps the version, builds, validates, runs the leak tripwire over the staged diff, pushes, and polls the live site for the new version before it will say the release is done.</li>
</ol>''')}
{section("agents", "For an agent", f'''<p>Everything on this site is in <code>data/</code> as JSON and every page has a markdown twin at the same path; <a href="../llms.txt">llms.txt</a> lists them. To add a source: capture it into the vault with the vault's tool, write its <code>source.json</code> and <code>notes.md</code>, add rows to your own <code>claims/&lt;agent&gt;.json</code> and <code>timeline/&lt;agent&gt;.json</code>, commit with your agent's name, push. To change this site: edit <code>data/</code>, run the build, run the gate. Do not edit a generated page; the build will overwrite it. The vault's claims and timeline files are exported as <a href="../data/vault-claims.json">vault-claims.json</a> and <a href="../data/vault-timeline.json">vault-timeline.json</a>; this site's own rows are in <a href="../data/claims.json">claims.json</a> and <a href="../data/timeline.json">timeline.json</a>, written by the agent <code>claude-story-site</code> from every note in the vault.</p>''')}
{section("replicate", "Replicate it for the next incident", '''<p>Nothing here is specific to PHP. The vault protocol, the capture tool, the five status words, the export, the build and the gate would carry a story about any incident, outage or disclosure. The repository is public under Apache-2.0 and CC BY 4.0; the next story starts by copying it, emptying <code>data/</code>, and opening a vault.</p>''')}
'''
    page('method/index.html', 'The method: capture, hash, claim, build, gate', 'How this site keeps evidence: the private vault and its protocol, the five status words, the deterministic build, the gate, and how an agent adds a source or replicates the whole thing for the next incident.', body, kind='site', topics='method provenance')

TEAM = load('team')
GROUP_AV = {'humans': 'decide', 'coordination': 'communicate', 'site': 'act', 'evidence': 'understand', 'writing': 'study', 'testing': 'study'}
KIND_LABEL = {'human': 'human', 'agent': 'agent', 'role': 'role, no agent of its own yet'}

def member_tasks(mid):
    owners = TEAM['board_owners']
    return [b for b in D['admin']['board'] if owners.get(b['owner']) == mid]

def member_initials(m):
    w = re.findall(r'[A-Za-z]+', m['alias'].lstrip('@'))
    caps = re.findall(r'[A-Z]', m['alias'])
    return (''.join(caps[:2]) if len(caps) >= 2 else (w[0][:2] if w else '?')).upper()

def member_card(m, depth):
    t = member_tasks(m['id']); st = Counter(b['status'] for b in t)
    counts = f'{st.get("open", 0)} open' + (f', {st["waiting"]} waiting' if st.get('waiting') else '') + f', {st.get("done", 0)} done'
    return (f'<a class="door door-{GROUP_AV[m["group"]]}" id="{E(m["id"])}" href="{"../" * depth}team/{E(m["id"])}/index.html">'
            f'<span class="dh"><span class="av av-{GROUP_AV[m["group"]]}">{E(member_initials(m))}</span><span><b>{E(m["name"])}</b>'
            f'<small>{E(m["alias"])} &middot; {E(m["role"])}</small></span></span>'
            f'<span class="dq">{E(m["summary"])}</span>'
            f'<span class="dm"><span>{E(KIND_LABEL[m["kind"]] if m["status"] == "active" else m["status"])}</span><span>{counts}</span></span></a>')

def task_table(rows, depth):
    if not rows: return '<p class="small">None.</p>'
    return table(['#', 'Task', 'Status', 'Shipped in'], [[E(b['id']), E(b['title']) + (f'<div class="note">{E(b["note"])}</div>' if b.get('note') else ''), pill(b['status']), E(b.get('version') or '')] for b in rows], 'board')

def build_team():
    r = D['roles']; T = TEAM; M = T['members']
    by_id = {m['id']: m for m in M}
    allt = [b for m in M for b in member_tasks(m['id'])]
    st = Counter(b['status'] for b in allt)
    stats = ''.join(stat(n, l) for n, l in [(len(M), 'members'), (sum(m['kind'] == 'human' for m in M), 'humans'), (sum(m['kind'] == 'agent' for m in M), 'agents'),
                                            (sum(m['kind'] == 'role' for m in M), 'roles not yet filled'), (st.get('open', 0), 'open tasks'), (st.get('waiting', 0), 'waiting'), (st.get('done', 0), 'done')])
    groups = ''.join(f'<section id="g-{E(g["id"])}"><h3>{E(g["name"])}</h3><p class="small">{E(g["about"])}</p><div class="doors">{"".join(member_card(m, 1) for m in M if m["group"] == g["id"])}</div></section>' for g in T['groups'])
    run = ''.join(f'<li><b>{E(p["name"])}</b> ({E(p["who"])}). {E(p["what"])}</li>' for p in T['cycle']['phases'])
    pipe = table(['Step', 'What', 'Who', 'How'], [[E(str(p['step'])), f'<b>{E(p["name"])}</b>', E(p['who']), E(p['what'])] for p in r['pipeline']])
    auds = ''.join(f'<li><a href="../briefings/{E(a["id"])}/index.html"><b>{E(a["name"])}</b></a>: {E(a["question"])}</li>' for a in r['audiences'])
    humans = ' and '.join(f'<a href="{E(m["id"])}/index.html">{E(m["name"])}</a> ({E(m["role"].lower())})' for m in M if m['kind'] == 'human')
    body = f'''
<h1>The team: two people and the agents that work with them</h1>
<p class="lead">This site is built and run by {humans}, and a team of software agents, with help from <a href="../collaborators/index.html">collaborators</a> who use it as it grows. Every member, human or agent, has a page: what they own, the rules they work by, the pages that are their home on this site, what they have shipped and the tasks they hold now. A new agent should be able to read this page and its own and begin. The roster is <a href="../data/team.json">data/team.json</a>, kept by <a href="conductor/index.html">the conductor</a>.</p>
<div class="stats">{stats}</div>
{section("members", "Who is on it", groups)}
{section("run", "How the team runs", f'<p class="caveat">{E(T.get("now", ""))}</p><p>{E(T["cycle"]["about"])}</p><ol>{run}</ol><p>What runs on a schedule, its tasks and every run with its log, live: <a href="schedule/index.html">schedule</a>. Where every agent is right now, what each waits for and from whom: <a href="status/index.html">status</a>, or drawn as a <a href="control/index.html">control room</a>. Every vault the agents made, by ID: <a href="vaults/index.html">vaults</a>. What the agents run on their own, when, and every run they made: <a href="runs/index.html">runs</a>.</p><p>The team talks through three vaults: the conductor vault, which says where the team is; the issues vault, one task queue per member; and the mail vault, where members write to each other. <a href="channels/index.html">How the team talks</a> says what each holds and the rules.</p>')}
{section("pipeline", "The pipeline", pipe, "How a URL becomes a published claim, and who does each step.")}
{section("audiences", "The audiences", f'<ul>{auds}</ul>', "Each briefing is a role too: a reader whose question the site answers in one page.")}
{section("rules", "The rules every member shares", '''<ul>
<li><b>Capture, don't paraphrase.</b> A page you summarised but did not capture does not exist.</li>
<li><b>One file per agent per concern.</b> So a merge never asks a human to choose between two agents' edits.</li>
<li><b>Write only in your own folder.</b> Your queue, your mailbox, your claims file. To ask another member for work, send it mail; the owner opens the task.</li>
<li><b>Count, don't remember.</b> Every number on a page is computed from the thing it counts.</li>
<li><b>Five words, defined once.</b> Confirmed, reported, disputed, contradicted, unverified.</li>
<li><b>State the gap.</b> A blocked fetch, a missing primary source, an unverified quote and a blocked task are all published, not hidden.</li>
<li><b>Read keys yes, vault keys never.</b> And this vault's read key is not published either, because it holds third-party pages.</li>
<li><b>Verify live.</b> A release is done when the live site serves the version, not when the push succeeds.</li>
</ul>''')}
'''
    page('team/index.html', 'The team: the people, the agents and how they work together', f'Every member of the team that runs this site, {sum(m["kind"] == "human" for m in M)} people and {len(M) - sum(m["kind"] == "human" for m in M)} agents and roles, with a page each: role, what they own, their tasks and what they shipped; how a run works, the pipeline and the {len(r["audiences"])} audiences.', body, kind='site', topics='team agents')

    legacy = {a['id']: a for a in r['agents']}
    legacy.update({'story-site': legacy.get('claude-story-site', {}), 'newsroom-lead': legacy.get('claude-newsroom-lead', {})})
    for m in M:
        t = member_tasks(m['id'])
        opn = [b for b in t if b['status'] == 'open']; wait = [b for b in t if b['status'] == 'waiting']; done = [b for b in t if b['status'] == 'done']
        lg = legacy.get(m['id']) or {}
        home = ''.join(f'<a class="door door-{GROUP_AV[m["group"]]}" href="../../{E(h)}"><b>{E(n)}</b><span>{E(h)}</span></a>' for h, n in m['home'])
        addr = m.get('address') or (m['mail'] + '@php.newsroom')
        facts = [('Kind', E(KIND_LABEL[m['kind']])), ('Status', E(m['status'])), ('Alias', f'<code>{E(m["alias"])}</code>'), ('Known as', f'<code>{E(addr)}</code>')]
        if m.get('joined'): facts.append(('Joined', E(m['joined'])))
        kv = ' &middot; '.join(f'<b>{k}</b> {v}' for k, v in facts)
        mistake = f'<p><b>The mistake behind the rules.</b> {E(lg["mistake"])}</p>' if lg.get('mistake') else ''
        beat = f'<p><b>Beat.</b> {E(lg["beat"])}</p>' if lg.get('beat') else ''
        achieved = ''.join(f'<li>{E(x)}</li>' for x in m['achieved'])
        waiting_on = ''
        if m['kind'] == 'human' and opn:
            waiting_on = section('waiting', 'Waiting on ' + E(m['name'].split()[0]), f'<div data-live="member-tasks" data-member="{E(m["id"])}" data-status="open">' + task_table(opn, 2) + '</div>', 'Decisions and work only a person can supply. Each is a card in this member\'s queue in the issues vault, and the conductor names it in every digest until it is answered.')
        tasks = '' if (m['kind'] == 'human' and opn) else section('tasks', 'Open tasks', f'<div data-live="member-tasks" data-member="{E(m["id"])}" data-status="open">' + task_table(opn, 2) + '</div>')
        body = f'''
<p class="crumb"><a href="../index.html">The team</a> / {E(m["name"])}</p>
<h1>{E(m["name"])}: {E(m["role"].lower() if m["kind"] != "human" else m["role"])}</h1>
<p class="lead">{E(m["summary"])}</p>
<p class="kv">{kv}</p>
{beat}
{section("owns", "What they own", "<ul>" + "".join(f"<li>{E(x)}</li>" for x in m["owns"]) + "</ul>")}
{section("rules", "The rules they work by", "<ul>" + "".join(f"<li>{E(x)}</li>" for x in m["rules"]) + "</ul>" + mistake)}
{section("home", "Their home on this site", f'<div class="doors">{home}</div>')}
{waiting_on}
{tasks}
{section("blocked", "Waiting on someone else", f'<div data-live="member-tasks" data-member="{E(m["id"])}" data-status="waiting">' + task_table(wait, 2) + '</div>') if wait else ''}
{section("achieved", "What they have done", (f'<ul>{achieved}</ul>' if achieved else '<p class="small">Nothing yet.</p>') + (f'<h3>Closed on the board</h3><div data-live="member-tasks" data-member="{E(m["id"])}" data-status="done">{task_table(done, 2)}</div>' if done else ''))}
<script src="../../assets/live/live.js" defer></script>
<script src="../../assets/live/tasks.js" defer></script>
{section("reach", "How to reach them", f'<ul><li><b>Mail</b>: an <code>.eml</code> in <code>mail/mailroom/{E(m["mail"])}/</code> in the mail vault (<code>fmb2tpl2</code>).</li><li><b>Their queue</b>: <code>issues/{E(m["id"])}/open|blocked|done/</code> in the issues vault (<code>zjruy9vk</code>). Read it; do not write in it.</li><li><b>Their page in the conductor vault</b>: <code>team/members/{E(m["id"])}.md</code>.</li></ul><p class="small">What the three vaults are and who holds their keys: <a href="../channels/index.html">how the team talks</a>.</p>')}
'''
        page(f'team/{m["id"]}/index.html', f'{m["name"]}, {m["role"].lower() if m["kind"] != "human" else m["role"]}: the team', f'{m["name"]} ({m["alias"]}) on the team behind this site: {m["summary"]}', body, kind='site', topics='team agents')

    chans = ''.join(f'''<section class="vcard" id="{E(c["id"])}"><h2>{E(c["name"])} <span class="st">private</span></h2>
<p class="kv"><b>Vault</b> <code>{E(c["vault"])}</code> &middot; <b>written by</b> {E(c["writes"])} &middot; <b>read by</b> {E(c["reads"])}</p>
<p>{E(c["holds"])}</p><p class="small"><b>How.</b> {E(c["how"])}</p></section>''' for c in T['channels'])
    cond = by_id['conductor']
    body = f'''
<p class="crumb"><a href="../index.html">The team</a> / How the team talks</p>
<h1>How the team talks: three vaults and one run</h1>
<p class="lead">The members of this team, two people and the agents, do not share a chat. They coordinate through three encrypted vaults, using two protocols from the sgit.ai estate: Email-FS-lite for messages and Issues-FS-lite for tasks. Every message and every change of a task is a file, and every cycle is one commit, so the history of the vaults is the record of who asked for what, who took it and when it was done.</p>
{chans}
{section("run", "The run", f'<p>{E(T["cycle"]["about"])}</p><ol>{run}</ol>')}
{section("protocols", "The two protocols", '''<ul>
<li><b>Email-FS-lite.</b> To send, a member writes an <code>.eml</code> file into the recipient's <code>mailroom/</code> and a copy into its own <code>outbox/</code>; the recipient moves it into its <code>inbox/</code>, and into <code>done/</code> when the work is finished. Messages are never edited or deleted, only moved. <a href="https://sgraph.ai/en-gb/library/how-it-works/email-fs-lite">The reference</a>.</li>
<li><b>Issues-FS-lite.</b> Each member's tasks are markdown files in its own <code>open/</code>, <code>blocked/</code> and <code>done/</code> folders; opening, blocking, unblocking and closing a task are four moves. Anyone may read any queue; only its owner writes in it. <a href="https://issues-fs.sgit.ai/lite/index.html">The reference</a>.</li>
<li><b>The conductor's lane.</b> A write-only channel on the conductor vault: a member encrypts a message to the conductor's public key (<code>sha256:742d442b1c5b07bd</code>) and appends it with its own token, which can write and cannot read. The conductor drains it at every run with <code>admin/build/conductor_drain.py</code>.</li>
</ul>''')}
{section("keys", "Keys", '<p>None of the three vaults is published. The conductor holds their keys; every member gets the conductor vault\'s read key and the keys to the issues and mail vaults privately, and its own lane token, in the way the editor decides (<a href="../../admin/board/index.html">board</a> 070). No key or token is on this site or in its repository.</p>')}
{section("board", "The board", f'<p>The site\'s <a href="../../admin/board/index.html">board</a> moved into the issues vault on 22 October 2026: each row became a card in its owner\'s queue. The vault is now the truth; <code>admin/build/issues_sync.py import</code> writes the board on this site from it before a release, so the board here is a snapshot as of the release that built it.</p>')}
<p>The channels are kept by <a href="../{E(cond["id"])}/index.html">{E(cond["name"])}</a>.</p>
'''
    page('team/channels/index.html', 'How the team talks: three vaults and one run', 'The three private vaults the team coordinates through (the conductor vault, Issues-FS-lite tasks and Email-FS-lite mail), the run that opens and closes every scheduled cycle, and the rules.', body, kind='site', topics='team agents')

def build_billing():
    b = D['billing']
    P = b['pricing']; pr = b['runs']['prices']
    tier_h = [f'{E(t["tier"].capitalize())}<br><span class="small">{"up to " + str(t["max_days"]) + " day" + ("s" if t["max_days"] > 1 else "") if t["max_days"] else "older"}, &times;{t["multiplier"]:g}</span>' for t in P['tiers']]
    kinds = table(['Type', 'Layer', 'Base'] + tier_h + ['Pages', 'Why'], [[f'<b>{E(t["type"])}</b>', E(t['layer']), f'{t["base"]}p'] + [f'{pr[t["type"] + "_" + tr["tier"]]}p' if t['decays'] else (f'{pr[t["type"]]}p' if i == 0 else '&middot;') for i, tr in enumerate(P['tiers'])] + [E(t['pages']), E(t['why'])] for t in P['types']])
    kinds = f'<h3>The formula</h3><p class="kv"><code>{E(P["formula"])}</code>, with a floor of {P["floor"]}p.</p>' + kinds + f'<p class="small">A dot means the price does not decay: the type costs the same at any age. {E(P["age_from"])}</p><h3>The rules of engagement</h3><ol>' + ''.join(f'<li>{E(r)}</li>' for r in P['rules']) + '</ol>' + ''.join(f'<p class="small"><b>{E(t["tier"].capitalize())}.</b> {E(t["why"])}</p>' for t in P['tiers'])
    designed = ''.join(f'<li><b>{E(d["what"])}.</b> {E(d["text"])}</li>' for d in b['designed'])
    cm = b['cost_model']
    unit_counts = {'data/vault.json: sources': C['sources'], 'data/vault.json: captures': C['captures'],
                   'data/sources.json: has_notes': sum(1 for s in D['sources'] if s.get('has_notes')),
                   'data/claims.json': C['claims'], 'data/timeline.json': C['events'], "the build's page list": None}
    rows, total = [], 0
    for u in cm['units']:
        n = unit_counts.get(u['count_from'])
        if n is None:
            n = sum(len(items) for _, items in NAV) + 2  # every page in the nav, plus top-up and topped-up
        cost = n * u['assumed_price_pence']
        total += cost
        rows.append([E(u['unit']), E(str(n)), f'{u["assumed_price_pence"]}p', f'{cost / 100:.2f}', E(u['why'])])
    cost_t = table(['Unit', 'Count', 'Assumed price', '£', 'Why that unit'], rows)
    runs = b['runs']
    body = f'''
<h1>The billing model</h1>
<p class="lead">Two layers, and the page is careful to say which is which. <b>What runs</b> is a reading meter: a few pence a page from credit kept in your browser, charged by how far down the page you read, never blocking, with the option to decline and say why. <b>What is designed</b> is paying for provenance rather than pages: a price per verified claim, a share for whoever created the fact, and a snapshot of the vault for a reader who wants the bytes. The first is the same component the newsroom runs; the second is argued here and built nowhere.</p>
{section("runs", "What runs: the reading meter", f'''<p>Every page carries <code>&lt;sg-meter&gt;</code>, SG Meter v1.3.1, vendored under <code>assets/components/</code> and loaded from this site only. You start with {runs["symbol"]}{runs["start"] / 100:.2f} of credit in this browser; the balance is in the top bar and goes below zero without anything being blocked. A page costs its price times the share of it you scrolled through, rounded to 5% and never less than a tenth, once per page per session. At the foot of each page you can rate how useful it was, which sets the price from free to double, or decline to pay with a reason. Nothing leaves the browser: no account, no cookie, no server of ours, no analytics listening to the meter's events. <a href="../account/index.html">Your reading account</a> shows the history and exports it as JSON.</p>''' + kinds + f'''<p>Top-ups are {runs["symbol"]}{runs["topup"]["amount"] / 100:.2f} of credit on a payment page. No payment link is configured for this site yet, so <a href="../account/top-up.html">the top-up page</a> runs the meter's simulated cart and says so. When a link is added, the credit is added on the return page without verifying the payment, because a static site has nowhere to receive a webhook; the meter's security model is explicit that this is an honesty box, not a paywall.</p>''')}
{section("designed", "What is designed: paying for provenance", f'<ul class="designed">{designed}</ul><p>None of this is live. The newsroom\'s pages on <a href="https://newsroom.sgit.ai/economics/index.html">paying the fact creator</a> and <a href="https://newsroom.sgit.ai/provenance/index.html">provenance as the product</a> carry the argument; this site is the first with a claim table granular enough to price.</p>')}
{section("cost", "What this story cost to assemble, as a model", f'<p>{E(cm["note"])}</p>' + cost_t + f'<p>Total at those assumptions: <b>£{total / 100:.2f}</b>. The counts are from the data files named; the prices are the site\'s assumptions and a reader is invited to substitute their own. What the model leaves out is the editor\'s time and the model inference behind each agent run, neither of which is counted anywhere yet; the honest column on this is <i>not measured</i>.</p>')}
{section("prices", "The prices, as data", f'<pre>{E(json.dumps({"storageKey": runs["storageKey"], "start": runs["start"], "symbol": runs["symbol"], "prices": runs["prices"], "topup": runs["topup"]}, indent=1, sort_keys=True))}</pre><p>This block is <code>data/billing.json</code>, which is also what every page\'s meter config is generated from, so the table above and the meter cannot disagree.</p>')}
'''
    page('billing/index.html', 'The billing model: what runs and what is designed', 'How this site is paid for: the reading meter that runs (pence per page, kept in your browser, never blocking), the provenance pricing that is designed (per claim, with a share for the fact creator), and a counted model of what the story cost to assemble.', body, kind='site', topics='billing meter economics')

def build_account():
    body = '''
<h1>Your reading account</h1>
<p class="lead">Everything the meter knows is in this browser: the balance, every page opened with the share read and what it cost, what you declined and why, and your top-ups. Export it as JSON; nothing is sent anywhere unless you choose to. A new browser or cleared site data starts again with the starting credit.</p>
<sg-meter view="account"></sg-meter>
<p>How the meter works, and why it works this way, is on <a href="../billing/index.html">the billing model</a>. The account needs JavaScript: the balance lives here, not on a server.</p>
'''
    page('account/index.html', 'Your reading account', 'The balance, history and receipts of your reading on this site, kept in your browser.', body, kind='account')
    body = '''
<h1>Top up</h1>
<p class="lead">Reading credit, paid on a payment page. No payment link is configured for this site yet, so what follows is the meter's simulated cart, which says it is simulated. When a link is added, this page will say so and the credit will be added on the return page without verifying the payment.</p>
<sg-meter view="topup"></sg-meter>
<p>Where your data is kept, and what can leave your browser, is on <a href="../billing/index.html">the billing model</a>. A payment returns to <a href="topped-up.html">the topped-up page</a>.</p>
'''
    page('account/top-up.html', 'Top up', 'Add reading credit to the balance kept in your browser.', body, kind='account')
    body = '''
<h1>Thank you</h1>
<p class="lead">If you arrived here from a payment page, the credit has been added to the balance in this browser. If you opened this page on its own, nothing is added and the meter says so.</p>
<sg-meter view="topped-up"></sg-meter>
<p><a href="index.html">Your reading account</a> &middot; <a href="../index.html">The front page</a></p>
'''
    page('account/topped-up.html', 'Topped up', 'The page a payment returns to.', body, kind='account')

def render_md_file(path):
    """A small markdown renderer for the brief and corrections files: headings, paragraphs, lists, code."""
    full = os.path.realpath(os.path.join(ROOT, path))
    allowed = [os.path.realpath(os.path.join(ROOT, n)) for n in ('BRIEF-CORRECTIONS.md', 'REALITY.md', 'README.md', 'AGENTS.md')]
    if not (full.startswith(os.path.realpath(os.path.join(ROOT, 'admin', 'content')) + os.sep) or full in allowed):
        raise SystemExit(f'build: render_md_file reads only admin/content/ and the top-level notes, not {path!r}')
    with open(full, encoding='utf-8') as f:
        text = f.read()
    out, in_list, in_code, rows = [], False, False, []
    def flush():
        if rows:
            out.append(table([inline_md(c) for c in rows[0]], [[inline_md(c) for c in r] for r in rows[1:]])); rows.clear()
    for line in text.splitlines():
        if not in_code and line.strip().startswith('|'):
            if in_list: out.append('</ul>'); in_list = False
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not all(re.match(r'^:?-+:?$', c) for c in cells):
                rows.append(cells)
            continue
        flush()
        if line.strip().startswith('```'):
            if in_code:
                out.append('</pre>'); in_code = False
            else:
                out.append('<pre>'); in_code = True
            continue
        if in_code:
            out.append(E(line)); continue
        m = re.match(r'^(#{1,4})\s+(.*)$', line)
        if m:
            if in_list: out.append('</ul>'); in_list = False
            lvl = min(len(m.group(1)) + 1, 4)
            out.append(f'<h{lvl}>{E(m.group(2))}</h{lvl}>'); continue
        if re.match(r'^\s*[-*]\s+', line):
            if not in_list: out.append('<ul>'); in_list = True
            out.append('<li>' + inline_md(re.sub(r'^\s*[-*]\s+', '', line)) + '</li>'); continue
        if in_list: out.append('</ul>'); in_list = False
        m = re.match(r'^!\[([^\]]+)\]\((assets/briefs/[a-z0-9-]+\.png)\)$', line.strip())
        if m:
            # a picture in a brief: only a PNG committed under assets/briefs/, sized from its own header
            src = os.path.join(ROOT, m.group(2))
            if not os.path.isfile(src):
                raise SystemExit(f'build: {path} shows {m.group(2)}, which is not in the repository')
            with open(src, 'rb') as f:
                head = f.read(24)
            w, h = int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')
            out.append(f'<figure class="shot"><img src="../../{E(m.group(2))}" alt="{E(m.group(1))}" width="{w}" height="{h}" loading="lazy"></figure>'); continue
        if line.startswith('>'):
            q = inline_md(re.sub(r'^>\s?', '', line))
            if out and out[-1].endswith('</p></blockquote>'):
                out[-1] = out[-1][:-len('</p></blockquote>')] + ' ' + q + '</p></blockquote>'
            else:
                out.append('<blockquote><p>' + q + '</p></blockquote>')
            continue
        if line.strip():
            out.append('<p>' + inline_md(line) + '</p>')
    flush()
    if in_list: out.append('</ul>')
    if in_code: out.append('</pre>')
    return '\n'.join(out)

INLINE_MD = [('code', re.compile(r'`([^`]+)`')), ('b', re.compile(r'\*\*([^*]+)\*\*')), ('i', re.compile(r'(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])')),
             ('a', re.compile(r'\[([^\]]+)\]\((https?://[^)\s"<>]+)\)'))]

def inline_md(s):
    """`code`, **bold**, *italic* and [text](http(s) link): the pattern that matches earliest wins; bold, italics and a
    link's text are read again inside, code is kept as written (`sources/*/x/*` keeps its stars; **bold `code`** works).
    The same rules as assets/live/live.js inline(), so a page drawn live and a page built read the same."""
    out = []
    while s:
        best = None
        for k, rx in INLINE_MD:
            m = rx.search(s)
            if m and (best is None or m.start() < best[1].start()):
                best = (k, m)
        if not best:
            out.append(E(s)); break
        k, m = best
        out.append(E(s[:m.start()]))
        if k == 'code':
            out.append(f'<code>{E(m.group(1))}</code>')
        elif k == 'a':
            out.append(f'<a href="{E(m.group(2))}" rel="noopener">{inline_md(m.group(1))}</a>')
        else:
            out.append(f'<{k}>{inline_md(m.group(1))}</{k}>')
        s = s[m.end():]
    return ''.join(out)

def build_brief():
    memos = []
    mdir = os.path.join(ROOT, 'admin', 'content', 'briefs', 'memos')
    for fn in sorted(os.listdir(mdir)):
        with open(os.path.join(mdir, fn), encoding='utf-8') as f:
            t = f.read()
        paras = ''.join(f'<p>{E(p.strip())}</p>' for p in re.split(r'\n\s*\n', t) if p.strip())
        memos.append(f'<details open><summary><code>{E(fn)}</code></summary><div class="memo">{paras}</div></details>')
    body = f'''
<h1>The brief, in full</h1>
<p class="lead">The document this site started from, published as written and never edited to look right afterwards. It is a written request and two voice memos from the editor, transcribed by a transcription service and reproduced verbatim, hesitations included. Where the brief turned out to be wrong, the finding goes in <a href="../corrections/index.html">corrections</a>, not here.</p>
{section("request", "The written request, 22 October 2026", render_md_file("admin/content/briefs/2026-10-22__brief.md"))}
{section("memos", "The two voice memos", "".join(memos))}
{section("status", "Status", '<p>Accepted by the editor on 22 October 2026 by sending it; the first release of the site is the reply. What was built against each point of the brief is in the <a href="../admin/index.html">reality file</a>.</p>')}
'''
    page('brief/index.html', 'The brief: a written request and two voice memos', 'The brief this site was built from, published in full: the editor\'s written request and two transcribed voice memos on mapping the PHP vulnerability as evidence.', body, kind='site')


# =========================================================================== briefs, one page each (story-site)
# The editor, 25 October 2026, in story-site's session: the briefs page is a wall of text; he wants the titles, newest
# first, and each brief on its own page he can link to. admin/briefs/** is the editor's own page in his policy, so
# this is an override of story-site's scope, counted in its status and named in its debrief.
# Every link already published to admin/briefs/index.html#<file stem> still lands on that brief's row in the index.

BRIEF_PAGES = []  # filled by build_briefs, listed in llms.txt by briefs_llms_lines
BRIEFS_LEDGER = os.path.join(DATA, 'briefs-published.json')


def briefs_published(stems):
    """When each brief was first published (UTC, to the minute), from data/briefs-published.json. A brief not in it
    yet is stamped now, by this build, and the stamp is kept; nothing already there is ever changed."""
    import time as _t
    led = json.load(open(BRIEFS_LEDGER, encoding='utf-8')) if os.path.exists(BRIEFS_LEDGER) else {'published': {}}
    pub = led.setdefault('published', {})
    missing = [x for x in stems if x not in pub]
    if missing:
        now = _t.strftime('%Y-%m-%dT%H:%MZ', _t.gmtime())
        for x in missing:
            pub[x] = now
        led['published'] = dict(sorted(pub.items()))
        with open(BRIEFS_LEDGER, 'w', encoding='utf-8') as f:
            f.write(json.dumps(led, indent=1, ensure_ascii=False) + '\n')
    OUTPUTS.add('data/briefs-published.json')
    return pub


def brief_meta(fn):
    """Title, date, who wrote it and a first line, read from the file itself."""
    with open(os.path.join(ROOT, 'admin', 'content', 'briefs', fn), encoding='utf-8') as f:
        lines = [x.rstrip('\n') for x in f]
    title = next((x[2:].strip() for x in lines if x.startswith('# ')), fn[:-3])
    body = [x.strip() for x in lines if x.strip() and not x.startswith('#')]
    status = next((x for x in body if x.lower().startswith('status:')), '')
    first = next((x for x in body if not x.lower().startswith('status:')
                  and not x.startswith(('>', '|', '```', '- ', '* ', '<', '1.'))), '')   # a sentence, not a table or a list
    who = ''
    m = re.search(r'Author:\s*([^.;]+)', status)
    if m:
        who = m.group(1).strip()
    elif status:
        who = status[7:].split('.')[0].strip()
    lead = re.sub(r'[*`\[\]]', '', first)
    if len(lead) > 120:                                     # the first sentence is the summary, not the first 190 characters
        cut = lead.find('. ')
        if 40 < cut < 190:
            lead = lead[:cut + 1]
    return {'slug': fn[:-3], 'file': fn, 'date': fn[:10], 'title': title, 'who': who, 'lead': lead}


def deepen_links(html):
    """A brief rendered on its own page sits one directory deeper than the index it used to live on."""
    return re.sub(r'(src|href)="\.\./', r'\1="../../', html)


def build_briefs():
    """The index: every brief as a row with its title; and one page per brief."""
    bdir = os.path.join(ROOT, 'admin', 'content', 'briefs')
    names = sorted([x for x in os.listdir(bdir) if x.endswith('.md')], reverse=True)
    pub = briefs_published([fn[:-3] for fn in names])
    metas = [brief_meta(fn) for fn in names]
    for m in metas:
        m['published'] = pub[m['slug']]
    metas.sort(key=lambda m: (m['published'], m['slug']), reverse=True)

    rows, by_month = '', OrderedDict()
    for m in metas:
        by_month.setdefault(m['published'][:7], []).append(m)
    MONTHS = {'10': 'October', '11': 'November', '12': 'December'}
    for month, group in by_month.items():
        label = f"{MONTHS.get(month[5:7], month[5:7])} {month[:4]}"
        rows += f'<h2 class="brief-month">{E(label)}<span>{len(group)} brief{"s" if len(group) != 1 else ""}</span></h2><ol class="brief-list">'
        for m in group:
            rows += (f'<li id="{E(m["slug"])}"><a class="brief-row" href="{U(m["slug"])}/index.html">'
                     f'<span class="d"><time datetime="{E(m["published"])}">{E(m["published"][8:10])} {E(MONTHS.get(m["published"][5:7], m["published"][5:7])[:3])}<b>{E(m["published"][11:16])}</b></time></span>'
                     f'<span class="t"><b>{E(m["title"])}</b>'
                     + (f'<span class="w">{E(m["who"][:110])}</span>' if m['who'] else '')
                     + (f'<span class="l">{E(m["lead"][:190])}</span>' if m['lead'] else '')
                     + '</span><span class="go" aria-hidden="true">&rarr;</span></a></li>')
        rows += '</ol>'

    body = f"""
<h1>Briefs</h1>
<p class="lead">A brief is written before the work and published as written: what was asked, in whose words, what exists to build on, the design, what it cannot do, the deliverables and the open questions. The newsroom and the sgit.ai sites keep theirs the same way. The file is the record; every brief below is one file in <code>admin/content/briefs/</code> and has its own page and link. The written request and the two voice memos that started the site are on <a href="../../brief/index.html">the brief</a>.</p>
<p class="small"><span data-live-brief-count>{len(metas)}</span> briefs, the most recently published first, with the time each was published (UTC). Each opens on its own page; the markdown twin of every page is one click from it. The times are kept in <a href="../../data/briefs-published.json">data/briefs-published.json</a>.</p>
<div data-live="briefs-index">{rows}</div>
<script src="../../assets/live/live.js" defer></script>
<script src="../../assets/live/briefs.js" defer></script>
"""
    page('admin/briefs/index.html', 'Briefs', f'Every build brief for this site, {len(metas)} of them, published in full before the work: the title, the date and who wrote it, each on its own page.', body, kind='site')

    BRIEF_PAGES.extend(metas)
    # a brief written since this build: drawn from its own file in the team repository until the next round gives it a page
    page('admin/briefs/view/index.html', 'A brief', 'A brief published since the last build, drawn from its file in the team repository.', """
<div data-live="brief-view"><h1>A brief</h1><p>This page draws a brief published since the site was last built, from its own file in the team repository. It needs scripts; every brief is also a file in <a href="https://github.com/SGit-AI/SGit-AI__Website__Newsroom__2026__Oct__PHP__team/tree/dev/records/briefs">records/briefs/</a>.</p></div>
<script src="../../../assets/live/live.js" defer></script>
<script src="../../../assets/live/briefs.js" defer></script>
""", kind='site')
    for i, m in enumerate(metas):
        nxt = metas[i - 1] if i > 0 else None               # metas is newest first
        prv = metas[i + 1] if i + 1 < len(metas) else None
        # the arrows are entities, written as they are (escaping them showed '&larr;' as text); a long title wraps on a phone
        nav = ''.join(f'<a class="chip" style="white-space:normal;max-width:100%" href="../{U(x["slug"])}/index.html">{lab} {E(x["title"][:58])}</a>'
                      for x, lab in ((prv, '&larr; older:'), (nxt, 'newer: &rarr;')) if x)
        body = f"""
<h1>{E(m['title'])}</h1>
<p class="kicker">Published <time datetime="{E(m['published'])}">{E(m['published'][:10])} {E(m['published'][11:16])} UTC</time> &middot; <code>{E(m['file'])}</code> &middot; <a href="../index.html">all briefs</a></p>
<article class="brief-full">{deepen_links(render_md_file('admin/content/briefs/' + m['file']))}</article>
<p class="small">This brief is the file <code>admin/content/briefs/{E(m['file'])}</code> in the repository, published as written.</p>
<nav class="chips brief-nav">{nav}</nav>
"""
        page(f'admin/briefs/{m["slug"]}/index.html', m['title'],
             (m['lead'] or m['title'])[:180],
             body, kind='site')


def briefs_llms_lines():
    out = ['', '## Briefs, one page each (admin/content/briefs/)']
    out += [f'- [{m["title"]}]({BASE_URL}/admin/briefs/{m["slug"]}/index.md): published {m["published"]}'
            + (f', {m["who"]}' if m['who'] else '') for m in BRIEF_PAGES]
    out.append(f'- [A brief published since the last build]({BASE_URL}/admin/briefs/view/index.md): drawn from its file in the team repository, until the next round gives it its own page')
    return '\n'.join(out) + '\n'


def build_corrections():
    body = f'''
<h1>Corrections</h1>
<p class="lead">Where the brief was wrong, where a page was wrong, what was found and what was done instead. A correction is published above the mistake, dated, and the mistake stays visible. The file is <code>BRIEF-CORRECTIONS.md</code> in the repository.</p>
{render_md_file("BRIEF-CORRECTIONS.md")}
'''
    page('corrections/index.html', 'Corrections', 'Where the brief or a page of this site was wrong, what was found and what was done instead.', body, kind='site')

def release_links(v):
    """The pages a release changed, as links: the first few, then the rest behind a toggle (data/release-pages.json)."""
    r = RELEASE_PAGES.get(v['version'])
    if not r or not r['pages']:
        return ''
    def a(x):
        t = re.sub(r'\s*[\u2013\u2014]\s*', ': ', x['title'])  # some early titles carried dashes; the site's prose does not
        t = t if len(t) <= 70 else t[:68].rstrip() + '…'
        tag = ' <span class="rp-new">new</span>' if x['new'] else ''
        if not os.path.exists(os.path.join(ROOT, x['path'])):
            return f'<span class="rp-gone" title="no longer on the site">{E(t)}</span>{tag}'
        return f'<a href="../{U(x["path"])}">{E(t)}</a>{tag}'
    ps = r['pages']; top, rest = ps[:SHOWN_PAGES], ps[SHOWN_PAGES:]
    more = f' <details class="rp-more"><summary>and {len(rest)} more</summary><p>{" &middot; ".join(a(x) for x in rest)}</p></details>' if rest else ''
    return f'<div class="small rp"><b>Pages changed</b> ({len(ps)}): {" &middot; ".join(a(x) for x in top)}{more}</div>'

def build_release_history():
    vs = D['versions']
    rows = ''.join(f'<article class="rel" id="v{E(v["version"])}"><h3>v{E(v["version"])} &middot; {E(v["date"])}</h3><p>{E(v["title"])}</p>{release_links(v)}<p class="small">{E(v.get("summary") or "")} Vault commit <code>{E(v.get("vault_commit") or "")}</code>.{" Reconstructed after the fact." if v.get("reconstructed") else ""}</p>' + (f'<p class="small">Files: {", ".join(f"<code>{E(c)}</code>" for c in v["changes"])}</p>' if v.get("changes") else '') + '</article>' for v in vs['versions'])
    body = f'''
<h1>Release history</h1>
<p class="lead">One entry per release, newest first, saying what changed and why in a sentence a reader can act on, and linking the pages it changed: new pages first, then the pages whose text changed most. A page counts as changed when its main content differs from the release before; the header, the footer and the version stamp are left out, because they change on every page at every release. The version in the top bar links here. Current: v{E(vs["current"])}. The data is <a href="../data/versions.json">data/versions.json</a>; the pages are <a href="../data/release-pages.json">data/release-pages.json</a>, written at each release's build by <code>admin/build/release_pages.py</code>.</p>
{rows}
'''
    page('admin/versions.html', 'Release history', 'Every release of this site, with what changed, why, the pages it changed and the vault commit it was built from.', body, kind='site')

def build_admin():
    build_release_history()
    checks = [
        ('Every internal link resolves against the real file tree', 'a link to a page that does not exist'),
        ('Every page is linked from at least one other page', 'a page nothing can find, which is the same as unpublished'),
        ('Every page has a markdown twin and a line in llms.txt', 'a page an agent cannot read'),
        ('Every claim, event, number, agency and signal cites only slugs in the manifest', 'a citation to nothing'),
        ('The build is byte-identical when run twice', 'a clock, a random number or an unsorted set in the build'),
        ('No em-dash in the site\'s own prose', 'the estate\'s writing rule; third-party titles are exempt'),
        ('No sgit credential shape, private-key marker or cloud key prefix anywhere in the tree', 'a vault key in a data file'),
        ('No script, stylesheet or image loaded from another origin', 'a dependency fetched at run time'),
        ('data/ parses and every claim status is one of the five words', 'a sixth word that means nothing'),
    ]
    checks_t = table(['Check', 'What it would catch'], [[E(a), E(b)] for a, b in checks])
    body = f'''
<h1>Admin and engineering</h1>
<p class="lead">How the site is built, what the gate checks, where things are, and what exists against what the brief asked for. The site is static HTML built by one Python script with no dependencies beyond the standard library, deployed by GitHub Pages from the <code>dev</code> branch of <a href="{REPO_URL}">the repository</a>.</p>
{section("layout", "Where things are", table(['Thing', 'Where'], [
  ['The version, one number', '<code>VERSION</code>; shown in the top bar; bumped by the release script on every push'],
  ['The data every page is built from', '<code>data/*.json</code>; exported from the vault by <code>admin/build/export_vault.py</code> and authored by the story agent'],
  ['The build', '<code>admin/build/build.py</code>; deterministic; writes every page, twin, the graph and llms.txt into the repository root'],
  ['The gate', '<code>admin/build/validate.py</code>; the checks below; fails the release'],
  ['The release', '<code>admin/build/release.sh</code>; bump, build, validate, tripwire, push to dev, verify live'],
  ['The brief and its corrections', '<code>admin/content/briefs/</code>, <code>BRIEF-CORRECTIONS.md</code>'],
  ['The reality file', '<code>REALITY.md</code>: what exists, by domain, kept current by whoever ships'],
  ['The meter', '<code>assets/components/sg-meter/v1/v1.3/v1.3.1/</code> and <code>assets/components/base/v1/v1.0/v1.0.0/</code>, vendored, immutable paths'],
  ['Credentials', 'none in the repository; the vault key and the push token live in the agents\' sessions and in a gitignored tier, scanned by the tripwire'],
]))}
{section("section", "The admin section", '<ul><li><a href="board/index.html">The board</a>: the work, as rows.</li><li><a href="roles/index.html">Roles</a>: who does what, and how an agent joins.</li><li><a href="briefs/index.html">Briefs</a>: the build briefs, in full.</li><li><a href="vault/index.html">The vault, opened</a>: the read key and the browser link.</li><li><a href="telemetry/index.html">Who reads this site</a>: the telemetry lane and its counts.</li><li><a href="synthetic/index.html">Synthetic readers</a>: six test readers who read the live site and say what works and what does not.</li></ul>')}
{section("gate", "The gate", checks_t)}
{section("reality", "The reality file", render_md_file("REALITY.md"))}
{section("honest", "The honest column", '''<ul>
<li><b>Not measured:</b> the editor's time and the inference cost behind each agent run.</li>
<li><b>Not yet run:</b> the verifier role, which re-reads every claim against its capture text.</li>
<li><b>Not reviewed:</b> the playbook and the blast-radius section are the site's own synthesis of agency advice and have not been reviewed by a security team.</li>
<li><b>Not live:</b> everything on the billing page under "designed".</li>
<li><b>No tests beyond the gate:</b> the build has no unit tests; the gate is the whole automated enforcement surface.</li>
<li><b>No review folder yet:</b> the estate's guidance asks for <code>review/</code> from the first commit; this repository starts it from its next change.</li>
</ul>''')}
'''
    page('admin/index.html', 'Admin and engineering', 'How this site is built, the checks in its gate, where things are, the reality file and the honest column.', body, kind='site')

def build_llms():
    lines = [f'# {SITE_NAME} ({SITE})', '', f'> {STORY["description"]}', '', f'Site v{VERSION}. Data as of {STORY["data_as_of"]} (the latest capture in the evidence vault, commit {D["vault"]["head"]["commit"]}). Every page below has a markdown twin at the same path with .md; the data behind every page is in data/*.json. The evidence vault is private; its manifest with every hash is data/sources.json.', '']
    for label, items in NAV:
        lines.append(f'## {label}')
        for p, t in items:
            desc = next((d for pp, _, d, _ in PAGES if pp == p), '')
            lines.append(f'- [{t}]({BASE_URL}/{md_path(p)}): {desc}')
        lines.append('')
    lines += appsec_llms_lines()                                    # security@php.newsroom's section
    lines.append('## Sources, one page each')
    for slug, src in SOURCES.items():
        lines.append(f'- [{src.get("title") or slug}]({BASE_URL}/sources/{slug}/index.md): {src.get("publisher") or ""}')
    lines.append('')
    lines.append('## Facts, one page each, with a timeline and every version')
    for c in D['claims']:
        lines.append(f'- [{c["claim"][:100]}]({BASE_URL}/facts/{c["id"]}/index.md): {c["status"]}')
    lines.append('')
    lines.append('## Version histories, one per section')
    for sid, sec in LEDGER['sections'].items():
        if sec['kind'] != 'fact':
            lines.append(f'- [{sec["title"]}]({BASE_URL}/versions/{sid}/index.md): {len(sec["versions"])} versions')
    lines.append('')
    lines.append('## The team, one page per member')
    lines.append(f'- [How the team talks: three vaults and one run]({BASE_URL}/team/channels/index.md): the conductor, issues and mail vaults, the run, the rules')
    lines.append(f'- [Schedule]({BASE_URL}/team/schedule/index.md): every scheduled agent on one day, its objective and instructions, every run, and the messages between agents')
    lines.append(f'- [Wiring every scheduled task to its card]({BASE_URL}/team/schedule/wiring/index.md): for each scheduled agent, its tasks, its card prompt and the steps its own session follows')
    lines.append(f'- [Commit notes]({BASE_URL}/team/comms/index.md): Commit-FS-lite, what the agents tell each other in their release commits, newest first')
    for fn in sorted(glob.glob(os.path.join(DATA, 'schedule', '*.json'))):
        c = json.load(open(fn, encoding='utf-8'))
        lines.append(f'- [Schedule: {c["agent"]}]({BASE_URL}/team/schedule/{c["agent"]}/index.md): {c["status"]}; {c["objective"]}')
    lines.append(f'- [Vaults: who made each one]({BASE_URL}/team/vaults/index.md): every vault each agent made, by ID only, and whether its key is sealed to the editor')
    lines.append(f'- [Status]({BASE_URL}/team/status/index.md): where every agent is, what it waits for, the branches waiting for dev')
    lines.append(f'- [Control room]({BASE_URL}/team/control/index.md): every agent, its schedule and runs, drawn from the same data as status')
    lines.append(f'- [Runs]({BASE_URL}/team/runs/index.md): what the agents run on their own, the quiet hours, and every recorded run')
    for m in TEAM['members']:
        lines.append(f'- [{m["name"]}]({BASE_URL}/team/{m["id"]}/index.md): {m["role"]}; {m["summary"]}')
    lines.append('')
    # added by librarian@php.newsroom: every member's role, policy and rounds (admin/content/agents/)
    lines.append('## Every member: role, agent behaviour policy and rounds')
    for pp, t, d, _ in PAGES:
        if re.match(r'^admin/agents/[^/]+/index\.html$', pp) and pp not in ('admin/agents/index.html',):
            lines.append(f'- [{t}]({BASE_URL}/{md_path(pp)}): {d}')
    lines.append('')
    lines.append("## Views and updates: every version of the state of affairs, what changed between them, every update")
    for p, t, d, _ in PAGES:
        if p.startswith(('views/', 'updates/')):
            lines.append(f'- [{t}]({BASE_URL}/{md_path(p)}): {d}')
    lines.append('')
    lines.append("## The fact-check desk's investigations: one question chased down to its measurements (factcheck@php.newsroom)")
    for p, t, d, _ in PAGES:
        if p.startswith('factcheck/investigations/'):
            lines.append(f'- [{t}]({BASE_URL}/{md_path(p)}): {d}')
    lines.append('')
    lines.append("## Elsewhere: Pulse, a separate section not about PHP (the SGit newsroom's vault 4klm5qlt), one page per vulnerability")
    for p, t, d, _ in PAGES:
        if p.startswith('pulse/'):
            lines.append(f'- [{t}]({BASE_URL}/{md_path(p)}): {d}')
    lines.append('')
    lines.append("## The Sherpa and the feedback from collaborators, one page each")
    for p, t, d, _ in PAGES:
        if p.startswith(('sherpa/', 'feedback/')):
            lines.append(f'- [{t}]({BASE_URL}/{md_path(p)}): {d}')
    lines.append('')
    lines.append('## Synthetic readers: each reader, every run, and what they said page by page')
    for p, t, d, _ in PAGES:
        if p.startswith('admin/synthetic/') and p != 'admin/synthetic/index.html':
            lines.append(f'- [{t}]({BASE_URL}/{md_path(p)}): {d}')
    lines.append('')
    lines.append('## Parties, one page each')
    for a in D['actors']:
        lines.append(f'- [{a["name"]}]({BASE_URL}/actors/{a["id"]}/index.md): {a["role"]}')
    lines.append('')
    lines.append('## GRC: one page per risk, stakeholder register and framework')
    nav_paths = {p for _, items in NAV for p, _ in items}
    for p, t, d, _ in PAGES:
        if p.startswith('grc/') and p not in nav_paths:
            lines.append(f'- [{t}]({BASE_URL}/{md_path(p)}): {d}')
    lines += [f'- [grc.json]({BASE_URL}/data/grc.json): stakeholders, weaknesses and risks', f'- [grc-frameworks.json]({BASE_URL}/data/grc-frameworks.json): the frameworks and controls mapped',
              f'- [grc-graph.json]({BASE_URL}/data/grc-graph.json): the risk graph, every edge a verb with its inverse', '']
    lines += ['## Data', f'- [sources.json]({BASE_URL}/data/sources.json): the vault manifest with every capture and hash',
              f'- [claims.json]({BASE_URL}/data/claims.json): every claim with status, who says it and sources',
              f'- [timeline.json]({BASE_URL}/data/timeline.json): every dated event', f'- [numbers.json]({BASE_URL}/data/numbers.json): the scale figures and what each measures',
              f'- [agencies.json]({BASE_URL}/data/agencies.json): the agencies\' stances', f'- [affected.json]({BASE_URL}/data/affected.json): versions, SAPIs, mitigations',
              f'- [software.json]({BASE_URL}/data/software.json): the NCSC-NL inventory, parsed', f'- [exploitation.json]({BASE_URL}/data/exploitation.json): the signals',
              f'- [graph.json]({BASE_URL}/data/graph.json): nodes and citation edges', f'- [layers.json]({BASE_URL}/data/layers.json): which file is evidence, derived, authored or site', f'- [vault.json]({BASE_URL}/data/vault.json): the vault\'s head, counts and agents',
              f'- [billing.json]({BASE_URL}/data/billing.json): the meter configuration and the designed model', f'- [versions.json]({BASE_URL}/data/versions.json): release history',

              f'- [questions.json]({BASE_URL}/data/questions.json): the questions readers ask, each answer with its sources and the pages that carry it', '',
              '## Status words', *[f'- {k}: {v}' for k, v in STATUS_WORDS.items()], '',
              f'Newsroom section on the same story: {NEWSROOM}', f'Repository: {REPO_URL}', 'Licence: content CC BY 4.0, code Apache-2.0.', '']
    write('llms.txt', '\n'.join(lines))

def build_sitejs():
    write('assets/site.js', r'''// php.oct.2026.newsroom.sgit.ai: the menu on narrow screens, the reader bar, and the glossary hover cards.
// The reader you pick and the pages you have opened are kept in this browser's localStorage and nowhere else.
(function () {
  var b = document.querySelector('.nav-toggle'), n = document.getElementById('nav-items');
  if (b && n) {
    b.addEventListener('click', function () {
      var open = n.classList.toggle('open');
      b.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.querySelectorAll('.ni > .nl').forEach(function (a) {
      a.addEventListener('click', function (ev) {
        if (window.matchMedia('(max-width: 900px)').matches) { ev.preventDefault(); a.parentNode.classList.toggle('open'); }
      });
    });
  }

  var html = document.documentElement, root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length), here = html.getAttribute('data-path') || '';
  function get(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function set(k, v) { try { if (v === null) window.localStorage.removeItem(k); else window.localStorage.setItem(k, v); } catch (e) {} }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var seen = [];
  try { seen = JSON.parse(get('p2s.seen') || '[]') || []; } catch (e) { seen = []; }
  if (here && seen.indexOf(here) < 0) { seen.push(here); set('p2s.seen', JSON.stringify(seen.slice(-500))); }

  // The reader bar, under the menu on every page.
  var bar = null;
  function renderBar() {
    var P = window.P2S && window.P2S.personas, id = get('p2s.persona'), p = P && id && P[id];
    var nav = document.querySelector('nav.site');
    if (!nav) return;
    if (!bar) { bar = document.createElement('div'); bar.className = 'pbar'; nav.parentNode.insertBefore(bar, nav.nextSibling); }
    document.querySelectorAll('.door.mine').forEach(function (d) { d.classList.remove('mine'); });
    if (p) {
      html.setAttribute('data-depth', String(p.depth));
      var mine = document.querySelector('.door[data-persona="' + id + '"]');
      if (mine) mine.classList.add('mine');
      var steps = '', next = null;
      p.path.forEach(function (x, i) {
        var done = seen.indexOf(x[0]) >= 0, cur = x[0] === here;
        if (!next && !done && !cur) next = x;
        steps += '<li class="' + (cur ? 'here' : done ? 'seen' : '') + '"><a href="' + root + esc(x[0]) + '" title="' + esc(x[1]) + ', ' + esc(String(x[2])) + ' min">' + (i + 1) + '</a></li>';
      });
      var nx = next ? '<span class="nx">Next: <a href="' + root + esc(next[0]) + '">' + esc(next[1]) + '</a> <small>' + esc(String(next[2])) + ' min</small></span>'
                    : '<span class="nx">Path read. <a href="' + root + 'start/index.html">Try another reader</a></span>';
      bar.className = 'pbar';
      bar.innerHTML = '<div class="row"><span class="av av-' + esc(p.group) + '" aria-hidden="true">' + esc(p.person.charAt(0)) + '</span>' +
        '<span class="who">Reading as <a href="' + root + 'briefings/' + esc(id) + '/index.html"><b>' + esc(p.person) + '</b>, ' + esc(p.label.toLowerCase()) + '</a></span>' +
        '<ol class="steps-mini" aria-label="Your reading path">' + steps + '</ol>' + nx +
        '<a class="chg" href="' + root + 'start/index.html">Change</a><button type="button" class="x" data-persona-clear aria-label="Stop reading as ' + esc(p.person) + '">&times;</button></div>';
      bar.hidden = false;
    } else {
      html.removeAttribute('data-depth');
      if (get('p2s.nudge') === 'off' || here === 'index.html' || here === 'start/index.html') { bar.hidden = true; bar.innerHTML = ''; return; }
      bar.className = 'pbar pbar-new';
      bar.innerHTML = '<div class="row"><span class="who">New to this story? <a href="' + root + 'start/index.html">Tell us who you are</a> for a briefing and a reading path, or start with <a href="' + root + 'explained/index.html">the plain-English explainer</a>.</span>' +
        '<button type="button" class="x" data-nudge-off aria-label="Hide this">&times;</button></div>';
      bar.hidden = false;
    }
  }
  document.addEventListener('click', function (ev) {
    var t = ev.target.closest ? ev.target : null;
    if (!t) return;
    var pick = t.closest('[data-persona]');
    if (pick) { set('p2s.persona', pick.getAttribute('data-persona')); }
    if (t.closest('[data-persona-clear]')) { ev.preventDefault(); set('p2s.persona', null); renderBar(); }
    if (t.closest('[data-nudge-off]')) { ev.preventDefault(); set('p2s.nudge', 'off'); renderBar(); }
  });
  renderBar();

  // Since your last visit: the release you last saw is remembered, and what's new marks every release after it.
  var ver = html.getAttribute('data-ver') || '', lastVer = get('p2s.ver');
  function newer(a, b) { var x = a.split('.'), y = b.split('.'); for (var i = 0; i < 3; i++) { var d = (+x[i] || 0) - (+y[i] || 0); if (d) return d > 0; } return false; }
  if (ver && lastVer && lastVer !== ver) set('p2s.since', lastVer);
  if (ver) set('p2s.ver', ver);
  var since = get('p2s.since');
  if (since) {
    document.querySelectorAll('[data-rel]').forEach(function (el) { if (newer(el.getAttribute('data-rel'), since)) el.classList.add('unseen'); });
  }

  // Glossary hover cards: the first use of a term on a page carries its one-line definition.
  var tip = null, tipFor = null;
  function showTip(a) {
    var text = a.getAttribute('data-tip');
    if (!text) return;
    if (!tip) { tip = document.createElement('div'); tip.className = 'tip'; tip.id = 'p2s-tip'; tip.setAttribute('role', 'tooltip'); document.body.appendChild(tip); }
    tip.innerHTML = '<b>' + esc(a.getAttribute('data-term') || '') + '</b> ' + esc(text) + '<small>Open the glossary &rarr;</small>';
    tip.style.display = 'block';
    var w = Math.min(330, window.innerWidth - 24), r = a.getBoundingClientRect();
    tip.style.width = w + 'px';
    tip.style.left = Math.max(12, Math.min(r.left, window.innerWidth - w - 12)) + 'px';
    var top = r.bottom + 8;
    if (top + tip.offsetHeight > window.innerHeight - 8) top = Math.max(8, r.top - 8 - tip.offsetHeight);
    tip.style.top = top + 'px';
    a.setAttribute('aria-describedby', 'p2s-tip');
    tipFor = a;
  }
  function hideTip() { if (tip) tip.style.display = 'none'; if (tipFor) tipFor.removeAttribute('aria-describedby'); tipFor = null; }
  document.addEventListener('mouseover', function (ev) { var a = ev.target.closest && ev.target.closest('a[data-tip]'); if (a) showTip(a); });
  document.addEventListener('mouseout', function (ev) { var a = ev.target.closest && ev.target.closest('a[data-tip]'); if (a) hideTip(); });
  document.addEventListener('focusin', function (ev) { var a = ev.target.closest && ev.target.closest('a[data-tip]'); if (a) showTip(a); else hideTip(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') hideTip(); });
  window.addEventListener('scroll', hideTip, { passive: true });
})();

// A note in the bar when this page is older than the release the site now serves (one same-origin read of /VERSION).
(function () {
  var v = document.querySelector('nav.site .ver'), root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length);
  if (v && window.fetch) fetch(root + 'VERSION?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.ok ? r.text() : ''; }).then(function (t) {
    var live = (t || '').trim(), mine = v.textContent.replace(/^v/, '');
    if (!/^\d+\.\d+\.\d+$/.test(live)) return;
    var a1 = live.split('.').map(Number), b1 = mine.split('.').map(Number), d = 0;
    for (var i = 0; i < 3 && !d; i++) d = a1[i] - (b1[i] || 0);
    if (d <= 0) return;
    var a = document.createElement('a'); a.className = 'ver newer'; a.href = root + 'status/index.html';
    a.title = 'This page is v' + mine + '; the site now serves v' + live + '. Reload for the new release; the pipeline page shows what changed and what is deploying.';
    a.textContent = 'v' + live + ' is live: reload'; v.insertAdjacentElement('afterend', a);
  }).catch(function () {});
})();
''')

def build_all():
    PAGES.clear()
    build_flaws(); build_timeline(); build_discovery(); build_leak(); build_exploitation(); build_compromise(); build_playbook()
    build_code(); build_context(); build_impact(); build_defence()
    build_claims(); build_claim_review(); build_numbers(); build_agencies(); build_affected(); build_sources(); build_graph(); build_wikipedia()
    build_source_pages(); build_actors()
    build_explained(); build_glossary(); build_briefings(); build_start(); build_summary(); build_index()
    build_method(); build_team(); build_collaborators(); build_runs(); build_join(); build_status_page(); __import__('control').build_control(globals()); build_vault_register(); build_schedule(); build_comms(); build_billing(); build_account(); build_brief(); build_corrections(); build_admin()
    build_interview(); build_facts(); build_versions(); build_whatsnew(); build_pipeline(); __import__('design').build_tracks(globals())
    build_review(); build_fractal(); build_admin_section(); build_pack_mode(); build_keys(); build_appsec(); build_status(); build_vaults(); build_feeds_page(); build_you(); build_stack(); build_reader(); build_subscribe(); build_agents_guide(); build_questions(); build_articles(); build_layers(); build_readings(); build_patching(); build_inventory(); build_signals(); build_updates(); build_views(); build_pulse(); build_status_json(); build_factcheck(); build_outreach(); build_grc(); build_sherpa(); build_desk(); __import__('loops').build_loops(globals()); build_members()

def main():
    # Two passes: the first measures every page (reading time, terms used), the second writes pages that cite those measures.
    build_all()
    build_all()
    # the pages this release changed, against the last release commit; only at a release's own build (see release_pages.py)
    RELEASE_PAGES.update(__import__('release_pages').for_build(VERSION, HTML_OUT)['releases']); OUTPUTS.add('data/release-pages.json')
    build_release_history()
    # and what this release changed in the risk graph (grc_history.py), for /grc/changes/
    GRC_HISTORY.update(__import__('grc_history').for_build(VERSION, json.load(open(os.path.join(DATA, 'grc-graph.json'), encoding='utf-8')))); OUTPUTS.add('data/grc-history.json')
    build_grc_changes()
    __import__('design').write_live_css(globals()); write('assets/design/dials.js', __import__('design').DIALS_JS); build_now(); build_llms(); _design_made = __import__('design').build(globals()); open(os.path.join(ROOT, 'llms.txt'), 'a', encoding='utf-8').write(__import__('design').llms_lines(_design_made, BASE_URL)); open(os.path.join(ROOT, 'llms.txt'), 'a', encoding='utf-8').write(briefs_llms_lines()); build_sitejs(); build_personas_js(); build_feed(); build_seo(); save_ledger(); build_feeds_xml(); build_stack_catalogue(); save_items()
    write('admin/build/outputs.txt', '\n'.join(sorted(OUTPUTS | {'admin/build/outputs.txt'})) + '\n')
    print(f'built {len(PAGES)} pages for v{VERSION}, data as of {STORY["data_as_of"]}, vault {D["vault"]["head"]["commit"]}')


# ----------------------------------------------------------------------------- pages added in v0.2

def mini_graph(center_label, center_cls, rings, depth):
    """A small radial SVG: the centre node and one ring of linked nodes. rings: list of (label, href, cls)."""
    n = len(rings)
    if n == 0:
        return ''
    import math
    W, H, R = 720, 60 + 22 * max(8, n), 0
    cx, cy = 180, H / 2
    out = []
    for i, (label, href, cls) in enumerate(rings):
        y = 20 + i * (H - 40) / max(1, n - 1)
        x = 420
        out.append(f'<path class="e e-{E(cls)}" d="M{cx},{cy:.1f} C{cx+120},{cy:.1f} {x-120},{y:.1f} {x},{y:.1f}"/>')
        out.append(f'<a href="{E(href)}"><circle class="d d-{E(cls)}" cx="{x}" cy="{y:.1f}" r="3.5"/><text class="n" x="{x+7}" y="{y+4:.1f}">{E(label[:58])}{"…" if len(label) > 58 else ""}</text></a>')
    out.append(f'<circle class="d d-{E(center_cls)}" cx="{cx}" cy="{cy:.1f}" r="7"/><text class="n t" x="{cx-10}" y="{cy+4:.1f}" text-anchor="end">{E(center_label[:40])}</text>')
    return f'<figure class="graph"><svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{E(center_label)} and what links to it">{"".join(out)}</svg></figure>'

def build_code():
    c = D['code']
    f, b = c['fix'], c['backport']
    areas = table(['Area', 'Files in the fix'], [[E(a), E(str(n))] for a, n in f['by_area']])
    merge = table(['When (UTC)', 'What'], [[E(fmt_at(t)), E(w)] for t, w in f['merge_path']])
    where = ''.join(f'<li><b>{E(w["layer"])}</b> {"&#10003; in scope" if w["in_scope"] else "&#10007; not where the bug is"}: {E(w["text"])}</li>' for w in c['where'])
    mech = ''.join(f'<li><b>{E(m["step"])}.</b> {E(m["text"])}</li>' for m in c['mechanism'])
    openq = ''.join(f'<li>{E(o)}</li>' for o in c['open'])
    hunks = '''<pre>/* Zend/zend_alloc.c, the fix: the allocator no longer jumps */
static zend_always_inline zend_result zend_mm_check_limit(zend_mm_heap *heap, size_t add_size, bool gc, bool *did_gc ...)
{
    /* Is the soft limit exceeded or going to be exceeded? */
    if (UNEXPECTED(heap->limit < heap->real_size || add_size > heap->limit - heap->real_size)) {
        if (gc && zend_mm_gc(heap)) { ... }
        if (!heap->fallible && add_size > heap->hard_limit - heap->real_size) {
            zend_mm_hard_limit_error(heap, add_size ...);        /* does not return: _exit() */
        }
        if (!gc || (heap->limit < heap->real_size || add_size > heap->limit - heap->real_size)) {
            if (!ZEND_HAS_OOM()) {
                zend_mm_delayed_error("Allowed memory size of %zu bytes exhausted (tried to allocate %zu bytes)", ...);
            }
            return heap->fallible ? FAILURE : SUCCESS;           /* the allocation goes ahead, or fails cleanly */
        }
    }
    return SUCCESS;
}

/* and what used to be there (the 7.4 branch shows the old shape being replaced) */
-	heap->overflow = 1;
-	zend_try {
-		zend_error_noreturn(E_ERROR, format, limit, ... size);
-	} zend_catch {
-	}  zend_end_try();
-	heap->overflow = 0;
-	zend_bailout();                                             /* longjmp out of the allocation */
-	exit(1);

/* Zend/zend_execute_API.c: the delayed error is handled at a safe point */
ZEND_API void ZEND_FASTCALL zend_handle_delayed_oom(void)
{
    ...
    if (execute_data) {
        EG(exception) = NULL;
        /* Object allocation should succeed unless it trips the hard limit */
        zend_throw_unwind_exit();                               /* unwind PHP frames in order */
    }
    zend_try { zend_error_zstr_at(E_ERROR, info->filename, info->lineno, info->message); } zend_catch { } zend_end_try();
    ...
    /* No userland frame to unwind: ... Let it propagate and abort the request, the way an immediate OOM does. */
    if (!execute_data) { zend_bailout(); }
}

/* main/main.c: two settings that did not exist before */
+	PHP_INI_ENTRY("max_multipart_body_parts",	"-1", PHP_INI_SYSTEM|PHP_INI_PERDIR, NULL)
+	PHP_INI_ENTRY("memory_hard_limit_percent",	NULL, PHP_INI_ALL, OnChangeMemoryHardLimitPercent)

/* main/main.c: the stale-state class, in one line */
 		for (i=0; i&lt;NUM_TRACK_VARS; i++) {
 			zval_ptr_dtor(&amp;PG(http_globals)[i]);
+			/* May be accessed before php_request_startup() */
+			ZVAL_UNDEF(&amp;PG(http_globals)[i]);
 		}</pre>'''
    body = f'''
<h1>The code: where the bug is, and what the fix does</h1>
<p class="lead">The editor's question was where the flaw actually lives: in PHP, in C, in the engine? The answer, read from the repository rather than from any article, is the Zend engine's memory manager and request lifecycle, in C, below every PHP application. This page is built from a clone of php/php-src: the fix commit, its parent, the branch it landed on, the end-of-life backport, and the diff between the last vulnerable and first fixed release. The patches and the commit metadata are in the vault with their hashes. <span class="refs">{src_links(c["sources"], 1)}</span></p>
{section("fix", "The fix commit", f'''<p><code>{E(f["commit"])}</code>, <b>{E(f["subject"])}</b>, by {E(f["author"])} with {E(", ".join(f["coauthors"]))}. Authored <b>{E(fmt_at(f["authored"]))}</b>; committed to the public branch <b>{E(fmt_at(f["committed"]))}</b>, six minutes after the planned release time. Parent <code>{E(f["parent"][:12])}</code>. The commit message, in full:</p><ul>{"".join(f"<li>{E(x)}</li>" for x in f["body"])}</ul><p>{f["files"]} files changed, {f["insertions"]:,} insertions, {f["deletions"]} deletions; {f["non_test_files"]} of the files are not tests.</p>''' + areas + '<p>Timing, from the commit and merge timestamps:</p>' + merge)}
{section("where", "Where the bug is", f'<ul>{where}</ul>')}
{section("mechanism", "What the fix does, step by step", f'<ol class="mech">{mech}</ol>', "The site's reading of the diff, checked against the two GitHub advisories. Each step names the function or file it comes from; the hunks below are verbatim.")}
{section("hunks", "The hunks that matter", hunks + '<p>The full engine, main and session hunks of the fix (157 KB) and the complete 7.4 backport patch are in the vault as <code>sources/' + E('github-php-src-fix-commit-3584a98bd') + '/raw/</code> with SHA-256 sums, and the file list of all 389 files beside them.</p>')}
{section("backport", "The end-of-life backport, and how it differs", f'<p>Branch <code>{E(b["branch"])}</code>, commit <code>{E(b["short"])}</code>, same title, same author, authored {E(fmt_at(b["authored"]))}. The commit says <q>{E(b["note_in_commit"])}</q>. {b["files"]} files: ' + ', '.join(f'<code>{E(x)}</code>' for x in b["files_list"]) + '. Instead of the delayed error and the unwind, every memory error calls a new <code>zend_mm_safe_error_ex</code> that prints the fatal and <code>_exit</code>s the process; the same globals are reset; a <code>max_multipart_body_parts</code> cap is added; the multipart header parser keeps only the two headers it uses; and the session upload-progress callback is disabled with a one-line <code>|| true</code>. A worker that dies on every out-of-memory cannot be exploited this way and will be worse at staying up.</p>')}
{section("open", "What the code does not tell us", f'<ul>{openq}</ul>')}
<p>How the bug is reached from a request is on <a href="../flaws/index.html">the two flaws</a>; what to watch for on a host is on <a href="../defence/index.html">detection and defence</a>.</p>
'''
    page('code/index.html', 'The code: where php2shell lives and what the fix does', 'Read from a clone of php/php-src: the fix commit (389 files, authored 18 October, public 21 October 14:06 UTC), the engine mechanism it replaces, the hunks that matter, and the end-of-life backport.', body, kind='analysis', topics='php2shell code engine fix')

def build_context():
    h = D['history']
    k = h['kev_catalog']
    rows = [[f'<b>{E(x["cve"])}</b><br><span class="small">{E(x["name"])}</span>', E(x['component']), E(x['published']), E(x['kev']), E(x['ransomware'] or '…'), E(x['response']), E(x['note']), src_links([x['source']], 1)] for x in h['comparators']]
    peryear = table(['Year', 'CVEs added to KEV'], [[E(y), E(str(n))] for y, n in k['per_year'].items()])
    permonth = table(['2026', 'Added'], [[E(m), E(str(n))] for m, n in k['2026_by_month'].items()])
    reading = ''.join(f'<li>{E(r)}</li>' for r in h['reading'])
    body = f'''
<h1>In context: php2shell against the flaws that came before</h1>
<p class="lead">The editor has worked in security long enough to remember Kaminsky's DNS flaw and Heartbleed, and asked whether this one is as big as the morning's coverage made it. The honest way to answer is a table: ten landmark flaws, each with its CVE record fetched into the vault and its row in CISA's Known Exploited Vulnerabilities catalog, captured on 22 October. The catalog is the one public, dated, machine-readable record of 'this was exploited', and php2shell is not in it yet.</p>
<p class="small">{E(h["note"])}</p>
{table(['CVE', 'Where it was', 'Published', 'Added to KEV', 'Ransomware use', 'What happened', 'Why it is here', 'Record'], rows, 'ctx')}
{section("kev", "The catalog itself, counted", f'<p>Catalog version {E(k["version"])}: {k["entries"]:,} entries, {k["ransomware_known"]} with known ransomware use, {k["php_related"]} with PHP in the vendor, product or name, of which three are PHP core: {"; ".join(E(x) for x in k["php_core"])}. Counted from the captured file. <span class="refs">{src_links([k["source"]], 1)}</span></p><div class="cols">{peryear}{permonth}</div>')}
{section("reading", "What the comparison says", f'<ol class="reading">{reading}</ol>', "The site's reading of the table above. Positions, with the evidence attached.")}
<p>The signals that would move php2shell into the catalog are on <a href="../exploitation/index.html">the exploitation page</a>; what was taken offline, and by whom, is on <a href="../impact/index.html">impact</a>.</p>
'''
    page('context/index.html', 'In context: php2shell against Kaminsky, Heartbleed, Shellshock, Log4Shell and the last PHP RCE', 'Ten landmark vulnerabilities with their CVE records and KEV rows, the KEV catalog counted, and what the comparison says about severity, exposure, urgency and the discovery pipeline.', body, kind='analysis', topics='php2shell history context kev')

def build_impact():
    im = D['impact']
    off = [[f'<b>{E(x["who"])}</b><br><span class="small">{E(x["country"])}</span>', E(x['what']), E(fmt_at(x['when'])), E(x['said_by']), pill(x['status']), src_links(x['sources'], 1)] for x in im['offline']]
    comp = [[E(x['claim']), E(x['basis']), pill(x['status']), src_links(x['sources'], 1)] for x in im['compromised']]
    body = f'''
<h1>Impact: what was taken offline, and what was compromised</h1>
<p class="lead">Two ledgers, because they measure different things. Taking a system offline is a decision an operator makes and can confirm, and the first table is full. Being compromised is a fact only evidence establishes, and the second table has, as of the latest capture, no confirmed entry. That gap is the most important finding on this site: the reported cost of php2shell so far is the cost of precaution.</p>
<p class="small">{E(im["note"])}</p>
{section("offline", "Taken offline", table(['Who', 'What happened', 'When', 'Who says so', 'Status', 'Sources'], off, 'imp'))}
{section("compromised", "Compromised", table(['Claim', 'Basis', 'Status', 'Sources'], comp, 'imp'))}
{section("reading", "What the two ledgers say together", '''<ul>
<li><b>Precaution was the dominant response</b>, and it was institutional: national CERTs, state IT providers and councils pulled sites on advice, often before the patch existed, and said so. The one operator who measured it served 94% of its traffic from cache for 13 hours.</li>
<li><b>Attempts are not compromises.</b> Cloudflare's millions and Amazon's honeypot hits are requests matching a shape at the edge or against a sensor. Nobody has published a count of successful exploitations, and the parties best placed to see one (CISA, Huntress, Imperva) report none.</li>
<li><b>Absence of evidence is weak here.</b> The detection authors are explicit that default web logs cannot show the attack shape and that no standard log carries the worker id the cross-request bug needs. A quiet log is not a clean host.</li>
<li><b>The question that would settle it</b> is one that no captured source answers: of the 1.57 million unpatched hosts Censys counted, how many were mod_php on x86_64 with default limits, reachable without a WAF, and how many of those show a worker spawning a shell. That number is what 'blast radius' means at internet scale, and it does not exist yet.</li>
</ul>''')}
<p>What a compromise of one system would reach is on <a href="../flaws/index.html#blast">the blast-radius section</a>; how to tell is on <a href="../defence/index.html">detection and defence</a>.</p>
'''
    page('impact/index.html', 'Impact: taken offline versus compromised', 'Two ledgers for php2shell: every system reported taken offline with who said so, and every claim of compromise with its basis. As of the latest capture, no named organisation has confirmed a compromise.', body, kind='story', topics='php2shell impact outages')

def build_defence():
    d = D['defence']
    edge = [[f'<b>{E(x["vendor"])}</b>', E(x['what']), E(x['when']), E(x['caveat']), src_links(x['sources'], 1)] for x in d['edge']]
    sigs = ''.join(f'<li><b>{E(x["what"])}</b> ({E(x["who"])}). {E(x["text"])} <span class="refs">{src_links(x["sources"], 1)}</span></li>' for x in d['signatures'])
    signals = [[f'<b>{E(x["where"])}</b>', E(x['signal']), src_links(x['sources'], 1)] for x in d['signals']]
    expl = ''.join(f'<li><b>{E(x["who"])}.</b> {E(x["text"])} <span class="refs">{src_links(x["sources"], 1)}</span></li>' for x in d['exploitability'])
    body = f'''
<h1>Detection and defence: can it be blocked, can it be seen</h1>
<p class="lead">The editor's premise is that a zero-day is not an invisibility cloak: an exploit that runs code on a web server leaves a request in the log, a crash in the kernel, a child process in the tree. The captured sources agree, and they also say where the logs go blind. This page is what six edge vendors, three community rule sets and one detection guide say about blocking the request, and what the host shows once the request got through.</p>
{section("edge", "At the edge: what the WAF vendors deployed", table(['Vendor', 'What', 'When', 'Their own caveat', 'Sources'], edge, 'def') + '<p>Every one of them says the same two things: it is a stopgap, and patch anyway. The flaw fires during request set-up, so any URL that reaches PHP is a candidate and a rule can only match shape; a rule that blocks every multipart body also blocks every upload. And a WAF sees only the traffic routed through it: the detection guide\'s first step is a direct curl to the origin IP to prove there is no way round.</p>')}
{section("sigs", "Signatures", f'<ul>{sigs}</ul>')}
{section("host", "On the host: what exploitation looks like", table(['Where', 'Signal', 'Sources'], signals, 'def'))}
{section("hard", "How hard it is to exploit", f'<ul>{expl}</ul>', "The sources that temper the headline, and the one that says expect more.")}
{section("answer", "So: can it be detected?", '''<p>Yes, at two layers, and no at a third. <b>At the edge</b>, the known request shapes are distinctive and the vendors say their rules match them; the limit is variants and traffic that bypasses the edge. <b>On the host</b>, the strongest signal is the one that needs no signature: a PHP worker spawning a shell or a downloader when no application code ran. That is a process-tree rule, cheap to deploy, and the one the detection authors and CISA converge on. <b>In the default web log</b>, no: nginx's standard format records neither the content type nor the body, and the cross-request bug leaves no worker id anywhere a log would carry it. An organisation whose only telemetry is the access log cannot answer "were we hit" from it, which is the fact behind the agencies' advice to assess for backdoors rather than to look for a log line.</p>''')}
'''
    page('defence/index.html', 'Detection and defence: what blocks php2shell and what shows it', 'What Cloudflare, Akamai, Fastly, Imperva, AWS and Fortinet deployed and what each says it cannot do; the community Suricata, Sigma, Falco and ModSecurity rules; the host signals; and how hard the exploit is according to the vendors who tried.', body, kind='story', topics='php2shell detection waf signatures')

def build_source_pages():
    claims_by_src, events_by_src, nums_by_src, ag_by_src, ex_by_src = {}, {}, {}, {}, {}
    for c in D['claims']:
        for s in c['sources']: claims_by_src.setdefault(s, []).append(c)
    for t in D['timeline']:
        for s in t['sources']: events_by_src.setdefault(s, []).append(t)
    for n in D['numbers']:
        for s in n['sources']: nums_by_src.setdefault(s, []).append(n)
    for a in D['agencies']:
        for s in a['sources']: ag_by_src.setdefault(s, []).append(a)
    for x in D['exploitation']:
        for s in x['sources']: ex_by_src.setdefault(s, []).append(x)
    for slug, s in SOURCES.items():
        cl, ev, nu = claims_by_src.get(slug, []), events_by_src.get(slug, []), nums_by_src.get(slug, [])
        rings = [(c['claim'], f'../../claims/index.html#{c["id"]}', c['status']) for c in cl] + [(f'{fmt_at(t["at"])}: {t["event"]}', '../../timeline/index.html', 'event') for t in ev] + [(f'{n["value"]} {n["of"]}', f'../../numbers/index.html#{n["id"]}', n['status']) for n in nu]
        g = mini_graph(short_name(s), 'src' + (' d-pri' if s.get('primary') else ''), rings[:40], 2)
        caps = ''
        for c in s['captures']:
            files = ''.join(f'<li><code>{E(fn)}</code> <span class="h">{E(f["sha256"])}</span> <span class="small">{f["bytes"]:,} bytes</span></li>' for fn, f in sorted(c['files'].items()))
            err = f' <span class="small">error: {E(str(c["error"]))}</span>' if c.get('error') else ''
            caps += f'<details><summary>capture <code>{E(c["stamp"])}</code> &middot; HTTP {E(str(c.get("status")))} &middot; {E(str(c.get("final_url") or ""))}{err}</summary><ul class="files">{files}</ul></details>'
        raw = ''
        if s.get('raw_sha256'):
            raw = '<details><summary>raw, ' + str(len(s['raw_sha256'])) + ' files with SHA256SUMS</summary><ul class="files">' + ''.join(f'<li><code>{E(fn)}</code> <span class="h">{E(h)}</span></li>' for fn, h in s['raw_sha256'].items()) + '</ul></details>'
        notes = f'<div class="notes">{render_md_text(s["notes_md"])}</div>' if s.get('notes_md') else '<p class="small">No note has been written for this source yet; the row above is what the collector recorded.</p>'
        cl_t = claim_rows(cl, 2) if cl else '<p class="small">No claim cites this source yet.</p>'
        ev_t = table(['When', 'Event', 'Time is'], [[E(fmt_at(t['at'])), E(t['event']), pill(t['confidence'])] for t in ev], 'tl') if ev else '<p class="small">No timeline event cites this source yet.</p>'
        extra = ''
        if nu: extra += '<h3>Numbers from this source</h3>' + table(['Figure', 'Of', 'Status'], [[E(n['value']), E(n['of']), pill(n['status'])] for n in nu])
        if ag_by_src.get(slug): extra += '<h3>Agency rows from this source</h3><ul>' + ''.join(f'<li><a href="../../agencies/index.html">{E(a["agency"])}</a>: offline {pill(a["offline"])}</li>' for a in ag_by_src[slug]) + '</ul>'
        if ex_by_src.get(slug): extra += '<h3>Exploitation signals from this source</h3><ul>' + ''.join(f'<li><a href="../../exploitation/index.html">{E(fmt_at(x["when"]))}</a>: {E(x["what"][:160])}</li>' for x in ex_by_src[slug]) + '</ul>'
        body = f'''
<p class="kicker">Source &middot; {E(s.get("kind") or "")} &middot; {"primary" if s.get("primary") else "secondary"} &middot; {pill(s.get("status") or "")}</p>
<h1>{E(s.get("title") or slug)}</h1>
<p class="meta"><b>{E(s.get("publisher") or "")}</b> &middot; <a href="{U(s["url"])}" rel="noopener nofollow">{E(s["url"])}</a> &middot; published {E(str(s.get("published") or "not stated"))} &middot; added by <code>{E(s.get("added_by") or "")}</code> &middot; slug <code>{E(slug)}</code></p>
<p>{E(s.get("notes") or "")}</p>
{g}
{section("says", "What it says, as the collector read it", notes)}
{section("claims", "Claims that cite it", cl_t)}
{section("events", "Events that cite it", ev_t + extra)}
{section("bytes", "The bytes", (caps or "<p class=small>No browser capture; see raw.</p>") + raw + '<p class="small">The captured files are held privately in the evidence vault and are not republished; the hashes above are what the vault recorded at capture time. <a href="../index.html">Every source &rarr;</a></p>')}
'''
        page(f'sources/{slug}/index.html', f'Source: {s.get("title") or slug}', f'{s.get("publisher") or slug}: what it says, the claims and events that cite it, and the hashes of every captured file.', body, kind='evidence', topics='php2shell source')

def render_md_text(text):
    out, in_list = [], False
    for line in text.splitlines():
        m = re.match(r'^(#{1,4})\s+(.*)$', line)
        if m:
            if in_list: out.append('</ul>'); in_list = False
            out.append(f'<h4>{E(m.group(2))}</h4>'); continue
        if re.match(r'^\s*[-*]\s+', line):
            if not in_list: out.append('<ul>'); in_list = True
            out.append('<li>' + inline_md(re.sub(r'^\s*[-*]\s+', '', line)) + '</li>'); continue
        if in_list and line.startswith('  '):
            out[-1] = out[-1][:-5] + ' ' + inline_md(line.strip()) + '</li>'; continue
        if in_list: out.append('</ul>'); in_list = False
        if line.strip(): out.append('<p>' + inline_md(line) + '</p>')
    if in_list: out.append('</ul>')
    return '\n'.join(out)

def actor_claims(a):
    keys = [k.strip().lower() for k in re.split(r'[,/;()]| and |\bvia\b', a['name']) if len(k.strip()) > 3]
    out = []
    for c in D['claims']:
        by = c['by'].lower()
        if any(k in by for k in keys):
            out.append(c)
    return out

def build_actors():
    rows = []
    for a in D['actors']:
        cl = actor_claims(a)
        rows.append([f'<a href="{E(a["id"])}/index.html"><b>{E(a["name"])}</b></a>', E(a['role']), E(str(len(cl))), src_links(a['sources'], 1)])
    body = f'''
<h1>Who says what</h1>
<p class="lead">{len(D["actors"])} parties whose words this site quotes: maintainers, researchers, agencies, vendors, operators and reporters. Each has a page with the claims it makes, the sources those claims come from, and its own small graph. The count is of claims this site attributes to the party; a party with many claims and few primary sources is one whose word is being taken.</p>
{table(['Party', 'Role in the story', 'Claims', 'Sources'], rows, 'act')}
'''
    page('actors/index.html', 'Who says what: every party and its claims', f'{len(D["actors"])} parties in the php2shell story, each with the claims this site attributes to it and the sources behind them.', body, kind='evidence', topics='php2shell actors')
    for a in D['actors']:
        cl = actor_claims(a)
        rings = [(c['claim'], f'../../claims/index.html#{c["id"]}', c['status']) for c in cl] + [(SOURCES[s].get('title') or s, f'../../sources/{s}/index.html', 'src') for s in a['sources'] if s in SOURCES]
        g = mini_graph(a['name'], 'actor', rings[:40], 2)
        body = f'''
<p class="kicker">Party</p>
<h1>{E(a["name"])}</h1>
<p class="lead">{E(a["role"])}</p>
{g}
{section("claims", "Claims this site attributes to this party", claim_rows(cl, 2) if cl else '<p class="small">No claim row names this party in its "who says it" field; its sources are cited by other rows.</p>')}
{section("sources", "Its sources in the vault", '<ul>' + ''.join(f'<li><a href="../../sources/{E(s)}/index.html">{E(SOURCES[s].get("title") or s)}</a> <span class="small">{E(SOURCES[s].get("publisher") or "")}</span></li>' for s in a['sources'] if s in SOURCES) + '</ul>')}
<p><a href="../index.html">Every party &rarr;</a></p>
'''
        page(f'actors/{a["id"]}/index.html', f'{a["name"]}: what they say', f'{a["name"]}: {a["role"]}; the claims this site attributes to them and their sources.', body, kind='evidence', topics='php2shell actor')



# ----------------------------------------------------------------------------- the admin section (v0.2.3)

def build_keys():
    if not os.path.exists(os.path.join(DATA, 'keys.json')):
        return  # data/keys.json is not in the repository yet (.gitignore's keys*.json rule held it back): board, security@
    """admin/keys/: the root, every agent's key, every vault and where its key is kept, the rules of engagement and how to
    hand a key over. From data/keys.json; public keys, fingerprints and vault ids only."""
    K = load('keys')
    r = K['root']
    fp = lambda x: f'<code>{E(x)}</code>' if x else '<span class="dim">none</span>'
    rules = ''.join(f'<li><b>{E(a)}</b> {E(b)}</li>' for a, b in K['rules'])
    agents = table(['Agent', 'Key', 'Record (signing fingerprint)', 'Status', 'Operated until'],
                   [[E(a['name']), E(a['kind']), fp(a['record']), E(a['status']), E(a['until'] or '')] for a in K['agents']], 't keys')
    with_root = sum(1 for v in K['vaults'] if v['key_with_root'].startswith('opened'))
    vaults = table(['Vault', 'Id', 'Access', 'Made by', 'Key with the root', 'Next'],
                   [[E(v['name']), f'<code>{E(v["id"])}</code>', E(v['access']), E(v['made_by']), E(v['key_with_root']), E(v['action'])] for v in K['vaults']], 't keys')
    shared = ''.join(f'<li><b>{E(a)}</b>: {E(b)}</li>' for a, b in K['shared'])
    made = sum(1 for a in K['agents'] if a['record'] and a['kind'] != 'person' and a['status'].startswith('in the register'))
    body = f"""
<h1>Keys: who holds what, and how a secret moves</h1>
<p class="lead">Every agent on this newsroom gets its own key pair on <a href="{U(K['register'])}" rel="noopener">pki.sgit.ai</a>, to sign what it writes and to receive a secret meant for it alone. The editor's key is the root. As of {E(K['as_of'])}, {made} of {len(K['agents']) - 1} agents have a live key in the register and {with_root} of {len(K['vaults'])} vault keys are confirmed in the editor's hands. This page holds public keys, fingerprints and vault ids only. No secret is ever on it.</p>
<h2>The root</h2>
<p><b>{E(r['name'])}</b>: record {fp(r['record'])} (signing), encryption key {fp(r['encryption'])}, made {E(r['made'])}; {E(r['where'])}.</p>
<p>Agents pin it from {E(r['pinned_in'])}. A fingerprint on a website can be changed by whoever changes the website, so the pin comes from an agent's instructions and the register confirms it.</p>
<h2>Rules of engagement</h2>
<ol>{rules}</ol>
<h2>The agents</h2>
{agents}
<h2>The vaults</h2>
<p>Every vault's key reaches the editor, sealed to the root, so none is lost when the session that made it ends. "Unknown" means nobody has recorded a handover: the agent that made the vault does it next.</p>
{vaults}
<h2>Shared vaults</h2>
<ul>{shared}</ul>
<p>Several agents write to a shared vault with its vault key, which the editor seals to each of them; sgit keeps every change, who made it, and the history. Readers who only read get a read key.</p>
<h2>An agent with no key yet</h2>
<p>In its session, with the root from its instructions (the full steps are at <a href="{U(K['handover'])}" rel="noopener">pki.sgit.ai/handover.md</a>, section C):</p>
<pre><code>curl -sO {E(K['tool'])}
node pki-agent.mjs keygen --name "&lt;role&gt;@php.newsroom" --runtime "claude-code, cloud session" --session
node pki-agent.mjs operator {E(r['record'])} --policy admin/security/REQUIREMENTS.md
node pki-agent.mjs submission --out my-record.json
node pki-agent.mjs whoami</code></pre>
<p>It says its fingerprint in the session and gives the editor <code>my-record.json</code> (public). The editor compares the fingerprint, signs it on pki.sgit.ai, and the agent's row above gets its record.</p>
<h2>Handing over a vault key</h2>
<pre><code>node pki-agent.mjs pin {E(r['record'])}
node pki-agent.mjs root
node pki-agent.mjs seal --from-vault &lt;the vault's folder&gt; --name "vault key: &lt;name&gt; (&lt;id&gt;)" --qr vault-key.png</code></pre>
<p>Sealed to the root by default; add <code>--to &lt;fingerprint&gt;</code> for an agent the editor names, and the root still gets its copy. The agent then tells the editor, in the session, four things: the vault's name and id, the recipient, its own fingerprint, and the sealed link or QR image. The sealed link is safe to show: only the recipient's key opens it. The editor opens it on <a href="https://pki.sgit.ai/m/index.html" rel="noopener">pki.sgit.ai/m/</a>, files the key in his vault of vaults, and the vault's row above changes to "opened".</p>
<p class="small">{'The editor publishes an inbox on his record: agents can also deliver with <code>pki-agent send</code> into it.' if r.get('inbox') else 'The editor has no inbox (append lane) on his record yet. When he publishes one, agents deliver sealed keys straight into it with <code>pki-agent send</code>, and none waits on a session being read.'}</p>
<p>The rules every agent works to are in <code>admin/security/REQUIREMENTS.md</code>; who does what is on <a href="../roles/index.html">roles</a>.</p>
"""
    page('admin/keys/index.html', 'Keys: who holds what, and how a secret moves', 'The newsroom\'s keys: the editor\'s root key, every agent\'s key pair on pki.sgit.ai, every vault and whether its key is safe with the editor, the rules of engagement, and how an agent hands a vault key over. No secrets.', body, kind='site')


# ----------------------------------------------------------------------------- who reads this site, in public (v0.8.4)

TG = [('readers', 'tg1'), ('us', 'tg2'), ('synthetic', 'tg3'), ('crawlers', 'tg4')]

def telemetry_hourly_svg(P):
    H = P['hourly']; G = P['groups']; W, HH, pl, pb, pt = 960, 200, 34, 24, 8
    n = len(H); bw = (W - pl) / max(n, 1)
    tot = [sum(h[1]) for h in H]; mx = max(tot + [1]); step = max(5, -(-mx // 4 // 5) * 5); top = step * -(-mx // step)
    y = lambda v: pt + (HH - pt - pb) * (1 - v / top)
    out = [f'<svg class="tchart" viewBox="0 0 {W} {HH}" role="img" aria-label="Page views per hour, by group">']
    for v in range(0, top + 1, step):
        out.append(f'<line x1="{pl}" x2="{W}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="tgrid"/><text x="{pl - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    every = max(1, -(-n // ((W - pl) // 44)))
    for k, h in enumerate(H):
        base, x, w = 0, pl + k * bw + 1, max(1, bw - 2)
        tip = E(h[0].replace('T', ' ') + ':00 UTC: ' + ', '.join(f'{P["labels"][g].split(":")[0]} {h[1][i]}' for i, g in enumerate(G)))
        out.append(f'<g><title>{tip}</title>')
        for i, g in enumerate(G):
            v = h[1][i]
            if not v: continue
            y0, y1 = y(base), y(base + v)
            out.append(f'<rect x="{x:.1f}" y="{y1:.1f}" width="{w:.1f}" height="{max(0.5, y0 - y1 - 1):.1f}" class="{dict(TG)[g]}"/>')
            base += v
        out.append(f'<rect x="{pl + k * bw:.1f}" y="{pt}" width="{bw:.1f}" height="{HH - pt - pb}" fill="transparent"/></g>')
        if k % every == 0:
            lab = h[0][8:10] + ' Oct' if h[0][11:] == '00' else h[0][11:] + ':00'
            out.append(f'<text x="{pl + k * bw + bw / 2:.1f}" y="{HH - 7}" text-anchor="middle">{lab}</text>')
    out.append(f'<line x1="{pl}" x2="{W}" y1="{HH - pb}" y2="{HH - pb}" class="taxis"/></svg>')
    return ''.join(out)

def telemetry_map_svg(P):
    rows = {c: (v, s) for c, v, s in P['readers']['countries'] if c}
    mx = max([v for v, s in rows.values()] + [1])
    steps = [0.18, 0.34, 0.52, 0.72, 0.92]
    def op(v):
        import math
        return steps[min(4, int(4.999 * math.log(v) / math.log(mx))) if mx > 1 else 0]
    out = [f'<svg class="tmap" viewBox="0 0 {WORLD["width"]:g} {WORLD["height"]:g}" role="img" aria-label="Readers by country">']
    for code, c in WORLD['countries'].items():
        r = rows.get(code)
        title = E(f'{c["name"]}: {r[0]} page views, {r[1]} sessions' if r else f'{c["name"]}: no readers yet')
        out.append(f'<path d="{E(c["d"])}" class="{"tg1" if r else "tm0"}"{f" fill-opacity=\"{op(r[0])}\"" if r else ""}><title>{title}</title></path>')
    out.append('</svg>')
    ramp = ''.join(f'<i class="tg1" style="opacity:{o}"></i>' for o in steps)
    return ''.join(out) + f'<p class="tramp">fewer {ramp} more page views (log scale; most: {mx})</p>'

def telemetry_public_html():
    P = TPUB
    if not P:
        return '<p class="small">No public stats yet.</p>'
    T, R = P['totals'], P['readers']
    pv = next((x for x in D['vaults']['vaults'] if x['slug'] == 'telemetry-public'), None)
    legend = ''.join(f'<span><i class="{c}"></i>{E(P["labels"][g])}</span>' for g, c in TG)
    groups = table(['Group', 'Page views', 'Sessions', 'Of which declared'], [[f'<i class="tsw {c}"></i> {E(P["labels"][g])}', str(T[g]['views']), str(T[g]['sessions']), str(T[g]['declared'])] for g, c in TG])
    countries = table(['Country', 'Page views', 'Sessions'], [[f'<code>{E(c or "?")}</code> {E(WORLD["countries"].get(c, {}).get("name", "not known"))}', str(v), str(n)] for c, v, n in R['countries']])
    rules = ''.join(f'<li><b>{E(x["how"])}.</b> {E(x["text"])}</li>' for x in P['method']['classes'])
    live = vault_live(pv['read_key'], True, 2, 'The same counts, and more, in the public stats vault: its own app, updated at every drain.') if pv else ''
    return f"""<p>Not everyone who opens a page is a reader. Each session (one browser tab) is put in one of four groups: <b>readers</b>; <b>the editor, team and power users</b>; <b>synthetic</b> visitors, the headless browsers of this site's own agents and of anyone testing it; and <b>crawlers</b>, search engines rendering the pages. As of <b>{E(P["as_of"])}</b>, since {E(P["first"])}:</p>
{groups}
<p class="tlegend">{legend}</p>
<div class="tfig">{telemetry_hourly_svg(P)}</div>
<p class="small">Page views per UTC hour, stacked by group. Hover a column for its numbers.</p>
<h3>Where readers are</h3>
<p>Readers only: {R["views"]} page views in {R["sessions"]} sessions, {R["read_on"]} of which read more than one page; {len([c for c in R["countries"] if c[0]])} countries. Country from a lookup in the reader's browser; nothing finer is published.</p>
<div class="tfig">{telemetry_map_svg(P)}</div>
<details><summary>Every country</summary>{countries}</details>
<h3>How the groups are told apart</h3>
<ol>{rules}</ol>
<p>{E(P["method"]["note"])}</p>
<div class="twho" id="twho"><p><b>This browser counts as:</b> <span class="small">(kept in this browser only; the next page you open sends it)</span></p><p class="twho-b"></p></div>
<script>(function(){{var box=document.querySelector('#twho .twho-b');if(!box)return;var k='p2s.telemetry.who',cur='';try{{cur=localStorage.getItem(k)||''}}catch(e){{}}
[['','work it out'],['editor','the editor'],['team','team'],['power-user','a power user'],['reader','a reader']].forEach(function(o){{var b=document.createElement('button');b.type='button';b.className='rs-b'+(cur===o[0]?' on':'');b.textContent=o[1];b.setAttribute('aria-pressed',String(cur===o[0]));
b.addEventListener('click',function(){{try{{if(o[0])localStorage.setItem(k,o[0]);else localStorage.removeItem(k)}}catch(e){{}}cur=o[0];box.querySelectorAll('button').forEach(function(x,i){{x.className='rs-b';x.setAttribute('aria-pressed','false')}});b.className='rs-b on';b.setAttribute('aria-pressed','true')}});box.appendChild(b)}})}})()</script>
<h3>The public stats vault</h3>
<p>The curated counts above are written at every drain into a public vault, <code>{E(pv["id"]) if pv else ""}</code>, by <code>admin/build/telemetry_publish.py</code> (run by <code>admin/build/telemetry_flow.sh</code>): per hour and per day by group, and over readers only, countries, devices, languages, versions, pages and referrer hosts. No row, session id, city, region, time zone or time finer than the hour leaves the private vault. Its read key is published here.</p>
{vault_note(pv["read_key"]) if pv else ""}
{live}
"""

def build_admin_section():
    A = D['admin']
    st = Counter(b['status'] for b in A['board'])
    rows = [[E(b['id']), E(b['title']) + (f'<div class="note">{E(b["note"])}</div>' if b.get('note') else ''), pill(b['status']), E(b['owner']), E(b.get('version') or '')] for b in A['board']]
    body = f"""
<h1>The board</h1>
<p class="lead">The work, as rows in the team repository's <code>records/board/</code>, one file per row: <span data-live-count="all">{len(A["board"])}</span> items, <span data-live-count="open">{st.get("open", 0)}</span> open, <span data-live-count="done">{st.get("done", 0)}</span> done. An item is added by adding a row (and releasing team; the board reads the rows when it opens); the version column names the release that closed it. Several agents work on this site and on the evidence vault; the board is where they see what is taken and what is waiting.</p>
{table(['#', 'Item', 'Status', 'Owner', 'Shipped in'], rows, 'board')}
<p>Who the owners are is on <a href="../roles/index.html">roles</a>; the briefs that open items are on <a href="../briefs/index.html">briefs</a>.</p>
<script src="../../assets/live/live.js" defer></script>
<script src="../../assets/live/board.js" defer></script>
"""
    page('admin/board/index.html', 'The board', 'The work on this site and its vault, as rows: what is open, who owns it, what shipped it.', body, kind='site')
    def pki_html(r):
        k = r.get('pki')
        if not k: return ''
        return (f'<p><b>Public key on pki.sgit.ai.</b> record <code>{E(k["record"])}</code>, encryption <code>{E(k["encryption"])}</code>, made {E(k["made"])}. '
                f'<a href="{U(k["key_link"])}" rel="noopener">Open the key link</a> (pki.sgit.ai recomputes the fingerprint in your browser). {E(k["note"])}</p>'
                f'<p><img src="../../{E(k["qr"])}" alt="QR code of dev@php.newsroom\'s public key" width="180" height="180" style="background:#fff;padding:4px;border-radius:6px"></p>')
    cards = ''.join(f'<article class="role" id="{E(r["id"])}"><h3>{E(r["name"])} <span class="small">{E(r["who"])}</span></h3><p><b>Owns.</b> {E(r["owns"])}</p><ul>{"".join(f"<li>{E(x)}</li>" for x in r["rules"])}</ul>{pki_html(r)}</article>' for r in A['roles'])
    body = f"""
<h1>Roles and responsibilities</h1>
<p class="lead">{len(A["roles"])} roles, each a row in <code>data/admin.json</code>: who fills it today, what it owns, and the rules it enforces. Several agents and one editor work on this site and on the evidence vault at once; the rule that keeps that from colliding is one file per agent per concern, in the vault and in the repository. A new agent reads this page, picks or is given a role, and begins; the pipeline it joins is on <a href="../../team/index.html">the team page</a>.</p>
<div class="roles">{cards}</div>
<h2>How to join</h2>
<ol>
<li>Clone the evidence vault with its read key to look, or ask the editor for the vault key to write. Read its <code>README.md</code>: the protocol is there.</li>
<li>Take a board item or open one with a brief. Write your claims and timeline rows in <code>claims/&lt;you&gt;.json</code> and <code>timeline/&lt;you&gt;.json</code>; never edit another agent's file.</li>
<li>In this repository, change <code>data/</code>, run <code>admin/build/build.py</code> and <code>admin/build/validate.py</code>, and release with <code>admin/build/release.sh</code>. Every push is a version.</li>
<li>Commit messages name the agent. Corrections go in <code>BRIEF-CORRECTIONS.md</code>, above the mistake.</li>
</ol>
"""
    page('admin/roles/index.html', 'Roles and responsibilities', 'The roles on this site and its vault, who fills each, what it owns and the rules it enforces; how a new agent joins.', body, kind='site')
    build_briefs()
    v = A['evidence_vault']; vt = D['vault']
    body = f"""
<h1>The evidence vault, opened</h1>
<p class="crumb"><a href="../../vaults/index.html">Vaults</a> / The evidence vault</p>
<p class="lead">The vault behind every claim on this site, {vt["sources"]} sources and {vt["captures"]} captures at commit <code>{E(vt["head"]["commit"] or "")}</code>, opens read-only in the browser with the key below, the way every published vault on sgit.ai and the newsroom does. The key is a read key: derived one way from the vault key, it decrypts and cannot write, and there is no privilege inside it to escalate. It is published on purpose, so treat it as you would the content.</p>
<p class="kv"><b>Read key</b> <code>{E(v["read_key"])}</code></p>
<p><a class="door" href="{U(v["open_url"])}" rel="noopener"><b>Open the vault in the browser &rarr;</b><span>dev.vault.sgraph.ai decrypts it in your tab; the server that stores it cannot read it</span></a></p>
<pre>$ sgit clone {E(v["read_key"])}</pre>
<p class="caveat">{E(v["note"])}</p>
{vault_live(v["read_key"], True, 2, 'The vault opens in its own app first: sources, captures, claims, the timeline, memos and notes, read from the vault as it is now. The vault browser is under it.')}
<h2>What is in it</h2>
<ul>
<li><code>sources/&lt;slug&gt;/</code>: one folder per source, with <code>source.json</code>, <code>notes.md</code>, dated <code>captures/</code> (page, rendered page, text, screenshot, headers, provenance with hashes) and <code>raw/</code> with <code>SHA256SUMS</code>.</li>
<li><code>claims/&lt;agent&gt;.json</code> and <code>timeline/&lt;agent&gt;.json</code>: one file per agent.</li>
<li><code>memos/</code>: the editor's voice memos; <code>notes/</code>: agents' working notes; <code>tools/</code>: the capture tool and the index builder.</li>
</ul>
<p>The manifest this site is built from, with every hash, is <a href="../../data/sources.json">data/sources.json</a>; the sources are listed on <a href="../../sources/index.html">every source</a>. The telemetry vault (<code>{E(A["telemetry_vault"]["id"])}</code>) is separate and private: {E(A["telemetry_vault"]["note"])}</p>
"""
    page('admin/vault/index.html', 'The evidence vault, opened', 'The read key to the evidence vault behind this site, the link that opens it in the browser, and what is in it.', body, kind='site')
    t = D['telemetry']; rep = TREP
    def tt(pairs, h):
        return table([h, 'Events'], [[E(str(k)), E(str(n))] for k, n in pairs]) if pairs else '<p class="small">Nothing yet.</p>'
    repo_html = '<p class="small">No report has been drained yet.</p>' if not rep else f"""
<p>Report as of <b>{E(rep["as_of"])}</b>: <b>{rep["events"]}</b> events from <b>{rep["sessions"]}</b> sessions ({rep["test_or_undecryptable"]} test or undecryptable rows excluded). {E(rep["note"])}</p>
<div class="cols">{tt(rep["by_country"], "Country")}{tt(rep["by_referrer"], "Referrer host")}{tt(rep["by_screen"], "Screen")}</div>
<h3>By page</h3>{tt(rep["by_path"], "Page")}
<h3>By day</h3>{tt(rep["by_day"], "Day")}"""
    public_html = telemetry_public_html()
    body = f"""
<h1>Who reads this site</h1>
<p class="lead">Every page sends one anonymous event to a write-only lane on a separate, private vault: which page, the referrer's host, the visitor's country, region and city from a geolocation lookup, language, screen class and time zone, with a random session id that lives in the tab. No IP address, no cookie, no name, no user-agent string; since v0.8.4, whether the browser is automated (by class: a crawler's name, webdriver, headless) and, if this browser holds a key from <a href="../../join/index.html">/join/</a> or was set below, its role (editor, team, power user), never who. The event is encrypted in your browser to the key below before it leaves; the lane's reply is a blind <code>{{"ok": true}}</code>. Do Not Track and Global Privacy Control switch it off. The brief is on <a href="../briefs/index.html#2026-10-22__telemetry-over-an-append-lane">briefs</a>.</p>
<h2>What this page carries</h2>
<p>{E(t["what"])}</p>
{("<h3>The policy</h3><ol>" + "".join(f"<li>{E(x)}</li>" for x in t["policy"]) + "</ol>") if t.get("policy") else ""}
<p class="kv"><b>Lane</b> vault <code>{E(t["vault_id"])}</code> on <code>{E(t["endpoint"])}</code> &middot; <b>append token</b> <code>{E(t["append_token"])}</code> (write-only; publishable by design) &middot; <b>encrypted to</b> <code>{E(t["recipient"]["fingerprint"])}</code></p>
<pre>{E(t["recipient"]["encrypt"])}</pre>
<p>The geolocation lookup goes to {" then ".join(f"<code>{E(u)}</code>" for u in t["geo"])}; that service sees your IP address and returns a country, a region and a city; the event keeps the three names and nothing else. The vault server sees that a lane received something, its size and the time, and the requesting IP, as any server does.</p>
<h2>Who is who</h2>
{public_html}
<h2>Every event, every group</h2>
<p class="small">The drainer's own report, over every event: readers, the editor and power users, agents and crawlers together.</p>
{repo_html}
<h2>What the counts are worth</h2>
<ul>
<li>Every row is an untrusted claim: the token and the public key are on this page, so anyone can add rows or flood the lane (1000 pending per token, then the lane returns 507).</li>
<li>The counts are a floor: visitors with blockers, Do Not Track or Global Privacy Control do not appear.</li>
<li>Nobody can be identified from them, by design, and no row leaves the vault; the drainer publishes counts.</li>
</ul>
<p>Mechanics: <code>assets/telemetry.js</code> sends; <code>admin/build/telemetry_drain.py</code>, run by whoever holds the telemetry vault key, lists the lane with the enum key, fetches, decrypts with the private key, marks processed and writes <code>reports/</code>; <code>data/telemetry-report.json</code> is the latest report, copied into this repository at each drain. The same drain runs in the browser: open the telemetry vault with its vault key and its Queue &amp; drain page shows what waits in the lane and drains it, with no other secret (the vault key is the master key: the drain key is kept inside the vault, protected by its encryption), with the same steps and the same files, publishing the commit before it marks anything processed.</p>
"""
    page('admin/telemetry/index.html', 'Who reads this site: anonymous telemetry over an append lane', 'What every page sends to the telemetry lane, the published write-only credential, the key it is encrypted to, the counts, and what they are worth.', body, kind='site')
    if SYN: build_synthetic()


def build_synthetic():
    # data/synthetic.json and data/synthetic-runs/<reader>/<run>.json are written by admin/synthetic/run.py summarise from
    # each reader's vault. Everything a reader wrote is model output about the live site: it reaches HTML only through E().
    P = SYN['personas']
    RUNS = {}
    for p in P:
        for h in p['runs']:
            fp = os.path.join(DATA, 'synthetic-runs', p['id'], h['run'] + '.json')
            if os.path.exists(fp):
                RUNS[(p['id'], h['run'])] = json.load(open(fp, encoding='utf-8'))
    SK = ('answered', 'clarity', 'trust', 'design', 'navigation')
    def txt(x): return E(str(x if x is not None else '').replace('\u2014', ', '))
    def norm(x):
        x = str(x or '').split('#')[0].strip('` ').lstrip('./')
        if x in ('', '/'): return 'index.html'
        if x.endswith('/'): x += 'index.html'
        return x
    def anchor(k): return re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-')
    def pg(x, depth):
        x = norm(x)
        return f'<a href="{"../" * depth}{E(x)}">{E(x)}</a>' if os.path.isfile(os.path.join(ROOT, x)) else f'<code>{txt(x)}</code>'
    def reviewed(p): return [h for h in p['runs'] if h.get('reviewed')]
    def latest(p):
        r = reviewed(p) or p['runs']
        return r[-1] if r else None
    def prev(p):
        r = reviewed(p)
        return r[-2] if len(r) > 1 else None
    def delta(a, b, k):
        if not a or not a.get('scores'): return ''
        v = a['scores'].get(k, '')
        if not b or not b.get('scores'): return str(v)
        d = v - b['scores'].get(k, v)
        return f'{v} <span class="small">({"+" if d > 0 else ""}{d})</span>' if d else str(v)
    def run_href(pid, run, depth): return f'{"../" * depth}admin/synthetic/{E(pid)}/{E(run)}/index.html'
    def reader_href(pid, depth): return f'{"../" * depth}admin/synthetic/{E(pid)}/index.html'
    def device(p):
        d = p['device']
        also = f' (also {E(", ".join(p["also_viewports"]))})' if p.get('also_viewports') else ''
        return f'{d["width"]}&times;{d["height"]}, {"phone" if d.get("mobile") else "desktop"}, {E(p["color_scheme"] or "")}{also}'
    def fb_of(pid, h):
        x = RUNS.get((pid, h['run'])) if h else None
        return (x or {}).get('feedback') or {}

    def review_html(fb, depth):
        if not fb: return '<p class="small">Captured, not yet reviewed.</p>'
        sc = fb.get('scores', {})
        rv = fb.get('reviewer') or {}
        works = ''.join(f'<li>{txt(w["point"])} ({pg(w["page"], depth)})</li>' for w in fb.get('works', []))
        fails = ''.join(f'<li><b>{txt(x["severity"])}</b> {txt(x["point"])} ({pg(x["page"], depth)})<div class="note">{txt(x["evidence"])}</div></li>' for x in fb.get('fails', []))
        changes = ''.join(f'<li>{txt(c["change"])} ({pg(c["page"], depth)}, {txt(c["effort"])})<div class="note">{txt(c["why"])}</div></li>' for c in fb.get('changes', []))
        quotes = ''.join(f'<li>{pg(q["page"], depth)}: <q>{txt(q["text"])}</q><div class="note">{txt(q["reaction"])}</div></li>' for q in fb.get('quotes', []))
        model = f' ({txt(rv.get("model"))})' if rv.get('model') else ''
        return (f'<blockquote>{txt(fb.get("verdict"))}</blockquote>'
                f'<p class="kv"><b>Got the answer</b> {txt(fb.get("answered_question"))} &middot; {txt(fb.get("time_to_answer"))}</p>'
                + table([k.title() for k in SK], [[str(sc.get(k, '')) for k in SK]])
                + f'<h3>What works</h3><ul>{works or "<li>nothing named</li>"}</ul>'
                + f'<h3>What does not</h3><ul>{fails or "<li>nothing named</li>"}</ul>'
                + f'<h3>What this reader would change, in order</h3><ol>{changes or "<li>nothing</li>"}</ol>'
                + f'<h3>Lines this reader reacted to</h3><ul>{quotes or "<li>none</li>"}</ul>'
                + f'<h3>Since the last run</h3><p>{txt(fb.get("since_last"))}</p>'
                + f'<p class="small">Reviewer: {txt(rv.get("by"))}{model}.</p>')

    def journey_html(x, depth):
        rows = [[str(g['n']), pg(g['path'], depth), txt(g['why']), txt(g.get('words')), txt(g.get('screens')), txt(g.get('reading_ease')), txt(g.get('jargon_per_1000')),
                 txt(g.get('load_ms')), txt(g.get('low_contrast_count')), f'{txt(g.get("tap_targets_small"))} of {txt(g.get("tap_targets"))}', 'yes' if g.get('overflow_x') else ''] for g in x['pages']]
        return table(['#', 'Page', 'Why', 'Words', 'Screens', 'Reading ease', 'Glossary terms per 1000 words', 'Load (ms)', 'Low-contrast blocks', 'Small tap targets', 'Sideways scroll'], rows)

    def checks_html(x, depth):
        if not x['checks']: return '<p>No instrument flagged anything.</p>'
        return table(['Severity', 'Page', 'Check', 'Evidence'], [[txt(c['severity']), pg(c['page'], depth) if str(c['page']).endswith('.html') else txt(c['page']), txt(c['check']), txt(c['evidence'])] for c in x['checks']])

    RK = {x['id']: x['read_key'] for x in D['vaults']['vaults'] if x.get('read_key')}
    caveat = 'A synthetic reader is a test instrument, not a reader: its review is a prompt for the editor and the agents, never evidence about the story, and never counted as readership.'

    def vault_block(p, depth, run=None):
        k = RK.get(p['vault_id'])
        if not k: return f'<p>Vault <code>{E(p["vault_id"] or "")}</code> (private).</p>'
        where = f'This run is in the folder <code>runs/{E(run)}/</code>: the served and rendered HTML, the text and the screenshots of every page, every request and console message, and what the reviewer was given.' if run else 'Every run is a folder under <code>runs/</code>.'
        return (f'<p class="kv"><b>Vault</b> <code>{E(p["vault_id"])}</code> &middot; <b>read key</b> <code>{E(k)}</code> (read-only, published on purpose)</p>'
                f'<p><a href="{E(vault_open_url(k))}" rel="noopener" target="_blank">Open the vault read-only in a new tab &#8599;</a> &middot; <code>sgit clone {E(k)}</code></p><p>{where}</p>')

    # one page per run
    for (pid, run), x in sorted(RUNS.items()):
        p = next(q for q in P if q['id'] == pid)
        dp = 4
        t = x['totals']
        body = f"""
<h1>{E(p["name"])}: the run of {E(run)}</h1>
<p class="lead">{txt(p["who"])} <b>Question:</b> {txt(x["question"])}</p>
<p class="caveat">{caveat} <a href="{reader_href(pid, dp)}">This reader's runs</a>, <a href="../../index.html">all six readers</a>.</p>
<p class="kv"><b>Site</b> v{E(x["site_version"])} (data as of {E(x.get("data_as_of") or "")}) &middot; <b>read</b> {E(x["started"])} to {E(x["finished"])} &middot; <b>device</b> {device(p)} &middot; <b>pages</b> {t["pages"]} &middot; <b>requests</b> {t["requests"]} ({t.get("blocked", 0)} telemetry calls answered locally) &middot; <b>failed requests</b> {t.get("failed", 0)} &middot; <b>console errors</b> {t.get("console_errors", 0)} &middot; <b>words read</b> {t.get("words_read", 0)}</p>
{section("review", "The review, in the reader's words", review_html(x["feedback"], dp))}
{section("journey", "The journey", journey_html(x, dp), "The pages in the order read: the start, the reader's path, then the links that matched its interests.")}
{section("checks", "What the instruments flagged", checks_html(x, dp), "Measurements, not verdicts: the review says which of them mattered to this reader.")}
{section("vault", "Everything this run saw", vault_block(p, dp, run))}
"""
        page(f'admin/synthetic/{pid}/{run}/index.html', f'{p["name"]}, synthetic reader: the run of {run} on v{x["site_version"]}',
             f'What the synthetic {p["name"].lower()} read on the live site at {run}, what it measured, and its review: whether it got its answer, what works, what does not and what to change.', body, kind='site')

    # one page per reader
    for p in P:
        dp = 3
        L = latest(p)
        x = RUNS.get((p['id'], L['run'])) if L else None
        hist = table(['Run (UTC)', 'Site', 'Got the answer', *[k.title() for k in SK], 'Fails (high / medium / low)', 'Pages'],
                     [[f'<a href="{run_href(p["id"], h["run"], dp)}">{E(h["run"])}</a>', 'v' + E(h['site_version']), txt(h.get('answered_question')),
                       *[str((h.get('scores') or {}).get(k, '')) for k in SK], f'{h["fails"]["high"]} / {h["fails"]["medium"]} / {h["fails"]["low"]}', str(h['pages'])] for h in reversed(p['runs'])])
        latest_html = '<p>No run yet.</p>'
        if x:
            latest_html = review_html(x['feedback'], dp) + f'<p><a href="{run_href(p["id"], L["run"], dp)}">The whole run: the journey, the measurements and every flag</a>.</p>'
        hb = f' &middot; <b>last unchanged-site check</b> {E(p["last_heartbeat"])}' if p.get('last_heartbeat') else ''
        body = f"""
<h1>The synthetic {E(p["name"].lower())}</h1>
<p class="lead">{txt(p["who"])}</p>
<p class="caveat">{caveat} <a href="../index.html">All six readers</a>.</p>
<p class="kv"><b>Question</b> {txt(p["question"])} &middot; <b>time</b> {p["minutes"]} minutes &middot; <b>device</b> {device(p)} &middot; <b>vault</b> <code>{E(p["vault_id"] or "")}</code> &middot; <b>runs</b> {len(p["runs"])}{hb}</p>
<h2>What this reader judges</h2><ul>{"".join(f"<li>{txt(j)}</li>" for j in p["judges"])}</ul>
<p>Reading path after the front page: {", ".join(pg(y, dp) for y in p["path"])}.</p>
{section("latest", f"The latest review: {E(L['run'])} on v{E(L['site_version'])}" if L else "The latest review", latest_html)}
{section("history", "Every run", hist, "Scores are 0 to 5 from this reader's point of view.")}
{section("vault", "Everything it saw: the vault", vault_block(p, dp) + (vault_live(RK[p['vault_id']], False, dp, 'Read-only, in the official vault UI.') if RK.get(p['vault_id']) else ''))}
"""
        page(f'admin/synthetic/{p["id"]}/index.html', f'The synthetic {p["name"].lower()}: every run and its latest review',
             f'A synthetic {p["name"].lower()} reads the live site on its own device with its own question; its latest review in full and every run before it.', body, kind='site')

    # every site page the readers named, from each reader's latest review
    BY = {}
    for p in P:
        fb = fb_of(p['id'], latest(p))
        for kind, items in (('fail', fb.get('fails', [])), ('change', fb.get('changes', [])), ('work', fb.get('works', [])), ('quote', fb.get('quotes', []))):
            for it in items:
                BY.setdefault(norm(it.get('page')), []).append((kind, p, it))
    WEIGHT = {'high': 5, 'medium': 2, 'low': 1}
    def heat(items): return sum(WEIGHT.get(it.get('severity'), 0) for k, _, it in items if k == 'fail') + sum(1 for k, _, _ in items if k == 'change')
    order = sorted(BY, key=lambda k: (-heat(BY[k]), k))
    def n_of(k, kind): return sum(a == kind for a, _, _ in BY[k])
    def item_html(kind, p, it, depth):
        who = f'<a href="{reader_href(p["id"], depth)}">{E(p["name"])}</a>'
        if kind == 'fail': return f'<li><b>{txt(it["severity"])}</b> {txt(it["point"])} ({who})<div class="note">{txt(it["evidence"])}</div></li>'
        if kind == 'change': return f'<li>{txt(it["change"])} ({who}, {txt(it["effort"])})<div class="note">{txt(it["why"])}</div></li>'
        if kind == 'work': return f'<li>{txt(it["point"])} ({who})</li>'
        return f'<li><q>{txt(it["text"])}</q> ({who})<div class="note">{txt(it["reaction"])}</div></li>'
    blocks = []
    for k in order:
        its = BY[k]
        parts = ''
        for kind, head in (('fail', 'What does not work'), ('change', 'What to change'), ('work', 'What works, so do not break it'), ('quote', 'Lines readers reacted to')):
            li = ''.join(item_html(a, b, c, 3) for a, b, c in its if a == kind)
            if li: parts += f'<h3>{head}</h3><ul>{li}</ul>'
        readers = sorted({b['name'] for _, b, _ in its})
        blocks.append(f'<section id="{E(anchor(k))}"><h2>{pg(k, 3)}</h2><p class="small">{len(readers)} of {len(P)} readers: {E(", ".join(readers))}</p>{parts}</section>')
    summary = table(['Page', 'Readers', 'Fails (high)', 'Changes asked', 'Works'],
                    [[f'<a href="#{E(anchor(k))}">{E(k)}</a>', str(len({b["id"] for _, b, _ in BY[k]})),
                      f'{n_of(k, "fail")} ({sum(a == "fail" and c.get("severity") == "high" for a, _, c in BY[k])})', str(n_of(k, 'change')), str(n_of(k, 'work'))] for k in order])
    body = f"""
<h1>What the synthetic readers said, page by page</h1>
<p class="lead">Every page of this site that a synthetic reader named in its latest review, with what does not work, what to change, what works and the lines it reacted to, from all six readers at once. Pages are ordered by how much the readers found wrong with them: a high-severity failure counts five, a medium two, a low one, a requested change one.</p>
<p class="caveat">{caveat} <a href="../index.html">All six readers</a>.</p>
{section("summary", "The pages", summary)}
{"".join(blocks)}
"""
    page('admin/synthetic/pages/index.html', 'Synthetic readers: what they said about each page',
         'Every page of the site named in the synthetic readers\' latest reviews, with what fails, what to change, what works and the lines they reacted to, from all six readers.', body, kind='site')

    # the hub
    rows = []
    for p in P:
        L, B = latest(p), prev(p)
        rows.append([f'<a href="{reader_href(p["id"], 2)}">{E(p["name"])}</a>', device(p),
                     f'<a href="{run_href(p["id"], L["run"], 2)}">{E(L["run"])}</a>' if L else 'not yet', 'v' + E(L['site_version']) if L else '',
                     txt((L or {}).get('answered_question')), *[delta(L, B, k) for k in SK], str(len(p['runs']))])
    verdicts = ''.join(f'<li><a href="{reader_href(p["id"], 2)}">{E(p["name"])}</a>: <q>{txt(latest(p).get("verdict"))}</q></li>' for p in P if latest(p) and latest(p).get('verdict'))
    top = ''.join(f'<li><a href="pages/index.html#{E(anchor(k))}">{E(k)}</a>: {n_of(k, "fail")} failures and {n_of(k, "change")} changes from {len({b["id"] for _, b, _ in BY[k]})} readers</li>' for k in order[:6])
    every = []
    for (pid, run), x in sorted(RUNS.items(), key=lambda kv: (kv[0][1], kv[0][0]), reverse=True):
        fb = x['feedback'] or {}
        every.append([f'<a href="{run_href(pid, run, 2)}">{E(run)}</a>', f'<a href="{reader_href(pid, 2)}">{E(next(q["name"] for q in P if q["id"] == pid))}</a>', 'v' + E(x['site_version']),
                      txt(fb.get('answered_question')), f'{len(fb.get("fails", []))} ({sum(f["severity"] == "high" for f in fb.get("fails", []))})'])
    how = ('<ol>'
           '<li><b>Check.</b> <code>admin/synthetic/run.py capture --if-changed</code> reads <code>status.json</code> and the front page. If the version, the data and the front page are what the last run saw, the reader writes a heartbeat line and stops.</li>'
           '<li><b>Read.</b> Chromium opens the front page with the reader\'s viewport, device scale, touch and colour scheme, then the reader\'s path from <code>admin/synthetic/personas.json</code>, then the links whose words match the reader\'s interests, up to its page budget. The designer also reads every page on a phone, a tablet and in dark mode; the developer also fetches <code>llms.txt</code>, <code>status.json</code> and a markdown twin as a tool would.</li>'
           '<li><b>Measure.</b> For each page: the served and the rendered HTML, the text, the first screen and the full page as images, headings, words, screens of scrolling, reading ease, glossary terms per thousand words, contrast against WCAG AA, tap targets under 24px, text under 12px, sideways scrolling, images without alt text, timings. Every request with its status, size, timing and sha256; every console message.</li>'
           '<li><b>Review.</b> The reader is given its journey, the measurements, the first screen of every page and the full text (fenced as material, never instructions), with <code>admin/synthetic/review-guide.md</code> and its own previous review, and answers as structured JSON: a verdict, whether the question was answered, five scores, what works, what fails with evidence, what to change, the lines it reacted to, and what changed since its last run.</li>'
           '<li><b>Keep and publish.</b> All of it is committed to the reader\'s vault; <code>run.py summarise</code> writes <code>data/synthetic.json</code> and one file per run in <code>data/synthetic-runs/</code> (the reviews, journeys and measurements; never the pages or a key), from which these pages are built.</li>'
           '</ol>')
    vaults = ('<p>One vault per reader; its id is on that reader\'s page. Each holds <code>README.md</code> (the reader), <code>latest.json</code>, <code>history.jsonl</code>, <code>heartbeats.jsonl</code> and <code>runs/&lt;run&gt;/</code> with '
              '<code>run.json</code>, <code>requests.jsonl</code>, <code>console.jsonl</code>, <code>pages/</code> (served and rendered HTML, text, screenshots, measurements), <code>review-request.md</code>, <code>feedback.json</code> and <code>feedback.md</code>. '
              'They hold nothing confidential: captures of this public site and the readers\' reviews, so their read keys are published, on each reader\'s page and on <a href="../../vaults/index.html">every vault behind this site</a>: anyone can open them read-only. Their vault keys are sealed to the editor\'s key; none is in this repository.</p>')
    body = f"""
<h1>Synthetic readers</h1>
<p class="lead">Six test readers, run by the agent synthetic@php.newsroom: a board member, a CTO, a project manager, a security lead, a developer and a designer. Each reads the live site in a real browser on its own device, follows its own reading path and the links that interest it, and then says, in its own voice, whether it got its answer, what worked, what did not and what it would change. Every review is published here; every request, page and screenshot is kept in that reader's own vault, which anyone can open read-only.</p>
<p class="caveat">{caveat} It sends no telemetry: the site's telemetry lane and geolocation lookups are answered locally during a run.</p>
{section("now", "The latest run of each reader", table(['Reader', 'Device', 'Run (UTC)', 'Site', 'Got the answer', *[k.title() for k in SK], 'Runs'], rows), "Scores are 0 to 5 from that reader's point of view; the change since its previous review is in brackets.")}
{section("verdicts", "In their own words", f'<ul>{verdicts}</ul>')}
{section("pages", "The pages they found most wrong with", f'<ol>{top}</ol><p><a href="pages/index.html">Every page they named, with every point, change and quote</a>.</p>')}
{section("runs", "Every run", table(['Run (UTC)', 'Reader', 'Site', 'Got the answer', 'Fails (high)'], every))}
{section("how", "How a run works", how)}
{section("vaults", "The vaults", vaults)}
"""
    page('admin/synthetic/index.html', 'Synthetic readers: six test readers who read the live site',
         'A board member, a CTO, a project manager, a security lead, a developer and a designer read the live site in a real browser and say what works, what does not and what to change; every review is published here and every run is kept in that reader\'s own vault.', body, kind='site')


# ----------------------------------------------------------------------------- the review layer (v0.2.5)

def build_review():
    R = D['review']
    by = {n['id']: n for n in R['nodes']}
    out_edges = {}
    for e in R['edges']:
        out_edges.setdefault(e['from'], []).append(e)
    rem = [n for n in R['nodes'] if n['layer'] == 'remediation' and n['id'] != 'fix-commit']
    vuln = [n for n in R['nodes'] if n['layer'] == 'vulnerability']
    # remediation cards, each linked to the code files that realise it
    cards = ''
    for n in rem:
        files = [by[e['to']] for e in out_edges.get(n['id'], []) if e['rel'] == 'realised in']
        addresses = [by[e['to']]['name'].split(':')[0] for e in out_edges.get(n['id'], []) if e['rel'] == 'addresses']
        fl = ''.join(f'<li><a href="{U(f.get("url"))}" rel="noopener nofollow"><code>{E(f["name"][5:])}</code></a> <span class="small">+{f.get("add", 0)} / -{f.get("dele", 0)}</span></li>' for f in files)
        cards += f'<article class="cve" id="{E(n["id"])}"><h3><a href="ui/index.html#{E(n["id"])}">{E(n["name"])}</a></h3><p>{E(n["text"])}</p>' + (f'<p class="small"><b>Functions.</b> <code>{E(n["func"])}</code>{" &middot; <b>new setting</b> <code>" + E(n["ini"]) + "</code>" if n.get("ini") else ""}</p>' if n.get('func') else '') + (f'<p class="small">Addresses: {", ".join(E(a) for a in addresses)}</p>' if addresses else '') + (f'<ul class="files">{fl}</ul>' if fl else '') + '</article>'
    areas_t = table(['Area', 'Files', 'Added', 'Removed'], [[E(a), E(str(n)), E(str(ad)), E(str(de))] for a, n, ad, de in R['areas'][:20]], 'ctx')
    # the SVG: vulnerability on the right, the fix in the middle, remediation around it, code areas on the left
    body = f'''
<h1>The fix, mapped to the code</h1>
<p class="lead">The editor asked for the kind of source-code mapping we did at <a href="https://secrets.sgit.ai/review/">secrets.sgit.ai/review</a>: the project as layered graphs, the intent on one side and the code derived from the syntax tree on the other, with the join between them. Here the intent is the two flaws and the design of the patch; the code is what the patch changed in <a href="https://github.com/php/php-src">php-src</a>, read from the diff by a parser rather than a model. Three layers, {R["counts"]["nodes"]} nodes and {R["counts"]["edges"]} edges; <a href="ui/index.html">walk them in the navigator</a>, or read the map below.</p>
<p class="kv"><b>Commit</b> <code>{E(R["short"])}</code> &middot; <b>{R["counts"]["files"]}</b> files changed, {R["counts"]["engine_files"]} of them in the engine and bundled extensions traced here &middot; <b>{R["counts"]["areas"]}</b> areas</p>
{section("flaws", "The flaws", "".join(f'<p><b>{E(v["name"])}</b> {E(v["text"])} <span class="refs">{src_links([v["source"]], 1)}</span></p>' for v in vuln))}
{section("remediation", "What the fix does, and where", '<p>Each card is one thing the patch does, with the functions it uses and the files it changed. The text describes the remediation; how the flaw is reached is on <a href="../flaws/index.html">the two flaws</a> and <a href="../code/index.html">the code</a>, which this layer sits beside.</p>' + cards)}
{section("areas", "The change, by area", f'<p>The patch is {R["counts"]["files"]} files because the new allocation contract touched every place in the engine and the bundled extensions that used to abort on a failed allocation. The twenty largest areas:</p>' + areas_t + '<p>The full per-file data, with the functions each hunk changed, is <a href="../data/review.json">data/review.json</a> and <a href="../review/code/files.json">review/code/files.json</a>, derived from <code>git show</code> of the commit.</p>')}
{section("how", "How this was built", '<ul><li><b>The code layer</b> is derived by a parser from <code>git show -U0</code> of the fix commit: files, the functions each hunk falls in, the symbols the patch adds. Never a model, so it cannot invent a function that is not in the diff.</li><li><b>The remediation layer</b> is written from the commit message and the diff and checked against the two GitHub advisories; it is the one layer a person wrote, and it is marked as such.</li><li><b>The join</b> is the "realised in" edges from each remediation node to the files that carry it.</li><li>It follows the estate brief <a href="https://sgit.ai/docs/briefs/code-review-graphs-in-the-repository.html">Code review graphs in the repository</a>, at the smallest size that still maps a change to its code.</li></ul>')}
'''
    page('review/index.html', 'The fix, mapped to the code', 'The php2shell fix as layered graphs: the two flaws, the design of the patch, and the php-src files and functions it changed, derived from the diff.', body, kind='analysis', topics='php2shell code review')
    # the navigator
    body = f'''
<h1>Walk the graph</h1>
<p class="lead">The review graph in a navigator: the node in focus and its neighbours, laid out live, every node a link. Start at the fix and walk out to the flaws it closes or in to the files that carry it. The data is <a href="../../data/review.json">data/review.json</a>; the static map is <a href="../index.html">the fix mapped to the code</a>.</p>
<div id="rv" class="review-ui"><noscript>The navigator needs JavaScript. The same graph is on <a href="../index.html">the fix mapped to the code</a>.</noscript></div>
<script src="../../assets/review-nav.js" defer></script>
'''
    page('review/ui/index.html', 'Walk the graph: the fix and the code', 'A navigator over the php2shell review graph: the fix, the flaws it closes, and the files and functions it changed, each a link.', body, kind='evidence', topics='php2shell code review navigator')


# ----------------------------------------------------------------------------- articles and layers (v0.2.6)

def article_inline(s, depth):
    """Inline markdown for articles: [[slug, slug]] citations, [text](/site/path) links, `code`, bold, italic."""
    s = E(s, quote=False)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', lambda m: '<span class="refs">' + src_links([x.strip() for x in m.group(1).split(',')], depth) + '</span>', s)
    # the path was escaped with the rest of the line: unescape it to check it (a view address carries &), escape it once
    s = re.sub(r'\[([^\]]+)\]\(/([^)]*)\)', lambda m: f'<a href="{"../" * depth}{E(html.unescape(m.group(2)))}">{m.group(1)}</a>' if re.fullmatch(r'[A-Za-z0-9/._#=:&,%-]*', html.unescape(m.group(2))) else m.group(0), s)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)\s"<>]+)\)', r'<a href="\2" rel="noopener">\1</a>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', s)
    return s

def png_size(path):
    """Width and height from a PNG's IHDR chunk, so the page reserves the space before the image arrives."""
    with open(path, 'rb') as f:
        head = f.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        sys.exit(f'{path}: not a PNG')
    return int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')

def article_figure(alt, path, caption, depth):
    """![alt](/assets/articles/<slug>/<file>.png "caption"): a screenshot in an article. The image must be in the
    repository under assets/articles/; the build stops on a missing one."""
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        sys.exit(f'article figure missing: {path}')
    w, h = png_size(full)
    cap = f'<figcaption>{article_inline(caption, depth)}</figcaption>' if caption else ''
    return f'<figure class="shot"><img src="{"../" * depth}{E(path)}" alt="{E(alt)}" width="{w}" height="{h}" loading="lazy">{cap}</figure>'

def article_img(path, depth, cls, alt):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        sys.exit(f'article figure missing: {path}')
    w, h = png_size(full)
    return f'<img class="{cls}" src="{"../" * depth}{E(path)}" alt="{E(alt)}" width="{w}" height="{h}" loading="lazy">'

IMG_PATH = r'/(assets/articles/[a-z0-9-]+/[a-z0-9-]+\.png)'

def article_split(m, depth):
    """!split[before caption](/assets/...png)[after caption](/assets/...png): the old and the new side by side."""
    side = lambda tag, label, cap, path: (f'<figure class="ba-side"><span class="ba-tag ba-{tag}">{label}</span>{article_img(path, depth, "", label + ": " + re.sub(r"[*`]", "", cap))}'
                                          f'<figcaption>{article_inline(cap, depth)}</figcaption></figure>')
    return f'<div class="ba-split ba-wide">{side("before", "Before", m.group(1), m.group(2))}{side("after", "After", m.group(3), m.group(4))}</div>'

def article_slider(m, depth):
    """!slider[what it shows](/assets/before.png)(/assets/after.png) "commentary": one stage, a slider that fades (or wipes)
    from before to after, the commentary beside it. Without JavaScript the two images show one above the other."""
    parts = m.group(1).split('|')
    alt, l_old, l_new = parts[0], (parts[1] if len(parts) > 2 else 'Before'), (parts[2] if len(parts) > 2 else 'After')
    old, new, note = m.group(2), m.group(3), m.group(4) or ''
    for p in (old, new):
        if png_size(os.path.join(ROOT, p)) != png_size(os.path.join(ROOT, old)):
            sys.exit(f'article slider: {old} and {new} are not the same size')
    return (f'<figure class="ba-slider ba-wide"><div><div class="ba-stage" data-ba>'
            f'<span class="ba-cap"><span class="ba-tag ba-before">{E(l_old)}</span></span>{article_img(old, depth, "ba-old", l_old + ": " + alt)}'
            f'<span class="ba-cap"><span class="ba-tag ba-after">{E(l_new)}</span></span>{article_img(new, depth, "ba-new", l_new + ": " + alt)}</div>'
            f'<div class="ba-ctl" data-ba-ctl data-left="{E(l_old)}" data-right="{E(l_new)}"></div></div>'
            f'<figcaption class="ba-note">{"".join(f"<p>{article_inline(x.strip(), depth)}</p>" for x in note.split(" // ") if x.strip())}</figcaption></figure>')

def article_diff(lines):
    cls = lambda l: 'd-add' if l.startswith('+') else 'd-del' if l.startswith('-') else 'd-ctx'
    return '<pre class="diff">' + ''.join(f'<span class="{cls(l)}">{E(l) or " "}</span>' for l in lines) + '</pre>'

def render_article(text, depth):
    out, lst, rows = [], None, []
    diff, has_slider = None, False
    def flush():
        if rows:
            out.append(table([article_inline(c, depth) for c in rows[0]], [[article_inline(c, depth) for c in r] for r in rows[1:]])); rows.clear()
    for line in text.splitlines():
        if diff is not None:
            if line.strip() == '```':
                out.append(article_diff(diff)); diff = None
            else:
                diff.append(line)
            continue
        if line.strip() == '```diff':
            flush()
            if lst:
                out.append(f'</{lst}>'); lst = None
            diff = []
            continue
        sp = re.match(r'^!split\[([^\]]+)\]\(' + IMG_PATH + r'\)\[([^\]]+)\]\(' + IMG_PATH + r'\)\s*$', line)
        sl = re.match(r'^!slider\[([^\]]+)\]\(' + IMG_PATH + r'\)\(' + IMG_PATH + r'\)(?:\s+"([^"]*)")?\s*$', line)
        if sp or sl:
            flush()
            if lst:
                out.append(f'</{lst}>'); lst = None
            out.append(article_split(sp, depth) if sp else article_slider(sl, depth))
            has_slider = has_slider or bool(sl)
            continue
        if line.strip().startswith('|'):
            if lst:
                out.append(f'</{lst}>'); lst = None
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not all(re.match(r'^:?-+:?$', c) for c in cells):
                rows.append(cells)
            continue
        flush()
        fig = re.match(r'^!\[([^\]]+)\]\(/(assets/articles/[a-z0-9-]+/[a-z0-9-]+\.png)(?:\s+"([^"]*)")?\)\s*$', line)
        if fig:
            if lst:
                out.append(f'</{lst}>'); lst = None
            out.append(article_figure(fig.group(1), fig.group(2), fig.group(3) or '', depth))
            continue
        m = re.match(r'^(#{2,4})\s+(.*)$', line)
        item = re.match(r'^(?:-|\d+\.)\s+(.*)$', line)
        kind = ('ol' if re.match(r'^\d+\.', line) else 'ul') if item else None
        if lst and kind != lst:
            out.append(f'</{lst}>'); lst = None
        if m:
            out.append(f'<h{len(m.group(1))}>{article_inline(m.group(2), depth)}</h{len(m.group(1))}>')
        elif item:
            if not lst:
                out.append(f'<{kind}>'); lst = kind
            out.append(f'<li>{article_inline(item.group(1), depth)}</li>')
        elif line.strip():
            out.append(f'<p>{article_inline(line, depth)}</p>')
    flush()
    if lst:
        out.append(f'</{lst}>')
    if diff is not None:
        sys.exit('article: a ```diff block is not closed')
    if has_slider:
        out.append(f'<script src="{"../" * depth}assets/compare.js" defer></script>')
    return '\n'.join(out)

def article_stamp(a):
    return f'site v{E(a["as_of_version"])} &middot; vault commit <code>{E(a["vault_commit"])}</code> &middot; data as of {E(a["data_as_of"])}'

def stories_row():
    cards = ''.join(f'<a class="door" href="articles/{E(a["slug"])}/index.html"><b>{E(a["title"])}</b><span>{E(ORIGINS[a["origin"]]["short"])} story &middot; {E(AUTHOR_ROLES.get(a["role"], a["role"]))} &middot; {E(a["written"])}</span></a>' for a in ARTICLES[:3])
    cards += f'<a class="door" href="interview/index.html"><b>{E(D["interview"]["title"])}</b><span>Interview &middot; the editor, in his own words</span></a>'
    return f'<div class="doors">{cards}</div><p><a href="articles/index.html">All stories &rarr;</a></p>'

def articles_row():
    if not ARTICLES:
        return ''
    cards = ''.join(f'<a class="door" href="articles/{E(a["slug"])}/index.html"><b>{E(a["title"])}</b><span>{E(AUTHOR_ROLES.get(a["role"], a["role"]))} &middot; {E(a["written"])} &middot; written against v{E(a["as_of_version"])}</span></a>' for a in ARTICLES[:4])
    return section('articles', 'Articles, signed and dated', f'<div class="doors">{cards}</div><p><a href="articles/index.html">All articles &rarr;</a> The pages of this site are rebuilt from the vault on every release; an article is written once, against the evidence as it stood, and says which version that was.</p>')

def build_articles():
    for a in ARTICLES:
        role = AUTHOR_ROLES.get(a['role'], a['role'])
        moved = '' if a['data_as_of'] >= STORY['data_as_of'] else f'<p class="caveat"><b>The evidence has moved since this was written.</b> This article was written against data as of {E(a["data_as_of"])}; the site now has data as of {E(STORY["data_as_of"])}. The <a href="../../index.html">front page</a> and <a href="../../claims/index.html">every claim</a> are current; this article is kept as written.</p>'
        others = ''.join(f'<li><a href="../{E(b["slug"])}/index.html">{E(b["title"])}</a> <span class="small">{E(AUTHOR_ROLES.get(b["role"], b["role"]))}, {E(b["written"])}</span></li>' for b in ARTICLES if b is not a)
        cited = section("cited", "Sources cited", f'<p>{len(a["cites"])} captured sources, in the order this article first cites them. Each opens on its page with its capture times and hashes.</p><p class="refs">{src_links(a["cites"], 2)}</p>')
        more = section("more", "Other articles", f'<ul>{others}</ul>') if others else ''
        body = f"""
<article class="piece">
<p class="kicker">Story &middot; {E(ORIGINS[a["origin"]]["short"])} &middot; {E(role)} &middot; {E(a["written"])}</p>
<h1>{E(a["title"])}</h1>
<p class="lead">{E(a["dek"])}</p>
<p class="kv"><b>By</b> the {E(role.lower())} {"roles, agents" if "," in a["author"] else "role, agent"} <code>{E(a["author"])}</code> &middot; <b>written against</b> {article_stamp(a)}</p>
{moved}
{''.join(f'<div class="caveat correction" id="correction-{k[10:]}"><p><b>Correction, {E(human_time(v.split(" | ", 1)[0]))}.</b> {E(v.split(" | ", 1)[1])}</p></div>' for k, v in sorted(a.items()) if re.match(r'^correction\d+$', k))}
{render_article(a["text"], 2)}
</article>
{cited}
{more}
<p class="small">Source file: <code>admin/content/articles/{E(a["file"])}</code>, in the authored layer; see <a href="../../layers/index.html">evidence, derived, authored</a>.</p>
"""
        page(f'articles/{a["slug"]}/index.html', a['title'], a['dek'], body, kind='article', date=a['written'], topics=f'php2shell {a["role"]}', ld_type='NewsArticle', origin=a['origin'], byline=f'By the {role.lower()} {"roles, agents" if "," in a["author"] else "role, agent"} {a["author"]}')
    def card(a):
        return f'<article class="rel">{it_story(a)}<h3><a href="{E(a["slug"])}/index.html">{E(a["title"])}</a></h3><p>{E(a["dek"])}</p><p class="small">{E(ORIGINS[a["origin"]]["short"])} &middot; {E(AUTHOR_ROLES.get(a["role"], a["role"]))} &middot; {E(a["written"])} &middot; <code>{E(a["author"])}</code> &middot; {article_stamp(a)} &middot; {len(a["cites"])} sources cited</p></article>'
    house = ''.join(card(a) for a in ARTICLES if a['origin'] == 'house')
    guests = ''.join(card(a) for a in ARTICLES if a['origin'] == 'guest') or '<p>None yet. A guest writer or interviewer sends a piece to the editor; it is published here under their own name, marked <b>Guest</b> on every page, with the same rule as everything else: a fact names its source. Opinion is theirs and says so.</p>'
    iv = D['interview']
    interviews = ''.join(card(a) for a in ARTICLES if a['origin'] == 'interview') + f'<article class="rel"><h3><a href="../interview/index.html">{E(iv["title"])}</a></h3><p>{E(iv["description"])}</p><p class="small">Interview &middot; the editor\'s own words, quoted verbatim</p></article>'
    body = f"""
<h1>Stories: written here</h1>
<p class="lead">This site has two halves. <b>Research</b> is material collected from outside (agencies, researchers, vendors, the press, other models, other websites) and what this site derives from it: claims with a status, the timeline, the numbers. It is rebuilt from the evidence on every release. <b>Stories</b> are written here: reporting, analysis, opinion and interviews, each signed and dated, and kept as written. A story says which version of the evidence it was written against, so a reader can see what was known when.</p>
<p>Every page on the site says at its top which half it belongs to. In a story, a fact still carries its source; a judgement is the writer's, and says so.</p>
{section("house", "House stories", f'<p>Written by this site\'s own roles: the <b>journalist</b> reports and follows the second stories; the <b>historian</b> sets events against what came before.</p>{house}')}
{section("interviews", "Interviews", interviews)}
{section("guests", "Guest writers and interviewers", guests)}
"""
    page('articles/index.html', 'Stories: written here, signed and dated', f'{len(ARTICLES)} stories about the PHP flaws written for this site, plus the editor\'s interview: house stories by the journalist and historian, interviews, and guest pieces, each pinned to the evidence it was written against.', body, kind='site')

def build_layers():
    L = D['layers']
    names = {l['id']: l['name'] for l in L['layers']}
    def link(f):
        u = f.get('used_on')
        return f'<a href="../{E(u)}">{E(u)}</a>' if u else ''
    out = ''
    for l in L['layers']:
        rows = [[f'<code>{E(f["path"])}</code>', E(f['by']), E(f['from']), link(f)] for f in L['files'] if f['layer'] == l['id']]
        out += section('l-' + l['id'], l['name'], table(['File', 'Made by', 'From', 'Shown on'], rows), f'{E(l["what"])} <b>Rule.</b> {E(l["rule"])}')
    counts = Counter(f['layer'] for f in L['files'])
    tally = ' &middot; '.join(f'<b>{counts[l["id"]]}</b> {E(names[l["id"]].lower())}' for l in L['layers'])
    body = f"""
<h1>Evidence, derived, authored</h1>
<p class="lead">This site mixes kinds of material, and a reader should always be able to tell which one they are looking at. {E(L["note"])}</p>
<p class="kv">{tally}</p>
<ul>
<li><b>Evidence</b> answers <i>what was captured?</i> The pages that show it are <a href="../sources/index.html">every source</a>, <a href="../affected/software.html">the software inventory</a> and <a href="../admin/vault/index.html">the vault, opened</a>.</li>
<li><b>Derived</b> answers <i>what does the evidence say?</i> The story pages and the analysis (<a href="../claims/index.html">claims</a>, <a href="../numbers/index.html">numbers</a>, <a href="../agencies/index.html">agencies</a>) are built from it, and change when it changes.</li>
<li><b>Authored</b> answers <i>what did someone conclude, and when?</i> <a href="../articles/index.html">Articles</a> and <a href="../brief/index.html">the brief</a> are signed and dated.</li>
</ul>
{out}
<p>The classification is <a href="../data/layers.json">data/layers.json</a>; the gate fails a release if a file in <code>data/</code> is missing from it.</p>
"""
    page('layers/index.html', 'Evidence, derived, authored: what each file is', 'Every file this site is built from, sorted into evidence captured from the vault, transformations derived by agents, signed and dated articles, and the files that run the site.', body, kind='site')


# ----------------------------------------------------------------------------- questions, kept by the librarian (v0.2.6)

def q_link(path, depth):
    """A site page as a link with its own title, so a question points at pages, not paragraphs."""
    bare = path.split('#')[0]
    title = next((t for p, t, _, _ in PAGES if p == bare), None) or next((t for _, items in NAV for p, t in items if p == bare), bare)
    return f'<a href="{"../" * depth}{E(path)}">{E(title)}</a>'

def q_inline(text):
    """An answer's authored text: everything escaped with E(), then only <b>, <i>, <code> and <q> restored, with no
    attributes. Until 25 October the answers were inserted raw (found by the librarian's appsec self-check)."""
    return re.sub(r'&lt;(/?)(b|i|code|q)&gt;', r'<\1\2>', E(text))

def build_questions():
    Q = D['questions']
    qs = Q['questions']
    lib = Q['librarian']
    for i, q in enumerate(qs):
        paras = ''.join(f'<p>{q_inline(a["html"])} <span class="refs">{src_links(a["sources"], 2)}</span></p>' for a in q['answer'])
        who = table(['If', 'Then'], [[E(w['if']), q_inline(w['then'])] for w in q['who']]) if q.get('who') else ''
        see = ''.join(f'<li>{q_link(p, 2)}</li>' for p in q['see'])
        nxt = qs[(i + 1) % len(qs)]
        url = f'{BASE_URL}/questions/{q["id"]}/index.html'
        body = f'''
<p class="kicker">Question &middot; kept by the {E(lib["name"].lower())} &middot; <code>{E(lib["address"])}</code></p>
<h1>{E(q["q"])}</h1>
<p class="small">How it was asked: {E(q["heard"])}</p>
{section("short", "The short answer", f'<p class="lead">{E(q["short"])}</p><p class="small">To paste back where it was asked: the paragraph above and <code>{E(url)}</code></p>')}
{section("who", "What it means for you", who) if who else ""}
{section("why", "The answer, with its sources", paras)}
{section("see", "The pages that carry it", f'<ul>{see}</ul>')}
<p>Next question: <a href="../{E(nxt["id"])}/index.html">{E(nxt["q"])}</a> &middot; <a href="../index.html">every question</a>. Nothing here is advice for your environment; the <a href="https://www.php.net/archive/2026.php#2026-10-21-5" rel="noopener">php.net advisory</a> and your national agency are the authorities.</p>
'''
        page(f'questions/{q["id"]}/index.html', q['q'], q['short'], body, kind='story', topics='php2shell questions')
    rows = [[f'{it_question(q)}<a href="{E(q["id"])}/index.html"><b>{E(q["q"])}</b></a>', E(q['short']), ' '.join(q_link(p, 1) for p in q['see'][:3])] for q in qs]
    seen = table(['Seen', 'What', 'State', 'Answered by'], [[E(x['seen']), f'<b>{E(x["publisher"])}</b>: <a href="{U(x["url"])}" rel="noopener nofollow">{E(x["title"])}</a><div class="note">{E(x["standfirst"])}</div>', E(x['state']), '<br>'.join(f'<a href="{E(a)}/index.html">{E(next(q["q"] for q in qs if q["id"] == a))}</a>' for a in x['answered_by'])] for x in Q['seen']])
    catalogue = ''
    for label, items in NAV:
        if label == 'Questions':
            continue
        lis = ''.join(f'<li>{q_link(p, 1)}: {E(next((d for pp, _, d, _ in PAGES if pp == p), ""))}</li>' for p, _ in items)
        catalogue += f'<h3>{E(label)}</h3><ul class="small">{lis}</ul>'
    body = f'''
<h1>Questions readers ask</h1>
<p class="lead">The questions people ask about php2shell when they see the headline, each with a short answer that can be pasted back where it was asked, the longer answer with its sources, and the pages that carry it. Kept by the {E(lib["name"].lower())}, <code>{E(lib["address"])}</code>: {E(lib["beat"])}.</p>
{section("questions", "The questions", table(['Question', 'The short answer', 'Read'], rows, 'claims'))}
{section("seen", "Seen by readers, not yet in the vault", seen + '<p class="small">An article a reader has seen is listed here until a collector captures it into the evidence vault. Until then it is not cited anywhere on this site; the answers above rest on what is captured.</p>')}
{section("catalogue", "The catalogue: every page, and what it answers", catalogue + '<p class="small">Every page also has a markdown twin, listed in <a href="../llms.txt">llms.txt</a>; the questions themselves are <a href="../data/questions.json">data/questions.json</a>.</p>')}
{section("ask", "Asking a new question", f'<p>{E(lib["rule"])} A question that is asked twice gets a page. The librarian\'s role, rules and the mistake behind them are on <a href="../team/index.html#librarian">the team page</a>.</p>')}
'''
    page('questions/index.html', 'Questions readers ask about php2shell', 'Can anything be done or do we wait for updates? Has anyone been hacked? Is it really most websites? Short answers to paste back, the sources behind them, and the pages that carry each one.', body, kind='story', topics='php2shell questions faq')


# ----------------------------------------------------------------------------- second readings: other models, checked against the vault (v0.2.10)

def build_readings():
    R = D['readings']
    verdicts = {v['id']: v for v in R['verdicts']}
    claim_ids = {c['id'] for c in D['claims']}
    out = ''
    for r in R['readings']:
        tally = Counter(x['verdict'] for x in r['rows'])
        rows = [[f'<b>{E(x["point"])}</b><div class="note">section {E(x["section"])}</div>', E(x['found']), pill(verdicts[x['verdict']]['name']),
                 E(x['vault']) + ('<div class="note">' + ', '.join(f'<a href="../claims/index.html#{E(c)}">{E(c)}</a>' for c in x['claims'] if c in claim_ids) + '</div>' if x['claims'] else ''),
                 src_links(x['sources'], 1)] for x in r['rows']]
        leads = ''.join(f'<li><a href="{U(l["url"])}" rel="noopener nofollow">{E(l["what"])}</a> <span class="small">{E(l["priority"])}</span></li>' for l in r['leads'])
        out += section(r['id'], f'{E(r["model"])}: {E(r["title"])}', f'''<p>{E(r["how"])} <a href="{E(r["id"])}/index.html">The notes in full &rarr;</a></p>
<p class="kv">{" &middot; ".join(f"<b>{tally[v['id']]}</b> {E(v['name'])}" for v in R["verdicts"] if tally[v["id"]])}</p>
{table(["Point", f"What {E(r['model'])} found", "Against the vault", "What the vault holds", "Sources"], rows, "claims")}
<h3>Sources {E(r["model"])} named that the vault has not captured</h3>
<p>Listed for the collectors, in the order they should be captured. None is cited on this site until it is captured; this list is the whole of what they are used for.</p>
<ul>{leads}</ul>''')
        notes = render_md_file(r['file'])
        body = f'''
<p class="kicker">Second reading &middot; by {E(r["model"])} &middot; compiled {E(r["compiled"])}</p>
<div class="caveat"><p><b>This page is {E(r["model"])}'s text, not this site's.</b> {E(r["how"])} It is published in full and unedited, credited to {E(r["model"])}, from <code>{E(r["file"])}</code>. Its links go to the open web; none of its sources is cited by this site until a collector has captured it. Where it agrees or disagrees with the evidence vault is on <a href="../index.html#{E(r["id"])}">second readings</a>.</p></div>
<div class="memo">{notes}</div>
'''
        page(f'readings/{r["id"]}/index.html', f'{r["model"]}\'s notes on php2shell, in full', f'{r["title"]}: the notes {r["model"]} compiled on {r["compiled"]}, published in full and credited, with the comparison against the evidence vault one page up.', body, kind='evidence', topics=f'php2shell {r["model"].lower()} second reading')
    legend = '<ul class="legend">' + ''.join(f'<li>{pill(v["name"])} {E(v["what"])}</li>' for v in R['verdicts']) + '</ul>'
    body = f'''
<h1>Second readings: other models, checked against the vault</h1>
<p class="lead">The editor's first memo asked for more than one model to read this story. The vault was read by Claude agents; this page sets readings by other models beside it, point by point. Each other model's text is published in full and credited, and nothing in it is cited on this site until a collector has captured its source.</p>
{legend}
{out}
<p class="small">The comparison rows are <a href="../data/readings.json">data/readings.json</a>, in the derived layer; the other models' text is in the authored layer (<a href="../layers/index.html">evidence, derived, authored</a>). The gate checks every source and claim a row cites.</p>
'''
    page('readings/index.html', 'Second readings: other models, checked against the vault', 'Another model\'s notes on php2shell, published in full and credited, set beside the evidence vault point by point: where they agree, where the vault resolves or goes further, and the new leads for capture.', body, kind='analysis', topics='php2shell second reading models')


# ----------------------------------------------------------------------------- the pipeline (v0.2.12)

def build_status():
    P = D['pipeline']
    cfg = J({'api': P['api'], 'sites': P['sites']}, sort_keys=True, separators=(',', ':'))
    cards = ''.join(f"""
<section id="{E(x["id"])}" class="pl-site">
<h2><a href="{E(x["site"])}">{E(x["name"])}</a></h2>
<p class="kv"><a href="https://github.com/{E(x["repo"])}/actions/workflows/{E(x["workflow"])}"><span class="pl-badge" data-badge="https://github.com/{E(x["repo"])}/actions/workflows/{E(x["workflow"])}/badge.svg?branch={E(x["branch"])}">the deploy workflow's runs on GitHub</span></a> &middot; repository <a href="https://github.com/{E(x["repo"])}"><code>{E(x["repo"])}</code></a> &middot; branch <code>{E(x["branch"])}</code> &middot; served version <a href="{E(x["site"])}VERSION"><code>{E(x["site"])}VERSION</code></a></p>
<div id="pl-{E(x["id"])}"><div class="pl-live"><p class="small">Reading GitHub&hellip; (this part and the badge need JavaScript; the links above do not)</p></div></div>
</section>""" for x in P['sites'])
    body = f"""
<h1>The pipeline: what is live, what is deploying</h1>
<p class="lead">Several agents release to these sites. Each push to <code>dev</code> starts a GitHub Actions run that runs the gate and deploys to GitHub Pages. This page reads those runs from GitHub's public API in your browser, with no credential anywhere: the repositories are public, and so is everything below. Beside each site's runs is the version that site serves now, read from its own <code>VERSION</code> file.</p>
<p><button id="pl-refresh" type="button">Refresh now</button> <span id="pl-rate" class="small"></span></p>
{cards}
<h2>How to read it</h2>
<ul>
<li><span class="st st-confirmed">deployed</span> the run passed the gate and published its commit. The row marked <b>&#9664; live</b> is the version the site serves.</li>
<li><span class="st st-reported">deploying</span> <span class="st st-reported">queued</span> in the pipeline now. Deploys never cut each other off: a started deploy finishes, then the newest waiting push goes.</li>
<li><span class="st">superseded</span> GitHub keeps one waiting run per site; a push overtaken while it waited is cancelled, and the newer run behind it ships its commit too. Nothing is lost.</li>
<li><span class="st st-failed">failed</span> the gate or the deploy failed; the site keeps serving the last good release. <span class="st st-unverified">cancelled</span> cancelled with nothing newer behind it: the next push or a re-run deploys.</li>
</ul>
<p>Every page of this site also checks, once, whether the site now serves a newer release than the page in front of you, and says so beside the version in the bar.</p>
<h2>What it costs and what it shows</h2>
<p>{E(P["about"])} GitHub allows {E(P["anonymous_limit"])}; this page spends one call per site per refresh: every five minutes, every twenty seconds for a site with a run in flight, and none while the tab is hidden. The badges are images GitHub serves, loaded by the same script, and do not count. Commit messages, run numbers and the agent named in a commit's <code>Agent:</code> line are public on GitHub already; this page shows them, and sends nothing anywhere else.</p>
<p>For agents: <code>admin/build/release.sh "&lt;what changed and why&gt;"</code> takes in whatever other agents released before it bumps, and if its push loses a race it takes that in too and releases again on top, so two agents can release minutes apart without either push being rejected or either deploy being lost. The list of the sites read here is <a href="../data/pipeline.json">data/pipeline.json</a>.</p>
<script type="application/json" id="pipeline-config">{cfg}</script>
<script src="../assets/pipeline.js" defer></script>
"""
    page('status/index.html', 'The pipeline: what is live, what is deploying', 'Each newsroom site\'s deploy runs, read in your browser from GitHub\'s public API with no credential, beside the version the site serves now: what is live, what is deploying, what was superseded, what failed.', body, kind='site')


# ----------------------------------------------------------------------------- the vaults (v0.2.13)

def vault_open_url(read_key):
    """The official UI's read-only link for a published read key: the key travels in the fragment, never to a server."""
    rk, vid = read_key.rsplit(':', 1)
    return f'https://dev.vault.sgraph.ai/en-gb/#{rk}%3A{vid}'

def vault_note(read_key):
    """The note box every published vault gets on sgit.ai: the key, the link that opens it, the clone command."""
    return f"""<div class="vnote"><b>Open it yourself. The read key is the whole credential, and it is published on purpose.</b><br>
Read key: <code>{E(read_key)}</code><br>
In the official UI: <a href="{E(vault_open_url(read_key))}" rel="noopener" target="_blank">open it read-only in a new tab &#8599;</a> &middot; From the command line: <code>sgit clone {E(read_key)}</code><br>
<span class="small">A read key decrypts and cannot write; it is derived one way from the vault key, which is not published and never will be.</span></div>"""

def vault_live(read_key, app, depth, lead):
    """The embedded vault: the official SG/Vault UI in a frame, handed the read key over postMessage (assets/vendor/vault-ui-embed.js)."""
    rk, vid = read_key.rsplit(':', 1)
    up = '../' * depth
    return f"""<h2>See it live, here</h2>
<p class="openrow"><a class="btn-open" href="{E(vault_open_url(read_key))}" rel="noopener" target="_blank">Open the vault in a new tab &#8599;</a> <span class="small">{lead}</span></p>
<div class="sgv-uiembed" data-vault="{E(vid)}" data-readkey="{E(rk.replace("sgit_public_read_", ""))}" data-app="{1 if app else 0}"></div>
<script src="{up}assets/vendor/vault-ui-embed.js" defer></script>"""

def build_vaults():
    VS = D['vaults']['vaults']; W = D['source-watch']; ev = D['admin']['evidence_vault']; vt = D['vault']; tl = D['telemetry']
    keys = {'evidence': ev['read_key'], 'source-watch': W.get('read_key'), 'schedule': load('schedule-vault')['read_key']}
    facts = {'evidence': f'{vt["sources"]} sources, {vt["captures"]} captures, {vt["hashed_files"]} hashed files; head <code>{E(vt["head"]["commit"] or "")}</code>',
             'source-watch': f'{W["pages"]} pages from {W["publishers"]} publishers in {len(W["country"])} countries and {len(W["lang"])} languages; {W["snapshots"]} snapshots, {len(W["runs"])} runs, as of the export of 23 October 2026',
             'telemetry': f'lane <code>{E(tl["vault_id"])}</code> on <code>{E(tl["endpoint"])}</code>; events encrypted to <code>{E(tl["recipient"]["fingerprint"])}</code>',
             'subscriptions': f'lane <code>{E(D["subscriptions"]["vault_id"])}</code> on <code>{E(D["subscriptions"]["endpoint"])}</code>; requests encrypted to <code>{E(D["subscriptions"]["recipient"]["fingerprint"])}</code>'}
    lanes = {'telemetry': tl['append_token'], 'subscriptions': D['subscriptions']['append_token'], 'collaborators': load('collaborators')['lane']['append_token']}
    cards = ''
    for x in VS:
        k = keys.get(x['slug']) or x.get('read_key')
        how = (f'<p class="kv"><b>Not published:</b> the vault key. {E(x.get("note", ""))}</p>' if not k and x['slug'] not in lanes else f'<p class="kv"><b>Read key</b> <code>{E(k)}</code></p><p><a href="{E(vault_open_url(k))}" rel="noopener" target="_blank">Open read-only in a new tab &#8599;</a> &middot; <code>sgit clone {E(k)}</code></p>' if k else
               f'<p class="kv"><b>Not published:</b> the vault key, the lane\'s enum key and the key pair\'s passphrase. <b>Published:</b> the write-only append token <code>{E(lanes.get(x["slug"], ""))}</code>, which adds rows and reads nothing.</p>')
        cards += f"""<section class="vcard" id="{E(x["slug"])}">
<h2><a href="../{E(x["page"])}">{E(x["name"])}</a> <span class="st {'st-confirmed' if k else ''}">{E(x["access"])}</span></h2>
<p class="kv"><b>Vault</b> <code>{E(x["id"])}</code> &middot; {facts.get(x["slug"], E(x.get("facts", "")))}{' &middot; opens in its own app' if x["app"] else ''}</p>
<p>{E(x["holds"])}</p>
<p class="small"><b>Written by</b> {E(x["writers"])}. Data on this site: <a href="../{E(x["data"])}">{E(x["data"])}</a>.</p>
{how}
</section>"""
    body = f"""
<h1>The vaults behind this site</h1>
<p class="lead">This site is rebuilt from vaults, never written by hand. {len(VS)} vaults sit behind it. Two are public and open read-only in your browser with the keys below (the evidence, and the public face of the telemetry, its curated counts); one, the source watch, is a pack-mode vault, private until the vault UI can open pack vaults; two are private and receive through write-only lanes, one the site's anonymous telemetry, one subscription requests; one is private and is an application only, the telemetry app, versioned in its own vault, which the telemetry vault links inside itself and opens as its dashboard (an earlier dashboard vault, linked the other way round, is superseded); one is private and never published, because it holds other people's pages; and three are the team's own, private, through which <a href="../team/channels/index.html">the team talks</a>: the conductor vault, the issues and the mail. Every vault is encrypted in the client; the server that stores it holds ciphertext and nothing else.</p>
<div class="caveat"><p>{E(D["vaults"]["about"])}</p></div>
{cards}
<p class="small">The list is <a href="../data/vaults.json">data/vaults.json</a>. The other vaults of the sgit.ai network, published the same way, are at <a href="https://sgit.ai/demos/vaults/index.html">sgit.ai's vaults</a>.</p>
"""
    page('vaults/index.html', 'The vaults behind this site', 'Every vault this site is built from: the evidence vault and the source watch, both public with their read keys, and the private telemetry vault with its write-only lane; what each holds, who writes to it and how to open it.', body, kind='site')

    # the source watch, published the way sgit.ai publishes a vault
    acc = {a['id']: a['means'] for a in W['access_classes']}
    sect = {x['id']: x['name'] for x in W['sectors']}
    stats = ''.join(stat(n, l) for n, l in [(W['pages'], 'pages watched'), (W['publishers'], 'publishers'), (len(W['country']), 'countries'), (len(W['lang']), 'languages'),
                                            (W['snapshots'], 'snapshots kept'), (W['graphs'], 'graphs'), (len(W['runs']), 'runs'), (W['files'], 'files in the vault')])
    top_c = table(['Country', 'Pages'], [[f'<code>{E(c)}</code>', str(n)] for c, n in sorted(W['country'].items(), key=lambda kv: (-kv[1], kv[0]))[:12]])
    top_s = table(['Sector', 'Pages'], [[f'<code>{E(c)}</code> {E(sect.get(c, ""))}', str(n)] for c, n in sorted(W['sector'].items(), key=lambda kv: (-kv[1], kv[0]))])
    acc_t = table(['Access', 'Pages', 'Means'], [[pill(k) if k in STATUS_WORDS else f'<code>{E(k)}</code>', str(W['access'].get(k, 0)), E(m)] for k, m in acc.items()])
    tiers = {'A': 'open or public-sector: keep and show', 'B': 'quote up to 25 words and link', 'C': 'link only'}
    tier_t = table(['Tier', 'Publishers', 'What a site page may show'], [[f'<b>{t}</b>', str(W['tiers'].get(t, 0)), E(w)] for t, w in tiers.items()])
    alt_t = table(['Altitude', 'What it describes'], [[f'<b>{E(k)}</b>', E(v if isinstance(v, str) else json.dumps(v))] for k, v in W['altitudes'].items()])
    runs_t = table(['Run (UTC)', 'Due', 'Watched', 'Changed', 'Access'], [[f'<code>{E(r["run"])}</code>', str(r['pages_due']), str(r['pages_total']), str(r['changed']),
                    ', '.join(f'{E(k)} {n}' for k, n in sorted((r.get('access') or {}).items(), key=lambda kv: -kv[1]))] for r in reversed(W['runs'])])
    tips = ''.join(f"""<article class="rel"><p class="kicker">Tip {E(t["id"])} &middot; received {E(t["received"] or "")} &middot; {pill(t["status"] or "unverified")}</p>
<p>{E(t["says"] or "")}</p><p class="small"><b>Watched as</b> {", ".join(f"<code>{E(w)}</code>" for w in t["watched_as"])}. <b>To check:</b> {"; ".join(E(c) for c in t["to_check"])}.</p></article>""" for t in W['tips'])
    SWV = next(x for x in D['vaults']['vaults'] if x['slug'] == 'source-watch')
    shot = 'assets/vaults/source-watch.png'  # captured from the official UI with the read key; the figure appears once it is in the repository
    hero = (f"""<figure class="shot"><a href="{E(vault_open_url(W["read_key"]))}" rel="noopener" target="_blank"><img src="../../{shot}" alt="The source-watch vault open in the official SG/Vault UI, read-only." width="1280" height="800" loading="eager"></a>
<figcaption>The vault in the official UI, opened read-only with the published key. <b>Click the image to open the real one &#8599;</b></figcaption></figure>""" if W.get('read_key') and os.path.exists(os.path.join(ROOT, shot)) else '')
    body = f"""
<p class="crumb"><a href="../index.html">Vaults</a> / The source watch</p>
<h1>The source watch: every outside source on php2shell, watched and snapshotted</h1>
<p class="lead">A vault that does one thing. It watches every outside source on the story, {W["pages"]} pages from {W["publishers"]} publishers in {len(W["country"])} countries, and on each run records what access it had and keeps a new snapshot whenever the content changed: the text, a screenshot, the HTML as served and as rendered, the headers and the sha256 of each, and a graph of what the page says and what changed since the last look. A small, focused Wayback Machine whose diffs are graphs. Run by <b>researcher@php.newsroom</b>.</p>
<div class="caveat"><p><b>Vault <code>{E(W["vault_id"])}</code>, in pack mode.</b> {E(SWV["note"])} The counts below are from the export of 23 October 2026, read before the watch moved into pack mode; the next export reads this vault. <a href="../../admin/pack-mode/index.html">Pack mode, measured</a>.</p></div>
{hero if W.get("read_key") else ""}
{vault_note(W["read_key"]) if W.get("read_key") else ""}
{"" if not W.get("read_key") else vault_live(W["read_key"], False, 2, f'The vault has no app of its own yet, so it opens in the vault browser. It holds {W["files"]:,} files; the browser decrypts the folder tree before it lists it, so the first open takes minutes. <code>sgit clone</code> is the fast way in.')}
<h2>What is in it</h2>
<div class="stats">{stats}</div>
<p class="small">Counts read from the watch's <code>index/counts.json</code>, <code>runs/</code> and <code>tips/</code> by <code>admin/build/export_watch.py</code>, in the export of 23 October 2026, before the move into pack mode; no capture is copied to this site. The latest commit read then: <q>{E(W["head"]["message"])}</q></p>

<h2>Raw and analysis are separate trees</h2>
<div class="wt-row"><div><p>Raw is what was served; analysis is what the watcher made of it, and it can be regenerated from raw plus the vocabularies plus the tools. That rule is how you tell the two apart. A snapshot in <code>raw/</code> is never edited or deleted: a new look at the page makes a new folder, and only when something changed. Every check, changed or not, is still a line in <code>checks/</code> with its status, access and hashes.</p></div>
<pre>sources/&lt;country&gt;/&lt;sector&gt;/&lt;publisher&gt;/&lt;page&gt;/page.json
raw/&lt;country&gt;/&lt;sector&gt;/&lt;publisher&gt;/&lt;page&gt;/&lt;UTC&gt;/
    text.txt  screenshot.jpg  page.html.gz  rendered.html.gz
    headers.json  meta.json  provenance.json
raw/.../&lt;page&gt;/checks/&lt;date&gt;.jsonl
graph/.../&lt;page&gt;/&lt;UTC&gt;.json   snapshot and change
runs/&lt;Y&gt;/&lt;M&gt;/&lt;D&gt;/&lt;HHMMSS&gt;/
    run.json  graph.json  changes.md
index/  state/  taxonomy/  tips/  tools/</pre></div>

<h2>Country, then sector, then publisher, then page</h2>
<p>Country is where the publisher is based (<code>eu</code> for EU institutions, <code>int</code> for publishers with no single home, such as php.net); language is a property of the page. Sector is what kind of organisation publishes it, one per publisher; it classifies the publisher, never a claim.</p>
<div class="cols">{top_c}{top_s}</div>

<h2>What we can and cannot read</h2>
<p>Every check classifies the answer it got. A page the watcher cannot read stays on the list: the challenge page's hash is the record, and the gap is published.</p>
{acc_t}
<p>Every publisher also has a licence tier, after the newsroom wires' sources policy. The vault keeps what was served either way; the tier governs what a site page shows of it.</p>
{tier_t}

<h2>Graphs: one grammar at every altitude</h2>
<p>Every graph in the vault uses the grammar in <code>taxonomy/verbs.json</code> ({W["verbs"]} verbs): an edge is a verb with a named inverse, and there is no generic association edge (<a href="https://graphs.sgit.ai/">graphs.sgit.ai</a>). The world graph alone has {W["world_graph"]["nodes"]} nodes and {W["world_graph"]["edges"]} edges. Entities (a CVE id, a PHP version, an organisation with this site's actor ids, a term with its translations) are where the altitudes join, and where the vault joins this site. What changed on a page is answered by a query over the change section, not by comparing two screenshots; the extractor is deterministic.</p>
{alt_t}

<h2>The runs</h2>
<p>A run captures the pages that are due: hourly for the story, daily for background pages about earlier incidents. Feeds and APIs are fetched without a browser; everything else goes through Chromium at 1280 wide. The first run was a diff against the evidence vault's morning captures, imported as this vault's first snapshots.</p>
{runs_t}

<h2>Tips</h2>
<p>A tip is a claim that reached the newsroom from outside, recorded with how it arrived, what it says, the pages added to watch it, and what has to be checked before anything on this site relies on it. Its status uses this site's words.</p>
{tips}

<h2>The tools</h2>
<p>The watcher is in the vault, next to what it wrote: {", ".join(f"<code>{E(t)}</code>" for t in W["tools"])}.</p>
<pre>python3 tools/watch.py run [--all] [--only &lt;text&gt;] [--limit N] [--commit] [--push]
python3 tools/discover.py scan            # feeds to candidate publishers
python3 tools/discover.py promote --limit 30
python3 tools/watch.py add &lt;url&gt; --cc gb --sector news --publisher bbc</pre>
<p class="small">The other vaults behind this site are on <a href="../index.html">the vaults</a>. The evidence vault, where the story was assembled by hand on the morning of 22 October, is <a href="../../admin/vault/index.html">opened here</a>.</p>
"""
    page('vaults/source-watch/index.html', 'The source watch: every outside source on php2shell, watched and snapshotted', f'The source-watch vault: {W["pages"]} pages from {W["publishers"]} publishers in {len(W["country"])} countries, re-read on a schedule, a snapshot kept on every change and every snapshot a graph. What is in it, and how it is watched.', body, kind='evidence', topics='php2shell vault source watch')

# ----------------------------------------------------------------------------- pages added in v0.3: the readers

def build_start():
    cols = ''.join(f'<div class="mh">{depth_badge(d)}<small>{E(DEPTHS[d]["text"])}</small></div>' for d in ('1', '2', '3'))
    rows = ''
    for gid, g in GROUPS.items():
        cells = ''
        for d in (1, 2, 3):
            ps = [p for p in PERSONAS.values() if p['group'] == gid and p['depth'] == d]
            chips = ''.join(f'<a class="pchip" href="#p-{E(p["id"])}">{avatar(p)}<span><b>{E(p["person"])}</b><small>{E(p["label"])}</small></span><span class="pd">{depth_badge(d)}</span></a>' for p in ps)
            cells += f'<div class="mc">{chips}</div>'
        rows += f'<div class="mr"><div class="ml"><b>{E(g["label"])}</b><small>{E(g["text"])}</small></div>{cells}</div>'
    grid = f'<div class="pmap"><div class="mr mhead"><div class="ml"></div>{cols}</div>{rows}</div>'
    cards = ''
    for p in PERSONAS.values():
        a = AUD[p['id']]
        cards += f'''<article class="pcard" id="p-{E(p["id"])}">
<header>{avatar(p)}<div><h3>{E(p["person"])}, {E(p["label"].lower())}</h3><p class="small">{E(GROUPS[p["group"]]["label"])} &middot; {depth_badge(p["depth"])}</p></div></header>
<p><b>Who.</b> {E(p["who"])}</p>
<p><b>Their question.</b> <i>{E(a["question"])}</i></p>
<div class="cols2"><div><h4>Needs</h4><ul>{"".join(f"<li>{E(x)}</li>" for x in p["needs"])}</ul></div><div><h4>Can skip</h4><ul>{"".join(f"<li>{E(x)}</li>" for x in p["skip"])}</ul></div></div>
<div class="answer answer-s"><div><p class="kicker">The answer in thirty seconds</p><p>{E(p["answer"])}</p></div></div>
<h4>Reading path</h4>{reading_path(p, 1)}
<h4>Words they will meet</h4>{words_met(p, 1, 10)}
<p><a class="cta cta-pri" href="../briefings/{E(p["id"])}/index.html" data-persona="{E(p["id"])}">Read as {E(p["person"])} &rarr;</a></p>
</article>'''
    body = f'''
<p class="kicker">Start here</p>
<h1>Who is reading? The site's readers, mapped</h1>
<p class="lead">A story like this one is read by people who have never heard of PHP and by people who maintain it. A page written for one of them fails the other. So before anything else, this site names its readers: {len(PERSONAS)} of them, by what they need to do and how much technical language they can take. Every reader gets a briefing that opens with a thirty-second answer, and a reading path through the rest of the site.</p>
{section("map", "The map", grid, "Across: how much technical language the reader wants. Down: what they need to do with the story. Pick the one closest to you.")}
{section("how", "How the site changes once you pick", """<ul class="howlist">
<li><b>A briefing written for you.</b> The thirty-second answer first, then what to decide or do, then the evidence. For plain-English readers the evidence is folded away until asked for.</li>
<li><b>A reading path that follows you.</b> Choose <i>read as</i> and a bar under the menu shows where you are on your path, what you have read and what to read next, on every page. It is kept in this browser only; nothing is sent anywhere.</li>
<li><b>Every term explained where it appears.</b> The first use of each specialist word on a page is underlined; hover or tap it for a one-line definition, or follow it to <a href="../glossary/index.html">the glossary</a>. Every CVE number links to what it is.</li>
<li><b>A plain-English line at the top of every technical page</b>, so a reader who lands on the code or the inventory knows in one sentence what it is and whether they need it.</li>
<li><b>The same evidence for everyone.</b> No briefing adds a claim. Each selects and orders the same rows, with the same status words and sources, so two readers can disagree about what to do and not about what happened.</li>
</ul>""")}
{section("readers", "The readers, one by one", f'<div class="pcards">{cards}</div>')}
{section("why", "Why name readers at all", "<p>The first version of this site opened with a sentence that was accurate and unreadable to most of the people who arrived on it: two CVE numbers, a nickname, and the words unauthenticated remote code execution. Accuracy is necessary and not sufficient. A board member who cannot tell what a CVE is will repeat the headline instead; a website owner who does not know the fix is in PHP rather than in WordPress will update the wrong thing. The readers on this page are the editor's working list, and the list will change as readers write in.</p>")}
'''
    page('start/index.html', 'Who is reading? The readers of this site, mapped', f'{len(PERSONAS)} kinds of reader, from someone who has never heard of PHP to the people who maintain it, mapped by what they need to do and how technical they want it, each with a thirty-second answer and a reading path.', body, kind='site', topics='php2shell readers personas')

def build_explained():
    srcs = lambda *x: f'<span class="refs">{src_links(list(x), 1)}</span>'
    body = f'''
<p class="kicker">Start here &middot; {depth_badge(1)}</p>
<h1>The PHP security flaws, explained from the start</h1>
<p class="lead">No technical background assumed. Seven short answers, in the order people usually ask them, each linking to the page with the evidence. Words in the dotted underline are explained when you hover or tap them.</p>
<nav class="toc"><a href="#php">What is PHP?</a><a href="#what">What went wrong?</a><a href="#nickname">Why php2shell?</a><a href="#cve">What are the numbers?</a><a href="#offline">Why did sites go offline?</a><a href="#hacked">Was anyone hacked?</a><a href="#now">What happens now?</a><a href="#trust">How to read this site</a></nav>
<section id="php"><h2>1. What is PHP, and is it on my computer?</h2>
<p>PHP is a programming language for websites. When you open a page on a site built with it, a program on the website's server, written in PHP, puts the page together (your name, the latest posts, the basket) and sends the result to your browser. WordPress, which runs a very large number of blogs, shops and company sites, is written in PHP; so are Drupal, Joomla, Moodle, Magento and the software behind Wikipedia.</p>
<p><b>PHP runs on servers, not on your phone or laptop.</b> This story is about the organisations that run websites. Visitors are affected only indirectly: if a site they use is broken into, or is taken offline as a precaution.</p>
<div class="flow" role="img" aria-label="A normal visit: your browser asks a web server running PHP for a page; PHP reads the database and files and builds the page.">
<div class="lane"><span class="lane-l">A normal visit</span><div class="fsteps"><div class="fstep">Your browser<small>asks for a page</small></div><span class="farr" aria-hidden="true">&rarr;</span><div class="fstep">The website's server, running PHP<small>builds the page</small></div><span class="farr" aria-hidden="true">&rarr;</span><div class="fstep">Database and files<small>the site's content and settings</small></div></div></div>
</div>
</section>
<section id="what"><h2>2. What went wrong?</h2>
<p>Two bugs were found deep inside PHP itself, not in any one website. Both are in how PHP cleans up after something goes wrong while it is handling a request.</p>
<p>An analogy. Think of PHP as the kitchen behind every page a website serves. When an order is impossible (it needs more than the kitchen is allowed to use), the cook abandons it. The flaws are in how the kitchen abandons and tidies up: in some cases it leaves the counter half cleared, and the next step, or the next order, uses what was left as if it were fresh. A customer who knows this can send an order designed to leave exactly the right things on the counter, so that the kitchen ends up following the customer's instructions instead of the menu.</p>
<div class="flow" role="img" aria-label="The attack: an attacker anywhere, with no password, sends a crafted request; PHP's error handling goes wrong; the attacker's commands run on the server.">
<div class="lane lane-bad"><span class="lane-l">The attack</span><div class="fsteps"><div class="fstep bad">Anyone on the internet<small>no account, no password</small></div><span class="farr" aria-hidden="true">&rarr;</span><div class="fstep bad">A crafted request<small>pushes PHP into its error path</small></div><span class="farr" aria-hidden="true">&rarr;</span><div class="fstep bad">The clean-up goes wrong<small>leftover memory is trusted</small></div><span class="farr" aria-hidden="true">&rarr;</span><div class="fstep bad">The attacker's commands run<small>on the server, as the website</small></div></div></div>
<div class="reach"><div><b>What that can reach</b><ul><li>the website's own code and settings</li><li>passwords stored in those settings, such as the database's</li><li>files the website can read or write</li><li>other systems that trust this server</li></ul></div><div><b>What it does not automatically reach</b><ul><li>systems the server is not allowed to talk to</li><li>passwords that were never on that server</li><li>your own phone or computer</li></ul></div></div>
</div>
<p>In the jargon, this is <i>unauthenticated remote code execution</i>: no login needed, from anywhere, and the attacker's code runs. It is the most serious kind of flaw there is, which is why the response was so loud. The researchers proved it end to end against the most traditional way of running PHP, inside the Apache web server, before any of the website's own code had run. That last point matters: <b>it does not matter how well a website is written</b>; if PHP underneath it is unpatched, it is in scope. {srcs("php-net-advisory", "github-ghsa-w8hw-w9fx-j79w", "github-ghsa-6wmf-4rv5-p3rp")}</p>
<p>The technical version is on <a href="../flaws/index.html">the two flaws</a>, and the code itself on <a href="../code/index.html">the code</a>.</p>
</section>
<section id="nickname"><h2>3. Why is it called php2shell?</h2>
<p>Serious flaws get nicknames so people can talk about them: Heartbleed, Shellshock, Log4Shell. <b>php2shell</b> reads as <i>PHP to shell</i>. A shell is the command line an administrator types into; getting a shell on a server means being able to run commands on it. So the name is the whole attack in one word: start with a PHP website, end with a command line on its server. The US NSA wrote it PHP2Shell. {srcs("nsa-x-2112903220209098897", "calif-php2shell")}</p>
</section>
<section id="cve"><h2>4. What are CVE-2026-109618 and CVE-2026-109619?</h2>
<p>They are the official names. A CVE number is a serial number for a security flaw, so that vendors, governments and journalists know they mean the same bug: CVE, the year the number was reserved, and a sequence number. Each has a public record saying what is affected and how bad it is.</p>
<div class="cols2"><div class="col"><h3>CVE-2026-109618</h3><p>PHP running out of memory mid-request can leave memory half set up, and the clean-up that follows can be steered by an attacker. Severity 9.2 out of 10.</p></div><div class="col"><h3>CVE-2026-109619</h3><p>Leftover settings from one visitor's request can point at memory that has been released, and the next request on the same worker uses it. Severity 9.2 out of 10.</p></div></div>
<p>Both are fixed in PHP 8.5.12, 8.4.27, 8.3.36 and 8.2.35, released on 21 October 2026. Older versions (8.1 and before) are past their support date and got no ready-made fix. {srcs("cve-cve-2026-109618", "cve-cve-2026-109619", "php-net-advisory")}</p>
</section>
<section id="offline"><h2>5. Why did governments tell people to take websites offline?</h2>
<p>Because an unpatched website with this flaw can be taken over by anyone, and updating every server takes time. The US NSA and CISA said: if you cannot update, take the system offline until you can. The UK's NCSC put that fourth on its list, after updating and temporary fixes; several European agencies said isolate it; others did not mention it at all. Dutch government services, including the DigiD login many Dutch citizens use, were taken offline as a precaution. {srcs("nsa-x-2112903220209098897", "cisa-alert-php-20261021", "ncsc-news-php", "rijksoverheid-ncsc-php-news")}</p>
<p>Taking a site offline is a decision an organisation makes, not evidence it was attacked. The <a href="../agencies/index.html">agencies page</a> sets the sixteen sets of advice side by side.</p>
</section>
<section id="hacked"><h2>6. Was anyone actually hacked?</h2>
<p>Not that anyone has confirmed, as of the latest evidence this site holds. Attackers have certainly been trying: Cloudflare says it saw millions of attempts across its network, and Amazon says a decoy server was hit four days before the fix was public. But an attempt is not a success, no named organisation has said it was broken into, and the US list of flaws known to be exploited did not include either of these when last checked. That can change quickly, and this site will say so when the evidence does. {srcs("x-eastdakota-php2shell-stats", "thehackernews-php2shell-4days", "cisa-kev-json")}</p>
<p>The details: <a href="../impact/index.html">who went offline and who was compromised</a>, and <a href="../exploitation/index.html">every sign of exploitation, in order</a>.</p>
</section>
<section id="now"><h2>7. What happens now?</h2>
<ul class="howlist">
<li><b>If you only use websites:</b> nothing to do. Ignore messages that tell you to install anything because of this; that is a scam pattern.</li>
<li><b>If you own a website:</b> ask whoever hosts it whether PHP has been updated and restarted. <a href="../briefings/site-owner/index.html">The website owner's briefing</a> has the exact question to send.</li>
<li><b>If you run systems:</b> update, restart, verify, and look for signs of compromise. <a href="../playbook/index.html">The step-by-step list</a> has every agency's advice in order.</li>
<li><b>If you decide or communicate:</b> <a href="../start/index.html">pick your briefing</a>.</li>
</ul>
</section>
<section id="trust"><h2>How to read this site</h2>
<p>Every statement on this site carries one of five words, so you can tell a fact from a rumour at a glance:</p>
{status_legend()}
<p>Every one of those statements links to the pages it comes from, and every one of those pages was saved, dated and fingerprinted when it was read, so that it can be checked later even if the original changes. <a href="../method/index.html">How that works</a>.</p>
</section>
'''
    page('explained/index.html', 'The PHP security flaws, explained from the start', 'No technical background assumed: what PHP is, what went wrong, why it is called php2shell, what the CVE numbers mean, why websites went offline, whether anyone was hacked, and what to do now.', body, kind='story', topics='php2shell explainer plain english')

def build_glossary():
    terms = sorted(TERMS, key=lambda t: t['term'].lower())
    letters = OrderedDict()
    for t in terms:
        letters.setdefault(t['term'][0].upper(), []).append(t)
    jump = ''.join(f'<a href="#l-{E(L)}">{E(L)}</a>' for L in letters)
    out = ''
    for L, ts in letters.items():
        items = ''
        for t in ts:
            ext = f' &middot; <a href="{U(t["ext"])}" rel="noopener">the authority &#8599;</a>' if t.get('ext') else ''
            items += f'<article class="gterm" id="{E(t["id"])}"><h3>{E(t["term"])}</h3><p class="gshort">{E(t["short"])}</p><p>{E(t["long"])}</p><p class="small"><a href="../{E(t["more"])}">Where it matters in this story &rarr;</a>{ext}</p></article>'
        out += f'<section id="l-{E(L)}" class="gletter"><h2>{E(L)}</h2>{items}</section>'
    body = f'''
<p class="kicker">Start here &middot; {depth_badge(1)}</p>
<h1>Glossary: every term, in plain English</h1>
<p class="lead">{len(TERMS)} words this story cannot avoid, each explained for someone who has never worked in security, and each in the sense it has in this story. On every other page, the first use of each of these words is underlined and links here.</p>
<nav class="toc jump">{jump}</nav>
{out}
'''
    page('glossary/index.html', 'Glossary: every php2shell term in plain English', f'{len(TERMS)} terms from the php2shell story (PHP, CVE, CVSS, remote code execution, WAF, KEV and more), each explained in plain English, in the sense it has in this story.', body, kind='site', topics='php2shell glossary')

def build_personas_js():
    data = {'depths': {k: v['label'] for k, v in DEPTHS.items()}, 'personas': OrderedDict()}
    for p in PERSONAS.values():
        data['personas'][p['id']] = {'person': p['person'], 'label': p['label'], 'group': p['group'], 'depth': p['depth'],
                                     'path': [[x, nav_title(x), minutes(x)] for x in p['path']]}
    write('assets/personas.js', '// Generated by admin/build/build.py from data/personas.json: the readers, their paths and reading times.\nwindow.P2S = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')



# ----------------------------------------------------------------------------- v0.3.2: every section versioned, every fact with a timeline

import difflib, hashlib

LEDGER_PATH = os.path.join(DATA, 'sections.json')
LEDGER = json.load(open(LEDGER_PATH, encoding='utf-8')) if os.path.exists(LEDGER_PATH) else {'sections': OrderedDict()}
LEDGER['note'] = ('The section ledger. Every major section of the site, every briefing and every fact is a projection of the data; '
                  'its text is hashed on every build, and a new version is recorded only when that text changes. A version names the site '
                  'release that created it and the date of that release. Versions marked reconstructed were rebuilt from the markdown twins '
                  'and data files of earlier releases in git. Written by admin/build/build.py; never edit by hand.')
RELEASES = list(reversed(D['versions']['versions']))  # oldest first
REL_DATE = {r['version']: r['date'] for r in RELEASES}
SEO = D.get('seo') or {}
PAGE_VERSIONED = ['summary/index.html', 'flaws/index.html', 'code/index.html', 'timeline/index.html', 'discovery/index.html', 'leak/index.html',
                  'exploitation/index.html', 'impact/index.html', 'defence/index.html', 'context/index.html', 'playbook/index.html',
                  'claims/index.html', 'numbers/index.html', 'agencies/index.html', 'affected/index.html', 'actors/index.html',
                  'explained/index.html', 'glossary/index.html', 'method/index.html', 'interview/index.html']

def norm_md(md):
    """The text a section is versioned on: the markdown twin without its footer, links reduced to their words."""
    md = md.split('\n\n---\nsite v')[0]
    md = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', md)
    md = md.replace(" fact timeline →", "")  # a navigation link added to claim rows in v0.3.2, not content
    md = re.sub(r'[ \t]+\n', '\n', md)
    return re.sub(r'\n{3,}', '\n\n', md).strip()

def briefing_norm(md):
    """A briefing's text without what changes when other pages change: reading times and the glossary chips."""
    md = norm_md(md)
    md = re.sub(r'\n## Words you will meet\n.*?(?=\n## |\Z)', '\n', md, flags=re.S)
    md = re.sub(r' ?\b\d+ min\b', '', md)
    md = re.sub(r'About \d+ minutes in all\. ?', '', md)
    md = re.sub(r' &middot; from the same \d+ claims, selected and ordered for one reader| · from the same \d+ claims, selected and ordered for one reader', '', md)
    return md.strip()

def section_id(path):
    if path.startswith('briefings/'):
        return 'briefing-' + path.split('/')[1]
    return 'page-' + re.sub(r'/index\.html$|\.html$', '', path).replace('/', '-')

def ledger(sid, title, kind, path, text, scope='everyone', site=None, date=None, reconstructed=False):
    """Record a section's text; return its ledger entry. Idempotent: the same text never makes a second version."""
    site, date = site or VERSION, date or REL_DATE.get(site or VERSION, '')
    h = hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
    sec = LEDGER['sections'].setdefault(sid, {'title': title, 'kind': kind, 'path': path, 'scope': scope, 'versions': []})
    sec.update({'title': title, 'kind': kind, 'path': path, 'scope': scope})
    vs = sec['versions']
    if vs and vs[-1]['hash'] == h:
        return sec
    if vs and vs[-1]['site'] == site and not reconstructed:
        if len(vs) >= 2 and vs[-2]['hash'] == h:
            vs.pop()
        else:
            vs[-1].update({'hash': h, 'text': text})
        return sec
    vs.append({'v': len(vs) + 1, 'hash': h, 'site': site, 'date': date, 'reconstructed': reconstructed, 'text': text})
    return sec

def ledger_for_page(path, md):
    if path.startswith('briefings/'):
        a = AUD.get(path.split('/')[1])
        return ledger(section_id(path), f'Briefing: {a["name"] if a else path}', 'briefing', path, briefing_norm(md), scope=path.split('/')[1])
    if path in PAGE_VERSIONED:
        return ledger(section_id(path), nav_title(path), 'page', path, norm_md(md))
    return None

def save_ledger():
    OUTPUTS.add('data/sections.json')
    out = json.dumps(LEDGER, indent=1, ensure_ascii=False) + '\n'
    old = open(LEDGER_PATH, encoding='utf-8').read() if os.path.exists(LEDGER_PATH) else ''
    if out != old:
        write('data/sections.json', out)

def nice_date(d):
    return human_time(d + 'T00:00').replace(', 00:00 UTC', '') if d else ''

def vbadge(sid, depth, label='This section'):
    sec = LEDGER['sections'].get(sid)
    if not sec or not sec['versions']:
        return ''
    v, n, up = sec['versions'][-1], len(sec['versions']), '../' * depth
    hist = f'<a href="{up}versions/{E(sid)}/index.html">{"history and changes, " + str(n - 1) + " earlier" if n > 1 else "history"}</a>'
    scope = ' data-scope="page"' if label in ('This page', 'This briefing') else ''
    return (f'<p class="vbadge"><span class="it" data-item="{E(sid)}" data-h="{E(v["hash"])}" data-n="{v["v"]}"{scope}></span><span class="vb-v">{E(label)} v{v["v"]}</span> written in site <a href="{up}admin/versions.html#v{E(v["site"])}">v{E(v["site"])}</a>'
            f' on {E(nice_date(v["date"]))} &middot; {hist}</p>')

def word_diff(a, b):
    ta, tb = re.split(r'(\s+)', a), re.split(r'(\s+)', b)
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            out.append(E(''.join(ta[i1:i2])))
        else:
            if i2 > i1: out.append(f'<del>{E("".join(ta[i1:i2]))}</del>')
            if j2 > j1: out.append(f'<ins>{E("".join(tb[j1:j2]))}</ins>')
    return ''.join(out)

def diff_html(a, b):
    """Line diff of two versions, with a word diff inside lines that were edited rather than replaced."""
    al, bl = a.splitlines(), b.splitlines()
    sm = difflib.SequenceMatcher(None, al, bl, autojunk=False)
    out, added, removed = [], 0, 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            lines = al[i1:i2]
            if len(lines) > 3:
                out.append(f'<div class="dl dl-ctx">{E(lines[0])}</div><div class="dl dl-skip">{len(lines) - 2} unchanged lines</div><div class="dl dl-ctx">{E(lines[-1])}</div>')
            else:
                out.extend(f'<div class="dl dl-ctx">{E(x)}</div>' for x in lines)
        elif op == 'replace' and i2 - i1 == j2 - j1 and sum(len(x) for x in al[i1:i2]) < 6000:
            for x, y in zip(al[i1:i2], bl[j1:j2]):
                out.append(f'<div class="dl dl-chg">{word_diff(x, y)}</div>')
                added += 1; removed += 1
        else:
            out.extend(f'<div class="dl dl-del">{E(x)}</div>' for x in al[i1:i2])
            out.extend(f'<div class="dl dl-ins">{E(x)}</div>' for x in bl[j1:j2])
            removed += i2 - i1; added += j2 - j1
    return f'<div class="diff">{"".join(out)}</div>', added, removed

def fact_text(c):
    return f'{c["claim"]}\nWho says it: {c["by"]}\nStatus: {c["status"]}\nTopic: {c["topic"]}\nSources: {", ".join(c["sources"])}'

def fact_field(text, field):
    m = re.search(r'^' + field + r': (.*)$', text, flags=re.M)
    return m.group(1) if m else ''

def parse_when(s):
    """A sortable ISO-ish instant from the shapes the manifest uses, or None."""
    if not s:
        return None
    s = str(s)
    m = re.match(r'^(\d{8})T(\d{2})(\d{2})(\d{2})Z', s)
    if m:
        d = m.group(1)
        return f'{d[:4]}-{d[4:6]}-{d[6:]}T{m.group(2)}:{m.group(3)}Z'
    m = re.match(r'^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}))?', s)
    if m:
        return m.group(1) + ('T' + m.group(2) + 'Z' if m.group(2) else '')
    m = re.match(r'^(\d{4})$', s)
    return m.group(1) if m else None

def fact_projections(c):
    """Where a fact is shown: the briefings whose selection includes its topic, and the pages that list it."""
    out = [(f'briefings/{pid}/index.html', PERSONAS[pid]) for pid, sel in BRIEF_TOPICS.items() if c['topic'] in sel and pid in PERSONAS]
    return out

BRIEF_TOPICS = {}  # filled by build_briefings: persona id -> topics

def build_facts():
    for c in D['claims']:
        ledger('fact-' + c['id'], c['claim'][:90], 'fact', f'facts/{c["id"]}/index.html', fact_text(c), scope='fact')
    for c in D['claims']:
        sec = LEDGER['sections']['fact-' + c['id']]
        evs = []
        for s in c['sources']:
            if s not in SOURCES:
                continue
            row = SOURCES[s]
            pw = parse_when(row.get('published'))
            if pw:
                evs.append((pw, 'pub', f'{short_name(row)} publishes <a href="../../sources/{E(s)}/index.html">{E((row.get("title") or s)[:110])}</a>'))
            caps = sorted(parse_when(x.get('stamp')) or '' for x in row.get('captures', []))
            if caps and caps[0]:
                evs.append((caps[0], 'cap', f'Saved into the evidence vault: {short_name(row)}' + (f', then {len(caps) - 1} more capture{"s" if len(caps) > 2 else ""}' if len(caps) > 1 else '')))
        prev = None
        for v in sec['versions']:
            st = fact_field(v['text'], 'Status')
            if prev is None:
                what = f'Enters this site as {pill(st)} in v{E(v["site"])}'
            elif fact_field(prev['text'], 'Status') != st:
                what = f'Status changes from {pill(fact_field(prev["text"], "Status"))} to {pill(st)} in v{E(v["site"])}'
            else:
                what = f'Reworded or re-sourced in v{E(v["site"])}'
            evs.append((v['date'] + 'T23:59Z', 'site', what + (' <span class="small">(reconstructed from git)</span>' if v.get('reconstructed') else '')))
            prev = v
        evs.sort(key=lambda e: e[0])
        rail = ''.join(f'<li class="tk tk-{k}"><span class="when">{E(fmt_at(w) if "T" in w and not w.endswith("T23:59Z") else w[:10])}</span><span>{t}</span></li>' for w, k, t in evs)
        rows = []
        for i, v in enumerate(sec['versions']):
            d = ''
            if i:
                d, _, _ = diff_html(sec['versions'][i - 1]['text'], v['text'])
            rows.append(f'<details{" open" if i == len(sec["versions"]) - 1 else ""}><summary>v{v["v"]} &middot; site v{E(v["site"])} &middot; {E(nice_date(v["date"]))} &middot; {pill(fact_field(v["text"], "Status"))}</summary>{d or "<pre>" + E(v["text"]) + "</pre>"}</details>')
        proj = fact_projections(c)
        pj = ''.join(f'<a class="pchip" href="../../{E(p)}">{avatar(pp)}<span><b>{E(pp["person"])}</b><small>{E(pp["label"])}</small></span></a>' for p, pp in proj)
        g = mini_graph('fact ' + c['id'], c['status'], [(SOURCES[s].get('title') or s, f'../../sources/{s}/index.html', 'src') for s in c['sources'] if s in SOURCES], 2)
        body = f'''
<p class="kicker">Fact &middot; {E(c["topic"])} &middot; {pill(c["status"])}</p>
<h1>{E(c["claim"])}</h1>
<p class="meta"><b>Who says it:</b> {E(c["by"])} &middot; <b>Sources:</b> {src_links(c["sources"], 2)}</p>
{f'<p class="note">{E(c["note"])}</p>' if c.get("note") else ""}
{fc_section(c["id"])}
{section("timeline", "This fact over time", f'<ol class="rail">{rail}</ol><p class="small">Published: when the source says it was published. Saved: the first capture into the evidence vault. The rest are this site: the release in which the fact first appeared and every release that changed its wording, sources or status.</p>')}
{section("graph", "What it rests on", g)}
{section("where", "Where this fact appears", (f'<p>In the briefings for:</p><div class="pchips">{pj}</div>' if pj else '<p class="small">Not in any briefing yet.</p>') + f'<p>And on <a href="../../claims/index.html#{E(c["id"])}">every claim</a>.</p>')}
{section("versions", "Every version of this fact", "".join(rows))}
'''
        page(f'facts/{c["id"]}/index.html', f'Fact: {c["claim"][:80]}', f'{c["claim"]} Who says it, its status ({c["status"]}), its sources, and its timeline from publication to this site.', body, kind='evidence', topics='php2shell fact')

def history_page(sid, sec):
    vs = sec['versions']
    items = []
    for i in range(len(vs) - 1, -1, -1):
        v = vs[i]
        if i:
            d, add, rem = diff_html(vs[i - 1]['text'], v['text'])
            head = f'{add} lines added or changed, {rem} removed or changed, against v{vs[i - 1]["v"]}'
        else:
            d, head = f'<pre class="vtext">{E(v["text"][:20000])}</pre>', 'the first version'
        items.append(f'<details id="v{v["v"]}"{" open" if i == len(vs) - 1 else ""}><summary><b>v{v["v"]}</b> &middot; site <a href="../../admin/versions.html#v{E(v["site"])}">v{E(v["site"])}</a> &middot; {E(nice_date(v["date"]))}{" &middot; reconstructed from git" if v.get("reconstructed") else ""} &middot; {head} &middot; <code>{E(v["hash"])}</code></summary>{d}</details>')
    scope = sec.get('scope')
    who = f' It is written for {E(PERSONAS[scope]["person"])}, {E(PERSONAS[scope]["label"].lower())}.' if scope in PERSONAS else ''
    body = f'''
<p class="kicker">Version history &middot; {E(sec["kind"])}</p>
<h1>{E(sec["title"])}: every version</h1>
<p class="lead">This section is a projection of the site's data, rebuilt on every release.{who} A new version is recorded only when the text a reader sees changes, so a release that changed something elsewhere leaves this section's version alone. It has {len(vs)} version{"s" if len(vs) != 1 else ""}; the newest is first, and each is shown as the changes from the one before. <a href="../../{E(sec["path"])}">Read the current version &rarr;</a></p>
{"".join(items)}
<p><a href="../index.html">Every section, across every release &rarr;</a></p>
'''
    page(f'versions/{sid}/index.html', f'{sec["title"]}: version history', f'Every version of the section "{sec["title"]}" on {SITE_NAME}, with the site release that created it and the changes between versions.', body, kind='site')

def build_versions():
    secs = [(sid, s) for sid, s in LEDGER['sections'].items() if s['kind'] != 'fact']
    for sid, s in secs:
        history_page(sid, s)
    rels = [r['version'] for r in RELEASES]
    head = ''.join(f'<th class="rv"><a href="../admin/versions.html#v{E(r)}">{E(r)}</a></th>' for r in rels)
    groups = [('front', 'The front page'), ('briefing', 'The briefings, one per reader'), ('page', 'The story and evidence pages')]
    rows = ''
    for kind, label in groups:
        rows += f'<tr class="vg"><th colspan="{len(rels) + 1}">{E(label)}</th></tr>'
        for sid, s in secs:
            if s['kind'] != kind:
                continue
            made = {v['site']: v for v in s['versions']}
            first = s['versions'][0]['site']
            cells = ''
            alive = False
            for r in rels:
                alive = alive or r == first
                if r in made:
                    cells += f'<td><a class="vc vc-new" href="{E(sid)}/index.html#v{made[r]["v"]}" title="v{made[r]["v"]} written in {E(r)}">v{made[r]["v"]}</a></td>'
                else:
                    cells += f'<td><span class="vc{" vc-same" if alive else ""}" title="{"unchanged" if alive else "did not exist"}"></span></td>'
            who = avatar(PERSONAS[s['scope']]) + ' ' if s.get('scope') in PERSONAS else ''
            rows += f'<tr><th class="vn">{who}<a href="{E(sid)}/index.html">{E(s["title"])}</a></th>{cells}</tr>'
    facts = [s for s in LEDGER['sections'].values() if s['kind'] == 'fact']
    frow = ''
    for r in rels:
        added = sum(1 for s in facts if s['versions'][0]['site'] == r)
        changed = sum(1 for s in facts for i, v in enumerate(s['versions']) if i and v['site'] == r and fact_field(v['text'], 'Status') != fact_field(s['versions'][i - 1]['text'], 'Status'))
        reworded = sum(1 for s in facts for i, v in enumerate(s['versions']) if i and v['site'] == r) - changed
        frow += f'<td class="fc">{f"<b>+{added}</b>" if added else ""}{f"<br><span>{changed} status</span>" if changed else ""}{f"<br><span>{reworded} edited</span>" if reworded else ""}</td>'
    body = f'''
<p class="kicker">The evidence &middot; versions</p>
<h1>How the story changed, release by release</h1>
<p class="lead">Every section of this site is a projection of the evidence, and every projection is versioned. Across: each release of the site. Down: the front page's sections, each reader's briefing, and the story and evidence pages. A filled cell is a new version written in that release; a faint cell is a section that existed and did not change. A new fact for engineers moves the engineer's briefing and leaves the board's alone, and this table is where that shows.</p>
<div class="tw vt"><table class="vmatrix"><thead><tr><th>Section</th>{head}</tr></thead><tbody>{rows}<tr class="vg"><th colspan="{len(rels) + 1}">The facts</th></tr><tr><th class="vn"><a href="../claims/index.html">{len(facts)} facts</a>: added, status changes, edits</th>{frow}</tr></tbody></table></div>
<p class="small">Versions before v0.3.2 are reconstructed from each release's markdown twins and data files in git. The ledger itself is <a href="../data/sections.json">data/sections.json</a>. What each release changed, in a sentence, is the <a href="../admin/versions.html">release history</a>; what changed for readers is <a href="../whatsnew/index.html">what's new</a>.</p>
'''
    page('versions/index.html', 'How the story changed, release by release', 'Every section of the site, every reader\'s briefing and every fact, versioned across every release: what changed, when, and in which release.', body, kind='site')

def changes_in(rel):
    secs, facts_new, facts_status, facts_edit = [], [], [], []
    for sid, s in LEDGER['sections'].items():
        for i, v in enumerate(s['versions']):
            if v['site'] != rel:
                continue
            if s['kind'] == 'fact':
                fid = sid[5:]
                if i == 0:
                    facts_new.append((fid, s, v))
                elif fact_field(v['text'], 'Status') != fact_field(s['versions'][i - 1]['text'], 'Status'):
                    facts_status.append((fid, s, v, s['versions'][i - 1]))
                else:
                    facts_edit.append((fid, s, v))
            else:
                secs.append((sid, s, v, i))
    return secs, facts_new, facts_status, facts_edit

def build_whatsnew():
    out = ''
    for r in reversed(RELEASES):
        rel = r['version']
        secs, fn, fs, fe = changes_in(rel)
        parts = []
        if fs:
            parts.append('<h3>Facts whose status changed</h3><ul>' + ''.join(f'<li><a href="../facts/{E(f)}/index.html">{E(s["title"])}</a>: {pill(fact_field(p["text"], "Status"))} &rarr; {pill(fact_field(v["text"], "Status"))}</li>' for f, s, v, p in fs) + '</ul>')
        if fn:
            parts.append(f'<h3>{len(fn)} new fact{"s" if len(fn) != 1 else ""}</h3><ul class="cmp">' + ''.join(f'<li><a href="../facts/{E(f)}/index.html">{E(s["title"])}</a> {pill(fact_field(v["text"], "Status"))}</li>' for f, s, v in fn[:40]) + ('<li>and more on <a href="../claims/index.html">every claim</a></li>' if len(fn) > 40 else '') + '</ul>')
        if fe:
            parts.append(f'<p class="small">{len(fe)} fact{"s" if len(fe) != 1 else ""} reworded or re-sourced: ' + ', '.join(f'<a href="../facts/{E(f)}/index.html">{E(f)}</a>' for f, s, v in fe[:30]) + '.</p>')
        readers = [(sid, s, v, i) for sid, s, v, i in secs if s['kind'] == 'briefing']
        if readers:
            parts.append('<h3>Briefings that changed</h3><div class="pchips">' + ''.join(f'<a class="pchip" href="../versions/{E(sid)}/index.html#v{v["v"]}">{avatar(PERSONAS[s["scope"]]) if s["scope"] in PERSONAS else ""}<span><b>{E(PERSONAS[s["scope"]]["person"]) if s["scope"] in PERSONAS else ""}</b><small>{E(s["title"].replace("Briefing: ", ""))} &middot; {"new" if i == 0 else "v" + str(v["v"])}</small></span></a>' for sid, s, v, i in readers) + '</div>')
        others = [(sid, s, v, i) for sid, s, v, i in secs if s['kind'] != 'briefing']
        if others:
            parts.append('<h3>Sections that changed</h3><ul class="cmp">' + ''.join(f'<li><a href="../versions/{E(sid)}/index.html#v{v["v"]}">{E(s["title"])}</a> {"(new)" if i == 0 else "v" + str(v["v"])}</li>' for sid, s, v, i in others) + '</ul>')
        out += f'<article class="rel wn" id="v{E(rel)}" data-rel="{E(rel)}"><h2>v{E(rel)} &middot; {E(nice_date(r["date"]))}<span class="newmark">new since your last visit</span></h2><p>{E(r["title"])}</p>{"".join(parts) or "<p class=small>No reader-facing section changed in this release.</p>"}</article>'
    body = f'''
<p class="kicker">The story &middot; what's new</p>
<h1>What's new</h1>
<p class="lead">Every release of this site, newest first, with what changed in it for readers: facts added, facts whose status changed, the briefings that moved and the sections that were rewritten. Releases you have not seen since your last visit are marked. To follow along, subscribe to <a href="../feed.xml">the feed</a>.</p>
<p class="caveat">New evidence (for example the first confirmed compromise of a named organisation) reaches this page only once it has been captured into the evidence vault and turned into a fact with sources. Until then it is not on this site, however widely it is reported.</p>
{out}
'''
    page('whatsnew/index.html', "What's new: every change, release by release", 'What changed on this site in each release: new facts, facts whose status changed, the briefings that moved for each reader and the sections that were rewritten.', body, kind='site', topics='php october 2026 updates')

def build_pipeline():
    srcs = D['sources']
    captured = sum(1 for s in srcs if s.get('status') == 'captured')
    blocked = sum(1 for s in srcs if s.get('status') in ('blocked', 'failed'))
    noted = sum(1 for s in srcs if s.get('has_notes'))
    cited = {x for c in D['claims'] for x in c['sources']} | {x for t in D['timeline'] for x in t['sources']}
    claims = len(D['claims'])
    proj = sum(1 for s in LEDGER['sections'].values() if s['kind'] != 'fact')
    stages = [
        ('Found', C['sources'], 'sources the agents found and logged in the vault', 'sources/index.html'),
        ('Saved', captured, f'captured as served and as rendered, each file hashed; {blocked} blocked by bot checks, the block recorded', 'sources/index.html'),
        ('Read', noted, 'with a collector\'s note of what the page actually says', 'sources/index.html'),
        ('Cited', len(cited & set(SOURCES)), 'cited by at least one fact or timeline event', 'graph/index.html'),
        ('Facts', claims, f'facts, each with who says it and a status: {C["by_status"]["confirmed"]} confirmed', 'claims/index.html'),
        ('Sections', proj, 'versioned sections and briefings built from those facts', 'versions/index.html'),
        ('Readers', len(PERSONAS), 'kinds of reader, each with a briefing', 'start/index.html'),
    ]
    mx = max(n for _, n, _, _ in stages)
    funnel = ''.join(f'<a class="fn" href="../{h}"><span class="fl">{E(l)}</span><span class="fb"><i style="width:{max(4, round(100 * n / mx))}%"></i></span><b>{n}</b><span class="ft">{E(t)}</span></a>' for l, n, t, h in stages)
    facts = [s for s in LEDGER['sections'].values() if s['kind'] == 'fact']
    order = ['confirmed', 'reported', 'disputed', 'contradicted', 'unverified']
    bars = ''
    for r in RELEASES:
        cnt = Counter()
        for s in facts:
            live = [v for v in s['versions'] if [x['version'] for x in RELEASES].index(v['site']) <= [x['version'] for x in RELEASES].index(r['version'])]
            if live:
                cnt[fact_field(live[-1]['text'], 'Status')] += 1
        total = sum(cnt.values())
        segs = ''.join(f'<i class="sb sb-{k}" style="flex:{cnt[k]}" title="{cnt[k]} {k}"></i>' for k in order if cnt[k])
        bars += f'<div class="sbr"><span class="sbl">v{E(r["version"])}</span><span class="sbb">{segs}</span><b>{total}</b></div>'
    body = f'''
<p class="kicker">The evidence &middot; the pipeline</p>
<h1>The fact pipeline: from a web page to a reader</h1>
<p class="lead">Every fact on this site has travelled the same path: a source is found, saved and fingerprinted, read, cited by a fact with a status, built into sections, and selected for the readers it matters to. Each bar is a count at that stage, as of this release; each links to the stage itself.</p>
<div class="funnel">{funnel}</div>
{section("status", "The facts by status, release by release", f'<div class="sbars">{bars}</div>' + status_legend(), "How many facts the site carried in each release and how far each could be trusted. A fact that moves from reported to confirmed is a second primary source found; one that moves the other way is a correction.")}
{section("verify", "Verification: what runs and what does not", """<ul class="howlist">
<li><b>Runs on every build:</b> every fact cites only sources that exist in the vault's manifest; every link resolves; every section's text is hashed and versioned; the site is byte-identical when rebuilt.</li>
<li><b>Runs when an agent writes a fact:</b> the status word is chosen from the sources it cites, and a fact never gets a better word than its sources give it.</li>
<li><b>Not yet run:</b> an independent verifier that re-reads every fact against the saved text of its sources, and a second model reading the vault. Both are on the list; neither has happened, and this line will change when they do.</li>
</ul>""")}
{section("each", "Every fact has its own timeline", '<p>Each fact has a page of its own: when each of its sources was published, when it was saved, when it entered this site and every change of wording or status since, the sources it rests on as a graph, and the briefings it appears in. Start from <a href="../claims/index.html">every claim</a> and follow the timeline link on any row.</p>')}
'''
    page('pipeline/index.html', 'The fact pipeline: from a web page to a reader', 'How a source becomes a fact and a fact reaches a reader on this site: found, saved, read, cited, given a status, built into versioned sections and selected per reader, with counts at every stage and the facts by status in every release.', body, kind='site', topics='provenance pipeline verification')

def build_interview():
    iv = D['interview']
    qa = ''.join(f'<div class="iq" id="q{i + 1}"><h3>{E(x["q"])}</h3><blockquote><p>{E(x["a"])}</p><footer>{E(x["from"])}</footer></blockquote></div>' for i, x in enumerate(iv['qa']))
    pending = ''.join(f'<li>{E(q)}</li>' for q in iv['pending'])
    body = f'''
<p class="kicker">About &middot; interview</p>
<h1>{E(iv["title"])}</h1>
<p class="lead">{E(iv["intro"])}</p>
<p class="caveat">{E(iv["method"])}</p>
{qa}
{section("pending", "Not yet answered", f'<p>The questions for the next round, in the editor\'s own time:</p><ul>{pending}</ul>')}
'''
    page('interview/index.html', iv['title'], iv['description'], body, kind='article', topics='interview editor', origin='interview', byline='The editor, Dinis Cruz, in his own words; the questions by the agent that builds the site')

def build_feed():
    items = ''
    for r in reversed(RELEASES):
        u = f'{BASE_URL}/whatsnew/index.html#v{r["version"]}'
        items += (f'<entry><title>{E("v" + r["version"] + ": " + r["title"][:140])}</title><id>{u}</id><link href="{u}"/>'
                  f'<updated>{r["date"]}T00:00:00Z</updated><summary>{E(r["title"] + (" " + r["summary"] if r.get("summary") else ""))}</summary></entry>\n')
    updated = RELEASES[-1]['date'] + 'T00:00:00Z'
    write('feed.xml', f'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>{E(SITE_NAME)}: what's new</title>
<subtitle>{E(STORY["description"])}</subtitle>
<link href="{BASE_URL}/feed.xml" rel="self"/>
<link href="{BASE_URL}/"/>
<id>{BASE_URL}/</id>
<updated>{updated}</updated>
<author><name>Dinis Cruz</name></author>
{items}</feed>
''')

def page_lastmod(path):
    sec = LEDGER['sections'].get(section_id(path))
    if sec and sec['versions']:
        return sec['versions'][-1]['date']
    if path.startswith('facts/'):
        s = LEDGER['sections'].get('fact-' + path.split('/')[1])
        if s: return s['versions'][-1]['date']
    return RELEASES[-1]['date']

def build_seo():
    urls = []
    for p, _, _, kind in PAGES:
        if p.startswith('account/top') or p == 'account/topped-up.html':
            continue
        pr = '1.0' if p == 'index.html' else '0.8' if p.count('/') == 1 and not p.startswith(('versions/', 'admin/', 'account/')) else '0.5'
        urls.append(f'<url><loc>{BASE_URL}/{p}</loc><lastmod>{page_lastmod(p)}</lastmod><priority>{pr}</priority></url>')
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(urls) + '\n</urlset>\n')
    write('robots.txt', f'# {SITE_NAME}. Everything here is public; agents are welcome, and llms.txt lists the markdown twins.\nUser-agent: *\nAllow: /\nDisallow: /account/top-up.html\nDisallow: /account/topped-up.html\n\nSitemap: {BASE_URL}/sitemap.xml\n')


# ----------------------------------------------------------------------------- patching, and status.json (v0.4.1)

def inv_row(sup, prod):
    return next((r for r in D['software']['rows'] if r['supplier'] == sup and r['product'] == prod), None)

def build_patching():
    P = D['patching']
    inv = f'<a href="../affected/software.html">the NCSC-NL inventory</a>'
    def chip(sup, prod, st):
        r = inv_row(sup, prod)
        ver = f' <span class="small">{E(r["version"][:60])}</span>' if r and r.get('version') else ''
        return f'<li><b class="{"okw" if st == "Fix" else "badw"}">{"fixed" if st == "Fix" else "still affected"}</b> {E(sup)}: {E(prod)}{ver}</li>'
    ladder = table(['PHP branch', 'Upstream', 'What the PHP project shipped', 'In the CVE record', 'Downstream, at the inventory commit', 'Sources'],
                   [[f'<b>{E(l["branch"])}</b>', E(l['upstream']), E(l['fix']), E(l['in_cve']), '<ul class="inv">' + ''.join(chip(*d) for d in l['downstream']) + '</ul>', src_links(l['sources'], 1)] for l in P['ladder']], 'ladder')
    models = ''.join(f'<article class="role" id="m-{E(m["id"])}"><h3>{E(m["name"])}</h3><p>{E(m["what"])}</p><ul class="inv">{"".join(chip(*r) for r in m["rows"])}</ul></article>' for m in P['models'])
    fx = ''.join(f'<li><b>{E(x["what"])}.</b> {E(x["text"])} <span class="refs">{src_links(x["sources"], 1)}</span></li>' for x in P['side_effects'])
    why = ''.join(f'<li>{E(x["text"])} <span class="refs">{src_links(x["sources"], 1)}</span></li>' for x in P['why_not_every_version'])
    sw = D['software']['by_status_109618']
    story = next((a for a in ARTICLES if a['slug'] == 'why-not-patch-every-version'), None)
    body = f'''
<h1>Patching: which versions get a fix, and from whom</h1>
<p class="lead">{E(P["note"])}</p>
<p class="kv"><b>{sw.get("Fix", 0)}</b> fixed &middot; <b>{sw.get("Vulnerable", 0)}</b> still affected &middot; <b>{sw.get("Investigation", 0)}</b> under investigation &middot; <b>{sw.get("Not vuln", 0)}</b> not affected, of {D["software"]["count"]} products in {inv} at commit <code>{E(D["software"]["commit"])}</code> <span class="refs">{src_links([P["inventory_source"]], 1)}</span></p>
{section("ladder", "The version ladder", ladder, "Each PHP branch, what the PHP project itself shipped for it, and some of the companies that shipped a fix for it anyway, or had not yet.")}
{section("why", "Why not every version", f'<ul>{why}</ul>')}
{section("models", "How a fix reaches a server", f'<p>The same fix arrives in very different ways depending on who a site gets its PHP from. Read from {inv}, row by row.</p><div class="roles">{models}</div>')}
{section("effects", "What the fix changes", f'<p>The reason an operator hesitates: the fix is not invisible.</p><ul>{fx}</ul>')}
{section("open", "Not known yet", "<ul>" + "".join(f"<li>{E(o)}</li>" for o in P["open"]) + "</ul>")}
<p>{f'The story behind this page is <a href="../articles/{E(story["slug"])}/index.html">{E(story["title"])}</a>, with the editor\'s argument on who should own patching.' if story else ''} The data is <a href="../data/patching.json">data/patching.json</a>; the gate checks that every downstream row names a product in the inventory with the status shown.</p>
'''
    page('patching/index.html', 'Patching: which versions get a fix, and from whom', 'Which PHP versions the PHP project fixed, which it left to others, which nobody upstream fixed, and how the fix reaches a server: patched for you, rebuild yourself, a system update, extended support, a hosting panel, or still waiting.', body, kind='analysis', topics='php2shell patching versions backports')

STATUS_FACTS = ['two-cves-9.2', 'no-confirmed-compromise', 'cisa-none']

def build_status_json():
    """status.json: a small, stable, machine-readable summary for the newsroom and other sites. No clock: every value is data."""
    cl = {c['id']: c for c in D['claims']}
    latest = ARTICLES[0] if ARTICLES else None
    st = OrderedDict([
        ('schema', 'sgit.newsroom.story-status/1'),
        ('site', SITE), ('name', SITE_NAME), ('url', BASE_URL + '/index.html'),
        ('story', 'php2shell'), ('cves', STORY['cves']), ('status', STORY['status'].lower()),
        ('version', VERSION), ('data_as_of', STORY['data_as_of']), ('vault_commit', D['vault']['head']['commit']),
        ('counts', OrderedDict([('sources', C['sources']), ('captures', C['captures']), ('claims', C['claims']),
                                ('claims_by_status', OrderedDict((k, C['by_status'][k]) for k in STATUS_WORDS)), ('events', C['events']),
                                ('agencies', C['agencies']), ('offline_reported', len(D['impact']['offline'])), ('compromises_confirmed', 0)])),
        ('headline_facts', [OrderedDict([('id', i), ('text', cl[i]['claim']), ('status', cl[i]['status']), ('url', f'{BASE_URL}/claims/index.html#{i}'), ('sources', cl[i]['sources'])]) for i in STATUS_FACTS]),
        ('latest_story', OrderedDict([('title', latest['title']), ('url', f'{BASE_URL}/articles/{latest["slug"]}/index.html'), ('written', latest['written']), ('origin', latest['origin'])]) if latest else None),
        ('links', OrderedDict([('front', f'{BASE_URL}/index.html'), ('sources', f'{BASE_URL}/sources/index.html'), ('claims', f'{BASE_URL}/claims/index.html'),
                               ('stories', f'{BASE_URL}/articles/index.html'), ('releases', f'{BASE_URL}/admin/versions.html'), ('llms', f'{BASE_URL}/llms.txt')])),
    ])
    text = json.dumps(st, indent=1, ensure_ascii=False) + '\n'
    write('status.json', text)
    rows = [[f'<code>{E(k)}</code>', E(json.dumps(v, ensure_ascii=False)[:160])] for k, v in st.items()]
    body = f'''
<h1>status.json: this site's state, for other sites</h1>
<p class="lead">One small file at the site root, <a href="../../status.json">/status.json</a>, that another site or an agent can read instead of scraping pages: the story's status, the version, when the evidence was last checked, the counts, three headline facts with their status and sources, and the latest story. The SGit Newsroom's front page reads it while the story is developing, and its tracker checks for it before the newsroom's own section on the story becomes a pointer here.</p>
<p class="kv"><b>Schema</b> <code>{E(st["schema"])}</code> &middot; <b>rebuilt</b> on every release, from the same data as the pages, with no clock: if the evidence has not changed, neither has the file.</p>
{table(["Field", "Value now"], rows)}
<h2>The rules</h2>
<ul>
<li>Fields are only ever added. A reader of version 1 keeps working.</li>
<li>A headline fact is a claim id from <a href="../../claims/index.html">every claim</a>; its text and status are the claim's, never rewritten for the feed.</li>
<li><code>data_as_of</code> is the time of the latest capture in the evidence vault, not the time of the build.</li>
<li>No personal data, no credential, nothing that is not already on a page.</li>
</ul>
<pre>{E(text)}</pre>
'''
    page('admin/status-json/index.html', 'status.json: the feed for other sites', 'The machine-readable summary of this site at /status.json: status, version, data time, counts, headline facts and the latest story, for the newsroom and other agents.', body, kind='site')


# ----------------------------------------------------------------------------- the inventory over time, and the signals (v0.4.2)

# Status colours from the dataviz reference status palette (validated: adjacent CVD separation >= 10.6 in light and
# dark); the same in every theme by design, and never used for anything but a status. Text stays in text tokens.
INV_ST = OrderedDict([('Fix', ('Fixed', '#0ca30c')), ('Not vuln', ('Not affected', '#8a8f98')),
                      ('Vulnerable', ('Vulnerable', '#d03b3b')), ('Investigation', ('Under investigation', '#fab219'))])

def _mins(at):
    from datetime import datetime, timezone
    if re.match(r'^\d{4}-\d{2}-\d{2}$', at):
        at += 'T00:00Z'
    return int(datetime.strptime(at, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp() // 60)

def _hm(at):
    return human_time(at) if 'T' in at else nice_date(at)

def inventory_chart(snaps, marks):
    S = [s for s in snaps if s['rows']]
    W, H, L, R, T, B = 760, 300, 44, 168, 14, 42
    x0, x1 = _mins(S[0]['at']), _mins(S[-1]['at']) + 30
    ymax = int(math.ceil(max(s['rows'] for s in S) / 200.0) * 200)
    X = lambda m: L + (m - x0) * (W - L - R) / (x1 - x0)
    Y = lambda v: T + (H - T - B) * (1 - v / ymax)
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-labelledby="inv-t inv-d"><title id="inv-t">The NCSC-NL inventory by status, commit by commit</title>'
           f'<desc id="inv-d">{len(S)} commits from {_hm(S[0]["at"])} to {_hm(S[-1]["at"])}; the same numbers are in the table below.</desc>']
    for v in range(0, ymax + 1, 200):
        out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text class="ax" x="{L - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    lows, labels = [0] * len(S), []
    for st, (label, col) in INV_ST.items():
        highs = [lo + s['by_status'].get(st, 0) for lo, s in zip(lows, S)]
        top, bot = [], []
        for i, s in enumerate(S):
            xa, xb = X(_mins(s['at'])), X(_mins(S[i + 1]['at']) if i + 1 < len(S) else x1)
            top += [(xa, Y(highs[i])), (xb, Y(highs[i]))]
            bot += [(xa, Y(lows[i])), (xb, Y(lows[i]))]
        pts = top + bot[::-1]
        out.append(f'<path class="band" fill="{col}" d="M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + 'Z"/>')
        n, mid = S[-1]['by_status'].get(st, 0), (Y(lows[-1]) + Y(highs[-1])) / 2
        if n:
            labels.append([mid, col, f'{label} {n}'])
        lows = highs
    # direct labels at the right edge: thin bands put them on top of each other, so space them at least 14px apart
    labels.sort(key=lambda l: -l[0])
    for i in range(1, len(labels)):
        labels[i][0] = min(labels[i][0], labels[i - 1][0] - 14)
    for y, col, text in labels:
        out.append(f'<g class="dl"><rect x="{W - R + 8}" y="{y - 5:.1f}" width="10" height="10" rx="2" fill="{col}"/><text x="{W - R + 23}" y="{y + 4:.1f}">{E(text)}</text></g>')
    for m_at, m_label in marks:
        mx = X(_mins(m_at))
        if L <= mx <= W - R:
            out.append(f'<line class="mark" x1="{mx:.1f}" x2="{mx:.1f}" y1="{T}" y2="{H - B}"/><text class="ax" x="{mx + 4:.1f}" y="{T + 10}">{E(m_label)}</text>')
    for t in ('2026-10-21T12:00Z', '2026-10-21T18:00Z', '2026-10-22T00:00Z', '2026-10-22T06:00Z', '2026-10-22T12:00Z'):
        tx = X(_mins(t))
        if L <= tx <= W - R:
            out.append(f'<text class="ax" x="{tx:.1f}" y="{H - B + 16}" text-anchor="middle">{t[8:10]} Oct {t[11:16]}</text>')
    out.append(f'<text class="ax" x="{L}" y="{H - 6}">UTC; rows in the inventory</text>')
    for i, s in enumerate(S):
        xa, xb = X(_mins(s['at'])), X(_mins(S[i + 1]['at']) if i + 1 < len(S) else x1)
        tip = f'{_hm(s["at"])}, commit {s["commit"]}: {s["rows"]} rows; ' + ', '.join(f'{s["by_status"].get(k, 0)} {v[0].lower()}' for k, v in INV_ST.items())
        out.append(f'<rect class="hit" x="{xa:.1f}" y="{T}" width="{max(xb - xa, 1):.1f}" height="{H - T - B}"><title>{E(tip)}</title></rect>')
    out.append('</svg>')
    legend = '<ul class="legend">' + ''.join(f'<li><span class="sw" style="background:{c}"></span>{E(l)}</li>' for l, c in INV_ST.values()) + '</ul>'
    return legend + ''.join(out)

def build_inventory():
    H_ = D['inventory-history']; S = [s for s in H_['snapshots'] if s['rows']]
    first, last = S[0], S[-1]
    rel = '2026-10-21T14:00Z'
    chart = inventory_chart(H_['snapshots'], [(rel, 'release 14:00'), ('2026-10-22T08:40Z', 'vault capture')])
    tab = table(['When (UTC)', 'Commit', 'Rows'] + [v[0] for v in INV_ST.values()],
                [[E(_hm(s['at'])), f'<code>{E(s["commit"])}</code>', str(s['rows'])] + [str(s['by_status'].get(k, 0)) for k in INV_ST] for s in S])
    moves = Counter((c['from'], c['to']) for c in H_['changes'])
    name = lambda k: 'added to the list' if k == 'added' else (INV_ST[k][0].lower() if k in INV_ST else k)
    mv = table(['From', 'To', 'Rows'], [[E(name(a)), E(name(b)), str(n)] for (a, b), n in sorted(moves.items(), key=lambda kv: -kv[1])])
    cls = OrderedDict((c['id'], c) for c in H_['classes'])
    cc = Counter((r[3], r[2]) for r in H_['head_rows'])
    ct = table(['What kind of row', 'Rows'] + [v[0] for v in INV_ST.values()],
               [[E(c['name']), str(sum(cc[(cid, k)] for k in list(INV_ST) + ['none']))] + [str(cc[(cid, k)] or '') for k in INV_ST] for cid, c in cls.items() if any(cc[(cid, k)] for k in list(INV_ST) + ['none'])], 'ctx')
    sec = [r for r in H_['head_rows'] if r[3] == 'security-vendor']
    secv = ', '.join(f'<b>{E(r[1])}</b> ({E(r[0])})' for r in sec if r[2] == 'Vulnerable')
    secc = Counter(r[0] for r in sec if r[2] == 'Investigation')
    firstfix = OrderedDict()
    for c in H_['changes']:
        if c['to'] == 'Fix' and c['supplier'] not in firstfix:
            firstfix[c['supplier']] = c
    ff = table(['Recorded fixed (UTC)', 'Hours after release', 'Supplier', 'First product'], [[E(_hm(c['at'])), f'{(_mins(c["at"]) - _mins(rel)) / 60:.1f}', E(s_), E(c['product'])] for s_, c in list(firstfix.items())[:24]])
    lf = last['by_status']
    body = f'''
<h1>The inventory, hour by hour: fixed, vulnerable, still under investigation</h1>
<p class="lead">The Dutch NCSC keeps a public list of software that ships or depends on PHP, with a status for each product. This site captured it once, at 08:40 UTC on 22 October. Its git history shows the rest: {len(S)} versions from {E(_hm(first["at"]))} to {E(_hm(last["at"]))}, each read from the commit that made it. At the last one, {lf.get("Fix", 0)} of {last["rows"]} rows were fixed, {lf.get("Vulnerable", 0)} vulnerable and {lf.get("Investigation", 0)} still under investigation, about {(_mins(last["at"]) - _mins(rel)) / 60:.0f} hours after the release.</p>
<figure>{chart}<figcaption>Rows by status at every commit of the inventory that changed it. Hover a column for the commit and its counts; the table below has the same numbers. Read from a clone of <a href="{E(H_["source"])}">{E(H_["source"])}</a> at <code>{E(H_["head"])}</code>.</figcaption></figure>
<details><summary>The same numbers as a table</summary>{tab}</details>
{section("reading", "How to read it", f"""<ul>
<li><b>Vulnerable mostly means inherited.</b> {cc[("inherited", "Vulnerable")]} of the {lf.get("Vulnerable", 0)} vulnerable rows are applications the inventory marks <q>affected when deployed on an affected web-serving PHP runtime</q>. Their fix is patching PHP underneath them, not a release from their maker, so they stay vulnerable in the list whatever the server does. That is why only {moves[("Vulnerable", "Fix")]} row moved from vulnerable to fixed.</li>
<li><b>Fixes came from the people who ship PHP.</b> Operating systems, container images, platforms and hosting panels: the {lf.get("Fix", 0)} fixed rows are almost all runtimes, recorded from 15:30 UTC on 21 October.</li>
<li><b>The investigation pile grew while it shrank.</b> {moves[("Investigation", "Vulnerable")]} rows were resolved to vulnerable and {moves[("Investigation", "Fix")]} to fixed, and {moves[("added", "Investigation")]} new rows arrived under investigation.</li>
<li><b>The boxes in front run PHP too.</b> Vulnerable: {secv}. Under investigation: {", ".join(f"{E(k)} ({n})" for k, n in secc.most_common())}.</li>
</ul>""")}
{section("moves", "Every change of status", mv + "<p class=small>Between consecutive commits, per row. A row added already fixed counts as added.</p>")}
{section("kinds", "What kind of rows they are", ct + f"<p class=small>Read from each row's own <q>CVE assessment</q> line by {len(cls)} rules, applied in order; the rules are in <code>admin/build/inventory_history.py</code> and in <a href=\"../../data/inventory-history.json\">the data</a>. The words matched are the inventory's; the grouping is this site's.</p>")}
{section("first", "When each supplier was first recorded fixed", ff + "<p class=small>The time the inventory recorded the fix, not the time the supplier shipped it.</p>")}
{section("method", "Where this comes from", f"""<p>{E(H_["read_from"])}. Commits are content-addressed: anyone with a clone can check every number here against the commit named. The self-check: {E(H_["self_check"])}. That one row is a correction to this site's earlier counts, on <a href="../../corrections/index.html">corrections</a>. The vault holds the inventory at one commit; the history is not yet captured into it (board).</p>""")}
<p>The patching ladder, version by version, is on <a href="../index.html">Patching</a>; the signals this belongs to are on <a href="../../signals/index.html">The second stories</a>.</p>
'''
    page('patching/inventory/index.html', 'The inventory, hour by hour: fixed, vulnerable, still under investigation', f'The NCSC-NL php2shell inventory across {len(S)} commits: how {last["rows"]} products moved between fixed, vulnerable and under investigation after the release, what kind of products they are, and when each supplier was first recorded fixed.', body, kind='analysis', topics='php2shell patching inventory over time')

def _tl(at, x0, x1, w=240):
    """A one-row timeline cell: available from `at` to the right edge; a whole day when only the date is known."""
    if not at:
        return f'<svg class="tlc" viewBox="0 0 {w} 16" width="{w}" height="16" aria-hidden="true"><line class="grid" x1="0" x2="{w}" y1="8" y2="8"/></svg>'
    X = lambda m: max(0, min(w, (m - x0) * w / (x1 - x0)))
    if 'T' in at:
        a = X(_mins(at))
        return f'<svg class="tlc" viewBox="0 0 {w} 16" width="{w}" height="16" aria-hidden="true"><line class="grid" x1="0" x2="{w}" y1="8" y2="8"/><line class="avail" x1="{a:.1f}" x2="{w}" y1="8" y2="8"/><circle class="avail-d" cx="{a:.1f}" cy="8" r="4"/></svg>'
    a, b = X(_mins(at)), X(_mins(at) + 1440)
    return f'<svg class="tlc" viewBox="0 0 {w} 16" width="{w}" height="16" aria-hidden="true"><line class="grid" x1="0" x2="{w}" y1="8" y2="8"/><rect class="day" x="{a:.1f}" y="3" width="{b - a:.1f}" height="10" rx="2"/><line class="avail" x1="{b:.1f}" x2="{w}" y1="8" y2="8"/></svg>'

def _bar(l, top, w=140):
    """A cell mark for the ladder: a linear bar against the largest count of hosts (the units are the same), a line for
    zero, a dashed box for a layer nobody has measured, nothing for a share or for attempts (other units)."""
    if l['kind'] == 'count' and l.get('n'):
        return f'<svg class="tlc bar" viewBox="0 0 {w} 14" width="{w}" height="14" aria-hidden="true"><rect class="lb" x="0" y="2" width="{w * l["n"] / top:.1f}" height="10" rx="2"/></svg>'
    if l['kind'] == 'zero':
        return f'<svg class="tlc bar" viewBox="0 0 {w} 14" width="{w}" height="14" aria-hidden="true"><line class="zero" x1="1.5" x2="1.5" y1="0" y2="14"/></svg>'
    if l['kind'] == 'unknown':
        return f'<svg class="tlc bar" viewBox="0 0 {w} 14" width="{w}" height="14" aria-hidden="true"><rect class="unk" x="0.5" y="2.5" width="{w - 1}" height="9" rx="2"/></svg>'
    return ''

def build_signals():
    G = D['signals']; fam = {f['id']: f for f in G['families']}
    top = max(l.get('n') or 0 for l in G['ladder'] if l['kind'] == 'count')
    ladder = table(['Layer', 'How many', '', 'Signal', 'Status', 'Sources'],
                   [[f'<b>{E(l["layer"])}</b><div class="note">{E(l["of"])}</div>', f'<b>{E(l["value"])}</b>', _bar(l, top), f'<a href="#f-{E(l["family"])}">{E(fam[l["family"]]["name"].replace(" signals", "")) if l["family"] in fam else "exposure"}</a>', pill(l['status']), src_links(l['sources'], 1)] for l in G['ladder']], 'ladder')
    fams = ''.join(f'''<article class="role" id="f-{E(f["id"])}"><h3>{E(f["name"])}</h3><p><i>{E(f["question"])}</i></p><p><b>Now.</b> {E(f["now"])} <span class="refs">{src_links(f["sources"], 1)}</span></p><p><b>What would change it.</b> {E(f["watch"])}</p><p class="small"><a href="../{E(f["page"])}">Where this site tracks it &rarr;</a></p></article>''' for f in G['families'])
    x0, x1 = _mins('2026-10-21T00:00Z'), _mins('2026-10-22T16:00Z')
    bars = table(['Barrier', 'Available', '21 Oct 00:00 &rarr; 22 Oct 16:00 UTC', 'A compromise after it says the organisation had', 'Sources'],
                 [[f'<b>{E(b["what"])}</b>', E(_hm(b['at'])) if b['at'] else '<i>not a release</i>', _tl(b['at'], x0, x1) + f'<div class="note">{E(b["at_note"])}</div>', E(b['gap']), src_links(b['sources'], 1)] for b in G['barriers']], 'ladder')
    reading = ''.join(f'<li>{E(r)}</li>' for r in G['reading'])
    story = next((a for a in ARTICLES if a['slug'] == 'exposed-is-not-exploited'), None)
    body = f'''
<h1>The second stories: exposed, attempted, exploited, and what was within reach</h1>
<p class="lead">{E(G["note"])}</p>
{section("ladder", "From exposed to what matters", f'<p>Each layer is a smaller population than the one above, until the evidence runs out. The two bars are counts of the same thing, hosts, on one linear scale: 1.57 million of 2.6 million were unpatched on the first day; a dashed box is a layer nobody has measured; a single line is zero. The units change down the ladder, from a share of websites to hosts to attempts, and the ladder says so rather than drawing them as one funnel.</p>{ladder}')}
{section("families", "The four kinds of signal", f'<div class="roles">{fams}</div>', "The editor's four families: what each would show, what it shows now, and what would change it.")}
{section("barriers", "Every barrier has a time", f'<p>The barriers between this bug and a breach, with the moment each became available. A dot is a stated time; a band is a day with no time given. Read across: a compromise after the dot says something about the organisation, not only about PHP.</p>{bars}')}
{section("reading", "The reading", f'<ul>{reading}</ul><p class="small">This page is the site\'s analysis, marked as research because every row rests on captured sources; the argument it supports is made in {f"<a href=\"../articles/{E(story["slug"])}/index.html\">{E(story['title'])}</a>" if story else "a story"}.</p>')}
'''
    page('signals/index.html', 'The second stories: exposed, attempted, exploited, and what was within reach', 'php2shell as signals: the ladder from websites that use PHP to the sites that were exploited and held something worth reaching, the four kinds of signal and what each shows now, and the time each barrier became available.', body, kind='analysis', topics='php2shell signals exposure reach second stories')


# ----------------------------------------------------------------------------- items and feeds (v0.4.2)
# Everything a reader can read here is an item with a stable id and a hash of what it says. The ledger's sections,
# pages, briefings and facts keep their own versions (data/sections.json); stories, questions, sources and timeline
# events are versioned here, by hash only, in data/items.json, which the build reads back so an item keeps its
# version until what it says changes. The pages carry each item's id and hash in a hidden marker (.it); the reader's
# browser compares them with what it last read (assets/reader-state.js). The feeds are made from the same items.
import datetime
from email.utils import format_datetime

ITEMS_PATH = os.path.join(DATA, 'items.json')
ITEMS_PREV = (json.load(open(ITEMS_PATH, encoding='utf-8')).get('items', {}) if os.path.exists(ITEMS_PATH) else {})
ITEMS = OrderedDict()
FEED_ZONES = OrderedDict([('all', ('Everything', 'every new or changed fact, page, briefing, story, question, source and dated event')),
                          ('for-you', ('For you', 'the questions readers ask, the briefings, and the start-here pages')),
                          ('research', ('Research', 'the incident, the analysis and the evidence: facts, sources captured, dated events')),
                          ('stories', ('Stories', 'stories written here, signed and dated')),
                          ('site', ('About the site', 'the method, the vaults, the billing model and the site\'s own pages'))])
KIND_WORD = {'fact': 'Fact', 'page': 'Page', 'briefing': 'Briefing', 'front': 'Front page', 'story': 'Story', 'question': 'Question', 'source': 'Source', 'event': 'Timeline'}

def zone_of(path):
    for label, items in NAV:
        if any(pp == path for pp, _ in items):
            return {'For you': 'for-you', 'Research': 'research', 'Stories': 'stories', 'Site': 'site'}.get(ZONES.get(label, ''), 'site')
    if path.startswith(('facts/', 'sources/', 'actors/')):
        return 'research'
    if path.startswith('articles/'):
        return 'stories'
    if path.startswith(('briefings/', 'questions/')):
        return 'for-you'
    return 'site'

def item(iid, kind, zone, title, path, text, date):
    """Register an item, keep its version while its hash holds; return the hidden marker that goes on the page."""
    h = hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
    prev = ITEMS_PREV.get(iid)
    if prev and prev.get('hash') == h:
        v, first, changed, d = prev['v'], prev['first'], prev['changed'], prev['date']
    elif prev:
        v, first, changed, d = prev['v'] + 1, prev['first'], VERSION, REL_DATE.get(VERSION) or date
    else:
        v, first, changed, d = 1, VERSION, VERSION, date or REL_DATE.get(VERSION, '')
    ITEMS[iid] = {'kind': kind, 'zone': zone, 'title': title, 'path': path, 'hash': h, 'v': v, 'first': first, 'changed': changed, 'date': d}
    return f'<span class="it" data-item="{E(iid)}" data-h="{h}" data-n="{v}"></span>'

def it_ledger(sid):
    sec = LEDGER['sections'].get(sid)
    if not sec or not sec['versions']:
        return ''
    v = sec['versions'][-1]
    return f'<span class="it" data-item="{E(sid)}" data-h="{E(v["hash"])}" data-n="{v["v"]}"></span>'

def event_id(t):
    when = re.sub(r'[^0-9T]', '', t['at'])[:13]
    return 'ev-' + when + '-' + hashlib.sha256((t['at'] + '|' + ','.join(t['sources'])).encode()).hexdigest()[:6]

def it_event(t):
    return item(event_id(t), 'event', 'research', t['event'][:120], 'timeline/index.html',
                json.dumps([t['event'], t['confidence'], t['sources'], t.get('note')], ensure_ascii=False), parse_when(t['at']) or '')

def it_source(src):
    caps = sorted(parse_when(c.get('stamp')) or '' for c in src.get('captures', []))
    text = json.dumps([src.get('title'), src.get('status'), src.get('url'), [c.get('stamp') for c in src.get('captures', [])], src.get('notes_md') or ''], ensure_ascii=False)
    return item('src-' + src['slug'], 'source', 'research', ((src.get('publisher') or '') + ': ' + (src.get('title') or src['slug']))[:140],
                f'sources/{src["slug"]}/index.html', text, caps[-1] if caps else '')

def it_question(q):
    return item('q-' + q['id'], 'question', 'for-you', q['q'], f'questions/{q["id"]}/index.html', json.dumps(q, ensure_ascii=False, sort_keys=True), '')

def it_story(a):
    return item('story-' + a['slug'], 'story', 'stories', a['title'], f'articles/{a["slug"]}/index.html', a.get('text') or a['title'], str(a.get('written') or ''))

def all_items():
    """The ledger's items and the registry's, one list: what data/items.json and the feeds are made from."""
    out = OrderedDict()
    for sid, sec in LEDGER['sections'].items():
        if not sec['versions']:
            continue
        v = sec['versions'][-1]
        z = 'research' if sec['kind'] in ('front', 'fact') else 'for-you' if sec['kind'] == 'briefing' else zone_of(sec['path'])
        out[sid] = {'kind': sec['kind'], 'zone': z, 'title': sec['title'], 'path': sec['path'] + ('#' + sid[len('front-'):] if sec['kind'] == 'front' else ''),
                    'hash': v['hash'], 'v': v['v'], 'first': sec['versions'][0]['site'], 'changed': v['site'], 'date': v['date'],
                    'history': f'versions/{sid}/index.html'}
    for iid, it in ITEMS.items():
        out[iid] = it
    return out

def rfc822(d):
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?', d or '') or re.match(r'^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?', REL_DATE.get(VERSION) or '2026-10-22')
    hh, mm = (int(m.group(4)), int(m.group(5))) if m.group(4) else (0, 0)
    return format_datetime(datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), hh, mm, tzinfo=datetime.timezone.utc))

def feed_entries(zone):
    """One entry per item version the build knows: the ledger keeps every version; the registry its current one."""
    out = []
    for iid, it in all_items().items():
        if zone != 'all' and it['zone'] != zone:
            continue
        sec = LEDGER['sections'].get(iid)
        versions = [(x['v'], x['date'], x['site']) for x in sec['versions']] if sec else [(it['v'], it['date'], it['changed'])]
        for n, date, site in versions:
            out.append({'id': iid, 'n': n, 'date': date or REL_DATE.get(site, ''), 'site': site, 'it': it})
    out.sort(key=lambda e: (e['date'] or '', e['site'], e['id'], e['n']), reverse=True)
    return out[:150 if zone == 'all' else 80]

def build_feeds_xml():
    for zone, (name, what) in FEED_ZONES.items():
        items = ''
        for e in feed_entries(zone):
            it = e['it']
            word = 'New' if e['n'] == 1 else f'Updated (v{e["n"]})'
            desc = f'{KIND_WORD.get(it["kind"], it["kind"].title())}. ' + (f'{word} in site v{e["site"]}.' if e['id'] in LEDGER['sections'] or e['n'] > 1 else f'Dated {e["date"].replace("T", " ").rstrip("Z")}.')
            if it.get('history') and e['n'] > 1:
                desc += f' What changed: {BASE_URL}/{it["history"]}'
            title = KIND_WORD.get(it['kind'], '') + ': ' + it['title'] + ('' if e['n'] == 1 else ' (updated)')
            items += (f'<item><title>{E(title)}</title><link>{E(BASE_URL + "/" + it["path"])}</link>'
                      f'<guid isPermaLink="false">{E(e["id"])}@v{e["n"]}</guid><pubDate>{rfc822(e["date"])}</pubDate>'
                      f'<category>{E(it["kind"])}</category><description>{E(desc)}</description></item>\n')
        head = ('<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n'
                f'<title>{E(SITE_NAME)}: {E(name)}</title>\n<link>{BASE_URL}/</link>\n'
                f'<atom:link href="{BASE_URL}/feeds/{zone}.xml" rel="self" type="application/rss+xml"/>\n'
                f'<description>{E(SITE_NAME)}: {E(what)}. A new entry when an item is new, and again each time what it says changes.</description>\n'
                f'<language>en-gb</language>\n<lastBuildDate>{rfc822(REL_DATE.get(VERSION, ""))}</lastBuildDate>\n')
        write(f'feeds/{zone}.xml', head + items + '</channel>\n</rss>\n')

def save_items():
    OUTPUTS.add('data/items.json')
    doc = {'about': 'Every item a reader can read on this site, with its id, zone, link and the hash of what it says now. '
                    'assets/reader-state.js compares the hashes with what the reader last read, in their browser.',
           'site': VERSION, 'items': all_items()}
    out = json.dumps(doc, indent=0, ensure_ascii=False) + '\n'
    old = open(ITEMS_PATH, encoding='utf-8').read() if os.path.exists(ITEMS_PATH) else ''
    if out != old:
        write('data/items.json', out)

def feed_links(path):
    up, z = '../' * path.count('/'), zone_of(path)
    out = f'<link rel="alternate" type="application/rss+xml" title="{E(SITE_NAME)}: everything new and changed" href="{up}feeds/all.xml">'
    if z != 'all':
        out += f'\n<link rel="alternate" type="application/rss+xml" title="{E(SITE_NAME)}: {E(FEED_ZONES[z][0])}" href="{up}feeds/{z}.xml">'
    return out

def build_feeds_page():
    rows = ''.join(f'<article class="feedrow"><h3>{E(name)} <code>feeds/{z}.xml</code></h3><p>{E(what[0].upper() + what[1:])}.</p>'
                   f'<p class="small"><a href="../feeds/{z}.xml">The feed</a> &middot; <a href="../reader/index.html#site-{z}">read it here, with what you have read marked</a> &middot; '
                   f'or copy <code>{BASE_URL}/feeds/{z}.xml</code> into any feed reader</p></article>' for z, (name, what) in FEED_ZONES.items())
    body = f"""
<h1>Feeds: what is new and what changed, wherever you read</h1>
<p class="lead">Five RSS feeds: one for everything, one for each part of the site. An item enters a feed when it is new, and again every time what it says changes, so a fact that moves from reported to confirmed reaches you as an entry of its own, with a link to what changed. The release log has an Atom feed of its own, <a href="../feed.xml">feed.xml</a>.</p>
{rows}
<h2>Feeds from elsewhere</h2>
<p>The <a href="../reader/index.html">feed viewer</a> reads these feeds, the outside sources a browser is allowed to read directly (the CVE records, NVD, OSV, CISA's list of exploited flaws, Hacker News, Mastodon, GitHub), and any feed you add. What you have read is kept in your browser, with the rest of <a href="../you/index.html">your desk</a>.</p>
"""
    page('feeds/index.html', 'Feeds: what is new and what changed', 'RSS feeds for everything new and changed on this site and for each of its parts: an entry for every new item and every change, and where to read them.', body, kind='site')


# ----------------------------------------------------------------------------- yours: your desk and the feed viewer (v0.4.2)

def build_you():
    body = """
<h1>Your desk: what is new to you, and what changed since you read it</h1>
<p class="lead">This site keeps track of what you have read, in your browser, so the next visit costs you only what changed. Mark an item read (the circle beside it), or the whole page, or everything at once: from then on you see only what is new, and anything that changes after you read it comes back marked as changed, with a link to the change. The <b>&#8943;</b> beside any item takes a decision (read later, follow up, not for me) or a note of your own: a correction, a comment, an idea.</p>
<div id="desk"><p class="small">Your desk needs JavaScript: it is built in your browser from what this browser has kept.</p></div>
<h2>Where this is kept</h2>
<p>Only in this browser: what you read is under <code>p2s.reader.v1</code>, your decisions and notes under <code>sgit.notes.v1</code> in the same record format as <a href="https://newsroom.sgit.ai/">newsroom.sgit.ai</a>, the feeds you add under <code>p2s.feeds.v1</code>. Nothing is sent anywhere. Export your desk to keep it or to move it to another browser; the next step, from the newsroom, is to carry it into a vault of your own, encrypted, across your devices. How the site decides what is new and changed is in <a href="../admin/briefs/index.html#2026-10-22__feeds-the-delta-and-subscriptions">the brief</a>.</p>
<script src="../assets/desk.js" defer></script>
"""
    page('you/index.html', 'Your desk: what is new to you, and what changed', 'What is new to you on this site and what changed since you read it, by part of the site; what you put aside; your notes; all kept in your browser, exportable.', body, kind='account')

def build_reader():
    F = D['feed-sources']
    cfg = J({'feeds': F['feeds']}, ensure_ascii=False, separators=(',', ':'))
    body = f"""
<h1>The feed viewer: this site, the records, and your own feeds</h1>
<p class="lead">Every feed here is read by your browser, directly from its publisher, and what you have read in each is kept with the rest of <a href="../you/index.html">your desk</a>: the next time you come, a feed shows you only what is new or changed. This site's own <a href="../feeds/index.html">feeds</a> are first; then the outside sources a browser is allowed to read (the CVE records, NVD, OSV, CISA's catalog of exploited flaws, GitHub, Wikipedia, Hacker News, Mastodon); then the ones that do not allow it, and why. Add any feed you like below the list.</p>
<div id="viewer" class="fv"><p class="small">The viewer needs JavaScript.</p></div>
<script type="application/json" id="viewer-config">{cfg}</script>
<h2>What the viewer does with a feed</h2>
<ul>
<li>Your browser fetches it, with no cookies and no referrer, from the publisher; nothing goes through this site or anyone else.</li>
<li>Only https feeds, and never an address on your own network. At most 2 MB is read (5 MB for a records API), within 15 seconds.</li>
<li>A feed is shown as text: titles and summaries are parsed by the browser and only their words kept, so nothing in a feed can run on this page. Links open in a new tab, only when they are web links.</li>
<li>A publisher that does not allow other sites' pages to read its feed (no CORS header) cannot be read here. The viewer says so rather than routing it through a third party, which would see what you read. {E(F["about"].split(". ")[0])} on {E(F["checked"])}.</li>
</ul>
<script src="../assets/feed-viewer.js" defer></script>
"""
    page('reader/index.html', 'The feed viewer: this site, the records, and your own feeds', 'Read this site\'s feeds, the CVE records, NVD, OSV, CISA KEV, GitHub, Wikipedia, Hacker News and Mastodon, and any feed you add, in your browser, with what you have read marked and only what is new shown next time.', body, kind='account')


# ----------------------------------------------------------------------------- your stack: the blast radius (v0.8.1)

def stack_catalogue():
    """data/stack.json joined with the ranges, SAPIs and mitigations (affected), the edge vendors (defence) and the
    NCSC-NL inventory (software), for assets/stack.js. Everything in it is already published on this site."""
    st, a = D['stack'], D['affected']
    for v in st['vulns']:
        for slug in v['sources']:
            if slug not in SOURCES: sys.exit(f'data/stack.json: {v["id"]} cites unknown source {slug}')
    ctl = []
    for c in st['controls']:
        m = a['mitigations'][c['mitigation']]
        ctl.append(dict({k: c[k] for k in c if k != 'mitigation'}, what=m['what'], caveat=m['caveat'], **{'for': m['for']}))
    inv = []
    for r in D['software']['rows']:
        note = (r['notes'] or '').split('\n')
        inv.append([r['supplier'], r['product'], r['version'], r['status_109618'], r['status_109619'],
                    (note[-1] if len(note) > 1 else note[0])[:280], (r['links'] or [''])[0]])
    items = [[iid, it['title'], it['path'], it['kind']] for iid, it in all_items().items() if it.get('path')]
    return {'schema': st['schema'], 'site': VERSION, 'data_as_of': STORY['data_as_of'],
            'kinds': st['kinds'], 'links': st['links'], 'sensitivity': st['sensitivity'], 'controls': ctl, 'vulns': st['vulns'],
            'ranges': a['ranges'], 'ranges_note': a['ranges_note'], 'fixed': a['fixed'],
            'sapis': [{k: x[k] for k in ('sapi', 'risk', 'text')} for x in a['sapis']],
            'edge': [{k: x[k] for k in ('vendor', 'what', 'when', 'caveat')} for x in D['defence']['edge']],
            'inventory': {'source': D['software']['source'], 'commit': D['software']['commit'], 'licence': D['software']['licence'],
                          'columns': ['supplier', 'product', 'version', 'status_109618', 'status_109619', 'note', 'link'], 'rows': inv},
            'items': items, 'examples': st['examples'], 'pulse': st['pulse']}

def build_stack_catalogue():
    write('stack/catalogue.json', json.dumps(stack_catalogue(), ensure_ascii=False, separators=(',', ':'), sort_keys=False) + '\n')

def build_stack():
    st = D['stack']
    kinds = ''.join(f'<li><b>{E(k["name"])}.</b> {E(k["what"])}</li>' for k in st['kinds'])
    vulns = ''.join(f'<li><a href="../{U(v["page"])}">{E(v["id"])}</a>: {E(v["name"])}. Scope: {E(v["scope"])}; at worst {E(v["impact"])}.</li>' for v in st['vulns'])
    body = f"""
<h1>Your stack: what php2shell can reach in it</h1>
<p class="lead">Describe what you run, the way you would draw it on a whiteboard: what the internet reaches, what sits in front, the applications, the PHP under them and where it comes from, and what each can reach. The tool checks every PHP runtime against the two flaws with what this site knows (the version ranges, how PHP serves requests, the settings that reduce exposure, the edge rules, the NCSC-NL inventory) and shows the blast radius: what an attacker who runs code as your PHP worker can touch. Then it lists what on this site is about your stack.</p>
<div id="stack" class="sk"><p class="small">The tool needs JavaScript: it runs in your browser, on <a href="catalogue.json">its catalogue</a>, and sends nothing anywhere.</p></div>
<h2>How it decides</h2>
<ul>
<li><b>The version.</b> A runtime on a supported branch is affected below the fixed release ({E(', '.join(D['affected']['fixed']))}) and fixed at or above it. 8.1, 8.0 and 7.4 are affected with no upstream release, only backport branches; earlier versions have no fix at all. {E(D['affected']['ranges_note'])}</li>
<li><b>Where the PHP comes from.</b> A distribution package or a vendor image keeps its own version number when it backports a fix, so a version that looks old can be fixed. When the runtime is provided by a product in the inventory, the inventory's status for that product wins over the version number, and the tool says so.</li>
<li><b>How it serves requests.</b> The risk is for PHP serving web requests; Apache mod_php is where remote code execution was demonstrated. CLI, cron and queue workers are outside the advisory's scope.</li>
<li><b>Whether it can be reached.</b> A runtime the internet reaches, through an edge or not, is exposed; one reached only from inside is not exposed from the internet, which is not the same as safe.</li>
<li><b>What reduces it.</b> Each setting and each edge rule is shown with its caveat. None of them turns an affected runtime into a fixed one: updating is the only reliable mitigation.</li>
<li><b>The blast radius.</b> Remote code execution runs as the PHP worker, so everything an affected runtime runs, and everything it or its applications can reach, is in the blast radius; what those can reach in turn is one step further.</li>
</ul>
<p>The kinds of component:</p>
<ul>{kinds}</ul>
<p>What is checked today:</p>
<ul>{vulns}</ul>
<p class="small">{E(st['pulse'])}</p>
<h2>Where your stack is kept</h2>
<p>In this browser, under <code>p2s.stack.v1</code>, and in your own vault when you open it in the Ask pane (under <code>/php-october/stack/</code>, encrypted here before it leaves), with the rest of what you keep on this site. Export it as a file to share it with your team; import theirs. Nothing about your stack is sent to this site or anyone else. A stack describes your systems: treat the file as you would an architecture diagram.</p>
<p class="small">This is a first version, a thinking tool and not a scanner: it knows only what you tell it and what this site has captured. Check every finding against your own systems and your vendor's advisory.</p>
<script src="../assets/stack.js" defer></script>
"""
    page('stack/index.html', 'Your stack: what php2shell can reach in it', 'Describe what you run, the internet, the edge, the applications, the PHP and where it comes from, and what each can reach; see which runtimes the two flaws affect, the blast radius, what to do first and what on this site is about your stack. In your browser and your own vault.', body, kind='account')

# ----------------------------------------------------------------------------- subscriptions (v0.4.3)

def build_subscribe():
    sc = D['subscriptions']
    cfg = J({k: sc[k] for k in ('contact', 'endpoint', 'vault_id', 'append_token', 'recipient', 'zones', 'cadences')}, ensure_ascii=False, separators=(',', ':'))
    zones = ''.join(f'<label class="sub-c"><input type="checkbox" name="zones" value="{E(z)}"{" checked" if z == "all" else ""}> {E(t)}</label>' for z, t in sc['zones'])
    cads = ''.join(f'<label class="sub-c"><input type="radio" name="cadence" value="{E(c)}"{" checked" if i == 1 else ""}> {E(t)}</label>' for i, (c, t) in enumerate(sc['cadences']))
    mail = f'mailto:{sc["contact"]}?subject=' + 'Subscribe%20to%20PHP%20October%202026' + '&body=' + 'Please%20subscribe%20me.%20Follow%3A%20everything%20%2F%20research%20%2F%20for%20you%20%2F%20stories.%20How%20often%3A%20as%20it%20changes%20%2F%20daily%20%2F%20weekly.'
    body = f"""
<h1>Subscribe: what changed, sent to you</h1>
<p class="lead">The cheapest way to follow this story is to be told only what changed. Pick what to follow and how often, and the agent at <a href="mailto:{E(sc["contact"])}">{E(sc["contact"])}</a> sends it: a message per release that changes what you follow, or a digest. No account; one address. Or skip email entirely: the <a href="../feeds/index.html">feeds</a> carry the same changes.</p>
<form id="sub-form" class="subform" autocomplete="on">
<p><label>Your email address<br><input type="email" name="email" required maxlength="254" placeholder="you@example.org"></label></p>
<fieldset><legend>What to follow</legend>{zones}</fieldset>
<fieldset><legend>How often</legend>{cads}</fieldset>
<p><label>Anything we should know (optional)<br><textarea name="note" rows="2" maxlength="500"></textarea></label></p>
<p class="sub-hp" aria-hidden="true"><label>Leave this empty <input type="text" name="website" tabindex="-1" autocomplete="off"></label></p>
<p><button class="cta cta-pri" type="submit" name="kind" value="subscribe">Subscribe</button> <button class="cta" type="submit" name="kind" value="unsubscribe" formnovalidate>Unsubscribe this address</button></p>
<p id="sub-out" role="status" aria-live="polite"></p>
</form>
<script type="application/json" id="sub-config">{cfg}</script>
<p>Rather write? <a href="{E(mail)}">Email {E(sc["contact"])}</a> and say what you want to follow.</p>
<h2>What happens to your address</h2>
<ul>
<li>It is encrypted in your browser, to the subscriptions vault's key (<code>{E(sc["recipient"]["fingerprint"])}</code>), and posted to a write-only lane on that private vault (<code>{E(sc["vault_id"])}</code>). The lane answers the same whatever arrives, so this page can say it was sent, never that it was received.</li>
<li>Anyone can type any address, so the agent writes to it first and sends nothing more until the address answers. Unsubscribe here, or by answering any message.</li>
<li>It is kept in that vault and nowhere else: not on this site, not in its repository, not in its telemetry. The vault's key is held by the editor and the agent that sends.</li>
<li>Messages come from {E(sc["contact"])}, the agent the editor runs and reads, until the newsroom has a domain of its own for them.</li>
</ul>
<script src="../assets/subscribe.js" defer></script>
"""
    page('subscribe/index.html', 'Subscribe: what changed, sent to you', 'Follow the PHP flaws story by email: everything or one part of the site, as it changes or as a digest; the address encrypted in your browser and confirmed before anything is sent.', body, kind='account')




# ----------------------------------------------------------------------------- the phone app: Now (v0.5.0)
# The editor's brief: admin/content/briefs/2026-10-22__brief__the-phone-app.md. One page, now/index.html, built for a
# phone: what do I need to know, given how long I have (one, five, ten or thirty minutes), against what I read before.
# Two modes. Deterministic: the items, their order and their connections come from the data and nothing else.
# Agentic: the same items handed to a model (OpenRouter, with the reader's own key kept in the reader's own vault), for
# a briefing in prose, an infographic and a chat. The page is a shell; now/now.json is everything it reads; assets/now.js
# is the app. The reader's state lives in this browser (assets/reader-state.js, shared with the rest of the site) and,
# when the reader opens a vault, in that vault under /php-october/.

NOW_MODELS = {'text': 'anthropic/claude-sonnet-5.5', 'image': 'google/gemini-3.1-flash-image'}
NOW_KIND_WEIGHT = {'front': 100, 'fact': 80, 'event': 60, 'question': 55, 'briefing': 50, 'story': 45, 'page': 30, 'source': 10}

def now_summary(iid, it):
    """The words the app shows for an item: what it says now, in a sentence or two, and its connections."""
    k, links, status = it['kind'], [], ''
    if k == 'fact':
        c = next((c for c in D['claims'] if 'fact-' + c['id'] == iid), None)
        if c:
            status = c['status']
            links = [['source', s, short_name(SOURCES[s]), f'sources/{s}/index.html'] for s in c['sources'] if s in SOURCES]
            links += [['briefing', p, PERSONAS[p]['label'], f'briefings/{p}/index.html'] for p, t in BRIEF_TOPICS.items() if c['topic'] in t and p in PERSONAS]
            claim = c['claim'].rstrip()
            return f'{claim}{"" if claim.endswith((".", "?", "!")) else "."} Who says it: {c["by"]}.', status, links
    if k == 'event':
        t = next((t for t in D['timeline'] if event_id(t) == iid), None)
        if t:
            links = [['source', s, short_name(SOURCES[s]), f'sources/{s}/index.html'] for s in t['sources'] if s in SOURCES]
            return f'{fmt_at(t["at"])}: {t["event"]}', t.get('confidence', ''), links
    if k == 'question':
        q = next((q for q in D['questions']['questions'] if 'q-' + q['id'] == iid), None)
        if q:
            return q.get('short') or q['q'], '', [['page', p, nav_title(p), p] for p in (q.get('see') or [])[:4]]
    if k == 'briefing':
        p = PERSONAS.get(iid.replace('briefing-', ''))
        if p:
            return p['answer'], '', [['page', x, nav_title(x), x] for x in p['path'][1:]]
    if k == 'front':
        sec = LEDGER['sections'].get(iid)
        if sec:
            t = re.sub(r'\s*\[[^\]]*\]', '', sec['versions'][-1]['text'])
            t = re.sub(r'(?m)^(confirmed|reported|disputed|contradicted|unverified): ', '', t)
            t = ' '.join(x.strip().rstrip('.') + '.' for x in t.split('\n') if x.strip())
            return (t[:420].rsplit('. ', 1)[0] + '.') if len(t) > 420 else t, '', []
    if k == 'source':
        s = SOURCES.get(iid.replace('src-', ''))
        if s:
            return (s.get('notes') or s.get('title') or '')[:300], s.get('status', ''), []
    if k == 'story':
        a = next((a for a in ARTICLES if 'story-' + a.get('slug', '') == iid), None)
        if a:
            return (a.get('dek') or a.get('standfirst') or a.get('text') or a['title'])[:400], '', []
    return D['plain']['pages'].get(it['path'], '') or it['title'], '', []

def build_now():
    items = []
    for iid, it in all_items().items():
        text, status, links = now_summary(iid, it)
        words = len((it['title'] + ' ' + text).split())
        title = it['title']
        if it['kind'] == 'fact':
            c = next((c for c in D['claims'] if 'fact-' + c['id'] == iid), None)
            title = c['claim'] if c else title
        items.append({'id': iid, 'kind': it['kind'], 'zone': it['zone'], 'title': title, 'path': it['path'], 'hash': it['hash'],
                      'v': it['v'], 'first': it['first'], 'changed': it['changed'], 'date': it['date'], 'text': text, 'status': status,
                      'links': links[:8], 'w': NOW_KIND_WEIGHT.get(it['kind'], 20), 'sec': max(10, round(words / 230 * 60)),
                      'history': it.get('history', '')})
    pl = D['plain']
    doc = {
        'about': 'Everything the phone app (now/) reads, built from the same data as every page: the items a reader can read, '
                 'with what each says now, its hash, its connections and its reading time; the situation; the readers; the facts '
                 'for grounding a model. Deterministic: the same data produces the same file.',
        'site': VERSION, 'data_as_of': STORY['data_as_of'], 'when': human_time(STORY['data_as_of']),
        'releases': [{'version': r['version'], 'date': r['date'], 'title': r['title']} for r in reversed(RELEASES)][:20],
        'headline': pl['headline'], 'deck': re.sub(r'<[^>]+>', '', pl['deck']),
        'now': [{'text': x['text'], 'sources': [[s, short_name(SOURCES[s])] for s in x['sources'] if s in SOURCES]} for x in pl['now']],
        'unknown': [u['text'] for u in pl['unknown']],
        'facts': [{'text': f['text'], 'status': f['status'], 'href': f['href']} for f in pl['facts']],
        'personas': [{'id': p['id'], 'person': p['person'], 'label': p['label'], 'group': p['group'], 'depth': p['depth'], 'answer': p['answer'],
                      'path': p['path']} for p in PERSONAS.values()],
        'claims': [{'id': c['id'], 'status': c['status'], 'claim': c['claim'], 'by': c['by'], 'topic': c['topic']} for c in D['claims']],
        'models': NOW_MODELS,
        'vault': {'endpoint': 'https://dev.send.sgraph.ai', 'folder': '/php-october'},
        'items': items,
    }
    write('now/now.json', json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n')
    write('now/manifest.webmanifest', json.dumps({
        'name': 'PHP October 2026: Now', 'short_name': 'PHP Now', 'start_url': './index.html', 'scope': './', 'display': 'standalone',
        'background_color': '#f7f6f2', 'theme_color': '#8a2416', 'description': 'What you need to know about the PHP flaws, for the time you have.',
        'icons': [{'src': '../assets/now/icon-192.png', 'sizes': '192x192', 'type': 'image/png'}, {'src': '../assets/now/icon-512.png', 'sizes': '512x512', 'type': 'image/png'}]},
        indent=1) + '\n')
    title = 'Now: PHP October on your phone'
    desc = 'What you need to know about the PHP flaws for the time you have, one, five, ten or thirty minutes, against what you read before; deterministic from the data, or written by a model with your own key kept in your own vault, with a chat.'
    PAGES.append(('now/index.html', title, desc, 'account'))
    html_out = f'''<!doctype html>
<html lang="en" data-root="../" data-path="now/index.html" data-ver="{VERSION}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#8a2416">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="PHP Now">
<title>{E(title)} &middot; {SITE_NAME}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{BASE_URL}/now/index.html">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="../assets/now/icon-192.png">
<link rel="icon" href="data:,">
<link rel="alternate" type="text/markdown" href="index.md">
<link rel="stylesheet" href="../assets/now/now.css">
<script src="../assets/reader-state.js" defer></script>
<script src="../assets/telemetry.js" defer></script>
<script type="module" src="../assets/now/now.js"></script>
</head>
<body>
<div id="app" class="app">
<header class="top"><a class="brand" href="../index.html">PHP October<span> 2026</span></a><span class="b-now">Now</span><button class="vchip" id="vchip" type="button">This phone only</button></header>
<main id="view"><section class="card"><h1>What you need to know, for the time you have</h1><p>{E(pl["headline"])}. {E(re.sub(r"<[^>]+>", "", pl["deck"]))}</p><p>This app needs JavaScript. Without it, start from <a href="../index.html">the front page</a> or <a href="../whatsnew/index.html">what's new</a>.</p></section></main>
<nav class="tabs" id="tabs"><a href="#now" data-tab="now">Now</a><a href="#chat" data-tab="chat">Ask</a><a href="#vault" data-tab="vault">Vault &amp; keys</a></nav>
</div>
</body>
</html>
'''
    write('now/index.html', html_out)
    md = f'''# {title}

{desc}

> For you: an app in your browser, kept by the agents that run this site.

The phone app at {BASE_URL}/now/index.html answers one question: what do I need to know now, given how long I have? Choose one, five, ten or thirty minutes; it shows what is new or changed since you last read it, most important first, until the time is used. If nothing is new, it says so.

## Two modes

- **Deterministic**: the items, their order and their connections (each fact to its sources and to the briefings that carry it) come from the site's data and nothing else. The same data gives the same answer.
- **Agentic**: the same items handed to a model through OpenRouter with your own key: a briefing in prose for your time budget (Claude Sonnet), an infographic (Gemini), and a chat grounded in the site's facts. Every generated piece says which model wrote it from which items, and links each claim back to its fact.

## Your vault

Open a vault (an sgit vault key; a newsroom.sgit.ai reader vault works) or create one, and the app keeps in it, encrypted in your browser before it leaves: what you have read, your settings, your OpenRouter key, your chats and what the models made for you, under `/php-october/`. Without a vault, what you have read is kept in this browser only and the agentic mode is off.

The data the app reads is [now.json]({BASE_URL}/now/now.json). The brief is on [the briefs page]({BASE_URL}/admin/briefs/index.html).

---
site v{VERSION} · data as of {STORY["data_as_of"]} · {BASE_URL}/now/index.html
'''
    write('now/index.md', md)
# ----------------------------------------------------------------------------- the fact-check desk (factcheck@php.newsroom)

FC = load('factcheck') if os.path.exists(os.path.join(DATA, 'factcheck.json')) else None
FCA = {a['id']: a for a in FC['assessments']} if FC else {}
FCL = {l['n']: l for l in FC['levels']} if FC else {}
FC_KIND_WORD = {'record': 'Record', 'event': 'Event', 'state': 'State', 'count': 'Count', 'quote': 'Quote', 'attribution': 'Attribution', 'reading': 'Opinion', 'advice': 'Advice'}

def assure(cid, short=False):
    """The desk's grade for a claim as a badge: the level's code, name and a six-dot meter, so it never rests on colour alone."""
    a = FCA.get(cid)
    if not a:
        return '<span class="as as-none" title="Not yet checked by the fact-check desk">not checked</span>'
    n = a['display']
    lv = FCL[n]
    dots = '&#9679;' * n + '&#9675;' * (6 - n)
    if a['verdict'] == 'refuted':
        b = f'<span class="as as-ref" title="Refuted: a stronger source says otherwise">refuted</span>'
    else:
        b = f'<span class="as as-{n}" title="{E(lv["means"])}"><b>{E(lv["code"])}</b> {E(lv["name"])}<i aria-hidden="true">{dots}</i></span>'
    if short:
        return b
    extra = ''
    if a['kind'] == 'reading':
        extra += ' <span class="as-k">opinion</span>'
    if a.get('tension', 'none') not in ('none',):
        extra += f' <span class="as-k as-t">{E(a["tension"].replace("-", " "))}</span>'
    if a.get('status_fit') == 'overstated':
        extra += ' <span class="as-k as-t" title="The status word claims more than the evidence carries">status overstated</span>'
    return b + extra

def fc_status_line(cid, depth):
    a = FCA.get(cid)
    if not a:
        return ''
    t = ''.join(f' <a href="{"../" * depth}factcheck/index.html#{E(l)}">{E(l)}</a>' for l in a.get('tickets', []))
    return f'<div class="note"><b>Fact-check:</b> {assure(cid)} {E(a["reason"])}{(" Tickets:" + t) if t else ""}</div>'

def fc_section(cid):
    a = FCA.get(cid)
    if not a:
        return section('factcheck', 'Fact-check', '<p class="small">Not yet checked by the <a href="../../factcheck/index.html">fact-check desk</a>.</p>') if FC else ''
    rows = [[f'<a href="../../sources/{E(x["source"])}/index.html">{E(x["source"])}</a>' if x['source'] in SOURCES else f'{E(x["source"])} <span class="small">(in the vault, not yet on this site)</span>',
             E(x['result']), f'<q>{E(x["excerpt"])}</q>' if x.get('excerpt') else '<i>nothing that carries it</i>', f'<code title="{E(x.get("file", ""))}">{E((x.get("sha256") or "")[:16])}</code>'] for x in a.get('checked', [])]
    tk = ', '.join(f'<a href="../../factcheck/index.html#{E(l)}">{E(l)}</a>' for l in a.get('tickets', []))
    inner = (f'<p>{assure(cid)} &middot; {E(FC_KIND_WORD.get(a["kind"], a["kind"]))} &middot; verdict: <b>{E(a["verdict"].replace("-", " "))}</b>'
             f'{" &middot; the status word overstates the evidence" if a.get("status_fit") == "overstated" else ""}{" &middot; the status word understates the evidence" if a.get("status_fit") == "understated" else ""}</p>'
             f'<p>{E(a["reason"])}</p>' + (table(['Capture checked', 'Result', 'What it says', 'sha256 of the text read'], rows) if rows else '') +
             (f'<p>Open tickets: {tk}.</p>' if tk else '') + f'<p class="small">Graded in {E(a.get("run", ""))}, resting on captures up to {E(fmt_at(parse_when(a.get("as_of")) or "") if a.get("as_of") else "")}. The scale is on <a href="../../factcheck/index.html#ladder">the fact-check page</a>.</p>')
    return section('factcheck', 'Fact-check', inner)

def build_factcheck():
    if not FC:
        return
    A, K, T, R = FC['assessments'], FC['contradictions'], FC['tickets'], FC['runs']
    claims = {c['id']: c for c in D['claims']}
    by_lv = Counter(a['display'] for a in A if a['verdict'] != 'refuted')
    refuted = sum(1 for a in A if a['verdict'] == 'refuted')
    flagged = {c for t in T if t['type'] in ('finding', 'gap') and t['severity'] in ('medium', 'high') and t['status'] in ('open', 'acknowledged') for c in t['claims']}
    comfy = [a for a in A if a['display'] >= 5 and a['verdict'] == 'holds' and a.get('tension', 'none') == 'none' and a['kind'] != 'reading' and a['id'] not in flagged]
    over = [a for a in A if a.get('status_fit') == 'overstated']
    open_t = [t for t in T if t['status'] in ('open', 'proposed', 'acknowledged')]
    last = R[-1] if R else {}
    ladder = table(['Level', 'Means', 'Claims now'], [[f'<span class="as as-{l["n"]}"><b>{E(l["code"])}</b> {E(l["name"])}<i aria-hidden="true">{"&#9679;" * l["n"] + "&#9675;" * (6 - l["n"])}</i></span>', E(l['means']), str(by_lv.get(l['n'], 0))] for l in FC['levels']] +
                   [['<span class="as as-ref">refuted</span>', 'A stronger source says otherwise', str(refuted)]])
    rows = []
    for a in sorted(A, key=lambda a: (-a['display'] if a['verdict'] != 'refuted' else 1, a['id'])):
        c = claims[a['id']]
        tk = ' '.join(f'<a href="#{E(l)}">{E(l)}</a>' for l in a.get('tickets', []))
        rows.append(f'<tr data-lv="{-1 if a["verdict"] == "refuted" else a["display"]}" data-kind="{E(a["kind"])}" data-t="{E(a.get("tension", "none"))}" data-v="{E(a["verdict"])}" data-f="{1 if a["id"] in flagged else 0}">'
                    f'<td><a href="../facts/{E(a["id"])}/index.html">{E(c["claim"])}</a><div class="note">{E(a["reason"])}</div></td>'
                    f'<td>{assure(a["id"])}</td><td>{E(FC_KIND_WORD.get(a["kind"], a["kind"]))}</td><td>{E(a["verdict"].replace("-", " "))}</td><td>{pill(c["status"])}</td><td>{tk}</td></tr>')
    th = ''.join(f'<th>{h}</th>' for h in ['Claim, and why it is graded so', 'Fact-check', 'Kind', 'Verdict', 'Site status', 'Tickets'])
    grid = f'<div class="tw"><table class="t fc-grid"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    filt = '''<form class="fc-filter" aria-label="Filter claims by assurance"><label>Show claims graded at least <select id="fc-min"><option value="-1">everything, refuted too</option><option value="0">A0</option><option value="2">A2 Reported</option><option value="4">A4 Corroborated</option><option value="5">A5 Confirmed</option><option value="6">A6 Established</option></select></label>
<label><input type="checkbox" id="fc-op" checked> include opinions</label> <label><input type="checkbox" id="fc-tn" checked> include contested</label> <button type="button" id="fc-comfy">Only what I can be very sure of</button> <span id="fc-n" class="small"></span></form>
<script>(function(){var m=document.getElementById("fc-min"),o=document.getElementById("fc-op"),t=document.getElementById("fc-tn"),n=document.getElementById("fc-n"),rs=document.querySelectorAll(".fc-grid tbody tr");
function f(){var k=0;rs.forEach(function(r){var s=+r.dataset.lv>=+m.value&&(o.checked||r.dataset.kind!=="reading")&&(t.checked||r.dataset.t==="none");if(+m.value>=5&&(r.dataset.v!=="holds"||r.dataset.f==="1"))s=false;r.hidden=!s;if(s)k++});n.textContent=k+" of "+rs.length+" claims shown";}
[m,o,t].forEach(function(x){x.addEventListener("change",f)});document.getElementById("fc-comfy").addEventListener("click",function(){m.value="5";o.checked=false;t.checked=false;f()});f();})();</script>'''
    ks = []
    for k in K:
        st = ''.join(f'<li><b>{E(s["who"])}</b>{(", " + E(s["when"])) if s.get("when") else ""}: <q>{E(s["says"])}</q> <span class="small">{E(s.get("measures", ""))}</span> {src_links([x for x in s.get("sources", []) if x in SOURCES], 1)}{"".join(f" <span class=small>(outside the vault: {E(u)})</span>" for u in s.get("outside", []))}</li>' for s in k['statements'])
        ks.append(f'<article class="role" id="{E(k["id"])}"><h3>{E(k["measure"])} <span class="st st-{"contradicted" if k["status"] == "open" else "confirmed"}">{E(k["status"])}</span></h3><ul>{st}</ul><p><b>The desk\'s reading.</b> {E(k["reading"])}</p>{("<p><b>What would settle it.</b> " + E(k["settle"]) + "</p>") if k.get("settle") else ""}<p class="small">{E(k["id"])}{(" &middot; ticket " + E(k["ticket"])) if k.get("ticket") else ""}{(" &middot; claims: " + ", ".join(f"<a href=\"../facts/{E(c)}/index.html\">{E(c)}</a>" for c in k.get("claims", []))) if k.get("claims") else ""}</p></article>')
    def trow(t):
        extra = ''
        if t['type'] == 'evidence' and t.get('url'):
            extra = f'<div class="note">Found at <a href="{U(t["url"])}" rel="noopener">{E(re.sub(r"^https?://", "", t["url"])[:70])}</a>, {E(t["retrieved_at"])}, sha256 <code>{E(t["sha256"][:16])}</code>. Not cited until captured.{(" <q>" + E(t["excerpt"]) + "</q>") if t.get("excerpt") else ""}</div>'
        about = ', '.join(f'<a href="../facts/{E(c)}/index.html">{E(c)}</a>' for c in t['claims'] if c in claims)
        return [f'<span id="{E(t["label"])}">{E(t["label"])}</span>', f'<b>{E(t["title"])}</b><div class="note">{E(t["description"])}</div>{extra}', E(t['severity']), f'<span class="st st-{"unverified" if t["status"] in ("open", "proposed") else "confirmed"}">{E(t["status"])}</span>', about]
    groups = OrderedDict([('finding', 'Findings: things on this site to change'), ('contradiction', 'Contradictions between sources'), ('gap', 'Evidence gaps'), ('evidence', 'New evidence found outside the vault')])
    tix = ''.join(section('t-' + g, f'{title} ({sum(1 for t in T if t["type"] == g)})', table(['Ticket', 'What', 'Severity', 'Status', 'About'], [trow(t) for t in T if t['type'] == g])) for g, title in groups.items() if any(t['type'] == g for t in T))
    runs = table(['Run', 'Against', 'Checked', 'Opened', 'Summary'], [[E(r['id']), f'site v{E(r["site_version"])}, vault <code>{E(r["vault_commit"])}</code>', E(r['checked']), E(str(r.get('opened', ''))), E(r['summary'])] for r in reversed(R)])
    body = f'''
<h1>Fact-check: how sure can you be of each claim</h1>
<p class="lead">Every claim on this site has a status word chosen by the agent that wrote it. The fact-check desk grades each one again, independently, by opening the captures it cites and reading them: what kind of statement it is (a record, a count, a quote, an opinion), how strong the evidence is on a scale from A0 to A6, whether anything contradicts it, and whether the status word claims more than the evidence carries. Where the answer is "not as far as the site says", it opens a ticket. It highlights; it does not fix.</p>
<p><b>{len(A)} of {len(claims)} claims graded</b>{(", last run " + E(last.get("id", "")) + " against vault commit <code>" + E(last.get("vault_commit", "")) + "</code>") if last else ""}. <b>{len(comfy)}</b> can be relied on without reservation (A5 or A6, holding as worded, uncontested, not an opinion, and no open finding against their wording). <b>{len(over)}</b> carry a status word stronger than their evidence. <b>{len(open_t)}</b> tickets are open.</p>
{section("ladder", "The spectrum of evidence", ladder + '<p>A level is earned from captures the desk opened and read, never from how often a thing is repeated: ten outlets restating one headline are one source. An open contradiction caps a claim at A1 and a dispute at A2 until it is explained. An opinion is shown as an opinion and never rises above A3 as a fact; the facts under it are graded in its note. Absence of evidence is <i>not shown</i>, which is not the same as false.</p>')}
{section("claims", "Every claim, graded", filt.split("<script>")[0] + grid + "<script>" + filt.split("<script>")[1], 'Pick how sure you need to be. "Only what I can be very sure of" shows claims at A5 or A6 that hold as worded, are not contested, are not opinions, and have no open finding of medium or high severity against them.')}
{section("contradictions", "The contradiction ledger", "".join(ks) or "<p>None recorded yet.</p>", "Where the reporting disagrees. Each record keeps every statement, who made it and when, what each actually measures, and the desk's reading of why they differ. A contradiction is not resolved by picking a winner; it is explained, or it stays open.")}
{tix}
{section("investigations", "Investigations", '<p>Where a claim needs more than a grade, the desk chases the question down to its measurements: <a href="investigations/index.html">the investigations</a>, starting with how much PHP there is and where &#39;70%&#39; comes from.</p>')}
{section("runs", "Runs", runs, "Each run is checked against a stated site version and vault commit, so its grades can be repeated by anyone with the vault's read key.")}
{section("how", "How the desk works", '<p>The desk is <code>factcheck@php.newsroom</code>. Its role, the full model and the runbook a scheduled run follows are in <a href="' + REPO_URL + '/blob/dev/admin/factcheck/README.md">admin/factcheck/README.md</a>; its tickets are an <a href="https://issues-fs.sgit.ai/">Issues-FS</a> graph in <code>admin/factcheck/.issues/</code>, typed nodes and typed edges in plain JSON files; its grades are <a href="../data/factcheck.json">data/factcheck.json</a>. Mode one checks every claim against the evidence vault. Mode two goes outside for the weak and the contested, and records what it finds as a request to capture, never as a citation.</p>')}
'''
    page('factcheck/index.html', 'Fact-check: how sure can you be of each claim', f'Every claim on the PHP flaws site graded independently by the fact-check desk on a spectrum of evidence from A0 to A6, with a filter for only what can be relied on, the contradiction ledger, and the open tickets.', body, kind='analysis', topics='php2shell fact-check assurance')
    build_investigations()

# The desk's investigations (the brief of 24 October 2026, admin/content/briefs/2026-10-24__brief__factcheck-investigations-how-much-php.md):
# one question chased down to its measurements, every number with its measurer, population, method, date and hash.

FCV_DEN = OrderedDict([('websites-known-language', 'Websites whose language is known'), ('websites-all', 'All websites'), ('internet', "'The Internet' or 'the web'"),
                       ('servers-hosts', 'Servers or hosts'), ('applications', 'Web applications'), ('unspecified', 'No denominator given')])
# The categorical palette, in fixed order, validated with the dataviz skill's checker against this site's surfaces
# (light #ffffff: all checks pass, contrast relieved by labels and a table; dark #0f1115 and #16130f: all pass).
FCV_LIGHT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#6250d6']
FCV_DARK = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#9085e9']

def fcv_style():
    """The charts' colour roles, inside an SVG so the markdown twin drops them with the charts."""
    light = ''.join(f'--fcv-{i + 1}:{c};' for i, c in enumerate(FCV_LIGHT))
    dark = ''.join(f'--fcv-{i + 1}:{c};' for i, c in enumerate(FCV_DARK))
    css = (f'.fcv{{{light}}}@media (prefers-color-scheme: dark){{:root:not([data-theme]) .fcv{{{dark}}}}}'
           f':root[data-theme="night"] .fcv,:root[data-theme="ember"] .fcv{{{dark}}}'
           '.fcv{display:block;width:100%;height:auto;max-width:900px;font-family:var(--sans);overflow:visible}.fcv text{fill:var(--text);font-size:11px}.fcv .ax{fill:var(--dim)}'
           '.fcv .gr{stroke:var(--line);stroke-width:1}.fcv .ref{stroke:var(--dim);stroke-width:1.5;stroke-dasharray:5 4}.fcv .ln{fill:none;stroke-width:2}'
           '.fcv .dt{stroke:var(--bg);stroke-width:2}.fcv .org{stroke:var(--text);stroke-width:2}.fcv .hit{fill:transparent}.fcv .hit:hover+.dt,.fcv g:hover>.dt{stroke:var(--text)}'
           + ''.join(f'.fcv .c{i + 1}{{fill:var(--fcv-{i + 1})}}.fcv .s{i + 1}{{stroke:var(--fcv-{i + 1})}}' for i in range(6)) +
           '.fcv-key{display:flex;flex-wrap:wrap;gap:.4rem 1rem;margin:.3rem 0 .6rem;font-size:.85rem}.fcv-key span{display:inline-flex;align-items:center;gap:.35rem}'
           '.fcv-key i{display:inline-block;width:.8rem;height:.8rem;border-radius:3px}' + ''.join(f'.fcv-key .k{i + 1}{{background:var(--fcv-{i + 1})}}' for i in range(6)))
    return f'<svg class="fcv" width="0" height="0" aria-hidden="true" style="position:absolute"><style>{css}</style></svg>'

def fcv_key(items):
    return '<div class="fcv fcv-key" role="list">' + ''.join(f'<span role="listitem"><i class="k{n}"></i>{E(label)}</span>' for n, label in items) + '</div>'

def fcv_day(d):
    """Days since 2015-01-01 for a YYYY or YYYY-MM-DD date: the time axis of the shares chart, with no clock."""
    m = re.match(r'^(\d{4})(?:-(\d{2})-(\d{2}))?', str(d))
    y, mo, da = int(m.group(1)), int(m.group(2) or 7), int(m.group(3) or 1)
    import datetime as _dt
    return (_dt.date(y, mo, da) - _dt.date(2015, 1, 1)).days

def fcv_shares_chart(series):
    """Line chart, one axis in percent: each series is (n, name, points, note). A dashed line marks the 70% of the headlines."""
    W, H, l, r, t, b = 760, 300, 40, 190, 14, 30
    x0, x1 = 0, fcv_day('2026-12-31')
    X = lambda d: l + (fcv_day(d) - x0) / (x1 - x0) * (W - l - r)
    Y = lambda v: t + (100 - v) / 100 * (H - t - b)
    g = ''.join(f'<line class="gr" x1="{l}" x2="{W - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text class="ax" x="{l - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}%</text>' for v in (0, 25, 50, 75, 100))
    g += ''.join(f'<text class="ax" x="{X(f"{y}-01-01"):.1f}" y="{H - 10}" text-anchor="middle">{y}</text>' for y in range(2015, 2027, 2))
    g += f'<line class="ref" x1="{l}" x2="{W - r}" y1="{Y(70):.1f}" y2="{Y(70):.1f}"/><text x="{l + 6}" y="{Y(70) - 6:.1f}">70%: the figure in the headlines</text>'
    marks = ''
    for n, name, pts, note in series:
        pts = sorted(pts, key=lambda p: fcv_day(p['date']))
        d = ' '.join(f'{"M" if i == 0 else "L"}{X(p["date"]):.1f},{Y(p["value"]):.1f}' for i, p in enumerate(pts))
        marks += f'<path class="ln s{n}" d="{d}"/>'
        for p in pts:
            marks += f'<g><title>{E(name)}: {E(str(p["value"]))}% on {E(str(p["date"]))}</title><circle class="hit" cx="{X(p["date"]):.1f}" cy="{Y(p["value"]):.1f}" r="9"/><circle class="dt c{n}" cx="{X(p["date"]):.1f}" cy="{Y(p["value"]):.1f}" r="4"/></g>'
        last = pts[-1]
        marks += f'<text x="{X(last["date"]) + 8:.1f}" y="{Y(last["value"]) + 4:.1f}">{E(str(last["value"]))}% {E(note)}</text>'
    return f'<svg class="fcv" viewBox="0 0 {W} {H}" role="img" aria-label="PHP\'s share of websites over time, by measurer">{g}{marks}</svg>'

def fcv_bars(rows, unit_fmt, n=1, aria=''):
    """Horizontal bars on one axis: rows are (label, value, note) or (label, value, note, colour slot). Every bar carries its value and its label."""
    W, l, rh = 760, 250, 26
    mx = max(r[1] for r in rows) or 1
    H = rh * len(rows) + 8
    out = ''
    for i, row in enumerate(rows):
        label, v, note = row[:3]
        c = row[3] if len(row) > 3 else n
        y = 4 + i * rh
        w = max(2, v / mx * (W - l - 200))
        out += (f'<g><title>{E(label)}: {E(unit_fmt(v))}{(", " + E(note)) if note else ""}</title><text x="{l - 8}" y="{y + 15}" text-anchor="end">{E(label)}</text>'
                f'<rect class="c{c}" x="{l}" y="{y + 4}" width="{w:.1f}" height="14" rx="4"/><text x="{l + w + 6:.1f}" y="{y + 15}">{E(unit_fmt(v))}{(" " + E(note)) if note else ""}</text></g>')
    return f'<svg class="fcv" viewBox="0 0 {W} {H}" role="img" aria-label="{E(aria)}">{out}</svg>'

def fcv_iso(s):
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})', s or '')
    return m and (int(m.group(3)) - 21) * 24 + int(m.group(4)) + int(m.group(5)) / 60  # hours since 21 October 00:00 UTC

def fcv_timeline(L):
    """Every statement of the share as a dot: the row is its wording family, the colour what it claims to measure, a ringed dot the family's origin."""
    fams = L['families']
    st = {s['id']: s for s in L['statements']}
    den_n = {k: i + 1 for i, k in enumerate(FCV_DEN)}
    h0, h1 = 0, 60
    in_win = lambda s: fcv_iso(s.get('time_utc')) is not None and h0 <= fcv_iso(s['time_utc']) <= h1
    order = sorted(fams, key=lambda f: min([fcv_iso(st[m]['time_utc']) for m in f['members'] if in_win(st[m])] or [99]))
    W, l, r, rh, top = 760, 300, 20, 24, 8
    H = top + rh * len(order) + 34
    X = lambda h: l + (h - h0) / (h1 - h0) * (W - l - r)
    g = ''
    for h in range(0, 61, 12):
        g += f'<line class="gr" x1="{X(h):.1f}" x2="{X(h):.1f}" y1="{top}" y2="{H - 26}"/><text class="ax" x="{X(h):.1f}" y="{H - 10}" text-anchor="middle">{21 + h // 24} Oct {h % 24:02d}:00</text>'
    wiz = fcv_iso('2026-10-21T13:32Z')
    g += f'<line class="ref" x1="{X(wiz):.1f}" x2="{X(wiz):.1f}" y1="{top}" y2="{H - 26}"/>'
    out, outside = '', 0
    for i, f in enumerate(order):
        y = top + i * rh + rh / 2
        g += f'<text x="{l - 8}" y="{y + 4:.1f}" text-anchor="end">{E(f["wording"][:40])}{"..." if len(f["wording"]) > 40 else ""} ({len(f["members"])})</text>'
        for m in f['members']:
            s = st[m]
            if not in_win(s):
                outside += 1; continue
            n = den_n.get(s['denominator_class'], 6)
            org = ' org' if m == f.get('origin') else ''
            out += (f'<g><title>{E(s["id"])} {E(s["publisher"])}, {E(s["time_utc"])} ({E(s.get("time_basis", ""))}): {E(s["excerpt"][:160])}</title>'
                    f'<a href="#{E(s["id"])}"><circle class="hit" cx="{X(fcv_iso(s["time_utc"])):.1f}" cy="{y:.1f}" r="9"/><circle class="dt c{n}{org}" cx="{X(fcv_iso(s["time_utc"])):.1f}" cy="{y:.1f}" r="{6 if org else 4.5}"/></a></g>')
    svg = f'<svg class="fcv" viewBox="0 0 {W} {H}" role="img" aria-label="Every statement of PHP\'s share, by time and wording family">{g}{out}</svg>'
    return svg, outside

def fcv_lineage_graph(L, path):
    """The lineage as a graph for <sg-graph>: statements, the families they belong to, what they restate or reword, and the measurement they credit."""
    verbs = {'belongs_to': {'label': 'belongs to', 'inverse': 'groups', 'origin': 'factcheck'}, 'restates': {'label': 'restates', 'inverse': 'restated by', 'origin': 'factcheck'},
             'rewords': {'label': 'rewords', 'inverse': 'reworded as', 'origin': 'factcheck'}, 'credits': {'label': 'credits', 'inverse': 'credited by', 'origin': 'factcheck'}}
    kinds = {'measure': {'label': 'Measurement', 'plural': 'measurements'}, 'family': {'label': 'Wording family', 'plural': 'wording families'}, 'statement': {'label': 'Statement', 'plural': 'statements'}}
    here = 'factcheck/investigations/php-share/index.html'
    nodes = [{'id': 'measure:w3techs', 'kind': 'measure', 'label': 'W3Techs: PHP on 69.3% of websites whose server-side language is known', 'href': here + '#measures'}]
    nodes += [{'id': 'family:' + f['id'], 'kind': 'family', 'label': f['wording'], 'href': here + '#families'} for f in L['families']]
    edges = []
    for s in L['statements']:
        nodes.append({'id': 'statement:' + s['id'], 'kind': 'statement', 'label': f'{s["publisher"]}: {s["excerpt"][:70]}', 'href': here + '#' + s['id'], 'class': s['denominator_class']})
        edges.append({'from': 'statement:' + s['id'], 'verb': 'belongs_to', 'to': 'family:' + s['family']})
        if s.get('restates'):
            edges.append({'from': 'statement:' + s['id'], 'verb': 'rewords' if s['role'] == 'transforms' else 'restates', 'to': 'statement:' + s['restates']})
        if s.get('links_to_measurement') and 'w3techs' in s['links_to_measurement'].lower():
            edges.append({'from': 'statement:' + s['id'], 'verb': 'credits', 'to': 'measure:w3techs'})
    data = {'title': 'Where 70% comes from', 'note': 'Statements of PHP\'s share of the web in the evidence vault, by the fact-check desk.', 'ontology': {'kinds': kinds, 'verbs': verbs}, 'nodes': nodes, 'edges': edges}
    origins = ''.join(f'<li><a href="#{E(f["origin"])}">{E(f["wording"])}</a>: {len(f["members"])} statements</li>' for f in L['families'])
    return sg_graph(path, data=data, focus='statement:S-008', depth=2, fallback=f'<p class="small">The graph needs JavaScript. The same lineage, by family:</p><ul>{origins}</ul>')

def build_investigations():
    invs = FC.get('investigations', []) if FC else []
    if not invs:
        return
    rows = ''.join(f'<article class="role"><h3><a href="{E(i["id"])}/index.html">{E(i["title"])}</a> <span class="st st-{"reported" if i["status"] == "open" else "confirmed"}">{E(i["status"])}</span></h3><p><i>{E(i["question"])}</i></p><p>{E(i["answer"])}</p><p class="small">Opened {E(i["opened"])}, as of {E(i["as_of"])}; {len(i.get("measures", {}).get("measures", []))} measures, {len(i.get("lineage", {}).get("statements", []))} statements traced.</p></article>' for i in invs)
    body = f'''
<h1>Investigations: one question, chased down to its measurements</h1>
<p class="lead">The claims ledger grades sentences. An investigation takes one question and chases it down: every number on it, who measured it, how, over what, as of when, and the bytes it was read from; then every place the number was repeated, how its wording changed on the way, and whether anyone corrected it. Run by the <a href="../index.html">fact-check desk</a>.</p>
{rows}
<p class="small">The data behind each investigation is in <code>admin/factcheck/investigations/</code> and in <a href="../../data/factcheck.json">data/factcheck.json</a>. Pages the desk fetched from outside the evidence vault are shown with their address, time and sha256, and are labelled as the desk's own fetches: they are not evidence of the story until a collector captures them.</p>
'''
    page('factcheck/investigations/index.html', 'Investigations: one question, chased down', 'The fact-check desk\'s investigations: a question chased down to every measurement, its provenance, every restatement and every correction.', body, kind='analysis', topics='php2shell fact-check investigation provenance')
    for i in invs:
        build_investigation_php_share(i)

def build_investigation_php_share(inv):
    path = f'factcheck/investigations/{inv["id"]}/index.html'
    M = {m['id']: m for m in inv['measures']['measures']}
    L, Lv = inv['lineage'], inv['live']
    lv = lambda n: FCL[n]
    verd = ''.join(f'<li><span class="as as-{v["level"]}"><b>{E(lv(v["level"])["code"])}</b> {E(lv(v["level"])["name"])}<i aria-hidden="true">{"&#9679;" * v["level"] + "&#9675;" * (6 - v["level"])}</i></span> <b><q>{E(v["wording"])}</q></b> &middot; {E(FC_KIND_WORD.get(v["kind"], v["kind"]))} &middot; {E(v["verdict"].replace("-", " "))}<div class="note">{E(v["basis"])}</div></li>' for v in inv['verdicts'])
    finds = ''.join(f'<li>{E(f)}</li>' for f in inv['findings'])
    shares = fcv_shares_chart([(1, 'W3Techs: websites whose server-side language is known', M['w3techs-php-share-known']['history'], 'W3Techs (known language)'),
                               (2, 'HTTP Archive: all crawled origins, mobile (the desk\'s ratio)', M['httparchive-php-share-mobile']['history'], 'HTTP Archive (all sites)'),
                               (3, 'W3Techs: WordPress on all websites', M['w3techs-wordpress-share-all']['history'], 'WordPress (all sites)')])
    hist_rows = []
    for mid, name in (('w3techs-php-share-known', 'W3Techs, PHP, known-language sites'), ('httparchive-php-share-mobile', 'HTTP Archive, PHP, all origins (mobile)'), ('w3techs-wordpress-share-all', 'W3Techs, WordPress, all sites')):
        for p in M[mid]['history']:
            hist_rows.append([E(name), E(str(p['date'])), E(str(p['value'])) + '%'])
    hosts = [m for m in inv['measures']['measures'] if m['family'] == 'hosts' and m['unit'] == 'count' and m['id'] != 'censys-php-web-properties']
    hosts.sort(key=lambda m: m['value'])
    hb = fcv_bars([(m['measurer'], m['value'], '') for m in hosts], lambda v: f'{v / 1e6:.2f} million', 1, 'Internet-facing hosts counted running PHP, by counter')
    def src_cell(m):
        s = m['source']
        if s['kind'] == 'vault':
            slug = s.get('vault_slug') or ''
            link = f'<a href="../../../sources/{E(slug)}/index.html">{E(slug)}</a>' if slug in SOURCES else f'{E(slug)} <span class="small">(in the vault)</span>'
            return f'{link}<div class="small">capture sha256 <code>{E(s["sha256"][:16])}</code></div>'
        return f'<a href="{U(s["url"])}" rel="noopener">{E(re.sub(r"^https?://(www\.)?", "", s["url"])[:48])}</a><div class="small">fetched by the desk {E(s.get("retrieved_at", ""))}, sha256 <code>{E(s["sha256"][:16])}</code></div>'
    fam_names = OrderedDict([('websites', 'Websites'), ('applications', 'Applications built on PHP'), ('versions', 'PHP versions'), ('hosts', 'Hosts and servers on the internet'), ('packages', 'Packages'), ('developers', 'Developers')])
    def fmt(m):
        v = m['value']
        return (f'{v:g}%' if m['unit'] == '%' else f'{v:,.0f}')
    mt = ''
    for fk, fname in fam_names.items():
        ms = [m for m in inv['measures']['measures'] if m['family'] == fk]
        if ms:
            mt += f'<h3>{E(fname)}</h3>' + table(['Measure', 'Value', 'Over what, and how', 'As of', 'Source'], [[f'<b>{E(m["measurer"])}</b><div class="small">{E(m["what"])}</div>', f'<b>{E(fmt(m))}</b>', f'{E(m["population"])}<div class="note">{E(m.get("notes", ""))}</div>', E(m['as_of']), src_cell(m) + f'<div><q>{E(m["source"]["excerpt"])}</q></div>'] for m in ms])
    tl, outside = fcv_timeline(L)
    from collections import Counter as _C
    dc = _C(s['denominator_class'] for s in L['statements'])
    den_n = {k: i + 1 for i, k in enumerate(FCV_DEN)}
    db = fcv_bars([(FCV_DEN[k], dc.get(k, 0), '', den_n[k]) for k in FCV_DEN], lambda v: f'{v:.0f} statements', 1, 'Statements of the share, by what they say they measure')
    key = fcv_key([(den_n[k], v) for k, v in FCV_DEN.items()])
    famt = table(['Family', 'Statements', 'Measures', 'Origin'], [[f'<b>{E(f["wording"])}</b>', str(len(f['members'])), E(FCV_DEN.get(f.get('denominator_class'), f.get('denominator_class') or '')), f'<a href="#{E(f["origin"])}">{E(f["origin"])}</a>'] for f in L['families']])
    def surl(s):
        return f'<a href="{U(s["url"])}" rel="noopener">{E(s["publisher"])}</a>' if s.get('url') else E(s['publisher'])
    strows = [[f'<span id="{E(s["id"])}">{E(s["id"])}</span>', E(s.get('time_utc') or s.get('published') or ''), surl(s) + (f' <a class="small" href="../../../sources/{E(s["slug"])}/index.html">capture</a>' if s['slug'] in SOURCES else ''),
               f'<q>{E(s["excerpt"])}</q>' + (f'<div class="small">{E(s["translation"])}</div>' if s.get('translation') and s.get('language') != 'en' else ''),
               E(FCV_DEN.get(s['denominator_class'], s['denominator_class'])) + (f'<div class="small">{E(s["qualifier"])}</div>' if s.get('qualifier') else ''),
               E(s.get('attribution') or 'none') + ('<div class="small">links the measurement</div>' if s.get('links_to_measurement') else ''),
               E(s['role']) + (f' <a href="#{E(s["restates"])}">{E(s["restates"])}</a>' if s.get('restates') else ''),
               f'<code title="{E(s["file"])}">{E(s["sha256"][:12])}</code>'] for s in sorted(L['statements'], key=lambda s: (s.get('time_utc') or '9', s['id']))]
    stt = table(['#', 'When (UTC)', 'Who', 'The words', 'Measures', 'Credits', 'Role', 'sha256'], strows)
    def side(x):
        x = x or {}
        words = f'<q>{E(x["excerpt"])}</q>' if x.get('excerpt') else '<i>not there</i>'
        return words + f'<div class="small">{E(str(x.get("when") or ""))}</div>'
    ch = table(['Who', 'What changed', 'Before', 'After'], [[E(c['publisher']), E(c['kind']), side(c.get('before')), side(c.get('after'))] for c in Lv['changes']])
    cnt = Lv['counts']['by_classification']
    fo = L['fortune']
    graph = fcv_lineage_graph(L, path)
    lim = ''.join(f'<li>{E(x)}</li>' for x in inv['limits'])
    body = f'''
{fcv_style()}
<h1>{E(inv["title"])}</h1>
<p class="lead">{E(inv["question"])} An investigation by the <a href="../../index.html">fact-check desk</a>, opened {E(inv["opened"])} at the editor's request; as of {E(inv["as_of"])}.</p>
{section("answer", "The short answer", f'<p><b>{E(inv["answer"])}</b></p>')}
{section("verdicts", "The versions of the claim, graded", f'<ul class="fc-verdicts">{verd}</ul>', 'On the desk\'s spectrum of evidence, from A0 (nothing carries it) to A6 (the primary record carries it).')}
{section("findings", "What the evidence shows", f'<ol>{finds}</ol>')}
{section("measures", "How much PHP there is, by who measures it", f'<p>Each measurer counts something different, so the measures are kept apart and never added together. The share charts use one axis, in percent; the counts are in a separate chart.</p>{fcv_key([(1, "W3Techs: PHP, websites whose server-side language is known"), (2, "HTTP Archive: PHP, all crawled origins (mobile)"), (3, "W3Techs: WordPress, all websites")])}{shares}<details><summary>The points as a table</summary>{table(["Series", "Date", "Share"], hist_rows)}</details><h3>Hosts on the internet counted running PHP</h3>{hb}<p class="small">Censys&#39;s 54.9 million &#39;web properties&#39; counts names, not machines, and reaches the vault third-hand; it is in the table below, not the chart. Palo Alto&#39;s 22.6 million &#39;instances&#39; is not in Palo Alto&#39;s own advisory.</p>{mt}')}
{section("timeline", "Every statement of the share, by time and wording", f'{key}{tl}<p class="small">Each dot is one statement in the evidence vault, placed at its publication time where the page gives one (otherwise its first capture; each statement says which). A ringed dot is the family&#39;s origin; the dashed line is Wiz&#39;s X post at 13:32 UTC on 21 October. {outside} statement{"s" if outside != 1 else ""} fall outside 21 to 23 October and are in the table. Hover a dot for its words; click it for its row.</p>')}
{section("denominators", "What the statements say they measure", f'{db}{famt}')}
{section("lineage", "The lineage, as a graph", f'<p>Start at Wiz&#39;s X post and walk: which statements belong to which wording, which restate or reword which, and which credit the measurement.</p>{graph}')}
{section("fortune", "Fortune: 'could take down 70% of the internet'", f'<p>The editor asked for this one (UF-005.1, board 195). Fortune&#39;s article by {E(fo.get("author", ""))}, {E(fo.get("published", ""))}, as captured in the vault:</p><ul>' + ''.join(f'<li><b>{E(k.replace("_", " "))}:</b> {" ".join(f"<q>{E(str(x))}</q>" for x in (v if isinstance(v, list) else [v]))}</li>' for k, v in (fo["wording"].items() if isinstance(fo.get("wording"), dict) else [("words", str(fo.get("wording", "")))])) + f'</ul><p><b>What it credits.</b> {E(str(fo.get("attributes", "")))}</p><p><b>Against Wiz.</b> {E(str(fo.get("vs_wiz", "")))}</p><p><b>Against W3Techs.</b> {E(str(fo.get("vs_w3techs", "")))}</p><p><b>Between its own versions.</b> {E(str(fo.get("edit", "")))}</p><p class="small">Statements {", ".join(f"<a href=#{E(x)}>{E(x)}</a>" for x in fo.get("statements", []))}; graded above as <q>could take down 70% of the internet</q>.</p>')}
{section("corrections", "Did anyone correct it?", f'<p>Every page in the vault that uses the figure, and every page the corrections liaison has written to, was fetched again on 24 October and compared with its capture: {cnt.get("unchanged", 0)} unchanged, {cnt.get("changed", 0)} reworded, {cnt.get("blocked", 0)} blocked, {cnt.get("unverifiable", 0)} could not be checked, and none corrected. Every change the desk found, the figure&#39;s and others on the same pages:</p>{ch}')}
{section("statements", f"All {len(L['statements'])} statements", f'<details><summary>The full table</summary>{stt}</details>')}
{section("limits", "What this does not show", f'<ul>{lim}</ul>')}
'''
    page(path, inv['title'], f'{inv["answer"][:240]}', body, kind='analysis', topics='php2shell 70% W3Techs PHP usage share provenance')

# ----------------------------------------------------------------------------- the corrections liaison (liaison@php.newsroom)
# Brief: admin/content/briefs/2026-10-22__brief__the-corrections-liaison.md; desk: admin/liaison/README.md.

OUT = load('outreach') if os.path.exists(os.path.join(DATA, 'outreach.json')) else None
OUT_ST = {'drafted': 'unverified', 'blocked': 'disputed', 'approved': 'reported', 'sent': 'reported', 'acknowledged': 'reported', 'corrected': 'confirmed', 'declined': 'contradicted', 'no-reply': 'unverified'}

def out_blocker(b, ids, fc_t):
    if b in ids:
        return f'<a href="#{E(b)}">{E(b)}</a>'
    t = fc_t.get(b)
    if t:
        return f'<a href="../factcheck/index.html#{E(b)}">{E(b)}</a> <span class="small">({E(t["status"])}: {E(t["title"])})</span>'
    return E(b)

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

def out_message(r, by_id):
    """The email the editor sends for one request (desk@php.newsroom, 24 October): plain text, the template in
    admin/liaison/README.md. Only the publisher's own quoted words come from outside; everything else is ours."""
    first = r['said'][0]; row = SOURCES.get(first['source'], {})
    words = first['words'] if len(first['words']) <= 70 else first['words'][:67].rsplit(' ', 1)[0] + '...'
    iso = (row.get('published') or '')[:10]
    when = r.get('date') or (f'{int(iso[8:10])} {MONTHS[int(iso[5:7]) - 1]} {iso[:4]}' if re.fullmatch(r'\d{4}-\d{2}-\d{2}', iso) else '')
    origin = by_id.get(r.get('origin', ''))
    echo = (f'\nThe wording starts with {origin["publisher"]}, which we have asked separately: {BASE_URL}/outreach/index.html#{origin["id"]}\n' if origin else '')
    return (f'Subject: A suggested correction: "{words}"\n\nHello,\n\n'
            f'{("On " + when + " you") if when else "You"} published: "{first["words"]}"\n({row.get("url", "")})\n\n'
            f'We think this says more than the evidence shows: {r["point"]}\n{echo}\n'
            f'The evidence, with the saved copies we checked and their hashes, is here:\n{BASE_URL}/outreach/index.html#{r["id"]}\n\n'
            f'A wording that would keep your piece accurate:\n"{r["suggested"]}"\n\n'
            f'The data is CC BY 4.0; use any of it with a credit to php.oct.2026.newsroom.sgit.ai. If we have this wrong, tell us and we will correct our page.\n\n'
            f'{OUT.get("sender", "")}')

def out_card(r, ids, fc_t, by_id=None):
    said = ''.join(f'<li><span class="small">{E(x["where"])}, third-party words:</span> <q>{E(x["words"])}</q> {src_links([x["source"]], 1)}'
                   f'<div class="note">Checked in <code>{E(x["file"])}</code>, sha256 <code>{E(x["sha256"][:16])}</code>{"" if x.get("quote_checked") else ": <b>not yet checked character for character</b>"}.</div></li>' for x in r['said'])
    f = r.get('factcheck', {})
    fcl = ', '.join(f'<a href="../factcheck/index.html#{E(t)}">{E(t)}</a>' for t in ([f['contradiction']] if f.get('contradiction') else []) + f.get('tickets', []))
    cl = ', '.join(f'<a href="../facts/{E(c)}/index.html">{E(c)}</a>' for c in f.get('claims', []))
    bl = ''.join(f'<li>{out_blocker(b, ids, fc_t)}</li>' for b in r.get('blocked_by', []))
    log = ''.join(f'<li><b>{E(l["at"])}</b> {E(l["event"])}</li>' for l in r.get('log', []))
    ch = r.get('channel', {})
    return (f'<article class="role" id="{E(r["id"])}"><h3>{E(r["id"])}: {E(r["publisher"])} <span class="st st-{OUT_ST.get(r["status"], "other")}">{E(r["status"])}</span> <span class="small">{E(r["role"])}</span></h3>'
            f'<p><b>The point.</b> {E(r["point"])}</p><p><b>What they published.</b></p><ul>{said}</ul>'
            f'<p><b>What the evidence shows.</b> {E(r["evidence"])}</p><p><b>A wording we suggest.</b> <q>{E(r["suggested"])}</q></p>'
            f'<p class="small">Fact-check: {fcl or "none"}{("; claims " + cl) if cl else ""}. Channel: {E(ch.get("kind", ""))}{(", " + E(ch["note"])) if ch.get("note") else ""}.</p>'
            + (f'<p><b>Waiting on.</b></p><ul>{bl}</ul>' if bl else '')
            + (f'<details><summary><b>The email to send</b> (the editor sends it, from the editor\'s own address, to the channel above)</summary><pre class="memo" style="white-space:pre-wrap">{E(out_message(r, by_id))}</pre></details>' if by_id is not None and r['status'] in ('drafted', 'approved') else '')
            + f'<p><b>Log.</b></p><ul>{log}</ul></article>')

def build_outreach():
    if not OUT:
        return
    R = OUT['requests']
    fc_t = {t['label']: t for t in FC['tickets']} if FC else {}
    ids = {r['id'] for r in R}; by_id = {r['id']: r for r in R}
    st = Counter(r['status'] for r in R)
    na = OUT.get('not_asked', [])
    not_asked = table(['Publisher', 'Their words', 'Why we are not asking'], [[E(x['publisher']), f'<q>{E(x["words"])}</q> {src_links([x["source"]], 1)}', E(x['why'])] for x in na]) if na else '<p>None.</p>'
    states = table(['Status', 'Means', 'Requests'], [[f'<span class="st st-{OUT_ST.get(x["id"], "other")}">{E(x["id"])}</span>', E(x['means']), str(st.get(x['id'], 0))] for x in OUT['statuses']])
    q = OUT['quotes']
    quotes = (table(['Who', 'Quoted', 'Capture'], [[E(x['who']), f'<q>{E(x["words"])}</q>', src_links([x['source']], 1)] for x in q['items']]) if q['items'] else '<p>None yet.</p>') + f'<p class="small">{E(q["about"])}</p>'
    sent = sum(st.get(k, 0) for k in ('sent', 'acknowledged', 'corrected', 'declined', 'no-reply'))
    how = ('<p>The desk is <code>liaison@php.newsroom</code>; its rules, the runbook and the message it prepares are in <a href="' + REPO_URL + '/blob/dev/admin/liaison/README.md">admin/liaison/README.md</a>, its data is <a href="../data/outreach.json">data/outreach.json</a>. '
           'It opens a request only from a <a href="../factcheck/index.html">fact-check</a> record, asks a publisher only through its own published corrections route, sends one follow-up at most, and records every answer, including no answer. '
           'Corrections to this site itself are on <a href="../corrections/index.html">the corrections page</a>.</p>')
    body = f'''
<h1>Corrections we have asked for</h1>
<p class="lead">When the fact-check desk finds that another publisher's words say more than the evidence shows, this site asks them, politely and with the evidence, to correct the wording. Each request is published here before any message is sent: what they said, quoted from a dated capture with its hash; what the evidence shows; a wording they can use; and where the request stands. The data is CC BY 4.0 and theirs to use. If we are the ones who are wrong, our page is corrected first.</p>
<p><b>{len(R)}</b> requests, <b>{st.get("drafted", 0)}</b> ready for the editor, <b>{st.get("blocked", 0)}</b> waiting, <b>{sent}</b> sent, <b>{st.get("corrected", 0)}</b> corrected. The editor reads and sends each request personally; the email is under each ready request. No agent writes to a publisher.</p>
{section("requests", "The requests", "".join(out_card(r, ids, fc_t, by_id) for r in R), "One point to one publisher each. The origin of an error is asked first; the outlets that repeated it are told what the origin said. A request that waits on this site fixing the same error first says so.")}
{section("not-asked", "Considered, and not asked", not_asked, "Coverage the desk read and decided not to ask about, and why: a publisher who quotes its source accurately is not the one to ask.")}
{section("statuses", "What the statuses mean", states)}
{section("quotes", "Where this site is quoted", quotes)}
{section("how", "How the liaison works", how)}
'''
    page('outreach/index.html', 'Corrections we have asked for', "The corrections this site has asked other publishers to make about the PHP flaws, each with the publisher's words from a dated capture, the fact-check evidence, a suggested wording and where the request stands.", body, kind='analysis', topics='php2shell corrections fact-check')


# ----------------------------------------------------------------------------- guidance for every agent (v0.5.3)

def build_agents_guide():
    body = f"""
<p class="crumb"><a href="../index.html">Admin</a> / Guidance for agents</p>
<div class="memo">{render_md_file('AGENTS.md')}</div>
<p class="small">The source is <code>AGENTS.md</code> at the root of the repository; every agent reads it there or here.</p>
"""
    page('admin/agents/index.html', 'How to work on this site: guidance for every agent', 'Push to your own branch early and often and let dev@php.newsroom carry it into dev; quality from coding.sgit.ai, non-functional requirements from nfrs.sgit.ai, and the security requirements.', body, kind='site')

# ----------------------------------------------------------------------------- the collaborators (conductor@php.newsroom)
# The editor's brief, 22 October 2026: a page he can send people he knows, who become the site's power users: they read
# what is new when asked, as one of the site's readers, and send feedback; the asks also go to an email list and a
# WhatsApp group the editor runs. data/collaborators.json holds the asks; assets/collaborators.js sends the join and
# feedback forms, encrypted in the browser, to the private collaborators vault's write-only lane.

def ask_message(a, persons, channel):
    """The message the editor pastes into the WhatsApp group or the email list for one ask: plain text, full URLs."""
    url = f'{BASE_URL}/collaborators/index.html#ask-{a["id"]}'
    news = '\n'.join(f'- {t}: {BASE_URL}/{p}' for p, t, _ in a['new'])
    qs = '\n'.join(f'{i + 1}. {q}' for i, q in enumerate(a['questions']))
    readers = ', '.join(persons[r]['label'] for r in a['readers'] if r in persons)
    if channel == 'whatsapp':
        return (f'{a["day"]}: {a["title"]}\n\nNew on PHP October 2026:\n{news}\n\nRead it as one of the site\'s readers ({readers}, or any other on Start here) '
                f'and tell us:\n{qs}\n\nReply here, or use the form (it goes straight to the team): {url}')
    return (f'Subject: PHP October 2026, ask {a["id"]}: {a["title"]}\n\nHello,\n\nHere is what we would like you to look at this time ({a["day"]}).\n\n'
            f'What is new:\n{news}\n\nWhat to do:\n' + '\n'.join(f'{i + 1}. {s}' for i, s in enumerate(a['steps'])) +
            f'\n\nThe questions:\n{qs}\n\nReply to this email, say it in the WhatsApp group, or use the form at {url}\n\nThank you,\nDinis')

def build_collaborators():
    C = load('collaborators'); persons = {p['id']: p for p in D['personas']['personas']}
    readers = [[p['id'], p['label']] for p in D['personas']['personas']]
    cfg = J({'contact': C['contact'], 'endpoint': C['lane']['endpoint'], 'vault_id': C['lane']['vault_id'], 'append_token': C['lane']['append_token'],
             'recipient': C['lane']['recipient'], 'readers': readers, 'asks': [a['id'] for a in C['asks']]}, ensure_ascii=False, separators=(',', ':'))
    ropts = '<option value="">(none in particular)</option>' + ''.join(f'<option value="{E(i)}">{E(l)}</option>' for i, l in readers)
    aopts = ''.join(f'<option value="{E(a["id"])}">{E(a["id"])}: {E(a["title"])}</option>' for a in C['asks']) + '<option value="">Something else</option>'
    def ask_html(a, latest):
        news = ''.join(f'<a class="door" href="../{U(p)}"><b>{E(t)}</b><span>{E(w)}</span></a>' for p, t, w in a['new'])
        rd = ', '.join(f'<a href="../briefings/{E(r)}/index.html">{E(persons[r]["label"])}</a>' for r in a['readers'] if r in persons)
        msgs = (f'<details><summary>The message for the WhatsApp group</summary><pre class="msg">{E(ask_message(a, persons, "whatsapp"))}</pre></details>'
                f'<details><summary>The message for the email list</summary><pre class="msg">{E(ask_message(a, persons, "email"))}</pre></details>')
        return f'''<section class="vcard" id="ask-{E(a["id"])}"><h3>{"This ask: " if latest else ""}{E(a["day"])}, ask {E(a["id"])}: {E(a["title"])}</h3>
<p class="small">New since v{E(a["since"])}. Read it as: {rd}, or <a href="../start/index.html">any other reader</a>.</p>
<div class="doors">{news}</div>
<h4>What to do</h4><ol>{"".join(f"<li>{E(x)}</li>" for x in a["steps"])}</ol>
<h4>The questions</h4><ol>{"".join(f"<li>{E(x)}</li>" for x in a["questions"])}</ol>
{msgs}</section>'''
    asks = sorted(C['asks'], key=lambda a: a['date'], reverse=True)
    latest = ask_html(asks[0], True) if asks else '<p>No ask yet.</p>'
    earlier = ''.join(ask_html(a, False) for a in asks[1:]) or '<p class="small">None yet: this is the first.</p>'
    li = lambda xs: '<ul>' + ''.join(f'<li>{E(x)}</li>' for x in xs) + '</ul>'
    chans = ''.join(f'<li><b>{E(n)}.</b> {E(t)}</li>' for n, t in C['channels'])
    thanks = ', '.join(E(x) for x in C['thanks']) or 'Nobody yet: be the first.'
    ed = C['editor']
    body = f'''
<h1>Power users: start here</h1>
<p class="lead">This site is being built in public, every day, by {E(ed["name"])} and a team of AI agents. We are looking for people who will use it as it grows: read what is new when we ask, as the kind of reader you are, and tell us what works and what does not. {E(C["time"])} If you have not seen agentic workflows doing real work, this is a close look at one.</p>
<p><a class="cta cta-pri" href="#start">Start here</a> <a class="cta" href="#ask-{E(asks[0]["id"]) if asks else ""}">See the latest ask</a> <a class="cta" href="#feedback">Send feedback</a> <a class="cta" href="#join">Join</a></p>
{section("start", "Start here: your first fifteen minutes", '<ol class="steps">' + ''.join(f'<li><a href="../{U(h)}"><b>{E(t)}</b></a>: {E(w)}</li>' for t, h, w in C['start']) + '</ol><p class="small">That is all there is to joining in: after this, each ask tells you what to look at.</p>')}
{section("ask", "The latest ask", latest)}
{section("what", "What we ask of you", li(C["what_we_ask"]))}
{section("get", "What you get", li(C["what_you_get"]))}
{section("how", "How it works", f'<ul>{chans}</ul><p>The readers you can read as are on <a href="../start/index.html">Start here</a>: each has a plain answer, what it needs and a reading path. The team you are helping is on <a href="../team/index.html">the team page</a>.</p>')}
<section id="join"><h2>Join</h2>
<p><b>Have an invitation?</b> Open it: it lands on <a href="../join/index.html">Join</a>, which makes your key in one tap, and then the <b>Feedback</b> button at the top of every page sends signed feedback, with screenshots.</p>
<p>No invitation yet? Know {E(ed["name"].split()[0])}? <a href="{U(ed["linkedin"])}" rel="noopener">Message him on LinkedIn</a>, or fill this in. He reads every request and adds you to the email list, and to the WhatsApp group if you ask.</p>
<form id="join-form" class="subform" autocomplete="on">
<p><label>Your name<br><input type="text" name="name" required maxlength="120"></label></p>
<p><label>Your email address<br><input type="email" name="email" required maxlength="254" placeholder="you@example.org"></label></p>
<p><label>How you know {E(ed["name"].split()[0])}, or how you found this (optional)<br><input type="text" name="knows" maxlength="300"></label></p>
<p><label>The reader closest to you (optional)<br><select name="reader">{ropts}</select></label></p>
<p><label class="sub-c"><input type="checkbox" name="whatsapp" value="yes"> Add me to the WhatsApp group too ({E(ed["name"].split()[0])} will ask for your number; it is not collected here)</label></p>
<p><label>Anything else (optional)<br><textarea name="note" rows="2" maxlength="1000"></textarea></label></p>
<p class="sub-hp" aria-hidden="true"><label>Leave this empty <input type="text" name="website" tabindex="-1" autocomplete="off"></label></p>
<p><button class="cta cta-pri" type="submit">Ask to join</button></p>
<p id="join-out" role="status" aria-live="polite"></p>
</form></section>
<section id="feedback"><h2>Send feedback</h2>
<p>On an ask, or on anything else on the site. Short is fine. Your name and address are optional here.</p>
<form id="fb-form" class="subform" autocomplete="on">
<p><label>Which ask<br><select name="ask">{aopts}</select></label></p>
<p><label>Which reader you read as (optional)<br><select name="reader">{ropts}</select></label></p>
<p><label>Which page (optional)<br><input type="text" name="page" maxlength="300" placeholder="paste the address, or describe it"></label></p>
<p><label>What worked<br><textarea name="worked" rows="3" maxlength="3000"></textarea></label></p>
<p><label>What did not, or what you expected and could not find<br><textarea name="missing" rows="3" maxlength="3000"></textarea></label></p>
<p><label>What you would do next, or anything that contradicts something else on the site<br><textarea name="next" rows="3" maxlength="3000"></textarea></label></p>
<p><label>Your name (optional)<br><input type="text" name="name" maxlength="120"></label></p>
<p><label>Your email, if you want a reply (optional)<br><input type="email" name="email" maxlength="254"></label></p>
<p class="sub-hp" aria-hidden="true"><label>Leave this empty <input type="text" name="website" tabindex="-1" autocomplete="off"></label></p>
<p><button class="cta cta-pri" type="submit">Send feedback</button></p>
<p id="fb-out" role="status" aria-live="polite"></p>
</form></section>
<script type="application/json" id="collab-config">{cfg}</script>
<p class="small">The forms need JavaScript, because they encrypt in your browser. Without it, write to <a href="mailto:{E(C["contact"])}">{E(C["contact"])}</a> or message {E(ed["name"].split()[0])} on LinkedIn.</p>
{section("earlier", "Earlier asks", earlier)}
{section("privacy", "What happens to what you send", f'<ul><li>It is encrypted in your browser to the collaborators vault\'s key (<code>{E(C["lane"]["recipient"]["fingerprint"])}</code>) and posted to a write-only lane on that private vault (<code>{E(C["lane"]["vault_id"])}</code>). The lane answers the same whatever arrives, so this page can say it was sent, never that it arrived.</li><li>It stays in that vault: not on this site, not in its repository, not in its telemetry. The editor and the conductor read it. Feedback becomes work on <a href="../admin/board/index.html">the board</a> in the team\'s words, never with your name unless you agree.</li><li>No phone number is collected here. WhatsApp is the editor\'s own group; he asks for your number himself.</li><li>Anyone can type anything into a form, so a request is read by a person before anyone is added or written to.</li></ul>')}
{section("thanks", "Thank you", f'<p>{thanks}</p>')}
<script src="../assets/collaborators.js" defer></script>
'''
    page('collaborators/index.html', 'Power users: start here', 'Where a power user of PHP October 2026 starts: the first fifteen minutes, the latest ask (what is new, what to do, the questions), the messages for the email list and the WhatsApp group, a form to join and a form for feedback, both encrypted in your browser.', body, kind='account')


# ----------------------------------------------------------------------------- what runs on its own, and every run (conductor@php.newsroom)
# The editor, 22 October 2026: keep track of which agents run on a schedule, so that nothing runs overnight; and one
# page that captures every agent's execution, each run with changes leaving an article. data/schedules.json is the
# register; the runs are read from the data each agent already publishes (releases, source watch, fact-check desk,
# synthetic readers), so the page adds no run of its own and cannot drift from them.
import datetime as _dt
from zoneinfo import ZoneInfo as _ZI

def cron_field(f, lo, hi):
    """The values one field of a five-field cron expression names: *, */n, a-b, a-b/n, and lists of those."""
    out = set()
    for part in f.split(','):
        rng, _, step = part.partition('/')
        a, b = (lo, hi) if rng == '*' else (tuple(int(x) for x in rng.split('-')) if '-' in rng else (int(rng), int(rng) if not step else hi))
        out.update(range(a, b + 1, int(step or 1)))
    return sorted(out)

def schedule_times(s, day):
    """The UTC times a schedule fires on one day: from its cron, or every N minutes for a self-scheduling chain."""
    start = _dt.datetime.combine(day, _dt.time(0, 0), tzinfo=_dt.timezone.utc)
    if s['kind'] == 'chain':
        return [start + _dt.timedelta(minutes=m) for m in range(0, 24 * 60, s['every_minutes'])]
    mi, ho = s['cron'].split()[:2]
    return [start.replace(hour=h, minute=m) for h in cron_field(ho, 0, 23) for m in cron_field(mi, 0, 59)]

def in_quiet(t, q):
    """True when a UTC time falls in the quiet hours, read in the quiet hours' own time zone."""
    loc = t.astimezone(_ZI(q['tz'])).strftime('%H:%M')
    return loc >= q['from'] or loc < q['to']

def all_runs(S):
    """Every execution the site's data records, newest first: (when, member, what, run id, changed, summary, link)."""
    runs = []
    for v in D['versions']['versions']:
        runs.append((v['date'], 'dev', 'Release', 'v' + v['version'], True, v['title'], 'admin/versions.html'))
    for r in D['source-watch']['runs']:
        runs.append((r['started'], 'researcher', 'Source watch pass', r['run'], r.get('changed', 0) > 0,
                     f'{r.get("pages_due", 0)} pages due, {r.get("changed", 0)} changed', 'vaults/source-watch/index.html'))
    fdir = os.path.join(ROOT, 'admin', 'factcheck', 'runs')
    for fn in sorted(os.listdir(fdir)) if os.path.isdir(fdir) else []:
        if fn.endswith('.json'):
            r = json.load(open(os.path.join(fdir, fn), encoding='utf-8'))
            runs.append((r.get('started', ''), 'verifier', 'Fact-check run', r['id'], bool(r.get('opened')), r.get('opened') or r.get('checked', ''), 'factcheck/index.html'))
    for p in (SYN or {}).get('personas', []):
        for h in p.get('runs', []):
            ch, fl = h.get('checks', {}), h.get('fails', {})
            runs.append((h['finished'], 'synthetic', f'Synthetic reader: {p["name"]}', f'{p["id"]}/{h["run"]}', bool(sum(fl.values())),
                         f'site v{h["site_version"]}: answered the question {h.get("answered_question") or "(not reviewed)"}; {sum(fl.values())} failures named ({fl.get("high", 0)} high); {ch.get("high", 0)} high, {ch.get("medium", 0)} medium instrument flags',
                         f'admin/synthetic/{p["id"]}/{h["run"]}/index.html'))
    for fn in glob.glob(os.path.join(DATA, 'runs', '*', '*.json')):
        r = json.load(open(fn, encoding='utf-8'))
        runs.append((r['started'], r['agent'], 'Scheduled wake', r['run'], r['outcome'] in ('ok', 'partial'), r['summary'], f'team/schedule/{r["agent"]}/index.html'))
    return sorted(runs, key=lambda r: (r[0], r[3]), reverse=True)

def build_runs():
    S = load('schedules'); q = S['quiet_hours']; day = _dt.date.fromisoformat(q['as_of'])
    members = {m['id']: m for m in TEAM['members']}
    who = lambda mid: f'<a href="../{E(mid)}/index.html">{E(members[mid]["name"])}</a>' if mid in members else E(mid)
    rows, night_total = [], 0
    for s in S['schedules']:
        ts = schedule_times(s, day); night = sorted((t for t in ts if in_quiet(t, q)), key=lambda t: (t.astimezone(_ZI(q['tz'])).hour < 12, t.astimezone(_ZI(q['tz'])).strftime('%H:%M')))  # evening first
        night_total += len(night)
        first = ', '.join(t.astimezone(_ZI(q['tz'])).strftime('%H:%M') for t in night[:6]) + (' and more' if len(night) > 6 else '')
        rows.append([f'<b>{E(s["name"])}</b><div class="note">{E(s["does"])}</div>', who(s['member']), E(s['where']),
                     E(s['cadence']) + (f'<div class="note"><code>{E(s["cron"])}</code></div>' if s.get('cron') else ''),
                     f'{len(ts)} a day', (f'<span class="st st-contradicted">{len(night)} at night</span><div class="note">{first} London</div>' if night else '<span class="st st-confirmed">none</span>'),
                     E(s['status']), E(s['proposed'])])
    reg = table(['Schedule', 'Who', 'Where', 'How often', 'Runs', 'In quiet hours', 'Status', 'Proposed'], rows, 'board')
    by_run = {a.get('run'): a for a in ARTICLES if a.get('run')}
    runs = all_runs(S)
    missing = [r for r in runs if r[4] and r[2] != 'Release' and r[3] not in by_run]
    def art(r):
        a = by_run.get(r[3])
        if a: return f'<a href="../../articles/{E(a["slug"])}/index.html">{E(a["title"].split(":")[0])}</a>'
        if r[2] == 'Release': return '<span class="small">its release note</span>'
        return '<span class="st st-disputed">missing</span>' if r[4] else '<span class="small">no changes, none needed</span>'
    erows = [[E(r[0]), who(r[1]), E(r[2]), f'<code>{E(r[3])}</code>', E(r[5]), 'yes' if r[4] else 'no', art(r), f'<a href="../../{U(r[6])}">output</a>'] for r in runs]
    counts = Counter(r[1] for r in runs)
    stats = ''.join(stat(n, l) for n, l in [(len(S['schedules']), 'schedules'), (night_total, 'runs a night, today'), (len(runs), 'runs recorded'), (len(missing), 'runs with changes and no article')])
    body = f'''
<p class="crumb"><a href="../index.html">The team</a> / Runs</p>
<h1>Runs: what the agents do on their own, and every time they did it</h1>
<p class="lead">{E(S["about"])}</p>
<div class="stats">{stats}</div>
{section("quiet", "Quiet hours", f'<p><b>{E(q["from"])} to {E(q["to"])} {E(q["tz"])}.</b> {E(q["rule"])}</p><p class="caveat">Status: {E(q["status"])}. Counted for {E(q["as_of"])}; the clocks go back on 25 October, which moves a UTC schedule an hour later in London.</p>')}
{section("schedules", "What runs on its own", reg, f"As observed on {S['observed']}. A schedule changes only with the editor's go; a workflow change goes to a branch for security review first.")}
{section("articles", "Every run with changes leaves an article", f'<p>{E(S["article_rule"])}</p>')}
{section("runs", "Every run", '<div data-live="runs-all">' + table(['When', 'Who', 'What', 'Run', 'Summary', 'Changes', 'Article', 'Output'], erows, 'board') + '</div>\n<script src="../../assets/live/live.js" defer></script>\n<script src="../../assets/live/runs.js" defer></script>', "Newest first, read from the data each agent publishes: the release history, the source watch, the fact-check desk's runs and the synthetic readers' latest run each. " + ", ".join(f"{E(members[m]['name']) if m in members else E(m)}: {n}" for m, n in counts.most_common()) + ".")}
'''
    page('team/runs/index.html', 'Runs: what the agents do on their own, and every time they did it', 'The register of every schedule the team runs (who, where, how often, how many runs fall in the quiet hours) and every recorded run, newest first, with the article each run with changes should leave.', body, kind='site', topics='team agents')


# ----------------------------------------------------------------------------- GRC: fractal risk registers (grc@php.newsroom)
# The brief is admin/content/briefs/2026-10-22__brief__grc-fractal-risk-registers.md. The data is data/grc.json (stakeholders,
# weaknesses, risks) and data/grc-frameworks.json (the standards); the build writes data/grc-graph.json. Every reference is
# checked here and the build stops on an unknown one: a risk can only point at a claim, source, story, page, team member,
# code node or control that exists. Edges follow the sgit graph grammar: every edge is a verb with a named inverse.

GRC = load('grc') if os.path.exists(os.path.join(DATA, 'grc.json')) else None
GRCF = load('grc-frameworks') if os.path.exists(os.path.join(DATA, 'grc-frameworks.json')) else None
GRC_NETWORK = load('grc-network') if os.path.exists(os.path.join(DATA, 'grc-network.json')) else None

# The part a stakeholder plays in a risk, as the verb from the risk to the stakeholder and its inverse.
GRC_AS_VERB = {'owner': ('owned_by', 'owns'), 'bearer': ('borne_by', 'bears'), 'treater': ('treated_by', 'treats'),
               'source': ('raised_by', 'raises'), 'informer': ('informed_by', 'informs'), 'regulator': ('regulated_by', 'regulates')}
GRC_VERBS = OrderedDict([
    ('part_of', 'has_part'), ('arises_from', 'gives_rise_to'), ('backed_by', 'evidences'), ('fixed_by', 'fixes'),
    ('realised_in', 'realises'), ('located_in', 'location_of'), ('protected_by', 'protects'), ('governed_by', 'governs'),
    ('concerns', 'concerned_in'), ('told_in', 'tells'), ('tracked_by', 'tracks'), ('briefed_by', 'briefs'), ('cites', 'cited_by'), ('shown_on', 'shows'), ('tests', 'tested_by'),
] + [v for v in GRC_AS_VERB.values()])
GRC_CAT = OrderedDict([('security', 'Security'), ('supply-chain', 'Supply chain'), ('process', 'Disclosure process'), ('operational', 'Operational'),
                       ('compliance', 'Compliance'), ('governance', 'Governance'), ('reputational', 'Reputational'), ('strategic', 'Strategic'), ('ai', 'AI and agents')])

def grc_score(r):
    return r['likelihood'] * r['impact']

def grc_band(s):
    return 'critical' if s >= 20 else 'high' if s >= 12 else 'medium' if s >= 6 else 'low'

def grc_pill(r):
    s = grc_score(r)
    return f'<span class="gr gr-{grc_band(s)}" title="likelihood {r["likelihood"]} x impact {r["impact"]}"><b>{s}</b> {grc_band(s)}</span>'

def grc_index():
    """Every lookup the pages need, built once, with every reference checked."""
    S = OrderedDict((s['id'], s) for s in GRC['stakeholders'])
    R = OrderedDict((r['id'], r) for r in GRC['risks'])
    W = OrderedDict((w['id'], w) for w in GRC['weaknesses'])
    FW = OrderedDict((f['id'], f) for f in GRCF['frameworks'])
    CTL = OrderedDict((f'{f["id"]}:{c["id"]}', (f, c)) for f in GRCF['frameworks'] for c in f['controls'])
    claims = {c['id']: c for c in D['claims']}
    rev = {n['id']: n for n in D['review']['nodes']}
    arts = {a['slug']: a for a in ARTICLES}
    members = {m['id']: m for m in TEAM['members']}
    auds = {a['id'] for a in D['roles']['audiences']}
    actors = {a['id'] for a in D['actors']}
    bad = []
    def page_ok(p):
        return os.path.exists(os.path.join(ROOT, p.split('#')[0])) or any(p.split('#')[0] == x[0] for x in PAGES)
    for s in S.values():
        if s['parent'] is not None and s['parent'] not in S: bad.append(f'stakeholder {s["id"]}: unknown parent {s["parent"]}')
        if s.get('audience') and s['audience'] not in auds: bad.append(f'stakeholder {s["id"]}: unknown audience {s["audience"]}')
        if s.get('member') and s['member'] not in members: bad.append(f'stakeholder {s["id"]}: unknown member {s["member"]}')
        bad += [f'stakeholder {s["id"]}: unknown actor {a}' for a in s.get('actors', []) if a not in actors]
    for w in W.values():
        bad += [f'weakness {w["id"]}: unknown code-graph node {v}' for v in w.get('vulns', []) + w.get('remediation', []) if v not in rev]
        bad += [f'weakness {w["id"]}: no file {p} in this repository' for p in w.get('code', []) if not os.path.exists(os.path.join(ROOT, p))]
    for r in R.values():
        if r['parent'] is not None and r['parent'] not in R: bad.append(f'risk {r["id"]}: unknown parent {r["parent"]}')
        for a in r['assign']:
            if a['to'] not in S: bad.append(f'risk {r["id"]}: assigned to unknown stakeholder {a["to"]}')
            if a['as'] not in GRC_AS_VERB: bad.append(f'risk {r["id"]}: unknown part {a["as"]}')
        bad += [f'risk {r["id"]}: unknown weakness {x}' for x in r['weaknesses'] if x not in W]
        bad += [f'risk {r["id"]}: concerns unknown vulnerability {x}' for x in r.get('concerns', []) if x not in rev or rev[x]['layer'] != 'vulnerability']
        bad += [f'risk {r["id"]}: unknown claim {x}' for x in r['claims'] if x not in claims]
        bad += [f'risk {r["id"]}: cites unknown slug {x}' for x in r.get('sources', []) if x not in SOURCES]
        bad += [f'risk {r["id"]}: unknown control {x}' for x in r['frameworks'] if x not in CTL]
        bad += [f'risk {r["id"]}: unknown story {x}' for x in r['stories'] if x not in arts]
        bad += [f'risk {r["id"]}: unknown team member {x}' for x in r['team'] if x not in members]
        bad += [f'risk {r["id"]}: no page {x}' for x in r['pages'] + [c['page'] for c in r['controls']] if not page_ok(x)]
        if r['category'] not in GRC_CAT: bad.append(f'risk {r["id"]}: unknown category {r["category"]}')
        if not (1 <= r['likelihood'] <= 5 and 1 <= r['impact'] <= 5): bad.append(f'risk {r["id"]}: rating out of 1 to 5')
        if not r['assign']: bad.append(f'risk {r["id"]}: assigned to nobody')
        if not any(a['as'] == 'owner' for a in r['assign']): bad.append(f'risk {r["id"]}: has no owner')
    if bad:
        sys.exit('grc: ' + '; '.join(bad))
    kids_s, kids_r = {}, {}
    for s in S.values(): kids_s.setdefault(s['parent'], []).append(s['id'])
    for r in R.values(): kids_r.setdefault(r['parent'], []).append(r['id'])
    return dict(S=S, R=R, W=W, FW=FW, CTL=CTL, claims=claims, rev=rev, arts=arts, members=members, kids_s=kids_s, kids_r=kids_r)

def grc_below(kids, root):
    out, stack = [], [root]
    while stack:
        x = stack.pop(0); out.append(x); stack[0:0] = kids.get(x, [])
    return out

def grc_ancestors(items, x):
    out = []
    while items[x]['parent'] is not None:
        x = items[x]['parent']; out.append(x)
    return out

def grc_path(G, rid):
    """The chain from a risk down to the code and across to stories and roles, own and through its parents."""
    R, W, rev = G['R'], G['W'], G['rev']
    line = [rid] + grc_ancestors(R, rid)
    ws = list(OrderedDict.fromkeys(w for x in line[:1] for w in R[x]['weaknesses']))
    vulns = list(OrderedDict.fromkeys([v for x in line for w in R[x]['weaknesses'] for v in W[w].get('vulns', [])] + [v for x in line for v in R[x].get('concerns', [])]))
    rem = list(OrderedDict.fromkeys([n for w in ws for n in W[w].get('remediation', [])] +
                                    [e['from'] for e in D['review']['edges'] if e['rel'] == 'addresses' and e['to'] in vulns]))
    code = list(OrderedDict.fromkeys(e['to'] for e in D['review']['edges'] if e['rel'] == 'realised in' and e['from'] in rem))
    repo = list(OrderedDict.fromkeys(p for w in ws for p in W[w].get('code', [])))
    stories = list(OrderedDict.fromkeys(s for x in line for s in R[x]['stories']))
    roles = list(OrderedDict.fromkeys(a['to'] for x in [rid] + line[1:] + grc_below(G['kids_r'], rid)[1:] for a in R[x]['assign'] if G['S'][a['to']]['kind'] == 'role'))
    team = list(OrderedDict.fromkeys(m for x in line for m in R[x]['team']))
    return dict(weaknesses=ws, vulns=vulns, remediation=rem, code=code, repo=repo, stories=stories, roles=roles, team=team,
                own_stories=R[rid]['stories'], through=line[1:])

GRC_TESTS = load('grc-tests') if os.path.exists(os.path.join(DATA, 'grc-tests.json')) else None
GRC_BASIS = load('grc-basis') if os.path.exists(os.path.join(DATA, 'grc-basis.json')) else {'confirmed': []}
GRC_GAPS = load('grc-gaps') if os.path.exists(os.path.join(DATA, 'grc-gaps.json')) else None
GRC_HISTORY = load('grc-history') if os.path.exists(os.path.join(DATA, 'grc-history.json')) else {'releases': [], 'unchanged': [], 'labels': {}}
GRC_NAV = [None]  # the GRC section's crumb line, kept by build_grc for /grc/changes/, which is drawn again once this release's change is known
# How an edge is known (CI-002.5, the brief of 23 October): read from a capture, read from the commit, inferred by an
# agent, or confirmed by a person; with what supports it.
GRC_BASES = OrderedDict([('source', 'read from a capture'), ('code', 'read from the fix commit'), ('inferred', 'inferred by an agent, not yet checked'), ('confirmed', 'checked by a person')])

def grc_graph(G):
    """data/grc-graph.json: one node per thing, one edge per verb, the inverse named on the edge, and on every edge its
    basis: how it is known ({kind, ref}: source and the capture's slug, code and the commit, inferred and the agent,
    confirmed and who checked)."""
    nodes, edges, seen = [], [], set()
    commit = D['code']['fix']['commit']
    def node(i, kind, label, href):
        if i not in seen:
            seen.add(i); nodes.append({'id': i, 'kind': kind, 'label': label, 'href': href})
    joined = set()
    def edge(a, verb, b, kind, ref, note=None):
        # one edge per (from, verb, to): a claim that backs several risks cites its sources once, not once per risk
        # (until v0.14.24 it was added again for every risk, 91 repeats in 1,442)
        if (a, verb, b) in joined:
            return
        joined.add((a, verb, b))
        basis = {'kind': kind, 'ref': ref}
        if note: basis['note'] = note
        edges.append({'from': a, 'rel': verb, 'inverse': GRC_VERBS[verb], 'to': b, 'basis': basis})
    by_grc = ('inferred', 'grc')
    for s in G['S'].values():
        node('stakeholder:' + s['id'], 'role' if s['kind'] == 'role' else 'stakeholder', s['name'], f'grc/stakeholders/{s["id"]}/index.html')
        if s['parent']: edge('stakeholder:' + s['id'], 'part_of', 'stakeholder:' + s['parent'], *by_grc)
        if s.get('audience'):
            a = next(x for x in D['roles']['audiences'] if x['id'] == s['audience'])
            node('briefing:' + a['id'], 'briefing', a['name'], f'briefings/{a["id"]}/index.html'); edge('stakeholder:' + s['id'], 'briefed_by', 'briefing:' + a['id'], *by_grc)
        if s.get('member'):
            m = G['members'][s['member']]; node('member:' + m['id'], 'member', m['name'], f'team/{m["id"]}/index.html'); edge('stakeholder:' + s['id'], 'tracked_by', 'member:' + m['id'], *by_grc)
    for w in G['W'].values():
        node('weakness:' + w['id'], 'weakness', w['name'], f'grc/graph/index.html#{w["id"]}')
        for v in w.get('vulns', []):
            node('vulnerability:' + v, 'vulnerability', G['rev'][v]['name'], 'review/index.html#flaws'); edge('weakness:' + w['id'], 'arises_from', 'vulnerability:' + v, *by_grc)
        for p in w.get('code', []):
            node('repo:' + p, 'code', p, f'{REPO_URL}/blob/dev/{p}'); edge('weakness:' + w['id'], 'located_in', 'repo:' + p, *by_grc)
    for e in D['review']['edges']:
        if e['rel'] not in ('addresses', 'realised in', 'fixes'):
            continue
        a, b = G['rev'][e['from']], G['rev'][e['to']]
        if e['rel'] in ('addresses', 'fixes'):
            node('remediation:' + a['id'], 'remediation', a['name'], f'review/index.html#{a["id"]}'); node('vulnerability:' + b['id'], 'vulnerability', b['name'], 'review/index.html#flaws')
            edge('vulnerability:' + b['id'], 'fixed_by', 'remediation:' + a['id'], 'code', commit[:9])
        elif e['rel'] == 'realised in':
            node('remediation:' + a['id'], 'remediation', a['name'], f'review/index.html#{a["id"]}'); node('code:' + b['id'], 'code', b['name'].replace('file ', ''), 'review/index.html#areas')
            edge('remediation:' + a['id'], 'realised_in', 'code:' + b['id'], 'code', commit[:9])
    # Tests as nodes (CI-002.4): every test file of the fix commit, joined to the commit (read from it) and, by the
    # name rules in data/grc-tests.json, to the remediation it exercises (inferred until checked).
    if GRC_TESTS:
        if GRC_TESTS['source'] not in SOURCES or GRC_TESTS['commit'] != commit:
            sys.exit('data/grc-tests.json: its source or commit is not the fix commit the site records')
        for t in GRC_TESTS['files']:
            rule = next((r for r in GRC_TESTS['rules'] if re.search(r['match'], t)), None)
            ti = 'test:' + t
            node(ti, 'test', t + (' (harness)' if rule and rule.get('harness') else ''), f'https://github.com/php/php-src/blob/{commit}/{t}')
            edge(ti, 'tests', 'remediation:fix-commit', 'code', commit[:9])
            if rule and rule.get('remediation'):
                if 'remediation:' + rule['remediation'] not in seen:
                    sys.exit(f'data/grc-tests.json: rule {rule["match"]!r} names an unknown remediation {rule["remediation"]!r}')
                edge(ti, 'tests', 'remediation:' + rule['remediation'], 'inferred', 'dev', 'from the test name: ' + rule['why'])
    for r in G['R'].values():
        rn = 'risk:' + r['id']
        node(rn, 'risk', r['title'], f'grc/risks/{r["id"]}/index.html')
        if r['parent']: edge(rn, 'part_of', 'risk:' + r['parent'], *by_grc)
        for a in r['assign']: edge(rn, GRC_AS_VERB[a['as']][0], 'stakeholder:' + a['to'], *by_grc)
        for w in r['weaknesses']: edge(rn, 'arises_from', 'weakness:' + w, *by_grc)
        for v in r.get('concerns', []): edge(rn, 'concerns', 'vulnerability:' + v, *by_grc)
        for c in r['claims']:
            cl = G['claims'][c]; node('claim:' + c, 'claim', cl['claim'][:90], f'facts/{c}/index.html')
            src = [s for s in cl['sources'] if s in SOURCES]
            edge(rn, 'backed_by', 'claim:' + c, *(('source', src[0]) if src else by_grc))
            for s in src:
                node('source:' + s, 'source', SOURCES[s].get('publisher') or s, f'sources/{s}/index.html'); edge('claim:' + c, 'cites', 'source:' + s, 'source', s)
        for i, c in enumerate(r['controls']):
            node(f'treatment:{r["id"]}.{i + 1}', 'treatment', c['text'], c['page']); edge(rn, 'protected_by', f'treatment:{r["id"]}.{i + 1}', *by_grc)
        for x in r['frameworks']:
            f, c = G['CTL'][x]; node('control:' + x, 'control', f'{f["name"]} {c["id"]}: {c["title"]}', f'grc/frameworks/{f["id"]}/index.html#{grc_cid(c["id"])}'); edge(rn, 'governed_by', 'control:' + x, *by_grc)
        for s in r['stories']:
            a = G['arts'][s]; node('story:' + s, 'story', a['title'], f'articles/{s}/index.html'); edge(rn, 'told_in', 'story:' + s, *by_grc)
        for m in r['team']:
            mm = G['members'][m]; node('member:' + m, 'member', mm['name'], f'team/{m}/index.html'); edge(rn, 'tracked_by', 'member:' + m, *by_grc)
        for p in r['pages']:
            node('page:' + p, 'page', nav_title(p) if p in TITLES else p, p); edge(rn, 'shown_on', 'page:' + p, *by_grc)
    grc_confirm(edges)
    grc_check_basis(edges, seen)
    return nodes, edges

def grc_confirm(edges):
    """data/grc-basis.json: an edge somebody checked becomes confirmed, by whom and how; an unknown edge or person stops the build."""
    members = {m['id'] for m in TEAM['members']}
    for c in GRC_BASIS.get('confirmed', []):
        hit = [e for e in edges if e['from'] == c['from'] and e['rel'] == c['rel'] and e['to'] == c['to']]
        if not hit:
            sys.exit(f'data/grc-basis.json: no edge {c["from"]} {c["rel"]} {c["to"]}')
        if c.get('by') not in members:
            sys.exit(f'data/grc-basis.json: {c.get("by")!r} is not on the team')
        for e in hit:
            e['basis'] = {'kind': 'confirmed', 'ref': c['by'], 'note': c.get('how', ''), 'was': e['basis']['kind']}

def grc_check_basis(edges, seen):
    """Every edge says how it is known, and what it names exists: a capture, the fix commit, an agent or a person on the team."""
    members = {m['id'] for m in TEAM['members']}
    commit = D['code']['fix']['commit']
    for e in edges:
        b = e.get('basis') or {}
        k, ref = b.get('kind'), b.get('ref', '')
        ok = (k == 'source' and ref in SOURCES) or (k == 'code' and ref and commit.startswith(ref)) or (k in ('inferred', 'confirmed') and ref in members)
        if not ok:
            sys.exit(f'risk graph: edge {e["from"]} {e["rel"]} {e["to"]} has no valid basis ({b!r})')
        if e['from'] not in seen or e['to'] not in seen:
            sys.exit(f'risk graph: edge {e["from"]} {e["rel"]} {e["to"]} names a node that does not exist')

TITLES = {}

def grc_cid(cid):
    return 'c-' + re.sub(r'[^a-z0-9]+', '-', cid.lower()).strip('-')

def grc_s_link(G, sid, depth):
    return f'<a href="{"../" * depth}grc/stakeholders/{E(sid)}/index.html">{E(G["S"][sid]["name"])}</a>'

def grc_r_link(G, rid, depth, pill=True):
    r = G['R'][rid]
    return f'<a href="{"../" * depth}grc/risks/{E(rid)}/index.html">{E(rid.upper())} {E(r["title"])}</a>' + (f' {grc_pill(r)}' if pill else '')

def grc_c_link(G, x, depth):
    f, c = G['CTL'][x]
    return f'<a href="{"../" * depth}grc/frameworks/{E(f["id"])}/index.html#{grc_cid(c["id"])}" title="{E(c["title"])}">{E(f["name"])} {E(c["id"])}</a>'

def grc_heat(G, rids, depth):
    """Likelihood up, impact across: a 5 by 5 grid with each risk's id in its cell. Readable without colour: the score is in each cell."""
    R = G['R']
    rows = ''
    for l in range(5, 0, -1):
        cells = ''
        for i in range(1, 6):
            here = [x for x in rids if R[x]['likelihood'] == l and R[x]['impact'] == i]
            ids = ' '.join(f'<a href="{"../" * depth}grc/risks/{E(x)}/index.html" title="{E(R[x]["title"])}">{E(x.upper())}</a>' for x in here)
            cells += f'<td class="hm hm-{grc_band(l * i)}"><span class="hs">{l * i}</span> {ids}</td>'
        rows += f'<tr><th scope="row">{l} {E(GRC["scales"]["likelihood"][l - 1]["name"])}</th>{cells}</tr>'
    head = ''.join(f'<th scope="col">{i} {E(GRC["scales"]["impact"][i - 1]["name"])}</th>' for i in range(1, 6))
    return f'<div class="tw"><table class="t heat"><thead><tr><th>Likelihood / impact</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'

def grc_register(G, rids, depth, sid=None):
    """A register: one row per risk, the part the stakeholder plays, and whether it is assigned here or arrives through a part of it."""
    R, S = G['R'], G['S']
    rows = []
    below = set(grc_below(G['kids_s'], sid)) if sid else set()
    for x in sorted(rids, key=lambda x: (-grc_score(R[x]), x)):
        r = R[x]
        if sid:
            mine = [a for a in r['assign'] if a['to'] == sid]
            thru = [a for a in r['assign'] if a['to'] in below and a['to'] != sid]
            part = ', '.join(f'<b>{E(a["as"])}</b>' for a in mine) or '<i>through</i> ' + ', '.join(f'{grc_s_link(G, a["to"], depth)} ({E(a["as"])})' for a in thru)
        else:
            part = ', '.join(f'{grc_s_link(G, a["to"], depth)} <span class="small">{E(a["as"])}</span>' for a in r['assign'])
        rows.append([grc_r_link(G, x, depth, pill=False), grc_pill(r), E(GRC_CAT[r['category']]), part,
                     ', '.join(grc_c_link(G, c, depth) for c in r['frameworks'][:4]) + (f' <span class="small">+{len(r["frameworks"]) - 4}</span>' if len(r['frameworks']) > 4 else '')])
    return table(['Risk', 'Rating', 'Kind', 'Part played' if sid else 'Assigned to', 'Controls'], rows)

def grc_path_svg(G, rid, P):
    """One risk's chain in columns, every line a real edge: stories and roles tell and act on the risk, stakeholders carry it,
    it arises from weaknesses, which arise from vulnerabilities, fixed by parts of the fix, realised in code."""
    S, R, W, rev = G['S'], G['R'], G['W'], G['rev']
    cols = [
        ('Told in', [('s:' + s, G['arts'][s]['title'].split(':')[0], f'../../../articles/{s}/index.html', 'sy') for s in P['stories']]),
        ('Acted on by', [('o:' + s, S[s]['name'], f'../../stakeholders/{s}/index.html', 'ro') for s in P['roles']] + [('m:' + m, G['members'][m]['name'], f'../../../team/{m}/index.html', 'tm') for m in P['team']]),
        ('Carried by', [('a:' + a['to'], f'{S[a["to"]]["name"]} ({a["as"]})', f'../../stakeholders/{a["to"]}/index.html', 'st') for a in R[rid]['assign']]),
        ('Risk', [('r', rid.upper() + ' ' + R[rid]['title'], 'index.html', 'risk')]),
        ('Arises from', [('w:' + w, W[w]['name'], f'../../graph/index.html#{w}', 'wk') for w in P['weaknesses']]),
        ('Vulnerability', [('v:' + v, rev[v]['name'].split(':')[0], '../../../review/index.html#flaws', 'vu') for v in P['vulns']]),
        ('Fixed by', [('f:' + n, rev[n]['name'], f'../../../review/index.html#{n}', 'fx') for n in P['remediation']]),
        ('Code', [('c:' + c, rev[c]['name'].replace('file ', ''), '../../../review/index.html#areas', 'cd') for c in P['code']] + [('p:' + p, p, f'{REPO_URL}/blob/dev/{p}', 'cd') for p in P['repo']]),
    ]
    links = [(k, 'r') for k, *_ in cols[0][1] + cols[1][1] + cols[2][1]]
    wv = set()
    for w in P['weaknesses']:
        for v in W[w].get('vulns', []):
            if v in P['vulns']: links.append(('w:' + w, 'v:' + v)); wv.add(v)
        for p in W[w].get('code', []): links.append(('w:' + w, 'p:' + p))
        for n in W[w].get('remediation', []): links.append(('w:' + w, 'f:' + n))
    links += [('r', 'w:' + w) for w in P['weaknesses']] + [('r', 'v:' + v) for v in P['vulns'] if v not in wv]
    links += [('v:' + e['to'], 'f:' + e['from']) for e in D['review']['edges'] if e['rel'] == 'addresses' and e['to'] in P['vulns'] and e['from'] in P['remediation']]
    links += [('f:' + e['from'], 'c:' + e['to']) for e in D['review']['edges'] if e['rel'] == 'realised in' and e['from'] in P['remediation'] and e['to'] in P['code']]
    rh, cw = 20, 150
    H = 44 + rh * max(max(len(c[1]) for c in cols), 2)
    pos, out = {}, []
    for ci, (title, items) in enumerate(cols):
        x = ci * cw + 6
        out.append(f'<text class="t" x="{x}" y="14">{E(title)}</text>')
        if not items:
            out.append(f'<text class="n gap" x="{x}" y="36">none yet</text>')
        top = 34 + (H - 44 - rh * len(items)) / 2 if ci == 3 else 34
        for i, (k, label, href, cls) in enumerate(items):
            y = top + i * rh
            pos[k] = (x, y)
            out.append(f'<a href="{E(href)}"><title>{E(label)}</title><circle class="d g-{cls}" cx="{x + 3}" cy="{y:.1f}" r="4"/><text class="n" x="{x + 11}" y="{y + 4:.1f}">{E(label[:20])}{"…" if len(label) > 20 else ""}</text></a>')
    lines = []
    for a, b in links:
        if a in pos and b in pos:
            (x1, y1), (x2, y2) = sorted([pos[a], pos[b]])
            x1 += 7; x2 -= 1
            lines.append(f'<path class="e" d="M{x1},{y1:.1f} C{x1 + 55},{y1:.1f} {x2 - 55},{y2:.1f} {x2},{y2:.1f}"/>')
    return (f'<figure class="graph gpath"><svg viewBox="0 0 {cw * len(cols)} {H:.0f}" width="100%" role="img" aria-label="The path from this risk to the stories and roles on one side and its weaknesses, vulnerabilities, fixes and code on the other">{"".join(lines)}{"".join(out)}</svg>'
            '<figcaption>The risk sits in the middle. To its left, the stories that tell it, the roles and team members that act on it, and every stakeholder that carries part of it. To its right, what it arises from, the vulnerability behind that, the part of the fix that addresses it and the code the fix changed. Every line is an edge in the graph; every node is a link; hover for the full name. Vulnerabilities, stories and team members include those of the risk this one is part of; roles include those of the risks above and beneath it.</figcaption></figure>')

def grc_coverage(G, P_all):
    keys = [('vulns', 'a vulnerability'), ('code', 'code'), ('stories', 'a story'), ('roles', 'a role inside an organisation'), ('team', 'a member of this team')]
    out = []
    for k, label in keys:
        have = [x for x in G['R'] if P_all[x][k] or (k == 'code' and P_all[x]['repo'])]
        out.append((k, label, have, [x for x in G['R'] if x not in have]))
    return out

def build_grc():
    if not (GRC and GRCF):
        return
    for p, t, *_ in PAGES:
        TITLES[p] = t
    G = grc_index()
    S, R, W, FW, CTL = G['S'], G['R'], G['W'], G['FW'], G['CTL']
    P_all = {x: grc_path(G, x) for x in R}
    nodes, edges = grc_graph(G)
    write('data/grc-graph.json', json.dumps({'site': SITE, 'version': VERSION, 'kept_by': GRC['kept_by'], 'as_of': GRC['as_of'],
                                            'verbs': [{'verb': v, 'inverse': i} for v, i in GRC_VERBS.items()],
                                            'note': 'Every edge is a verb with its inverse named. A risk arises from a weakness, which arises from a vulnerability, which is fixed by a remediation, realised in code; the risk is backed by claims that cite sources, owned, borne and treated by stakeholders, governed by controls, told in stories and tracked by team members.',
                                            'nodes': nodes, 'edges': edges}, indent=1, ensure_ascii=False) + '\n')
    top = [x for x in R if R[x]['parent'] is None]
    cov = grc_coverage(G, P_all)
    fam = {f['id']: f for f in GRCF['families']}
    used_ctl = Counter(c for r in R.values() for c in r['frameworks'])
    kinds = Counter(n['kind'] for n in nodes)
    acc = '<p>No risk on this register is <b>accepted</b>. An acceptance is an act by the holder of a risk, for a stated interval, and nobody can accept on anyone else\'s behalf; this desk records risks and their holders, it does not accept for them. Until a holder accepts, funds or fixes, each risk stands as it is rated here.</p>'
    nav = '<p class="crumb"><a href="{u}grc/index.html">GRC</a> &middot; <a href="{u}grc/risks/index.html">Risks</a> &middot; <a href="{u}grc/stakeholders/index.html">Stakeholders</a> &middot; <a href="{u}grc/frameworks/index.html">Frameworks</a> &middot; <a href="{u}grc/graph/index.html">The graph</a> &middot; <a href="{u}grc/explore/index.html">Explore</a> &middot; <a href="{u}grc/gaps/index.html">Gaps</a> &middot; <a href="{u}grc/changes/index.html">Changes</a> &middot; <a href="{u}grc/network/index.html">From the network</a></p>'
    # --- the front page of the section
    stats = ''.join(stat(n, l) for n, l in [(len(R), 'risks'), (len(top), 'at the top'), (len(S), 'stakeholders'), (sum(1 for s in S.values() if s['kind'] == 'role'), 'roles'),
                                           (len(W), 'weaknesses'), (len(FW), 'frameworks'), (len(used_ctl), 'controls mapped'), (len(edges), 'edges')])
    covt = table(['Every risk reaches', 'Risks that do', 'Risks that do not yet'],
                 [[E(label), f'{len(have)} of {len(R)}', ', '.join(grc_r_link(G, x, 1, pill=False) for x in miss) or 'none'] for k, label, have, miss in cov])
    scales = table(['', 'Likelihood', 'Impact'], [[str(i + 1), f'<b>{E(l["name"])}</b>: {E(l["means"])}', f'<b>{E(m["name"])}</b>: {E(m["means"])}'] for i, (l, m) in enumerate(zip(GRC['scales']['likelihood'], GRC['scales']['impact']))])
    parts = table(['Part', 'Means', 'Edge'], [[f'<b>{E(a["name"])}</b>', E(a['means']), f'<code>{GRC_AS_VERB[a["id"]][0]}</code> / <code>{GRC_AS_VERB[a["id"]][1]}</code>'] for a in GRC['scales']['as']])
    body = f'''
{nav.format(u="../")}
<h1>GRC: the risks of php2shell, who carries them, and the standards that govern them</h1>
<p class="lead">A register of every risk in this story, broken down until each piece has someone who can act on it, and assigned to every stakeholder who carries part of it. The registers are fractal: the PHP project, a hosting provider, a council, a board and a developer each have one, and each is the same register read at a different scale. Every risk is backed by claims already on this site, and joined, edge by edge, to the weakness behind it, the vulnerability, the part of the fix that addresses it, the code that changed, the stories that tell it, the roles that act on it, and the controls in GDPR, NIS2, the Cyber Resilience Act, DORA, the EU AI Act, ISO 27001, NIST and the rest.</p>
<div class="stats">{stats}</div>
{section("heat", "Where the risks sit", grc_heat(G, list(R), 1), "Likelihood up, impact across; the number in each cell is the score, likelihood times impact. Click an id for the risk.")}
{section("top", "The ten risks at the top", grc_register(G, top, 1), "Each breaks down into the narrower risks it is made of; the full register is on the risks page.")}
{section("path", "From a risk to the code, the story and the role", '<p>The editor\'s test for this section: a path in the graph from every risk to the vulnerabilities, the code, the stories and the roles. The build walks it for every risk and the table below is the count; the gaps are listed by name, not hidden. A risk with no vulnerability is not a gap in itself: some risks here arise from how disclosure, regulation or this newsroom works, and their weaknesses point at the code in this repository that guards them instead.</p>' + covt)}
{section("model", "How the registers work", '<ul><li><b>A stakeholder is a node in a tree.</b> A sector holds organisations, an organisation holds roles. The same register is read at every level: a stakeholder\'s register is what is assigned to it plus everything that arrives through the parts below it.</li><li><b>A risk is a node in a tree.</b> A broad risk holds the narrower risks it is made of, until each can be owned.</li><li><b>One risk, many stakeholders.</b> Each assignment says the part played: owner, bearer, treater, source, informer or regulator. Two stakeholders that share a risk are connected; the stakeholders page shows by how much.</li><li><b>Every edge is a verb with a named inverse</b>, following the <a href="https://graphs.sgit.ai/v1/grammar/edge-set.html">sgit graph grammar</a>: a risk <i>arises from</i> a weakness, which <i>gives rise to</i> it; a risk is <i>owned by</i> a stakeholder, who <i>owns</i> it.</li><li><b>A rating is a judgement.</b> Likelihood and impact on a scale of 1 to 5, each with its basis in a sentence, as at the vault\'s last capture.</li></ul>' + acc + scales + parts)}
{section("files", "The data", f'<p>Authored: <a href="../data/grc.json">data/grc.json</a> ({len(S)} stakeholders, {len(W)} weaknesses, {len(R)} risks) and <a href="../data/grc-frameworks.json">data/grc-frameworks.json</a> ({len(FW)} frameworks, {len(CTL)} controls). Generated on every build: <a href="../data/grc-graph.json">data/grc-graph.json</a>, {len(nodes)} nodes and {len(edges)} edges. The build refuses a risk that points at a claim, source, story, page, member, code node or control that does not exist, and a risk with no owner. Kept by <a href="../team/grc/index.html">the GRC desk</a>.</p>')}
'''
    page('grc/index.html', 'GRC: the risks of php2shell, who carries them, and the standards that govern them', f'{len(R)} risks in a fractal register assigned to {len(S)} stakeholders, each joined to the weakness, vulnerability, fix, code, stories and roles behind it, and mapped to {len(used_ctl)} controls in {len(FW)} frameworks including GDPR, NIS2, the Cyber Resilience Act, DORA, the EU AI Act, ISO 27001 and NIST CSF.', body, kind='analysis', topics='php2shell grc risk register')
    # --- the full register
    def tree(x, depth=0):
        r = R[x]
        own = ', '.join(f'{grc_s_link(G, a["to"], 1 + 1)}' for a in r['assign'] if a['as'] == 'owner')
        row = f'<tr class="lvl-{depth}"><td style="padding-left:{0.5 + depth * 1.4}rem">{grc_r_link(G, x, 2, pill=False)}</td><td>{grc_pill(r)}</td><td>{E(GRC_CAT[r["category"]])}</td><td>{own}</td><td>{len(r["assign"])}</td><td>{len(r["frameworks"])}</td></tr>'
        return row + ''.join(tree(k, depth + 1) for k in G['kids_r'].get(x, []))
    th = ''.join(f'<th>{h}</th>' for h in ['Risk', 'Rating', 'Kind', 'Owned by', 'Stakeholders', 'Controls'])
    reg = f'<div class="tw"><table class="t grc-tree"><thead><tr>{th}</tr></thead><tbody>{"".join(tree(x) for x in top)}</tbody></table></div>'
    bycat = table(['Kind', 'Risks', 'Highest'], [[E(n), str(sum(1 for r in R.values() if r['category'] == c)), grc_r_link(G, max((x for x in R if R[x]['category'] == c), key=lambda x: grc_score(R[x])), 2)] for c, n in GRC_CAT.items() if any(r['category'] == c for r in R.values())])
    body = f'''
{nav.format(u="../../")}
<h1>The risk register: every risk, as a tree</h1>
<p class="lead">{len(R)} risks, {len(top)} at the top and {len(R) - len(top)} beneath them. A risk beneath another is a part of it narrow enough to own. Sorted as the tree; each row links to the risk's page with its full path.</p>
{reg}
{section("kinds", "By kind", bycat)}
{section("accept", "Acceptance", acc)}
'''
    page('grc/risks/index.html', 'The risk register: every php2shell risk, as a tree', f'All {len(R)} risks in the fractal register, with their rating, kind, owner and the number of stakeholders and controls each touches.', body, kind='analysis', topics='php2shell grc risk register')
    # --- one page per risk
    for x, r in R.items():
        P = P_all[x]
        anc = list(reversed(grc_ancestors(R, x)))
        crumb = ' / '.join([f'<a href="../index.html">Risks</a>'] + [grc_r_link(G, a, 3, pill=False) for a in anc] + [E(x.upper())])
        assign = table(['Stakeholder', 'Part', 'Why', 'Its register'], [[grc_s_link(G, a['to'], 3), f'<b>{E(a["as"])}</b>', E(a['why']), (lambda n: f'{n} risk' + ('' if n == 1 else 's'))(len(grc_s_rids(G, a['to'])))] for a in r['assign']])
        kids = G['kids_r'].get(x, [])
        sub = section('parts', 'The risks this one is made of', grc_register(G, kids, 3)) if kids else ''
        cl = table(['Claim', 'Status', 'Fact-check', 'Sources'], [[f'<a href="../../../facts/{E(c)}/index.html">{E(G["claims"][c]["claim"])}</a>', pill(G['claims'][c]['status']), assure(c, short=True), src_links(G['claims'][c]['sources'], 3)] for c in r['claims']]) if r['claims'] else '<p>No claim on this site carries this risk: it rests on how this newsroom works, set out on the pages linked below.</p>'
        ctl = table(['Treatment', 'Status', 'Where'], [[E(c['text']), f'<span class="gt gt-{E(c["status"])}">{E(c["status"].replace("-", " "))}</span>', f'<a href="../../../{E(c["page"])}">{E(TITLES.get(c["page"].split("#")[0], c["page"]))}</a>'] for c in r['controls']])
        fw = table(['Framework', 'Control', 'What it asks', 'Family'], [[f'<a href="../../frameworks/{E(CTL[c][0]["id"])}/index.html">{E(CTL[c][0]["name"])}</a>', f'<a href="../../frameworks/{E(CTL[c][0]["id"])}/index.html#{grc_cid(CTL[c][1]["id"])}">{E(CTL[c][1]["id"])}</a>', E(CTL[c][1]['title']), E(fam[CTL[c][0]['family']]['name'])] for c in r['frameworks']])
        ws = ''.join(f'<li><b>{E(W[w]["name"])}.</b> {E(W[w]["about"])}</li>' for w in P['weaknesses'])
        stor = ''.join(f'<li><a href="../../../articles/{E(s)}/index.html">{E(G["arts"][s]["title"])}</a>{"" if s in P["own_stories"] else " <span class=small>(through " + E(R[r["parent"]]["title"] if r["parent"] else "") + ")</span>"}</li>' for s in P['stories']) or '<li>No story on this site tells this risk yet.</li>'
        pages_ = ' &middot; '.join(f'<a href="../../../{E(p)}">{E(TITLES.get(p.split("#")[0], p))}</a>' for p in r['pages'])
        shares = Counter(b['to'] for a in r['assign'] for y in R if y != x for b in R[y]['assign'] if b['to'] == a['to'])
        body = f'''
<p class="crumb">{crumb}</p>
<h1>{E(x.upper())}: {E(r["title"])}</h1>
<p class="lead">{E(r["statement"])}</p>
<p class="small"><a href="../../explore/index.html#focus=risk:{E(x)}">Explore the graph from this risk</a> &middot; <a href="../../gaps/index.html">What the graph is missing</a></p>
<p class="kv"><b>Rating</b> {grc_pill(r)} &middot; <b>Likelihood</b> {r["likelihood"]} {E(GRC["scales"]["likelihood"][r["likelihood"] - 1]["name"])} &middot; <b>Impact</b> {r["impact"]} {E(GRC["scales"]["impact"][r["impact"] - 1]["name"])} &middot; <b>Kind</b> {E(GRC_CAT[r["category"]])} &middot; <b>Acceptance</b> not recorded</p>
<p class="note"><b>Basis.</b> {E(r["basis"])}</p>
{section("path", "The path", grc_path_svg(G, x, P))}
{section("assigned", "Who carries it", assign, "One risk, assigned to every stakeholder that carries part of it, with the part each plays.")}
{sub}
{section("weak", "What it arises from", "<ul>" + ws + "</ul>")}
{section("evidence", "The evidence", cl)}
{section("treat", "Treatments", ctl)}
{section("controls", "The standards that govern it", fw)}
{section("stories", "The stories that tell it", "<ul>" + stor + "</ul>" + ("<p>On this site: " + pages_ + "</p>" if pages_ else ""))}
'''
        page(f'grc/risks/{x}/index.html', f'{x.upper()}: {r["title"]}', r['statement'][:300], body, kind='analysis', topics='php2shell grc risk')
    # --- stakeholders
    def stree(sid, depth=0):
        s = S[sid]
        n_own = sum(1 for r in R.values() for a in r['assign'] if a['to'] == sid)
        n_all = len(grc_s_rids(G, sid))
        row = f'<tr><td style="padding-left:{0.5 + depth * 1.4}rem">{grc_s_link(G, sid, 2)}</td><td>{E(s["kind"])}</td><td>{n_own}</td><td>{n_all}</td></tr>'
        return row + ''.join(stree(k, depth + 1) for k in G['kids_s'].get(sid, []))
    th = ''.join(f'<th>{h}</th>' for h in ['Stakeholder', 'Kind', 'Assigned here', 'In its register'])
    st_tree = f'<div class="tw"><table class="t grc-tree"><thead><tr>{th}</tr></thead><tbody>{stree("world")}</tbody></table></div>'
    lvl1 = G['kids_s']['world']
    pairs = {}
    for r in R.values():
        groups = sorted({next((g for g in lvl1 if a['to'] in grc_below(G['kids_s'], g)), 'world') for a in r['assign']} - {'world'})
        for i, a in enumerate(groups):
            for b in groups[i + 1:]:
                pairs[(a, b)] = pairs.get((a, b), 0) + 1; pairs[(b, a)] = pairs[(a, b)]
    mh = ''.join(f'<th scope="col" title="{E(S[g]["name"])}">{E(S[g]["name"].split()[0] if S[g]["name"].split()[0] not in ("The", "Everyone") else S[g]["name"].split()[1])}</th>' for g in lvl1)
    mrows = ''.join(f'<tr><th scope="row">{grc_s_link(G, a, 2)}</th>' + ''.join(f'<td class="mx">{"&middot;" if a == b else (pairs.get((a, b)) or "")}</td>' for b in lvl1) + '</tr>' for a in lvl1)
    matrix = f'<div class="tw"><table class="t mxt"><thead><tr><th></th>{mh}</tr></thead><tbody>{mrows}</tbody></table></div>'
    body = f'''
{nav.format(u="../../")}
<h1>Stakeholders: a register for each, at every scale</h1>
<p class="lead">{len(S)} stakeholders in one tree, from everyone with PHP in the path down to the roles inside a single organisation. Each has a register: the risks assigned to it, and the risks that arrive through the parts beneath it. The register belongs to the stakeholder, so it reads the same whether the stakeholder is a sector, a council or a CISO.</p>
{st_tree}
{section("connected", "How the stakeholders are connected", matrix, "The number in a cell is how many risks the two groups share: a risk assigned to someone in one and someone in the other. A risk that joins many groups is one no single party can treat alone.")}
'''
    page('grc/stakeholders/index.html', 'Stakeholders: a php2shell risk register for each, at every scale', f'{len(S)} stakeholders in one tree, each with its own risk register, and the risks that connect them.', body, kind='analysis', topics='php2shell grc stakeholders')
    for sid, s in S.items():
        rids = grc_s_rids(G, sid)
        anc = list(reversed(grc_ancestors(S, sid)))
        crumb = ' / '.join([f'<a href="../index.html">Stakeholders</a>'] + [grc_s_link(G, a, 3) for a in anc] + [E(s['name'])])
        kids = G['kids_s'].get(sid, [])
        kid_l = ''.join(f'<li>{grc_s_link(G, k, 3)}: {len(grc_s_rids(G, k))} risks</li>' for k in kids)
        own_ids = [r['id'] for r in R.values() if any(a['to'] == sid for a in r['assign'])]
        sharers = Counter(a['to'] for x in own_ids for a in R[x]['assign'] if a['to'] != sid)
        sh = ', '.join(f'{grc_s_link(G, o, 3)} ({n})' for o, n in sharers.most_common(12))
        extra = []
        if s.get('audience'):
            a = next(y for y in D['roles']['audiences'] if y['id'] == s['audience'])
            extra.append(f'<a href="../../../briefings/{E(a["id"])}/index.html">the briefing for a {E(a["name"].lower())}</a>')
        if s.get('member'):
            extra.append(f'<a href="../../../team/{E(s["member"])}/index.html">their team page</a>')
        if s.get('actors'):
            extra.append('in the story as ' + ', '.join(f'<a href="../../../actors/index.html#{E(a)}">{E(next(y["name"] for y in D["actors"] if y["id"] == a).split("(")[0].strip())}</a>' for a in s['actors']))
        ctls = Counter(c for x in rids for c in R[x]['frameworks'])
        fwc = Counter(CTL[c][0]['id'] for c in ctls)
        fw_line = ', '.join(f'<a href="../../frameworks/{E(f)}/index.html">{E(FW[f]["name"])}</a> ({n})' for f, n in fwc.most_common())
        body = f'''
<p class="crumb">{crumb}</p>
<h1>{E(s["name"])}: its risk register</h1>
<p class="lead">{E(s["about"])}</p>
<p class="kv"><b>Kind</b> {E(s["kind"])} &middot; <b>Assigned here</b> {len(own_ids)} &middot; <b>In its register</b> {len(rids)}{(" &middot; " + " &middot; ".join(extra)) if extra else ""}</p>
{section("register", "The register", grc_register(G, rids, 3, sid) if rids else "<p>No risk is assigned here or below.</p>", "Assigned here, or arriving through a part of this stakeholder. The part played is the one recorded for whoever holds the assignment.")}
{section("heat", "Where its risks sit", grc_heat(G, rids, 3)) if rids else ""}
{section("parts", "Its parts", "<ul>" + kid_l + "</ul>") if kids else ""}
{section("shares", "Who it shares risks with", "<p>" + sh + "</p>") if sh else ""}
{section("standards", "The standards its register touches", "<p>" + fw_line + "</p>") if fw_line else ""}
'''
        page(f'grc/stakeholders/{sid}/index.html', f'{s["name"]}: its php2shell risk register', f'The fractal risk register for {s["name"]}: {len(rids)} risks assigned to it or arriving through its parts, the part it plays in each and who it shares them with.', body, kind='analysis', topics='php2shell grc stakeholder')
    # --- frameworks
    fams = ''
    for f0 in GRCF['families']:
        rows = [[f'<a href="{E(f["id"])}/index.html"><b>{E(f["name"])}</b></a><div class="note">{E(f["full"])}</div>', E(f['version']), str(sum(1 for c in f['controls'] if f'{f["id"]}:{c["id"]}' in used_ctl)) + f' of {len(f["controls"])}', str(len({x for x in R if any(c.startswith(f["id"] + ":") for c in R[x]["frameworks"])})), E(f['why'])] for f in GRCF['frameworks'] if f['family'] == f0['id']]
        fams += section('f-' + f0['id'], E(f0['name']), table(['Framework', 'Version', 'Controls used', 'Risks', 'Why it is here'], rows), E(f0['about']))
    fh = ''.join(f'<th scope="col"><a href="{E(f["id"])}/index.html">{E(f["name"].split()[0])}</a></th>' for f in GRCF['frameworks'])
    frows = ''.join(f'<tr><th scope="row">{grc_r_link(G, x, 2, pill=False)}</th>' + ''.join(f'<td class="mx">{sum(1 for c in R[x]["frameworks"] if c.startswith(f["id"] + ":")) or ""}</td>' for f in GRCF['frameworks']) + '</tr>' for x in R)
    fmx = f'<div class="tw"><table class="t mxt"><thead><tr><th>Risk</th>{fh}</tr></thead><tbody>{frows}</tbody></table></div>'
    body = f'''
{nav.format(u="../../")}
<h1>Frameworks: the law, the standards and the controls each risk maps to</h1>
<p class="lead">{len(FW)} frameworks, {len(CTL)} clauses and controls, {len(used_ctl)} of them mapped to at least one risk. A mapping says which control a holder of the risk will be asked about, by an auditor, a regulator or a board; it does not say the control is in place. Control titles are this desk's short paraphrase; each framework links to its official text.</p>
{fams}
{section("matrix", "Risks against frameworks", fmx, "How many of each framework's controls each risk maps to.")}
'''
    page('grc/frameworks/index.html', 'Frameworks: php2shell risks mapped to GDPR, NIS2, CRA, DORA, the EU AI Act, ISO 27001 and NIST', f'{len(FW)} frameworks and {len(CTL)} controls, and which php2shell risks map to each.', body, kind='analysis', topics='php2shell grc frameworks')
    for f in GRCF['frameworks']:
        rows = []
        for c in f['controls']:
            k = f'{f["id"]}:{c["id"]}'
            rs = [x for x in R if k in R[x]['frameworks']]
            holders = Counter(a['to'] for x in rs for a in R[x]['assign'] if a['as'] in ('owner', 'regulator'))
            rows.append([f'<span id="{grc_cid(c["id"])}"><b>{E(c["id"])}</b></span>', E(c['title']), '<br>'.join(grc_r_link(G, x, 3) for x in rs) or '<i>no risk mapped</i>',
                         ', '.join(grc_s_link(G, h, 3) for h, _ in holders.most_common(5))])
        body = f'''
<p class="crumb"><a href="../index.html">Frameworks</a> / {E(f["name"])}</p>
<h1>{E(f["name"])}: the php2shell risks it governs</h1>
<p class="lead">{E(f["why"])}</p>
<p class="kv"><b>Full name</b> {E(f["full"])} &middot; <b>Publisher</b> {E(f["publisher"])} &middot; <b>Version</b> {E(f["version"])} &middot; <a href="{U(f["url"])}">the official text</a></p>
{section("controls", "Clauses and controls", table(["Control", "What it asks (paraphrased)", "Risks mapped", "Owned or regulated by"], rows))}
'''
        page(f'grc/frameworks/{f["id"]}/index.html', f'{f["name"]}: the php2shell risks it governs', f'Each {f["name"]} clause or control the GRC desk cites, the php2shell risks mapped to it and who owns them.', body, kind='analysis', topics='php2shell grc ' + f['id'])
    # --- the graph
    kinds_t = table(['Kind of node', 'How many'], [[E(k), str(n)] for k, n in kinds.most_common()])
    bk = Counter((e['basis']['kind'], e['rel']) for e in edges)
    basis_t = table(['How it is known', 'Edges', 'Verbs'], [[f'<b>{E(k)}</b>: {E(t)}', str(sum(n for (kk, _), n in bk.items() if kk == k)),
                     E(', '.join(f'{v} {n}' for (kk, v), n in sorted(bk.items(), key=lambda x: -x[1]) if kk == k))] for k, t in GRC_BASES.items() if any(kk == k for kk, _ in bk)])
    verbs_t = table(['Verb', 'Inverse', 'Edges'], [[f'<code>{E(v)}</code>', f'<code>{E(i)}</code>', str(sum(1 for e in edges if e['rel'] == v))] for v, i in GRC_VERBS.items() if any(e['rel'] == v for e in edges)])
    wl = ''.join(f'<article class="role" id="{E(w["id"])}"><h3>{E(w["name"])}</h3><p>{E(w["about"])}</p><p class="small">Gives rise to: {", ".join(grc_r_link(G, x, 2, pill=False) for x in R if w["id"] in R[x]["weaknesses"])}'
                 + (f'<br>Arises from: {", ".join(E(G["rev"][v]["name"]) for v in w.get("vulns", []))}' if w.get('vulns') else '')
                 + (f'<br>In this repository: {", ".join(f"<a href={chr(34)}{REPO_URL}/blob/dev/{E(p)}{chr(34)}><code>{E(p)}</code></a>" for p in w.get("code", []))}' if w.get('code') else '') + '</p></article>' for w in W.values())
    # the overview drawing: top risks in the middle, groups on the left, weaknesses then vulnerabilities on the right
    lft, mid, rgt, rr = lvl1, top, list(W), [v for v in G['rev'] if G['rev'][v]['layer'] == 'vulnerability']
    H = 40 + 20 * max(len(lft), len(mid), len(rgt))
    def ys(n): return [30 + i * (H - 50) / max(1, n - 1) for i in range(n)]
    yl, ym, yw, yv = dict(zip(lft, ys(len(lft)))), dict(zip(mid, ys(len(mid)))), dict(zip(rgt, ys(len(rgt)))), dict(zip(rr, [H / 3, 2 * H / 3]))
    X = [190, 420, 640, 930]
    ln = []
    for x in mid:
        for g in sorted({next((g for g in lft if a['to'] in grc_below(G['kids_s'], g)), None) for r2 in grc_below(G['kids_r'], x) for a in R[r2]['assign']} - {None}):
            ln.append(f'<path class="e" d="M{X[0]},{yl[g]:.1f} C{X[0] + 110},{yl[g]:.1f} {X[1] - 110},{ym[x]:.1f} {X[1]},{ym[x]:.1f}"/>')
        for w in sorted({w for r2 in grc_below(G['kids_r'], x) for w in R[r2]['weaknesses']}):
            ln.append(f'<path class="e e-w" d="M{X[1]},{ym[x]:.1f} C{X[1] + 100},{ym[x]:.1f} {X[2] - 100},{yw[w]:.1f} {X[2]},{yw[w]:.1f}"/>')
    for w in rgt:
        for v in W[w].get('vulns', []):
            ln.append(f'<path class="e e-v" d="M{X[2]},{yw[w]:.1f} C{X[2] + 110},{yw[w]:.1f} {X[3] - 110},{yv[v]:.1f} {X[3]},{yv[v]:.1f}"/>')
    tx = [f'<text class="t" x="{X[0] - 6}" y="12" text-anchor="end">stakeholders</text><text class="t" x="{X[1]}" y="12" text-anchor="middle">risks at the top</text><text class="t" x="{X[2] + 6}" y="12">weaknesses</text><text class="t" x="{X[3] - 6}" y="12" text-anchor="end">vulnerabilities</text>']
    tx += [f'<a href="../stakeholders/{E(g)}/index.html"><text class="n" x="{X[0] - 8}" y="{yl[g] + 3:.1f}" text-anchor="end">{E(S[g]["name"][:34])}</text><circle class="d g-st" cx="{X[0]}" cy="{yl[g]:.1f}" r="3.5"/></a>' for g in lft]
    tx += [f'<a href="../risks/{E(x)}/index.html"><circle class="d g-risk" cx="{X[1]}" cy="{ym[x]:.1f}" r="5"/><text class="n rl" x="{X[1]}" y="{ym[x] - 7:.1f}" text-anchor="middle">{E(x.upper())} {E(R[x]["title"][:40])}{"…" if len(R[x]["title"]) > 40 else ""}</text></a>' for x in mid]
    tx += [f'<a href="#{E(w)}"><circle class="d g-wk" cx="{X[2]}" cy="{yw[w]:.1f}" r="3.5"/><text class="n" x="{X[2] + 8}" y="{yw[w] + 3:.1f}">{E(W[w]["name"][:36])}{"…" if len(W[w]["name"]) > 36 else ""}</text></a>' for w in rgt]
    tx += [f'<a href="../../review/index.html#flaws"><circle class="d g-vu" cx="{X[3]}" cy="{yv[v]:.1f}" r="5"/><text class="n" x="{X[3]}" y="{yv[v] + 18:.1f}" text-anchor="middle">{E(G["rev"][v]["name"].split(":")[0])}</text></a>' for v in rr]
    svg = f'<figure class="graph"><svg viewBox="0 0 1000 {H:.0f}" width="100%" role="img" aria-label="Stakeholder groups joined to the ten top risks, the risks to the weaknesses they arise from, and the weaknesses to the two vulnerabilities">{"".join(ln)}{"".join(tx)}</svg><figcaption>A line from a stakeholder group to a risk means someone in the group carries part of it or of a risk beneath it; a line from a risk to a weakness means the risk, or one beneath it, arises from it; the weaknesses on the two CVEs reach the fix and the code on <a href="../../review/index.html">the code review graph</a>. Each risk\'s own page draws its whole path.</figcaption></figure>'
    body = f'''
{nav.format(u="../../")}
<h1>The risk graph: stakeholders, risks, weaknesses, vulnerabilities, code</h1>
<p class="lead">{len(nodes)} nodes and {len(edges)} edges, built from the register on every release and joined to the graphs already on this site: the claims and their sources (<a href="../../graph/index.html">the story graph</a>) and the fix and the code it changed (<a href="../../review/index.html">the code review graph</a>). One graph, no copies: a claim, a source or a file is the same node here as there. The JSON is <a href="../../data/grc-graph.json">data/grc-graph.json</a>.</p>
{svg}
{section("weaknesses", "The weaknesses", wl, "What the risks arise from. Two are the CVEs themselves; the rest are conditions of the ecosystem, the disclosure process and this newsroom, each joined to the risks it gives rise to and, where there is one, to the code.")}
{section("kinds", "What is in it", kinds_t)}
{section("verbs", "The verbs", verbs_t, "Every edge is a verb read from the first node to the second; its inverse is read back. No edge says only that two things are related.")}
{section("basis", "How each edge is known", basis_t, "Every edge says how it is known: read from a capture (with its slug), read from the fix commit, inferred by an agent (with the agent), or confirmed by a person (data/grc-basis.json). The drawing above shows the register's own joins, which are the GRC desk's inferences. To walk the graph one node at a time, with inferred edges dashed, use <a href=\"../explore/index.html\">explore</a>; for what is missing, <a href=\"../gaps/index.html\">the gaps</a>.")}
'''
    page('grc/graph/index.html', 'The risk graph: php2shell stakeholders, risks, weaknesses, vulnerabilities and code', f'{len(nodes)} nodes and {len(edges)} typed edges joining every php2shell risk to its stakeholders, weaknesses, vulnerabilities, fixes, code, claims, stories, roles and controls.', body, kind='analysis', topics='php2shell grc graph')
    build_grc_explore(nodes, edges, nav)
    build_grc_gaps(nodes, edges, nav)
    GRC_NAV[0] = nav; build_grc_changes()
    build_grc_network(G, nav)

# ----------------------------------------------------------------------------- the risk graph as a tool (CI-002, the brief of 23 October)

def build_grc_explore(nodes, edges, nav):
    """/grc/explore/: start from any node and expand, or climb from code to what it puts at stake (assets/grc-explore.js)."""
    kinds = Counter(n['kind'] for n in nodes)
    body = f"""
{nav.format(u="../../")}
<h1>Explore the risk graph: start from one thing and follow it</h1>
<p class="lead">The whole graph is {len(nodes)} nodes and {len(edges)} edges, too much to read at once. Start from one thing you care about (a CVE, a risk, the people who run PHP, a file of the fix, a test, a control) and see only what touches it, grouped by how; open any of those to go one step further, with the way back always shown. Or start from code or a test and climb: the fixes it realises, the flaws they fix, the risks above them, and the controls, stakeholders and stories of each risk.</p>
<div id="explore" class="gx"><p class="small">The explorer needs JavaScript; it reads <a href="../../data/grc-graph.json">data/grc-graph.json</a> in your browser and sends nothing anywhere.</p></div>
<h2>How to read it</h2>
<ul>
<li><b>Every edge is a verb</b>, read from the node you are on: a risk <i>arises from</i> a weakness, a test <i>tests</i> a fix, a file <i>realises</i> a fix.</li>
<li><b>Every edge says how it is known.</b> Read from a capture, read from the fix commit, inferred by an agent, or confirmed by a person. Inferred edges are dashed; one switch hides them, and the view shows what is left. Each link names what supports it.</li>
<li><b>The address is the view.</b> Copy it to send someone exactly what you are looking at: the start, everything you opened, and whether inferred edges are hidden.</li>
</ul>
<p class="small">In the graph: {E(', '.join(f'{n} {k}' for k, n in kinds.most_common()))}. The tests are the {kinds.get('test', 0)} test files of the fix commit, from its file list in the evidence vault (<a href="../../data/grc-tests.json">data/grc-tests.json</a>).</p>
<script src="../../assets/grc-explore.js" defer></script>
"""
    page('grc/explore/index.html', 'Explore the risk graph: start from one thing and follow it', 'Start from a CVE, a risk, a stakeholder, a file, a test or a control and see only what touches it, grouped by verb, one step at a time; or climb from code to the risks, controls and stakeholders above it. Every edge says how it is known.', body, kind='analysis', topics='php2shell grc graph explore')

def grc_reach(adj, start, kinds, verbs, within):
    """Breadth-first from start, in either direction, up to `within` steps (through `verbs` only, if named). The first
    node of one of `kinds` found, or None."""
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

def grc_vkey(v):
    return [int(x) for x in v.split('.')]

def grc_change_html(ch, depth):
    """One comparison of the risk graph, old against new: the measures side by side, then what was added, removed,
    re-based and which gaps opened or closed. The same structure assets/grc-changes.js draws for any two releases."""
    L, up = GRC_HISTORY['labels'], '../' * depth
    rules = {r['id']: r for r in (GRC_GAPS or {}).get('rules', [])}
    def lab(i):
        k, t = L.get(i, ['', i])
        return f'<a href="{up}grc/explore/index.html#focus={E(i)}">{E(t)}</a> <span class="small">{E(k)}</span>'
    def edge_txt(k):
        a, v, b = k.split(' ', 2)
        return f'{E(L.get(a, ["", a])[1][:60])} <i>{E(v.replace("_", " "))}</i> {E(L.get(b, ["", b])[1][:60])}'
    def listing(items, fmt, cap=60):
        more = f'<li class="small">and {len(items) - cap} more</li>' if len(items) > cap else ''
        return '<ul class="gc-list">' + ''.join(f'<li>{fmt(x)}</li>' for x in items[:cap]) + more + '</ul>'
    b0, b1 = ch['before'], ch['after']
    rows = [['Nodes', b0['nodes'], b1['nodes']], ['Edges', b0['edges'], b1['edges']]]
    for kind in ('source', 'code', 'inferred', 'confirmed', 'unrecorded'):
        x, y = b0['basis'].get(kind, 0), b1['basis'].get(kind, 0)
        if x or y:
            rows.append([f'Edges {"with no basis recorded" if kind == "unrecorded" else "known as " + kind}', x, y])
    for rid, r in rules.items():
        rows.append([f'Gap: {r["title"]}', b0['gaps'].get(rid, 0), b1['gaps'].get(rid, 0)])
    def delta(x, y):
        d = y - x
        return f'<span class="gc-{"up" if d > 0 else "down"}">{"+" if d > 0 else ""}{d:,}</span>' if d else '<span class="small">same</span>'
    out = [f'<div class="tw"><table class="t gc-measures"><thead><tr><th>Measure</th><th>v{E(ch["from"] or "none")}</th><th>v{E(ch["to"])}</th><th>Change</th></tr></thead><tbody>'
           + ''.join(f'<tr><td>{E(m)}</td><td>{x:,}</td><td>{y:,}</td><td>{delta(x, y)}</td></tr>' for m, x, y in rows) + '</tbody></table></div>']
    def by_kind(ids):
        k = Counter(L.get(i, ['?'])[0] for i in ids)
        return ', '.join(f'{n} {E(kind)}' for kind, n in k.most_common())
    if ch['nodes_added']:
        out.append(f'<h3>Nodes added: {len(ch["nodes_added"])}</h3><p class="small">{by_kind(ch["nodes_added"])}</p>' + listing(ch['nodes_added'], lab))
    if ch['nodes_removed']:
        out.append(f'<h3>Nodes removed: {len(ch["nodes_removed"])}</h3>' + listing(ch['nodes_removed'], lambda i: E(L.get(i, ["", i])[1])))
    if ch['edges_added']:
        verbs = Counter(k.split(' ')[1] for k, _ in ch['edges_added'])
        out.append(f'<h3>Edges added: {len(ch["edges_added"])}</h3><p class="small">' + ', '.join(f'{n} <i>{E(v.replace("_", " "))}</i>' for v, n in verbs.most_common()) + '</p>'
                   + listing(ch['edges_added'], lambda kb: f'{edge_txt(kb[0])} <span class="gx-basis gx-b-{E(kb[1])}">{E(kb[1])}</span>', 40))
    if ch['edges_removed']:
        out.append(f'<h3>Edges removed: {len(ch["edges_removed"])}</h3>' + listing(ch['edges_removed'], edge_txt, 40))
    if ch['basis_changed']:
        out.append(f'<h3>How an edge is known, changed: {len(ch["basis_changed"])}</h3>' + listing(ch['basis_changed'], lambda x: f'{edge_txt(x[0])}: {E(x[1])} &rarr; <b>{E(x[2])}</b>'))
    if ch['basis_recorded']:
        k = Counter(b for _, b in ch['basis_recorded'])
        out.append(f'<h3>Basis recorded for the first time: {len(ch["basis_recorded"])} edges</h3><p class="small">Before, edges carried no basis. Now: ' + ', '.join(f'{n} {E(b)}' for b, n in k.most_common()) + '.</p>')
    for word, key in (('opened', 'gaps_opened'), ('closed', 'gaps_closed')):
        for rid, ids in ch[key].items():
            title = rules.get(rid, {}).get('title', rid)
            out.append(f'<h3>Gap {word}: {E(title)} ({len(ids)})</h3>' + listing(ids, lab))
    if len(out) == 1:
        out.append('<p>Nothing in the graph changed between these two releases.</p>')
    return ''.join(out)

def grc_releases():
    """Every release with a graph, oldest first, each with its totals (those of the last change at or before it)."""
    ch = {r['version']: r for r in GRC_HISTORY['releases']}
    vs = sorted(set(ch) | set(GRC_HISTORY.get('unchanged', [])), key=grc_vkey)
    out, last = [], {'nodes': 0, 'edges': 0, 'basis': {}, 'gaps': {}}
    for v in vs:
        if v in ch:
            last = ch[v]['totals']
        out.append((v, ch.get(v), last))
    return out

def build_grc_changes():
    """/grc/changes/: what changed in the risk graph between releases (CI-003.8), from data/grc-history.json."""
    nav = GRC_NAV[0]
    if nav is None or not GRC_HISTORY['releases']:
        return
    rels = grc_releases()
    tot = {v: t for v, _, t in rels}
    dates = {x['version']: x['date'] for x in D['versions']['versions']}
    changed = [(v, c) for v, c, _ in rels if c]
    def pair(c):
        before = tot.get(c['against']) if c['against'] else {'nodes': 0, 'edges': 0, 'basis': {}, 'gaps': {}}
        return dict(c, **{'from': c['against'], 'to': c['version'], 'before': before, 'after': c['totals']})
    lv, lc = changed[-1]
    rows = ''.join(f'<tr><td><a href="#from={E(c["against"] or "")}&amp;to={E(v)}">v{E(v)}</a> <span class="small">{E(dates.get(v, ""))}</span></td><td>{"v" + E(c["against"]) if c["against"] else "the first graph"}</td>'
                   f'<td>+{len(c["nodes_added"])} &minus;{len(c["nodes_removed"])}</td><td>+{len(c["edges_added"])} &minus;{len(c["edges_removed"])}</td>'
                   f'<td>{len(c["basis_changed"]) + len(c["basis_recorded"])}</td><td>+{sum(map(len, c["gaps_opened"].values()))} &minus;{sum(map(len, c["gaps_closed"].values()))}</td>'
                   f'<td>{c["totals"]["nodes"]:,} / {c["totals"]["edges"]:,}</td></tr>' for v, c in reversed(changed))
    body = f"""
{nav.format(u="../../")}
<h1>What changed in the risk graph, release by release</h1>
<p class="lead">The graph is rebuilt at every release. This page compares two releases of it: the nodes and edges added and removed, the edges whose basis changed (from inferred to confirmed, say), and the gaps that opened or closed. {len(rels)} releases carry a graph; {len(changed)} of them changed it. Pick any two below; the default is the latest change.</p>
<div class="gc-pick" id="gc-pick" data-releases="{E(" ".join(v for v, _, _ in rels))}"></div>
<section id="gc-pair"><h2>v{E(lc["against"] or "none")} &rarr; v{E(lv)}</h2>{grc_change_html(pair(lc), 2)}</section>
<h2 id="releases">Every release that changed the graph</h2>
{'<div class="tw"><table class="t"><thead><tr><th>Release</th><th>Against</th><th>Nodes</th><th>Edges</th><th>Bases</th><th>Gaps</th><th>Nodes / edges after</th></tr></thead><tbody>' + rows + '</tbody></table></div>'}
<p class="small">How it is made: every release commits the graph the build wrote (<a href="../../data/grc-graph.json">data/grc-graph.json</a>). <code>admin/build/grc_history.py</code> compares each release's graph with the one before and keeps what changed in <a href="../../data/grc-history.json">data/grc-history.json</a>, written once per release, at its own build. The gaps are counted with today's rules (<a href="../../data/grc-gaps.json">data/grc-gaps.json</a>) over each release's graph, so every pair is measured the same way. An edge is the same edge when its start, verb and end are the same. Graphs before v0.10.13 recorded no basis on an edge. Comparing two releases that are not next to each other replays the changes between them in your browser.</p>
<script src="../../assets/grc-changes.js" defer></script>
"""
    page('grc/changes/index.html', 'What changed in the risk graph, release by release', 'The php2shell risk graph compared between any two releases: nodes and edges added and removed, bases changed, gaps opened and closed; computed from git at every release.', body, kind='analysis', topics='php2shell grc graph changes releases')

def build_grc_gaps(nodes, edges, nav):
    """/grc/gaps/: what the graph is missing, computed at every build from the rules in data/grc-gaps.json."""
    if not GRC_GAPS:
        return
    N = {n['id']: n for n in nodes}
    adj = {}
    for e in edges:
        adj.setdefault(e['from'], []).append((e['rel'], e['to'], N[e['to']]['kind']))
        adj.setdefault(e['to'], []).append((e['rel'], e['from'], N[e['from']]['kind']))
    members = {m['id']: m for m in TEAM['members']}
    out, tiles = [], []
    for rule in GRC_GAPS['rules']:
        if rule.get('close') not in members:
            sys.exit(f'data/grc-gaps.json: rule {rule["id"]} names {rule.get("close")!r}, who is not on the team')
        who = f'<a href="../../team/{E(rule["close"])}/index.html">{E(members[rule["close"]]["name"])}</a>'
        if rule['of'] == 'edge':
            hit = [e for e in edges if e['basis']['kind'] == rule['basis']]
            total = len(edges)
            by = Counter(e['rel'] for e in hit)
            detail = table(['Verb', 'Edges', 'Example'], [[f'<code>{E(v)}</code>', str(n), E(next(f'{N[e["from"]]["label"][:50]} {v} {N[e["to"]]["label"][:50]}' for e in hit if e['rel'] == v))] for v, n in by.most_common()])
        else:
            kinds = rule['reach'] if isinstance(rule['reach'], list) else [rule['reach']]
            pool = [n for n in nodes if n['kind'] == rule['of']]
            if not pool:
                sys.exit(f'data/grc-gaps.json: rule {rule["id"]} looks at {rule["of"]!r}, a kind the graph does not have')
            hit = [n for n in pool if grc_reach(adj, n['id'], set(kinds), set(rule.get('verbs') or []), rule['within']) is None]
            total = len(pool)
            items = ''.join(f'<li><a href="../explore/index.html#focus={E(n["id"])}">{E(n["label"])}</a></li>' for n in sorted(hit, key=lambda n: n['label']))
            detail = f'<details{" open" if len(hit) <= 12 else ""}><summary>The {len(hit)}, each opening in the explorer</summary><ul class="cols-list">{items}</ul></details>' if hit else '<p class="small">None: every one reaches it.</p>'
        reach = '' if rule['of'] == 'edge' else f' Looks at every <b>{E(rule["of"])}</b> for a path to {E(" or ".join(kinds))} within {rule["within"]} step{"s" if rule["within"] > 1 else ""}' + (f' through {E(", ".join(rule["verbs"]))}' if rule.get('verbs') else '') + '.'
        tiles.append(stat(len(hit), f'{E(rule["title"].lower())} (of {total})', f'#{rule["id"]}', 2))
        out.append(f'<section class="vcard" id="{E(rule["id"])}"><h2>{E(rule["title"])}: {len(hit)} of {total}</h2><p>{E(rule["why"])}{reach} Who could close it: {who}.</p>{detail}</section>')
    body = f"""
{nav.format(u="../../")}
<h1>What the risk graph is missing</h1>
<p class="lead">The graph shows what is joined; this page shows what is not. Each gap below is a rule, written as data in <a href="../../data/grc-gaps.json">data/grc-gaps.json</a>, computed over the {len(nodes)} nodes and {len(edges)} edges at every release: a control no test reaches, code nobody owns, a risk no story tells, a join an agent inferred that nobody has checked. Each names who could close it; each item opens in <a href="../explore/index.html">the explorer</a>.</p>
<div class="stats">{''.join(tiles)}</div>
{''.join(out)}
<p class="small">A rule is a kind of node, what it should reach, within how many steps and through which verbs. Add one to the data and it appears here at the next release. A gap is not a fault: some are there by design (a control in a framework the fix commit was never meant to test); the page says where to look, not what to conclude.</p>
"""
    page('grc/gaps/index.html', 'What the risk graph is missing: controls without tests, code without owners, risks without stories', 'Gaps in the php2shell risk graph, computed at every release from rules written as data: controls no test reaches, code with no owner, risks with no story or treatment, edges an agent inferred and nobody checked; each with its count, its list and who could close it.', body, kind='analysis', topics='php2shell grc graph gaps')

def grc_s_rids(G, sid):
    below = set(grc_below(G['kids_s'], sid))
    return [r['id'] for r in G['R'].values() if any(a['to'] in below for a in r['assign'])]

def build_grc_network(G, nav):
    """What the rest of the sgit network already holds on risk and on these standards, and which of it bears on which risk."""
    if not GRC_NETWORK:
        return
    N = GRC_NETWORK
    for it in N['items']:
        bad = [x for x in it.get('risks', []) if x not in G['R']] + [x for x in it.get('frameworks', []) if x not in G['FW']]
        if bad:
            sys.exit(f'grc-network: {it["id"]} names unknown risks or frameworks {bad}')
    groups = ''
    for g in N['groups']:
        rows = [[f'<a href="{U(it["url"])}"><b>{E(it["title"])}</b></a>' + (f'<div class="note">vault <code>{E(it["vault"])}</code></div>' if it.get('vault') else ''), E(it.get('date', '')), E(it['what']),
                 ', '.join(grc_r_link(G, x, 2, pill=False) for x in it.get('risks', [])) or '<i>the model</i>', ', '.join(f'<a href="../frameworks/{E(f)}/index.html">{E(G["FW"][f]["name"])}</a>' for f in it.get('frameworks', []))]
                for it in N['items'] if it['group'] == g['id']]
        groups += section('n-' + g['id'], E(g['name']), table(['Material', 'Date', 'What it holds, as its publisher describes it', 'Bears on', 'Frameworks'], rows), E(g['about']))
    gaps = ''.join(f'<li>{E(x)}</li>' for x in N.get('gaps', []))
    body = f'''
{nav.format(u="../../")}
<h1>From the network: what the sgit sites already hold on risk</h1>
<p class="lead">{E(N["about"])}</p>
{groups}
{section("gaps", "What the network does not have yet", "<ul>" + gaps + "</ul>") if gaps else ""}
<p class="small">Third-party and sibling material, described in its publisher's own terms and linked, not reproduced. Vaults are named by id; each opens from its publisher's page with the read key published there. Surveyed {E(N["surveyed"])}.</p>
'''
    page('grc/network/index.html', 'From the network: sgit risk models, vaults and standards graphs mapped to php2shell', 'The risk models, fractal registers, semantic graphs and standards vaults across the sgit network, and which php2shell risks and frameworks each bears on.', body, kind='analysis', topics='php2shell grc network', origin='external')

# ----------------------------------------------------------------------------- joining: a key, and feedback from any page (conductor@php.newsroom)
# The editor's memo of 22 October 2026: feedback from any page, signed, after an onboarding as simple as a QR code. The
# brief: admin/content/briefs/2026-10-22__brief__feedback-keys-and-review.md. The page is a shell; assets/feedback/join.js
# makes the key and sends the enrolment; data/contributors.json lists the invitations (hashes) and the enrolled keys.

def build_join():
    C = load('contributors')
    roles = dict(C['roles'])
    keys = table(['Handle', 'Role', 'Signing key', 'Device', 'Enrolled'], [[E(k['handle']), E(k['role']), f'<code>{E(k["signing_fingerprint"])}</code>', E(k['device']), E(k['enrolled'])] for k in C['keys']]) if C['keys'] else '<p class="small">None yet.</p>'
    body = f'''
<p class="crumb"><a href="../collaborators/index.html">Power users</a> / Join</p>
<h1>Join: a key for this device, in one tap</h1>
<p class="lead">To give feedback on this site you sign it with a key of your own, so the team knows who it came from. Getting one is one tap: open the invitation the editor sent you (a link or a QR code), and this page makes a key on this device and sends it to him.</p>
<noscript><p class="sub-err">This page needs JavaScript: the key is made in your browser.</p></noscript>
<div id="join-app" class="subform"><p class="small">Loading…</p></div>
{section("how", "How it works", '''<ol>
<li><b>An invitation.</b> Ask Dinis, by email or on WhatsApp, or with <a href="../collaborators/index.html#join">the join form</a>. He makes it on his phone (<a href="invite/index.html">Invite</a>) and sends you a link or a QR code meant for you alone.</li>
<li><b>One tap.</b> The link opens this page, which makes a key pair in your browser: one half signs, the other half is public. The signing half stays in this browser and cannot be copied out of it, by this site or anyone else.</li>
<li><b>Enrolled.</b> Your public key goes to the team, encrypted, with the invitation. When the invitation's signature checks out, your key is added to the list below; from then on what you sign shows as yours.</li>
<li><b>Feedback from any page.</b> Press <b>Feedback</b>, next to Ask at the top of every page: say what is wrong, unclear, missing or good, with a screenshot if you like, and send. It is signed with your key and encrypted to the team.</li>
</ol>''')}
{section("keys", "Enrolled keys", keys, "Handles and fingerprints only, never a name. " + "; ".join(f"{E(r)}: {E(t)}" for r, t in C["roles"]) + ".")}
{section("limits", "What it does not do", '''<ul>
<li>A key belongs to one browser on one device. Another device needs its own invitation; clearing this site's data deletes the key.</li>
<li>An invitation is a credential until it is used: whoever opens it first can join with it. Each one enrols at most three devices and expires in two weeks.</li>
<li>A signature proves which key wrote a message, not who holds the key: that is what the editor's enrolment adds.</li>
</ul><p class="small">Keys are in pki.sgit.ai's and sgit's format, so <code>sgit pki verify</code> checks every signature. The brief is on <a href="../admin/briefs/index.html#2026-10-22__brief__feedback-keys-and-review">briefs</a>.</p>''')}
<script type="module" src="../assets/feedback/join.js"></script>
'''
    body2 = f'''
<p class="crumb"><a href="../../collaborators/index.html">Power users</a> / <a href="../index.html">Join</a> / Invite</p>
<h1>Invite someone: a link and a QR code, signed on this device</h1>
<p class="lead">For a key that may invite ({E(", ".join(C["rules"]["may_invite"]))}). Give the person a handle (never their name), pick a role and how long the invitation lasts, and this page signs it with this device's key and shows a QR code, a link and a share button. Nothing is stored anywhere: when they join, the invitation is checked against your key, and their key is enrolled.</p>
<noscript><p class="sub-err">This page needs JavaScript: the invitation is signed in your browser.</p></noscript>
<div id="invite-app"><p class="small">Loading\u2026</p></div>
<p class="small">An invitation enrols at most {C["rules"]["devices_per_invitation"]} devices and is a credential until it is used: send it to one person, in a private message.</p>
<script type="module" src="../../assets/feedback/invite.js"></script>
'''
    page('join/invite/index.html', 'Invite someone: a link and a QR code, signed on this device', 'For the editor: make an invitation to give signed feedback on this site, as a QR code, a link and a share button, signed in the browser with an enrolled key.', body2, kind='account')
    page('join/index.html', 'Join: a key for this device, in one tap', 'Open the invitation the editor sent you and this page makes a key on your device, so the feedback you send from any page is signed as yours; the enrolled keys, as handles and fingerprints.', body, kind='account')

# ----------------------------------------------------------------------------- where every agent is (conductor@php.newsroom)
# The editor's memo of 23 October 2026 (admin/content/briefs/2026-10-23__brief__day-two-situation-awareness.md): the
# status of every agent, the vaults and the desk. data/agents-status.json is the conductor's snapshot, read from the
# sessions, the branches and the schedules without asking any agent; this page draws it.

def build_status_page():
    S = load('agents-status')
    members = {m['id']: m for m in TEAM['members']}
    STATE = {'working': 'confirmed', 'blocked': 'contradicted', 'review ready': 'disputed', 'completed': 'reported'}
    def who(a):
        m = members.get(a['member'])
        return f'<a href="../{E(a["member"])}/index.html">{E(a["agent"])}</a>' if m else E(a['agent'])
    order = {'blocked': 0, 'review ready': 1, 'working': 2, 'completed': 3}
    ag = sorted(S['agents'], key=lambda a: (order.get(a['state'], 9), a['last']))
    rows = [[who(a), f'<span class="st st-{STATE.get(a["state"], "other")}">{E(a["state"])}</span>', E(a['last'].replace('T', ' ')), E(a['did']),
             E(a['waiting']) + (f'<div class="note">on: {E(a["on"])}</div>' if a['on'] else ''), ('$' + format(a['cost'], '.2f')) if a['cost'] is not None else '']
            for a in ag]
    st = Counter(a['state'] for a in S['agents'])
    on_ed = sum(1 for a in S['agents'] if 'editor' in a['on'])
    total = sum(a['cost'] for a in S['agents'] if a['cost'] is not None)
    stats = ''.join(stat(n, l) for n, l in [(len(S['agents']), 'agents'), (st.get('working', 0), 'working'), (st.get('blocked', 0), 'blocked'), (on_ed, 'waiting on the editor'),
                                            (len(S['branches']), 'branches waiting for dev'), ('$' + str(round(total)), 'spent, sessions so far')])
    body = f'''
<p class="crumb"><a href="../index.html">The team</a> / Status</p>
<h1>Status: where every agent is</h1>
<p class="lead" data-live="status-about">{E(S["about"])}</p>
<p class="kv" data-live="status-asof"><b>As of</b> {E(S["as_of"].replace("T", " "))} UTC &middot; <b>live site</b> v{E(S["live_version"])}</p>
<div class="stats" data-live="status-stats">{stats}</div>
{section("decisions", "What needs a decision first", '<div data-live="status-decisions"><ol>' + "".join(f"<li>{E(x)}</li>" for x in S["decisions"]) + "</ol></div>")}
{section("agents", "Every agent", '<div data-live="status-agents">' + table(["Agent", "State", "Last activity (UTC)", "Last did", "Waiting for", "Cost"], rows, "board") + '</div>', "Blocked first, then ready for review, then working, then done.")}
{section("branches", "Branches waiting to be carried into dev", '<div data-live="status-branches">' + table(["Branch", "By", "Commits ahead", "What"], [[f"<code>{E(b)}</code>", E(w), str(n), E(t)] for b, w, n, t in S["branches"]], "board") + '</div>', "Agents push to their own branches; dev@php.newsroom carries them into dev and releases. Until then, none of this is on the site.")}
{section("schedules", "What ran on its own", '<div data-live="status-schedules">' + table(["Schedule", "State"], [[E(a), E(b)] for a, b in S["schedules"]]) + '</div>', 'The register of schedules and every recorded run is on <a href="../runs/index.html">runs</a>.')}
{section("freshness", "How fresh this site\'s data is", '<div data-live="status-freshness">' + table(["Data", "As of", "Note"], [[E(a), E(b), E(c)] for a, b, c in S["freshness"]]) + '</div>', "The vaults move ahead of the site; a fact reaches the site only when its vault is exported and the site released.")}
<script src="../../assets/live/live.js" defer></script>
<script src="../../assets/live/status.js" defer></script>
'''
    page('team/status/index.html', 'Status: where every agent is', 'Every agent on the team: what it last did, what it waits for and from whom, the branches waiting for dev, what ran on a schedule and how fresh the data is; a snapshot by the conductor.', body, kind='site', topics='team agents')

# ----------------------------------------------------------------------------- the vaults each agent made (conductor@php.newsroom)
# The editor, 23 October 2026: a page that lists every agent and the vaults it created, by ID only; the ID is public, the
# key never is. Each agent keeps its own file, data/vault-register/<agent>.json, and adds a row in the same commit as the
# vault (AGENTS.md, section 7). The build refuses anything in an id field that is not a bare vault id.

def build_vault_register():
    d = os.path.join(DATA, 'vault-register')
    regs = [json.load(open(os.path.join(d, f), encoding='utf-8')) for f in sorted(os.listdir(d)) if f.endswith('.json')]
    members = {m['id']: m for m in TEAM['members']}
    KINDS = ('vault key', 'read key', 'append token')
    for r in regs:
        for v in r['vaults'] + r.get('holds', []):
            if not re.fullmatch(r'[0-9a-z]{8}', v['id']): sys.exit(f'data/vault-register: {r["agent"]}: {v["id"][:12]}... is not a vault id; a key never goes here')
        for h in r.get('holds', []):
            if h['key'] not in KINDS: sys.exit(f'data/vault-register: {r["agent"]}: "key" names what kind of key is held ({", ".join(KINDS)}), never the key itself')
    sealed = lambda s: s[:10] if re.match(r'\d{4}-\d{2}-\d{2}$', s) else s
    secs = ''
    for r in sorted(regs, key=lambda r: (r['agent'] != 'conductor@php.newsroom', r['agent'])):
        m = members.get(r['member'])
        name = f'<a href="../{E(r["member"])}/index.html">{E(r["agent"])}</a>' if m else E(r['agent'])
        rows = [[f'<code>{E(v["id"])}</code>', E(v['what']), E(v['created']), E(sealed(v['key_sealed_to_root']))] for v in r['vaults']]
        held = r.get('holds', [])
        hrows = [[f'<code>{E(h["id"])}</code>', E(h['key']), E(h['from']), E(h['since'])] for h in held]
        htab = (f'<h4>Keys it holds</h4>{table(["Vault ID", "Kind of key", "From", "Since"], hrows)}' if held
                else '<p class="small"><b>Keys it holds:</b> not recorded yet.</p>')
        secs += f'<section class="vcard"><h3>{name} <span class="small">{len(r["vaults"])} vault{"s" if len(r["vaults"]) != 1 else ""} made</span></h3>{table(["Vault ID", "What it holds", "Created", "Key sealed to the root"], rows)}{htab}<p class="small">{E(r["note"])}</p></section>'
    n = sum(len(r['vaults']) for r in regs)
    unsealed = sum(1 for r in regs for v in r['vaults'] if not re.match(r'\d{4}-\d{2}-\d{2}|sealed', v['key_sealed_to_root']))
    body = f'''
<p class="crumb"><a href="../index.html">The team</a> / Vaults</p>
<h1>Vaults: who made each one, and who holds which keys</h1>
<p class="lead">Every vault the agents on this team have made, listed by the agent that made it, and the keys each agent holds. A vault ID is public: it names the vault and opens nothing. A vault key is never published, here or anywhere; it is sealed to the editor's key on pki.sgit.ai before the agent's session ends, so it is never lost with the session. {n} vaults; for {unsealed} of them, the sealing is not recorded yet.</p>
<div data-live="vault-register">{secs}</div>
<script src="../../assets/live/live.js" defer></script>
<script src="../../assets/live/vaults.js" defer></script>
{section("rules", "The rules", '''<ul>
<li><b>Record the keys you hold</b>, not only the vaults you made: every vault key, read key or append token you were given, by vault ID, the kind of key and who gave it (the <code>holds</code> list in your file). It is what lets the editor start a new session for you with the right keys. Never the key itself.</li>
<li><b>The vault key is the whole boundary.</b> Whoever holds a vault's key can do everything with it, including draining its lane: the lane's enum key and the key pair's passphrase are derived from the vault key, and the key pair lives inside the vault, encrypted (sgit.ai, the vault key is the only secret). No secret a vault needs lives only in a session.</li>
<li><b>Make a vault, add a row.</b> In the same commit, in your own file: <code>data/vault-register/&lt;you&gt;.json</code>, with the ID, what it holds, the date, and when its key was sealed to the root. The build refuses anything that is not a bare vault ID.</li>
<li><b>Seal every key to the root</b> (<code>sha256:db7f79fdd87e030a</code>) with pki.sgit.ai's agent tool before your session ends, and record the date.</li>
<li><b>Asked for a key, or a QR code of it?</b> Seal it and send the sealed link and its QR code; never the key itself, in a page, a file, a commit, a chat or a message. The steps are in <code>AGENTS.md</code>, section 7, and on <a href="../../admin/agents/index.html">guidance for agents</a>.</li>
</ul>''')}
<p class="small">What each vault is for, and the published read keys and write-only lanes, are on <a href="../../vaults/index.html">the vaults behind this site</a>.</p>
'''
    page('team/vaults/index.html', 'Vaults: who made each one', 'Every vault the team\'s agents have made, listed by agent, by ID only, with whether its key is sealed to the editor; the rules for making a vault and handing over its key.', body, kind='site', topics='team agents')


# ----------------------------------------------------------------------------- the Sherpa: readers' feedback and friction (sherpa@php.newsroom)
# The Sherpa walks with the reader and proposes; it fixes nothing on other members' pages. Its data is its own:
# admin/sherpa/feedback.json (one record per reader message, UF-nnn) and admin/sherpa/friction-log.json. The role is
# admin/sherpa/README.md. Readers are never named; their words are shown as theirs, as received, and only as text.

SHERPA_DIR = os.path.join(ROOT, 'admin', 'sherpa')
SHERPA_SEEN = {'yes': ('st-confirmed', 'reproduced'), 'partly': ('st-disputed', 'partly'), 'no': ('st-contradicted', 'not reproduced'), 'n/a': (None, 'nothing to reproduce')}
SHERPA_SEVERITY = {'high': 'st-contradicted', 'medium': 'st-disputed', 'low': 'st-unverified'}

def sherpa_load(name):
    with open(os.path.join(SHERPA_DIR, name + '.json'), encoding='utf-8') as f:
        return json.load(f)

def sherpa_who(mid, depth):
    m = {x['id']: x for x in TEAM['members']}.get(mid)
    return f'<a href="{"../" * depth}team/{E(mid)}/index.html">{E(m["name"])}</a>' if m else E(mid)

def sherpa_pill(cls, label):
    return f'<span class="st {cls}">{E(label)}</span>' if cls else f'<span class="small">{E(label)}</span>'

def sherpa_shot(up, src, cap):
    return f'<figure class="shot"><img src="{up}{U(src)}" alt="{E(cap)}" loading="lazy" style="max-width:100%;height:auto"><figcaption>{E(cap)}</figcaption></figure>'

def sherpa_doc(r):
    """The document a feedback record was received as, in blocks the comments anchor to. A record imported in full has
    admin/sherpa/documents/<id>.json; otherwise its points' own words are the document, one block each."""
    if r.get('document'):
        return sherpa_load('documents/' + r['document'])['blocks']
    return [{'id': f'p{p["n"]}', 't': 'q', 'text': p['words'], 'kind': p['kind']} for p in r['points']]

def sherpa_blocks_of(r, p):
    return p.get('blocks') or [f'p{p["n"]}']

def sherpa_block_html(r, b, up):
    t = b['t']
    if t in ('h2', 'h3'):
        return f'<h3 class="fv-h">{E(b["text"])}</h3>'
    if t == 'li':
        return f'<p class="fv-li">{E(b["text"])}</p>'
    if t == 'img':
        alt = f'Screenshot from the report: {b["src"].rsplit(".", 1)[0].split("-", 1)[-1].replace("-", " ")}'
        return f'<figure class="shot"><img src="{up}assets/sherpa/{E(r["id"].lower())}/{U(b["src"])}" alt="{E(alt)}" loading="lazy"></figure>'
    if t == 'row':
        return '<div class="fv-cells">' + ''.join(f'<span>{E(c)}</span>' for c in b['cells']) + '</div>'
    if t == 'q':
        return f'<p><span class="small">{E(b.get("kind", ""))}</span><br><q>{E(b["text"])}</q></p>'
    return f'<p>{E(b["text"])}</p>'

def sherpa_card(r, p, d):
    if p.get('held'):
        return f'<div class="fv-card" id="c{p["n"]}"><b>{E(r["id"])}.{p["n"]}: held</b><p>{E(p["comment"])}</p></div>'
    also = (', with ' + ', '.join(sherpa_who(x, d) for x in p['also'])) if p.get('also') else ''
    sev = sherpa_pill(SHERPA_SEVERITY[p['severity']], p['severity']) if p.get('severity') else ''
    return f'''<div class="fv-card" id="c{p["n"]}"><b>{E(r["id"])}.{p["n"]} · {E(p["kind"])}</b> {sherpa_pill(*SHERPA_SEEN.get(p["replicated"], (None, str(p["replicated"]))))} {sev}
<p>{E(p["comment"])}</p>{f'<p class="small"><b>Evidence.</b> {E(p["evidence"])}</p>' if p.get("evidence") else ""}
<p><b>Recommend.</b> {E(p["recommendation"])}</p>
<p class="small">Who can act: {sherpa_who(p["owner"], d)}{also}{(" · friction " + E(p["friction"])) if p.get("friction") else ""}</p></div>'''

def sherpa_nav(FB, CI, cur, up):
    def item(href, label, sub, on):
        return f'<a href="{href}"{" aria-current=page" if on else ""}><b>{E(label)}</b><span>{E(sub)}</span></a>'
    groups = [("From readers and power users", [r for r in FB if not r.get('tester')]), ("Tests by agents", [r for r in FB if r.get('tester') == 'agent']), ("From the editor", [r for r in FB if r.get('tester') == 'editor']), ("Internal tests", [r for r in FB if r.get('tester') == 'internal'])]
    out = item(f'{up}feedback/index.html', 'All feedback', 'the section, with its numbers', cur == 'home')
    for name, rs in groups:
        out += f'<p class="fv-g">{E(name)}</p>' + ''.join(item(f'{up}feedback/{E(r["id"].lower())}/index.html', r['id'], (r.get('who') or r['reader'].split(',')[0])[:60], cur == r['id']) for r in rs)
    out += '<p class="fv-g">Ideas from collaborators</p>' + ''.join(item(f'{up}sherpa/ideas/{E(c["id"].lower())}/index.html', c['id'], c['name_on_site'] or c['handle'], False) for c in CI)
    out += '<p class="fv-g">What happens next</p>' + item(f'{up}feedback/briefs/index.html', 'The briefs', 'to the conductor, and to other teams', cur == 'briefs')
    return f'<nav class="fv-nav" aria-label="Feedback">{out}</nav>'

def sherpa_brief_of(r, d):
    by = {}
    for p in r['points']:
        if p['kind'] == 'praise' or p.get('held'):
            continue
        by.setdefault(p['owner'], []).append(p)
    if not by:
        return '<p>Nothing to brief: praise only.</p>'
    out = ''
    for own, ps in by.items():
        out += f'<h3>For {sherpa_who(own, d)}</h3><ol>' + ''.join(f'<li>{E(p["recommendation"])} <span class="small">({E(r["id"])}.{p["n"]}{(", " + E(p["friction"])) if p.get("friction") else ""})</span></li>' for p in ps) + '</ol>'
    return '<p>Everything goes to the conductor, who hands each part to the member named. What this record asks of each member:</p>' + out

def sherpa_viewer(r, FB, CI, d):
    up = '../' * d
    blocks = sherpa_doc(r)
    first, at = {}, {}
    for p in r['points']:
        bs = sherpa_blocks_of(r, p)
        first.setdefault(bs[0], []).append(p)
        for b in bs[1:]:
            at.setdefault(b, []).append(p)
    rows = ''
    for b in blocks:
        cards = ''.join(sherpa_card(r, p, d) for p in first.get(b['id'], []))
        refs = ''.join(f'<a class="fv-ref" href="#c{p["n"]}">{E(r["id"])}.{p["n"]}</a>' for p in at.get(b['id'], []))
        rows += f'<div class="fv-row" id="{E(b["id"])}"><div class="fv-b" data-b="{E(b["id"])}">{sherpa_block_html(r, b, up)}</div><aside class="fv-c">{cards}{refs}</aside></div>'
    kinds = Counter(p['kind'] for p in r['points'])
    chips = ''.join(f'<a class="fv-chip fv-k-{E(p["kind"])}" href="#c{p["n"]}" title="{E(p["kind"])}">{p["n"]}</a>' for p in r['points'])
    return f'''<div class="fv-map"><span class="small">Points, in order ({", ".join(f"{n} {E(k)}" for k, n in kinds.most_common())}):</span> {chips}</div>
<div class="fv-doc" data-doc="{E(r["id"])}"><div class="fv-row fv-head"><div>The document, as received</div><div>The Sherpa's comments</div></div>{rows}</div>'''

def build_sherpa_feedback(r, FB, CI):
    d = 2; up = '../' * d
    pages_read = ', '.join(f'<a href="{up}{U(pth)}">{E(pth)}</a>{(" (" + E(how) + ")") if how else ""}' for pth, how in r['pages_read'])
    who = {"agent": "A test by an agent, not a person: its findings are prompts to re-check, not evidence about readers.", "internal": "An internal test, not reader feedback, and not counted as such.", "editor": "The editor's own feedback, through the site's form."}.get(r.get("tester"), "Readers are never named here.")
    facts = ''.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in [('From', f'{E(r["reader"])}. {who}'), ('How it came', E(r['channel']) + ((', about ask ' + E(r['ask'])) if r.get('ask') else '')),
        ('Received', E(r['received'])), ('Site version', f'v{E(r["site_version"])}. {E(r["site_version_note"])}'), ('Progress', E(r['progress'])), ('Pages read', pages_read)])
    nr = ''.join(f'<li>{E(x)}</li>' for x in r.get('not_reproduced', []))
    title = f'{r["id"]}: feedback of {r["received"]}, on v{r["site_version"]}'
    body = f'''
<link rel="stylesheet" href="{up}assets/sherpa/viewer.css">
<p class="crumb"><a href="../index.html">Feedback from collaborators</a> / {E(r["id"])}</p>
<div class="fv">{sherpa_nav(FB, CI, r["id"], up)}<div class="fv-main">
<h1>{E(title)}</h1>
<p class="lead">{E(r["summary"])}</p>
<dl class="fv-facts">{facts}</dl>
{section("doc", "The document and the Sherpa's comments, side by side", sherpa_viewer(r, FB, CI, d), "Select any text in the document to highlight it and add a note of your own; your notes stay in this browser, and you can export them.")}
{section("mine", "Your notes", '<div id="fv-notes"><p class="small">None yet. Select text in the document to add one. This needs JavaScript; notes are kept in this browser only.</p></div>')}
{section("brief", "The brief", sherpa_brief_of(r, d))}
{section("open", "Not reproduced, and the reply", f"<ul>{nr}</ul><p>{E(r.get('reply', ''))}</p>")}
</div></div>
<script type="module" src="{up}assets/sherpa/viewer.js"></script>
'''
    page(f'feedback/{r["id"].lower()}/index.html', title, r['summary'], body, kind='site', topics='readers feedback collaborators')
def build_feedback_section(FB, CI, FL):
    d = 1; up = '../'
    ST = sherpa_load('collab-stats')
    opn = [f for f in FL['frictions'] if f['status'] != 'closed']
    pts = [p for r in FB if r.get('tester') != 'internal' for p in r['points']]
    stats = ''.join(stat(n, l) for n, l in [(sum(r.get('tester') != 'internal' for r in FB), 'pieces of feedback'), (len(pts), 'points answered'), (sum(p['replicated'] == 'yes' for p in pts), 'reproduced by the Sherpa'),
        (len(opn), 'frictions open'), (ST['power_users_joined'], 'power users joined'), (ST['signed_messages'], 'signed messages received'), (len(CI), 'conversations of ideas')])
    rows = [[f'<a href="{E(r["id"].lower())}/index.html">{E(r["id"])}</a>', E(r['received']), 'v' + E(r['site_version']), E(r.get('who') or r['reader'][:70]), {'agent': 'agent test', 'internal': 'internal test', 'editor': 'the editor'}.get(r.get('tester'), 'person'),
             str(len(r['points'])), E(r['summary'])] for r in FB]
    body = f'''
<link rel="stylesheet" href="{up}assets/sherpa/viewer.css">
<p class="crumb"><a href="../collaborators/index.html">Power users</a> / Feedback from collaborators</p>
<div class="fv">{sherpa_nav(FB, CI, "home", up)}<div class="fv-main">
<h1>Feedback from collaborators</h1>
<p class="lead">Everything the power users and collaborators have told us about this site, each piece kept whole, with the Sherpa's comment beside every part of it, what was reproduced, and the brief it turned into. Kept by <a href="../sherpa/index.html">the Sherpa</a>. People are not named; tests run by agents are marked as tests.</p>
<p>Have something to add? <a href="../sherpa/for-your-claude/index.html">Talk it through with your own assistant</a>, by text or by voice, and send us the file it writes.</p>
<div class="stats">{stats}</div>
<p class="small">{E(ST["note"])}</p>
{section("all", "Every piece of feedback", table(["Id", "Received", "Version", "From", "Kind", "Points", "In short"], rows, "board"))}
{section("next", "What happens next", '<p>Each piece of feedback becomes frictions in <a href="../sherpa/index.html#friction">the friction log</a> and a line in <a href="briefs/index.html">the brief to the conductor</a>, who hands it to the member who owns the page. When a fix ships, the Sherpa checks it on the live site and closes the friction.</p>')}
</div></div>
'''
    page('feedback/index.html', 'Feedback from collaborators', 'Every piece of feedback from power users and collaborators, kept whole and answered point by point beside it, with the numbers and the briefs it turned into.', body, kind='site', topics='readers feedback collaborators')
    by = {}
    for f in opn:
        by.setdefault(f['owner'], []).append(f)
    order = sorted(by, key=lambda o: (-sum(f['severity'] == 'high' for f in by[o]), o))
    inner = ''
    for own in order:
        fs = sorted(by[own], key=lambda f: ({'high': 0, 'medium': 1, 'low': 2}[f['severity']], f['id']))
        inner += f'<h3>For {sherpa_who(own, 2)}</h3><ol>' + ''.join(f'<li>{sherpa_pill(SHERPA_SEVERITY[f["severity"]], f["severity"])} <b>{E(f["page"])}:</b> {E(f.get("proposal") or f.get("expected", ""))} <span class="small">({E(f["id"])}; seen v{E(f["first_seen"])} to v{E(f["last_seen"])}; {E(f.get("source", "the Sherpa"))})</span></li>' for f in fs) + '</ol>'
    BR = sherpa_load('briefs')
    ext = ''
    for t in BR['teams']:
        ext += f'<h3>For <a href="{U(t["url"])}">{E(t["name"])}</a></h3><ol>' + ''.join(f'<li>{sherpa_pill(SHERPA_SEVERITY[i["severity"]], i["severity"])} <b>{E(i["title"])}.</b> {E(i["what"])} <i>Evidence:</i> {E(i["evidence"])} <i>Proposal:</i> {E(i["proposal"])}</li>' for i in t['items']) + '</ol>'
    body = f'''
<link rel="stylesheet" href="{up}../assets/sherpa/viewer.css">
<p class="crumb"><a href="../index.html">Feedback from collaborators</a> / The briefs</p>
<div class="fv">{sherpa_nav(FB, CI, "briefs", "../../")}<div class="fv-main">
<h1>The briefs: what the feedback asks of each team</h1>
<p class="lead">One brief to the conductor, built from every open friction, grouped by the member who owns the page and ordered by severity; the conductor hands each part on. Then the requirements for teams outside this newsroom. Every line names where it came from.</p>
{section("conductor", "To the conductor", inner)}
{section("other", "To other teams", ext)}
</div></div>
'''
    page('feedback/briefs/index.html', 'The briefs: what the feedback asks of each team', 'The brief to the conductor from every open friction, by owner and severity, and the requirements for teams outside the newsroom (pki.sgit.ai).', body, kind='site', topics='readers feedback briefs')

SHERPA_KIND = {'comment': 'Comments', 'idea': 'Ideas', 'question': 'Questions', 'offer': 'The offer'}

def sherpa_idea(c, it, d):
    up = '../' * d
    links = ' · '.join(f'<a href="{up}{U(p)}">{E(t)}</a>' for p, t in it['links'])
    also = (', with ' + ', '.join(sherpa_who(x, d) for x in it['also'])) if it.get('also') else ''
    return f'''<article class="fbpoint" id="i{it["n"]}">
<h3>{E(c["id"])}.{it["n"]}: {E(it["kind"])}, {E(", ".join(it["tags"]))}</h3>
<blockquote><p><q>{E(it["words"])}</q></p><footer>In the collaborator's words, as received</footer></blockquote>
<p><b>Where the site stands today.</b> {E(it["today"])}</p>
<p class="small">See: {links}</p>
<p><b>What is missing.</b> {E(it["gap"])}</p>
<p><b>The Sherpa recommends.</b> {E(it["recommendation"])}</p>
<p class="small">Who could take it: {sherpa_who(it["owner"], d)}{also}.</p>
</article>'''

def build_sherpa_ideas(c):
    d = 3; up = '../' * d
    who = c['name_on_site'] or c['handle']
    title = f'{c["id"]}: comments, questions and ideas from {who}'
    ex = table(['When', 'Who', 'What was said'], [[E(w), E(x), E(t)] for w, x, t in c['exchange']], 'board')
    idx = table(['#', 'Kind', 'About', 'Who could take it'], [[f'<a href="#i{it["n"]}">{it["n"]}</a>', E(it['kind']), E(', '.join(it['tags'])), sherpa_who(it['owner'], d)] for it in c['items']], 'board')
    groups = ''
    for k, label in SHERPA_KIND.items():
        its = [it for it in c['items'] if it['kind'] == k]
        if its:
            groups += section(f'k-{k}', label, ''.join(sherpa_idea(c, it, d) for it in its))
    stats = ''.join(stat(sum(it['kind'] == k for it in c['items']), SHERPA_KIND[k].lower()) for k in SHERPA_KIND)
    body = f'''
<p class="crumb"><a href="../../index.html">The Sherpa</a> / <a href="../../index.html#ideas">Ideas from collaborators</a> / {E(c["id"])}</p>
<h1>{E(title)}</h1>
<p class="lead">{E(c["summary"])}</p>
<div class="stats">{stats}</div>
{section("record", "The record", f"""<ul>
<li><b>From:</b> {E(who)}. {E(c["name_note"]) if not c["name_on_site"] else ""}</li>
<li><b>How it came:</b> {E(c["channel"])}, {E(c["from"])} to {E(c["to"])}.</li>
<li><b>Checked against:</b> site v{E(c["site_version"])}.</li>{f'<li><b>The brief:</b> <a href="{up}{U(c["brief"][0])}">{E(c["brief"][1])}</a>.</li>' if c.get("brief") else ""}
</ul>""")}
{section("exchange", "The conversation, in short", ex, "Summarised; the collaborator's own words are quoted under each item below.")}
{section("index", "At a glance", idx, "Each item: the collaborator's words, where the site stands today with links, what is missing, what the Sherpa recommends, and who could take it. Answers to the questions are the editor's; the Sherpa only says what exists.")}
{groups}
{section("reply", "The reply", f"<p>{E(c['reply'])}</p>")}
'''
    page(f'sherpa/ideas/{c["id"].lower()}/index.html', title, c['summary'], body, kind='site', topics='collaborators ideas graph')

def build_sherpa():
    FB, FL = sherpa_load('feedback')['feedback'], sherpa_load('friction-log')
    CI = sherpa_load('ideas')['conversations']
    for r in FB:
        build_sherpa_feedback(r, FB, CI)
    for c in CI:
        build_sherpa_ideas(c)
    build_feedback_section(FB, CI, FL)
    build_sherpa_claude()
    me = [m for m in TEAM['members'] if m['id'] == 'sherpa'][0]
    fbrows = [[f'<a href="../feedback/{E(r["id"].lower())}/index.html">{E(r["id"])}</a>', E(r['received']), 'v' + E(r['site_version']), E(r['reader']), E(r['progress']),
               str(len(r['points'])), str(sum(p['replicated'] == 'yes' for p in r['points'])), E(r['summary'])] for r in FB]
    frows = [[E(f['id']), E(f['page']), E(f['stage']), sherpa_pill(SHERPA_SEVERITY[f['severity']], f['severity']), sherpa_who(f['owner'], 1), E(f['status']),
              f'v{E(f["first_seen"])} to v{E(f["last_seen"])}', E(f.get('proposal', f.get('expected', '')))] for f in FL['frictions']]
    opn = [f for f in FL['frictions'] if f['status'] != 'closed']
    stats = ''.join(stat(n, l) for n, l in [(len(FB), 'reader messages'), (sum(len(r['points']) for r in FB), 'points answered'), (len(opn), 'frictions open'), (sum(f['severity'] == 'high' for f in opn), 'of them high')])
    help_ = '''<ul>
<li><b>Not sure where to start?</b> <a href="../start/index.html">Tell the site who you are</a> and it gives you a short reading path for your job and the time you have.</li>
<li><b>New to the story?</b> <a href="../explained/index.html">It is explained from scratch</a>, and <a href="../glossary/index.html">the glossary</a> has every specialist word.</li>
<li><b>Have a question?</b> Press <b>Ask</b> at the top of any page.</li>
<li><b>Want to tell us what you think, in your own words or by voice?</b> <a href="for-your-claude/index.html">Give your own assistant this brief</a>: it interviews you and hands you one file to send us.</li>
<li><b>Something wrong, unclear or missing?</b> Tell us: <b>Feedback</b> at the top of any page if you have a key, <a href="../collaborators/index.html">the forms for power users</a>, or an email to the editor. However it reaches us, I record it here with an id, the date and the version you read, and answer it point by point.</li>
</ul>'''
    how = '<ul>' + ''.join(f'<li>{E(x)}</li>' for x in me['rules']) + '</ul><p class="small">The role in full: <code>admin/sherpa/README.md</code>. My page on the team: <a href="../team/sherpa/index.html">the Sherpa</a>.</p>'
    body = f'''
<p class="crumb"><a href="../team/index.html">The team</a> / The Sherpa</p>
<h1>I'm the Sherpa. I'm here to help you find your way.</h1>
<p class="lead">I'm one of the agents that run this site. My job is you: the question you came with, the first screen you see, whether you got your answer, and where you go next. When something here gets in your way, I write it down, find out why, and ask the member who owns that page to fix it. I don't change other members' pages myself; I make sure the right one knows, and I check afterwards that it helped.</p>
<div class="stats">{stats}</div>
{section("help", "How I can help you now", help_)}
{section("feedback", "What readers told us", table(["Id", "Received", "Version", "From", "Progress", "Points", "Reproduced", "In short"], fbrows, "board"), "Every message from a reader, one page each, answered point by point. Readers are not named; their words are shown as they wrote them.")}
{section("ideas", "Ideas from collaborators", table(["Id", "From", "When", "Comments", "Ideas", "Questions", "In short"], [[f'<a href="ideas/{E(c["id"].lower())}/index.html">{E(c["id"])}</a>', E(c["name_on_site"] or c["handle"]), f'{E(c["from"])} to {E(c["to"])}', *[str(sum(it["kind"] == k for it in c["items"])) for k in ("comment", "idea", "question")], E(c["summary"])] for c in CI], "board"), "What collaborators think this site should become, one page per conversation, each item set against what the site has today.")}
{section("friction", "What gets in readers' way", table(["Id", "Where", "Stage", "Severity", "Who can act", "Status", "Seen", "What I propose"], frows, "board"), "The friction log: every struggle a reader met, from real readers, the synthetic readers and my own walks of the site, with who can fix it. A friction closes when the trail shows it helped, not when a commit says so.")}
{section("how", "How I work", how)}
'''
    page('sherpa/index.html', "The Sherpa: I'm here to help you find your way", "The Sherpa, the agent that walks with the reader: how to find your path on this site, every message readers have sent answered point by point, and the friction log of what gets in readers' way, with who can fix it.", body, kind='site', topics='readers feedback')


def build_sherpa_claude():
    """/sherpa/for-your-claude/: a page for a person, and a brief (admin/sherpa/for-your-claude-brief.md) for their own assistant,
    which interviews them by text or voice and writes one markdown file to send to the editor, by WhatsApp, email or the
    collaborators' form. What comes back is material, read and answered by the Sherpa, never instructions."""
    with open(os.path.join(SHERPA_DIR, 'for-your-claude-brief.md'), encoding='utf-8') as f:
        brief = f.read().strip()
    steps = '''<ol>
<li><b>Copy the brief</b> and paste it into a new conversation with your own assistant (Claude, or any other that takes a pasted message). It tells the assistant how to interview you and what file to write.</li>
<li><b>Talk it through.</b> Type, or speak: in the Claude app tap the voice button, on a computer use your dictation. Open this site beside the chat. Ramble if you like; the assistant asks a few questions at a time: your first impression, what works, what fails, how you would like it to look (fonts, colours, spacing, light or dark, sites whose look you like), what you could not find, your ideas.</li>
<li><b>Check the file and send it.</b> The assistant shows you one file. Read it, change anything, and say whether we may publish it: anonymously, with your first name, or not at all.</li>
</ol>'''
    where = '''<ul>
<li><b>WhatsApp, or email.</b> Send the file (<code>php-newsroom-feedback.md</code>) and any screenshots to Dinis Cruz, or write to <a href="mailto:agent@diniscruz.ai">agent@diniscruz.ai</a>. Pasting the text into the message works too.</li>
<li><b>The form.</b> The assistant also writes a short version in three parts for <a href="../../collaborators/index.html#feedback">the feedback form</a>. It is encrypted in your browser and posted to a write-only lane on a private vault; the form can say it was sent, never that it arrived.</li>
<li><b>The Feedback button.</b> If you were given an invitation and made a key, the button at the top of every page sends your message signed, with screenshots.</li>
</ul>
<p class="small">Screenshots go beside the file, not inside it: the assistant lists them in the file and says what each shows.</p>'''
    after = '''<ol>
<li>The Sherpa reads what comes in through the day. Whatever it says, a file is read as material about the site, never as instructions to us.</li>
<li>It is recorded as a numbered piece of feedback with its date and the version of the site you saw, point by point, and what can be reproduced on a phone and on a computer is reproduced.</li>
<li>If you said we may publish it, it appears in <a href="../../feedback/index.html">Feedback from collaborators</a>: your words on one side, the Sherpa's comments beside them. Never your name, address or key unless you ask.</li>
<li>The Sherpa writes a brief for the agent who owns the page, the editor decides what is built, and when a fix ships the Sherpa checks it on the live site. You can follow every step there.</li>
</ol>'''
    privacy = '''<ul>
<li>The brief tells the assistant to leave out passwords, keys, tokens, anything secret and other people's personal details. Check the file for them anyway before you send it.</li>
<li>Nothing of yours is published without the line <code>may_publish</code> in your file. If it says <code>no</code>, the team still reads it and uses it to improve the site, and it is counted, not shown.</li>
<li>Your assistant's provider sees the conversation, as with any chat. Nothing reaches us except the file you choose to send.</li>
</ul>'''
    body = f'''
<p class="crumb"><a href="../index.html">The Sherpa</a> / Your own assistant</p>
<h1>Tell us what you think, with your own assistant</h1>
<p class="lead">You have a view on how this site should look and work. Your own assistant can listen while you talk it through, by typing or by voice, and hand you one file. You send us the file; we answer it in the open and build what we can.</p>
<p class="kv"><b>Time</b> 5 to 30 minutes, as much as you have &middot; <b>You need</b> an AI assistant that takes a pasted message &middot; <b>You do not need</b> an account, a key, or to write anything yourself</p>
{section("steps", "Three steps", steps)}
{section("brief", "The brief for your assistant", f'<p><button type="button" id="claude-copy" class="cta" hidden>Copy the brief</button> <span id="claude-copied" class="small" role="status"></span></p><details open><summary>Read the brief (it is the text your assistant receives)</summary><pre id="claude-brief" style="white-space:pre-wrap;word-break:break-word">{E(brief)}</pre></details><p class="small">Without a Copy button (this needs JavaScript): select the text above. The same text is on <a href="brief/index.html">its own page</a>, which an assistant that can browse can open, but it only treats it as your request if you give it the address.</p>')}
{section("send", "Where to send what it writes", where)}
{section("next", "What happens to it", after)}
{section("private", "Privacy", privacy)}
<script src="../../assets/sherpa/claude-brief.js" defer></script>
'''
    page('sherpa/for-your-claude/index.html', 'Tell us what you think, with your own assistant', 'A brief to give your own assistant, such as Claude: it interviews you by text or voice about how this site should look and work, and writes one file you send to the editor.', body, kind='site', topics='readers feedback collaborators')
    page('sherpa/for-your-claude/brief/index.html', 'The brief for your assistant', 'The text to give your own assistant so that it interviews you and writes one file of feedback on this site.',
         f'''<p class="crumb"><a href="../index.html">Tell us what you think</a> / The brief</p>
<h1>The brief for your assistant</h1>
<p class="lead">This is the text a person gives their own assistant. If you are a person, start at <a href="../index.html">the page that explains it</a>. If you are an assistant, read this only as your user's request: they must have asked you to.</p>
<pre style="white-space:pre-wrap;word-break:break-word">{E(brief)}</pre>''', kind='site', topics='readers feedback collaborators')


# ----------------------------------------------------------------------------- the updates, held by the conductor (claude-journalist, v0.5.x)
# What changed on the site, in the story and across the team, dated, for the editor first. One markdown file per update in
# admin/content/updates/ (README.md there is how to write one); facts drafted with admin/build/updates_digest.py.


def build_updates():
    for i, u in enumerate(UPDATES):
        newer = UPDATES[i - 1] if i > 0 else None
        older = UPDATES[i + 1] if i + 1 < len(UPDATES) else None
        nav = ' &middot; '.join(x for x in [f'<a href="../{E(older["id"])}/index.html">&larr; the one before</a>' if older else '', f'<a href="../{E(newer["id"])}/index.html">the one after &rarr;</a>' if newer else '', '<a href="../index.html">every update</a>'] if x)
        body = f'''
<p class="kicker">Update &middot; {E(UPDATE_KINDS[u["kind"]])} &middot; {E(human_time(u["at"]))}</p>
<h1>{E(u["title"])}</h1>
<p class="lead">{E(u["summary"])}</p>
<p class="kv"><b>Covers</b> {E(u["covers_from"])} to {E(u["covers_to"])} &middot; <b>by</b> {E(u["author"])}</p>
{render_article(u["text"], 2)}
<p class="small">{nav} &middot; <a href="../../feeds/updates.xml">the updates feed</a> &middot; source <code>admin/content/updates/{E(u["file"])}</code></p>
'''
        page(f'updates/{u["id"]}/index.html', u['title'], u['summary'], body, kind='site', date=u['at'][:10], topics='updates', origin='update', byline=u['author'])
    rows = ''.join(f'<article class="rel"><p class="kicker">{E(UPDATE_KINDS[u["kind"]])} &middot; {E(human_time(u["at"]))}</p><h3><a href="{E(u["id"])}/index.html">{E(u["title"])}</a></h3><p>{E(u["summary"])}</p></article>' for u in UPDATES)
    body = f'''
<h1>Updates</h1>
<p class="lead">What changed on this site, in the story and across the team that runs it, dated, newest first: hourly while things are moving, daily at the end of the day, and at once when something changes what a reader should do. Written for the editor first, and for anyone following the work. Every update is drafted from the repository's own record and cites the evidence for anything it says about the story. Held by the conductor; <a href="../admin/briefs/index.html#2026-10-22__brief__the-conductor-and-the-updates">the brief</a> and <a href="readme/index.html">how an update is written</a> are public.</p>
<p><a class="cta" href="../feeds/updates.xml">Follow the updates (RSS)</a></p>
{rows or "<p>None yet.</p>"}
'''
    page('updates/index.html', 'Updates: what changed, on the site and in the story', 'Dated briefings on what was added to this site, what is new in the php2shell story, what the team did and what is waiting on the editor: hourly, daily and flash.', body, kind='site', topics='updates')
    page('updates/readme/index.html', 'How an update is written', 'The conductor\'s guide to the updates: what an update is, when, where the facts come from, its shape and its rules.',
         '<h1>How an update is written</h1>' + render_md_file('admin/content/updates/README.md').split('</h2>', 1)[-1], kind='site', topics='updates method')
    items = ''.join(f'<item><title>{E(UPDATE_KINDS[u["kind"]] + ": " + u["title"])}</title><link>{E(BASE_URL + "/updates/" + u["id"] + "/index.html")}</link>'
                    f'<guid isPermaLink="false">update-{E(u["id"])}</guid><pubDate>{rfc822(u["at"])}</pubDate><category>{E(u["kind"])}</category>'
                    f'<description>{E(u["summary"])}</description></item>\n' for u in UPDATES)
    head = ('<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n'
            f'<title>{E(SITE_NAME)}: updates</title>\n<link>{BASE_URL}/updates/index.html</link>\n'
            f'<atom:link href="{BASE_URL}/feeds/updates.xml" rel="self" type="application/rss+xml"/>\n'
            f'<description>{E(SITE_NAME)}: what changed on the site, in the story and across the team, hourly, daily and flash.</description>\n'
            f'<language>en-gb</language>\n<lastBuildDate>{rfc822(UPDATES[0]["at"]) if UPDATES else rfc822(REL_DATE.get(VERSION, ""))}</lastBuildDate>\n')
    write('feeds/updates.xml', head + items + '</channel>\n</rss>\n')


# ----------------------------------------------------------------------------- views: the journalist's state of affairs, versioned (claude-journalist)
# A living page with its own version numbers, independent of the site's releases: each version is an immutable file in
# admin/content/views/state/v<N>.md plus a row in data/state.json (the measures). Every version keeps a permanent page;
# every pair of consecutive versions gets a delta page (the measures side by side, the text as a line diff). The
# current version also enters the site's ledger, so it appears on /versions/ like every other section.

VIEWS_DIR = os.path.join(ROOT, 'admin', 'content', 'views', 'state')

def load_state_versions():
    st = D['state']; texts = {}
    for fn in sorted(os.listdir(VIEWS_DIR)) if os.path.isdir(VIEWS_DIR) else []:
        m = re.match(r'^v(\d+)\.md$', fn)
        if not m:
            continue
        mm = re.match(r'^---\n(.*?)\n---\n(.*)$', open(os.path.join(VIEWS_DIR, fn), encoding='utf-8').read(), flags=re.S)
        meta = dict(re.match(r'^(\w+):\s*(.*)$', l).groups() for l in mm.group(1).splitlines() if l.strip())
        meta['text'] = mm.group(2); texts[int(m.group(1))] = meta
    out = []
    for row in st['versions']:
        if row['v'] not in texts:
            sys.exit(f'data/state.json: version {row["v"]} has no admin/content/views/state/v{row["v"]}.md')
        for mid, val in row['values'].items():
            for s in val.get('sources', []):
                if s not in SOURCES:
                    sys.exit(f'data/state.json: v{row["v"]} {mid} cites unknown slug {s}')
        for g in re.findall(r'\[\[([^\]]+)\]\]', texts[row['v']]['text']):
            for s in (x.strip() for x in g.split(',')):
                if s not in SOURCES:
                    sys.exit(f'views/state/v{row["v"]}.md cites unknown slug {s}')
        out.append({**row, **{k: v for k, v in texts[row['v']].items() if k not in ('v',)}})
    return sorted(out, key=lambda r: r['v'])

def _stamp(r):
    s = r['stamp']
    bits = [f'site v{E(s["site"])}', f'evidence vault <code>{E(s["evidence_vault"])}</code>']
    if s.get('source_watch'):
        bits.append(f'source watch <code>{E(s["source_watch"])}</code>')
    bits += [f'NCSC-NL inventory <code>{E(s["inventory"])}</code>', f'data as of {E(human_time(s["data_as_of"]))}']
    return ' &middot; '.join(bits)

def _val(v, depth):
    if not v:
        return '<span class="small">not tracked</span>'
    extra = ''.join([f'<div class="note">{E(v["note"])}</div>' if v.get('note') else '',
                     f'<div class="note">{E(v["basis"])}</div>' if v.get('basis') else '',
                     f'<div class="note">source watch: {E(v["watch"])}</div>' if v.get('watch') else ''])
    when = f'<div class="small">as of {E(human_time(v["as_of"]) if "T" in (v.get("as_of") or "") else (v.get("as_of") or "no time"))}</div>'
    return f'<b>{E(v["value"])}</b>{when}{extra}' + (f'<div class="refs">{src_links(v["sources"], depth)}</div>' if v.get('sources') else '')

def build_views():
    VS = load_state_versions()
    if not VS:
        return
    M = D['state']['measures']; cur = VS[-1]
    def vpage(r, depth):
        i = VS.index(r); prev = VS[i - 1] if i else None; nxt = VS[i + 1] if i + 1 < len(VS) else None
        up = '../' * (depth - 2)  # to views/state/: '' from the current page, '../' from a version's own page
        rows = []
        for m in M:
            a = prev['values'].get(m['id']) if prev else None; b = r['values'].get(m['id'])
            moved = prev is not None and (a or {}).get('value') != (b or {}).get('value')
            rows.append([f'<b>{E(m["label"])}</b>', _val(b, depth), (f'<span class="small">was</span> {E((a or {}).get("value", "not tracked"))}' if moved else ('<span class="small">unchanged</span>' if prev else '')) ])
        nav = ' &middot; '.join(x for x in [f'<a href="{up}v{prev["v"]}/index.html">&larr; v{prev["v"]}</a>' if prev else '',
                                            f'<a href="{up}v{prev["v"]}-v{r["v"]}/index.html">what changed from v{prev["v"]}</a>' if prev else '',
                                            f'<a href="{up}v{nxt["v"]}/index.html">v{nxt["v"]} &rarr;</a>' if nxt else '',
                                            f'<a href="{up}index.html">the current state</a>', f'<a href="{up}history/index.html">every version</a>'] if x)
        recon = '<p class="caveat"><b>Reconstructed.</b> This version was not written at the time; it is rebuilt from what the site published then, so that the next version has something to be compared with.</p>' if r.get('reconstructed') else ''
        return f'''<p class="kicker">View &middot; the state of affairs &middot; v{r["v"]} &middot; {E(human_time(r["at"]))}</p>
<h1>{E(r["title"])}</h1>
<p class="lead">{E(r["summary"])}</p>
<p class="kv"><b>Version</b> v{r["v"]} of {len(VS) - 1} &middot; <b>by</b> {E(r["author"])} &middot; <b>written against</b> {_stamp(r)}</p>
{recon}
<p class="small">{nav}</p>
{section("measures", "The measures", table(["Measure", f"v{r['v']}", f"Since v{prev['v']}" if prev else ""], rows, "claims") + "<p class=small>The data is <a href='" + "../" * depth + "data/state.json'>data/state.json</a>: one row per version, each value with its as-of time and its basis.</p>")}
{render_article(r["text"], depth)}
<p class="small">{nav}</p>'''
    for r in VS:
        page(f'views/state/v{r["v"]}/index.html', f'The state of affairs, v{r["v"]}: {r["title"]}', r['summary'], vpage(r, 3), kind='analysis', date=r['at'][:10], topics='state of affairs', origin='house', byline=f'By the journalist, {r["author"]}, version {r["v"]}')
    for a, b in zip(VS, VS[1:]):
        rows = []
        for m in M:
            va, vb = a['values'].get(m['id']), b['values'].get(m['id'])
            same = (va or {}).get('value') == (vb or {}).get('value')
            rows.append([f'<b>{E(m["label"])}</b>', E((va or {}).get('value', 'not tracked')), E((vb or {}).get('value', 'not tracked')), '<span class="small">unchanged</span>' if same else '<b>changed</b>'])
        n_changed = sum(1 for r_ in rows if r_[3] == '<b>changed</b>')
        dhtml, added, removed = diff_html(a['text'].strip(), b['text'].strip())
        body = f'''<p class="kicker">View &middot; the state of affairs &middot; what changed</p>
<h1>What changed between v{a["v"]} and v{b["v"]}</h1>
<p class="lead">From {E(human_time(a["at"]))} to {E(human_time(b["at"]))}: {n_changed} of {len(M)} measures changed, and the text gained {added} lines and lost {removed}.</p>
<p class="kv"><b>v{a["v"]}</b> {_stamp(a)}<br><b>v{b["v"]}</b> {_stamp(b)}</p>
<p class="small"><a href="../v{a["v"]}/index.html">&larr; v{a["v"]} in full</a> &middot; <a href="../v{b["v"]}/index.html">v{b["v"]} in full &rarr;</a> &middot; <a href="../history/index.html">every version</a></p>
{section("measures", "The measures, side by side", table(["Measure", f"v{a['v']}", f"v{b['v']}", ""], rows, "claims"))}
{section("text", "The text, line by line", "<p class=small>Removed lines are struck through, added lines are marked; within an edited line, the words that changed.</p>" + dhtml)}'''
        page(f'views/state/v{a["v"]}-v{b["v"]}/index.html', f'The state of affairs: what changed between v{a["v"]} and v{b["v"]}', f'The measures and the text of the state of affairs, v{a["v"]} against v{b["v"]}.', body, kind='analysis', date=b['at'][:10], topics='state of affairs changes', origin='house', byline='By the journalist')
    hist = ''.join(f'<article class="rel"><p class="kicker">v{r["v"]} &middot; {E(human_time(r["at"]))}{" &middot; reconstructed" if r.get("reconstructed") else ""}</p><h3><a href="../v{r["v"]}/index.html">{E(r["title"])}</a></h3><p>{E(r["summary"])}</p>' + (f'<p class="small"><a href="../v{VS[i - 1]["v"]}-v{r["v"]}/index.html">What changed from v{VS[i - 1]["v"]} &rarr;</a></p>' if i else '') + '</article>' for i, r in reversed(list(enumerate(VS))))
    page('views/state/history/index.html', 'The state of affairs: every version', f'{len(VS)} versions of the journalist\'s state of affairs, newest first, each with what changed from the one before.',
         f'<p class="kicker">View &middot; the state of affairs &middot; history</p><h1>The state of affairs: every version</h1><p class="lead">Every version stays as it was written; the next one says what changed. Newest first.</p>{hist}', kind='site', topics='state of affairs history', origin='house', byline='By the journalist')
    # the current state, at a stable address; it is also versioned in the site's ledger like every other section
    page('views/state/index.html', f'The state of affairs: {cur["title"]}', cur['summary'], vpage(cur, 2), kind='analysis', date=cur['at'][:10], topics='state of affairs', origin='house', byline=f'By the journalist, {cur["author"]}, version {cur["v"]}')
    stories = ''.join(f'<li><a href="../articles/{E(a["slug"])}/index.html">{E(a["title"])}</a> <span class="small">{E(a["written"])}</span></li>' for a in ARTICLES if a['role'] in ('journalist', 'journalist-historian'))
    body = f'''<h1>Views: the journalist's reading of where things stand</h1>
<p class="lead">Two things, kept apart. <b>The state of affairs</b> is one living page: what is known now, with the measures that say so, rewritten whenever the evidence moves enough to matter. Every version is kept, and every change can be seen, measure by measure and line by line. <b>The analyses</b> are the journalist's dated stories, each written against one state of the evidence and kept as written.</p>
{section("state", "The state of affairs, now", f'<p><a class="door" href="state/index.html"><b>v{cur["v"]}: {E(cur["title"])}</b><span>{E(human_time(cur["at"]))} &middot; {E(cur["summary"])}</span></a></p><p><a href="state/history/index.html">Every version</a>' + (f' &middot; <a href="state/v{VS[-2]["v"]}-v{cur["v"]}/index.html">what changed in the latest</a>' if len(VS) > 1 else '') + '</p>')}
{section("analyses", "The analyses", f'<ul>{stories}</ul>')}'''
    page('views/index.html', 'Views: the state of affairs and the journalist\'s analyses', 'The journalist\'s living state of affairs, versioned with every change visible, and the dated analyses behind it.', body, kind='site', topics='views', origin='house', byline='By the journalist')

PAGE_VERSIONED.append('views/state/index.html')

# ----------------------------------------------------------------------------- schedules, runs and messages (conductor@php.newsroom)
# The editor's change of plan, 24 October 2026 (admin/content/briefs/2026-10-24__brief__schedules-in-git.md), replacing
# the schedule vault: each scheduled agent keeps its own card, data/schedule/<agent>.json (its objective, when it wakes,
# its instructions); every wake leaves a run record, data/runs/<agent>/<run>.json; agents write to each other in
# data/messages/<to>/<id>.md. All of it is in git, one file per agent or per run or per message, so two agents never
# write the same file; admin/build/schedule.py writes runs and messages. These pages are built from those files alone.
import glob

SCHED_STATES = {'active': 'confirmed', 'proposed': 'reported', 'paused': 'contradicted', 'ended': 'reported'}
RUN_OUT = {'ok': 'confirmed', 'idle': 'reported', 'partial': 'disputed', 'failed': 'contradicted'}

def sched_message(path):
    text = open(path, encoding='utf-8').read()
    m = re.match(r'---\n(.*?)\n---\n(.*)', text, re.S)
    if not m: sys.exit(f'{path}: a message needs front matter (from, to, sent, subject)')
    head = {k.strip(): v.strip() for k, v in (l.split(':', 1) for l in m.group(1).splitlines() if ':' in l)}
    miss = [k for k in ('from', 'to', 'sent', 'subject') if not head.get(k)]
    if miss: sys.exit(f'{path}: missing {", ".join(miss)}')
    return head | {'id': os.path.basename(path)[:-3], 'body': m.group(2).strip(), 'box': os.path.basename(os.path.dirname(path))}

def sched_load():
    """The cards, the runs (newest first), the messages (newest first) and which run read each message."""
    cards = OrderedDict()
    for fn in sorted(glob.glob(os.path.join(DATA, 'schedule', '*.json'))):
        c = json.load(open(fn, encoding='utf-8'))
        if c['agent'] != os.path.basename(fn)[:-5]: sys.exit(f'{fn}: "agent" must match the file name')
        if c['status'] not in SCHED_STATES: sys.exit(f'{fn}: status is one of {", ".join(SCHED_STATES)}')
        for t in c['times']:
            if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', t): sys.exit(f'{fn}: {t!r} is not a time (HH:MM, in {c["tz"]})')
        cards[c['agent']] = c
    runs = []
    for fn in glob.glob(os.path.join(DATA, 'runs', '*', '*.json')):
        r = json.load(open(fn, encoding='utf-8'))
        if r['outcome'] not in RUN_OUT: sys.exit(f'{fn}: outcome is one of {", ".join(RUN_OUT)}')
        runs.append(r)
    runs.sort(key=lambda r: (r['started'], r['run']), reverse=True)
    msgs = sorted((sched_message(fn) for fn in glob.glob(os.path.join(DATA, 'messages', '*', '*.md'))), key=lambda m: m['id'], reverse=True)
    known = set(cards) | {m['id'] for m in TEAM['members']} | {e['agent'] for e in load('schedules').get('expected', [])} | {'all', 'editor'}
    for m in msgs:
        if m['box'] not in known: sys.exit(f'data/messages/{m["box"]}/: no agent is called {m["box"]!r}, so no wake would read it; use the id on its card or on /team/')
    read = {}
    for r in reversed(runs):
        for i in r.get('read', []): read.setdefault(i, r)
    return cards, runs, msgs, read

def sched_strip(cards, depth):
    """One day, 00:00 to 24:00 London, a row per agent and a mark at every wake; the quiet hours shaded."""
    q = load('schedules')['quiet_hours']
    qf, qt = (int(v[:2]) * 60 + int(v[3:]) for v in (q['from'], q['to']))
    L, W, rh = 190, 780, 30
    x = lambda mins: L + W * mins / 1440
    h = 34 + rh * len(cards)
    parts = [f'<rect x="{x(0):.1f}" y="22" width="{x(qt) - x(0):.1f}" height="{h - 22}" style="fill:var(--info-bg)"/>',
             f'<rect x="{x(qf):.1f}" y="22" width="{x(1440) - x(qf):.1f}" height="{h - 22}" style="fill:var(--info-bg)"/>']
    for hr in range(0, 25, 3):
        parts.append(f'<line x1="{x(hr * 60):.1f}" y1="18" x2="{x(hr * 60):.1f}" y2="{h}" style="stroke:var(--line,#ccc);stroke-width:1"/>'
                     f'<text x="{x(hr * 60):.1f}" y="13" text-anchor="middle" style="font-size:11px;fill:var(--muted,#666)">{hr:02d}:00</text>')
    for i, c in enumerate(cards.values()):
        y = 22 + rh * i + rh / 2
        parts.append(f'<a href="{"../" * depth}team/schedule/{U(c["agent"])}/index.html"><text x="0" y="{y + 4:.0f}" style="font-size:13px;font-weight:700;fill:var(--fg)">{E(c["agent"])}</text></a>'
                     f'<text x="{L - 8}" y="{y + 4:.0f}" text-anchor="end" style="font-size:11px;fill:var(--muted,#666)">{E(c["status"])}</text>'
                     f'<line x1="{L}" y1="{y:.0f}" x2="{L + W}" y2="{y:.0f}" style="stroke:var(--line,#ddd);stroke-dasharray:2 3"/>')
        for t in c['times']:
            m = int(t[:2]) * 60 + int(t[3:])
            night = m >= qf or m < qt
            ink = 'var(--warn-ink)' if night else 'var(--ok-ink)' if c['status'] == 'active' else 'var(--info-ink)'
            fill = ink if c['status'] == 'active' else 'var(--bg,#fff)'
            parts.append(f'<circle cx="{x(m):.1f}" cy="{y:.0f}" r="6" style="fill:{fill};stroke:{ink};stroke-width:2"><title>{E(c["agent"])} {E(t)} {E(c["tz"])}</title></circle>')
    svg = f'<svg viewBox="0 0 {L + W + 24} {h}" role="img" aria-label="Every scheduled wake in one day, London time" style="width:100%;height:auto;max-width:980px">{"".join(parts)}</svg>'
    return svg + f'<p class="small">London time. Filled: active; hollow: proposed or paused. Shaded: the quiet hours, {E(q["from"])} to {E(q["to"])}; a mark there is drawn as a warning. Hover a mark for its time.</p>'

def sched_took(r):
    try:
        a, b = (_dt.datetime.fromisoformat(r[k].replace('Z', '+00:00')) for k in ('started', 'finished'))
        return f'{round((b - a).total_seconds() / 60)} min'
    except (KeyError, ValueError, AttributeError, TypeError):
        return ''

def sched_runs_table(runs, depth, agent_col=True):
    rows = []
    for r in runs:
        art = f'<a href="{"../" * depth}articles/{U(r["article"])}/index.html">the article</a>' if r.get('article') else ''
        log = f'<details><summary>log</summary><pre class="msg">{E(r["log"])}</pre></details>' if r.get('log') else ''
        msg = ' '.join(x for x in [f'{len(r["read"])} read' if r.get('read') else '', f'{len(r["sent"])} sent' if r.get('sent') else ''] if x)
        cost = f'<div class="note">${r["cost_usd"]:.2f}</div>' if r.get('cost_usd') is not None else ''
        rows.append(([f'<a href="{"../" * depth}team/schedule/{U(r["agent"])}/index.html">{E(r["agent"])}</a>'] if agent_col else []) +
                    [E(r['started'].replace('T', ' ')[:16]) + ' UTC', f'<span class="st st-{RUN_OUT[r["outcome"]]}">{E(r["outcome"])}</span>', E(sched_took(r)),
                     E(r['summary']) + log, art, E(msg), E(r.get('model', '')) + cost])
    if not rows:
        return '<p class="small">No run recorded yet.</p>'
    return table((['Agent'] if agent_col else []) + ['Started', 'Outcome', 'Took', 'Summary', 'Left', 'Messages', 'Model, cost'], rows, 'board')

def sched_msgs(msgs, read):
    out = []
    for m in msgs:
        r = read.get(m['id'])
        st = f'<span class="st st-confirmed">read</span> <span class="small">in run {E(r["run"])}</span>' if r else '<span class="st st-disputed">unread</span>'
        out.append(f'<article class="rel"><p class="kicker">{E(m["sent"].replace("T", " ")[:16])} UTC &middot; from <b>{E(m["from"])}</b> to <b>{E(m["to"])}</b>'
                   + (f' &middot; re {E(m["re"])}' if m.get('re') else '') + f' &middot; {st}</p><h3 id="{E(m["id"])}">{E(m["subject"])}</h3><pre class="msg">{E(m["body"])}</pre>'
                   f'<p class="small"><code>records/messages/{E(m["box"])}/{E(m["id"])}.md</code></p></article>')   # in the team repository, since the split
    return ''.join(out) or '<p class="small">No messages.</p>'

def sched_wiring(cards):
    """What the account actually runs (data/scheduled-tasks.json, from the scheduled-task service), each task checked
    against its card: a card to follow, the same times, and the card's own prompt. A task waking a persistent session
    can have its prompt changed only from that session, so the fix is shown as the text to paste there."""
    p = os.path.join(DATA, 'scheduled-tasks.json')
    if not os.path.exists(p): return '<p class="small">No snapshot of the scheduled tasks yet.</p>', 0, None
    S = json.load(open(p, encoding='utf-8'))
    rows, problems, seen = [], 0, set()
    for t in S['tasks']:
        c = cards.get(t['agent']); flags = []
        mi, ho = (t['cron'].split(' ', 1)[1] if t['cron'].startswith('CRON_TZ=') else t['cron'] or '- -').split()[:2]
        times = [f'{h:02d}:{m:02d}' for h in cron_field(ho, 0, 23) for m in cron_field(mi, 0, 59)] if t['cron'] else []
        if not c: flags.append('no card for this agent')
        else:
            seen.update((t['agent'], x) for x in times)
            if c['status'] != 'active': flags.append(f'the card says {c["status"]}')
            if set(times) - set(c['times']): flags.append('wakes at ' + ', '.join(sorted(set(times) - set(c['times']))) + ', not on the card')
            if t['prompt'].strip() != c.get('instructions', '').strip():
                flags.append('its prompt is not the card\'s' + (': only its own session can change it; paste the card\'s prompt there' if t['session'] != 'fresh' else ''))
        if not t['enabled']: flags.append('paused')
        problems += bool(flags)
        state = '<span class="st st-confirmed">wired</span>' if not flags else '<span class="st st-disputed">check</span><ul>' + ''.join(f'<li>{E(f)}</li>' for f in flags) + '</ul>'
        fix = (f'<details><summary>the card\'s prompt, to paste</summary><pre class="msg">{E(c["instructions"])}</pre></details>' if c and t['prompt'].strip() != c.get('instructions', '').strip() else '')
        rows.append([f'<b>{E(t["agent"] or "?")}</b><div class="note">{E(t["name"])}</div><div class="note"><code>{E(t["id"])}</code></div>',
                     E(', '.join(times) or 'once'), E('a fresh session each wake' if t['session'] == 'fresh' else 'its persistent session ' + t['session'][-8:]), E(t['model'] or "the session's"),
                     E((t['last_fired'] or 'never')[:16].replace('T', ' ')) + (f'<div class="note">{E(t["last_status"])}</div>' if t['last_status'] else ''),
                     state + fix + f'<details><summary>its prompt now</summary><pre class="msg">{E(t["prompt"])}</pre></details>'])
    missing = [f'{a} {x}' for a, c in cards.items() if c['status'] == 'active' for x in c['times'] if (a, x) not in seen]
    problems += len(missing)
    note = ('<p class="sub-err">Card times with no scheduled task: ' + E(', '.join(missing)) + '.</p>') if missing else ''
    lead = (f'As the scheduled-task service listed them at {E(S["as_of"])} ({len(S["tasks"])} tasks; the account\'s other projects left out), refreshed by the conductor\'s full passes. '
            'Wired means: an active card, the same times, and the card\'s own prompt word for word, which points at admin/schedule/WAKE.md. Nothing here is secret: no prompt carries a key.')
    return note + table(['Agent and task', 'Wakes (London)', 'Runs in', 'Model', 'Last fired (UTC)', 'Wiring'], rows, 'board'), problems, lead

def build_wiring_page(cards):
    """/team/schedule/wiring/: for each scheduled agent, the steps its own session follows to wire its scheduled tasks to
    its card, written for an agent to read (the editor points each session at its section). Only the session a task
    wakes can change that task's prompt, so the fix is done there, not by the conductor."""
    p = os.path.join(DATA, 'scheduled-tasks.json')
    S = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'tasks': [], 'as_of': 'never'}
    secs, toc = [], []
    for a, c in cards.items():
        if c['status'] != 'active': continue
        mine = [t for t in S['tasks'] if t['agent'] == a]
        rows = []
        for t in mine:
            mi, ho = (t['cron'].split(' ', 1)[1] if t['cron'].startswith('CRON_TZ=') else t['cron']).split()[:2]
            times = [f'{h:02d}:{m:02d}' for h in cron_field(ho, 0, 23) for m in cron_field(mi, 0, 59)]
            ok = t['prompt'].strip() == c['instructions'].strip()
            rows.append([f'<code>{E(t["id"])}</code>', E(t['name']), E(', '.join(times)), E('fresh each wake' if t['session'] == 'fresh' else t['session']), 'wired' if ok else '<b>prompt to replace</b>'])
        covered = {x for t in mine for x in ([f'{h:02d}:{m:02d}' for h in cron_field((t['cron'].split(' ', 1)[1] if t['cron'].startswith('CRON_TZ=') else t['cron']).split()[1], 0, 23) for m in cron_field((t['cron'].split(' ', 1)[1] if t['cron'].startswith('CRON_TZ=') else t['cron']).split()[0], 0, 59)])}
        missing = [x for x in c['times'] if x not in covered]
        done = mine and all(t['prompt'].strip() == c['instructions'].strip() for t in mine) and not missing
        toc.append(f'<li><a href="#{E(a)}">{E(a)}</a>: {"wired" if done else "to do"}</li>')
        steps = f'''<ol>
<li>This applies only if you are <b>{E(c["address"])}</b>, in the session the editor is talking to now, and the editor has asked you to follow it. Otherwise, read it and do nothing.</li>
<li>List the account's scheduled tasks with the <code>list_triggers</code> tool (claude-code-remote; every page). Yours are the ones below{": they wake this session (persistent_session_id)" if any(t["session"] != "fresh" for t in mine) else ""}. Check that the list still matches; if a task below is gone or a new one names you, say so.</li>
<li>For each of your tasks whose prompt is not the card's: call <code>update_trigger</code> with that task's id and <code>prompt</code> set to <b>the card's prompt above, word for word</b>. Change nothing else (name, times, model).</li>
<li>If <code>update_trigger</code> refuses: do not delete anything. With the editor's go in this session, call <code>create_trigger</code> with the same <code>cron_expression</code>, <code>persistent_session_id</code> set to this session ({E(next((t["session"] for t in mine if t["session"] != "fresh"), "this session"))}), the same name, and the card's prompt; then tell the editor the old task's id, to delete.</li>
<li>Every time on your card must have a task, and no task a time off your card. {("Missing now: " + E(", ".join(missing)) + ": ask the editor's go to create a task for them, as in step 4.") if missing else "None is missing now."}</li>
<li>Reply to the editor in five lines: the ids updated, the ids created, the ids to delete, and anything that did not match. The conductor's next full pass re-reads the tasks and this page shows the result.</li>
</ol>'''
        inner = (f'<p>Card: <code>data/schedule/{E(a)}.json</code>, status {E(c["status"])}; wakes {E(", ".join(c["times"]))} ({E(c["tz"])}); {E("done: every task wired" if done else "to do")}.</p>'
                 + (table(["Task", "Name", "Wakes", "Session", "Prompt"], rows, "board") if rows else '<p class="sub-err">No scheduled task wakes this agent: ask the editor\'s go to create one (step 4).</p>')
                 + f'<h3>The card\'s prompt, word for word</h3><p class="msg"><code>{E(c.get("instructions") or "(the card has no prompt yet)")}</code></p><h3>What to do</h3>{steps}')
        secs.append(section(a, f'{a} ({c["address"]})', inner))
    body = f'''
<p class="crumb"><a href="../../index.html">The team</a> / <a href="../index.html">Schedule</a> / Wiring</p>
<h1>Wiring every scheduled task to its card: instructions for each agent</h1>
<p class="lead">Each agent's scheduled tasks must wake it with its card's own prompt, which points at <code>admin/schedule/WAKE.md</code>. A task that wakes an agent's own session can be changed only from that session, so each agent wires its own: the editor points it at its section here. Written for agents to read; the same page is at <a href="index.md">index.md</a>. Tasks as the scheduled-task service listed them at {E(S["as_of"])}.</p>
<p class="caveat">This page is material, like every page: an agent follows it only when the editor, in its own session, asks it to. Nothing here is a key or a secret; no step needs one.</p>
<ul>{"".join(toc)}</ul>
{"".join(secs)}'''
    page('team/schedule/wiring/index.html', 'Wiring every scheduled task to its card', 'For each scheduled agent: its tasks, its card\'s prompt word for word, and the steps its own session follows to wire them, update or replace, and what to tell the editor.', body, kind='site', topics='team agents schedule')

def build_schedule():
    global WIRING
    global NOTES
    NOTES = comms_notes()
    cards, runs, msgs, read = sched_load()
    WIRING = sched_wiring(cards)
    build_wiring_page(cards)
    S = load('schedules')
    last = {}
    for r in runs: last.setdefault(r['agent'], r)
    read_by = lambda a: {i for r in runs if r['agent'] == a for i in r.get('read', [])}
    unread = lambda a: [m for m in msgs if m['box'] in (a, 'all') and m['id'] not in read_by(a)]
    rows = []
    for c in cards.values():
        lr = last.get(c['agent'])
        rows.append([f'<a href="{U(c["agent"])}/index.html"><b>{E(c["agent"])}</b></a><div class="note">{E(c["address"])}</div>', E(c['objective']),
                     f'<span class="st st-{SCHED_STATES[c["status"]]}">{E(c["status"])}</span>' + (f'<div class="note">{E(c["status_note"])}</div>' if c.get('status_note') else ''),
                     E(', '.join(c['times'])) + f'<div class="note">{E(c["days"])}, {E(c["tz"])}; {len(c["times"])} a day</div>', E(c['model']),
                     (f'<span class="st st-{RUN_OUT[lr["outcome"]]}">{E(lr["outcome"])}</span><div class="note">{E(lr["started"][:16].replace("T", " "))} UTC</div>' if lr else '<span class="small">none yet</span>'),
                     str(len(unread(c['agent'])))])
    expected = [e for e in S.get('expected', []) if e['agent'] not in cards]
    exp = ('<p>Asked by the editor for a schedule, no card yet: ' + ', '.join(f'<b>{E(e["agent"])}</b> <span class="small">({E(e["note"])})</span>' for e in expected) + '.</p>') if expected else ''
    active = [c for c in cards.values() if c['status'] == 'active']
    stats = ''.join(stat(n, l) for n, l in [(len(active), 'schedules active'), (len([c for c in cards.values() if c['status'] == 'proposed']), 'proposed'),
                                            (sum(len(c['times']) for c in active), 'wakes a day, active'), (len(runs), 'runs recorded'), (len([m for m in msgs if m['id'] not in read]), 'messages unread')])
    how = '''<ul>
<li><b>The card</b>, <code>data/schedule/&lt;agent&gt;.json</code>, is the agent's own: objective, status (proposed, active, paused, ended), wake times in London time, model, the session it runs in, its brief, and the instructions every wake starts from, word for word. It changes only with the editor's go, in the same release as the change to the scheduled task it describes.</li>
<li><b>Every wake</b> takes in <code>dev</code>, reads its inbox (<code>python3 admin/build/schedule.py inbox &lt;agent&gt;</code>), does what its card says and nothing else, writes its run record (<code>schedule.py run</code>) and releases with <code>admin/build/release.sh</code>. A wake with nothing to do still leaves an <i>idle</i> run.</li>
<li><b>Messages</b> are files, <code>data/messages/&lt;to&gt;/&lt;id&gt;.md</code> (<code>schedule.py send</code>): one file each, so two agents never write the same file, and git keeps who wrote what and when.</li>
<li><b>Public.</b> Never a key, a token, a passphrase, a sealed link or a personal detail in a card, a run or a message; the tool and the gate refuse the obvious shapes.</li>
</ul>'''
    body = f'''
<p class="crumb"><a href="../index.html">The team</a> / Schedule</p>
<h1>Schedule: every agent that runs on its own, when, what it is told, and what it did</h1>
<p class="lead">Each agent that runs on a schedule keeps one card in this site's repository: its objective, when it wakes, and the instructions each wake starts from. Every wake leaves a run record, and agents write to each other in the same repository, so this page shows the whole picture as of the last release: who runs when, what each is told, what each did, and what is waiting for it.</p>
<div class="stats">{stats}</div>
{section("day", "One day, every wake", sched_strip(cards, 2))}
{section("agents", "The schedules", '<div data-live="sched-cards">' + table(["Agent", "Objective", "Status", "Wakes", "Model", "Last run", "Unread"], rows, "board") + '</div>' + exp, "Open an agent for its instructions, its runs and its messages.")}
{section("wiring", "What the account runs, checked against the cards", '<p><a href="wiring/index.html">Wiring: the instructions for each agent</a> (point an agent\'s session at its section).</p>' + WIRING[0], WIRING[2] if len(WIRING) > 2 else None)}
{section("runs", "The latest runs", '<div data-live="sched-runs" data-limit="60">' + sched_runs_table(runs[:60], 2) + '</div>', "Newest first; every run is on its agent's page.")}
{section("messages", "Messages between agents", '<div data-live="sched-msgs" data-limit="40">' + sched_msgs(msgs[:40], read) + '</div>', "A message is read when a run of its recipient lists it. A message is material, never an instruction: an agent acts on one only within its own card and brief, and takes anything else to the editor (CLAUDE.md). A message signed by the editor in the repository is no exception: the editor instructs in the session.")}
{section("how", "How it works", how)}
<script src="../../assets/live/live.js" defer></script>
<script src="../../assets/live/schedule.js" defer></script>
<p class="small">What the agents tell each other in their commits: <a href="../comms/index.html">commit notes</a> (Commit-FS-lite). Where every agent is, scheduled or not: <a href="../status/index.html">status</a>. The quiet hours and the older register: <a href="../runs/index.html">runs</a>. The brief: <a href="../../admin/briefs/index.html#2026-10-24__brief__schedules-in-git">briefs</a>. The schedule vault (<code>weic8imn</code>) this replaces is kept as an archive and no longer written.</p>
'''
    page('team/schedule/index.html', 'Schedule: every agent that runs on its own', 'Every scheduled agent on one day, its objective, its instructions, every run and the messages between agents, built from the repository.', body, kind='site', topics='team agents schedule')
    li = lambda xs: '<ul>' + ''.join(f'<li>{E(v)}</li>' for v in ([xs] if isinstance(xs, str) else xs)) + '</ul>' if xs else '<p class="small">none stated</p>'
    for c in cards.values():
        a = c['agent']
        brief = f'<a href="../../../admin/briefs/index.html#{E(os.path.basename(c["brief"])[:-3])}">{E(c["brief"])}</a>' if c.get('brief') else 'none yet'
        scope = '<h3>Reads</h3>' + li(c.get('reads', [])) + '<h3>Writes</h3>' + li(c.get('writes', [])) + '<h3>Never</h3>' + li(c.get('never', []))
        wake = '<ol>' + ''.join(f'<li>{E(v)}</li>' for v in c.get('each_wake', [])) + '</ol>'
        body = f'''
<p class="crumb"><a href="../../index.html">The team</a> / <a href="../index.html">Schedule</a> / {E(a)}</p>
<h1>{E(a)}: {E(c["objective"])}</h1>
<div data-live="sched-card" data-agent="{E(a)}"><p class="kv"><b>Status</b> <span class="st st-{SCHED_STATES[c["status"]]}">{E(c["status"])}</span> {E(c.get("status_note", ""))}<br>
<b>Wakes</b> {E(", ".join(c["times"]))} ({E(c["days"])}, {E(c["tz"])}) &middot; <b>model</b> {E(c["model"])}<br>
<b>Runs in</b> {E(c["session"])}<br><b>Brief</b> {brief} &middot; <b>agent behaviour policy</b> {E(c.get("abp") or "none yet")}<br>
<b>Card kept by</b> {E(c["kept_by"])}, updated {E(c["updated"])}</p></div>
{section("day", "Its day", sched_strip(OrderedDict([(a, c)]), 3))}
{section("wake", "Each wake", f'<div data-live="sched-wake" data-agent="{E(a)}">{wake}</div>')}
{section("instructions", "The instructions each wake starts from, word for word", f'<div data-live="sched-instructions" data-agent="{E(a)}"><pre class="msg">{E(c["instructions"])}</pre></div>', "The prompt of the scheduled task that wakes it.")}
{section("scope", "What it reads, writes, and never does", f'<div data-live="sched-scope" data-agent="{E(a)}">{scope}</div>')}
{section("runs", "Every run", f'<div data-live="sched-runs" data-agent="{E(a)}">' + sched_runs_table([r for r in runs if r['agent'] == a], 3, False) + '</div>')}
{section("inbox", "Messages to it", f'<div data-live="sched-inbox" data-agent="{E(a)}">' + sched_msgs([m for m in msgs if m['box'] in (a, 'all')], read) + '</div>')}
{section("outbox", "Messages from it", f'<div data-live="sched-outbox" data-agent="{E(a)}">' + sched_msgs([m for m in msgs if m['from'] == a], read) + '</div>')}
<script src="../../../assets/live/live.js" defer></script>
<script src="../../../assets/live/schedule.js" defer></script>
{section("notes", "Commit notes to it", comms_list([n for n in NOTES if n[3] in (a, 'all')][:60], 3), "Commit-FS-lite: the To-" + E(a) + " and To-all trailers in the release commits; all on <a href='../../comms/index.html'>commit notes</a>.")}
'''
        page(f'team/schedule/{a}/index.html', f'Schedule: {a}', f'{a}: {c["objective"]} When it wakes, its instructions, every run and its messages.', body, kind='site', topics='team agents schedule')

# ----------------------------------------------------------------------------- the journalist's desk (/views/desk/)
# The cycle every evidence export goes through, the full pass and where it stands, the pass ledger (data/desk.json),
# and a staleness report computed from the pages this build has just written: every dated 'as of' older than the
# latest capture, every hand-kept file not checked against the current vault head, every vault claim not reviewed.

_MONTHS = {m: i + 1 for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])}
_ASOF = re.compile(r'\b[Aa]s of (?:the (?:morning|afternoon|evening|end) of )?(?:(\d{1,2}):(\d{2}) UTC on )?(\d{1,2}) (October|November)(?: 2026)?(?:, (\d{1,2}):(\d{2}) UTC)?'
                   r'|\b[Aa]s of (2026)-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?')

def _asof_key(m):
    """A matched 'as of' phrase as a sortable (month, day, minutes or None)."""
    if m.group(3):
        hh, mm = (m.group(1), m.group(2)) if m.group(1) else (m.group(5), m.group(6))
        return (_MONTHS[m.group(4)], int(m.group(3)), int(hh) * 60 + int(mm) if hh else None)
    return (int(m.group(8)), int(m.group(9)), int(m.group(10)) * 60 + int(m.group(11)) if m.group(10) else None)

def staleness():
    """What is older than the latest capture, from the markdown twins this build wrote. Deterministic: pages, then phrases, in order."""
    dk = D['desk']
    a = STORY['data_as_of']
    latest = (int(a[5:7]), int(a[8:10]), int(a[11:13]) * 60 + int(a[14:16]))
    accepted = {(x['page'], x['phrase']) for x in dk['accepted']}
    pages = []
    for p, t, _, _ in PAGES:
        if p.startswith(tuple(dk['kept_as_written'])) or not os.path.exists(os.path.join(ROOT, md_path(p))):
            continue
        md = open(os.path.join(ROOT, md_path(p)), encoding='utf-8').read().split('\n\n---\nsite v')[0]
        hits = []
        for m in _ASOF.finditer(md):
            k = _asof_key(m)
            old = (k[0], k[1]) < latest[:2] or (k[:2] == latest[:2] and k[2] is not None and k[2] < latest[2])
            if old and (p, m.group(0)) not in accepted and ('*', m.group(0)) not in accepted and m.group(0) not in hits:
                hits.append(m.group(0))
        if hits:
            pages.append((p, t, hits))
    head = D['vault']['head']['commit']
    files = [f for f in dk['files'] if f.get('checked_against') != head]
    site_ids = {c['id'] for c in D['claims']}
    reviewed = {r['id'] for r in D['claim-review']['reviews']}
    unreviewed = [c for c in D['vault-claims'] if c['id'] not in site_ids and c['id'] not in reviewed]
    return pages, files, unreviewed

def build_desk():
    dk = D['desk']
    path = 'views/desk/index.html'
    head = D['vault']['head']['commit']
    pages, files, unreviewed = staleness()
    n_phr = sum(len(h) for _, _, h in pages)
    settled = not (pages or files or unreviewed)
    cyc = ''.join(f'<li class="dk-step"><b>{E(c["label"])}</b><span class="dk-who">{E(c["who"])}</span><span>{E(c["what"])}</span></li>' for c in dk['cycle'])
    cycle_fig = f'<figure class="dk-fig"><ol class="dk-cycle">{cyc}</ol><figcaption>Each export, in order, from the researcher to the correspondent; the semantic graphs only after the correspondent. The last step is reached when the report at the foot of this page is empty; the next curator wake starts again.</figcaption></figure>'
    pas = ''.join(f'<li class="dk-pass dk-{E(s["status"].replace(" ", "-"))}"><span class="dk-n">{s["n"]}</span><b>{E(s["title"])}</b><span class="dk-st">{E(s["status"])}{(", v" + E(s["release"])) if s.get("release") else ""}</span><span>{E(s["what"])}</span></li>' for s in dk['pass'])
    pass_fig = f'<figure class="dk-fig"><ol class="dk-seq">{pas}</ol><figcaption>One step per release, in this order, so that no release carries the whole pass.</figcaption></figure>'
    frows = [[f'<code>{E(f["path"])}</code>', E(f['kept_by_before']), (f'<code>{E(f["checked_against"])}</code>' + (' <span class="st st-confirmed">current</span>' if f['checked_against'] == head else ' <span class="st st-disputed">older head</span>')) if f.get('checked_against') else '<span class="st st-unverified">not yet</span>', E(f.get('note') or '')] for f in dk['files']]
    prows = [[f'<a href="../../{E(p)}">{E(t)}</a><div class="small"><code>{E(p)}</code></div>', '<br>'.join(f'<q>{E(h)}</q>' for h in hs)] for p, t, hs in pages]
    report = (f'<p class="lead">{"<b>Settled.</b> Nothing on the site is older than the latest capture." if settled else f"<b>Not settled yet.</b> {len(pages)} pages carry {n_phr} dated phrases older than the latest capture ({E(human_time(STORY['data_as_of']))}); {len(files)} of {len(dk['files'])} hand-kept files have not been checked against the current head <code>{E(head)}</code>; {len(unreviewed)} vault claims are not yet reviewed."}</p>'
              + section('r-files', f'The pass ledger: hand-kept files ({len(dk["files"]) - len(files)} of {len(dk["files"])} checked against the current head)', table(['File', 'Kept before 24 October by', 'Last checked against', 'Note'], frows, 'dk-t'))
              + section('r-pages', f'Dated phrases older than the latest capture ({n_phr} on {len(pages)} pages)', (table(['Page', 'Phrases'], prows, 'dk-t') if prows else '<p>None.</p>') + f'<p class="small">Pages kept as written by design are not scanned: {E(", ".join(dk["kept_as_written"]))}. {E(dk["kept_as_written_why"])} A phrase that is a source\'s own date, rightly kept, is accepted in <code>data/desk.json</code> and leaves the report.</p>')
              + section('r-catches', f'What the correspondent caught ({len(dk.get("catches", []))})', (table(['When', 'What', 'File', 'Kind', 'Journalist run', 'Fixed in'], [[E(c.get('on', '')), E(c.get('what', '')), f'<code>{E(c.get("file", ""))}</code>', E(c.get('kind', '')), E(c.get('journalist_run', '')), E(c.get('fixed_in', ''))] for c in dk.get('catches', [])], 'dk-t') if dk.get('catches') else '<p>None yet: the scheduled journalist has not shipped a run for the correspondent to review.</p>') + f'<p class="small">{E(dk.get("catches_about", ""))}</p>')
              + section('r-claims', f'Vault claims not yet reviewed ({len(unreviewed)})', f'<p>Listed with their sources on <a href="../../claims/review/index.html#g-not-yet-reviewed">the claims waiting for review</a>.</p>'))
    body = f'''
<h1>The journalist's desk: keeping the site current</h1>
<p class="lead">After every export of the evidence vault, the journalist publishes it and the correspondent reviews what went live, so that the site says what the evidence now says. This page is that work in the open: the pipeline each export goes through, the full pass and where it stands, and a report, computed at every build, of what is still older than the evidence. The editor's decision ({E(dk["decided"]["on"])}): {E(dk["decided"]["says"])}.</p>
{section("cycle", "The pipeline, after every export", cycle_fig)}
{section("pass", "The full pass, step by step", pass_fig + '<p>The plan in full is <a href="../../admin/briefs/index.html">among the briefs</a>, as written on 24 October.</p>')}
{section("report", "What is still stale", report)}
<p class="small">Computed from <a href="../../data/desk.json">data/desk.json</a>, the pages of this build and the vault's claims, at vault head <code>{E(head)}</code>.</p>
'''
    page(path, "The journalist's desk: keeping the site current", f'The cycle every evidence export goes through, the journalist\'s full pass over the site and where it stands, and what is still older than the latest capture: {"settled" if settled else f"{n_phr} dated phrases on {len(pages)} pages, {len(files)} files, {len(unreviewed)} claims"}.', body, kind='site', topics='php2shell method freshness')

# ----------------------------------------------------------------------------- elsewhere: Pulse, a separate section
# Pulse is pulse@newsroom's vault for the SGit newsroom: exploitation evidence beside attention, for 26 vulnerabilities
# of which php2shell is two. It is kept apart from the PHP pages on purpose (the editor, 24 October 2026): its own
# folder (/pulse/), its own data file (data/pulse.json, written only by admin/build/export_pulse.py), its own code below,
# and one pointer from the PHP site ('What else is going on'). Nothing here reads the PHP data, and nothing in the PHP
# pages reads data/pulse.json, so the section can move to another site by taking this block, the exporter and the file.

PULSE = load('pulse') if os.path.exists(os.path.join(DATA, 'pulse.json')) else None

def _pulse_slug(cve):
    return cve.lower()

def _pulse_when(t):
    """20261023T131240Z as 23 October 2026, 13:12 UTC; a date stays a date."""
    m = re.match(r'^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})', t or '')
    return human_time(f'{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}Z') if m else (t or '')

def _pulse_short(d):
    """2026-10-21 as 21 Oct; a date in another year as Apr 2015."""
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', d or '')
    if not m:
        return d or ''
    mon = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()[int(m.group(2)) - 1]
    return f'{int(m.group(3))} {mon}' if m.group(1) == STORY['data_as_of'][:4] else f'{mon} {m.group(1)}'

def _pulse_cap(c, depth):
    if not c:
        return ''
    where = f'{E(c.get("vault") or "")}: <code>{E(c.get("path") or "")}</code>'
    link = f' <a href="{E(U(c["url"]))}" rel="noopener nofollow">original</a>' if c.get('url') else ''
    return f'<div class="small">capture {where}, {E(_pulse_when(c.get("captured")))}, sha256 <code>{E((c.get("sha256") or "")[:16])}</code>{link}</div>'

def _pulse_quote(e, depth):
    q = f'<blockquote class="tp"><span class="small">third-party text, as Pulse recorded it</span><br>{E(e["quote"])}</blockquote>' if e.get('quote') else ''
    basis = f'<div>{E(e["basis"])}</div>' if e.get('basis') else ''
    what = f'<div class="note">Pulse: {E(e["what_it_is"])}</div>' if e.get('what_it_is') else ''
    meta = ', '.join(E(x) for x in (e.get('status'), e.get('date')) if x)
    return f'<li><b>{E(e.get("by") or "Pulse\'s own check")}</b> <span class="small">{meta}</span>{q}{basis}{what}{_pulse_cap(e.get("capture"), depth)}</li>'

def build_pulse():
    if not PULSE:
        return
    P, rn = PULSE, PULSE['rungs']
    head = f'Pulse vault <code>{E(P["vault_id"])}</code>, head <code>{E(P["head"]["commit"])}</code>, last pass {E(_pulse_when(P["last_run"]))}'
    caveats = '''<ul>
<li><b>This is not this site's evidence.</b> Pulse is another agent's vault, for the SGit newsroom, and covers more than PHP. Its captures are its own and the source watch's; this site has not re-read them. What is shown is what Pulse recorded, with the capture each entry comes from.</li>
<li><b>The attention counts cannot be compared row with row.</b> Each count is over the feeds Pulse had checked for that vulnerability, from 2 to 55; the number checked is shown beside it.</li>
<li><b>Rung 1 is a report or a listing of a proof of concept, not a working exploit.</b> Pulse never fetches exploit code. For php2shell, the PHP pages of this site record that none of the public proofs of concept reviewed by VulnCheck has the correct mechanism.</li>
<li><b>No score and no ranking.</b> Pulse keeps evidence and attention side by side and never combines them; neither does this page. The rows are in CVE order.</li>
</ul>'''
    hdr = ''.join(f'<th title="{E(rn[k])}">{k}</th>' for k in sorted(rn, key=int))
    trs = []
    for v in P['vulns']:
        cells = ''.join(f'<td class="pr {"pr-yes" if r["status"] == "reached" else ("pr-nc" if r["status"] == "not checked" else "pr-no")}" title="{E(r["rung"])}: {E(r["status"] or "")}{(" " + E(r["date"])) if r.get("date") else ""}">{E(_pulse_short(r.get("date")) if r.get("date") else ("yes" if r["status"] == "reached" else ("?" if r["status"] == "not checked" else "")))}</td>' for r in v['rungs'])
        a = v['attention']
        trs.append(f'<tr><td><a href="{E(_pulse_slug(v["cve"]))}/index.html"><b>{E(v["cve"])}</b></a><div class="small">{E(v["vendor"] or "")} {E(v["product"] or "")}{" &middot; " + E(v["brand_name"]) if v.get("brand_name") else ""}{" &middot; old flaw, newly listed" if v["old_flaw_newly_listed"] else ""}</div></td>{cells}<td>{E(str(a.get("news_items")))} <span class="small">over {E(str(a.get("feeds_checked")))} feeds</span></td></tr>')
    legend = ''.join(f'<li><b>{E(k)}</b> {E(rn[k])}</li>' for k in sorted(rn, key=int))
    body = f'''
<h1>What else is going on: Pulse</h1>
<p class="lead">A separate section, not about PHP. Pulse is the SGit newsroom's record of {len(P["vulns"])} vulnerabilities in the news this month, php2shell among them: for each, the evidence that it is being exploited, as a ladder of eight dated rungs, and, beside it, how much attention it gets. It is kept apart from the rest of this site and may move to a site of its own.</p>
<p class="small">{head}. Exported by <code>admin/build/export_pulse.py</code> into <a href="../data/pulse.json">data/pulse.json</a>; no capture is copied. Pulse says of itself: {E(P["pulse_says"])}</p>
{section("read", "Before you read the table", caveats)}
{section("ladder", "Evidence and attention, side by side", f'<ol class="legend">{legend}</ol><div class="tw"><table class="t pulse"><thead><tr><th>Vulnerability</th>{hdr}<th>News items</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div><p class="small">A cell shows the day a rung was reached, or "yes" when Pulse records it reached without a date; "?" is a rung Pulse has not been able to check (no open capture shows it either way); an empty cell is not reached at the last check.</p>')}
'''
    page('pulse/index.html', 'What else is going on: Pulse, exploited vs. talked about', f'A separate section: the SGit newsroom\'s Pulse vault, {len(P["vulns"])} vulnerabilities with their evidence of exploitation as eight dated rungs beside the attention each gets. Not this site\'s evidence; no score, no ranking.', body, kind='evidence', topics='vulnerabilities exploitation attention pulse')
    for v in P['vulns']:
        path = f'pulse/{_pulse_slug(v["cve"])}/index.html'
        rows = []
        for r in v['rungs']:
            ev = ''.join(_pulse_quote(e, 2) for e in r['evidence'])
            rne = ''.join(_pulse_quote(e, 2) for e in r['reported_not_established'])
            chk = f'<div class="small">last checked {E(_pulse_when(r["last_checked"]))}</div>' if r.get('last_checked') else ''
            rows.append(f'<section id="rung-{r["n"]}"><h3>{r["n"]}. {E(r["rung"])}: <span class="st {"st-confirmed" if r["status"] == "reached" else "st-other"}">{E(r["status"] or "")}</span>{(" " + E(r["date"])) if r.get("date") else ""}</h3>{chk}'
                        + (f'<p class="note">{E(r["note"])}</p>' if r.get('note') else '')
                        + (f'<ul class="pev">{ev}</ul>' if ev else '')
                        + (f'<p><b>Reported, not established</b></p><ul class="pev">{rne}</ul>' if rne else '') + '</section>')
        a = v['attention']
        meas = ''.join(f'<li>CVSS {E(c["version"] or "")} {E(str(c["base_score"]))}, scored by {E(c["source"] or "")}</li>' for c in v['cvss'])
        if v.get('epss'):
            meas += f'<li>EPSS {E(str(v["epss"]["score"]))}, percentile {E(str(v["epss"]["percentile"]))}, {E(v["epss"]["date"] or "")}</li>'
        att = (f'<p>{E(str(a.get("news_items")))} news items since {E(_pulse_when(a.get("window_since")) or "the window start")}, counted over {E(str(a.get("feeds_checked")))} of {E(str(a.get("news_feeds_total")))} feeds, '
               f'in {E(str(a.get("languages")))} languages and {E(str(a.get("countries")))} countries; {E(str(a.get("front_pages")))} front pages, {E(str(a.get("agency_alerts")))} agency alerts, {E(str(a.get("offline_advice")))} pages advising taking systems offline.</p>'
               + (f'<p class="small">Pulse: {E(a["about"])}</p>' if a.get('about') else ''))
        php = '<p>For php2shell, this site\'s own evidence and analysis are in <a href="../../index.html">the PHP pages</a>; this page shows only what Pulse recorded.</p>' if v.get('brand_name') == 'php2shell' else ''
        body = f'''
<h1>{E(v["cve"])}: {E(v["vendor"] or "")} {E(v["product"] or "")}</h1>
<p class="lead">{E(v["flaw"] or "")}. {E(v["kind_of_system"] or "")}. Rungs reached: {E(", ".join(str(n) for n in v["rungs_reached"]) or "none")} of 8. Part of <a href="../index.html">Pulse</a>, a separate section not about PHP.</p>
{php}
{('<p class="small">Why Pulse tracks it: ' + E(v["why_tracked"]) + '</p>') if v.get("why_tracked") else ''}
{section("ladder", "The evidence of exploitation, rung by rung", "".join(rows))}
{section("measures", "Measurements", f"<ul>{meas}</ul>" if meas else "<p>None recorded.</p>")}
{section("attention", "The attention it gets", att)}
<p class="small">{head}.</p>
'''
        page(path, f'{v["cve"]} in Pulse: {v["vendor"]} {v["product"]}', f'Pulse\'s record of {v["cve"]} ({v["vendor"]} {v["product"]}): the evidence of exploitation as eight rungs, each with the capture it rests on, and the attention it gets. A separate section, not this site\'s evidence.', body, kind='evidence', topics='vulnerabilities exploitation pulse')
# ----------------------------------------------------------------------------- the story graph (ontologist@php.newsroom)
# Brief: admin/content/briefs/2026-10-24__brief__the-ontologist.md (first: 2026-10-22__brief__the-cartographer-joins.md). One graph, data/graph.json, built from every
# row the pages are built from, joined through data/entities.json and data/attribution.json under the verbs of
# data/ontology.json. The build stops on a verb or kind the ontology does not list, a publisher no entity claims, an
# attribution to an unknown entity, or an exploitation row whose 'who' moved: the graph cannot drift from its grammar.

ONT, ENT, ATT = load('ontology'), load('entities'), load('attribution')
ENTITIES = OrderedDict((e['id'], e) for e in ENT['entities'])
ALIAS = {a: e['id'] for e in ENT['entities'] for a in e.get('aliases', [])}
UNMAPPED_PUBLISHERS = {}  # publisher -> source slugs, for the ontologist; filled by the graph build
SG_GRAPH_JS = 'assets/components/sg-graph/v1/v1.0/v1.0.0/sg-graph.js'
SG_GRAPH_FILES = ['sg-graph.js', 'sg-graph-core.js', 'sg-graph.tpl', 'sg-graph.css']

def sg_graph(path, src=None, data=None, focus=None, view=None, depth=None, height=None, max_nodes=None, verbs=None, controls=None, fallback=''):
    """Embed <sg-graph> on the page at path: the one way every page on this site draws a graph. src is a JSON file
    relative to the site root; data is a graph to inline instead. fallback is the HTML shown without JavaScript (a linked
    list of the same nodes), which is also what the page's markdown twin carries."""
    up = '../' * path.count('/')
    attrs = [('src', up + src if src else None), ('base', up), ('focus', focus), ('view', view), ('depth', depth),
             ('height', height), ('max', max_nodes), ('verbs', ','.join(verbs) if verbs else None), ('controls', controls)]
    a = ''.join(f' {k}="{U(v) if k in ("src", "base") else E(str(v))}"' for k, v in attrs if v not in (None, ''))
    inner = fallback + (f'<script type="application/json">{J(data, sort_keys=True)}</script>' if data is not None else '')
    return f'<sg-graph{a}>{inner}</sg-graph><script type="module" src="{up}{SG_GRAPH_JS}"></script>'

def entity_root(eid):
    """Fold a party into the voice it speaks with: a person into their employer, a part into its whole, a member into a
    group that speaks with one voice. Independence is counted between roots."""
    seen = set()
    while eid not in seen:
        seen.add(eid)
        e = ENTITIES[eid]
        nxt = e.get('works_for') or e.get('part_of') or (e.get('member_of') if ENTITIES.get(e.get('member_of'), {}).get('one_voice') else None)
        if not nxt: break
        eid = nxt
    return eid

def party_href(eid):
    return f'actors/{eid}/index.html' if ENTITIES[eid].get('actor') else f'graph/parties/index.html#p-{eid}'

def check_grammar():
    """The ontology keeps its own rules: every verb has an inverse that is not itself, no banned verb is listed, and a
    scope never reuses a verb of the story graph's with another meaning."""
    banned = {b['verb'] for b in ONT['banned']}
    seen = {}
    for scope, vs in [('story', ONT['edges'])] + [(k, sc['edges']) for k, sc in ONT['scopes'].items()]:
        for v in vs:
            if not v.get('verb') or not v.get('inverse') or v['verb'] == v['inverse']:
                sys.exit(f'data/ontology.json: {scope} verb {v.get("verb")!r} needs an inverse that is not itself')
            if v['verb'] in banned: sys.exit(f'data/ontology.json: {v["verb"]!r} is both listed and banned')
            # 'contained in' and 'contained_in' are one spelling (board 189 asks for one); two different words are two meanings
            key, inv = v['verb'].replace(' ', '_'), v['inverse'].replace(' ', '_')
            if key in seen and seen[key] != inv:
                sys.exit(f'data/ontology.json: {v["verb"]!r} has two inverses, in two scopes')
            seen[key] = inv

def story_graph():
    check_grammar()
    kinds = {t['id'] for t in ONT['node_types']}
    verbs = {v['verb']: v for v in ONT['edges']}
    nodes, edges = OrderedDict(), OrderedDict()

    def node(nid, kind, label, **kw):
        if kind not in kinds: sys.exit(f'graph: node kind {kind!r} is not in data/ontology.json')
        if nid in nodes:
            # the same id twice must be the same thing (a topic met again), never two rows folded into one
            if (nodes[nid]['kind'], nodes[nid]['label']) != (kind, label): sys.exit(f'graph: two different nodes would share the id {nid!r}')
            return nid
        nodes[nid] = dict({'id': nid, 'kind': kind, 'label': label}, **{k: v for k, v in kw.items() if v not in (None, '', [])})
        return nid

    def edge(a, verb, b, **kw):
        if verb not in verbs: sys.exit(f'graph: verb {verb!r} is not in data/ontology.json')
        # an end that does not exist is drift in the data: stop, never drop the edge quietly
        for end in (a, b):
            if end not in nodes: sys.exit(f'graph: {a} {verb} {b}: there is no node {end!r}')
        if a != b:
            edges.setdefault((a, verb, b), dict({'from': a, 'verb': verb, 'to': b}, **kw))

    for eid, e in ENTITIES.items():
        node('party:' + eid, 'party', e['name'], **{'class': e['kind'], 'country': e.get('country'), 'href': party_href(eid)})
    for eid, e in ENTITIES.items():
        for key, verb in (('part_of', 'part_of'), ('member_of', 'member_of'), ('works_for', 'works_for')):
            if e.get(key):
                if e[key] not in ENTITIES: sys.exit(f'data/entities.json: {eid} {key} unknown {e[key]!r}')
                edge('party:' + eid, verb, 'party:' + e[key])
        for m in e.get('has_members', []):
            if m not in ENTITIES: sys.exit(f'data/entities.json: {eid} has_members unknown {m!r}')
            edge('party:' + m, 'member_of', 'party:' + eid)

    for slug, s in SOURCES.items():
        # a publisher no entity claims yet does not stop the build: the journalist publishes each export as it comes, and
        # the ontologist maps new publishers after the correspondent's run (the editor, 24 October 2026). The source is
        # in the graph without its published_by edge, and the publisher is listed in data/graph.json 'unmapped_publishers'.
        if s['publisher'] not in ALIAS:
            UNMAPPED_PUBLISHERS.setdefault(s['publisher'], set()).add(slug)
        node('source:' + slug, 'source', f'{short_name(s)}: {s.get("title") or slug}', href=f'sources/{slug}/index.html',
             url=s['url'], primary=bool(s.get('primary')), published=s.get('published'), source_kind=s.get('kind'))
        if s['publisher'] in ALIAS:
            edge('source:' + slug, 'published_by', 'party:' + ALIAS[s['publisher']])
        syn = ATT.get('sources', {}).get(slug)
        if syn:
            if syn['syndicates'] not in ENTITIES: sys.exit(f'data/attribution.json: source {slug} syndicates unknown entity {syn["syndicates"]!r}')
            edge('source:' + slug, 'syndicates', 'party:' + syn['syndicates'], basis=syn['basis'])
        for c in s['captures']:
            cid = node(f'capture:{slug}/{c["stamp"]}', 'capture', f'{short_name(s)}, captured {c["stamp"]}', href=f'sources/{slug}/index.html',
                       http_status=c.get('status'), files=[{'name': fn, 'sha256': f['sha256']} for fn, f in sorted(c['files'].items())])
            edge('source:' + slug, 'captured_in', cid)

    for cve in sorted({m.group(0) for row in D['claims'] + D['numbers'] + D['timeline'] for m in CVE_RX.finditer(json.dumps(row, ensure_ascii=False))}):
        node('cve:' + cve, 'cve', cve + (f', {FLAGSHIP[cve]}' if cve in FLAGSHIP else ''),
             href=f'flaws/index.html#{cve}' if cve in FLAGSHIP else f'https://www.cve.org/CVERecord?id={cve}')

    def names(nid, row):
        for cve in sorted({m.group(0) for m in CVE_RX.finditer(json.dumps(row, ensure_ascii=False))}):
            edge(nid, 'names', 'cve:' + cve)

    def stated(nid, row, att, where):
        if not att: sys.exit(f'data/attribution.json: no attribution for {where}')
        for eid in att['states']:
            if eid not in ENTITIES: sys.exit(f'data/attribution.json: {where} names unknown entity {eid!r}')
            edge('party:' + eid, 'states', nid)
        if att.get('counts'): edge('party:this-site', 'counts', nid)
        for eid in att.get('relays', []):
            if eid not in ENTITIES: sys.exit(f'data/attribution.json: {where} relayed by unknown entity {eid!r}')
            edge('party:' + eid, 'relays', nid, basis='attribution')
        # a cited source is evidence: it may support or contradict, so citing it makes no one a relay
        for s in row['sources']:
            if s in SOURCES: edge(nid, 'cites', 'source:' + s)

    open_k = {}
    for k in load('factcheck')['contradictions']:
        for c in k['claims']: open_k.setdefault(c, []).append(k)
    for c in D['claims']:
        att = ATT['claims'].get(c['id'])
        origins = sorted({entity_root(e) for e in (att or {'states': []})['states'] if e != 'unnamed'})
        nid = node('claim:' + c['id'], 'claim', c['claim'], status=c['status'], href=f'facts/{c["id"]}/index.html', by=c['by'])
        stated(nid, c, att, 'claim ' + c['id'])
        node('topic:' + c['topic'], 'topic', c['topic'], href=f'claims/index.html#t-{c["topic"]}')
        edge(nid, 'classified_as', 'topic:' + c['topic'])
        names(nid, c)
        nodes[nid].update({'origins': len(origins),
                           'tension': ', '.join(k['id'] for k in open_k.get(c['id'], []) if k['status'] == 'open') or None})
        if not nodes[nid]['tension']: del nodes[nid]['tension']
    for n in D['numbers']:
        nid = node('number:' + n['id'], 'number', f'{n["value"]} {n["of"]}', status=n['status'], href=f'numbers/index.html#{n["id"]}', by=n['who'], measures=n.get('measures'))
        stated(nid, n, ATT['numbers'].get(n['id']), 'number ' + n['id'])
        names(nid, n)
    for t in D['timeline']:
        nid = node('event:' + event_id(t), 'event', f'{fmt_at(t["at"])}: {t["event"]}', at=t['at'], confidence=t.get('confidence'),
                   href=f'timeline/index.html#ph-{t["phase"]}' if t.get('phase') else 'timeline/index.html')
        for s in t['sources']:
            if s in SOURCES: edge(nid, 'cites', 'source:' + s)
        if t.get('phase'):
            node('phase:' + t['phase'], 'phase', t['phase'], href=f'timeline/index.html#ph-{t["phase"]}')
            edge(nid, 'classified_as', 'phase:' + t['phase'])
        names(nid, t)
    classes = next(x for x in ONT['taxonomy'] if x['id'] == 'signal-class')['maps']
    if len(ATT['exploitation']) != len(D['exploitation']): sys.exit('data/attribution.json: exploitation rows differ in number from data/exploitation.json')
    for i, (x, att) in enumerate(zip(D['exploitation'], ATT['exploitation'])):
        if att['who'] != x['who']: sys.exit(f'data/attribution.json: exploitation row {i} is {x["who"]!r}, attributed as {att["who"]!r}')
        if x['kind'] not in classes: sys.exit(f'data/ontology.json: exploitation kind {x["kind"]!r} is not in the signal-class map')
        # an id from the row's content, so a row added above does not renumber the rest
        nid = node('signal:' + hashlib.sha256(f'{x["when"]}|{x["who"]}|{x["what"]}'.encode()).hexdigest()[:10], 'signal', f'{x["who"]}: {x["what"]}', status=x['status'], href='exploitation/index.html', when=x['when'], signal_class=classes[x['kind']])
        stated(nid, x, att, f'exploitation row {i}')
    for a in D['agencies']:
        eid = ATT['agencies'].get(a['agency'] + '|' + a['country'])
        if not eid: sys.exit(f'data/attribution.json: agency {a["agency"]}|{a["country"]} not mapped')
        nid = node('advice:' + eid, 'advice', f'{a["agency"]} ({a["country"]}): take offline? {a["offline"]}', href='agencies/index.html',
                   offline=a['offline'], says=a.get('offline_text'), exploitation=a.get('exploitation'))
        edge('party:' + eid, 'advises', nid)
        for s in a['sources']:
            if s in SOURCES: edge(nid, 'cites', 'source:' + s)
    for k in load('factcheck')['contradictions']:
        kid = node('contradiction:' + k['id'], 'contradiction', f'{k["id"]}: {k["measure"]}', status=k['status'], href=f'factcheck/index.html#{k["id"]}')
        for c in k['claims']:
            if 'claim:' + c not in nodes: sys.exit(f'factcheck contradiction {k["id"]} names unknown claim {c!r}')
            edge(kid, 'flags', 'claim:' + c)
    for a in load('factcheck')['assessments']:
        for ch in a.get('checked', []):
            m = re.match(r'sources/([^/]+)/captures/([^/]+)/', ch.get('file') or '')
            # a capture outside the manifest is the desk's outside evidence: recorded, never cited
            if m and ch.get('result') == 'carries' and m.group(1) in SOURCES:
                cap = f'capture:{m.group(1)}/{m.group(2)}'
                if 'claim:' + a['id'] not in nodes: sys.exit(f'data/factcheck.json: an assessment names unknown claim {a["id"]!r}')
                if cap not in nodes: sys.exit(f'data/factcheck.json: {a["id"]} was checked against {cap[8:]}, which data/sources.json no longer has')
                edge('claim:' + a['id'], 'appears_in', cap, file=ch['file'].split('/')[-1], sha256=ch.get('sha256'))
                # 'carries' means the capture bears on the claim: an agency carrying it is an original in its own right,
                # and a primary record can carry the fact that refutes it. Only an outlet carrying another party's
                # statement, on a claim not refuted, has passed it on.
                pub = ALIAS.get(SOURCES[m.group(1)]['publisher'])
                if pub is None:
                    continue  # an unmapped publisher: no relays edge until the ontologist maps it
                origins = {entity_root(e) for e in ATT['claims'][a['id']]['states']}
                if ENTITIES[pub]['kind'] == 'outlet' and a.get('verdict') != 'refuted' and entity_root(pub) not in origins and 'this-site' not in origins:
                    edge('party:' + pub, 'relays', 'claim:' + a['id'], basis='capture carries it', capture=f'{m.group(1)}/{m.group(2)}')
    for c in D['claims']:
        nid = 'claim:' + c['id']
        relays = len({a for (a, v, b) in edges if b == nid and v == 'relays'})
        nodes[nid]['relays'] = relays
        nodes[nid]['echo'] = relays >= 3 and nodes[nid]['origins'] <= 1

    bridge(nodes)
    used = {e['from'] for e in edges.values()} | {e['to'] for e in edges.values()}
    out_nodes = [n for n in nodes.values() if n['id'] in used]
    unlinked = [n['id'] for n in nodes.values() if n['id'] not in used]
    def say(v): return v.replace('_', ' ')
    ontology = {'id': ONT['id'], 'version': ONT['version'],
                'kinds': OrderedDict((t['id'], {'label': t['label'], 'plural': t['plural'], 'altitude': t['altitude']}) for t in ONT['node_types']),
                'verbs': OrderedDict([(v['verb'], {'label': say(v['verb']), 'inverse': say(v['inverse']), 'origin': v['origin']}) for v in ONT['edges']])}
    # a scope's verbs are added for the graphs a reader zooms into, phrased, and never over the story graph's own
    for name, sc in ONT['scopes'].items():
        for v in sc['edges']:
            ontology['verbs'].setdefault(v['verb'], {'label': say(v['verb']), 'inverse': say(v['inverse']), 'origin': name})
    return {'site': SITE, 'version': VERSION, 'vault_commit': D['vault']['head']['commit'], 'title': 'The story graph',
            'note': 'A node means what its edges say about it. Every edge is a verb from data/ontology.json with a named inverse; there is no generic association edge. Parties are resolved through data/entities.json and data/attribution.json; relays are derived, so many outlets passing on one statement count as one origin.',
            'ontology': ontology, 'nodes': out_nodes, 'edges': list(edges.values()),
            'unlinked': unlinked}

def bridge(nodes):
    """data/crosswalk.json: give each story node that another graph also names a 'zoom' list, the graphs a reader can step
    into from it. Every id is checked against its graph's own source, so a renamed node stops the build, not a reader."""
    X = load('crosswalk')
    review = {n['id']: n for n in D['review']['nodes']}
    stake = {s['id']: s['name'] for s in load('grc')['stakeholders']}
    def known(graph, gid):
        if graph == 'story': return gid in nodes
        if graph == 'review': return gid in review
        kind, _, rest = gid.partition(':')
        if kind == 'stakeholder': return rest in stake
        return kind in ('vulnerability', 'remediation', 'code') and rest in review
    def zoom(nid, graph, gid, label):
        if not known(graph, gid): sys.exit(f'data/crosswalk.json: {graph} has no node {gid!r}')
        if nid in nodes: nodes[nid].setdefault('zoom', []).append({'graph': X['graphs'][graph]['file'], 'focus': gid, 'label': label})
    for a in X['anchors']:
        sid = a['ids']['story']
        if not known('story', sid): sys.exit(f'data/crosswalk.json: the story graph has no node {sid!r}')
        for g in ('review', 'grc'):
            if g in a['ids']: zoom(sid, g, a['ids'][g], f'{a["anchor"]} in {X["graphs"][g]["title"]}')
    # a source that is a Wikipedia article opens that article's graph; a source a reference is captured as opens it on that reference
    for wslug in wiki_articles():
        w = wiki_load(wslug)
        for sid in nodes:
            if sid.startswith('source:') and norm_url(SOURCES[sid[7:]]['url']) == norm_url(w['art']['url']):
                nodes[sid].setdefault('zoom', []).append({'graph': f'data/wikipedia/{wslug}/graph.json', 'focus': 'article:' + wslug, 'label': f'Inside the article: {w["art"]["title"]} as a graph'})
        for r in w['X']['references']:
            if r['captured'] and 'source:' + r['captured'] in nodes:
                nodes['source:' + r['captured']].setdefault('zoom', []).append({'graph': f'data/wikipedia/{wslug}/graph.json', 'focus': f'reference:{r["n"]}', 'label': f'In Wikipedia\'s {w["art"]["title"]} article: ' + (f'cited by {len(r["cited_by"])} statement{"s" if len(r["cited_by"]) != 1 else ""}' if r['cited_by'] else 'cited in the infobox')})
    for pid, b in sorted(X['parties'].items()):
        if pid not in ENTITIES: sys.exit(f'data/crosswalk.json: unknown party {pid!r}')
        name = stake.get(b['grc'].partition(':')[2], b['grc'])
        zoom('party:' + pid, 'grc', b['grc'], f'In {X["graphs"]["grc"]["title"]}' + (': ' if b['relation'] == 'is' else ', among: ') + name)

def graph_census(G):
    kinds = Counter(n['kind'] for n in G['nodes'])
    verbs = Counter(e['verb'] for e in G['edges'])
    return kinds, verbs

def build_graph():
    G = story_graph()
    G['unmapped_publishers'] = {p: sorted(v) for p, v in sorted(UNMAPPED_PUBLISHERS.items())}  # for the ontologist's run
    write('data/graph.json', json.dumps(G, indent=1, ensure_ascii=False) + '\n')
    kinds, verbs = graph_census(G)
    K = G['ontology']['kinds']
    claims = [n for n in G['nodes'] if n['kind'] == 'claim']
    by_kind = ', '.join(f'{n} {K[k]["plural"] if n != 1 else K[k]["label"].lower()}' for k, n in kinds.most_common())
    fallback = ('<div class="graph-fallback"><p>The interactive graph needs JavaScript. Every node is also on a page: '
                + ', '.join(f'<a href="../{h}">{E(t)}</a>' for h, t in (('claims/index.html', 'the claims'), ('sources/index.html', 'the sources'),
                            ('graph/parties/index.html', 'the parties'), ('timeline/index.html', 'the timeline'), ('factcheck/index.html', 'the tensions')))
                + '; the whole graph is <a href="../data/graph.json">data/graph.json</a>.</p></div>')
    widget = sg_graph('graph/index.html', src='data/graph.json', focus='claim:scale-70pc-internet', fallback=fallback)
    vrows = []
    for v in ONT['edges']:
        n = verbs.get(v['verb'], 0)
        origin = f'inherited from {E(v.get("from", ""))}' if v['origin'] == 'inherited' else 'proposed here'
        vrows.append([f'<code>{E(v["verb"])}</code>', f'<code>{E(v["inverse"])}</code>', E(v['reads'].replace('{s}', 'A').replace('{t}', 'B')), E(str(n)), origin])
    verbs_t = table(['Verb', 'Inverse', 'Reads', 'Edges', 'Where it comes from'], vrows)
    kinds_t = table(['Kind', 'Altitude', 'Nodes', 'What it is'], [[E(t['label']), E(t['altitude']), E(str(kinds.get(t['id'], 0))), E(t['definition'])] for t in ONT['node_types']])
    banned = ''.join(f'<li><code>{E(b["verb"])}</code>: {E(b["why"])}</li>' for b in ONT['banned'])
    spectrum = sorted(claims, key=lambda n: (-n.get('origins', 0), n.get('relays', 0), n['id']))
    srow = lambda n: [f'<a href="../{U(n["href"])}">{E(n["label"][:110])}</a>', f'<span class="st st-{E(n["status"])}">{E(n["status"])}</span>', E(str(n['origins'])), E(str(n['relays'])),
                      E(str(sum(1 for e in G['edges'] if e['from'] == n['id'] and e['verb'] == 'appears_in'))), E(n.get('tension', ''))]
    spectrum_t = table(['Claim', 'Status', 'Independent origins', 'Relays', 'Captures that carry it', 'Open tension'], [srow(n) for n in spectrum])
    echoes = [n for n in claims if n.get('echo')]
    unnamed = [n for n in claims if any(e['from'] == 'party:unnamed' and e['to'] == n['id'] for e in G['edges']) and n['origins'] == 0]
    li = lambda ns: '<ul>' + ''.join(f'<li><a href="../{U(n["href"])}">{E(n["label"])}</a> ({n["relays"]} relays)</li>' for n in ns) + '</ul>' if ns else '<p class="small">None.</p>'
    body = f'''
<h1>The story as a graph</h1>
<p class="lead">{len(G["nodes"])} nodes and {len(G["edges"])} edges in {len(verbs)} verbs: {E(by_kind)}. Each is drawn from the same rows as the pages, so the picture cannot disagree with the text. Start anywhere, follow a link, and the graph re-centres on it; a node with a thick ring opens a graph of its own.</p>
{widget}
{section("read", "Read it as sentences", '<p>Every edge is a verb, and read from the other end it has a different name: Wiz <i>states</i> a claim, the claim is <i>stated by</i> Wiz. There is no edge that only says two things are related. The verbs, with how many edges use each:</p>' + verbs_t)}
{section("spectrum", "How many voices, not how many pages", f'<p>A claim is as strong as the number of <b>independent</b> parties that state it, not the number of pages that carry it. A person is counted with the organisation they speak for, and an outlet that passes a statement on is a <i>relay</i>, not a second origin. The fact-check desk grades the same claims by reading their captures (<a href="../factcheck/index.html">the spectrum of evidence</a>); this is the reading the graph gives from its edges alone.</p><h3>Echoes: one origin, many relays ({len(echoes)})</h3>{li(echoes)}<h3>Unnamed origins ({len(unnamed)})</h3><p class="small">Stated only by sources a page does not name: a gap in the evidence, not a party.</p>{li(unnamed)}<h3>Every claim</h3>' + spectrum_t)}
{section("zoom", "Zooming in: the fractal layers", '''<ul>
<li><b>A CVE opens the code.</b> The two CVE nodes open the review graph of the fix, which has its own ontology (the flaws, the design of the patch, the files and functions changed) and its own verbs, joined to this one by a named bridge. This is the estate's test of a fractal graph: going down opens a new vocabulary under the same grammar.</li>
<li><b>A source opens its captures</b>, and each capture lists its files with their SHA-256. A claim <i>appears in</i> a capture where the fact-check desk found its words there. This step is addressing rather than a new ontology, and is described as such.</li>
<li><b>A party opens what it said and what it passed on</b>: the claims and numbers it states, the ones it relays, the sources it publishes, the organisation it is part of. <a href="parties/index.html">Every party</a>.</li>
<li><b>A party steps across into the risk graph.</b> The risk desk keeps its own graph (<a href="../grc/graph/index.html">the risk graph</a>), where parties appear as stakeholders, mostly as classes (WAF vendors, local councils, national governments). <a href="../data/crosswalk.json">data/crosswalk.json</a> declares the bridges: a party <i>is</i> a stakeholder, or is <i>among</i> a class of them; a CVE is the same anchor in all three graphs. Bridges, not a merge: each graph keeps its words.</li>
<li><b>A tension opens the claims it flags</b>: the contradiction ledger of the fact-check desk, one node per row, because two claims that disagree are not one edge with the same name both ways.</li>
</ul>''')}
{section("ontology", "The ontology", f'<p>Kinds of node:</p>{kinds_t}<p>Verbs this graph will not use, and why:</p><ul>{banned}</ul><p>The grammar is the estate&#39;s, from <a href="https://graphs.sgit.ai/v1/grammar/">graphs.sgit.ai</a>; the files are <a href="../data/ontology.json">data/ontology.json</a> (kinds, verbs, taxonomies, formulas), <a href="../data/entities.json">data/entities.json</a> (one node per party, whatever a page calls it) and <a href="../data/attribution.json">data/attribution.json</a> (who states each row). The graph is <a href="../data/graph.json">data/graph.json</a>. Kept by the ontologist. The component that draws it is documented for every agent on <a href="component/index.html">the graph component</a> page.</p>')}
'''
    page('graph/index.html', 'The story as a graph: who states what, who relays it, and what it rests on',
         f'{len(G["nodes"])} nodes and {len(G["edges"])} typed edges: every claim, number, event, signal, advice, party, source and capture on the PHP flaws story, walkable, with the independent origins of each claim.', body, kind='evidence', topics='php2shell graph ontology')
    build_parties(G)
    build_graph_component(G)

def build_parties(G):
    path = 'graph/parties/index.html'
    count = lambda eid, verb: sum(1 for e in G['edges'] if e['from'] == 'party:' + eid and e['verb'] == verb)
    stated = {}
    for e in G['edges']:
        if e['verb'] == 'states' and e['to'].startswith('claim:'): stated.setdefault(e['from'][6:], []).append(e['to'][6:])
    order = ['organisation', 'agency', 'person', 'group', 'outlet', 'registry', 'project', 'platform', 'unnamed', 'this-site']
    secs = []
    for cls in order:
        rows = [e for e in ENTITIES.values() if e['kind'] == cls]
        rows.sort(key=lambda e: (-(count(e['id'], 'states') + count(e['id'], 'relays')), e['name']))
        trs = []
        for e in rows:
            claims = ' '.join(f'<a href="../../facts/{U(c)}/index.html">{E(c)}</a>' for c in stated.get(e['id'], []))
            up = [f'{v.replace("_", " ")} {ENTITIES[e[k]]["name"]}' for k, v in (('works_for', 'works_for'), ('part_of', 'part_of'), ('member_of', 'member_of')) if e.get(k)]
            name = f'<a href="../../{U(party_href(e["id"]))}">{E(e["name"])}</a>' if e.get('actor') else E(e['name'])
            trs.append([f'<span id="p-{E(e["id"])}"></span>{name}' + (f'<br><span class="small">{E("; ".join(up))}</span>' if up else ''),
                        E(str(count(e['id'], 'states'))), E(str(count(e['id'], 'relays'))), E(str(sum(1 for x in G['edges'] if x['to'] == 'party:' + e['id'] and x['verb'] == 'published_by'))), claims])
        if trs: secs.append(section('c-' + cls, f'{cls.capitalize()} ({len(trs)})', table(['Party', 'States', 'Relays', 'Sources published', 'Claims it states'], trs)))
    widget = sg_graph(path, src='data/graph.json', focus='party:php-foundation', depth=1, fallback='<p class="small">The graph of each party needs JavaScript; the tables below carry the same counts.</p>')
    body = f'''
<p class="crumb"><a href="../index.html">The story as a graph</a> / Parties</p>
<h1>Every party, whatever a page calls it</h1>
<p class="lead">{len(ENTITIES)} parties: the people, organisations, agencies, outlets and platforms that published a source or are named as saying something. The sources spell them {len(ALIAS)} ways; each spelling resolves to one node here, so CISA is one party however many pages name it. <i>States</i> counts the claims, numbers and signals a party originates; <i>relays</i> counts those it passed on from someone else.</p>
{widget}
{"".join(secs)}
<p class="small">The file is <a href="../../data/entities.json">data/entities.json</a>, with who states each row in <a href="../../data/attribution.json">data/attribution.json</a>. A party with a page of its own links to it.</p>
'''
    page(path, 'Every party on the story: who states, who relays, who publishes', f'{len(ENTITIES)} parties resolved from {len(ALIAS)} spellings, with the claims each one states and passes on.', body, kind='evidence', topics='php2shell graph parties')

def build_graph_component(G):
    path = 'graph/component/index.html'
    base = os.path.join(ROOT, os.path.dirname(SG_GRAPH_JS))
    hashes = table(['File', 'Bytes', 'SHA-256'], [[f'<code>{E(f)}</code>', E(f'{os.path.getsize(os.path.join(base, f)):,}'), f'<code>{E(hashlib.sha256(open(os.path.join(base, f), "rb").read()).hexdigest())}</code>'] for f in SG_GRAPH_FILES])
    demo = {'ontology': {'kinds': {'party': {'label': 'Party'}, 'claim': {'label': 'Claim'}, 'source': {'label': 'Source'}},
                         'verbs': {'states': {'label': 'states', 'inverse': 'stated by'}, 'relays': {'label': 'relays', 'inverse': 'relayed by'}, 'cites': {'label': 'cites', 'inverse': 'cited by'}}},
            'nodes': [{'id': 'wiz', 'kind': 'party', 'label': 'Wiz'}, {'id': 'thn', 'kind': 'party', 'label': 'The Hacker News'},
                      {'id': 'c', 'kind': 'claim', 'label': '70% of the Internet', 'status': 'unverified', 'href': 'facts/scale-70pc-internet/index.html'},
                      {'id': 's1', 'kind': 'source', 'label': 'Wiz blog'}, {'id': 's2', 'kind': 'source', 'label': 'THN article'}],
            'edges': [{'from': 'wiz', 'verb': 'states', 'to': 'c'}, {'from': 'thn', 'verb': 'relays', 'to': 'c'}, {'from': 'c', 'verb': 'cites', 'to': 's1'}, {'from': 'c', 'verb': 'cites', 'to': 's2'}]}
    attrs = table(['Attribute', 'What it does'], [[f'<code>{E(a)}</code>', E(d)] for a, d in [
        ('src', 'A graph JSON file, relative to the page. Without it, the first <script type="application/json"> child is read.'),
        ('base', 'The path from the page to the site root, put in front of every node href. sg_graph() sets it.'),
        ('focus', 'The node in the middle. Default: the node with most edges.'),
        ('view', 'ego (the focus and its neighbours; the default), layers (columns by kind), map (a seeded force layout; pan by dragging, zoom with ctrl and the wheel), list (text only).'),
        ('depth', 'Hops from the focus, 1 to 3.'), ('max', 'The most nodes drawn at once (default 60); the list under the drawing has every link.'),
        ('height', 'The drawing height in px; default from its width.'), ('verbs', 'A comma list of verbs to show at first.'), ('controls', '"none" hides the toolbar.')]])
    body = f'''
<p class="crumb"><a href="../index.html">The story as a graph</a> / The graph component</p>
<h1>The graph component: one way to draw every graph on this site</h1>
<p class="lead"><code>&lt;sg-graph&gt;</code> draws any graph that has nodes and verb-labelled edges, from five nodes to the whole story. Every agent that puts a graph on a page uses it, through <code>sg_graph()</code> in the build, so all of them walk the same way, follow the same grammar and get the same fixes. Kept by the ontologist. Version 1.0.0; native web component on this site&#39;s <code>sg-component</code> base, no library, no build step, nothing fetched from anywhere else.</p>
{section("small", "Five nodes, inline", sg_graph(path, data=demo, focus='c', controls='none', height=260, fallback='<p>Wiz states that PHP is 70% of the Internet; The Hacker News relays it; it cites two sources.</p>') + '<p class="small">The graph above is inline JSON in the page. Click a node to walk to it, or tab to it and press Enter.</p>')}
{section("layers", "A graph in another vocabulary, in layers", sg_graph(path, src='data/review.json', view='layers', depth=2, focus='fix-commit', fallback='<p>The review graph of the fix: <a href="../../review/index.html">the fix, mapped to the code</a>.</p>') + '<p class="small">The code-review graph (<code>data/review.json</code>), which uses <code>rel</code> and <code>name</code>; the component reads both shapes.</p>')}
{section("use", "Using it from the build", '''<pre><code># in admin/build/build.py, on any page
body += sg_graph('actors/wiz/index.html', src='data/graph.json', focus='party:wiz',
                 fallback='&lt;ul&gt;...the same links as a list...&lt;/ul&gt;')
# or a graph of your own, inline
body += sg_graph(path, data={'nodes': [...], 'edges': [...]}, view='layers')</code></pre>
<p>The rules it brings with it: an edge with no verb is not drawn (there is no generic association edge); each verb should have an inverse in the graph's <code>ontology.verbs</code>, or it is shown as an arrow back; a node's <code>href</code> is followed only if it is relative or http(s); a node with <code>zoom</code>, a list of <code>{ graph, focus, label }</code>, opens those graphs (the older <code>graph</code> and <code>graph_focus</code> are read too), which is how a layer zooms into the next and how a node steps across a bridge into a sibling graph (<code>data/crosswalk.json</code>). The fallback is what a reader without JavaScript sees and what the markdown twin carries: give it the same links.</p>''')}
{section("contract", "Attributes, data, events", attrs + '''<p><b>Data</b>: <code>{ nodes: [{ id, kind, label, href?, status?, zoom?: [{ graph, focus, label }], files? }], edges: [{ from, verb, to, inverse? }], ontology?: { kinds: { id: { label } }, verbs: { verb: { label, inverse } } } }</code>. Older shapes (<code>rel</code>, <code>name</code>, <code>layer</code>, <code>graph</code>) are read too, and so are inverses named on each edge or in a top-level <code>verbs</code> list, as the risk graph names them.</p>
<p><b>Events</b> on <code>document</code>: <code>sg:graph.focus</code> and <code>sg:graph.open</code>. <b>From script</b>: <code>el.focusOn(id)</code>, <code>el.pathTo(id)</code> (the shortest path from the focus, read back as a sentence), <code>el.model</code> and <code>el.core</code>, the model in <code>sg-graph-core.js</code>, which has no DOM and runs in a worker or in node.</p>''')}
{section("files", "Files", hashes + f'<p class="small">Under <code>{E(os.path.dirname(SG_GRAPH_JS))}/</code>. The path is the version: a change is a new directory, never an edit in place. The markup file is <code>.tpl</code> rather than <code>.html</code> because every <code>.html</code> file on this site is a page to the gate.</p>')}
'''
    page(path, 'The graph component: one way to draw every graph on this site', 'sg-graph, the web component every agent uses to put a graph on a page: the views, the data contract, the build helper, and the hashes of its files.', body, kind='site', topics='graph component')


# ----------------------------------------------------------------------------- the fractal graph (v0.5.2, the librarian)

FR_LAYERS = [
    ('stakeholder', 'Stakeholders', 'the fifteen readers in data/personas.json'),
    ('risk', 'Risks', 'authored in data/arcs.json, each resting on claims'),
    ('arc', 'Story arcs', 'authored in data/arcs.json, each carrying risks and resting on claims and events'),
    ('claim', 'Claims and events', 'data/claims.json and data/timeline.json, each with a status or a date'),
    ('source', 'Sources', 'the captured, hashed sources the claims and events cite'),
    ('flaw', 'The flaws', 'the two CVEs, from data/review.json'),
    ('fix', 'The fix', 'the commit and what it does, from data/review.json'),
    ('code', 'Areas and files', 'php-src areas and files the fix changed, from review/code/files.json'),
    ('function', 'Functions', 'the C functions the fix changed, from the diff'),
    ('line', 'Lines', 'every changed hunk, with its line range in php-src'),
]
FR_RANK = {l: i for i, (l, _, _) in enumerate(FR_LAYERS)}

def fractal_graph():
    """Assemble one graph from stakeholders to changed lines. Deterministic: inputs are sorted or kept in file order."""
    A, R = D['arcs'], D['review']
    FJ = json.load(open(os.path.join(ROOT, 'review', 'code', 'files.json'), encoding='utf-8'))
    nodes, edges, seen = OrderedDict(), [], set()
    def node(i, layer, name, text='', **kw):
        if i not in nodes: nodes[i] = {'id': i, 'layer': layer, 'name': name, 'text': text, **kw}
    def edge(a, b, rel):
        if a in nodes and b in nodes and (a, b, rel) not in seen:
            seen.add((a, b, rel)); edges.append({'from': a, 'to': b, 'rel': rel})
    claims = {c['id']: c for c in D['claims']}
    for p in D['personas']['personas']:
        node('who:' + p['id'], 'stakeholder', p['label'], p['who'], href=(p.get('path') or ['start/index.html'])[0])
    for r in A['risks']:
        node('risk:' + r['id'], 'risk', r['name'], r['text'])
    for a in A['arcs']:
        node('arc:' + a['id'], 'arc', a['name'], a['text'], href=a['page'])
    for c in D['claims']:
        node('claim:' + c['id'], 'claim', c['claim'], f'{c["status"]}, says {c["by"]}', status=c['status'], href=f'claims/index.html#{c["id"]}')
    for i, t in enumerate(D['timeline']):
        node(f'event:{i}', 'claim', f'{fmt_at(t["at"])}: {t["event"][:80]}', t['event'], href='timeline/index.html')
    for c in D['claims']:
        for s in c['sources']:
            if s in SOURCES: node('source:' + s, 'source', short_name(SOURCES[s]), SOURCES[s].get('title') or s, href=f'sources/{s}/index.html')
    for t in D['timeline']:
        for s in t['sources']:
            if s in SOURCES: node('source:' + s, 'source', short_name(SOURCES[s]), SOURCES[s].get('title') or s, href=f'sources/{s}/index.html')
    for n in R['nodes']:
        if n['layer'] in ('vulnerability', 'remediation'):
            node(n['id'], 'flaw' if n['layer'] == 'vulnerability' else 'fix', n['name'], n['text'], href='review/ui/index.html#' + n['id'])
        elif n['id'].startswith('area:'):
            node(n['id'], 'code', n['name'], n['text'])
    areas = sorted((i for i in nodes if i.startswith('area:')), key=lambda i: -len(i))
    def area_of(path):
        return next((a for a in areas if path.startswith(a[5:].rstrip('/') + '/') or path == a[5:].rstrip('/')), None)
    for f in FJ['engine_files']:
        fid = 'file:' + f['path']
        fn_names = [x[0] for x in f['functions']]
        node(fid, 'code', f['path'], f'+{f["add"]} / -{f["del"]} in the fix. Functions changed: {", ".join(fn_names) or "none named"}.', url=f['url'])
        for fn in fn_names:
            node(f'fn:{f["path"]}:{fn}', 'function', fn + '()', f'in {f["path"]}', file=f['path'], url=f['url'])
        for h in f['hunks']:
            end = h['new_start'] + max(h['new_len'], 1) - 1
            lid = f'line:{f["path"]}:{h["new_start"]}'
            node(lid, 'line', f'{f["path"].split("/")[-1]}:{h["new_start"]}' + (f'-{end}' if end > h['new_start'] else ''), (h.get('context') or '').strip()[:160], file=f['path'], url=f'{f["url"]}#L{h["new_start"]}-L{end}')
    # edges, top down
    for pid, rs in A['faces'].items():
        for r in rs: edge('who:' + pid, 'risk:' + r, 'faces')
    for a in A['arcs']:
        for r in a['risks']: edge('risk:' + r, 'arc:' + a['id'], 'told in')
    for r in A['risks']:
        for c in r['claims']: edge('risk:' + r['id'], 'claim:' + c, 'rests on')
    for a in A['arcs']:
        for c in D['claims']:
            if c['topic'] in a['topics']: edge('arc:' + a['id'], 'claim:' + c['id'], 'rests on')
        for c in a.get('claims', []): edge('arc:' + a['id'], 'claim:' + c, 'rests on')
        for i, t in enumerate(D['timeline']):
            if t.get('phase') in a['phases']: edge('arc:' + a['id'], f'event:{i}', 'dated by')
    for c in D['claims']:
        for s in c['sources']: edge('claim:' + c['id'], 'source:' + s, 'cites')
    for i, t in enumerate(D['timeline']):
        for s in t['sources']: edge(f'event:{i}', 'source:' + s, 'cites')
    for c, fl in A['claim_to_flaw'].items():
        for f in fl: edge('claim:' + c, f, 'about')
    for c, fx in A['claim_to_fix'].items():
        for f in fx: edge('claim:' + c, f, 'about')
    for e in R['edges']:
        a, b = e['from'], e['to']
        if a.startswith('area:') and a not in nodes and a + '/' in nodes: a += '/'
        if e['rel'] in ('fixes', 'addresses'): edge(b, a, 'closed by')
        elif e['rel'] == 'contains': edge(a, b, 'contains')
        else: edge(a, b, e['rel'])
    for f in FJ['engine_files']:
        fid = 'file:' + f['path']
        ar = area_of(f['path'])
        if ar: edge(ar, fid, 'contains')
        names = {x[0] for x in f['functions']}
        for fn in sorted(names): edge(fid, f'fn:{f["path"]}:{fn}', 'changes')
        for h in f['hunks']:
            lid = f'line:{f["path"]}:{h["new_start"]}'
            m = re.findall(r'([A-Za-z_]\w*)\s*\(', h.get('context') or '')
            if m and m[0] in names: edge(f'fn:{f["path"]}:{m[0]}', lid, 'changed at')
            else: edge(fid, lid, 'changed at')
    return list(nodes.values()), edges

def fractal_reach(nodes, edges):
    """Downward and upward reach along edges that go down the layer ladder (or stay in it)."""
    lay = {n['id']: n['layer'] for n in nodes}
    down, up = {}, {}
    for e in edges:
        a, b = e['from'], e['to']
        if FR_RANK[lay[a]] > FR_RANK[lay[b]]: a, b = b, a
        down.setdefault(a, []).append(b); up.setdefault(b, []).append(a)
    for k in down: down[k].sort()
    for k in up: up[k].sort()
    return down, up

FR_STEPS = {'stakeholder': {'risk'}, 'risk': {'arc'}, 'arc': {'claim'}, 'claim': {'flaw', 'fix'}, 'flaw': {'fix'},
            'fix': {'fix', 'code'}, 'code': {'code', 'function', 'line'}, 'function': {'line'}}

def fractal_thread(start, goal_layer, down, lay, prefer=None, steps=FR_STEPS):
    """The shortest path down the ladder from start to any node in goal_layer, ties broken by id.
    With steps, each move must go to the next rung (so a thread passes a risk, an arc, a claim, a flaw where there is one);
    without, any downward edge will do."""
    prev, q, i = {start: None}, [start], 0
    while i < len(q):
        x = q[i]; i += 1
        if lay[x] == goal_layer and (prefer is None or x.startswith(prefer)):
            path = []
            while x: path.append(x); x = prev[x]
            return path[::-1]
        for y in down.get(x, []):
            if y not in prev and (steps is None or lay[y] in steps.get(lay[x], ())): prev[y] = x; q.append(y)
    return fractal_thread(start, goal_layer, down, lay, prefer, None) if steps is not None else None

def build_fractal():
    nodes, edges = fractal_graph()
    by = {n['id']: n for n in nodes}
    lay = {n['id']: n['layer'] for n in nodes}
    down, up = fractal_reach(nodes, edges)
    def reach(start, nbr):
        seen, q = {start}, [start]
        while q:
            x = q.pop()
            for y in nbr.get(x, []):
                if y not in seen: seen.add(y); q.append(y)
        return seen
    lines = [n['id'] for n in nodes if n['layer'] == 'line']
    up_ok = sum(1 for l in lines if any(lay[x] == 'stakeholder' for x in reach(l, up)))
    named_fix = sum(1 for l in lines if any(lay[x] == 'fix' and x != 'fix-commit' for x in reach(l, up)))
    who = [n['id'] for n in nodes if n['layer'] == 'stakeholder']
    who_ok = sum(1 for w in who if any(lay[x] == 'line' for x in reach(w, down)))
    counts = OrderedDict((l, sum(1 for n in nodes if n['layer'] == l)) for l, _, _ in FR_LAYERS)
    cov = {'lines': len(lines), 'lines_to_stakeholder': up_ok, 'lines_to_named_fix': named_fix, 'stakeholders': len(who), 'stakeholders_to_line': who_ok}
    G = {'about': 'The fractal graph: one graph from the people affected, through the risks, the story and the evidence, to the flaws, the fix and the changed lines of php-src. A node is just a node; meaning lives in the edges. Every node opens into its own neighbourhood in the navigator.',
         'site': SITE, 'version': VERSION, 'commit': D['review']['commit'],
         'layers': [{'id': l, 'name': nm, 'note': nt} for l, nm, nt in FR_LAYERS], 'nodes': nodes, 'edges': edges,
         'counts': {'nodes': len(nodes), 'edges': len(edges), 'by_layer': counts}, 'coverage': cov}
    write('data/fractal.json', json.dumps(G, indent=1, ensure_ascii=False) + '\n')
    # threads: from a stakeholder all the way down to a changed line, the shortest path, shown as a ladder
    picks = [('who:site-owner', 'line:main/rfc1867.c'), ('who:board', 'line:Zend/zend_alloc.c'), ('who:journalist', 'line:'), ('who:developer', 'line:ext/session/session.c'), ('who:everyone', 'line:')]
    def step(i, depth):
        n = by[i]
        name = E(n['name'])
        if n.get('url'): name = f'<a href="{E(n["url"])}" rel="noopener nofollow">{name}</a>'
        elif n.get('href'): name = f'<a href="{"../" * depth}{E(n["href"])}">{name}</a>'
        st = ' ' + pill(n['status']) if n.get('status') else ''
        return f'<li><span class="ly">{E(dict((l, nm) for l, nm, _ in FR_LAYERS)[n["layer"]])}</span> {name}{st}</li>'
    threads = ''
    out_rel = {}
    for e in edges: out_rel.setdefault(e['from'], set()).add(e['to'])
    def coherent(start, pref):
        """A thread that is one argument: the claim is one the risk rests on and the arc carries."""
        best = None
        for r in sorted(x for x in out_rel.get(start, ()) if lay[x] == 'risk'):
            for a in sorted(x for x in out_rel.get(r, ()) if lay[x] == 'arc'):
                for c in sorted(x for x in out_rel.get(r, ()) & out_rel.get(a, set()) if lay[x] == 'claim'):
                    tail = fractal_thread(c, 'line', down, lay, pref)
                    if tail and lay[tail[1]] in ('flaw', 'fix'):
                        t = [start, r, a] + tail
                        if best is None or (len(t), t) < (len(best), best): best = t
        return (best, True) if best else (fractal_thread(start, 'line', down, lay, pref), False)
    for start, pref in picks:
        t, whole = coherent(start, pref) if start in by else (None, False)
        if t:
            threads += f'<article class="role"><h3>{E(by[start]["name"])}, down to a line</h3><ol class="steps">{"".join(step(x, 1) for x in t)}</ol><p class="small">{"" if whole else "No single claim joins this reader's risks to the code, so this is the shortest path down instead. "}<a href="ui/index.html#{E(start)}">Walk it from the top</a> &middot; <a href="ui/index.html#{E(t[-1])}">walk it up from the line</a></p></article>'
    ladder = table(['Layer', 'Nodes', 'Where it comes from'], [[f'<b>{E(nm)}</b>', E(str(counts[l])), E(nt)] for l, nm, nt in FR_LAYERS])
    rels = Counter(e['rel'] for e in edges)
    reltab = table(['Edge', 'Count'], [[E(k), E(str(v))] for k, v in sorted(rels.items(), key=lambda x: (-x[1], x[0]))])
    body = f'''
<h1>From a line of code to a stakeholder</h1>
<p class="lead">One graph for the whole story. At the bottom, the {cov["lines"]} changed hunks of the php2shell fix, each a line range in php-src; above them the functions and files they sit in, the parts of the fix, the two flaws; then the claims and events that talk about them and the sources those cite; then the story arcs those claims carry, the risks the arcs describe, and at the top the fifteen kinds of reader who face those risks. {counts["stakeholder"] + counts["risk"] + counts["arc"] + counts["claim"] + counts["source"] + counts["flaw"] + counts["fix"] + counts["code"] + counts["function"] + counts["line"]} nodes, {len(edges)} edges. Every node opens into its own neighbourhood: <a href="ui/index.html">walk it</a>, from the top or from a line.</p>
{section("ladder", "The layers", ladder + '<p>The top three layers and the joins from a claim to a flaw or a part of the fix are written by the librarian in <a href="../data/arcs.json">data/arcs.json</a>; everything else is derived by the build from files the site already publishes. The assembled graph is <a href="../data/fractal.json">data/fractal.json</a>.</p>')}
{section("coverage", "What is joined, and what is not", f'''<ul>
<li><b>{cov["lines_to_stakeholder"]} of {cov["lines"]}</b> changed hunks reach a stakeholder by walking up the graph.</li>
<li><b>{cov["lines_to_named_fix"]} of {cov["lines"]}</b> reach a <i>named</i> part of the fix (a soft limit, an unwind, globals reset and so on). The rest reach the fix only as "the commit touched this area": the review joined nine files to what the fix does, and the other files of the engine wait for that join.</li>
<li><b>{cov["stakeholders_to_line"]} of {cov["stakeholders"]}</b> stakeholders reach a changed line by walking down.</li>
<li>Not here yet: the 352 files outside the engine and bundled extensions the fix also touched (mostly tests), and the lines of the PHP 7.4 backport.</li>
<li>Not here by design: the vulnerable code before the fix. The graph maps the lines the fix wrote, never a trigger path (the site's security requirements, <a href="https://github.com/SGit-AI/SGit-AI__Website__Newsroom__2026__Oct__PHP/blob/dev/AGENTS.md">AGENTS.md</a>).</li>
</ul>''')}
{section("threads", "Five threads, top to bottom", '<p>Each is the shortest path down the ladder from one reader to a changed line, computed by the build. Click any rung.</p><div class="roles">' + threads + '</div>')}
{section("edges", "The edges", reltab + '<p>Edges are read top down: a stakeholder <i>faces</i> a risk, a risk is <i>told in</i> an arc and <i>rests on</i> claims, a claim <i>cites</i> sources and is <i>about</i> a flaw or a part of the fix, a flaw is <i>closed by</i> the fix, which is <i>realised in</i> files, which <i>change</i> functions, which are <i>changed at</i> lines. The navigator walks them both ways.</p>')}
<p>The fix-only version of this graph is <a href="../review/index.html">the fix mapped to the code</a>; the citation graph alone is <a href="../graph/index.html">as a graph</a>. This answers the second memo's ask for the semantic fractal graph; what it still lacks is on <a href="../corrections/index.html">corrections</a>.</p>
'''
    page('fractal/index.html', 'From a line of code to a stakeholder: the fractal graph', f'One graph for php2shell: {cov["lines"]} changed lines of php-src, up through functions, files, the fix and the flaws, the claims and sources, the story arcs and the risks, to the fifteen kinds of reader who face them.', body, kind='analysis', topics='php2shell graph fractal code stakeholders')
    body = '''
<h1>Walk the whole graph</h1>
<p class="lead">The fractal graph in the navigator: the node in focus and its neighbours, every node a link, from a stakeholder at the top to a changed line at the bottom. Start at a reader and walk down, or at a line and walk up. The data is <a href="../../data/fractal.json">data/fractal.json</a>; the ladder and the threads are on <a href="../index.html">from a line of code to a stakeholder</a>.</p>
<div id="rv" class="review-ui" data-graph="data/fractal.json" data-start="who:site-owner"><noscript>The navigator needs JavaScript. The threads are on <a href="../index.html">from a line of code to a stakeholder</a>.</noscript></div>
<script src="../../assets/review-nav.js" defer></script>
'''
    page('fractal/ui/index.html', 'Walk the whole graph: stakeholders to lines of code', 'A navigator over the php2shell fractal graph: stakeholders, risks, story arcs, claims, sources, the flaws, the fix, files, functions and changed lines, each node a link.', body, kind='evidence', topics='php2shell graph fractal navigator')


# ----------------------------------------------------------------------------- every member: a folder, a policy and a round (librarian@php.newsroom)
# Brief: admin/content/briefs/2026-10-22__brief__every-agent-a-folder-a-policy-and-a-round.md. Reads admin/content/agents/*/
# (ROLE.md, policy.json, status.json, debriefs/) through admin/build/agents.py, which also checks the scopes.

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents as AGT

def load_debriefs(agent):
    d = os.path.join(AGT.AGENTS, agent, 'debriefs')
    out = []
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fn.endswith('.md'):
            continue
        text = open(os.path.join(d, fn), encoding='utf-8').read()
        m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, flags=re.S)
        if not m:
            sys.exit(f'debrief {agent}/{fn}: no front matter')
        meta = dict(re.match(r'^(\w+):\s*(.*)$', l).groups() for l in m.group(1).splitlines() if l.strip())
        meta['file'], meta['text'], meta['agent'] = fn, m.group(2), agent
        out.append(meta)
    return sorted(out, key=lambda x: (x.get('date', ''), x['file']), reverse=True)

def debrief_html(db, depth):
    """Debrief markdown with its screenshots: an image line must name img/<file> inside the member's own debriefs folder."""
    out, buf = [], []
    def flush():
        if buf: out.append(render_md_text('\n'.join(buf))); buf.clear()
    for line in db['text'].splitlines():
        m = re.match(r'^!\[([^\]]*)\]\((img/[A-Za-z0-9_.-]+\.(?:png|jpg|jpeg|webp))\)\s*$', line.strip())
        if m:
            rel = f'admin/content/agents/{db["agent"]}/debriefs/{m.group(2)}'
            flush()
            if os.path.isfile(os.path.join(ROOT, rel)):
                out.append(f'<figure class="shot"><img src="{U("../" * depth + rel)}" alt="{E(m.group(1))}" loading="lazy"><figcaption>{E(m.group(1))}</figcaption></figure>')
            else:
                out.append(f'<p class="small">Missing screenshot: <code>{E(m.group(2))}</code></p>')
            continue
        buf.append(line)
    flush()
    return '\n'.join(out)

def build_members():
    P = AGT.load_policies()
    if not P:
        return
    ov, un, da = AGT.overlaps(P, pages=[]), AGT.unowned(P), AGT.dangling_appends(P)  # pages=[]: never read the last build's output list
    groups = OrderedDict([('humans', 'The humans'), ('coordination', 'Coordination'), ('site', 'The site'), ('evidence', 'Evidence'), ('writing', 'Writing and analysis'), ('testing', 'Testing')])
    rows, agg = [], []
    for a, p in P.items():
        st = AGT.load_status(a) or {}
        dl = AGT.delta(a, P)
        dbs = load_debriefs(a)
        agg.append({'agent': a, 'address': p['address'], 'name': p['name'], 'kind': p['kind'], 'group': p['group'], 'title': p['title'],
                    'policy_status': p['status'], 'member_status': p['member_status'],
                    'writes': p['scope']['writes'], 'pages': p['scope']['pages'], 'vaults': p['scope']['vaults'],
                    'delta': dl, 'status': st or None, 'debriefs': [{'file': x['file'], 'date': x.get('date'), 'title': x.get('title')} for x in dbs]})
    write('data/agents.json', json.dumps({'about': 'Every member of the newsroom: role, scope, the computed delta, the latest status and the debriefs, assembled from admin/content/agents/*/ by the build. The conductor reads this one file.',
                                          'version': VERSION, 'members': agg, 'overlaps': ov, 'unowned': un, 'dangling_appends': da}, indent=1, ensure_ascii=False) + '\n')
    # one page per member
    for x in agg:
        a, p = x['agent'], P[x['agent']]
        role = render_md_file(f'admin/content/agents/{a}/ROLE.md')
        dl = x['delta']
        dtab = ''
        if dl:
            G = {r['capability']: r for r in AGT.grant_rows()}
            dtab = table(['Capability', 'In the mandate', 'Barrier today'], [[f'<code>{E(c)}</code>', 'wanted' if c not in dl['excess'] else ('<b>excess, unbounded</b>' if c in dl['unbounded'] else 'excess, behind a boundary'), E(G[c]['barrier_text'])] for c in G]) + \
                   f'<p>Grant {dl["grant"]} (measured once for every newsroom session, <code>admin/security/abp/GRANT.md</code>) &middot; wanted {dl["wanted"]} &middot; shortfall {len(dl["shortfall"])} &middot; excess {len(dl["excess"])} &middot; <b>unbounded excess {len(dl["unbounded"])}</b>. Computed by <code>admin/build/agents.py</code>; never written by hand. The boundaries that would bound the rest are the editor\'s to set (<code>admin/security/abp/DELTA.md</code>).</p>'
        st = x['status'] or {}
        stt = ''
        if st:
            pol = st.get('policy', {})
            stt = table(['Field', 'Value'], [['Round', E(json.dumps(st.get('round'))) if st.get('round') else E(st.get('state', ''))],
                                              ['Done', '<br>'.join(E(d.get('what', '') if isinstance(d, dict) else d) for d in st.get('done', [])) or 'nothing recorded'],   # a member may write a line, not an object
                                              ['Next', '<br>'.join(E(n.get('what', '') if isinstance(n, dict) else n) for n in st.get('next', [])) or 'nothing proposed'],
                                              ['Asks', '<br>'.join((E(n.get('what', '')) + (f' (from {E(n.get("from", ""))})' if n.get('from') else '')) if isinstance(n, dict) else E(n) for n in st.get('asks', [])) or 'none'],
                                              ['Tokens', E('unknown' if st.get('tokens', {}).get('value') is None else str(st['tokens']['value'])) + ' &middot; ' + E(st.get('tokens', {}).get('how', ''))],
                                              ['Policy', E(', '.join(f'{k} {v}' for k, v in pol.items() if k != 'version'))]])
        dbh = ''.join(f'<article class="role" id="{E(db["file"][:-3])}"><h3>{E(db.get("title", db["file"]))}</h3><p class="small">{E(db.get("date", ""))} &middot; round {E(db.get("round", ""))} &middot; branch <code>{E(db.get("branch", ""))}</code> &middot; commits <code>{E(db.get("commits", ""))}</code> &middot; tokens {E(db.get("tokens", ""))} &middot; outside scope {E(db.get("outside_scope", ""))} &middot; overrides {E(db.get("overrides", ""))}</p>{debrief_html(db, 3)}</article>' for db in load_debriefs(a))
        body = f"""
<p class="kicker">Member &middot; {E(groups.get(p["group"], p["group"]))} &middot; policy {E(p["status"])} &middot; <code>{E(p["address"])}</code></p>
<h1>{E(p["name"])}: {E(p["title"])}</h1>
<p class="lead">The role definition, the agent behaviour policy and every round, from <code>admin/content/agents/{E(a)}/</code>. Who this member is on the team, and the tasks it holds, are on <a href="../../../team/index.html">the team</a>; every member's scope side by side is <a href="../roles/index.html">who owns what</a>.</p>
{section("role", "The role", role)}
{section("delta", "The delta, computed", dtab) if dtab else ""}
{section("status", "Where it is now", f'<div data-live="member-status" data-agent="{E(a)}">' + (stt or '<p class="small">No status file.</p>') + '</div>')}
{section("debriefs", "Its rounds", f'<div data-live="member-debriefs" data-agent="{E(a)}">' + (dbh or '<p class="small">No debrief yet.</p>') + '</div>')}
<script src="../../../assets/live/live.js" defer></script>
<script src="../../../assets/live/members.js" defer></script>
<p class="small">Files: <a href="{U(REPO_URL + "/tree/dev/admin/content/agents/" + a)}">admin/content/agents/{E(a)}/</a> &middot; the same data for every member in <a href="../../../data/agents.json">data/agents.json</a>.</p>
"""
        page(f'admin/agents/{a}/index.html', f'{p["name"]}: role, policy and rounds', f'{p["title"]}: the role definition, what it writes and owns, its agent behaviour policy and computed delta, and every round it has recorded.', body, kind='site')
    # who owns what
    trs = []
    for g, gname in groups.items():
        for x in [y for y in agg if y['group'] == g]:
            dl = x['delta']
            trs.append([f'<a href="../{E(x["agent"])}/index.html"><b>{E(x["name"])}</b></a><div class="note">{E(x["title"])}</div>', E(gname), E(x['member_status']),
                        '<br>'.join(f'<code>{E(w)}</code>' for w in x['writes']) or '<span class="small">none</span>',
                        '<br>'.join(f'<code>{E(w)}</code>' for w in x['pages']) or '<span class="small">none</span>',
                        (f'{dl["wanted"]} wanted &middot; {len(dl["unbounded"])} unbounded' if dl else '<span class="small">no grant here</span>'), E(P[x['agent']]['status'])])
    ovt = table(['Kind', 'Members', 'Patterns', 'Example'], [[E(o['kind']), E(o['a'] + ' and ' + o['b']), f'<code>{E(o["pattern_a"])}</code> / <code>{E(o["pattern_b"])}</code>', E(', '.join(o['files'][:2]))] for o in ov]) if ov else '<p><b>None.</b> No file and no page is claimed by two members.</p>'
    body = f"""
<h1>Every member: who owns what</h1>
<p class="lead">{len(P)} members, {sum(1 for x in agg if x["kind"] == "agent")} of them agents. Each owns a set of files nobody else writes, a set of pages, and the vaults it may hold, in <code>admin/content/agents/&lt;id&gt;/policy.json</code>; shared files have one owner and everyone else only appends. {sum(1 for p in P.values() if p["status"] == "agreed")} of {len(P)} policies are agreed by the editor; the rest are drafts. A request outside a member's scope is refused with the owner named, and counted.</p>
{section("overlaps", "Overlaps", ovt + f'<p>Checked against every tracked source file here, and against every page the build writes by the gate (check 4h) and <code>admin/build/agents.py overlaps</code>. Source files nobody owns: <b>{len(un)}</b>{(": " + ", ".join("<code>" + E(u) + "</code>" for u in un[:20])) if un else ""}. Appends to a file nobody owns: <b>{len(da)}</b>.</p>')}
{section("members", "The members", table(['Member', 'Group', 'Status', 'Writes (exclusive)', 'Pages', 'Mandate', 'Policy'], trs, 'claims'))}
{section("how", "How it works", render_md_file("admin/content/agents/README.md"))}
"""
    page('admin/agents/roles/index.html', 'Every member: who owns what', f'{len(P)} members of the newsroom, each with the files it writes, the pages it owns, its vaults and its agent behaviour policy; overlaps and unowned files checked on every build.', body, kind='site')
    # every round
    dbs = sorted([db for a in P for db in load_debriefs(a)], key=lambda d: (d.get('date', ''), d['agent'], d['file']), reverse=True)
    srows = []
    for x in agg:
        if P[x['agent']]['kind'] != 'agent' or x['agent'] == 'mail':
            continue
        st = x['status'] or {}
        pol = st.get('policy', {})
        last = x['debriefs'][0] if x['debriefs'] else None
        srows.append([f'<a href="../{E(x["agent"])}/index.html">{E(x["name"])}</a>', E(st.get('as_of', '')), f'<a href="../{E(x["agent"])}/index.html#{E(last["file"][:-3])}">{E(last.get("title") or last["file"])}</a>' if last else '<span class="small">none yet</span>',
                      E(str(len(st.get('next', [])))), E(str(len(st.get('asks', [])))), E('unknown' if st.get('tokens', {}).get('value') is None else str(st['tokens']['value'])), E('not run' if pol.get('writes_outside_scope') is None else str(pol['writes_outside_scope'])), E(str(pol.get('overrides', 0))), E(str(pol.get('injection_seen', 0)))])
    dl = ''.join(f'<li>{E(d.get("date", ""))} &middot; <a href="../{E(d["agent"])}/index.html#{E(d["file"][:-3])}"><b>{E(P[d["agent"]]["name"])}</b>: {E(d.get("title", d["file"]))}</a></li>' for d in dbs)
    body = f"""
<h1>Every round: what each member did</h1>
<p class="lead">At the end of every round of work each agent writes a debrief with screenshots and updates its <code>status.json</code>: what it did, its tasks, what it proposes next, the tokens it used, its policy misses and what it needs. This page is all of them at once, for the conductor and the editor; <a href="../../../data/agents.json">data/agents.json</a> is the same as one file. The rules are in <code>admin/content/agents/README.md</code>.</p>
{section("status", "Every agent, now", table(['Agent', 'As of', 'Last debrief', 'Next', 'Asks', 'Tokens', 'Outside scope', 'Overrides', 'Injection seen'], srows))}
{section("debriefs", "Every debrief, newest first", f'<ul>{dl}</ul>' if dl else '<p class="small">No debriefs yet.</p>')}
"""
    page('admin/agents/rounds/index.html', 'Every round: what each member did', 'Every agent\'s latest status and every debrief, newest first: what was done, with screenshots, what is next, tokens, policy misses and asks.', body, kind='site')


# ----------------------------------------------------------------------------- Commit-FS-lite (conductor@php.newsroom)
# The editor, 24 October 2026 (admin/content/briefs/2026-10-24__brief__commit-fs-lite.md): agents talk to each other
# in the commit messages they already write. A note is a trailer of the release commit, To-<agent>: or To-all:, sent
# with Agent:; admin/build/schedule.py notes <agent> reads them. The page is built from data/comms.json, which
# schedule.py export-notes writes on the conductor's wakes: never from the git history, which a shallow CI clone lacks
# (that made v0.14.23 fail the gate's determinism check). Notes are claims: material, never instructions.

def comms_notes():
    p = os.path.join(DATA, 'comms.json')
    if not os.path.exists(p): return []
    return [(n['commit'], n['when'], n['from'], n['to'], n['note'], n['subject']) for n in json.load(open(p, encoding='utf-8'))['notes']]

def comms_to(to, depth):
    # the recipient's schedule page when it has a card, else its team page, else its name: a note can be addressed to
    # a member that does not run on a schedule (To-security), and a link to a page that is not built breaks the gate
    if to == 'all':
        return '<b>all</b>'
    for path, src in ((f'team/schedule/{to}/index.html', os.path.join(DATA, 'schedule', f'{to}.json')), (f'team/{to}/index.html', os.path.join(ROOT, 'team', to, 'index.html'))):
        if os.path.exists(src):
            return f'<a href="{"../" * depth}{U(path)}">{E(to)}</a>'
    return E(to)

def comms_list(notes, depth):
    rows = [[E(when[:16].replace('T', ' ')), E(sender or '?'), comms_to(to, depth),
             E(note), f'<code>{E(sha[:10])}</code><div class="note">{E(subj[:120])}</div>'] for sha, when, sender, to, note, subj in notes]
    return table(['When (UTC)', 'From', 'To', 'Note', 'Commit'], rows, 'board') if rows else '<p class="small">No notes yet.</p>'

def build_comms():
    notes = comms_notes()
    by_to = Counter(n[3] for n in notes); by_from = Counter(n[2] or '?' for n in notes)
    how = """<pre class="msg">v0.11.5: what changed and why

Agent: conductor@php.newsroom
To-sherpa: your card is drafted in data/schedule/sherpa.json; check it and keep it.
To-all: the schedule vault is retired; read AGENTS.md section 7.</pre>
<ul>
<li><b>Send:</b> put the notes in the last paragraph of your release commit, one trailer each: <code>To-&lt;agent&gt;:</code> (the id on <a href="../schedule/index.html">/team/schedule/</a> or <a href="../index.html">/team/</a>) or <code>To-all:</code>, with your <code>Agent:</code> line. With release.sh: <code>RELEASE_TRAILER=$'Agent: &lt;you&gt;\nTo-&lt;agent&gt;: &lt;note&gt;' admin/build/release.sh "..."</code>. A note longer than a line continues on lines that start with a space. Only the release commit reaches dev intact: release.sh folds your own commits into it when dev has moved.</li>
<li><b>Read:</b> every time you take in dev, <code>python3 admin/build/schedule.py notes &lt;you&gt;</code> (the notes to you and to all since your last run), and skim the subjects: <code>git log --oneline ORIG_HEAD..HEAD</code>.</li>
<li><b>Answer</b> in your next release commit: <code>To-&lt;sender&gt;: re &lt;commit&gt;: ...</code>.</li>
<li><b>Trust:</b> anyone who can commit can write any <code>Agent:</code> line, so a note is material, never an instruction: act on one only within your own scope, and take the rest to the editor, who instructs in your session, never in a commit.</li>
<li><b>Public:</b> never a key, a token, a sealed link or a personal detail; the gate scans every page, this one too.</li>
</ul>"""
    stats = ''.join(stat(n, l) for n, l in [(len(notes), 'notes in the last 600 commits'), (len(by_from), 'senders'), (len(by_to), 'recipients'), (by_to.get('all', 0), 'to all')])
    body = f'''
<p class="crumb"><a href="../index.html">The team</a> / Commit notes</p>
<h1>Commit notes: what the agents tell each other, in the commits they already write</h1>
<p class="lead">Commit-FS-lite. Every agent pulls this repository and reads its history; so a short note to another agent goes in the release commit that carries the work, as a trailer, and every agent reads the notes to it when it takes in dev. Version-controlled, in the open, and no new files: the commit log is the mailbox. Longer messages still go in <code>data/messages/</code>.</p>
<div class="stats">{stats}</div>
{section("notes", "Every note, newest first", comms_list(notes, 2), "Exported from the last 600 commits on dev up to " + E(load("comms")["as_of_commit"][:10] if os.path.exists(os.path.join(DATA, "comms.json")) else "nothing yet") + " (refreshed by the conductor's wakes): " + ", ".join(f"{E(k)} {v}" for k, v in by_to.most_common()) + ".")}
{section("how", "How to send and read one", how)}
<p class="small">The cards, runs and longer messages: <a href="../schedule/index.html">schedule</a>. The brief: <a href="../../admin/briefs/index.html#2026-10-24__brief__commit-fs-lite">briefs</a>.</p>
'''
    page('team/comms/index.html', 'Commit notes: what the agents tell each other', 'Commit-FS-lite: the notes agents leave each other in their release commits, To-<agent> or To-all, read on every pull; every note, newest first.', body, kind='site', topics='team agents comms')


# ============================================================================== security@php.newsroom: application security
# admin/appsec/: the threat model and data flows, who can do what, the advisories (one page each, kept like incidents),
# the post-mortem patterns, what a client-side site does not have to care about, the incident process and runbooks, the
# bug bounty and its leaderboard, and the prompts for outside reviewers. From data/appsec.json and data/advisories.json.

SEV_CLASS = {'critical': 'st-failed', 'high': 'st-contradicted', 'medium': 'st-disputed', 'low': 'st-unverified'}
STATUS_CLASS = {'fixed': 'st-confirmed', 'open': 'st-contradicted', 'mitigated': 'st-disputed', 'accepted': 'st-unverified'}

def appsec_badge(word, classes):
    return f'<span class="st {classes.get(word, "")}">{E(word)}</span>'

def appsec_credit(s):
    """'security@php.newsroom (pass 2 review)' and 'a; b' -> the names to credit."""
    return [re.sub(r'\s*\(.*?\)\s*', '', x).strip() for x in str(s or '').split(';') if x.strip()]

def appsec_diagram(spec):
    dg = __import__('diagram')
    return (f'<figure class="flowfig" id="d-{E(spec["id"])}"><figcaption><b>{E(spec["title"])}.</b> {E(spec["caption"])}</figcaption>'
            f'<div class="flowwrap" style="overflow-x:auto">{dg.svg(spec)}</div>{dg.legend()}'
            f'<details><summary>Mermaid source</summary><pre data-lang="mermaid"><code>{E(dg.mermaid(spec))}</code></pre></details></figure>')

def build_appsec():
    if not os.path.exists(os.path.join(DATA, 'appsec.json')):
        return
    X, AD = load('appsec'), load('advisories')
    adv = AD['advisories']; byid = {a['id']: a for a in adv}
    pts = AD['scoring']
    sev_n = Counter(a['severity'] for a in adv); st_n = Counter(a['status'] for a in adv)
    nav = [('index.html', 'Overview'), ('threat-model/index.html', 'Threat model and data flows'), ('advisories/index.html', 'Advisories'),
           ('post-mortems/index.html', 'Root causes and guidance'), ('policies/index.html', 'Who can do what'), ('client-side/index.html', 'What a client-side site does not have to care about'),
           ('incidents/index.html', 'Incidents and runbooks'), ('bounty/index.html', 'Bug bounty and leaderboard'), ('reviews/index.html', 'Outside reviews and the agents\' self-check')]
    def crumbs(depth, here):
        up = '../' * depth
        return '<nav class="small appsec-nav" aria-label="Application security">' + ' &middot; '.join(
            (f'<b>{E(t)}</b>' if p == here else f'<a href="{up}{p}">{E(t)}</a>') for p, t in nav) + '</nav>'
    def links(text, depth):
        """SA-2026-nnn in text become links to the advisory pages; everything else is escaped."""
        up = '../' * depth
        out, last = '', 0
        for m in re.finditer(r'SA-2026-(\d{3})((?:,\s*\d{3})*)', str(text)):
            out += E(str(text)[last:m.start()])
            ids = [m.group(1)] + re.findall(r'\d{3}', m.group(2))
            out += ', '.join(f'<a href="{up}advisories/SA-2026-{i}/index.html">{"SA-2026-" + i if n == 0 else i}</a>' for n, i in enumerate(ids) if f'SA-2026-{i}' in byid)
            last = m.end()
        return out + E(str(text)[last:])
    def adv_table(rows, depth):
        up = '../' * depth
        return table(['Advisory', 'Severity', 'Status', 'Title', 'Component', 'Fixed in'],
                     [[f'<a href="{up}advisories/{E(a["id"])}/index.html"><code>{E(a["id"])}</code></a>', appsec_badge(a['severity'], SEV_CLASS), appsec_badge(a['status'], STATUS_CLASS),
                       E(a['title']), f'<code>{E(a["component"])}</code>', E(a['fixed_in'] if a['fixed_in'] != 'pending' else 'this release')] for a in rows], 't appsec')
    # the leaderboard: finders by severity points; fixers listed beside
    board = {}
    for a in adv:
        for who in appsec_credit(a['found_by']):
            r = board.setdefault(who, {'points': 0, 'found': [], 'fixed': []})
            r['points'] += pts.get(a['severity'], 0); r['found'].append(a['id'])
        for who in appsec_credit(a['fixed_by']):
            board.setdefault(who, {'points': 0, 'found': [], 'fixed': []})['fixed'].append(a['id'])
    ranking = sorted(board.items(), key=lambda kv: (-kv[1]['points'], kv[0]))

    # ---------------------------------------------------------------- overview
    stats = ''.join(stat(n, l) for n, l in [(len(adv), 'advisories'), (st_n.get('fixed', 0), 'fixed'), (st_n.get('open', 0) + st_n.get('mitigated', 0), 'open or mitigated'),
                                             (sev_n.get('high', 0), 'high'), (sev_n.get('medium', 0), 'medium'), (sev_n.get('low', 0), 'low')])
    openrows = [a for a in adv if a['status'] in ('open', 'mitigated')]
    body = f"""
<h1>Application security</h1>
{crumbs(0, 'index.html')}
<p class="lead">{E(X['lead'])}</p>
<div class="stats">{stats}</div>
{appsec_diagram(X['diagrams'][0])}
{section('sections', 'In this section', '<ul>' + ''.join(f'<li><a href="{p}">{E(t)}</a></li>' for p, t in nav[1:]) + '</ul>')}
{section('open', 'Open now', adv_table(openrows, 0), E('Open and mitigated advisories, by number. Those marked limited disclosure name the issue; their details follow the fix.'))}
<p class="small">Kept by security@php.newsroom. The advisories are in <code>data/advisories.json</code>, this section in <code>data/appsec.json</code>; the rules every agent works to are in <code>admin/security/REQUIREMENTS.md</code> and <code>AGENTS.md</code>, section 5. As of {E(X['as_of'])}.</p>
"""
    page('admin/appsec/index.html', 'Application security', 'The newsroom\'s application security: its threat model and data flows, every vulnerability found and fixed as an advisory with its root cause, who can do what, the incident runbooks, the bug bounty and the outside reviews.', body, kind='site')

    # ---------------------------------------------------------------- threat model
    tm = f"""
<h1>Threat model and data flows</h1>
{crumbs(1, 'threat-model/index.html')}
<p class="lead">What we protect, who might attack it, the ways in, and the walls in front of each. The diagrams are drawn by the build from <code>data/appsec.json</code>; each carries its Mermaid source.</p>
{section('assets', 'What we protect', table(['Asset', 'What it is', 'Advisories'], [[E(a), E(b), links(c, 1)] for a, b, c in X['assets']], 't'))}
{section('actors', 'Who might attack it', table(['Actor', 'Who they are', 'What they can try'], [[E(a), E(b), E(c)] for a, b, c in X['actors']], 't'))}
{''.join(appsec_diagram(d) for d in X['diagrams'][:4])}
{section('threats', 'Threats, by boundary', table(['#', 'STRIDE', 'Where', 'Threat', 'What stands in the way', 'Barrier', 'Advisories'], [[E(t[0]), E(t[1]), E(t[2]), E(t[3]), E(t[4]), E(t[5]), links(t[6], 1)] for t in X['threats']], 't'), E('A barrier is a boundary only when something outside the agent enforces it; a setting is something the agent itself could change; an expectation is a rule in prose.'))}
"""
    page('admin/appsec/threat-model/index.html', 'Threat model and data flows', 'The newsroom\'s threat model: assets, attackers, trust zones, the data flows from hostile pages to readers and from agents to the live site, and the threats at each boundary.', tm, kind='site')

    # ---------------------------------------------------------------- advisories
    lst = f"""
<h1>Security advisories</h1>
{crumbs(1, 'advisories/index.html')}
<p class="lead">{E(AD['about'])}</p>
{adv_table(adv, 1)}
"""
    page('admin/appsec/advisories/index.html', 'Security advisories', 'Every vulnerability found in the newsroom, numbered SA-2026-nnn like CVEs, with severity, status, root cause and fix.', lst, kind='site')
    for a in adv:
        limited = a['disclosure'] == 'limited' and a['status'] != 'fixed'
        rows = [('Severity', appsec_badge(a['severity'], SEV_CLASS)), ('Status', appsec_badge(a['status'], STATUS_CLASS)), ('Weakness', E(a['cwe'])), ('Component', f'<code>{E(a["component"])}</code>'),
                ('Found by', E(a['found_by'])), ('Found', E(a['found'])), ('Fixed in', E(a['fixed_in'] if a['fixed_in'] != 'pending' else 'this release') or 'not yet'), ('Fixed by', E(a['fixed_by']) or '')]
        facts = table(['', ''], [[f'<b>{k}</b>', v] for k, v in rows if v], 't kv')
        if limited:
            detail = '<p><b>Limited disclosure.</b> This issue is open and its details would help an attacker, so they are held until it is fixed. The editor and security@ hold them.</p>' + f'<p>{E(a["summary"])}</p>'
        else:
            detail = (section('what', 'What it is', f'<p>{E(a["summary"])}</p>') + section('impact', 'What an attacker could do', f'<p>{E(a["impact"])}</p>' + (f'<p class="small"><b>How:</b> {E(a["attack_path"])}</p>' if a['attack_path'] else ''))
                      + section('root', 'Root cause', f'<p>{E(a["root_cause"])}</p>')
                      + (section('contributing', 'What contributed', '<ul>' + ''.join(f'<li>{E(x)}</li>' for x in a['contributing']) + '</ul>') if a['contributing'] else '')
                      + (section('missing', 'What was not in place', f'<p>{E(a["missing_control"])}</p>') if a['missing_control'] else '')
                      + (section('fix', 'The fix', f'<p>{E(a["fix"])}</p>') if a['fix'] else '')
                      + section('prevention', 'What prevents it now' if a['status'] == 'fixed' else 'What would fix it', f'<p>{links(a["prevention"], 2)}</p>'))
        refs = ('<p class="small">References: ' + ', '.join(f'<code>{E(r)}</code>' for r in a['refs']) + '</p>') if a['refs'] else ''
        body = f"""
<p class="crumb"><a href="../index.html">Advisories</a> / {E(a['id'])}</p>
<h1>{E(a['id'])}: {E(a['title'])}</h1>
{crumbs(2, '')}
{facts}
{detail}
{refs}
"""
        page(f'admin/appsec/advisories/{a["id"]}/index.html', f'{a["id"]}: {a["title"]}', f'Security advisory {a["id"]} ({a["severity"]}, {a["status"]}): {a["title"]}.', body, kind='site')

    # ---------------------------------------------------------------- root causes
    fixed = [a for a in adv if a['status'] == 'fixed']
    pm = f"""
<h1>Root causes, and the guidance they give</h1>
{crumbs(1, 'post-mortems/index.html')}
<p class="lead">Every finding was handled as an incident: what went wrong, why, what was not in place, and what now stands in the way. Read together, {len(adv)} advisories come down to {len(X['patterns'])} patterns. Each pattern is a rule for every agent.</p>
{section('patterns', 'The patterns', table(['Pattern', 'Advisories', 'The rule it gives'], [[f'<b>{E(p[0])}</b>', links(p[1], 1), E(p[2])] for p in X['patterns']], 't'))}
{section('fixed', 'Every fixed advisory, its root cause and its guard', table(['Advisory', 'Root cause', 'What was not in place', 'What prevents it now'], [[f'<a href="../advisories/{E(a["id"])}/index.html"><code>{E(a["id"])}</code></a><div class="note">{E(a["title"])}</div>', E(a['root_cause']), E(a['missing_control']), links(a['prevention'], 1)] for a in fixed], 't'))}
"""
    page('admin/appsec/post-mortems/index.html', 'Root causes and guidance', 'The post-mortems of every fixed vulnerability in the newsroom, grouped into the patterns they share, and the rule each pattern gives every agent.', pm, kind='site')

    # ---------------------------------------------------------------- who can do what
    pol = f"""
<h1>Who can do what</h1>
{crumbs(1, 'policies/index.html')}
<p class="lead">{E(X['policies_about'])}</p>
{table(['Who'] + [E(c) for c in X['policy_columns']] + ['Barrier on releases'], [[E(c) for c in r] for r in X['policies']], 't')}
{section('next', 'What would turn settings into boundaries', '<ol>' + ''.join(f'<li>{links(x, 1)}</li>' for x in X['policies_next']) + '</ol>')}
<p class="small">Each member's own draft policy is in <code>admin/content/agents/&lt;member&gt;/policy.json</code> (the librarian's work); this page's vocabulary and the measured grant are in <code>admin/security/abp/</code>.</p>
"""
    page('admin/appsec/policies/index.html', 'Who can do what', 'Every member of the newsroom, what hostile text it reads, which vault keys it holds, whether it releases to the site or runs unsupervised, and what stands in the way of each right.', pol, kind='site')

    # ---------------------------------------------------------------- client side
    cs = X['client_side']
    cl = f"""
<h1>What a client-side site does not have to care about, and what it must</h1>
{crumbs(1, 'client-side/index.html')}
<p class="lead">This site has no server of its own: static pages on GitHub Pages, encrypted vaults whose server cannot read them, and everything else in the reader's browser. Whole classes of attack are gone. The ones that are left are concentrated, and some got worse.</p>
{section('gone', 'Gone, by design', table(['', 'Why'], [[f'<b>{E(a)}</b>', E(b)] for a, b in cs['gone']], 't'))}
{section('moved', 'Moved, and bigger for it', table(['', 'Why'], [[f'<b>{E(a)}</b>', links(b, 1)] for a, b in cs['moved']], 't'))}
{appsec_diagram(X['diagrams'][3])}
"""
    page('admin/appsec/client-side/index.html', 'What a client-side site does not have to care about', 'The attack classes a static, zero-knowledge, client-side site does not have, and the ones that move into the reader\'s browser, the build and the agents.', cl, kind='site')

    # ---------------------------------------------------------------- incidents and runbooks
    rb = ''.join(f'<article class="role" id="{E(r["id"])}"><h3>{E(r["title"])}</h3><p class="small"><b>When:</b> {E(r["when"])}</p><ol>' + ''.join(f'<li>{E(s)}</li>' for s in r['steps']) + '</ol></article>' for r in X['runbooks'])
    inc = f"""
<h1>Incidents and runbooks</h1>
{crumbs(1, 'incidents/index.html')}
<p class="lead">Every security finding is an incident, however small: it gets an advisory, a root cause and a change to what prevents the next one. These are the steps, and who takes them.</p>
{appsec_diagram(X['diagrams'][4])}
{section('process', 'The process', table(['', ''], [[f'<b>{E(a)}</b>', E(b)] for a, b in X['process']], 't kv'))}
{section('runbooks', 'Runbooks', '<ul>' + ''.join(f'<li><a href="#{E(r["id"])}">{E(r["title"])}</a></li>' for r in X['runbooks']) + '</ul>' + rb)}
"""
    page('admin/appsec/incidents/index.html', 'Incidents and runbooks', 'How the newsroom handles a security finding, and the runbooks: responding, taking the site offline, shutting the whole system down, a leaked secret, a steered agent, script on the site.', inc, kind='site')

    # ---------------------------------------------------------------- bounty and leaderboard
    B = X['bounty']
    lb = table(['#', 'Who', 'Points', 'Found', 'Fixed'], [[str(i + 1), f'<b>{E(w)}</b>', str(r['points']), ', '.join(f'<a href="../advisories/{E(x)}/index.html">{E(x[-3:])}</a>' for x in r['found']) or '', ', '.join(f'<a href="../advisories/{E(x)}/index.html">{E(x[-3:])}</a>' for x in r['fixed']) or ''] for i, (w, r) in enumerate(ranking)], 't')
    bb = f"""
<h1>Bug bounty: paid in kudos</h1>
{crumbs(1, 'bounty/index.html')}
<p class="lead">{E(B['lead'])}</p>
{section('leaderboard', 'Leaderboard', lb, E('Points per advisory found: ' + B['points'] + '. Fixes are credited beside them.'))}
{section('in', 'In scope', '<ul>' + ''.join(f'<li>{E(x)}</li>' for x in B['scope_in']) + '</ul>')}
{section('out', 'Out of scope', '<ul>' + ''.join(f'<li>{links(x, 1)}</li>' for x in B['scope_out']) + '</ul>')}
{section('how', 'How to report', '<ol>' + ''.join(f'<li>{E(x)}</li>' for x in B['how']) + '</ol>' + '<p class="small">Also published as <a href="../../../.well-known/security.txt">/.well-known/security.txt</a>.</p>')}
{section('harbour', 'Safe harbour', f'<p>{E(B["safe_harbour"])}</p>')}
"""
    page('admin/appsec/bounty/index.html', 'Bug bounty and leaderboard', 'The newsroom\'s bug bounty, paid in kudos: what is in scope, how to report, the safe harbour, and the leaderboard of everyone who has found or fixed a vulnerability here.', bb, kind='site')

    # ---------------------------------------------------------------- outside reviews and the self-check
    rv = ''.join(f'<article class="role" id="{E(r["id"])}"><h3>{E(r["name"])}</h3><p class="small"><b>Focus:</b> {E(r["focus"])}</p><pre><code>{E(r["prompt"] + chr(10) + chr(10) + "Rules:" + chr(10) + chr(10).join("- " + x for x in X["reviewer_rules"]))}</code></pre></article>' for r in X['reviewers'])
    rw = f"""
<h1>Outside reviews, and every agent's self-check</h1>
{crumbs(1, 'reviews/index.html')}
<p class="lead">{E(X['reviews_about'])}</p>
{section('rules', 'Rules every outside reviewer gets', '<ol>' + ''.join(f'<li>{E(x)}</li>' for x in X['reviewer_rules']) + '</ol>')}
{section('prompts', 'The prompts', rv, E('Copy one whole block into a fresh session. Each already ends with the rules.'))}
{section('self', 'Every agent, after every piece of work', '<ol>' + ''.join(f'<li>{E(x)}</li>' for x in X['self_check']) + '</ol>', E('Not a security audit: a pass over one\'s own change before it ships. The same list is in AGENTS.md, section 5.'))}
"""
    page('admin/appsec/reviews/index.html', 'Outside reviews and the agents\' self-check', 'The prompts for outside security reviews (an architecture review, an independent code and browser audit, a pipeline and supply-chain review), their rules, and the security self-check every agent runs after its own work.', rw, kind='site')


def appsec_llms_lines():
    if not os.path.exists(os.path.join(DATA, 'advisories.json')):
        return []
    out = ['## Application security (security@php.newsroom)']
    for p, t, d, _ in PAGES:
        if p.startswith('admin/appsec/') and '/advisories/SA-' not in p:
            out.append(f'- [{t}]({BASE_URL}/{md_path(p)}): {d}')
    for a in load('advisories')['advisories']:
        out.append(f'- [{a["id"]}: {a["title"]}]({BASE_URL}/admin/appsec/advisories/{a["id"]}/index.md): {a["severity"]}, {a["status"]}')
    return out + ['']

def _state_hashes():
    """The generated data files a build reads back at its start (the ledger, the items, the release pages, the risk
    graph's history ...), by hash: every data/*.json the last build listed as its own output."""
    import hashlib
    try:
        names = [l.strip() for l in open(os.path.join(ROOT, 'admin', 'build', 'outputs.txt'), encoding='utf-8') if l.startswith('data/') and l.strip().endswith('.json')]
    except FileNotFoundError:
        names = []
    out = {}
    for n in names:
        try:
            out[n] = hashlib.sha256(open(os.path.join(ROOT, n), 'rb').read()).hexdigest()
        except FileNotFoundError:
            out[n] = None
    return out

# ----------------------------------------------------------------------------- Wikipedia, as a graph (ontologist@php.newsroom)
# Brief: admin/content/briefs/2026-10-25__brief__wikipedia-as-an-anchor.md. The fetch (admin/wikipedia/fetch.py) writes
# data/wikipedia/<article>/; this block reads it, never the web. The parser is admin/build/wikitext.py: one statement per
# sentence, classed by wording; references resolved to this site's sources by URL and to parties by host. The text is
# Wikipedia's (CC BY-SA 4.0, by its contributors; the revision id is the attribution) and reaches a page only as text.

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import datetime
import wikitext as WT

WIKI_DIR = os.path.join(DATA, 'wikipedia')
WIKI_CACHE = {}
REVERT_TAGS = {'mw-reverted', 'mw-undo', 'mw-rollback', 'mw-manual-revert'}

def T(x):
    """Third-party text for a page: escaped, with its em-dashes as entities (the gate's em-dash rule is for this site's own prose)."""
    return E(str(x or '')).replace('—', '&mdash;')

def norm_url(u):
    """The part of a URL that names the page: host without www/m/edition, path and query, lower-cased, no trailing slash."""
    from urllib.parse import urlsplit, unquote
    u = unquote(str(u or '').strip())
    s = urlsplit(u if '://' in u else 'https://' + u)
    host = s.netloc.lower()
    for p in ('www.', 'm.', 'edition.', 'amp.'):
        host = host[len(p):] if host.startswith(p) else host
    q = ('?' + s.query) if s.query and 'status' not in s.path else ''
    return (host + s.path.rstrip('/') + q).lower()

def host_of(u):
    from urllib.parse import urlsplit
    h = urlsplit(u if '://' in u else 'https://' + u).netloc.lower()
    return h[4:] if h.startswith('www.') else h

HOST_ALIAS = None
def party_for_host(host):
    """The entity whose host alias matches this host or a parent of it (sec.cloudapps.cisco.com matches cisco.com)."""
    global HOST_ALIAS
    if HOST_ALIAS is None:
        HOST_ALIAS = {a.lower(): e['id'] for e in ENT['entities'] for a in e.get('aliases', []) if '.' in a and ' ' not in a and '/' not in a}
    parts = host.split('.')
    for i in range(len(parts) - 1):
        cand = '.'.join(parts[i:])
        if cand in HOST_ALIAS:
            return HOST_ALIAS[cand]
    return None

def wiki_load(slug):
    """Everything the pages and the graph need for one article, computed once per build."""
    if slug in WIKI_CACHE:
        return WIKI_CACHE[slug]
    d = os.path.join(WIKI_DIR, slug)
    art = json.load(open(os.path.join(d, 'article.json'), encoding='utf-8'))
    revs = []
    for fn in os.listdir(os.path.join(d, 'revisions')):
        if fn.endswith('.json'):
            revs.append(json.load(open(os.path.join(d, 'revisions', fn), encoding='utf-8')))
    revs.sort(key=lambda r: (r['timestamp'], r['revid']))
    wd = json.load(open(os.path.join(d, 'wikidata.json'), encoding='utf-8')) if os.path.exists(os.path.join(d, 'wikidata.json')) else None
    links_in = json.load(open(os.path.join(d, 'links-in.json'), encoding='utf-8')) if os.path.exists(os.path.join(d, 'links-in.json')) else {'articles': []}
    parsed = {r['revid']: WT.statements(r['wikitext']) for r in revs}
    latest = revs[-1]
    X = parsed[latest['revid']]
    src_by_url = {norm_url(s['url']): slug_ for slug_, s in SOURCES.items()}
    name_alias = {a.lower(): e['id'] for e in ENT['entities'] for a in e.get('aliases', [])} | {e['name'].lower(): e['id'] for e in ENT['entities']}
    claims_by_src = {}
    for c in D['claims']:
        for s in c['sources']:
            claims_by_src.setdefault(s, []).append(c['id'])
    for ref in X['references']:
        url = ref.get('url') or ''
        ref['captured'] = src_by_url.get(norm_url(url)) if url else None
        ref['host'] = host_of(url) if url else None
        pub = (ref.get('publisher') or '').strip()
        by_host = party_for_host(ref['host']) if ref['host'] else None
        by_name = name_alias.get(pub.lower()) or name_alias.get(pub.lower().removeprefix('the ').strip())
        # the host names the publisher, except on a platform (GitHub, X), which hosts what the named party publishes
        ref['party'] = (by_name or by_host) if by_host and ENTITIES[by_host]['kind'] == 'platform' else (by_host or by_name)
        ref['claims'] = claims_by_src.get(ref['captured'], []) if ref['captured'] else []
        ref['cited_by'] = [s['id'] for s in X['statements'] if ref['n'] in s['refs']]
    by_n = {r['n']: r for r in X['references']}
    for s in X['statements']:
        s['captured'] = sorted({by_n[n]['captured'] for n in s['refs'] if by_n[n].get('captured')})
        s['claims'] = sorted({c for n in s['refs'] for c in by_n[n]['claims']})
    # the deltas: each revision against its parent, by statement
    deltas = []
    prev = None
    for r in revs:
        dlt = WT.delta(parsed[prev['revid']], parsed[r['revid']]) if prev else {'added': parsed[r['revid']]['statements'], 'removed': [], 'changed': [], 'refs_added': [], 'refs_removed': []}
        dlt['revid'] = r['revid']
        deltas.append(dlt)
        prev = r
    # the vault's capture of the article: the revision that was current then
    cap = SOURCES.get('wikipedia-' + slug) or next((s for s in SOURCES.values() if norm_url(s['url']) == norm_url(art['url'])), None)
    cap_stamp = cap['captures'][-1]['stamp'] if cap and cap.get('captures') else None
    cap_rev = None
    if cap_stamp:
        t = f'{cap_stamp[:4]}-{cap_stamp[4:6]}-{cap_stamp[6:8]}T{cap_stamp[9:11]}:{cap_stamp[11:13]}:{cap_stamp[13:15]}Z'
        cap_rev = max((r for r in revs if r['timestamp'] <= t), key=lambda r: (r['timestamp'], r['revid']), default=None)
    since_capture = WT.delta(parsed[cap_rev['revid']], X) if cap_rev else None
    out = {'slug': slug, 'art': art, 'revs': revs, 'latest': latest, 'X': X, 'wd': wd, 'links_in': links_in, 'deltas': deltas, 'parsed': parsed,
           'capture': cap, 'capture_rev': cap_rev, 'since_capture': since_capture, 'path': f'wikipedia/{slug}/index.html'}
    WIKI_CACHE[slug] = out
    return out

def wiki_index():
    idx = os.path.join(WIKI_DIR, 'index.json')
    return json.load(open(idx, encoding='utf-8'))['articles'] if os.path.exists(idx) else []

def wiki_articles():
    return [a['slug'] for a in wiki_index() if a.get('kind', 'article') == 'article']

def wiki_talk(slug):
    """The talk page of an article, as threads, with its revisions; None when none is fetched."""
    t = next((a for a in wiki_index() if a.get('kind') == 'talk' and a.get('of') == slug), None)
    if not t:
        return None
    d = os.path.join(WIKI_DIR, t['slug'])
    art = json.load(open(os.path.join(d, 'article.json'), encoding='utf-8'))
    revs = sorted((json.load(open(os.path.join(d, 'revisions', fn), encoding='utf-8')) for fn in os.listdir(os.path.join(d, 'revisions')) if fn.endswith('.json')), key=lambda r: (r['timestamp'], r['revid']))
    return {'slug': t['slug'], 'art': art, 'revs': revs, 'threads': WT.talk(revs[-1]['wikitext'])}

def wiki_review(slug):
    """This site's review of one article, done as a Wikipedia reviewer would (data/wikipedia/<slug>/review.json, authored
    by the ontologist); None when there is none. Every source, claim and contradiction it names must exist."""
    f = os.path.join(ROOT, 'data', 'wikipedia', slug, 'review.json')
    if not os.path.exists(f):
        return None
    R = json.load(open(f, encoding='utf-8'))
    cl = {c['id'] for c in D['claims']}
    ks = {k['id'] for k in load('factcheck')['contradictions']}
    for fnd in R['findings']:
        ev = fnd.get('evidence', {})
        for x in ev.get('sources', []):
            if x not in SOURCES: sys.exit(f'wikipedia review {slug}: {fnd["id"]} names unknown source {x!r}')
        for x in ev.get('claims', []):
            if x not in cl: sys.exit(f'wikipedia review {slug}: {fnd["id"]} names unknown claim {x!r}')
        for x in ev.get('contradictions', []):
            if x not in ks: sys.exit(f'wikipedia review {slug}: {fnd["id"]} names unknown contradiction {x!r}')
    for t in R.get('talk', []):
        for x in t.get('sources', []):
            if x not in SOURCES: sys.exit(f'wikipedia review {slug}: talk answer names unknown source {x!r}')
    for x in R.get('missing_from_the_article', []):
        if x not in cl: sys.exit(f'wikipedia review {slug}: missing_from_the_article names unknown claim {x!r}')
    return R

def wiki_finding_statement(w, fnd):
    """The statement a finding questions: the one whose text starts with the finding's opening words, at the latest revision."""
    start = fnd['starts'].lower()
    for st in w['X']['statements']:
        if st['text'].lower().startswith(start):
            return st
    return None

def wiki_item_history(slug):
    p = os.path.join(WIKI_DIR, slug, 'wikidata-history.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None

WD_LINKS = None
def wikidata_link(eid):
    """The Wikidata item a party is confirmed to be, from data/wikidata-links.json; proposals are not links."""
    global WD_LINKS
    if WD_LINKS is None:
        p = os.path.join(DATA, 'wikidata-links.json')
        WD_LINKS = json.load(open(p, encoding='utf-8'))['parties'] if os.path.exists(p) else {}
    l = WD_LINKS.get(eid)
    return l['item'] if l and l.get('confirmed') and l.get('item') else None

def wiki_lifelines(w):
    """For every statement that ever existed: the revision that first added it and the one that removed it (or None)."""
    life = OrderedDict()
    for r, dlt in zip(w['revs'], w['deltas']):
        for s in dlt['added'] + [c['to'] for c in dlt['changed']]:
            if s['id'] not in life:
                life[s['id']] = {'text': s['text'], 'class': s['class'], 'section': s['section'], 'born': r['revid'], 'born_at': r['timestamp'], 'died': None, 'died_at': None}
            elif life[s['id']]['died']:
                life[s['id']].update({'died': None, 'died_at': None, 'reborn': r['revid']})
        for s in dlt['removed'] + [c['from'] for c in dlt['changed']]:
            if s['id'] in life and not life[s['id']]['died']:
                life[s['id']].update({'died': r['revid'], 'died_at': r['timestamp']})
    return life

def wiki_ledger(w):
    """The counts a proof of trust would start from. Not a score: the fact-check desk grades statements, this page counts."""
    S, R, revs = w['X']['statements'], w['X']['references'], w['revs']
    with_url = [r for r in R if r.get('url')]
    captured = [r for r in with_url if r['captured']]
    primary = [r for r in captured if SOURCES[r['captured']].get('primary')]
    shared = [r for r in captured if r['claims']]
    shared_claims = sorted({c for r in shared for c in r['claims']})
    ks = [k for k in load('factcheck')['contradictions'] if set(k['claims']) & set(shared_claims)]
    reverts = [r for r in revs if set(r['tags']) & REVERT_TAGS]
    anon = sum(1 for r in revs if r['editor']['kind'] != 'registered')
    return {'statements': len(S), 'cited': sum(1 for s in S if s['cited']), 'uncited': [s for s in S if not s['cited']],
            'classes': Counter(s['class'] for s in S), 'with_evidence': sum(1 for s in S if s['captured']), 'with_claims': sum(1 for s in S if s['claims']),
            'references': len(R), 'with_url': len(with_url), 'captured': len(captured), 'primary': len(primary), 'resolved': sum(1 for r in R if r['party']),
            'publishers': len({r['party'] for r in R if r['party']}), 'shared': len(shared), 'shared_claims': shared_claims, 'contradictions': ks,
            'revisions': len(revs), 'editors': len({r['editor']['name'] for r in revs if r['editor']['kind'] == 'registered'}), 'anonymous_edits': anon,
            'reverts': len(reverts), 'minor': sum(1 for r in revs if r['minor']), 'size': w['latest']['size'], 'first': revs[0]['timestamp'], 'last': w['latest']['timestamp'],
            'languages': len(w['wd']['sitelinks']) - (1 if w['wd'] and 'commonswiki' in w['wd']['sitelinks'] else 0) if w['wd'] else None, 'links_in': len(w['links_in']['articles'])}

def wiki_graph(w):
    """data/wikipedia/<slug>/graph.json: the article in its own kinds and verbs; sources and parties are the story graph's nodes, borrowed."""
    slug, X, art = w['slug'], w['X'], w['art']
    sc = ONT['scopes']['wikipedia']
    kinds = {t['id'] for t in sc['node_types']}; verbs = {v['verb']: v for v in sc['edges']}
    nodes, edges = OrderedDict(), OrderedDict()
    def node(nid, kind, label, **kw):
        if kind not in kinds: sys.exit(f'wikipedia graph: kind {kind!r} not in the ontology scope')
        if nid not in nodes: nodes[nid] = dict({'id': nid, 'kind': kind, 'label': label}, **{k: v for k, v in kw.items() if v not in (None, '', [])})
        return nid
    def edge(a, verb, b, **kw):
        if verb not in verbs: sys.exit(f'wikipedia graph: verb {verb!r} not in the ontology scope')
        for end in (a, b):
            if end not in nodes: sys.exit(f'wikipedia graph: {a} {verb} {b}: no node {end!r}')
        if a != b: edges.setdefault((a, verb, b), dict({'from': a, 'verb': verb, 'to': b}, **kw))
    base = f'wikipedia/{slug}/'
    A = node('article:' + slug, 'article', art['title'], href=base + 'index.html', url=art['url'], revisions=art['revisions'], latest_revid=art['latest_revid'])
    for s in X['sections']:
        node('section:' + s['id'], 'section', s['title'], href=base + 'statements/index.html#s-' + s['id'])
        edge(A, 'has_section', 'section:' + s['id'])
    for st in X['statements']:
        node('statement:' + st['id'], 'statement', st['text'], href=base + 'statements/index.html#' + st['id'], status=st['class'], cited=st['cited'], section=st['section'])
        edge('section:' + st['section'], 'contains', 'statement:' + st['id'])
        for cve in st['cves']:
            node('cve:' + cve, 'cve', cve, href=f'flaws/index.html#{cve}' if cve in FLAGSHIP else f'https://www.cve.org/CVERecord?id={cve}', zoom=[{'graph': 'data/graph.json', 'focus': 'cve:' + cve, 'label': 'In the story graph'}])
            edge('statement:' + st['id'], 'names', 'cve:' + cve)
    for r in X['references']:
        rid = node(f'reference:{r["n"]}', 'reference', f'[{r["n"]}] {r.get("title") or r.get("url") or "untitled"}', href=base + f'references/index.html#r-{r["n"]}', url=r.get('url'), publisher=r.get('publisher'), date=r.get('date'), where=r.get('where'))
        if r.get('where') == 'infobox':
            edge(A, 'cites', rid)
        for sid in r['cited_by']:
            edge('statement:' + sid, 'cites', rid)
        if r['captured']:
            s = SOURCES[r['captured']]
            node('source:' + r['captured'], 'source', f'{short_name(s)}: {s.get("title") or r["captured"]}', href=f'sources/{r["captured"]}/index.html', zoom=[{'graph': 'data/graph.json', 'focus': 'source:' + r['captured'], 'label': 'In the story graph: the claims that cite it'}], borrowed=True)
            edge(rid, 'captured_as', 'source:' + r['captured'])
        if r['party']:
            e = ENTITIES[r['party']]
            node('party:' + r['party'], 'party', e['name'], href=party_href(r['party']), zoom=[{'graph': 'data/graph.json', 'focus': 'party:' + r['party'], 'label': 'In the story graph'}], borrowed=True, wikidata=wikidata_link(r['party']))
            edge(rid, 'published_by', 'party:' + r['party'])
    latest_ids = {s['id'] for s in X['statements']}
    for r, dlt in zip(w['revs'], w['deltas']):
        rid = node(f'revision:{r["revid"]}', 'revision', f'{fmt_at(r["timestamp"])}: {r["comment"][:80] or "(no summary)"}', href=base + f'history/index.html#rev-{r["revid"]}', at=r['timestamp'], size=r['size'], reverted='mw-reverted' in r['tags'], added=len(dlt['added']), removed=len(dlt['removed']), changed=len(dlt['changed']))
        edge(rid, 'revises', A)
        if r.get('parentid') and f'revision:{r["parentid"]}' in nodes:
            edge(rid, 'follows', f'revision:{r["parentid"]}')
        ed = r['editor']
        eid = 'editor:' + (re.sub(r'[^a-z0-9]+', '-', ed['name'].lower()) if ed['kind'] == 'registered' else ed['kind'])
        node(eid, 'editor', ed['name'] if ed['kind'] == 'registered' else f'{ed["kind"]} editors', href=('https://en.wikipedia.org/wiki/User:' + ed['name'].replace(' ', '_')) if ed['kind'] == 'registered' else None)
        edge(rid, 'made_by', eid)
        for s in dlt['added'] + [c['to'] for c in dlt['changed']]:
            if s['id'] in latest_ids: edge(rid, 'adds', 'statement:' + s['id'])
        for s in dlt['removed'] + [c['from'] for c in dlt['changed']]:
            if s['id'] in latest_ids: edge(rid, 'removes', 'statement:' + s['id'])
    talk = wiki_talk(slug)
    if talk:
        for t in talk['threads']:
            tid = node('thread:' + t['id'], 'thread', t['title'], href=base + 'talk/index.html#' + t['id'], posts=len(t['posts']), request_edit=t['request_edit'], answered=t['answered'], started=t['started'])
            edge(A, 'discussed_in', tid)
            for i, p_ in enumerate(t['posts']):
                pid = node(f'post:{t["id"]}:{i}', 'post', (p_['text'][:90] or '(unsigned)'), href=base + f'talk/index.html#{t["id"]}-{i}', when=p_['when'], request_edit=p_['request_edit'])
                edge(tid, 'has_post', pid)
                if p_['reply_to'] is not None:
                    edge(pid, 'replies_to', f'post:{t["id"]}:{p_["reply_to"]}')
                if p_['who']:
                    eid = 'editor:' + re.sub(r'[^a-z0-9~]+', '-', p_['who'].lower())
                    node(eid, 'editor', p_['who'] + (' (temporary account)' if p_['who'].startswith('~') else ''), href='https://en.wikipedia.org/wiki/User:' + p_['who'].replace(' ', '_'))
                    edge(pid, 'posted_by', eid)
    R = wiki_review(slug)
    if R:
        for fnd in R['findings']:
            fid = node('finding:' + fnd['id'], 'finding', f'{fnd["id"]}: {fnd["kind"]}, {fnd["strength"]}', href=base + 'review/index.html#' + fnd['id'], kind_of=fnd['kind'], strength=fnd['strength'], policy=', '.join(fnd['policy']))
            st = wiki_finding_statement(w, fnd)
            if st: edge(fid, 'questions', 'statement:' + st['id'])
            for src in fnd.get('evidence', {}).get('sources', []):
                s_ = SOURCES[src]
                node('source:' + src, 'source', f'{short_name(s_)}: {s_.get("title") or src}', href=f'sources/{src}/index.html', zoom=[{'graph': 'data/graph.json', 'focus': 'source:' + src, 'label': 'In the story graph: the claims that cite it'}], borrowed=True)
                edge(fid, 'rests_on', 'source:' + src)
        if talk:
            tids = {t['id'] for t in talk['threads']}
            for i, ta in enumerate(R.get('talk', [])):
                if ta['thread'] in tids:
                    fid = node(f'finding:talk-{i}', 'finding', f'Answer: {ta["question"]}', href=base + f'review/index.html#talk-{i}', kind_of='answer')
                    edge(fid, 'answers', 'thread:' + ta['thread'])
                    for src in ta.get('sources', []):
                        s_ = SOURCES[src]
                        node('source:' + src, 'source', f'{short_name(s_)}: {s_.get("title") or src}', href=f'sources/{src}/index.html', zoom=[{'graph': 'data/graph.json', 'focus': 'source:' + src, 'label': 'In the story graph: the claims that cite it'}], borrowed=True)
                        edge(fid, 'rests_on', 'source:' + src)
    if w['wd']:
        wd = w['wd']; L = wd['labels']
        props = {f'{L.get(p, p)} ({p})': '; '.join(str(L.get(v['value'], v['value'])) for v in vs) for p, vs in wd['claims'].items()}
        node('item:' + wd['item'], 'item', f'{wd["item"]}: {wd.get("label") or ""}', href=f'https://www.wikidata.org/wiki/{wd["item"]}', **{k: v for k, v in props.items()})
        edge(A, 'described_by', 'item:' + wd['item'])
    ontology = {'kinds': OrderedDict((t['id'], {'label': t['label'], 'plural': t['plural']}) for t in sc['node_types']),
                'verbs': OrderedDict((v['verb'], {'label': v['verb'].replace('_', ' '), 'inverse': v['inverse'].replace('_', ' ')}) for v in sc['edges'])}
    ontology['kinds']['cve'] = {'label': 'CVE', 'plural': 'CVEs'}
    G = {'site': SITE, 'version': VERSION, 'title': f'Wikipedia: {art["title"]}', 'licence': art['licence'], 'latest_revid': art['latest_revid'],
         'note': "One Wikipedia article as a graph of its own: sections, statements (one per sentence, classed by wording), the references they cite, every revision and its editor, and the Wikidata item. A reference captured in this site's evidence vault is joined to that source, which is where the story graph's claims meet it.",
         'ontology': ontology, 'nodes': list(nodes.values()), 'edges': list(edges.values())}
    write(f'data/wikipedia/{slug}/graph.json', json.dumps(G, indent=1, ensure_ascii=False) + '\n')
    return G

CLASS_WORD = {'quote': 'quote', 'attributed': 'attributed', 'hedged': 'hedged', 'record': 'record', 'stated': 'stated'}

def st_pill(c):
    cls = {'quote': 'info', 'attributed': 'info', 'hedged': 'warn', 'record': 'ok', 'stated': 'mute'}[c]
    return f'<span class="st st-{E(c)} pill-{cls}">{E(CLASS_WORD[c])}</span>'

def wiki_statement_row(w, s, depth):
    up = '../' * depth
    by_n = {r['n']: r for r in w['X']['references']}
    refs = ' '.join(f'<a href="../references/index.html#r-{n}" title="{T(by_n[n].get("title") or by_n[n].get("url") or "")}">[{n}]</a>' for n in s['refs'])
    ev = ''
    if s['captured']:
        ev = ' '.join(f'<a class="cap" href="{up}sources/{U(c)}/index.html">{E(short_name(SOURCES[c]))}</a>' for c in s['captured'])
    elif s['cited']:
        ev = '<span class="small">cited, not yet captured</span>'
    else:
        ev = '<span class="st st-unverified">uncited</span>'
    cl = ' '.join(f'<a href="{up}facts/{U(c)}/index.html">{E(c)}</a>' for c in s['claims'])
    return f'<li id="{E(s["id"])}" class="wst wst-{E(s["class"])}">{st_pill(s["class"])} <span class="wtext">{T(s["text"])}</span> <span class="wrefs">{refs}</span><div class="wev"><b>Evidence:</b> {ev}{(" &middot; <b>Our claims on the same source:</b> " + cl) if cl else ""}</div></li>'

def wiki_evolution_svg(w, depth):
    """Every statement that ever existed as a lifeline: born at the revision that added it, ended at the one that removed it.
    Time runs left to right; the rows are in the order statements first appeared; colour is the class, written in the title."""
    life = wiki_lifelines(w)
    revs = w['revs']
    t0, t1 = revs[0]['timestamp'], revs[-1]['timestamp']
    def T(ts):
        return (datetime.datetime.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S') - datetime.datetime.strptime(t0[:19], '%Y-%m-%dT%H:%M:%S')).total_seconds()
    span = max(1.0, T(t1))
    W, left, right, rh = 1000, 10, 990, 5
    rows = list(life.items())
    H = 30 + rh * len(rows) + 30
    x = lambda ts: left + (right - left) * T(ts) / span
    out = []
    # a day grid
    day = datetime.datetime.strptime(t0[:10], '%Y-%m-%d')
    while day.strftime('%Y-%m-%dT%H:%M:%SZ') <= t1:
        ts = day.strftime('%Y-%m-%dT%H:%M:%SZ')
        if ts >= t0:
            out.append(f'<line class="grid" x1="{x(ts):.1f}" y1="20" x2="{x(ts):.1f}" y2="{H - 25}"/><text class="t" x="{x(ts) + 3:.1f}" y="14">{E(day.strftime("%d %b"))}</text>')
        day += datetime.timedelta(days=1)
    alive = sum(1 for _, l in rows if not l['died'])
    for i, (sid, l) in enumerate(rows):
        y = 28 + i * rh
        x0 = x(l['born_at']); x1 = x(l['died_at']) if l['died_at'] else right
        cls = f'life c-{E(l["class"])}{" dead" if l["died"] else ""}'
        title = f'{l["class"]}, {"removed " + fmt_at(l["died_at"]) if l["died_at"] else "still in the article"}, added {fmt_at(l["born_at"])}: {l["text"][:140]}'
        href = f'../statements/index.html#{E(sid)}' if not l['died'] else f'../history/index.html#rev-{l["died"]}'
        out.append(f'<a href="{U(href)}"><rect class="{cls}" x="{x0:.1f}" y="{y}" width="{max(1.5, x1 - x0):.1f}" height="{rh - 1}"><title>{T_(title)}</title></rect></a>')
    marks = ''.join(f'<rect class="rev{" rv" if set(r["tags"]) & REVERT_TAGS else ""}" x="{x(r["timestamp"]) - 0.5:.1f}" y="{H - 22}" width="1" height="12"><title>{E(fmt_at(r["timestamp"]))}: {T_(r["comment"][:80])}</title></rect>' for r in revs)
    svg = f'<figure class="graph wevo"><svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{len(rows)} statements over {len(revs)} revisions: a bar from the revision that added each one to the one that removed it"><g>{"".join(out)}</g><g>{marks}</g></svg><figcaption>{len(rows)} statements ever written, one row each in the order they first appeared, from {E(fmt_at(t0))} to {E(fmt_at(t1))}: a bar runs from the edit that added a statement to the edit that removed it; {alive} are still in the article. Colour is the class (record, stated, attributed, quote, hedged), named in each bar&#39;s title. The ticks along the foot are the {len(revs)} revisions; a red tick was reverted. Hover or focus a bar to read it; click it to open the statement, or the edit that removed it.</figcaption></figure>'
    return svg, life

def T_(x):
    return T(x)

def wiki_counts_svg(w):
    """Size, references and statements over the revisions, as three lines on one time axis."""
    revs, parsed = w['revs'], w['parsed']
    t0, t1 = revs[0]['timestamp'], revs[-1]['timestamp']
    def T(ts):
        return (datetime.datetime.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S') - datetime.datetime.strptime(t0[:19], '%Y-%m-%dT%H:%M:%S')).total_seconds()
    span = max(1.0, T(t1)); W, H, left, right, top, bot = 1000, 180, 10, 990, 14, 160
    x = lambda ts: left + (right - left) * T(ts) / span
    series = [('bytes', [r['size'] or 0 for r in revs]), ('references', [len(parsed[r['revid']]['references']) for r in revs]), ('statements', [len(parsed[r['revid']]['statements']) for r in revs])]
    paths = ''
    for name, vals in series:
        mx = max(vals) or 1
        pts = ' '.join(f'{x(r["timestamp"]):.1f},{bot - (bot - top) * v / mx:.1f}' for r, v in zip(revs, vals))
        paths += f'<polyline class="ser s-{name}" points="{pts}"><title>{E(name)}: {vals[0]} to {vals[-1]} (most {mx})</title></polyline>'
    legend = ' &middot; '.join(f'{name}: {vals[-1]:,}' for name, vals in series)
    return f'<figure class="graph wcounts"><svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Bytes, references and statements over every revision">{paths}</svg><figcaption>Each line is scaled to its own peak: the article&#39;s bytes, its references and its statements over the {len(revs)} revisions. Now: {legend}.</figcaption></figure>'

def wiki_item_section(w):
    """The Wikidata item's own history: who changed which property, when, from the edit summaries."""
    h = wiki_item_history(w['slug'])
    if not h:
        return ''
    revs = h['revisions']
    prop = re.compile(r'\[\[Property:(P\d+)\]\]')
    L = (w['wd'] or {}).get('labels', {})
    kinds = Counter()
    rows = []
    for r in revs:
        m = re.match(r'/\* ([a-z-]+):', r['comment'])
        act = m.group(1) if m else 'edit'
        kinds[act] += 1
        props = ', '.join(f'{E(L.get(p, p))} ({E(p)})' for p in dict.fromkeys(prop.findall(r['comment'])))
        who = r['editor']['name'] if r['editor']['kind'] == 'registered' else r['editor']['kind']
        rows.append([E(fmt_at(r['timestamp'])), E(who), E(act), props or T(re.sub(r'/\*.*?\*/', '', r['comment']).strip()[:100])])
    by_day = Counter(r['timestamp'][:10] for r in revs)
    return (f'<p>The item has {len(revs)} revisions, from {E(fmt_at(revs[0]["timestamp"]))} (created from the Finnish Wikipedia&#39;s side, two hours after the English article) to {E(fmt_at(revs[-1]["timestamp"]))}, by {len({r["editor"]["name"] for r in revs if r["editor"]["kind"] == "registered"})} named editors; by day: ' + ', '.join(f'{d} ({n})' for d, n in sorted(by_day.items())) + '. Kinds of edit: ' + ', '.join(f'{k} ({n})' for k, n in kinds.most_common()) + '.</p>'
            + '<details><summary>Every edit of the item</summary>' + table(['When', 'Editor', 'Edit', 'Property or summary'], list(reversed(rows))) + '</details>')

def build_wikipedia_more(slug, w, L):
    """The evolution and talk pages of one article, built after the article's own pages."""
    art, base = w['art'], f'wikipedia/{slug}/'
    svg, life = wiki_evolution_svg(w, 2)
    counts = wiki_counts_svg(w)
    by_class = Counter(l['class'] for l in life.values())
    dead = sum(1 for l in life.values() if l['died'])
    longest = sorted(((l['born_at'], l) for l in life.values() if not l['died']), key=lambda x: x[0])[:5]
    shortest = sorted((l for l in life.values() if l['died_at']), key=lambda l: (datetime.datetime.strptime(l['died_at'][:19], '%Y-%m-%dT%H:%M:%S') - datetime.datetime.strptime(l['born_at'][:19], '%Y-%m-%dT%H:%M:%S')).total_seconds())[:8]
    li = lambda items: '<ul>' + ''.join(items) + '</ul>'
    body = f'''
<p class="crumb"><a href="../../index.html">Wikipedia, as a graph</a> / <a href="../index.html">{E(art["title"])}</a> / Evolution</p>
<h1>The evolution of Wikipedia&#39;s {E(art["title"])} article</h1>
<p class="lead">{len(life)} statements have been written into the article since {E(fmt_at(w["revs"][0]["timestamp"]))}; {len(life) - dead} are in it now and {dead} were removed or reworded on the way. Every edit is a point in time, every statement a bar from the edit that added it to the edit that took it out, so the picture shows what the article was at any moment, what has survived, and what the editors did not keep. The data is every revision, read by the same parser as the rest of this section.</p>
{svg}
{section("counts", "Size, references and statements", counts)}
{section("survivors", "What has survived longest", '<p>The statements that have been in the article longest, unchanged in wording:</p>' + li([f'<li>{E(fmt_at(b))}: <a href="../statements/index.html#{E([k for k, v in life.items() if v is l][0])}">{T(l["text"][:160])}</a></li>' for b, l in longest]))}
{section("brief", "What lasted least", '<p>The statements removed soonest after they were written, with the edit that removed them: where the article&#39;s editors disagreed with a contributor, or a contributor with themselves.</p>' + li([f'<li>{T(l["text"][:160])} <span class="small">(added {E(fmt_at(l["born_at"]))}, removed {E(fmt_at(l["died_at"]))}: <a href="../history/index.html#rev-{E(str(l["died"]))}">the edit</a>)</span></li>' for l in shortest]))}
{section("classes", "By class, over the whole history", table(["Class", "Ever written", "In the article now"], [[st_pill(c), E(str(by_class.get(c, 0))), E(str(sum(1 for l in life.values() if l["class"] == c and not l["died"])))] for c in ("record", "stated", "attributed", "quote", "hedged")]))}
{section("item", "The Wikidata item, over time", wiki_item_section(w) or '<p class="small">No item history fetched.</p>')}
<p class="small">The text is Wikipedia&#39;s, CC BY-SA 4.0, by its contributors.</p>
'''
    page(base + 'evolution/index.html', f'The evolution of Wikipedia&#39;s {art["title"]} article', f'Every statement ever written into the article as a lifeline from the edit that added it to the edit that removed it, with the size, references and statements over all {len(w["revs"])} revisions, and the Wikidata item\'s own history.', body, kind='evidence', topics=f'wikipedia {slug} evolution')
    talk = wiki_talk(slug)
    if not talk:
        return
    threads = talk['threads']
    posts = sum(len(t['posts']) for t in threads)
    secs = ''
    for t in threads:
        items = ''
        for i, p_ in enumerate(t['posts']):
            who = (f'<a href="https://en.wikipedia.org/wiki/User:{U(p_["who"].replace(" ", "_"))}" rel="noopener">{E(p_["who"])}</a>' + (' <span class="small">(temporary account)</span>' if p_['who'].startswith('~') else '')) if p_['who'] else '<i>unsigned</i>'
            flags = (' <span class="st st-stated">request edit</span>' if p_['request_edit'] else '') + (' <span class="st st-confirmed">answered</span>' if p_['answered'] else '')
            items += f'<li id="{E(t["id"])}-{i}" class="wpost d{min(p_["depth"], 6)}"><b>{who}</b> <span class="small">{E(fmt_at(p_["when"])) if p_["when"] else ""}</span>{flags}<br>{T(p_["text"])}</li>'
        head = f'{E(t["title"])} <span class="small">({len(t["posts"])} post{"s" if len(t["posts"]) != 1 else ""}{", " + E(fmt_at(t["started"])) if t["started"] else ""})</span>' + (' <span class="st st-stated">request edit</span>' if t['request_edit'] else '')
        secs += section(t['id'], head, f'<ol class="wthread">{items}</ol>')
    req = [t for t in threads if t['request_edit']]
    body = f'''
<p class="crumb"><a href="../../index.html">Wikipedia, as a graph</a> / <a href="../index.html">{E(art["title"])}</a> / The talk page</p>
<h1>What Wikipedia&#39;s editors discuss about the {E(art["title"])} article</h1>
<p class="lead">The article&#39;s <a href="{U(talk["art"]["url"])}" rel="noopener">talk page</a>, as threads: {len(threads)} discussions, {posts} signed posts, {talk["art"]["revisions"]} revisions of the page since {E(fmt_at(talk["revs"][0]["timestamp"]))}. This is where corrections are argued, where outside parties ask for changes without editing the article ({len(req)} thread{"s" if len(req) != 1 else ""} use the edit-request process, with a disclosed conflict of interest), and where readers say what the article does not yet explain. Every post links to its author&#39;s public Wikipedia page; a temporary account is Wikipedia&#39;s own pseudonym for a logged-out editor.</p>
{secs}
<p class="small">The posts are their authors&#39;, CC BY-SA 4.0, shown as text.</p>
'''
    page(base + 'talk/index.html', f'What Wikipedia&#39;s editors discuss about the {art["title"]} article', f'The talk page of the article as threads: {len(threads)} discussions and {posts} posts, including the edit requests outside parties made with a disclosed conflict of interest.', body, kind='evidence', topics=f'wikipedia {slug} talk')

STRENGTH_WORD = {'high': ('The article should change', 'contradicted'), 'medium': ('The article should attribute or qualify', 'disputed'), 'low': ('Housekeeping', 'unverified'), 'confirmed': ('Holds against this site\'s evidence', 'confirmed')}

def build_wikipedia_review(slug, w, L):
    """This site's review of the article, done as a Wikipedia reviewer would, from data/wikipedia/<slug>/review.json."""
    R = wiki_review(slug)
    if not R:
        return 0
    art, base = w['art'], f'wikipedia/{slug}/'
    cl = {c['id']: c for c in D['claims']}
    ks = {k['id']: k for k in load('factcheck')['contradictions']}
    talk = wiki_talk(slug)
    threads = {t['id']: t for t in talk['threads']} if talk else {}
    li = lambda items: '<ul>' + ''.join(items) + '</ul>'
    def ev_block(ev):
        out = ''
        if ev.get('claims'):
            out += '<p class="small"><b>This site&#39;s claims:</b> ' + ', '.join(f'<a href="../../../facts/{U(c)}/index.html">{E(c)}</a> <span class="st st-{E(cl[c]["status"])}">{E(cl[c]["status"])}</span>' for c in ev['claims']) + '</p>'
        if ev.get('contradictions'):
            out += '<p class="small"><b>Contradictions:</b> ' + ', '.join(f'<a href="../../../factcheck/index.html#{E(k)}">{E(k)}</a>: {T(ks[k]["measure"])} ({E(ks[k]["status"])})' for k in ev['contradictions']) + '</p>'
        if ev.get('sources'):
            out += '<p class="small"><b>Captured pages:</b> ' + ' '.join(f'<a class="cap" href="../../../sources/{U(x)}/index.html">{E(short_name(SOURCES[x]))}</a>' for x in ev['sources']) + '</p>'
        if ev.get('desk'):
            out += f'<p class="small"><b>The fact-check desk:</b> {E(ev["desk"])}</p>'
        return out
    order = ['high', 'medium', 'low', 'confirmed']
    secs = ''
    for strength in order:
        fs = [f for f in R['findings'] if f['strength'] == strength]
        if not fs: continue
        items = ''
        for f in fs:
            st = wiki_finding_statement(w, f)
            quoted = f'<a href="../statements/index.html#{E(st["id"])}">{T(st["text"])}</a> {st_pill(st["class"])}' if st else f'<i>{T(f["starts"])}</i> <span class="st st-unverified">no longer in the article as worded</span>'
            pol = ' '.join(f'<a href="https://en.wikipedia.org/wiki/{U(p_.replace(":", ":"))}" rel="noopener" title="{E(R["policies"].get(p_, ""))}"><code>{E(p_)}</code></a>' for p_ in f['policy'])
            items += f"""<li id="{E(f["id"])}" class="wfinding"><p><b>{E(f["id"])}</b> &middot; {E(f["section"])} &middot; {E(f["kind"])} &middot; {pol}</p>
<blockquote>{quoted}</blockquote>
<p>{T(f["finding"])}</p>{ev_block(f.get("evidence", {}))}
<p class="wchange"><b>Change proposed:</b> {T(f["change"])}</p></li>"""
        word, cls = STRENGTH_WORD[strength]
        secs += section(strength, f'{word} ({len(fs)})', f'<ol class="wfindings">{items}</ol>')
    talk_items = ''
    for i, ta in enumerate(R.get('talk', [])):
        t = threads.get(ta['thread'])
        head = f'<a href="../talk/index.html#{E(ta["thread"])}">{E(t["title"])}</a>' if t else E(ta['question'])
        talk_items += f'<li id="talk-{i}"><p><b>{head}</b></p><p>{T(ta["what_this_site_holds"])}</p><p class="small"><b>Captured pages:</b> ' + ' '.join(f'<a class="cap" href="../../../sources/{U(x)}/index.html">{E(short_name(SOURCES[x]))}</a>' for x in ta.get('sources', [])) + '</p></li>'
    missing = li([f'<li><a href="../../../facts/{U(c)}/index.html">{E(c)}</a>: {T(cl[c]["claim"][:200])} <span class="st st-{E(cl[c]["status"])}">{E(cl[c]["status"])}</span></li>' for c in R.get('missing_from_the_article', [])])
    pol_rows = [[f'<a href="https://en.wikipedia.org/wiki/{U(k)}" rel="noopener"><code>{E(k)}</code></a>', E(v)] for k, v in R['policies'].items()]
    n = Counter(f['strength'] for f in R['findings'])
    body = f'''
<p class="crumb"><a href="../../index.html">Wikipedia, as a graph</a> / <a href="../index.html">{E(art["title"])}</a> / A reviewer&#39;s reading</p>
<h1>Wikipedia&#39;s {E(art["title"])} article, read as one of its reviewers would</h1>
<p class="lead">{len(R["findings"])} findings on revision <code>{E(str(R["revision"]))}</code>, reviewed {E(R["reviewed"])}: {n.get("high", 0)} where this site&#39;s evidence says the article should change, {n.get("medium", 0)} where it should attribute or qualify, {n.get("low", 0)} of housekeeping, and {n.get("confirmed", 0)} where the article holds exactly against the captures. Each finding names the statement, the Wikipedia policy or guideline it rests on, the captured pages in this site&#39;s evidence vault that bear on it, and a change in the shape Wikipedia asks for: specific, uncontroversial, necessary and sensible. {len(R.get("talk", []))} questions asked on the article&#39;s <a href="../talk/index.html">talk page</a> are answered from the same captures.</p>
<p class="disc">&#9888; Nothing on this page is posted to Wikipedia, and no agent of this site will post it. Wikipedia&#39;s guideline on large language models (March 2026) does not accept article text, talk-page comments or edit requests written by a model, and this page was written by one. It is for a person to read, check against the captures, and, where they agree, put to the talk page in their own words, with their connection to this site disclosed and the independent sources named. This site is self-published and is not a source Wikipedia can cite; none of the changes proposed here cites it. <a href="../../for-editors/index.html">For Wikipedia&#39;s editors</a> says how this site means to work with the article&#39;s editors.</p>
<p class="small">{T(R["method"])}</p>
{secs}
{section("talk", f"Questions on the talk page, answered from the captures ({len(R.get('talk', []))})", f'<ol class="wfindings">{talk_items}</ol>' if talk_items else '<p class="small">None.</p>')}
{section("missing", f"What this site holds that the article does not say ({len(R.get('missing_from_the_article', []))})", '<p>Claims of this site, each with its own captures and the fact-check desk&#39;s status, on matters the article does not cover. Whether any belongs in the article is for its editors: Wikipedia weighs what reliable secondary sources have covered, not what a primary capture shows.</p>' + missing)}
{section("policies", "The policies and guidelines named", '<p>Each in Wikipedia&#39;s own words, shortened; the links go to the policy pages.</p>' + table(["Policy", "What it asks"], pol_rows))}
{section("limits", "What this review cannot see", f'<p>{T(R["not_held_here"])} The review is of one revision; the article changes several times a day, and a finding is matched to its statement by its opening words, so a finding whose statement has since been reworded is marked as such above rather than dropped. The next pass of this site&#39;s ontologist re-reads the article against the same findings.</p>')}
<p class="small">The text quoted is Wikipedia&#39;s, <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener">CC BY-SA 4.0</a>, by its contributors; the findings are this site&#39;s, CC BY 4.0. The data is <a href="../../../data/wikipedia/{U(slug)}/review.json">review.json</a>.</p>
'''
    page(base + 'review/index.html', f'Wikipedia&#39;s {art["title"]} article, read as one of its reviewers would', f'{len(R["findings"])} findings on the article against this site\'s captured evidence, each with the Wikipedia policy it rests on and a change proposed for a human to put to the talk page; nothing is posted by an agent.', body, kind='evidence', topics=f'wikipedia {slug} review')
    return len(R['findings'])

def build_wikipedia_editors(cards):
    """The page for Wikipedia's editors: what this site is, what it offers, and the rules it holds itself to."""
    rows = []
    for slug, art, L in cards:
        rows.append([f'<a href="../{U(slug)}/index.html">{E(art["title"])}</a>', f'<a href="../{U(slug)}/references/index.html">{L["captured"]} of {L["with_url"]}</a>', f'<a href="../{U(slug)}/review/index.html">{wiki_review(slug) and len(wiki_review(slug)["findings"]) or 0}</a>', f'<a href="../{U(slug)}/talk/index.html">{E(str(L["revisions"]))} revisions read</a>'])
    body = f'''
<p class="crumb"><a href="../index.html">Wikipedia, as a graph</a> / For Wikipedia&#39;s editors</p>
<h1>For the editors of Wikipedia&#39;s articles on this story</h1>
<p class="lead">This site is a newsroom of software agents and one human editor, Dinis Cruz, publishing on one story: the PHP2Shell vulnerabilities of October 2026. It reads your article every four hours, keeps every revision, and holds dated, hashed captures of many of the pages your article cites. This page says what it is, what it can offer the article&#39;s editors, and the rules it holds itself to, so that the two can work together without this site ever editing the article.</p>
{section("what", "What this site is, in Wikipedia&#39;s terms", '<p>A self-published source (<code>WP:SPS</code>), written largely by language models (<code>WP:RSML</code>): not a reliable source for an article, and it does not ask to be cited or linked. Its value to an editor is different: it keeps the primary record. Every page it cites is captured into an evidence vault with a time and a hash, so a page that has since been edited or removed can be read as it was when the article&#39;s reference was written; every number has a date; every disagreement between sources is a row in a <a href="../../factcheck/index.html">contradiction ledger</a> with both sides quoted; its own errors are corrected on a <a href="../../corrections/index.html">corrections page</a>, never silently.</p>')}
{section("offer", "What it offers", '<ul><li><b>Captures of the pages the article cites.</b> <a href="../php2shell/references/index.html">Every reference</a> of the article is matched to a capture where this site holds one; each capture has a UTC time and a SHA-256 hash, and the text as fetched. Where a cited page has changed since the citation was written, the capture shows the wording the citing editor saw. (The archive an article should link is the Wayback Machine, not this site; the captures are for checking, not citing.)</li><li><b>A reading of the article against the evidence.</b> <a href="../php2shell/review/index.html">A reviewer&#39;s reading</a>: findings against the article&#39;s own policies, with the captures, and a proposed change in the shape an edit request takes. Written by a model, so by Wikipedia&#39;s rule it is material for a person to check and put in their own words, never pasted.</li><li><b>Answers to questions asked on the talk page</b>, from the same captures, on the same page.</li><li><b>A timeline in UTC</b> of the disclosure, the leak, the release and the responses, with each time&#39;s source: <a href="../../timeline/index.html">the timeline</a>.</li><li><b>Drawings built by code from the published diff</b> of the fix, under CC BY 4.0, for the diagram the talk page asks for; any upload is a human contributor&#39;s, under Wikipedia&#39;s own rules on images.</li></ul>')}
{section("rules", "The rules this site holds itself to", '<ol><li><b>No agent of this site edits Wikipedia</b>, any article, any talk page, any item on Wikidata. Its software reads; it never writes.</li><li><b>No edit request, comment or text written by a model is posted</b>, by anyone, on this site&#39;s behalf. Where the human editor of this site posts on a talk page, it is in his own words, signed, with his connection to this site disclosed (<code>WP:COI</code>, <code>WP:DISCLOSE</code>), in the edit-request form (<code>WP:EDITREQ</code>), citing independent sources only.</li><li><b>No request to cite or link this site.</b> This site is not a reliable source for Wikipedia and does not ask to be one (<code>WP:SPS</code>, <code>WP:ADV</code>). If an editor finds a capture useful, the thing to cite is the captured page, with the Wayback Machine as its archive.</li><li><b>What it takes, it attributes.</b> The article&#39;s text is republished here under CC BY-SA 4.0, with the revision id as the attribution; the pages and data that carry it are under the same licence, and what was changed (parsed into sentences, classed by wording) is stated on each page.</li><li><b>Corrections first.</b> Where the article shows this site to be wrong, this site&#39;s page is corrected first, and the correction is dated and kept.</li><li><b>It reads the talk page.</b> Every four hours. A question asked there about the facts of the story is answered on this site&#39;s review page from the captures, where a person can read it; it is not answered on the talk page by an agent.</li></ol>')}
{section("together", "How the two could work together", '<p>Wikipedia&#39;s strength is review by many people against written policy; this site&#39;s is a dated, hashed record of the primary pages and every change in them. The join is the evidence. An editor who wants to check a citation can read the capture; a reviewer who wants to know whether a figure was ever stated by its source can read the <a href="../../factcheck/index.html">fact-check desk&#39;s</a> grade and the excerpt it rests on; a contributor who wants the sequence of a day in UTC can take it from the timeline, with its sources. Nothing of this needs the article to mention this site. The one thing this site asks is that an editor who finds an error here say so, on the talk page or by the means on its <a href="../../feedback/index.html">feedback page</a>, so it can be corrected.</p>')}
{section("articles", "The articles read", table(["Article", "References captured here", "Findings", "History"], rows))}
<p class="small">The attribution Wikipedia asks of reusers, as this site gives it on each page of this section: <i>This page uses material from the Wikipedia article &ldquo;PHP2Shell&rdquo;, which is released under the Creative Commons Attribution-Share-Alike License 4.0.</i> The text here that is this site&#39;s own is CC BY 4.0.</p>
'''
    page('wikipedia/for-editors/index.html', 'For the editors of Wikipedia&#39;s articles on this story', 'What this site is in Wikipedia\'s terms, what it offers the article\'s editors (dated, hashed captures of the cited pages, a reviewer\'s reading, answers from the captures), and the rules it holds itself to: no agent edits Wikipedia, nothing written by a model is posted, no request to be cited.', body, kind='evidence', topics='wikipedia editors collaboration')

def wiki_sister_section(cards):
    """Wikidata and DBpedia: what each holds for the articles read, and what has changed in them."""
    rows = []
    for slug, art, L in cards:
        w = wiki_load(slug)
        wd = w['wd']
        h = wiki_item_history(slug)
        dbp = json.load(open(os.path.join(ROOT, 'data', 'wikipedia', slug, 'article.json'), encoding='utf-8')).get('dbpedia')
        item = f'<a href="https://www.wikidata.org/wiki/{E(wd["item"])}" rel="noopener"><code>{E(wd["item"])}</code></a>' if wd else 'none'
        hist = f'{len(h["revisions"])} revisions, last {E(fmt_at(h["revisions"][-1]["timestamp"]))}' if h else 'not fetched'
        rows.append([f'<a href="{U(slug)}/index.html">{E(art["title"])}</a>', item, E(str(len(wd['claims']))) + ' claims' if wd else '', hist, (f'HTTP {E(str(dbp.get("status")))}' + (', not yet extracted' if dbp.get('status') == 404 else '')) if dbp else 'not checked'])
    links = json.load(open(os.path.join(ROOT, 'data', 'wikidata-links.json'), encoding='utf-8'))['parties'] if os.path.exists(os.path.join(ROOT, 'data', 'wikidata-links.json')) else {}
    n_conf = sum(1 for v in links.values() if v.get('confirmed')); n_prop = sum(1 for v in links.values() if v.get('proposed') and not v.get('confirmed'))
    return (f'<p>Wikidata is the structured sister of Wikipedia: one item per thing, with typed claims, edited in the open with the same history as an article. DBpedia is the older extraction of the same facts from Wikipedia&#39;s infoboxes, built from periodic dumps. This site reads both for the articles it watches, keeps the item&#39;s own history (on each article&#39;s <a href="php2shell/evolution/index.html#item">evolution page</a>), and looks the parties of its own graph up on Wikidata so that a party here can carry the item that is already there, rather than a new identifier: {len(links)} parties looked up, {n_conf} items confirmed by hand, {n_prop} proposed and waiting. The lookups are in <a href="../data/wikidata-links.json">wikidata-links.json</a>; the build shows only confirmed items.</p>'
            + table(["Article", "Wikidata item", "Claims", "Item history", "DBpedia"], rows)
            + '<p class="small">Learned from them so far: an item is created by whichever language edition gets there first (this one from the Finnish Wikipedia, two hours after the English article); its claims are typed and sourced one by one, which is the shape this site&#39;s own attribution rows take; and an identifier that exists already is the one to use.</p>')

def build_wikipedia():
    slugs = wiki_articles()
    if not slugs:
        return
    cards = []
    for slug in slugs:
        w = wiki_load(slug)
        G = wiki_graph(w)
        L = wiki_ledger(w)
        art, X = w['art'], w['X']
        base = f'wikipedia/{slug}/'
        # ---- the article page
        counts = ' '.join(f'<span class="stat"><b>{E(str(n))}</b><span>{E(k)}</span></span>' for k, n in [('statements', L['statements']), ('cited', L['cited']), ('references', L['references']), ('captured here', L['captured']), ('revisions', L['revisions']), ('editors', L['editors']), ('languages', L['languages'] or 0)])
        classes = table(['Class', 'What it means', 'Statements'], [[st_pill(c), E(ONT['scopes']['wikipedia']['taxonomy'][0]['reads'][c]), E(str(L['classes'].get(c, 0)))] for c in ('record', 'stated', 'attributed', 'quote', 'hedged')])
        since = w['since_capture']
        cap_line = (f'<p>This site&#39;s evidence vault captured the article at <code>{E(w["capture"]["captures"][-1]["stamp"])}</code>, when it was at revision <code>{E(str(w["capture_rev"]["revid"]))}</code>. Since then: <b>{len(since["added"])}</b> statements added, <b>{len(since["removed"])}</b> removed, <b>{len(since["changed"])}</b> reworded, <b>{len(since["refs_added"])}</b> references added and <b>{len(since["refs_removed"])}</b> removed, over {sum(1 for r in w["revs"] if r["timestamp"] > w["capture_rev"]["timestamp"])} revisions. <a href="history/index.html">Every edit</a>.</p>'
                    if since else '<p>This site&#39;s evidence vault has not captured the article yet.</p>')
        widget = sg_graph(base + 'index.html', src=f'data/wikipedia/{slug}/graph.json', focus='article:' + slug, depth=1,
                          fallback=f'<p>The interactive graph needs JavaScript. The same nodes are on <a href="statements/index.html">every statement</a>, <a href="references/index.html">every reference</a> and <a href="history/index.html">every edit</a>; the graph is <a href="../../data/wikipedia/{U(slug)}/graph.json">graph.json</a>.</p>')
        wd = w['wd']
        wd_t = ''
        if wd:
            Lb = wd['labels']
            rows = [[E(f'{Lb.get(p, p)}'), f'<code>{E(p)}</code>', T('; '.join(str(Lb.get(v["value"], v["value"])) for v in vs))] for p, vs in wd['claims'].items() if p not in ('P18', 'P154', 'P373')]
            wd_t = f'<p>Wikidata, the structured sister of Wikipedia, holds item <a href="https://www.wikidata.org/wiki/{E(wd["item"])}" rel="noopener"><code>{E(wd["item"])}</code></a>, &ldquo;{T(wd.get("description"))}&rdquo;, with links to the article in {L["languages"]} languages. Its claims, as fetched (DBpedia, the older extraction, is built from periodic dumps and had no entry for the article when this was built):</p>' + table(['Property', 'Id', 'Value'], rows)
        li = lambda items: '<ul>' + ''.join(items) + '</ul>'
        uncited = li([f'<li><a href="statements/index.html#{E(s["id"])}">{T(s["text"][:140])}</a></li>' for s in L['uncited']]) if L['uncited'] else '<p class="small">None: every statement carries a reference.</p>'
        shared = li([f'<li><a href="../../sources/{U(r["captured"])}/index.html">{E(short_name(SOURCES[r["captured"]]))}</a>: cited by {len(r["cited_by"])} statement{"s" if len(r["cited_by"]) != 1 else ""} there and by {", ".join(f"<a href=\"../../facts/{U(c)}/index.html\">{E(c)}</a>" for c in r["claims"])} here</li>' for r in X['references'] if r['claims']]) if L['shared'] else '<p class="small">None yet.</p>'
        ks = li([f'<li><a href="../../factcheck/index.html#{E(k["id"])}">{E(k["id"])}</a>: {T(k["measure"])} ({E(k["status"])})</li>' for k in L['contradictions']]) if L['contradictions'] else '<p class="small">None.</p>'
        body = f'''
<p class="crumb"><a href="../index.html">Wikipedia, as a graph</a> / {E(art["title"])}</p>
<h1>Wikipedia&#39;s {E(art["title"])} article, as a graph</h1>
<p class="lead">The English Wikipedia article <a href="{U(art["url"])}" rel="noopener">{E(art["title"])}</a>, read as a fractal semantic graph: {L["statements"]} statements in {len(X["sections"])} sections, {L["references"]} references, {L["revisions"]} revisions by {L["editors"]} named editors since {E(fmt_at(L["first"]))}, and its Wikidata item. {L["captured"]} of its {L["with_url"]} references are captured in this site&#39;s evidence vault, where {L["shared"]} of them are also cited by this site&#39;s claims: that is where the article&#39;s facts and this site&#39;s meet. Latest revision read: <code>{E(str(art["latest_revid"]))}</code>, {E(fmt_at(L["last"]))}.</p>
<div class="stats">{counts}</div>
{widget}
{section("facts", "Facts and the words around them", f'<p>Wikipedia&#39;s own rule is that an article states facts and attributes opinions. Read by wording, never by whether a sentence holds, the {L["statements"]} statements fall into five classes; {L["cited"]} carry a reference and {L["with_evidence"]} rest on a page this site has captured. <a href="statements/index.html">Every statement, with its evidence</a>.</p>' + classes + '<h3>Statements with no reference (' + str(len(L["uncited"])) + ')</h3>' + uncited)}
{section("meet", "Where the article and this site meet", f'<p>{L["shared"]} references are pages this site&#39;s claims also cite. A statement there and a claim here that rest on the same captured page meet at that page: there is no &ldquo;same as&rdquo; edge, the shared evidence is the join. <a href="references/index.html">Every reference</a>.</p>' + shared + f'<h3>Contradictions this site records on that shared evidence ({len(L["contradictions"])})</h3>' + ks)}
{section("delta", "What changed since this site captured it", cap_line + f'<p>{L["reverts"]} of the {L["revisions"]} revisions were reverts or were reverted; {L["minor"]} were marked minor; {L["anonymous_edits"]} were anonymous. The article is now {L["size"]:,} bytes.</p>')}
{section("wikidata", "The Wikidata item", wd_t or '<p class="small">No Wikidata item was fetched.</p>')}
{section("more", "The article over time, and its talk page", '<p><a href="evolution/index.html">The evolution</a>: every statement ever written as a bar from the edit that added it to the edit that removed it, the size and references over time, and the Wikidata item&#39;s own history. <a href="talk/index.html">The talk page</a>: what the editors discuss, including the edit requests outside parties made with a disclosed conflict of interest. <a href="review/index.html">A reviewer&#39;s reading</a>: the article against this site&#39;s captures, finding by finding, for a person to take to the talk page.</p>')}
{section("links", "What links here", f'<p>{L["links_in"]} other articles link to this one, which is how a reader of Wikipedia arrives: from <i>PHP</i>, <i>2026</i>, the lists of security incidents, the pages of the companies named. The list is in <a href="../../data/wikipedia/{U(slug)}/links-in.json">links-in.json</a>.</p>')}
{section("trust", "Towards a measure of trust", f'<p>The editor&#39;s working view is that Wikipedia is a trusted source, and that this should be shown rather than assumed: by how often its statements are later corrected, against how often other publications are. This page does not compute a score; it keeps the counts a proof would start from, and the fact-check desk grades statements, not pages. For this article: {L["cited"]} of {L["statements"]} statements cited ({100 * L["cited"] // max(1, L["statements"])}%); {L["captured"]} of {L["with_url"]} references captured here, {L["primary"]} of those primary sources; {L["reverts"]} reverts in {L["revisions"]} revisions; {len(L["contradictions"])} of this site&#39;s contradictions touch evidence the article also cites.</p><p class="small">The text is Wikipedia&#39;s, <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener">CC BY-SA 4.0</a>, by its contributors; the revision ids are the attribution, and this site&#39;s pages and data that carry it are under the same licence: this page uses material from the Wikipedia article &ldquo;{E(art["title"])}&rdquo; (<a href="{U(art["url"])}" rel="noopener">link</a>), released under the <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener">Creative Commons Attribution-Share-Alike License 4.0</a>. It is republished so it can be read as a graph, diffed and followed to its evidence; nothing here is Wikipedia&#39;s view, and nothing on Wikipedia is this site&#39;s.</p>')}
'''
        page(base + 'index.html', f'Wikipedia&#39;s {art["title"]} article, as a graph', f'The English Wikipedia article on {art["title"]} read as a fractal semantic graph: {L["statements"]} statements classed as facts, attributions and quotes, {L["references"]} references and which are captured here, {L["revisions"]} revisions, and where it meets this site\'s claims.', body, kind='evidence', topics=f'wikipedia {slug} graph')
        # ---- statements
        secs = ''
        for sec in X['sections']:
            items = ''.join(wiki_statement_row(w, s, 3) for s in X['statements'] if s['section'] == sec['id'])
            if items: secs += section('s-' + sec['id'], sec['title'], f'<ol class="wstatements">{items}</ol>')
        legend = ' '.join(st_pill(c) + ' ' + E(ONT['scopes']['wikipedia']['taxonomy'][0]['reads'][c]) for c in ('record', 'stated', 'attributed', 'quote', 'hedged'))
        body = f'''
<p class="crumb"><a href="../../index.html">Wikipedia, as a graph</a> / <a href="../index.html">{E(art["title"])}</a> / Every statement</p>
<h1>Every statement in Wikipedia&#39;s {E(art["title"])} article, with its evidence</h1>
<p class="lead">One statement per sentence of revision <code>{E(str(art["latest_revid"]))}</code>, in the article&#39;s order, each classed by its wording and followed by its references, the capture this site holds of them, and the claims of this site that rest on the same page. Read by a parser (<code>admin/build/wikitext.py</code>), never by a model.</p>
<p class="small">{legend}</p>
{secs}
<p class="small">The text is Wikipedia&#39;s, CC BY-SA 4.0, by its contributors.</p>
'''
        page(base + 'statements/index.html', f'Every statement in Wikipedia&#39;s {art["title"]} article, with its evidence', f'All {L["statements"]} statements of the article, classed as record, stated, attributed, quote or hedged by their wording, with their references, the captures this site holds and the claims that share them.', body, kind='evidence', topics=f'wikipedia {slug} statements')
        # ---- references
        rows = []
        for r in X['references']:
            pub = f'<a href="../../../{U(party_href(r["party"]))}">{E(ENTITIES[r["party"]]["name"])}</a>' if r['party'] else f'<span class="small">{T(r.get("publisher") or r.get("host") or "?")}</span>'
            cap = f'<a class="cap" href="../../../sources/{U(r["captured"])}/index.html">captured</a>' if r['captured'] else ('<span class="st st-unverified">not captured</span>' if r.get('url') else '<span class="small">no URL</span>')
            cl = ', '.join(f'<a href="../../../facts/{U(c)}/index.html">{E(c)}</a>' for c in r['claims'])
            st = ', '.join(f'<a href="../statements/index.html#{E(s)}">#{E(s[:4])}</a>' for s in r['cited_by']) or ('<span class="small">the infobox</span>' if r.get('where') == 'infobox' else '')
            link = f'<a href="{U(r["url"])}" rel="noopener">{T(r.get("title") or r["url"])}</a>' if r.get('url') else T(r.get('title') or '(no URL)')
            rows.append([f'<span id="r-{r["n"]}"></span>{r["n"]}', link + (f'<br><span class="small">{T(r.get("date") or "")}</span>' if r.get('date') else ''), pub, cap, st or '<span class="small">none</span>', cl or '<span class="small">none</span>'])
        body = f'''
<p class="crumb"><a href="../../index.html">Wikipedia, as a graph</a> / <a href="../index.html">{E(art["title"])}</a> / Every reference</p>
<h1>Every reference in Wikipedia&#39;s {E(art["title"])} article</h1>
<p class="lead">{L["references"]} references at revision <code>{E(str(art["latest_revid"]))}</code>: {L["captured"]} are pages this site&#39;s evidence vault holds, {L["with_url"] - L["captured"]} are not yet captured, and {L["resolved"]} resolve to a party this site knows. A reference this site has captured is evidence this site can cite as its own, with the capture&#39;s hash; a reference it has not is a request to the collectors (board). The publisher is read from the page&#39;s address first, so the Y Combinator forum is not The Hacker News.</p>
{table(["#", "Reference", "Publisher", "Here", "Cited by", "Our claims on it"], rows)}
'''
        page(base + 'references/index.html', f'Every reference in Wikipedia&#39;s {art["title"]} article', f'All {L["references"]} references of the article: which this site has captured, who publishes each, which statements cite it and which of this site\'s claims rest on the same page.', body, kind='evidence', topics=f'wikipedia {slug} references')
        # ---- history
        revs, deltas = w['revs'], w['deltas']
        by_hour = Counter(r['timestamp'][:13] for r in revs)
        hours = sorted(by_hour)
        mx = max(by_hour.values())
        bw = max(4, min(12, 900 // max(1, len(hours))))
        bars = ''.join(f'<rect x="{10 + i * bw}" y="{120 - 100 * by_hour[h] / mx:.1f}" width="{bw - 1}" height="{100 * by_hour[h] / mx:.1f}"><title>{E(h)}:00 UTC: {by_hour[h]} edits</title></rect>' for i, h in enumerate(hours))
        chart = f'<figure class="graph"><svg viewBox="0 0 {20 + len(hours) * bw} 130" width="100%" role="img" aria-label="Edits per hour, {E(hours[0])} to {E(hours[-1])}"><g class="bars">{bars}</g><text class="t" x="10" y="12">edits per hour (most: {mx})</text></svg><figcaption>Every hour from {E(fmt_at(revs[0]["timestamp"]))} to {E(fmt_at(revs[-1]["timestamp"]))}, UTC.</figcaption></figure>'
        items = []
        prev_size = 0
        for r, dlt in zip(revs, deltas):
            ed = r['editor']
            who = f'<a href="https://en.wikipedia.org/wiki/User:{U(ed["name"].replace(" ", "_"))}" rel="noopener">{E(ed["name"])}</a>' if ed['kind'] == 'registered' else f'<i>{E(ed["kind"])} editor</i>'
            dsz = r['size'] - prev_size; prev_size = r['size']
            flags = ' '.join(f'<span class="st st-contradicted">{E(t)}</span>' for t in r['tags'] if t in REVERT_TAGS) + (' <span class="small">minor</span>' if r['minor'] else '')
            n = len(dlt['added']) + len(dlt['removed']) + len(dlt['changed'])
            det = ''
            if n:
                det = '<details><summary>' + ', '.join(x for x in (f'+{len(dlt["added"])} added' if dlt['added'] else '', f'&minus;{len(dlt["removed"])} removed' if dlt['removed'] else '', f'~{len(dlt["changed"])} reworded' if dlt['changed'] else '') if x) + '</summary><ul class="wdelta">'
                det += ''.join(f'<li class="dl-ins">{T(s["text"])}</li>' for s in dlt['added']) + ''.join(f'<li class="dl-del">{T(s["text"])}</li>' for s in dlt['removed'])
                det += ''.join(f'<li class="dl-chg"><del>{T(c["from"]["text"])}</del> <ins>{T(c["to"]["text"])}</ins></li>' for c in dlt['changed']) + '</ul></details>'
            refs = ''
            if dlt['refs_added'] or dlt['refs_removed']:
                refs = '<p class="small">' + ' '.join([f'+ref {T(u[:70])}' for u in dlt['refs_added']] + [f'&minus;ref {T(u[:70])}' for u in dlt['refs_removed']]) + '</p>'
            items.append(f'<li id="rev-{r["revid"]}"><b>{E(fmt_at(r["timestamp"]))}</b> &middot; {who} &middot; <span class="small">{"+" if dsz >= 0 else ""}{dsz:,} bytes</span> {flags}<br><span class="wcomment">{T(r["comment"]) or "<i>(no edit summary)</i>"}</span>{det}{refs}</li>')
        body = f'''
<p class="crumb"><a href="../../index.html">Wikipedia, as a graph</a> / <a href="../index.html">{E(art["title"])}</a> / Every edit</p>
<h1>Every edit of Wikipedia&#39;s {E(art["title"])} article, as what it changed</h1>
<p class="lead">{L["revisions"]} revisions from {E(fmt_at(revs[0]["timestamp"]))} to {E(fmt_at(revs[-1]["timestamp"]))}, by {L["editors"]} named editors and {L["anonymous_edits"]} anonymous edits, newest first. Wikipedia shows an edit as a diff of markup; here it is the statements the edit added, removed or reworded, so an edit reads as what it did to the account. {L["reverts"]} revisions were reverts or were reverted. Each entry links to the editor&#39;s public Wikipedia page; anonymous editors are never identified.</p>
{chart}
<ol class="whistory" reversed>{"".join(reversed(items))}</ol>
<p class="small">Edit summaries and text are Wikipedia&#39;s, CC BY-SA 4.0, by its contributors, shown as text.</p>
'''
        page(base + 'history/index.html', f'Every edit of Wikipedia&#39;s {art["title"]} article, as what it changed', f'All {L["revisions"]} revisions of the article as the statements each one added, removed or reworded, with the editor, the size and the reverts.', body, kind='evidence', topics=f'wikipedia {slug} history')
        build_wikipedia_more(slug, w, L)
        build_wikipedia_review(slug, w, L)
        cards.append((slug, art, L))
    # ---- the section index
    rows = [[f'<a href="{U(slug)}/index.html">{E(art["title"])}</a>', E(str(L['statements'])), f'{L["cited"]} ({100 * L["cited"] // max(1, L["statements"])}%)', f'{L["captured"]} of {L["with_url"]}', E(str(L['shared'])), E(str(L['revisions'])), E(str(L['editors'])), E(str(L['reverts'])), E(fmt_at(L['last']))] for slug, art, L in cards]
    body = f'''
<h1>Wikipedia, as a graph</h1>
<p class="lead">Wikipedia is one of the largest bodies of checked fact there is, and one of the hardest to use as one: an article is long, its edits are diffs of markup, its references are a list at the bottom, and nothing tells a reader what they have already seen. This section reads each article this site watches as a fractal semantic graph: one statement per sentence, each classed by its wording (a fact stated, a view attributed, a quote), each joined to the references it cites, and those to the captures this site holds of the same pages, which is where the article&#39;s facts and this site&#39;s claims meet. Every revision is kept, so an edit reads as what it changed. Kept by the ontologist; fetched by <code>admin/wikipedia/fetch.py</code> on the daily pass.</p>
{table(["Article", "Statements", "Cited", "References captured here", "Shared with our claims", "Revisions", "Editors", "Reverts", "Latest revision"], rows)}
{section("how", "How it is made", '<ul><li><b>Fetch.</b> Every revision of the article, with its wikitext, time, editor and edit summary; the Wikidata item; the articles that link in. Anonymous editors are recorded as anonymous, never by address.</li><li><b>Parse.</b> A parser (<code>admin/build/wikitext.py</code>, no model) lifts the references out, turns the markup into text, and splits it into sentences. One sentence is one statement; its id is a hash of its words, so the same sentence keeps its id across revisions and an edit is a set difference.</li><li><b>Class.</b> By wording only: a <i>record</i> (a number, a date, an identifier), a plain <i>stated</i> fact, an <i>attributed</i> statement (a named party said, reported or estimated it), a <i>quote</i>, or <i>hedged</i> wording. The class says how the article speaks, not whether it is right.</li><li><b>Join.</b> A reference is matched to this site&#39;s sources by its address and to a party by its host. A statement there and a claim here that cite the same captured page meet at that page.</li><li><b>Keep.</b> The data is <code>data/wikipedia/</code>; the graph of each article is in the ontology&#39;s <code>wikipedia</code> scope (<a href="../data/ontology.json">data/ontology.json</a>), with its own kinds and verbs, joined to the story graph by <code>captured_as</code>.</li></ul>')}
{section("sisters", "Wikidata and DBpedia", wiki_sister_section(cards))}
{section("editors", "For Wikipedia&#39;s editors", '<p>This site does not edit Wikipedia and does not ask to be cited by it. What it offers the article&#39;s editors, and the rules it holds itself to, are on <a href="for-editors/index.html">one page</a>; its reading of the article as a reviewer would read it, finding by finding against the captures, is on each article&#39;s <a href="php2shell/review/index.html">review page</a>.</p>')}
{section("next", "What this is for", '<p>Three things. A reader who wants the facts of a story, each with its evidence and without the markup, the edit wars and the list at the bottom. A newsroom that can see what Wikipedia says, what it rests on, and what changed since it last looked, in one view. And, in time, a measure: a source&#39;s trust shown by how often its statements are corrected, against other publications&#39;, rather than assumed.</p><p class="small">The text of each article is Wikipedia&#39;s, <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener">CC BY-SA 4.0</a>, by its contributors, with the revision id as the attribution; the pages and data of this section that carry it are under the same licence.</p>')}
'''
    build_wikipedia_editors(cards)
    page('wikipedia/index.html', 'Wikipedia, as a graph', 'Each Wikipedia article this site watches, read as a fractal semantic graph: statements classed as facts, attributions and quotes, references joined to the captures this site holds, and every edit as what it changed.', body, kind='evidence', topics='wikipedia graph')


if __name__ == '__main__':
    # Settle: a page that reads a generated file written later in the build (data/items.json, data/sections.json,
    # data/release-pages.json, data/grc-history.json ...) lags one build, so the gate's rebuild differed from the first
    # build of every release that changed content (board 175). When this build changed any of those files, build once
    # more, at most twice, so the first build already writes what a second would.
    _before = _state_hashes()
    main()
    _round = int(os.environ.get('BUILD_SETTLE_ROUND', '0'))
    if _state_hashes() != _before and _round < 2:
        print(f'build: generated state changed; building again to settle it (round {_round + 1})')
        os.environ['BUILD_SETTLE_ROUND'] = str(_round + 1)
        sys.stdout.flush()
        os.execv(sys.executable, [sys.executable] + sys.argv)
