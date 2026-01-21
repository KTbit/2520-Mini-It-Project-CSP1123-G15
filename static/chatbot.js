(function () {
  const STORAGE_KEY = "recipe_finder_chat_history_v1";

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

  function loadHistory() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveHistory(history) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (e) {}
  }

  function addMsg(role, text, persist = true) {
    const wrapper = document.createElement('div');
    wrapper.className = 'cb-msg cb-' + role;
    wrapper.innerHTML = '<div class="cb-bubble">' + escapeHtml(text) + '</div>';
    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;

    if (persist) {
      const history = loadHistory();
      history.push({ role, text, ts: Date.now() });
      saveHistory(history);
    }
    return wrapper;
  }

  function renderHistory() {
    const history = loadHistory();
    if (!history.length) return;
    for (const m of history) addMsg(m.role, m.text, false);
  }

  // Render history on page load
  renderHistory();

  // NOTE: CSS uses `.cb-panel.cb-open { display: flex; ... }`
  // so we toggle `cb-open` (not `show`).
  toggleBtn.addEventListener('click', () => {
    panel.classList.toggle('cb-open');
    toggleBtn.setAttribute('aria-expanded', panel.classList.contains('cb-open') ? 'true' : 'false');
    if (panel.classList.contains('cb-open')) {
      input.focus();
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      panel.classList.remove('cb-open');
      toggleBtn.setAttribute('aria-expanded', 'false');
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = (input.value || '').trim();
    if (!text) return;

    addMsg('user', text);
    input.value = '';
    input.focus();

    // temporary "typing" message without persisting
    const typing = addMsg('bot', 'Typing...', false);

    try {
      const res = await fetch('/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });

      if (!res.ok) {
        typing.querySelector('.cb-bubble').textContent = 'Sorry — something went wrong.';
        // persist error as bot message
        const history = loadHistory();
        history.push({ role: 'bot', text: 'Sorry — something went wrong.', ts: Date.now() });
        saveHistory(history);
        return;
      }

      const data = await res.json();
      const reply = (data && data.reply) ? data.reply : '...';
      typing.querySelector('.cb-bubble').textContent = reply;

      const history = loadHistory();
      history.push({ role: 'bot', text: reply, ts: Date.now() });
      saveHistory(history);
    } catch (err) {
      typing.querySelector('.cb-bubble').textContent = 'Network error — please try again.';
      const history = loadHistory();
      history.push({ role: 'bot', text: 'Network error — please try again.', ts: Date.now() });
      saveHistory(history);
    }
  });
})();