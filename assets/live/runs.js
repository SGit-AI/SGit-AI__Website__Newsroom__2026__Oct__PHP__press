/* The runs page, live: in "Every run", the scheduled wakes are read from the team repository's run records when the
   page opens (records/index/runs.json, written by the team site's deploy); the other rows (releases, source watch
   passes, fact-check runs, synthetic readers) are from other repositories and stay as built. A run record an agent
   releases is on the page a minute or two later, with no build. The Article column: what the build found for that run
   (the articles that name it), else the run's own article when it names one, else "missing" when it changed something
   and "no changes" when it did not. Needs assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, box = document.querySelector('[data-live="runs-all"]');
  if (!L || !box || !box.querySelector('tbody')) return;
  var el = L.el, s = function (v) { return v == null ? '' : String(v); };
  var built = [].slice.call(box.querySelectorAll('tbody tr')), article = {};
  built.forEach(function (tr) { var c = tr.cells; if (c.length > 6 && c[2].textContent === 'Scheduled wake') article[c[3].textContent] = c[6]; });
  Promise.all([L.json('records/index/runs.json'), L.json('records/data/team.json').catch(function () { return { members: [] }; }),
               L.json('records/index/schedule.json').catch(function () { return null; })]).then(function (d) {
    var runs = (d[0] && d[0].runs) || [], members = {}, cards = null;
    if (d[2] && Array.isArray(d[2].cards)) { cards = {}; d[2].cards.forEach(function (c) { cards[c.agent] = 1; }); }
    (d[1].members || []).forEach(function (m) { members[m.id] = m; });
    var who = function (mid) { return members[mid] ? el('a', { href: L.link('team/' + encodeURIComponent(mid) + '/index.html') }, [s(members[mid].name)]) : s(mid); };
    var rows = built.filter(function (tr) { return !(tr.cells.length > 2 && tr.cells[2].textContent === 'Scheduled wake'); })
      .map(function (tr) { return { when: tr.cells[0].textContent, run: tr.cells[3].textContent, tr: tr }; });
    runs.forEach(function (r) {
      var changed = r.outcome === 'ok' || r.outcome === 'partial', art;
      if (article[r.run]) art = [].slice.call(article[r.run].childNodes).map(function (n) { return n.cloneNode(true); });
      else if (r.article) art = [el('a', { href: L.link('articles/' + encodeURIComponent(r.article) + '/index.html') }, ['the article'])];
      else art = [changed ? el('span', { class: 'st st-disputed' }, ['missing']) : el('span', { class: 'small' }, ['no changes, none needed'])];
      var cells = [s(r.started), [who(r.agent)], 'Scheduled wake', [el('code', {}, [s(r.run)])], s(r.summary), changed ? 'yes' : 'no', art,
                   [el('a', { href: L.link(!cards || cards[r.agent] ? 'team/schedule/' + encodeURIComponent(r.agent) + '/index.html' : 'team/schedule/index.html') }, ['output'])]];   // a new agent's first run can come before its card
      rows.push({ when: s(r.started), run: s(r.run), tr: el('tr', {}, cells.map(function (c) { return el('td', {}, Array.isArray(c) ? c : [c]); })) });
    });
    rows.sort(function (a, b) { return a.when < b.when ? 1 : a.when > b.when ? -1 : a.run < b.run ? 1 : a.run > b.run ? -1 : 0; });
    var tbody = el('tbody', {}, rows.map(function (x) { return x.tr; }));
    var table = box.querySelector('table');
    table.replaceChild(tbody, table.tBodies[0]);
    L.stamp(box, runs.length + ' scheduled wakes from records/runs/ in the team repository; the other rows as built');
  }).catch(function () { /* the table as built stays */ });
})();
