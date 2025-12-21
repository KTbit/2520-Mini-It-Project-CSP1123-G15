(function () {
  const toggleBtn = document.getElementById('cb-toggle');
  const panel = document.getElementById('cb-panel');
  const closeBtn = document.getElementById('cb-close');
  const form = document.getElementById('cb-form');
  const input = document.getElementById('cb-input');
  const messages = document.getElementById('cb-messages');

  if (!toggleBtn || !panel || !form || !input || !messages) return;

  const escapeHtml = (s) => String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const render = (text) => {
    // very small formatter: **bold** + newlines
    let t = escapeHtml(text || '');
    t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    t = t.replace(/\n/g, '<br>');
    // make /recipes/123 clickable
    t = t.replace(/(\/recipes\/\d+)/g, '<a href="$1">$1</a>');
    return t;
  };

  const addMsg = (who, text) => {
    const item = document.createElement('div');
    item.className = 'cb-msg ' + (who === 'user' ? 'cb-user' : 'cb-bot');
    item.innerHTML = `<div class="cb-bubble">${render(text)}</div>`;
    messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
  };

  const setOpen = (open) => {
    panel.classList.toggle('cb-open', open);
    toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) setTimeout(() => input.focus(), 50);
  };

  toggleBtn.addEventListener('click', () => {
    const open = !panel.classList.contains('cb-open');
    setOpen(open);
    if (open && messages.childElementCount === 0) {
      addMsg('bot', 'Hi! I\'m RecipeBot. Type **help** for examples.');
    }
  });

  if (closeBtn) closeBtn.addEventListener('click', () => setOpen(false));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = (input.value || '').trim();
    if (!text) return;

    addMsg('user', text);
    input.value = '';

    try {
      const res = await fetch('/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });

      if (!res.ok) {
        addMsg('bot', 'Sorry — something went wrong.');
        return;
      }

      const data = await res.json();
      addMsg('bot', data.reply || '...');
    } catch (err) {
      addMsg('bot', 'Network error — please try again.');
    }
  });
})();
