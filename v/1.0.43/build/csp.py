"""The Content-Security-Policy of every page this site builds, kept by security@php.newsroom.

GitHub Pages sends no headers we control, so the policy rides in a <meta http-equiv> tag, written by build.py's
write() as the first thing after <meta charset>. Standard library only; deterministic (same page, same policy).

Why it matters here: this site renders text from captured third-party pages, feeds, readers' submissions and model
output, and its origin holds readers' secrets in the browser (the /now/ vault key, the signing keys of enrolled
contributors). One escaping mistake would run an attacker's script with all of that in reach (SA-2026-012 is the
one that happened). The policy is the second wall: even when data gets into the page as markup, the browser runs
only this site's own scripts and the inline ones whose exact bytes the build hashed.

What it allows, and why:
  script-src   'self' and the sha256 of each inline script on that page; never 'unsafe-inline' or 'unsafe-eval',
               so injected <script>, event-handler attributes and javascript: URLs do not run
  connect-src  'self' and the services the pages talk to (CONNECT); /reader/ also any https feed a reader adds
  frame-src    the official vault UI, embedded read-only on the vault pages
  img-src      'self', data: and blob: (QR codes, screenshots, the model's infographic), and the GitHub badges
  style-src    'self' 'unsafe-inline': the pages and components set inline styles; CSS cannot run script
  object-src 'none'; base-uri 'none'; form-action 'self'
frame-ancestors (clickjacking) cannot be set from a meta tag; GitHub Pages would have to send it as a header.
"""
import base64, hashlib, json, os, re

CONNECT = [
    'https://dev.send.sgraph.ai',      # the append lanes (telemetry, subscriptions, collaborators) and the vault library
    'https://openrouter.ai',           # the Ask pane and /now/: the reader's own key, from the reader's browser
    'https://ipapi.co', 'https://ipwho.is',   # telemetry's coarse location (country, region), disclosed on the page
    'https://api.github.com',          # /status/: the deploy runs, read with no credential
]
FRAMES = ['https://dev.vault.sgraph.ai']
IMAGES = ["'self'", 'data:', 'blob:', 'https://github.com', 'https://*.githubusercontent.com']
# pages that read whatever https feed a reader adds (assets/feed-viewer.js checks the address before it fetches)
OPEN_CONNECT = ('reader/index.html',)


def sibling_sites():
    """/status/ reads each newsroom site's VERSION file: the origins of the sites in data/pipeline.json, nothing else."""
    try:
        P = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'pipeline.json'), encoding='utf-8'))
        return sorted({re.match(r'https://[a-z0-9.-]+', s['site']).group(0) for s in P['sites'] if re.match(r'https://[a-z0-9.-]+/?$', s.get('site', ''))})
    except (OSError, ValueError, KeyError, AttributeError):
        return []

INLINE = re.compile(r'<script\b(?![^>]*\bsrc=)([^>]*)>(.*?)</script\b[^>]*>', re.S | re.I)
DATA_TYPES = re.compile(r'\btype\s*=\s*["\']?(application/(ld\+)?json|text/template|text/plain)', re.I)


def inline_hashes(page):
    """The sha256 of every inline script the browser would run, in order of first appearance."""
    out = []
    for m in INLINE.finditer(page):
        if DATA_TYPES.search(m.group(1)):
            continue
        h = "'sha256-" + base64.b64encode(hashlib.sha256(m.group(2).encode('utf-8')).digest()).decode() + "'"
        if h not in out:
            out.append(h)
    return out


def policy(path, page):
    connect = ["'self'"] + CONNECT + (['https:'] if path in OPEN_CONNECT else []) + (sibling_sites() if path == 'status/index.html' else [])
    return '; '.join([
        "default-src 'self'",
        "script-src 'self' " + ' '.join(inline_hashes(page)),
        "style-src 'self' 'unsafe-inline'",
        'img-src ' + ' '.join(IMAGES),
        "font-src 'self' data:",
        'connect-src ' + ' '.join(connect),
        'frame-src ' + ' '.join(FRAMES),
        "worker-src 'self' blob:",
        "manifest-src 'self'",
        "media-src 'self' data: blob:",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
    ]).replace("script-src 'self' ;", "script-src 'self';")


def with_csp(path, page):
    """The page with its policy as the first tag after <meta charset>; a page that already has one is left as it is."""
    if 'http-equiv="Content-Security-Policy"' in page or '<meta charset="utf-8">' not in page:
        return page
    tag = f'<meta http-equiv="Content-Security-Policy" content="{policy(path, page)}">'
    return page.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + tag, 1)
