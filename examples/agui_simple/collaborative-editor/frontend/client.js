/**
 * Collaborative Editor WebSocket Client
 *
 * Manages document state synchronization and AI assistance requests.
 */

class CollaborativeEditorClient {
    constructor(wsUrl = 'ws://localhost:8000/ws') {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.isConnected = false;
        this.clientId = null;
        this.documentId = 'default';
        this.messageHandlers = new Map();

        // Metrics
        this.stats = {
            totalEdits: 0,
            totalAssists: 0,
            totalSuggestions: 0,
            totalResponseTime: 0,
            assistCount: 0,
        };

        // State tracking
        this.currentMessageId = null;
        this.currentMessageContent = '';
        this.isReceivingAssistance = false;
        this.lastEditTime = Date.now();

        // DOM elements
        this.editor = document.getElementById('editor');
        this.assistantContent = document.getElementById('assistant-content');
        this.connectionStatus = document.getElementById('connection-status');
        this.connectionText = document.getElementById('connection-text');
        this.wordCountEl = document.getElementById('word-count');
        this.charCountEl = document.getElementById('char-count');
        this.activeUsersEl = document.getElementById('active-users');

        // Toolbar buttons
        this.toolbarButtons = [
            'btn-suggest',
            'btn-expand',
            'btn-summarize',
            'btn-grammar',
            'btn-style',
            'btn-complete',
        ].map((id) => document.getElementById(id));

        this.setupEventHandlers();
        this.setupEditorListeners();
    }

    setupEventHandlers() {
        // AG-UI event handlers
        this.on('metadata', (event) => this.handleMetadata(event));
        this.on('text_message_start', (event) => this.handleMessageStart(event));
        this.on('text_message_chunk', (event) => this.handleMessageChunk(event));
        this.on('text_message_complete', (event) => this.handleMessageComplete(event));
        this.on('error', (event) => this.handleError(event));

        // Custom message handlers
        this.onMessage('document_state', (msg) => this.handleDocumentState(msg));
        this.onMessage('document_update', (msg) => this.handleDocumentUpdate(msg));
    }

    setupEditorListeners() {
        // Track document changes
        let editTimeout = null;

        this.editor.addEventListener('input', () => {
            // Update word and character counts
            this.updateCounts();

            // Debounce document updates (300ms)
            clearTimeout(editTimeout);
            editTimeout = setTimeout(() => {
                this.sendDocumentEdit();
                this.stats.totalEdits++;
                this.updateStats();
            }, 300);
        });

        // Initial count update
        this.updateCounts();
    }

    updateCounts() {
        const content = this.editor.value;
        const words = content.trim().split(/\s+/).filter((w) => w.length > 0).length;
        const chars = content.length;

        this.wordCountEl.textContent = words;
        this.charCountEl.textContent = chars;
    }

    connect() {
        console.log('Connecting to', this.wsUrl);

        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.updateConnectionStatus(true);

            // Join document
            this.joinDocument(this.documentId);
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                // Check if it's an AG-UI event or custom message
                if (message.event_type) {
                    this.handleAGUIEvent(message);
                } else if (message.type) {
                    this.handleCustomMessage(message);
                }
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.updateConnectionStatus(false);

            // Attempt reconnection after 3 seconds
            setTimeout(() => this.connect(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    joinDocument(documentId) {
        this.send({
            type: 'join_document',
            document_id: documentId,
        });
        console.log('Joining document:', documentId);
    }

    sendDocumentEdit() {
        if (!this.isConnected) return;

        const content = this.editor.value;
        const cursorPosition = this.editor.selectionStart;

        this.send({
            type: 'document_edit',
            document_id: this.documentId,
            content: content,
            cursor_position: cursorPosition,
        });
    }

    requestAssistance(command) {
        if (!this.isConnected || this.isReceivingAssistance) return;

        const content = this.editor.value;
        const selection = this.getSelectedText();
        const cursorPosition = this.editor.selectionStart;

        // Disable toolbar during assistance
        this.setToolbarEnabled(false);
        this.isReceivingAssistance = true;

        // Show processing card
        this.addAssistantCard({
            type: 'processing',
            header: `Processing: ${command}`,
            content: 'Analyzing your document...',
        });

        this.send({
            type: 'ai_assistance',
            document_id: this.documentId,
            command: command,
            selection: selection,
            cursor_position: cursorPosition,
        });

        this.stats.totalAssists++;
        this.updateStats();
    }

    getSelectedText() {
        const start = this.editor.selectionStart;
        const end = this.editor.selectionEnd;
        return this.editor.value.substring(start, end);
    }

    handleAGUIEvent(event) {
        const eventType = event.event_type;

        if (this.messageHandlers.has(eventType)) {
            this.messageHandlers.get(eventType)(event);
        } else {
            console.warn('Unhandled AG-UI event:', eventType);
        }
    }

    handleCustomMessage(message) {
        const messageType = message.type;

        const handler = this.customMessageHandlers.get(messageType);
        if (handler) {
            handler(message);
        } else {
            console.warn('Unhandled message type:', messageType);
        }
    }

    on(eventType, handler) {
        this.messageHandlers.set(eventType, handler);
    }

    onMessage(messageType, handler) {
        if (!this.customMessageHandlers) {
            this.customMessageHandlers = new Map();
        }
        this.customMessageHandlers.set(messageType, handler);
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    // AG-UI event handlers

    handleMetadata(event) {
        console.log('Received metadata:', event);
        this.clientId = event.data.client_id;
    }

    handleMessageStart(event) {
        console.log('Message start:', event);
        this.currentMessageId = event.message_id;
        this.currentMessageContent = '';
        this.assistStartTime = Date.now();
    }

    handleMessageChunk(event) {
        this.currentMessageContent += event.content;
    }

    handleMessageComplete(event) {
        console.log('Message complete:', event);

        const responseTime = (Date.now() - this.assistStartTime) / 1000;
        this.stats.totalResponseTime += responseTime;
        this.stats.assistCount++;

        // Extract metadata
        const metadata = event.metadata || {};
        const suggestions = metadata.suggestions || [];
        const grammarIssues = metadata.grammar_issues || [];
        const styleRecommendations = metadata.style_recommendations || [];

        this.stats.totalSuggestions += suggestions.length + grammarIssues.length + styleRecommendations.length;

        // Remove processing card and add complete card
        this.clearProcessingCards();
        this.addAssistantCard({
            type: 'complete',
            header: `✅ ${metadata.command || 'Assistance Complete'}`,
            content: event.content,
            metadata: metadata,
        });

        // Re-enable toolbar
        this.setToolbarEnabled(true);
        this.isReceivingAssistance = false;

        // Update stats
        this.updateStats();

        // Reset current message tracking
        this.currentMessageId = null;
        this.currentMessageContent = '';
    }

    handleError(event) {
        console.error('Error event:', event);

        this.clearProcessingCards();
        this.addAssistantCard({
            type: 'error',
            header: '❌ Error',
            content: event.error.message || 'An error occurred',
        });

        this.setToolbarEnabled(true);
        this.isReceivingAssistance = false;
    }

    // Custom message handlers

    handleDocumentState(message) {
        console.log('Received document state:', message);

        // Set initial document content
        this.editor.value = message.content;
        this.updateCounts();

        // Update active users count (simplified - just show 1 for now)
        this.activeUsersEl.textContent = '1';
    }

    handleDocumentUpdate(message) {
        console.log('Received document update from another client');

        // Save current cursor position
        const cursorPos = this.editor.selectionStart;

        // Update document content
        this.editor.value = message.content;
        this.updateCounts();

        // Try to restore cursor position (simplified)
        this.editor.setSelectionRange(cursorPos, cursorPos);

        // Flash border to indicate update
        this.editor.style.borderColor = '#667eea';
        setTimeout(() => {
            this.editor.style.borderColor = '';
        }, 500);
    }

    // UI updates

    updateConnectionStatus(connected) {
        if (connected) {
            this.connectionStatus.classList.add('connected');
            this.connectionText.textContent = 'Connected';
        } else {
            this.connectionStatus.classList.remove('connected');
            this.connectionText.textContent = 'Disconnected';
        }

        this.setToolbarEnabled(connected);
    }

    setToolbarEnabled(enabled) {
        this.toolbarButtons.forEach((btn) => {
            if (btn) btn.disabled = !enabled;
        });
    }

    addAssistantCard(config) {
        // Remove empty state if present
        const emptyState = this.assistantContent.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const card = document.createElement('div');
        card.className = `assistant-card ${config.type}`;

        let html = `
            <div class="assistant-card-header">
                ${config.type === 'processing' ? '<span class="spinner"></span>' : ''}
                ${config.header}
            </div>
            <div class="assistant-card-content">${this.escapeHtml(config.content)}</div>
        `;

        // Add suggestions if present
        if (config.metadata && config.metadata.suggestions) {
            html += '<div style="margin-top: 10px;">';
            config.metadata.suggestions.slice(0, 5).forEach((suggestion) => {
                html += `
                    <div class="suggestion-item">
                        <div class="suggestion-type">${suggestion.type || 'suggestion'}</div>
                        <div class="suggestion-message">${suggestion.message}</div>
                    </div>
                `;
            });
            html += '</div>';
        }

        card.innerHTML = html;

        // Add to top of assistant content
        this.assistantContent.insertBefore(card, this.assistantContent.firstChild);

        // Limit to 10 cards
        while (this.assistantContent.children.length > 10) {
            this.assistantContent.removeChild(this.assistantContent.lastChild);
        }
    }

    clearProcessingCards() {
        const processingCards = this.assistantContent.querySelectorAll('.assistant-card.processing');
        processingCards.forEach((card) => card.remove());
    }

    updateStats() {
        document.getElementById('stat-edits').textContent = this.stats.totalEdits;
        document.getElementById('stat-assists').textContent = this.stats.totalAssists;
        document.getElementById('stat-suggestions').textContent = this.stats.totalSuggestions;

        const avgTime =
            this.stats.assistCount > 0
                ? (this.stats.totalResponseTime / this.stats.assistCount).toFixed(1)
                : '0.0';
        document.getElementById('stat-time').textContent = `${avgTime}s`;
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
    client = new CollaborativeEditorClient();
    client.connect();
});

// Global function for toolbar buttons
function requestAssistance(command) {
    if (client) {
        client.requestAssistance(command);
    }
}
