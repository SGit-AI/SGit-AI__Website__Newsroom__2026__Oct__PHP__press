#!/usr/bin/env python3
"""The security checks, kept by security@php.newsroom. Standard library only.

Three ways in:
  validate.py imports tree_fails(ROOT): the checks on the working tree that fail a release.
  release.sh runs `security_check.py --staged`: the tripwire on what is about to be committed.
  The security agent runs `security_check.py --report [--history] [--vault <clone> ...]` on its regular pass:
  everything above, plus every commit on every branch, plus any vault clone it is given (read-only clones only).

What it looks for, and why, is in admin/security/README.md. A finding prints the file, the line and the kind, never
the secret itself.
"""
import json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# Credential shapes. The published keys (sgit_public_read_*, the two lanes' append tokens) are public on purpose and
# are not matched; a vault key is sgit_private_vault_<secret>:<vault id>.
SECRET_KINDS = [
    ('an sgit private key', r'sgit_private_[a-z]+_[0-9A-Za-z]{12,}'),            # sgit vault and private read keys
    ('a PEM private key', r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    ('an AWS access key id', r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'),
    ('an Anthropic key', r'\bsk-ant-[A-Za-z0-9_-]{20,}'),
    ('an OpenAI or OpenRouter key', r'\bsk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{32,}'),
    ('a GitHub token', r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}'),
    ('a GitHub fine-grained token', r'\bgithub_pat_[A-Za-z0-9_]{40,}'),
    ('a Slack token', r'\bxox[baprs]-[0-9A-Za-z-]{10,}'),
    ('a Slack webhook', r'hooks\.slack\.com/services/[A-Za-z0-9/]{20,}'),
    ('a Google API key', r'\bAIza[0-9A-Za-z_-]{35}\b'),
    ('a JWT', r'\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
    ('an SG/Send access token', r'\bsg-send_[A-Za-z0-9]{6,}'),
]
SECRET = re.compile('|'.join(f'(?P<k{i}>{rx})' for i, (_, rx) in enumerate(SECRET_KINDS)))


def kind_of(m):
    """What a match is, by name: a finding never repeats any character of the secret it found (CodeQL py/clear-text-logging)."""
    return SECRET_KINDS[int(m.lastgroup[1:])][0]
# Environment variables whose values must never appear in the tree, whatever their shape.
SECRET_ENV = ('SG_SEND_ACCESS_TOKEN', 'SYNTHETIC_VAULT_KEYS', 'ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY', 'GITHUB_TOKEN', 'GH_TOKEN')
# Paths that hold decrypted vault content or keys and must never be committed (the site publishes the whole tree).
SENSITIVE_PATH = re.compile(r'(^|/)(\.sg_vault|\.sg-send)(/|$)|(^|/)(lane\.json|pki-passphrase|subscribers\.json|panel\.json|keys?[-_.][^/]*\.json)$|(^|/)(requests|drain|feedback|enrolments)/[^/]*\.jsonl$|(^|/)inbox/[^/]*\.eml$|\.(pem|key)$')

# Invisible characters that hide text from a person but not from a model: Unicode tags and bidi controls always,
# zero-width characters in prose and data.
TAGS_BIDI = re.compile('[\U000E0000-\U000E007F\u202A-\u202E\u2066-\u2069]')
ZERO_WIDTH = re.compile('[\u200B-\u200F\u2060-\u2064]')
# Text addressed to a model. Kept narrow on purpose: a hit stops the release until a person allows it in
# admin/security/injection-allowlist.json (for example a story that quotes a headline about prompt injection).
INJECTION = re.compile(r'(ignore|disregard|forget) (all |any |the )?(previous|prior|above|earlier) (instructions|prompts?|context)'
                       r'|you are now (a|an|in|the) |new (system )?instructions:|<\|im_(start|end)\|>|\[/?INST\]|^\s*(system|assistant):\s'
                       r'|(do not|don\'t) (tell|inform|mention (this )?to) the (user|editor|human)'
                       r'|(AI|LLM|agent|assistant|model)s?,? (must|should|are to) (now )?(ignore|reveal|send|email|push|delete|print|output)', re.I | re.M)
TEXT_EXT = ('.html', '.md', '.txt', '.json', '.xml', '.jsonl', '.csv', '.webmanifest')
SKIP_DIRS = {'.git', '.sg_vault', 'node_modules', '__pycache__'}
SLUG = re.compile(r'[a-z0-9][a-z0-9._-]*')
JSON_SCRIPT = re.compile(r'<script type="application/(?:ld\+)?json"[^>]*>(.*?)</script>', re.S)
INLINE_HANDLER = re.compile(r'<[a-zA-Z][^<>]*\son[a-z]+\s*=', re.I)    # the site never writes one; data that does is an injection
BAD_SCHEME = re.compile(r'\b(href|src|action|formaction)\s*=\s*["\']?\s*(javascript|vbscript|data:text/html)', re.I)


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
        for f in sorted(files):
            yield os.path.join(d, f)


def read_text(p):
    try:
        b = open(p, 'rb').read()
    except OSError:
        return None
    if b'\x00' in b[:8000]:
        return None
    return b.decode('utf-8', 'replace')


def line_of(text, i):
    return text.count('\n', 0, i) + 1


def env_secrets():
    out = []
    for k in SECRET_ENV:
        v = os.environ.get(k, '')
        if len(v) >= 12 and not v.startswith('proxy-'):
            out.append((k, v))
            if k == 'SYNTHETIC_VAULT_KEYS':
                try:
                    out += [(f'{k}[{pid}]', x['vault_key']) for pid, x in json.loads(v).items() if x.get('vault_key')]
                except Exception:
                    pass
    return out


def allowlist(root):
    p = os.path.join(root, 'admin', 'security', 'injection-allowlist.json')
    try:
        return {(a['path'], a['match'].lower()) for a in json.load(open(p))['allowed']}
    except (OSError, ValueError, KeyError):
        return set()


def tree_fails(root=ROOT):
    """The checks validate.py runs: every one a reason not to publish."""
    fails, allowed, envs = [], allowlist(root), env_secrets()
    for p in walk(root):
        rp = os.path.relpath(p, root).replace(os.sep, '/')
        if rp.startswith('admin/build/security_check.py'):
            continue
        t = read_text(p)
        if t is None:
            continue
        m = SECRET.search(t)
        if m:
            fails.append(f'{rp}:{line_of(t, m.start())}: credential shape: {kind_of(m)}')
        for k, v in envs:
            if v in t:
                fails.append(f'{rp}: holds the value of {k}')
        if SENSITIVE_PATH.search(rp):
            fails.append(f'{rp}: a vault-key, lane or decrypted-vault file in the published tree')
        vendor = rp.startswith('assets/vendor/') or rp.startswith('assets/components/')
        if not rp.endswith(TEXT_EXT) and not rp.endswith(('.js', '.css', '.py', '.sh', '.yml')):
            continue
        m = TAGS_BIDI.search(t)
        if m:
            fails.append(f'{rp}:{line_of(t, m.start())}: hidden character U+{ord(m.group(0)):04X} (Unicode tag or bidi control)')
        if rp.endswith(TEXT_EXT):
            m = ZERO_WIDTH.search(t)
            if m:
                fails.append(f'{rp}:{line_of(t, m.start())}: zero-width character U+{ord(m.group(0)):04X} in published text')
            if not vendor:
                for m in INJECTION.finditer(t):
                    if (rp, m.group(0).lower()) not in allowed:
                        fails.append(f'{rp}:{line_of(t, m.start())}: text addressed to a model: "{m.group(0)[:60]}" '
                                     '(if it is a quote the site needs, allow it in admin/security/injection-allowlist.json)')
        if rp.endswith('.html'):
            for m in JSON_SCRIPT.finditer(t):
                try:
                    json.loads(m.group(1))
                    ok = '<' not in m.group(1)
                except ValueError:
                    ok = False
                if not ok:
                    fails.append(f'{rp}:{line_of(t, m.start())}: a JSON script block that does not parse or holds "<" (closed early by its data?)')
            # every page carries its Content-Security-Policy (admin/build/csp.py), and it never lets inline or eval'd script run
            cm = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', t)
            if not cm:
                fails.append(f'{rp}: no Content-Security-Policy (admin/build/csp.py writes one into every page)')
            elif re.search(r"script-src[^;]*'unsafe-(inline|eval)'", cm.group(1)):
                fails.append(f'{rp}: its Content-Security-Policy lets inline or eval\'d script run')
            m = INLINE_HANDLER.search(JSON_SCRIPT.sub('', t))
            if m:
                fails.append(f'{rp}: an inline event-handler attribute ({m.group(0)[-40:]!r}): the build never writes one, so data did')
            m = BAD_SCHEME.search(t)
            if m:
                fails.append(f'{rp}:{line_of(t, m.start())}: {m.group(2)}: URL in {m.group(1)}')
    # Slugs become paths and attributes: one shape only.
    try:
        src = json.load(open(os.path.join(root, 'data', 'sources.json')))
        for s in (src['sources'] if isinstance(src, dict) else src):
            if not SLUG.fullmatch(str(s.get('slug', ''))):
                fails.append(f'data/sources.json: source slug {str(s.get("slug"))[:40]!r} is not [a-z0-9._-]')
    except (OSError, ValueError, KeyError):
        pass
    # The key register (data/keys.json) holds fingerprints and vault ids, never key material.
    kp = os.path.join(root, 'data', 'keys.json')
    if os.path.exists(kp):
        try:
            K = json.load(open(kp, encoding='utf-8'))
            FP = re.compile(r'sha256:[0-9a-f]{16}')
            for f in ('record', 'encryption'):
                if not FP.fullmatch(str(K['root'].get(f))):
                    fails.append(f'data/keys.json: root {f} is not a sha256:<16 hex> fingerprint')
            for a in K['agents']:
                if a.get('record') is not None and not FP.fullmatch(str(a['record'])):
                    fails.append(f'data/keys.json: agent {a.get("id")!r} record is not a fingerprint')
            for v in K['vaults']:
                if not re.fullmatch(r'[a-z0-9]{8}', str(v.get('id'))):
                    fails.append(f'data/keys.json: vault id {str(v.get("id"))[:20]!r} is not an 8-character vault id')
            def walk_keys(o, path=''):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if re.search(r'(vault_key|passphrase|private|secret|token|enum_key|access_key)', k, re.I):
                            fails.append(f'data/keys.json: field {path}{k} must not exist: this file never holds key material')
                        walk_keys(v, f'{path}{k}.')
                elif isinstance(o, list):
                    for x in o: walk_keys(x, path)
                elif isinstance(o, str) and (re.search(r'\bm1\.[A-Za-z0-9_-]{40,}|-----BEGIN', o) or re.search(r'[0-9a-f]{40,}', o)):
                    fails.append(f'data/keys.json: {path.rstrip(".")} holds what looks like key material or a sealed message')
            walk_keys(K)
        except (ValueError, KeyError, TypeError) as e:
            fails.append(f'data/keys.json: does not parse as the key register ({e})')
    # Messages between agents (data/messages/<to>/<id>.md): the sender in the front matter is the one in the file name,
    # no field is given twice, and nobody writes as the editor, who speaks to agents only in their own sessions.
    for p in sorted(__import__('glob').glob(os.path.join(root, 'data', 'messages', '*', '*.md'))):
        rp = os.path.relpath(p, root).replace(os.sep, '/')
        t = read_text(p) or ''
        m = re.match(r'---\n(.*?)\n---\n', t, re.S)
        if not m:
            fails.append(f'{rp}: a message with no front matter'); continue
        keys = [l.split(':', 1)[0].strip() for l in m.group(1).splitlines() if ':' in l]
        head = dict((k.strip(), v.strip()) for k, v in (l.split(':', 1) for l in m.group(1).splitlines() if ':' in l))
        dup = sorted({k for k in keys if keys.count(k) > 1})
        if dup:
            fails.append(f'{rp}: front matter gives {", ".join(dup)} more than once (a forged header)')
        parts = os.path.basename(p)[:-3].split('__')
        if len(parts) < 3 or head.get('from') != parts[1]:
            fails.append(f'{rp}: "from: {head.get("from")}" is not the sender in the file name')
        if head.get('from') in ('editor', 'dinis', 'dinis-cruz', 'root'):
            fails.append(f'{rp}: a message signed as "{head.get("from")}": the editor never writes to agents through this repository')
    # Nothing the build reads may be silently ignored by git: twice an ignore rule kept a file the site needed out of the
    # repository while it looked committed (SA-2026-017).
    try:
        ign = subprocess.run(['git', 'ls-files', '--others', '--ignored', '--exclude-standard', '--', 'data', 'admin/build', 'admin/content', 'assets'],
                             cwd=root, capture_output=True, text=True).stdout.split()
        for f in ign:
            if '__pycache__' not in f and not f.endswith('.pyc'):
                fails.append(f'{f}: ignored by .gitignore, but it is where the build reads from: commit it, or move it out of the tree')
    except OSError:
        pass
    # Workflows: every action pinned to a commit, never a tag a third party can move.
    wf = os.path.join(root, '.github', 'workflows')
    for f in sorted(os.listdir(wf)) if os.path.isdir(wf) else []:
        t = open(os.path.join(wf, f), encoding='utf-8').read()
        for m in re.finditer(r'uses:\s*([^\s#]+)', t):
            if not re.search(r'@[0-9a-f]{40}$', m.group(1)) and not m.group(1).startswith('./'):
                fails.append(f'.github/workflows/{f}:{line_of(t, m.start())}: {m.group(1)} is not pinned to a commit SHA')
        if re.search(r'pull_request_target|\$\{\{\s*github\.event\.(issue|comment|pull_request|head_commit|review)', t):
            fails.append(f'.github/workflows/{f}: untrusted event text or pull_request_target in a workflow')
    return fails


def staged_fails(root=ROOT):
    """The release tripwire: the paths and the added lines about to be committed."""
    fails, envs = [], env_secrets()
    names = subprocess.run(['git', 'diff', '--cached', '--name-only', '-z'], cwd=root, capture_output=True, text=True).stdout.split('\0')
    for n in filter(None, names):
        if SENSITIVE_PATH.search(n):
            fails.append(f'{n}: a vault-key, lane or decrypted-vault file is staged')
    diff = subprocess.run(['git', 'diff', '--cached', '--no-color', '-U0'], cwd=root, capture_output=True, text=True, errors='replace').stdout
    cur = None
    for line in diff.split('\n'):
        if line.startswith('+++ b/'):
            cur = line[6:]
        elif line.startswith('+') and not line.startswith('+++') and cur != 'admin/build/security_check.py':
            m = SECRET.search(line)
            if m:
                fails.append(f'{cur}: credential shape in an added line: {kind_of(m)}')
            for k, v in envs:
                if v in line:
                    fails.append(f'{cur}: an added line holds the value of {k}')
    # the secret part of any vault key held in a local clone under the repository
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != '.git']
        if os.path.basename(d) == 'local' and os.path.basename(os.path.dirname(d)) == '.sg_vault':
            for f in files:
                t = read_text(os.path.join(d, f)) or ''
                for k in set(re.findall(r'([0-9A-Za-z]{16,}):[a-z0-9]{8}', t)):
                    if k in diff:
                        fails.append(f'the secret part of a key held in {os.path.relpath(d, root)} is in the staged diff')
    return fails


def history_fails(root=ROOT):
    """Every commit on every branch, for credential shapes (the tree check only sees the present)."""
    out = subprocess.run(['git', 'log', '--all', '-p', '--no-color', '--format=commit %H'], cwd=root, capture_output=True, text=True, errors='replace').stdout
    fails, commit, cur, envs = [], '', '', env_secrets()
    for line in out.split('\n'):
        if line.startswith('commit '):
            commit = line[7:19]
        elif line.startswith('+++ b/'):
            cur = line[6:]
        elif line.startswith('+') and cur != 'admin/build/security_check.py':
            m = SECRET.search(line)
            if m:
                fails.append(f'history {commit} {cur}: credential shape: {kind_of(m)}')
            for k, v in envs:
                if v in line:
                    fails.append(f'history {commit} {cur}: holds the value of {k}')
    return sorted(set(fails))


def vault_report(path):
    """A read-only clone of a vault: what in it is addressed to a model or hidden from a person. Reported, never failed:
    a capture of a page that talks about prompt injection is evidence, not an attack; a person reads each hit."""
    hits = []
    for p in walk(path):
        if not p.endswith(TEXT_EXT):
            continue
        t = read_text(p) or ''
        rp = os.path.relpath(p, path)
        for m in INJECTION.finditer(t):
            hits.append(f'{rp}:{line_of(t, m.start())}: addressed to a model: {t[max(0, m.start() - 60):m.end() + 60]!r}'[:300])
        m = TAGS_BIDI.search(t)
        if m and '/x-' not in '/' + rp and 'x.com' not in rp:
            hits.append(f'{rp}:{line_of(t, m.start())}: hidden character U+{ord(m.group(0)):04X}')
        if SECRET.search(t):
            hits.append(f'{rp}: credential shape')
    return hits


def main(argv):
    if '--staged' in argv:
        f = staged_fails()
        for x in f:
            print('tripwire:', x)
        return 1 if f else 0
    fails = tree_fails()
    print(f'tree: {len(fails)} finding(s)')
    for x in fails:
        print('  FAIL', x)
    if '--history' in argv:
        h = history_fails()
        print(f'history: {len(h)} finding(s)')
        for x in h:
            print('  FAIL', x)
        fails += h
    for i, a in enumerate(argv):
        if a == '--vault' and i + 1 < len(argv):
            v = vault_report(argv[i + 1])
            print(f'vault {argv[i + 1]}: {len(v)} item(s) for a person to read')
            for x in v[:200]:
                print('  READ', x)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
