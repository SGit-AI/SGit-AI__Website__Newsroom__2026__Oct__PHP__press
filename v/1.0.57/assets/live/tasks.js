/* A team member's tasks, live: the board rows its owner names map to this member (records/data/team.json,
   board_owners), read with the board itself (records/index/board.json, written by the team site's deploy) when the page
   opens, so a row released in team is in its owner's open, waiting or closed tasks a minute or two later, with no build.
   Draws the build's task_table() into data-live="member-tasks"; what the build drew stays when a fetch fails. Needs
   assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, boxes = document.querySelectorAll('[data-live="member-tasks"]');
  if (!L || !boxes.length) return;
  var el = L.el;
  Promise.all([L.json('records/index/board.json'), L.json('records/data/team.json')]).then(function (d) {
    var rows = (d[0] && d[0].rows) || [], owners = (d[1] && d[1].board_owners) || {}, last = null;
    boxes.forEach(function (box) { try {
      var mid = box.getAttribute('data-member'), status = box.getAttribute('data-status');
      var mine = rows.filter(function (b) { return owners[b.owner] === mid && b.status === status; });
      L.fill(box, mine.length ? L.table(['#', 'Task', 'Status', 'Shipped in'], mine.map(function (b) {
        return [String(b.id), [String(b.title)].concat(b.note ? [el('div', { class: 'note' }, [b.note])] : []), [L.pill(b.status)], b.version || ''];
      })) : el('p', { class: 'small' }, ['None.']));
      last = box;
    } catch (e) { /* this table keeps what the build drew */ } });
    if (last) L.stamp(last, 'the tasks from the board (records/board/ in the team repository)');
  }).catch(function () { /* the tables as built stay */ });
})();
