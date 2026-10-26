// php.oct.2026.newsroom.sgit.ai: explore the risk graph (/grc/explore/). The brief: admin/content/briefs/
// 2026-10-23__brief__the-risk-graph-as-a-tool.md, steps 1 and 4 (CI-002.3 and CI-002.6).
//
// Two ways in, one component, on data/grc-graph.json and nothing else:
//   Focus   start at any node (a CVE, a risk, a stakeholder, a file, a test, a control): its neighbours grouped by
//           verb; open any neighbour to see its own; the path back to the start always shown. The address carries the
//           start and every opened node (#focus=<id>&open=<id>,<id>), so a view can be shared.
//   Impact  start at code, a test or a fix and climb: the fixes it realises, the flaws they fix, the weaknesses those
//           give rise to, the risks above them, and the controls, stakeholders, treatments and stories of each risk,
//           every one with the path that reaches it (#impact=<id>).
// Every edge says how it is known (basis): read from a capture, from the fix commit, inferred by an agent, or
// confirmed by a person. Inferred edges are dashed, and a switch hides them. Everything is set as text.
(function () {
  'use strict';
  var box = document.getElementById('explore');
  if (!box) return;
  var root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length);   // only ever '../' repeated: the depth, never page text
  var G = null, N = {}, OUT = {}, IN = {};
  var FAMILY = { stakeholder: 1, role: 1, member: 1, briefing: 1, risk: 2, treatment: 2, weakness: 3, vulnerability: 3, remediation: 4, code: 4, test: 4, control: 5, claim: 6, source: 6, story: 6, page: 6 };
  var FAMILY_NAME = { 1: 'people and roles', 2: 'risks and treatments', 3: 'weaknesses and flaws', 4: 'fixes, code and tests', 5: 'controls', 6: 'evidence and stories' };
  var BASIS = { source: 'read from a capture', code: 'read from the fix commit', inferred: 'inferred by an agent, not yet checked', confirmed: 'checked by a person' };
  // Climbing from code to what it puts at stake: [direction, verb] per kind. "in" follows an edge that points here.
  var UP = {
    code: [['in', 'realised_in'], ['in', 'located_in']],
    test: [['out', 'tests']],
    remediation: [['in', 'fixed_by']],
    vulnerability: [['in', 'arises_from'], ['in', 'concerns']],
    weakness: [['in', 'arises_from']],
    risk: [['out', 'part_of'], ['out', 'governed_by'], ['out', 'owned_by'], ['out', 'borne_by'], ['out', 'treated_by'], ['out', 'raised_by'], ['out', 'informed_by'], ['out', 'regulated_by'], ['out', 'protected_by'], ['out', 'told_in'], ['out', 'tracked_by']],
    stakeholder: [['out', 'part_of']], role: [['out', 'part_of']]
  };
  var IMPACT_ORDER = ['remediation', 'vulnerability', 'weakness', 'risk', 'control', 'stakeholder', 'role', 'treatment', 'story', 'member'];
  var S = { mode: 'focus', focus: null, open: [], hide: false };

  function el(tag, attrs) {
    var e = document.createElement(tag), k, i;
    attrs = attrs || {};
    for (k in attrs) {
      if (!Object.prototype.hasOwnProperty.call(attrs, k) || attrs[k] == null || attrs[k] === false) continue;
      if (k === 'class') e.className = attrs[k]; else if (k === 'text') e.textContent = attrs[k];
      else if (k.slice(0, 2) === 'on') e.addEventListener(k.slice(2), attrs[k]); else e.setAttribute(k, attrs[k]);
    }
    for (i = 2; i < arguments.length; i++) add(e, arguments[i]);
    return e;
  }
  function add(e, c) { if (c == null || c === false) return; if (Array.isArray(c)) c.forEach(function (x) { add(e, x); }); else e.appendChild(c.nodeType ? c : document.createTextNode(String(c))); }
  function svg(tag, attrs, text) { var e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (var k in attrs) if (attrs[k] != null) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = String(text); return e; }
  function href(n) { return /^https:\/\//.test(n.href || '') ? n.href : root + String(n.href || '').replace(/^\/+/, ''); }
  function nodeLink(n) { return el('a', { href: href(n), text: 'its page', rel: /^https:/.test(n.href || '') ? 'noopener' : null }); }
  function basisLink(b) {
    if (!b) return null;
    var t = BASIS[b.kind] || b.kind, a;
    if (b.kind === 'source') a = el('a', { href: root + 'sources/' + b.ref + '/index.html', text: b.ref });
    else if (b.kind === 'code') a = el('a', { href: 'https://github.com/php/php-src/commit/' + b.ref, rel: 'noopener', text: b.ref });
    else a = el('a', { href: root + 'team/' + b.ref + '/index.html', text: b.ref });
    return el('span', { class: 'gx-basis gx-b-' + b.kind }, t + ': ', a, b.note ? ' (' + b.note + ')' : '');
  }
  function kindPill(n) { return el('span', { class: 'gx-k gx-f' + (FAMILY[n.kind] || 6), text: n.kind }); }
  function plural(k, n) { return n === 1 ? k : /y$/.test(k) ? k.slice(0, -1) + 'ies' : /s$/.test(k) ? k + 'es' : k + 's'; }
  function short(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; }

  // ── the address ───────────────────────────────────────────────────────────
  function readHash() {
    var h = {}; location.hash.replace(/^#/, '').split('&').forEach(function (kv) { var p = kv.split('='); if (p[0]) h[p[0]] = decodeURIComponent(p[1] || ''); });
    if (h.impact && N[h.impact]) { S.mode = 'impact'; S.focus = h.impact; S.open = []; }
    else if (h.focus && N[h.focus]) { S.mode = 'focus'; S.focus = h.focus; S.open = (h.open || '').split(',').filter(function (x) { return N[x] && x !== h.focus; }); }
    S.hide = h.hide === 'inferred';
  }
  function writeHash() {
    var parts = [];
    if (S.mode === 'impact') parts.push('impact=' + encodeURIComponent(S.focus));
    else { parts.push('focus=' + encodeURIComponent(S.focus)); if (S.open.length) parts.push('open=' + S.open.map(encodeURIComponent).join(',')); }
    if (S.hide) parts.push('hide=inferred');
    history.replaceState(null, '', '#' + parts.join('&'));
  }
  function go(mode, id, keepOpen) { S.mode = mode; S.focus = id; if (!keepOpen) S.open = []; writeHash(); draw(); window.scrollTo(0, box.offsetTop - 10); }

  // ── neighbours: grouped by the verb read from this node ────────────────────
  function visible(e) { return !(S.hide && e.basis && e.basis.kind === 'inferred'); }
  function neighbours(id) {
    var groups = {};
    (OUT[id] || []).filter(visible).forEach(function (e) { (groups[e.rel] = groups[e.rel] || []).push({ id: e.to, e: e }); });
    (IN[id] || []).filter(visible).forEach(function (e) { (groups[e.inverse] = groups[e.inverse] || []).push({ id: e.from, e: e }); });
    return Object.keys(groups).sort(function (a, b) { return groups[b].length - groups[a].length || (a < b ? -1 : 1); }).map(function (v) { return [v, groups[v]]; });
  }
  // The tree of what is open: each opened node hangs under the first open node it touches, back to the start.
  function tree() {
    var parent = {}, order = [S.focus], seen = {};
    seen[S.focus] = 1;
    var queue = [S.focus];
    while (queue.length) {
      var x = queue.shift();
      neighbours(x).forEach(function (g) { g[1].forEach(function (n) {
        if (!seen[n.id] && S.open.indexOf(n.id) >= 0) { seen[n.id] = 1; parent[n.id] = { from: x, e: n.e }; order.push(n.id); queue.push(n.id); }
      }); });
    }
    return { parent: parent, order: order };
  }
  function pathTo(T, id) { var p = [id]; while (T.parent[p[0]]) p.unshift(T.parent[p[0]].from); return p; }

  // ── focus ─────────────────────────────────────────────────────────────────
  function focusView() {
    var T = tree(), out = el('div', { class: 'gx-focus' });
    out.appendChild(picture(T));
    T.order.forEach(function (id) {
      var n = N[id], card = el('section', { class: 'gx-card' + (id === S.focus ? ' gx-start' : ''), id: 'gx-' + id.replace(/[^a-z0-9]/gi, '-') });
      var path = pathTo(T, id);
      if (path.length > 1) card.appendChild(el('p', { class: 'gx-path' }, path.map(function (p, i) {
        var bits = [];
        if (i) { var pe = T.parent[p].e; bits.push(el('span', { class: 'gx-verb' + (pe.basis && pe.basis.kind === 'inferred' ? ' gx-inf' : ''), text: ' ' + (pe.from === T.parent[p].from ? pe.rel : pe.inverse).replace(/_/g, ' ') + ' ' })); }
        bits.push(el('button', { class: 'gx-crumb', type: 'button', text: short(N[p].label, 40), onclick: function () { go('focus', p); } }));
        return bits;
      })));
      card.appendChild(el('h3', null, kindPill(n), ' ', n.label));
      var acts = el('p', { class: 'gx-acts' }, nodeLink(n));
      if (id !== S.focus) acts.appendChild(el('button', { class: 'rs-b', type: 'button', text: 'Start here', onclick: function () { go('focus', id); } }));
      if (UP[n.kind]) acts.appendChild(el('button', { class: 'rs-b', type: 'button', text: 'What it puts at stake', onclick: function () { go('impact', id); } }));
      if (id !== S.focus) acts.appendChild(el('button', { class: 'rs-b', type: 'button', text: 'Close', onclick: function () { S.open = S.open.filter(function (x) { return x !== id; }); writeHash(); draw(); } }));
      card.appendChild(acts);
      neighbours(id).forEach(function (g) {
        var verb = g[0], list = g[1], more = list.length > 14;
        var row = el('div', { class: 'gx-group' }, el('span', { class: 'gx-gv', text: verb.replace(/_/g, ' ') + ' (' + list.length + ')' }));
        var chips = el('span', { class: 'gx-chips' });
        list.slice(0, more ? 12 : list.length).forEach(function (x) { chips.appendChild(chip(x, T)); });
        if (more) chips.appendChild(el('button', { class: 'gx-more', type: 'button', text: '+' + (list.length - 12) + ' more', onclick: function (ev) {
          ev.target.remove(); list.slice(12).forEach(function (x) { chips.appendChild(chip(x, T)); });
        } }));
        row.appendChild(chips);
        card.appendChild(row);
      });
      out.appendChild(card);
    });
    return out;
  }
  function chip(x, T) {
    var n = N[x.id], isOpen = x.id === S.focus || S.open.indexOf(x.id) >= 0;
    var b = el('button', { type: 'button', class: 'gx-chip gx-f' + (FAMILY[n.kind] || 6) + (x.e.basis && x.e.basis.kind === 'inferred' ? ' gx-inf' : '') + (isOpen ? ' gx-open' : ''),
                           title: n.kind + ': ' + n.label + '\n' + (BASIS[x.e.basis && x.e.basis.kind] || '') + (x.e.basis && x.e.basis.note ? ' (' + x.e.basis.note + ')' : ''), text: short(n.label, 46) });
    b.addEventListener('click', function () {
      if (isOpen) { var t = document.getElementById('gx-' + x.id.replace(/[^a-z0-9]/gi, '-')); if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
      S.open.push(x.id); writeHash(); draw();
      var t2 = document.getElementById('gx-' + x.id.replace(/[^a-z0-9]/gi, '-')); if (t2) t2.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    var w = el('span', { class: 'gx-cw' }, b);
    w.appendChild(el('span', { class: 'gx-why' }, basisLink(x.e.basis)));
    return w;
  }
  // The open part of the graph, drawn: the start on the left, each opened node one column further per step, and
  // every edge between visible nodes (dashed when inferred). Click a node to bring its card into view.
  function picture(T) {
    var depth = {}, cols = [];
    T.order.forEach(function (id) { var d = T.parent[id] ? depth[T.parent[id].from] + 1 : 0; depth[id] = d; (cols[d] = cols[d] || []).push(id); });
    // the neighbours of the last opened node, as a faint last column, so the next step is visible
    var lastOpen = T.order[T.order.length - 1], ghosts = [];
    neighbours(lastOpen).forEach(function (g) { g[1].forEach(function (x) { if (depth[x.id] == null && ghosts.indexOf(x.id) < 0 && ghosts.length < 18) ghosts.push(x.id); }); });
    var nc = cols.length + (ghosts.length ? 1 : 0), W = Math.max(640, Math.min(1100, 230 * nc)), colW = W / Math.max(1, nc);
    var maxRows = Math.max.apply(null, cols.map(function (c) { return c.length; }).concat([ghosts.length, 1]));
    var H = Math.max(70, 34 * maxRows + 26), pos = {};
    cols.forEach(function (c, i) { c.forEach(function (id, j) { pos[id] = { x: 14 + i * colW, y: 20 + (j + 0.5) * (H - 30) / c.length }; }); });
    ghosts.forEach(function (id, j) { pos[id] = { x: 14 + cols.length * colW, y: 20 + (j + 0.5) * (H - 30) / ghosts.length, ghost: true }; });
    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, class: 'gx-svg', role: 'img', 'aria-label': 'The open part of the risk graph' });
    var ids = Object.keys(pos);
    G.edges.forEach(function (e) {
      if (!pos[e.from] || !pos[e.to] || !visible(e)) return;
      if ((pos[e.from].ghost && pos[e.to].ghost)) return;
      if ((pos[e.from].ghost || pos[e.to].ghost) && e.from !== lastOpen && e.to !== lastOpen) return;
      var a = pos[e.from], b = pos[e.to], x1 = a.x + colW * 0.72, x2 = b.x;
      if (a.x > b.x) { a = pos[e.to]; b = pos[e.from]; x1 = a.x + colW * 0.72; x2 = b.x; }
      var mx = (x1 + x2) / 2;
      s.appendChild(svg('path', { d: 'M' + x1 + ',' + a.y + ' C' + mx + ',' + a.y + ' ' + mx + ',' + b.y + ' ' + x2 + ',' + b.y, class: 'gx-e' + (e.basis && e.basis.kind === 'inferred' ? ' gx-e-inf' : '') + (pos[e.from].ghost || pos[e.to].ghost ? ' gx-e-ghost' : '') }));
    });
    ids.forEach(function (id) {
      var p = pos[id], n = N[id];
      var g = svg('g', { class: 'gx-n' + (p.ghost ? ' gx-n-ghost' : '') + (id === S.focus ? ' gx-n-start' : ''), tabindex: '0', role: 'button' });
      g.appendChild(svg('circle', { cx: p.x + 6, cy: p.y, r: id === S.focus ? 7 : 5, class: 'gx-f' + (FAMILY[n.kind] || 6) }));
      g.appendChild(svg('text', { x: p.x + 16, y: p.y + 4 }, short(n.label, Math.floor(colW / 7.2))));
      g.appendChild(svg('title', {}, n.kind + ': ' + n.label));
      g.addEventListener('click', function () {
        if (p.ghost) { S.open.push(id); writeHash(); draw(); return; }
        var t = document.getElementById('gx-' + id.replace(/[^a-z0-9]/gi, '-')); if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      s.appendChild(g);
    });
    var legend = el('p', { class: 'gx-legend' });
    Object.keys(FAMILY_NAME).forEach(function (f) { legend.appendChild(el('span', null, el('i', { class: 'gx-f' + f }), FAMILY_NAME[f])); });
    legend.appendChild(el('span', null, el('b', { class: 'gx-dash' }), 'inferred, not yet checked'));
    return el('div', { class: 'gx-pic' }, el('div', { class: 'gx-scroll' }, s), legend, el('p', { class: 'small', text: 'Faint on the right: what the last opened node touches; click one to open it.' }));
  }

  // ── impact: climb from code, a test or a fix ─────────────────────────────────
  function impactView() {
    var start = S.focus, seen = {}, parent = {}, queue = [start], found = [];
    seen[start] = 1;
    while (queue.length) {
      var x = queue.shift(), n = N[x];
      (UP[n.kind] || []).forEach(function (r) {
        var list = r[0] === 'out' ? (OUT[x] || []).filter(function (e) { return e.rel === r[1]; }).map(function (e) { return { id: e.to, e: e, verb: e.rel }; })
                                  : (IN[x] || []).filter(function (e) { return e.rel === r[1]; }).map(function (e) { return { id: e.from, e: e, verb: e.inverse }; });
        list.filter(function (y) { return visible(y.e); }).forEach(function (y) {
          if (seen[y.id]) return;
          seen[y.id] = 1; parent[y.id] = { from: x, verb: y.verb, e: y.e }; found.push(y.id);
          if (y.id.indexOf('remediation:fix-commit') === 0 && N[start].kind === 'test') { /* every test reaches the commit: keep climbing from it */ }
          queue.push(y.id);
        });
      });
    }
    var out = el('div', { class: 'gx-impact' });
    var n0 = N[start];
    out.appendChild(el('section', { class: 'gx-card gx-start' }, el('h3', null, kindPill(n0), ' ', n0.label), el('p', { class: 'gx-acts' }, nodeLink(n0),
      el('button', { class: 'rs-b', type: 'button', text: 'Explore around it instead', onclick: function () { go('focus', start); } }))));
    var byKind = {};
    found.forEach(function (id) { (byKind[N[id].kind] = byKind[N[id].kind] || []).push(id); });
    var tiles = el('div', { class: 'stats' });
    IMPACT_ORDER.forEach(function (k) { if (byKind[k]) tiles.appendChild(el('a', { class: 'stat', href: '#gx-k-' + k, onclick: function (ev) { ev.preventDefault(); var t = document.getElementById('gx-k-' + k); if (t) t.scrollIntoView({ behavior: 'smooth' }); } }, el('b', { text: String(byKind[k].length) }), el('span', { text: plural(k, byKind[k].length) }))); });
    out.appendChild(tiles);
    if (!found.length) out.appendChild(el('p', { class: 'small', text: 'Nothing above this node' + (S.hide ? ' with inferred edges hidden' : '') + '.' }));
    IMPACT_ORDER.concat(Object.keys(byKind).filter(function (k) { return IMPACT_ORDER.indexOf(k) < 0; })).forEach(function (k) {
      if (!byKind[k]) return;
      var sec = el('section', { class: 'gx-card', id: 'gx-k-' + k }, el('h3', { text: byKind[k].length + ' ' + plural(k, byKind[k].length) }));
      var ul = el('ul', { class: 'gx-reach' });
      byKind[k].forEach(function (id) {
        var steps = [], c = id;
        while (parent[c]) { steps.unshift(parent[c]); c = parent[c].from; }
        var inferred = steps.some(function (s) { return s.e.basis && s.e.basis.kind === 'inferred'; });
        var li = el('li', null, el('button', { class: 'gx-crumb', type: 'button', text: N[id].label, onclick: function () { go('focus', id); } }), inferred ? el('span', { class: 'gx-tag', text: 'through an inferred step' }) : null);
        li.appendChild(el('div', { class: 'gx-path small' }, steps.map(function (s, i) {
          return [i ? '' : short(N[s.from].label, 36), el('span', { class: 'gx-verb' + (s.e.basis && s.e.basis.kind === 'inferred' ? ' gx-inf' : ''), text: ' ' + s.verb.replace(/_/g, ' ') + ' ' }), short(N[steps[i + 1] ? steps[i + 1].from : id].label, 36)];
        })));
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      out.appendChild(sec);
    });
    return out;
  }

  // ── the frame ─────────────────────────────────────────────────────────────
  function controls() {
    var bar = el('div', { class: 'gx-bar' });
    var dl = document.getElementById('gx-nodes');
    if (!dl) { dl = el('datalist', { id: 'gx-nodes' }); G.nodes.forEach(function (n) { dl.appendChild(el('option', { value: n.kind + ': ' + n.label })); }); document.body.appendChild(dl); }
    var q = el('input', { type: 'search', list: 'gx-nodes', placeholder: 'Start from: a CVE, a risk, a stakeholder, a file, a test, a control…', 'aria-label': 'Start from a node' });
    q.addEventListener('change', function () { var hit = G.nodes.filter(function (n) { return n.kind + ': ' + n.label === q.value; })[0]; if (hit) go(UP[hit.kind] && S.mode === 'impact' ? 'impact' : 'focus', hit.id); });
    bar.appendChild(q);
    [['focus', 'Explore around it'], ['impact', 'What it puts at stake']].forEach(function (m) {
      bar.appendChild(el('button', { type: 'button', class: 'rs-b' + (S.mode === m[0] ? ' on' : ''), 'aria-pressed': String(S.mode === m[0]), disabled: m[0] === 'impact' && !UP[N[S.focus].kind] ? 'disabled' : null, text: m[1],
        onclick: function () { go(m[0], S.focus, m[0] === 'focus'); } }));
    });
    var cb = el('input', { type: 'checkbox', id: 'gx-hide', checked: S.hide ? 'checked' : null });
    cb.addEventListener('change', function () { S.hide = cb.checked; writeHash(); draw(); });
    bar.appendChild(el('label', { class: 'gx-sw', for: 'gx-hide' }, cb, ' Hide what an agent inferred'));
    var share = el('button', { type: 'button', class: 'rs-b', text: 'Copy the link to this view', onclick: function () { try { navigator.clipboard.writeText(location.href); share.textContent = 'Copied'; } catch (e) { share.textContent = location.href; } } });
    bar.appendChild(share);
    var starts = el('p', { class: 'small gx-starts' }, 'Try: ');
    [['vulnerability:cve-109618', 'CVE-2026-109618'], ['risk:r01', 'the top risk'], ['code:file:Zend/zend_alloc.c', 'Zend/zend_alloc.c'], ['stakeholder:operators', 'the people who run PHP'], ['test:Zend/tests/oom_request_parsing.phpt', 'a test']].forEach(function (t, i) {
      if (!N[t[0]]) return;
      if (i) starts.appendChild(document.createTextNode(' · '));
      starts.appendChild(el('button', { class: 'gx-crumb', type: 'button', text: t[1], onclick: function () { go(N[t[0]].kind === 'code' || N[t[0]].kind === 'test' ? 'impact' : 'focus', t[0]); } }));
    });
    return el('div', null, bar, starts);
  }
  function draw() {
    box.textContent = '';
    box.appendChild(controls());
    box.appendChild(S.mode === 'impact' ? impactView() : focusView());
  }

  fetch(root + 'data/grc-graph.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }).then(function (g) {
    G = g;
    G.nodes.forEach(function (n) { N[n.id] = n; });
    G.edges.forEach(function (e) { (OUT[e.from] = OUT[e.from] || []).push(e); (IN[e.to] = IN[e.to] || []).push(e); });
    S.focus = 'vulnerability:cve-109618';
    readHash();
    if (!N[S.focus]) S.focus = G.nodes[0].id;
    draw();
    window.addEventListener('hashchange', function () { readHash(); draw(); });
  }).catch(function (e) { box.textContent = 'The graph could not be read (' + (e && e.message || e) + ').'; });
})();
