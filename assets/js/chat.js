const API_BASE = "https://nextia-production.up.railway.app";

const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const typingIndicator = document.getElementById("typingIndicator");

let isLoading = false;

/* ───────────────────────────────────────────── */
/* Session UUID */
/* ───────────────────────────────────────────── */

function getSessionId() {
    let sessionId = localStorage.getItem("clara_session_id");

    if (!sessionId) {
        sessionId = crypto.randomUUID();
        localStorage.setItem("clara_session_id", sessionId);
    }

    return sessionId;
}

const sessionId = getSessionId();

/* ───────────────────────────────────────────── */
/* UI */
/* ───────────────────────────────────────────── */

function addMessage(content, role) {

    const message = document.createElement("div");

    message.classList.add("message", role);

    message.textContent = content;

    chatMessages.appendChild(message);

    scrollToBottom();
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setLoading(state) {

    isLoading = state;

    messageInput.disabled = state;
    sendButton.disabled = state;

    typingIndicator.classList.toggle("hidden", !state);

    if (!state) {
        messageInput.focus();
    }
}

function showLeadSuccess() {

    const exists = document.querySelector(".lead-success");

    if (exists) return;

    const success = document.createElement("div");

    success.classList.add("lead-success");

    success.innerHTML = `
        ✅ Informações recebidas com sucesso.
        Nossa equipe entrará em contato em breve.
    `;

    chatMessages.appendChild(success);

    scrollToBottom();
}

/* ───────────────────────────────────────────── */
/* API */
/* ───────────────────────────────────────────── */

async function sendMessage(message) {

    try {

        setLoading(true);

        const response = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                session_id: sessionId,
                message: message
            })
        });

        if (!response.ok) {
            throw new Error("Erro na comunicação com a API.");
        }

        const data = await response.json();

        addMessage(data.reply, "ai");

        if (data.fase === "concluido") {
            showLeadSuccess();

            setTimeout(() => {
                console.log("Lead concluído.");
            }, 1000);
        }

    } catch (error) {

        console.error(error);

        addMessage(
            "Desculpe, ocorreu um erro ao processar sua mensagem.",
            "ai"
        );

    } finally {

        setLoading(false);
    }
}

async function initSession() {

    try {

        setLoading(true);

        const response = await fetch(`${API_BASE}/api/session/init`, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                session_id: sessionId,
                message: "oi"
            })
        });

        if (!response.ok) {
            throw new Error("Erro ao iniciar sessão.");
        }

        const data = await response.json();

        addMessage(data.reply, "ai");

    } catch (error) {

        console.error(error);

        addMessage(
            "Não foi possível iniciar a conversa com a Clara.",
            "ai"
        );

    } finally {

        setLoading(false);
    }
}

/* ───────────────────────────────────────────── */
/* Eventos */
/* ───────────────────────────────────────────── */

chatForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    if (isLoading) return;

    const message = messageInput.value.trim();

    if (!message) return;

    addMessage(message, "user");

    messageInput.value = "";

    await sendMessage(message);
});

/* ───────────────────────────────────────────── */
/* Boot */
/* ───────────────────────────────────────────── */

window.addEventListener("DOMContentLoaded", () => {
    initSession();
});
