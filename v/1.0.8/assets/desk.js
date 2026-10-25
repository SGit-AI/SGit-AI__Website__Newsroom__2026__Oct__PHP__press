// php.oct.2026.newsroom.sgit.ai: your desk (/you/). Everything here is read from this browser's own store
// (assets/reader-state.js, window.P2SReader) and data/items.json; nothing is sent anywhere.
//
// What is new to you and what changed since you read it, by part of the site; what you put aside to read later or
// follow up; every note and decision; the feeds you added in the viewer; and the whole record as one JSON file, to
// keep, to move to another browser, or (when the vault pane comes here) to carry into your vault.
(function () {
  'use strict';
  var R = window.P2SReader, box = document.getElementById('desk');
  if (!R || !box) return;
  var root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length);   // only ever '../' repeated: the depth, never page text
  var ZONES = [['research', 'Research'], ['for-you', 'For you'], ['stories', 'Stories'], ['site', 'About the site']];
  var KW = { fact: 'Fact', page: 'Page', briefing: 'Briefing', front: 'Front page', story: 'Story', question: 'Question', source: 'Source', event: 'Timeline' };
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function link(it, id) { var a = el('a', null, it.title || id); a.href = root + it.path; return a; }

  function render(all) {
    box.textContent = '';
    var c = R.counts(all), S = R.store();
    var top = el('div', 'stats');
    [[c.new, 'new to you'], [c.changed, 'changed since you read them'], [c.read, 'read'], [c.total, 'items on the site']].forEach(function (x) {
      var d = el('div', 'stat'); d.appendChild(el('b', null, String(x[0]))); d.appendChild(el('span', null, x[1])); top.appendChild(d);
    });
    box.appendChild(top);
    var acts = el('p', 'rs-acts');
    function act(label, fn) { var b = el('button', 'rs-b', label); b.type = 'button'; b.addEventListener('click', fn); acts.appendChild(b); }
    act('Mark everything read', function () { Object.keys(all).forEach(function (id) { R.markRead(id, all[id].hash); }); R.persist(); render(all); });
    act('Export your desk (JSON)', function () {
      var doc = { format: 'p2s.desk/1', site: location.host, exported: new Date().toISOString(), reader: R.store(), notes: { v: 1, notes: R.notes() },
                  feeds: (function () { try { return JSON.parse(localStorage.getItem('p2s.feeds.v1') || 'null'); } catch (e) { return null; } })() };
      var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(doc, null, 1)], { type: 'application/json' }));
      a.download = 'php-october-2026-desk-' + new Date().toISOString().slice(0, 10) + '.json'; document.body.appendChild(a); a.click(); a.remove();
    });
    var imp = el('label', 'rs-b rs-file', 'Import a desk file');
    var f = el('input'); f.type = 'file'; f.accept = 'application/json,.json'; f.hidden = true;
    f.addEventListener('change', function () {
      var file = f.files && f.files[0]; if (!file || file.size > 5e6) return;
      file.text().then(function (t) {
        var d = JSON.parse(t);
        if (!d || d.format !== 'p2s.desk/1') throw new Error('not a desk file');
        var S0 = R.store(), mine = R.notes(), ids = {};
        mine.forEach(function (n) { ids[n.id] = 1; });
        Object.keys((d.reader && d.reader.items) || {}).forEach(function (id) { var a = S0.items[id], b = d.reader.items[id]; if (!a || (b.at > a.at)) S0.items[id] = { h: String(b.h), at: String(b.at) }; });
        var merged = mine.concat(((d.notes && d.notes.notes) || []).filter(function (n) { return n && !ids[n.id]; }).map(function (n) {
          return { id: String(n.id), at: String(n.at), kind: String(n.kind), path: String(n.path || ''), title: String(n.title || '').slice(0, 200), item: n.item ? String(n.item) : null, text: String(n.text || '').slice(0, 2000), quote: String(n.quote || '').slice(0, 600), cleared: !!n.cleared };
        }));
        if (d.feeds && Array.isArray(d.feeds.feeds)) { try { localStorage.setItem('p2s.feeds.v1', JSON.stringify(d.feeds)); } catch (e) {} }
        R.replace(S0, { v: 1, notes: merged.sort(function (a, b) { return a.at < b.at ? -1 : 1; }) });
        render(all);
      }).catch(function (e) { alert('That file could not be imported: ' + e.message); });
    });
    imp.appendChild(f); acts.appendChild(imp);
    act('Forget everything here', function () { if (confirm('Forget what you have read, every decision and every note, in this browser?')) { R.replace({ v: 1, items: {}, visits: {}, view: 'fade' }, { v: 1, notes: [] }); render(all); } });
    box.appendChild(acts);

    // what is new and changed, by zone
    ZONES.forEach(function (z) {
      var rows = Object.keys(all).filter(function (id) { return all[id].zone === z[0] && R.state(id, all[id].hash) !== 'read' && ['done', 'not-for-me'].indexOf(R.decision(id)) < 0; });
      var sec = el('section'); sec.id = 'z-' + z[0];
      var h = el('h2', null, z[1] + ': ' + rows.length + ' new or changed'); sec.appendChild(h);
      if (!rows.length) { sec.appendChild(el('p', 'small', 'Nothing new to you here.')); box.appendChild(sec); return; }
      rows.sort(function (a, b) { var x = all[a].date || '', y = all[b].date || ''; return x < y ? 1 : x > y ? -1 : a < b ? -1 : 1; });
      var ul = el('ul', 'desk-list');
      rows.slice(0, 200).forEach(function (id) {
        var it = all[id], st = R.state(id, it.hash), li = el('li', 'it-' + st);
        var b = el('button', 'it-b it-tick', '○'); b.type = 'button'; b.title = 'Mark as read';
        b.addEventListener('click', function () { R.markRead(id, it.hash); R.persist(); li.remove(); h.textContent = z[1] + ': ' + (ul.children.length) + ' new or changed'; });
        li.appendChild(b);
        li.appendChild(el('span', 'it-tag' + (st === 'new' ? ' it-tag-new' : ''), st === 'new' ? 'new' : 'changed'));
        li.appendChild(el('span', 'desk-k', KW[it.kind] || it.kind));
        li.appendChild(link(it, id));
        if (st === 'changed' && it.history) { var d = el('a', 'small', ' what changed'); d.href = root + it.history; li.appendChild(d); }
        if (it.date) li.appendChild(el('span', 'small', ' ' + String(it.date).replace('T', ' ').replace('Z', ' UTC')));
        ul.appendChild(li);
      });
      if (rows.length > 200) sec.appendChild(el('p', 'small', 'The first 200 of ' + rows.length + '.'));
      sec.appendChild(ul); box.appendChild(sec);
    });

    // decisions and notes
    var notes = R.notes().filter(function (n) { return !n.cleared; });
    [['read-later', 'Read later'], ['follow-up', 'Follow up']].forEach(function (k) {
      var ids = {}; notes.forEach(function (n) { if (n.item && R.decision(n.item) === k[0]) ids[n.item] = n; });
      var sec = el('section'); sec.appendChild(el('h2', null, k[1] + ': ' + Object.keys(ids).length));
      var ul = el('ul', 'desk-list');
      Object.keys(ids).forEach(function (id) { var it = all[id], li = el('li'); li.appendChild(it ? link(it, id) : el('span', null, ids[id].title || id)); ul.appendChild(li); });
      if (!ul.children.length) sec.appendChild(el('p', 'small', 'Nothing here. Use the ⋯ beside any item to put it here.')); else sec.appendChild(ul);
      box.appendChild(sec);
    });
    var own = notes.filter(function (n) { return R.DECISIONS.indexOf(n.kind) < 0; });
    var sec = el('section'); sec.appendChild(el('h2', null, 'Your notes: ' + own.length));
    var ul = el('ul', 'desk-list');
    own.slice().reverse().forEach(function (n) {
      var li = el('li'), it = n.item && all[n.item];
      li.appendChild(el('b', null, (R.KINDS.filter(function (k) { return k[0] === n.kind; })[0] || [0, 'Note'])[1] + ' '));
      if (it) li.appendChild(link(it, n.item)); else li.appendChild(el('span', null, n.title || n.item || n.path));
      li.appendChild(el('p', 'it-note', n.text));
      li.appendChild(el('span', 'small', new Date(n.at).toLocaleString()));
      ul.appendChild(li);
    });
    if (!own.length) sec.appendChild(el('p', 'small', 'No notes yet. Any item’s ⋯ menu takes a note, a correction or an idea.')); else sec.appendChild(ul);
    box.appendChild(sec);
  }
  R.items(render);
  window.addEventListener(R.EVENT, function () { R.items(render); });
})();
