// /status/: where each site's deploy pipeline is, read in the browser from GitHub's public API with no credential.
// Per site: the version the site serves now (its /VERSION file), and the latest runs of its Pages workflow on dev
// (each push to dev starts one, so the newest run is dev's head). Anonymous calls to api.github.com are limited to
// 60 an hour per IP address, so this page calls it once per site per refresh: every 5 minutes, every 20 seconds
// for a site with a run in flight, and not at all while the tab is hidden or the allowance is nearly spent.
(function () {
  var cfgEl = document.getElementById('pipeline-config');
  if (!cfgEl) return;
  var cfg = JSON.parse(cfgEl.textContent);
  var state = {}, rate = null, timer = null;
  var IDLE = 300000, ACTIVE = 20000;

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function ago(iso) {
    if (!iso) return '';
    var s = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 1000));
    if (s < 90) return s + 's ago';
    if (s < 5400) return Math.round(s / 60) + ' min ago';
    if (s < 129600) return Math.round(s / 3600) + ' h ago';
    return Math.round(s / 86400) + ' days ago';
  }
  function dur(a, b) {
    if (!a || !b) return '';
    var s = Math.max(0, Math.round((Date.parse(b) - Date.parse(a)) / 1000));
    return s < 90 ? s + 's' : Math.round(s / 60) + ' min';
  }
  function versionOf(run) {
    var m = /^v(\d+\.\d+\.\d+)/.exec((run.head_commit && run.head_commit.message) || run.display_title || '');
    return m ? m[1] : null;
  }
  function agentOf(run) {
    var msg = (run.head_commit && run.head_commit.message) || '';
    var m = /^Agent:\s*(.+)$/m.exec(msg);
    if (m) return m[1].trim();
    var k = /claude\.ai\/code\/(session_\w+)/.exec(msg);  // no Agent: line: name the session, so two agents still read apart
    return k ? 'session \u2026' + k[1].slice(-6) : '';
  }
  function cmp(a, b) {
    var x = (a || '0').split('.').map(Number), y = (b || '0').split('.').map(Number);
    for (var i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) < (y[i] || 0) ? -1 : 1; }
    return 0;
  }
  // A run's state in words. GitHub cancels a run that waits behind a newer one; that newer run deploys its commit
  // too, so a cancelled run with a newer deploy behind it was superseded, not lost.
  function stateOf(run, runs) {
    if (run.status !== 'completed') return run.status === 'in_progress' ? 'deploying' : 'queued';
    if (run.conclusion === 'success') return 'deployed';
    if (run.conclusion === 'cancelled') {
      var later = runs.some(function (r) { return r.run_number > run.run_number && (r.status !== 'completed' || r.conclusion === 'success'); });
      return later ? 'superseded' : 'cancelled';
    }
    return 'failed';
  }
  var CLS = { deployed: 'st-confirmed', deploying: 'st-reported', queued: 'st-reported', failed: 'st-failed', cancelled: 'st-unverified', superseded: '' };

  function getJSON(url) {
    return fetch(url, { cache: 'no-cache', headers: { 'Accept': 'application/vnd.github+json' } }).then(function (r) {
      var rem = r.headers.get('X-RateLimit-Remaining'), lim = r.headers.get('X-RateLimit-Limit'), reset = r.headers.get('X-RateLimit-Reset');
      if (rem != null) rate = { remaining: +rem, limit: +lim, reset: +reset * 1000 };
      if (!r.ok) { var e = new Error('GitHub answered ' + r.status); e.status = r.status; throw e; }
      return r.json();
    });
  }
  function getLive(site) {
    return fetch(site.site + 'VERSION?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.ok ? r.text() : null; }).then(function (t) { return t ? t.trim() : null; }).catch(function () { return null; });
  }

  function refresh(site) {
    var s = state[site.id] = state[site.id] || {};
    var api = cfg.api + '/repos/' + site.repo + '/actions/workflows/' + site.workflow + '/runs?branch=' + encodeURIComponent(site.branch) + '&per_page=12';
    return Promise.all([
      getLive(site),
      getJSON(api).then(function (j) { return j.workflow_runs || []; }, function (e) { s.error = e; return null; })
    ]).then(function (res) {
      s.live = res[0];
      if (res[1]) { s.runs = res[1]; s.error = null; }
      s.at = Date.now();
      render(site);
    });
  }

  function summary(site, s) {
    var runs = s.runs || [], head = runs[0], live = s.live;
    if (!head) return { cls: '', text: live ? 'Live: v' + live + '. No runs read yet.' : 'Not read yet.' };
    var hv = versionOf(head), st = stateOf(head, runs);
    var lastOk = runs.filter(function (r) { return r.conclusion === 'success'; })[0];
    if (st === 'deploying' || st === 'queued')
      return { cls: 'st-reported', text: (hv ? 'v' + hv : 'Commit ' + head.head_sha.slice(0, 7)) + ' is ' + st + ' (run #' + head.run_number + ', pushed ' + ago(head.created_at) + '). Live until it lands: v' + (live || '?') + '.' };
    if (st === 'failed')
      return { cls: 'st-failed', text: 'The newest push' + (hv ? ', v' + hv + ',' : '') + ' failed to deploy (run #' + head.run_number + '). Live is still v' + (live || '?') + '.' };
    if (hv && live && cmp(live, hv) < 0)
      return { cls: 'st-reported', text: 'v' + hv + ' deployed ' + ago(head.updated_at) + '; the site still serves v' + live + ' (the CDN can lag a few minutes).' };
    return { cls: 'st-confirmed', text: 'Up to date: v' + (live || hv || '?') + ' is live' + (lastOk ? ', deployed ' + ago(lastOk.updated_at) : '') + '.' };
  }

  function render(site) {
    var box = document.getElementById('pl-' + site.id);
    if (!box) return;
    var s = state[site.id] || {}, runs = s.runs || [];
    var out = box.querySelector('.pl-live');
    out.textContent = '';
    var sm = summary(site, s);
    var p = el('p', 'pl-sum');
    var b = el('span', 'st ' + sm.cls, sm.cls === 'st-confirmed' ? 'live' : sm.cls === 'st-failed' ? 'failed' : sm.cls ? 'in the pipeline' : 'unknown');
    p.appendChild(b); p.appendChild(document.createTextNode(' ' + sm.text));
    out.appendChild(p);
    if (s.error) {
      var reset = rate && rate.reset ? new Date(rate.reset).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null;
      out.appendChild(el('p', 'small', ((s.error.status === 403 || s.error.status === 429) && rate && rate.remaining === 0)
        ? 'GitHub\'s anonymous allowance for your address is spent' + (reset ? ' until ' + reset : '') + '; the live version above is still read from the site, and the badge above is GitHub\'s own.'
        : 'GitHub could not be read just now (' + s.error.message + '); trying again at the next refresh.'));
    }
    if (!runs.length) return;
    var t = el('table', 't pl-runs'), th = el('thead'), tr = el('tr');
    ['Run', 'Version', 'State', 'Pushed', 'Took', 'By'].forEach(function (h) { tr.appendChild(el('th', null, h)); });
    th.appendChild(tr); t.appendChild(th);
    var tb = el('tbody');
    runs.forEach(function (r) {
      var row = el('tr'), v = versionOf(r), st = stateOf(r, runs);
      var a = el('a', null, '#' + r.run_number); a.href = /^https:\/\/github\.com\//.test(String(r.html_url)) ? r.html_url : '#'; a.target = '_blank'; a.rel = 'noopener';
      var c1 = el('td'); c1.appendChild(a); row.appendChild(c1);
      var c2 = el('td'), ca = el('a', null, v ? 'v' + v : r.head_sha.slice(0, 7));
      ca.href = /^[\w.-]+\/[\w.-]+$/.test(site.repo) && /^[0-9a-f]{7,40}$/.test(String(r.head_sha)) ? 'https://github.com/' + site.repo + '/commit/' + r.head_sha : '#'; ca.target = '_blank'; ca.rel = 'noopener';
      ca.title = ((r.head_commit && r.head_commit.message) || '').split('\n')[0];
      c2.appendChild(ca);
      if (v && s.live === v) c2.appendChild(el('span', 'small', ' ◀ live'));
      row.appendChild(c2);
      var c3 = el('td'); c3.appendChild(el('span', 'st ' + (CLS[st] || ''), st)); row.appendChild(c3);
      row.appendChild(el('td', 'small', ago(r.created_at)));
      row.appendChild(el('td', 'small', r.status === 'completed' ? dur(r.run_started_at || r.created_at, r.updated_at) : ''));
      row.appendChild(el('td', 'small', agentOf(r)));
      tb.appendChild(row);
    });
    t.appendChild(tb);
    var w = el('div', 'tw'); w.appendChild(t); out.appendChild(w);
  }

  function renderRate() {
    var r = document.getElementById('pl-rate');
    if (!r) return;
    var when = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    r.textContent = 'Read at ' + when + '. ' + (rate ? 'GitHub anonymous allowance for your address: ' + rate.remaining + ' of ' + rate.limit + ' calls left this hour.' : '');
  }

  function active() {
    return cfg.sites.filter(function (site) { var h = (state[site.id] || {}).runs; return h && h[0] && h[0].status !== 'completed'; });
  }
  function schedule() {
    clearTimeout(timer);
    if (document.hidden) return;
    if (rate && rate.remaining < 6) return;
    var act = active();
    timer = setTimeout(function () { run(act.length ? act : cfg.sites); }, act.length ? ACTIVE : IDLE);
  }
  function run(sites) {
    return Promise.all(sites.map(refresh)).then(function () { renderRate(); schedule(); });
  }

  // GitHub's own status badge for each workflow: an image from github.com, so it is loaded here, by the page's script,
  // rather than by the page itself (the site's gate allows no third-party resource in the HTML).
  Array.prototype.forEach.call(document.querySelectorAll('.pl-badge[data-badge]'), function (s) {
    var img = new Image(); img.alt = s.textContent; img.height = 20; img.src = s.getAttribute('data-badge');
    s.textContent = ''; s.appendChild(img);
  });

  var btn = document.getElementById('pl-refresh');
  if (btn) btn.addEventListener('click', function () { run(cfg.sites); });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { clearTimeout(timer); return; }
    var stale = cfg.sites.some(function (site) { var s = state[site.id]; return !s || Date.now() - s.at > 60000; });
    if (stale) run(cfg.sites); else schedule();
  });
  run(cfg.sites);
})();
