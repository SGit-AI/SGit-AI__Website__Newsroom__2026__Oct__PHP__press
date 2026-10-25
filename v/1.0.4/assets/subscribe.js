// php.oct.2026.newsroom.sgit.ai: subscribe and unsubscribe (/subscribe/). The brief is
// admin/content/briefs/2026-10-22__feeds-the-delta-and-subscriptions.md.
//
// The request (the address, what to follow, how often) is encrypted here, in your browser, to the subscriptions
// vault's public key (data/subscriptions.json), with sgit's hybrid envelope v2 as assets/telemetry.js does it,
// and posted to that vault's write-only lane. The lane's answer is blind, so this page cannot tell whether a
// request arrived, only that it was sent. Anyone can type any address, so nothing is sent to an address until
// it answers the confirmation that the agent at the contact address writes to it.
(function () {
  'use strict';
  var form = document.getElementById('sub-form'), cfgEl = document.getElementById('sub-config');
  if (!form || !cfgEl) return;
  var cfg = JSON.parse(cfgEl.textContent), out = document.getElementById('sub-out'), last = 0;
  function say(t, ok) { out.textContent = t; out.className = ok ? 'sub-ok' : 'sub-err'; }
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
  form.addEventListener('submit', async function (ev) {
    ev.preventDefault();
    var f = new FormData(form);
    if (f.get('website')) return say('Sent.', true);                       // the field people cannot see: a form-filling bot
    var email = String(f.get('email') || '').trim(), kind = String(f.get('kind') || 'subscribe');
    if (email.length > 254 || !/^[^\s@<>()",;:]+@[^\s@<>()",;:]+\.[a-z]{2,}$/i.test(email)) return say('That does not look like an email address.', false);
    var zones = f.getAll('zones').map(String).filter(function (z) { return cfg.zones.some(function (x) { return x[0] === z; }); });
    var cadence = String(f.get('cadence') || '');
    if (kind === 'subscribe' && !zones.length) return say('Pick at least one part of the site to follow.', false);
    if (cadence && !cfg.cadences.some(function (x) { return x[0] === cadence; })) cadence = cfg.cadences[0][0];
    if (Date.now() - last < 30000) return say('Sent a moment ago; give it a minute before sending again.', false);
    if (!window.crypto || !crypto.subtle) return say('This browser cannot encrypt the request. Write to ' + cfg.contact + ' instead.', false);
    var req = { v: 1, kind: kind, email: email, zones: kind === 'subscribe' ? zones : [], cadence: kind === 'subscribe' ? cadence : null,
                note: String(f.get('note') || '').slice(0, 500), at: new Date().toISOString(), site: document.documentElement.getAttribute('data-ver') || '',
                lang: navigator.language || '', tz: (Intl.DateTimeFormat().resolvedOptions().timeZone || '') };
    try {
      say('Encrypting and sending…', true);
      var payload = await envelope(cfg.recipient.encrypt, JSON.stringify(req));
      var r = await fetch(cfg.endpoint + '/api/vault/append/write/' + cfg.vault_id, { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'omit', referrerPolicy: 'no-referrer', body: JSON.stringify({ append_token: cfg.append_token, payload: payload }) });
      if (!r.ok) throw new Error('the lane answered ' + r.status);
      last = Date.now();
      form.reset();
      say(kind === 'subscribe'
        ? 'Sent. The agent at ' + cfg.contact + ' will write to ' + email + ' to confirm it is yours; nothing is sent to it until you answer. Not there in a day? Write to ' + cfg.contact + '.'
        : 'Sent. ' + email + ' will be taken off the list, and the agent at ' + cfg.contact + ' will write once to say so.', true);
    } catch (e) {
      say('It could not be sent (' + e.message + '). Write to ' + cfg.contact + ' instead; the link is below.', false);
    }
  });
})();
