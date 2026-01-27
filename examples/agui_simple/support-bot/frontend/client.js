/**
 * Customer Support Bot WebSocket Client
 *
 * Maintains conversation history and displays ticket context.
 */

class SupportBotClient {
    constructor(wsUrl = 'ws://localhost:8000/ws') {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.isConnected = false;
        this.messageHandlers = new Map();

        // Ticket info
        this.ticketId = null;
        this.customerId = null;
        this.messageCount = 0;
        this.priority = 'LOW';
        this.status = 'OPEN';
        this.isEscalated = false;

        // DOM elements
        this.messagesArea = document.getElementById('messages-area');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.ticketIdEl = document.getElementById('ticket-id');

        this.setupEventHandlers();
    }

    setupEventHandlers() {
        // AG-UI event handlers
        this.on('metadata', (event) => this.handleMetadata(event));
        this.on('text_message_start', (event) => this.handleMessageStart(event));
        this.on('text_message_chunk', (event) => this.handleMessageChunk(event));
        this.on('text_message_complete', (event) => this.handleMessageComplete(event));
        this.on('error', (event) => this.handleError(event));
    }

    connect() {
        console.log('Connecting to', this.wsUrl);

        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.sendBtn.disabled = false;
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.sendBtn.disabled = true;

            // Attempt reconnection after 3 seconds
            setTimeout(() => this.connect(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleMessage(message) {
        const eventType = message.event_type;

        if (this.messageHandlers.has(eventType)) {
            this.messageHandlers.get(eventType)(message);
        } else {
            console.warn('Unhandled event type:', eventType);
        }
    }

    on(eventType, handler) {
        this.messageHandlers.set(eventType, handler);
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    // AG-UI event handlers

    handleMetadata(event) {
        console.log('Received metadata:', event);
        this.customerId = event.data.customer_id;

        // Show welcome message
        this.addSystemMessage(
            'Connected to support! We\'re here to help 24/7. ' +
            'Average response time is less than 5 minutes.'
        );
    }

    handleMessageStart(event) {
        console.log('Message start:', event);
        this.currentMessageContent = '';
        this.currentMessageElement = null;
    }

    handleMessageChunk(event) {
        if (!this.currentMessageElement) {
            this.currentMessageElement = this.addAgentMessage('');
        }
        this.currentMessageContent += event.content;
        this.currentMessageElement.textContent = this.currentMessageContent;

        // Auto-scroll
        this.scrollToBottom();
    }

    handleMessageComplete(event) {
        console.log('Message complete:', event);

        const metadata = event.metadata || {};

        // Update ticket info
        if (metadata.ticket_id && !this.ticketId) {
            this.ticketId = metadata.ticket_id;
            this.ticketIdEl.textContent = metadata.ticket_id;
        }

        if (metadata.priority) {
            this.priority = metadata.priority.toUpperCase();
            document.getElementById('stat-priority').textContent = this.priority;

            // Color code priority
            const priorityEl = document.getElementById('stat-priority');
            priorityEl.style.color = {
                HIGH: '#ef4444',
                MEDIUM: '#f59e0b',
                LOW: '#10b981',
            }[this.priority] || '#667eea';
        }

        if (metadata.status) {
            this.status = metadata.status.toUpperCase();
            document.getElementById('stat-status').textContent = this.status;
        }

        // Handle escalation
        if (metadata.escalated && !this.isEscalated) {
            this.isEscalated = true;
            this.showEscalationNotice();
        }

        // Update final message content
        if (this.currentMessageElement) {
            this.currentMessageElement.innerHTML = this.formatMessage(event.content);
        }

        this.currentMessageElement = null;
        this.scrollToBottom();
    }

    handleError(event) {
        console.error('Error event:', event);
        this.addSystemMessage(`Error: ${event.error.message || 'An error occurred'}`);
    }

    // UI methods

    addUserMessage(content) {
        const messageEl = document.createElement('div');
        messageEl.className = 'message user';

        messageEl.innerHTML = `
            <div class="message-header">You • ${this.getCurrentTime()}</div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;

        this.appendMessage(messageEl);
        this.messageCount++;
        this.updateStats();

        return messageEl;
    }

    addAgentMessage(content) {
        const messageEl = document.createElement('div');
        messageEl.className = 'message agent';

        messageEl.innerHTML = `
            <div class="message-header">Support Agent • ${this.getCurrentTime()}</div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;

        this.appendMessage(messageEl);
        this.messageCount++;
        this.updateStats();

        return messageEl.querySelector('.message-content');
    }

    addSystemMessage(content) {
        const messageEl = document.createElement('div');
        messageEl.className = 'message system';

        messageEl.innerHTML = `
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;

        this.appendMessage(messageEl);
    }

    appendMessage(messageEl) {
        // Remove empty state if present
        const emptyState = this.messagesArea.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        this.messagesArea.appendChild(messageEl);
        this.scrollToBottom();
    }

    showEscalationNotice() {
        const notice = document.createElement('div');
        notice.className = 'escalation-notice';
        notice.innerHTML = `
            <h3>🚀 Escalated to Human Agent</h3>
            <p>Your case has been escalated to a specialist who will assist you shortly.</p>
        `;

        // Insert before input area
        this.messagesArea.appendChild(notice);
        this.scrollToBottom();
    }

    updateStats() {
        document.getElementById('stat-messages').textContent = this.messageCount;
    }

    scrollToBottom() {
        this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
    }

    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
        });
    }

    formatMessage(text) {
        // Simple markdown-like formatting
        let formatted = this.escapeHtml(text);

        // Bold
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Links
        formatted = formatted.replace(
            /(https?:\/\/[^\s]+)/g,
            '<a href="$1" target="_blank" style="color: #667eea;">$1</a>'
        );

        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize client on page load
let client;

window.addEventListener('DOMContentLoaded', () => {
    client = new SupportBotClient();
    client.connect();
});

// Global functions for UI interactions

function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();

    if (message && client.isConnected) {
        client.addUserMessage(message);
        client.send({
            type: 'message',
            message: message,
        });
        input.value = '';
    }
}

function sendQuickIssue(issue) {
    document.getElementById('message-input').value = issue;
    sendMessage();
}
