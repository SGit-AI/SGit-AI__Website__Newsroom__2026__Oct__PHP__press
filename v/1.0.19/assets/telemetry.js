// php.oct.2026.newsroom.sgit.ai: anonymous page-view telemetry over an append lane.
// One event per page per session: path, referrer host, country/region/city from a geolocation
// lookup (the lookup service sees your IP; the event does not carry it), language, screen class,
// time zone, a random session id that lives in memory. Encrypted in this browser to the telemetry
// vault's public key (sgit hybrid envelope v2) and posted to a write-only lane. Never blocks,
// fails silently. The brief: admin/briefs/index.html. The data: data/telemetry.json.
// Two optional fields since v0.8.4, so the counts can tell readers from everyone else (admin/build/telemetry_classes.py):
//   agent  automation, by class only (webdriver, headless, lighthouse, googlebot, bingbot, ..., bot), never the user-agent string
//   who    a role, never an identity: what this browser was set to on /admin/telemetry/, or the role of its /join/ key
//          in data/contributors.json (editor, team, power-user). The identity store is read only if it already exists.
(async function () {
  try {
    if (!window.crypto || !crypto.subtle || !window.fetch) return
    if (navigator.doNotTrack === '1' || navigator.globalPrivacyControl === true) return
    const root = '../'.repeat(((document.documentElement.getAttribute('data-root') || '').match(/\.\.\//g) || []).length)
    const cfg = await (await fetch(root + 'data/telemetry.json', { cache: 'no-store' })).json()
    if (!cfg || !cfg.append_token || !cfg.recipient || !cfg.recipient.encrypt || cfg.enabled === false) return
    const key = 'php-newsroom.telemetry.session'
    let sid = ''
    try { sid = sessionStorage.getItem(key) || '' } catch (e) {}
    if (!sid) { sid = Array.from(crypto.getRandomValues(new Uint8Array(4))).map(b => b.toString(16).padStart(2, '0')).join(''); try { sessionStorage.setItem(key, sid) } catch (e) {} }
    const seenKey = key + '.seen'
    let seen = []
    try { seen = JSON.parse(sessionStorage.getItem(seenKey) || '[]') } catch (e) {}
    if (seen.includes((window.P2S_REAL_PATH || location.pathname))) return                       // one event per page per session
    const ref = (() => { try { return document.referrer ? new URL(document.referrer).host : '' } catch (e) { return '' } })()
    if (ref === location.host) { /* internal navigation: keep, it is a journey */ }
    const w = window.innerWidth || 0
    const ev = { v: 1, site: location.host, ver: (document.querySelector('nav .ver') || {}).textContent || '', ts: new Date().toISOString().slice(0, 16) + 'Z',
                 sid, path: (window.P2S_REAL_PATH || location.pathname), ref, country: '', region: '', city: '', lang: navigator.language || '',
                 screen: w < 600 ? 'phone' : w < 1000 ? 'tablet' : 'desktop', tz: (Intl.DateTimeFormat().resolvedOptions().timeZone || '') }
    const agent = automation(); if (agent) ev.agent = agent
    const who = await role(root); if (who) ev.who = who
    const geo = await lookup(cfg.geo || ['https://ipapi.co/json/', 'https://ipwho.is/'])
    if (geo) { ev.country = geo.country || ''; ev.region = geo.region || ''; ev.city = geo.city || '' }
    const payload = await envelope(cfg.recipient.encrypt, JSON.stringify(ev))
    const r = await fetch(`${cfg.endpoint}/api/vault/append/write/${cfg.vault_id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ append_token: cfg.append_token, payload }), keepalive: true })
    if (r.ok) { seen.push((window.P2S_REAL_PATH || location.pathname)); try { sessionStorage.setItem(seenKey, JSON.stringify(seen.slice(-50))) } catch (e) {} }
  } catch (e) { /* telemetry never surfaces */ }

  function automation() {
    const ua = navigator.userAgent || ''
    const named = [['googlebot', /Googlebot|Google-InspectionTool|Storebot-Google|AdsBot-Google/], ['bingbot', /bingbot|BingPreview/i], ['applebot', /Applebot/],
                   ['duckduckbot', /DuckDuckBot/], ['yandexbot', /YandexBot/], ['baiduspider', /Baiduspider/], ['lighthouse', /Lighthouse/]]
    for (const [n, re] of named) if (re.test(ua)) return n
    if (/bot\b|crawler|spider/i.test(ua)) return 'bot'
    if (navigator.webdriver) return 'webdriver'
    if (/HeadlessChrome/.test(ua)) return 'headless'
    return ''
  }
  async function role(root) {
    const ok = r => ['editor', 'team', 'power-user', 'reader'].includes(r) ? r : ''
    try { const set = ok(localStorage.getItem('p2s.telemetry.who') || ''); if (set) return set === 'reader' ? '' : set } catch (e) {}
    try {
      if (!indexedDB || !indexedDB.databases) return ''
      if (!(await indexedDB.databases()).some(d => d.name === 'p2s-identity')) return ''
      const me = await new Promise((done) => {
        const req = indexedDB.open('p2s-identity')
        req.onsuccess = () => { try { const g = req.result.transaction('keys', 'readonly').objectStore('keys').get('me'); g.onsuccess = () => done(g.result || null); g.onerror = () => done(null) } catch (e) { done(null) } }
        req.onerror = () => done(null)
      })
      if (!me || !me.bundle) return ''
      const c = await (await fetch(root + 'data/contributors.json', { cache: 'no-store' })).json()
      const fp = [me.bundle.signing_fingerprint, me.bundle.fingerprint]
      const k = (c.keys || []).find(k => fp.includes(k.signing_fingerprint) || fp.includes(k.fingerprint) || fp.includes(k.from))
      if (k && k.role) return ok(k.role)
      return me.bundle.label === 'editor' ? 'editor' : 'power-user'           // a key from an invitation, not enrolled yet
    } catch (e) { return '' }
  }
  async function lookup(urls) {
    for (const u of urls) {
      try {
        const ctrl = new AbortController(); const t = setTimeout(() => ctrl.abort(), 2500)
        const r = await fetch(u, { signal: ctrl.signal, cache: 'no-store' }); clearTimeout(t)
        if (!r.ok) continue
        const j = await r.json()
        const out = { country: j.country_code || j.country || '', region: j.region || j.region_name || '', city: j.city || '' }
        if (out.country) return out                                      // the ip field is never read
      } catch (e) {}
    }
    return null
  }
  // sgit's hybrid envelope v2, as the newsroom's meter and sgit_ai PKI__Crypto do it: a fresh AES-256-GCM key
  // wrapped with RSA-OAEP-SHA256 to the recipient's public key; the .enc text is base64 of {v:2,w,i,c};
  // the lane payload is base64 of that text's bytes (encoded twice, per the API page).
  async function envelope(pem, text) {
    const te = new TextEncoder()
    const der = Uint8Array.from(atob(pem.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '')), c => c.charCodeAt(0)).buffer
    const b64 = bytes => { let s = ''; for (const x of new Uint8Array(bytes)) s += String.fromCharCode(x); return btoa(s) }
    const pub = await crypto.subtle.importKey('spki', der, { name: 'RSA-OAEP', hash: 'SHA-256' }, false, ['encrypt'])
    const aes = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt'])
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const c = await crypto.subtle.encrypt({ name: 'AES-GCM', iv, tagLength: 128 }, aes, te.encode(text))
    const w = await crypto.subtle.encrypt({ name: 'RSA-OAEP' }, pub, await crypto.subtle.exportKey('raw', aes))
    const enc = btoa(JSON.stringify({ v: 2, w: b64(w), i: b64(iv), c: b64(c) }))
    return btoa(enc)
  }
})()
