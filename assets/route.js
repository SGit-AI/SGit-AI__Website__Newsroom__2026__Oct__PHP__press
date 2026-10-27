/* Where a URL a script builds really goes. Loaded first, without defer, in <head> of every page.

   1. The real page. The line moves the address bar to a view (/agencies/as/security/), and the site's security policy
      rules out <base> (base-uri 'none'), so a relative request would resolve against the view and miss. Every script
      resolves against window.P2S_BASE, the page as it was loaded.
   2. The host that serves it. On the newsroom's split sites (the press partitions this site into site, refs, updates
      and team) the press writes a route into each page, <meta name="p2s-route">. With it, assets/ come from the press,
      data/ from the data API, and a page of a section another site owns from that site: one source for every file.
      Without it (this repository's own site), a URL resolves exactly as it always has.

   window.P2S_URL(u) does both; fetch() goes through it, and so do the scripts that import or load other scripts. On the
   404 page of a split site it also sends an address another host owns there (window.P2S_LEAVING tells the router). */
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
    var path = url.pathname.replace(/^\//, ''), parts = path.split('/'), seg = parts[0], tail = url.search + url.hash;
    if (seg === 'assets' && route.assets) return route.assets + path.slice('assets/'.length) + tail;
    if (seg === 'data' && route.data) return route.data + path.slice('data/'.length) + tail;   // every file a script fetches is in the API
    // a folder two sites share the top of (site's content/articles/, updates' content/views/) is routed by its first two
    // segments; anything else by its first
    var S = route.sections || {}, at = function (k) { return Object.prototype.hasOwnProperty.call(S, k) && S[k]; };
    var home = (parts.length > 2 && at(parts[0] + '/' + parts[1])) || at(seg) || route.rest;
    return home && home !== route.self ? home + '/' + path + tail : url.href;
  };
  // The 404 page, on a split site: an address of another site's section (a page, its markdown twin, a view address),
  // of an asset or of a data file is sent where it lives now, before the router reads it as a view of a page here.
  // Only to a host the route names: a path such as //other.example/ would otherwise read as another origin.
  if (route && document.documentElement.getAttribute('data-path') === '404.html') {
    var hosts = {}, k;
    [route.self, route.rest, route.assets, route.data].concat(Object.keys(route.sections || {}).map(function (s) { return route.sections[s]; }))
      .forEach(function (h) { try { if (h) hosts[new URL(h).origin] = 1; } catch (e) {} });
    var there = window.P2S_URL(location.pathname.replace(/^\/+/, '/') + location.search + location.hash), origin = '';
    try { origin = new URL(there).origin; } catch (e) { origin = ''; }
    if (origin && origin !== location.origin && hosts[origin]) { window.P2S_LEAVING = there; location.replace(there); }
    // An item this site draws live, newer than its last deploy (no file at its address yet): opened by its kind's view,
    // which draws it from its owner's files and puts this address back in the bar (the brief on centers of gravity).
    var LIVE = [[/^\/admin\/briefs\/([0-9a-z][0-9a-z_.-]*)\/?(?:index\.html)?$/, '/admin/briefs/view/index.html#'],
                [/^\/articles\/([0-9a-z][0-9a-z-]*)\/?(?:index\.html)?$/, '/articles/view/index.html#']];
    if (!window.P2S_LEAVING) LIVE.some(function (k) {
      var m = location.pathname.match(k[0]);
      if (m && m[1] !== 'view' && !/\.(html|md)$/.test(m[1])) { window.P2S_LEAVING = k[1] + m[1]; location.replace(k[1] + encodeURIComponent(m[1])); return true; }
      return false;
    });
  }
  var f = window.fetch;
  if (f) window.fetch = function (input, init) {
    try { if (typeof input === 'string' || input instanceof URL) input = window.P2S_URL(String(input)); } catch (e) { /* an unparsable URL: let fetch reject it */ }
    return f.call(this, input, init);
  };
})();
