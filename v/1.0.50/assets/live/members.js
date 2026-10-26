/* A member's page, live: "Where it is now" (its status.json) and its rounds (its debriefs), read from the team
   repository's records when the page opens (records/index/agents.json, written by the team site's deploy), so a status
   or a debrief a member releases is on its page a minute or two later, with no build. Draws the build's markup
   (build.py: build_members, debrief_html) into data-live="member-status" and "member-debriefs"; the role, the policy and
   the delta stay as built. A screenshot is drawn only from the member's own debriefs/img/ folder, as the build requires,
   and is served by the team site. What the build drew stays when the fetch fails. Needs assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, boxes = document.querySelectorAll('[data-live^="member-"]');
  if (!L || !boxes.length) return;
  var el = L.el, IMG = /^!\[([^\]]*)\]\((img\/[A-Za-z0-9_.-]+\.(?:png|jpg|jpeg|webp))\)\s*$/;

  function pyDumps(v) {                                     // json.dumps(v) as Python writes it: ", " and ": ", ASCII only
    if (v === null || typeof v !== 'object') return JSON.stringify(v).replace(/[\u007f-￿]/g, function (c) { return '\\u' + ('000' + c.charCodeAt(0).toString(16)).slice(-4); });
    if (Array.isArray(v)) return '[' + v.map(pyDumps).join(', ') + ']';
    return '{' + Object.keys(v).map(function (k) { return pyDumps(k) + ': ' + pyDumps(v[k]); }).join(', ') + '}';
  }

  function lines(xs, f, none) {                             // the build's '<br>'.join(...) or a word for nothing
    xs = Array.isArray(xs) ? xs : [];
    if (!xs.length) return [none];
    var out = [];
    xs.forEach(function (x, i) { if (i) out.push(el('br')); out.push(f(x)); });
    return out;
  }

  function status(st) {
    if (!st) return el('p', { class: 'small' }, ['No status file.']);
    var what = function (x) { return x && typeof x === 'object' ? String(x.what || '') : String(x); };
    var ask = function (x) { return x && typeof x === 'object' ? String(x.what || '') + (x.from ? ' (from ' + x.from + ')' : '') : String(x); };
    var tok = st.tokens && typeof st.tokens === 'object' ? st.tokens : {}, pol = st.policy && typeof st.policy === 'object' ? st.policy : {};
    return L.table(['Field', 'Value'], [
      ['Round', st.round ? pyDumps(st.round) : String(st.state || '')],
      ['Done', lines(st.done, what, 'nothing recorded')],
      ['Next', lines(st.next, what, 'nothing proposed')],
      ['Asks', lines(st.asks, ask, 'none')],
      ['Tokens', (tok.value == null ? 'unknown' : L.pyStr(tok.value)) + ' · ' + (tok.how || '')],
      ['Policy', Object.keys(pol).filter(function (k) { return k !== 'version'; }).map(function (k) { return k + ' ' + L.pyStr(pol[k]); }).join(', ')]]);
  }

  function debrief(db, agent) {
    var f = document.createDocumentFragment(), buf = [];
    var flush = function () { if (buf.length) { f.appendChild(L.md(buf.join('\n'))); buf = []; } };
    String(db.text || '').split(/\r?\n/).forEach(function (line) {
      var m = line.trim().match(IMG);
      if (!m) { buf.push(line); return; }
      flush();
      var img = el('img', { src: L.link('records/agents/' + encodeURIComponent(agent) + '/debriefs/' + m[2]), alt: m[1], loading: 'lazy' });
      var fig = el('figure', { class: 'shot' }, [img, el('figcaption', {}, [m[1]])]);
      img.addEventListener('error', function () { fig.replaceWith(el('p', { class: 'small' }, ['Missing screenshot: ', el('code', {}, [m[2]])])); });
      f.appendChild(fig);
    });
    flush();
    var g = function (k) { return db[k] == null ? '' : String(db[k]); };
    return el('article', { class: 'role', id: String(db.file || '').replace(/\.md$/, '') }, [el('h3', {}, [db.title || db.file]),
      el('p', { class: 'small' }, [g('date') + ' · round ' + g('round') + ' · branch ', el('code', {}, [g('branch')]), ' · commits ', el('code', {}, [g('commits')]),
        ' · tokens ' + g('tokens') + ' · outside scope ' + g('outside_scope') + ' · overrides ' + g('overrides')]), f]);
  }

  L.json('records/index/agents.json').then(function (d) {
    var by = {}, last = null;
    ((d && d.agents) || []).forEach(function (a) { by[a.agent] = a; });
    boxes.forEach(function (box) { try {
      var a = by[box.getAttribute('data-agent')], kind = box.getAttribute('data-live');
      if (!a) return;
      if (kind === 'member-status') L.fill(box, status(a.status));
      else if (kind === 'member-debriefs') L.fill(box, a.debriefs.length ? a.debriefs.map(function (db) { return debrief(db, a.agent); }) : el('p', { class: 'small' }, ['No debrief yet.']));
      else return;
      last = box;
    } catch (e) { /* this container keeps what the build drew */ } });
    if (last) L.stamp(last, 'the status and the debriefs from records/agents/ in the team repository');
  }).catch(function () { /* the page as built stays */ });
})();
