// php.oct.2026.newsroom.sgit.ai: this device's key, for signing what a contributor sends. Kept by conductor@php.newsroom;
// the brief is admin/content/briefs/2026-10-22__brief__feedback-keys-and-review.md.
//
// The key pair is sgit's and pki.sgit.ai's format: RSA-OAEP 4096 (to receive a secret later) and ECDSA P-256 (to sign),
// the public half the JSON bundle `sgit pki export` emits, a fingerprint "sha256:" + the first 16 hex of the SHA-256
// of the key's SPKI bytes. The private halves are generated non-extractable and kept in this browser's IndexedDB: they
// can sign, and no script can read them back out. A signature is ECDSA P-256/SHA-256, raw r||s, base64, over the
// canonical bytes pki.sgit.ai uses (keys sorted, no spaces, a newline at the end, without the sig field), so
// `sgit pki verify` checks it. What is sent is encrypted here to the collaborators vault's public key (sgit's hybrid
// envelope v2, as assets/subscribe.js does it) and posted to that vault's write-only lane.

const DB = 'p2s-identity', STORE = 'keys', ME = 'me'
const EC = { name: 'ECDSA', namedCurve: 'P-256' }, ECDSA = { name: 'ECDSA', hash: 'SHA-256' }
const RSA_GEN = { name: 'RSA-OAEP', modulusLength: 4096, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }
const te = new TextEncoder()

const b64 = bytes => { let s = ''; new Uint8Array(bytes).forEach(x => { s += String.fromCharCode(x) }); return btoa(s) }
const hex = bytes => [...new Uint8Array(bytes)].map(b => b.toString(16).padStart(2, '0')).join('')
const pem = (der, label) => `-----BEGIN ${label}-----\n${b64(der).match(/.{1,64}/g).join('\n')}\n-----END ${label}-----\n`
const fingerprint = async spki => 'sha256:' + hex(await crypto.subtle.digest('SHA-256', spki)).slice(0, 16)

/** pki.sgit.ai's canonical JSON: keys sorted, no whitespace, integers only. */
export function canon(v) {
  if (Array.isArray(v)) return '[' + v.map(canon).join(',') + ']'
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}'
  if (typeof v === 'number' && !Number.isInteger(v)) throw new Error('a signed message carries no non-integer numbers')
  return JSON.stringify(v)
}

function db() {
  return new Promise((ok, no) => {
    const r = indexedDB.open(DB, 1)
    r.onupgradeneeded = () => r.result.createObjectStore(STORE)
    r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error)
  })
}
async function idb(mode, fn) {
  const d = await db()
  return new Promise((ok, no) => { const t = d.transaction(STORE, mode), r = fn(t.objectStore(STORE)); t.oncomplete = () => ok(r && r.result); t.onerror = () => no(t.error) })
}

/** This device's identity, or null: { bundle, handle, created, sign (a CryptoKey that cannot be exported) }. */
export async function getIdentity() {
  try { return (await idb('readonly', s => s.get(ME))) || null } catch (e) { return null }
}

/** Make this device's key pair (a few seconds: RSA 4096) and keep it. Returns the identity. */
export async function createIdentity(label) {
  const enc = await crypto.subtle.generateKey(RSA_GEN, false, ['encrypt', 'decrypt'])
  const sig = await crypto.subtle.generateKey(EC, false, ['sign', 'verify'])
  const encSpki = await crypto.subtle.exportKey('spki', enc.publicKey), sigSpki = await crypto.subtle.exportKey('spki', sig.publicKey)
  const bundle = { v: 1, encrypt: pem(encSpki, 'PUBLIC KEY'), sign: pem(sigSpki, 'PUBLIC KEY'), label: String(label || '').slice(0, 80),
                   fingerprint: await fingerprint(encSpki), signing_fingerprint: await fingerprint(sigSpki) }
  const me = { bundle, created: new Date().toISOString(), sign: sig.privateKey, decrypt: enc.privateKey }
  await idb('readwrite', s => s.put(me, ME))
  return me
}

/** Forget this device's key. It cannot be recovered: a new one needs a new invitation. */
export async function forgetIdentity() { await idb('readwrite', s => s.delete(ME)) }

/** The message with from (the signing fingerprint) and sig: raw r||s, base64, over canon(message without sig) + "\n". */
export async function sign(me, msg) {
  const body = { ...msg, from: me.bundle.signing_fingerprint }
  delete body.sig
  const sig = await crypto.subtle.sign(ECDSA, me.sign, te.encode(canon(body) + '\n'))
  return { ...body, sig: b64(sig) }
}

async function envelope(pemText, text) {
  const der = Uint8Array.from(atob(pemText.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '')), c => c.charCodeAt(0)).buffer
  const pub = await crypto.subtle.importKey('spki', der, { name: 'RSA-OAEP', hash: 'SHA-256' }, false, ['encrypt'])
  const aes = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt'])
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const c = await crypto.subtle.encrypt({ name: 'AES-GCM', iv, tagLength: 128 }, aes, te.encode(text))
  const w = await crypto.subtle.encrypt({ name: 'RSA-OAEP' }, pub, await crypto.subtle.exportKey('raw', aes))
  return btoa(btoa(JSON.stringify({ v: 2, w: b64(w), i: b64(iv), c: b64(c) })))
}

/** Encrypt a message to the lane's recipient and post it. The lane answers blind, so this says sent, never arrived. */
export async function sendToLane(lane, msg) {
  const payload = await envelope(lane.recipient.encrypt, JSON.stringify(msg))
  if (payload.length > 4_800_000) throw new Error('too large to send: use a smaller screenshot')
  const r = await fetch(`${lane.endpoint}/api/vault/append/write/${lane.vault_id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    credentials: 'omit', referrerPolicy: 'no-referrer', body: JSON.stringify({ append_token: lane.append_token, payload }) })
  if (!r.ok) throw new Error('the lane answered ' + r.status)
}

/** The lane and the contributors list, from the site's own data. */
export async function siteData(root) {
  const get = async p => { const r = await fetch(root + p, { credentials: 'omit' }); if (!r.ok) throw new Error(p + ': ' + r.status); return r.json() }
  const [collab, contributors] = await Promise.all([get('data/collaborators.json'), get('data/contributors.json')])
  return { lane: collab.lane, contributors }
}

// ------------------------------------------------------------------ invitations, signed in the browser
// An invitation is a small signed object: { v, kind: 'invite', exp (YYYY-MM-DD), nonce, role, handle, from, sig },
// signed by an enrolled key the way every message is. It travels in a link's fragment as base64url JSON:
// <site>/join/#i1.<invitation>. It needs nothing written anywhere to be valid: the drain checks that its signer is an
// enrolled key allowed to invite, that it has not expired, and how many devices it has already enrolled.
const b64url = s => btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
const unb64url = s => atob(s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4))

export async function makeInvite(me, { handle, role, days = 14 }) {
  const exp = new Date(Date.now() + days * 864e5).toISOString().slice(0, 10)
  const nonce = hex(crypto.getRandomValues(new Uint8Array(12)))
  return sign(me, { v: 1, kind: 'invite', exp, nonce, role, handle })
}
export const inviteLink = (root, inv) => root + 'join/#i1.' + b64url(unescape(encodeURIComponent(JSON.stringify(inv))))
export function readInvite(fragment) {
  const m = /^#i1\.([A-Za-z0-9_-]{40,4000})$/.exec(fragment || '')
  if (!m) return null
  try {
    const inv = JSON.parse(decodeURIComponent(escape(unb64url(m[1]))))
    if (inv.kind !== 'invite' || !/^[a-z0-9-]{1,40}$/.test(inv.handle) || !/^\d{4}-\d{2}-\d{2}$/.test(inv.exp) || !inv.sig) return null
    return inv
  } catch (e) { return null }
}
