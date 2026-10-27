/* The schedule, live: the cards, the runs and the messages, read from the team repository's records when the page
   opens (records/index/schedule.json, runs.json and messages.json, written by the team site's deploy), so a card, a run
   record or a message an agent releases is on these pages a minute or two later, with no build. Draws the same markup
   as the build (build.py: build_schedule, sched_runs_table, sched_msgs) into the page's live containers
   (data-live="sched-..."); the day strip, the wiring and the commit notes stay as built. A container keeps what the
   build drew when a fetch fails. Needs assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, boxes = document.querySelectorAll('[data-live^="sched-"]');
  if (!L || !boxes.length) return;
  var el = L.el;
  var STATES = { active: 'confirmed', proposed: 'reported', paused: 'contradicted', ended: 'reported' };
  var OUT = { ok: 'confirmed', idle: 'reported', partial: 'disputed', failed: 'contradicted' };
  var st = function (cls, text) { return el('span', { class: 'st st-' + cls }, [text]); };
  var note = function (text) { return el('div', { class: 'note' }, [text]); };
  var utc = function (s) { return String(s || '').replace('T', ' ').slice(0, 16) + ' UTC'; };

  function took(r) {
    var a = Date.parse(String(r.started || '').replace(/Z$/, '') + 'Z'), b = Date.parse(String(r.finished || '').replace(/Z$/, '') + 'Z');
    return isNaN(a) || isNaN(b) ? '' : Math.round((b - a) / 60000) + ' min';
  }

  var hasCard = {};   // a run's agent links to its schedule page only when it has a card (a new agent's first run can come before it)
  function runsTable(runs, agentCol) {
    if (!runs.length) return el('p', { class: 'small' }, ['No run recorded yet.']);
    var rows = runs.map(function (r) {
      var summary = [r.summary || ''];
      if (r.log) summary.push(el('details', {}, [el('summary', {}, ['log']), el('pre', { class: 'msg' }, [r.log])]));
      var msg = [(r.read || []).length ? r.read.length + ' read' : '', (r.sent || []).length ? r.sent.length + ' sent' : ''].filter(Boolean).join(' ');
      var model = [r.model || ''];
      if (typeof r.cost_usd === 'number') model.push(note('$' + r.cost_usd.toFixed(2)));
      var row = [utc(r.started), [st(OUT[r.outcome] || 'other', r.outcome)], took(r), summary,
                 r.article ? [el('a', { href: L.link('articles/' + encodeURIComponent(r.article) + '/index.html') }, ['the article'])] : '', msg, model];
      return agentCol ? [hasCard[r.agent] ? [el('a', { href: L.link('team/schedule/' + encodeURIComponent(r.agent) + '/index.html') }, [r.agent])] : r.agent].concat(row) : row;
    });
    return L.table((agentCol ? ['Agent'] : []).concat(['Started', 'Outcome', 'Took', 'Summary', 'Left', 'Messages', 'Model, cost']), rows, 'board');
  }

  function msgs(list, runsById) {
    if (!list.length) return el('p', { class: 'small' }, ['No messages.']);
    var f = document.createDocumentFragment();
    list.forEach(function (m) {
      var r = m.read_in && runsById[m.read_in];
      var state = r ? [st('confirmed', 'read'), ' ', el('span', { class: 'small' }, ['in run ' + r.run])] : [st('disputed', 'unread')];
      var kicker = el('p', { class: 'kicker' }, [utc(m.sent) + ' · from ', el('b', {}, [m.from]), ' to ', el('b', {}, [m.to])]
        .concat(m.re ? [' · re ' + m.re] : []).concat([' · ']).concat(state));
      f.appendChild(el('article', { class: 'rel' }, [kicker, el('h3', { id: m.id }, [m.subject]), el('pre', { class: 'msg' }, [m.body]),
        el('p', { class: 'small' }, [el('code', {}, ['records/messages/' + m.box + '/' + m.id + '.md'])])]));
    });
    return f;
  }

  function list(xs, ordered) {
    if (typeof xs === 'string') xs = [xs];                     // a card may hold a line where the template has a list
    if (!Array.isArray(xs)) xs = xs ? [JSON.stringify(xs)] : [];
    if (!xs.length) return el('p', { class: 'small' }, ['none stated']);
    return el(ordered ? 'ol' : 'ul', {}, xs.map(function (v) { return el('li', {}, [typeof v === 'string' ? v : JSON.stringify(v)]); }));
  }

  function card(c) {
    var brief = c.brief ? el('a', { href: L.link('admin/briefs/index.html') + '#' + encodeURIComponent(String(c.brief).split('/').pop().replace(/\.md$/, '')) }, [c.brief]) : 'none yet';
    return el('p', { class: 'kv' }, [el('b', {}, ['Status']), ' ', st(STATES[c.status] || 'other', c.status), ' ' + (c.status_note || ''), el('br'),
      el('b', {}, ['Wakes']), ' ' + (c.times || []).join(', ') + ' (' + (c.days || '') + ', ' + (c.tz || '') + ') · ', el('b', {}, ['model']), ' ' + (c.model || ''), el('br'),
      el('b', {}, ['Runs in']), ' ' + (c.session || ''), el('br'), el('b', {}, ['Brief']), ' ', brief, ' · ', el('b', {}, ['agent behaviour policy']), ' ' + (c.abp || 'none yet'), el('br'),
      el('b', {}, ['Card kept by']), ' ' + (c.kept_by || '') + ', updated ' + (c.updated || '')]);
  }

  function cardsTable(cards, runs, messages) {
    var last = {}, readBy = {};
    runs.forEach(function (r) { if (!last[r.agent]) last[r.agent] = r; (r.read || []).forEach(function (i) { (readBy[r.agent] = readBy[r.agent] || {})[i] = 1; }); });
    var rows = cards.map(function (c) {
      var lr = last[c.agent], unread = messages.filter(function (m) { return (m.box === c.agent || m.box === 'all') && !(readBy[c.agent] || {})[m.id]; }).length;
      return [[el('a', { href: L.link('team/schedule/' + encodeURIComponent(c.agent) + '/index.html') }, [el('b', {}, [c.agent])]), note(c.address || '')], c.objective || '',
        [st(STATES[c.status] || 'other', c.status)].concat(c.status_note ? [note(c.status_note)] : []),
        [(c.times || []).join(', '), note((c.days || '') + ', ' + (c.tz || '') + '; ' + (c.times || []).length + ' a day')], c.model || '',
        lr ? [st(OUT[lr.outcome] || 'other', lr.outcome), note(utc(lr.started))] : [el('span', { class: 'small' }, ['none yet'])], String(unread)];
    });
    return L.table(['Agent', 'Objective', 'Status', 'Wakes', 'Model', 'Last run', 'Unread'], rows, 'board');
  }

  Promise.all([L.json('records/index/schedule.json'), L.json('records/index/runs.json'), L.json('records/index/messages.json')]).then(function (d) {
    var cards = d[0].cards || [], runs = d[1].runs || [], messages = d[2].messages || [], byRun = {}, byAgent = {};
    runs.forEach(function (r) { byRun[r.run] = r; });
    cards.forEach(function (c) { byAgent[c.agent] = c; hasCard[c.agent] = 1; });
    var last = null;
    boxes.forEach(function (box) { try {
      var kind = box.getAttribute('data-live'), a = box.getAttribute('data-agent') || '', n = parseInt(box.getAttribute('data-limit') || '0', 10) || Infinity, c = byAgent[a];
      var mine = function (xs, f) { return xs.filter(f).slice(0, n); };
      if (kind === 'sched-cards') L.fill(box, cardsTable(cards, runs, messages));
      else if (kind === 'sched-runs') L.fill(box, runsTable(mine(runs, function (r) { return !a || r.agent === a; }), !a));
      else if (kind === 'sched-msgs') L.fill(box, msgs(mine(messages, function () { return true; }), byRun));
      else if (kind === 'sched-inbox') L.fill(box, msgs(mine(messages, function (m) { return m.box === a || m.box === 'all'; }), byRun));
      else if (kind === 'sched-outbox') L.fill(box, msgs(mine(messages, function (m) { return m.from === a; }), byRun));
      else if (kind === 'sched-card' && c) L.fill(box, card(c));
      else if (kind === 'sched-wake' && c) L.fill(box, list(c.each_wake, true));
      else if (kind === 'sched-instructions' && c) L.fill(box, el('pre', { class: 'msg' }, [c.instructions || '']));
      else if (kind === 'sched-scope' && c) L.fill(box, [el('h3', {}, ['Reads']), list(c.reads), el('h3', {}, ['Writes']), list(c.writes), el('h3', {}, ['Never']), list(c.never)]);
      else return;
      last = box;
    } catch (e) { /* this container keeps what the build drew */ } });
    if (last) L.stamp(last, cards.length + ' cards, ' + runs.length + ' runs and ' + messages.length + ' messages from records/ in the team repository');
  }).catch(function () { /* the pages as built stay */ });
})();
