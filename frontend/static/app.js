"use strict";

const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chat-form");
const messageInput = document.querySelector("#message-input");

const appendMessage = (text) => {
    const textDiv = document.createElement('div');
    textDiv.className = 'py-1';
    textDiv.textContent = text;
    messages.appendChild(textDiv);
    messages.scrollTop = messages.scrollHeight;
};

const ws = new WebSocket(`ws://${location.host}/ws`);
ws.addEventListener('open', () => appendMessage('[connected]'));
ws.addEventListener('close', () => appendMessage('[disconnected]'));
ws.addEventListener('message', (e) => {
    try {
        const { text } = JSON.parse(e.data);
        appendMessage(text);
    } catch {
        appendMessage(e.data);
    }
});

chatForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const text = messageInput.value.trim();
    if (!text || ws.readyState !== WebSocket.OPEN) {
        // TODO: Display failure message or alert?
        return;
    }

    ws.send(JSON.stringify({ type: 'chat', text, ts: Date.now() }));

    messageInput.value = '';
    messageInput.focus();
});
