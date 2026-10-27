/* The vault register, live: every agent's register (the vaults it made, the keys it holds, by vault ID and kind of key,
   never a key) read from the team repository's records when the page opens (records/index/registers.json, written by
   the team site's deploy). The build's rule holds here too: a row whose id is not a bare vault id, or whose key is not
   a kind of key, is never drawn (the team gate refuses it at push time; this is the second lock). Draws the build's
   markup (build.py: build_vault_register) into data-live="vault-register"; what the build drew stays when the fetch
   fails. Needs assets/live/live.js. */
(function () {
  'use strict';
  var L = window.P2S_LIVE, box = document.querySelector('[data-live="vault-register"]');
  if (!L || !box) return;
  var el = L.el, ID = /^[0-9a-z]{8}$/, KINDS = ['vault key', 'read key', 'append token'];
  var links = {};                                   // the member links the build drew, by agent address
  box.querySelectorAll('h3 a').forEach(function (a) { links[a.textContent] = a.getAttribute('href'); });
  var sealed = function (s) { return String(s == null ? '' : s); };   // the build shows the date or the words as written
  L.json('records/index/registers.json').then(function (d) {
    var regs = (d && Array.isArray(d.registers)) ? d.registers.slice() : null;
    if (!regs) return;
    regs.sort(function (a, b) { return (a.agent !== 'conductor@php.newsroom') - (b.agent !== 'conductor@php.newsroom') || String(a.agent).localeCompare(String(b.agent)); });
    var out = [], held = 0, refused = 0;
    regs.forEach(function (r) {
      var ok = function (v) { var good = v && ID.test(String(v.id)); if (!good) refused++; return good; };
      var vaults = (r.vaults || []).filter(ok), holds = (r.holds || []).filter(function (h) { return ok(h) && KINDS.indexOf(h.key) >= 0; });
      held += holds.length;
      var name = links[r.agent] ? el('a', { href: links[r.agent] }, [r.agent]) : document.createTextNode(String(r.agent || ''));
      var rows = vaults.map(function (v) { return [[el('code', {}, [v.id])], v.what || '', v.created || '', sealed(v.key_sealed_to_root)]; });
      var hrows = holds.map(function (h) { return [[el('code', {}, [h.id])], h.key, h.from || '', h.since || '']; });
      out.push(el('section', { class: 'vcard' }, [el('h3', {}, [name, ' ', el('span', { class: 'small' }, [vaults.length + ' vault' + (vaults.length !== 1 ? 's' : '') + ' made'])]),
        L.table(['Vault ID', 'What it holds', 'Created', 'Key sealed to the root'], rows),
        hrows.length ? el('div', {}, [el('h4', {}, ['Keys it holds']), L.table(['Vault ID', 'Kind of key', 'From', 'Since'], hrows)])
                     : el('p', { class: 'small' }, [el('b', {}, ['Keys it holds:']), ' not recorded yet.']),
        el('p', { class: 'small' }, [r.note || ''])]));
    });
    L.fill(box, out);
    L.stamp(box, regs.length + ' registers from records/registers/ in the team repository' + (refused ? '; ' + refused + ' row(s) not drawn: not a bare vault id' : ''));
  }).catch(function () { /* the register as built stays */ });
})();
