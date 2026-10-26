/**
 * sg-graph-core: the graph model behind <sg-graph>, with no DOM in it, so it runs the same in a
 * page, a worker, an agent's browser (window.__tools) or node for its tests.
 *
 * One data contract for every graph on the site (data/ontology.json says which kinds and verbs
 * exist; this module does not need it to work):
 *
 *     { nodes: [{ id, kind, label, href?, layer?, status?, graph?, ...anything }],
 *       edges: [{ from, to, verb, source?, ...anything }],
 *       ontology?: { kinds: { <kind>: { label, plural? } }, verbs: { <verb>: { inverse, label? } } } }
 *
 * Older shapes are read too: `rel` or `type` for verb, `name` for label, `layer` for kind.
 * Everything here is deterministic: the same graph gives the same layout, byte for byte.
 *
 * Brief: admin/content/briefs/2026-10-22__brief__the-cartographer-joins.md
 *
 * @module sg-graph-core
 * @version 1.0.0
 */

/** Normalise any accepted shape into { nodes, edges, byId, out, inn, ontology, dropped }. */
export function load(data) {
    const nodes = []
    const byId = new Map()
    for (const raw of (data && data.nodes) || []) {
        if (!raw || raw.id == null || byId.has(String(raw.id))) continue
        const n = { ...raw, id: String(raw.id) }
        n.kind = String(raw.kind || raw.layer || raw.type || 'node')
        n.label = String(raw.label || raw.name || raw.title || raw.id)
        nodes.push(n)
        byId.set(n.id, n)
    }
    const edges = []
    let dropped = 0
    for (const raw of (data && data.edges) || []) {
        const from = String(raw.from ?? raw.source ?? ''), to = String(raw.to ?? raw.target ?? '')
        const verb = raw.verb || raw.rel || raw.type
        // the estate's grammar: no generic association edge, so an edge without a verb is not drawn
        if (!byId.has(from) || !byId.has(to) || !verb) { dropped++; continue }
        edges.push({ ...raw, from, to, verb: String(verb) })
    }
    const out = new Map(), inn = new Map()
    for (const n of nodes) { out.set(n.id, []); inn.set(n.id, []) }
    for (const e of edges) { out.get(e.from).push(e); inn.get(e.to).push(e) }
    const given = (data && data.ontology) || {}
    const ontology = { ...given, kinds: { ...(given.kinds || {}) }, verbs: { ...(given.verbs || {}) } }
    // a graph without an ontology block may still name its inverses: in a 'verbs' list, or on each edge (the risk graph)
    for (const v of (data && Array.isArray(data.verbs) ? data.verbs : [])) {
        if (v && v.verb && !ontology.verbs[v.verb]) ontology.verbs[v.verb] = { label: say(v.verb), inverse: say(v.inverse || '') || undefined }
    }
    for (const e of edges) {
        if (e.inverse && !ontology.verbs[e.verb]) ontology.verbs[e.verb] = { label: say(e.verb), inverse: say(e.inverse) }
    }
    for (const n of nodes) n.zoom = zooms(n)
    return { nodes, edges, byId, out, inn, ontology, dropped, meta: data || {} }
}

/** The graphs a node opens into: its 'zoom' list, or the older single 'graph' and 'graph_focus'. */
function zooms(n) {
    if (Array.isArray(n.zoom)) return n.zoom.filter(z => z && typeof z.graph === 'string')
    return typeof n.graph === 'string' ? [{ graph: n.graph, focus: n.graph_focus, label: 'Open the graph inside it' }] : []
}

function say(v) { return String(v || '').replace(/_/g, ' ')
}

/** The phrase for an edge read from one end: "cites" from its tail, "cited by" from its head. */
export function phrase(G, edge, fromId) {
    const v = (G.ontology.verbs || {})[edge.verb] || {}
    if (edge.from === fromId) return v.label || say(edge.verb)
    return v.inverse || (edge.inverse && say(edge.inverse)) || `← ${say(edge.verb)}`
}

/** A filter is { kinds: Set|null, verbs: Set|null, hide: Set|null }: kinds and verbs keep only what they list, hide drops what it lists; null passes everything. */
export function passes(G, filter, edge) {
    if (!filter) return true
    if (filter.hide && filter.hide.has(edge.verb)) return false
    if (filter.verbs && !filter.verbs.has(edge.verb)) return false
    if (filter.kinds) {
        const a = G.byId.get(edge.from).kind, b = G.byId.get(edge.to).kind
        if (!filter.kinds.has(a) || !filter.kinds.has(b)) return false
    }
    return true
}

/** Every edge touching id, each with the node at its other end, sorted by phrase then label. */
export function neighbours(G, id, filter) {
    const rows = []
    for (const e of G.out.get(id) || []) if (passes(G, filter, e)) rows.push({ edge: e, other: G.byId.get(e.to), phrase: phrase(G, e, id) })
    for (const e of G.inn.get(id) || []) if (passes(G, filter, e)) rows.push({ edge: e, other: G.byId.get(e.from), phrase: phrase(G, e, id) })
    rows.sort((a, b) => cmp(a.phrase, b.phrase) || cmp(a.other.label, b.other.label) || cmp(a.other.id, b.other.id))
    return rows
}

/** The nodes within depth hops of focus (either direction), at most limit of them, and the edges among them. */
export function ego(G, focus, depth = 1, filter = null, limit = 400) {
    if (!G.byId.has(focus)) return { nodes: [], edges: [], hop: new Map(), truncated: false }
    const hop = new Map([[focus, 0]])
    let frontier = [focus], truncated = false
    for (let d = 1; d <= depth && frontier.length; d++) {
        const next = []
        for (const id of frontier) {
            for (const r of neighbours(G, id, filter)) {
                if (hop.has(r.other.id)) continue
                if (hop.size >= limit) { truncated = true; break }
                hop.set(r.other.id, d)
                next.push(r.other.id)
            }
        }
        frontier = next
    }
    const ids = new Set(hop.keys())
    const edges = G.edges.filter(e => ids.has(e.from) && ids.has(e.to) && passes(G, filter, e))
    return { nodes: [...ids].map(id => G.byId.get(id)), edges, hop, truncated }
}

/** The shortest path between a and b, ignoring direction: { nodes, edges }, or null when there is none or a is b. Connecting the dots. */
export function path(G, a, b, filter = null) {
    if (!G.byId.has(a) || !G.byId.has(b) || a === b) return null
    const prev = new Map([[a, null]])
    const queue = [a]
    while (queue.length) {
        const id = queue.shift()
        if (id === b) break
        for (const r of neighbours(G, id, filter)) {
            if (prev.has(r.other.id)) continue
            prev.set(r.other.id, { id, edge: r.edge })
            queue.push(r.other.id)
        }
    }
    if (!prev.has(b)) return null
    const nodes = [], edges = []
    for (let at = b; at != null; at = prev.get(at) && prev.get(at).id) {
        nodes.unshift(G.byId.get(at))
        if (prev.get(at)) edges.unshift(prev.get(at).edge)
    }
    return { nodes, edges }
}

/** Nodes whose label or id contains every word of the query, best first. */
export function search(G, query, limit = 20) {
    const words = String(query || '').toLowerCase().split(/\s+/).filter(Boolean)
    if (!words.length) return []
    const hits = []
    for (const n of G.nodes) {
        const hay = (n.label + ' ' + n.id).toLowerCase()
        if (words.every(w => hay.includes(w))) hits.push([hay.startsWith(words[0]) ? 0 : 1, degree(G, n.id) * -1, n])
    }
    hits.sort((x, y) => x[0] - y[0] || x[1] - y[1] || cmp(x[2].label, y[2].label))
    return hits.slice(0, limit).map(h => h[2])
}

export function degree(G, id) { return (G.out.get(id) || []).length + (G.inn.get(id) || []).length }

/** Counts by kind and by verb, in a stable order. */
export function census(G) {
    const kinds = new Map(), verbs = new Map()
    for (const n of G.nodes) kinds.set(n.kind, (kinds.get(n.kind) || 0) + 1)
    for (const e of G.edges) verbs.set(e.verb, (verbs.get(e.verb) || 0) + 1)
    const sorted = m => [...m].sort((a, b) => b[1] - a[1] || cmp(a[0], b[0]))
    return { kinds: sorted(kinds), verbs: sorted(verbs) }
}

// ---------------------------------------------------------------------------------------- layouts
// Each returns Map(id -> {x, y}) in the pixel space it is given, so text is drawn at its real size.

/** Focus in the centre, one ring per hop, each ring ordered by the phrase that joins it so like sits with like. */
export function radial(G, sub, focus, w, h) {
    const pos = new Map([[focus, { x: w / 2, y: h / 2 }]])
    const rings = new Map()
    const key = new Map()
    for (const r of neighbours(G, focus, null)) if (!key.has(r.other.id)) key.set(r.other.id, r.phrase)
    for (const n of sub.nodes) {
        const d = sub.hop.get(n.id)
        if (!d) continue
        if (!rings.has(d)) rings.set(d, [])
        rings.get(d).push(n)
    }
    const R = Math.min(w, h) / 2 - 24
    const nr = rings.size || 1
    for (const [d, list] of rings) {
        list.sort((a, b) => cmp(key.get(a.id) || '~', key.get(b.id) || '~') || cmp(a.kind, b.kind) || cmp(a.label, b.label))
        const rad = R * d / nr
        list.forEach((n, i) => {
            const t = -Math.PI / 2 + (2 * Math.PI * i) / list.length
            pos.set(n.id, { x: w / 2 + rad * Math.cos(t), y: h / 2 + rad * Math.sin(t) })
        })
    }
    return pos
}

/** Columns by layer (or kind), rows ordered by a few barycentre sweeps so edges cross less. */
export function layered(G, sub, w, h, order) {
    const cols = new Map()
    for (const n of sub.nodes) {
        const c = n.layer || n.kind
        if (!cols.has(c)) cols.set(c, [])
        cols.get(c).push(n)
    }
    const names = [...cols.keys()].sort((a, b) => rank(order, a) - rank(order, b) || cmp(a, b))
    for (const c of names) cols.get(c).sort((a, b) => cmp(a.label, b.label))
    const y = new Map()
    const place = () => names.forEach(c => cols.get(c).forEach((n, i) => y.set(n.id, i / Math.max(1, cols.get(c).length - 1))))
    place()
    const adj = new Map(sub.nodes.map(n => [n.id, []]))
    for (const e of sub.edges) { adj.get(e.from).push(e.to); adj.get(e.to).push(e.from) }
    for (let sweep = 0; sweep < 6; sweep++) {
        for (const c of names) {
            const bc = n => { const a = adj.get(n.id); return a.length ? a.reduce((s, id) => s + y.get(id), 0) / a.length : y.get(n.id) }
            cols.get(c).sort((a, b) => bc(a) - bc(b) || cmp(a.label, b.label))
        }
        place()
    }
    const pos = new Map()
    const pad = 16, cw = (w - 2 * pad) / Math.max(1, names.length)
    names.forEach((c, ci) => {
        const list = cols.get(c)
        const step = (h - 2 * pad) / Math.max(1, list.length)
        list.forEach((n, i) => pos.set(n.id, { x: pad + cw * ci + 8, y: pad + step * (i + 0.5) }))
    })
    return { pos, columns: names.map((c, i) => ({ name: c, x: pad + cw * i + 8, count: cols.get(c).length })) }
}

/** A force layout with a seeded start and a fixed number of steps, so it is the same every time. */
export function force(G, sub, w, h, steps = 220) {
    const ids = sub.nodes.map(n => n.id)
    const rnd = seeded(hash(ids.join('|')))
    const p = new Map(ids.map(id => [id, { x: w * (0.1 + 0.8 * rnd()), y: h * (0.1 + 0.8 * rnd()), dx: 0, dy: 0 }]))
    const k = Math.sqrt((w * h) / Math.max(1, ids.length)) * 0.7
    let temp = w / 8
    for (let s = 0; s < steps; s++) {
        for (const a of ids) { const pa = p.get(a); pa.dx = 0; pa.dy = 0 }
        for (let i = 0; i < ids.length; i++) {
            const pa = p.get(ids[i])
            for (let j = i + 1; j < ids.length; j++) {
                const pb = p.get(ids[j])
                let dx = pa.x - pb.x, dy = pa.y - pb.y
                const d2 = dx * dx + dy * dy || 0.01, f = (k * k) / d2
                pa.dx += dx * f; pa.dy += dy * f; pb.dx -= dx * f; pb.dy -= dy * f
            }
        }
        for (const e of sub.edges) {
            const pa = p.get(e.from), pb = p.get(e.to)
            const dx = pa.x - pb.x, dy = pa.y - pb.y, d = Math.sqrt(dx * dx + dy * dy) || 0.01, f = d / k
            pa.dx -= dx * f; pa.dy -= dy * f; pb.dx += dx * f; pb.dy += dy * f
        }
        for (const id of ids) {
            const q = p.get(id), d = Math.sqrt(q.dx * q.dx + q.dy * q.dy) || 1, m = Math.min(d, temp)
            q.x = Math.min(w - 12, Math.max(12, q.x + (q.dx / d) * m + (w / 2 - q.x) * 0.002))
            q.y = Math.min(h - 12, Math.max(12, q.y + (q.dy / d) * m + (h / 2 - q.y) * 0.002))
        }
        temp *= 0.975
    }
    return new Map([...p].map(([id, q]) => [id, { x: q.x, y: q.y }]))
}

// ---------------------------------------------------------------------------------------- helpers

export function cmp(a, b) { return a < b ? -1 : a > b ? 1 : 0 }
function rank(order, c) { const i = (order || []).indexOf(c); return i < 0 ? 1e6 : i }
function hash(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) } return h >>> 0 }
function seeded(a) { return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296 } }

/** A URL from data is followed only if it stays on http(s) or is relative; anything else is refused. */
export function safeHref(href, base) {
    if (typeof href !== 'string' || !href) return null
    try {
        const u = new URL(href, base || 'http://x.invalid/')
        if (u.protocol !== 'http:' && u.protocol !== 'https:') return null
        return base ? u.href : href
    } catch { return null }
}
