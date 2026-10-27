/* The story as days, live (story-site, 27 October 2026; brief records/briefs/2026-10-27__brief__the-story-as-days.md in
   team, the editor's decisions of 27 October). Two places use it:

     the front page   [data-live="days-now"]   the strip of days, then the last 24 hours, for the reader's role
     a day page       [data-live="day"]        /on/<date>/ and /on/<date>/as/<role>/: one calendar day in UTC

   The days are content: site's content/days/story.json (where the story starts, the questions every day ends on) and
   one content/days/<date>.json per day (its items, its headline per role, where it stood at the end). The desk closes a
   day at its first wake after midnight UTC. The role is the line's (<html data-role>), so switching it in the line
   redraws the day. Every value reaches the page as a text node (assets/live/live.js); a malformed day is left out, and
   a container keeps what it had when a fetch fails. Needs assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, front = document.querySelector('[data-live="days-now"]'), dayBox = document.querySelector('[data-live="day"]');
  if (!L || (!front && !dayBox)) return;
  var h = document.documentElement;
  var NAMES = { exec: 'Executive', general: 'General reader', security: 'Security', engineer: 'Engineer', journalist: 'Journalist', researcher: 'Researcher', everything: 'Everything' };
  var AS = { exec: 'an Executive', general: 'a general reader', security: 'Security', engineer: 'an Engineer', journalist: 'a Journalist', researcher: 'a Researcher', everything: 'everything' };
  var WORD = { exec: 'executive', general: 'general', security: 'security', engineer: 'engineer', journalist: 'journalist', researcher: 'researcher', everything: 'everything' };
  var ORDER = ['exec', 'general', 'security', 'engineer', 'journalist', 'researcher', 'everything'];
  var WD = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  var MO = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var DATE = /^\d{4}-\d{2}-\d{2}$/, TIME = /^\d{2}:\d{2}$/, TAGS = { New: 1, Changed: 1, Corrected: 1, Still: 1 };
  var s = function (v) { return v == null ? '' : String(v); };
  function el(tag, cls, kids) { return L.el(tag, cls ? { class: cls } : {}, kids); }

  function words(iso, short) { var d = new Date(iso + 'T12:00Z'); return short ? WD[d.getUTCDay()].slice(0, 3) + ' ' + d.getUTCDate() : WD[d.getUTCDay()] + ' ' + d.getUTCDate() + ' ' + MO[d.getUTCMonth()]; }
  function addDays(iso, n) { var d = new Date(iso + 'T12:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function role() { var r = h.getAttribute('data-role'); return NAMES[r] ? r : 'exec'; }
  function mine(day, r) { return day.items.filter(function (i) { return r === 'everything' || i.roles.indexOf(r) >= 0; }); }
  function at(day, i) { return Date.parse(day.date + 'T' + i.t + ':00Z'); }
  function known(day, i) { var l = Date.parse(s(i.learned)); return isNaN(l) ? at(day, i) : Math.max(l, at(day, i)); }

  // a day file, checked: what is not as the shape says is left out, never half drawn
  function valid(d, date) {
    if (!d || d.date !== date || typeof d.n !== 'number' || !Array.isArray(d.items) || !d.headline || typeof d.state !== 'object') return null;
    d.items = d.items.filter(function (i) { return i && TIME.test(s(i.t)) && TAGS[i.tag] && i.text && Array.isArray(i.roles); });
    return d;
  }

  var STORY = null, DAYS = [];
  function load() {
    return L.json('content/days/story.json').then(function (st) {
      if (!st || !DATE.test(s(st.start)) || !Array.isArray(st.measures)) throw new Error('content/days/story.json: not the shape');
      STORY = st;
      var today = new Date().toISOString().slice(0, 10), dates = [];
      for (var d = st.start; d <= today && dates.length < 60; d = addDays(d, 1)) dates.push(d);
      return Promise.all(dates.map(function (d) { return L.json('content/days/' + d + '.json').then(function (x) { return valid(x, d); }, function () { return null; }); }));
    }).then(function (xs) { DAYS = xs.filter(Boolean); if (!DAYS.length) throw new Error('no days'); });
  }

  // how much happened, said honestly
  function sizeOf(items, day) {
    var n = items.length, big = items.some(function (i) { return i.big; });
    if (!n) return ['none', 'Nothing new for you'];
    if (big && n >= 2) return ['big', 'A big day for you'];
    if (big) return ['big', 'One change that matters'];
    if (n <= 2) return ['small', n === 1 ? 'One small change for you' : 'Two small changes for you'];
    return ['big', 'A busy day for you'];
  }
  var headOf = function (day, r) { return s(day.headline[r] || day.headline._); };
  var dayHref = function (day) { return L.root() + 'on/index.html#' + day.date; };
  var isToday = function (day) { return day.date === new Date().toISOString().slice(0, 10); };

  function strip(cur, r) {
    var maxN = 1, maxC = 1, box = el('nav', 'dz-strip');
    box.setAttribute('aria-label', 'The days of the story');
    DAYS.forEach(function (d) { maxN = Math.max(maxN, mine(d, r).length); maxC = Math.max(maxC, d.coverage || 0); });
    function tile(href, current, n, dd, l, count, cov, cls) {
      var a = L.el('a', { class: cls || null, href: href, 'aria-current': current ? 'page' : null }, []);
      var bars = el('span', 'dz-bars'), i1 = el('i', count ? null : 'zero');
      if (count) i1.style.height = Math.max(8, Math.round(40 * count / maxN)) + 'px';
      bars.appendChild(i1);
      if (cov != null) { var i2 = el('i', 'cov'); i2.style.height = Math.max(3, Math.round(40 * cov / maxC)) + 'px'; bars.appendChild(i2); }
      a.appendChild(bars); a.appendChild(el('span', 'n', [n])); a.appendChild(el('span', 'd', [dd])); a.appendChild(el('span', 'l', [l]));
      return a;
    }
    DAYS.forEach(function (d) {
      var a = tile(dayHref(d), cur === d.date, 'Day ' + d.n, words(d.date, true), isToday(d) ? 'So far' : s(d.label), mine(d, r).length, d.coverage, null);
      a.setAttribute('data-day', d.date); box.appendChild(a);
    });
    var now = tile(L.root() + 'index.html', cur === 'now', 'Now', 'last 24 hours', 'Rolling', lastDay(r).length, null, 'now');
    now.appendChild(el('span', 'live', ['Live'])); box.appendChild(now);
    return box;
  }

  function itemList(items) {
    var ul = el('ul', 'dz-items');
    items.forEach(function (i) {
      if (i.midnight) { ul.appendChild(el('li', 'midnight', [i.midnight])); return; }
      var tag = el('span', 'dz-tag', [i.tag]); tag.setAttribute('data-t', i.tag);
      var body = el('div', null, [tag, el('span', 'dz-x', [i.text])]);
      if (i.before) body.appendChild(el('span', 'dz-ba', [el('s', null, [i.before]), ' → ', el('b', null, [s(i.after)])]));
      if (i.learned && i.day) body.appendChild(el('span', 'dz-late', ['Happened at ' + i.t + ' UTC on Day ' + i.day.n + '; the newsroom had it at ' + s(i.learned).slice(11, 16) + ' UTC on ' + words(s(i.learned).slice(0, 10)) + '.']));
      if (i.src) body.appendChild(el('span', 'dz-src', [i.src]));
      ul.appendChild(el('li', i.big ? 'big' : null, [el('span', 'dz-tm', [i.t]), body]));
    });
    return ul;
  }

  function sinceDay(id, k) { var v = DAYS[k].state[id], j = k; while (j > 0 && DAYS[j - 1].state[id] === v) j--; return DAYS[j].n; }
  function tiles(k, base) {
    var box = el('div', 'dz-tiles'), day = DAYS[k];
    STORY.measures.forEach(function (m) {
      var v = day.state[m.id], p = base != null && base >= 0 ? DAYS[base].state[m.id] : null, moved = p != null && v !== p;
      if (v == null) return;
      var t = el('div', 'dz-tile' + (moved ? ' moved' : p != null ? ' same' : ''), [el('div', 'q', [m.q]), el('div', 'v', [v])]);
      if (moved) t.appendChild(el('div', 'was', ['was ' + p]));
      else if (p != null) t.appendChild(el('div', 'was', ['Unchanged since Day ' + sinceDay(m.id, k)]));
      box.appendChild(t);
    });
    return box;
  }

  function lastDay(r) {
    var out = [], now = Date.now();
    DAYS.forEach(function (d) { mine(d, r).forEach(function (i) { var t = known(d, i); if (t > now - 864e5 && t <= now) out.push(Object.assign({ day: d, when: at(d, i) }, i)); }); });
    return out.sort(function (a, b) { return b.when - a.when; });
  }

  function hero(big, small, when, head, sz, line) {
    return el('div', 'dz-hero', [el('div', 'dz-no', [el('small', null, [small]), big]), el('p', 'dz-when', when),
      el('h1', 'dz-head', [head]), el('p', 'dz-size', [el('span', 'pill ' + sz[0], [sz[1]]), line])]);
  }

  /* ------------------------------------------------------------ the front page: the last 24 hours */
  function drawFront() {
    var r = role(), items = lastDay(r), k = DAYS.length - 1, last = DAYS[k];
    var lead = items.filter(function (i) { return i.big; })[0], headDay = lead ? lead.day : last;
    var list = [], cur = null;
    items.forEach(function (i) {
      if (cur && i.day !== cur) list.push({ midnight: 'Midnight UTC · above, Day ' + cur.n + '; below, Day ' + i.day.n });
      cur = i.day; list.push(i);
    });
    var cutoff = Date.now() - 864e5, base = -1;                   // the last day that had ended 24 hours ago
    DAYS.forEach(function (d, j) { if (Date.parse(addDays(d.date, 1) + 'T00:00:00Z') <= cutoff) base = j; });
    var wrap = el('div', 'dz', [strip('now', r),
      hero('24h', 'Now', [el('b', null, ['The last 24 hours']), ' · Day ' + last.n + ', ' + words(last.date) + ' · for ' + AS[r]],
        headOf(headDay, r), items.length ? sizeOf(items, headDay) : ['none', 'Nothing new for you'],
        items.length ? ' ' + items.length + (items.length === 1 ? ' item' : ' items') + ' for you in the last 24 hours, newest first.' : ' Nothing changed for you in the last 24 hours; where it stands is beside this.'),
      el('div', 'dz-cols', [
        el('div', null, [el('section', null, [el('h2', 'dz-h', ['What changed for you, newest first']),
          items.length ? itemList(list) : el('div', 'dz-nothing', [el('p', 'big', ['Nothing new for you in the last 24 hours.']), el('p', null, ['The days above hold what happened before.'])])])]),
        el('div', null, [el('section', null, [el('h2', 'dz-h', ['Where it stands now']), tiles(k, base)])])])]);
    L.fill(front, wrap);
    front.hidden = false;
  }

  /* ------------------------------------------------------------ a day page: /on/<date>/ */
  var shown = null;
  function wanted() {
    var m = location.hash.match(/^#(\d{4}-\d{2}-\d{2})$/) || location.pathname.match(/\/on\/(\d{4}-\d{2}-\d{2})\//);
    var d = m ? m[1] : shown;
    return DAYS.some(function (x) { return x.date === d; }) ? d : DAYS[DAYS.length - 1].date;
  }
  function address(date, r) {
    var base = '/on/' + date + '/';
    h.setAttribute('data-view-base', base);                      // the line keeps the view under this address
    try { history.replaceState(history.state, '', base + 'as/' + WORD[r] + '/' + location.search); } catch (e) {}
  }
  function others(day, r) {
    var box = el('div', 'dz-others');
    ORDER.forEach(function (o) {
      if (o === r || o === 'everything') return;
      var n = mine(day, o).length;
      box.appendChild(el('span', n ? null : 'none', [NAMES[o] + ' ', el('b', null, [n ? String(n) : 'nothing'])]));
    });
    return box;
  }
  function drawDay() {
    var r = role(), date = wanted(), k = 0;
    DAYS.forEach(function (d, j) { if (d.date === date) k = j; });
    var day = DAYS[k], items = mine(day, r), today = isToday(day), sz = sizeOf(items, day);
    shown = date;
    var state = today ? 'so far' : day.closed ? s(day.label) : 'closing: the desk closes this day at its next wake';
    var cov = day.coverage ? (day.coverage >= 40 && items.length <= 2 ? ' ' + day.coverage + ' articles were published; most repeated what was known.' : ' ' + day.coverage + ' articles published.') : '';
    var pager = el('nav', 'dz-pager');
    if (k > 0) pager.appendChild(L.el('a', { class: 'prev', href: dayHref(DAYS[k - 1]), 'data-day': DAYS[k - 1].date }, [el('small', null, ['← Earlier']), 'Day ' + DAYS[k - 1].n + ': ' + s(DAYS[k - 1].label)]));
    var nx = k < DAYS.length - 1 ? DAYS[k + 1] : null;
    pager.appendChild(nx ? L.el('a', { class: 'next', href: dayHref(nx), 'data-day': nx.date }, [el('small', null, ['Later →']), 'Day ' + nx.n + ': ' + (isToday(nx) ? 'today so far' : s(nx.label))])
      : L.el('a', { class: 'next', href: L.root() + 'index.html' }, [el('small', null, ['Later →']), 'The last 24 hours']));
    var wrap = el('div', 'dz', [strip(date, r),
      hero(String(day.n), today ? 'Today' : 'Day', [el('b', null, [words(day.date)]), ' · ' + state + ' · for ' + AS[r]], headOf(day, r), sz,
        ' ' + (items.length ? items.length + (items.length === 1 ? ' item' : ' items') + ' for you.' : 'This day changed nothing you need to know or do.') + cov),
      el('div', 'dz-cols', [
        el('div', null, [
          el('section', null, [el('h2', 'dz-h', [today ? 'So far today, for you' : 'What changed this day, for you']),
            items.length ? itemList(items.map(function (i) { return Object.assign({ day: day }, i); }))
              : el('div', 'dz-nothing', [el('p', 'big', ['Nothing new for you on Day ' + day.n + '.']),
                el('p', null, ['What you needed to know at the end of Day ' + (day.n - 1) + ' still holds. Where it stood is beside this; what the day held for other readers is below.'])])]),
          el('section', null, [el('h2', 'dz-h', ['For other readers this day']), others(day, r),
            el('p', 'dz-note', ['Choose who you are in the bar above to read the day as them.'])])]),
        el('div', null, [el('section', null, [el('h2', 'dz-h', [today ? 'Where it stands now' : 'Where it stood at the end of Day ' + day.n]), tiles(k, k - 1)])])]),
      pager]);
    L.fill(dayBox, wrap);
    document.title = 'Day ' + day.n + ', ' + words(day.date) + ': ' + headOf(day, r) + ' · PHP October 2026';
    address(date, r);
  }

  function draw() { try { if (front) drawFront(); if (dayBox) drawDay(); } catch (e) { /* what the page had stays */ } }
  load().then(function () {
    draw();
    new MutationObserver(function (ms) { if (ms.some(function (m) { return m.attributeName === 'data-role'; })) draw(); }).observe(h, { attributes: true, attributeFilter: ['data-role'] });
    if (dayBox) {
      document.addEventListener('click', function (e) {               // day to day without leaving the page
        var a = e.target.closest && e.target.closest('a[data-day]');
        if (!a || e.metaKey || e.ctrlKey || e.shiftKey) return;
        e.preventDefault(); shown = a.getAttribute('data-day');
        try { history.pushState(null, '', '/on/' + shown + '/as/' + WORD[role()] + '/'); } catch (x) {}
        drawDay(); window.scrollTo(0, 0);
      });
      window.addEventListener('popstate', function () { var m = location.pathname.match(/\/on\/(\d{4}-\d{2}-\d{2})\//); if (m) { shown = m[1]; drawDay(); } });
      window.addEventListener('hashchange', drawDay);
      document.addEventListener('keydown', function (e) {
        if (e.target.closest && e.target.closest('input,textarea,select,[contenteditable]')) return;
        var k = DAYS.map(function (d) { return d.date; }).indexOf(shown);
        var t = e.key === 'ArrowLeft' ? DAYS[k - 1] : e.key === 'ArrowRight' ? DAYS[k + 1] : null;
        if (!t) return;
        shown = t.date; try { history.pushState(null, '', '/on/' + shown + '/as/' + WORD[role()] + '/'); } catch (x) {}
        drawDay();
      });
    }
  }).catch(function () { /* no days to draw: the page as built stays */ });
})();
