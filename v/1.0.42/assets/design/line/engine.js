/* From the editor's briefing pack 'the line' (25 October 2026), brief
   admin/content/briefs/2026-10-25__brief__the-line.md. Vendored unchanged: pure functions, no DOM,
   no storage. The site's runtime is assets/design/line/line.js; the tests are engine.test.mjs. */
/*
 * The line: reference implementation.
 *
 * Pure functions, no DOM, no storage access: give them the state, get back what the line says.
 * Works as a browser global (window.LensLine) and as a CommonJS module (node).
 * Source of truth for the words: spec/line-copy.json. For the roles: spec/roles.json.
 * For the moments and thresholds: spec/moments.json.
 *
 *   startingRole(ctx, roles)            -> who you start as (rule ladder in the brief, section 4)
 *   visitStart(record, now, thresholds) -> is this a new visit, and from when do changes count
 *   momentFrom(ctx, thresholds)         -> which visit moment this load is (spec/moments.json)
 *   computeLine(state, roles, copy)     -> what the line says, its size, tone and actions
 *   chooseDepth(role, reader, set, roles) -> the depth to use
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) { module.exports = factory(); }
  else { root.LensLine = factory(); }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function fill(tpl, vars) {
    if (tpl == null) return "";
    return String(tpl).replace(/\{(\w+)\}/g, function (_, k) { return vars[k] != null ? String(vars[k]) : "{" + k + "}"; });
  }

  function chooseDepth(role, reader, depthSet, roles) {
    if (depthSet) return depthSet;
    if (reader && roles.readers[reader]) return roles.readers[reader].depth;
    return roles.roles[role].depth;
  }

  /* ---------- 1. Who you start as ---------- */
  // ctx: { stored: record|null, asParam: "journalist"|null, referrer: "https://...", searchTerms: "php 8.4.27 fpm" }
  function startingRole(ctx, roles) {
    var R = roles.roles, RD = roles.readers;
    function resolve(id) {
      if (R[id]) return { role: id, reader: null };
      if (RD[id]) return { role: RD[id].role, reader: id };
      return null;
    }
    if (ctx.asParam) {
      var s = resolve(ctx.asParam);
      if (s) return { role: s.role, reader: s.reader, source: "shared", reason: "a link shared set to this view", borrowed: !!(ctx.stored && ctx.stored.confirmed && ctx.stored.role !== s.role) };
    }
    if (ctx.stored) return { role: ctx.stored.role, reader: ctx.stored.reader || null, source: ctx.stored.source, reason: null, borrowed: false };
    var ref = (ctx.referrer || "").toLowerCase(), q = (ctx.searchTerms || "").toLowerCase();
    if (/(cisa\.gov|ncsc\.gov\.uk|cert\.europa\.eu|cert\.ssi\.gouv\.fr|ncsc\.nl|cyber\.gov\.au|ncsc\.govt\.nz|jpcert\.or\.jp|cert\.lv|ncsc\.admin\.ch|acn\.gov\.it|cyber\.gc\.ca)/.test(ref))
      return { role: "security", reader: null, source: "guess:advisory", reason: "a government security advisory", borrowed: false };
    if (/\b8\.\d+\.\d+\b|\bfpm\b|mod_php/.test(q))
      return { role: "engineer", reader: null, source: "guess:search-version", reason: "a search for a PHP version", borrowed: false };
    if (/(openwall\.com|seclists\.org|github\.com\/advisories)/.test(ref))
      return { role: "researcher", reader: null, source: "guess:archive", reason: "a mailing-list archive", borrowed: false };
    if (ctx.isNewsReferrer)
      return { role: "general", reader: null, source: "guess:news", reason: "a news article", borrowed: false };
    return { role: roles["default"], reader: null, source: "default", reason: null, borrowed: false };
  }

  /* ---------- 2. Which moment this is ---------- */
  var DEFAULT_T = { sessionGapMinutes: 30, sameVisitMinutes: 60, catchUpDays: 7, catchUpChanges: 20, askAtMost: 2, switchedToastSeconds: 6 };

  // Is this load the start of a new visit, and from when do changes count?
  // Call it first, count the role's changes after `since`, then call momentFrom.
  // On a new visit the caller then sets record.lastVisit = previous lastActive and visits += 1.
  function visitStart(record, now, t) {
    t = t || DEFAULT_T;
    if (!record) return { newVisit: true, since: null };
    var newVisit = (+now - +new Date(record.lastActive)) >= t.sessionGapMinutes * 60000;
    return { newVisit: newVisit, since: newVisit ? record.lastActive : record.lastVisit };
  }

  // ctx: { record|null (as stored before this load), session: {shared?, asOf?, switchedAt?}, now: Date,
  //        changesForRole: changes for the role after visitStart().since, liveChanges: n }
  function momentFrom(ctx, t) {
    t = t || DEFAULT_T;
    var s = ctx.session || {}, r = ctx.record, now = +ctx.now, min = 60000;
    var n = ctx.changesForRole || 0;
    if (s.shared) return "shared";
    if (s.asOf) return "past";
    if (!r) return "first";
    if (s.switchedAt && now - +new Date(s.switchedAt) < t.switchedToastSeconds * 1000) return "switched";
    if (ctx.liveChanges > 0) return "live";
    var v = visitStart(r, ctx.now, t);
    var visitNo = v.newVisit ? r.visits + 1 : r.visits;
    if (!r.confirmed && visitNo === 1) return "first";              // the first visit, still unanswered, on every page
    if (!r.confirmed && visitNo <= t.askAtMost) return "second";     // asked once more, then never
    var awayDays = (now - +new Date(v.since)) / (24 * 60 * min);
    if (n > t.catchUpChanges || (n > 0 && awayDays >= t.catchUpDays)) return "long";
    if (n > 0) return "week";                                       // stays until Show me / Mark as seen
    if (!v.newVisit) return "reading";
    var sinceActive = now - +new Date(r.lastActive);
    if (sinceActive < t.sameVisitMinutes * min) return "hour";
    var a = new Date(r.lastActive), b = new Date(now);
    if (a.getUTCFullYear() === b.getUTCFullYear() && a.getUTCMonth() === b.getUTCMonth() && a.getUTCDate() === b.getUTCDate()) return "sameday";
    return "reading";
  }

  /* ---------- 3. What the line says ---------- */
  // state: { role, reader?, depth?, moment, page, pageTitle?, pageIsFor? [roles], gatePassed?,
  //          firstReason?, changes? [[tag,text]], since, sinceShort, lastTime, asOf, asOfShort,
  //          days, count, ownRole?, sharedRole? }
  function computeLine(state, roles, copy) {
    var R = roles.roles, T = copy.templates, PL = copy.pageLines;
    var role = state.role, who = R[role];
    var dflt = chooseDepth(role, state.reader, null, roles);
    var depth = state.depth || dflt;
    var depthLabel = roles.depths[depth].label;
    var changes = state.changes || copy.sampleChanges[role] || [];
    var n = changes.length;
    var others = roles.order.filter(function (x) { return x !== role; }).map(function (x) { return R[x].name; }).join(" · ");
    var pageLines = PL[state.page] || PL.untagged;
    var vars = {
      name: who.name + (depth !== dflt ? " · " + depthLabel : ""),
      as: who.as, forAs: role === "everything" ? "for you" : "for " + who.as,
      others: others, n: n, changes: n === 1 ? "change" : "changes",
      since: state.since || "Thursday at 18:40", sinceShort: state.sinceShort || "yesterday",
      lastTime: state.lastTime || "09:15", asOf: state.asOf || "Thursday at 18:40", asOfShort: state.asOfShort || "Thu",
      days: state.days || "[10]", count: state.count || "[46]",
      countChanges: (state.count || "[46]") + (state.count === 1 ? " change" : " changes"),
      reason: state.firstReason || "", firstPart: who.firstPart, depthLower: depthLabel.toLowerCase(),
      pageTitle: state.pageTitle || "", ownName: R[state.ownRole || roles["default"]].name
    };
    vars.pageLine = fill(pageLines[role] || pageLines._ || "", vars);

    var key, line = { items: [], actions: [], others: "", picture: null };
    var isTeam = state.pageIsFor && state.pageIsFor.indexOf(role) < 0 && !state.gatePassed;

    if (isTeam) key = "gate";
    else key = state.moment;
    var tpl = T[key] || T.reading;

    line.rule = tpl.rule; line.key = key; line.tone = tpl.tone;
    line.size = tpl.size === "panel-on-front-else-open" ? (state.page === "front" ? "panel" : "open") : tpl.size;
    line.dot = tpl.dot === "amber-if-first-else-orange" ? (state.moment === "first" ? "amber" : "orange") : tpl.dot;
    line.chip = fill(tpl.chip, vars);
    line.actions = (tpl.actions || []).map(function (a) { return fill(a, vars); });
    line.text = fill(tpl.text, vars);
    line.lead = fill(tpl.lead, vars);

    if (key === "shared") {
      var sv = state.sharedRole || role;
      vars.sharedName = R[sv].name;
      line.chip = fill(tpl.chip, vars); line.lead = fill(tpl.lead, vars); line.text = fill(tpl.text, vars);
    }
    if (key === "past") line.picture = "dates";
    if (key === "first") {
      line.lead = role === "everything" ? tpl.leadEverything : fill(tpl.lead, vars);
      line.text = vars.reason ? fill(tpl.textGuess, vars) : tpl.textDefault;
      if (state.page !== "front") line.items = [[tpl.itemOnInnerPage, vars.pageLine]];
      line.others = fill(tpl.others, vars);
    }
    if (key === "second") {
      line.lead = role === "everything" ? tpl.leadEverything : fill(tpl.lead, vars);
      line.items = changes.slice(0, tpl.items);
      if (n === 0) { line.text = fill(tpl.textNothingNew, vars); line.actions = line.actions.slice(0, 1); line.chip = vars.name; }
      line.others = fill(tpl.others, vars);
    }
    if (key === "live") line.text = state.page === "front" ? tpl.textFront : tpl.textOther;
    if (key === "week") { line.text = state.page === "front" ? tpl.textFront : tpl.textOther; line.items = changes.slice(0, tpl.items); }
    if (key === "switched") line.lead = role === "everything" ? tpl.leadEverything : fill(depth !== dflt ? tpl.leadDepth : tpl.lead, vars);
    if (key === "reading" || key === "sameday" || key === "hour") {
      if (key === "hour") { line.rule = 7; line.lead = ""; }
      line.text = vars.pageLine;
    }
    if (!line.picture && line.tone === "calm" && copy.pictures[state.page]) line.picture = state.page;
    return line;
  }

  return { fill: fill, chooseDepth: chooseDepth, startingRole: startingRole, visitStart: visitStart, momentFrom: momentFrom, computeLine: computeLine };
});
