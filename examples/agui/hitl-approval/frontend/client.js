/**
 * AG-UI WebSocket Client for HITL Approval Workflow
 *
 * Handles:
 * - WebSocket connection to backend
 * - AG-UI event parsing
 * - Interrupt handling (approval workflow)
 * - Message display
 */

class AGUIClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.currentMessageId = null;
        this.currentMessageContent = '';
        this.pendingInterrupt = null;
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            updateStatus('Connected', true);
            addSystemMessage('Connected to trading agent');
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            updateStatus('Disconnected', false);
            addSystemMessage('Disconnected from trading agent');
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            addSystemMessage('Connection error occurred');
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
        console.log('Received event:', eventType, event);

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
            case 'interrupt':
                this.handleInterrupt(event);
                break;
            case 'error':
                this.handleError(event);
                break;
            default:
                console.warn('Unknown event type:', eventType);
        }
    }

    handleMetadata(event) {
        console.log('Agent metadata:', event.data);
        const capabilities = event.data.capabilities || [];
        const hitlMode = event.data.hitl_mode;

        if (hitlMode === 'bidirectional') {
            addSystemMessage(`✅ HITL Mode: Bidirectional (Approval Threshold: ${event.data.approval_threshold || 0.8})`);
        }
    }

    handleTextMessageStart(event) {
        this.currentMessageId = event.message_id;
        this.currentMessageContent = '';
        // Create message element
        const messageEl = document.createElement('div');
        messageEl.className = 'message agent';
        messageEl.id = `msg-${this.currentMessageId}`;
        document.getElementById('messages').appendChild(messageEl);
        scrollToBottom();
    }

    handleTextMessageChunk(event) {
        this.currentMessageContent += event.content;
        const messageEl = document.getElementById(`msg-${this.currentMessageId}`);
        if (messageEl) {
            messageEl.innerHTML = formatMarkdown(this.currentMessageContent);
        }
        scrollToBottom();
    }

    handleTextMessageComplete(event) {
        const messageEl = document.getElementById(`msg-${this.currentMessageId}`);
        if (messageEl) {
            messageEl.innerHTML = formatMarkdown(event.content);

            // Add status badge if present
            const approvalStatus = event.metadata?.approval_status;
            if (approvalStatus) {
                const badge = document.createElement('div');
                badge.style.marginTop = '10px';
                badge.style.padding = '5px 10px';
                badge.style.borderRadius = '5px';
                badge.style.fontSize = '12px';
                badge.style.fontWeight = 'bold';

                if (approvalStatus === 'approved') {
                    badge.style.background = '#4ecdc4';
                    badge.style.color = 'white';
                    badge.textContent = '✅ Approved';
                } else if (approvalStatus === 'rejected') {
                    badge.style.background = '#ff6b6b';
                    badge.style.color = 'white';
                    badge.textContent = '❌ Rejected';
                } else if (approvalStatus === 'approved_with_modifications') {
                    badge.style.background = '#f7b731';
                    badge.style.color = 'white';
                    badge.textContent = '📝 Approved with Modifications';
                } else if (approvalStatus === 'timeout') {
                    badge.style.background = '#ff6b6b';
                    badge.style.color = 'white';
                    badge.textContent = '⏱️ Timeout';
                }

                messageEl.appendChild(badge);
            }
        }
        this.currentMessageId = null;
        this.currentMessageContent = '';
        scrollToBottom();
    }

    handleInterrupt(event) {
        this.pendingInterrupt = event;
        console.log('Interrupt received:', event);

        // Create interrupt dialog
        const dialog = document.createElement('div');
        dialog.className = 'interrupt-dialog';
        dialog.id = `interrupt-${event.interrupt_id}`;

        const title = document.createElement('h3');
        title.textContent = '⚠️ Approval Required';
        dialog.appendChild(title);

        const message = document.createElement('p');
        message.textContent = event.message;
        dialog.appendChild(message);

        const context = document.createElement('div');
        context.style.marginTop = '10px';
        context.style.fontSize = '14px';
        context.style.color = '#666';

        if (event.context) {
            context.innerHTML = `
                <strong>Confidence:</strong> ${(event.context.confidence * 100).toFixed(1)}%<br>
                <strong>Threshold:</strong> ${(event.context.approval_threshold * 100).toFixed(1)}%<br>
                <strong>Proposed Action:</strong><br>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; margin-top: 5px; overflow-x: auto;">${event.context.proposed_response || 'See below'}</pre>
            `;
        }
        dialog.appendChild(context);

        const actions = document.createElement('div');
        actions.className = 'interrupt-actions';

        if (event.actions.includes('APPROVE')) {
            const approveBtn = document.createElement('button');
            approveBtn.className = 'btn-approve';
            approveBtn.textContent = '✅ Approve';
            approveBtn.onclick = () => this.respondToInterrupt(event.interrupt_id, 'APPROVE');
            actions.appendChild(approveBtn);
        }

        if (event.actions.includes('REJECT')) {
            const rejectBtn = document.createElement('button');
            rejectBtn.className = 'btn-reject';
            rejectBtn.textContent = '❌ Reject';
            rejectBtn.onclick = () => this.respondToInterrupt(event.interrupt_id, 'REJECT');
            actions.appendChild(rejectBtn);
        }

        if (event.actions.includes('EDIT')) {
            const editBtn = document.createElement('button');
            editBtn.className = 'btn-edit';
            editBtn.textContent = '📝 Edit';
            editBtn.onclick = () => this.respondToInterruptWithEdit(event.interrupt_id);
            actions.appendChild(editBtn);
        }

        dialog.appendChild(actions);

        document.getElementById('messages').appendChild(dialog);
        scrollToBottom();
    }

    respondToInterrupt(interruptId, action) {
        console.log(`Responding to interrupt ${interruptId} with action ${action}`);

        const response = {
            type: 'interrupt_response',
            interrupt_id: interruptId,
            action: action,
            context: {
                feedback: action === 'APPROVE' ? 'Trade approved by user' : 'Trade rejected by user'
            }
        };

        this.ws.send(JSON.stringify(response));

        // Remove interrupt dialog
        const dialog = document.getElementById(`interrupt-${interruptId}`);
        if (dialog) {
            dialog.remove();
        }

        this.pendingInterrupt = null;
    }

    respondToInterruptWithEdit(interruptId) {
        const modifiedContent = prompt('Enter modified trade proposal:');
        if (!modifiedContent) return;

        console.log(`Responding to interrupt ${interruptId} with EDIT`);

        const response = {
            type: 'interrupt_response',
            interrupt_id: interruptId,
            action: 'EDIT',
            context: {
                modified_content: modifiedContent
            }
        };

        this.ws.send(JSON.stringify(response));

        // Remove interrupt dialog
        const dialog = document.getElementById(`interrupt-${interruptId}`);
        if (dialog) {
            dialog.remove();
        }

        this.pendingInterrupt = null;
    }

    handleError(event) {
        console.error('Agent error:', event);
        addSystemMessage(`Error: ${event.error_message}`);
    }

    sendMessage(content) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            alert('Not connected to agent');
            return;
        }

        const message = {
            type: 'message',
            message: content
        };

        this.ws.send(JSON.stringify(message));

        // Add user message to chat
        const messageEl = document.createElement('div');
        messageEl.className = 'message user';
        messageEl.textContent = content;
        document.getElementById('messages').appendChild(messageEl);
        scrollToBottom();
    }
}

// Helper functions
function formatMarkdown(text) {
    // Simple markdown formatting
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

function addSystemMessage(text) {
    const messageEl = document.createElement('div');
    messageEl.className = 'message system';
    messageEl.textContent = text;
    document.getElementById('messages').appendChild(messageEl);
    scrollToBottom();
}

function updateStatus(text, connected) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = `● ${text}`;
    statusEl.className = connected ? 'status connected' : 'status disconnected';
}

function scrollToBottom() {
    const messages = document.getElementById('messages');
    messages.scrollTop = messages.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message) return;

    client.sendMessage(message);
    input.value = '';
}

function sendQuickMessage(type) {
    const messages = {
        conservative: 'Execute a conservative trade strategy',
        moderate: 'Analyze this moderate trading opportunity',
        aggressive: 'Execute an aggressive high-risk trade'
    };

    const message = messages[type];
    if (message) {
        document.getElementById('messageInput').value = message;
        sendMessage();
    }
}

// Initialize client
const client = new AGUIClient('ws://localhost:8000/ws');
client.connect();
