/* Where a URL a script builds really goes. Loaded first, without defer, in <head> of every page.

   1. The real page. The line moves the address bar to a view (/agencies/as/security/), and the site's security policy
      rules out <base> (base-uri 'none'), so a relative request would resolve against the view and miss. Every script
      resolves against window.P2S_BASE, the page as it was loaded.
   2. The host that serves it. On the newsroom's split sites (the press partitions this site into site, refs, updates
      and team) the press writes a route into each page, <meta name="p2s-route">. With it, assets/ come from the press,
      data/ from the data API, and a page of a section another site owns from that site: one source for every file.
      Without it (this repository's own site), a URL resolves exactly as it always has.

   window.P2S_URL(u) does both; fetch() goes through it, and so do the scripts that import or load other scripts. */
(function () {
  'use strict';
  if (window.P2S_URL) return;
  window.P2S_BASE = window.P2S_BASE || location.href;
  window.P2S_REAL_PATH = window.P2S_REAL_PATH || location.pathname;
  var route = null;
  try {
    var m = document.querySelector('meta[name="p2s-route"]');
    route = m ? JSON.parse(m.getAttribute('content')) : null;
  } catch (e) { route = null; }
  window.P2S_URL = function (u) {
    var url = new URL(u, window.P2S_BASE);
    if (!route || url.origin !== location.origin) return url.href;
    var path = url.pathname.replace(/^\//, ''), seg = path.split('/')[0], tail = url.search + url.hash;
    if (seg === 'assets' && route.assets) return route.assets + path.slice('assets/'.length) + tail;
    if (seg === 'data' && route.data) return route.data + path.slice('data/'.length) + tail;   // every file a script fetches is in the API
    var home = (route.sections && route.sections[seg]) || route.rest;
    return home && home !== route.self ? home + '/' + path + tail : url.href;
  };
  var f = window.fetch;
  if (f) window.fetch = function (input, init) {
    if (typeof input === 'string' || input instanceof URL) input = window.P2S_URL(String(input));
    return f.call(this, input, init);
  };
})();
