// php.oct.2026.newsroom.sgit.ai: before and after, in an article (the !slider block of render_article).
//
// Each stage holds the old screenshot and the new one, the same size. Without this script they show one above the
// other. With it they sit on top of each other and a slider moves between them: Fade dissolves the new over the old,
// Wipe reveals the new from the left, up to a line you drag. Before and After jump to either end; the arrow keys move
// the slider like any range input.
(function () {
  'use strict';
  function el(tag, attrs, text) { var e = document.createElement(tag); for (var k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; return e; }
  document.querySelectorAll('[data-ba]').forEach(function (stage, n) {
    var oldImg = stage.querySelector('img.ba-old'), newImg = stage.querySelector('img.ba-new'), ctl = stage.parentNode.querySelector('[data-ba-ctl]');
    if (!oldImg || !newImg || !ctl) return;
    var mode = 'fade', line = el('span', { class: 'ba-line', 'aria-hidden': 'true' });
    var range = el('input', { type: 'range', min: '0', max: '100', value: '50', 'aria-label': 'Before to after' });
    var before = el('button', { type: 'button' }, ctl.getAttribute('data-left') || 'Before'), after = el('button', { type: 'button' }, ctl.getAttribute('data-right') || 'After');
    var fade = el('button', { type: 'button', 'aria-pressed': 'true' }, 'Fade'), wipe = el('button', { type: 'button', 'aria-pressed': 'false' }, 'Wipe');
    function apply() {
      var v = +range.value;
      if (mode === 'fade') { newImg.style.opacity = String(v / 100); newImg.style.clipPath = ''; }
      else { newImg.style.opacity = '1'; newImg.style.clipPath = 'inset(0 ' + (100 - v) + '% 0 0)'; line.style.left = v + '%'; }
      stage.classList.toggle('ba-wipe', mode === 'wipe');
      range.setAttribute('aria-valuetext', v === 0 ? 'before' : v === 100 ? 'after' : v + '% after');
    }
    range.addEventListener('input', apply);
    before.addEventListener('click', function () { range.value = 0; apply(); });
    after.addEventListener('click', function () { range.value = 100; apply(); });
    fade.addEventListener('click', function () { mode = 'fade'; fade.setAttribute('aria-pressed', 'true'); wipe.setAttribute('aria-pressed', 'false'); apply(); });
    wipe.addEventListener('click', function () { mode = 'wipe'; wipe.setAttribute('aria-pressed', 'true'); fade.setAttribute('aria-pressed', 'false'); apply(); });
    // in wipe mode, a drag across the picture moves the line
    var drag = false;
    function at(e) { var r = stage.getBoundingClientRect(); range.value = Math.round(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * 100); apply(); }
    stage.addEventListener('pointerdown', function (e) { if (mode !== 'wipe') return; drag = true; stage.setPointerCapture(e.pointerId); at(e); });
    stage.addEventListener('pointermove', function (e) { if (drag) at(e); });
    stage.addEventListener('pointerup', function () { drag = false; });
    ctl.appendChild(before); ctl.appendChild(range); ctl.appendChild(after); ctl.appendChild(fade); ctl.appendChild(wipe);
    stage.appendChild(line); stage.classList.add('ba-live'); ctl.classList.add('ba-live');
    apply();
  });
})();
