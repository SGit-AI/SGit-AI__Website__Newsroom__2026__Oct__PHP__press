/* The briefs, live: the index lists every brief in the team repository's records/briefs/ when the page opens
   (records/index/briefs.json, written by the team site's deploy), so a brief is listed a minute or two after its writer
   releases it, with no build. A brief the last build has not seen yet has no page of its own: its address
   (/admin/briefs/<slug>/) answers with the site's 404 page, whose route (route.js) opens admin/briefs/view/#<slug>, which
   draws it from its own file (records/briefs/<slug>.md, served by the team site) with
   the build's markdown rules (live.js mdDoc). The next round gives it its own page. Draws the build's markup (build.py:
   build_briefs) into data-live="briefs-index" and "brief-view". Needs assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, index = document.querySelector('[data-live="briefs-index"]'), view = document.querySelector('[data-live="brief-view"]');
  if (!L || !(index || view)) return;
  var el = L.el, MONTHS = { '10': 'October', '11': 'November', '12': 'December' }, SLUG = /^[0-9a-z][0-9a-z_.-]*$/;
  var s = function (v) { return v == null ? '' : String(v); };

  function drawIndex(briefs) {
    var out = [], month = null, ol = null, groups = {};
    briefs.forEach(function (m) { var k = s(m.published).slice(0, 7); groups[k] = (groups[k] || 0) + 1; });
    briefs.forEach(function (m) {
      var p = s(m.published), k = p.slice(0, 7);
      if (k !== month) {
        month = k; var n = groups[k], mon = MONTHS[k.slice(5, 7)] || k.slice(5, 7);
        out.push(el('h2', { class: 'brief-month' }, [mon + ' ' + k.slice(0, 4), el('span', {}, [n + ' brief' + (n !== 1 ? 's' : '')])]));
        ol = el('ol', { class: 'brief-list' }); out.push(ol);
      }
      var slug = s(m.slug), href = L.link('admin/briefs/' + encodeURIComponent(slug) + '/index.html');   // newer than the build? its address answers through the 404 page and the view
      var t = [el('b', {}, [s(m.title)])];
      if (m.who) t.push(el('span', { class: 'w' }, [s(m.who).slice(0, 110)]));
      if (m.lead) t.push(el('span', { class: 'l' }, [s(m.lead).slice(0, 190)]));
      ol.appendChild(el('li', { id: slug }, [el('a', { class: 'brief-row', href: href }, [
        el('span', { class: 'd' }, [el('time', { datetime: p }, [p.slice(8, 10) + ' ' + (MONTHS[p.slice(5, 7)] || p.slice(5, 7)).slice(0, 3), el('b', {}, [p.slice(11, 16)])])]),
        el('span', { class: 't' }, t), el('span', { class: 'go', 'aria-hidden': 'true' }, ['→'])])]));
    });
    L.fill(index, out);
    document.querySelectorAll('[data-live-brief-count]').forEach(function (x) { x.textContent = String(briefs.length); });
    L.stamp(index, briefs.length + ' briefs from records/briefs/ in the team repository');
  }

  function drawView(briefs) {
    var slug = decodeURIComponent(location.hash.replace(/^#/, '')), m = briefs.filter(function (b) { return b.slug === slug; })[0];
    if (!SLUG.test(slug) || !m) {                            // only a brief the index names: never a path from the address bar
      L.fill(view, el('p', {}, ['No brief is called that. ', el('a', { href: L.link('admin/briefs/index.html') }, ['All briefs']), '.']));
      return;
    }
    return L.text('records/briefs/' + encodeURIComponent(m.file)).then(function (md) {
      var p = s(m.published);
      document.title = s(m.title) + ' · Briefs';
      try { history.replaceState(null, '', '/admin/briefs/' + encodeURIComponent(m.slug) + '/') } catch (e) {}   // the brief's own address, as the reader asked for it
      L.fill(view, [el('h1', {}, [s(m.title)]),
        el('p', { class: 'kicker' }, ['Published ', el('time', { datetime: p }, [p.slice(0, 10) + ' ' + p.slice(11, 16) + ' UTC']), ' · ', el('code', {}, [s(m.file)]), ' · ',
          el('a', { href: L.link('admin/briefs/index.html') }, ['all briefs'])]),
        el('article', { class: 'brief-full' }, [L.mdDoc(md)]),
        el('p', { class: 'small' }, ['This brief is the file ', el('code', {}, ['records/briefs/' + s(m.file)]), ' in the team repository, published as written. Its own page comes with the next round.'])]);
    });
  }

  L.json('records/index/briefs.json').then(function (d) {
    var briefs = (d && Array.isArray(d.briefs)) ? d.briefs : null;
    if (!briefs) return;
    if (index) drawIndex(briefs);
    if (view) { window.addEventListener('hashchange', function () { drawView(briefs); }); return drawView(briefs); }
  }).catch(function () { /* the page as built stays */ });
})();
