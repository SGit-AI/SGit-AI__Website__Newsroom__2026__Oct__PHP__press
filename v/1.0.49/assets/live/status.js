/* The status page, live: where every agent is, read from the team repository's records when the page opens
   (records/data/agents-status.json, the conductor's snapshot, and records/data/team.json for the members' pages), so a
   snapshot the conductor releases is on the page a minute or two later, with no build. Draws the build's markup
   (build.py: build_status_page) into data-live="status-..."; the section headings and their notes stay as built. What
   the build drew stays when a fetch fails. Needs assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, boxes = document.querySelectorAll('[data-live^="status-"]');
  if (!L || !boxes.length) return;
  var el = L.el, STATE = { working: 'confirmed', blocked: 'contradicted', 'review ready': 'disputed', completed: 'reported' };
  var ORDER = { blocked: 0, 'review ready': 1, working: 2, completed: 3 };
  var s = function (v) { return v == null ? '' : String(v); };
  Promise.all([L.json('records/data/agents-status.json'), L.json('records/data/team.json').catch(function () { return { members: [] }; })]).then(function (d) {
    var S = d[0], members = {}, last = null;
    if (!S || !Array.isArray(S.agents)) return;
    (d[1].members || []).forEach(function (m) { members[m.id] = m; });
    var who = function (a) { return members[a.member] ? el('a', { href: L.link('team/' + encodeURIComponent(a.member) + '/index.html') }, [s(a.agent)]) : s(a.agent); };
    var ag = S.agents.slice().sort(function (a, b) { var x = (a.state in ORDER ? ORDER[a.state] : 9) - (b.state in ORDER ? ORDER[b.state] : 9); return x || (s(a.last) < s(b.last) ? -1 : s(a.last) > s(b.last) ? 1 : 0); });
    var n = { working: 0, blocked: 0 }, onEd = 0, total = 0;
    S.agents.forEach(function (a) { if (a.state in n) n[a.state]++; if (s(a.on).indexOf('editor') >= 0) onEd++; if (typeof a.cost === 'number') total += a.cost; });
    var rows4 = function (xs, f) { return (Array.isArray(xs) ? xs : []).map(f); };
    var draw = {
      'status-about': function () { return [s(S.about)]; },
      'status-asof': function () { return [el('b', {}, ['As of']), ' ' + s(S.as_of).replace('T', ' ') + ' UTC · ', el('b', {}, ['live site']), ' v' + s(S.live_version)]; },
      'status-stats': function () { return [L.stat(S.agents.length, 'agents'), L.stat(n.working, 'working'), L.stat(n.blocked, 'blocked'), L.stat(onEd, 'waiting on the editor'),
                                           L.stat((S.branches || []).length, 'branches waiting for dev'), L.stat('$' + Math.round(total), 'spent, sessions so far')]; },
      'status-decisions': function () { return el('ol', {}, rows4(S.decisions, function (x) { return el('li', {}, [s(x)]); })); },
      'status-agents': function () { return L.table(['Agent', 'State', 'Last activity (UTC)', 'Last did', 'Waiting for', 'Cost'], ag.map(function (a) {
        return [[who(a)], [el('span', { class: 'st st-' + (STATE[a.state] || 'other') }, [s(a.state)])], s(a.last).replace('T', ' '), s(a.did),
                [s(a.waiting)].concat(a.on ? [el('div', { class: 'note' }, ['on: ' + s(a.on)])] : []), typeof a.cost === 'number' ? '$' + a.cost.toFixed(2) : ''];
      }), 'board'); },
      'status-branches': function () { return L.table(['Branch', 'By', 'Commits ahead', 'What'], rows4(S.branches, function (b) { return [[el('code', {}, [s(b[0])])], s(b[1]), s(b[2]), s(b[3])]; }), 'board'); },
      'status-schedules': function () { return L.table(['Schedule', 'State'], rows4(S.schedules, function (x) { return [s(x[0]), s(x[1])]; })); },
      'status-freshness': function () { return L.table(['Data', 'As of', 'Note'], rows4(S.freshness, function (x) { return [s(x[0]), s(x[1]), s(x[2])]; })); }
    };
    boxes.forEach(function (box) { try {
      var f = draw[box.getAttribute('data-live')];
      if (!f) return;
      L.fill(box, f()); last = box;
    } catch (e) { /* this part keeps what the build drew */ } });
    var tail = document.querySelector('[data-live="status-freshness"]') || last;
    if (tail) L.stamp(tail, "the conductor's snapshot (records/data/agents-status.json in the team repository, as of " + s(S.as_of).replace('T', ' ') + ' UTC)');
  }).catch(function () { /* the page as built stays */ });
})();
