/**
 * chat.js
 * Página de conversa com a Clara (chat.html).
 * Contrato da API mantido igual ao original:
 *   POST /api/session/init  { session_id, message }  → { reply }
 *   POST /api/chat          { session_id, message }  → { reply, fase }
 */

'use strict';

const API_BASE = 'https://nextia-production.up.railway.app';
const SESSION_KEY = 'clara_session_id';

const chatMessages    = document.getElementById('chatMessages');
const chatForm        = document.getElementById('chatForm');
const messageInput    = document.getElementById('messageInput');
const sendButton      = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');

let isLoading = false;

/* ───────────────────────────────────────────── */
/* Sessão                                        */
/* ───────────────────────────────────────────── */

// Gera um ID mesmo em navegadores sem crypto.randomUUID
function createId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

// localStorage pode falhar (modo privado, bloqueio de cookies)
function getSessionId() {
  try {
    let id = localStorage.getItem(SESSION_KEY);
    if (!id) {
      id = createId();
      localStorage.setItem(SESSION_KEY, id);
    }
    return id;
  } catch {
    return createId(); // sessão válida só enquanto a aba estiver aberta
  }
}

const sessionId = getSessionId();

/* ───────────────────────────────────────────── */
/* Interface                                     */
/* ───────────────────────────────────────────── */

function scrollToBottom() {
  if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Adiciona uma mensagem ao chat.
 * @param {string} content
 * @param {'ai'|'user'} role - classes usadas pelo chat.css
 */
function addMessage(content, role) {
  if (!chatMessages) return;

  const message = document.createElement('div');
  message.classList.add('message', role);
  message.textContent = content; // textContent evita injeção de HTML vindo da API

  chatMessages.appendChild(message);
  scrollToBottom();
}

function setLoading(state) {
  isLoading = state;

  if (messageInput) messageInput.disabled = state;
  if (sendButton) sendButton.disabled = state;
  typingIndicator?.classList.toggle('hidden', !state);
  chatMessages?.setAttribute('aria-busy', String(state));

  if (!state) messageInput?.focus();
}

function showLeadSuccess() {
  if (!chatMessages || chatMessages.querySelector('.lead-success')) return;

  const success = document.createElement('div');
  success.classList.add('lead-success');
  success.setAttribute('role', 'status');
  success.textContent = 'Informações recebidas. Nosso time vai entrar em contato em breve.';

  chatMessages.appendChild(success);
  scrollToBottom();
}

/* ───────────────────────────────────────────── */
/* API                                           */
/* ───────────────────────────────────────────── */

async function postJSON(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) throw new Error(`Erro ${response.status} em ${path}`);
  return response.json();
}

async function initSession() {
  try {
    setLoading(true);
    const data = await postJSON('/api/session/init', {
      session_id: sessionId,
      message: 'oi',
    });
    addMessage(data.reply, 'ai');
  } catch (error) {
    console.error('[chat.js]', error);
    addMessage(
      'Não consegui iniciar a conversa agora. Tente recarregar a página ou use o formulário de contato no site.',
      'ai'
    );
  } finally {
    setLoading(false);
  }
}

async function sendMessage(message) {
  try {
    setLoading(true);
    const data = await postJSON('/api/chat', {
      session_id: sessionId,
      message,
    });

    addMessage(data.reply, 'ai');
    if (data.fase === 'concluido') showLeadSuccess();
  } catch (error) {
    console.error('[chat.js]', error);
    addMessage('Desculpe, não consegui processar sua mensagem. Pode tentar de novo?', 'ai');
  } finally {
    setLoading(false);
  }
}

/* ───────────────────────────────────────────── */
/* Eventos                                       */
/* ───────────────────────────────────────────── */

chatForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (isLoading || !messageInput) return;

  const message = messageInput.value.trim();
  if (!message) return;

  addMessage(message, 'user');
  messageInput.value = '';
  await sendMessage(message);
});

/* ───────────────────────────────────────────── */
/* Início                                        */
/* ───────────────────────────────────────────── */

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSession);
} else {
  initSession();
}
