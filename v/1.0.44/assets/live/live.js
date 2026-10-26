/* Pages that read their records when they load (phase 2 of the split): the helpers every live view uses.

   A live view fetches the records it shows from the repository that holds them, by URL (records/... is served by the
   team site, data/... by the data API: assets/route.js sends each where it lives), and draws them in the page. The
   page as built is the fallback: if the fetch fails, or scripts are off, the reader sees what the last build saw.

   The browser's counterpart of the build's E() and U(): every value from a record reaches the page as a text node or
   through setAttribute, never through innerHTML, and a link is kept only when it is http(s) or relative. Loaded with
   defer, before the views. */
(function () {
  'use strict';
  if (window.P2S_LIVE) return;

  function href(u) {
    try {
      var x = new URL(String(u), window.P2S_BASE || location.href);
      return (x.protocol === 'https:' || x.protocol === 'http:') ? x.href : null;
    } catch (e) { return null; }
  }

  // el('td', {class: 'x'}, ['text', el(...)]): strings become text nodes; null and false are skipped.
  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v == null || v === false) return;
      if (k === 'href' || k === 'src') { v = href(v); if (!v) return; }
      if (/^on/i.test(k) || k === 'style') return;             // no handlers and no styles from data
      n.setAttribute(k, String(v));
    });
    (kids || []).forEach(function (c) {
      if (c == null || c === false) return;
      n.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
    });
    return n;
  }

  // The build's pill(): the leading status word is the pill when it is one of the status words, else class "other";
  // a long status with a qualifier shows the word as the pill and the qualifier beside it.
  var WORDS = ['confirmed', 'reported', 'disputed', 'contradicted', 'unverified'];
  function pill(status) {
    var s = status == null ? '' : String(status), w = (s.toLowerCase().match(/^[a-z]*/) || [''])[0];
    var cls = WORDS.indexOf(w) >= 0 ? w : 'other', m = cls !== 'other' ? s.match(/^(\w+)([;:,]?\s+[(;:]?[\s\S]*)$/) : null;
    if (m && s.length > 24) {
      var f = document.createDocumentFragment();
      f.appendChild(el('span', { class: 'st st-' + cls }, [m[1]]));
      f.appendChild(document.createTextNode(' '));
      f.appendChild(el('span', { class: 'small' }, [m[2].replace(/^[\s;:,]+|[\s;:,]+$/g, '')]));
      return f;
    }
    return el('span', { class: 'st st-' + cls }, [s]);
  }

  // The site's root, from data-root ("../" repeated), so a view asks for records/... as the build would link it.
  function root() {
    return '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length);
  }

  function json(path) {
    return fetch(root() + path, { cache: 'no-cache', credentials: 'omit' }).then(function (r) {
      if (!r.ok) throw new Error(path + ': HTTP ' + r.status);
      return r.json();
    });
  }

  // A line under a live view: where it was read from, and when.
  function stamp(after, what) {
    var t = new Date(), hh = String(t.getHours()).padStart(2, '0'), mm = String(t.getMinutes()).padStart(2, '0');
    var p = el('p', { class: 'small live-stamp' }, ['Live: ' + what + ', read when this page opened (' + hh + ':' + mm + ').']);
    after.parentNode.insertBefore(p, after.nextSibling);
    return p;
  }

  window.P2S_LIVE = { el: el, href: href, pill: pill, json: json, root: root, stamp: stamp };
})();
