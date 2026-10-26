// Run: node --test assets/design/line/engine.test.mjs   (Node 18+)
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const L = require("./engine.js");
const roles = require("./roles.json");
const copy = require("./copy.json");
const T = require("./moments.json").thresholds;

const at = (s) => new Date(s);
const rec = (o) => Object.assign({ v: 2, role: "exec", reader: null, depth: "plain", source: "default", confirmed: true, asked: 1,
  firstVisit: "2026-10-23T09:02:00Z", lastVisit: "2026-10-23T18:40:00Z", lastActive: "2026-10-23T18:40:00Z", visits: 2, seen: {} }, o);

test("nothing known: Executive, by default", () => {
  const s = L.startingRole({ stored: null }, roles);
  assert.equal(s.role, "exec"); assert.equal(s.source, "default");
});
test("from a CERT advisory: Security, with the reason", () => {
  const s = L.startingRole({ stored: null, referrer: "https://www.cisa.gov/news-events/alerts/x" }, roles);
  assert.equal(s.role, "security"); assert.equal(s.reason, "a government security advisory");
});
test("a search with a PHP version: Engineer", () => {
  assert.equal(L.startingRole({ stored: null, searchTerms: "php 8.4.27 fpm" }, roles).role, "engineer");
});
test("a shared link names a reader: role from the reader, borrowed when a different view is saved", () => {
  const s = L.startingRole({ stored: rec({}), asParam: "comms" }, roles);
  assert.equal(s.role, "journalist"); assert.equal(s.reader, "comms"); assert.equal(s.borrowed, true);
  // a role id wins over a reader with the same id
  assert.equal(L.startingRole({ stored: null, asParam: "journalist" }, roles).reader, null);
});
test("a saved view wins over a guess", () => {
  assert.equal(L.startingRole({ stored: rec({ role: "researcher" }), referrer: "https://www.cisa.gov/" }, roles).role, "researcher");
});

test("moments: first, reading, second, week, long, hour, sameday", () => {
  assert.equal(L.momentFrom({ record: null, now: at("2026-10-24T08:00:00Z") }, T), "first");
  assert.equal(L.momentFrom({ record: rec({ lastActive: "2026-10-24T07:50:00Z" }), now: at("2026-10-24T08:00:00Z"), changesForRole: 0 }, T), "reading");
  // unseen changes stay in the line for the whole visit, until Show me / Mark as seen
  assert.equal(L.momentFrom({ record: rec({ lastActive: "2026-10-24T07:50:00Z" }), now: at("2026-10-24T08:00:00Z"), changesForRole: 3 }, T), "week");
  assert.equal(L.momentFrom({ record: rec({ confirmed: false, visits: 1, lastActive: "2026-10-24T07:55:00Z" }), now: at("2026-10-24T08:00:00Z") }, T), "first");
  assert.equal(L.momentFrom({ record: rec({ confirmed: false, visits: 1 }), now: at("2026-10-24T08:00:00Z"), changesForRole: 2 }, T), "second");
  assert.equal(L.momentFrom({ record: rec({ confirmed: false, visits: 2, lastActive: "2026-10-24T07:55:00Z" }), now: at("2026-10-24T08:00:00Z") }, T), "second");
  assert.equal(L.momentFrom({ record: rec({ confirmed: false, visits: 2 }), now: at("2026-10-24T08:00:00Z"), changesForRole: 2 }, T), "week");
  assert.equal(L.momentFrom({ record: rec({}), now: at("2026-10-24T08:00:00Z"), changesForRole: 3 }, T), "week");
  assert.equal(L.momentFrom({ record: rec({}), now: at("2026-11-03T08:00:00Z"), changesForRole: 3 }, T), "long");
  assert.equal(L.momentFrom({ record: rec({}), now: at("2026-10-24T08:00:00Z"), changesForRole: 25 }, T), "long");
  assert.equal(L.momentFrom({ record: rec({ lastActive: "2026-10-24T07:20:00Z" }), now: at("2026-10-24T08:00:00Z"), changesForRole: 0 }, T), "hour");
  assert.equal(L.momentFrom({ record: rec({ lastActive: "2026-10-24T09:15:00Z" }), now: at("2026-10-24T14:30:00Z"), changesForRole: 0 }, T), "sameday");
});
test("visitStart: a new visit after 30 idle minutes counts changes from the previous visit's end", () => {
  const r = rec({ lastVisit: "2026-10-22T10:00:00Z", lastActive: "2026-10-23T18:40:00Z" });
  assert.deepEqual(L.visitStart(r, at("2026-10-24T08:00:00Z"), T), { newVisit: true, since: "2026-10-23T18:40:00Z" });
  assert.deepEqual(L.visitStart(r, at("2026-10-23T18:50:00Z"), T), { newVisit: false, since: "2026-10-22T10:00:00Z" });
});
test("session state wins: shared, then past", () => {
  assert.equal(L.momentFrom({ record: rec({}), session: { shared: { role: "journalist" }, asOf: "2026-10-23T18:40:00Z" }, now: at("2026-10-24T08:00:00Z") }, T), "shared");
  assert.equal(L.momentFrom({ record: rec({}), session: { asOf: "2026-10-23T18:40:00Z" }, now: at("2026-10-24T08:00:00Z") }, T), "past");
});

test("first visit, front page: the panel, the default text, the six others", () => {
  const l = L.computeLine({ role: "exec", moment: "first", page: "front" }, roles, copy);
  assert.equal(l.size, "panel"); assert.equal(l.tone, "ask"); assert.equal(l.dot, "amber");
  assert.equal(l.lead, "You're viewing this as an Executive.");
  assert.match(l.text, /We start everyone here/);
  assert.equal(l.others.split(" · ").length, 6);
});
test("first visit guessed, on an inner page: open, with the reason and the page's line", () => {
  const l = L.computeLine({ role: "security", moment: "first", page: "agencies", firstReason: "a government security advisory" }, roles, copy);
  assert.equal(l.size, "open"); assert.equal(l.text, "You came from a government security advisory, so we started you here.");
  assert.equal(l.items[0][0], "This page"); assert.match(l.items[0][1], /2 say take offline/);
});
test("reading on: the page's line for the role, with the page's picture", () => {
  const l = L.computeLine({ role: "journalist", moment: "reading", page: "agencies" }, roles, copy);
  assert.equal(l.tone, "calm"); assert.equal(l.rule, 7); assert.equal(l.picture, "agencies"); assert.match(l.text, /Only 2 of 16/);
});
test("a role without its own line falls back to the page's general line", () => {
  assert.match(L.computeLine({ role: "researcher", moment: "reading", page: "agencies" }, roles, copy).text, /^16 agencies/);
});
test("back within a week: news, counted for the role, up to three items", () => {
  const l = L.computeLine({ role: "exec", moment: "week", page: "front" }, roles, copy);
  assert.equal(l.tone, "news"); assert.equal(l.lead, "Since Thursday at 18:40: 3 changes for an Executive."); assert.equal(l.items.length, 3);
});
test("a page not written for the role: the gate wins over everything", () => {
  const l = L.computeLine({ role: "exec", moment: "week", page: "console", pageIsFor: ["team"] }, roles, copy);
  assert.equal(l.rule, 1); assert.equal(l.tone, "gate"); assert.equal(l.text, "Nothing on it is hidden; it just isn't written for an Executive.");
  assert.equal(L.computeLine({ role: "exec", moment: "week", page: "console", pageIsFor: ["team"], gatePassed: true }, roles, copy).rule, 5);
});
test("depth changed from the default shows in the chip and the switch line", () => {
  const l = L.computeLine({ role: "exec", moment: "switched", page: "front", depth: "deep" }, roles, copy);
  assert.equal(l.chip, "Executive · Deep"); assert.equal(l.lead, "Now reading as an Executive, deep.");
});
test("shared view keeps the reader's own", () => {
  const l = L.computeLine({ role: "journalist", sharedRole: "journalist", ownRole: "exec", moment: "shared", page: "front" }, roles, copy);
  assert.equal(l.lead, "You're seeing the Journalist view from a shared link."); assert.equal(l.text, "Yours, Executive, is kept. This lasts for this visit only.");
});
test("Everything has its own wording", () => {
  assert.equal(L.computeLine({ role: "everything", moment: "first", page: "front" }, roles, copy).lead, "You're viewing everything, unfiltered.");
  assert.equal(L.computeLine({ role: "everything", moment: "switched", page: "front" }, roles, copy).lead, "Now showing everything, unfiltered.");
});
test("no placeholder is ever left in braces, for every role, moment and page", () => {
  const moments = ["first", "reading", "hour", "sameday", "second", "week", "long", "live", "switched", "shared", "past"];
  for (const r of roles.order) for (const m of moments) for (const p of ["front", "agencies", "numbers", "playbook", "other"]) {
    const l = L.computeLine({ role: r, moment: m, page: p, pageTitle: "The flaws", sharedRole: r }, roles, copy);
    const all = [l.chip, l.lead, l.text, l.others, ...l.actions, ...l.items.flat()].join(" ");
    assert.doesNotMatch(all, /\{\w+\}/, `${r}/${m}/${p}: ${all}`);
  }
});
test("every reader in data/personas.json maps to a role, and every role's readers exist", () => {
  for (const [id, r] of Object.entries(roles.roles)) for (const rd of r.readers) assert.equal(roles.readers[rd].role, id);
  assert.equal(Object.keys(roles.readers).length, 16);
});
