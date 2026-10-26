// php.oct.2026.newsroom.sgit.ai: /join/invite/, where an enrolled key makes an invitation, entirely in the browser.
// Kept by conductor@php.newsroom; the brief is admin/content/briefs/2026-10-22__brief__feedback-keys-and-review.md.
//
// The invitation is signed here by this device's key (assets/feedback/identity.js) and shown as a link, a QR code and a
// share button (WhatsApp, Messages, email: whatever this device offers). Nothing is written anywhere: the drain checks,
// when the invited person joins, that this key is enrolled with a role that may invite and that the invitation is in date.
import qrcode from '../vendor/qrcode-generator/2.0.4/qrcode.mjs'
import { getIdentity, siteData, makeInvite, inviteLink } from './identity.js'

const root = new URL(document.documentElement.getAttribute('data-root') || '../../', location.href).href
const out = document.getElementById('invite-app')
function el(tag, attrs, ...kids) {
  const e = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs || {})) { if (k.startsWith('on')) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v) }
  for (const k of kids) if (k != null) e.append(k)
  return e
}
const show = (...kids) => out.replaceChildren(...kids)

function qrSvg(text) {
  const q = qrcode(0, 'M'); q.addData(text); q.make()
  const n = q.getModuleCount(), cell = 6, pad = 4 * cell, size = n * cell + 2 * pad
  let path = ''
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (q.isDark(r, c)) path += `M${pad + c * cell},${pad + r * cell}h${cell}v${cell}h-${cell}z`
  const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg')
  svg.setAttribute('viewBox', `0 0 ${size} ${size}`); svg.setAttribute('width', '260'); svg.setAttribute('height', '260')
  svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', 'QR code of the invitation link')
  const bg = document.createElementNS(ns, 'rect'); bg.setAttribute('width', size); bg.setAttribute('height', size); bg.setAttribute('fill', '#fff')
  const p = document.createElementNS(ns, 'path'); p.setAttribute('d', path); p.setAttribute('fill', '#000')
  svg.append(bg, p)
  return svg
}

async function start() {
  const me = await getIdentity()
  if (!me) { show(el('p', null, 'This device has no key yet. Open an invitation first: ', el('a', { href: root + 'join/index.html' }, 'Join'), '.')); return }
  const { contributors } = await siteData(root)
  const mine = contributors.keys.find(k => k.signing_fingerprint === me.bundle.signing_fingerprint)
  const may = contributors.rules.may_invite || ['editor']
  if (!mine || !may.includes(mine.role)) {
    show(el('p', null, 'This device’s key (', el('code', null, me.bundle.signing_fingerprint), ') ', mine ? `is enrolled as ${mine.role}, which cannot invite yet.` : 'is not enrolled yet: it is once the next release lists it on Join.'),
      el('p', { class: 'small' }, 'Invitations can be made by: ' + may.join(', ') + '.'))
    return
  }
  const handle = el('input', { type: 'text', name: 'handle', required: '', maxlength: '40', pattern: '[a-z0-9-]{1,40}', placeholder: 'e.g. power-user-04' })
  const role = el('select', { name: 'role' }, ...contributors.roles.filter(([r]) => r !== 'editor').map(([r, t]) => el('option', { value: r }, r)))
  const days = el('select', { name: 'days' }, ...[[2, '2 days'], [7, 'a week'], [14, 'two weeks']].map(([d, t]) => el('option', { value: d, ...(d === 7 ? { selected: '' } : {}) }, t)))
  const res = el('div')
  const form = el('form', { class: 'subform', onsubmit: async e => {
    e.preventDefault()
    const h = handle.value.trim().toLowerCase()
    if (!/^[a-z0-9-]{1,40}$/.test(h)) { res.replaceChildren(el('p', { class: 'sub-err' }, 'A handle is lowercase letters, digits and hyphens: never a person’s full name.')); return }
    const inv = await makeInvite(me, { handle: h, role: role.value, days: Number(days.value) })
    const link = inviteLink(root, inv)
    const text = `You are invited to give feedback on PHP October 2026. Open this on the device you will use (it makes your key there, in one tap): ${link}`
    const copy = el('button', { type: 'button', class: 'cta', onclick: async () => { try { await navigator.clipboard.writeText(link); copy.textContent = 'Copied' } catch (x) { copy.textContent = 'Copy failed: select the link' } } }, 'Copy the link')
    const share = navigator.share ? el('button', { type: 'button', class: 'cta cta-pri', onclick: () => navigator.share({ title: 'Your invitation', text }).catch(() => {}) }, 'Share (WhatsApp, Messages, email)') : null
    const wa = el('a', { class: 'cta', href: 'https://wa.me/?text=' + encodeURIComponent(text), rel: 'noopener', target: '_blank' }, 'Open in WhatsApp')
    res.replaceChildren(el('p', { class: 'sub-ok' }, `Invitation for ${h} (${inv.role}), valid until ${inv.exp}, signed by this device.`),
      qrSvg(link), el('p', null, share, ' ', wa, ' ', copy),
      el('p', { class: 'small' }, 'Send it to that one person: until it is used, anyone holding the link can join with it, up to three devices. ',
        el('code', { style: 'word-break:break-all' }, link)))
  } },
    el('p', null, el('label', null, 'A handle for them (not their name) ', handle)),
    el('p', null, el('label', null, 'Role ', role), ' ', el('label', null, 'Valid for ', days)),
    el('p', null, el('button', { type: 'submit', class: 'cta cta-pri' }, 'Make the invitation')))
  show(el('p', { class: 'kv' }, el('b', null, 'Signing as '), mine.handle, ' (', mine.role, ') ', el('code', null, me.bundle.signing_fingerprint)), form, res)
}
if (!window.crypto || !crypto.subtle || !window.indexedDB) show(el('p', { class: 'sub-err' }, 'This browser cannot sign (no Web Crypto or IndexedDB).'))
else start().catch(e => show(el('p', { class: 'sub-err' }, 'Could not start: ' + e.message)))
