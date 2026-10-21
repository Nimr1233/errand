// The chat box for your site. Add one line before </body>:
//   <script src="helper.js" data-worker="https://errand-helper.<you>.workers.dev"></script>
// Visitors are told, before they type, that answers come from Google's Gemini, that chats may be read
// by Google's reviewers, and that the helper is for adults (Gemini API terms).
(() => {
  const worker = document.currentScript.dataset.worker;
  const box = document.createElement('div');
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-label', 'Site helper');
  box.style.cssText = 'position:fixed;right:16px;bottom:16px;width:min(320px,calc(100vw - 32px));font:15px system-ui;' +
    'background:#fff;color:#111;border:1px solid #888;border-radius:10px;padding:12px;z-index:99999;display:none';
  const note = document.createElement('p');
  note.textContent = 'Answers come from Google Gemini. Chats may be read by Google\'s reviewers. Please don\'t type ' +
    'personal details. For adults (18+) only.';
  note.style.cssText = 'margin:0 0 8px;font-size:13px';
  const log = document.createElement('div');
  log.setAttribute('aria-live', 'polite');
  const form = document.createElement('form');
  const input = document.createElement('input');
  input.setAttribute('aria-label', 'Your question');
  input.style.cssText = 'width:100%;min-height:40px;margin-top:8px;box-sizing:border-box';
  form.append(input);
  box.append(note, log, form);
  const open = document.createElement('button');
  open.type = 'button';
  open.textContent = 'Ask';
  open.style.cssText = 'position:fixed;right:16px;bottom:16px;min-height:44px;padding:0 18px;z-index:99998';
  open.onclick = () => { box.style.display = 'block'; open.style.display = 'none'; input.focus(); };
  form.onsubmit = async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    input.value = '';
    const line = (who, text) => { const p = document.createElement('p'); p.textContent = who + ': ' + text; log.append(p); };
    line('You', q);
    try {
      const r = await fetch(worker + '/ask', {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({question: q})});
      const d = await r.json();
      line('Helper', d.answer || d.error);
    } catch { line('Helper', 'could not answer right now'); }
  };
  document.body.append(open, box);
})();
