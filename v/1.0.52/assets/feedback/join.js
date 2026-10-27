// php.oct.2026.newsroom.sgit.ai: /join/, the page an invitation's QR code opens. Kept by conductor@php.newsroom; the
// brief is admin/content/briefs/2026-10-22__brief__feedback-keys-and-review.md.
//
// The link is https://php.oct.2026.newsroom.sgit.ai/join/#j1.<code>.<handle>. The fragment never reaches a server, and
// this page removes it from the address bar at once. One tap makes this device's key (assets/feedback/identity.js)
// and sends the enrolment, signed by the new key and encrypted to the collaborators key, to the collaborators lane;
// the editor's side checks the signature and the code and enrols the key. Nothing else is stored or sent.
import { getIdentity, createIdentity, sign, sendToLane, siteData, readInvite } from './identity.js'

const root = new URL(document.documentElement.getAttribute('data-root') || '../', location.href).href
const out = document.getElementById('join-app')
// Two shapes of invitation: #i1.<a signed invitation> (made in the browser on /join/invite/), and #j1.<code>.<handle>
// (the conductor's bootstrap, for the editor's first key). Either is removed from the address bar at once.
const inv = readInvite(location.hash)
const m = inv ? [null, null, inv.handle] : /^#j1\.([0-9a-f]{32})\.([a-z0-9-]{1,40})$/.exec(location.hash)
if (location.hash) history.replaceState(null, '', location.pathname + location.search)

function el(tag, attrs, ...kids) {
  const e = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs || {})) { if (k === 'onclick') e.addEventListener('click', v); else e.setAttribute(k, v) }
  for (const k of kids) if (k != null) e.append(k)
  return e
}
function show(...kids) { out.replaceChildren(...kids) }
const device = () => /iPad|Tablet/i.test(navigator.userAgent) ? 'tablet' : /Mobi|Android|iPhone/i.test(navigator.userAgent) ? 'phone' : 'desktop'
const fpLine = me => el('p', { class: 'kv' }, el('b', null, 'This device’s key '), el('code', null, me.bundle.signing_fingerprint), ' (signing) · ', el('code', null, me.bundle.fingerprint), ' (encryption)')

// Where this device's key stands, from the site's own list (data/contributors.json): enrolled, or waiting for the team's
// next run. The editor's feedback of 23 October: right after joining, "Enrolled keys" said "None yet", with no word on
// whether joining had worked.
async function standing(me) {
  let k = null, may = ['editor']
  try { const { contributors } = await siteData(root); k = contributors.keys.find(x => x.signing_fingerprint === me.bundle.signing_fingerprint); may = contributors.rules.may_invite || may } catch (e) {}
  if (!k) return el('p', { class: 'kv' }, el('b', null, 'Waiting to be enrolled. '), 'Your enrolment reached the team; it is checked at the next run and your key appears in the list below after the release that follows. What you send in the meantime is kept, and counts as yours once you are enrolled.')
  return el('p', { class: 'kv' }, el('b', null, 'Enrolled. '), `This device’s key is enrolled as ${k.handle} (${k.role}) since ${k.enrolled}.`,
    may.includes(k.role) ? el('span', null, ' You can ', el('a', { href: root + 'join/invite/index.html' }, 'invite someone'), '.') : '')
}
const FEEDBACK_HOW = 'Press Feedback, next to Ask at the top of any page: say what is wrong, unclear, missing or good, with screenshots if you like. It is signed with this key.'

async function enrol(code, handle) {
  show(el('p', { class: 'sub-ok' }, 'Making this device’s key… (a few seconds)'))
  try {
    const { lane } = await siteData(root)
    let me = await getIdentity()
    if (!me) me = await createIdentity(handle)
    const msg = await sign(me, { v: 1, kind: 'enrol', code: code || '', invite: inv || null, handle, bundle: me.bundle, device: device(), at: new Date().toISOString(),
                                 site: document.documentElement.getAttribute('data-ver') || '' })
    await sendToLane(lane, msg)
    show(el('p', { class: 'sub-ok' }, 'Done. Your key is made and your enrolment is sent.'), fpLine(me), await standing(me),
      el('ol', null,
        el('li', null, 'Your key is checked at the team’s next run and added to the contributors. You can send feedback straight away; it is kept until then.'),
        el('li', null, FEEDBACK_HOW),
        el('li', null, 'Start with ', el('a', { href: root + 'collaborators/index.html' }, 'Power users: start here'), '.')),
      el('p', { class: 'small' }, 'The key lives in this browser only and cannot be copied out of it. Another device needs its own invitation. Clearing this site’s data deletes the key.'))
  } catch (e) {
    show(el('p', { class: 'sub-err' }, 'That did not work: ' + e.message + '. Try again, or tell the editor.'), el('button', { class: 'cta cta-pri', type: 'button', onclick: () => enrol(code, handle) }, 'Try again'))
  }
}

async function start() {
  const me = await getIdentity()
  if (!m) {
    if (me) { show(fpLine(me), await standing(me), el('p', null, FEEDBACK_HOW)); return }
    show(el('p', null, 'This page needs an invitation: a link or QR code from the editor. ',
      'To get one, ask Dinis by email or on WhatsApp, or use ', el('a', { href: root + 'collaborators/index.html#join' }, 'the join form'), '.'))
    return
  }
  const [, code, handle] = m
  if (inv && inv.exp < new Date().toISOString().slice(0, 10)) { show(el('p', { class: 'sub-err' }, 'This invitation expired on ' + inv.exp + '. Ask for a new one.')); return }
  show(el('p', null, 'You have been invited to give feedback on this site as ', el('b', null, handle), '. One tap makes a key for this device and sends it to the editor.'),
    me ? fpLine(me) : '',
    el('button', { class: 'cta cta-pri', type: 'button', onclick: () => enrol(code, handle) }, me ? 'Use this device’s key' : 'Make my key and join'))
}
if (!window.crypto || !crypto.subtle || !window.indexedDB) show(el('p', { class: 'sub-err' }, 'This browser cannot make a key (no Web Crypto or IndexedDB). Try a current browser.'))
else start()
