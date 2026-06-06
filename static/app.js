/* ── Sound Design RAG — Chat UI ─────────────────── */

const chat = document.getElementById('chat-container');
const messages = document.getElementById('messages');
const welcome = document.getElementById('welcome');
const form = document.getElementById('query-form');
const input = document.getElementById('query-input');
const sendBtn = document.getElementById('send-btn');
const badge = document.getElementById('status-badge');
const sourceCount = document.getElementById('source-count');

let isLoading = false;

/* ── Init ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
    const status = await fetchStatus();
    badge.textContent = status.ready ? 'ready' : 'empty';
    badge.className = 'badge ' + (status.ready ? 'ready' : 'empty');
    if (status.documents > 0) {
        sourceCount.textContent = `${status.documents} chunks from ${status.sources.length} books`;
    }
});

/* ── Status ────────────────────────────────────────── */
async function fetchStatus() {
    try {
        const res = await fetch('/status');
        return await res.json();
    } catch {
        badge.textContent = 'offline';
        badge.className = 'badge empty';
        return { documents: 0, sources: [], ready: false };
    }
}

/* ── Submit ────────────────────────────────────────── */
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q || isLoading) return;
    input.value = '';
    addMessage(q, 'user');
    hideWelcome();
    setLoading(true);

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
            addMessage(err.detail || 'Something went wrong.', 'error');
            return;
        }

        const data = await res.json();
        addAssistantMessage(data.answer, data.sources);
    } catch (err) {
        removeTyping(typingId);
        addMessage('Network error. Is the server running?', 'error');
    } finally {
        setLoading(false);
    }
});

/* ── Suggestions ───────────────────────────────────── */
document.getElementById('suggestions').addEventListener('click', (e) => {
    const chip = e.target.closest('.suggestion-chip');
    if (chip) {
        input.value = chip.dataset.q;
        form.requestSubmit();
    }
});

/* ── Messages ──────────────────────────────────────── */
function addMessage(text, role) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;

    div.append(avatar, bubble);
    messages.appendChild(div);
    scrollDown();
    return div;
}

function addAssistantMessage(text, sources) {
    const div = document.createElement('div');
    div.className = 'message assistant';

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    // Render markdown-like formatting
    bubble.innerHTML = renderMarkdown(text);

    if (sources && sources.length) {
        const src = document.createElement('div');
        src.className = 'sources';
        src.textContent = sources.map(s => `${s.source_file} (p.${s.page_num})`).join(' · ');
        bubble.appendChild(src);
    }

    div.append(avatar, bubble);
    messages.appendChild(div);
    scrollDown();
}

function addTyping() {
    const div = document.createElement('div');
    div.className = 'message assistant typing';
    div.id = 'typing-' + Date.now();

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('span');
        dot.className = 'dot';
        bubble.appendChild(dot);
    }

    div.append(avatar, bubble);
    messages.appendChild(div);
    scrollDown();
    return div.id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

/* ── Helpers ───────────────────────────────────────── */
function hideWelcome() { welcome.style.display = 'none'; }
function setLoading(v) { isLoading = v; sendBtn.disabled = v; input.disabled = v; }
function scrollDown() { chat.scrollTop = chat.scrollHeight; }

/* ── Simple Markdown Renderer ───────────────────────── */
function renderMarkdown(text) {
    // Code blocks
    text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Italic
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Bullet lists
    text = text.replace(/^[\s]*[-*]\s+(.+)$/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    // Numbered lists
    text = text.replace(/^[\s]*\d+\.\s+(.+)$/gm, '<li>$1</li>');
    // Paragraphs (double newlines)
    text = text.replace(/\n\n/g, '</p><p>');
    // Single newlines
    text = text.replace(/\n/g, '<br>');
    // Wrap in paragraphs if not already wrapped
    if (!text.startsWith('<')) {
        text = '<p>' + text + '</p>';
    }
    return text;
}
