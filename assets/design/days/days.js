/* The days mock-up's renderer (story-site, 27 October 2026). Draws one day (or the last 24 hours) for one reader from
   window.DAYS. Every value reaches the page as a text node; the address keeps the view (#day=6&as=security) so a state
   can be shared. In the real thing the address would be /on/2026-10-26/as/security/ (the router's reserved word "on"). */
(function () {
  'use strict';
  var D = window.DAYS, DAYS = D.days, NOW = Date.parse(D.now);
  var $ = function (s) { return document.querySelector(s); };
  function el(tag, cls, kids) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    (kids || []).forEach(function (k) { if (k != null) n.appendChild(typeof k === 'object' ? k : document.createTextNode(String(k))); });
    return n;
  }
  var WD = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  var MO = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  function dateWords(iso, short) { var d = new Date(iso + 'T12:00Z'); return short ? WD[d.getUTCDay()].slice(0, 3) + ' ' + d.getUTCDate() : WD[d.getUTCDay()] + ' ' + d.getUTCDate() + ' ' + MO[d.getUTCMonth()]; }

  // the view: a day number or "now", and a role
  function read() {
    var h = new URLSearchParams(location.hash.slice(1));
    var day = h.get('day'), as = h.get('as');
    return { day: day === null || day === 'now' ? 'now' : Math.max(0, Math.min(DAYS.length - 1, parseInt(day, 10) || 0)), as: D.roles[as] ? as : 'exec' };
  }
  function go(v) { location.hash = 'day=' + v.day + '&as=' + v.as; }
  var forRole = function (items, as) { return items.filter(function (i) { return as === 'everything' || i.roles.indexOf(as) >= 0; }); };
  var at = function (day, t) { return Date.parse(day.date + 'T' + t + 'Z'); };

  // how much happened, said honestly
  function sizeOf(n, day) {
    if (!n) return ['none', 'Nothing new for you'];
    var big = forRole(day.items, view.as).some(function (i) { return i.big; });
    if (big && n >= 2) return [day.size === 'huge' ? 'huge' : 'big', 'A big day for you'];
    if (big) return ['big', 'One change that matters'];
    if (n <= 2) return ['small', n === 1 ? 'One small change for you' : 'Two small changes for you'];
    return ['big', 'A busy day for you'];
  }

  var view;
  function draw() {
    view = read();
    document.title = (view.day === 'now' ? 'The last 24 hours' : 'Day ' + view.day) + ', for ' + D.roles[view.as].as + ' · Mock-up · PHP October 2026';
    drawWho(); drawStrip();
    if (view.day === 'now') drawNow(); else drawDay(DAYS[view.day]);
  }

  function drawWho() {
    var w = $('.who'); w.textContent = '';
    D.order.forEach(function (r) {
      var b = el('button', null, [D.roles[r].name]); b.type = 'button'; b.setAttribute('aria-pressed', String(r === view.as));
      b.addEventListener('click', function () { go({ day: view.day, as: r }); }); w.appendChild(b);
    });
  }

  function drawStrip() {
    var s = $('.strip'); s.textContent = '';
    var maxN = 1, maxC = 1;
    DAYS.forEach(function (d) { maxN = Math.max(maxN, forRole(d.items, view.as).length); maxC = Math.max(maxC, d.coverage); });
    function tile(href, cur, n, d, l, mine, cov, cls) {
      var a = el('a', cls, []); a.href = href; if (cur) a.setAttribute('aria-current', 'page');
      var bars = el('span', 'bars');
      var i1 = el('i', mine ? null : 'zero'); if (mine) i1.style.height = Math.max(8, Math.round(46 * mine / maxN)) + 'px'; bars.appendChild(i1);
      if (cov != null) { var i2 = el('i', 'cov'); i2.style.height = Math.max(3, Math.round(46 * cov / maxC)) + 'px'; bars.appendChild(i2); }
      a.appendChild(bars); a.appendChild(el('span', 'n', [n])); a.appendChild(el('span', 'd', [d])); a.appendChild(el('span', 'l', [l]));
      return a;
    }
    DAYS.forEach(function (d, k) {
      s.appendChild(tile('#day=' + k + '&as=' + view.as, view.day === k, 'Day ' + d.n, dateWords(d.date, true), d.today ? 'So far' : d.label,
        forRole(d.items, view.as).length, d.today ? null : d.coverage));
    });
    var last = lastDay(), a = tile('#day=now&as=' + view.as, view.day === 'now', 'Now', 'last 24 hours', 'Rolling', last.length, null, 'now');
    a.appendChild(el('span', 'live', ['Live'])); s.appendChild(a);
    s.appendChild(el('p', 'key', [el('span', null, [el('i'), 'news for you, by day']), el('span', null, [el('i', 'cov'), 'articles published (coverage is not news)'])]));
  }

  function itemList(items, day, opts) {
    var ul = el('ul', 'items');
    items.forEach(function (i) {
      if (i.midnight) { ul.appendChild(el('li', 'midnight', [i.midnight])); return; }
      var body = el('div', null, [el('span', 'tag', [i.tag]), el('span', 'x', [i.text])]);
      body.firstChild.dataset.t = i.tag;
      if (i.before) body.appendChild(el('span', 'ba', [el('s', null, [i.before]), ' → ', el('b', null, [i.after])]));
      if (i.learned) body.appendChild(el('span', 'late', ['Happened at ' + i.t + ' UTC on Day ' + i.day + '; the newsroom had it at ' + i.learned + ' UTC.']));
      body.appendChild(el('span', 'src', [i.src]));
      ul.appendChild(el('li', i.big ? 'big' : null, [el('span', 't', [i.t]), body]));
    });
    return ul;
  }

  function tiles(day, prev) {
    var box = el('div', 'tiles');
    D.measures.forEach(function (m) {
      var v = day.state[m.id], p = prev ? prev.state[m.id] : null, moved = prev && v !== p;
      var t = el('div', 'tile ' + (moved ? 'moved' : prev ? 'same' : ''), [el('div', 'q', [m.q]), el('div', 'v', [v])]);
      if (moved) t.appendChild(el('div', 'was', [p]));
      else if (prev) { var since = sinceDay(m.id, day.n); t.appendChild(el('div', 'was', [since === day.n ? '' : 'Unchanged since Day ' + since])); }
      box.appendChild(t);
    });
    return box;
  }
  function sinceDay(id, n) { var v = DAYS[n].state[id], k = n; while (k > 0 && DAYS[k - 1].state[id] === v) k--; return k; }

  function others(day, label) {
    var s = el('section', null, [el('h2', null, [label])]), box = el('div', 'others');
    D.order.forEach(function (r) {
      if (r === view.as || r === 'everything') return;
      var n = forRole(day.items, r).length, b = el('button', null, [D.roles[r].name + ' ', el('b', null, [n ? String(n) : 'nothing'])]);
      b.type = 'button'; if (!n) b.disabled = true;
      b.addEventListener('click', function () { go({ day: view.day, as: r }); }); box.appendChild(b);
    });
    s.appendChild(box); return s;
  }

  function drawDay(day) {
    var m = $('#day'); m.textContent = '';
    var mine = forRole(day.items, view.as), prev = day.n > 0 ? DAYS[day.n - 1] : null, sz = sizeOf(mine.length, day);
    var head = day.headline[view.as] || day.headline._;
    var hero = el('div', 'hero', [
      el('div', 'dayno', [el('small', null, [day.today ? 'Today' : 'Day']), String(day.n)]),
      el('p', 'when', [el('b', null, [dateWords(day.date)]), ' · ' + (day.today ? 'so far, as of 09:10 UTC' : day.label) + ' · for ' + D.roles[view.as].as]),
      el('h1', null, [head]),
      el('p', 'size', [el('span', 'pill ' + sz[0], [sz[1]]),
        mine.length ? (mine.length + (mine.length === 1 ? ' item' : ' items') + ' for you.') : 'This day changed nothing you need to know or do.',
        day.coverage >= 40 && mine.length <= 2 ? ' ' + day.coverage + ' articles were published; most repeated what was known.' : (day.coverage ? ' ' + day.coverage + ' articles published.' : '')])
    ]);
    m.appendChild(hero);
    var left = el('div'), right = el('div');
    var s1 = el('section', null, [el('h2', null, [day.today ? 'So far today, for you' : 'What changed this day, for you'])]);
    if (mine.length) s1.appendChild(itemList(mine.map(function (i) { return Object.assign({ day: day.n }, i); }), day));
    else s1.appendChild(el('div', 'nothing', [el('p', 'big', ['Nothing new for you on Day ' + day.n + '.']),
      el('p', null, ['Everything you needed to know at the end of Day ' + (day.n - 1) + ' still holds. Where it stands is on the right; what happened for other readers is below.'])]));
    left.appendChild(s1);
    left.appendChild(others(day, 'For other readers this day'));
    if (day.coverage) left.appendChild(el('section', 'cov', [el('h2', null, ['Coverage']),
      el('p', null, [day.coverage + ' articles published this day, in ' + (day.coverage > 50 ? 'many languages' : 'a handful of outlets') + '. They are counted, not listed: an article is not news unless it moves one of the measures.'])]));
    right.appendChild(el('section', null, [el('h2', null, [day.today ? 'Where it stands now' : 'Where it stood at the end of Day ' + day.n]), tiles(day, prev)]));
    m.appendChild(el('div', 'cols', [left, right]));
    m.appendChild(pager(day.n));
  }

  function lastDay() {
    var out = [];
    DAYS.forEach(function (d) { forRole(d.items, view.as).forEach(function (i) { var t = at(d, i.t); if (t > NOW - 864e5 && t <= NOW) out.push(Object.assign({ day: d.n, when: t }, i)); }); });
    return out.sort(function (a, b) { return b.when - a.when; });
  }

  function drawNow() {
    var m = $('#day'); m.textContent = '';
    var items = lastDay(), today = DAYS[DAYS.length - 1], yday = DAYS[DAYS.length - 2];
    var lead = items.filter(function (i) { return i.big; })[0];
    var head = lead ? (yday.headline[view.as] || yday.headline._) : (today.headline[view.as] || today.headline._);
    var sz = sizeOf(items.length, lead ? yday : today);
    m.appendChild(el('div', 'hero', [
      el('div', 'dayno', [el('small', null, ['Now']), '24h']),
      el('p', 'when', [el('b', null, ['The last 24 hours']), ' · from 09:10 UTC yesterday (Day 6) to now (Day 7) · for ' + D.roles[view.as].as]),
      el('h1', null, [head]),
      el('p', 'size', [el('span', 'pill ' + sz[0], [sz[1]]), items.length + (items.length === 1 ? ' item' : ' items') + ' for you in the last 24 hours, newest first.'])
    ]));
    var list = [], crossed = false;
    items.forEach(function (i) {
      if (!crossed && i.day < today.n) { list.push({ midnight: 'Midnight UTC · above, Day ' + today.n + ' so far; below, the end of Day ' + yday.n }); crossed = true; }
      list.push(i);
    });
    var left = el('div', null, [el('section', null, [el('h2', null, ['What changed for you, newest first']), itemList(list)]),
      el('section', null, [el('h2', null, ['How the front page chooses']), el('p', 'rule', ['The front page is always the last 24 hours, so it is never empty at midnight. Each day page is a calendar day in UTC, closed at midnight and kept: an item stays on the day it happened, with the time the newsroom learned it when that is later. Last night\'s listing happened on Day 6 at 22:24 and was captured at 00:45 on Day 7: it is on Day 6\'s page, and at the top here.'])])]);
    var right = el('div', null, [el('section', null, [el('h2', null, ['Where it stands now']), tiles(today, DAYS[DAYS.length - 3])]),
      el('p', 'rule', ['Marked: what changed in the last two days.'])]);
    m.appendChild(el('div', 'cols', [left, right]));
    m.appendChild(pager(DAYS.length));
  }

  function pager(n) {
    var p = el('nav', 'pager'), prev = n > 0 ? DAYS[n - 1] : null, next = n < DAYS.length - 1 ? DAYS[n + 1] : null;
    var a = el('a', 'prev', [el('small', null, ['← Earlier']), prev ? 'Day ' + prev.n + ': ' + prev.label : '']); a.href = '#day=' + (n - 1) + '&as=' + view.as; a.hidden = !prev;
    var b = el('a', 'next', [el('small', null, ['Later →']), next ? 'Day ' + next.n + ': ' + (next.today ? 'today so far' : next.label) : 'The last 24 hours']); b.href = '#day=' + (next ? n + 1 : 'now') + '&as=' + view.as;
    b.hidden = view.day === 'now';
    p.appendChild(a); p.appendChild(b); return p;
  }

  document.addEventListener('keydown', function (e) {
    if (e.target.closest && e.target.closest('input,textarea,select')) return;
    var v = read(), last = DAYS.length - 1;
    if (e.key === 'ArrowLeft') go({ day: v.day === 'now' ? last : Math.max(0, v.day - 1), as: v.as });
    else if (e.key === 'ArrowRight') go({ day: v.day === 'now' ? 'now' : v.day === last ? 'now' : v.day + 1, as: v.as });
  });
  window.addEventListener('hashchange', draw);
  draw();
})();
