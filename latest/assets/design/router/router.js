/* The router. GitHub Pages answers any address that is not a file with /404.html; this script, loaded by 404.html
   and by the preview cards, reads such an address as a page and a view, and opens the page with that view.

     /agencies/as/security/        the agencies page, for Security
     /as/executive/                the front page, for an Executive
     /playbook/as/cfo/deep/        the playbook, for a CFO, at the deepest wording

   The page is everything before the first reserved word (as, on, vs, since); what follows is the view. The view
   is handed to the line for this visit only (sessionStorage), never saved over the reader's own, and the page is
   opened at its real address; the line then shows the view in the address bar again. An address with no reserved
   word is a real "not found". Briefs: 2026-10-25__brief__the-404-router-and-two-modes.md and
   2026-10-25__brief__urls-personas-and-a-single-page-site.md. Dates (on, vs, since) are read but not applied yet:
   the site does not keep each release's pages to show, so a dated address opens today's page. */
(function () {
  'use strict';
  var RESERVED = { as: 1, on: 1, vs: 1, since: 1 }, DEPTHS = { plain: 1, technical: 1, deep: 1 };
  var ROLE_WORDS = { executive: 'exec', exec: 'exec', general: 'general', security: 'security', engineer: 'engineer',
    journalist: 'journalist', researcher: 'researcher', everything: 'everything' };
  var segs = location.pathname.split('/').filter(Boolean), at = -1;
  for (var i = 0; i < segs.length; i++) { if (RESERVED[segs[i]]) { at = i; break; } }

  function show(id) { var el = document.getElementById(id); if (el) el.hidden = false; }
  if (at < 0) { document.addEventListener('DOMContentLoaded', function () { show('not-found'); }); return; }

  var readers = {};                                      // reader id -> role, from <html data-line-readers>
  (document.documentElement.getAttribute('data-line-readers') || '').split(',').forEach(function (p) {
    var kv = p.split(':'); if (kv[0] && kv[1]) readers[kv[0]] = kv[1];
  });
  var view = {};
  for (var j = at; j < segs.length; j++) {
    var w = segs[j], v = segs[j + 1];
    if (w === 'as' && v) {
      v = v.toLowerCase();
      if (ROLE_WORDS[v]) view.shared = { role: ROLE_WORDS[v], reader: null, depth: null };
      else if (readers[v]) view.shared = { role: readers[v], reader: v, depth: null };
      if (view.shared && DEPTHS[segs[j + 2]]) { view.shared.depth = segs[j + 2]; j++; }
      j++;
    }
  }

  try {
    var s = JSON.parse(sessionStorage.getItem('p2s.lens.session') || '{}') || {};
    if (view.shared) { s.shared = view.shared; delete s.asDone; }
    sessionStorage.setItem('p2s.lens.session', JSON.stringify(s));
  } catch (e) {}

  var base = '/' + segs.slice(0, at).join('/') + (at ? '/' : '');
  location.replace(base + location.search + location.hash);
})();
