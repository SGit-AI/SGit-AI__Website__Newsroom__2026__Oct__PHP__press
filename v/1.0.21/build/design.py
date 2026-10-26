"""The redesign, as mockups for review: /admin/design/. Called by build.py with its namespace; writes five pages,
their markdown twins and their lines in llms.txt. Deterministic, standard library only, real data throughout.

The editor's brief (23 October 2026): use the width; less geeky, more professional and visual; a menu that is not a
mess; the reader's persona, and how much of the site they want to see, should change the layout and what is shown;
what a reader has seen gets out of the way; the team gets an admin console with its own menu and layout.
The brief is admin/content/briefs/2026-10-23__brief__the-redesign.md.
"""
import hashlib, json, re
from collections import Counter, OrderedDict

# --------------------------------------------------------------------------- the two dials
# Who you are (the persona) and how much of the site you want (the view). A page group is shown in Focus to the
# personas listed, from Standard to everyone listed in standard ('*' = all), and in Everything to all.
VIEWS = [('focus', 'Focus', 'Only what your role needs: today, your briefing, what to do, ask.'),
         ('standard', 'Standard', 'The story and the evidence, organised by task.'),
         ('everything', 'Everything', 'Every page, the method, the data and the team console: power users and the team.')]
GROUPS = OrderedDict([
    ('today',    ('Today', 'front page, what is new, the phone app', ['*'], ['*'])),
    ('briefing', ('Your briefing', 'the briefing written for your role', ['*'], ['*'])),
    ('ask',      ('Ask', 'questions readers ask, the Sherpa', ['*'], ['*'])),
    ('explain',  ('Explained', 'plain-English explainer, glossary', ['everyone', 'site-owner', 'board', 'pm', 'cfo', 'comms'], ['*'])),
    ('act',      ('What to do', 'playbook, patching, affected systems, check your stack', ['site-owner', 'security', 'engineer', 'developer', 'appsec', 'cto', 'ciso'], ['*'])),
    ('incident', ('The incident', 'the flaws, timeline, discovery, leak, exploitation, impact, defence', ['security', 'journalist', 'researcher', 'analyst', 'ciso'], ['*'])),
    ('analysis', ('The analysis', 'claims, fact-check, numbers, agencies, who says what', ['journalist', 'analyst', 'comms', 'dpo'], ['decide', 'act', 'communicate', 'study'])),
    ('grc',      ('Risk and compliance', 'risk register, frameworks, stakeholders', ['dpo', 'ciso'], ['decide'])),
    ('code',     ('The code', 'the fix in php-src, the review graph', ['researcher', 'engineer', 'appsec'], ['act', 'study'])),
    ('stories',  ('Stories', 'signed articles written here', ['journalist', 'analyst'], ['*'])),
    ('evidence', ('The evidence', 'every source, the vaults, the pipeline, versions', ['researcher', 'journalist'], ['communicate', 'study'])),
    ('site',     ('The site and the team', 'method, roles, board, releases, admin', [], [])),
])

def group_of(path):
    p = path
    if p in ('index.html', 'whatsnew/index.html', 'summary/index.html') or p.startswith(('now/', 'you/', 'reader/', 'feeds/', 'subscribe/')): return 'today'
    if p.startswith(('briefings/', 'start/')): return 'briefing'
    if p.startswith(('questions/', 'sherpa/', 'interview/')): return 'ask'
    if p.startswith(('explained/', 'glossary/')): return 'explain'
    if p.startswith(('playbook/', 'patching/', 'affected/', 'stack/', 'check/')): return 'act'
    if p.startswith(('flaws/', 'timeline/', 'discovery/', 'leak/', 'exploitation/', 'compromise/', 'impact/', 'defence/', 'context/', 'signals/')): return 'incident'
    if p.startswith(('claims/', 'factcheck/', 'numbers/', 'agencies/', 'actors/', 'graph/', 'readings/')): return 'analysis'
    if p.startswith('grc/'): return 'grc'
    if p.startswith(('code/', 'review/')): return 'code'
    if p.startswith(('articles/',)): return 'stories'
    if p.startswith(('sources/', 'vaults/', 'layers/', 'pipeline/', 'versions/', 'facts/', 'admin/vault/')): return 'evidence'
    return 'site'

def level(gid, persona):
    """'f' shown in Focus, 's' from Standard, 'e' only in Everything."""
    _, _, focus, std = GROUPS[gid]
    if '*' in focus or persona['id'] in focus: return 'f'
    if '*' in std or persona['group'] in std or persona['id'] in std: return 's'
    return 'e'

def visible(by_group, persona, view):
    """Pages this reader sees in this view. In Focus the briefings shrink to their own briefing and the reader map."""
    n = 0
    for g in GROUPS:
        lv = level(g, persona)
        if view == 'everything' or lv == 'f' or (view == 'standard' and lv == 's'):
            n += 2 if (g == 'briefing' and view == 'focus') else by_group[g]
    return n

# --------------------------------------------------------------------------- helpers
def svg_spark(values, w=220, h=44, cls='var(--info)'):
    if not values: return ''
    mx = max(values) or 1
    step = w / max(1, len(values) - 1)
    pts = ' '.join(f'{i * step:.1f},{h - 4 - (v / mx) * (h - 8):.1f}' for i, v in enumerate(values))
    return f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-label="trend"><polyline fill="none" stroke="{cls}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points="{pts}"/></svg>'

def svg_donut(parts, size=168):
    """parts: list of (value, colour, label). A ring with the total in the middle."""
    tot = sum(v for v, _, _ in parts) or 1
    r, c = 62, 2 * 3.14159265 * 62
    off, segs = 0.0, ''
    for v, col, lab in parts:
        L = c * v / tot
        segs += f'<circle r="{r}" cx="84" cy="84" fill="none" stroke="{col}" stroke-width="22" stroke-dasharray="{L:.2f} {c - L:.2f}" stroke-dashoffset="{-off:.2f}" transform="rotate(-90 84 84)"><title>{v} {lab}</title></circle>'
        off += L
    return (f'<svg viewBox="0 0 168 168" width="{size}" height="{size}" role="img" aria-label="facts by status">{segs}'
            f'<text x="84" y="80" text-anchor="middle" font-size="30" font-weight="700" fill="currentColor">{tot}</text>'
            f'<text x="84" y="104" text-anchor="middle" font-size="12" fill="currentColor" opacity=".65">facts</text></svg>')

STATUS_COL = OrderedDict([('confirmed', 'var(--good)'), ('reported', 'var(--info)'), ('disputed', 'var(--warn)'), ('contradicted', '#d6a556'), ('unverified', 'var(--alert)')])

def build(ns):
    D, E, VERSION, STORY, PERSONAS, AUD = ns['D'], ns['E'], ns['VERSION'], ns['STORY'], ns['PERSONAS'], ns['AUD']
    NAV, PAGES, write, human_time, BASE_URL, SITE_NAME = ns['NAV'], ns['PAGES'], ns['write'], ns['human_time'], ns['BASE_URL'], ns['SITE_NAME']
    SOURCES, short_name = ns['SOURCES'], ns['short_name']
    when = human_time(STORY['data_as_of'])
    pl, im, claims = D['plain'], D['impact'], D['claims']
    st = Counter(c['status'] for c in claims)
    nav_pages = [p for _, items in NAV for p, _ in items]
    all_pages = [p for p, _, _, _ in PAGES]
    by_group = Counter(group_of(p) for p in all_pages)
    made = []

    def shell(path, title, desc, body, mock, persona=None, view=None, nav=None, console=False):
        """The page: the mockup banner, then the proposed top bar (or none, for the console), then the body."""
        up = '../' * path.count('/')
        banner = (f'<div class="mock-banner"><div class="shell"><span><b>Mockup {mock}</b> for review: a proposed design, built from the live data of release v{E(VERSION)}. '
                  f'Not the live site.</span><a href="{up}admin/design/index.html">All mockups and the design notes &rarr;</a></div></div>')
        top = ''
        if not console:
            p = PERSONAS[persona]
            links = ''.join(f'<a href="#"{" class=here" if i == 0 else ""}>{E(t)}{f"<span class=n>{n}</span>" if n else ""}</a>' for i, (t, n) in enumerate(nav or []))
            dial = ''.join(f'<span{" class=on" if v == view else ""}>{E(lab)}</span>' for v, lab, _ in VIEWS)
            top = (f'<header class="topbar"><div class="shell"><a class="logo" href="{up}index.html"><i>PHP</i>October<span>2026</span></a>'
                   f'<nav class="mainnav" aria-label="Main">{links}</nav>'
                   f'<div class="dials"><span class="who"><span class="av {E(p["group"])}">{E(p["person"][0])}</span>{E(p["person"])}, {E(p["label"])}</span>'
                   f'<span class="dial" aria-label="How much of the site">{dial}</span><a class="iconbtn" href="#">Ask</a></div></div></header>')
        html = f'''<!doctype html>
<html lang="en" data-root="{up}" data-path="{path}" data-ver="{VERSION}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)} &middot; {SITE_NAME}</title>
<meta name="description" content="{E(desc)}">
<meta name="robots" content="noindex">
<link rel="canonical" href="{BASE_URL}/{path}">
<link rel="icon" href="data:,">
<link rel="alternate" type="text/markdown" href="{up}{path[:-5]}.md">
<link rel="stylesheet" href="{up}assets/design/v2.css">
</head>
<body>
{banner}
{top}
{body}
</body>
</html>
'''
        PAGES.append((path, title, desc, 'site'))
        write(path, html)
        md = re.sub(r'<(script|style|svg).*?</\1>', '', body, flags=re.S)
        md = re.sub(r'<(h1|h2|h3)[^>]*>(.*?)</\1>', lambda m: '\n' + '#' * (int(m.group(1)[1]) + 1) + ' ' + re.sub(r'<[^>]+>', '', m.group(2)) + '\n', md, flags=re.S)
        md = re.sub(r'<li[^>]*>', '\n- ', md)
        md = re.sub(r'<(p|div|section|article|tr)[^>]*>', '\n', md)
        md = re.sub(r'<[^>]+>', ' ', md)
        md = re.sub(r'[ \t]+', ' ', md)
        md = re.sub(r'\n\s*\n+', '\n\n', md)
        import html as H
        write(path[:-5] + '.md', f'# {title}\n\n{desc}\n\n> Mockup {mock} for review, built from the data of release v{VERSION}. Not the live site.\n\n' + H.unescape(md).strip() + f'\n\n---\nsite v{VERSION} · {BASE_URL}/{path}\n')
        made.append((path, title, desc))

    # ======================================================================= mockup A: the board member, Focus
    board = PERSONAS['board']
    tiles = [
        ('good', 'A fix', 'Available', f'PHP {", ".join(D["affected"]["fixed"])}, since 21 Oct', None),
        ('alert', 'Severity', 'Critical', '9.2 out of 10, both flaws', None),
        ('good', 'Confirmed break-ins', 'None', 'no named organisation, as of the latest capture', None),
        ('warn', 'Taken offline', f'{len(im["offline"])} organisations', 'as a precaution, across 6 countries', None),
        ('info', 'Agencies compared', f'{len(D["agencies"])}', 'all say update; they split on offline', None),
    ]
    tl_days = Counter(t['at'][:10] for t in D['timeline'] if t['at'][:7] == '2026-10')
    days = sorted(tl_days)
    spark = svg_spark([tl_days[d] for d in days], cls='var(--alert)')
    kpis = ''.join(f'<div class="card kpi {c}"><div class="k">{E(k)}</div><div class="v">{E(v)}</div><div class="d">{E(d)}</div>{spark if k == "Agencies compared" and False else ""}</div>' for c, k, v, d, _ in tiles)
    decisions = [
        ('Are we exposed?', 'Ask for the list, not a percentage: every system that runs PHP, including vendor products and hosting panels, and which are on the internet.'),
        ('Is everything updated and restarted?', 'Updating is not enough until PHP is restarted. Ask for the running version, checked after the restart, system by system.'),
        ('Who can pull a system offline, and how fast?', 'Every agency puts offline last, but you need to be able to do it in minutes. Name the person and rehearse it once.'),
    ]
    dec = ''.join(f'<div class="decision"><div class="num">{i + 1}</div><div><h3>{E(t)}</h3><p>{E(x)}</p></div></div>' for i, (t, x) in enumerate(decisions))
    latest = ''.join(f'<li><span class="pill new">New</span> <span class="small">{E(x["when"])}</span><div class="t">{E(x["text"])}</div></li>' for x in pl['latest'][-3:])
    moments = ''.join(f'<div class="jst {"good" if m["tone"] == "ok" else "alert" if m["tone"] == "bad" else m["tone"] if m["tone"] in ("warn", "info") else ""}"><div class="w">{E(m["when"])}</div><div class="x">{E(m["what"])}</div></div>' for m in pl['moments'])
    stance = Counter()
    for a in D['agencies']:
        o = a['offline']
        stance['Take offline' if o == 'yes' else 'Isolate' if o.startswith('isolate') or o == 'restrict from abroad' else 'Offline after other steps' if o in ('after mitigations', 'consider') else 'No offline advice' if o == 'none' else 'Not readable'] += 1
    order = [('Take offline', 'var(--alert)'), ('Isolate', 'var(--warn)'), ('Offline after other steps', '#d6a556'), ('No offline advice', 'var(--info)'), ('Not readable', 'var(--line-2)')]
    sbar = ''.join(f'<div style="flex:{stance[k]};background:{c}" title="{stance[k]} {E(k)}"></div>' for k, c in order if stance[k])
    slegend = ''.join(f'<li><i style="background:{c}"></i>{stance[k]} {E(k.lower())}</li>' for k, c in order if stance[k])
    body = f'''
<section class="band"><div class="shell hero">
  <div><p class="eyebrow"><span class="live">Developing</span> &nbsp;&middot;&nbsp; last checked {E(when)}</p>
    <h1 class="display">{E(pl["headline"])}</h1>
    <p class="lede">{E(re.sub(r"<[^>]+>", "", pl["deck"]))}</p></div>
  <aside class="ans"><div class="who-line"><span class="av decide">{E(board["person"][0])}</span><div><b>Your answer in thirty seconds</b><div class="small" style="color:var(--band-muted)">for {E(board["person"])}, {E(board["label"].lower())}</div></div></div>
    <p>{E(board["answer"])}</p></aside>
</div></section>
<main class="shell">
  <section class="block"><div class="tiles">{kpis}</div></section>
  <section class="block"><div class="grid cols-12">
    <div class="card span-8" style="align-self:start"><div class="block-head"><h2 class="h2">Three questions to put to your team this week</h2><span class="small">from your briefing</span></div>{dec}</div>
    <div class="span-4 grid" style="align-content:start">
      <div class="card"><div class="block-head"><h2 class="h2">Since you last looked</h2><span class="pill">3 new</span></div><ul class="delta">{latest}</ul><p class="small" style="margin-bottom:0">Read items disappear from this list. <a href="#">Everything new &rarr;</a></p></div>
      <div class="card flat" style="background:var(--brand-soft);border-color:transparent"><h3>Ask about it</h3><p class="small" style="color:var(--ink-2)">"What should I tell the board on Thursday?" Answers cite the evidence.</p><a class="iconbtn" href="#">Ask a question</a></div>
    </div></div></section>
  <section class="block"><div class="grid cols-12">
    <div class="card span-7"><div class="block-head"><h2 class="h2">How it unfolded</h2><a class="small" href="#">The full timeline</a></div><div class="journey">{moments}</div></div>
    <div class="card span-5"><div class="block-head"><h2 class="h2">What governments advise</h2><span class="small">{len(D["agencies"])} agencies</span></div>
      <p style="margin:.2rem 0 .8rem;color:var(--ink-2)">All say install the fix. They split on what to do if you cannot.</p>
      <div style="display:flex;height:22px;border-radius:7px;overflow:hidden;gap:2px">{sbar}</div><ul class="legend">{slegend}</ul>
      <p class="small" style="margin-bottom:0"><a href="../c/index.html">See every agency &rarr;</a></p></div>
  </div></section>
  <footer class="foot">Focus view shows {visible(by_group, board, "focus")} of {len(all_pages)} pages for this reader. Switch to Standard for the story and the evidence, or Everything for the whole site. Every number here links to its saved source on the live site.</footer>
</main>'''
    shell('admin/design/a/index.html', 'Mockup A: the front page for a board member, Focus view', 'The front page for a board member who wants only what their role needs: the situation, five numbers, three questions for the team, what is new, and one picture each of how it unfolded and what governments advise.', body, 'A', 'board', 'focus',
          [('Today', 3), ('Your briefing', 0), ('What to ask', 0), ('Explained', 0)])

    # ======================================================================= mockup B: the security lead, Standard
    sam = PERSONAS['security']
    items = list(ns['all_items']().items())  # this build's items, not the file save_items() writes at the end of it (read from disk, it lagged one build: board 175)
    feed = [(k, v) for k, v in items if v['kind'] in ('fact', 'event', 'question', 'story', 'front')]
    feed.sort(key=lambda kv: (kv[1].get('date') or '', kv[1]['changed'], kv[0]), reverse=True)
    feed = feed[:9]
    def fitem(k, v, i):
        c = next((c for c in claims if 'fact-' + c['id'] == k), None)
        status = c['status'] if c else ''
        col = {'confirmed': 'good', 'reported': 'info', 'disputed': 'warn', 'contradicted': 'warn', 'unverified': 'alert'}.get(status, '')
        text = c['claim'] if c else v['title']
        srcs = ''.join(f'<span class="chip">{E(short_name(SOURCES[s]))}</span>' for s in (c['sources'] if c else [])[:4] if s in SOURCES)
        spill = f'<span class="pill {col}">{E(status)}</span>' if status else ''
        return (f'<article class="card fitem"><div><div class="meta"><span class="pill {"new" if i < 4 else "warn"}">{"New" if i < 4 else "Changed"}</span>'
                f'<span class="pill">{E(v["kind"])}</span>{spill}<span class="small">v{E(v["changed"])}</span></div>'
                f'<h3>{E(text[:180])}</h3>{f"<div class=chips>{srcs}</div>" if srcs else ""}</div><div class="check" title="Mark read">&#10003;</div></article>')
    feedhtml = ''.join(fitem(k, v, i) for i, (k, v) in enumerate(feed))
    steps = [('Patch internet-facing first', 'mod_php, then FPM, then the rest. Restart every worker; rebuild every image.'),
             ('Bound the known paths', 'session.upload_progress off, low post_max_size, fatal_error_backtraces off on 8.5. None of these is a fix.'),
             ('Watch the process tree', 'Alert on a PHP worker spawning a shell or a downloader. A clean access log proves nothing.')]
    actions = ''.join(f'<div class="card action"><div class="n">{i + 1}</div><div><h3>{E(t)}</h3><p>{E(x)}</p></div></div>' for i, (t, x) in enumerate(steps))
    donut = svg_donut([(st[k], c, k) for k, c in STATUS_COL.items() if st[k]])
    dleg = ''.join(f'<li><i style="background:{c}"></i>{st[k]} {E(k)}</li>' for k, c in STATUS_COL.items() if st[k])
    dmax = max(tl_days.values()) if tl_days else 1
    bars = ''.join(f'<div class="{"hot" if d >= "2026-10-20" else ""}" style="height:{max(3, round(100 * tl_days[d] / dmax))}%" title="{tl_days[d]} events on {d}"></div>' for d in days)
    blabels = ''.join(f'<span>{E(d[8:])}</span>' for d in days)
    ex = ''.join(f'<li><span class="small">{E(x["when"])}</span><div class="t" style="font-size:.9rem">{E(x["who"].split("(")[0].strip())}: {E(x["what"][:90])}</div></li>' for x in D['exploitation'][:4])
    groups_nav = [('Today', '9 new'), ('What to do', ''), ('The incident', ''), ('Detection and defence', ''), ('The agencies', '16'), ('Every claim', f'{len(claims)}'), ('Ask', '')]
    rnav = ''.join(f'<a href="#"{" class=here" if i == 0 else ""}>{E(t)}<span>{E(n)}</span></a>' for i, (t, n) in enumerate(groups_nav))
    path_done = 2
    body = f'''
<main class="shell app">
  <aside class="rail">
    <div class="card"><div style="display:flex;gap:.7rem;align-items:center"><span class="av act" style="width:42px;height:42px">{E(sam["person"][0])}</span><div><b>{E(sam["person"])}</b><div class="small">{E(sam["label"])}</div></div></div>
      <p class="small" style="margin:.7rem 0 .4rem">Your reading path</p><div class="progress"><b style="width:{round(100 * path_done / len(sam["path"]))}%"></b></div><p class="small" style="margin:.4rem 0 0">{path_done} of {len(sam["path"])} read &middot; next: Exploitation signals</p></div>
    <nav class="railnav card flat" style="padding:.4rem">{rnav}</nav>
  </aside>
  <div>
    <p class="eyebrow">Since your last visit &middot; {E(when)}</p>
    <h1 class="display" style="font-size:clamp(1.7rem,2.6vw,2.6rem);margin:.3rem 0 .4rem">9 things are new, 3 changed. Two matter for your runbook.</h1>
    <p class="lede" style="margin:0 0 1.2rem">{E(sam["answer"])}</p>
    <section><div class="block-head"><h2 class="h2">Your next three actions</h2><a class="small" href="#">The whole playbook</a></div><div class="actions">{actions}</div></section>
    <section class="feed"><div class="block-head" style="margin-top:1.6rem"><h2 class="h2">What changed</h2><div class="chips"><span class="chip" style="background:var(--ink);color:var(--surface)">All</span><span class="chip">Facts</span><span class="chip">Timeline</span><span class="chip">Questions</span><span class="chip">Stories</span></div></div>{feedhtml}
      <p class="small">Marked read, an item fades and then leaves this list; it comes back only if what it says changes.</p></section>
  </div>
  <aside class="rail right">
    <div class="card"><h3>How sure are we?</h3><div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">{donut}<ul class="legend" style="flex-direction:column">{dleg}</ul></div></div>
    <div class="card"><h3>Events per day, October</h3><div class="bars">{bars}</div><div class="bars-l">{blabels}</div><p class="small" style="margin:.5rem 0 0">Red: from the leak on 20 October.</p></div>
    <div class="card"><h3>Exploitation signals</h3><ul class="delta">{ex}</ul><p class="small" style="margin:0"><span class="pill good">0</span> confirmed compromises</p></div>
    <div class="card"><h3>Fixed in</h3><div class="chips">{"".join(f"<span class=chip style='font-family:var(--mono)'>{E(v)}</span>" for v in D["affected"]["fixed"])}</div><p class="small" style="margin:.5rem 0 0">8.1 and older: source backports only.</p></div>
  </aside>
</main>'''
    shell('admin/design/b/index.html', 'Mockup B: the front page for a security lead, Standard view', 'A three-column working view for a security lead: their reading path and the site by task on the left, what changed since the last visit and the next three actions in the middle, and the state of the evidence as charts on the right.', body, 'B', 'security', 'standard',
          [('Today', 9), ('What to do', 0), ('The incident', 0), ('The evidence', 0), ('Your briefing', 0)])

    # ======================================================================= mockup C: a content page, the agencies
    BUCKETS = [('none', 'No offline advice', 'var(--info)'), ('consider', 'Consider it, or after other steps', '#d6a556'), ('restrict', 'Restrict access', 'var(--warn)'),
               ('isolate', 'Isolate from the internet', 'var(--warn)'), ('yes', 'Take it offline', 'var(--alert)')]
    def bucket(o): return 'yes' if o == 'yes' else 'isolate' if o.startswith('isolate') else 'restrict' if o == 'restrict from abroad' else 'consider' if o in ('after mitigations', 'consider') else 'none' if o == 'none' else None
    cols = ''.join(f'<div class="bk"><div class="bk-h" style="border-top-color:{c}"><b>{sum(1 for a in D["agencies"] if bucket(a["offline"]) == k)}</b> {E(lab)}</div><div class="chips">' + ''.join(f'<span class="chip"><b style="font-family:var(--mono);font-weight:600">{E(a["country"].split()[0])}</b> {E(a["agency"].split(" (")[0])}</span>' for a in D['agencies'] if bucket(a['offline']) == k) + '</div></div>' for k, lab, c in BUCKETS)
    unread = [a for a in D['agencies'] if bucket(a['offline']) is None]
    dots = f'<div class="buckets">{cols}</div>' + (f'<p class="small" style="margin:.8rem 0 0">Not readable from this capture environment: {", ".join(E(a["agency"]) for a in unread)}.</p>' if unread else '')
    def scls(o): return 's-yes' if o == 'yes' else 's-isolate' if o.startswith('isolate') or o == 'restrict from abroad' else 's-consider' if o in ('after mitigations', 'consider') else 's-none' if o == 'none' else 's-unknown'
    def slab(o): return {'yes': 'Take offline', 'none': 'No offline advice', 'unknown': 'Could not be read'}.get(o, o[0].upper() + o[1:])
    cards = ''.join(f'''<article class="card agency {scls(a["offline"])}"><div style="display:flex;justify-content:space-between;gap:.5rem"><h3 style="margin:0">{E(a["agency"])}</h3><span class="cc">{E(a["country"])}</span></div>
<span class="pill {"alert" if a["offline"] == "yes" else "warn" if scls(a["offline"]) in ("s-isolate", "s-consider") else "info" if a["offline"] == "none" else ""}">{E(slab(a["offline"]))}</span>
{f"<q>{E(a['offline_text'][:170])}</q>" if a.get("offline_text") and a["offline"] not in ("none", "unknown") else f"<p class=small style='margin:0'>{E((a.get('note') or '')[:150])}</p>"}
<div class="chips">{"".join(f"<span class=chip>{E(short_name(SOURCES[s]))}</span>" for s in a["sources"][:2] if s in SOURCES)}</div></article>''' for a in D['agencies'])
    body = f'''
<section class="band"><div class="shell hero">
  <div><p class="eyebrow">The analysis &middot; government advice</p><h1 class="display">{len(D["agencies"])} agencies. All say update. They split on offline.</h1>
  <p class="lede">The question that divides them is not whether to patch but what to do with a system you cannot patch today. Read left to right: from no offline advice to take it offline.</p></div>
  <div class="ans"><p class="eyebrow" style="margin:0 0 .4rem">In one line</p><p style="font-size:1.15rem">The US says take it offline. The UK says that is the fourth step. Europe says isolate. Australia, Japan and the Netherlands say nothing about it.</p></div>
</div></section>
<main class="shell">
  <section class="block"><div class="card"><div class="block-head"><h2 class="h2">The spectrum</h2><span class="small">every agency, by what it says to do with a system you cannot patch</span></div>
    <div class="rail-g"></div>{dots}</div></section>
  <section class="block"><div class="block-head"><h2 class="h2">Agency by agency</h2><div class="chips"><span class="chip" style="background:var(--ink);color:var(--surface)">All {len(D["agencies"])}</span><span class="chip">Take offline</span><span class="chip">Isolate</span><span class="chip">No offline advice</span></div></div>
    <div class="tiles" style="grid-template-columns:repeat(auto-fill,minmax(270px,1fr))">{cards}</div></section>
  <section class="block"><details class="card flat"><summary class="h2" style="cursor:pointer">The evidence table: every agency's words, dates and sources</summary><p class="small">On the live site this is the full table, one row per agency with the verbatim sentence, the publication time and every saved source.</p></details></section>
  <footer class="foot">A wall of text becomes three layers: the one-line answer, the picture, and the cards; the evidence table is one click away, not the first thing you see.</footer>
</main>'''
    shell('admin/design/c/index.html', 'Mockup C: a content page, what sixteen agencies advise', 'The agencies page redesigned: the answer in one line, every agency placed on one spectrum from no offline advice to take it offline, a card per agency, and the evidence table one click away.', body, 'C', 'ciso', 'standard',
          [('Today', 0), ('What to do', 0), ('The incident', 0), ('The evidence', 0), ('Your briefing', 0)])

    # ======================================================================= mockup D: the admin console
    A = D['admin']
    bstat = Counter(b['status'] for b in A['board'])
    def tickets(status, n=7):
        rows = [b for b in A['board'] if b['status'] == status][-n:][::-1]
        return ''.join(f'<div class="ticket"><span class="id">#{E(b["id"])}</span><div>{E(b["title"][:120])}{"…" if len(b["title"]) > 120 else ""}</div><div class="o"><span>{E(b["owner"])}</span>{("<span>v" + E(b["version"]) + "</span>") if b.get("version") else ""}</div></div>' for b in rows)
    rel = D['versions']['versions'][:8]
    rels = ''.join(f'<tr><td style="font-family:var(--mono);white-space:nowrap">v{E(r["version"])}</td><td class="small" style="white-space:nowrap">{E(r["date"])}</td><td>{E(r["title"][:130])}{"…" if len(r["title"]) > 130 else ""}</td></tr>' for r in rel)
    roles = ''.join(f'<tr><td><b>{E(r["name"])}</b></td><td class="small">{E(r["owns"][:120])}</td><td style="text-align:right">{sum(1 for b in A["board"] if b["owner"] == r["id"] and b["status"] == "open")}</td></tr>' for r in A['roles'][:9])
    side = [('Console', [('Overview', '', True), ('Board', str(bstat['open']), False), ('Agents', str(len(A['roles'])), False), ('Releases', str(len(D['versions']['versions'])), False), ('Pipeline', '', False)]),
            ('Editorial', [('Briefs', '', False), ('Fact-check queue', '', False), ('Corrections', '', False), ('Readers and feedback', '', False)]),
            ('Systems', [('Vaults and keys', str(len(D['vaults']['vaults'])), False), ('Telemetry', '', False), ('Synthetic readers', '', False), ('Design', '5', False)])]
    sidehtml = ''.join(f'<h4>{E(g)}</h4>' + ''.join(f'<a href="#"{" class=here" if h else ""}>{E(t)}{f"<span>{E(n)}</span>" if n else ""}</a>' for t, n, h in items) for g, items in side)
    kp = [('info', 'Release', f'v{VERSION}', f'{len(D["versions"]["versions"])} releases since 22 Oct'), ('warn', 'Open on the board', str(bstat['open']), f'{bstat["done"]} done, {bstat.get("waiting", 0)} waiting'),
          ('good', 'Pages built', str(len(all_pages)), 'every one with a markdown twin'), ('info', 'Sources in the vault', str(len(D['sources'])), f'{sum(1 for s in D["sources"] if s.get("status") == "captured")} captured')]
    kpis = ''.join(f'<div class="card kpi {c}"><div class="k">{E(k)}</div><div class="v">{E(v)}</div><div class="d">{E(d)}</div></div>' for c, k, v, d in kp)
    body = f'''
<div class="console">
  <nav class="side" aria-label="Console"><a class="logo" href="../../../index.html"><i>PHP</i>Team console</a>{sidehtml}
    <h4>Reader site</h4><a href="../a/index.html">Back to the reader site</a></nav>
  <main class="cmain">
    <div class="block-head"><div><p class="eyebrow">Team console &middot; public, like everything here</p><h1 class="display" style="font-size:clamp(1.6rem,2.4vw,2.4rem)">Overview</h1></div><span class="small">built {E(when)}</span></div>
    <div class="tiles" style="margin-bottom:1.4rem">{kpis}</div>
    <div class="block-head"><h2 class="h2">The board</h2><span class="small">newest first in each lane</span></div>
    <div class="kanban">
      <div class="lane"><h3>Open <span>{bstat["open"]}</span></h3>{tickets("open")}</div>
      <div class="lane"><h3>Waiting <span>{bstat.get("waiting", 0)}</span></h3>{tickets("waiting")}</div>
      <div class="lane"><h3>Done <span>{bstat["done"]}</span></h3>{tickets("done")}</div>
    </div>
    <div class="grid cols-12" style="margin-top:1.6rem">
      <div class="card span-7"><div class="block-head"><h2 class="h2">Releases</h2><span class="small">latest 8</span></div><div class="tw"><table class="tbl">{rels}</table></div></div>
      <div class="card span-5"><div class="block-head"><h2 class="h2">Agents and what they own</h2><span class="small">open items</span></div><div class="tw"><table class="tbl">{roles}</table></div></div>
    </div>
  </main>
</div>'''
    shell('admin/design/d/index.html', 'Mockup D: the team console', 'The admin section as a console with its own menu and layout: a dark sidebar by area, the board as lanes, releases, and the agents with what each owns and how many open items it carries.', body, 'D', console=True)

    # ======================================================================= the hub: the design notes
    pgroups = OrderedDict((g['id'], g) for g in D['personas']['groups'])
    reps = ['everyone', 'board', 'cfo', 'ciso', 'journalist', 'security', 'engineer', 'researcher']
    head = ''.join(f'<th><span class="av {E(PERSONAS[r]["group"])}" style="width:26px;height:26px;font-size:.75rem" title="{E(PERSONAS[r]["label"])}">{E(PERSONAS[r]["person"][0])}</span><div class="small">{E(PERSONAS[r]["label"].split(" or ")[0])}</div></th>' for r in reps)
    rows = ''.join(f'<tr><td><b>{E(lab)}</b><div class="small">{E(what)} &middot; {by_group[g]} pages</div></td>' + ''.join(f'<td><span class="dot-v {level(g, PERSONAS[r])}" title="{ {"f": "Focus", "s": "Standard", "e": "Everything"}[level(g, PERSONAS[r])] }"></span></td>' for r in reps) + '</tr>' for g, (lab, what, _, _) in GROUPS.items())
    counts = ''.join(f'<tr><td><b>{E(PERSONAS[r]["person"])}</b> <span class="small">{E(PERSONAS[r]["label"])}</span></td>' + ''.join(f'<td>{visible(by_group, PERSONAS[r], v)}</td>' for v, _, _ in VIEWS) + '</tr>' for r in reps)
    menus = ''.join(f'<div class="card"><p class="eyebrow">{E(lab)}</p><p style="margin:.3rem 0 .6rem">{E(txt)}</p><div class="chips">' + ''.join(f'<span class="chip">{E(x)}</span>' for x in m) + '</div></div>' for lab, txt, m in [
        ('Focus', 'Four places. For a board member, a CFO, a website owner.', ['Today', 'Your briefing', 'What to ask', 'Explained']),
        ('Standard', 'The site by task, not by where the data came from.', ['Today', 'What to do', 'The incident', 'The evidence', 'Your briefing', 'Ask']),
        ('Everything', 'All of it, for power users and the team.', ['Today', 'What to do', 'The incident', 'The evidence', 'Risk and compliance', 'Stories', 'Method and data', 'Team console'])])
    problems = [('It reads as a wall of text', 'Long paragraphs and tables first; the picture, if any, comes last. Mockup C turns the agencies page into answer, picture, cards, then the table.'),
                ('It does not use the screen', 'Pages stop at 1,080 pixels; on a laptop half the screen is empty. The proposal runs to 1,680 with two or three columns that stack on a phone.'),
                ('The menu is the site map', f'Eleven groups and {len(nav_pages)} entries, ordered by how the site was built, not by what a reader wants to do. The proposal: four to eight entries, chosen by who you are and how much you want.'),
                ('Everyone sees everything', 'A board member meets the vault, the board and the billing model on the way to their answer. The proposal: two dials, who you are and how much of the site you see.'),
                ('Read things stay in the way', 'The delta strip is right, but read items still fill the pages. The proposal: read items fade, then leave; they return only when they change.'),
                ('The team lives in the reader site', 'The board, roles, keys and telemetry sit in the reader menu. The proposal: a console with its own menu and layout, still public.')]
    prob = ''.join(f'<div class="card"><h3>{E(t)}</h3><p class="small" style="color:var(--ink-2);margin:0">{E(x)}</p></div>' for t, x in problems)
    thumbs = ''.join(f'<a class="thumb" href="{k}/index.html"><img src="../../assets/design/{k}.png" alt="Mockup {k.upper()}" loading="lazy" width="1600" height="1000"><h3>{E(t)}</h3><p class="small">{E(x)}</p></a>' for k, t, x in [
        ('a', 'A. Front page: board member, Focus', 'The situation on a dark band, five numbers, three questions for the team, what is new, two pictures.'),
        ('b', 'B. Front page: security lead, Standard', 'Three columns: reading path and tasks; what changed and the next three actions; the evidence as charts.'),
        ('c', 'C. A content page: the agencies', 'Answer in one line, every agency on one spectrum, a card each, the evidence table one click away.'),
        ('d', 'D. The team console', 'Its own menu and layout: board as lanes, releases, agents and what they own.')])
    body = f'''
<section class="band"><div class="shell hero">
  <div><p class="eyebrow">Admin &middot; design &middot; for review</p><h1 class="display">The redesign: who you are, and how much you want to see</h1>
  <p class="lede">The editor's review of 23 October: the site is right in substance and wrong in form. Too geeky, too much text, a menu that is a site map, and half the screen unused. Four mockups, built from the live data, and the model behind them.</p></div>
  <div class="ans"><p class="eyebrow" style="margin:0 0 .4rem">The model, in one line</p><p style="font-size:1.12rem">Two dials. <b>Who you are</b> sets the layout and the order. <b>How much you want</b> (Focus, Standard, Everything) sets which pages exist for you at all. What you have read gets out of the way.</p></div>
</div></section>
<main class="shell">
  <section class="block"><a class="card" href="../../404.html" style="display:block;text-decoration:none;color:inherit;border-left:4px solid var(--brand)"><p class="eyebrow" style="margin:0">Live, 25 October &middot; the router</p><h2 class="h2" style="margin:.3rem 0">Every page has views: /agencies/as/security/</h2><p class="small" style="margin:0;color:var(--ink-2)">Any address past the word &ldquo;as&rdquo; is answered by 404.html, which opens the page before it, written for the reader after it; the line then keeps the view in the address bar on every page. The front page, the agencies, the numbers and the playbook also have a card per reader, so a pasted link unfurls with who it is for.</p></a></section>
  <section class="block"><a class="card" href="line/index.html" style="display:block;text-decoration:none;color:inherit;border:2px solid var(--brand)"><p class="eyebrow" style="margin:0">New, 25 October &middot; the editor&rsquo;s design, built</p><h2 class="h2" style="margin:.3rem 0">F. The line: the site talks to you, as the reader you are, at the moment you are in</h2><p class="small" style="margin:0;color:var(--ink-2)">One band under the masthead on every page, never closed, that says one thing: who we think you are and why, what has changed since you were last here, that this page is not written for you, or simply this page&rsquo;s sentence for your role. Seven roles, three depths, eleven visit moments. Six pages, and a catalogue of every line the rules produce. The brief: the line.</p></a></section>
  <section class="block"><div class="card" style="border-left:4px solid var(--ink)"><p class="eyebrow" style="margin:0">Written, 25 October &middot; before the work</p><h2 class="h2" style="margin:.3rem 0">Where the reader\u2019s persona should live: in the address, not in a query</h2><p class="small" style="margin:0;color:var(--ink-2)">The article on URL paths and a single-page site: a link that names its persona (<code>/agencies/as/security/</code>), every page keeping its own path, what that needs from SEO, and how the site stops repainting the whole screen on every click. On the briefs page.</p></div></section>
  <section class="block"><a class="card" href="lens/index.html" style="display:block;text-decoration:none;color:inherit;border:2px solid var(--brand)"><p class="eyebrow" style="margin:0">New, 24 October &middot; a working prototype</p><h2 class="h2" style="margin:.3rem 0">E. The lens: the site shapes itself to you, in front of you</h2><p class="small" style="margin:0;color:var(--ink-2)">Four settings at the top right (how long you have, who you are, what you want to do, what you have seen). Every page is built whole; a change re-lays the page in the same frame, with no reload and no flash, and the next page arrives already shaped. Three pages: the front page, a content page that answers to two of the settings, and a page for the team only. The brief: the lens.</p></a></section>
  <section class="block"><div class="block-head"><h2 class="h2">The four mockups</h2><span class="small">each is a real page, at full width; resize it to see it stack</span></div><div class="thumbs">{thumbs}</div></section>
  <section class="block"><div class="block-head"><h2 class="h2">What is wrong now</h2></div><div class="tiles" style="grid-template-columns:repeat(auto-fill,minmax(300px,1fr))">{prob}</div></section>
  <section class="block"><div class="grid cols-12">
    <div class="card span-7"><div class="block-head"><h2 class="h2">Which pages each reader sees</h2><span class="small">a dark square is in Focus; mid is from Standard; light is only in Everything</span></div><div class="tw"><table class="tbl matrix"><thead><tr><th>Part of the site</th>{head}</tr></thead><tbody>{rows}</tbody></table></div></div>
    <div class="span-5 grid" style="align-content:start">
      <div class="card"><div class="block-head"><h2 class="h2">Pages per reader, per view</h2></div><div class="tw"><table class="tbl matrix"><thead><tr><th>Reader</th>{"".join(f"<th>{E(l)}</th>" for _, l, _ in VIEWS)}</tr></thead><tbody>{counts}</tbody></table></div><p class="small" style="margin-bottom:0">Counted from the {len(all_pages)} pages this release builds.</p></div>
      <div class="card"><h3>Who sees the team console</h3><p class="small" style="color:var(--ink-2);margin:0">Everything view only. It stays public, because how the site is run is part of the story; it just stops being in a reader's way.</p></div>
    </div></div></section>
  <section class="block"><div class="block-head"><h2 class="h2">The menu, per view</h2><span class="small">today: 11 groups, {len(nav_pages)} entries, the same for everyone</span></div><div class="tiles">{menus}</div></section>
  <section class="block"><div class="grid cols-12">
    <div class="card span-6"><h2 class="h2" style="margin-bottom:.6rem">Design principles</h2><ol style="margin:0;padding-left:1.2rem;color:var(--ink-2)">
      <li><b>Use the screen.</b> Up to 1,680 pixels, two or three columns on a laptop, one on a phone; text columns stay readable at 60 to 75 characters.</li>
      <li><b>Answer, picture, detail.</b> Every page opens with its answer in one line, then a picture, then the cards; tables and evidence one click down.</li>
      <li><b>Quiet colour, loud only for status.</b> Ink and paper; red, amber, green and blue only where they mean confirmed, warning, risk or information.</li>
      <li><b>The reader chooses who and how much.</b> Two dials in the top bar, remembered in the browser and in their vault.</li>
      <li><b>Seen things get out of the way.</b> Read items fade, then leave; they return only when they change.</li>
      <li><b>The team has a console.</b> Its own menu and layout, public, out of the reader's path.</li></ol></div>
    <div class="card span-6"><h2 class="h2" style="margin-bottom:.6rem">How to roll it out</h2><ol style="margin:0;padding-left:1.2rem;color:var(--ink-2)">
      <li>The editor picks from these mockups and marks them up; this page records the decisions.</li>
      <li>The design tokens and the wide grid go into the live stylesheet; every page widens at once.</li>
      <li>The top bar with the two dials replaces the menu; the view decides which entries exist.</li>
      <li>The front page and the briefings move to layouts A and B, per persona group.</li>
      <li>Content pages follow pattern C, starting with the agencies, the numbers and the impact.</li>
      <li>The admin pages move into console D.</li></ol></div>
  </div></section>
  <footer class="foot">Mockups built by the design agent from release v{E(VERSION)}; the brief is on the briefs page. Board items record each step.</footer>
</main>'''
    shell('admin/design/index.html', 'Design: the redesign, in four mockups', 'The proposed redesign of the site for review: what is wrong now, the two dials (who you are and how much you see), which pages each reader sees, the menu per view, and four mockups built from the live data.', body, 'notes', 'board', 'everything',
          [('Today', 0), ('What to do', 0), ('The incident', 0), ('The evidence', 0), ('Team console', 0)])
    made += build_lens(ns)
    made += build_line(ns)
    made += build_router(ns)
    return made

def llms_lines(made, BASE_URL):
    views = [x for x in made if x[0] == '404.html' or '/as/' in '/' + x[0]]
    out = ['', '## Design: the redesign, in mockups (for review)']
    out += [f'- [{t}]({BASE_URL}/{p[:-5]}.md): {d}' for p, t, d in made if (p, t, d) not in views]
    out += ['', '## Views: a page written for one reader (the router, and the cards that unfurl in a chat)']
    out += [f'- [{t}]({BASE_URL}/{p[:-5]}.md): {d}' for p, t, d in views]
    return '\n'.join(out) + '\n'


# =========================================================================== v0.12: the redesign, live
# The editor, 24 October: "A, B and C are three different audiences ... implement all of them; D is for everybody,
# the team." Each persona belongs to a track (data/personas.json): A Briefing (the front page), B Operations (/ops/),
# C Analysis (/analysis/). The menu is by task, and the two dials (who you are, how much you see) decide what of it a
# reader sees, in their browser (assets/design/dials.js). The admin pages sit in the console (layout D).

TRACK_HOME = {'a': 'index.html', 'b': 'ops/index.html', 'c': 'analysis/index.html'}
MENU = [('Today', ['today']), ('For you', ['briefing', 'explain', 'ask']), ('What to do', ['act']), ('The incident', ['incident', 'code']),
        ('The evidence', ['analysis', 'evidence']), ('Risk and compliance', ['grc']), ('Stories', ['stories']), ('About', ['site'])]

def scope_css(css, sc='.v2'):
    """Every rule of v2.css under one class, so the redesign's names cannot reach the rest of the site."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out, i, n = [], 0, len(css)
    def sel(s):
        s = s.strip()
        if s in (':root', 'body', 'html'): return sc
        if s == '*': return sc + ', ' + sc + ' *'
        return sc + ' ' + s
    def block(start):
        """Read rules from start until the matching close brace; return (text, end)."""
        res, j = [], start
        while j < n:
            while j < n and css[j] in ' \n\t\r': j += 1
            if j >= n or css[j] == '}': return ''.join(res), j + 1
            k = css.index('{', j); pre = css[j:k].strip()
            if pre.startswith('@media'):
                inner, j = block(k + 1); res.append(pre + '{' + inner + '}\n')
            elif pre.startswith('@keyframes'):
                depth, m = 1, k + 1
                while depth: depth += {'{': 1, '}': -1}.get(css[m], 0); m += 1
                res.append(css[j:m] + '\n'); j = m
            else:
                e = css.index('}', k); body = css[k + 1:e]; j = e + 1
                if pre == 'html' and 'text-size-adjust' in body: continue
                res.append(', '.join(sel(s) for s in pre.split(',')) + '{' + body + '}\n')
        return ''.join(res), j
    text, _ = block(0)
    return text

LIVE_CSS = """
/* the live layer: wider pages with readable text, the task menu and its dials, the full-bleed band, the console */
nav.site .row,footer.site .row{max-width:1680px}
main{max-width:1440px}
main > p,main > ul,main > ol,main section > p,main section > ul,main section > ol,main .lead,main .deck{max-width:82ch}
html[data-track-home] main{max-width:1680px}
.v2 .band{margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw)}
.v2 .band > .shell{max-width:1680px}
.v2 > .shell,.v2 .wrap{max-width:none;padding-left:0;padding-right:0}
.dials-live{display:flex;align-items:center;gap:.45rem;flex-wrap:wrap;font-size:.8rem}
.dials-live select{font:inherit;font-size:.8rem;border:1px solid var(--line2,#cfccc2);border-radius:999px;padding:.25rem .6rem;background:var(--panel,#fff);color:inherit;max-width:14rem}
.dials-live .dl-view{display:inline-flex;border:1px solid var(--line2,#cfccc2);border-radius:999px;padding:2px;background:var(--panel,#fff)}
.dials-live .dl-view button{border:0;background:none;font:inherit;font-size:.76rem;font-weight:600;padding:.2rem .6rem;border-radius:999px;cursor:pointer;color:inherit;opacity:.7}
.dials-live .dl-view button.on{background:var(--fg,#1b1b1a);color:var(--bg,#fff);opacity:1}
.dials-live .dl-home{font-weight:600;white-space:nowrap}
[data-g].dl-hide{display:none!important}
nav.site .tools{flex-wrap:wrap;max-width:100%;min-width:0}
@media (max-width:760px){.dials-live{width:100%}.dials-live select{flex:1;max-width:none;min-width:0}}
.ni.dl-hide{display:none!important}
.console-live{display:grid;grid-template-columns:250px minmax(0,1fr);gap:clamp(1rem,2vw,2rem);align-items:start}
.console-live > .side{position:sticky;top:5rem;height:auto;max-height:calc(100vh - 6rem);border-radius:14px}
.console-live > .cmain{min-width:0}
@media (max-width:900px){.console-live{grid-template-columns:1fr}.console-live > .side{position:static;max-height:none}}
/* the team console uses the whole screen (the editor, 25 October): the reader pages stay at 1,440, admin does not.
   Prose inside it keeps its own 82ch measure from the rule above, so only the tables and lanes get the extra room. */
html[data-path^="admin/"] main,html[data-path^="team/"] main{max-width:none}
html[data-path^="admin/"] .console-live{grid-template-columns:260px minmax(0,1fr)}
/* the briefs page: a list of titles, each its own page (the editor, 25 October) */
.brief-month{display:flex;align-items:baseline;justify-content:space-between;gap:1rem;margin:2rem 0 .6rem;
  padding-bottom:.3rem;border-bottom:2px solid var(--fg,#1b1b1a);font-size:1.05rem}
.brief-month span{font-size:.78rem;font-weight:400;color:var(--dim,#6b6b66)}
.brief-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.4rem}
.brief-row{display:grid;grid-template-columns:4.8rem minmax(0,1fr) 1.4rem;gap:.9rem;align-items:baseline;
  padding:.7rem .9rem;border:1px solid var(--line,#e5e1d8);border-radius:10px;background:var(--panel,#fff);
  text-decoration:none;color:inherit}
.brief-row:hover{border-color:var(--accent,#0f766e);box-shadow:0 2px 10px rgba(15,27,45,.07)}
.brief-row .d{font-family:var(--mono);font-size:.76rem;color:var(--dim,#6b6b66);white-space:nowrap}
.brief-row .d time{display:flex;flex-direction:column;line-height:1.35}
.brief-row .d b{font-weight:600;color:var(--fg,#1b1b1a)}
.brief-row .t{display:flex;flex-direction:column;gap:.15rem;min-width:0}
.brief-row .t b{font-size:1.02rem;line-height:1.3}
.brief-row .w{font-size:.78rem;color:var(--dim,#6b6b66)}
.brief-row .l{font-size:.85rem;color:var(--fg,#1b1b1a);opacity:.75;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.brief-row .go{color:var(--accent,#0f766e);font-weight:700;text-align:right}
.brief-full{max-width:82ch}
.brief-nav{margin-top:1.4rem}
@media (max-width:700px){.brief-row{grid-template-columns:minmax(0,1fr);gap:.2rem}.brief-row .go{display:none}.brief-row .l{white-space:normal}}
/* the chrome, after the lens prototype (24 October): the headline near the top of every page. The bar is one line on
   a laptop; the newcomer line, the reading strip and the page's kind are one slim line each; the rail of a track's
   home comes after its content on a phone. */
@media (min-width:1100px){
  nav.site .row>.brand,nav.site .row>.crumbs{white-space:nowrap}
  nav.site .row>.nav-items{flex:1 0 100%;order:9}
  nav.site .row>.status{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:0 1 auto}
  nav.site .row>.crumbs{white-space:nowrap}
  nav.site .tools{flex-wrap:nowrap;margin-left:auto;flex:none}
  .dials-live{flex-wrap:nowrap}
  .dials-live select{max-width:11rem}
}
@media (min-width:1100px) and (max-width:1499px){nav.site .row>.status{display:none}}
.pbar .row{padding-top:.2rem;padding-bottom:.2rem}
.rs-strip{display:flex;flex-wrap:wrap;align-items:center;gap:.25rem .9rem;padding:.3rem .7rem;margin:.5rem 0 .5rem;font-size:.82rem}
.rs-strip p{margin:0}
.origin{display:inline-flex;max-width:100%;margin:0 0 .5rem;padding:.2rem .6rem}
.origin span{flex:0 1 auto}
@media (max-width:760px){
  .origin span{display:none}
  .rs-strip{font-size:.78rem}
  .pbar{font-size:.78rem}
  .v2 .app>div{order:1}
  .v2 .app>.rail{order:2}
}
"""

def write_live_css(ns):
    src = open(ns['os'].path.join(ns['ROOT'], 'assets', 'design', 'v2.css'), encoding='utf-8').read()
    ns['write']('assets/design/v2-live.css', '/* Generated by admin/build/design.py from assets/design/v2.css: every rule scoped under .v2, then the live layer. Do not edit. */\n' + scope_css(src) + LIVE_CSS)

def track_of(pid, PERSONAS):
    return (PERSONAS.get(pid) or {}).get('track', 'a')

def menu_html(ns, path, up):
    """The task menu: every NAV page, regrouped by what a reader wants to do, each entry tagged with its part of the site."""
    E, U, NAV = ns['E'], ns['U'], ns['NAV']
    seen, groups = set(), OrderedDict((label, []) for label, _ in MENU)
    where = {g: label for label, gs in MENU for g in gs}
    extra = [('ops/index.html', 'Operations view: patch and defend'), ('analysis/index.html', 'Analysis view: weigh the evidence')]
    for p, t in [(p, t) for _, items in NAV for p, t in items] + extra:
        if p in seen: continue
        seen.add(p)
        g = group_of(p)
        if p.startswith('admin/') and not p.startswith('admin/design/'): g = 'site'
        groups[where.get(g, 'About')].append((p, t, g))
    out = []
    for label, items in groups.items():
        if not items: continue
        active = any(p == path for p, _, _ in items)
        subs = ''.join(f'<a class="sl{" here" if p == path else ""}" href="{up}{U(p)}" data-g="{E(g)}">{E(t)}</a>' for p, t, g in items)
        gs = ' '.join(sorted({g for _, _, g in items}))
        out.append(f'<div class="ni" data-gs="{E(gs)}"><a class="nl{" here" if active else ""}" href="{up}{U(items[0][0])}">{E(label)}<span class="caret">&#9662;</span></a><div class="sub">{subs}</div></div>')
    return ''.join(out)

def dials_html(ns, up):
    E, J, PERSONAS = ns['E'], ns['J'], ns['PERSONAS']
    cfg = {'groups': {g: [f, s] for g, (_, _, f, s) in GROUPS.items()},
           'personas': {pid: {'group': p['group'], 'track': p.get('track', 'a'), 'depth': p['depth'], 'person': p['person'], 'label': p['label']} for pid, p in PERSONAS.items()},
           'homes': TRACK_HOME, 'tracks': {k: v['label'] for k, v in ns['D']['personas'].get('tracks', {}).items()}}
    opts = ''.join(f'<option value="{E(pid)}">{E(p["label"])}</option>' for pid, p in PERSONAS.items())
    return (f'<div class="dials-live" aria-label="Who you are, and how much of the site you see">'
            f'<select class="dl-who" aria-label="Who are you?"><option value="">Who are you?</option>{opts}</select>'
            f'<span class="dl-view" role="group" aria-label="How much of the site"><button type="button" data-v="focus">Focus</button><button type="button" data-v="standard">Standard</button><button type="button" data-v="everything">Everything</button></span>'
            f'<a class="dl-home" href="{up}index.html" hidden>Your home</a></div>'
            f'<script type="application/json" id="p2s-dials">{J(cfg)}</script>')

DIALS_JS = r"""// php.oct.2026.newsroom.sgit.ai: the two dials, who you are and how much of the site you see. Generated by
// admin/build/design.py. Kept in this browser only (p2s.persona, shared with the rest of the site, and p2s.view).
(function () {
  'use strict';
  var cfgEl = document.getElementById('p2s-dials'); if (!cfgEl) return;
  var C = JSON.parse(cfgEl.textContent), html = document.documentElement, up = '../'.repeat(((html.getAttribute('data-root') || '').match(/\.\.\//g) || []).length), here = html.getAttribute('data-path') || '';
  function rel(h) { return /^[a-z0-9][a-z0-9\/._-]*$/i.test(String(h || '')) ? String(h) : null; }   // a home is a page of this site, never a scheme
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function set(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} }
  function persona() { var id = get('p2s.persona'); return id && C.personas[id] ? id : null; }
  function view() { var v = get('p2s.view'); if (v === 'focus' || v === 'standard' || v === 'everything') return v; var p = persona(); if (!p) return 'everything'; var P = C.personas[p]; return (P.depth === 1 || P.group === 'understand') ? 'focus' : 'standard'; }
  function level(g, pid) {
    var r = C.groups[g]; if (!r) return 'e'; var P = C.personas[pid];
    if (r[0].indexOf('*') >= 0 || r[0].indexOf(pid) >= 0) return 'f';
    if (r[1].indexOf('*') >= 0 || r[1].indexOf(P.group) >= 0 || r[1].indexOf(pid) >= 0) return 's';
    return 'e';
  }
  function shows(g, pid, v) { if (v === 'everything' || !pid) return true; var l = level(g, pid); return l === 'f' || (v === 'standard' && l === 's'); }
  function apply() {
    var pid = persona(), v = view();
    html.setAttribute('data-view', v); if (pid) html.setAttribute('data-persona', pid); else html.removeAttribute('data-persona');
    document.querySelectorAll('[data-g]').forEach(function (a) { a.classList.toggle('dl-hide', !shows(a.getAttribute('data-g'), pid, v)); });
    document.querySelectorAll('.ni[data-gs]').forEach(function (ni) { ni.classList.toggle('dl-hide', !ni.querySelector('[data-g]:not(.dl-hide)')); });
    document.querySelectorAll('.dl-who').forEach(function (s) { s.value = pid || ''; });
    document.querySelectorAll('.dl-view button').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-v') === v); });
    var home = pid ? rel(C.homes[C.personas[pid].track]) : null;
    document.querySelectorAll('.dl-home').forEach(function (a) { if (home && home !== here) { a.hidden = false; a.href = up + home; a.textContent = (C.tracks[C.personas[pid].track] || 'Your') + ' home'; } else a.hidden = true; });
    var P = pid ? C.personas[pid] : null;
    document.querySelectorAll('[data-answer-for]').forEach(function (box) {
      var src = document.getElementById('p2s-answers'); if (!src) return; var A = JSON.parse(src.textContent), a = A[pid] || A[box.getAttribute('data-answer-for')];
      if (!a) return; var w = box.querySelector('[data-a-who]'), t = box.querySelector('[data-a-text]'), av = box.querySelector('[data-a-av]');
      if (w) w.textContent = 'for ' + a.person + ', ' + a.label.toLowerCase(); if (t) t.textContent = a.answer; if (av) { av.textContent = a.person.charAt(0); av.className = 'av ' + a.group; }
    });
  }
  // the front page sends a reader who said who they are to their track's home, once per visit; ?home stays here
  (function () {
    var pid = persona(); if (!pid || here !== 'index.html' || /[?&]home\b/.test(location.search)) return;
    var t = C.personas[pid].track, home = rel(C.homes[t]);
    var seen = null; try { seen = sessionStorage.getItem('p2s.routed'); } catch (e) {}
    if (t !== 'a' && home && !seen) { try { sessionStorage.setItem('p2s.routed', '1'); } catch (e) {} location.replace(up + home); }
  })();
  document.addEventListener('change', function (e) {
    if (e.target && e.target.classList && e.target.classList.contains('dl-who')) {
      var id = e.target.value || null; set('p2s.persona', id); set('p2s.view', null); apply();
      var home = id ? rel(C.homes[C.personas[id].track]) : null;
      if (home && (here === 'index.html' || here === 'ops/index.html' || here === 'analysis/index.html') && home !== here) location.href = up + home + (home === 'index.html' ? '?home' : '');
    }
  });
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('.dl-view button') : null;
    if (b) { set('p2s.view', b.getAttribute('data-v')); apply(); }
  });
  apply();
})();
"""

def answers_json(ns):
    PERSONAS, J = ns['PERSONAS'], ns['J']
    return f'<script type="application/json" id="p2s-answers">{J({pid: {"person": p["person"], "label": p["label"], "group": p["group"], "answer": p["answer"]} for pid, p in PERSONAS.items()})}</script>'

def answer_card(ns, default):
    E, PERSONAS = ns['E'], ns['PERSONAS']
    p = PERSONAS[default]
    return (f'<aside class="ans" data-answer-for="{E(default)}"><div class="who-line"><span class="av {E(p["group"])}" data-a-av>{E(p["person"][0])}</span>'
            f'<div><b>Your answer in thirty seconds</b><div class="small" style="color:var(--band-muted)" data-a-who>for {E(p["person"])}, {E(p["label"].lower())}</div></div></div>'
            f'<p data-a-text>{E(p["answer"])}</p><p class="small" style="color:var(--band-muted);margin-bottom:0">Choose who you are in the bar above and this answer, the menu and your home change to fit.</p></aside>')

def kpi(ns, cls, k, v, d, href=None, up=''):
    E, U = ns['E'], ns['U']
    inner = f'<div class="k">{E(k)}</div><div class="v">{E(v)}</div><div class="d">{E(d)}</div>'
    return f'<a class="card kpi {cls}" href="{up}{U(href)}" style="text-decoration:none;color:inherit">{inner}</a>' if href else f'<div class="card kpi {cls}">{inner}</div>'

def agency_parts(ns, up):
    """The agencies as stance columns under one colour scale, and a card each: mockup C, for the live page."""
    D, E, SOURCES, short_name, U = ns['D'], ns['E'], ns['SOURCES'], ns['short_name'], ns['U']
    BUCKETS = [('none', 'No offline advice', 'var(--info)'), ('consider', 'Consider it, or after other steps', '#d6a556'), ('restrict', 'Restrict access', 'var(--warn)'),
               ('isolate', 'Isolate from the internet', 'var(--warn)'), ('yes', 'Take it offline', 'var(--alert)')]
    def bucket(o): return 'yes' if o == 'yes' else 'isolate' if o.startswith('isolate') else 'restrict' if o == 'restrict from abroad' else 'consider' if o in ('after mitigations', 'consider') else 'none' if o == 'none' else None
    cols = ''.join(f'<div class="bk"><div class="bk-h" style="border-top-color:{c}"><b>{sum(1 for a in D["agencies"] if bucket(a["offline"]) == k)}</b> {E(lab)}</div><div class="chips">' + ''.join(f'<span class="chip"><b style="font-family:var(--mono);font-weight:600">{E(a["country"].split()[0])}</b> {E(a["agency"].split(" (")[0])}</span>' for a in D['agencies'] if bucket(a['offline']) == k) + '</div></div>' for k, lab, c in BUCKETS)
    unread = [a for a in D['agencies'] if bucket(a['offline']) is None]
    spectrum = f'<div class="card"><div class="block-head"><h2 class="h2">The spectrum</h2><span class="small">every agency, by what it says to do with a system you cannot patch</span></div><div class="rail-g"></div><div class="buckets">{cols}</div>' + (f'<p class="small" style="margin:.8rem 0 0">Not readable from this capture environment: {", ".join(E(a["agency"]) for a in unread)}.</p>' if unread else '') + '</div>'
    def scls(o): return {'yes': 's-yes', 'isolate': 's-isolate', 'restrict': 's-isolate', 'consider': 's-consider', 'none': 's-none'}.get(bucket(o), 's-unknown')
    def slab(o): return {'yes': 'Take offline', 'none': 'No offline advice', 'unknown': 'Could not be read'}.get(o, o[0].upper() + o[1:])
    cards = ''.join(f'''<article class="card agency {scls(a["offline"])}"><div style="display:flex;justify-content:space-between;gap:.5rem"><h3 style="margin:0">{E(a["agency"])}</h3><span class="cc">{E(a["country"])}</span></div>
<span class="pill {"alert" if a["offline"] == "yes" else "warn" if scls(a["offline"]) in ("s-isolate", "s-consider") else "info" if a["offline"] == "none" else ""}">{E(slab(a["offline"]))}</span>
{f"<q>{E(a['offline_text'][:200])}</q>" if a.get("offline_text") and a["offline"] not in ("none", "unknown") else f"<p class=small style='margin:0'>{E((a.get('note') or '')[:170])}</p>"}
<div class="chips">{"".join(f"<a class=chip href='{up}sources/{U(s)}/index.html'>{E(short_name(SOURCES[s]))}</a>" for s in a["sources"][:3] if s in SOURCES)}</div></article>''' for a in D['agencies'])
    return spectrum, f'<div class="tiles" style="grid-template-columns:repeat(auto-fill,minmax(270px,1fr))">{cards}</div>'

def console_side(ns, path, up):
    E, U, NAV, D = ns['E'], ns['U'], ns['NAV'], ns['D']
    seen, rows = set(), []
    for _, items in NAV:
        for p, t in items:
            if p in seen or not (p.startswith(('admin/', 'status/', 'team/')) or p in ('method/index.html', 'brief/index.html', 'corrections/index.html')): continue
            seen.add(p); rows.append((p, t))
    def area(p):
        if p.startswith(('admin/board', 'admin/agents', 'admin/roles', 'team/', 'admin/versions', 'status/', 'admin/index')): return 'Console'
        if p.startswith(('admin/briefs', 'brief/', 'corrections/', 'admin/factcheck', 'admin/sherpa', 'admin/synthetic', 'method/')): return 'Editorial'
        return 'Systems'
    out = OrderedDict((k, []) for k in ('Console', 'Editorial', 'Systems'))
    for p, t in rows: out[area(p)].append((p, t))
    html = f'<a class="logo" href="{up}admin/index.html"><i>PHP</i>Team console</a>'
    for k, items in out.items():
        if not items: continue
        html += f'<h4>{E(k)}</h4>' + ''.join(f'<a href="{up}{U(p)}"{" class=here" if p == path else ""}>{E(t.split(":")[0])}</a>' for p, t in items)
    html += f'<h4>Reader site</h4><a href="{up}index.html">Back to the reader site</a>'
    return f'<nav class="side" aria-label="Team console">{html}</nav>'

def console_overview(ns):
    D, E, VERSION = ns['D'], ns['E'], ns['VERSION']
    A = D['admin']; bstat = Counter(b['status'] for b in A['board'])
    def tickets(status, n=6):
        rows = [b for b in A['board'] if b['status'] == status][-n:][::-1]
        return ''.join(f'<div class="ticket"><span class="id">#{E(b["id"])}</span><div>{E(b["title"][:120])}{"…" if len(b["title"]) > 120 else ""}</div><div class="o"><span>{E(b["owner"])}</span>{("<span>v" + E(b["version"]) + "</span>") if b.get("version") else ""}</div></div>' for b in rows)
    rel = D['versions']['versions'][:6]
    rels = ''.join(f'<tr><td style="font-family:var(--mono);white-space:nowrap"><a href="versions.html#v{E(r["version"])}">v{E(r["version"])}</a></td><td class="small" style="white-space:nowrap">{E(r["date"])}</td><td>{E(r["title"][:140])}{"…" if len(r["title"]) > 140 else ""}</td></tr>' for r in rel)
    kp = ''.join([kpi(ns, 'info', 'Release', f'v{VERSION}', f'{len(D["versions"]["versions"])} releases since 22 October'), kpi(ns, 'warn', 'Open on the board', str(bstat['open']), f'{bstat["done"]} done, {bstat.get("waiting", 0)} waiting', 'admin/board/index.html', '../'),
                  kpi(ns, 'good', 'Agents', str(len(A['roles'])), 'each with a mandate and a key', 'admin/roles/index.html', '../'), kpi(ns, 'info', 'Sources in the vault', str(len(D['sources'])), f'{sum(1 for s in D["sources"] if s.get("status") == "captured")} captured', 'sources/index.html', '../')])
    return f'''<div class="v2 console-top">
<p class="eyebrow">Team console &middot; public, like everything here</p>
<div class="tiles" style="margin:.6rem 0 1.4rem">{kp}</div>
<div class="block-head"><h2 class="h2">The board</h2><a class="small" href="board/index.html">every row &rarr;</a></div>
<div class="kanban"><div class="lane"><h3>Open <span>{bstat["open"]}</span></h3>{tickets("open")}</div><div class="lane"><h3>Waiting <span>{bstat.get("waiting", 0)}</span></h3>{tickets("waiting")}</div><div class="lane"><h3>Done <span>{bstat["done"]}</span></h3>{tickets("done")}</div></div>
<div class="card" style="margin-top:1.4rem"><div class="block-head"><h2 class="h2">Latest releases</h2><a class="small" href="versions.html">all {len(D["versions"]["versions"])} &rarr;</a></div><div class="tw"><table class="tbl">{rels}</table></div></div>
</div>'''

def it_mark(E, iid, it):
    return f'<span class="it" data-item="{E(iid)}" data-h="{E(it["hash"])}" data-n="{E(str(it.get("v", 1)))}"></span>'

def build_tracks(ns):
    """The homes of tracks B (Operations) and C (Analysis), as live pages through the site's own page()."""
    D, E, U, PERSONAS, page = ns['D'], ns['E'], ns['U'], ns['PERSONAS'], ns['page']
    SOURCES, short_name, human_time, STORY = ns['SOURCES'], ns['short_name'], ns['human_time'], ns['STORY']
    claims = D['claims']; st = Counter(c['status'] for c in claims); when = human_time(STORY['data_as_of'])
    items = ns['all_items']()  # this build's items; data/items.json on disk is the previous build's until save_items() runs (board 175)
    cl = {('fact-' + c['id']): c for c in claims}
    tl_days = Counter(t['at'][:10] for t in D['timeline'] if t['at'][:7] == '2026-10'); days = sorted(tl_days)

    # ------------------------------------------------------------------ B: Operations
    sam = PERSONAS['security']
    feed = sorted([(k, v) for k, v in items.items() if v.get('kind') in ('fact', 'event', 'question', 'story', 'front')],
                  key=lambda kv: (kv[1].get('date') or '', kv[1].get('changed') or '', kv[0]), reverse=True)[:14]
    def fitem(k, v):
        c = cl.get(k); status = c['status'] if c else ''
        col = {'confirmed': 'good', 'reported': 'info', 'disputed': 'warn', 'contradicted': 'warn', 'unverified': 'alert'}.get(status, '')
        text = c['claim'] if c else v['title']
        srcs = ''.join(f'<a class="chip" href="../sources/{U(s)}/index.html">{E(short_name(SOURCES[s]))}</a>' for s in (c['sources'] if c else [])[:4] if s in SOURCES)
        spill = f'<span class="pill {col}">{E(status)}</span>' if status else ''
        return (f'<article class="card fitem lv"><div><div class="meta">{it_mark(E, k, v)}<span class="pill">{E(v["kind"])}</span>{spill}<span class="small">v{E(v.get("changed", ""))} &middot; {E(v.get("date") or "")}</span></div>'
                f'<h3><a href="../{U(v["path"])}" style="color:inherit;text-decoration:none">{E(text[:200])}</a></h3>{f"<div class=chips>{srcs}</div>" if srcs else ""}</div></article>')
    steps = [('Patch internet-facing first', 'mod_php, then FPM, then the rest. Restart every worker; rebuild every image; check the running version after the restart.', 'playbook/index.html'),
             ('Bound the known paths', 'session.upload_progress off, low post_max_size, fatal_error_backtraces off on 8.5, pm.max_requests on FPM. Each blocks a path; none is a fix.', 'flaws/index.html#mitigations'),
             ('Watch the process tree', 'Alert on a PHP worker spawning a shell or a downloader. A clean access log proves nothing about the host.', 'defence/index.html')]
    actions = ''.join(f'<a class="card action" href="../{U(h)}" style="text-decoration:none;color:inherit"><div class="n">{i + 1}</div><div><h3>{E(t)}</h3><p>{E(x)}</p></div></a>' for i, (t, x, h) in enumerate(steps))
    donut = svg_donut([(st[k], c, k) for k, c in STATUS_COL.items() if st[k]])
    dleg = ''.join(f'<li><i style="background:{c}"></i>{st[k]} {E(k)}</li>' for k, c in STATUS_COL.items() if st[k])
    dmax = max(tl_days.values()) if tl_days else 1
    bars = ''.join(f'<div class="{"hot" if d >= "2026-10-20" else ""}" style="height:{max(3, round(100 * tl_days[d] / dmax))}%" title="{tl_days[d]} events on {E(d)}"></div>' for d in days)
    blabels = ''.join(f'<span>{E(d[8:])}</span>' for d in days)
    ex = ''.join(f'<li><span class="small">{E(x["when"])}</span><div class="t" style="font-size:.9rem">{E(x["who"].split("(")[0].strip())}: {E(x["what"][:100])}</div></li>' for x in D['exploitation'][:4])
    rnav = ''.join(f'<a href="../{U(h)}">{E(t)}<span>{E(n)}</span></a>' for t, n, h in [('If you run PHP', 'steps', 'playbook/index.html'), ('Check your stack', '', 'stack/index.html'), ('Patching: who gets a fix', '', 'patching/index.html'),
        ('The two flaws', '', 'flaws/index.html'), ('Exploitation signals', '', 'exploitation/index.html'), ('Detection and defence', '', 'defence/index.html'), ('The agencies', str(len(D['agencies'])), 'agencies/index.html'), ('Every claim', str(len(claims)), 'claims/index.html'), ('The code', '', 'code/index.html')])
    path_html = ''.join(f'<li><a href="../{U(x)}">{E(ns["nav_title"](x))}</a></li>' for x in sam['path'])
    body = f'''<div class="v2">
<div class="app">
  <aside class="rail">
    <div class="card" data-answer-for="security"><div style="display:flex;gap:.7rem;align-items:center"><span class="av act" data-a-av style="width:42px;height:42px">{E(sam["person"][0])}</span><div><b>Operations</b><div class="small" data-a-who>for {E(sam["person"])}, {E(sam["label"].lower())}</div></div></div>
      <p class="small" style="margin:.7rem 0 .2rem">Your reading path</p><ol class="small" style="margin:0;padding-left:1.1rem">{path_html}</ol></div>
    <nav class="railnav card flat" style="padding:.4rem" aria-label="Operations">{rnav}</nav>
  </aside>
  <div>
    <p class="eyebrow">Operations &middot; data as of {E(when)}</p>
    <h1 class="display" style="font-size:clamp(1.7rem,2.6vw,2.6rem);margin:.3rem 0 .5rem">What changed, what to do next, and how sure we are</h1>
    <p class="lede" style="margin:0 0 1.2rem" data-answer-for="security"><span data-a-text>{E(sam["answer"])}</span></p>
    <section><div class="block-head"><h2 class="h2">Your next three actions</h2><a class="small" href="../playbook/index.html">The whole playbook</a></div><div class="actions">{actions}</div></section>
    <section class="feed"><div class="block-head" style="margin-top:1.6rem"><h2 class="h2">What changed, newest first</h2><a class="small" href="../whatsnew/index.html">Release by release</a></div>
      {"".join(fitem(k, v) for k, v in feed)}
      <p class="small">Mark an item read with its circle: it fades, and leaves when you choose to hide read items. It comes back only if what it says changes.</p></section>
  </div>
  <aside class="rail right">
    <div class="card"><h3>How sure are we?</h3><div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">{donut}<ul class="legend" style="flex-direction:column">{dleg}</ul></div><p class="small" style="margin:.4rem 0 0"><a href="../factcheck/index.html">The fact-check</a></p></div>
    <div class="card"><h3>Events per day, October</h3><div class="bars">{bars}</div><div class="bars-l">{blabels}</div><p class="small" style="margin:.5rem 0 0">Red: from the leak on 20 October. <a href="../timeline/index.html">The timeline</a></p></div>
    <div class="card"><h3>Exploitation signals</h3><ul class="delta">{ex}</ul><p class="small" style="margin:0"><a href="../exploitation/index.html">Every signal</a> &middot; <a href="../compromise/index.html">No named compromise: the evidence</a></p></div>
    <div class="card"><h3>Fixed in</h3><div class="chips">{"".join(f"<span class=chip style='font-family:var(--mono)'>{E(v)}</span>" for v in D["affected"]["fixed"])}</div><p class="small" style="margin:.5rem 0 0">8.1 and older: source backports only. <a href="../affected/index.html">Affected systems</a></p></div>
  </aside>
</div></div>{answers_json(ns)}'''
    page('ops/index.html', 'Operations: what changed, what to do next, how sure we are', 'The home for people who patch and defend: the next three actions, everything that changed newest first with what you have read marked, and the state of the evidence as charts: facts by status, events per day, exploitation signals, fixed versions.', body, kind='story', topics='php2shell operations')

    # ------------------------------------------------------------------ C: Analysis
    nums = D['numbers']
    ncards = ''.join(f'<a class="card kpi {"good" if n["status"] == "confirmed" else "warn" if n["status"] in ("disputed", "contradicted") else "alert" if n["status"] == "unverified" else "info"}" href="../numbers/index.html#{U(n["id"])}" style="text-decoration:none;color:inherit"><div class="k">{E(n["status"])}</div><div class="v">{E(n["value"])}</div><div class="d">{E(n["of"])}</div></a>' for n in nums[:8])
    spectrum, _ = agency_parts(ns, '../')
    topics = Counter(c['topic'] for c in claims)
    tmax = max(topics.values()) if topics else 1
    tbars = ''.join(f'<div style="display:grid;grid-template-columns:9rem minmax(0,1fr) 2.5rem;gap:.6rem;align-items:center;margin:.35rem 0"><span class="small" style="color:var(--ink-2)">{E(t)}</span><span style="display:flex;height:14px;border-radius:5px;overflow:hidden;background:var(--surface-2)">' + ''.join(f'<i style="width:{100 * sum(1 for c in claims if c["topic"] == t and c["status"] == k) / tmax:.1f}%;background:{col}" title="{k}"></i>' for k, col in STATUS_COL.items()) + f'</span><b class="small">{n}</b></div>' for t, n in topics.most_common())
    contested = [c for c in claims if c['status'] in ('disputed', 'contradicted', 'unverified')]
    cont = ''.join(f'<li><span class="pill {"alert" if c["status"] == "unverified" else "warn"}">{E(c["status"])}</span> <a href="../facts/{U(c["id"])}/index.html" style="color:inherit">{E(c["claim"][:170])}</a><div class="small">who says it: {E(c["by"][:90])}</div></li>' for c in contested[:10])
    body = f'''<div class="v2">
<section class="band"><div class="shell hero">
  <div><p class="eyebrow">Analysis &middot; data as of {E(when)}</p><h1 class="display">{len(claims)} facts. {st["confirmed"]} confirmed. {st["disputed"] + st["contradicted"] + st["unverified"]} still contested.</h1>
  <p class="lede">Every fact on this site carries one of five words for how far it can be trusted, and links to the saved pages it rests on. This is the view for weighing them: the numbers and what each measures, where governments disagree, and what is contested.</p></div>
  <div class="ans" data-answer-for="journalist"><div class="who-line"><span class="av communicate" data-a-av>R</span><div><b>Your answer in thirty seconds</b><div class="small" style="color:var(--band-muted)" data-a-who>for {E(PERSONAS["journalist"]["person"])}, journalist</div></div></div><p data-a-text>{E(PERSONAS["journalist"]["answer"])}</p></div>
</div></section>
<section class="block"><div class="grid cols-12">
  <div class="card span-4"><h2 class="h2" style="margin-bottom:.6rem">How sure are we?</h2><div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">{svg_donut([(st[k], c, k) for k, c in STATUS_COL.items() if st[k]])}<ul class="legend" style="flex-direction:column">{"".join(f"<li><i style='background:{c}'></i>{st[k]} {E(k)}</li>" for k, c in STATUS_COL.items() if st[k])}</ul></div><p class="small" style="margin-bottom:0"><a href="../factcheck/index.html">The fact-check</a> &middot; <a href="../claims/index.html">every claim</a></p></div>
  <div class="card span-8"><div class="block-head"><h2 class="h2">The facts by topic, and by status</h2><span class="small">green confirmed, blue reported, amber disputed, red unverified</span></div>{tbars}</div>
</div></section>
<section class="block"><div class="block-head"><h2 class="h2">The numbers in the news, and how far each holds</h2><a class="small" href="../numbers/index.html">What each one measures</a></div><div class="tiles">{ncards}</div></section>
<section class="block">{spectrum}<p class="small"><a href="../agencies/index.html">Agency by agency, with their own words &rarr;</a></p></section>
<section class="block"><div class="grid cols-12">
  <div class="card span-7"><div class="block-head"><h2 class="h2">Contested: disputed, contradicted, unverified</h2><span class="small">{len(contested)} facts</span></div><ul class="delta">{cont}</ul></div>
  <div class="span-5 grid" style="align-content:start">
    <a class="card" href="../graph/index.html" style="text-decoration:none;color:inherit"><h3>As a graph</h3><p class="small" style="margin:0;color:var(--ink-2)">Every claim, event and source, and the citations between them.</p></a>
    <a class="card" href="../actors/index.html" style="text-decoration:none;color:inherit"><h3>Who says what</h3><p class="small" style="margin:0;color:var(--ink-2)">Every party quoted, with the claims each one makes.</p></a>
    <a class="card" href="../sources/index.html" style="text-decoration:none;color:inherit"><h3>Every source</h3><p class="small" style="margin:0;color:var(--ink-2)">{len(D["sources"])} pages, saved and fingerprinted at the minute they were read.</p></a>
    <a class="card" href="../articles/index.html" style="text-decoration:none;color:inherit"><h3>Stories</h3><p class="small" style="margin:0;color:var(--ink-2)">Signed and dated analysis, written here and kept as written.</p></a>
  </div></div></section>
</div>{answers_json(ns)}'''
    page('analysis/index.html', 'Analysis: how sure we are, and where the sources disagree', 'The home for people who weigh the evidence: every fact by status and topic, the numbers in the news with how far each holds, where governments disagree, and what is still contested, each linked to its saved sources.', body, kind='story', topics='php2shell analysis evidence')


# =========================================================================== the lens (prototype E, 24 October 2026)
# The editor's note of 24 October: the whole site reflects the reader, and changes in front of them, in real time, as
# they move a setting; no reload, no flicker, the same from page to page. The design: four settings in one control at
# the top right (time, who, aim, seen). Every page is built whole; each block says which settings show it (data-t,
# data-for, data-aim) and where it goes for each aim (--o-u, --o-a, --o-v). A blocking script in <head> (lens-boot.js)
# puts the reader's settings on <html> before the first paint, and lens.css does the rest, so a page arrives already
# shaped; lens.js only wires the control, counts, and animates a change with the View Transitions API.
# Brief: admin/content/briefs/2026-10-24__brief__the-lens.md

LZ_TIMES = [('1', '1 min', 'The answer, and what to do'), ('5', '5 min', 'The situation and the evidence for it'), ('15', '15 min', 'The detail: what is contested, how it unfolded'), ('all', 'All', 'Everything we hold')]
LZ_AIMS = [('understand', 'Understand it', 'u'), ('act', 'Know what to do', 'a'), ('verify', 'Check the evidence', 'v')]
LZ_SEEN = [('show', 'Show'), ('fade', 'Fade'), ('hide', 'Hide')]
LZ_TEAM = ('team', 'I work on this site')

def lens_css(ns):
    """lens.css: the rules that shape a page from the settings on <html>. Generated, because the readers come from data."""
    PERSONAS, groups = ns['PERSONAS'], [g['id'] for g in ns['D']['personas']['groups']] + [LZ_TEAM[0]]
    r = [r"""/* php.oct.2026.newsroom.sgit.ai: the lens. Generated by admin/build/design.py; the settings are put on <html> by
   lens-boot.js before the first paint: data-t (1, 5, 15, all), data-group, data-who, data-aim, data-seen. */
@view-transition{navigation:auto}
.lz-flow{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));grid-auto-flow:row dense;gap:clamp(.9rem,1.4vw,1.4rem);align-items:start}
.lz-flow>*{grid-column:span 12;min-width:0}
.lz-flow>.w8{grid-column:span 8}.lz-flow>.w7{grid-column:span 7}.lz-flow>.w6{grid-column:span 6}.lz-flow>.w5{grid-column:span 5}.lz-flow>.w4{grid-column:span 4}
@media (max-width:980px){.lz-flow>.w8,.lz-flow>.w7,.lz-flow>.w6,.lz-flow>.w5,.lz-flow>.w4{grid-column:span 12}}
.lb{order:var(--o-u,50)}
html[data-aim=act] .lb{order:var(--o-a,50)}
html[data-aim=verify] .lb{order:var(--o-v,50)}
.lz-ask{order:-1}.lz-more{order:999}
/* time: a block shows from its own tier up */
html[data-t="1"] .lb:not([data-t="1"]){display:none}
html[data-t="5"] .lb[data-t="15"],html[data-t="5"] .lb[data-t=all]{display:none}
html[data-t="15"] .lb[data-t=all]{display:none}
html[data-t=all] .lz-more{display:none}
/* aim: in 1 and 5 minutes, only the blocks for the reader's aim */
"""]
    for a, _, _ in LZ_AIMS:
        r.append(f'html[data-aim={a}]:is([data-t="1"],[data-t="5"]) .lb[data-aim]:not([data-aim~={a}]):not([data-aim~="*"]){{display:none}}\n')
    r.append('/* who: a block for some readers only; a variant of a block for one reader or one group. A reader who has not\n   said is read as someone who wants to understand it. */\n.lv{display:none}\nhtml:not([data-group]) .lv[data-only~="_"]{display:revert}\n'
             'html:not([data-group]) .lb[data-for]:not([data-for~=understand]):not([data-for~="*"]){display:none}\n')
    for g in groups:
        r.append(f'html[data-group={g}] .lb[data-for]:not([data-for~={g}]):not([data-for~="*"]){{display:none}}\n')
        r.append(f'html[data-group={g}] .lv[data-only~={g}]{{display:revert}}\n')
    for pid in PERSONAS:
        r.append(f'html[data-who={pid}] .lv[data-only~={pid}]{{display:revert}}\n')
    r.append('html[data-who] .has-g>.lv:not(.g){display:none}\n')
    r.append(r"""/* a page that serves only some readers */
html[data-lz-for]:not([data-lz-ok]) .lz-gate{display:block}
.lz-gate{display:none}
/* seen: the boot script writes one rule per block the reader marked */
html[data-seen=fade] .lb.is-seen{opacity:.42}
html[data-seen=fade] .lb.is-seen:hover{opacity:1}
/* first visit: the three questions, until the reader answers or skips */
html[data-lz-set] .lz-ask{display:none}
.lz-ask .q{display:none}.lz-ask[data-step="1"] .q1,.lz-ask[data-step="2"] .q2,.lz-ask[data-step="3"] .q3{display:block}
/* the control */
.lz-top{position:sticky;top:0;z-index:30;background:color-mix(in srgb,var(--surface) 92%,transparent);backdrop-filter:saturate(1.4) blur(8px);border-bottom:1px solid var(--line)}
.lz-top .shell{display:flex;align-items:center;gap:1rem;min-height:58px}
.lz-logo{font-family:var(--serif);font-weight:700;font-size:1.15rem;color:var(--ink);text-decoration:none;white-space:nowrap}
.lz-logo b{background:var(--alert);color:#fff;border-radius:6px;padding:.1rem .4rem;margin-right:.4rem;font-family:var(--sans);font-size:.78rem;vertical-align:2px}
.lz-tabs{display:flex;gap:.2rem;flex:1;min-width:0;overflow-x:auto;scrollbar-width:none}
.lz-tabs a{padding:.4rem .7rem;border-radius:8px;color:var(--ink-2);text-decoration:none;font-size:.9rem;white-space:nowrap}
.lz-tabs a[aria-current]{background:var(--surface-2);color:var(--ink);font-weight:600;box-shadow:inset 0 0 0 1px var(--line)}
.lz-chip{display:inline-flex;align-items:center;gap:.5rem;border:1px solid var(--line-2);background:var(--surface);color:var(--ink);border-radius:999px;padding:.35rem .5rem .35rem .8rem;font:inherit;font-size:.86rem;cursor:pointer;white-space:nowrap;box-shadow:var(--shadow)}
.lz-chip b{font-weight:700}.lz-chip .sep{color:var(--muted)}
.lz-chip .av{width:24px;height:24px;font-size:.72rem}
.lz-chip.pulse{animation:lzp 1.2s ease 2}
@keyframes lzp{50%{box-shadow:0 0 0 6px color-mix(in srgb,var(--brand) 30%,transparent)}}
.lz-panel{position:fixed;right:var(--gut);top:var(--lz-top,64px);width:min(440px,calc(100vw - 2*var(--gut)));background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:0 18px 50px rgba(15,27,45,.22);padding:1rem 1.1rem;z-index:40}
.lz-panel[hidden]{display:none}
.lz-row{margin:0 0 .9rem}.lz-row:last-of-type{margin-bottom:.4rem}
.lz-row>b{display:block;font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:.35rem}
.lz-seg{display:flex;flex-wrap:wrap;gap:.3rem}
.lz-seg button{font:inherit;font-size:.86rem;border:1px solid var(--line-2);background:var(--surface-2);color:var(--ink);border-radius:9px;padding:.35rem .6rem;cursor:pointer;text-align:left;line-height:1.2}
.lz-seg button small{display:block;color:var(--muted);font-size:.72rem}
.lz-seg button[aria-pressed=true]{background:var(--ink);color:var(--surface);border-color:var(--ink)}
.lz-seg button[aria-pressed=true] small{color:color-mix(in srgb,var(--surface) 75%,transparent)}
.lz-row.off{opacity:.45}.lz-row.off button{cursor:not-allowed}
.lz-row .why{font-size:.78rem;color:var(--muted);margin:.3rem 0 0}
.lz-panel select{font:inherit;font-size:.86rem;margin-top:.4rem;width:100%;padding:.35rem;border-radius:8px;border:1px solid var(--line-2);background:var(--surface);color:var(--ink)}
.lz-status{display:flex;flex-wrap:wrap;gap:.3rem .8rem;align-items:center;font-size:.86rem;color:var(--ink-2);margin:.2rem 0 1.2rem}
.lz-status .meter{flex:0 0 120px;height:6px;border-radius:999px;background:var(--line);overflow:hidden}
.lz-status .meter i{display:block;height:100%;background:var(--brand);width:var(--p,50%);transition:width .35s}
.lz-status button{font:inherit;border:0;background:none;color:var(--brand);text-decoration:underline;cursor:pointer;padding:0}
.lz-ask{border:2px solid var(--brand);background:var(--brand-soft)}
.lz-ask h2{margin:.1rem 0 .7rem}
.lz-ask .lz-seg button{font-size:1rem;padding:.55rem .9rem;background:var(--surface)}
.lz-ask .lz-seg button[aria-pressed=true]{background:var(--ink);color:var(--surface)}
.lz-ask .skip{font:inherit;font-size:.82rem;border:0;background:none;color:var(--muted);text-decoration:underline;cursor:pointer;margin-top:.8rem;padding:0}
.lz-ask .dots{display:flex;gap:.3rem;margin-bottom:.6rem}.lz-ask .dots i{width:22px;height:5px;border-radius:9px;background:var(--line-2)}
.lz-ask[data-step="1"] .dots i:nth-child(-n+1),.lz-ask[data-step="2"] .dots i:nth-child(-n+2),.lz-ask[data-step="3"] .dots i:nth-child(-n+3){background:var(--brand)}
.lb{position:relative}
.lb .lz-got{position:absolute;top:.7rem;right:.7rem;font:inherit;font-size:.72rem;border:1px solid var(--line-2);background:var(--surface);color:var(--muted);border-radius:999px;padding:.1rem .5rem;cursor:pointer;opacity:0;transition:opacity .2s}
.lb:hover .lz-got,.lb .lz-got:focus,.lb.is-seen .lz-got{opacity:1}
.lb.is-seen .lz-got{color:var(--good);border-color:var(--good)}
.band .lz-got{background:transparent;color:var(--band-muted)}
.lz-tag{display:inline-flex;gap:.3rem;flex-wrap:wrap;margin-bottom:.5rem}
.lz-tag span{font-size:.66rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);border:1px dashed var(--line-2);border-radius:6px;padding:.05rem .4rem}
html:not([data-lz-tags]) .lz-tag{display:none}
.lz-more{text-align:center;padding:1.6rem 1rem}
.lz-more button{font:inherit;border:0;border-radius:999px;background:var(--brand);color:var(--brand-ink);padding:.6rem 1.2rem;font-weight:700;cursor:pointer}
.lz-gate{position:sticky;top:64px;z-index:20;border:2px solid var(--warn);background:var(--warn-soft);margin-bottom:1rem}
.lz-gate button,.lz-gate a{font:inherit;margin:.3rem .4rem 0 0}
.lzh{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(300px,1fr);gap:2rem;align-items:start;padding:clamp(1rem,2vw,1.8rem)}
.band.lb{border-radius:var(--r);overflow:hidden}
.lz-flow>.plain{background:none;border:0;box-shadow:none;padding:0}
@media (max-width:980px){.lzh{grid-template-columns:minmax(0,1fr)}}
.lz-flash{animation:lzf 1.4s ease}
@keyframes lzf{0%{box-shadow:0 0 0 3px var(--brand)}100%{box-shadow:var(--shadow)}}
::view-transition-old(root),::view-transition-new(root){animation-duration:.22s}
@media (prefers-reduced-motion:reduce){::view-transition-group(*),::view-transition-old(*),::view-transition-new(*){animation:none!important}.lz-flash,.lz-chip.pulse{animation:none}}
@media (max-width:700px){.lz-top .shell{gap:.5rem}.lz-tabs{display:none}.lz-chip .lbl{display:none}
  .lz-panel{position:fixed;left:0;right:0;bottom:0;top:auto;width:auto;border-radius:16px 16px 0 0;max-height:80vh;overflow:auto}}
""")
    return ''.join(r)

LENS_BOOT_JS = r"""// php.oct.2026.newsroom.sgit.ai: the lens, before the first paint. Generated by admin/build/design.py. Loaded without
// defer in <head>, so the page is drawn already shaped for this reader: no flash of the wrong page, on any page.
(function () {
  var h = document.documentElement, s = {};
  try { s = JSON.parse(localStorage.getItem('p2s.lens') || '{}') || {}; } catch (e) {}
  if (s.who === undefined) { try { var p = localStorage.getItem('p2s.persona'); if (p) s.who = p; } catch (e) {} }
  var G = JSON.parse(h.getAttribute('data-lz-groups') || '{}');
  if (s.who && G[s.who]) s.group = G[s.who];
  h.setAttribute('data-t', s.t || '5'); h.setAttribute('data-aim', s.aim || 'understand'); h.setAttribute('data-seen', s.seen || 'fade');
  if (s.group) h.setAttribute('data-group', s.group); if (s.who && G[s.who]) h.setAttribute('data-who', s.who);
  if (s.set) h.setAttribute('data-lz-set', '');
  var need = h.getAttribute('data-lz-for'); if (need && (s.group === need || (function () { try { return sessionStorage.getItem('p2s.lens.ok.' + need); } catch (e) { return null; } })())) h.setAttribute('data-lz-ok', '');
  var seen = s.seenKeys || {}, css = '';
  for (var k in seen) if (/^[a-z0-9-]+$/.test(k)) css += 'html[data-seen=hide] .lb[data-k="' + k + '"]{display:none}';
  if (css) { var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st); }
})();
"""

LENS_JS = r"""// php.oct.2026.newsroom.sgit.ai: the lens control. Generated by admin/build/design.py. Moves the settings on <html>
// (which lens.css reads), saves them in this browser (p2s.lens; p2s.persona is shared with the rest of the site),
// counts what each choice would show, and animates the change where the browser can.
(function () {
  'use strict';
  var h = document.documentElement, cfgEl = document.getElementById('lz-cfg'); if (!cfgEl) return;
  var C = JSON.parse(cfgEl.textContent), sup = (h.getAttribute('data-lz') || '').split(' ');
  function load() { try { return JSON.parse(localStorage.getItem('p2s.lens') || '{}') || {}; } catch (e) { return {}; } }
  function save(s) { try { localStorage.setItem('p2s.lens', JSON.stringify(s)); if (s.who && C.people[s.who]) localStorage.setItem('p2s.persona', s.who); else localStorage.removeItem('p2s.persona'); } catch (e) {} }
  function state() { var s = load(); if (s.who === undefined) { try { s.who = localStorage.getItem('p2s.persona') || ''; } catch (e) {} } s.t = s.t || '5'; s.aim = s.aim || 'understand'; s.seen = s.seen || 'fade'; s.group = s.who && C.people[s.who] ? C.people[s.who].group : (s.group || ''); s.seenKeys = s.seenKeys || {}; return s; }
  var blocks = Array.prototype.slice.call(document.querySelectorAll('.lb'));
  var RANK = { '1': 1, '5': 2, '15': 3, 'all': 4 };
  function shows(b, s) {
    if (RANK[b.getAttribute('data-t') || '1'] > RANK[s.t]) return false;
    var aim = b.getAttribute('data-aim'); if (aim && (s.t === '1' || s.t === '5') && aim.split(' ').indexOf(s.aim) < 0 && aim.split(' ').indexOf('*') < 0) return false;
    var f = b.getAttribute('data-for'), g = s.group || 'understand'; if (f && f.split(' ').indexOf(g) < 0 && f.split(' ').indexOf('*') < 0) return false;
    if (s.seen === 'hide' && s.seenKeys[b.getAttribute('data-k')]) return false;
    return true;
  }
  function measure(s) { var n = 0, secs = 0; blocks.forEach(function (b) { if (shows(b, s)) { n++; secs += +b.getAttribute('data-secs') || 0; } }); return { n: n, secs: secs }; }
  function mins(secs) { return secs < 60 ? 'under a minute' : 'about ' + Math.round(secs / 60) + ' min'; }
  function paint(s) {
    h.setAttribute('data-t', s.t); h.setAttribute('data-aim', s.aim); h.setAttribute('data-seen', s.seen);
    if (s.group) h.setAttribute('data-group', s.group); else h.removeAttribute('data-group');
    if (s.who && C.people[s.who]) h.setAttribute('data-who', s.who); else h.removeAttribute('data-who');
    if (s.set) h.setAttribute('data-lz-set', ''); else h.removeAttribute('data-lz-set');
    blocks.forEach(function (b) { b.classList.toggle('is-seen', !!s.seenKeys[b.getAttribute('data-k')]); var g = b.querySelector('.lz-got'); if (g) g.textContent = s.seenKeys[b.getAttribute('data-k')] ? 'Seen' : 'Got it'; });
    var hide = document.getElementById('lz-hide'); if (hide) hide.textContent = Object.keys(s.seenKeys).filter(function (k) { return /^[a-z0-9-]+$/.test(k); }).map(function (k) { return 'html[data-seen=hide] .lb[data-k="' + k + '"]{display:none}'; }).join('');
    var m = measure(s), all = measure({ t: 'all', aim: s.aim, group: '', seen: 'show', seenKeys: {} });
    var who = s.who && C.people[s.who] ? C.people[s.who] : null, grp = s.group ? C.groups[s.group] : null;
    document.querySelectorAll('[data-lz-sum]').forEach(function (el) {
      el.innerHTML = '';
      var t = document.createElement('b'); t.textContent = C.times[s.t]; el.appendChild(t);
      var sep = document.createElement('span'); sep.className = 'sep lbl'; sep.textContent = ' · '; el.appendChild(sep);
      var w = document.createElement('span'); w.className = 'lbl'; w.textContent = who ? who.label : grp ? grp : 'Anyone'; el.appendChild(w);
      var sep2 = sep.cloneNode(true); sep2.className = 'sep lbl'; el.appendChild(sep2);
      var a = document.createElement('span'); a.className = 'lbl'; a.textContent = C.aims[s.aim]; el.appendChild(a);
    });
    document.querySelectorAll('[data-lz-status]').forEach(function (el) {
      el.innerHTML = '';
      var mt = document.createElement('span'); mt.className = 'meter'; var i = document.createElement('i'); i.style.setProperty('--p', Math.round(100 * m.n / Math.max(1, all.n)) + '%'); mt.appendChild(i); el.appendChild(mt);
      var tx = document.createElement('span'); tx.textContent = 'Showing ' + m.n + ' of ' + all.n + ' parts of this page, ' + mins(m.secs) + ' of reading, ' + (who ? 'for ' + who.person + ', ' + who.label.toLowerCase() : s.group ? 'for ' + C.short[s.group] : 'for anyone') + ', to ' + C.aims[s.aim].toLowerCase() + '.'; el.appendChild(tx);
      var b = document.createElement('button'); b.type = 'button'; b.setAttribute('data-lz-open', ''); b.textContent = 'Change'; el.appendChild(b);
    });
    document.querySelectorAll('.lz-seg button[data-k]').forEach(function (b) {
      var k = b.getAttribute('data-k'), v = b.getAttribute('data-v');
      b.setAttribute('aria-pressed', String((k === 'group' ? s.group : s[k]) === v));
      var c = b.querySelector('[data-c]'); if (c) { var t = {}; for (var x in s) t[x] = s[x]; t[k] = v; if (k === 'group') { t.who = ''; } var r = measure(t); c.textContent = r.n + (r.n === 1 ? ' part, ' : ' parts, ') + mins(r.secs); }
    });
    document.querySelectorAll('select[data-k=who]').forEach(function (sel) { sel.value = s.who || ''; });
    document.querySelectorAll('.lz-ask .q3 [data-name]').forEach(function (el) { el.textContent = who ? who.person : grp ? 'you' : 'you'; });
  }
  function change(fn, flash) {
    var s = state(), before = {}; blocks.forEach(function (b) { before[b.getAttribute('data-k')] = shows(b, s); });
    fn(s); save(s);
    var run = function () { paint(s); };
    if (document.startViewTransition && !matchMedia('(prefers-reduced-motion: reduce)').matches) document.startViewTransition(run); else run();
    if (flash !== false) setTimeout(function () { blocks.forEach(function (b) { if (!before[b.getAttribute('data-k')] && shows(b, s)) { b.classList.remove('lz-flash'); void b.offsetWidth; b.classList.add('lz-flash'); } }); }, 260);
  }
  // the dials this page does not answer to are shown, greyed, with the reason
  document.querySelectorAll('.lz-row[data-dial]').forEach(function (row) {
    var d = row.getAttribute('data-dial'); if (sup.indexOf(d) >= 0) return;
    row.classList.add('off'); row.querySelectorAll('button,select').forEach(function (b) { b.disabled = true; });
    var p = document.createElement('p'); p.className = 'why'; p.textContent = C.why[d] || 'This page is the same whatever you choose here; your choice is kept for the next page.'; row.appendChild(p);
  });
  var panel = document.getElementById('lz-panel'), chip = document.querySelector('.lz-chip');
  function open(v) { if (!panel) return; if (v && chip) panel.style.setProperty('--lz-top', Math.round(chip.getBoundingClientRect().bottom + 8) + 'px'); panel.hidden = !v; if (chip) chip.setAttribute('aria-expanded', String(v)); }
  document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target : null; if (!t) return;
    if (t.closest('.lz-chip') || t.closest('[data-lz-open]')) { open(panel.hidden); return; }
    var b = t.closest('.lz-seg button[data-k]');
    if (b && !b.disabled) {
      var k = b.getAttribute('data-k'), v = b.getAttribute('data-v'), ask = b.closest('.lz-ask');
      change(function (s) { if (k === 'group') { s.group = v; if (!s.who || !C.people[s.who] || C.people[s.who].group !== v) s.who = ''; } else s[k] = v; });
      if (ask) { var st = +ask.getAttribute('data-step'); if (st < 3) ask.setAttribute('data-step', String(st + 1)); else { change(function (s) { s.set = true; }, false); if (chip) { chip.classList.add('pulse'); } } }
      return;
    }
    var got = t.closest('.lz-got');
    if (got) { var k2 = got.closest('.lb').getAttribute('data-k'); change(function (s) { if (s.seenKeys[k2]) delete s.seenKeys[k2]; else s.seenKeys[k2] = 1; }, false); return; }
    if (t.closest('.lz-ask .skip')) { change(function (s) { s.set = true; }, false); if (chip) chip.classList.add('pulse'); return; }
    if (t.closest('[data-lz-reask]') || t.closest('[data-lz-tags]')) e.preventDefault();
    if (t.closest('[data-lz-reask]')) { change(function (s) { s.set = false; }, false); var a = document.querySelector('.lz-ask'); if (a) a.setAttribute('data-step', '1'); open(false); scrollTo({ top: 0, behavior: 'smooth' }); return; }
    var more = t.closest('[data-lz-more]');
    if (more) { change(function (s) { s.t = s.t === '1' ? '5' : s.t === '5' ? '15' : 'all'; }); return; }
    if (t.closest('[data-lz-anyway]')) { var need = h.getAttribute('data-lz-for'); try { sessionStorage.setItem('p2s.lens.ok.' + need, '1'); } catch (e2) {} h.setAttribute('data-lz-ok', ''); return; }
    if (t.closest('[data-lz-tags]')) { if (h.hasAttribute('data-lz-tags')) h.removeAttribute('data-lz-tags'); else h.setAttribute('data-lz-tags', ''); return; }
    if (panel && !panel.hidden && !t.closest('#lz-panel')) open(false);
  });
  document.addEventListener('change', function (e) {
    if (e.target && e.target.matches && e.target.matches('select[data-k=who]')) { var v = e.target.value; change(function (s) { s.who = v; s.group = v && C.people[v] ? C.people[v].group : s.group; }); }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') open(false); });
  // another tab changed the settings: follow it
  addEventListener('storage', function (e) { if (e.key === 'p2s.lens' || e.key === 'p2s.persona') paint(state()); });
  paint(state());
})();
"""

def build_lens(ns):
    """Prototype E: the lens, three pages under admin/design/lens/, built from the live data."""
    D, E, U, J, VERSION, PERSONAS, write, PAGES = ns['D'], ns['E'], ns['U'], ns['J'], ns['VERSION'], ns['PERSONAS'], ns['write'], ns['PAGES']
    SOURCES, short_name, human_time, STORY, BASE_URL, SITE_NAME = ns['SOURCES'], ns['short_name'], ns['human_time'], ns['STORY'], ns['BASE_URL'], ns['SITE_NAME']
    pl, claims = D['plain'], D['claims']; st = Counter(c['status'] for c in claims); when = human_time(STORY['data_as_of'])
    GRP = OrderedDict((g['id'], g['label']) for g in D['personas']['groups']); GRP[LZ_TEAM[0]] = LZ_TEAM[1]
    write('assets/design/lens.css', lens_css(ns)); write('assets/design/lens-boot.js', LENS_BOOT_JS); write('assets/design/lens.js', LENS_JS)
    cfg = {'people': {pid: {'group': p['group'], 'person': p['person'], 'label': p['label']} for pid, p in PERSONAS.items()},
           'groups': dict(GRP), 'short': {'understand': 'someone who wants to understand it', 'decide': 'someone who decides', 'communicate': 'someone who tells others', 'act': 'someone who runs systems', 'study': 'someone who studies it', 'team': 'the team'}, 'times': {k: lab for k, lab, _ in LZ_TIMES}, 'aims': {k: lab for k, lab, _ in LZ_AIMS},
           'why': {'aim': 'This page reads the same whatever you came to do; your aim is kept for the next page.',
                   't': 'This page has one length; your time is kept for the next page.', 'who': 'This page is the same for every reader.'}}
    groups_attr = J({pid: p['group'] for pid, p in PERSONAS.items()})
    made = []

    def words(html):
        # a reader sees one variant of a part: count the longest, not all of them
        var = re.findall(r'<p class="lv[^"]*"[^>]*>(.*?)</p>', html, flags=re.S)
        rest = re.sub(r'<p class="lv[^"]*"[^>]*>.*?</p>', ' ', html, flags=re.S)
        n = lambda x: len(re.sub(r'<[^>]+>', ' ', x).split())
        return n(rest) + max([n(v) for v in var] or [0])

    def block(k, body, t='1', aim=None, for_=None, w=12, o=(50, 50, 50), cls='card', tag=True):
        secs = max(8, round(words(body) / 230 * 60))
        tags = [f'{dict((a, b) for a, b, _ in LZ_TIMES)[t]}+'] + ([f'aim: {aim}'] if aim else []) + ([f'for: {for_}'] if for_ else [])
        return (f'<section class="lb {cls} w{w}" data-k="{E(k)}" data-t="{E(t)}"' + (f' data-aim="{E(aim)}"' if aim else '') + (f' data-for="{E(for_)}"' if for_ else '') +
                f' data-secs="{secs}" style="--o-u:{o[0]};--o-a:{o[1]};--o-v:{o[2]};view-transition-name:lb-{E(k)}">'
                + (f'<div class="lz-tag">{"".join(f"<span>{E(x)}</span>" for x in tags)}</div>' if tag else '') + f'{body}<button type="button" class="lz-got">Got it</button></section>')

    def src_chips(ids, up):
        return ''.join(f'<a class="chip" href="{up}sources/{U(s)}/index.html">{E(short_name(SOURCES[s]))}</a>' for s in ids[:3] if s in SOURCES)

    def control(up):
        seg = lambda k, opts: '<div class="lz-seg">' + ''.join(f'<button type="button" data-k="{k}" data-v="{E(v)}" aria-pressed="false">{E(lab)}<small data-c>{E(sub)}</small></button>' for v, lab, sub in opts) + '</div>'
        people = ''.join(f'<option value="{E(pid)}">{E(p["person"])}, {E(p["label"])}</option>' for pid, p in PERSONAS.items())
        return (f'<button type="button" class="lz-chip" aria-expanded="false" aria-controls="lz-panel" title="How this site is shaped for you"><span data-lz-sum><b>5 min</b></span><span aria-hidden="true">&#9662;</span></button>',
                f'<div class="lz-panel" id="lz-panel" hidden role="dialog" aria-label="Shape this site for you">'
                f'<div class="lz-row" data-dial="t"><b>How long have you got?</b>{seg("t", [(k, lab, "") for k, lab, _ in LZ_TIMES])}</div>'
                f'<div class="lz-row" data-dial="who"><b>Who are you?</b>{seg("group", [(g, lab, "") for g, lab in GRP.items()])}<select data-k="who" aria-label="Or pick the closest reader"><option value="">Or pick the closest reader&hellip;</option>{people}</select></div>'
                f'<div class="lz-row" data-dial="aim"><b>What do you want to do?</b>{seg("aim", [(k, lab, "") for k, lab, _ in LZ_AIMS])}</div>'
                f'<div class="lz-row" data-dial="seen"><b>What you marked &ldquo;Got it&rdquo;</b>{seg("seen", [(k, lab, "") for k, lab in LZ_SEEN])}</div>'
                f'<p class="small" style="margin:.6rem 0 0;color:var(--muted)">Kept in this browser only. The page changes as you choose. <a href="#" data-lz-reask>Ask me again</a> &middot; <a href="#" data-lz-tags>Show what drives each part</a></p></div>')

    def page(path, title, desc, supports, body, for_=None, tab=0):
        up = '../' * path.count('/')
        chip, panel = control(up)
        tabs = ''.join(f'<a href="{up}{U(p)}"{" aria-current=page" if i == tab else ""}>{E(t)}</a>' for i, (p, t) in enumerate([('admin/design/lens/index.html', 'Front page'), ('admin/design/lens/agencies/index.html', 'The agencies'), ('admin/design/lens/console/index.html', 'Team console')]))
        banner = (f'<div class="mock-banner"><div class="shell"><span><b>Prototype E</b>, the lens: a working proposal, built from the live data of release v{E(VERSION)}. Not the live site. '
                  f'This page answers to: {E(", ".join({"t": "time", "who": "who you are", "aim": "your aim", "seen": "what you have seen"}[x] for x in supports.split()))}.</span>'
                  f'<a href="{up}admin/design/index.html">The design notes &rarr;</a></div></div>')
        html = f'''<!doctype html>
<html lang="en" data-root="{up}" data-path="{path}" data-ver="{VERSION}" data-lz="{E(supports)}" data-lz-groups="{E(groups_attr)}"{f' data-lz-for="{E(for_)}"' if for_ else ''}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)} &middot; {SITE_NAME}</title>
<meta name="description" content="{E(desc)}">
<meta name="robots" content="noindex">
<link rel="canonical" href="{BASE_URL}/{path}">
<link rel="icon" href="data:,">
<link rel="alternate" type="text/markdown" href="{up}{path[:-5]}.md">
<script src="{up}assets/design/lens-boot.js"></script>
<link rel="stylesheet" href="{up}assets/design/v2.css">
<link rel="stylesheet" href="{up}assets/design/lens.css">
<style id="lz-hide"></style>
<script src="{up}assets/design/lens.js" defer></script>
</head>
<body>
{banner}
<header class="lz-top"><div class="shell"><a class="lz-logo" href="{up}admin/design/lens/index.html"><b>PHP</b>October 2026</a><nav class="lz-tabs" aria-label="Prototype pages">{tabs}</nav>{chip}</div></header>
{panel}
{body}
<script type="application/json" id="lz-cfg">{J(cfg)}</script>
</body>
</html>
'''
        PAGES.append((path, title, desc, 'site'))
        write(path, html)
        txt = re.sub(r'<(script|style|svg|button).*?</\1>', '', body, flags=re.S)
        txt = re.sub(r'<(h1|h2|h3)[^>]*>(.*?)</\1>', lambda m: '\n' + '#' * (int(m.group(1)[1]) + 1) + ' ' + re.sub(r'<[^>]+>', '', m.group(2)) + '\n', txt, flags=re.S)
        txt = re.sub(r'<li[^>]*>', '\n- ', txt); txt = re.sub(r'<(p|div|section|article|tr)[^>]*>', '\n', txt); txt = re.sub(r'<[^>]+>', ' ', txt)
        txt = re.sub(r'[ \t]+', ' ', txt); txt = re.sub(r'\n\s*\n+', '\n\n', txt)
        import html as H
        write(path[:-5] + '.md', f'# {title}\n\n{desc}\n\n> Prototype E for review, built from the data of release v{VERSION}. Not the live site. Every part of the page is listed here; the page shows the parts that fit the reader.\n\n' + H.unescape(txt).strip() + f'\n\n---\nsite v{VERSION} · {BASE_URL}/{path}\n')
        made.append((path, title, desc))

    def ask_card():
        seg = lambda k, opts: '<div class="lz-seg">' + ''.join(f'<button type="button" data-k="{k}" data-v="{E(v)}" aria-pressed="false">{E(lab)}</button>' for v, lab in opts) + '</div>'
        return (f'<section class="card lz-ask" data-step="1" aria-live="polite"><div class="dots"><i></i><i></i><i></i></div>'
                f'<div class="q q1"><p class="eyebrow">This site shapes itself to you. Three taps, and you can change them any time, top right.</p><h2 class="h2">How long have you got?</h2>{seg("t", [(k, lab) for k, lab, _ in LZ_TIMES])}</div>'
                f'<div class="q q2"><p class="eyebrow">The page below has already changed to fit that.</p><h2 class="h2">Which is closest to you?</h2>{seg("group", list(GRP.items())[:-1])}</div>'
                f'<div class="q q3"><p class="eyebrow">Last one.</p><h2 class="h2">What do you want to do?</h2>{seg("aim", [(k, lab) for k, lab, _ in LZ_AIMS])}</div>'
                f'<button type="button" class="skip">Skip: show me the standard page</button></section>')

    def more_card():
        return '<div class="lz-more"><p class="lede" style="margin:0 auto .8rem">That is the page for the time you gave it.</p><button type="button" data-lz-more>Show more</button></div>'

    # ---------------------------------------------------------------- the front page
    up = '../../../'
    answers = ''.join(f'<p class="lv g" data-only="{E(pid)}" style="font-size:1.08rem;margin:.4rem 0 0">{E(p["answer"])}</p>' for pid, p in PERSONAS.items())
    gans = {'understand': PERSONAS['everyone']['answer'], 'decide': PERSONAS['board']['answer'], 'communicate': PERSONAS['journalist']['answer'], 'act': PERSONAS['security']['answer'], 'study': PERSONAS['researcher']['answer'],
            'team': f'Release v{VERSION}. The site is rebuilt from the evidence vault; the board, the agents and their schedules are in the team console.'}
    answers += ''.join(f'<p class="lv" data-only="{E(g)}" style="font-size:1.08rem;margin:.4rem 0 0">{E(a)}</p>' for g, a in gans.items())
    answers += f'<p class="lv" data-only="_" style="font-size:1.08rem;margin:.4rem 0 0">{E(PERSONAS["everyone"]["answer"])}</p>'
    hero = (f'<div class="lzh">'
            f'<div><p class="eyebrow">{E(STORY["status"])} &middot; data as of {E(when)}</p><h1 class="display" style="font-size:clamp(1.9rem,3.2vw,3.2rem)">{E(pl["headline"])}</h1><p class="lede">{E(pl["deck"])}</p></div>'
            f'<div class="ans has-g"><b>Your answer</b>{answers}</div></div>')
    fx = D['affected']['fixed']
    tiles = (f'<div class="tiles">' + ''.join(f'<div class="card kpi {c}"><div class="k">{E(k)}</div><div class="v">{E(v)}</div><div class="d">{E(d)}</div></div>' for c, k, v, d in [
        ('good', 'Is there a fix?', 'Yes', f'PHP {", ".join(fx)}'), ('alert', 'How serious?', 'Critical', 'both flaws, rated 9.2 of 10'),
        ('info', 'Facts we hold', str(len(claims)), f'{st["confirmed"]} confirmed, {st["disputed"] + st["contradicted"] + st["unverified"]} contested'),
        ('warn', 'Agencies compared', str(len(D['agencies'])), 'all say install the fix')]) + '</div>')
    steps = [('Patch internet-facing first', 'mod_php, then FPM, then the rest. Restart every worker; rebuild every image; check the running version after the restart.'),
             ('Bound the known paths', 'session.upload_progress off, low post_max_size, pm.max_requests on FPM. Each blocks a path; none is a fix.'),
             ('Watch the process tree', 'Alert on a PHP worker spawning a shell or a downloader. A clean access log proves nothing about the host.')]
    qs = [('Do we know every system that runs PHP?', 'Websites, internal tools, suppliers and the images we build from.'), ('Is each one updated, and restarted?', f'Fixed in PHP {", ".join(fx)}. An update only counts once the service restarts.'),
          ('Who can take a system offline, and how fast?', 'Two US agencies say take it offline if it cannot be updated; decide now who calls it.')]
    contested = [c for c in claims if c['status'] in ('contradicted', 'disputed', 'unverified')]
    numbered = lambda xs: '<div class="actions">' + ''.join(f'<div class="card action" style="box-shadow:none"><div class="n">{i + 1}</div><div><h3>{E(t)}</h3><p>{E(x)}</p></div></div>' for i, (t, x) in enumerate(xs)) + '</div>'
    donut = svg_donut([(st[k], c, k) for k, c in STATUS_COL.items() if st[k]])
    dleg = ''.join(f'<li><i style="background:{c}"></i>{st[k]} {E(k)}</li>' for k, c in STATUS_COL.items() if st[k])
    spectrum, cards = agency_parts(ns, up)
    lst = lambda xs: '<ul class="delta">' + ''.join(f'<li><div class="t">{x}</div></li>' for x in xs) + '</ul>'
    B = [
        block('hero', hero, '1', None, None, 12, (0, 0, 0), 'band', tag=False),
        block('tiles', tiles, '1', 'understand verify', None, 12, (1, 6, 2), 'plain'),
        block('qs', f'<div class="block-head"><h2 class="h2">Three questions for your team</h2></div>{numbered(qs)}', '1', 'act understand', 'decide', 12, (2, 1, 9)),
        block('steps', f'<div class="block-head"><h2 class="h2">Your next three actions</h2><a class="small" href="{up}playbook/index.html">The whole playbook</a></div>{numbered(steps)}', '1', 'act', 'act team', 12, (9, 1, 9)),
        block('check', f'<div class="block-head"><h2 class="h2">Before you write: three things often got wrong</h2></div>' + lst([f'<span class="pill warn">{E(c["status"])}</span> {E(c["claim"][:160])}<div class="small">who says it: {E(c["by"][:80])}</div>' for c in contested[:3]]), '1', 'act verify', 'communicate', 12, (3, 1, 1)),
        block('touch', f'<div class="block-head"><h2 class="h2">Does it touch you?</h2></div><div class="tiles">' + ''.join(f'<div class="card" style="box-shadow:none"><h3>{E(c["q"])}</h3><p class="small" style="margin:.3rem 0 0;color:var(--ink-2)">{E(c["a"])}</p></div>' for c in pl['cards'][:3]) + '</div>', '1', 'understand', 'understand', 12, (2, 8, 9)),
        block('open', f'<div class="block-head"><h2 class="h2">The open questions</h2></div>' + lst([E(x['text']) for x in pl['unknown']]), '1', 'understand verify', 'study', 12, (3, 9, 2)),
        block('sure', f'<h2 class="h2">How sure are we?</h2><div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">{donut}<ul class="legend" style="flex-direction:column">{dleg}</ul></div><p class="small" style="margin:.4rem 0 0">Every fact carries one of five words for how far it can be trusted.</p>', '1', 'verify', None, 5, (12, 12, 3)),
        block('now', '<div class="block-head"><h2 class="h2">Right now</h2></div>' + lst([E(x['text']) + f'<div class="chips" style="margin-top:.3rem">{src_chips(x.get("sources", []), up)}</div>' for x in pl['now']]), '5', 'understand act', None, 7, (4, 4, 6)),
        block('latest', '<div class="block-head"><h2 class="h2">The latest</h2></div>' + lst([f'<span class="small">{E(x["when"])}</span> {E(x["text"])}' for x in pl['latest'][:5]]), '5', 'understand act', None, 5, (5, 5, 7)),
        block('spectrum', spectrum, '5', 'act verify understand', None, 12, (7, 3, 5), 'plain'),
        block('unknown', '<div class="block-head"><h2 class="h2">What nobody knows yet</h2></div>' + lst([E(x['text']) for x in pl['unknown']]), '5', 'understand verify', 'understand decide communicate act team', 7, (6, 7, 4)),
        block('facts', '<div class="block-head"><h2 class="h2">The core facts</h2></div>' + lst([f'<span class="pill {"good" if x.get("status") == "confirmed" else "info"}">{E(x.get("status", ""))}</span> {E(x["text"])}' for x in pl['facts']]), '15', 'understand verify', None, 7, (8, 10, 6)),
        block('moments', '<div class="block-head"><h2 class="h2">How it unfolded</h2></div>' + lst([f'<b>{E(x["when"])}</b> {E(x["what"])}' for x in pl['moments']]), '15', 'understand', None, 5, (9, 11, 10)),
        block('contested', '<div class="block-head"><h2 class="h2">Contested</h2><span class="small">disputed, contradicted, unverified</span></div>' + lst([f'<span class="pill {"alert" if c["status"] == "unverified" else "warn"}">{E(c["status"])}</span> {E(c["claim"][:170])}<div class="small">who says it: {E(c["by"][:90])}</div>' for c in contested[:10]]), '15', 'verify', None, 12, (11, 12, 8)),
        block('cards', f'<div class="block-head"><h2 class="h2">Agency by agency</h2></div>{cards}', 'all', None, None, 12, (20, 20, 20), 'plain'),
        block('every', '<div class="block-head"><h2 class="h2">Everything else we hold</h2></div><div class="chips">' + ''.join(f'<a class="chip" href="{up}{U(p)}">{E(t)}</a>' for p, t in [('claims/index.html', f'Every claim ({len(claims)})'), ('sources/index.html', f'Every source ({len(SOURCES)})'), ('timeline/index.html', 'The timeline'), ('numbers/index.html', 'The numbers'), ('code/index.html', 'The code'), ('method/index.html', 'How this site knows')]) + '</div>', 'all', None, None, 12, (21, 21, 21)),
    ]
    how = ('<details class="card" style="margin-top:1.6rem"><summary><b>How this prototype works</b> (for the editor and dev)</summary><ol class="small" style="color:var(--ink-2)">'
           '<li>Every part of every page is built, always. Each part says which settings show it: a time tier, an aim, a kind of reader.</li>'
           '<li>A tiny script in the page head (no defer) reads the settings and puts them on the page before anything is drawn, so a page never flashes the wrong version, on the first page or the tenth.</li>'
           '<li>The stylesheet shows, hides and orders the parts from those settings. Changing a setting changes one attribute; the browser re-lays the page in the same frame, and animates it where it can (View Transitions).</li>'
           '<li>The counts on each option (&ldquo;6 parts, about 3 min&rdquo;) are worked out from the parts on this page, so the reader sees what a choice will do before making it.</li>'
           '<li>A page that does not answer to a setting says so in the control, and keeps the setting for the next page. A page for some readers only says who it is for, and lets anyone read it anyway.</li>'
           '<li>&ldquo;Got it&rdquo; marks a part as seen; Fade or Hide takes it out of the way on every page, until it changes.</li></ol></details>')
    body = f'<main class="shell" style="padding-top:1.2rem"><p class="lz-status" data-lz-status></p><div class="lz-flow">{ask_card()}{"".join(B)}{more_card()}</div>{how}</main>'
    page('admin/design/lens/index.html', 'Prototype E: the lens, the front page', 'A working prototype of a site that shapes itself to the reader in front of them: how long they have, who they are, what they want to do, and what they have seen; set once at the top right, applied on every page with no reload and no flash.', 't who aim seen', body)

    # ---------------------------------------------------------------- a page with partial support: time and who, not aim
    up = '../../../../'; spectrum, cards = agency_parts(ns, up)
    n = len(D['agencies']); offl = sum(1 for a in D['agencies'] if a['offline'] == 'yes')
    one = {'_': f'All {n} say install the fix. They split on what to do with a system you cannot patch today: {offl} say take it offline.',
           'decide': f'All {n} agencies say install the fix now. The question for you is the system you cannot patch today: {offl} agencies, both American, say take it offline; decide who can make that call.',
           'act': f'Patch first, everywhere. For a host you cannot patch now: {offl} agencies say offline, Europe says isolate from the public internet, the UK says temporary mitigations first.',
           'communicate': f'Careful with "agencies say take sites offline": {offl} of {n} say so, both American. The rest say install the fix, then isolate or mitigate.'}
    ones = ''.join(f'<p class="lv" data-only="{E(g)}" style="font-size:1.25rem;font-family:var(--serif);margin:0">{E(t)}</p>' for g, t in one.items())
    ones += f'<p class="lv" data-only="understand study team" style="font-size:1.25rem;font-family:var(--serif);margin:0">{E(one["_"])}</p>'
    BA = [block('a-one', f'<p class="eyebrow">The agencies &middot; in one line</p>{ones}', '1', None, None, 12, (0, 0, 0)),
          block('a-spec', spectrum, '5', None, None, 12, (1, 1, 1), 'plain'),
          block('a-cards', f'<div class="block-head"><h2 class="h2">Agency by agency</h2><span class="small">each in its own words, with its saved sources</span></div>{cards}', '15', None, None, 12, (2, 2, 2), 'plain'),
          block('a-table', f'<h2 class="h2">The evidence table</h2><p class="small" style="margin:.3rem 0 0">Every agency with its publication time, its exact words, what it says of exploitation, and its sources: <a href="{up}agencies/index.html">on the live agencies page</a>.</p>', 'all', None, None, 12, (3, 3, 3))]
    body = f'<main class="shell" style="padding-top:1.2rem"><h1 class="display" style="font-size:clamp(1.8rem,3vw,3rem)">What {n} agencies advise</h1><p class="lz-status" data-lz-status></p><div class="lz-flow">{"".join(BA)}{more_card()}</div></main>'
    page('admin/design/lens/agencies/index.html', 'Prototype E: the lens, a content page', 'A content page that answers to two of the four settings: its length follows your time and its one line follows who you are; it reads the same whatever your aim, and the control says so.', 't who seen', body, tab=1)

    # ---------------------------------------------------------------- a page for some readers only: the team
    A = D['admin']; bstat = Counter(b['status'] for b in A['board'])
    owners = Counter(b['owner'] for b in A['board'] if b['status'] != 'done').most_common(10)
    gate = ('<section class="card lz-gate"><b>This page is for the people who run the site.</b> <span class="small">You are reading as someone else; nothing here is hidden, it is just not written for you.</span><br>'
            f'<button type="button" class="chip" data-lz-anyway>Read it anyway</button><a class="chip" href="{up}admin/design/lens/index.html">Back to your front page</a></section>')
    kp = ''.join(f'<div class="card kpi {c}"><div class="k">{E(k)}</div><div class="v">{E(v)}</div><div class="d">{E(d)}</div></div>' for c, k, v, d in [
        ('info', 'Release', f'v{VERSION}', f'{len(D["versions"]["versions"])} releases'), ('warn', 'Open on the board', str(bstat['open']), f'{bstat["done"]} done'), ('good', 'Members', str(len(A['roles'])), 'each with a role and a policy')])
    rows = ''.join(f'<tr><td>{E(o)}</td><td>{c}</td></tr>' for o, c in owners)
    BC = [block('c-kpi', f'<div class="tiles">{kp}</div>', '1', None, None, 12, (0, 0, 0), 'plain'),
          block('c-own', f'<h2 class="h2">Open work, by owner</h2><div class="tw"><table class="tbl"><tbody>{rows}</tbody></table></div>', '1', None, None, 12, (1, 1, 1))]
    body = f'<main class="shell" style="padding-top:1.2rem">{gate}<h1 class="display" style="font-size:clamp(1.8rem,3vw,3rem)">Team console</h1><p class="lz-status" data-lz-status></p><div class="lz-flow">{"".join(BC)}</div></main>'
    page('admin/design/lens/console/index.html', 'Prototype E: the lens, a page for the team', 'A page written for one kind of reader: anyone else is told who it is for and can read it anyway; the time and aim settings do not apply, and the control says so.', 'seen', body, for_='team', tab=2)
    return made


# =========================================================================== the line (prototype F, 25 October 2026)
# The editor's briefing pack of 25 October: every page carries one band under the masthead that says one thing, to the
# persona in front of it, at this moment of their visits; the page under it is shaped for that role and depth, what has
# changed since they were last here is marked, and what they have read folds away.
# The words, the roles, the moments and the engine are the pack's, vendored under assets/design/line/; this builds the
# pages from the evidence vault and fills every number the words leave as a placeholder.
# Brief: admin/content/briefs/2026-10-25__brief__the-line.md

LINE_DIR = 'assets/design/line'
LINE_PAGES = [('index.html', 'front', 'Front page'), ('agencies/index.html', 'agencies', 'The agencies'),
              ('numbers/index.html', 'numbers', 'The numbers'), ('playbook/index.html', 'playbook', 'The playbook'),
              ('console/index.html', 'console', 'Team console'), ('catalogue/index.html', 'catalogue', 'Every line')]


def line_spec(ns, name):
    import json as _j
    return _j.load(open(ns['os'].path.join(ns['ROOT'], LINE_DIR, name), encoding='utf-8'))


def line_numbers(ns):
    """Every number the pack's words leave as a placeholder, from the evidence vault."""
    D = ns['D']
    claims = D['claims']; st = Counter(c['status'] for c in claims)
    def bucket(o):
        return ('yes' if o == 'yes' else 'isolate' if o.startswith('isolate') else 'restrict' if o == 'restrict from abroad'
                else 'consider' if o in ('after mitigations', 'consider') else 'none' if o == 'none' else None)
    b = Counter(bucket(a['offline']) for a in D['agencies'])
    words = {1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five', 6: 'Six'}
    seg_ag = [[b['none'], '#d4cfc3'], [b['consider'], '#f3d9a8'], [b['restrict'], '#eab676'], [b['isolate'], '#c9742c'], [b['yes'], '#8a3b12']]
    seg_n = [[st['confirmed'], '#15803d'], [st['reported'], '#7aa7d9'], [st['disputed'], '#e0a14a'],
             [st['contradicted'], '#b3261e'], [st['unverified'], '#a39d8f']]
    fx = D['affected']['fixed']
    return {'fixed': (', '.join(fx[:-1]) + ' or ' + fx[-1]) if len(fx) > 1 else fx[0], 'nAgencies': len(D['agencies']),
            'nOffline': b['yes'], 'nOfflineWord': words.get(b['yes'], str(b['yes'])), 'nIsolate': b['isolate'],
            'nRestrict': b['restrict'], 'nConsider': b['consider'], 'nNone': b['none'],
            'nFacts': len(claims), 'nConfirmed': st['confirmed'], 'nReported': st['reported'], 'nDisputed': st['disputed'],
            'nContradicted': st['contradicted'], 'nUnverified': st['unverified'],
            'segAgencies': [s for s in seg_ag if s[0]], 'segNumbers': [s for s in seg_n if s[0]]}


def line_copy(ns):
    """assets/design/line/copy.json: the pack's words with this release's numbers in them."""
    import json as _j
    src = line_spec(ns, 'copy.src.json'); N = line_numbers(ns)
    def walk(x):
        if isinstance(x, str):
            if x.startswith('{seg') and x.endswith('}'):
                return N[x[1:-1]]
            for k, v in N.items():
                if isinstance(v, (int, str)) and '{' + k + '}' in x:
                    x = x.replace('{' + k + '}', str(v))
            return x
        if isinstance(x, list):
            return [walk(i) for i in x]
        if isinstance(x, dict):
            return OrderedDict((k, walk(v)) for k, v in x.items())
        return x
    out = walk(src)
    out['_note'] = ('Generated by admin/build/design.py from assets/design/line/copy.src.json and the evidence vault at '
                    'release v' + ns['VERSION'] + '. Edit copy.src.json, never this file.')
    return _j.dumps(out, indent=1, ensure_ascii=False) + '\n'


def line_shape_css(ns):
    """The shaping: which parts a role sees, and in what order. Generated from roles.json."""
    R = line_spec(ns, 'roles.json')
    out = ['/* Generated by admin/build/design.py from assets/design/line/roles.json: the page under the line, per role.\n'
           '   A part says which roles it is for (data-for) and where it sits for each of them (--o-<role>); the hero\n'
           '   carries one answer per role and shows the reader theirs. */\n',
           '.lnp .lp{order:50}\n.lnp .lp-more{order:999}\n',
           '.ln-answer{display:none}\n.ln-answer[data-role-text~="exec"]{display:revert}\n']
    for role in R['order']:
        out.append('html[data-role="%s"] .ln-answer{display:none}\n' % role)
        out.append('html[data-role="%s"] .ln-answer[data-role-text~="%s"]{display:revert}\n' % (role, role))
    for role in R['order']:
        out.append('html[data-role="%s"] .lnp .lp{order:var(--o-%s,50)}\n' % (role, role))
        out.append('html[data-role="%s"] .lnp .lp[data-for]:not([data-for~="%s"]):not([data-for~="*"]){display:none}\n' % (role, role))
        out.append('html[data-role="%s"] .ln-mast nav a[data-menu]:not([data-menu~="%s"]):not([data-menu~="*"]){display:none}\n' % (role, role))
    return ''.join(out)


def line_changes(ns):
    """What has changed lately, for whom: from the story's own timeline, tagged by topic.
    In the live build this is the diff between releases (brief, section 10.5); here it is the dated record the site
    already keeps, which is the same material a diff would carry."""
    D = ns['D']
    # data/timeline.json carries a phase per event; the roles each phase is news for, and the part it lands in
    PHASE = {'response': (['exec', 'security', 'engineer', 'general', 'everything'], 'now+unknown'),
             'aftermath': (['exec', 'general', 'journalist', 'security', 'everything'], 'now+unknown'),
             'release': (['security', 'engineer', 'exec', 'everything'], 'settings'),
             'coordination': (['journalist', 'researcher', 'everything'], 'timeline'),
             'leak': (['journalist', 'researcher', 'everything'], 'timeline'),
             'discovery': (['journalist', 'researcher', 'everything'], 'timeline'),
             'method': (['researcher', 'journalist', 'everything'], 'timeline'),
             'origin': (['researcher', 'everything'], 'timeline')}
    out = []
    for t in sorted(D['timeline'], key=lambda x: x.get('at', ''), reverse=True)[:40]:
        at = (t.get('at') or '').strip()
        text = (t.get('event') or t.get('what') or t.get('text') or '').strip()
        if not at or not text:
            continue
        if len(at) == 10:
            at += 'T00:00:00Z'
        elif len(at) == 16 and at.endswith('Z') is False:
            at += ':00Z'
        roles, part = PHASE.get(t.get('phase') or '', (['*'], ''))
        out.append(OrderedDict([('at', at), ('tag', 'New'), ('text', text[:160]), ('roles', roles), ('key', part)]))
    return out[:24]


def line_part(ns, key, title, body, roles_for, orders, fold=True, cls='card'):
    E = ns['E']
    h = hashlib.sha256(body.encode('utf-8')).hexdigest()[:12]
    style = ';'.join('--o-%s:%d' % (r, i) for r, i in sorted(orders.items()))
    return ('<section class="lp %s" data-k="%s" data-title="%s" data-hash="%s"%s%s style="%s;view-transition-name:lp-%s">%s</section>'
            % (cls, E(key), E(title), h, (' data-for="%s"' % E(' '.join(roles_for))) if roles_for else '',
               ' data-fold="1"' if fold else '', style, E(key), body))


def build_line(ns):
    """Prototype F: the line, six pages under admin/design/line/, built from the live data."""
    import json as _j
    D, E, U, J, VERSION, PERSONAS = ns['D'], ns['E'], ns['U'], ns['J'], ns['VERSION'], ns['PERSONAS']
    write, PAGES, STORY, BASE_URL, SITE_NAME = ns['write'], ns['PAGES'], ns['STORY'], ns['BASE_URL'], ns['SITE_NAME']
    human_time, SOURCES, short_name = ns['human_time'], ns['SOURCES'], ns['short_name']
    R = line_spec(ns, 'roles.json'); N = line_numbers(ns)
    pl, claims = D['plain'], D['claims']; st = Counter(c['status'] for c in claims)
    when = human_time(STORY['data_as_of'])
    write(LINE_DIR + '/copy.json', line_copy(ns))
    write(LINE_DIR + '/shape.css', line_shape_css(ns))
    changes = line_changes(ns)
    write(LINE_DIR + '/config.js',
          '/* Generated by admin/build/design.py: the roles, the words, the moments and the change log the line runs on. */\n'
          'window.LINE = ' + _j.dumps({'roles': R, 'copy': _j.loads(line_copy(ns)), 'moments': line_spec(ns, 'moments.json'),
                                       'changes': changes}, ensure_ascii=False, separators=(',', ':')) + ';\n')
    made = []

    # ------------------------------------------------------------------ the parts of the front page, per role
    FP = {r: R['roles'][r]['frontParts'] for r in R['order']}
    def who(key):
        return [r for r in R['order'] if key in FP[r]]
    def order(key):
        return {r: FP[r].index(key) + 1 for r in R['order'] if key in FP[r]}

    def depth_p(plain, technical, deep, cls='lede'):
        return (f'<p class="{cls} lv" data-depth="plain">{E(plain)}</p>'
                f'<p class="{cls} lv" data-depth="technical">{E(technical)}</p>'
                f'<p class="{cls} lv" data-depth="deep">{E(deep)}</p>')

    fx = D['affected']['fixed']
    fix_line = (f'A fix came out on 21 October. Whoever runs a website needs to install it, and restart it.',
                f'Fixed in PHP {", ".join(fx)}. An update only counts once the service restarts.',
                f'Target {", ".join(fx[:-1])} or {fx[-1]}; restart every worker, rebuild images, verify with php -v inside the running container.')
    first_reader = {r: (R['roles'][r]['readers'] or [None])[0] for r in R['order']}
    answers = ''.join(
        f'<p class="ln-answer lv2" data-role-text="{E(r)}">{E(PERSONAS[first_reader[r]]["answer"] if first_reader[r] in PERSONAS else "The whole site, unfiltered: every part of the page, in the usual order.")}</p>'
        for r in R['order'])
    hero = (f'<div class="band lnp-hero"><div class="shell hero">'
            f'<div><p class="eyebrow">{E(STORY["status"])} &middot; data as of {E(when)}</p>'
            f'<h1 class="display">{E(pl["headline"])}</h1>{depth_p(*fix_line)}</div>'
            f'<aside class="ans"><p class="eyebrow" style="margin:0 0 .3rem">Your answer</p>{answers}</aside></div></div>')

    tiles = ('<div class="tiles">' + ''.join(
        f'<div class="card kpi {c}"><div class="k">{E(k)}</div><div class="v">{E(v)}</div><div class="d">{E(d)}</div></div>'
        for c, k, v, d in [('good', 'Is there a fix?', 'Yes', 'since 21 October'),
                           ('alert', 'How serious?', 'Critical', 'both flaws, 9.2 of 10'),
                           ('info', 'Anyone broken into?', 'None named', 'millions of attempts'),
                           ('warn', 'Government advice', 'Update', f'all {N["nAgencies"]} agencies agree')]) + '</div>')

    def steps(title, items, href=None):
        return (f'<div class="block-head"><h2 class="h2">{E(title)}</h2>'
                + (f'<a class="small" href="{href}">More</a>' if href else '') + '</div><div class="actions">'
                + ''.join(f'<div class="card action" style="box-shadow:none"><div class="n">{i+1}</div><div><h3>{E(a)}</h3><p>{E(b)}</p></div></div>'
                          for i, (a, b) in enumerate(items)) + '</div>')

    def two(a_title, a_items, b_title, b_items):
        col = lambda t, xs: (f'<div class="card"><div class="block-head"><h2 class="h2">{E(t)}</h2></div>'
                             + ''.join(f'<p class="small" style="color:var(--ink-2)">{x}</p>' for x in xs) + '</div>')
        return '<div class="grid cols-12" style="gap:1rem">' + f'<div class="span-6">{col(a_title, a_items)}</div><div class="span-6">{col(b_title, b_items)}</div>' + '</div>'

    spectrum, agency_cards = agency_parts(ns, '../../../')
    contested = [c for c in claims if c['status'] in ('contradicted', 'disputed', 'unverified')]
    def claim_rows(items, n=3):
        return ''.join(f'<li><span class="pill {"alert" if c["status"] == "unverified" else "warn"}">{E(c["status"])}</span> '
                       f'{E(c["claim"][:150])}<div class="small">who says it: {E(c["by"][:80])}</div></li>' for c in items[:n])

    status_bar = ('<div class="block-head"><h2 class="h2">How sure are we?</h2>'
                  f'<span class="small">{N["nFacts"]} facts</span></div>'
                  '<div style="display:flex;height:16px;border-radius:5px;overflow:hidden;background:var(--surface-2)">'
                  + ''.join(f'<i style="flex:{n};background:{c}" title="{E(k)}"></i>'
                            for k, c, n in [('confirmed', 'var(--good)', st['confirmed']), ('reported', 'var(--info)', st['reported']),
                                            ('disputed', 'var(--warn)', st['disputed']), ('contradicted', '#b3261e', st['contradicted']),
                                            ('unverified', 'var(--muted)', st['unverified'])] if n)
                  + '</div><ul class="legend">' + ''.join(f'<li><b>{n}</b> {E(k)}</li>' for k, n in
                        [('confirmed', st['confirmed']), ('reported', st['reported']), ('disputed', st['disputed']),
                         ('contradicted', st['contradicted']), ('unverified', st['unverified'])] if n) + '</ul>')

    mit = D['affected'].get('mitigations', [])[:4]
    settings_rows = ''.join(f'<div class="crow"><code>{E((m.get("what") or "")[:46])}</code><span class="small">{E((m.get("caveat") or m.get("for") or "")[:110])}</span></div>' for m in mit)
    expl = D['exploitation'][:3]
    numbers_rows = ''.join(
        f'<div class="trow"><b class="serif">{E(n["value"])}</b><span class="small">{E((n.get("measures") or n.get("of") or "")[:150])}</span>'
        f'<span class="pill {"good" if n["status"] == "confirmed" else "alert" if n["status"] == "unverified" else "warn" if n["status"] in ("disputed", "contradicted") else "info"}">{E(n["status"])}</span></div>'
        for n in D['numbers'][:6])
    sapis = D['affected'].get('sapis', [])[:3]
    code = D.get('code', {})

    PARTS = OrderedDict([
        ('hero', ('The situation', hero, False, 'plain')),
        ('tiles', ('The four questions', tiles, True, 'plain')),
        ('questions', ('Three questions for your team', steps('Three questions for your team', [
            ('Do we know every system that runs PHP?', 'Websites, internal tools, suppliers, and the images we build from.'),
            ('Is each one updated, and restarted?', f'Fixed in PHP {", ".join(fx)}. An update only counts once the service restarts.'),
            ('Who can take a system offline, and how fast?', f'{N["nOfflineWord"]} US agencies say take it offline if it cannot be updated. Decide now who makes that call.')]), True, 'card')),
        ('touch+todo', ('Does it touch you?', two('Does it touch you?', [E(c['a'][:200]) for c in pl['cards'][:2]],
                                                  'What to do', [E(x['text'][:200]) for x in pl['now'][:3]]), True, 'plain')),
        ('actions', ('Your next three actions', steps('Your next three actions', [
            ('Patch internet-facing first.', 'mod_php, then FPM, then the rest. Restart every worker; rebuild every image.'),
            ('Bound the known paths.', 'session.upload_progress off, low post_max_size, pm.max_requests on FPM. Each blocks a path; none is a fix.'),
            ('Watch the process tree.', 'Alert on a PHP worker spawning a shell or a downloader. A clean access log proves nothing about the host.')]), True, 'card')),
        ('now+unknown', ('Right now, and what nobody knows', two('Right now', [E(x['text'][:200]) for x in pl['now'][:3]],
                                                                 'What nobody knows yet', [E(x['text'][:200]) for x in pl['unknown'][:3]]), True, 'plain')),
        ('signals+advice', ('Attack signals, and the advice now', two(
            'Attack signals', [f'<b>{E(x["when"])}</b> {E(x["what"][:150])}' for x in expl],
            'The advice, now', [E(x['text'][:180]) for x in pl['now'][1:3]]), True, 'plain')),
        ('spectrum', ('What governments advise', spectrum, True, 'plain')),
        ('status', ('How sure are we?', status_bar, True, 'card')),
        ('settings', ('Fixed versions, and the settings until you are there', (
            f'<div class="block-head"><h2 class="h2">Fixed versions, and the settings until you are there</h2></div>'
            f'<div class="crow"><code>Fixed in</code><span class="small">{E(" · ".join(fx))}</span></div>{settings_rows}'), True, 'card')),
        ('exposure+code', ('Which setups are exposed', two(
            'Which setups are exposed', [f'<b>{E(s["sapi"])}</b> {E(s["text"][:150])}' for s in sapis],
            'Where the fix is', [E(str(code.get('fix', ''))[:200]), E(str(code.get('where', ''))[:200])]), True, 'plain')),
        ('before-you-write', ('Before you write', (
            '<div class="block-head"><h2 class="h2">Before you write: three things often got wrong</h2></div>'
            f'<ul class="delta">{claim_rows(contested, 3)}</ul>'), True, 'card')),
        ('numbers', ('The numbers, and how far each holds', (
            '<div class="block-head"><h2 class="h2">The numbers in the news, and how far each holds</h2></div>' + numbers_rows), True, 'card')),
        ('timeline', ('How it unfolded', (
            '<div class="block-head"><h2 class="h2">How it unfolded</h2></div><div class="journey">'
            + ''.join(f'<div class="jst"><b>{E(m["when"])}</b><span>{E(m["what"][:120])}</span></div>' for m in pl['moments'][:5]) + '</div>'), True, 'plain')),
        ('contested', ('Also contested', (
            f'<div class="block-head"><h2 class="h2">Also contested</h2><span class="small">{len(contested)} facts</span></div>'
            f'<ul class="delta">{claim_rows(contested[3:], 3)}</ul>'), True, 'card')),
        ('open-questions', ('The open questions', steps('The open questions', [
            (E(x['text'][:90]), E(x['text'][90:220]) if len(x['text']) > 90 else '') for x in pl['unknown'][:3]]), True, 'card')),
        ('bug-classes+shown', ('The two bug classes', two(
            'The two bug classes', [E(str(code.get('mechanism', ''))[:220])],
            'What was shown', [f'<b>{E(s["sapi"])}</b> {E(s["text"][:140])}' for s in sapis[:2]]), True, 'plain')),
    ])

    front_body = ''.join(line_part(ns, k, title, body, who(k), order(k), fold, cls)
                         for k, (title, body, fold, cls) in PARTS.items() if who(k))

    # ------------------------------------------------------------------ the other pages
    def plain_part(key, title, body, cls='card', fold=True):
        return line_part(ns, key, title, body, [], {}, fold, cls)

    head = lambda eyebrow, h1, sub: (f'<div class="lnp-head"><p class="eyebrow">{E(eyebrow)}</p>'
                                     f'<h1 class="display" style="font-size:clamp(1.7rem,2.8vw,2.8rem)">{E(h1)}</h1>'
                                     f'<p class="lede">{E(sub)}</p></div>')
    agencies_body = (plain_part('head', 'The agencies', head('The agencies',
                        f'{N["nAgencies"]} agencies. All say update. They split on offline.',
                        'Every government cyber agency this site holds, placed by what it says to do with a system you cannot patch, in its own words.'), 'plain', False)
                     + plain_part('spectrum', 'The spectrum', spectrum, 'plain')
                     + plain_part('cards', 'Agency by agency', f'<div class="block-head"><h2 class="h2">Agency by agency</h2></div>{agency_cards}', 'plain'))
    numbers_body = (plain_part('head', 'The numbers', head('The numbers', 'The numbers in the news, and how far each holds',
                        'Every figure that has been repeated about this story, with where it comes from and whether it holds up.'), 'plain', False)
                    + plain_part('status', 'How sure are we?', status_bar)
                    + plain_part('table', 'The numbers', '<div class="block-head"><h2 class="h2">Every number</h2></div>' + numbers_rows)
                    + plain_part('contested', 'Contested', '<div class="block-head"><h2 class="h2">Contested</h2></div>' + f'<ul class="delta">{claim_rows(contested, 5)}</ul>'))
    playbook_body = (plain_part('head', 'The playbook', head('The playbook', 'The response, step by step', fix_line[1]), 'plain', False)
                     + plain_part('steps', 'In order', steps('In order', [
                         ('Find every system that runs PHP.', 'Websites, internal tools, suppliers, vendor appliances and the images you build from.'),
                         ('Patch internet-facing first.', 'mod_php, then FPM, then the rest. Restart every worker; rebuild every image.'),
                         ('Bound the known paths.', 'Each temporary setting blocks a path; none is a fix.'),
                         ('Watch the process tree.', 'Alert on a PHP worker spawning a shell or a downloader.'),
                         ('Decide who calls isolate or offline, and when.', f'{N["nOfflineWord"]} US agencies say take it offline if it cannot be updated.')]))
                     + plain_part('settings', 'The settings', PARTS['settings'][1]))
    A = D['admin']; bstat = Counter(b['status'] for b in A['board'])
    console_body = (plain_part('head', 'Team console', head('Team console', 'The board, the releases, the agents',
                        'Public, as everything here is; written for the team that runs the site.'), 'plain', False)
                    + plain_part('kpis', 'The release', '<div class="tiles">' + ''.join(
                        f'<div class="card kpi {c}"><div class="k">{E(k)}</div><div class="v">{E(v)}</div><div class="d">{E(d)}</div></div>'
                        for c, k, v, d in [('info', 'Release', 'v' + VERSION, f'{len(D["versions"]["versions"])} releases'),
                                           ('warn', 'Open on the board', str(bstat['open']), f'{bstat["done"]} done'),
                                           ('good', 'Members', str(len(A['roles'])), 'each with a role and a policy')]) + '</div>'))

    # ------------------------------------------------------------------ the pages
    def page(path, page_id, title, desc, body, for_=None, menu_role=None):
        full = 'admin/design/line/' + path
        up = '../' * full.count('/')
        tabs = ''.join(
            f'<a href="{up}admin/design/line/{U(p)}"{" aria-current=page" if p == path else ""}>{E(t)}</a>'
            for p, _pid, t in LINE_PAGES)
        readers = ','.join(f'{rid}:{r["role"]}' for rid, r in R['readers'].items())
        depths = ' '.join(f'data-line-depth-{r}="{R["roles"][r]["depth"]}"' for r in R['order'])
        island = {'page': page_id, 'pageTitle': title, 'root': up, 'version': VERSION,
                  'frontPath': 'admin/design/line/index.html', 'statusUrl': up + 'status.json',
                  'pageFor': ['team'] if for_ else None}
        banner = (f'<div class="mock-banner"><div class="shell"><span><b>Prototype F</b>, the line: the editor\'s design of '
                  f'25 October, built from the live data of release v{E(VERSION)}. Not the live site.</span>'
                  f'<a href="{up}admin/design/index.html">The design notes &rarr;</a></div></div>')
        menu = ''.join(f'<a href="{up}admin/design/line/{U(LINE_PAGES[0][0])}" data-menu="{E(" ".join(rs))}">{E(lab)}</a>'
                       for lab, rs in menu_role or [])
        html = f'''<!doctype html>
<html lang="en" data-root="{up}" data-path="{full}" data-ver="{VERSION}" data-line-readers="{E(readers)}" {depths}{f' data-line-for="{E(for_)}"' if for_ else ''}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)} &middot; {SITE_NAME}</title>
<meta name="description" content="{E(desc)}">
<meta name="robots" content="noindex">
<link rel="canonical" href="{BASE_URL}/{full}">
<link rel="icon" href="data:,">
<link rel="alternate" type="text/markdown" href="{up}{full[:-5]}.md">
<script src="{up}assets/route.js"></script>
<script src="{up}{LINE_DIR}/boot.js"></script>
<link rel="stylesheet" href="{up}assets/design/v2.css">
<link rel="stylesheet" href="{up}{LINE_DIR}/line.css">
<link rel="stylesheet" href="{up}{LINE_DIR}/shape.css">
<script src="{up}{LINE_DIR}/config.js" defer></script>
<script src="{up}{LINE_DIR}/engine.js" defer></script>
<script src="{up}{LINE_DIR}/line.js" defer></script>
</head>
<body class="v2">
{banner}
<header class="ln-mast"><a class="lg" href="{up}admin/design/line/index.html"><b>PHP</b>October 2026</a>
<nav aria-label="Prototype pages">{tabs}</nav><span class="menu-for">the menu follows your role on the live site</span></header>
<div class="ln" data-size="line" data-tone="calm" aria-live="polite" aria-label="How this page is written for you"><div class="ln-row"><span class="ln-msg"></span></div></div>
<main class="shell lnp">{body}
<div class="lp-more"><p class="small" style="margin:0 0 .5rem">That is the page for you.</p><button type="button" data-line-more>Show everything on it</button></div>
</main>
<script type="application/json" id="line-page">{J(island)}</script>
<script type="application/json" id="line-changes">{J(changes)}</script>
</body>
</html>
'''
        PAGES.append((full, title, desc, 'site'))
        write(full, html)
        txt = re.sub(r'<(script|style|svg|button).*?</\1>', '', body, flags=re.S)
        txt = re.sub(r'<(h1|h2|h3)[^>]*>(.*?)</\1>', lambda m: '\n' + '#' * (int(m.group(1)[1]) + 1) + ' ' + re.sub(r'<[^>]+>', '', m.group(2)) + '\n', txt, flags=re.S)
        txt = re.sub(r'<li[^>]*>', '\n- ', txt); txt = re.sub(r'<(p|div|section|article|tr)[^>]*>', '\n', txt); txt = re.sub(r'<[^>]+>', ' ', txt)
        txt = re.sub(r'[ \t]+', ' ', txt); txt = re.sub(r'\n\s*\n+', '\n\n', txt)
        import html as _H
        write(full[:-5] + '.md', f'# {title}\n\n{desc}\n\n> Prototype F for review, built from the data of release v{VERSION}. '
              f'Not the live site. Every part of the page is listed here; a reader sees the parts written for their role.\n\n'
              + _H.unescape(txt).strip() + f'\n\n---\nsite v{VERSION} · {BASE_URL}/{full}\n')
        made.append((full, title, desc))

    page('index.html', 'front', 'Prototype F: the line, the front page',
         'The front page of the line prototype: one band under the masthead that says one thing to the persona in front of it, '
         'and the page under it ordered for that role, at the depth they asked for.', front_body)
    page('agencies/index.html', 'agencies', 'Prototype F: the line, the agencies',
         'A content page under the line: the same page for every reader, with its own sentence per role in the line and the '
         'spectrum of government advice as the line\'s picture.', agencies_body)
    page('numbers/index.html', 'numbers', 'Prototype F: the line, the numbers',
         'A content page under the line: the numbers in the news, with the facts by status as the line\'s picture.', numbers_body)
    page('playbook/index.html', 'playbook', 'Prototype F: the line, the playbook',
         'A content page under the line: the response step by step, with a line written for each role.', playbook_body)
    page('console/index.html', 'console', 'Prototype F: the line, a page for the team',
         'A page written for the team: the line carries the gate, the page is dimmed rather than hidden, and anyone can read it anyway.',
         console_body, for_='team')

    # the catalogue: every line the rules produce, drawn by the engine in the browser
    cat = ('<div class="lnp-head"><p class="eyebrow">Prototype F &middot; the catalogue</p>'
           '<h1 class="display" style="font-size:clamp(1.7rem,2.8vw,2.8rem)">Every line, by moment, role and page</h1>'
           '<p class="lede">Every sentence the rules can produce at this release, drawn by the same engine the pages use '
           '(assets/design/line/engine.js). Nothing here is stored; it is a reading of the rules.</p></div>'
           '<div id="ln-cat"></div>')
    page('catalogue/index.html', 'catalogue', 'Prototype F: every line the rules produce',
         'Every line the rules produce, by visit moment, by role and by page, drawn by the engine at this release.', cat)
    return made


# =========================================================================== the line live, and the router (25 October 2026)
# The editor approved the router (board 311) and asked for the line on the live pages with it (board 297): every page
# carries the line under the masthead instead of the two dials; an address past a reserved word (as, on, vs, since) is a
# view of a real page, answered by /404.html, which opens the page with the view; a handful of view addresses are real
# files, cards, so a link pasted into a chat unfurls with a title that says who it is for.
# Briefs: 2026-10-25__brief__the-404-router-and-two-modes.md, 2026-10-25__brief__the-line.md.

RESERVED_WORDS = ('as', 'on', 'vs', 'since')
CARD_PAGES = [('index.html', 'front', 'The front page'), ('agencies/index.html', 'agencies', 'The agencies'),
              ('numbers/index.html', 'numbers', 'The numbers'), ('playbook/index.html', 'playbook', 'The playbook')]


def line_html_attrs(ns):
    """What boot.js needs on <html> before the first paint: the readers inside each role, and each role's depth."""
    R = line_spec(ns, 'roles.json')
    readers = ','.join(f'{rid}:{r["role"]}' for rid, r in R['readers'].items())
    depths = ''.join(f' data-line-depth-{r}="{R["roles"][r]["depth"]}"' for r in R['order'])
    return f' data-line-readers="{ns["E"](readers)}"{depths}'


def line_head(up):
    """The line's head on a live page: the boot script first (blocking), its styles, then its deferred scripts."""
    return (f'<script src="{up}assets/route.js"></script>\n<script src="{up}{LINE_DIR}/boot.js"></script>\n'
            f'<link rel="stylesheet" href="{up}{LINE_DIR}/line.css">\n<link rel="stylesheet" href="{up}{LINE_DIR}/shape.css">\n')


def line_scripts(up):
    return (f'<script src="{up}{LINE_DIR}/config.js" defer></script>\n<script src="{up}{LINE_DIR}/engine.js" defer></script>\n'
            f'<script src="{up}{LINE_DIR}/line.js" defer></script>')


LINE_BAND = ('<div class="ln" data-size="line" data-tone="calm" aria-live="polite" aria-label="How this page is written for you">'
             '<div class="ln-row"><span class="ln-msg"></span></div></div>')


def check_reserved(ns):
    """No real page may have a path segment that is a reserved word, or the router could not tell page from view."""
    bad = [p for p, *_ in ns['PAGES'] if any(seg in RESERVED_WORDS for seg in p.split('/')[:-1])]
    if bad:
        raise SystemExit('build: these pages use a reserved word (%s) as a directory, which the router reads as a view: %s'
                         % (', '.join(RESERVED_WORDS), ', '.join(bad[:6])))


WORD = {'exec': 'executive', 'general': 'general', 'security': 'security', 'engineer': 'engineer',
        'journalist': 'journalist', 'researcher': 'researcher', 'everything': 'everything'}


def views_row(ns, path, up):
    """At the foot of a page that has cards: the page for each role, as links. With the line running, a tap switches
    the view in place; without it, or for a crawler, each link is a card that opens the page as that reader."""
    page = next((x for x in CARD_PAGES if x[0] == path), None)
    if not page:
        return ''
    E = ns['E']
    R = line_spec(ns, 'roles.json')
    base_dir = path[:-len('index.html')]
    links = ' &middot; '.join(f'<a href="{up}{base_dir}as/{WORD[r]}/index.html" data-as="{E(r)}">{E(R["roles"][r]["name"])}</a>'
                              for r in R['order'])
    return f'<nav class="ln-views" aria-label="This page, written for each reader"><span>Read this page as:</span> {links}</nav>'


def card_html(ns, path, up, title, desc, og_url, canonical, body):
    """A card: a real file at a view address, so a link pasted into a chat unfurls with who it is for."""
    E = ns['E']
    image = ns['BASE_URL'] + '/' + ((ns.get('SEO') or {}).get('image') or 'assets/og-card.png')
    return f'''<!doctype html>
<html lang="en" data-path="{E(path)}" data-ver="{E(ns["VERSION"])}"{line_html_attrs(ns)}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{ns["SITE_NAME"]}">
<meta property="og:url" content="{E(og_url)}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{E(image)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:,">
<link rel="alternate" type="text/markdown" href="index.md">
<link rel="stylesheet" href="{up}assets/design/v2.css">
<script src="{up}assets/design/router/router.js"></script>
</head>
<body>
<!-- This address is a view: the page before the word "as", written for the reader named after it. The page's own
     content is at that page's address, with its markdown twin beside it. -->
<main class="shell" style="padding:3rem var(--gut)">{body}</main>
</body>
</html>
'''


def not_found_html(ns):
    """/404.html: GitHub Pages serves it at whatever address was missing, at any depth, so it links nothing relative:
    the router is inline (the site's policy hashes inline scripts) and every link is absolute."""
    E, B = ns['E'], ns['BASE_URL']
    router = open(ns['os'].path.join(ns['ROOT'], 'assets', 'design', 'router', 'router.js'), encoding='utf-8').read()
    return f'''<!doctype html>
<html lang="en" data-path="404.html" data-ver="{E(ns["VERSION"])}"{line_html_attrs(ns)}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{ns["SITE_NAME"]}: this page, written for you</title>
<meta name="description" content="The PHP security flaws of October 2026, as evidence: the page you opened, written for the reader you are.">
<meta name="robots" content="noindex">
<link rel="canonical" href="{B}/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{ns["SITE_NAME"]}">
<meta property="og:url" content="{B}/">
<meta property="og:title" content="{ns["SITE_NAME"]}: this page, written for you">
<meta property="og:description" content="The PHP security flaws of October 2026, as evidence: every page written for the reader in front of it.">
<meta property="og:image" content="{B}/assets/og-card.png">
<link rel="icon" href="data:,">
<style>body{{margin:0;background:#f5f3ee;color:#0f1b2d;font:16px/1.5 Inter,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
main{{max-width:44rem;margin:0 auto;padding:3rem 1.2rem}}h1{{font-family:Georgia,serif;font-size:2rem;line-height:1.15}}a{{color:#0f766e}}
.e{{font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#64748b}}</style>
<script>{router}</script>
</head>
<body>
<!-- An address past one of the words as, on, vs or since is a view of the page before that word; the page's own
     content is at that page's address, with its markdown twin beside it. Any other address is not a page here. -->
<main>
<p class="e">PHP October 2026</p>
<p id="routing">Opening the page written for you&hellip;</p>
<div id="not-found" hidden><h1>No page at this address</h1>
<p>It may have moved. <a href="{B}/">The front page</a> has the story as it stands, and <a href="{B}/start/index.html">who is reading</a> lets you pick the page written for you.</p></div>
<noscript><p>This address is a view of a page on this site. <a href="{B}/">Open the front page</a>.</p></noscript>
</main>
</body>
</html>
'''


def build_router(ns):
    """/404.html, the router; and the cards: real files at the view addresses most likely to be shared."""
    import json as _j
    E, U, write, BASE_URL, PAGES = ns['E'], ns['U'], ns['write'], ns['BASE_URL'], ns['PAGES']
    R = line_spec(ns, 'roles.json')
    copy = _j.loads(line_copy(ns))
    check_reserved(ns)                                   # before the cards, whose own paths are views
    made = []

    desc = 'The page that answers any address that is not a file: it opens the page a view address names, written for the reader it names.'
    write('404.html', not_found_html(ns))
    write('404.md', f'# {ns["SITE_NAME"]}: the router\n\n{desc}\n\nAn address past one of the words as, on, vs or since is a view of '
          f'the page before that word: /agencies/as/security/ is the agencies page, written for Security. Any other missing '
          f'address is not a page here.\n\n---\nsite v{ns["VERSION"]} · {BASE_URL}/404.html\n')
    PAGES.append(('404.html', 'The router', desc, 'site'))
    made.append(('404.html', 'The router (404.html)', desc))

    for path, pid, ptitle in CARD_PAGES:
        base_dir = path[:-len('index.html')]
        lines = copy['pageLines'].get(pid, {})
        for role in R['order']:
            word, name = WORD[role], R['roles'][role]['name']
            line = lines.get(role) or lines.get('_') or ''
            who = R['roles'][role]['as'] if role != 'everything' else 'everyone, unfiltered'
            title = f'{ptitle}, for {who} · {ns["SITE_NAME"]}'
            card = f'{base_dir}as/{word}/index.html'
            up = '../' * card.count('/')
            body = (f'<p class="eyebrow">PHP October 2026 &middot; {E(name)}</p><h1 class="display" style="font-size:2rem">{E(ptitle)}</h1>'
                    f'<p class="lede">{E(line)}</p><p><a href="{up}{U(path)}">Open {E(ptitle.lower())}</a></p>')
            write(card, card_html(ns, card, up, title, line or ptitle, f'{BASE_URL}/{base_dir}as/{word}/', f'{BASE_URL}/{base_dir}', body))
            write(card[:-5] + '.md', f'# {ptitle}, for {who}\n\n{line}\n\nA view of [{ptitle}]({BASE_URL}/{path}), written for {who}. '
                  f'The page itself, and its markdown twin, are at that address.\n\n---\nsite v{ns["VERSION"]} · {BASE_URL}/{card}\n')
            PAGES.append((card, title, line or ptitle, 'site'))
            made.append((card, f'{ptitle}, for {who}', line or ptitle))
    return made
