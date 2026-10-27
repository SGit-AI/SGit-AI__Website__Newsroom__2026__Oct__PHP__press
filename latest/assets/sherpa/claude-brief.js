// The brief for your own assistant (sherpa@php.newsroom): a Copy button on /sherpa/for-your-claude/.
// It copies the text of the page's own brief (textContent, never markup) to the clipboard; nothing is read from anywhere
// else and nothing is sent.
(function () {
  var brief = document.getElementById('claude-brief'), button = document.getElementById('claude-copy'), note = document.getElementById('claude-copied');
  if (!brief || !button || !note) return;
  button.hidden = false;
  function fallback() {
    var range = document.createRange(); range.selectNodeContents(brief);
    var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
    var ok = false; try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    note.textContent = ok ? 'Copied. Paste it into a new conversation with your assistant.' : 'The brief is selected: copy it with your keyboard, then paste it into a new conversation with your assistant.';
  }
  button.addEventListener('click', function () {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(brief.textContent).then(function () { note.textContent = 'Copied. Paste it into a new conversation with your assistant.'; }, fallback);
    } else fallback();
  });
})();
