/* ElectWise — app.js */
'use strict';

// ── CONFIG ────────────────────────────────────────────────────────────────────
let API_KEY = localStorage.getItem('ew_api_key') || '';
let BACKEND = localStorage.getItem('ew_backend') || 'http://localhost:8000';
let chatHistory = [];
let fcCards = [];
let fcIndex = 0;
let quizData = [];
let quizAnswers = {};

// ── INIT ──────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  initSettings();
  loadTimeline();
  // restore last tab
  const last = localStorage.getItem('ew_tab') || 'timeline';
  switchTab(last);
});

// ── SETTINGS ─────────────────────────────────────────────────────────────────
function initSettings() {
  const inp = document.getElementById('api-key-input');
  const urlInp = document.getElementById('backend-url-input');
  if (inp && API_KEY) inp.value = API_KEY;
  if (urlInp) urlInp.value = BACKEND;
  updateKeyStatus();
}

function toggleSettings() {
  const drawer = document.getElementById('settings-drawer');
  const overlay = document.getElementById('settings-overlay');
  drawer.classList.toggle('open');
  overlay.classList.toggle('open');
}

function saveKey() {
  const val = document.getElementById('api-key-input').value.trim();
  if (!val) { setKeyStatus('Please enter a valid key.', false); return; }
  API_KEY = val;
  localStorage.setItem('ew_api_key', val);
  setKeyStatus('✓ API key saved!', true);
}

function saveBackendUrl() {
  const val = document.getElementById('backend-url-input').value.trim().replace(/\/$/, '');
  BACKEND = val || 'http://localhost:8000';
  localStorage.setItem('ew_backend', BACKEND);
  setKeyStatus('✓ Backend URL saved!', true);
}

function setKeyStatus(msg, ok) {
  const el = document.getElementById('key-status');
  el.textContent = msg;
  el.className = 'key-status ' + (ok ? 'ok' : 'err');
}

function updateKeyStatus() {
  if (API_KEY) setKeyStatus('✓ API key loaded from storage', true);
}

// ── TAB SWITCHING ─────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById('tab-' + tab);
  if (panel) panel.classList.add('active');
  const btn = document.querySelector(`[data-tab="${tab}"]`);
  if (btn) btn.classList.add('active');
  localStorage.setItem('ew_tab', tab);
}

// ── API HELPER ────────────────────────────────────────────────────────────────
async function apiPost(path, body) {
  const payload = { ...body, api_key: API_KEY || undefined };
  const res = await fetch(BACKEND + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

async function apiGet(path) {
  const res = await fetch(BACKEND + path);
  if (!res.ok) throw new Error('Request failed');
  return res.json();
}

// ── TIMELINE ──────────────────────────────────────────────────────────────────
async function loadTimeline() {
  try {
    const data = await apiGet('/api/timeline');
    renderTimeline(data.timeline);
  } catch (e) {
    document.getElementById('timeline-track').innerHTML =
      `<p style="color:var(--danger);padding:1rem">⚠️ Could not load timeline. Is the backend running? <br><small>${e.message}</small></p>`;
  }
}

function renderTimeline(steps) {
  const track = document.getElementById('timeline-track');
  track.innerHTML = steps.map((s, i) => `
    <div class="tl-item" id="tl-${s.id}" onclick="toggleTl(${s.id})">
      <div class="tl-left">
        <div class="tl-bubble" style="border-color:${s.color}20">${s.icon}</div>
        ${i < steps.length - 1 ? '<div class="tl-connector"></div>' : ''}
      </div>
      <div class="tl-body">
        <div class="tl-phase-tag" style="color:${s.color}">${s.phase}</div>
        <div class="tl-title">${s.title}</div>
        <div class="tl-subtitle">${s.subtitle}</div>
        <div class="tl-deadline">🗓️ ${s.deadline}</div>
        <div class="tl-detail-box">
          <p>${s.detail}</p>
          <ul class="tl-tips">${s.tips.map(t => `<li>${t}</li>`).join('')}</ul>
        </div>
      </div>
    </div>
  `).join('');
}

let openTl = null;
function toggleTl(id) {
  if (openTl === id) {
    document.getElementById('tl-' + id)?.classList.remove('expanded');
    openTl = null;
    return;
  }
  if (openTl) document.getElementById('tl-' + openTl)?.classList.remove('expanded');
  openTl = id;
  const el = document.getElementById('tl-' + id);
  el?.classList.add('expanded');
  el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── FLASHCARDS ────────────────────────────────────────────────────────────────
function setFcTopic(t) {
  document.getElementById('fc-topic').value = t;
}

async function generateFlashcards() {
  const topic = document.getElementById('fc-topic').value.trim() || 'general election process';
  const btn = document.getElementById('fc-gen-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating…';

  try {
    const data = await apiPost('/api/flashcards', { topic, count: 6 });
    fcCards = data.flashcards || [];
    fcIndex = 0;
    renderFcCard();
    renderFcProgress();
    document.getElementById('fc-nav').style.display = 'flex';
  } catch (e) {
    showFcError(e.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '✨ Generate Cards';
  }
}

function renderFcCard() {
  if (!fcCards.length) return;
  const card = fcCards[fcIndex];
  const wrapper = document.getElementById('fc-card-wrapper');
  wrapper.innerHTML = `
    <div class="flashcard" id="fc-card" onclick="flipCard()">
      <div class="fc-inner">
        <div class="fc-front">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span class="fc-cat">${card.category || 'Election'}</span>
            <span class="fc-diff ${card.difficulty || 'beginner'}">${card.difficulty || 'beginner'}</span>
          </div>
          <div class="fc-emoji">${card.emoji || '🗳️'}</div>
          <div class="fc-question">${card.question}</div>
          <div class="fc-hint">Tap to reveal answer</div>
        </div>
        <div class="fc-back">
          <span class="fc-cat">${card.category || 'Election'}</span>
          <div class="fc-answer">${card.answer}</div>
          ${card.fact ? `<div class="fc-fact">💡 <strong>Did you know?</strong> ${card.fact}</div>` : ''}
          <div class="fc-hint">Tap to flip back</div>
        </div>
      </div>
    </div>
  `;
  document.getElementById('fc-counter').textContent = `${fcIndex + 1} / ${fcCards.length}`;
  renderFcProgress();
}

function flipCard() {
  document.getElementById('fc-card')?.classList.toggle('flipped');
}

function fcPrev() {
  if (fcIndex > 0) { fcIndex--; renderFcCard(); }
}

function fcNext() {
  if (fcIndex < fcCards.length - 1) { fcIndex++; renderFcCard(); }
}

function renderFcProgress() {
  const bar = document.getElementById('fc-progress');
  bar.innerHTML = fcCards.map((_, i) =>
    `<div class="fc-dot ${i === fcIndex ? 'active' : i < fcIndex ? 'seen' : ''}"></div>`
  ).join('');
}

function showFcError(msg) {
  document.getElementById('fc-card-wrapper').innerHTML = `
    <div class="fc-empty-state">
      <div class="empty-icon">⚠️</div>
      <h3>Could not generate cards</h3>
      <p>${msg}</p>
      ${!API_KEY ? '<p style="margin-top:.5rem;color:var(--accent)">Please add your Gemini API key in ⚙️ Settings.</p>' : ''}
    </div>`;
}

// ── QUIZ ──────────────────────────────────────────────────────────────────────
function setQuizTopic(t) {
  document.getElementById('quiz-topic').value = t;
}

async function generateQuiz() {
  const topic = document.getElementById('quiz-topic').value.trim() || 'general election process';
  const btn = document.getElementById('quiz-gen-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating…';
  quizAnswers = {};

  try {
    const data = await apiPost('/api/quiz', { topic });
    quizData = data.questions || [];
    renderQuiz();
  } catch (e) {
    document.getElementById('quiz-area').innerHTML =
      `<div class="fc-empty-state"><div class="empty-icon">⚠️</div><h3>Error</h3><p>${e.message}</p>${!API_KEY ? '<p style="color:var(--accent)">Add your Gemini API key in ⚙️ Settings.</p>' : ''}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '🧠 Start Quiz';
  }
}

function renderQuiz() {
  const area = document.getElementById('quiz-area');
  const letters = ['A', 'B', 'C', 'D'];
  area.innerHTML = quizData.map((q, qi) => `
    <div class="quiz-q" id="quiz-q-${qi}">
      <div class="quiz-q-header">
        <div class="quiz-num">${qi + 1}</div>
        <div class="quiz-text">${q.emoji || '❓'} ${q.question}</div>
      </div>
      <div class="quiz-options">
        ${q.options.map((opt, oi) => `
          <button class="quiz-opt" id="qopt-${qi}-${oi}" onclick="answerQuiz(${qi},${oi})">
            <span class="opt-letter">${letters[oi]}</span> ${opt}
          </button>
        `).join('')}
      </div>
      <div class="quiz-explanation" id="quiz-exp-${qi}">${q.explanation}</div>
    </div>
  `).join('') + `<div id="quiz-score-wrap"></div>`;
}

function answerQuiz(qi, chosen) {
  if (quizAnswers[qi] !== undefined) return;
  quizAnswers[qi] = chosen;
  const q = quizData[qi];
  const correct = q.correct;

  for (let i = 0; i < q.options.length; i++) {
    const btn = document.getElementById(`qopt-${qi}-${i}`);
    btn.disabled = true;
    if (i === correct) btn.classList.add('correct');
    else if (i === chosen) btn.classList.add('wrong');
  }
  document.getElementById(`quiz-exp-${qi}`).classList.add('visible');

  if (Object.keys(quizAnswers).length === quizData.length) {
    setTimeout(showQuizScore, 600);
  }
}

function showQuizScore() {
  const score = quizData.filter((q, i) => quizAnswers[i] === q.correct).length;
  const total = quizData.length;
  const pct = Math.round((score / total) * 100);
  const msg = pct === 100 ? '🎉 Perfect score!' : pct >= 60 ? '👍 Good job!' : '📚 Keep learning!';
  document.getElementById('quiz-score-wrap').innerHTML = `
    <div class="quiz-score">
      <div class="score-big" style="color:${pct>=60?'var(--success)':'var(--accent)'}">${score}/${total}</div>
      <div class="score-label">${msg} You answered ${score} of ${total} correctly (${pct}%).</div>
      <button class="retry-btn" onclick="generateQuiz()">🔄 New Quiz</button>
    </div>`;
  document.getElementById('quiz-score-wrap').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── CHAT ──────────────────────────────────────────────────────────────────────
function quickAsk(q) {
  switchTab('chat');
  document.getElementById('chat-input').value = q;
  setTimeout(sendChat, 100);
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  // Clear welcome screen on first message
  const welcome = document.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  addChatMsg('user', msg);
  chatHistory.push({ role: 'user', content: msg });

  const btn = document.getElementById('send-btn');
  btn.disabled = true;
  const typingId = showTyping();

  try {
    const data = await apiPost('/api/chat', { message: msg, history: chatHistory });
    removeTyping(typingId);
    const reply = data.reply || 'Sorry, I could not generate a response.';
    addChatMsg('ai', formatMarkdown(reply));
    chatHistory.push({ role: 'assistant', content: reply });
    if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
  } catch (e) {
    removeTyping(typingId);
    const errMsg = e.message.includes('API key')
      ? '⚠️ Please add your Gemini API key in ⚙️ Settings (top right).'
      : `⚠️ Error: ${e.message}`;
    addChatMsg('ai', errMsg);
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

function addChatMsg(role, html) {
  const wrap = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-msg ${role === 'user' ? 'user' : ''}`;
  div.innerHTML = `
    <div class="msg-avatar ${role === 'user' ? 'user-av' : 'ai-av'}">${role === 'user' ? '👤' : '🤖'}</div>
    <div class="msg-bubble">${html}</div>
  `;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
  return div;
}

function showTyping() {
  const wrap = document.getElementById('chat-messages');
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.className = 'chat-msg';
  div.id = id;
  div.innerHTML = `
    <div class="msg-avatar ai-av">🤖</div>
    <div class="msg-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>
  `;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
  return id;
}

function removeTyping(id) {
  document.getElementById(id)?.remove();
}

function formatMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^#{1,3}\s(.+)$/gm, '<strong>$1</strong>')
    .replace(/^\d+\.\s(.+)$/gm, (_, l) => `<li>${l}</li>`)
    .replace(/(<li>.*<\/li>)/gs, '<ol>$1</ol>')
    .replace(/^[-•]\s(.+)$/gm, (_, l) => `<li>${l}</li>`)
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}
