// php.oct.2026.newsroom.sgit.ai: the collaborators' two forms (/collaborators/), join and feedback. Kept by
// conductor@php.newsroom; the page is built from data/collaborators.json.
//
// Each form's message is encrypted here, in your browser, to the collaborators vault's public key, with sgit's
// hybrid envelope v2 as assets/subscribe.js does it, and posted to that vault's write-only lane. The lane's answer
// is blind, so this page can say a message was sent, never that it arrived. Nothing is stored in the browser.
(function () {
  'use strict';
  var cfgEl = document.getElementById('collab-config');
  if (!cfgEl) return;
  var cfg = JSON.parse(cfgEl.textContent), last = 0;
  async function envelope(pem, text) {
    var te = new TextEncoder();
    var der = Uint8Array.from(atob(pem.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '')), function (c) { return c.charCodeAt(0); }).buffer;
    function b64(bytes) { var s = ''; new Uint8Array(bytes).forEach(function (x) { s += String.fromCharCode(x); }); return btoa(s); }
    var pub = await crypto.subtle.importKey('spki', der, { name: 'RSA-OAEP', hash: 'SHA-256' }, false, ['encrypt']);
    var aes = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt']);
    var iv = crypto.getRandomValues(new Uint8Array(12));
    var c = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv, tagLength: 128 }, aes, te.encode(text));
    var w = await crypto.subtle.encrypt({ name: 'RSA-OAEP' }, pub, await crypto.subtle.exportKey('raw', aes));
    return btoa(btoa(JSON.stringify({ v: 2, w: b64(w), i: b64(iv), c: b64(c) })));
  }
  function field(f, name, max) { return String(f.get(name) || '').trim().slice(0, max); }
  function okEmail(e) { return !e || (e.length <= 254 && /^[^\s@<>()",;:]+@[^\s@<>()",;:]+\.[a-z]{2,}$/i.test(e)); }
  function wire(formId, outId, build, done) {
    var form = document.getElementById(formId), out = document.getElementById(outId);
    if (!form || !out) return;
    function say(t, ok) { out.textContent = t; out.className = ok ? 'sub-ok' : 'sub-err'; }
    form.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      var f = new FormData(form);
      if (f.get('website')) return say('Sent.', true);                     // the field people cannot see: a form-filling bot
      var msg = build(f);
      if (typeof msg === 'string') return say(msg, false);
      if (Date.now() - last < 30000) return say('Sent a moment ago; give it a minute before sending again.', false);
      if (!window.crypto || !crypto.subtle) return say('This browser cannot encrypt the message. Write to ' + cfg.contact + ' instead.', false);
      msg.v = 1; msg.at = new Date().toISOString(); msg.site = document.documentElement.getAttribute('data-ver') || '';
      msg.lang = navigator.language || ''; msg.tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
      try {
        say('Encrypting and sending…', true);
        var payload = await envelope(cfg.recipient.encrypt, JSON.stringify(msg));
        var r = await fetch(cfg.endpoint + '/api/vault/append/write/' + cfg.vault_id, { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'omit', referrerPolicy: 'no-referrer', body: JSON.stringify({ append_token: cfg.append_token, payload: payload }) });
        if (!r.ok) throw new Error('the lane answered ' + r.status);
        last = Date.now();
        form.reset();
        say(done(msg), true);
      } catch (e) {
        say('It could not be sent (' + e.message + '). Write to ' + cfg.contact + ' instead.', false);
      }
    });
  }
  wire('join-form', 'join-out', function (f) {
    var m = { kind: 'join', name: field(f, 'name', 120), email: field(f, 'email', 254), knows: field(f, 'knows', 300),
              reader: field(f, 'reader', 40), whatsapp: f.get('whatsapp') === 'yes', note: field(f, 'note', 1000) };
    if (!m.name) return 'Tell us your name.';
    if (!m.email || !okEmail(m.email)) return 'That does not look like an email address.';
    if (m.reader && !cfg.readers.some(function (x) { return x[0] === m.reader; })) m.reader = '';
    return m;
  }, function (m) {
    return 'Sent. The editor reads every request; you will hear back at ' + m.email + (m.whatsapp ? ', and he will ask for your number to add you to the WhatsApp group.' : '.');
  });
  wire('fb-form', 'fb-out', function (f) {
    var m = { kind: 'feedback', ask: field(f, 'ask', 10), reader: field(f, 'reader', 40), page: field(f, 'page', 300),
              worked: field(f, 'worked', 3000), missing: field(f, 'missing', 3000), next: field(f, 'next', 3000),
              name: field(f, 'name', 120), email: field(f, 'email', 254) };
    if (!m.worked && !m.missing && !m.next) return 'Write something in at least one of the three boxes.';
    if (!okEmail(m.email)) return 'That does not look like an email address (or leave it empty).';
    if (m.ask && !cfg.asks.includes(m.ask)) m.ask = '';
    if (m.reader && !cfg.readers.some(function (x) { return x[0] === m.reader; })) m.reader = '';
    return m;
  }, function () { return 'Sent, thank you. It goes to the team at the next run, and what it changes shows on the board.'; });
})();
