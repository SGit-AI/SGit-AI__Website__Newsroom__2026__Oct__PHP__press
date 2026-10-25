/**
 * sg-graph — any graph on this site, from a five-node sketch to the whole story, walked one link
 * at a time. The model is sg-graph-core.js; this file only draws it and listens.
 *
 *   <sg-graph src="../data/graph.json" base="../" focus="claim:ai-found"></sg-graph>
 *   <sg-graph view="layers" base="../"><script type="application/json">{"nodes":[…],"edges":[…]}</script></sg-graph>
 *
 * Attributes (all optional):
 *   src      a graph JSON file, relative to the page; without it the first <script type="application/json"> child is read
 *   base     the path from the page to the site root, prefixed to every node's href ("../" one level down)
 *   focus    the node in the middle; default the node with most edges
 *   view     ego (the focus and its neighbours, the default) | layers (columns by altitude or kind)
 *            | map (a seeded force layout, with pan and zoom) | list (text only)
 *   depth    hops from the focus, 1 to 3 (default 1)
 *   max      the most nodes drawn at once (default 60); the list under the drawing always has them all
 *   height   the drawing's height in px (default: from its width)
 *   verbs    a comma list: show only these verbs at first
 *   controls "none" hides the toolbar, for a small fixed figure
 *
 * Every node is a control: click, Enter or Space puts it in focus. A node with an href has a link to its page;
 * a node with a `zoom` list ([{ graph, focus, label }], or the older `graph` and `graph_focus`) opens those graphs
 * (the fractal step: a new ontology joined by a named edge, or a bridge to a sibling graph), and the trail leads back out. The page's URL is never changed, so it works the same inside a vault host.
 *
 * Without JavaScript the element's own children show: put a linked list there (the build's sg_graph() helper does).
 * Data from the graph is only ever set as text, and an href only if it is http(s) or relative.
 *
 * Events, on document: sg:graph.focus { id, label, kind }   sg:graph.open { id, graph }
 * API on the element: .model (the loaded graph), .focusOn(id), .pathTo(id), .core (sg-graph-core.js)
 *
 * Brief: admin/content/briefs/2026-10-22__brief__the-cartographer-joins.md
 *
 * @module sg-graph
 * @version 1.0.0
 */

import { SgComponent } from '../../../../base/v1/v1.0/v1.0.0/sg-component.js'
import * as core from './sg-graph-core.js'

const SVG = 'http://www.w3.org/2000/svg'

export const VIEWS = Object.freeze(['ego', 'layers', 'map', 'list'])
const VIEW_LABEL = Object.freeze({ ego: 'Around one', layers: 'In layers', map: 'Map', list: 'List' })
const STATUS = Object.freeze(['confirmed', 'reported', 'disputed', 'contradicted', 'unverified', 'open', 'explained'])

function h(tag, props = {}, ...kids) {
    const el = document.createElement(tag)
    for (const [k, v] of Object.entries(props)) {
        if (v == null || v === false) continue
        if (k === 'text') el.textContent = v
        else if (k === 'on') for (const [ev, fn] of Object.entries(v)) el.addEventListener(ev, fn)
        else el.setAttribute(k, v === true ? '' : v)
    }
    for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) el.append(kid)
    return el
}

function s(tag, attrs = {}) {
    const el = document.createElementNS(SVG, tag)
    for (const [k, v] of Object.entries(attrs)) if (v != null) el.setAttribute(k, v)
    return el
}

function clip(text, n) { return text.length > n ? text.slice(0, n - 1) + '…' : text }

export class SgGraph extends SgComponent {

    static jsUrl = import.meta.url

    static get observedAttributes() { return ['focus', 'view', 'depth'] }

    get resourceName() { return 'sg-graph' }

    get core() { return core }

    get model() { return this._G }

    async onReady() {
        this._stack  = []
        this._trail  = []
        this._target = null
        this._root   = this.$('.root')
        if (this.getAttribute('controls') === 'none') this.$('[data-role="bar"]').hidden = true
        const data = await this._read(this.getAttribute('src'))
        this._open(data, this.getAttribute('src') || '', 'the graph')
        const keep = (this.getAttribute('verbs') || '').split(',').map(v => v.trim()).filter(Boolean)
        if (keep.length) this._filter.hide = new Set(this._G.edges.map(e => e.verb).filter(v => !keep.includes(v)))
        this._wire()
        if (this._pending) { const id = this._pending; this._pending = null; this.focusOn(id, { trail: false }) }
        this._ro = new ResizeObserver(() => this._resized())
        this._ro.observe(this.$('[data-role="stage"]'))
        this._render()
    }

    attributeChangedCallback(name, old, value) {
        if (!this._G || old === value) return
        if (name === 'focus' && value) return this.focusOn(value)
        this._render()
    }

    // ------------------------------------------------------------------------------------ public

    focusOn(id, { trail = true } = {}) {
        if (!this._G) { this._pending = id; return false }
        if (!this._G.byId.has(id)) return false
        if (trail && this._focus && this._focus !== id) this._trail.push(this._focus)
        if (this._trail.length > 12) this._trail.shift()
        this._focus  = id
        this._target = null
        const n = this._G.byId.get(id)
        this.emit('sg:graph.focus', { id, label: n.label, kind: n.kind })
        this._render()
        return true
    }

    pathTo(id) {
        if (!this._G) return null
        this._target = this._G.byId.has(id) ? id : null
        this._render()
        return this._target ? core.path(this._G, this._focus, id, this._filter) : null
    }

    // ------------------------------------------------------------------------------------ data

    async _read(src) {
        if (src) {
            const r = await fetch(new URL(src, document.baseURI))
            if (!r.ok) throw new Error(`${r.status} ${src}`)
            return r.json()
        }
        const tag = this.querySelector('script[type="application/json"]')
        if (!tag) throw new Error('no src and no <script type="application/json"> child')
        return JSON.parse(tag.textContent)
    }

    _open(data, src, label) {
        const G = core.load(data)
        // an inner graph keeps its own words and borrows the outer graph's only for what it does not name
        if (this._G) {
            G.ontology.kinds = { ...this._G.ontology.kinds, ...G.ontology.kinds }
            G.ontology.verbs = { ...this._G.ontology.verbs, ...G.ontology.verbs }
        }
        this._G = G
        this._filter = { kinds: null, verbs: null, hide: new Set() }
        this._src = src
        this._graphLabel = (data && data.title) || label
        const want = this._stack.length ? this._zoomFocus : this.getAttribute('focus')
        this._focus = G.byId.has(want) ? want : this._busiest()
        this._trail = []
    }

    _busiest() {
        let best = null, d = -1
        for (const n of this._G.nodes) { const k = core.degree(this._G, n.id); if (k > d) { d = k; best = n.id } }
        return best
    }

    async _zoom(node, z = node.zoom[0]) {
        if (this._zooming || !z) return
        this._zooming = true
        try {
            const u = new URL(this._href(z.graph, true), document.baseURI)
            // a zoom comes from the graph's data: only this site's own files are opened, never another site's
            if (u.origin !== location.origin) throw new Error(`${u.origin} is not this site`)
            const url = u.href
            const data = await this._read(url)
            this._stack.push({ G: this._G, focus: this._focus, trail: this._trail, label: this._graphLabel, src: this._src, filter: this._filter })
            this._zoomFocus = z.focus
            this._open(data, url, z.label || node.label)
            this.emit('sg:graph.open', { id: node.id, graph: z.graph, focus: z.focus })
            this._render()
        } catch (err) {
            this._say(`Could not open the inner graph: ${err.message}`)
        } finally {
            this._zooming = false
        }
    }

    _unzoom(to) {
        while (this._stack.length > to) {
            const back = this._stack.pop()
            Object.assign(this, { _G: back.G, _focus: back.focus, _trail: back.trail, _graphLabel: back.label, _src: back.src, _filter: back.filter })
        }
        this._render()
    }

    _href(href, raw = false) {
        const base = this.getAttribute('base') || ''
        const rel = /^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith('/') || href.startsWith('#') ? href : base + href
        return raw ? rel : core.safeHref(rel, document.baseURI)
    }

    // ------------------------------------------------------------------------------------ controls

    _wire() {
        const find = this.$('[data-role="find"]')
        find.addEventListener('input', () => this._hits(find.value))
        find.addEventListener('keydown', ev => {
            if (ev.key === 'Enter') { const first = this.$('[data-role="hits"] button'); if (first) first.click() }
            if (ev.key === 'Escape') { find.value = ''; this._picking = false; find.placeholder = 'Find a node'; this._hits('') }
        })
        for (const b of this.$$('[data-view]')) b.addEventListener('click', () => { this.setAttribute('view', b.dataset.view) })
        const depth = this.$('[data-role="depth"]')
        depth.value = String(this._depth())
        depth.addEventListener('change', () => this.setAttribute('depth', depth.value))
    }

    _hits(q) {
        const box = this.$('[data-role="hits"]')
        box.replaceChildren()
        const found = core.search(this._G, q, 12)
        box.hidden = !found.length
        for (const n of found) {
            box.append(h('button', { type: 'button', on: { click: () => {
                if (this._picking) { this._picking = false; this.pathTo(n.id) } else this.focusOn(n.id)
                this.$('[data-role="find"]').value = ''
                this.$('[data-role="find"]').placeholder = 'Find a node'
                box.hidden = true
            } } }, h('span', { class: 'k', text: this._kindLabel(n.kind) }), ' ', clip(n.label, 90)))
        }
    }

    _view()  { const v = this.getAttribute('view'); return VIEWS.includes(v) ? v : 'ego' }
    _depth() { return Math.min(3, Math.max(1, parseInt(this.getAttribute('depth') || '1', 10) || 1)) }
    _max()   { return Math.max(5, parseInt(this.getAttribute('max') || '60', 10) || 60) }

    _kindLabel(kind) {
        const t = (this._G.ontology.kinds || {})[kind]
        return (t && t.label) || kind
    }

    _resized() {
        const w = this.$('[data-role="stage"]').clientWidth
        if (Math.abs(w - (this._w || 0)) > 24) this._render()
    }

    _say(text) { this.$('[data-role="foot"]').textContent = text }

    // ------------------------------------------------------------------------------------ render

    _render() {
        if (!this._G) return
        const had = this.shadowRoot.activeElement
        const keep = had && (had.dataset.id ? `[data-id="${CSS.escape(had.dataset.id)}"]` : had.dataset.verb ? `[data-verb="${CSS.escape(had.dataset.verb)}"]` : null)
        this._paint()
        // the node walked to is where the keyboard goes next; a chip toggled keeps it
        const back = keep && (had.dataset.id ? this.$(`.n.focus`) || this.$(keep) : this.$(keep))
        if (back) back.focus({ preventScroll: true })
    }

    _paint() {
        const view = this._view()
        for (const b of this.$$('[data-view]')) b.setAttribute('aria-pressed', String(b.dataset.view === view))
        this._root.dataset.view = view
        this._renderTrail()
        const sub = view === 'map' && this._G.nodes.length <= 400 && !this._filter.hide.size
            ? { nodes: this._G.nodes, edges: this._G.edges, hop: new Map(), truncated: false }
            : core.ego(this._G, this._focus, this._depth(), this._filter, this._max())
        const path = this._target ? core.path(this._G, this._focus, this._target, this._filter) : null
        if (path) for (const n of path.nodes) if (!sub.nodes.includes(n)) { sub.nodes = [...sub.nodes, n]; sub.hop.set(n.id, this._depth()) }
        if (path) sub.edges = [...new Set([...sub.edges, ...path.edges])]
        this._renderChips()
        this._renderStage(view, sub, path)
        this._renderDetail(path)
        this._renderList()
        const c = core.census(this._G)
        this._say(`${this._G.nodes.length} nodes, ${this._G.edges.length} edges, ${c.verbs.length} verbs` +
            (sub.truncated ? `; ${sub.nodes.length} drawn, the most this view draws: step to a node or lower the depth to see the rest` : '') +
            (this._G.dropped ? `; ${this._G.dropped} edges without a verb or an end were left out` : ''))
    }

    _renderTrail() {
        const nav = this.$('[data-role="trail"]')
        nav.replaceChildren()
        this._stack.forEach((f, i) => nav.append(h('button', { type: 'button', class: 'up', on: { click: () => this._unzoom(i) } }, '↑ ', clip(f.label, 40)), ' › '))
        if (this._stack.length) nav.append(h('b', { text: clip(this._graphLabel, 40) }), ' · ')
        for (const id of this._trail.slice(-5)) {
            const n = this._G.byId.get(id)
            if (n) nav.append(h('button', { type: 'button', on: { click: () => { this._trail = this._trail.slice(0, this._trail.lastIndexOf(id)); this.focusOn(id, { trail: false }) } } }, clip(n.label, 28)), ' → ')
        }
        const f = this._G.byId.get(this._focus)
        if (f) nav.append(h('b', { text: clip(f.label, 40) }))
    }

    _renderChips() {
        const box = this.$('[data-role="chips"]')
        box.replaceChildren()
        const here = new Map()
        for (const r of core.neighbours(this._G, this._focus, null)) here.set(r.edge.verb, (here.get(r.edge.verb) || 0) + 1)
        if (here.size < 2 && !this._filter.hide.size) return
        for (const [verb, n] of [...here].sort((a, b) => core.cmp(a[0], b[0]))) {
            const on = !this._filter.hide.has(verb)
            box.append(h('button', { type: 'button', class: 'chip', 'data-verb': verb, 'aria-pressed': String(on), on: { click: () => {
                on ? this._filter.hide.add(verb) : this._filter.hide.delete(verb)
                this._render()
            } } }, ((this._G.ontology.verbs || {})[verb] || {}).label || verb, h('span', { class: 'n', text: ` ${n}` })))
        }
    }

    _renderStage(view, sub, path) {
        const stage = this.$('[data-role="stage"]')
        stage.replaceChildren()
        stage.hidden = view === 'list'
        if (view === 'list' || !sub.nodes.length) return
        const w = this._w = Math.max(280, stage.clientWidth || 640)
        const narrow = w < 520
        const hAttr = parseInt(this.getAttribute('height') || '0', 10)
        let H = hAttr || Math.round(Math.min(640, Math.max(300, w * (narrow ? 1 : 0.62))))
        let pos, columns = null
        if (view === 'layers') {
            const order = Object.keys(this._G.ontology.kinds || {})
            const rows = Math.max(...[...groupCount(sub.nodes)].map(([, n]) => n))
            H = hAttr || Math.max(H, 40 + rows * 22)
            const L = core.layered(this._G, sub, w, H - 24, order)
            pos = new Map([...L.pos].map(([id, p]) => [id, { x: p.x, y: p.y + 24 }]))
            columns = L.columns
        } else if (view === 'map') {
            // the force layout is the costly one: the same nodes at the same size are laid out once
            const key = `${w}x${H}|${sub.nodes.map(n => n.id).join('|')}`
            this._layouts = this._layouts || new Map()
            if (!this._layouts.has(key)) { if (this._layouts.size > 8) this._layouts.clear(); this._layouts.set(key, core.force(this._G, sub, w, H)) }
            pos = this._layouts.get(key)
        } else {
            pos = core.radial(this._G, sub, this._focus, w, H)
        }
        const svg = s('svg', { viewBox: `0 0 ${w} ${H}`, width: '100%', height: H, role: 'group', 'aria-label': `${this._graphLabel}: ${sub.nodes.length} nodes around ${(this._G.byId.get(this._focus) || {}).label || ''}` })
        const zoom = s('g', { class: 'zoom' })
        svg.append(zoom)
        if (columns) for (const c of columns) {
            const t = s('text', { class: 'col', x: c.x, y: 14 })
            t.textContent = `${this._kindLabel(c.name)} (${c.count})`
            zoom.append(t)
        }
        const onPath = new Set(path ? path.edges : [])
        const pathNodes = new Set(path ? path.nodes.map(n => n.id) : [])
        for (const e of sub.edges) {
            const a = pos.get(e.from), b = pos.get(e.to)
            if (!a || !b) continue
            const mx = (a.x + b.x) / 2 + (view === 'layers' ? 0 : (b.y - a.y) * 0.08), my = (a.y + b.y) / 2 - (view === 'layers' ? 0 : (b.x - a.x) * 0.08)
            const p = s('path', { class: `e v-${slug(e.verb)}${onPath.has(e) ? ' on-path' : ''}`, d: `M${a.x.toFixed(1)},${a.y.toFixed(1)} Q${mx.toFixed(1)},${my.toFixed(1)} ${b.x.toFixed(1)},${b.y.toFixed(1)}` })
            const title = s('title')
            title.textContent = `${this._G.byId.get(e.from).label} ${core.phrase(this._G, e, e.from)} ${this._G.byId.get(e.to).label}`
            p.append(title)
            zoom.append(p)
        }
        const labelled = this._labelled(view, sub, narrow, pathNodes)
        const sorted = [...sub.nodes].sort((a, b) => (a.id === this._focus) - (b.id === this._focus))
        for (const n of sorted) {
            const p = pos.get(n.id)
            if (!p) continue
            const focus = n.id === this._focus
            const g = s('g', { 'data-id': n.id, class: `n k-${slug(n.kind)}${n.status && STATUS.includes(n.status) ? ' s-' + n.status : ''}${focus ? ' focus' : ''}${pathNodes.has(n.id) ? ' on-path' : ''}${n.zoom.length ? ' has-graph' : ''}`,
                transform: `translate(${p.x.toFixed(1)},${p.y.toFixed(1)})`, tabindex: '0', role: 'button',
                'aria-label': `${this._kindLabel(n.kind)}: ${n.label}${focus ? ' (in focus)' : ''}` })
            g.append(s('circle', { r: focus ? 9 : n.zoom.length ? 7 : 5.5 }))
            const title = s('title')
            title.textContent = `${this._kindLabel(n.kind)}: ${n.label}`
            g.append(title)
            if (labelled.has(n.id)) {
                const right = view === 'layers' || p.x < w * 0.62
                // on a phone the focus is mid-screen: its label goes under it, centred, so it is not cut at the edge
                const under = focus && narrow && view !== 'layers'
                const t = s('text', under ? { x: 0, y: 24, 'text-anchor': 'middle' } : { x: right ? 12 : -12, y: 4, 'text-anchor': right ? 'start' : 'end' })
                t.textContent = clip(n.label, under ? Math.floor(w / 7.5) : focus ? 48 : narrow ? 22 : view === 'layers' ? Math.max(14, Math.floor(w / Math.max(1, (columns || []).length) / 7.2) - 3) : 34)
                g.append(t)
            }
            const go = () => focus && n.zoom.length ? this._zoom(n) : this.focusOn(n.id)
            g.addEventListener('click', go)
            g.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); go() } })
            zoom.append(g)
        }
        if (view === 'map') panZoom(svg, zoom)
        stage.append(svg)
    }

    _labelled(view, sub, narrow, pathNodes) {
        const ids = new Set([this._focus, ...pathNodes])
        if (view === 'layers') { if (!narrow) for (const n of sub.nodes) ids.add(n.id); return ids }
        const budget = narrow ? 10 : view === 'map' ? 24 : 36
        const ranked = [...sub.nodes].sort((a, b) => (sub.hop.get(a.id) || 9) - (sub.hop.get(b.id) || 9) || core.degree(this._G, b.id) - core.degree(this._G, a.id) || core.cmp(a.id, b.id))
        for (const n of ranked) { if (ids.size >= budget) break; ids.add(n.id) }
        return ids
    }

    _renderDetail(path) {
        const box = this.$('[data-role="detail"]')
        box.replaceChildren()
        const n = this._G.byId.get(this._focus)
        if (!n) return
        const head = h('p', { class: 'head' }, h('span', { class: 'k', text: this._kindLabel(n.kind) }), n.status ? h('span', { class: `st s-${n.status}`, text: n.status }) : null)
        box.append(head, h('p', { class: 'label', text: n.label }))
        const acts = h('p', { class: 'acts' })
        const href = n.href && this._href(n.href)
        if (href) acts.append(h('a', { href, text: 'Open its page' }))
        for (const z of n.zoom) acts.append(h('button', { type: 'button', class: 'zoomin', on: { click: () => this._zoom(n, z) } }, `${z.label || 'Open the graph inside it'} ↓`))
        acts.append(h('button', { type: 'button', on: { click: () => { this._picking = true; const f = this.$('[data-role="find"]'); f.placeholder = 'Connect to… (type a name)'; f.focus() } } }, 'How is this connected to…'))
        box.append(acts)
        const props = Object.entries(n).filter(([k, v]) => !['id', 'kind', 'label', 'href', 'graph', 'graph_focus', 'zoom', 'status'].includes(k) && v !== null && v !== '' && typeof v !== 'object')
        if (props.length) box.append(h('dl', {}, props.slice(0, 10).map(([k, v]) => [h('dt', { text: k.replace(/_/g, ' ') }), h('dd', { text: clip(String(v), 240) })])))
        if (Array.isArray(n.files) && n.files.length) {
            box.append(h('p', { class: 'small', text: 'Files and their sha256:' }), h('ul', { class: 'files' }, n.files.map(f => h('li', {}, h('code', { text: String(f.name) }), ' ', h('code', { class: 'hash', text: String(f.sha256 || '').slice(0, 16) + '…', title: String(f.sha256 || '') })))))
        }
        if (this._target) {
            const t = this._G.byId.get(this._target)
            if (this._target === this._focus) box.append(h('p', { class: 'path', text: 'That is the node in focus.' }))
            else if (!path) box.append(h('p', { class: 'path', text: `No path from here to ${t.label} with the verbs shown.` }))
            else {
                const ol = h('ol', { class: 'path', 'aria-label': `How ${n.label} is connected to ${t.label}` })
                path.edges.forEach((e, i) => {
                    const a = path.nodes[i], b = path.nodes[i + 1]
                    ol.append(h('li', {}, h('b', { text: clip(a.label, 60) }), ` ${core.phrase(this._G, e, a.id)} `, h('b', { text: clip(b.label, 60) })))
                })
                box.append(h('p', { class: 'small', text: `Connected in ${path.edges.length} step${path.edges.length === 1 ? '' : 's'}:` }), ol)
            }
        }
    }

    _renderList() {
        const box = this.$('[data-role="list"]')
        box.replaceChildren()
        const rows = core.neighbours(this._G, this._focus, this._filter)
        const groups = new Map()
        for (const r of rows) { if (!groups.has(r.phrase)) groups.set(r.phrase, []); groups.get(r.phrase).push(r) }
        const f = this._G.byId.get(this._focus)
        if (!f) { box.append(h('p', { class: 'small', text: 'This graph has no nodes.' })); return }
        box.append(h('p', { class: 'small', text: `${rows.length} link${rows.length === 1 ? '' : 's'} from ${clip(f.label, 60)}:` }))
        for (const [phrase, list] of groups) {
            const seen = new Set()
            const items = list.filter(r => !seen.has(r.other.id) && seen.add(r.other.id))
            box.append(h('details', { open: groups.size <= 4 || items.length <= 6 },
                h('summary', {}, h('b', { text: phrase }), ` (${items.length})`),
                h('ul', {}, items.map(r => {
                    const href = r.other.href && this._href(r.other.href)
                    return h('li', {},
                        h('button', { type: 'button', class: 'to', 'data-id': r.other.id, on: { click: () => this.focusOn(r.other.id) } }, h('span', { class: 'k', text: this._kindLabel(r.other.kind) }), ' ', clip(r.other.label, 110)),
                        href ? h('a', { href, class: 'page', 'aria-label': `Open the page for ${r.other.label}`, text: '↗' }) : null)
                }))))
        }
    }
}

function slug(x) { return String(x).toLowerCase().replace(/[^a-z0-9]+/g, '-') }

function groupCount(nodes) {
    const m = new Map()
    for (const n of nodes) { const c = n.layer || n.kind; m.set(c, (m.get(c) || 0) + 1) }
    return m
}

function panZoom(svg, g) {
    let k = 1, tx = 0, ty = 0, drag = null
    const apply = () => g.setAttribute('transform', `translate(${tx.toFixed(1)},${ty.toFixed(1)}) scale(${k.toFixed(3)})`)
    svg.addEventListener('wheel', ev => {
        if (!ev.ctrlKey && !ev.metaKey) return
        ev.preventDefault()
        const r = svg.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top
        const f = ev.deltaY < 0 ? 1.15 : 1 / 1.15
        tx = x - (x - tx) * f; ty = y - (y - ty) * f; k *= f
        apply()
    }, { passive: false })
    svg.addEventListener('pointerdown', ev => { if (ev.target === svg) { drag = { x: ev.clientX - tx, y: ev.clientY - ty }; svg.setPointerCapture(ev.pointerId) } })
    svg.addEventListener('pointermove', ev => { if (drag) { tx = ev.clientX - drag.x; ty = ev.clientY - drag.y; apply() } })
    svg.addEventListener('pointerup', () => { drag = null })
    svg.addEventListener('pointercancel', () => { drag = null })
}

customElements.define('sg-graph', SgGraph)
