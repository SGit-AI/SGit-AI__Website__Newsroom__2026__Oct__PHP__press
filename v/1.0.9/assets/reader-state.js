// php.oct.2026.newsroom.sgit.ai: what you have read, and what changed since. The brief is
// admin/content/briefs/2026-10-22__feeds-the-delta-and-subscriptions.md.
//
// Every item on the site (a fact, a section, a briefing, a story, a question, a source, a dated event) carries a
// hidden marker with its id and the hash of what it says now (<span class="it" data-item data-h>), and
// data/items.json lists them all. This script keeps, in this browser only:
//
//   p2s.reader.v1   { v: 1, items: { id: { h, at } }, visits: { last, prev }, view }
//                   the hash of each item when you marked it read; an item whose hash has moved on since is
//                   "changed", one you never marked is "new". view is how read items are shown: fade, hide or full.
//   sgit.notes.v1   your decisions and notes, as records in the newsroom's format (assets/vault-pane/notes.js on
//                   newsroom.sgit.ai) with one added field, item: { id, at, kind, path, title, item, text, quote }.
//                   kind is a decision (done, read-later, follow-up, not-for-me, more-like-this), a remark (liked,
//                   wrong, fix, idea) or note. The same records will go into your vault when the vault pane comes here.
//
// Nothing is sent anywhere. window.P2SReader is the same store for the feed viewer and your desk.
(function () {
  'use strict';
  var KEY = 'p2s.reader.v1', NOTES = 'sgit.notes.v1', EVENT = 'p2s-reader';
  var html = document.documentElement, root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length), here = html.getAttribute('data-path') || location.pathname;
  var KINDS = [
    ['done', 'Done', 'read it, done with it'], ['read-later', 'Read later', 'come back to this'], ['follow-up', 'Follow up', 'act on this'],
    ['not-for-me', 'Not for me', 'this did not need to reach me'], ['more-like-this', 'More like this', 'more of this, please'],
    ['liked', 'Liked', 'keep this as it is'], ['wrong', 'Wrong', 'something here is not right'], ['fix', 'Fix this', 'broken or rough'],
    ['idea', 'Idea', 'do this next'], ['note', 'Note', 'words of your own']];
  var DECISIONS = ['done', 'read-later', 'follow-up', 'not-for-me', 'more-like-this'];
  var HIDES = ['done', 'not-for-me'];

  // ------------------------------------------------------------------ the store
  function load(k, d) { try { var v = JSON.parse(localStorage.getItem(k) || 'null'); return v || d; } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  var S = load(KEY, null);
  if (!S || S.v !== 1 || typeof S.items !== 'object') S = { v: 1, items: {}, visits: {}, view: 'fade' };
  S.visits = S.visits || {}; S.view = S.view || 'fade';
  var N = load(NOTES, null);
  if (!N || !Array.isArray(N.notes)) N = { v: 1, notes: [] };
  function persist() { save(KEY, S); save(NOTES, { v: 1, notes: N.notes }); try { window.dispatchEvent(new CustomEvent(EVENT)); } catch (e) {} }
  function now() { return new Date().toISOString(); }
  function hex8() { var b = crypto.getRandomValues(new Uint8Array(4)); return Array.prototype.map.call(b, function (x) { return ('0' + x.toString(16)).slice(-2); }).join(''); }

  // A visit is a page view more than 30 minutes after the last one: "since your last visit" means since then.
  (function () {
    var t = Date.now(), last = Date.parse(S.visits.seen || 0) || 0;
    if (!last || t - last > 30 * 60 * 1000) { S.visits.prev = S.visits.last || null; S.visits.last = now(); }
    S.visits.seen = now(); save(KEY, S);
  })();

  function state(id, h) {
    var r = S.items[id];
    if (!r) return 'new';
    return r.h === h ? 'read' : 'changed';
  }
  function markRead(id, h) { S.items[id] = { h: h, at: now() }; }
  function markUnread(id) { delete S.items[id]; }
  function decision(id) {
    for (var i = N.notes.length - 1; i >= 0; i--) { var n = N.notes[i]; if (n.item === id && DECISIONS.indexOf(n.kind) >= 0) return n.cleared ? null : n.kind; }
    return null;
  }
  function notesFor(id) { return N.notes.filter(function (n) { return n.item === id && DECISIONS.indexOf(n.kind) < 0 && !n.cleared; }); }
  function addNote(id, kind, text, title, path) {
    var rec = { id: hex8(), at: now(), kind: kind, path: path || here, title: (title || document.title || '').slice(0, 200), n: null, story: null,
                item: id, text: (text || '').slice(0, 2000), quote: '', persona: null };
    N.notes.push(rec); return rec;
  }
  function clearDecision(id) { N.notes.push({ id: hex8(), at: now(), kind: decision(id) || 'done', item: id, path: here, cleared: true, text: '', quote: '' }); }
  function removeNote(nid) { N.notes = N.notes.filter(function (n) { return n.id !== nid; }); }

  var ITEMS = null, itemsWait = [];
  function items(cb) {
    if (ITEMS) return cb(ITEMS);
    itemsWait.push(cb);
    if (itemsWait.length > 1) return;
    fetch(root + 'data/items.json', { cache: 'no-cache', credentials: 'omit' }).then(function (r) { return r.ok ? r.json() : { items: {} }; })
      .catch(function () { return { items: {} }; }).then(function (j) { ITEMS = j.items || {}; var w = itemsWait; itemsWait = []; w.forEach(function (f) { f(ITEMS); }); });
  }
  function counts(all) {
    var c = { new: 0, changed: 0, read: 0, total: 0 };
    Object.keys(all).forEach(function (id) { var s = state(id, all[id].hash); if (HIDES.indexOf(decision(id)) >= 0 && s !== 'changed') s = 'read'; c[s]++; c.total++; });
    return c;
  }

  window.P2SReader = { KEY: KEY, NOTES: NOTES, EVENT: EVENT, KINDS: KINDS, DECISIONS: DECISIONS, state: state, markRead: markRead, markUnread: markUnread,
    decision: decision, notesFor: notesFor, addNote: addNote, clearDecision: clearDecision, removeNote: removeNote, items: items, counts: counts,
    persist: persist, store: function () { return S; }, notes: function () { return N.notes; },
    replace: function (s, n) { if (s && s.v === 1) S = s; if (n && Array.isArray(n.notes)) N = n; persist(); } };

  // ------------------------------------------------------------------ the page
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function historyFor(id) { return /^(fact|page|briefing|front)-[a-z0-9._-]+$/i.test(id) ? root + 'versions/' + id + '/index.html' : null; }
  var marks = Array.prototype.slice.call(document.querySelectorAll('.it[data-item]'));
  var pageMark = marks.filter(function (m) { return m.getAttribute('data-scope') === 'page'; })[0] || null;
  var blocks = [];
  marks.forEach(function (m) {
    if (m === pageMark) return;
    var b = m.closest('tr, article, li, section, .tile, .qa') || m.parentNode;
    if (blocks.some(function (x) { return x.block === b; })) return;
    blocks.push({ id: m.getAttribute('data-item'), h: m.getAttribute('data-h'), mark: m, block: b });
  });
  var main = document.querySelector('main');
  if (!main) return;

  function titleOf(x) {
    var h = x.block.querySelector('h1, h2, h3, b, a');
    return ((h && h.textContent) || x.block.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 140);
  }
  function decorate(x) {
    var st = state(x.id, x.h), d = decision(x.id);
    x.block.classList.remove('it-new', 'it-changed', 'it-read', 'it-decided');
    x.block.classList.add('it-' + (st === 'read' || (HIDES.indexOf(d) >= 0 && st !== 'changed') ? 'read' : st));
    if (d) x.block.classList.add('it-decided');
    var c = x.ctl;
    if (!c) {
      c = x.ctl = el('span', 'it-ctl');
      x.mark.parentNode.insertBefore(c, x.mark.nextSibling);
    }
    c.textContent = '';
    var read = st === 'read';
    var b = el('button', 'it-b it-tick' + (read ? ' on' : ''), read ? '✓' : '○');
    b.type = 'button'; b.title = read ? 'Read. Mark as unread' : (st === 'changed' ? 'Changed since you read it. Mark as read' : 'New to you. Mark as read');
    b.setAttribute('aria-label', b.title);
    b.addEventListener('click', function (ev) { ev.preventDefault(); ev.stopPropagation(); if (read) markUnread(x.id); else markRead(x.id, x.h); persist(); refresh(); });
    c.appendChild(b);
    if (st === 'changed') {
      var hl = historyFor(x.id), tag = el(hl ? 'a' : 'span', 'it-tag', 'changed since you read it');
      if (hl) tag.href = hl;
      c.appendChild(tag);
    } else if (st === 'new' && S.visits.prev) {
      c.appendChild(el('span', 'it-tag it-tag-new', 'new to you'));
    }
    if (d) c.appendChild(el('span', 'it-tag it-tag-d', (KINDS.filter(function (k) { return k[0] === d; })[0] || [d, d])[1]));
    var more = el('button', 'it-b it-more', '⋯'); more.type = 'button'; more.title = 'Decide, or add a note'; more.setAttribute('aria-label', more.title);
    more.addEventListener('click', function (ev) { ev.preventDefault(); ev.stopPropagation(); menu(x, more); });
    c.appendChild(more);
    var old = x.block.querySelector(':scope > .it-notes, td > .it-notes');
    if (old) old.remove();
    var ns = notesFor(x.id);
    if (ns.length) {
      var box = el('div', 'it-notes');
      ns.forEach(function (n) {
        var p = el('p', 'it-note'); p.appendChild(el('b', null, (KINDS.filter(function (k) { return k[0] === n.kind; })[0] || [0, 'Note'])[1] + ': '));
        p.appendChild(document.createTextNode(n.text || ''));
        var del = el('button', 'it-b it-x', '×'); del.type = 'button'; del.title = 'Delete this note';
        del.addEventListener('click', function (ev) { ev.preventDefault(); removeNote(n.id); persist(); refresh(); });
        p.appendChild(del); box.appendChild(p);
      });
      (c.parentNode.tagName === 'TD' ? c.parentNode : x.block).appendChild(box);
    }
  }

  var open = null;
  function closeMenu() { if (open) { open.remove(); open = null; } }
  document.addEventListener('click', function (ev) { if (open && !open.contains(ev.target)) closeMenu(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') closeMenu(); });
  function menu(x, anchor) {
    closeMenu();
    var m = open = el('div', 'it-menu'); m.setAttribute('role', 'dialog'); m.setAttribute('aria-label', 'Your decision on this item');
    var d = decision(x.id);
    m.appendChild(el('p', 'it-menu-h', titleOf(x)));
    var row = el('div', 'it-menu-row');
    KINDS.forEach(function (k) {
      if (k[0] === 'note') return;
      var b = el('button', 'it-chip' + (d === k[0] ? ' on' : ''), k[1]); b.type = 'button'; b.title = k[2];
      b.addEventListener('click', function (ev) {
        ev.stopPropagation();
        if (DECISIONS.indexOf(k[0]) >= 0) {
          if (d === k[0]) clearDecision(x.id); else { addNote(x.id, k[0], '', titleOf(x)); if (k[0] === 'done' || k[0] === 'not-for-me') markRead(x.id, x.h); }
          persist(); closeMenu(); refresh(); return;
        }
        ta.setAttribute('data-kind', k[0]); ta.placeholder = k[1] + ': ' + k[2]; ta.focus();
      });
      row.appendChild(b);
    });
    m.appendChild(row);
    var ta = el('textarea', 'it-ta'); ta.rows = 3; ta.maxLength = 2000; ta.placeholder = 'A note, a correction, an idea. Kept in this browser.'; ta.setAttribute('data-kind', 'note');
    m.appendChild(ta);
    var ok = el('button', 'it-chip on', 'Keep the note'); ok.type = 'button';
    ok.addEventListener('click', function (ev) { ev.stopPropagation(); var t = ta.value.trim(); if (!t) { ta.focus(); return; } addNote(x.id, ta.getAttribute('data-kind') || 'note', t, titleOf(x)); persist(); closeMenu(); refresh(); });
    m.appendChild(ok);
    m.appendChild(el('p', 'small', 'Nothing leaves this browser. Your desk lists every note and decision, and exports them.'));
    document.body.appendChild(m);
    var r = anchor.getBoundingClientRect(), w = Math.min(340, window.innerWidth - 24);
    m.style.width = w + 'px';
    m.style.left = Math.max(12, Math.min(r.left + window.scrollX - w + r.width, window.scrollX + window.innerWidth - w - 12)) + 'px';
    m.style.top = (r.bottom + window.scrollY + 6) + 'px';
  }

  // How read items are shown: faded, hidden behind one marker per run, or as they are.
  function applyView() {
    html.setAttribute('data-read-view', S.view);
    document.querySelectorAll('.it-run').forEach(function (r) { r.remove(); });
    blocks.forEach(function (x) { x.block.classList.remove('it-gone'); });
    if (S.view !== 'hide') return;
    var run = [];
    function flush() {
      if (!run.length) return;
      var first = run[0], n = run.length, isRow = first.tagName === 'TR';
      var marker = el(isRow ? 'tr' : 'div', 'it-run'), cell = isRow ? el('td') : marker;
      if (isRow) { cell.colSpan = first.children.length || 1; marker.appendChild(cell); }
      var b = el('button', 'it-run-b', n + (n === 1 ? ' item' : ' items') + ' you have read, hidden · show'); b.type = 'button';
      var these = run.slice();
      b.addEventListener('click', function () { these.forEach(function (x) { x.classList.remove('it-gone'); }); marker.remove(); });
      cell.appendChild(b); first.parentNode.insertBefore(marker, first);
      run = [];
    }
    var prevParent = null, prevEl = null;
    blocks.forEach(function (x) {
      var b = x.block, isRead = b.classList.contains('it-read');
      if (!isRead) { flush(); prevEl = null; return; }
      if (run.length && (b.parentNode !== prevParent || b.previousElementSibling !== prevEl)) flush();
      b.classList.add('it-gone'); run.push(b); prevParent = b.parentNode; prevEl = b;
    });
    flush();
  }

  // The strip at the top of every page.
  var strip = el('div', 'rs-strip'); strip.setAttribute('role', 'region'); strip.setAttribute('aria-label', 'What is new to you');
  main.insertBefore(strip, main.firstChild);
  function renderStrip(all) {
    var onPage = { new: 0, changed: 0, read: 0 };
    blocks.forEach(function (x) { var s = state(x.id, x.h); if (HIDES.indexOf(decision(x.id)) >= 0 && s !== 'changed') s = 'read'; onPage[s]++; });
    var c = all ? counts(all) : null;
    strip.textContent = '';
    var p = el('p', 'rs-line');
    var since = S.visits.prev ? new Date(S.visits.prev) : null;
    p.appendChild(el('b', null, since ? 'Since your last visit, ' + since.toLocaleDateString([], { day: 'numeric', month: 'short' }) + ' ' + since.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ': ' : 'Your reading: '));
    if (blocks.length) p.appendChild(document.createTextNode('on this page ' + onPage.new + ' new, ' + onPage.changed + ' changed, ' + onPage.read + ' read'));
    if (c) {
      p.appendChild(document.createTextNode((blocks.length ? '; ' : '') + 'across the site '));
      var a = el('a', null, c.new + ' new and ' + c.changed + ' changed'); a.href = root + 'you/index.html'; p.appendChild(a);
      p.appendChild(document.createTextNode(' of ' + c.total + '.'));
    }
    strip.appendChild(p);
    var row = el('p', 'rs-acts');
    function act(label, title, fn) { var b = el('button', 'rs-b', label); b.type = 'button'; b.title = title; b.addEventListener('click', fn); row.appendChild(b); }
    if (blocks.length || pageMark) act('Mark this page read', 'Everything on this page, at what it says now', function () {
      blocks.forEach(function (x) { markRead(x.id, x.h); }); if (pageMark) markRead(pageMark.getAttribute('data-item'), pageMark.getAttribute('data-h')); persist(); refresh();
    });
    act('Mark everything read', 'Every item on the site, at what it says now: from here on you see only what changes', function () {
      items(function (all) { Object.keys(all).forEach(function (id) { markRead(id, all[id].hash); }); persist(); refresh(); });
    });
    var vs = el('span', 'rs-view'); vs.appendChild(document.createTextNode('Read items: '));
    [['fade', 'fade'], ['hide', 'hide'], ['full', 'show']].forEach(function (v) {
      var b = el('button', 'rs-v' + (S.view === v[0] ? ' on' : ''), v[1]); b.type = 'button'; b.setAttribute('aria-pressed', S.view === v[0] ? 'true' : 'false');
      b.addEventListener('click', function () { S.view = v[0]; persist(); refresh(); });
      vs.appendChild(b);
    });
    row.appendChild(vs);
    var desk = el('a', 'rs-desk', 'Your desk'); desk.href = root + 'you/index.html'; row.appendChild(desk);
    strip.appendChild(row);
    var unreadHere = onPage.new + onPage.changed;
    if (blocks.length && !unreadHere && S.view === 'hide') {
      var done = el('p', 'rs-done', 'You are up to date on this page: everything here is read at what it says now. ');
      var w = el('a', null, 'What changed on the site'); w.href = root + 'whatsnew/index.html'; done.appendChild(w);
      strip.appendChild(done);
    }
  }
  function refresh() { blocks.forEach(decorate); applyView(); renderStrip(ITEMS); }
  refresh();
  items(function () { renderStrip(ITEMS); });
  window.addEventListener('storage', function (e) { if (e.key === KEY || e.key === NOTES) { S = load(KEY, S); N = load(NOTES, N); refresh(); } });
})();
