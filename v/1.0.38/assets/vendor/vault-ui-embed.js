/* Vendored from https://sgit.ai/assets/vault-ui-embed.js on 2026-10-22 (sha256 308af99563423f5e...), unchanged below this line.
   The sgit.ai network's embed of the official SG/Vault UI; this site's gate allows no third-party script. */
/* vault-ui-embed.js, the official SG/Vault interface, embedded via its embed
   protocol, as a reusable component.

   Usage (one div per embed):
     <div class="sgv-uiembed" data-vault="4bshby5n" data-readkey="<64-hex>"
          data-app="1"></div>
   data-app="0" hides the App Mode surface (vaults without an app.json).

   Both surfaces open ON PAGE LOAD, stacked (App Mode first, the vault browser
   under it) so the reader lands on the vault, not on a row of buttons. The
   opens are SEQUENTIAL by design: the browser surface starts once the app
   reports vault-ready (or after a short grace period), so its objects come out
   of the client's encrypted-object cache, the second surface mostly decrypts
   rather than fetches, which is the caching story demonstrating itself.

   The handshake (see the UI's embed-protocol.js): load ?embed=1&parent=<origin>,
   wait for {sg:'vault-embed-ready'} FROM THAT FRAME, then post
   {sg:'vault-open', key, mode} with targetOrigin pinned to the vault origin.
   The key is a published read-only credential; it never appears in a URL and
   the frame keeps it in memory only. vault-ready / vault-error come back as
   structured events and drive each frame's status line. */
(function () {
  'use strict';
  var ORIGIN = 'https://dev.vault.sgraph.ai';

  function mountAll() {
    var hosts = document.querySelectorAll('.sgv-uiembed');
    for (var i = 0; i < hosts.length; i++) mount(hosts[i]);
  }

  function mount(el) {
    var vaultId = el.getAttribute('data-vault');
    var readKey = el.getAttribute('data-readkey');
    var hasApp = el.getAttribute('data-app') !== '0';
    if (!vaultId || !readKey) return;
    var cred = 'sgit_rk1_' + readKey + ':' + vaultId;

    var sections = [];
    if (hasApp) sections.push(section(el, cred, 'app', '▶ App Mode (the vault’s own app'));
    sections.push(section(el, cred, 'vault', '▤ Vault browser) FILES / SGIT / SETTINGS'));

    // One listener for the mount; route replies by which frame sent them.
    window.addEventListener('message', function (e) {
      if (e.origin !== ORIGIN) return;
      for (var i = 0; i < sections.length; i++) {
        var s = sections[i];
        if (!s.frame.contentWindow || e.source !== s.frame.contentWindow) continue;
        var d = e.data || {};
        if (d.sg === 'vault-embed-ready' && s.armed) {
          clearTimeout(s.fallbackT);
          e.source.postMessage({ sg: 'vault-open', key: cred, mode: s.mode }, ORIGIN);
          s.note.textContent = 'Handshake complete, key handed over postMessage, opening…';
        } else if (d.sg === 'vault-ready') {
          s.note.innerHTML = 'Opened <b>read-only</b> over the embed protocol, the key never appeared in a URL and was never written to the frame’s storage' +
            (Number(d.fileCount) > 0 ? '; ' + Number(d.fileCount) + ' files decrypted in the frame' : '') + '.';
          if (s.onReady) { s.onReady(); s.onReady = null; }
        } else if (d.sg === 'vault-error') {
          s.note.textContent = 'Vault open failed: ' + (d.message || 'unknown error');
          if (s.onReady) { s.onReady(); s.onReady = null; }
        }
        return;
      }
    });

    // Auto-open on load: the first surface now; the next when the previous is
    // ready (its fetches then hit the warm cache), with a grace timeout so one
    // slow surface never blocks the next.
    var chain = sections.slice();
    (function next() {
      var s = chain.shift();
      if (!s) return;
      var advanced = false;
      var advance = function () { if (!advanced) { advanced = true; next(); } };
      s.onReady = advance;
      setTimeout(advance, 9000);
      s.open();
    }());
  }

  // Build one surface: a label, its status line, its frame, and a retry control.
  function section(el, cred, mode, label) {
    var s = { mode: mode, armed: false, fallbackT: null, onReady: null };

    var h = document.createElement('div');
    h.className = 'sgv-uiembed-label';
    h.textContent = label;

    s.note = document.createElement('p');
    s.note.className = 'small dim'; s.note.style.margin = '.35rem 0 .5rem';
    s.note.textContent = 'Opening…';

    s.frame = document.createElement('iframe');
    s.frame.className = 'sgv-embed-frame sgv-embed-ui sgv-breakout';
    s.frame.title = 'The official SG/Vault UI (' + (mode === 'app' ? 'App Mode' : 'vault browser') + '), opened read-only';
    s.frame.style.display = 'none';

    el.appendChild(h); el.appendChild(s.note); el.appendChild(s.frame);

    s.open = function () {
      s.armed = true;
      s.frame.style.display = 'block';
      s.note.textContent = 'Handshaking with the vault UI…';
      var page = mode === 'vault' ? '/en-gb/vault/' : '/en-gb/app/';
      s.frame.src = ORIGIN + page + '?embed=1&parent=' + encodeURIComponent(location.origin);
      clearTimeout(s.fallbackT);
      s.fallbackT = setTimeout(function () {
        if (mode === 'app') {
          s.frame.src = ORIGIN + '/#' + encodeURIComponent(cred);
          s.note.textContent = 'Embed handshake timed out; fell back to the URL-fragment flow.';
        } else {
          s.note.innerHTML = 'Embed handshake timed out. ';
          var retry = document.createElement('button');
          retry.type = 'button'; retry.className = 'sgv-embed-load';
          retry.style.padding = '.2rem .7rem'; retry.style.fontSize = '.75rem';
          retry.textContent = '↻ retry';
          retry.addEventListener('click', function () { retry.remove(); s.open(); });
          s.note.appendChild(retry);
        }
      }, 12000);
    };
    return s;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountAll);
  else mountAll();
}());
