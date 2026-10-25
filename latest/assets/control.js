// /team/control/: the control room, drawn in the browser from data/control.json (built by admin/build/control.py).
// Every string in that file is third-party text: it reaches the page only through textContent / createElement, and
// no href or attribute is ever built from it. Plain ES2017, no framework, no inline script, no network call except
// the one same-origin fetch of the JSON (refreshed every 60 s and when the tab becomes visible).
(function () {
  'use strict';
  var root = document.getElementById('control-root');
  if (!root) return;

  var SRC = root.getAttribute('data-src') || '../../data/control.json';
  var QS = new URLSearchParams(location.search);
  var T0 = Date.now();
  var NOW0 = QS.get('now') ? Date.parse(QS.get('now')) : NaN;   // ?now=ISO pins the clock (used for screenshots/tests)
  var TICKS_KEY = 'php-newsroom.control.ticks.v1', FILTER_KEY = 'php-newsroom.control.filter.v1';
  var ROTATE_MS = 20000, REFRESH_MS = 60000, GRACE = 45 * 60000;
  var STATES = ['blocked', 'working', 'review', 'waiting', 'paused', 'done'];
  var ICON = { working: '\u25B6', blocked: '\u2716', waiting: '\u25F7', review: '\u25CE', done: '\u2713', paused: '\u275A\u275A' };
  var OICON = { ok: '\u2713', idle: '\u2013', partial: '\u25D0', failed: '\u2716' };

  var D = null, tz = 'Europe/London', loadedAt = 0, lastError = '';
  var ui = { owner: 'all', status: 'all', hideDone: false };
  var wall = false, rotate = false, rotIdx = 0, rotTimer = null, prevTheme = null, lastMinute = -1;
  var drawerId = null, drawerOpener = null;
  var els = {};

  // ---------- small helpers ----------
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function add(parent) { for (var i = 1; i < arguments.length; i++) if (arguments[i]) parent.appendChild(arguments[i]); return parent; }
  function now() { return isNaN(NOW0) ? Date.now() : NOW0 + (Date.now() - T0); }
  function ts(s) {   // "iso-ish": 2026-10-24T18:25Z, 2026-10-24 18:25, with or without seconds; no zone means UTC
    if (!s) return NaN;
    s = String(s).trim().replace(' ', 'T');
    if (/T\d\d:\d\d(:\d\d(\.\d+)?)?$/.test(s)) s += 'Z';
    return Date.parse(s);
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  var fmts = {};
  function parts(ms, zone) {
    var f = fmts[zone] || (fmts[zone] = new Intl.DateTimeFormat('en-GB', { timeZone: zone, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    var o = {};
    f.formatToParts(new Date(ms)).forEach(function (p) { o[p.type] = p.value; });
    return { y: +o.year, mo: +o.month, d: +o.day, h: +o.hour % 24, mi: +o.minute, s: +o.second };
  }
  function offsetAt(ms, zone) { var p = parts(ms, zone); return Date.UTC(p.y, p.mo - 1, p.d, p.h, p.mi, p.s) - Math.floor(ms / 1000) * 1000; }
  function wallToMs(y, mo, d, h, mi, zone) { var g = Date.UTC(y, mo - 1, d, h, mi); var ms = g - offsetAt(g, zone); return g - offsetAt(ms, zone); }
  function hm(ms) { var p = parts(ms, tz); return pad(p.h) + ':' + pad(p.mi); }
  function dayName(ms, opts) { try { return new Intl.DateTimeFormat('en-GB', Object.assign({ timeZone: tz }, opts)).format(new Date(ms)); } catch (e) { return ''; } }
  function stamp(ms) { return isNaN(ms) ? 'unknown' : dayName(ms, { weekday: 'short', day: 'numeric', month: 'short' }) + ' ' + hm(ms); }
  function ago(ms) {
    if (isNaN(ms)) return 'unknown';
    var s = Math.round((now() - ms) / 1000);
    if (s < -60) return 'in the future';
    s = Math.max(0, s);
    if (s < 90) return 'just now';
    if (s < 5400) return Math.round(s / 60) + ' min ago';
    if (s < 172800) return Math.round(s / 3600) + ' h ago';
    return Math.round(s / 86400) + ' days ago';
  }
  function money(c) { return c == null || isNaN(+c) ? 'cost n/a' : '$' + (+c).toLocaleString('en-US', { maximumFractionDigits: +c < 10 ? 2 : 0 }); }
  function store(key, val) { try { if (val === undefined) { var r = localStorage.getItem(key); return r ? JSON.parse(r) : null; } localStorage.setItem(key, JSON.stringify(val)); } catch (e) { /* storage may be blocked */ } return null; }
  function arr(x) { return Array.isArray(x) ? x : []; }
  function str(x) { return x == null ? '' : String(x); }
  function stOf(a) { var s = a && a.state; return STATES.indexOf(s) >= 0 ? s : 'none'; }
  function byStart(a, b) { return ts(b.started) - ts(a.started); }
  function isEditor(a) { return /editor/i.test(str(a.on)); }

  // ---------- data relations ----------
  function runsOf(a) {
    var id = str(a.id), st = str(a.stage);
    return arr(D.runs).filter(function (r) { var ra = str(r.agent); return ra && (ra === id || (st && ra === st) || id.indexOf(ra + '-') === 0); }).sort(byStart);
  }
  function runsByAgent(name) { return arr(D.runs).filter(function (r) { return r.agent === name; }).sort(byStart); }
  function schedOf(a) {
    var id = str(a.id), st = str(a.stage);
    return arr(D.schedules).filter(function (s) { var sa = str(s.agent); return sa && (sa === id || (st && sa === st) || id.indexOf(sa + '-') === 0); });
  }
  function stageAgent(stage) {
    var list = arr(D.agents);
    return list.filter(function (a) { return a.id === stage; })[0] || list.filter(function (a) { return a.stage === stage; })[0] || null;
  }
  function activeSched(name) { return arr(D.schedules).filter(function (s) { return s.agent === name && s.status === 'active'; })[0] || null; }

  // ---------- pieces ----------
  function badge(state, label) {
    var b = el('span', 'ctl-badge s-' + state);
    add(b, el('span', null, ICON[state] || '\u25CB'), el('span', null, label || state));
    b.firstChild.setAttribute('aria-hidden', 'true');
    return b;
  }
  function tile(k, v, cls, small) {
    var t = el('div', 'ctl-tile ' + (cls || ''));
    var vv = el('span', 'v', v);
    if (small) vv.appendChild(el('small', null, small));
    add(t, el('span', 'k', k), vv);
    return t;
  }
  function btn(label, handler, pressed, cls) {
    var b = el('button', cls || 'ctl-btn', label);
    b.type = 'button';
    if (pressed != null) b.setAttribute('aria-pressed', pressed ? 'true' : 'false');
    b.addEventListener('click', handler);
    return b;
  }
  function panel(title, sub) {
    var p = el('section', 'ctl-panel'), h = el('h2', null, title);
    if (sub) h.appendChild(el('span', 'sub', sub));
    p.appendChild(h);
    return p;
  }

  // ---------- top strip ----------
  function buildTop() {
    var top = el('div', 'ctl-top'), agents = arr(D.agents);
    var clock = tile('London time', '--:--:--', 'clock');
    clock.setAttribute('role', 'timer');
    els.clock = clock.querySelector('.v');
    els.date = el('small', null, '');
    els.clock.appendChild(els.date);
    top.appendChild(clock);
    top.appendChild(tile('Site version', 'v' + str(D.version).replace(/^v/, ''), ''));
    var asof = ts(D.as_of), age = now() - asof, cls, word;
    if (isNaN(asof)) { cls = 'bad'; word = '\u2716 unknown'; } else if (age < 3600e3) { cls = 'good'; word = '\u2713 fresh'; } else if (age < 4 * 3600e3) { cls = 'warn'; word = '! ageing'; } else { cls = 'bad'; word = '\u2716 stale'; }
    top.appendChild(tile('Data age', isNaN(asof) ? '?' : ago(asof).replace(' ago', ''), cls, word));
    var blocked = agents.filter(function (a) { return a.state === 'blocked'; }).length;
    var ed = agents.filter(isEditor).length;
    var ahead = arr(D.branches).filter(function (b) { return +b[2] > 0; });
    var commits = ahead.reduce(function (n, b) { return n + (+b[2] || 0); }, 0);
    top.appendChild(tile('Blocked', (blocked ? '\u2716 ' : '') + blocked, blocked ? 'hot' : ''));
    top.appendChild(tile('Waiting on editor', String(ed), ed ? 'warn' : ''));
    top.appendChild(tile('Decisions', String(arr(D.decisions).length), ''));
    top.appendChild(tile('Branches ahead', String(ahead.length), '', commits + ' commits'));
    var tools = el('div', 'ctl-tools');
    add(tools, btn('Wall mode', function () { setWall(!wall); }, wall));
    if (wall) add(tools, btn('Auto-rotate', function () { setRotate(!rotate); }, rotate));
    add(tools, btn('Refresh', function () { load(); }));
    top.appendChild(tools);
    return top;
  }

  // ---------- pipeline lane ----------
  function buildLane() {
    var p = panel('Pipeline', 'stage colour is the agent\u2019s state; red dashed = scheduled but no run record in 24 h');
    var lane = el('div', 'ctl-lane');
    lane.setAttribute('role', 'list');
    arr(D.pipeline).forEach(function (stage, i) {
      if (i) { var ar = el('span', 'ctl-arrow'); ar.setAttribute('aria-hidden', 'true'); lane.appendChild(ar); }
      var a = stageAgent(stage), st = a ? stOf(a) : 'none';
      var runs = runsByAgent(stage), last = runs[0];
      var miss = !!activeSched(stage) && !(last && now() - ts(last.started) < 24 * 3600e3);
      var b = el('button', 's-' + st + ' ctl-stage' + (miss ? ' miss' : ''));
      b.type = 'button';
      b.setAttribute('role', 'listitem');
      b.setAttribute('data-fk', 'stage:' + stage);
      add(b, el('span', 'nm', stage));
      var s = el('span', 'stt'); add(s, el('span', null, ICON[st] || '\u25CB'), el('span', null, a ? st : 'no agent')); s.firstChild.setAttribute('aria-hidden', 'true');
      add(b, s);
      var l1 = el('span', 'ln'); add(l1, document.createTextNode('Active '), el('b', null, a ? ago(ts(a.last)) : 'n/a')); add(b, l1);
      var l2 = el('span', 'ln'); add(l2, document.createTextNode('Run record '), el('b', null, last ? ago(ts(last.started)) : 'none')); add(b, l2);
      if (miss) add(b, el('span', 'alert', '\u2716 no run record in 24 h'));
      b.setAttribute('aria-label', stage + ': ' + (a ? st : 'no agent') + '; active ' + (a ? ago(ts(a.last)) : 'n/a') + '; run record ' + (last ? ago(ts(last.started)) : 'none') + (miss ? '; scheduled but no run record in 24 hours' : ''));
      if (a) b.addEventListener('click', function () { openDrawer(a.id, b); }); else b.disabled = true;
      lane.appendChild(b);
    });
    p.appendChild(lane);
    return p;
  }

  // ---------- 24 h timeline ----------
  function buildTimeline() {
    var n = now(), tp = parts(n, tz), scheds = arr(D.schedules).filter(function (s) { return s.status === 'active'; });
    var p = panel('Wake timeline', dayName(n, { weekday: 'long', day: 'numeric', month: 'long' }) + ', ' + tz);
    if (!scheds.length) { p.appendChild(el('p', 'ctl-empty', 'No active schedules.')); return p; }
    var nowPct = (tp.h * 60 + tp.mi + tp.s / 60) / 1440 * 100;
    var g = el('div', 'ctl-tl'), axisLab = el('div', 'lab'), axis = el('div', 'axis');
    for (var h = 0; h <= 24; h += 3) {
      var sp = el('span', h % 6 ? 'alt' : '', pad(h % 24 === 0 && h ? 24 : h));
      sp.style.left = (h / 24 * 100) + '%';
      axis.appendChild(sp);
    }
    var nl = el('span', 'nowlab', '\u25BC now ' + hm(n)); nl.style.left = nowPct + '%'; nl.style.top = '-.1em';
    if (nowPct < 6) nl.style.transform = 'none'; else if (nowPct > 94) nl.style.transform = 'translateX(-100%)';
    nl.style.background = 'var(--panel)';
    axis.appendChild(nl);
    add(g, axisLab, axis);
    var tot = { ok: 0, late: 0 };
    scheds.forEach(function (s) {
      var runs = runsByAgent(s.agent), ok = 0, past = 0;
      var lab = el('div', 'lab', s.agent); lab.title = str(s.agent);
      var track = el('div', 'track');
      var q1 = el('div', 'quiet'); q1.style.left = '0'; q1.style.width = (7 / 24 * 100) + '%';
      var q2 = el('div', 'quiet'); q2.style.left = (22 / 24 * 100) + '%'; q2.style.right = '0';
      add(track, q1, q2);
      arr(s.times).forEach(function (t) {
        var m = /^(\d{1,2}):(\d\d)$/.exec(str(t)); if (!m) return;
        var H = +m[1], M = +m[2], w = wallToMs(tp.y, tp.mo, tp.d, H, M, tz);
        var hit = runs.filter(function (r) { var st = ts(r.started); return st >= w - 60000 && st <= w + GRACE; })[0];
        var cls, glyph, txt;
        if (hit) { cls = hit.outcome === 'failed' || hit.outcome === 'partial' ? 'ok warnrun' : 'ok'; glyph = hit.outcome === 'failed' ? '!' : '\u2713'; txt = 'run record at ' + hm(ts(hit.started)) + ', ' + str(hit.outcome); ok++; past++; tot.ok++; }
        else if (n > w + GRACE) { cls = 'late'; glyph = '\u2715'; txt = 'no run record'; past++; tot.late++; }
        else if (n >= w) { cls = 'due'; glyph = '\u2026'; txt = 'due, waiting for a run record'; }
        else { cls = 'soon'; glyph = ''; txt = 'to come'; }
        var d = el('span', 'ctl-dot ' + cls, glyph);
        d.style.left = ((H * 60 + M) / 1440 * 100) + '%';
        var label = s.agent + ' wake ' + pad(H) + ':' + pad(M) + ': ' + txt;
        d.setAttribute('role', 'img'); d.setAttribute('aria-label', label); d.title = label;
        track.appendChild(d);
      });
      var nw = el('div', 'now'); nw.style.left = nowPct + '%'; track.appendChild(nw);
      if (past) lab.appendChild(el('small', null, ok + '/' + past));
      add(g, lab, track);
    });
    p.appendChild(g);
    var lg = el('div', 'ctl-legend');
    [['ok', '\u2713', 'run record within 45 min'], ['late', '\u2715', 'wake passed, no run record'], ['due', '\u2026', 'due now'], ['soon', '', 'still to come']].forEach(function (x) {
      var i = el('span'); add(i, el('span', 'ctl-dot ' + x[0], x[1]), document.createTextNode(x[2])); lg.appendChild(i);
    });
    var qs = el('span'); add(qs, el('span', 'sw'), document.createTextNode('quiet hours 22:00\u201307:00')); lg.appendChild(qs);
    lg.appendChild(el('span', null, tot.ok + ' met, ' + tot.late + ' missed today'));
    p.appendChild(lg);
    return p;
  }

  // ---------- agent cards ----------
  function buildAgents() {
    var agents = arr(D.agents).slice(), p = panel('Agents', agents.length + ' sessions; select one for the detail');
    var counts = {};
    agents.forEach(function (a) { counts[stOf(a)] = (counts[stOf(a)] || 0) + 1; });
    var legend = el('div', 'ctl-states');
    STATES.forEach(function (s) { if (counts[s]) legend.appendChild(badge(s, s + ' ' + counts[s])); });
    p.appendChild(legend);
    agents.sort(function (a, b) {
      var ra = STATES.indexOf(stOf(a)), rb = STATES.indexOf(stOf(b));
      if (ra < 0) ra = 9; if (rb < 0) rb = 9;
      if (ra !== rb) return ra - rb;
      if (isEditor(a) !== isEditor(b)) return isEditor(a) ? -1 : 1;
      return ts(b.last) - ts(a.last);
    });
    var grid = el('div', 'ctl-grid');
    agents.forEach(function (a) {
      var st = stOf(a), c = el('button', 'ctl-card s-' + st);
      c.type = 'button';
      c.setAttribute('data-fk', 'agent:' + a.id);
      var hd = el('span', 'hd');
      add(hd, el('span', 'nm', str(a.name || a.id)), el('span', 'cost', money(a.cost)));
      add(c, hd, badge(st));
      var wt = str(a.waiting), on = str(a.on);
      if (wt || on) {
        var w = el('span', 'wt' + (isEditor(a) ? ' ed' : ''), (isEditor(a) ? '\u25B2 Waiting on editor' : 'Waiting on ' + (on || 'something')) + (wt ? ': ' + wt : ''));
        w.style.display = '-webkit-box'; w.style.webkitBoxOrient = 'vertical'; w.style.webkitLineClamp = '2'; w.style.overflow = 'hidden';
        c.appendChild(w);
      }
      var lastMs = ts(a.last), old = !isNaN(lastMs) && now() - lastMs > 24 * 3600e3;
      c.appendChild(el('span', 'ag' + (old ? ' old' : ''), (old ? '! ' : '') + 'Last activity ' + ago(lastMs)));
      c.setAttribute('aria-label', str(a.name || a.id) + ', ' + st + ', ' + money(a.cost) + (isEditor(a) ? ', waiting on the editor' : '') + ', last activity ' + ago(lastMs));
      c.addEventListener('click', function () { openDrawer(a.id, c); });
      grid.appendChild(c);
    });
    p.appendChild(grid);
    return p;
  }

  // ---------- queue ----------
  function queueItems() {
    var items = [];
    arr(D.decisions).forEach(function (t) { items.push({ key: 'd:' + str(t).slice(0, 160), title: str(t), owner: 'editor', status: 'decision', kind: 'dec', id: '' }); });
    arr(D.board).forEach(function (b) { items.push({ key: 'b:' + str(b.id), title: str(b.title), owner: str(b.owner) || 'unassigned', status: str(b.status) || 'open', kind: 'row', id: str(b.id) }); });
    return items;
  }
  function buildQueue() {
    var items = queueItems(), ticks = store(TICKS_KEY) || {};
    var p = panel('Your queue', 'tick to clear; ticks stay in this browser only');
    function uniq(k) { var o = {}; items.forEach(function (i) { o[i[k]] = 1; }); return Object.keys(o).sort(); }
    var f = el('div', 'ctl-filters');
    function group(label, key, values) {
      var gl = el('span', 'gl', label); f.appendChild(gl);
      ['all'].concat(values).forEach(function (v) {
        f.appendChild(btn(v === 'all' ? 'all' : v, function () { ui[key] = v; store(FILTER_KEY, ui); render(); }, ui[key] === v, 'ctl-chip'));
      });
    }
    if (uniq('owner').indexOf(ui.owner) < 0) ui.owner = 'all';
    if (uniq('status').indexOf(ui.status) < 0) ui.status = 'all';
    group('Owner', 'owner', uniq('owner'));
    var sep = el('span', 'gl', ' '); f.appendChild(sep);
    group('State', 'status', uniq('status'));
    f.appendChild(btn('hide ticked', function () { ui.hideDone = !ui.hideDone; store(FILTER_KEY, ui); render(); }, ui.hideDone, 'ctl-chip'));
    p.appendChild(f);
    var shown = items.filter(function (i) { return (ui.owner === 'all' || i.owner === ui.owner) && (ui.status === 'all' || i.status === ui.status) && !(ui.hideDone && ticks[i.key]); });
    shown.sort(function (a, b) { return (ticks[a.key] ? 1 : 0) - (ticks[b.key] ? 1 : 0); });
    var open = items.filter(function (i) { return !ticks[i.key]; }).length;
    p.firstChild.appendChild(el('span', 'sub', open + ' open of ' + items.length));
    if (!shown.length) { p.appendChild(el('p', 'ctl-empty', 'Nothing matches the filter.')); return p; }
    var ul = el('ul', 'ctl-q');
    shown.forEach(function (i) {
      var li = el('li'), on = !!ticks[i.key];
      var b = el('button', 'ctl-qi ' + i.kind);
      b.type = 'button';
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.setAttribute('data-fk', 'q:' + i.key);
      var box = el('span', 'box', on ? '\u2713' : ''); box.setAttribute('aria-hidden', 'true');
      var body = el('span'), mt = el('span', 'mt');
      add(mt, el('b', null, i.kind === 'dec' ? 'Decision' : 'Board ' + i.id), document.createTextNode(' \u00B7 ' + i.status + ' \u00B7 ' + i.owner + (on ? ' \u00B7 done' : '')));
      add(body, el('span', 'tt', i.title), mt);
      add(b, box, body);
      b.setAttribute('aria-label', (i.kind === 'dec' ? 'Decision: ' : 'Board ' + i.id + ': ') + i.title + '; ' + i.status + ', ' + i.owner + '; ' + (on ? 'ticked' : 'not ticked'));
      b.addEventListener('click', function () {
        var t = store(TICKS_KEY) || {};
        if (t[i.key]) delete t[i.key]; else t[i.key] = Date.now();
        store(TICKS_KEY, t); render();
      });
      li.appendChild(b); ul.appendChild(li);
    });
    p.appendChild(ul);
    return p;
  }

  function buildLists() {
    var w = el('div', 'ctl-two');
    var pb = panel('Branches ahead of dev', arr(D.branches).length + ' listed');
    var ul = el('ul', 'ctl-list');
    arr(D.branches).forEach(function (b) {
      var li = el('li');
      add(li, el('span', 'a', str(b[0]) + ' (+' + str(b[2]) + ')'), el('span', 'd', str(b[1]) + ' \u2014 ' + str(b[3])));
      ul.appendChild(li);
    });
    if (!ul.firstChild) ul.appendChild(el('li', 'ctl-empty', 'None.'));
    pb.appendChild(ul);
    var pf = panel('Data freshness', 'as exported to the site');
    var uf = el('ul', 'ctl-list');
    arr(D.freshness).forEach(function (f) {
      var li = el('li'), ms = ts(f[1]), old = !isNaN(ms) && now() - ms > 24 * 3600e3;
      add(li, el('span', 'a', str(f[0])), el('span', 'd', (old ? '! ' : '') + (isNaN(ms) ? str(f[1]) : stamp(ms) + ' (' + ago(ms) + ')') + ' \u2014 ' + str(f[2])));
      uf.appendChild(li);
    });
    if (!uf.firstChild) uf.appendChild(el('li', 'ctl-empty', 'None.'));
    pf.appendChild(uf);
    add(w, pb, pf);
    return w;
  }

  // ---------- drawer ----------
  function ensureDrawer() {
    if (els.drawer) return;
    els.veil = el('div', 'ctl-veil'); els.veil.hidden = true;
    els.veil.addEventListener('click', closeDrawer);
    els.drawer = el('aside', 'ctl-drawer'); els.drawer.hidden = true;
    els.drawer.setAttribute('role', 'dialog'); els.drawer.setAttribute('aria-modal', 'true'); els.drawer.tabIndex = -1;
    add(root, els.veil, els.drawer);
  }
  function fillDrawer() {
    var a = arr(D.agents).filter(function (x) { return x.id === drawerId; })[0], d = els.drawer;
    while (d.firstChild) d.removeChild(d.firstChild);
    if (!a) { closeDrawer(); return; }
    var st = stOf(a);
    d.className = 'ctl-drawer s-' + st;
    d.setAttribute('aria-label', 'Detail for ' + str(a.name || a.id));
    var x = btn('\u2715', closeDrawer, null, 'x'); x.setAttribute('aria-label', 'Close detail (Esc)'); x.setAttribute('data-close', '1');
    add(d, x, el('h2', null, str(a.name || a.id)));
    var meta = el('p'); add(meta, badge(st), document.createTextNode('  ' + str(a.member) + ' \u00B7 ' + money(a.cost)));
    d.appendChild(meta);
    d.appendChild(el('p', 'small', 'Last activity ' + stamp(ts(a.last)) + ' London (' + ago(ts(a.last)) + ')'));
    d.appendChild(el('h3', null, 'What it did'));
    d.appendChild(el('p', null, str(a.did) || 'Nothing recorded.'));
    d.appendChild(el('h3', null, 'Waiting' + (a.on ? ' on ' + str(a.on) : '')));
    d.appendChild(el('p', null, str(a.waiting) || 'Nothing.'));
    d.appendChild(el('h3', null, 'Schedule'));
    var ss = schedOf(a);
    if (!ss.length) d.appendChild(el('p', 'ctl-empty', 'No schedule card.'));
    ss.forEach(function (s) {
      d.appendChild(el('p', null, str(s.status) + ': ' + arr(s.times).join(', ') + ' (' + tz + ')'));
      if (s.model) d.appendChild(el('p', 'small', 'Model: ' + str(s.model)));
      if (s.objective) d.appendChild(el('p', 'small', str(s.objective)));
    });
    d.appendChild(el('h3', null, 'Latest runs'));
    var rs = runsOf(a).slice(0, 5);
    if (!rs.length) d.appendChild(el('p', 'ctl-empty', 'No run records.'));
    rs.forEach(function (r) {
      var o = str(r.outcome), box = el('div', 'ctl-run'), r1 = el('div', 'r1');
      var ob = el('span', 'ctl-badge o-' + o);
      add(ob, el('span', null, OICON[o] || '?'), el('span', null, o || 'unknown'));
      add(r1, ob, el('span', 'mono', stamp(ts(r.started))), el('span', 'small', ago(ts(r.started))));
      add(box, r1, el('div', 'sm', str(r.summary)));
      d.appendChild(box);
    });
  }
  function openDrawer(id, opener) {
    ensureDrawer();
    drawerId = id; drawerOpener = opener || document.activeElement;
    fillDrawer();
    if (!drawerId) return;
    els.veil.hidden = false; els.drawer.hidden = false;
    var c = els.drawer.querySelector('[data-close]'); if (c) c.focus();
  }
  function closeDrawer() {
    if (!els.drawer || els.drawer.hidden) return;
    els.drawer.hidden = true; els.veil.hidden = true;
    var fk = drawerOpener && drawerOpener.getAttribute && drawerOpener.getAttribute('data-fk');
    drawerId = null;
    var target = (drawerOpener && document.contains(drawerOpener)) ? drawerOpener : (fk && root.querySelector('[data-fk="' + fk.replace(/"/g, '') + '"]'));
    if (target) target.focus();
    drawerOpener = null;
  }
  document.addEventListener('keydown', function (e) {
    if (!els.drawer || els.drawer.hidden) return;
    if (e.key === 'Escape') { e.preventDefault(); closeDrawer(); return; }
    if (e.key === 'Tab') {   // keep focus inside the open drawer
      var f = els.drawer.querySelectorAll('button, [href], [tabindex]:not([tabindex="-1"])');
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (!els.drawer.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
      else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  // ---------- wall mode and rotation ----------
  var GROUPS = ['Flow', 'Agents', 'Queue'];
  function setWall(on, noUrl) {
    wall = !!on;
    document.body.classList.toggle('ctl-wall', wall);
    var h = document.documentElement;
    if (wall) { if (prevTheme === null) prevTheme = h.getAttribute('data-theme') || ''; h.setAttribute('data-theme', 'night'); }
    else {
      if (prevTheme !== null) { if (prevTheme) h.setAttribute('data-theme', prevTheme); else h.removeAttribute('data-theme'); prevTheme = null; }
      setRotate(false, true);
    }
    if (!noUrl) {
      try { var u = new URL(location.href); if (wall) u.searchParams.set('wall', '1'); else { u.searchParams.delete('wall'); u.searchParams.delete('rotate'); } history.replaceState(null, '', u); } catch (e) { /* ignore */ }
    }
    render();
  }
  function setRotate(on, noRender) {
    rotate = !!on && wall;
    if (rotTimer) { clearInterval(rotTimer); rotTimer = null; }
    if (rotate) rotTimer = setInterval(function () { if (!drawerId && !document.hidden) go(rotIdx + 1); }, ROTATE_MS);
    try { var u = new URL(location.href); if (rotate) u.searchParams.set('rotate', '1'); else u.searchParams.delete('rotate'); history.replaceState(null, '', u); } catch (e) { /* ignore */ }
    if (!noRender) render();
  }
  function go(i) { rotIdx = (i + GROUPS.length) % GROUPS.length; render(); }

  // ---------- render ----------
  function render() {
    if (!D) return;
    var active = document.activeElement, fk = active && active.getAttribute && active.getAttribute('data-fk');
    var scroll = window.pageYOffset;
    var main = el('div', 'ctl-main');
    var msg = el('div', 'ctl-msg'); msg.setAttribute('role', 'status');
    if (lastError) msg.textContent = 'Could not refresh (' + lastError + '). Showing data loaded ' + ago(loadedAt) + '.'; else msg.hidden = true;
    add(main, msg, buildTop());
    var panels = el('div', 'ctl-panels' + (rotate ? ' rotating' : ''));
    var g1 = el('div', 'ctl-group'), g2 = el('div', 'ctl-group'), g3 = el('div', 'ctl-group');
    add(g1, buildLane(), buildTimeline());
    add(g2, buildAgents());
    add(g3, buildQueue(), buildLists());
    [g1, g2, g3].forEach(function (g, i) { g.setAttribute('data-group', GROUPS[i]); if (rotate && i !== rotIdx) g.hidden = true; });
    if (rotate) {
      var rot = el('div', 'ctl-rot');
      GROUPS.forEach(function (n, i) {
        var b = btn((i + 1) + ' ' + n, function () { go(i); }, null, 'ctl-chip pg');
        if (i === rotIdx) b.setAttribute('aria-current', 'true');
        rot.appendChild(b);
      });
      var bar = el('span', 'bar'), fill = el('i'); bar.appendChild(fill); rot.appendChild(bar);
      rot.appendChild(el('span', null, 'next in 20 s'));
      panels.appendChild(rot);
      setTimeout(function () { fill.className = 'run'; }, 30);
    }
    add(panels, g1, g2, g3);
    main.appendChild(panels);
    if (els.boot) { els.boot.remove(); els.boot = null; }
    if (els.main) root.replaceChild(main, els.main); else root.insertBefore(main, root.firstChild);
    els.main = main;
    tick();
    if (fk) { var t = root.querySelector('[data-fk="' + fk.replace(/"/g, '') + '"]'); if (t) t.focus({ preventScroll: true }); }
    window.scrollTo(0, scroll);
    if (drawerId && els.drawer && !els.drawer.hidden) fillDrawer();
  }

  function tick() {
    if (!els.clock) return;
    var n = now(), p = parts(n, tz);
    els.clock.firstChild.nodeValue = pad(p.h) + ':' + pad(p.mi) + ':' + pad(p.s);
    els.date.textContent = dayName(n, { weekday: 'short', day: 'numeric', month: 'short' });
    if (p.mi !== lastMinute) { var first = lastMinute < 0; lastMinute = p.mi; if (!first) render(); }
  }

  // ---------- loading ----------
  function load() {
    var u;
    try { u = new URL(SRC, location.href); u.searchParams.set('_', String(Date.now())); } catch (e) { u = SRC; }
    return fetch(u, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (j) {
      if (!j || typeof j !== 'object') throw new Error('not a control.json');
      D = j; tz = typeof j.tz === 'string' && j.tz ? j.tz : 'Europe/London';
      try { parts(Date.now(), tz); } catch (e) { tz = 'Europe/London'; }
      loadedAt = Date.now(); lastError = '';
      render();
    }).catch(function (e) {
      lastError = e && e.message ? e.message : 'network error';
      if (D) render(); else { if (els.boot) els.boot.remove(); els.boot = el('p', 'ctl-msg', 'The control room data could not be loaded (' + lastError + '). Retrying every minute.'); root.insertBefore(els.boot, root.firstChild); }
    });
  }

  function init() {
    var saved = store(FILTER_KEY);
    if (saved && typeof saved === 'object') { ui.owner = str(saved.owner) || 'all'; ui.status = str(saved.status) || 'all'; ui.hideDone = !!saved.hideDone; }
    document.body.classList.add('ctl-on');
    root.textContent = '';
    ensureDrawer();
    var w = QS.get('wall') === '1';
    if (w) setWall(true, true);
    if (w && QS.get('rotate') === '1') setRotate(true, true);
    setInterval(tick, 1000);
    setInterval(load, REFRESH_MS);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) load(); });
    load();
  }
  init();
})();
