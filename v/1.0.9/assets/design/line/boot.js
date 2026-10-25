/* The line, before the first paint. Loaded without defer in <head>, so every page is drawn already
   shaped for the reader: no flash of someone else's page, on the first page or the tenth.
   It reads the record, the session, the URL and the referrer, works out the role, the depth and the
   visit moment, and writes them onto <html>. Nothing else; the line's words are line.js's job.
   The ladder it follows is the brief's sections 4 and 5; assets/design/line/engine.js is the source of
   truth and line.js re-derives with it after first paint, so this file can only be early, never wrong. */
(function () {
  'use strict';
  /* The real page's address and every URL a script builds are resolved by assets/route.js, loaded just before this
     file on every page (window.P2S_BASE, window.P2S_URL, the fetch() wrapper). */
  if (!window.P2S_BASE) { window.P2S_BASE = location.href; window.P2S_REAL_PATH = location.pathname; }
  var h = document.documentElement, T = { gap: 30, hour: 60, days: 7, changes: 20, ask: 2, toast: 6 };
  function read(k, s) { try { var v = (s ? sessionStorage : localStorage).getItem(k); return v ? JSON.parse(v) : null; } catch (e) { return null; } }
  var rec = read('p2s.lens'), ses = read('p2s.lens.session', true) || {};
  if (rec && rec.v !== 2) rec = null;                       // the lens's v1 record: start again
  var q = {}; location.search.replace(/^\?/, '').split('&').forEach(function (kv) {
    var p = kv.split('='); if (p[0]) { try { q[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || ''); } catch (e) {} }
  });
  var readers = {}, raw = h.getAttribute('data-line-readers') || '';
  raw.split(',').forEach(function (pair) { var p = pair.split(':'); if (p[0]) readers[p[0]] = p[1]; });
  var ROLES = { exec: 1, general: 1, security: 1, engineer: 1, journalist: 1, researcher: 1, everything: 1 };
  function resolve(id) { return ROLES[id] ? { role: id, reader: null } : readers[id] ? { role: readers[id], reader: id } : null; }

  /* who you start as: a shared link, then the saved view, then a guess, then the Executive */
  var shared = null, start = null;
  if (q.as) { var s = resolve(q.as); if (s) shared = { role: s.role, reader: s.reader, depth: q.depth || null }; }
  if (!shared && ses.shared) shared = ses.shared;
  if (shared && (!rec || rec.role !== shared.role || (rec.reader || null) !== (shared.reader || null))) {
    start = { role: shared.role, reader: shared.reader || null, source: 'shared' };
  } else if (rec) {
    start = { role: rec.role, reader: rec.reader || null, source: rec.source };
    shared = null;
  } else {
    var ref = (document.referrer || '').toLowerCase(), term = (q.q || q.utm_term || '').toLowerCase() + ' ' + ref;
    if (/(cisa\.gov|ncsc\.gov\.uk|cert\.europa\.eu|cert\.ssi\.gouv\.fr|ncsc\.nl|cyber\.gov\.au|ncsc\.govt\.nz|jpcert\.or\.jp|cert\.lv|ncsc\.admin\.ch|acn\.gov\.it|cyber\.gc\.ca)/.test(ref))
      start = { role: 'security', source: 'guess:advisory' };
    else if (/\b8\.\d+\.\d+\b|\bfpm\b|mod_php/.test(term)) start = { role: 'engineer', source: 'guess:search-version' };
    else if (/(openwall\.com|seclists\.org|github\.com\/advisories)/.test(ref)) start = { role: 'researcher', source: 'guess:archive' };
    else if (/(bbc\.|reuters\.|theguardian\.|nytimes\.|wired\.|news\.ycombinator|techcrunch\.|heise\.)/.test(ref)) start = { role: 'general', source: 'guess:news' };
    else start = { role: 'exec', source: 'default' };
    start.reader = null;
  }

  /* which moment this load is */
  var now = Date.now(), moment;
  var asOf = q.asof || ses.asOf || null;
  var changes = 0;                                           // line.js counts them; boot only needs "any"
  try { changes = +(h.getAttribute('data-line-changes') || 0); } catch (e) {}
  if (shared) moment = 'shared';
  else if (asOf) moment = 'past';
  else if (!rec) moment = 'first';
  else if (ses.switchedAt && now - +new Date(ses.switchedAt) < T.toast * 1000) moment = 'switched';
  else {
    var newVisit = (now - +new Date(rec.lastActive)) >= T.gap * 60000;
    var visitNo = rec.visits + (newVisit ? 1 : 0);
    var since = newVisit ? rec.lastActive : rec.lastVisit;
    var awayDays = (now - +new Date(since)) / 86400000;
    if (!rec.confirmed && visitNo === 1) moment = 'first';
    else if (!rec.confirmed && visitNo <= T.ask) moment = 'second';
    else if (changes > T.changes || (changes > 0 && awayDays >= T.days)) moment = 'long';
    else if (changes > 0) moment = 'week';
    else if (!newVisit) moment = 'reading';
    else if (now - +new Date(rec.lastActive) < T.hour * 60000) moment = 'hour';
    else {
      var a = new Date(rec.lastActive), b = new Date(now);
      moment = (a.toDateString() === b.toDateString()) ? 'sameday' : 'reading';
    }
  }

  var depth = (rec && rec.depthSet && rec.depth) || (shared && shared.depth) || h.getAttribute('data-line-depth-' + start.role) || 'plain';
  h.setAttribute('data-role', start.role);
  if (start.reader) h.setAttribute('data-reader', start.reader);
  h.setAttribute('data-depth', depth);
  h.setAttribute('data-moment', moment);
  if (rec && rec.confirmed) h.setAttribute('data-confirmed', '');
  if (shared) h.setAttribute('data-borrowed', 'shared'); else if (asOf) h.setAttribute('data-borrowed', 'past');
  var gate = h.getAttribute('data-line-for');
  if (gate && gate.split(' ').indexOf(start.role) < 0 && (ses.gates || []).indexOf(location.pathname) < 0) h.setAttribute('data-gate', '');
})();
