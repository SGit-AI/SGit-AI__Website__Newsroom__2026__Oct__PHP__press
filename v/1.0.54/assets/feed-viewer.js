// php.oct.2026.newsroom.sgit.ai: the feed viewer (/reader/). The brief, with its security model, is
// admin/content/briefs/2026-10-22__feeds-the-delta-and-subscriptions.md.
//
// Your browser fetches every feed itself: this site's own, the outside sources a browser is allowed to read
// directly (their servers send a CORS header), and any feed you add. Nothing goes through a third party, which
// would see what you read. A feed is untrusted input, so:
//   - https only, and never an address on your own network (localhost, private ranges, .local, .internal);
//   - fetched with credentials omitted, no referrer, a 15 second limit and at most 2 MB read (5 MB for a JSON API);
//   - parsed with the browser's XML or JSON parser; summaries that carry HTML are parsed into an inert document and
//     only their text is kept; every string goes into the page as text, so markup in a feed is shown, never run;
//   - a link is kept only when it is http or https, and opens in a new tab with noopener and noreferrer.
// What you have read is kept with the rest of your reading (window.P2SReader); the feeds you add are kept under
// p2s.feeds.v1. Nothing is sent anywhere.
(function () {
  'use strict';
  var R = window.P2SReader, box = document.getElementById('viewer'), cfgEl = document.getElementById('viewer-config');
  if (!box || !cfgEl) return;
  var CFG = JSON.parse(cfgEl.textContent), root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length);
  var FKEY = 'p2s.feeds.v1', MAX = 2e6, MAX_JSON = 5e6, TIMEOUT = 15000;
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function fnv(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16); }
  function mine() { try { var f = JSON.parse(localStorage.getItem(FKEY) || 'null'); if (!f || !Array.isArray(f.feeds)) return { v: 1, feeds: [] }; f.feeds = f.feeds.filter(function (x) { return x && typeof x.url === 'string' && !allowedFeedUrl(x.url); }); return f; } catch (e) { return { v: 1, feeds: [] }; } }
  function saveMine(f) { try { localStorage.setItem(FKEY, JSON.stringify(f)); } catch (e) {} }

  // ------------------------------------------------------------------ safety
  function safeUrl(u, base) {
    try { var x = new URL(u, base); return (x.protocol === 'https:' || x.protocol === 'http:') ? x.href : null; } catch (e) { return null; }
  }
  function allowedFeedUrl(u) {
    var x; try { x = new URL(u); } catch (e) { return 'That is not a web address.'; }
    if (x.protocol !== 'https:') return 'Only https feeds can be added.';
    if (x.username || x.password) return 'An address with a name or password in it is not accepted.';
    var h = x.hostname.toLowerCase().replace(/^\[|\]$/g, '');
    if (h === 'localhost' || /\.(local|localhost|internal|home|lan|intranet|corp)$/.test(h) || h.indexOf('.') < 0) return 'Addresses on your own network are not accepted.';
    if (/^(127\.|10\.|192\.168\.|169\.254\.|0\.|172\.(1[6-9]|2\d|3[01])\.|100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.)/.test(h) || /^\d+$/.test(h)) return 'Addresses on your own network are not accepted.';
    if (h.indexOf(':') >= 0 && /^(::1?$|f[cd]|fe80)/.test(h)) return 'Addresses on your own network are not accepted.';
    if (u.length > 2048) return 'That address is too long.';
    return null;
  }
  function textOf(htmlish) {
    if (!htmlish) return '';
    var s = String(htmlish);
    if (/[<&]/.test(s)) { try { s = new DOMParser().parseFromString(s, 'text/html').body.textContent || ''; } catch (e) { s = s.replace(/<[^>]*>/g, ' '); } }
    return s.replace(/\s+/g, ' ').trim();
  }
  function clip(s, n) { s = textOf(s); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
  function readCapped(res, cap) {
    var len = +res.headers.get('content-length') || 0;
    if (len > cap) return Promise.reject(new Error('the feed is larger than ' + Math.round(cap / 1e6) + ' MB'));
    if (!res.body || !res.body.getReader) return res.text().then(function (t) { if (t.length > cap) throw new Error('the feed is too large'); return t; });
    var rd = res.body.getReader(), chunks = [], n = 0, dec = new TextDecoder();
    return (function pump() {
      return rd.read().then(function (r) {
        if (r.done) return chunks.join('') + dec.decode();
        n += r.value.length;
        if (n > cap) { try { rd.cancel(); } catch (e) {} throw new Error('the feed is larger than ' + Math.round(cap / 1e6) + ' MB'); }
        chunks.push(dec.decode(r.value, { stream: true })); return pump();
      });
    })();
  }
  function get(url, json) {
    var ac = new AbortController(), tm = setTimeout(function () { ac.abort(); }, TIMEOUT);
    return fetch(url, { credentials: 'omit', referrerPolicy: 'no-referrer', mode: 'cors', cache: 'no-cache', redirect: 'follow', signal: ac.signal })
      .then(function (r) { if (!r.ok) throw new Error('the server answered ' + r.status); return readCapped(r, json ? MAX_JSON : MAX); })
      .then(function (t) { clearTimeout(tm); return t; }, function (e) {
        clearTimeout(tm);
        if (e.name === 'AbortError') throw new Error('no answer within 15 seconds');
        if (e instanceof TypeError) throw new Error('your browser was not allowed to read it: the publisher does not let other sites’ pages read this feed (no CORS header), or it is offline');
        throw e;
      });
  }

  // ------------------------------------------------------------------ parsers: every one returns [{ key, title, link, date, summary, ver }]
  function parseXml(text, base) {
    var doc = new DOMParser().parseFromString(text, 'application/xml');
    if (doc.getElementsByTagName('parsererror').length) throw new Error('this is not a feed the viewer can read (the XML does not parse)');
    function t(n, names) { for (var i = 0; i < names.length; i++) { var e = n.getElementsByTagName(names[i])[0]; if (e) return e.textContent || ''; } return ''; }
    var out = [], items = doc.getElementsByTagName('item'), entries = doc.getElementsByTagName('entry');
    if (items.length) {
      Array.prototype.forEach.call(items, function (n) {
        out.push({ key: t(n, ['guid']) || t(n, ['link']) || t(n, ['title']), title: t(n, ['title']), link: safeUrl(t(n, ['link']), base),
                   date: t(n, ['pubDate', 'dc:date', 'date']), summary: t(n, ['description', 'content:encoded']), ver: t(n, ['pubDate']) });
      });
    } else if (entries.length) {
      Array.prototype.forEach.call(entries, function (n) {
        var l = Array.prototype.filter.call(n.getElementsByTagName('link'), function (x) { return !x.getAttribute('rel') || x.getAttribute('rel') === 'alternate'; })[0];
        out.push({ key: t(n, ['id']) || (l && l.getAttribute('href')) || t(n, ['title']), title: t(n, ['title']), link: l ? safeUrl(l.getAttribute('href'), base) : null,
                   date: t(n, ['updated', 'published']), summary: t(n, ['summary', 'content']), ver: t(n, ['updated']) });
      });
    } else if (!doc.getElementsByTagName('channel').length && !doc.getElementsByTagName('feed').length) throw new Error('this is not an RSS or Atom feed');
    var title = t(doc, ['title']);
    return { title: title, entries: out };
  }
  var ADAPTERS = {
    jsonfeed: function (j, base) { return { title: j.title, entries: (j.items || []).map(function (i) { return { key: i.id || i.url, title: i.title || clip(i.content_text || i.content_html, 90), link: safeUrl(i.url, base), date: i.date_modified || i.date_published, summary: i.summary || i.content_text || i.content_html, ver: i.date_modified }; }) }; },
    nvd: function (j) { return { entries: (j.vulnerabilities || []).map(function (v) { var c = v.cve || {}; var d = (c.descriptions || []).filter(function (x) { return x.lang === 'en'; })[0]; return { key: c.id, title: c.id + ' at NVD: ' + (c.vulnStatus || ''), link: safeUrl('https://nvd.nist.gov/vuln/detail/' + c.id), date: c.lastModified, summary: d && d.value, ver: c.lastModified }; }) }; },
    cve5: function (j) { var m = j.cveMetadata || {}, cna = (j.containers || {}).cna || {}; var d = (cna.descriptions || [])[0]; return { entries: [{ key: m.cveId, title: m.cveId + (cna.title ? ': ' + cna.title : '') + ' (CVE record)', link: safeUrl('https://www.cve.org/CVERecord?id=' + m.cveId), date: m.dateUpdated, summary: d && d.value, ver: m.dateUpdated }] }; },
    osv: function (j) { return { entries: [{ key: j.id, title: j.id + ' at OSV' + (j.summary ? ': ' + j.summary : ''), link: safeUrl('https://osv.dev/vulnerability/' + j.id), date: j.modified, summary: j.details, ver: j.modified }] }; },
    kev: function (j, base, opt) { var want = (opt && opt.match) || 'PHP'; return { title: j.title, entries: (j.vulnerabilities || []).filter(function (v) { return (v.vendorProject + ' ' + v.product).indexOf(want) >= 0; }).sort(function (a, b) { return a.dateAdded < b.dateAdded ? 1 : -1; }).map(function (v) { return { key: v.cveID, title: v.cveID + ': ' + v.vulnerabilityName, link: safeUrl('https://nvd.nist.gov/vuln/detail/' + v.cveID), date: v.dateAdded, summary: v.shortDescription + ' Action: ' + v.requiredAction + ' Due ' + v.dueDate + '.', ver: v.dateAdded + v.dueDate }; }) }; },
    hn: function (j) { return { entries: (j.hits || []).map(function (h) { return { key: h.objectID, title: h.title || h.story_title || clip(h.comment_text, 90), link: safeUrl(h.url || 'https://news.ycombinator.com/item?id=' + h.objectID), date: h.created_at, summary: (h.points != null ? h.points + ' points, ' : '') + (h.num_comments != null ? h.num_comments + ' comments on Hacker News' : clip(h.comment_text, 300)), ver: h.created_at }; }) }; },
    mastodon: function (j) { return { entries: (j || []).map(function (s) { return { key: s.id, title: (s.account && s.account.acct ? '@' + s.account.acct + ': ' : '') + clip(s.content, 110), link: safeUrl(s.url), date: s.created_at, summary: s.content, ver: s.edited_at || s.created_at }; }) }; },
    ghadvisories: function (j) { return { entries: (j || []).map(function (a) { return { key: a.ghsa_id, title: a.ghsa_id + (a.cve_id ? ' (' + a.cve_id + ')' : '') + ': ' + a.summary, link: safeUrl(a.html_url), date: a.updated_at || a.published_at, summary: (a.severity ? a.severity + '. ' : '') + clip(a.description, 400), ver: a.updated_at }; }) }; },
    ghreleases: function (j) { return { entries: (j || []).map(function (r) { return { key: String(r.id), title: r.name || r.tag_name, link: safeUrl(r.html_url), date: r.published_at, summary: clip(r.body, 400), ver: r.published_at }; }) }; },
    wikirevs: function (j) { var pages = (j.query && j.query.pages) || {}, out = []; Object.keys(pages).forEach(function (k) { var p = pages[k]; (p.revisions || []).forEach(function (r) { out.push({ key: String(r.revid), title: (p.title || '') + ': edited by ' + r.user, link: safeUrl('https://en.wikipedia.org/w/index.php?diff=' + r.revid), date: r.timestamp, summary: r.comment, ver: r.timestamp }); }); }); return { entries: out }; }
  };
  function load(feed) {
    var urls = feed.urls || [feed.url];
    return Promise.all(urls.map(function (u) {
      var json = !!feed.adapter && feed.adapter !== 'xml';
      return get(u, json).then(function (text) {
        if (feed.adapter && feed.adapter !== 'xml') return ADAPTERS[feed.adapter](JSON.parse(text), u, feed);
        var tt = text.replace(/^﻿/, '').trim();
        if (tt.charAt(0) === '{') return ADAPTERS.jsonfeed(JSON.parse(tt), u);
        return parseXml(tt, u);
      }, function (e) { if (urls.length > 1) return { entries: [], error: e.message }; throw e; });
    })).then(function (rs) {
      var entries = [], errs = [];
      rs.forEach(function (r) { entries = entries.concat(r.entries || []); if (r.error) errs.push(r.error); });
      entries = entries.filter(function (x) { return x && (x.title || x.summary); }).slice(0, 300).map(function (x) {
        return { id: 'feed:' + feed.id + ':' + fnv(String(x.key || x.link || x.title)), h: fnv(String(x.title || '') + '|' + String(x.ver || x.date || '')),
                 title: clip(x.title || x.summary, 200), link: x.link, date: x.date, summary: clip(x.summary, 500) };
      });
      entries.sort(function (a, b) { var x = Date.parse(a.date) || 0, y = Date.parse(b.date) || 0; return y - x; });
      return { title: rs[0] && rs[0].title, entries: entries, partial: errs };
    });
  }

  // ------------------------------------------------------------------ the view
  var feeds = [], current = null, cache = {};
  function allFeeds() {
    var m = mine().feeds.map(function (f) { return { id: f.id, name: f.name || f.url, url: f.url, group: 'Added by you', what: f.url, user: true }; });
    return CFG.feeds.concat(m);
  }
  function stateOf(e) { return R ? R.state(e.id, e.h) : 'new'; }
  function unreadIn(list) { return list.filter(function (e) { return stateOf(e) !== 'read'; }).length; }

  var side = el('nav', 'fv-side'), pane = el('section', 'fv-pane');
  box.appendChild(side); box.appendChild(pane);

  function renderSide() {
    side.textContent = '';
    var groups = {};
    feeds = allFeeds();
    feeds.forEach(function (f) { (groups[f.group] = groups[f.group] || []).push(f); });
    Object.keys(groups).forEach(function (g) {
      side.appendChild(el('h3', null, g));
      var ul = el('ul');
      groups[g].forEach(function (f) {
        var li = el('li' , f.id === (current && current.id) ? 'on' : null), a = el('a', null, f.name); a.href = '#' + f.id;
        li.appendChild(a);
        if (f.cors === false) li.appendChild(el('span', 'fv-n fv-closed', 'closed'));
        else if (cache[f.id] && cache[f.id].entries) { var n = unreadIn(cache[f.id].entries); li.appendChild(el('span', 'fv-n' + (n ? '' : ' fv-zero'), String(n))); }
        ul.appendChild(li);
      });
      side.appendChild(ul);
    });
    var form = el('form', 'fv-add'); form.appendChild(el('h3', null, 'Add a feed'));
    var inp = el('input'); inp.type = 'url'; inp.placeholder = 'https://example.org/feed.xml'; inp.required = true; inp.maxLength = 2048; inp.setAttribute('aria-label', 'Feed address');
    var nm = el('input'); nm.type = 'text'; nm.placeholder = 'A name for it (optional)'; nm.maxLength = 80; nm.setAttribute('aria-label', 'Feed name');
    var go = el('button', 'rs-b', 'Add'); go.type = 'submit';
    var msg = el('p', 'small');
    form.appendChild(inp); form.appendChild(nm); form.appendChild(go); form.appendChild(msg);
    form.appendChild(el('p', 'small', 'RSS, Atom or JSON Feed, https only. Your browser fetches it; it is kept in this browser.'));
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var u = inp.value.trim(), bad = allowedFeedUrl(u);
      if (bad) { msg.textContent = bad; return; }
      var f = mine(); if (f.feeds.some(function (x) { return x.url === u; })) { msg.textContent = 'You have that one already.'; return; }
      if (f.feeds.length >= 50) { msg.textContent = 'Fifty feeds is the limit here.'; return; }
      var id = 'u-' + fnv(u); f.feeds.push({ id: id, url: u, name: nm.value.trim().slice(0, 80) || new URL(u).hostname, added: new Date().toISOString() });
      saveMine(f); location.hash = id; renderSide(); show(id);
    });
    side.appendChild(form);
  }

  function show(id) {
    var f = allFeeds().filter(function (x) { return x.id === id; })[0] || allFeeds()[0];
    current = f; renderSide();
    pane.textContent = '';
    var head = el('div', 'fv-head');
    head.appendChild(el('h2', null, f.name));
    if (f.what) head.appendChild(el('p', 'small', f.what));
    var src = f.urls ? f.urls : [f.url];
    var srcp = el('p', 'small fv-src');
    src.forEach(function (u, i) { var a = el('a', null, u.length > 90 ? u.slice(0, 89) + '…' : u); var s = safeUrl(u, location.href); if (s) { a.href = s; a.rel = 'noopener noreferrer nofollow'; a.target = '_blank'; } srcp.appendChild(a); if (i < src.length - 1) srcp.appendChild(document.createTextNode(' · ')); });
    head.appendChild(srcp);
    if (f.user) {
      var rm = el('button', 'rs-b', 'Remove this feed'); rm.type = 'button';
      rm.addEventListener('click', function () { var m = mine(); m.feeds = m.feeds.filter(function (x) { return x.id !== f.id; }); saveMine(m); location.hash = ''; renderSide(); show(allFeeds()[0].id); });
      head.appendChild(rm);
    }
    pane.appendChild(head);
    if (f.cors === false) {
      var p = el('p', 'caveat', 'This publisher does not let other sites’ pages read its feed (it sends no CORS header), so your browser cannot load it here, and this site does not route it through anyone else. Open it in a feed reader, or on the publisher’s site. ');
      var a = el('a', null, 'Open the feed'); a.href = safeUrl(f.url) || '#'; a.rel = 'noopener noreferrer nofollow'; a.target = '_blank'; p.appendChild(a);
      pane.appendChild(p); return;
    }
    var status = el('p', 'small', 'Loading…'); pane.appendChild(status);
    var url = f.url && f.url.indexOf('http') !== 0 ? root + f.url : f.url;
    load(f.url ? Object.assign({}, f, { url: url }) : f).then(function (r) {
      cache[f.id] = r; status.remove(); renderSide(); renderEntries(f, r);
    }, function (e) { status.textContent = 'Could not load it: ' + e.message + '.'; });
  }

  function renderEntries(f, r) {
    var old = pane.querySelector('.fv-body'); if (old) old.remove();
    var body = el('div', 'fv-body');
    var n = unreadIn(r.entries);
    var acts = el('p', 'rs-acts');
    acts.appendChild(el('span', 'small', r.entries.length + ' entries, ' + n + ' new or changed to you. '));
    var all = el('button', 'rs-b', 'Mark all read'); all.type = 'button';
    all.addEventListener('click', function () { r.entries.forEach(function (e) { R.markRead(e.id, e.h); }); R.persist(); renderSide(); renderEntries(f, r); });
    acts.appendChild(all);
    body.appendChild(acts);
    if (r.partial && r.partial.length) body.appendChild(el('p', 'small', 'Part of this source could not be read: ' + r.partial.join('; ') + '.'));
    var view = (R && R.store().view) || 'fade', hidden = 0;
    if (!r.entries.length) body.appendChild(el('p', 'small', 'The feed is there and has no entries at the moment.'));
    var ul = el('ul', 'fv-list');
    r.entries.forEach(function (e) {
      var st = stateOf(e);
      if (st === 'read' && view === 'hide') { hidden++; return; }
      var li = el('li', 'it-' + st);
      var b = el('button', 'it-b it-tick' + (st === 'read' ? ' on' : ''), st === 'read' ? '✓' : '○'); b.type = 'button';
      b.title = st === 'read' ? 'Read. Mark as unread' : 'Mark as read';
      b.addEventListener('click', function () { if (st === 'read') R.markUnread(e.id); else R.markRead(e.id, e.h); R.persist(); renderSide(); renderEntries(f, r); });
      li.appendChild(b);
      if (st !== 'read') li.appendChild(el('span', 'it-tag' + (st === 'new' ? ' it-tag-new' : ''), st === 'new' ? 'new' : 'changed'));
      var t = el(e.link ? 'a' : 'span', 'fv-t', e.title);
      if (e.link) { t.href = e.link; t.rel = 'noopener noreferrer nofollow'; t.target = '_blank'; t.addEventListener('click', function () { R.markRead(e.id, e.h); R.persist(); }); }
      li.appendChild(t);
      var d = Date.parse(e.date);
      if (d) li.appendChild(el('span', 'small', ' ' + new Date(d).toLocaleString([], { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })));
      if (e.summary) li.appendChild(el('p', 'fv-s', e.summary));
      ul.appendChild(li);
    });
    body.appendChild(ul);
    if (hidden) {
      var sh = el('button', 'it-run-b', hidden + ' read entries hidden · show'); sh.type = 'button';
      sh.addEventListener('click', function () { R.store().view = 'fade'; R.persist(); renderEntries(f, r); });
      body.appendChild(sh);
    }
    pane.appendChild(body);
  }

  window.addEventListener('hashchange', function () { show(location.hash.slice(1)); });
  renderSide();
  show(location.hash.slice(1) || CFG.feeds[0].id);
})();
