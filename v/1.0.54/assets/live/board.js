/* The board, live: every row from the team repository's records/board/, read when the page opens
   (records/index/board.json, written by the team site's deploy), so a row an agent releases is on the board a minute
   or two later, with no build. The table and the counts as built stay when the fetch fails. Needs assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, table = document.querySelector('table.board');
  if (!L || !table) return;
  L.json('records/index/board.json').then(function (d) {
    var rows = (d && Array.isArray(d.rows)) ? d.rows : null;
    if (!rows) return;
    var body = L.el('tbody');
    rows.forEach(function (b) {
      var item = L.el('td', {}, [b.title]);
      if (b.note) item.appendChild(L.el('div', { class: 'note' }, [b.note]));
      body.appendChild(L.el('tr', {}, [L.el('td', {}, [b.id]), item, L.el('td', {}, [L.pill(b.status)]), L.el('td', {}, [b.owner]), L.el('td', {}, [b.version || ''])]));
    });
    table.replaceChild(body, table.tBodies[0]);
    var n = { all: rows.length, open: 0, done: 0 };
    rows.forEach(function (b) { if (b.status === 'open') n.open++; if (b.status === 'done') n.done++; });
    document.querySelectorAll('[data-live-count]').forEach(function (s) {
      var k = s.getAttribute('data-live-count');
      if (k in n) s.textContent = String(n[k]);
    });
    L.stamp(table.closest('.tw') || table, rows.length + ' rows from records/board/ in the team repository');
  }).catch(function () { /* the board as built stays */ });
})();
