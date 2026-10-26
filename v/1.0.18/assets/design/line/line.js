/* The line: the runtime. assets/design/line/engine.js decides what it says (pure, tested); this file
   gives it the reader's state, draws the result, and keeps the record. Loaded deferred, after
   config.js and engine.js. boot.js has already shaped the page; nothing here moves the layout above
   the fold except the line growing below its reserved row.
   Brief: admin/content/briefs/2026-10-25__brief__the-line.md. */
(function () {
  'use strict';
  var L = window.LensLine, C = window.LINE;
  if (!L || !C) return;
  (function () {                                            // what this page is: its island, or <html> on a live page
    var el = document.getElementById('line-page');
    if (el) { try { var p = JSON.parse(el.textContent); for (var k in p) C[k] = p[k]; } catch (e) {} return; }
    var path = document.documentElement.getAttribute('data-path') || 'index.html';
    var PAGES = { 'index.html': 'front', 'agencies/index.html': 'agencies', 'numbers/index.html': 'numbers', 'playbook/index.html': 'playbook' };
    C.page = PAGES[path] || 'other';
    C.pageTitle = (document.title || '').split(' \u00b7 ')[0];
    C.root = '../'.repeat((path.match(/\//g) || []).length);   // a count, never page text (as the site's other scripts)
    C.version = document.documentElement.getAttribute('data-ver') || '';
    C.frontPath = 'index.html'; C.statusUrl = C.root + 'status.json'; C.pageFor = null; C.live = true;
  })();
  var ROLES = C.roles, COPY = C.copy, T = C.moments.thresholds, h = document.documentElement;
  var box = document.querySelector('.ln'); if (!box) return;
  var page = C.page, root = C.root || '', liveChanges = 0, lastSaid = null;

  /* ---------------------------------------------------------------- the record */
  function read(k, s) { try { var v = (s ? sessionStorage : localStorage).getItem(k); return v ? JSON.parse(v) : null; } catch (e) { return null; } }
  function put(k, v, s) { try { (s ? sessionStorage : localStorage).setItem(k, JSON.stringify(v)); } catch (e) {} }
  function drop(k, s) { try { (s ? sessionStorage : localStorage).removeItem(k); } catch (e) {} }
  function now() { return new Date(); }
  function rec() { var r = read('p2s.lens'); return r && r.v === 2 ? r : null; }
  function ses() { return read('p2s.lens.session', true) || {}; }
  function personaOf(role, reader) { return reader || (ROLES.roles[role].readers || [])[0] || null; }
  function save(r) {
    put('p2s.lens', r);
    try { var p = personaOf(r.role, r.reader); if (p) localStorage.setItem('p2s.persona', p); else localStorage.removeItem('p2s.persona'); } catch (e) {}
  }
  function fresh(start, t) {
    return { v: 2, role: start.role, reader: start.reader || null, depth: L.chooseDepth(start.role, start.reader, null, ROLES),
      depthSet: false, source: start.source, reason: start.reason || null, confirmed: false, asked: 1,
      firstVisit: t, lastVisit: t, lastActive: t, visits: 1, seen: {}, said: [], history: [{ at: t, role: start.role, reader: start.reader || null, source: start.source }] };
  }

  /* ---------------------------------------------------------------- what has changed, for this role */
  var LOG = (function () { var el = document.getElementById('line-changes'); try { return el ? JSON.parse(el.textContent) : (C.changes || []); } catch (e) { return C.changes || []; } })();
  function changesFor(role, since) {
    if (!since) return [];
    return LOG.filter(function (c) { return c.at > since && (!c.roles || c.roles.indexOf(role) >= 0 || c.roles.indexOf('*') >= 0); });
  }
  var DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  function hhmm(d) { return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }
  function words(iso) {
    if (!iso) return {};
    var d = new Date(iso), t = now();
    var days = Math.round((new Date(t.getFullYear(), t.getMonth(), t.getDate()) - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 86400000);
    var day = days === 0 ? 'today' : days === 1 ? 'yesterday' : DAYS[d.getDay()];
    return { since: (days <= 1 ? day : DAYS[d.getDay()]) + ' at ' + hhmm(d), sinceShort: day, lastTime: hhmm(d), days: days, dayName: days <= 1 ? day : DAYS[d.getDay()] };
  }

  /* ---------------------------------------------------------------- state for the engine */
  /* a link that carries a view, or a date in the past: for this visit only, never the saved view */
  function fromUrl(s) {
    var q = {}, changed = false;
    location.search.replace(/^\?/, '').split('&').forEach(function (kv) {
      var p = kv.split('='); if (p[0]) { try { q[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || ''); } catch (e) {} }
    });
    if (q.as && !s.shared && s.asDone !== q.as) {           // once kept or dropped, the link stops re-arming it
      var id = q.as, role = ROLES.roles[id] ? id : (ROLES.readers[id] || {}).role;
      if (role) { s.shared = { role: role, reader: ROLES.roles[id] ? null : id, depth: q.depth || null }; changed = true; }
    }
    if (q.asof && !s.asOf) { s.asOf = q.asof; changed = true; }
    if (changed) put('p2s.lens.session', s, true);
    return s;
  }

  function state() {
    var r = rec(), s = fromUrl(ses()), t = now(), shared = s.shared || null, asOf = s.asOf || null;
    if (r && shared && shared.role === r.role && (shared.reader || null) === (r.reader || null)) {
      s.asDone = shared.reader || shared.role; delete s.shared; put('p2s.lens.session', s, true); shared = null;
    }
    if (!r) {
      var start = L.startingRole({ stored: null, asParam: shared ? (shared.reader || shared.role) : null, referrer: document.referrer }, ROLES);
      r = fresh(start, t.toISOString()); save(r);
      if (shared) { shared = null; drop('p2s.lens.session', true); }
    }
    var v = L.visitStart(r, t, T);
    var role = shared ? shared.role : r.role, reader = shared ? (shared.reader || null) : r.reader;
    var list = changesFor(role, v.since);
    var m = L.momentFrom({ record: r, session: { shared: shared, asOf: asOf, switchedAt: s.switchedAt }, now: t, changesForRole: list.length, liveChanges: liveChanges }, T);
    if (v.newVisit && !shared && !asOf) {
      r.visits += 1; r.lastVisit = r.lastActive;
      if (m === 'second') r.asked += 1;
    }
    r.lastActive = t.toISOString(); save(r);
    var w = words(v.since);
    /* the date in a shared past link is read as a date and written back as words, never as the text it came in */
    var ad = asOf ? new Date(asOf) : null, aw = { full: '', short: '' };
    if (ad && !isNaN(+ad)) { aw.full = DAYS[ad.getDay()] + ' at ' + hhmm(ad); aw.short = DAYS[ad.getDay()].slice(0, 3); }
    return { r: r, s: s, moment: m, role: role, reader: reader, shared: shared, asOf: asOf, list: list, w: w,
      asOfWords: aw, depth: r.depthSet ? r.depth : (shared && shared.depth) || null };
  }

  /* ---------------------------------------------------------------- drawing */
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function act(label, second) { var b = el('button', 'ln-act', label); b.type = 'button'; b.dataset.act = label; if (second) b.dataset.second = ''; return b; }

  function draw(st) {
    var line = L.computeLine({
      role: st.role, reader: st.reader, depth: st.depth, moment: st.moment, page: page,
      pageTitle: C.pageTitle, pageIsFor: C.pageFor || null, gatePassed: (st.s.gates || []).indexOf(location.pathname) >= 0,
      firstReason: st.r.reason, sharedRole: st.shared ? st.shared.role : st.role, ownRole: st.r.role,
      changes: st.list.map(function (c) { return [c.tag, c.text]; }),
      since: st.w.since, sinceShort: st.w.sinceShort, lastTime: st.w.lastTime, days: st.w.days, count: st.list.length,
      asOf: st.asOfWords.full, asOfShort: st.asOfWords.short
    }, ROLES, COPY);

    h.setAttribute('data-role', st.role);
    h.setAttribute('data-depth', st.depth || L.chooseDepth(st.role, st.reader, null, ROLES));
    h.setAttribute('data-moment', st.moment);
    if (st.r.confirmed) h.setAttribute('data-confirmed', ''); else h.removeAttribute('data-confirmed');
    if (line.rule === 1) h.setAttribute('data-gate', ''); else h.removeAttribute('data-gate');

    box.dataset.size = line.size; box.dataset.tone = line.tone; box.dataset.rule = line.rule;
    box.textContent = '';
    var row = el('div', 'ln-row');
    var chip = el('button', 'ln-chip'); chip.type = 'button'; chip.setAttribute('aria-expanded', 'false');
    var dot = el('span', 'ln-dot'); dot.dataset.dot = line.dot; chip.appendChild(dot);
    chip.appendChild(document.createTextNode(line.chip + ' ▾'));
    row.appendChild(chip);
    var msg = el('span', 'ln-msg');
    if (line.lead) { msg.appendChild(el('b', null, line.lead)); msg.appendChild(document.createTextNode(' ')); }
    msg.appendChild(document.createTextNode(line.text || ''));
    row.appendChild(msg);
    var pic = line.picture && COPY.pictures[line.picture];
    if (pic && Array.isArray(pic.segments)) {
      var p = el('span', 'ln-pic'), bar = el('span', 'b');
      pic.segments.forEach(function (s) { var i = el('i'); i.style.flex = s[0]; i.style.background = s[1]; bar.appendChild(i); });
      p.appendChild(bar); p.appendChild(el('span', 'l', pic.label)); row.appendChild(p);
    }
    if (line.size === 'line' && line.actions.length) {
      var a1 = el('span', 'ln-acts');
      line.actions.forEach(function (x, i) { a1.appendChild(act(x, i > 0)); });
      row.appendChild(a1);
    }
    box.appendChild(row);
    if (line.size !== 'line') {
      if (line.items.length) {
        var items = el('div', 'ln-items');
        line.items.forEach(function (it) {
          var i = el('div', 'i'), tg = el('span', 'ln-tag', it[0]); tg.dataset.t = it[0];
          i.appendChild(tg); i.appendChild(el('span', null, it[1])); items.appendChild(i);
        });
        box.appendChild(items);
      }
      var a2 = el('div', 'ln-acts ln-open-acts');
      line.actions.forEach(function (x, i) { a2.appendChild(act(x, i > 0)); });
      if (line.others) {
        var o = el('span', 'ln-others');
        o.appendChild(document.createTextNode(line.others.split(':')[0] + ':'));
        ROLES.order.filter(function (x) { return x !== st.role; }).forEach(function (x) {
          var b = act(ROLES.roles[x].name, true); b.dataset.act = ''; b.dataset.role = x; o.appendChild(b);
        });
        a2.appendChild(o);
      }
      box.appendChild(a2);
    }
    if (lastSaid !== line.key) {
      lastSaid = line.key;
      st.r.said = (st.r.said || []).concat([{ at: new Date().toISOString(), rule: line.rule, key: line.key, tapped: null }]).slice(-20);
      save(st.r);
    }
    shapePage(st, line);
    if (C.live) { answerCards(st); rewriteAddress(st); }
    if (line.key === 'switched') setTimeout(function () { var s2 = ses(); delete s2.switchedAt; put('p2s.lens.session', s2, true); render(); }, T.switchedToastSeconds * 1000);
    return line;
  }

  /* the page under the line: badges on what changed, folding what has been read */
  function shapePage(st, line) {
    var badge = { week: COPY.inPage.changedBadge.replace('{sinceShortDay}', st.w.dayName || 'your last visit'),
      second: COPY.inPage.changedBadge.replace('{sinceShortDay}', st.w.dayName || 'your last visit'),
      long: COPY.inPage.changedBadge.replace('{sinceShortDay}', 'your last visit'),
      live: COPY.inPage.liveBadge, past: COPY.inPage.pastBadge }[st.moment];
    var changed = {}; st.list.forEach(function (c) { if (c.key) changed[c.key] = 1; });
    var fold = (st.moment === 'hour' || st.moment === 'sameday');
    document.querySelectorAll('.lnp .lp').forEach(function (part) {
      var k = part.dataset.k, old = part.querySelector(':scope > .lp-badge');
      if (old) old.remove();
      var isChanged = !!changed[k] || (st.r.seen[page + '/' + k] && st.r.seen[page + '/' + k] !== part.dataset.hash);
      if (badge && isChanged) {
        var b = el('span', 'lp-badge', badge); if (st.moment === 'live') b.dataset.kind = 'live';
        part.insertBefore(b, part.firstChild);
      }
      var read = !!st.r.seen[page + '/' + k];
      part.classList.toggle('is-folded', !!(fold && read && !isChanged && part.dataset.fold === '1'));
      if (part.classList.contains('is-folded') && !part.querySelector(':scope > .lp-fold')) {
        var f = el('div', 'lp-fold');
        f.appendChild(el('span', 'ln-tag', COPY.inPage.foldedTag));
        f.appendChild(el('b', null, part.dataset.title || ''));
        f.appendChild(el('span', null, 'unchanged since you read it'));
        var open = el('button', null, COPY.inPage.foldedOpen); open.type = 'button'; open.dataset.open = '1';
        f.appendChild(open); part.insertBefore(f, part.firstChild);
      }
    });
    document.querySelectorAll('.lnp').forEach(function (m) { m.classList.toggle('dim', line.rule === 1); });
  }

  function render() { var st = state(); return draw(st); }

  /* ---------------------------------------------------------------- live pages: the answer card for this reader */
  function answerCards(st) {
    var src = document.getElementById('p2s-answers'); if (!src) return;
    var A; try { A = JSON.parse(src.textContent); } catch (e) { return; }
    var pid = personaOf(st.role, st.reader);
    document.querySelectorAll('[data-answer-for]').forEach(function (b) {
      var a = A[pid] || A[b.getAttribute('data-answer-for')]; if (!a) return;
      var w = b.querySelector('[data-a-who]'), t = b.querySelector('[data-a-text]'), av = b.querySelector('[data-a-av]');
      if (w) w.textContent = 'for ' + a.person + ', ' + a.label.toLowerCase();
      if (t) t.textContent = a.answer;
      if (av) { av.textContent = a.person.charAt(0); av.className = 'av ' + a.group; }
    });
  }

  /* ---------------------------------------------------------------- live pages: the view in the address bar
     The page is a real file at its real path; the address shows the view, /agencies/as/security/, so copying it
     shares the view. Moving the address deeper would make every relative link resolve against the wrong
     directory, so first every link on the page is made absolute against the real page, and so is every link
     added later. Scripts resolve their own requests against window.P2S_BASE, set before any of them ran. */
  var REAL = window.P2S_BASE || location.href, fixed = false;
  function word(role, reader) {
    if (reader && reader !== (ROLES.roles[role].readers || [])[0]) return reader;
    return role === 'exec' ? 'executive' : role;
  }
  function absolutize(rootNode) {
    var nodes = rootNode.querySelectorAll ? rootNode.querySelectorAll('a[href],area[href],img[src],form[action],link[href]') : [];
    var list = (rootNode.matches && rootNode.matches('a[href],area[href],img[src],form[action]')) ? [rootNode] : [];
    Array.prototype.forEach.call(nodes, function (n) { list.push(n); });
    list.forEach(function (n) {
      var attr = n.hasAttribute('href') ? 'href' : n.hasAttribute('src') ? 'src' : 'action', v = n.getAttribute(attr);
      if (!v || /^([a-z][a-z0-9+.-]*:|\/\/|#)/i.test(v)) return;           // absolute, protocol-relative, or an anchor
      try { n.setAttribute(attr, new URL(v, REAL).href); } catch (e) {}
    });
  }
  function fixLinks() {
    if (fixed) return; fixed = true;
    absolutize(document);
    if (window.MutationObserver) new MutationObserver(function (ms) {
      ms.forEach(function (m) {
        if (m.type === 'attributes') absolutize(m.target);
        else m.addedNodes.forEach(function (n) { if (n.nodeType === 1) absolutize(n); });
      });
    }).observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ['href', 'src', 'action'] });
  }
  function rewriteAddress(st) {
    if (!history.replaceState) return;
    var real = new URL(REAL), dir = real.pathname.replace(/index\.html$/, '');
    var view = dir + 'as/' + word(st.role, st.reader) + '/';
    if (st.depth && st.r.depthSet && st.depth !== L.chooseDepth(st.role, st.reader, null, ROLES)) view += st.depth + '/';
    if (location.pathname === view) return;
    fixLinks();
    try { history.replaceState(history.state, '', view + real.search + location.hash); } catch (e) {}
  }

  /* ---------------------------------------------------------------- the control */
  var sheet;
  function buildSheet(st) {
    sheet = document.querySelector('.ln-sheet');
    if (!sheet) { sheet = el('div', 'ln-sheet'); sheet.hidden = true; sheet.setAttribute('role', 'dialog');
      sheet.setAttribute('aria-label', 'Who you are reading as'); box.parentNode.insertBefore(sheet, box.nextSibling); }
    sheet.textContent = '';
    function section(title, nodes) {
      var s = el('section'); s.appendChild(el('h3', null, title));
      var g = el('div', 'ln-seg'); nodes.forEach(function (n) { g.appendChild(n); }); s.appendChild(g); sheet.appendChild(s);
    }
    section('Who are you?', ROLES.order.map(function (x) {
      var b = el('button', null, ROLES.roles[x].name); b.type = 'button'; b.dataset.role = x;
      b.setAttribute('aria-pressed', String(x === st.role));
      b.appendChild(el('small', null, ROLES.roles[x].question)); return b;
    }));
    var inRole = ROLES.roles[st.role].readers || [];
    if (inRole.length) section('Closer to you, inside ' + ROLES.roles[st.role].name, inRole.map(function (id) {
      var rd = ROLES.readers[id], b = el('button', null, rd.label); b.type = 'button'; b.dataset.reader = id;
      b.setAttribute('aria-pressed', String(id === st.reader)); b.appendChild(el('small', null, rd.person)); return b;
    }));
    section('How technical?', ['plain', 'technical', 'deep'].map(function (d) {
      var b = el('button', null, ROLES.depths[d].label); b.type = 'button'; b.dataset.depth = d;
      b.setAttribute('aria-pressed', String(d === (st.depth || L.chooseDepth(st.role, st.reader, null, ROLES))));
      b.appendChild(el('small', null, ROLES.depths[d].text)); return b;
    }));
    var foot = el('p', 'ln-foot');
    [['share', 'Share this view'], ['forget', 'Forget me on this browser']].forEach(function (x) {
      var b = el('button', null, x[1]); b.type = 'button'; b.dataset.tool = x[0]; foot.appendChild(b);
    });
    foot.appendChild(el('span', null, 'Kept in this browser only.'));
    sheet.appendChild(foot);
  }
  function openSheet(v) {
    if (!sheet) return;
    sheet.hidden = !v;
    var chip = box.querySelector('.ln-chip'); if (chip) chip.setAttribute('aria-expanded', String(v));
  }
  var toastEl;
  function toast(key, vars) {
    var t = COPY.toasts[key]; if (!t) return;
    if (!toastEl) { toastEl = el('div', 'ln-toast'); document.body.appendChild(toastEl); }
    toastEl.textContent = L.fill(t, vars || {});
    var hint = COPY.toasts[key + 'Hint']; if (hint) toastEl.appendChild(el('small', null, L.fill(hint, vars || {})));
    toastEl.hidden = false;
    clearTimeout(toastEl._t); toastEl._t = setTimeout(function () { toastEl.hidden = true; }, 5000);
  }

  /* ---------------------------------------------------------------- what the reader can do */
  function setView(patch, how) {
    var r = rec(), s = ses(), t = new Date().toISOString();
    if (!r) return;
    if (patch.role && patch.role !== r.role) { r.role = patch.role; r.reader = null; }
    if ('reader' in patch) { r.reader = patch.reader; if (patch.reader) r.role = ROLES.readers[patch.reader].role; }
    if (patch.depth) { r.depth = patch.depth; r.depthSet = true; }
    if (!patch.depth && patch.role) { r.depth = L.chooseDepth(r.role, r.reader, null, ROLES); r.depthSet = false; }
    r.source = how || 'chosen'; r.confirmed = true; r.reason = null;
    r.history = (r.history || []).concat([{ at: t, role: r.role, reader: r.reader, depth: r.depth, source: r.source }]).slice(-50);
    s.switchedAt = t; delete s.shared;
    save(r); put('p2s.lens.session', s, true);
    go();
  }
  function go() {
    if (document.startViewTransition && !matchMedia('(prefers-reduced-motion: reduce)').matches) document.startViewTransition(function () { render(); buildSheet(state()); });
    else { render(); buildSheet(state()); }
  }

  document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target : null; if (!t) return;
    if (t.closest('.ln-chip')) { e.preventDefault(); openSheet(sheet && sheet.hidden); return; }
    var fold = t.closest('.lp-fold button[data-open]');
    if (fold) { fold.closest('.lp').classList.remove('is-folded'); return; }
    var asLink = t.closest('a[data-as]');                     // "Read this page as": switch in place, no navigation
    if (asLink && ROLES.roles[asLink.getAttribute('data-as')]) { e.preventDefault(); setView({ role: asLink.getAttribute('data-as') }); return; }
    var more = t.closest('[data-line-more]');
    if (more) { e.preventDefault(); setView({ role: 'everything' }); return; }
    var roleBtn = t.closest('[data-role]');
    if (roleBtn && roleBtn.tagName === 'BUTTON') { e.preventDefault(); setView({ role: roleBtn.dataset.role }); openSheet(false); return; }
    var rdBtn = t.closest('[data-reader]');
    if (rdBtn && rdBtn.tagName === 'BUTTON') { e.preventDefault(); setView({ reader: rdBtn.dataset.reader }); openSheet(false); return; }
    var dBtn = t.closest('[data-depth]');
    if (dBtn && dBtn.tagName === 'BUTTON') { e.preventDefault(); setView({ depth: dBtn.dataset.depth }); return; }
    var tool = t.closest('[data-tool]');
    if (tool) {
      e.preventDefault();
      var r0 = rec(), st0 = state();
      if (tool.dataset.tool === 'share') {
        var url = C.live ? location.href.split('#')[0]       // a live page's address already is its view
          : location.origin + location.pathname + '?as=' + (r0.reader || r0.role) + '&depth=' + (st0.depth || L.chooseDepth(st0.role, st0.reader, null, ROLES));
        if (navigator.clipboard) navigator.clipboard.writeText(url);
        toast('linkCopied', { as: ROLES.roles[st0.role].as, depthLower: ROLES.depths[st0.depth || L.chooseDepth(st0.role, st0.reader, null, ROLES)].label.toLowerCase() });
      } else if (tool.dataset.tool === 'forget') {
        if (!tool.dataset.sure) { tool.dataset.sure = '1'; tool.textContent = COPY.toasts.forgetAsk; return; }
        drop('p2s.lens'); drop('p2s.lens.session', true); drop('p2s.persona');
        toast('forgotten'); go();
      }
      return;
    }
    var b = t.closest('.ln-act[data-act]'); if (!b || !b.dataset.act) return;
    e.preventDefault();
    var a = b.dataset.act, r = rec(), s = ses(), iso = new Date().toISOString();
    if (!r) return;
    if (r.said && r.said.length) r.said[r.said.length - 1].tapped = a;
    if (a === "That's me" || a === 'Yes, keep it') { r.confirmed = true; r.reason = null; save(r); toast('confirmed'); go(); return; }
    if (a === 'Show me' || a === 'Mark as seen' || a === 'Later') { r.lastVisit = iso; liveChanges = 0; save(r); go(); return; }
    if (a === 'Catch me up' || a.indexOf('Show all') === 0) { r.lastVisit = iso; liveChanges = 0; save(r); toast('caughtUp'); go(); return; }
    if (a === 'Undo') {
      var hist = r.history || [];
      if (hist.length > 1) { hist.pop(); var prev = hist[hist.length - 1]; r.role = prev.role; r.reader = prev.reader || null; r.depth = prev.depth || r.depth; }
      delete s.switchedAt; save(r); put('p2s.lens.session', s, true); go(); return;
    }
    if (a === 'Switch to mine') { s.asDone = (s.shared || {}).reader || (s.shared || {}).role; delete s.shared; put('p2s.lens.session', s, true); toast('backToMine', { ownName: ROLES.roles[r.role].name }); go(); return; }
    if (a === 'Make it mine') { var sh = s.shared || {}; s.asDone = sh.reader || sh.role; delete s.shared; put('p2s.lens.session', s, true); setView({ role: sh.role, reader: sh.reader || null, depth: sh.depth }, 'shared'); toast('keptShared', { as: ROLES.roles[sh.role || r.role].as }); return; }
    if (a === 'Back to today') { delete s.asOf; put('p2s.lens.session', s, true); toast('backToToday'); go(); return; }
    if (a === 'Read it anyway') { s.gates = (s.gates || []).concat([location.pathname]); put('p2s.lens.session', s, true); toast('gatePassed'); go(); return; }
    if (a === 'Back to your front page') { location.href = new URL(root + C.frontPath, REAL).href; return; }
    save(r); go();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') openSheet(false); });
  document.addEventListener('click', function (e) { if (sheet && !sheet.hidden && !e.target.closest('.ln-sheet') && !e.target.closest('.ln-chip')) openSheet(false); }, true);

  /* ---------------------------------------------------------------- what the reader has read */
  function watchParts() {
    if (!window.IntersectionObserver) return;
    var timers = {};
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var part = en.target, k = part.dataset.k; if (!k) return;
        if (en.isIntersecting) { timers[k] = setTimeout(function () { part.dataset.lingered = '1'; }, 3000); }
        else {
          clearTimeout(timers[k]);
          if (part.dataset.lingered === '1' && en.boundingClientRect.top < 0 && !ses().asOf) {
            var r = rec(); if (!r) return;
            r.seen[page + '/' + k] = part.dataset.hash || '1'; save(r);
          }
        }
      });
    }, { threshold: 0.4 });
    document.querySelectorAll('.lnp .lp').forEach(function (p) { io.observe(p); });
  }

  /* ---------------------------------------------------------------- the story updating while you read */
  function watchRelease() {
    if (!C.statusUrl) return;
    setInterval(function () {
      fetch(C.statusUrl, { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (j) {
        if (j && j.version && j.version !== C.version && !liveChanges) { liveChanges = 1; render(); }
      }).catch(function () {});
    }, 180000);
  }

  addEventListener('storage', function (e) { if (e.key === 'p2s.lens') go(); });

  /* ---------------------------------------------------------------- the catalogue: every line the rules produce */
  function catalogue(host) {
    var MOMENTS = [['first', 'First visit'], ['reading', 'Same visit, reading on'], ['hour', 'Back within the hour'],
      ['sameday', 'Later the same day'], ['second', 'Second visit, never answered'], ['week', 'Back within a week'],
      ['long', 'Back after a week or more'], ['live', 'The story updates while reading'], ['switched', 'Just changed view'],
      ['shared', 'Opened a shared link'], ['past', 'Looking at the past']];
    var reasons = { security: 'a government security advisory', engineer: 'a search for a PHP version',
      researcher: 'a mailing-list archive', general: 'a news article' };
    function one(label, st) {
      var line = L.computeLine({ role: st.role, moment: st.moment, page: st.page, pageTitle: 'The flaws',
        pageIsFor: st.page === 'console' ? ['team'] : null, firstReason: reasons[st.role],
        sharedRole: st.sharedRole || st.role, ownRole: 'exec', depth: st.depth,
        days: 10, count: LOG.length }, ROLES, COPY);   /* a reading of the rules: a worked example, never [brackets] */
      var wrap = el('div', 'ln-cat-row');
      var head = el('div', 'ln-cat-head');
      head.appendChild(el('b', null, label));
      head.appendChild(el('small', null, 'rule ' + line.rule + ' · ' + line.size + ' · ' + line.tone));
      wrap.appendChild(head);
      var b = el('div', 'ln ln-cat-line'); b.dataset.size = line.size; b.dataset.tone = line.tone;
      var row = el('div', 'ln-row');
      var chip = el('span', 'ln-chip'); var d = el('span', 'ln-dot'); d.dataset.dot = line.dot;
      chip.appendChild(d); chip.appendChild(document.createTextNode(line.chip));
      row.appendChild(chip);
      var m = el('span', 'ln-msg');
      if (line.lead) { m.appendChild(el('b', null, line.lead)); m.appendChild(document.createTextNode(' ')); }
      m.appendChild(document.createTextNode(line.text || ''));
      row.appendChild(m);
      if (line.actions.length) { var a = el('span', 'ln-acts'); line.actions.forEach(function (x, i) { var k = el('span', 'ln-act', x); if (i) k.dataset.second = ''; a.appendChild(k); }); row.appendChild(a); }
      b.appendChild(row);
      if (line.size !== 'line' && line.items.length) {
        var it = el('div', 'ln-items');
        line.items.forEach(function (x) { var i = el('div', 'i'), t = el('span', 'ln-tag', x[0]); t.dataset.t = x[0]; i.appendChild(t); i.appendChild(el('span', null, x[1])); it.appendChild(i); });
        b.appendChild(it);
      }
      if (line.others) b.appendChild(el('div', 'ln-others', line.others));
      wrap.appendChild(b);
      return wrap;
    }
    function group(title, rows) {
      host.appendChild(el('h2', 'h2 ln-cat-h', title));
      rows.forEach(function (r) { host.appendChild(r); });
    }
    group('An Executive on the front page, visit by visit', MOMENTS.map(function (m) {
      return one(m[1], { role: m[0] === 'shared' ? 'journalist' : 'exec', sharedRole: 'journalist', moment: m[0], page: 'front' });
    }));
    group('Back within a week, the front page, every role', ROLES.order.map(function (r) {
      return one(ROLES.roles[r].name, { role: r, moment: 'week', page: 'front' });
    }));
    group('The agencies, reading on, every role', ROLES.order.map(function (r) {
      return one(ROLES.roles[r].name, { role: r, moment: 'reading', page: 'agencies' });
    }));
    group('An Executive reading on, every page', ['front', 'agencies', 'numbers', 'playbook', 'console', 'other'].map(function (p) {
      return one(p, { role: 'exec', moment: 'reading', page: p });
    }));
    group('A first visit landing on an inner page', [['exec', 'agencies'], ['security', 'playbook'], ['journalist', 'numbers']].map(function (x) {
      return one(ROLES.roles[x[0]].name + ' on ' + x[1], { role: x[0], moment: 'first', page: x[1] });
    }));
  }

  var cat = document.getElementById('ln-cat');
  if (cat) { box.remove(); catalogue(cat); return; }
  var st0 = state(); draw(st0); buildSheet(st0); watchParts(); watchRelease();
})();
