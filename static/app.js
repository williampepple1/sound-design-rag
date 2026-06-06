/* ── Sound Design RAG — Chat UI Logic ───────────── */

const messages = document.getElementById('messages');
const welcome = document.getElementById('welcome');
const form = document.getElementById('query-form');
const input = document.getElementById('query-input');
const sendBtn = document.getElementById('send-btn');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const sourcesList = document.getElementById('sources-list');
const clearBtn = document.getElementById('btn-clear');

let isLoading = false;

/* ── Init ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
    input.focus();
    const status = await fetchStatus();
    updateStatusUI(status);
    if (status.sources?.length) renderSources(status.sources, status.documents);
});

/* ── Status ────────────────────────────────────────── */
async function fetchStatus() {
    try {
        const res = await fetch('/status');
        return await res.json();
    } catch {
        statusDot.className = 'status-dot dot-warn';
        statusText.textContent = 'offline';
        return { documents: 0, sources: [], ready: false };
    }
}

function updateStatusUI(s) {
    if (s.ready) {
        statusDot.className = 'status-dot dot-ok';
        statusText.textContent = `${s.documents} chunks · ${s.sources.length} books`;
    } else {
        statusDot.className = 'status-dot dot-warn';
        statusText.textContent = s.documents > 0 ? `${s.documents} docs` : 'empty';
    }
}

function renderSources(sources, total) {
    const iconMap = {
        'audio mixing cookbook': '📘',
        'mixing secrets': '📗',
        'mastering guide': '📕',
        'fviimusic tips': '📙',
    };
    sourcesList.innerHTML = sources.map(s => {
        const key = Object.keys(iconMap).find(k => s.toLowerCase().includes(k));
        const icon = iconMap[key] || '📄';
        return `<div class="source-item"><span class="source-icon">${icon}</span><span class="source-name">${s}</span></div>`;
    }).join('');
}

/* ── Submit ────────────────────────────────────────── */
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q || isLoading) return;
    input.value = '';
    addMsg(q, 'user');
    hideWelcome();
    setLoading(true);
    sendBtn.disabled = true;

    const typingId = addTyping();

    try {
        const res = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: q, n_results: 5 }),
        });
        removeTyping(typingId);

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
            addMsg(err.detail || 'Something went wrong.', 'error');
            return;
        }

        const data = await res.json();
        addAssistantMsg(data.answer, data.sources);
    } catch (err) {
        removeTyping(typingId);
        addMsg('Network error — is the server running?', 'error');
    } finally {
        setLoading(false);
        sendBtn.disabled = false;
        input.focus();
    }
});

/* ── Suggestions ───────────────────────────────────── */
document.getElementById('suggestions').addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (chip) {
        input.value = chip.dataset.q;
        form.requestSubmit();
    }
});

/* ── Clear ─────────────────────────────────────────── */
clearBtn.addEventListener('click', () => {
    // Remove all messages except welcome
    const msgs = messages.querySelectorAll('.msg');
    msgs.forEach(m => m.remove());
    welcome.style.display = 'flex';
    input.focus();
});

/* ── Messages ──────────────────────────────────────── */
function addMsg(text, role) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = role === 'user' ? '👤' : role === 'error' ? '⚠️' : '🤖';

    const body = document.createElement('div');
    body.className = 'msg-body';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.textContent = text;

    body.appendChild(bubble);
    div.append(avatar, body);
    messages.appendChild(div);
    scrollDown();
}

function addAssistantMsg(text, sources) {
    const div = document.createElement('div');
    div.className = 'msg assistant';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const body = document.createElement('div');
    body.className = 'msg-body';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerHTML = renderMarkdown(text);

    if (sources && sources.length) {
        const sdiv = document.createElement('div');
        sdiv.className = 'msg-sources';
        sources.forEach(s => {
            const span = document.createElement('span');
            span.className = 'msg-source';
            span.textContent = `${s.source_file} (p.${s.page_num})`;
            sdiv.appendChild(span);
        });
        bubble.appendChild(sdiv);
    }

    body.appendChild(bubble);
    div.append(avatar, body);
    messages.appendChild(div);
    scrollDown();
}

function addTyping() {
    const div = document.createElement('div');
    div.className = 'msg assistant typing';
    const id = 'typing-' + Date.now();
    div.id = id;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const body = document.createElement('div');
    body.className = 'msg-body';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('span');
        dot.className = 'typing-dot';
        bubble.appendChild(dot);
    }

    body.appendChild(bubble);
    div.append(avatar, body);
    messages.appendChild(div);
    scrollDown();
    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

/* ── Helpers ───────────────────────────────────────── */
function hideWelcome() { welcome.style.display = 'none'; }
function setLoading(v) { isLoading = v; }
function scrollDown() { messages.scrollTop = messages.scrollHeight; }

/* ── Markdown Renderer ─────────────────────────────── */
function renderMarkdown(text) {
    let t = text;
    // Code blocks
    t = t.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Italic
    t = t.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Bullet lists
    t = t.replace(/^[\s]*[-*]\s+(.+)$/gm, '<li>$1</li>');
    t = t.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    // Numbered lists
    t = t.replace(/^[\s]*\d+\.\s+(.+)$/gm, '<li>$1</li>');
    // Paragraphs
    t = t.replace(/\n\n/g, '</p><p>');
    t = t.replace(/\n/g, '<br>');
    if (!t.startsWith('<')) t = '<p>' + t + '</p>';
    return t;
}

/* ── Input validation ──────────────────────────────── */
input.addEventListener('input', () => {
    sendBtn.disabled = !input.value.trim();
});
