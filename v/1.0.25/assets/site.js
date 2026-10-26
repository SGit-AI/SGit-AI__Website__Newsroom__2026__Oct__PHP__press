// php.oct.2026.newsroom.sgit.ai: the menu on narrow screens, the reader bar, and the glossary hover cards.
// The reader you pick and the pages you have opened are kept in this browser's localStorage and nowhere else.
(function () {
  var b = document.querySelector('.nav-toggle'), n = document.getElementById('nav-items');
  if (b && n) {
    b.addEventListener('click', function () {
      var open = n.classList.toggle('open');
      b.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.querySelectorAll('.ni > .nl').forEach(function (a) {
      a.addEventListener('click', function (ev) {
        if (window.matchMedia('(max-width: 900px)').matches) { ev.preventDefault(); a.parentNode.classList.toggle('open'); }
      });
    });
  }

  var html = document.documentElement, root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length), here = html.getAttribute('data-path') || '';
  function get(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function set(k, v) { try { if (v === null) window.localStorage.removeItem(k); else window.localStorage.setItem(k, v); } catch (e) {} }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var seen = [];
  try { seen = JSON.parse(get('p2s.seen') || '[]') || []; } catch (e) { seen = []; }
  if (here && seen.indexOf(here) < 0) { seen.push(here); set('p2s.seen', JSON.stringify(seen.slice(-500))); }

  // The reader bar, under the menu on every page.
  var bar = null;
  function renderBar() {
    var P = window.P2S && window.P2S.personas, id = get('p2s.persona'), p = P && id && P[id];
    var nav = document.querySelector('nav.site');
    if (!nav) return;
    if (!bar) { bar = document.createElement('div'); bar.className = 'pbar'; nav.parentNode.insertBefore(bar, nav.nextSibling); }
    document.querySelectorAll('.door.mine').forEach(function (d) { d.classList.remove('mine'); });
    if (p) {
      html.setAttribute('data-depth', String(p.depth));
      var mine = document.querySelector('.door[data-persona="' + id + '"]');
      if (mine) mine.classList.add('mine');
      var steps = '', next = null;
      p.path.forEach(function (x, i) {
        var done = seen.indexOf(x[0]) >= 0, cur = x[0] === here;
        if (!next && !done && !cur) next = x;
        steps += '<li class="' + (cur ? 'here' : done ? 'seen' : '') + '"><a href="' + root + esc(x[0]) + '" title="' + esc(x[1]) + ', ' + esc(String(x[2])) + ' min">' + (i + 1) + '</a></li>';
      });
      var nx = next ? '<span class="nx">Next: <a href="' + root + esc(next[0]) + '">' + esc(next[1]) + '</a> <small>' + esc(String(next[2])) + ' min</small></span>'
                    : '<span class="nx">Path read. <a href="' + root + 'start/index.html">Try another reader</a></span>';
      bar.className = 'pbar';
      bar.innerHTML = '<div class="row"><span class="av av-' + esc(p.group) + '" aria-hidden="true">' + esc(p.person.charAt(0)) + '</span>' +
        '<span class="who">Reading as <a href="' + root + 'briefings/' + esc(id) + '/index.html"><b>' + esc(p.person) + '</b>, ' + esc(p.label.toLowerCase()) + '</a></span>' +
        '<ol class="steps-mini" aria-label="Your reading path">' + steps + '</ol>' + nx +
        '<a class="chg" href="' + root + 'start/index.html">Change</a><button type="button" class="x" data-persona-clear aria-label="Stop reading as ' + esc(p.person) + '">&times;</button></div>';
      bar.hidden = false;
    } else {
      html.removeAttribute('data-depth');
      if (get('p2s.nudge') === 'off' || here === 'index.html' || here === 'start/index.html') { bar.hidden = true; bar.innerHTML = ''; return; }
      bar.className = 'pbar pbar-new';
      bar.innerHTML = '<div class="row"><span class="who">New to this story? <a href="' + root + 'start/index.html">Tell us who you are</a> for a briefing and a reading path, or start with <a href="' + root + 'explained/index.html">the plain-English explainer</a>.</span>' +
        '<button type="button" class="x" data-nudge-off aria-label="Hide this">&times;</button></div>';
      bar.hidden = false;
    }
  }
  document.addEventListener('click', function (ev) {
    var t = ev.target.closest ? ev.target : null;
    if (!t) return;
    var pick = t.closest('[data-persona]');
    if (pick) { set('p2s.persona', pick.getAttribute('data-persona')); }
    if (t.closest('[data-persona-clear]')) { ev.preventDefault(); set('p2s.persona', null); renderBar(); }
    if (t.closest('[data-nudge-off]')) { ev.preventDefault(); set('p2s.nudge', 'off'); renderBar(); }
  });
  renderBar();

  // Since your last visit: the release you last saw is remembered, and what's new marks every release after it.
  var ver = html.getAttribute('data-ver') || '', lastVer = get('p2s.ver');
  function newer(a, b) { var x = a.split('.'), y = b.split('.'); for (var i = 0; i < 3; i++) { var d = (+x[i] || 0) - (+y[i] || 0); if (d) return d > 0; } return false; }
  if (ver && lastVer && lastVer !== ver) set('p2s.since', lastVer);
  if (ver) set('p2s.ver', ver);
  var since = get('p2s.since');
  if (since) {
    document.querySelectorAll('[data-rel]').forEach(function (el) { if (newer(el.getAttribute('data-rel'), since)) el.classList.add('unseen'); });
  }

  // Glossary hover cards: the first use of a term on a page carries its one-line definition.
  var tip = null, tipFor = null;
  function showTip(a) {
    var text = a.getAttribute('data-tip');
    if (!text) return;
    if (!tip) { tip = document.createElement('div'); tip.className = 'tip'; tip.id = 'p2s-tip'; tip.setAttribute('role', 'tooltip'); document.body.appendChild(tip); }
    tip.innerHTML = '<b>' + esc(a.getAttribute('data-term') || '') + '</b> ' + esc(text) + '<small>Open the glossary &rarr;</small>';
    tip.style.display = 'block';
    var w = Math.min(330, window.innerWidth - 24), r = a.getBoundingClientRect();
    tip.style.width = w + 'px';
    tip.style.left = Math.max(12, Math.min(r.left, window.innerWidth - w - 12)) + 'px';
    var top = r.bottom + 8;
    if (top + tip.offsetHeight > window.innerHeight - 8) top = Math.max(8, r.top - 8 - tip.offsetHeight);
    tip.style.top = top + 'px';
    a.setAttribute('aria-describedby', 'p2s-tip');
    tipFor = a;
  }
  function hideTip() { if (tip) tip.style.display = 'none'; if (tipFor) tipFor.removeAttribute('aria-describedby'); tipFor = null; }
  document.addEventListener('mouseover', function (ev) { var a = ev.target.closest && ev.target.closest('a[data-tip]'); if (a) showTip(a); });
  document.addEventListener('mouseout', function (ev) { var a = ev.target.closest && ev.target.closest('a[data-tip]'); if (a) hideTip(); });
  document.addEventListener('focusin', function (ev) { var a = ev.target.closest && ev.target.closest('a[data-tip]'); if (a) showTip(a); else hideTip(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') hideTip(); });
  window.addEventListener('scroll', hideTip, { passive: true });
})();

// A note in the bar when this page is older than the release the site now serves (one same-origin read of /VERSION).
(function () {
  var v = document.querySelector('nav.site .ver'), root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length);
  if (v && window.fetch) fetch(root + 'VERSION?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.ok ? r.text() : ''; }).then(function (t) {
    var live = (t || '').trim(), mine = v.textContent.replace(/^v/, '');
    if (!/^\d+\.\d+\.\d+$/.test(live)) return;
    var a1 = live.split('.').map(Number), b1 = mine.split('.').map(Number), d = 0;
    for (var i = 0; i < 3 && !d; i++) d = a1[i] - (b1[i] || 0);
    if (d <= 0) return;
    var a = document.createElement('a'); a.className = 'ver newer'; a.href = root + 'status/index.html';
    a.title = 'This page is v' + mine + '; the site now serves v' + live + '. Reload for the new release; the pipeline page shows what changed and what is deploying.';
    a.textContent = 'v' + live + ' is live: reload'; v.insertAdjacentElement('afterend', a);
  }).catch(function () {});
})();
