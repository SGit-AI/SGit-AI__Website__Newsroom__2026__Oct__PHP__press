"""Who sent each telemetry session: a reader, a power user, the editor, a synthetic visitor (an agent's or a test's
headless browser) or a crawler. Used by telemetry_drain.py (the report), telemetry_public.py (the public stats) and,
through reports/classes.json in the telemetry vault, the telemetry application.

Two kinds of answer. Declared: since v0.8.4 the browser says it itself, in two optional fields: `agent` (automation:
navigator.webdriver, a headless browser, a crawler's user agent, named by class, never the string) and `who` (the role
of the /join/ key on this device once it is enrolled in data/contributors.json, or what the reader chose on
/admin/telemetry/: editor, team, power-user). A declaration is a claim like everything else in an event (the token is
published), but nobody gains by making one. Inferred: for events sent before that, and for browsers that declare
nothing, the rules below, in order. They are guesses and every report says which sessions were inferred.

A session is one browser tab (a random id in sessionStorage), not a person.
"""
import collections

CLASSES = ['reader', 'power-user', 'editor', 'synthetic', 'crawler']
LABELS = {'reader': 'readers', 'power-user': 'power users and team', 'editor': 'the editor', 'synthetic': 'synthetic (agents, tests, headless browsers)', 'crawler': 'crawlers (search engines)'}

# Data-centre towns where the search engines' renderers geolocate, seen in this site's own events.
CRAWLER_PLACES = {'Mountain View', 'Council Bluffs', 'The Dalles', 'Boydton', 'Dulles', 'Oak Hill', 'Moncks Corner', 'Lenoir', 'Pryor', 'Quincy', 'Des Moines'}
BOT_AGENTS = {'googlebot', 'bingbot', 'applebot', 'duckduckbot', 'yandexbot', 'baiduspider', 'google-inspectiontool', 'bot'}
AUTOMATION_AGENTS = {'webdriver', 'headless', 'lighthouse'}
INVITE_PAGES = ('/join/', '/collaborators/')

RULES = [
    ('declared', 'agent', 'The browser declared automation: a crawler by name (crawler), or navigator.webdriver or a headless browser (synthetic).'),
    ('declared', 'who', 'The browser declared a role: its /join/ key is enrolled as editor, team or power user, or the reader set it on /admin/telemetry/.'),
    ('inferred', 'crawler', 'More than 40 pages in one tab, or a Pacific time zone with a search-engine data centre (Mountain View, Council Bluffs, Boydton, Dulles, Oak Hill and others) or no place at all, or an unknown time zone.'),
    ('inferred', 'synthetic', 'The browser\'s time zone is UTC, or its language ends in @posix: headless browsers in cloud containers report them, people\'s browsers almost never do. This is where this site\'s own agents\' checks land.'),
    ('inferred', 'editor', 'The time zone is Europe/Lisbon and the browser\'s language English: the editor\'s browsers. A guess, which the editor can correct by setting this browser on /admin/telemetry/.'),
    ('inferred', 'power-user', 'The tab opened on /join/ or /collaborators/, the pages the editor\'s invitations link to.'),
    ('inferred', 'reader', 'Everything else.'),
]


def _norm_who(w):
    w = str(w or '').strip().lower()
    return {'editor': 'editor', 'team': 'power-user', 'power-user': 'power-user', 'power user': 'power-user', 'reader': 'reader'}.get(w)


def classify_session(events):
    """events: one session's rows (v == 1), in any order. Returns (class, how, rule)."""
    ev = sorted(events, key=lambda r: (r.get('_received') or 0))
    agents = {str(r.get('agent') or '').lower() for r in ev} - {''}
    if agents & BOT_AGENTS or any(a.endswith('bot') for a in agents):
        return 'crawler', 'declared', 'agent'
    if agents & AUTOMATION_AGENTS:
        return 'synthetic', 'declared', 'agent'
    whos = [_norm_who(r.get('who')) for r in ev if _norm_who(r.get('who'))]
    if whos:
        return collections.Counter(whos).most_common(1)[0][0], 'declared', 'who'
    first = ev[0]
    tz, city = first.get('tz') or '', first.get('city') or ''
    if len(ev) > 40 or tz == 'Etc/Unknown' or (tz == 'America/Los_Angeles' and (city in CRAWLER_PLACES or not city)):
        return 'crawler', 'inferred', 'crawler'
    if tz in ('UTC', 'Etc/UTC', 'Etc/GMT', 'GMT') or not tz or str(first.get('lang') or '').endswith('@posix'):
        return 'synthetic', 'inferred', 'synthetic'
    if tz == 'Europe/Lisbon' and str(first.get('lang') or '').lower().startswith('en'):
        return 'editor', 'inferred', 'editor'
    if any(str(r.get('path') or '').startswith(INVITE_PAGES) for r in ev[:1]):
        return 'power-user', 'inferred', 'power-user'
    return 'reader', 'inferred', 'reader'


def classify(rows):
    """rows: every drained row. Returns {sid: (class, how, rule)} for the rows that count (v == 1, not a test)."""
    by = collections.defaultdict(list)
    for r in rows:
        if r.get('v') == 1 and not r.get('test') and r.get('sid'):
            by[r['sid']].append(r)
    return {sid: classify_session(ev) for sid, ev in by.items()}


def counts(rows, classes):
    out = {c: {'views': 0, 'sessions': 0, 'declared': 0} for c in CLASSES}
    seen = set()
    for r in rows:
        sid = r.get('sid')
        if sid not in classes: continue
        c, how, _ = classes[sid]
        out[c]['views'] += 1
        if sid not in seen:
            seen.add(sid); out[c]['sessions'] += 1
            if how == 'declared': out[c]['declared'] += 1
    return out
