"""Data-flow diagrams for the application security pages, from one spec: an inline SVG for the page and Mermaid
source for its markdown twin. Kept by security@php.newsroom. Standard library only, deterministic, no script.

A spec (data/appsec.json, "diagrams"):
  {"id", "title", "caption",
   "zones": [{"id", "label", "kind": hostile|public|team|reader|service|root}],   left to right, in this order
   "nodes": [{"id", "label", "zone"}],                                            top to bottom within a zone
   "edges": [{"from", "to", "label", "kind": data|untrusted|secret|control}]}
Every label is escaped here; nothing in a spec becomes markup.
"""
from html import escape as E

ZONE_FILL = {'hostile': '#d64545', 'public': '#d99a1e', 'team': '#3b7dd8', 'reader': '#2f9e6b', 'service': '#8a8f98', 'root': '#7b5cc4'}
EDGE = {'data': ('#6b7280', ''), 'untrusted': ('#d64545', '6 4'), 'secret': ('#7b5cc4', '2 3'), 'control': ('#3b7dd8', '')}
COL_W, GAP, NODE_W, NODE_H, ROW, TOP = 190, 64, 160, 50, 74, 56


def wrap(text, width=22):
    words, lines, cur = str(text).split(), [], ''
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur: lines.append(cur)
    return lines[:3]


def svg(spec):
    zones = spec['zones']
    zi = {z['id']: i for i, z in enumerate(zones)}
    rows, pos = {}, {}
    for n in spec['nodes']:
        c = zi[n['zone']]; r = rows.get(c, 0); rows[c] = r + 1
        x = 16 + c * (COL_W + GAP) + (COL_W - NODE_W) / 2
        pos[n['id']] = (x, TOP + r * ROW, c)
    height = TOP + max(rows.values()) * ROW + 10
    width = 16 + len(zones) * (COL_W + GAP) - GAP + 16
    out = [f'<svg class="flow" viewBox="0 0 {width} {height}" width="100%" style="max-width:{max(width, 760)}px;display:block" role="img" aria-labelledby="{E(spec["id"])}-t" xmlns="http://www.w3.org/2000/svg">',
           f'<title id="{E(spec["id"])}-t">{E(spec["title"])}</title>', '<defs>']
    for k, (col, _) in EDGE.items():
        out.append(f'<marker id="{E(spec["id"])}-a-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
    out.append('</defs>')
    for i, z in enumerate(zones):
        x = 16 + i * (COL_W + GAP); col = ZONE_FILL.get(z.get('kind'), '#8a8f98')
        out.append(f'<rect x="{x}" y="8" width="{COL_W}" height="{height - 14}" rx="10" fill="{col}" fill-opacity="0.10" stroke="{col}" stroke-opacity="0.55"/>')
        for j, line in enumerate(wrap(z['label'], 26)[:2]):
            out.append(f'<text x="{x + COL_W / 2}" y="{26 + j * 14}" text-anchor="middle" font-size="12" font-weight="700" fill="{col}">{E(line)}</text>')
    for e in spec['edges']:
        (x1, y1, c1), (x2, y2, c2) = pos[e['from']], pos[e['to']]
        col, dash = EDGE.get(e.get('kind', 'data'), EDGE['data'])
        if c2 > c1:   sx, sy, tx, ty = x1 + NODE_W, y1 + NODE_H / 2, x2, y2 + NODE_H / 2
        elif c2 < c1: sx, sy, tx, ty = x1, y1 + NODE_H / 2, x2 + NODE_W, y2 + NODE_H / 2
        else:         sx, sy, tx, ty = x1 + NODE_W / 2 + 18, (y1 + NODE_H) if y2 > y1 else y1, x2 + NODE_W / 2 + 18, y2 if y2 > y1 else y2 + NODE_H
        if c1 == c2:
            d = f'M{sx},{sy} C{sx + 40},{(sy + ty) / 2} {tx + 40},{(sy + ty) / 2} {tx},{ty}'
        else:
            mx = (sx + tx) / 2
            d = f'M{sx},{sy} C{mx},{sy} {mx},{ty} {tx},{ty}'
        out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.6"{f" stroke-dasharray={chr(34)}{dash}{chr(34)}" if dash else ""} marker-end="url(#{E(spec["id"])}-a-{E(e.get("kind", "data"))})"/>')
        if e.get('label'):
            lx, ly = (sx + tx) / 2, (sy + ty) / 2 - 4
            lab = str(e['label'])[:28]
            out.append(f'<rect x="{lx - len(lab) * 3.1 - 4}" y="{ly - 10}" width="{len(lab) * 6.2 + 8}" height="14" rx="3" fill="Canvas" fill-opacity="0.92"/>'
                       f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="10" fill="{col}">{E(lab)}</text>')
    for n in spec['nodes']:
        x, y, c = pos[n['id']]
        lines = wrap(n['label'])
        out.append(f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="7" fill="Canvas" stroke="currentColor" stroke-opacity="0.6"/>')
        for j, line in enumerate(lines):
            out.append(f'<text x="{x + NODE_W / 2}" y="{y + NODE_H / 2 + (j - (len(lines) - 1) / 2) * 13 + 4}" text-anchor="middle" font-size="11.5" fill="currentColor">{E(line)}</text>')
    out.append('</svg>')
    return ''.join(out)


def mermaid(spec):
    ident = lambda x: ''.join(ch if ch.isalnum() else '_' for ch in str(x))
    q = lambda t: str(t).replace('"', "'").replace('\n', ' ')
    lines = ['flowchart LR']
    for z in spec['zones']:
        lines.append(f'  subgraph {ident("z_" + z["id"])}["{q(z["label"])}"]')
        lines += [f'    {ident(n["id"])}["{q(n["label"])}"]' for n in spec['nodes'] if n['zone'] == z['id']]
        lines.append('  end')
    arrow = {'untrusted': '-.->', 'secret': '-.->', 'control': '==>', 'data': '-->'}
    for e in spec['edges']:
        a = arrow.get(e.get('kind', 'data'), '-->')
        lines.append(f'  {ident(e["from"])} {a}' + (f'|"{q(e["label"])}"|' if e.get('label') else '') + f' {ident(e["to"])}')
    return '\n'.join(lines)


def legend():
    items = [('untrusted', 'untrusted data (anyone can write it)'), ('secret', 'a secret or key'), ('control', 'an instruction or a release'), ('data', 'data')]
    return '<p class="small flow-legend">' + ' &middot; '.join(
        f'<svg width="34" height="10" aria-hidden="true"><line x1="1" y1="5" x2="33" y2="5" stroke="{EDGE[k][0]}" stroke-width="2"'
        + (f' stroke-dasharray="{EDGE[k][1]}"' if EDGE[k][1] else '') + f'/></svg> {E(t)}' for k, t in items) + '</p>'
