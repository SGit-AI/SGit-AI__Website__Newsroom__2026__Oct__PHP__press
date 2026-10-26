#!/usr/bin/env python3
"""The board and the issues vault (Issues-FS-lite), in both directions.

The issues vault (zjruy9vk) holds one queue per member: issues/<member>/{open,blocked,done}/NNN-slug.md, a
markdown file with YAML front-matter per task. Each member writes only inside its own folder; work is asked
for by mail and the owner opens it. Members are the ids in data/team.json; board owners map to them through
team.json's board_owners.

  seed   --vault <clone>   write a card for every board row that has none yet, in its owner's queue. Run once
                           by the conductor to move the board into the vault; a seeded card says accepted: no
                           until its owner takes it, because the owner did not open it.
  import --vault <clone>   read every card and write the board in data/admin.json from them: status from the
                           folder (open, blocked as waiting, done), owner from the folder, title and version
                           from the front-matter. Rows with no card are kept as they are.

Standard library only. Neither direction touches the network: pull and push the clone with sgit.
"""
import argparse, json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STATES = {'open': 'open', 'waiting': 'blocked', 'done': 'done'}
BACK = {'open': 'open', 'blocked': 'waiting', 'done': 'done'}

def load(name):
    return json.load(open(os.path.join(ROOT, 'data', name + '.json'), encoding='utf-8'))

def slug(t, n=6):
    words = re.findall(r'[a-z0-9]+', t.lower())
    return '-'.join(words[:n]) or 'task'

def q(s):
    return json.dumps(s, ensure_ascii=False)

def card(b, member, by):
    fm = [('board', q(b['id'])), ('title', q(b['title'])), ('created', '2026-10-22'), ('source', q('data/admin.json board ' + b['id'])),
          ('priority', 'normal'), ('owner', member), ('kind', 'need' if member in by['humans'] else 'task')]
    if b['status'] == 'done':
        fm.append(('accepted', 'yes'))
    else:
        fm.append(('accepted', 'no'))
    if b.get('version'): fm.append(('version', q(b['version'])))
    if b['status'] == 'waiting': fm.append(('blocked_on', q(b.get('note') or 'see the note')))
    body = f"# {b['title']}\n\n"
    if b.get('note'): body += f"## Note\n\n{b['note']}\n\n"
    body += ("## Seeded\n\nMoved from the site's board by the conductor on 22 October 2026. The owner did not open this card; "
             "taking it means setting accepted: yes and writing below how you will approach it.\n")
    return '---\n' + ''.join(f'{k}: {v}\n' for k, v in fm) + '---\n' + body

def parse(path):
    text = open(path, encoding='utf-8').read()
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    fm = {}
    for line in (m.group(1).splitlines() if m else []):
        k, _, v = line.partition(':')
        v = v.strip()
        try: v = json.loads(v)
        except ValueError: pass
        fm[k.strip()] = v
    return fm

def cards(vault):
    base = os.path.join(vault, 'issues')
    for member in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        for state in ('open', 'blocked', 'done'):
            d = os.path.join(base, member, state)
            if not os.path.isdir(d): continue
            for fn in sorted(os.listdir(d)):
                if fn.endswith('.md'):
                    yield member, state, fn, parse(os.path.join(d, fn))

def seed(vault):
    team, admin = load('team'), load('admin')
    owners = team['board_owners']
    by = {'humans': {m['id'] for m in team['members'] if m['kind'] == 'human'}}
    have = {(c[3].get('board'), c[0]) for c in cards(vault)}  # board ids are not unique (two rows are 013), so a card is its id and its owner
    made = 0
    for m in team['members']:
        for state in ('open', 'blocked', 'done'):
            os.makedirs(os.path.join(vault, 'issues', m['id'], state), exist_ok=True)
            keep = os.path.join(vault, 'issues', m['id'], state, '.keep')
            if not os.path.exists(keep): open(keep, 'w').close()
    for b in admin['board']:
        member = owners.get(b['owner'])
        if not member: sys.exit(f"board {b['id']}: owner {b['owner']!r} is not in team.json board_owners")
        if (b['id'], member) in have: continue
        path = os.path.join(vault, 'issues', member, STATES[b['status']], f"{b['id']}-{slug(b['title'])}.md")
        open(path, 'w', encoding='utf-8').write(card(b, member, by))
        made += 1
    print(f'seeded {made} cards; {len(have)} were already in the vault')

def imp(vault):
    p = os.path.join(ROOT, 'data', 'admin.json')
    admin = json.load(open(p, encoding='utf-8'))
    owners = load('team')['board_owners']
    rows = {(b['id'], owners.get(b['owner'])): i for i, b in enumerate(admin['board'])}
    changed = 0
    for member, state, fn, fm in cards(vault):
        bid = fm.get('board') or f"{member}/{fn[:-3]}"
        i = rows.get((bid, member))
        row = admin['board'][i] if i is not None else {'id': bid, 'owner': member}
        new = dict(row, title=fm.get('title', row.get('title', fn)), status=BACK[state])
        if fm.get('version'): new['version'] = fm['version']
        if new != row:
            changed += 1
            if i is None: rows[(bid, member)] = len(admin['board']); admin['board'].append(new)
            else: admin['board'][i] = new
    json.dump(admin, open(p, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); open(p, 'a').write('\n')
    print(f'board: {changed} rows changed from the vault')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['seed', 'import']); ap.add_argument('--vault', required=True)
    a = ap.parse_args()
    (seed if a.cmd == 'seed' else imp)(os.path.abspath(a.vault))

if __name__ == '__main__':
    main()
