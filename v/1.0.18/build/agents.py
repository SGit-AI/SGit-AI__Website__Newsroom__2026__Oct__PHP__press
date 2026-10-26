#!/usr/bin/env python3
"""The members' scopes, checked. Kept by librarian@php.newsroom; brief: admin/content/briefs/2026-10-22__brief__every-agent-a-folder-a-policy-and-a-round.md.

Every member of the newsroom has a folder in admin/content/agents/<id>/ with a policy.json that says which files it
writes (exclusive), which shared files it appends to, which pages it owns and which vaults it holds. This file reads
them all and answers four questions, without judging:

  overlaps                 do two members claim the same file or page?           (must be none)
  unowned                  which source files does nobody claim?                 (should be none)
  check --agent X [RANGE]  did a round write outside its member's scope?         (the debrief records it)
  delta X                  what can a session of X do that its mandate did not ask for? (computed, never written)

and runs the end-of-round reminder for Claude Code (stop-hook). Standard library only; the build imports it.
Usage: python3 admin/build/agents.py report | overlaps | unowned | check --agent <id> [<range>] | delta <id> | stop-hook
"""
import functools, json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
AGENTS = os.path.join(ROOT, 'admin', 'content', 'agents')
GRANT = os.path.join(ROOT, 'admin', 'security', 'abp', 'GRANT.md')

def load_policies():
    out = {}
    for d in sorted(os.listdir(AGENTS)) if os.path.isdir(AGENTS) else []:
        p = os.path.join(AGENTS, d, 'policy.json')
        if os.path.isfile(p):
            with open(p, encoding='utf-8') as f:
                out[d] = json.load(f)
    return out

def load_status(agent):
    p = os.path.join(AGENTS, agent, 'status.json')
    if not os.path.isfile(p):
        return None
    with open(p, encoding='utf-8') as f:
        return json.load(f)

@functools.lru_cache(maxsize=None)
def glob_re(pattern):
    """A path glob: ** crosses folders, * and ? do not."""
    out, i = '', 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith('**', i):
            out += '.*'; i += 2
            if pattern.startswith('/', i): i += 1; out = out[:-2] + '(?:.*/)?'
            continue
        out += '[^/]*' if c == '*' else '[^/]' if c == '?' else re.escape(c)
        i += 1
    return re.compile('^' + out + '$')

def match(pattern, path):
    return bool(glob_re(pattern).match(path))

def append_target(entry):
    """'data/admin.json#board: ...' -> 'data/admin.json'; 'admin/content/briefs/: ...' -> 'admin/content/briefs/**'."""
    head = re.split(r'[#:]', entry, maxsplit=1)[0].strip()
    return head + '**' if head.endswith('/') else head

@functools.lru_cache(maxsize=None)
def git(*args):
    try:
        return subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True, check=True).stdout
    except Exception:
        return ''

def outputs():
    p = os.path.join(ROOT, 'admin', 'build', 'outputs.txt')
    return set(open(p, encoding='utf-8').read().split()) if os.path.isfile(p) else set()

def source_files():
    """Tracked files the build does not generate: the files somebody has to own."""
    gen = outputs() | {'admin/build/outputs.txt'}
    return sorted(f for f in git('ls-files').splitlines() if f and f not in gen)

def pattern_overlap(a, b, universe):
    if a == b:
        return [a]
    hits = [f for f in universe if match(a, f) and match(b, f)]
    if hits:
        return hits
    # two patterns that could meet on a file that does not exist yet: one is a literal the other matches
    for x, y in ((a, b), (b, a)):
        if '*' not in x and '?' not in x and match(y, x):
            return [x]
    return []

def overlaps(policies=None, pages=None):
    """Pairs of members claiming the same file or page. pages=None checks against the pages the last build wrote
    (admin/build/outputs.txt), for the gate and the CLI; the build passes pages=[] so its own output never depends on
    the previous run's list (then two page patterns overlap only if one names a page the other matches)."""
    P = policies or load_policies()
    files = source_files()
    pages = sorted(f for f in outputs() if f.endswith('.html')) if pages is None else pages
    found = []
    ids = sorted(P)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            for kind, universe in (('writes', files), ('pages', pages)):
                for pa in P[a]['scope'][kind]:
                    for pb in P[b]['scope'][kind]:
                        hit = pattern_overlap(pa, pb, universe)
                        if hit:
                            found.append({'kind': kind, 'a': a, 'b': b, 'pattern_a': pa, 'pattern_b': pb, 'files': hit[:5], 'count': len(hit)})
    return found

def owner_of(path, P):
    return sorted(a for a, p in P.items() if any(match(w, path) for w in p['scope']['writes']))

def unowned(policies=None):
    P = policies or load_policies()
    return [f for f in source_files() if not owner_of(f, P)]

def dangling_appends(policies=None):
    """Every shared file a member appends to must have one owner who writes it."""
    P = policies or load_policies()
    out = []
    for a, p in sorted(P.items()):
        for e in p['scope']['appends']:
            t = append_target(e)
            probe = t[:-2] + 'x' if t.endswith('**') else t
            if not any(match(w, probe) for o, q in P.items() for w in q['scope']['writes']):
                out.append({'agent': a, 'append': e, 'target': t})
    return out

def grant_rows():
    """The measured grant: one row per capability in GRANT.md's table, with its barrier symbol."""
    rows = []
    if not os.path.isfile(GRANT):
        return rows
    for line in open(GRANT, encoding='utf-8'):
        m = re.match(r'^\|\s*`([a-z-]+\.[a-z-]+\.[a-z-]+)`\s*\|(.*)$', line)
        if m:
            cells = [c.strip() for c in m.group(2).split('|')]
            barrier = next((s for s in ('●', '◉', '◐', '○') if s in (cells[1] if len(cells) > 1 else '')), '?')
            rows.append({'capability': m.group(1), 'what': cells[0], 'barrier': barrier, 'barrier_text': cells[1] if len(cells) > 1 else ''})
    return rows

def delta(agent, policies=None):
    """Granted and not wanted (excess), and the excess with nothing that counts as a control in the way (unbounded)."""
    P = policies or load_policies()
    p = P[agent]
    if not p.get('grant'):
        return None
    G = grant_rows()
    wanted = {w['capability'] for w in p['mandate']['wanted']}
    excess = [r for r in G if r['capability'] not in wanted]
    return {'grant': len(G), 'wanted': len(wanted), 'shortfall': sorted(wanted - {r['capability'] for r in G}),
            'excess': [r['capability'] for r in excess], 'unbounded': [r['capability'] for r in excess if r['barrier'] in ('●', '◉', '◐')]}

def changed(rng):
    files = set(git('diff', '--name-only', rng).split()) if rng else set()
    files |= set(git('diff', '--name-only', 'HEAD').split())
    files |= set(l[3:] for l in git('status', '--porcelain', '-uall').splitlines() if l.startswith('??'))
    return sorted(files)

# Written by admin/build/release.sh on every member's release (the version bump), so never a member's own change.
RELEASE_FILES = {'VERSION', 'data/versions.json'}

def check(agent, rng='origin/dev...HEAD', policies=None):
    P = policies or load_policies()
    p = P[agent]
    gen = outputs() | {'admin/build/outputs.txt'} | RELEASE_FILES
    res = {'agent': agent, 'range': rng, 'writes': [], 'appends': [], 'generated': [], 'outside': []}
    for f in changed(rng):
        if f in gen:
            res['generated'].append(f)
        elif any(match(w, f) for w in p['scope']['writes']):
            res['writes'].append(f)
        elif any(match(append_target(e), f) for e in p['scope']['appends']):
            res['appends'].append(f)
        else:
            res['outside'].append({'file': f, 'owner': owner_of(f, P)})
    return res

def stop_hook():
    """Claude Code Stop hook: a round that committed work and wrote no debrief is reminded once (exit 2), never looped."""
    try:
        data = json.loads(sys.stdin.read() or '{}')
    except Exception:
        data = {}
    if data.get('stop_hook_active'):
        return 0
    branch = git('rev-parse', '--abbrev-ref', 'HEAD').strip()
    if not branch or branch in ('dev', 'main', 'HEAD') or not git('rev-parse', '--verify', '-q', 'origin/dev').strip():
        return 0
    ahead = git('log', '--no-merges', '--format=%H', 'origin/dev..HEAD').split()
    if not ahead:
        return 0
    if any(re.match(r'^admin/content/agents/[^/]+/debriefs/[^/]+\.md$', f) for f in changed('origin/dev...HEAD')):
        return 0
    sys.stderr.write(
        f'This branch has {len(ahead)} commit(s) beyond origin/dev and no debrief. Before you stop, close the round '
        '(admin/content/agents/README.md, "Every round"): write admin/content/agents/<you>/debriefs/<date>__<slug>.md with '
        'screenshots, update status.json (done, tasks, next, tokens, policy misses, asks), run '
        '`python3 admin/build/agents.py check --agent <you>`, commit and push to your branch. If this session is not one of '
        'the members in admin/content/agents/, say so to the editor instead.\n')
    return 2

def report():
    P = load_policies()
    return {'members': len(P), 'agents': sum(1 for p in P.values() if p['kind'] == 'agent'),
            'agreed': sum(1 for p in P.values() if p['status'] == 'agreed'),
            'overlaps': overlaps(P), 'unowned': unowned(P), 'dangling_appends': dangling_appends(P),
            'deltas': {a: delta(a, P) for a in sorted(P) if P[a].get('grant')}}

def main(argv):
    if not argv:
        print(__doc__); return 0
    cmd = argv[0]
    if cmd == 'stop-hook':
        return stop_hook()
    if cmd == 'report':
        print(json.dumps(report(), indent=1, ensure_ascii=False)); return 0
    if cmd == 'overlaps':
        o = overlaps(); print(json.dumps(o, indent=1)); return 1 if o else 0
    if cmd == 'unowned':
        u = unowned(); print('\n'.join(u)); return 1 if u else 0
    if cmd == 'delta':
        print(json.dumps(delta(argv[1]), indent=1)); return 0
    if cmd == 'check':
        a = argv[argv.index('--agent') + 1]
        rest = [x for x in argv[1:] if x not in ('--agent', a)]
        r = check(a, rest[0] if rest else 'origin/dev...HEAD')
        print(json.dumps(r, indent=1)); return 1 if r['outside'] else 0
    print(__doc__); return 2

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
