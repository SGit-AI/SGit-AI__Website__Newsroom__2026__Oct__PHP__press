// php.oct.2026.newsroom.sgit.ai: the phone app (now/). The brief: admin/content/briefs/2026-10-22__brief__the-phone-app.md.
//
// One question: what do I need to know now, for the time I have? The answer is computed from now/now.json (every item
// on the site, with the hash of what it says now) against what this reader has read (assets/reader-state.js, the same
// store as the rest of the site), ranked, and cut to one, five, ten or thirty minutes.
//
// Two modes. Deterministic: the items, their order and their connections come from the data and nothing else.
// Agentic: the same items, handed to a model through OpenRouter with the reader's own key, for a briefing in prose
// (text model, Claude Sonnet by default), an infographic (image model, Gemini by default) and a chat grounded in the
// site's facts. A model is only ever given what the deterministic mode shows, and every claim it makes must cite an
// item id, which the page turns back into a link.
//
// The reader's vault: any sgit vault key (a newsroom.sgit.ai reader vault works). Opened in this browser with the
// vault library (assets/vendor/sg-vault, loaded only when needed) through assets/vault/newsroom-vault.js. Everything
// the app keeps is written under /php-october/, encrypted here before it leaves:
//   devices/<this device>.json  what this device has read, and its notes   (one file per device: no write conflicts)
//   settings.json                reader, time budget, mode, models
//   secrets/openrouter.json      the OpenRouter key                          (never in local storage, never sent anywhere but OpenRouter)
//   chats/<id>.json              each conversation
//   made/<stamp>.json|.png       what the models wrote and drew, with the model, the items given and the cost
// The vault key is kept for the life of the tab in sessionStorage, and in localStorage only if the reader ticks
// "remember on this phone". The write token for the vault server lives inside the vault (/.vault/access-token.json).

const ROOT = '../'
const LS = 'p2s.now.v1', KEY_S = 'p2s.now.vault', PERSONA = 'p2s.persona'
// a script's own files through the page's resolver (boot.js): from the press on the split sites, from here on this site
const AT = u => (window.P2S_URL ? window.P2S_URL(u) : u)
const LIB = ['sg-send/sg-send-crypto.js', 'sg-send/sg-send.js', 'sg-vault/sg-vault-crypto.js', 'sg-vault/sg-vault-object-store.js', 'sg-vault/sg-vault-ref-manager.js',
  'sg-vault/sg-vault-commit.js', 'sg-vault/sg-vault.js', 'sg-vault/sg-vault--file-ops.js', 'sg-vault/sg-vault--folder-ops.js', 'sg-vault/sg-vault--sync.js',
  'sg-vault/sg-vault--history.js', 'sg-vault/sg-vault--branches.js'].map(f => AT(`${ROOT}assets/vendor/sg-vault/v0.2.3/${f}`)).concat([AT(`${ROOT}assets/vendor/sg-vault/local/sg-vault--create-with-id.js`)])
const BUDGETS = [[1, 'headlines'], [5, 'the gist'], [10, 'with links'], [30, 'the lot']]
const KIND = { fact: 'Fact', page: 'Page', briefing: 'Briefing', front: 'Front page', story: 'Story', question: 'Question', source: 'Source', event: 'Timeline' }
const OR = 'https://openrouter.ai/api/v1/chat/completions'

// ------------------------------------------------------------------ small helpers
const $ = sel => document.querySelector(sel)
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue
    if (k.startsWith('on')) el.addEventListener(k.slice(2), v)
    else if (k === 'html') el.innerHTML = v
    else el.setAttribute(k, v === true ? '' : v)
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid instanceof Node ? kid : String(kid))
  return el
}
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
const load = (k, d) => { try { return JSON.parse(localStorage.getItem(k) || 'null') || d } catch (e) { return d } }
const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)) } catch (e) {} }
const stamp = () => new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z')
function ago(iso) {
  const t = Date.parse(iso); if (!t) return ''
  const m = Math.round((Date.now() - t) / 60000)
  return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : Math.round(m / 1440) + ' days ago'
}
function toast(t) { const e = h('div', { class: 'toast', role: 'status' }, t); document.body.append(e); setTimeout(() => e.remove(), 2600) }

// ------------------------------------------------------------------ state
let DATA = null
const S = Object.assign({ mode: 'det', budget: 5, tab: 'now', models: null }, load(LS, {}))
const V = { nv: null, vault: null, send: null, key: null, writable: false, status: 'off', last: null, err: '', orKey: null, files: [], made: [], chats: [] }
const R = () => window.P2SReader
const persona = () => { const id = (() => { try { return localStorage.getItem(PERSONA) } catch (e) { return null } })(); return (DATA.personas.find(p => p.id === id)) || null }
const models = () => Object.assign({}, DATA.models, S.models || {})
function keep() { save(LS, { mode: S.mode, budget: S.budget, tab: S.tab, models: S.models }) }

// ------------------------------------------------------------------ what do I need to know
function delta() {
  const r = R(), st = r ? r.store() : { items: {} }, fresh = !st.items || Object.keys(st.items).length === 0
  const p = persona(), mine = new Set(p ? [`briefing-${p.id}`].concat(p.path.map(x => 'page-' + x.replace(/\/index\.html$/, '').replace(/\//g, '-'))) : [])
  const order = DATA.releases.map(x => x.version)
  const out = []
  for (const it of DATA.items) {
    const s = r ? r.state(it.id, it.hash) : 'new'
    if (s === 'read') continue
    let score = it.w + (s === 'changed' ? 15 : 0) + Math.max(0, 12 - order.indexOf(it.changed) * 3)
    if (mine.has(it.id) || (it.links || []).some(l => l[0] === 'briefing' && p && l[1] === p.id)) score += 20
    if (it.kind === 'fact' && /contradicted|disputed/.test(it.status)) score += 6
    out.push(Object.assign({ state: s, score }, it))
  }
  out.sort((a, b) => b.score - a.score || (b.date || '').localeCompare(a.date || '') || a.id.localeCompare(b.id))
  return { fresh, list: out, last: st.visits && st.visits.prev }
}

function cut(list, minutes) {
  // Seconds to spend: the situation line costs 20, a headline 6, a summary its reading time, with links a little more.
  let left = minutes * 60 - 20
  const level = minutes <= 1 ? 'head' : minutes <= 5 ? 'gist' : minutes <= 10 ? 'links' : 'all'
  const pool = minutes < 30 ? list.filter(x => x.kind !== 'source') : list
  const shown = []
  for (const it of pool) {
    const cost = level === 'head' ? 6 : level === 'gist' ? it.sec : it.sec + 8
    if (cost > left && shown.length) break
    shown.push(it); left -= cost
  }
  return { shown, level, rest: list.length - shown.length }
}

// ------------------------------------------------------------------ rendering: Now
function itemCard(it, level) {
  const r = R(), read = r && r.state(it.id, it.hash) === 'read'
  const card = h('article', { class: 'it' + (read ? ' read' : '') })
  const meta = h('div', { class: 'meta' }, h('span', { class: 'chip c-' + it.state }, it.state === 'changed' ? 'Changed' : 'New'), h('span', { class: 'chip' }, KIND[it.kind] || it.kind),
    it.status ? h('span', { class: 'chip st-' + it.status.split(/[ ,:;]/)[0] }, it.status.split(/[;:(]/)[0].trim()) : null,
    h('span', null, it.changed === it.first ? `added in v${it.changed}` : `v${it.v}, changed in v${it.changed}`))
  card.append(meta, h('h3', null, h('a', { href: ROOT + it.path }, it.title)))
  if (level !== 'head' && it.text && it.text !== it.title) card.append(h('p', null, it.text))
  if ((level === 'links' || level === 'all') && it.links && it.links.length) {
    const conn = h('div', { class: 'conn' }, h('span', { class: 'k' }, 'connects to'))
    for (const l of it.links) conn.append(h('a', { href: ROOT + l[3] }, (l[0] === 'briefing' ? 'for ' : '') + l[2]))
    if (it.history && it.state === 'changed') conn.append(h('a', { href: ROOT + it.history }, 'what changed'))
    card.append(conn)
  }
  card.append(h('button', { class: 'tick', type: 'button', 'aria-label': read ? 'Mark as not read' : 'Mark as read', onclick: () => {
    if (!r) return
    if (read) r.markUnread(it.id); else r.markRead(it.id, it.hash)
    r.persist(); scheduleSync(); render()
  } }, '✓'))
  return card
}

function renderNow(view) {
  const d = delta(), p = persona()
  view.append(h('div', { class: 'seg', role: 'group', 'aria-label': 'How long do you have?' }, BUDGETS.map(([m, t]) =>
    h('button', { type: 'button', class: S.budget === m ? 'on' : '', 'aria-pressed': S.budget === m ? 'true' : 'false', onclick: () => { S.budget = m; keep(); render() } }, m + ' min', h('small', null, t)))))
  view.append(h('div', { class: 'seg', role: 'group', 'aria-label': 'Mode' },
    h('button', { type: 'button', class: S.mode === 'det' ? 'on' : '', onclick: () => { S.mode = 'det'; keep(); render() } }, 'From the data', h('small', null, 'deterministic')),
    h('button', { type: 'button', class: S.mode === 'agent' ? 'on' : '', onclick: () => { S.mode = 'agent'; keep(); render() } }, 'Written for me', h('small', null, 'agentic, your key'))))

  // the first time: the situation, then a way to start counting from here
  if (d.fresh) {
    const c = h('section', { class: 'card state' }, h('p', { class: 'lbl' }, 'First time here'), h('p', { class: 'big' }, DATA.headline), h('p', null, DATA.deck))
    c.append(h('p', { class: 'lbl' }, `Right now · as of ${DATA.when}`), h('ul', { class: 'nowlist' }, DATA.now.map(x => h('li', null, x.text))))
    if (S.budget >= 5) c.append(h('p', { class: 'lbl' }, 'The core facts'), h('ul', { class: 'nowlist' }, DATA.facts.slice(0, S.budget >= 10 ? 9 : 4).map(f => h('li', null, h('span', { class: 'chip st-' + f.status }, f.status), ' ', f.text))))
    if (S.budget >= 10) c.append(h('p', { class: 'lbl' }, 'What nobody knows yet'), h('ul', { class: 'nowlist' }, DATA.unknown.map(u => h('li', null, u))))
    c.append(h('p', { class: 'small' }, 'From here on, this app counts what changes. Tell it you are up to date and next time it shows only what is new.'),
      h('button', { class: 'btn pri wide', type: 'button', onclick: () => { const r = R(); if (!r) return; DATA.items.forEach(it => r.markRead(it.id, it.hash)); r.persist(); scheduleSync(); toast('Up to date. Next time: only what changed.'); render() } }, 'I am up to date: count from now'))
    if (!p) c.append(personaPicker())
    view.append(c)
    if (S.mode === 'agent') view.append(agentCard([], true))
    return
  }

  const { shown, level, rest } = cut(d.list, S.budget)
  const counts = { new: d.list.filter(x => x.state === 'new').length, changed: d.list.filter(x => x.state === 'changed').length }
  const top = h('section', { class: 'card state' + (d.list.length ? '' : ' quiet') })
  if (!d.list.length) {
    top.append(h('p', { class: 'lbl' }, d.last ? `Since you last looked, ${ago(d.last)}` : 'Since you last looked'),
      h('p', { class: 'big' }, 'Good: nothing new.'),
      h('p', null, `Nothing on the site has changed since you read it. The site was last updated from its evidence at ${DATA.when} (release v${DATA.site}).`),
      h('ul', { class: 'nowlist' }, DATA.now.slice(0, S.budget >= 5 ? 4 : 2).map(x => h('li', null, x.text))))
  } else {
    const lead = shown[0]
    top.append(h('p', { class: 'lbl' }, d.last ? `Since you last looked, ${ago(d.last)}` : 'Since you last looked'),
      h('p', { class: 'big' }, `${d.list.length} thing${d.list.length === 1 ? '' : 's'} to know.`),
      lead ? h('p', null, h('b', null, 'Most important: '), lead.title) : null,
      h('div', { class: 'counts' }, h('span', null, h('b', null, counts.new), ' new'), h('span', null, h('b', null, counts.changed), ' changed'),
        h('span', null, `showing ${shown.length} for ${S.budget} min`)))
  }
  view.append(top)
  if (S.mode === 'agent') view.append(agentCard(shown, false))
  for (const it of shown) view.append(itemCard(it, level))
  if (shown.length) view.append(h('button', { class: 'btn wide', type: 'button', onclick: () => { const r = R(); shown.forEach(it => r.markRead(it.id, it.hash)); r.persist(); scheduleSync(); toast(`${shown.length} marked read`); render() } }, `Mark these ${shown.length} as read`))
  if (rest > 0) view.append(h('p', { class: 'more small' }, `${rest} more beyond your ${S.budget} minutes. `,
    S.budget < 30 ? h('a', { href: '#now', onclick: e => { e.preventDefault(); S.budget = BUDGETS[Math.min(3, BUDGETS.findIndex(b => b[0] === S.budget) + 1)][0]; keep(); render() } }, 'More time') : h('a', { href: ROOT + 'you/index.html' }, 'Your desk has them all')))
  view.append(h('p', { class: 'small' }, `Release v${DATA.site} · data as of ${DATA.when} · ${p ? `reading as ${p.person}, ${p.label.toLowerCase()} · ` : ''}`, h('a', { href: ROOT + 'whatsnew/index.html' }, 'what changed, release by release')))
}

function personaPicker() {
  const sel = h('select', { 'aria-label': 'Who are you?', onchange: e => { try { localStorage.setItem(PERSONA, e.target.value) } catch (x) {} scheduleSync(); render() } },
    h('option', { value: '' }, 'Who are you? (optional)'), DATA.personas.map(p => h('option', { value: p.id, selected: persona() && persona().id === p.id }, `${p.label} (${p.person})`)))
  return h('div', null, h('p', { class: 'lbl' }, 'Read as'), sel)
}

// ------------------------------------------------------------------ agentic
function ready() { return V.vault && V.orKey }
function agentCard(shown, fresh) {
  const c = h('section', { class: 'card gen' })
  if (!ready()) {
    c.append(h('h2', null, 'Written for you, by a model'),
      h('p', null, 'In this mode a model reads exactly what the deterministic view shows and writes it up for the time you have, draws it as an infographic, or answers your questions. It uses your own OpenRouter key, kept encrypted in your own vault.'),
      h('p', { class: 'small' }, V.vault ? 'Your vault is open. Add your OpenRouter key to it to start.' : 'First open or create your vault, then add your OpenRouter key.'),
      h('a', { class: 'btn pri wide', href: '#vault' }, V.vault ? 'Add your OpenRouter key' : 'Open your vault'))
    return c
  }
  const m = models(), out = h('div', { class: 'out' })
  const items = fresh ? DATA.items.filter(x => x.kind === 'front' || (x.kind === 'fact' && /confirmed|contradicted/.test(x.status))).slice(0, 24) : shown
  c.append(h('h2', null, `Your ${S.budget}-minute briefing, written for you`),
    h('p', { class: 'small' }, `${m.text.split('/').pop()} writes from the ${items.length} item${items.length === 1 ? '' : 's'} below and nothing else, citing each. ${m.image.split('/').pop()} draws.`),
    h('div', { class: 'row' },
      h('button', { class: 'btn pri', type: 'button', onclick: e => briefing(items, out, e.target) }, 'Write it'),
      h('button', { class: 'btn', type: 'button', onclick: e => infographic(items, out, e.target) }, 'Draw it')), out)
  for (const x of V.made.slice(0, 2)) out.append(madeCard(x))
  return c
}

function itemsForModel(items) {
  return items.map(it => ({ id: it.id, kind: it.kind, state: it.state || 'current', status: it.status || undefined, title: it.title, says: it.text, changed_in: 'v' + it.changed }))
}

function rules(p) {
  return [
    'You write for the reader of PHP October 2026 (php.oct.2026.newsroom.sgit.ai), a site that tracks two critical PHP security flaws (CVE-2026-109618 and CVE-2026-109619, nicknamed php2shell) as evidence.',
    'Use only the items and facts you are given. Do not add facts, numbers, names or dates from elsewhere. If the items do not answer something, say so.',
    'After every sentence that states a fact, cite the item ids it rests on in square brackets, for example [fact-two-cves-9.2]. Use only ids you were given.',
    'Keep each fact at the status it was given (confirmed, reported, disputed, contradicted, unverified); never make a reported fact sound confirmed. Attempts are not compromises.',
    'Plain words. ' + (p ? `The reader is ${p.person}, ${p.label.toLowerCase()}; ${p.depth === 1 ? 'no technical background: explain any term you must use.' : p.depth === 2 ? 'comfortable with servers and patches, not with internals.' : 'technical: versions, settings and code paths are welcome.'}` : 'Assume no technical background unless asked.'),
    'Never use em dashes.'].join('\n')
}

async function openrouter(body, onDelta) {
  const res = await fetch(OR, { method: 'POST', headers: { Authorization: 'Bearer ' + V.orKey, 'Content-Type': 'application/json', 'HTTP-Referer': location.origin, 'X-Title': 'PHP October 2026: Now' },
    body: JSON.stringify(Object.assign({ usage: { include: true } }, body, onDelta ? { stream: true } : {})) })
  if (!res.ok) { let t = ''; try { t = (await res.json()).error.message } catch (e) { t = res.statusText } throw new Error(`OpenRouter ${res.status}: ${t}`) }
  if (!onDelta) return res.json()
  const rd = res.body.getReader(), dec = new TextDecoder(); let buf = '', text = '', usage = null, model = body.model
  for (;;) {
    const { value, done } = await rd.read(); if (done) break
    buf += dec.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1)
      if (!line.startsWith('data:')) continue
      const data = line.slice(5).trim(); if (data === '[DONE]') continue
      try { const j = JSON.parse(data); const dl = j.choices && j.choices[0] && j.choices[0].delta && j.choices[0].delta.content; if (dl) { text += dl; onDelta(text) } if (j.usage) usage = j.usage; if (j.model) model = j.model } catch (e) {}
    }
  }
  return { text, usage, model }
}

function md(text) {
  // Escape everything, then allow paragraphs, bullets, bold, italics and citations of known item ids.
  const ids = new Map(DATA.items.map(it => [it.id, it.path]))
  const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/(^|\W)\*(\S.*?)\*(?=\W|$)/g, '$1<i>$2</i>')
    .replace(/\[([a-z0-9][a-z0-9._:-]*(?:\s*,\s*[a-z0-9][a-z0-9._:-]*)*)\]/gi, (m, list) => list.split(/\s*,\s*/).map(id => ids.has(id) ? `<a class="cite" href="${ROOT}${esc(ids.get(id))}">${esc(id)}</a>` : `<span class="cite">${esc(id)}?</span>`).join(' '))
  const out = []; let ul = false
  for (const raw of String(text).split('\n')) {
    const line = raw.trim()
    if (/^[-*•]\s+/.test(line)) { if (!ul) { out.push('<ul>'); ul = true } out.push('<li>' + inline(line.replace(/^[-*•]\s+/, '')) + '</li>'); continue }
    if (ul) { out.push('</ul>'); ul = false }
    if (!line) continue
    const hm = line.match(/^#{1,4}\s+(.*)$/)
    out.push(hm ? '<p><b>' + inline(hm[1]) + '</b></p>' : '<p>' + inline(line) + '</p>')
  }
  if (ul) out.push('</ul>')
  return out.join('')
}

function costLine(u, model) {
  if (!u) return model
  return `${model} · ${u.prompt_tokens || 0} in, ${u.completion_tokens || 0} out` + (u.cost != null ? ` · ~$${Number(u.cost).toFixed(4)}` : '')
}

function madeCard(x) {
  const c = h('div', { class: 'gen-out' })
  c.append(h('p', { class: 'who' }, `${x.kind === 'image' ? 'Drawn' : 'Written'} by ${x.model}, ${ago(x.at)}, from ${x.items.length} items · not checked by a person`))
  if (x.kind === 'image' && x.src) c.append(h('img', { src: x.src, alt: 'An infographic generated by ' + x.model + ' from the items listed' }))
  if (x.text) c.append(h('div', { class: 'body', html: md(x.text) }))
  return c
}

async function briefing(items, out, btn) {
  const p = persona(), m = models(), words = Math.round(S.budget * 170)
  btn.disabled = true; const live = h('div', { class: 'body' }, h('span', { class: 'spin' }), ' writing…'); out.prepend(live)
  try {
    const r = await openrouter({ model: m.text, max_tokens: Math.min(4000, words * 3), messages: [
      { role: 'system', content: rules(p) },
      { role: 'user', content: `Write my ${S.budget}-minute briefing: about ${words} words, the most important first. ${items.length ? `These ${items.length} items are what is new or changed since I last looked:` : 'Nothing is new since I last looked; say so in one line, then remind me of where things stand from the facts below.'}\n\n${JSON.stringify(itemsForModel(items))}\n\nWhere things stand (as of ${DATA.when}):\n${DATA.now.map(x => '- ' + x.text).join('\n')}` }] },
      t => { live.innerHTML = md(t) })
    const rec = { kind: 'briefing', at: new Date().toISOString(), model: r.model || m.text, budget: S.budget, persona: p ? p.id : null, items: items.map(i => i.id), usage: r.usage, text: r.text }
    live.replaceWith(madeCard(rec)); out.firstChild.append(h('p', { class: 'small' }, costLine(r.usage, rec.model)))
    await keepMade(rec)
  } catch (e) { live.innerHTML = `<p class="err">${esc(e.message)}</p>` }
  btn.disabled = false
}

async function infographic(items, out, btn) {
  const m = models()
  btn.disabled = true; const live = h('div', { class: 'body' }, h('span', { class: 'spin' }), ' drawing… (this can take a minute)'); out.prepend(live)
  const facts = (items.length ? items : DATA.items.filter(x => x.kind === 'fact').slice(0, 10)).slice(0, 12)
  const prompt = [`A clean, factual infographic, portrait (4:5), titled "The PHP flaws: where things stand" with the subtitle "${DATA.when}".`,
    'Use only these statements, in this order of importance, with their status shown as a small label (confirmed, reported, disputed, unverified). Do not add any number, name or date that is not here:',
    ...facts.map(f => `- [${f.status || f.kind}] ${f.title}${f.text && f.text !== f.title ? ': ' + f.text.slice(0, 220) : ''}`),
    'Situation: ' + DATA.now.map(x => x.text).join(' '),
    'Style: newspaper data graphic, calm, high contrast, large readable type, no logos, no people, no code screenshots. Footer in small type: "php.oct.2026.newsroom.sgit.ai · generated by ' + m.image + ' from the site\'s facts"'].join('\n')
  try {
    const j = await openrouter({ model: m.image, modalities: ['image', 'text'], messages: [{ role: 'user', content: prompt }] })
    const msg = j.choices && j.choices[0] && j.choices[0].message, img = msg && msg.images && msg.images[0] && msg.images[0].image_url && msg.images[0].image_url.url
    if (!img) throw new Error('The model returned no image' + (msg && msg.content ? ': ' + String(msg.content).slice(0, 200) : ''))
    const rec = { kind: 'image', at: new Date().toISOString(), model: j.model || m.image, items: facts.map(i => i.id), usage: j.usage, prompt, src: img, text: msg.content || '' }
    live.replaceWith(madeCard(rec)); out.firstChild.append(h('p', { class: 'small' }, costLine(j.usage, rec.model)))
    await keepMade(rec)
  } catch (e) { live.innerHTML = `<p class="err">${esc(e.message)}</p>` }
  btn.disabled = false
}

async function keepMade(rec) {
  V.made.unshift(rec)
  if (!V.vault || !V.writable) return
  try {
    const name = stamp() + '-' + rec.kind
    const meta = Object.assign({}, rec); delete meta.src
    if (rec.src) {
      const b64 = rec.src.split(',')[1], bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
      await V.nv.writeFile(V.vault, '/php-october/made', name + '.png', bytes); meta.image = name + '.png'
    }
    await V.nv.writeFile(V.vault, '/php-october/made', name + '.json', JSON.stringify(meta, null, 1))
    await V.nv.publish(V.vault); toast('Kept in your vault')
  } catch (e) { toast('Not saved to the vault: ' + e.message) }
}

// ------------------------------------------------------------------ chat
let CHAT = { id: null, messages: [] }
function grounding() {
  const d = delta(), p = persona()
  return [rules(p), '',
    `Where things stand, as of ${DATA.when} (site release v${DATA.site}):`, ...DATA.now.map(x => '- ' + x.text), '',
    'Every fact on the site, with its id (cite as fact-<id>) and status:', ...DATA.claims.map(c => `- fact-${c.id} [${c.status}] ${c.claim} (who says it: ${c.by})`), '',
    'What nobody knows yet:', ...DATA.unknown.map(u => '- ' + u), '',
    `New or changed for this reader since they last looked (${d.list.length} items; the first 30):`, JSON.stringify(itemsForModel(d.list.slice(0, 30)))].join('\n')
}
function renderChat(view) {
  if (!ready()) { view.append(agentCard([], true)); return }
  const box = h('div', { class: 'chat', 'aria-live': 'polite' })
  const say = (role, text, who) => { const e = h('div', { class: 'msg ' + (role === 'user' ? 'u' : 'a') }); if (role === 'user') e.textContent = text; else { e.innerHTML = md(text); if (who) e.append(h('p', { class: 'who' }, who)) } box.append(e); return e }
  view.append(h('section', { class: 'card' }, h('h2', null, 'Ask about the PHP flaws'),
    h('p', { class: 'small' }, `${models().text} answers from the site's ${DATA.claims.length} facts and what is new for you, citing each. It says when the facts do not cover a question.`),
    V.chats.length ? h('details', null, h('summary', null, `Earlier conversations (${V.chats.length})`), h('ul', null, V.chats.slice(0, 12).map(c => h('li', null, h('a', { href: '#chat', onclick: e => { e.preventDefault(); openChat(c) } }, (c.title || c.id) + ' · ' + ago(c.at)))))) : null,
    h('button', { class: 'btn', type: 'button', onclick: () => { CHAT = { id: null, messages: [] }; render() } }, 'New conversation')))
  for (const m of CHAT.messages) say(m.role, m.content, m.who)
  if (!CHAT.messages.length) view.append(h('div', { class: 'suggest' }, ['Has anyone actually been hacked?', 'What changed since I last looked?', 'Do I need to do anything about my WordPress site?', 'Which numbers in the news are wrong?', 'What should I tell my board?']
    .map(q => h('button', { type: 'button', onclick: () => send(q) }, q))))
  view.append(box)
  const ta = h('textarea', { rows: 1, placeholder: 'Ask a question…', 'aria-label': 'Your question', onkeydown: e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(ta.value) } } })
  view.append(h('div', { class: 'composer' }, ta, h('button', { class: 'btn pri', type: 'button', onclick: () => send(ta.value) }, 'Ask')))
  async function send(q) {
    q = String(q || '').trim(); if (!q) return
    ta.value = ''; CHAT.messages.push({ role: 'user', content: q }); say('user', q)
    const a = say('assistant', '…')
    try {
      const msgs = [{ role: 'system', content: grounding() }].concat(CHAT.messages.map(m => ({ role: m.role, content: m.content })))
      const r = await openrouter({ model: models().text, max_tokens: 1500, messages: msgs }, t => { a.innerHTML = md(t) })
      const who = costLine(r.usage, r.model || models().text)
      a.append(h('p', { class: 'who' }, who))
      CHAT.messages.push({ role: 'assistant', content: r.text, who })
      await keepChat()
    } catch (e) { a.innerHTML = `<p class="err">${esc(e.message)}</p>`; CHAT.messages.pop() }
  }
}
async function openChat(c) { try { const j = await V.nv.readJson(V.vault, `/php-october/chats/${c.file}`); if (j) { CHAT = { id: j.id, messages: j.messages } ; render() } } catch (e) { toast(e.message) } }
async function keepChat() {
  if (!CHAT.id) CHAT.id = stamp()
  if (!V.vault || !V.writable) return
  const rec = { id: CHAT.id, at: new Date().toISOString(), title: CHAT.messages[0].content.slice(0, 80), model: models().text, site: DATA.site, messages: CHAT.messages }
  try { await V.nv.writeFile(V.vault, '/php-october/chats', CHAT.id + '.json', JSON.stringify(rec, null, 1)); await V.nv.publish(V.vault)
    if (!V.chats.some(c => c.id === CHAT.id)) V.chats.unshift({ id: CHAT.id, file: CHAT.id + '.json', title: rec.title, at: rec.at }) } catch (e) { toast('Chat not saved: ' + e.message) }
}

// ------------------------------------------------------------------ the vault
let libP = null
function loadLib() {
  if (libP) return libP
  libP = (async () => {
    for (const src of LIB) await new Promise((ok, no) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => no(new Error('could not load ' + src)); document.head.append(s) })
    return import(new URL('../vault/newsroom-vault.js', import.meta.url).href)
  })()
  return libP
}
function vchip() {
  const b = $('#vchip'); if (!b) return
  b.className = 'vchip' + (V.status === 'open' ? ' on' : V.status === 'busy' ? ' busy' : '')
  b.textContent = V.status === 'open' ? `Vault ${V.key.split(':').pop()} ✓` : V.status === 'busy' ? 'Vault…' : 'This phone only'
}
async function openVault(key, remember) {
  V.status = 'busy'; V.err = ''; vchip()
  try {
    const NV = await loadLib()
    const send = NV.client({ endpoint: DATA.vault.endpoint })
    const v = await NV.openVault(send, key.trim())
    const token = await v.readEmbeddedAccessToken(); send.token = token || ''
    Object.assign(V, { nv: NV, vault: v, send, key: NV.prefixedKey(v), writable: !!token, status: 'open' })
    try { sessionStorage.setItem(KEY_S, V.key); if (remember) localStorage.setItem(KEY_S, V.key); else localStorage.removeItem(KEY_S) } catch (e) {}
    await pull()
    if (V.writable) await push(true)                      // this device's record and settings, in the vault from the first open
    else toast('Opened read-only: this vault has no write token inside it')
  } catch (e) { V.status = 'off'; V.err = e.code === 'ENOVAULT' ? 'No vault at that key.' : e.message; V.vault = null }
  vchip(); render()
}
async function createVault(token, remember) {
  V.status = 'busy'; V.err = ''; vchip(); render()
  try {
    const NV = await loadLib()
    const send = NV.client({ endpoint: DATA.vault.endpoint, token: token.trim() })
    const v = await NV.createVault(send, { name: 'php-october-reader', description: 'My PHP October 2026 reader vault' })
    await NV.writeFile(v, '/.vault', 'access-token.json', JSON.stringify({ token: token.trim() }))
    await NV.writeFile(v, '/php-october', 'README.md', '# PHP October 2026, mine\n\nKept by the phone app at https://php.oct.2026.newsroom.sgit.ai/now/index.html: what I have read (devices/), my settings, my OpenRouter key (secrets/), my chats and what the models made for me (made/). Encrypted in my browser before it left.\n')
    Object.assign(V, { nv: NV, vault: v, send, key: NV.prefixedKey(v), writable: true, status: 'open', fresh: true })
    await push(true)
    try { sessionStorage.setItem(KEY_S, V.key); if (remember) localStorage.setItem(KEY_S, V.key) } catch (e) {}
  } catch (e) { V.status = 'off'; V.err = e.message; V.vault = null }
  vchip(); render()
}
function forget() {
  try { sessionStorage.removeItem(KEY_S); localStorage.removeItem(KEY_S) } catch (e) {}
  Object.assign(V, { vault: null, key: null, send: null, writable: false, status: 'off', orKey: null, files: [], made: [], chats: [], fresh: false })
  vchip(); render()
}
function deviceId() { return V.nv ? V.nv.deviceBranch() : 'this-browser' }
async function pull() {
  const NV = V.nv, v = V.vault, r = R()
  const devs = await NV.listFiles(v, '/php-october/devices').catch(() => [])
  for (const f of devs) {
    if (!f.endsWith('.json')) continue
    const j = await NV.readJson(v, '/php-october/devices/' + f).catch(() => null)
    if (j && j.reader && r) {
      const mine = r.store()
      for (const [id, rec] of Object.entries(j.reader.items || {})) { const cur = mine.items[id]; if (!cur || (rec.at || '') > (cur.at || '')) mine.items[id] = rec }
      const notes = r.notes(), have = new Set(notes.map(n => n.id))
      for (const n of (j.notes || [])) if (!have.has(n.id)) notes.push(n)
      r.persist()
    }
  }
  const st = await NV.readJson(v, '/php-october/settings.json').catch(() => null)
  if (st) { if (st.models) S.models = st.models; if (st.persona) try { localStorage.setItem(PERSONA, st.persona) } catch (e) {} keep() }
  const sec = await NV.readJson(v, '/php-october/secrets/openrouter.json').catch(() => null)
  V.orKey = sec && sec.key || null
  const chats = await NV.listFiles(v, '/php-october/chats').catch(() => [])
  V.chats = chats.filter(f => f.endsWith('.json')).sort().reverse().map(f => ({ id: f.replace(/\.json$/, ''), file: f, title: f.replace(/\.json$/, ''), at: '' }))
  const made = await NV.listFiles(v, '/php-october/made').catch(() => [])
  V.made = []
  for (const f of made.filter(f => f.endsWith('.json')).sort().reverse().slice(0, 4)) {
    const j = await NV.readJson(v, '/php-october/made/' + f).catch(() => null)
    if (!j) continue
    if (j.image) { try { const bytes = await V.vault.getFile('/php-october/made', j.image); j.src = URL.createObjectURL(new Blob([bytes], { type: 'image/png' })) } catch (e) {} }
    V.made.push(j)
  }
  V.files = await NV.listFiles(v, '/php-october').catch(() => [])
  V.last = new Date().toISOString()
}
async function push(quiet) {
  if (!V.vault || !V.writable) return
  const r = R(), NV = V.nv
  const doc = { v: 1, device: deviceId(), at: new Date().toISOString(), site: DATA.site, reader: r ? r.store() : null, notes: r ? r.notes() : [] }
  await NV.writeFile(V.vault, '/php-october/devices', deviceId() + '.json', JSON.stringify(doc))
  const p = persona()
  await NV.writeFile(V.vault, '/php-october', 'settings.json', JSON.stringify({ v: 1, persona: p ? p.id : null, budget: S.budget, mode: S.mode, models: S.models || null }, null, 1))
  await NV.publish(V.vault)
  V.last = new Date().toISOString()
  V.files = await NV.listFiles(V.vault, '/php-october').catch(() => V.files)
  if (!quiet) toast('Saved to your vault')
}
let syncT = null
function scheduleSync() { if (!V.vault || !V.writable) return; clearTimeout(syncT); syncT = setTimeout(() => push(true).catch(e => toast('Vault: ' + e.message)), 4000) }
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden' && syncT) { clearTimeout(syncT); syncT = null; push(true).catch(() => {}) } })
window.addEventListener('pagehide', () => { if (syncT) { clearTimeout(syncT); syncT = null; push(true).catch(() => {}) } })

function renderVault(view) {
  if (V.status === 'busy') { view.append(h('section', { class: 'card' }, h('p', null, h('span', { class: 'spin' }), ' Opening your vault…'))); return }
  if (!V.vault) {
    const key = h('input', { type: 'password', placeholder: 'sgit_private_vault_…:vault-id', autocomplete: 'off', 'aria-label': 'Vault key' })
    const rem = h('input', { type: 'checkbox' })
    view.append(h('section', { class: 'card' }, h('h2', null, 'Open your vault'),
      h('p', null, 'Your vault keeps what you have read across your devices, your settings, your OpenRouter key and your chats, encrypted on this phone before anything leaves it. Any sgit vault key works, including a newsroom.sgit.ai reader vault.'),
      key, h('label', { class: 'ck' }, rem, h('span', null, 'Remember on this phone. Anyone who can unlock this phone could then open your vault.')),
      h('button', { class: 'btn pri wide', type: 'button', onclick: () => key.value.trim() && openVault(key.value, rem.checked) }, 'Open'),
      V.err ? h('p', { class: 'err' }, V.err) : null))
    const tok = h('input', { type: 'text', placeholder: 'access token', autocomplete: 'off', 'aria-label': 'Access token for the vault server' })
    const rem2 = h('input', { type: 'checkbox' })
    view.append(h('section', { class: 'card' }, h('h2', null, 'No vault yet? Create one'),
      h('p', null, 'Creating a vault needs an access token for the vault server (ask the editor). The new vault key is shown once: save it somewhere safe. It is the only way back in.'),
      tok, h('label', { class: 'ck' }, rem2, h('span', null, 'Remember on this phone')),
      h('button', { class: 'btn wide', type: 'button', onclick: () => tok.value.trim() && createVault(tok.value, rem2.checked) }, 'Create my vault')))
  } else {
    const c = h('section', { class: 'card' }, h('h2', null, `Your vault ${V.key.split(':').pop()}`),
      h('p', { class: 'small' }, `${V.writable ? 'Open, read and write' : 'Open, read-only'} · last synced ${V.last ? ago(V.last) : 'never'} · this device is ${deviceId()}`))
    if (V.fresh) c.append(h('p', null, h('b', null, 'Save your vault key now.'), ' It is the only way to open this vault on another device, and nobody can recover it.'),
      h('p', { class: 'key' }, V.key), h('button', { class: 'btn', type: 'button', onclick: async () => { try { await navigator.clipboard.writeText(V.key); toast('Copied') } catch (e) { toast('Copy it by hand') } } }, 'Copy the key'))
    c.append(h('div', { class: 'row' }, h('button', { class: 'btn', type: 'button', onclick: async () => { V.status = 'busy'; render(); try { await pull(); await push() } catch (e) { toast(e.message) } V.status = 'open'; render() } }, 'Sync now'),
      h('button', { class: 'btn', type: 'button', onclick: forget }, 'Close on this phone')))
    c.append(h('details', null, h('summary', null, 'What is in it'), h('ul', { class: 'files' }, V.files.map(f => h('li', null, '/php-october/' + f)))))
    view.append(c)
    const k = h('input', { type: 'password', placeholder: V.orKey ? 'replace the saved key' : 'sk-or-…', autocomplete: 'off', 'aria-label': 'OpenRouter key' })
    view.append(h('section', { class: 'card' }, h('h2', null, 'Your OpenRouter key'),
      h('p', null, V.orKey ? h('span', { class: 'ok' }, `Saved in your vault, ending …${V.orKey.slice(-4)}.`) : 'Needed for the agentic mode and the chat. ', ' Kept encrypted in your vault and in this tab\'s memory; sent only to OpenRouter. ', h('a', { href: 'https://openrouter.ai/keys', rel: 'noopener', target: '_blank' }, 'Get a key')),
      k, h('div', { class: 'row' },
        h('button', { class: 'btn pri', type: 'button', disabled: !V.writable, onclick: async () => { if (!k.value.trim()) return; try { await V.nv.writeFile(V.vault, '/php-october/secrets', 'openrouter.json', JSON.stringify({ key: k.value.trim(), saved: new Date().toISOString() })); await V.nv.publish(V.vault); V.orKey = k.value.trim(); toast('Key saved in your vault'); render() } catch (e) { toast(e.message) } } }, 'Save to my vault'),
        V.orKey ? h('button', { class: 'btn', type: 'button', onclick: async () => { try { await V.nv.writeFile(V.vault, '/php-october/secrets', 'openrouter.json', JSON.stringify({ key: null, removed: new Date().toISOString() })); await V.nv.publish(V.vault); V.orKey = null; render() } catch (e) { toast(e.message) } } }, 'Remove') : null)))
  }
  const m = models(), ti = h('input', { type: 'text', value: m.text, 'aria-label': 'Text model' }), ii = h('input', { type: 'text', value: m.image, 'aria-label': 'Image model' })
  view.append(h('section', { class: 'card' }, h('h2', null, 'Models and reader'),
    h('p', { class: 'lbl' }, 'Writes and chats'), ti, h('p', { class: 'lbl' }, 'Draws infographics'), ii,
    h('button', { class: 'btn', type: 'button', onclick: () => { S.models = { text: ti.value.trim() || DATA.models.text, image: ii.value.trim() || DATA.models.image }; keep(); scheduleSync(); toast('Saved') } }, 'Use these'),
    personaPicker(),
    h('p', { class: 'small' }, 'Any OpenRouter model id works. The defaults are ', h('code', null, DATA.models.text), ' and ', h('code', null, DATA.models.image), '.')))
  view.append(h('p', { class: 'small' }, 'What this app keeps where: what you have read is in this browser (shared with ', h('a', { href: ROOT + 'you/index.html' }, 'your desk'), ') and, with a vault open, in ', h('code', null, '/php-october/devices/'), '. Your OpenRouter key is never written to this browser\'s storage. ', h('a', { href: ROOT + 'now/index.md' }, 'How the app works.')))
}

// ------------------------------------------------------------------ shell
function render() {
  const view = $('#view'); if (!view || !DATA) return
  view.textContent = ''
  const tab = (location.hash || '#now').slice(1)
  S.tab = ['now', 'chat', 'vault'].includes(tab) ? tab : 'now'
  document.querySelectorAll('#tabs a').forEach(a => a.classList.toggle('here', a.dataset.tab === S.tab))
  if (S.tab === 'now') renderNow(view)
  else if (S.tab === 'chat') renderChat(view)
  else renderVault(view)
  vchip()
}
window.addEventListener('hashchange', () => { render(); window.scrollTo(0, 0) })
window.addEventListener('p2s-reader', () => {})

async function start() {
  try { DATA = await (await fetch('now.json', { cache: 'no-cache' })).json() } catch (e) { $('#view').append(h('p', { class: 'err' }, 'Could not load the data: ' + e.message)); return }
  $('#vchip').addEventListener('click', () => { location.hash = '#vault' })
  render()
  let key = null; try { key = sessionStorage.getItem(KEY_S) || localStorage.getItem(KEY_S) } catch (e) {}
  if (key) openVault(key, !!(function () { try { return localStorage.getItem(KEY_S) } catch (e) { return null } })())
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start()
