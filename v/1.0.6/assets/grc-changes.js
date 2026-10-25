// php.oct.2026.newsroom.sgit.ai: what changed in the risk graph between any two releases (/grc/changes/, CI-003.8).
//
// data/grc-history.json holds, for every release that changed the graph, what changed against the release before.
// Comparing two releases replays those changes from the first graph to each of the two, then compares the two
// states. The page's first comparison is drawn by the build (build.py, grc_change_html); this draws the same
// structure for the pair the reader picks, and keeps the pair in the address (#from=0.10.12&to=0.14.22).
(function () {
  'use strict';
  var root = document.getElementById('gc-pick'), pair = document.getElementById('gc-pair');
  if (!root || !pair || !window.fetch) return;
  var UP = '../../', VERSIONS = root.getAttribute('data-releases').split(' ');
  function el(tag, attrs) {
    var e = document.createElement(tag), i, k;
    for (k in attrs || {}) e.setAttribute(k, attrs[k]);
    for (i = 2; i < arguments.length; i++) { var c = arguments[i]; if (c == null) continue; e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); }
    return e;
  }
  function vkey(v) { return v.split('.').map(Number); }
  function cmp(a, b) { var x = vkey(a), y = vkey(b); for (var i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] - y[i]; return 0; }
  function count(list, f) { var m = {}; list.forEach(function (x) { var k = f(x); m[k] = (m[k] || 0) + 1; }); return Object.keys(m).sort(function (a, b) { return m[b] - m[a] || (a < b ? -1 : 1); }).map(function (k) { return [k, m[k]]; }); }

  Promise.all([fetch(UP + 'data/grc-history.json').then(function (r) { return r.json(); }), fetch(UP + 'data/grc-gaps.json').then(function (r) { return r.json(); })]).then(function (got) {
    var H = got[0], RULES = got[1].rules, L = H.labels;
    var changes = H.releases.slice().sort(function (a, b) { return cmp(a.version, b.version); });

    // the graph as it stood at release v: node ids, edge key -> basis, gap rule -> ids
    function stateAt(v) {
      var s = { nodes: {}, edges: {}, gaps: {} };
      changes.forEach(function (c) {
        if (cmp(c.version, v) > 0) return;
        c.nodes_added.forEach(function (i) { s.nodes[i] = 1; });
        c.nodes_removed.forEach(function (i) { delete s.nodes[i]; });
        c.edges_added.forEach(function (kb) { s.edges[kb[0]] = kb[1]; });
        c.edges_removed.forEach(function (k) { delete s.edges[k]; });
        c.basis_changed.forEach(function (x) { s.edges[x[0]] = x[2]; });
        c.basis_recorded.forEach(function (x) { s.edges[x[0]] = x[1]; });
        Object.keys(c.gaps_opened).forEach(function (r) { (s.gaps[r] = s.gaps[r] || {}); c.gaps_opened[r].forEach(function (i) { s.gaps[r][i] = 1; }); });
        Object.keys(c.gaps_closed).forEach(function (r) { c.gaps_closed[r].forEach(function (i) { if (s.gaps[r]) delete s.gaps[r][i]; }); });
      });
      return s;
    }
    function totals(s) {
      var basis = {}, gaps = {};
      Object.keys(s.edges).forEach(function (k) { basis[s.edges[k]] = (basis[s.edges[k]] || 0) + 1; });
      RULES.forEach(function (r) { gaps[r.id] = r.of === 'edge' ? (basis[r.basis] || 0) : Object.keys(s.gaps[r.id] || {}).length; });
      return { nodes: Object.keys(s.nodes).length, edges: Object.keys(s.edges).length, basis: basis, gaps: gaps };
    }
    function minus(a, b) { return Object.keys(a).filter(function (k) { return !(k in b); }).sort(); }
    function compare(va, vb) {
      var a = stateAt(va), b = stateAt(vb), ch = { from: va, to: vb, before: totals(a), after: totals(b), gaps_opened: {}, gaps_closed: {} };
      ch.nodes_added = minus(b.nodes, a.nodes); ch.nodes_removed = minus(a.nodes, b.nodes);
      ch.edges_added = minus(b.edges, a.edges).map(function (k) { return [k, b.edges[k]]; }); ch.edges_removed = minus(a.edges, b.edges);
      var both = Object.keys(a.edges).filter(function (k) { return k in b.edges && a.edges[k] !== b.edges[k]; }).sort();
      ch.basis_changed = both.filter(function (k) { return a.edges[k] !== 'unrecorded'; }).map(function (k) { return [k, a.edges[k], b.edges[k]]; });
      ch.basis_recorded = both.filter(function (k) { return a.edges[k] === 'unrecorded'; }).map(function (k) { return [k, b.edges[k]]; });
      RULES.forEach(function (r) {
        if (r.of === 'edge') return;
        var o = minus(b.gaps[r.id] || {}, a.gaps[r.id] || {}), c = minus(a.gaps[r.id] || {}, b.gaps[r.id] || {});
        if (o.length) ch.gaps_opened[r.id] = o;
        if (c.length) ch.gaps_closed[r.id] = c;
      });
      return ch;
    }

    function label(i) { return (L[i] || ['', i]); }
    function lab(i) { var x = label(i); return [el('a', { href: UP + 'grc/explore/index.html#focus=' + encodeURIComponent(i) }, x[1]), ' ', el('span', { class: 'small' }, x[0])]; }
    function edgeTxt(k) { var p = k.split(' '), a = p[0], v = p[1], b = p.slice(2).join(' '); return [label(a)[1].slice(0, 60) + ' ', el('i', null, v.replace(/_/g, ' ')), ' ' + label(b)[1].slice(0, 60)]; }
    function listing(items, fmt, cap) {
      cap = cap || 60;
      var ul = el('ul', { class: 'gc-list' });
      items.slice(0, cap).forEach(function (x) { var li = el('li'); [].concat(fmt(x)).forEach(function (c) { li.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); }); ul.appendChild(li); });
      if (items.length > cap) ul.appendChild(el('li', { class: 'small' }, 'and ' + (items.length - cap) + ' more'));
      return ul;
    }
    function delta(x, y) { var d = y - x; return d ? el('span', { class: 'gc-' + (d > 0 ? 'up' : 'down') }, (d > 0 ? '+' : '') + d.toLocaleString('en-GB')) : el('span', { class: 'small' }, 'same'); }
    function draw(ch) {
      pair.textContent = '';
      pair.appendChild(el('h2', null, 'v' + ch.from + ' → v' + ch.to));
      var rows = [['Nodes', ch.before.nodes, ch.after.nodes], ['Edges', ch.before.edges, ch.after.edges]];
      ['source', 'code', 'inferred', 'confirmed', 'unrecorded'].forEach(function (k) {
        var x = ch.before.basis[k] || 0, y = ch.after.basis[k] || 0;
        if (x || y) rows.push([k === 'unrecorded' ? 'Edges with no basis recorded' : 'Edges known as ' + k, x, y]);
      });
      RULES.forEach(function (r) { rows.push(['Gap: ' + r.title, ch.before.gaps[r.id] || 0, ch.after.gaps[r.id] || 0]); });
      var tb = el('tbody');
      rows.forEach(function (r) { tb.appendChild(el('tr', null, el('td', null, r[0]), el('td', null, r[1].toLocaleString('en-GB')), el('td', null, r[2].toLocaleString('en-GB')), el('td', null, delta(r[1], r[2])))); });
      pair.appendChild(el('div', { class: 'tw' }, el('table', { class: 't gc-measures' }, el('thead', null, el('tr', null, el('th', null, 'Measure'), el('th', null, 'v' + ch.from), el('th', null, 'v' + ch.to), el('th', null, 'Change'))), tb)));
      var any = false;
      function h(t) { any = true; pair.appendChild(el('h3', null, t)); }
      if (ch.nodes_added.length) { h('Nodes added: ' + ch.nodes_added.length); pair.appendChild(el('p', { class: 'small' }, count(ch.nodes_added, function (i) { return label(i)[0]; }).map(function (x) { return x[1] + ' ' + x[0]; }).join(', '))); pair.appendChild(listing(ch.nodes_added, lab)); }
      if (ch.nodes_removed.length) { h('Nodes removed: ' + ch.nodes_removed.length); pair.appendChild(listing(ch.nodes_removed, function (i) { return label(i)[1]; })); }
      if (ch.edges_added.length) {
        h('Edges added: ' + ch.edges_added.length);
        pair.appendChild(el('p', { class: 'small' }, count(ch.edges_added, function (kb) { return kb[0].split(' ')[1]; }).map(function (x) { return x[1] + ' ' + x[0].replace(/_/g, ' '); }).join(', ')));
        pair.appendChild(listing(ch.edges_added, function (kb) { return edgeTxt(kb[0]).concat([' ', el('span', { class: 'gx-basis gx-b-' + kb[1] }, kb[1])]); }, 40));
      }
      if (ch.edges_removed.length) { h('Edges removed: ' + ch.edges_removed.length); pair.appendChild(listing(ch.edges_removed, edgeTxt, 40)); }
      if (ch.basis_changed.length) { h('How an edge is known, changed: ' + ch.basis_changed.length); pair.appendChild(listing(ch.basis_changed, function (x) { return edgeTxt(x[0]).concat([': ' + x[1] + ' → ', el('b', null, x[2])]); })); }
      if (ch.basis_recorded.length) { h('Basis recorded for the first time: ' + ch.basis_recorded.length + ' edges'); pair.appendChild(el('p', { class: 'small' }, 'Before, edges carried no basis. Now: ' + count(ch.basis_recorded, function (x) { return x[1]; }).map(function (x) { return x[1] + ' ' + x[0]; }).join(', ') + '.')); }
      [['opened', 'gaps_opened'], ['closed', 'gaps_closed']].forEach(function (w) {
        Object.keys(ch[w[1]]).forEach(function (rid) {
          var r = RULES.filter(function (x) { return x.id === rid; })[0];
          h('Gap ' + w[0] + ': ' + (r ? r.title : rid) + ' (' + ch[w[1]][rid].length + ')'); pair.appendChild(listing(ch[w[1]][rid], lab));
        });
      });
      if (!any) pair.appendChild(el('p', null, 'Nothing in the graph changed between these two releases.'));
    }

    // the picker: two releases, kept in the address
    function sel(id, label) { var s = el('select', { id: id, 'aria-label': label }); VERSIONS.forEach(function (v) { s.appendChild(el('option', { value: v }, 'v' + v)); }); return s; }
    var from = sel('gc-from', 'From release'), to = sel('gc-to', 'To release');
    var latest = changes[changes.length - 1];
    function fromHash() {
      var m = /from=([0-9.]+)/.exec(location.hash), n = /to=([0-9.]+)/.exec(location.hash);
      return [m && VERSIONS.indexOf(m[1]) >= 0 ? m[1] : (latest.against || VERSIONS[0]), n && VERSIONS.indexOf(n[1]) >= 0 ? n[1] : latest.version];
    }
    function go(push) {
      var a = from.value, b = to.value;
      if (cmp(a, b) > 0) { var t = a; a = b; b = t; from.value = a; to.value = b; }
      draw(compare(a, b));
      if (push) history.replaceState(null, '', '#from=' + a + '&to=' + b);
    }
    var p = fromHash(); from.value = p[0]; to.value = p[1];
    from.addEventListener('change', function () { go(true); });
    to.addEventListener('change', function () { go(true); });
    window.addEventListener('hashchange', function () { var q = fromHash(); from.value = q[0]; to.value = q[1]; go(false); });
    root.appendChild(el('label', null, 'Compare ', from)); root.appendChild(el('label', null, ' with ', to));
    if (/from=|to=/.test(location.hash)) go(false);
  }).catch(function () { /* the build's comparison stays */ });
})();
