/**
 * AG-UI WebSocket Client for Streaming Chat
 *
 * Handles:
 * - WebSocket connection management
 * - AG-UI event parsing and display
 * - Real-time message streaming
 * - Conversation history
 */

class StreamingChatClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.currentMessageId = null;
        this.currentMessageElement = null;
        this.messageCount = 0;
        this.isStreaming = false;
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateStatus('Connected', true);
            this.addSystemMessage('✅ Connected to streaming assistant');
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateStatus('Disconnected', false);
            this.addSystemMessage('❌ Disconnected from assistant');
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.addSystemMessage('⚠️ Connection error occurred');
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleEvent(data);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };
    }

    handleEvent(event) {
        const eventType = event.event_type;

        switch (eventType) {
            case 'metadata':
                this.handleMetadata(event);
                break;
            case 'text_message_start':
                this.handleTextMessageStart(event);
                break;
            case 'text_message_chunk':
                this.handleTextMessageChunk(event);
                break;
            case 'text_message_complete':
                this.handleTextMessageComplete(event);
                break;
            case 'error':
                this.handleError(event);
                break;
            default:
                console.log('Received event:', eventType, event);
        }
    }

    handleMetadata(event) {
        console.log('Agent metadata:', event.data);
        const capabilities = event.data.capabilities || [];
        if (capabilities.length > 0) {
            console.log('Agent capabilities:', capabilities.join(', '));
        }
    }

    handleTextMessageStart(event) {
        this.isStreaming = true;
        this.currentMessageId = event.message_id;

        // Create message container
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message agent';

        // Add avatar
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '🤖';
        messageDiv.appendChild(avatar);

        // Add content container
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.id = `msg-${this.currentMessageId}`;
        messageDiv.appendChild(contentDiv);

        // Add cursor span for streaming effect
        const cursor = document.createElement('span');
        cursor.className = 'cursor';
        cursor.style.borderRight = '2px solid #667eea';
        cursor.style.animation = 'blink 1s infinite';
        contentDiv.appendChild(cursor);

        document.getElementById('messages').appendChild(messageDiv);
        this.currentMessageElement = contentDiv;
        this.scrollToBottom();

        // Hide typing indicator
        this.hideTypingIndicator();
    }

    handleTextMessageChunk(event) {
        if (!this.currentMessageElement) return;

        // Get current text (excluding cursor)
        const cursor = this.currentMessageElement.querySelector('.cursor');
        let currentText = this.currentMessageElement.textContent;

        // Append new chunk
        this.currentMessageElement.textContent = currentText + event.content;

        // Re-add cursor
        if (cursor) {
            this.currentMessageElement.appendChild(cursor);
        }

        this.scrollToBottom();
    }

    handleTextMessageComplete(event) {
        if (this.currentMessageElement) {
            // Remove cursor
            const cursor = this.currentMessageElement.querySelector('.cursor');
            if (cursor) {
                cursor.remove();
            }

            // Set final content with formatting
            this.currentMessageElement.innerHTML = this.formatMessage(event.content);
        }

        this.isStreaming = false;
        this.currentMessageId = null;
        this.currentMessageElement = null;
        this.scrollToBottom();

        // Update message count
        this.messageCount++;
        this.updateMessageCount();
    }

    handleError(event) {
        console.error('Agent error:', event);
        this.addSystemMessage(`❌ Error: ${event.error_message}`);
        this.isStreaming = false;
        this.hideTypingIndicator();
    }

    sendMessage(content) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            alert('Not connected to agent');
            return;
        }

        if (this.isStreaming) {
            console.log('Still streaming previous message, please wait');
            return;
        }

        const message = {
            type: 'message',
            message: content
        };

        this.ws.send(JSON.stringify(message));

        // Add user message to chat
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '👤';
        messageDiv.appendChild(avatar);

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;
        messageDiv.appendChild(contentDiv);

        document.getElementById('messages').appendChild(messageDiv);
        this.scrollToBottom();

        // Show typing indicator
        this.showTypingIndicator();

        // Update message count
        this.messageCount++;
        this.updateMessageCount();
    }

    showTypingIndicator() {
        let indicator = document.getElementById('typingIndicator');
        if (!indicator) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message agent';

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.textContent = '🤖';
            messageDiv.appendChild(avatar);

            indicator = document.createElement('div');
            indicator.className = 'typing-indicator';
            indicator.id = 'typingIndicator';
            indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

            messageDiv.appendChild(indicator);
            document.getElementById('messages').appendChild(messageDiv);
        }
        indicator.classList.add('active');
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.closest('.message')?.remove();
        }
    }

    addSystemMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;

        messageDiv.appendChild(contentDiv);
        document.getElementById('messages').appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(text) {
        // Simple formatting: preserve newlines and basic markdown
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^(.*)$/, '<p>$1</p>')
            .replace(/<p><\/p>/g, '');
    }

    updateStatus(text, connected) {
        const statusText = document.getElementById('statusText');
        const statusDot = document.getElementById('statusDot');

        statusText.textContent = text;

        if (connected) {
            statusDot.classList.add('connected');
        } else {
            statusDot.classList.remove('connected');
        }
    }

    updateMessageCount() {
        document.getElementById('messageCount').textContent = `${this.messageCount} messages`;
    }

    scrollToBottom() {
        const messages = document.getElementById('messages');
        messages.scrollTop = messages.scrollHeight;
    }
}

// Add cursor blinking animation
const style = document.createElement('style');
style.textContent = `
    @keyframes blink {
        0%, 49% { opacity: 1; }
        50%, 100% { opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize client
const client = new StreamingChatClient('ws://localhost:8000/ws');
client.connect();

// UI helper functions
function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message) return;
    if (client.isStreaming) {
        alert('Please wait for the current response to complete');
        return;
    }

    client.sendMessage(message);
    input.value = '';
    input.focus();
}

function sendQuickPrompt(text) {
    const input = document.getElementById('messageInput');
    input.value = text;
    sendMessage();
}

// Focus input on load
window.addEventListener('load', () => {
    document.getElementById('messageInput').focus();
});
