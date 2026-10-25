// The feedback viewer (sherpa@php.newsroom): select text in a document to highlight it and add a note. Notes are the
// reader's own: kept in this browser's localStorage only, shown with textContent, never sent anywhere, exportable as JSON.
const KEY = 'p2s.fv.notes.v1'
const doc = document.querySelector('.fv-doc')
const list = document.getElementById('fv-notes')

function load () { try { return JSON.parse(localStorage.getItem(KEY) || '[]') } catch (e) { return [] } }
function save (all) { try { localStorage.setItem(KEY, JSON.stringify(all)); return true } catch (e) { return false } }
function el (tag, attrs, ...kids) {
  const n = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs || {})) { if (k === 'onclick') n.addEventListener('click', v); else n.setAttribute(k, v) }
  for (const k of kids) if (k != null) n.append(k)
  return n
}

function mark (blockEl, quote) {
  const w = document.createTreeWalker(blockEl, NodeFilter.SHOW_TEXT)
  for (let t = w.nextNode(); t; t = w.nextNode()) {
    const i = t.data.indexOf(quote)
    if (i < 0 || t.parentElement.closest('.fv-mark')) continue
    const r = document.createRange(); r.setStart(t, i); r.setEnd(t, i + quote.length)
    const m = el('mark', { class: 'fv-mark' }); r.surroundContents(m); return true
  }
  return false
}

function render () {
  if (!doc) return
  const id = doc.dataset.doc, mine = load().filter(n => n.doc === id)
  doc.querySelectorAll('.fv-mine').forEach(n => n.remove())
  doc.querySelectorAll('mark.fv-mark').forEach(m => m.replaceWith(...m.childNodes))
  for (const n of mine) {
    const b = doc.querySelector(`.fv-b[data-b="${CSS.escape(n.block)}"]`)
    if (!b) continue
    mark(b, n.quote)
    b.parentElement.querySelector('.fv-c').append(el('div', { class: 'fv-mine' }, el('b', null, 'Your note'), el('p', null, n.note || '(a highlight)'),
      el('button', { type: 'button', class: 'rs-b', onclick: () => { save(load().filter(x => x.at !== n.at)); render() } }, 'Remove')))
  }
  if (!list) return
  list.textContent = ''
  if (!mine.length) { list.append(el('p', { class: 'small' }, 'None yet. Select text in the document to add one. Notes are kept in this browser only.')); return }
  const ul = el('ul')
  for (const n of mine) ul.append(el('li', null, el('q', null, n.quote), ' ', n.note ? '(' + n.note + ')' : ''))
  const exp = el('button', { type: 'button', class: 'rs-b', onclick: () => {
    const blob = new Blob([JSON.stringify({ doc: id, page: location.pathname, notes: mine }, null, 2)], { type: 'application/json' })
    const a = el('a', { href: URL.createObjectURL(blob), download: id.toLowerCase() + '-my-notes.json' }); document.body.append(a); a.click(); a.remove()
  } }, 'Export my notes (JSON)')
  list.append(ul, exp)
}

let tool = null
function closeTool () { if (tool) { tool.remove(); tool = null } }

document.addEventListener('mouseup', ev => {
  if (!doc || (tool && tool.contains(ev.target))) return
  closeTool()
  const s = window.getSelection(), q = s ? s.toString().trim() : ''
  if (!q || q.length > 600) return
  const a = s.anchorNode && s.anchorNode.parentElement && s.anchorNode.parentElement.closest('.fv-b')
  const f = s.focusNode && s.focusNode.parentElement && s.focusNode.parentElement.closest('.fv-b')
  if (!a || a !== f || !doc.contains(a)) return
  const rect = s.getRangeAt(0).getBoundingClientRect()
  const note = el('textarea', { 'aria-label': 'Your note on the highlighted text', placeholder: 'Your note (optional)' })
  const ok = el('button', { type: 'button', class: 'rs-b', onclick: () => {
    const all = load(); all.push({ doc: doc.dataset.doc, block: a.dataset.b, quote: q, note: note.value.trim().slice(0, 2000), at: new Date().toISOString() })
    if (!save(all)) alert('This browser will not keep notes (private window or storage blocked).')
    closeTool(); window.getSelection().removeAllRanges(); render()
  } }, 'Save highlight')
  tool = el('div', { class: 'fv-tool fv-card', style: `top:${rect.bottom + window.scrollY + 6}px;left:${Math.max(8, rect.left + window.scrollX)}px;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:.5rem;width:min(22rem,90vw)` },
    el('div', { class: 'fv-form' }, el('b', null, 'Highlight and note'), note, el('div', null, ok, ' ', el('button', { type: 'button', class: 'rs-b', onclick: closeTool }, 'Cancel'))))
  document.body.append(tool)
})
document.addEventListener('keydown', ev => { if (ev.key === 'Escape') closeTool() })
render()
