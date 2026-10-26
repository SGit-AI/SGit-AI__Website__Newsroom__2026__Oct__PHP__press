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

  // A link to a path of the site (team/schedule/x/index.html), resolved where it lives: on this site, or on the site that
  // serves that section (assets/route.js), as the build's links are after the partition.
  function link(path) {
    var u = root() + path;
    try { return window.P2S_URL ? window.P2S_URL(u) : u; } catch (e) { return u; }
  }

  // The build's table(): a <div class="tw"> around a table with the given class, header cells and rows of cells.
  function table(headers, rows, cls) {
    var head = el('tr', {}, headers.map(function (h) { return el('th', {}, [h]); }));
    var body = el('tbody', {}, rows.map(function (r) { return el('tr', {}, r.map(function (c) { return el('td', {}, Array.isArray(c) ? c : [c]); })); }));
    return el('div', { class: 'tw' }, [el('table', { class: cls || 't' }, [el('thead', {}, [head]), body])]);
  }

  // Replace a live container's contents with nodes (a string becomes text). Drawn aside first and swapped in whole, so
  // a container is never left half drawn or empty.
  function fill(box, nodes) {
    var f = document.createDocumentFragment();
    (Array.isArray(nodes) ? nodes : [nodes]).forEach(function (n) {
      if (n == null || n === false) return;
      f.appendChild(typeof n === 'object' ? n : document.createTextNode(String(n)));
    });
    while (box.firstChild) box.removeChild(box.firstChild);
    box.appendChild(f);
  }

  // The build's inline_md(): `code`, **bold**, *italic* and [text](http(s) link), as nodes. The first pattern that
  // matches earliest wins; what is inside bold, italic and a link's text is read again; code is read as text.
  var INLINE = [['code', /`([^`]+)`/], ['b', /\*\*([^*]+)\*\*/], ['i', /(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])/], ['a', /\[([^\]]+)\]\((https?:\/\/[^)\s"<>]+)\)/]];
  function inline(s) {
    var f = document.createDocumentFragment();
    s = String(s == null ? '' : s);
    while (s) {
      var best = null;
      INLINE.forEach(function (p) { var m = p[1].exec(s); if (m && (!best || m.index < best.m.index)) best = { k: p[0], m: m }; });
      if (!best) { f.appendChild(document.createTextNode(s)); break; }
      if (best.m.index) f.appendChild(document.createTextNode(s.slice(0, best.m.index)));
      var k = best.k, m = best.m;
      if (k === 'code') f.appendChild(el('code', {}, [m[1]]));
      else if (k === 'a') { var a = el('a', { href: m[2], rel: 'noopener' }); a.appendChild(inline(m[1])); f.appendChild(a); }
      else { var n = el(k); n.appendChild(inline(m[1])); f.appendChild(n); }
      s = s.slice(m.index + m[0].length);
    }
    return f;
  }

  // The build's render_md_text(): headings (as h4), lists (a line indented two spaces continues its item), paragraphs.
  function md(text) {
    var f = document.createDocumentFragment(), ul = null;
    String(text == null ? '' : text).split(/\r?\n/).forEach(function (line) {
      var h = line.match(/^(#{1,4})\s+(.*)$/);
      if (h) { ul = null; f.appendChild(el('h4', {}, [h[2]])); return; }
      if (/^\s*[-*]\s+/.test(line)) {
        if (!ul) { ul = el('ul'); f.appendChild(ul); }
        var li = el('li'); li.appendChild(inline(line.replace(/^\s*[-*]\s+/, ''))); ul.appendChild(li); return;
      }
      if (ul && line.indexOf('  ') === 0) { var last = ul.lastChild; last.appendChild(document.createTextNode(' ')); last.appendChild(inline(line.trim())); return; }
      ul = null;
      if (line.trim()) { var p = el('p'); p.appendChild(inline(line)); f.appendChild(p); }
    });
    return f;
  }

  // Python's str() of a JSON value, for the few places the build prints one (True, None, 12, 1.5).
  function pyStr(v) {
    if (v === true) return 'True';
    if (v === false) return 'False';
    if (v == null) return 'None';
    return typeof v === 'object' ? JSON.stringify(v) : String(v);
  }

  // The build's stat(): a number over its label.
  function stat(n, label) { return el('div', { class: 'stat' }, [el('b', {}, [String(n)]), el('span', {}, [label])]); }

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

  window.P2S_LIVE = { el: el, href: href, pill: pill, json: json, root: root, stamp: stamp, link: link, table: table, fill: fill, inline: inline, md: md, pyStr: pyStr, stat: stat };
})();
