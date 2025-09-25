"use strict";

const ws = new WebSocket(`ws://${location.host}/ws`);

ws.onmessage = e => {
    const div = document.createElement('div');
    div.textContent = e.data;
    document.getElementById('messages').appendChild(div);
};

document.getElementById('chat-form').addEventListener('submit', e => {
    e.preventDefault();
    const input = document.getElementById('msg');
    ws.send(input.value);
    input.value = '';
});