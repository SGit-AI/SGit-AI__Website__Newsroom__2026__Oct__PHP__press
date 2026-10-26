"""Wikitext to statements: a small, deterministic parser for the build, so a Wikipedia article can be read as a graph.

Kept by the ontologist (ontologist@php.newsroom). Standard library only; no model anywhere in it. Brief:
admin/content/briefs/2026-10-25__brief__wikipedia-as-an-anchor.md.

What it does, in order:
    1. lifts every <ref> out of the text (named ones once, reused by name) and parses its {{cite ...}} template;
    2. turns the wikitext into plain text, section by section, keeping a marker where each reference sat;
    3. splits each paragraph into sentences: one sentence is one statement, with the references attached to it;
    4. classes each statement by its wording (never by whether it is true): a quote, an attributed statement,
       hedged wording, a record (a number, a date, an identifier) or a plain statement; and cited or not.
    A statement's id is a hash of its wording, so the same sentence keeps its id from one revision to the next, and
    what changed between two revisions is the set difference.

Wikipedia's own rule is that an article states facts and attributes opinions. So an 'attributed' statement is where the
article itself says a thing is somebody's view or report; 'quote' is their words; 'hedged' is the article being careful.
Those are classes of wording. The evidence for any of them is in the references, and the site's own captures of them.
"""
import hashlib, re

CITE_URL_FIELDS = ('url', 'archive-url', 'archiveurl')
ABBREV = {'u.s', 'u.k', 'e.g', 'i.e', 'inc', 'ltd', 'co', 'corp', 'vs', 'v', 'no', 'mr', 'ms', 'dr', 'st', 'jr', 'sr', 'approx', 'ca', 'cf', 'al', 'fig', 'gov', 'dept'}
VERBS = (r"said|says|stated|states|told|announced|reported|reports|wrote|writes|described|called|warned|warns|claimed|claims|estimated|estimates|"
         r"confirmed|denied|denies|noted|argued|accused|blamed|characteri[sz]ed|advised|urged|recommended|disclosed|acknowledged|admitted|"
         r"criticized|criticised|suggested|speculated|believes?|believed|expected|expects|expressed|considered|considers|thinks|thought|found|finds|assessed|assesses")
# a named party, then a reporting verb (not a passive 'was announced', which is the article's own voice)
ATTRIBUTED = re.compile(r"\baccording to\b|\b(?:[A-Z][\w.&'’-]*|the [A-Z][\w.&'’-]*)(?: (?:[A-Z][\w.&'’-]*|of|and|for|the|de|du|&))*,? (?:(?:also|later|initially|first|publicly|has|have|had) )?(?:" + VERBS + r")\b|"
                        r"\b(?:who|which) (?:" + VERBS + r")\b|\b(?:coverage|reporting|a report|an article|a post|a statement) (?:in|from|by) [A-Z].{0,60}? (?:" + VERBS + r")\b")
HEDGED = re.compile(r"\b(may|might|could|possibly|reportedly|allegedly|purportedly|likely|unlikely|unclear|appears?|appeared|seem(s|ed)?|"
                    r"is thought|are thought|was thought|were thought|is believed|are believed|is estimated|are estimated|was estimated|estimated to|"
                    r"an estimated|potentially|apparently|supposedly|presumably|speculated|suspected|not yet confirmed|unconfirmed)\b", re.I)
RECORD = re.compile(r"\bCVE-\d{4}-\d{4,7}\b|\b\d+(\.\d+){1,3}\b|\b\d{1,2} (January|February|March|April|May|June|July|August|September|October|November|December) \d{4}\b|"
                    r"\b\d{4}-\d{2}-\d{2}\b|\b\d+(,\d{3})+\b|\b\d+(\.\d+)? ?(%|percent|million|billion|thousand|hours?|minutes?|days?)\b|\b\d{1,2}:\d{2}\b", re.I)
QUOTE = re.compile(r'[“"]([^”"]{12,})[”"]')
CVE = re.compile(r'\bCVE-\d{4}-\d{4,7}\b')


# ------------------------------------------------------------------------------------------------ references

def split_template(body):
    """'cite web |url=... |title=...' into (name, {field: value}), splitting on bars only at depth 0."""
    parts, depth, cur = [], 0, []
    for ch in body:
        if ch in '{[':
            depth += 1
        elif ch in '}]':
            depth -= 1
        if ch == '|' and depth == 0:
            parts.append(''.join(cur)); cur = []
        else:
            cur.append(ch)
    parts.append(''.join(cur))
    name = parts[0].strip().lower()
    fields = {}
    for p in parts[1:]:
        if '=' in p:
            k, v = p.split('=', 1)
            fields[k.strip().lower()] = plain(v.strip())
    return name, fields


def parse_ref(content):
    """The content of one <ref>: the cite template's fields, plus the url and the title the page would show."""
    m = re.search(r'\{\{\s*(cite[^|}]*|citation)\s*\|(.*)\}\}\s*$', content.strip(), re.S | re.I)
    if not m:
        text = plain(content)
        url = re.search(r'https?://\S+', content)
        return {'template': None, 'fields': {}, 'url': url.group(0).rstrip('].') if url else None, 'title': text[:160] or None, 'publisher': None, 'date': None, 'archive_url': None}
    name, f = split_template(m.group(1) + '|' + m.group(2))
    url = f.get('url')
    if name == 'cite tweet' and f.get('user') and f.get('number'):
        url = f'https://x.com/{f["user"]}/status/{f["number"]}'
    publisher = f.get('website') or f.get('work') or f.get('newspaper') or f.get('publisher') or f.get('agency') or f.get('magazine') or f.get('journal')
    author = ', '.join(x for x in (f.get('author') or (' '.join(filter(None, (f.get('first'), f.get('last')))) or None), f.get('author2'), f.get('author3')) if x) or None
    return {'template': name, 'fields': f, 'url': url, 'title': f.get('title') or f.get('name'), 'publisher': publisher, 'author': author,
            'date': f.get('date'), 'access_date': f.get('access-date') or f.get('accessdate'), 'archive_url': f.get('archive-url') or f.get('archiveurl'),
            'language': f.get('language'), 'quote': f.get('quote')}


def lift_refs(text):
    """Replace every <ref> with a marker and return (text, refs): refs keyed by name or by order for the unnamed."""
    refs, order = {}, []
    n = [0]

    def key_of(attrs):
        m = re.search(r'name\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s/>]+))', attrs or '')
        if m:
            return 'n:' + (m.group(2) or m.group(3) or m.group(4)).strip()
        n[0] += 1
        return f'a:{n[0]}'

    def full(m):
        k = key_of(m.group(1))
        if k not in refs:
            refs[k] = parse_ref(m.group(2)); refs[k]['key'] = k; order.append(k)
        elif refs[k].get('url') is None and m.group(2).strip():
            refs[k].update(parse_ref(m.group(2))); refs[k]['key'] = k
        return f'\x00{k}\x00'

    def short(m):
        k = key_of(m.group(1))
        if k not in refs:
            refs[k] = {'template': None, 'fields': {}, 'url': None, 'title': None, 'publisher': None, 'date': None, 'archive_url': None, 'key': k, 'undefined': True}; order.append(k)
        return f'\x00{k}\x00'

    text = re.sub(r'<ref([^>/]*)>(.*?)</ref>', full, text, flags=re.S | re.I)
    text = re.sub(r'<ref([^>]*)/>', short, text, flags=re.I)
    for i, k in enumerate(order, 1):
        refs[k]['n'] = i
    return text, refs


# ------------------------------------------------------------------------------------------------ plain text

def strip_templates(text):
    """Remove {{...}} with nesting; keep the text of a few that only wrap words."""
    out, i, depth, start = [], 0, 0, 0
    keep = ('nowrap', 'lang', 'em', 'strong', 'small', 'code', 'mono', 'convert', 'nobr', 'as of', 'asof')
    glyph = {'ndash': '–', 'snd': ' – ', 'spaced ndash': ' – ', 'en dash': '–', 'mdash': '—', 'em dash': '—', 'circa': 'c. ', 'c.': 'c. ', 'nbsp': ' ', 'endash': '–', 'emdash': '—'}
    while i < len(text):
        if text.startswith('{{', i):
            if depth == 0:
                start = i
            depth += 1; i += 2; continue
        if text.startswith('}}', i) and depth:
            depth -= 1; i += 2
            if depth == 0:
                inner = text[start + 2:i - 2]
                name = inner.split('|', 1)[0].strip().lower()
                if name in glyph:
                    out.append(glyph[name])
                elif name in keep and '|' in inner:
                    args = [a for a in split_template(inner)[1].values()] or []
                    last = inner.rsplit('|', 1)[1]
                    out.append(plain(last if '=' not in last else (args[-1] if args else '')))
            continue
        if depth == 0:
            out.append(text[i])
        i += 1
    return ''.join(out)


def strip_files(text):
    """Remove [[File:...]] and [[Image:...]] with their captions, which nest their own [[links]]."""
    out, i = [], 0
    while i < len(text):
        m = re.match(r'\[\[(?:File|Image|Category):', text[i:], re.I)
        if m:
            depth, j = 0, i
            while j < len(text):
                if text.startswith('[[', j):
                    depth += 1; j += 2; continue
                if text.startswith(']]', j):
                    depth -= 1; j += 2
                    if depth == 0:
                        break
                    continue
                j += 1
            i = j
            continue
        out.append(text[i]); i += 1
    return ''.join(out)


def plain(text):
    """Wikitext markup to plain text, leaving the \x00ref\x00 markers alone."""
    t = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    t = re.sub(r'\{\|.*?\|\}', '', t, flags=re.S)
    t = strip_templates(t)
    t = strip_files(t)
    t = re.sub(r'\[\[([^\]|]*)\|([^\]]*)\]\]', r'\2', t)
    t = re.sub(r'\[\[([^\]]*)\]\]', r'\1', t)
    t = re.sub(r'\[(https?://[^\s\]]+)\s+([^\]]*)\]', r'\2', t)
    t = re.sub(r'\[(https?://[^\s\]]+)\]', '', t)
    t = re.sub(r"'{2,5}", '', t)
    t = re.sub(r'<br\s*/?>', ' ', t, flags=re.I)
    t = re.sub(r'</?(nowiki|small|big|sup|sub|span|div|u|s|code|blockquote|poem|gallery)[^>]*>', '', t, flags=re.I)
    t = t.replace('&nbsp;', ' ').replace('&ndash;', '–').replace('&mdash;', '—').replace('&amp;', '&').replace('&quot;', '"')
    return re.sub(r'[ \t]+', ' ', t)


def sections(text):
    """[(level, title, body)] with the lead as ('', body); headings are == Title ==."""
    out, title, level, buf = [], '', 0, []
    for line in text.split('\n'):
        m = re.match(r'^(={2,6})\s*(.*?)\s*\1\s*$', line)
        if m:
            out.append((level, title, '\n'.join(buf))); buf = []
            level, title = len(m.group(1)), plain(m.group(2)).strip()
        else:
            buf.append(line)
    out.append((level, title, '\n'.join(buf)))
    return out


def sentences(paragraph):
    """Split one paragraph into sentences, keeping each sentence's reference markers with it."""
    p = re.sub(r'\s*\n\s*', ' ', paragraph.strip())
    if not p:
        return []
    out, start = [], 0
    for m in re.finditer(r'([.!?]["”’)]?)((?:\x00[^\x00]+\x00)*)\s+(?=[A-Z“"(\[\d])', p):
        before = p[start:m.end()]
        word = re.findall(r'(\S+)[.!?]["”’)]?$', before.split('\x00')[0].rstrip())
        if m.group(1)[0] in '!?' and word and word[-1][:1].isupper() and not m.group(2):
            continue
        if word and word[-1].lower().rstrip('.') in ABBREV:
            continue
        if word and re.match(r'^[A-Z]$', word[-1].rstrip('.')):
            continue
        out.append(before.strip()); start = m.end()
    out.append(p[start:].strip())
    return [s for s in out if s]


def classify(text):
    if QUOTE.search(text):
        return 'quote'
    if ATTRIBUTED.search(text):
        return 'attributed'
    if HEDGED.search(text):
        return 'hedged'
    if RECORD.search(text):
        return 'record'
    return 'stated'


def statements(wikitext):
    """Everything the build needs from one revision: sections, statements with refs and classes, and the references."""
    text, refs = lift_refs(wikitext)
    out, secs = [], []
    skip = {'references', 'external links', 'see also', 'notes', 'further reading', 'sources', 'bibliography'}
    for level, title, body in sections(text):
        if title.lower() in skip:
            continue
        sec_id = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or 'lead'
        secs.append({'id': sec_id, 'title': title or 'Lead', 'level': level})
        body = plain(body)
        for para in re.split(r'\n\s*\n|\n(?=[*#;:])', body):
            para = re.sub(r'^[*#;:]+\s*', '', para.strip())
            if not para or para.startswith('{') or para.startswith('|'):
                continue
            for i, s in enumerate(sentences(para)):
                keys = re.findall(r'\x00([^\x00]+)\x00', s)
                words = re.sub(r'\x00[^\x00]+\x00', '', s).strip()
                words = re.sub(r'\s+([.,;:!?])', r'\1', words)
                if len(words) < 3:
                    continue
                norm = re.sub(r'\s+', ' ', words.lower())
                sid = hashlib.sha256(norm.encode()).hexdigest()[:10]
                out.append({'id': sid, 'section': sec_id, 'text': words, 'refs': [refs[k]['n'] for k in dict.fromkeys(keys) if k in refs],
                            'class': classify(words), 'cited': bool(keys), 'cves': sorted(set(CVE.findall(words)))})
    cited = {n for st in out for n in st['refs']}
    reflist = [refs[k] for k in sorted(refs, key=lambda k: refs[k]['n'])]
    for r in reflist:
        # a marker that no statement carries sat inside a template the parser dropped: the infobox, a table, a caption
        r['where'] = 'statement' if r['n'] in cited else 'infobox'
    return {'sections': secs, 'statements': out, 'references': reflist}


def delta(a, b):
    """What changed from revision a's statements to b's: added, removed, and the pairs that look like edits of one another."""
    import difflib
    A = {s['id']: s for s in a['statements']}; B = {s['id']: s for s in b['statements']}
    removed = [A[k] for k in A if k not in B]; added = [B[k] for k in B if k not in A]
    changed, used = [], set()
    for r in removed:
        best, score = None, 0.0
        for x in added:
            if x['id'] in used:
                continue
            sc = difflib.SequenceMatcher(None, r['text'], x['text']).ratio()
            if sc > score:
                best, score = x, sc
        if best and score >= 0.6:
            used.add(best['id']); changed.append({'from': r, 'to': best, 'similarity': round(score, 2)})
    removed = [r for r in removed if not any(c['from']['id'] == r['id'] for c in changed)]
    added = [x for x in added if x['id'] not in used]
    ra = {r['url'] for r in a['references'] if r.get('url')}; rb = {r['url'] for r in b['references'] if r.get('url')}
    return {'added': added, 'removed': removed, 'changed': changed, 'refs_added': sorted(rb - ra), 'refs_removed': sorted(ra - rb)}


# ------------------------------------------------------------------------------------------------ talk pages

SIG = re.compile(r'\[\[User(?: talk)?:([^|\]]+)(?:\|[^\]]*)?\]\](?:[^\n]*?)(\d{1,2}:\d{2}, \d{1,2} \w+ \d{4}) \(UTC\)')
MONTHS = {m: i for i, m in enumerate(('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'), 1)}


def sig_time(t):
    """'20:59, 21 October 2026' to '2026-10-21T20:59Z'."""
    m = re.match(r'(\d{1,2}):(\d{2}), (\d{1,2}) (\w+) (\d{4})', t)
    return f'{m.group(5)}-{MONTHS[m.group(4)]:02d}-{int(m.group(3)):02d}T{int(m.group(1)):02d}:{m.group(2)}Z' if m and m.group(4) in MONTHS else t


def talk(wikitext):
    """A talk page as threads of signed posts. A post is a run of lines up to a signature; its depth is the count of
    leading colons, and it replies to the nearest earlier post with a smaller depth. Templates on a post (request
    edit, and whether it was answered) are kept by name."""
    text = re.sub(r'<!--.*?-->', '', wikitext, flags=re.S)
    threads, cur = [], None
    for level, title, body in sections(text):
        if not title:
            continue
        posts, buf, depth = [], [], 0
        def flush(buf, depth):
            raw = '\n'.join(buf).strip()
            if not raw:
                return
            m = SIG.search(raw)
            who, when = (m.group(1).strip(), sig_time(m.group(2))) if m else (None, None)
            tpl = [t.strip().lower() for t in re.findall(r'\{\{\s*([^|}]+)', raw)]
            body_text = plain(re.sub(r'\{\{[^{}]*\}\}', '', SIG.sub('', raw))).strip()
            body_text = re.sub(r'^[:*#]+', '', body_text, flags=re.M).strip()
            posts.append({'who': who, 'when': when, 'depth': depth, 'text': body_text, 'templates': tpl,
                          'request_edit': any(t.startswith('request edit') for t in tpl) or 'edit request' in raw.lower(),
                          'answered': bool(re.search(r'request edit\s*\|\s*answered\s*=\s*yes', raw, re.I))})
        for line in body.split('\n'):
            d = len(line) - len(line.lstrip(':'))
            if buf and (d != depth) and line.strip():
                flush(buf, depth); buf = []
            if line.strip():
                depth = d
            buf.append(line)
            if SIG.search(line):
                flush(buf, depth); buf = []
        flush(buf, depth)
        for i, p_ in enumerate(posts):
            p_['reply_to'] = next((j for j in range(i - 1, -1, -1) if posts[j]['depth'] < p_['depth']), None)
        tid = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        threads.append({'id': tid, 'title': title, 'level': level, 'posts': posts,
                        'request_edit': any(p_['request_edit'] for p_ in posts), 'answered': any(p_['answered'] for p_ in posts),
                        'started': min((p_['when'] for p_ in posts if p_['when']), default=None), 'last': max((p_['when'] for p_ in posts if p_['when']), default=None)})
    return threads
