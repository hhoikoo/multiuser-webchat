const messages = document.querySelector(".messages");
const chatForm = document.querySelector(".chat-form");
const messageInput = document.querySelector(".message-input");

const appendMessage = (text) => {
	const div = document.createElement("div");
	// TODO: Get user ID, and if message from myself use "message-right".
	div.className = "message message-left";
	div.textContent = text;
	messages.prepend(div);
};

const loadHistory = async () => {
	try {
		const response = await fetch("/messages?minutes=30");
		if (!response.ok) {
			console.error("Failed to fetch history:", response.statusText);
			return;
		}

		const data = await response.json();
		const messagesHistory = data?.messages ?? [];

		for (const msg of messagesHistory) {
			appendMessage(msg.text);
		}

		if (messagesHistory.length > 0) {
			appendMessage(
				`[loaded ${messagesHistory.length} message(s) from history]`,
			);
		}
	} catch (error) {
		console.error("Error loading history:", error);
	}
};

class WebSocketManager {
	static MAX_RECONNECT_ATTEMPTS = 5;
	static BASE_RECONNECT_DELAY = 1000; // 1 second
	static MAX_RECONNECT_DELAY = 30000; // 30 seconds

	constructor(url) {
		this.url = url;
		this.ws = null;
		this.reconnectAttempts = 0;
		this.reconnectTimer = null;
		this.isManualClose = false;
		this.hasLoadedHistory = false;

		this.connect();
	}

	connect() {
		try {
			this.ws = new WebSocket(this.url);
			this.setupEventListeners();
		} catch (error) {
			console.error("WebSocket connection error:", error);
			this.handleReconnect();
		}
	}

	setupEventListeners() {
		this.ws.addEventListener("open", async () => {
			appendMessage("[connected]");
			this.reconnectAttempts = 0; // Reset attempts on successful connection

			// Load message history only on first connection
			if (!this.hasLoadedHistory) {
				await loadHistory();
				this.hasLoadedHistory = true;
			}
		});

		this.ws.addEventListener("close", () => {
			if (!this.isManualClose) {
				appendMessage("[disconnected]");
				this.handleReconnect();
			}
		});

		this.ws.addEventListener("error", (error) => {
			console.error("WebSocket error:", error);
		});

		this.ws.addEventListener("message", (e) => {
			try {
				const { text } = JSON.parse(e.data);
				appendMessage(text);
			} catch {
				appendMessage(e.data);
			}
		});
	}

	handleReconnect() {
		if (this.reconnectAttempts >= WebSocketManager.MAX_RECONNECT_ATTEMPTS) {
			appendMessage(
				`[reconnection failed after ${WebSocketManager.MAX_RECONNECT_ATTEMPTS} attempts]`,
			);
			return;
		}

		this.reconnectAttempts++;
		const delay = Math.min(
			WebSocketManager.BASE_RECONNECT_DELAY * 2 ** (this.reconnectAttempts - 1),
			WebSocketManager.MAX_RECONNECT_DELAY,
		);

		appendMessage(
			`[reconnecting in ${delay / 1000}s... (attempt ${this.reconnectAttempts}/${WebSocketManager.MAX_RECONNECT_ATTEMPTS})]`,
		);

		this.reconnectTimer = setTimeout(() => {
			this.connect();
		}, delay);
	}

	send(data) {
		if (this.ws && this.ws.readyState === WebSocket.OPEN) {
			this.ws.send(data);
			return true;
		}
		return false;
	}

	close() {
		this.isManualClose = true;
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
		if (this.ws) {
			this.ws.close();
		}
	}

	isConnected() {
		return this.ws && this.ws.readyState === WebSocket.OPEN;
	}
}

const wsManager = new WebSocketManager(`ws://${location.host}/ws`);

chatForm.addEventListener("submit", (e) => {
	e.preventDefault();

	const text = messageInput.value.trim();
	if (!text || !wsManager.isConnected()) {
		// TODO: Display failure message or alert?
		return;
	}

	wsManager.send(JSON.stringify({ type: "chat", text, ts: Date.now() }));

	messageInput.value = "";
	messageInput.focus();
});
