/* An article, live: the page is a frame, and the article is its Markdown, read from site's content/articles/ when the
   page opens (the brief on centers of gravity, 27 October 2026). A writer who corrects a line, adds a correction to the
   front matter or fixes a citation releases site, and the page shows it a minute or two later, with no build. An article
   newer than the last build has no frame of its own yet: its address answers with the site's 404 page, whose route
   (route.js) opens articles/view/#<slug>, which finds its file in content/index/articles.json (written by site's deploy)
   and draws it here the same way.

   The build's build_articles() and render_article(), drawn as nodes: the kicker, title, dek and byline from the front
   matter; the evidence-has-moved note against the vault's latest capture (data/vault.json); each correction<n>; the
   body (## to #### headings, - and 1. lists, | tables, ![figures], !split and !slider before-and-after, ```diff blocks,
   paragraphs; inline `code`, **bold**, *italic*, [[source, source]] citations, [text](/a/page) and [text](https://...)
   links); the glossary's first use of each term and every CVE ID linked (the build's gloss(), from site's
   content/data/glossary.json); and the sources cited. A citation's name and title are the build's when it drew that
   source, else data/sources.json's, fetched only when the article cites a source the build did not draw. Every value
   reaches the page as a text node or through setAttribute (assets/live/live.js). What the build drew stays when a
   fetch fails. Needs assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, box = document.querySelector('[data-live="article"]');
  if (!L || !box) return;
  var el = L.el, s = function (v) { return v == null ? '' : String(v); };
  var ORIGINS = { house: 'House', guest: 'Guest', update: 'Update', interview: 'Interview' };
  var ROLES = { journalist: 'Journalist', historian: 'Historian', 'journalist-historian': 'Journalist and historian', cyber: 'Cyber desk', dev: 'Dev desk' };
  var FLAGSHIP = { 'CVE-2026-109618': 'the out-of-memory flaw', 'CVE-2026-109619': 'the stale global state flaw' };
  var SKIP = { a: 1, code: 1, pre: 1, h1: 1, h2: 1, h3: 1, h4: 1, svg: 1, script: 1, style: 1, th: 1, button: 1, summary: 1, title: 1, label: 1 };
  var CVE = /\bCVE-\d{4}-\d{4,7}\b/g;
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var IMG = '\\/(assets\\/articles\\/[a-z0-9-]+\\/[a-z0-9-]+\\.png)';
  var SPLIT = new RegExp('^!split\\[([^\\]]+)\\]\\(' + IMG + '\\)\\[([^\\]]+)\\]\\(' + IMG + '\\)\\s*$');
  var SLIDER = new RegExp('^!slider\\[([^\\]]+)\\]\\(' + IMG + '\\)\\(' + IMG + '\\)(?:\\s+"([^"]*)")?\\s*$');
  var FIG = /^!\[([^\]]+)\]\(\/(assets\/articles\/[a-z0-9-]+\/[a-z0-9-]+\.png)(?:\s+"([^"]*)")?\)\s*$/;

  function humanTime(at) {
    var m = s(at).match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}:\d{2})/);
    return m ? +m[3] + ' ' + MONTHS[+m[2] - 1] + ' ' + m[1] + ', ' + m[4] + ' UTC' : s(at);
  }

  // The front matter: key: value lines between --- and ---, then the Markdown (the build's load_articles()).
  function parse(text) {
    var m = s(text).replace(/\r\n/g, '\n').match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!m) return null;
    var meta = {};
    m[1].split('\n').forEach(function (l) { var kv = l.match(/^(\w+):\s*(.*)$/); if (kv) meta[kv[1]] = kv[2]; });
    meta.text = m[2];
    meta.cites = [];
    (m[2].match(/\[\[([^\]]+)\]\]/g) || []).forEach(function (g) {
      g.slice(2, -2).split(',').forEach(function (x) { x = x.trim(); if (meta.cites.indexOf(x) < 0) meta.cites.push(x); });
    });
    return meta;
  }

  // The build's short_name(): a source's publisher, shortened for a citation.
  var SHORT = [['US Cybersecurity and Infrastructure Security Agency', 'CISA'], ['UK National Cyber Security Centre', 'NCSC UK'], ['US National Security Agency', 'NSA'],
    ['NIST National Vulnerability Database', 'NVD'], ['Canadian Centre for Cyber Security', 'CCCS'], ['Swiss Federal Office for Cyber Security', 'BACS'],
    ['The PHP Foundation', 'PHP Foundation'], ['PHP Group', 'php.net'], ['oss-security list', 'oss-security'], ['php/php-src on GitHub', 'php-src'],
    ['OpenAI Developer Community', 'OpenAI forum'], ['CVE Program', 'CVE record'], ['ENISA / EU CSIRTs Network', 'ENISA CNW'], ['NSA Cybersecurity', 'NSA Cyber'],
    ["ASD's ACSC", 'ACSC'], ['Alexandre Daubois', 'Daubois'], ['The Hacker News', 'THN'], ['Techzine Global', 'Techzine']];
  function shortName(row) {
    var pub = s(row.publisher || row.slug).replace(/\s*\(.*?\)\s*/g, ' ').trim();
    SHORT.forEach(function (r) { pub = pub.split(r[0]).join(r[1]); });
    if (row.kind === 'social' && /^https?:\/\/(www\.)?(x|twitter)\.com\//.test(s(row.url))) pub += ' on X';
    pub = pub.replace(/\s+,/g, ',');
    if (pub.length <= 34) return pub;
    var cut = pub.slice(0, 34), sp = cut.lastIndexOf(' ');
    return (sp >= 0 ? cut.slice(0, sp) : cut).replace(/,+$/, '') + '…';
  }

  // What the build drew: each source it cited (its name and title), each CVE it linked, each figure's size.
  var drawn = { src: {}, cve: {}, img: {} };
  function learn(root) {
    root.querySelectorAll('a.src[href]').forEach(function (a) {
      var m = a.getAttribute('href').match(/sources\/([^/]+)\/index\.html$/);
      if (m) drawn.src[decodeURIComponent(m[1])] = { short: a.textContent, title: a.getAttribute('title') || '' };
    });
    root.querySelectorAll('a.cve-link[data-term]').forEach(function (a) { drawn.cve[a.getAttribute('data-term')] = a.getAttribute('href'); });
    root.querySelectorAll('img[src][width][height]').forEach(function (i) {
      var m = i.getAttribute('src').match(/(assets\/articles\/[a-z0-9-]+\/[a-z0-9-]+\.png)$/);
      if (m) drawn.img[m[1]] = [i.getAttribute('width'), i.getAttribute('height')];
    });
  }

  function Renderer(sources, terms) {
    var self = this;
    // the build's src_links(): one link per source, its short name, its title on hover; a source not in the manifest marked
    this.src = function (slugs) {
      var f = document.createDocumentFragment();
      slugs.forEach(function (x, i) {
        if (i) f.appendChild(document.createTextNode(' '));
        var row = sources(x);
        f.appendChild(row ? el('a', { class: 'src', href: L.link('sources/' + encodeURIComponent(x) + '/index.html'), title: row.title || x }, [row.short])
                          : el('span', { class: 'src src-missing', title: 'not in the manifest' }, [x]));
      });
      return f;
    };
    // the build's article_inline(): the pattern that matches earliest wins; a link's text and bold and italic are read again
    var INL = [['code', /`([^`]+)`/], ['cite', /\[\[([^\]]+)\]\]/], ['page', /\[([^\]]+)\]\(\/([A-Za-z0-9\/._#=:&,%-]*)\)/],
               ['a', /\[([^\]]+)\]\((https?:\/\/[^)\s"<>]+)\)/], ['b', /\*\*([^*]+)\*\*/], ['i', /\*([^*]+)\*/]];
    this.inline = function (text) {
      var f = document.createDocumentFragment(), t = s(text);
      while (t) {
        var best = null;
        INL.forEach(function (p) { var m = p[1].exec(t); if (m && (!best || m.index < best.m.index)) best = { k: p[0], m: m }; });
        if (!best) { f.appendChild(document.createTextNode(t)); break; }
        var k = best.k, m = best.m, n;
        if (m.index) f.appendChild(document.createTextNode(t.slice(0, m.index)));
        if (k === 'code') n = el('code', {}, [m[1]]);
        else if (k === 'cite') n = el('span', { class: 'refs' }, [self.src(m[1].split(',').map(function (x) { return x.trim(); }))]);
        else if (k === 'page') { n = el('a', { href: L.link(m[2]) }); n.appendChild(self.inline(m[1])); }
        else if (k === 'a') { n = el('a', { href: m[2], rel: 'noopener' }); n.appendChild(self.inline(m[1])); }
        else { n = el(k); n.appendChild(self.inline(m[1])); }
        f.appendChild(n);
        t = t.slice(m.index + m[0].length);
      }
      return f;
    };
    function img(path, cls, alt) {
      var wh = drawn.img[path] || [];
      return el('img', { class: cls, src: L.link(path), alt: alt, width: wh[0], height: wh[1], loading: 'lazy' });
    }
    function cap(tag, attrs, text) { var n = el(tag, attrs); n.appendChild(self.inline(text)); return n; }
    function split(m) {
      var side = function (tag, label, c, path) {
        return el('figure', { class: 'ba-side' }, [el('span', { class: 'ba-tag ba-' + tag }, [label]), img(path, '', label + ': ' + c.replace(/[*`]/g, '')), cap('figcaption', {}, c)]);
      };
      return el('div', { class: 'ba-split ba-wide' }, [side('before', 'Before', m[1], m[2]), side('after', 'After', m[3], m[4])]);
    }
    function slider(m) {
      var parts = m[1].split('|'), alt = parts[0], lo = parts.length > 2 ? parts[1] : 'Before', ln = parts.length > 2 ? parts[2] : 'After';
      var stage = el('div', { class: 'ba-stage', 'data-ba': '' }, [
        el('span', { class: 'ba-cap' }, [el('span', { class: 'ba-tag ba-before' }, [lo])]), img(m[2], 'ba-old', lo + ': ' + alt),
        el('span', { class: 'ba-cap' }, [el('span', { class: 'ba-tag ba-after' }, [ln])]), img(m[3], 'ba-new', ln + ': ' + alt)]);
      var note = el('figcaption', { class: 'ba-note' }, s(m[4]).split(' // ').filter(function (x) { return x.trim(); }).map(function (x) { return cap('p', {}, x.trim()); }));
      return el('figure', { class: 'ba-slider ba-wide' }, [el('div', {}, [stage, el('div', { class: 'ba-ctl', 'data-ba-ctl': '', 'data-left': lo, 'data-right': ln })]), note]);
    }
    function diff(lines) {
      return el('pre', { class: 'diff' }, lines.map(function (l) {
        return el('span', { class: l.charAt(0) === '+' ? 'd-add' : l.charAt(0) === '-' ? 'd-del' : 'd-ctx' }, [l || ' ']);
      }));
    }
    // the build's render_article()
    this.body = function (text) {
      var f = document.createDocumentFragment(), lst = null, rows = [], dl = null;
      var flush = function () {
        if (!rows.length) return;
        f.appendChild(L.table(rows[0].map(self.inline), rows.slice(1).map(function (r) { return r.map(self.inline); })));
        rows = [];
      };
      s(text).split(/\r?\n/).forEach(function (line) {
        if (dl) { if (line.trim() === '```') { f.appendChild(diff(dl)); dl = null; } else dl.push(line); return; }
        if (line.trim() === '```diff') { flush(); lst = null; dl = []; return; }
        var sp = line.match(SPLIT), sl = line.match(SLIDER);
        if (sp || sl) { flush(); lst = null; f.appendChild(sp ? split(sp) : slider(sl)); return; }
        if (line.trim().charAt(0) === '|') {
          lst = null;
          var cells = line.trim().replace(/^\|+|\|+$/g, '').split('|').map(function (c) { return c.trim(); });
          if (!cells.every(function (c) { return /^:?-+:?$/.test(c); })) rows.push(cells);
          return;
        }
        flush();
        var fig = line.match(FIG);
        if (fig) {
          lst = null;
          f.appendChild(el('figure', { class: 'shot' }, [img(fig[2], null, fig[1]), fig[3] ? cap('figcaption', {}, fig[3]) : null]));
          return;
        }
        var h = line.match(/^(#{2,4})\s+(.*)$/), item = line.match(/^(?:-|\d+\.)\s+(.*)$/);
        var kind = item ? (/^\d+\./.test(line) ? 'ol' : 'ul') : null;
        if (lst && kind !== lst.tagName.toLowerCase()) lst = null;
        if (h) f.appendChild(cap('h' + h[1].length, {}, h[2]));
        else if (item) { if (!lst) { lst = el(kind); f.appendChild(lst); } lst.appendChild(cap('li', {}, item[1])); }
        else if (line.trim()) f.appendChild(cap('p', {}, line));
      });
      flush();
      if (dl) f.appendChild(diff(dl));
      return f;
    };
    // the build's gloss(): the first use of each glossary term on the page, and every CVE ID, in text outside links,
    // code, headings and the rest of SKIP. `keep` is a node drawn by the build and kept: its terms count as used.
    this.gloss = function (root, keep, used) {
      var walk = function (n) {
        if (n.nodeType === 1) {
          if (keep.indexOf(n) >= 0 || SKIP[n.tagName.toLowerCase()]) {
            n.querySelectorAll && [].forEach.call(n.matches('a.term') ? [n] : n.querySelectorAll('a.term'), function (a) {
              var id = (a.getAttribute('href') || '').split('#')[1]; if (id) used[id] = 1;
            });
            return;
          }
          [].slice.call(n.childNodes).forEach(walk);
        } else if (n.nodeType === 3 && n.data.trim()) term(n);
      };
      var term = function (tn) {
        var t = tn.data, spans = [], m;
        CVE.lastIndex = 0;
        while ((m = CVE.exec(t))) {
          var c = m[0], href, tip;
          if (FLAGSHIP[c]) { href = L.link('flaws/index.html#' + c); tip = c + ': ' + FLAGSHIP[c] + ', one of the two php2shell flaws. CVSS 9.2, critical. Fixed 21 October 2026.'; }
          else if (c in drawn.cve ? /\/sources\/cve-/.test(drawn.cve[c]) : sources('cve-' + c.toLowerCase())) { href = L.link('sources/cve-' + c.toLowerCase() + '/index.html'); tip = c + ': an earlier flaw; its official record, as captured into the vault.'; }
          else { href = 'https://www.cve.org/CVERecord?id=' + c; tip = c + ': its official record at cve.org.'; }
          spans.push([m.index, m.index + c.length, el('a', { class: 'cve-link', href: href, rel: /^https?:/.test(href) && href.indexOf('cve.org') > 0 ? 'noopener' : null, 'data-term': c, 'data-tip': tip }, [c])]);
        }
        var free = function (a, b) { return !spans.some(function (x) { return x[0] < b && a < x[1]; }); };
        terms.forEach(function (tr) {
          if (used[tr.id]) return;
          tr.rx.some(function (rx) {
            rx.lastIndex = 0;
            var hit;
            while ((hit = rx.exec(t))) {
              if (!hit[0]) { rx.lastIndex++; continue; }
              if (free(hit.index, hit.index + hit[0].length)) break;
            }
            if (!hit) return false;
            spans.push([hit.index, hit.index + hit[0].length, el('a', { class: 'term', href: L.link('glossary/index.html#' + tr.id), 'data-term': tr.term, 'data-tip': tr.short }, [hit[0]])]);
            used[tr.id] = 1;
            return true;
          });
        });
        if (!spans.length) return;
        spans.sort(function (a, b) { return a[0] - b[0]; });
        var f = document.createDocumentFragment(), last = 0;
        spans.forEach(function (x) { if (x[0] > last) f.appendChild(document.createTextNode(t.slice(last, x[0]))); f.appendChild(x[2]); last = x[1]; });
        if (last < t.length) f.appendChild(document.createTextNode(t.slice(last)));
        tn.parentNode.replaceChild(f, tn);
      };
      walk(root);
    };
  }

  // The article in the frame: the parts build_articles() writes inside <article class="piece">, with the nodes the
  // build put after the title (the plain-English box, the version badge) kept as they were.
  function piece(r, a, asOf, keep) {
    var role = ROLES[a.role] || s(a.role), many = s(a.author).indexOf(',') >= 0;
    var out = [el('p', { class: 'kicker' }, ['Story · ' + (ORIGINS[a.origin] || s(a.origin)) + ' · ' + role + ' · ' + s(a.written)]), el('h1', {}, [s(a.title)])];
    out = out.concat(keep);
    out.push(el('p', { class: 'lead' }, [s(a.dek)]));
    out.push(el('p', { class: 'kv' }, [el('b', {}, ['By']), ' the ' + role.toLowerCase() + (many ? ' roles, agents ' : ' role, agent '), el('code', {}, [s(a.author)]),
      ' · ', el('b', {}, ['written against']), ' site v' + s(a.as_of_version) + ' · vault commit ', el('code', {}, [s(a.vault_commit)]), ' · data as of ' + s(a.data_as_of)]));
    if (asOf && s(a.data_as_of) < asOf) out.push(el('p', { class: 'caveat' }, [el('b', {}, ['The evidence has moved since this was written.']),
      ' This article was written against data as of ' + s(a.data_as_of) + '; the site now has data as of ' + asOf + '. The ', el('a', { href: L.link('index.html') }, ['front page']),
      ' and ', el('a', { href: L.link('claims/index.html') }, ['every claim']), ' are current; this article is kept as written.']));
    Object.keys(a).filter(function (k) { return /^correction\d+$/.test(k); }).sort().forEach(function (k) {
      var v = s(a[k]), i = v.indexOf(' | ');
      if (i < 0) return;
      out.push(el('div', { class: 'caveat correction', id: 'correction-' + k.slice(10) }, [el('p', {}, [el('b', {}, ['Correction, ' + humanTime(v.slice(0, i)) + '.']), ' ' + v.slice(i + 3)])]));
    });
    out.push(r.body(a.text));
    return out;
  }

  function draw(file, a, side) {
    var glossary = side[0], vault = side[1], rows = side[2];
    var known = function (x) { return drawn.src[x] || (rows && rows[x]); };
    var terms = ((glossary && glossary.terms) || []).filter(function (t) { return t.match && t.match.length; }).map(function (t) {
      return { id: t.id, term: t.term, short: t.short, rx: t.match.map(function (p) { try { return new RegExp(p, 'g'); } catch (e) { return null; } }).filter(Boolean) };
    });
    var r = new Renderer(known, terms);
    var h1 = box.querySelector('h1'), keep = [];
    for (var n = h1 && h1.nextElementSibling; n && !n.matches('p.lead'); n = n.nextElementSibling) keep.push(n);
    var stage = el('div', {}, piece(r, a, (vault && vault.latest_capture) || '', keep));
    stage.normalize();
    if (terms.length) try { r.gloss(stage, keep, {}); } catch (e) { /* the text unglossed rather than the kept nodes lost */ }
    var slides = stage.querySelector('[data-ba]');
    L.fill(box, [].slice.call(stage.childNodes));
    if (h1 && h1.textContent !== s(a.title)) document.title = document.title.replace(h1.textContent, s(a.title));
    var cited = document.getElementById('cited');
    if (cited && cited.querySelector('p.refs')) {
      var ps = cited.querySelectorAll('p');
      L.fill(ps[0], [a.cites.length + ' captured sources, in the order this article first cites them. Each opens on its page with its capture times and hashes.']);
      L.fill(cited.querySelector('p.refs'), [r.src(a.cites)]);
    }
    if (slides) {   // the before-and-after sliders were drawn again: assets/compare.js binds the new ones
      if (window.P2S_COMPARE) window.P2S_COMPARE(box);
      else document.head.appendChild(el('script', { src: L.link('assets/compare.js'), defer: '' }));
    }
    L.stamp(box, 'the article from content/articles/' + file + ' in the site repository');
  }

  // The article's file: named by the frame, or (the view) found by its slug in the index site's deploy writes.
  function find() {
    var src = box.getAttribute('data-md');
    if (src) return Promise.resolve(src);
    var slug = decodeURIComponent(location.hash.slice(1));
    return L.json('content/index/articles.json').then(function (ix) {
      var hit = ((ix && ix.articles) || []).filter(function (x) { return x.slug === slug; })[0];
      if (!hit || !/^[0-9a-z_.-]+\.md$/.test(s(hit.file))) throw new Error('no article ' + slug);
      return 'content/articles/' + hit.file;
    });
  }

  learn(document);
  find().then(function (src) {
    var file = src.replace(/^content\/articles\//, '');
    return Promise.all([L.text(src), L.json('content/data/glossary.json').catch(function () { return null; }), L.json('data/vault.json').catch(function () { return null; })]).then(function (d) {
      var a = parse(d[0]);
      if (!a || !a.title) return;
      var need = a.cites.some(function (x) { return !drawn.src[x]; }) ||
                 (a.text.match(CVE) || []).some(function (c) { return !FLAGSHIP[c] && !(c in drawn.cve); });
      var rows = need ? L.json('data/sources.json').then(function (list) {
        var by = {};
        (Array.isArray(list) ? list : []).forEach(function (x) { if (x && x.slug) by[x.slug] = { short: shortName(x), title: s(x.title || x.publisher || x.slug) }; });
        return by;
      }).catch(function () { return null; }) : Promise.resolve(null);
      return rows.then(function (by) {
        draw(file, a, [d[1], d[2], by]);
        if (!box.getAttribute('data-md')) {
          try { history.replaceState(null, '', '/articles/' + encodeURIComponent(decodeURIComponent(location.hash.slice(1))) + '/') } catch (e) {}   // the article's own address, as the reader asked for it
        }
      });
    });
  }).catch(function () { /* the article as built stays */ });
})();
