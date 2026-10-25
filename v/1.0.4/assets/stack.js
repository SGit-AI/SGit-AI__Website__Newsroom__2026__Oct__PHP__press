// php.oct.2026.newsroom.sgit.ai: your stack and its blast radius (/stack/). The model is data/stack.json, joined at
// build time with the version ranges, SAPIs and mitigations (data/affected.json), the edge vendors (data/defence.json)
// and the NCSC-NL inventory (data/software.json) into stack/catalogue.json, which this script reads.
//
// The reader describes what they run as components (the internet, an edge, applications, platforms, PHP runtimes, data,
// secrets, services) and the links between them. Every runtime is checked against every vulnerability in the
// catalogue: its version against the ranges, where it comes from against the inventory, its SAPI against the scope,
// whether the internet reaches it, which settings and edge rules reduce it. The blast radius is what an attacker who
// runs code as an affected PHP worker can touch: what runs on it, and what it and they can reach, then one step further.
//
// Kept in this browser (p2s.stack.v1) and, through the Ask pane's vault, under /php-october/stack/ in the reader's own
// vault (assets/ask/ask.js listens for the p2s-stack event). Nothing is sent anywhere. Everything is rendered as text:
// an imported stack file is someone else's data.
(function () {
  'use strict';
  var box = document.getElementById('stack');
  if (!box) return;
  var root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length);   // only ever '../' repeated: the depth, never page text
  var KEY = 'p2s.stack.v1', FORMAT = 'p2s.stack/1';
  var CAT = null, ST = null, UI = { open: {} };
  var LEVEL = { ok: 0, low: 1, unknown: 2, high: 3, critical: 4 };
  var LEVEL_WORD = { ok: 'fixed or not affected', low: 'out of scope', unknown: 'not known', high: 'affected, not exposed to the internet', critical: 'affected and exposed' };

  // ------------------------------------------------------------------ small helpers
  function el(tag, attrs) {
    var e = document.createElement(tag), k, i;
    attrs = attrs || {};
    for (k in attrs) {
      if (!Object.prototype.hasOwnProperty.call(attrs, k) || attrs[k] == null || attrs[k] === false) continue;
      if (k === 'class') e.className = attrs[k]; else if (k === 'text') e.textContent = attrs[k];
      else if (k.slice(0, 2) === 'on') e.addEventListener(k.slice(2), attrs[k]); else e.setAttribute(k, attrs[k] === true ? '' : attrs[k]);
    }
    for (i = 2; i < arguments.length; i++) add(e, arguments[i]);
    return e;
  }
  function add(e, c) { if (c == null || c === false) return; if (Array.isArray(c)) c.forEach(function (x) { add(e, x); }); else e.appendChild(c.nodeType ? c : document.createTextNode(String(c))); }
  function siteLink(path, text) { return el('a', { href: root + String(path).replace(/^\/+/, ''), text: text }); }
  function outLink(url, text) { return /^https:\/\//i.test(url || '') ? el('a', { href: url, target: '_blank', rel: 'noopener noreferrer', text: text }) : document.createTextNode(text); }
  function uid(kind) { return kind.slice(0, 3) + '-' + Math.random().toString(36).slice(2, 8); }
  function clip(s, n) { s = String(s == null ? '' : s).replace(/[\u0000-\u001f]/g, ' ').trim(); return s.length > n ? s.slice(0, n) : s; }
  function kindOf(id) { for (var i = 0; i < CAT.kinds.length; i++) if (CAT.kinds[i].id === id) return CAT.kinds[i]; return null; }
  function pill(level, text) { return el('span', { class: 'sk-pill sk-' + level, text: text || LEVEL_WORD[level] }); }
  function statusPill(s) { var c = { 'Fix': 'ok', 'Not vuln': 'ok', 'Vulnerable': 'critical', 'Investigation': 'unknown' }[s] || 'unknown'; return el('span', { class: 'sk-pill sk-' + c, text: s || 'no status' }); }

  // ------------------------------------------------------------------ the store
  function load() {
    var s = null;
    try { s = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) {}
    if (!s || s.v !== 1 || typeof s.stacks !== 'object') s = { v: 1, current: null, stacks: {} };
    return s;
  }
  function save() {
    var cur = ST.stacks[ST.current]; if (cur) cur.updated = new Date().toISOString();
    try { localStorage.setItem(KEY, JSON.stringify(ST)); } catch (e) {}
    try { window.dispatchEvent(new CustomEvent('p2s-stack')); } catch (e) {}
  }
  function current() { return ST.stacks[ST.current] || null; }
  function fromExample(ex) {
    var id = 'st-' + Math.random().toString(36).slice(2, 8);
    ST.stacks[id] = { id: id, name: ex.name, from: ex.id, updated: new Date().toISOString(), components: JSON.parse(JSON.stringify(ex.components)), edges: JSON.parse(JSON.stringify(ex.edges)) };
    ST.current = id; save();
  }
  function blank() {
    var id = 'st-' + Math.random().toString(36).slice(2, 8);
    ST.stacks[id] = { id: id, name: 'My stack', updated: new Date().toISOString(), components: [{ id: 'net', kind: 'internet', name: 'The internet' }], edges: [] };
    ST.current = id; save();
  }
  // Import: a stack file is untrusted. Keep only known kinds and fields, short strings, links between known ids.
  function clean(doc) {
    var src = doc && (doc.stack || doc);
    if (!src || !Array.isArray(src.components)) throw new Error('not a stack file');
    var ids = {}, comps = [];
    src.components.slice(0, 200).forEach(function (c) {
      if (!c || !kindOf(c.kind)) return;
      var id = /^[A-Za-z0-9_-]{1,40}$/.test(c.id || '') && !ids[c.id] ? c.id : uid(c.kind);
      ids[id] = 1; if (c.id && c.id !== id) ids['old:' + c.id] = id;
      var x = { id: id, kind: c.kind, name: clip(c.name, 120) || kindOf(c.kind).name };
      ['vendor', 'product', 'version', 'sapi', 'sensitivity'].forEach(function (k) { if (c[k] != null) x[k] = clip(c[k], 200); });
      if (c.patched === true) x.patched = true;
      if (Array.isArray(c.controls)) x.controls = c.controls.filter(function (k) { return CAT.controls.some(function (t) { return t.id === k; }); });
      comps.push(x);
    });
    var map = function (i) { return ids['old:' + i] || (ids[i] ? i : null); };
    var edges = (Array.isArray(src.edges) ? src.edges : []).slice(0, 1000).map(function (e) { return Array.isArray(e) ? [map(e[0]), map(e[1])] : [null, null]; })
      .filter(function (e) { return e[0] && e[1] && e[0] !== e[1]; });
    return { name: clip(src.name, 120) || 'Imported stack', components: comps, edges: edges };
  }

  // ------------------------------------------------------------------ the analysis
  function linkRule(fromKind, toKind) { for (var i = 0; i < CAT.links.length; i++) { var l = CAT.links[i]; if (l.from.indexOf(fromKind) >= 0 && l.to.indexOf(toKind) >= 0) return l; } return null; }
  function inv(key) {
    if (!key) return null;
    var p = String(key).split('|'), rows = CAT.inventory.rows;
    for (var i = 0; i < rows.length; i++) if (rows[i][0] === p[0] && rows[i][1] === p[1]) return rows[i];
    return null;
  }
  function invStatus(row, vuln) { return row ? row[CAT.inventory.columns.indexOf(vuln.inventory)] : null; }
  function parseVer(v) { var m = String(v || '').match(/(\d+)\.(\d+)(?:\.(\d+))?/); return m ? { maj: +m[1], min: +m[2], patch: m[3] == null ? null : +m[3], branch: m[1] + '.' + m[2] } : null; }
  // The version alone, against the ranges in data/affected.json.
  function byVersion(ver) {
    var v = parseVer(ver);
    if (!v) return { verdict: 'unknown', why: 'No version given: add the version PHP reports (php -v).' };
    var r = null; CAT.ranges.forEach(function (x) { if (x.branch === v.branch) r = x; });
    if (r && r.in_cve) {
      var fixed = parseVer(r.fixed);
      if (v.patch == null) return { verdict: 'unknown', why: 'PHP ' + v.branch + ' is affected below ' + r.fixed + '; give the full version to tell.' };
      return v.patch >= fixed.patch ? { verdict: 'fixed', why: 'PHP ' + ver + ' is at or above ' + r.fixed + ', the fixed release on its branch.' }
        : { verdict: 'affected', why: 'PHP ' + ver + ' is below ' + r.fixed + ', the fixed release on the ' + v.branch + ' branch.', fix: r.fixed };
    }
    if (r) return { verdict: 'nofix', why: 'PHP ' + v.branch + ' is ' + r.affected + '; fixed: ' + r.fixed + '. The CVE record lists only 8.2 to 8.5, so a scanner reading it will say this branch is not affected.' };
    if (v.maj < 7 || (v.maj === 7 && v.min <= 3)) return { verdict: 'nofix', why: 'PHP ' + v.branch + ' is affected, by every primary source that addresses it, with no release and no backport.' };
    return { verdict: 'unlisted', why: 'PHP ' + v.branch + ' is not in any published range; check it against the advisory.' };
  }
  function analyse(stack) {
    var C = {}, out = {}, inc = {}, A = { runtimes: [], node: {}, exposedApps: {}, bypass: {}, edgesOnPath: {}, actions: [], findings: {} };
    stack.components.forEach(function (c) { C[c.id] = c; out[c.id] = []; inc[c.id] = []; });
    stack.edges.forEach(function (e) { if (C[e[0]] && C[e[1]] && linkRule(C[e[0]].kind, C[e[1]].kind)) { out[e[0]].push(e[1]); inc[e[1]].push(e[0]); } });
    // What the internet reaches: along "sends requests to" from every internet node, through edges, to applications.
    var reach = {}, queue = stack.components.filter(function (c) { return c.kind === 'internet'; }).map(function (c) { return c.id; });
    queue.forEach(function (id) { reach[id] = 1; });
    while (queue.length) { var id = queue.shift(); out[id].forEach(function (t) { var k = C[t].kind; if ((k === 'edge' || k === 'app') && !reach[t]) { reach[t] = 1; queue.push(t); } }); }
    stack.components.forEach(function (c) {
      if (c.kind !== 'app' || !reach[c.id]) return;
      A.exposedApps[c.id] = 1;
      A.bypass[c.id] = inc[c.id].some(function (p) { return C[p].kind === 'internet'; });
      A.edgesOnPath[c.id] = inc[c.id].filter(function (p) { return C[p].kind === 'edge' && reach[p]; });
    });
    // Each runtime: the applications on it (directly or through a platform) and the platforms that provide it.
    stack.components.filter(function (c) { return c.kind === 'runtime'; }).forEach(function (rt) {
      var platforms = inc[rt.id].filter(function (p) { return C[p].kind === 'platform'; });
      var apps = {}; inc[rt.id].forEach(function (p) { if (C[p].kind === 'app') apps[p] = 1; });
      platforms.forEach(function (pl) { inc[pl].forEach(function (p) { if (C[p].kind === 'app') apps[p] = 1; }); });
      apps = Object.keys(apps);
      var exposed = apps.some(function (a) { return A.exposedApps[a]; });
      var edges = {}; apps.forEach(function (a) { (A.edgesOnPath[a] || []).forEach(function (e) { edges[e] = 1; }); });
      var bypass = apps.some(function (a) { return A.bypass[a]; });
      var sapi = CAT.sapis.filter(function (s) { return s.sapi === rt.sapi; })[0] || null;
      var notWeb = sapi && /not web-serving/.test(sapi.risk);
      var r = { id: rt.id, c: rt, apps: apps, platforms: platforms, exposed: exposed, bypass: bypass, edges: Object.keys(edges), sapi: sapi, vulns: [], level: 'ok' };
      CAT.vulns.forEach(function (vu) {
        var v = byVersion(rt.version), why = [v.why], verdict = v.verdict, provider = null;
        platforms.forEach(function (pl) {
          var row = inv(C[pl].product), s = invStatus(row, vu);
          if (!row) return;
          provider = { id: pl, row: row, status: s };
          if (s === 'Fix') {
            // A distribution backports the fix and keeps its old version number (7.4.3-4ubuntu2.29+esm5), so for a
            // package the version PHP reports cannot tell; an image or a host ships the upstream release, so it can.
            var backport = /ubuntu|deb\d|\+esm|\.el\d|module\+el|~|\bpl\d|-\d+$/i.test(row[2] || '');
            if (verdict === 'fixed') why.push(C[pl].name + ': the inventory also says ' + row[0] + ' ships a fix.');
            else if (!backport) why.push(C[pl].name + ': the inventory says ' + row[0] + ' ships a fix' + (row[2] ? ' (' + row[2] + ')' : '') + '; this version is older than it, so take their latest build.');
            else if (C[pl].patched) { why.push(C[pl].name + ': you say the vendor\u2019s fixed build (' + row[2] + ') is installed. A backport keeps the old version number, so PHP still reports ' + (rt.version || 'its old version') + '.'); verdict = 'vendor-fixed'; }
            else { why.push(C[pl].name + ': the inventory says the fixed build is ' + row[2] + '. A backport keeps the old version number, so the version PHP reports cannot tell: check the package version (dpkg -l, rpm -q), then tick \u201Cinstalled\u201D on the platform.'); verdict = verdict === 'unknown' ? 'unknown' : 'vendor-check'; }
          }
          else if (s === 'Not vuln') { why.push(C[pl].name + ': the inventory says not vulnerable.'); verdict = 'fixed'; }
          else if (s === 'Vulnerable') why.push(C[pl].name + ': the inventory says vulnerable.');
          else if (s === 'Investigation') why.push(C[pl].name + ': the inventory says the vendor is still investigating.');
        });
        var ctl = CAT.controls.filter(function (t) {
          if (t.vulns.indexOf(vu.id) < 0) return false;
          if (t.sapis && rt.sapi && t.sapis.indexOf(rt.sapi) < 0) return false;
          var b = parseVer(rt.version); if (t.branches && (!b || t.branches.indexOf(b.branch) < 0)) return false;
          return true;
        });
        var on = ctl.filter(function (t) { return (rt.controls || []).indexOf(t.id) >= 0; }), off = ctl.filter(function (t) { return (rt.controls || []).indexOf(t.id) < 0; });
        var level;
        if (verdict === 'fixed') level = 'ok';
        else if (verdict === 'vendor-fixed') level = 'ok';
        else if (notWeb) { level = 'low'; why.push('It does not serve web requests (' + rt.sapi + '): outside the advisory’s scope.'); }
        else if (verdict === 'unknown' || verdict === 'unlisted' || verdict === 'vendor-check') level = 'unknown';
        else level = exposed ? 'critical' : 'high';
        if (!rt.sapi && level !== 'ok') why.push('How it serves requests is not given: mod_php is where remote code execution was demonstrated.');
        r.vulns.push({ vuln: vu, verdict: verdict, level: level, why: why, fix: v.fix, provider: provider, on: on, off: off });
        if (LEVEL[level] > LEVEL[r.level]) r.level = level;
      });
      A.runtimes.push(r);
    });
    // The blast radius: from every runtime that is affected (critical or high), what runs on it, then what they reach.
    A.runtimes.forEach(function (r) {
      if (LEVEL[r.level] < LEVEL.high) return;
      var src = [r.id].concat(r.apps, r.platforms);
      src.forEach(function (n) { mark(n, 'hit', r); });
      var first = {};
      src.forEach(function (n) { out[n].forEach(function (t) { var k = C[t].kind; if (k === 'data' || k === 'secret' || k === 'service') { first[t] = 1; mark(t, 'radius', r); } }); });
      Object.keys(first).forEach(function (n) { out[n].forEach(function (t) { if (!A.node[t] || A.node[t].state !== 'hit') mark(t, 'further', r); }); });
    });
    function mark(n, state, r) {
      var cur = A.node[n], order = { further: 1, radius: 2, hit: 3 };
      if (!cur) cur = A.node[n] = { state: state, from: [], level: r.level };
      if (order[state] > order[cur.state]) cur.state = state;
      if (LEVEL[r.level] > LEVEL[cur.level]) cur.level = r.level;
      if (cur.from.indexOf(r.id) < 0) cur.from.push(r.id);
    }
    // the way in: back from every compromised application, through what the internet reaches
    A.wayIn = {}; var back = Object.keys(A.node).filter(function (n) { return A.node[n].state === 'hit' && C[n].kind === 'app' && reach[n]; });
    back.forEach(function (n) { A.wayIn[n] = A.node[n].level; });
    while (back.length) { var n0 = back.shift(); inc[n0].forEach(function (p0) { if (reach[p0] && !A.wayIn[p0]) { A.wayIn[p0] = A.wayIn[n0]; back.push(p0); } }); }
    A.C = C; A.out = out; A.inc = inc; A.reach = reach;
    return A;
  }

  // ------------------------------------------------------------------ the graph
  function svg(tag, attrs, text) { var e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (var k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; return e; }
  function graph(stack, A) {
    var cols = [[], [], [], [], []];
    stack.components.forEach(function (c) { var k = kindOf(c.kind); cols[k ? k.col : 4].push(c); });
    var W = 1000, cw = W / 5, nh = 46, gap = 18, top = 34;
    var rows = Math.max.apply(null, cols.map(function (c) { return c.length; }).concat([1]));
    var H = top + rows * (nh + gap) + 10, pos = {};
    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'sk-graph', role: 'img', 'aria-label': 'The stack as a graph, coloured by blast radius' });
    ['Internet', 'Edge', 'Applications', 'PHP and platforms', 'Data, secrets, services'].forEach(function (t, i) { s.appendChild(svg('text', { x: i * cw + cw / 2, y: 16, 'text-anchor': 'middle', class: 'sk-col' }, t)); });
    cols.forEach(function (list, i) {
      var off = top + (rows - list.length) * (nh + gap) / 2;
      list.forEach(function (c, j) { pos[c.id] = { x: i * cw + 12, y: off + j * (nh + gap), w: cw - 24, h: nh }; });
    });
    var gE = svg('g', {}), gN = svg('g', {});
    stack.edges.forEach(function (e) {
      var a = pos[e[0]], b = pos[e[1]]; if (!a || !b) return;
      var x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y + b.h / 2;
      if (b.x <= a.x) { x1 = a.x + a.w / 2; y1 = a.y + (b.y > a.y ? a.h : 0); x2 = b.x + b.w / 2; y2 = b.y + (b.y > a.y ? 0 : b.h); }
      var na = A.node[e[0]], nb = A.node[e[1]], hot = na && nb && (na.state === 'hit') && (nb.state === 'hit' || nb.state === 'radius');
      // the way in: from the internet, through the edge, to an application that runs on an affected runtime
      if (!hot && A.wayIn[e[0]] && A.wayIn[e[1]]) { hot = true; na = { level: A.wayIn[e[1]] }; }
      var mx = (x1 + x2) / 2;
      gE.appendChild(svg('path', { d: 'M' + x1 + ',' + y1 + ' C' + mx + ',' + y1 + ' ' + mx + ',' + y2 + ' ' + x2 + ',' + y2, class: 'sk-e' + (hot ? ' sk-e-hot sk-e-' + na.level : '') }));
    });
    stack.components.forEach(function (c) {
      var p = pos[c.id], n = A.node[c.id], rt = A.runtimes.filter(function (r) { return r.id === c.id; })[0];
      var cls = 'sk-n sk-k-' + c.kind + (rt ? ' sk-s-' + rt.level : '') + (n ? ' sk-r-' + n.state + ' sk-l-' + n.level : '');
      var g = svg('g', { class: cls, tabindex: '0', 'data-id': c.id });
      g.appendChild(svg('rect', { x: p.x, y: p.y, width: p.w, height: p.h, rx: 8 }));
      var name = c.name.length > 22 ? c.name.slice(0, 21) + '…' : c.name;
      g.appendChild(svg('text', { x: p.x + 10, y: p.y + 19, class: 'sk-nt' }, name));
      var sub = rt ? ('PHP ' + (c.version || '?') + (c.sapi ? ' · ' + c.sapi : '')) : n ? { hit: 'runs as the worker', radius: 'in the blast radius', further: 'one step further' }[n.state] : (kindOf(c.kind) || {}).name;
      g.appendChild(svg('text', { x: p.x + 10, y: p.y + 36, class: 'sk-ns' }, (String(sub).length > 30 ? String(sub).slice(0, 29) + '…' : String(sub))));
      g.appendChild(svg('title', {}, c.name + (rt ? ': ' + LEVEL_WORD[rt.level] : n ? ': ' + { hit: 'compromised with the PHP worker', radius: 'reachable from an affected PHP worker', further: 'one step beyond the blast radius' }[n.state] : '')));
      g.addEventListener('click', function () { UI.open[c.id] = true; draw(); var t = document.getElementById('sk-c-' + c.id); if (t) t.scrollIntoView({ behavior: 'smooth', block: 'center' }); });
      gN.appendChild(g);
    });
    s.appendChild(gE); s.appendChild(gN);
    var legend = el('p', { class: 'sk-legend' },
      el('span', null, el('i', { class: 'sk-sw sk-sw-critical' }), 'affected and exposed'), el('span', null, el('i', { class: 'sk-sw sk-sw-high' }), 'affected, internal'),
      el('span', null, el('i', { class: 'sk-sw sk-sw-radius' }), 'in the blast radius'), el('span', null, el('i', { class: 'sk-sw sk-sw-further' }), 'one step further'),
      el('span', null, el('i', { class: 'sk-sw sk-sw-ok' }), 'fixed'), el('span', null, el('i', { class: 'sk-sw sk-sw-unknown' }), 'not known'));
    return el('div', { class: 'sk-gwrap' }, s, legend);
  }

  // ------------------------------------------------------------------ the results
  function verdictCard(r, A) {
    var c = r.c, card = el('div', { class: 'sk-v sk-vl-' + r.level });
    card.appendChild(el('h3', null, c.name + ' ', pill(r.level)));
    var ctx = [];
    ctx.push(r.exposed ? (r.bypass ? 'The internet reaches it directly, not only through the edge.' : 'The internet reaches it' + (r.edges.length ? ' through ' + r.edges.map(function (e) { return A.C[e].name; }).join(', ') : '') + '.') : 'The internet does not reach it in this stack.');
    if (r.apps.length) ctx.push('It runs ' + r.apps.map(function (a) { return A.C[a].name; }).join(', ') + '.');
    if (r.sapi) ctx.push(r.sapi.sapi + ': ' + r.sapi.risk + '. ' + r.sapi.text);
    card.appendChild(el('p', { class: 'small', text: ctx.join(' ') }));
    r.vulns.forEach(function (x) {
      var d = el('div', { class: 'sk-vu' });
      d.appendChild(el('p', null, siteLink(x.vuln.page, x.vuln.id), ' ', x.vuln.name.replace(/^php2shell: /, ''), ' ', pill(x.level, { affected: 'affected', nofix: 'affected, no upstream fix', fixed: 'fixed', 'vendor-fixed': 'fixed by the vendor', 'vendor-check': 'check the vendor build', unknown: 'not known', unlisted: 'not in any range' }[x.verdict] || x.verdict)));
      d.appendChild(el('ul', { class: 'sk-why' }, x.why.map(function (w) { return el('li', { text: w }); })));
      if (x.on.length) d.appendChild(el('p', { class: 'small' }, el('b', { text: 'Reducing it: ' }), x.on.map(function (t) { return t.label + ' (' + t.caveat + ')'; }).join('; ')));
      card.appendChild(d);
    });
    if (r.edges.length && LEVEL[r.level] >= LEVEL.high) {
      r.edges.forEach(function (e) {
        var vendor = A.C[e].vendor, ed = CAT.edge.filter(function (x) { return x.vendor === vendor; })[0];
        card.appendChild(el('p', { class: 'small' }, el('b', { text: A.C[e].name + ': ' }), ed ? ed.what + ' (' + ed.when + '). ' + ed.caveat + '.' : 'This site has no record of a rule from this vendor. An edge rule is a stopgap at best.'));
      });
    }
    return card;
  }
  function actions(A) {
    var list = [], later = [], seen = {};
    function push(level, text, link, after) { if (seen[text]) return; seen[text] = 1; (after ? later : list).push({ level: level, text: text, link: link }); }
    A.runtimes.slice().sort(function (a, b) { return LEVEL[b.level] - LEVEL[a.level]; }).forEach(function (r) {
      if (LEVEL[r.level] < LEVEL.unknown) return;
      var x = r.vulns.filter(function (v) { return v.level === r.level; })[0] || r.vulns[0], c = r.c;
      if (x.verdict === 'affected') push(r.level, 'Update ' + c.name + ' from PHP ' + c.version + ' to ' + x.fix + ' or later' + (r.platforms.length ? ', through ' + r.platforms.map(function (p) { return A.C[p].name; }).join(', ') : '') + '.', 'patching/index.html');
      else if (x.verdict === 'nofix') push(r.level, c.name + ' is on a branch with no upstream release: move it to a supported branch (8.2 or later), or take a vendor build that carries the backport. The inventory lists which vendors ship one.', 'patching/index.html');
      else if (x.verdict === 'vendor-check') push(r.level, 'Check that ' + r.platforms.map(function (p) { return A.C[p].name; }).join(', ') + ' has the vendor\u2019s fixed build installed (the inventory names ' + ((x.provider && x.provider.row[2]) || 'it') + '); if not, install it.', 'patching/index.html');
      else if (x.verdict === 'unknown' || x.verdict === 'unlisted') push(r.level, 'Find out exactly which PHP ' + c.name + ' runs, and from where (php -v, and the package or image it came from).', 'playbook/index.html');
      if (LEVEL[r.level] >= LEVEL.high) r.vulns.forEach(function (v) { v.off.forEach(function (t) { push('high', 'Until it is updated, on ' + c.name + ': ' + t.label + '. ' + t.caveat, 'flaws/index.html', true); }); });
    });
    var hot = Object.keys(A.node).filter(function (n) { return A.node[n].state === 'radius' && A.C[n].kind === 'secret'; });
    if (hot.length) push('high', 'The secrets in the blast radius (' + hot.map(function (n) { return A.C[n].name; }).join('; ') + ') are what an attacker takes first. If an affected runtime was reachable after disclosure on 21 October, decide whether to rotate them once it is updated: exposed is not the same as exploited.', 'signals/index.html');
    list = list.concat(later);
    if (!list.length) push('ok', 'Nothing in this stack is known to be affected. Keep it current: the pulse will check it against new vulnerabilities as they are added.', 'whatsnew/index.html');
    return list;
  }
  function relevant(stack, A) {
    var terms = {}, rows = [];
    function term(t) { t = String(t || '').trim(); if (t.length >= 3) terms[t.toLowerCase()] = t; }
    stack.components.forEach(function (c) {
      if (c.vendor) term(c.vendor);
      if (c.sapi) { term(c.sapi.replace(/^Apache /, '')); if (/FPM/.test(c.sapi)) term('FPM'); }
      var v = parseVer(c.version); if (c.kind === 'runtime' && v) term('PHP ' + v.branch);
      var row = inv(c.product); if (row) { rows.push({ c: c, row: row }); term(row[0].split(/[\/;(]/)[0]); row[1].split(/\s+/).slice(0, 1).forEach(term); }
    });
    var keys = Object.keys(terms).filter(function (t) { return !/^(the|php|and)$/.test(t); });
    var hits = [];
    (CAT.items || []).forEach(function (it) {
      var t = String(it[1]).toLowerCase(), m = keys.filter(function (k) { return new RegExp('(^|[^a-z0-9])' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '($|[^a-z0-9])').test(t); });
      if (m.length) hits.push({ it: it, m: m });
    });
    hits.sort(function (a, b) { return b.m.length - a.m.length; });
    return { rows: rows, hits: hits.slice(0, 20), terms: keys.map(function (k) { return terms[k]; }) };
  }

  // ------------------------------------------------------------------ the builder
  function field(label, input, hint) { return el('label', { class: 'sk-f' }, el('span', { text: label }), input, hint ? el('small', { text: hint }) : null); }
  function input(c, key, attrs) {
    var i = el('input', Object.assign({ type: 'text', value: c[key] || '' }, attrs || {}));
    i.addEventListener('change', function () { c[key] = clip(i.value, 200); save(); draw(); });
    return i;
  }
  function select(c, key, options, empty) {
    var s = el('select');
    s.appendChild(el('option', { value: '', text: empty || '(choose)' }));
    options.forEach(function (o) { var v = Array.isArray(o) ? o[0] : o, t = Array.isArray(o) ? o[1] : o; s.appendChild(el('option', { value: v, text: t, selected: c[key] === v })); });
    s.addEventListener('change', function () { c[key] = s.value; save(); draw(); });
    return s;
  }
  function productPicker(c) {
    var row = inv(c.product), dl = document.getElementById('sk-inv');
    if (!dl) { dl = el('datalist', { id: 'sk-inv' }); CAT.inventory.rows.forEach(function (r) { dl.appendChild(el('option', { value: r[0] + ': ' + r[1] })); }); document.body.appendChild(dl); }
    var i = el('input', { type: 'search', list: 'sk-inv', value: row ? row[0] + ': ' + row[1] : '', placeholder: 'Search the inventory: WordPress, Ubuntu, Docker, Plesk…', 'aria-label': 'Product, from the NCSC-NL inventory' });
    i.addEventListener('change', function () {
      var v = i.value, hit = CAT.inventory.rows.filter(function (r) { return r[0] + ': ' + r[1] === v; })[0];
      c.product = hit ? hit[0] + '|' + hit[1] : ''; save(); draw();
    });
    var info = row ? el('div', { class: 'sk-inv' }, el('p', null, 'CVE-2026-109618 ', statusPill(row[3]), '  CVE-2026-109619 ', statusPill(row[4]), row[2] ? '  version: ' + row[2] : ''), el('p', { class: 'small', text: row[5] }), row[6] ? el('p', { class: 'small' }, outLink(row[6], 'The vendor’s page')) : null) : null;
    return el('div', null, field('Product (the NCSC-NL inventory, ' + CAT.inventory.rows.length + ' products)', i, 'Leave empty for your own code.'), info);
  }
  function componentCard(stack, c, A) {
    var k = kindOf(c.kind), rt = A.runtimes.filter(function (r) { return r.id === c.id; })[0], n = A.node[c.id];
    var head = el('summary', null, el('b', { text: c.name }), ' ', el('span', { class: 'small', text: k.name }), ' ', rt ? pill(rt.level) : n ? pill(n.level === 'critical' ? 'critical' : 'high', { hit: 'runs as the worker', radius: 'in the blast radius', further: 'one step further' }[n.state]) : null);
    var d = el('details', { class: 'sk-c', id: 'sk-c-' + c.id, open: !!UI.open[c.id] }, head);
    d.addEventListener('toggle', function () { UI.open[c.id] = d.open; });
    d.appendChild(field('Name', input(c, 'name')));
    if (c.kind === 'edge') d.appendChild(field('Vendor', select(c, 'vendor', CAT.edge.map(function (e) { return e.vendor; }), 'Another vendor, or none of these')));
    if (c.kind === 'app' || c.kind === 'platform') d.appendChild(productPicker(c));
    if (c.kind === 'app') d.appendChild(field('Its version (optional)', input(c, 'version', { placeholder: 'e.g. 7.1.2' })));
    if (c.kind === 'platform') {
      var prow = inv(c.product);
      if (prow && (prow[3] === 'Fix' || prow[4] === 'Fix') && prow[2]) {
        var pc = el('input', { type: 'checkbox', checked: !!c.patched });
        pc.addEventListener('change', function () { c.patched = pc.checked; save(); draw(); });
        d.appendChild(el('label', { class: 'sk-f' }, pc, ' The vendor\u2019s fixed build is installed (' + prow[2] + ')'));
      }
    }
    if (c.kind === 'runtime') {
      d.appendChild(field('PHP version', input(c, 'version', { placeholder: 'e.g. 8.3.30, from php -v' })));
      d.appendChild(field('How it serves requests (SAPI)', select(c, 'sapi', CAT.sapis.map(function (s) { return [s.sapi, s.sapi + ' (' + s.risk + ')']; }))));
      var box2 = el('fieldset', { class: 'sk-ctl' }, el('legend', { text: 'Settings in place' }));
      CAT.controls.forEach(function (t) {
        var cb = el('input', { type: 'checkbox', checked: (c.controls || []).indexOf(t.id) >= 0 });
        cb.addEventListener('change', function () { var l = (c.controls || []).filter(function (x) { return x !== t.id; }); if (cb.checked) l.push(t.id); c.controls = l; save(); draw(); });
        box2.appendChild(el('label', { title: t.what + ' Caveat: ' + t.caveat }, cb, ' ' + t.label + ' ', el('small', { text: '(' + t['for'] + ')' })));
      });
      d.appendChild(box2);
    }
    if (c.kind === 'data' || c.kind === 'secret' || c.kind === 'service') d.appendChild(field('What it holds', select(c, 'sensitivity', CAT.sensitivity)));
    // links out of this component, to every component of a kind it can connect to
    var targets = stack.components.filter(function (t) { return t.id !== c.id && linkRule(c.kind, t.kind); });
    if (targets.length) {
      var fs = el('fieldset', { class: 'sk-ctl' }, el('legend', { text: 'Connections' }));
      targets.forEach(function (t) {
        var on = stack.edges.some(function (e) { return e[0] === c.id && e[1] === t.id; });
        var cb = el('input', { type: 'checkbox', checked: on });
        cb.addEventListener('change', function () { stack.edges = stack.edges.filter(function (e) { return !(e[0] === c.id && e[1] === t.id); }); if (cb.checked) stack.edges.push([c.id, t.id]); save(); draw(); });
        fs.appendChild(el('label', null, cb, ' ' + linkRule(c.kind, t.kind).name + ' ', el('b', { text: t.name })));
      });
      d.appendChild(fs);
    }
    var ins = A.inc[c.id].map(function (p) { return A.C[p].name + ' ' + linkRule(A.C[p].kind, c.kind).name + ' it'; });
    if (ins.length) d.appendChild(el('p', { class: 'small', text: ins.join('; ') + '.' }));
    d.appendChild(el('p', null, el('button', { type: 'button', class: 'rs-b', text: 'Remove ' + c.name, onclick: function () {
      if (!confirm('Remove ' + c.name + ' from this stack?')) return;
      stack.components = stack.components.filter(function (x) { return x.id !== c.id; });
      stack.edges = stack.edges.filter(function (e) { return e[0] !== c.id && e[1] !== c.id; }); save(); draw();
    } })));
    return d;
  }

  // ------------------------------------------------------------------ the page
  function toolbar() {
    var bar = el('div', { class: 'sk-bar' }), cur = current();
    var pick = el('select', { 'aria-label': 'Your stacks' });
    Object.keys(ST.stacks).forEach(function (id) { pick.appendChild(el('option', { value: id, text: ST.stacks[id].name, selected: id === ST.current })); });
    pick.addEventListener('change', function () { ST.current = pick.value; save(); draw(); });
    bar.appendChild(pick);
    function b(t, fn) { bar.appendChild(el('button', { type: 'button', class: 'rs-b', text: t, onclick: fn })); }
    b('Rename', function () { var n = prompt('Name this stack', cur.name); if (n) { cur.name = clip(n, 120); save(); draw(); } });
    b('New, blank', function () { blank(); draw(); });
    var ex = el('select', { 'aria-label': 'Start from an example' }, el('option', { value: '', text: 'New, from an example…' }));
    CAT.examples.forEach(function (e) { ex.appendChild(el('option', { value: e.id, text: e.name })); });
    ex.addEventListener('change', function () { var e = CAT.examples.filter(function (x) { return x.id === ex.value; })[0]; if (e) { fromExample(e); draw(); } });
    bar.appendChild(ex);
    b('Export', function () {
      var doc = { format: FORMAT, site: location.host, exported: new Date().toISOString(), catalogue: CAT.site, stack: cur };
      var a = el('a', { href: URL.createObjectURL(new Blob([JSON.stringify(doc, null, 1)], { type: 'application/json' })), download: 'stack-' + cur.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40) + '.json' });
      document.body.appendChild(a); a.click(); a.remove();
    });
    var f = el('input', { type: 'file', accept: 'application/json,.json', hidden: true });
    f.addEventListener('change', function () {
      var file = f.files && f.files[0]; if (!file) return;
      if (file.size > 1e6) { alert('That file is over 1 MB: not a stack file.'); return; }
      file.text().then(function (t) {
        var doc = JSON.parse(t); if (doc.format && doc.format !== FORMAT) throw new Error('not a stack file (' + String(doc.format).slice(0, 40) + ')');
        var s = clean(doc), id = 'st-' + Math.random().toString(36).slice(2, 8);
        ST.stacks[id] = Object.assign({ id: id, updated: new Date().toISOString() }, s); ST.current = id; save(); draw();
      }).catch(function (e) { alert('Not imported: ' + (e && e.message || e)); });
    });
    bar.appendChild(el('label', { class: 'rs-b rs-file' }, 'Import', f));
    b('Delete', function () {
      if (!confirm('Delete the stack “' + cur.name + '” from this browser?')) return;
      delete ST.stacks[ST.current]; ST.current = Object.keys(ST.stacks)[0] || null; if (!ST.current) fromExample(CAT.examples[0]); save(); draw();
    });
    return bar;
  }
  function adder(stack) {
    var p = el('p', { class: 'sk-add' }, el('span', { class: 'small', text: 'Add: ' }));
    CAT.kinds.forEach(function (k) {
      if (k.id === 'internet' && stack.components.some(function (c) { return c.kind === 'internet'; })) return;
      p.appendChild(el('button', { type: 'button', class: 'rs-b', title: k.what, text: '+ ' + k.name, onclick: function () {
        var c = { id: uid(k.id), kind: k.id, name: k.id === 'internet' ? 'The internet' : 'New ' + k.name.split(':')[0].toLowerCase() };
        if (k.id === 'runtime') c.controls = [];
        stack.components.push(c); UI.open[c.id] = true; save(); draw();
        var t = document.getElementById('sk-c-' + c.id); if (t) t.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } }));
    });
    return p;
  }
  function draw() {
    var stack = current(); if (!stack) { fromExample(CAT.examples[0]); stack = current(); }
    var A = analyse(stack);
    var y = window.scrollY;
    box.textContent = '';
    box.appendChild(toolbar());
    // the summary
    var counts = { critical: 0, high: 0, unknown: 0, low: 0, ok: 0 };
    A.runtimes.forEach(function (r) { counts[r.level]++; });
    var radius = Object.keys(A.node).filter(function (n) { return A.node[n].state === 'radius'; });
    var tiles = el('div', { class: 'stats' });
    [[counts.critical, 'PHP runtimes affected and exposed'], [counts.high, 'affected, internal'], [counts.unknown, 'not known'], [counts.ok + counts.low, 'fixed or out of scope'], [radius.length, 'data, secrets and services in the blast radius']].forEach(function (x) {
      tiles.appendChild(el('div', { class: 'stat' }, el('b', { text: String(x[0]) }), el('span', { text: x[1] })));
    });
    box.appendChild(tiles);
    if (!A.runtimes.length) box.appendChild(el('p', { class: 'sk-note', text: 'This stack has no PHP runtime yet: add one (“+ PHP runtime”) and connect your applications to it.' }));
    box.appendChild(el('h2', { text: 'The blast radius' }));
    box.appendChild(graph(stack, A));
    box.appendChild(el('p', { class: 'small', text: 'Click a component to edit it. Remote code execution runs as the PHP worker: everything that runs on an affected runtime is compromised with it, what it can reach is in the blast radius, and what that reaches is one step further. Secrets go further than any graph: what a key opens is not drawn here.' }));
    var grid = el('div', { class: 'sk-grid' });
    var left = el('section', null, el('h2', { text: 'Your stack: ' + stack.name }), adder(stack));
    stack.components.forEach(function (c) { left.appendChild(componentCard(stack, c, A)); });
    var right = el('section', null, el('h2', { text: 'Each PHP runtime, against each flaw' }));
    A.runtimes.slice().sort(function (a, b) { return LEVEL[b.level] - LEVEL[a.level]; }).forEach(function (r) { right.appendChild(verdictCard(r, A)); });
    if (!A.runtimes.length) right.appendChild(el('p', { class: 'small', text: 'No runtime to check.' }));
    grid.appendChild(left); grid.appendChild(right);
    box.appendChild(el('h2', { text: 'What to do first' }));
    box.appendChild(el('ol', { class: 'sk-acts' }, actions(A).map(function (a) { return el('li', null, pill(a.level, { critical: 'first', high: 'next', unknown: 'find out', ok: 'fine' }[a.level] || a.level), ' ', a.text, ' ', a.link ? siteLink(a.link, 'Why') : null); })));
    box.appendChild(grid);
    // what on this site is about this stack
    var R = relevant(stack, A), rel = el('section', { class: 'sk-rel' }, el('h2', { text: 'What on this site is about your stack' }));
    if (R.rows.length) {
      rel.appendChild(el('h3', { text: 'Your products in the NCSC-NL inventory' }));
      rel.appendChild(el('ul', null, R.rows.map(function (x) { return el('li', null, el('b', { text: x.row[0] + ': ' + x.row[1] }), ' ', statusPill(x.row[3]), ' ', statusPill(x.row[4]), ' ', el('span', { class: 'small', text: x.row[5] }), ' ', x.row[6] ? outLink(x.row[6], 'vendor') : null); })));
      rel.appendChild(el('p', { class: 'small' }, 'From ', outLink(CAT.inventory.source, 'NCSC-NL’s inventory'), ' at ' + CAT.inventory.commit + ' (' + CAT.inventory.licence + '); the whole list is on ', siteLink('affected/software.html', 'the software inventory'), '.'));
    }
    if (R.hits.length) {
      rel.appendChild(el('h3', { text: 'Pages that name your stack (' + R.terms.join(', ') + ')' }));
      rel.appendChild(el('ul', null, R.hits.map(function (h) { return el('li', null, siteLink(h.it[2], h.it[1]), ' ', el('span', { class: 'small', text: '(' + h.m.join(', ') + ')' })); })));
    }
    rel.appendChild(el('p', { class: 'small' }, 'Always: ', siteLink('flaws/index.html', 'the two flaws'), ', ', siteLink('patching/index.html', 'who gets a fix'), ', ', siteLink('playbook/index.html', 'if you run PHP'), ', ', siteLink('defence/index.html', 'detection and defence'), '. ' + CAT.pulse));
    box.appendChild(rel);
    box.appendChild(el('p', { class: 'small', text: 'Catalogue: site v' + CAT.site + ', data as of ' + CAT.data_as_of + '. Kept in this browser' + (stack.updated ? ', saved ' + stack.updated.slice(0, 16).replace('T', ' ') + ' UTC' : '') + '; in your vault when it is open in the Ask pane.' }));
    window.scrollTo(0, y);
  }

  fetch(root + 'stack/catalogue.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }).then(function (cat) {
    CAT = cat; ST = load();
    if (!ST.current || !ST.stacks[ST.current]) { var ids = Object.keys(ST.stacks); if (ids.length) ST.current = ids[0]; else fromExample(CAT.examples[0]); }
    draw();
    // the vault (Ask pane) may bring stacks from another device
    window.addEventListener('p2s-stack-pulled', function () { ST = load(); if (!ST.stacks[ST.current]) ST.current = Object.keys(ST.stacks)[0]; draw(); });
  }).catch(function (e) { box.textContent = 'The catalogue could not be read (' + (e && e.message || e) + ').'; });
  window.P2SStack = { analyse: function (s) { return CAT ? analyse(s || current()) : null; }, store: function () { return ST; } };
})();
