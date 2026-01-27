/**
 * Multi-Agent Coordination WebSocket Client
 *
 * Visualizes agent coordination in real-time.
 */

class MultiAgentClient {
    constructor(wsUrl = 'ws://localhost:8000/ws') {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.isConnected = false;
        this.agents = [];
        this.messageHandlers = new Map();

        // Stats
        this.stats = {
            totalCoordinations: 0,
            successfulCoordinations: 0,
        };

        // Current coordination
        this.currentAgents = new Set();

        // DOM elements
        this.agentsList = document.getElementById('agents-list');
        this.resultsContent = document.getElementById('results-content');
        this.queryInput = document.getElementById('query-input');
        this.sendBtn = document.getElementById('send-btn');

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

        // Store specialized agents
        if (event.data && event.data.specialized_agents) {
            this.agents = event.data.specialized_agents;
            this.renderAgents();
        }
    }

    handleMessageStart(event) {
        console.log('Message start:', event);
        this.currentMessageContent = '';

        // Show processing card
        this.addResultCard({
            type: 'processing',
            header: '⏳ Coordinating Agents...',
            content: 'Analyzing query and delegating to specialized agents...',
        });

        // Disable send button during processing
        this.sendBtn.disabled = true;
    }

    handleMessageChunk(event) {
        this.currentMessageContent += event.content;
    }

    handleMessageComplete(event) {
        console.log('Message complete:', event);

        const metadata = event.metadata || {};

        // Update stats
        this.stats.totalCoordinations++;
        this.stats.successfulCoordinations++;
        this.updateStats();

        // Mark involved agents as completed
        const involvedAgents = metadata.agents_involved || [];
        involvedAgents.forEach((agentName) => {
            this.setAgentStatus(agentName, 'done');
        });

        // After a delay, reset to idle
        setTimeout(() => {
            involvedAgents.forEach((agentName) => {
                this.setAgentStatus(agentName, 'idle');
            });
        }, 3000);

        // Remove processing card and add complete card
        this.removeProcessingCards();
        this.addResultCard({
            type: 'complete',
            header: '✅ Coordination Complete',
            content: event.content,
            metadata: metadata,
        });

        // Re-enable send button
        this.sendBtn.disabled = false;
    }

    handleError(event) {
        console.error('Error event:', event);

        this.removeProcessingCards();
        this.addResultCard({
            type: 'error',
            header: '❌ Error',
            content: event.error.message || 'An error occurred',
        });

        this.sendBtn.disabled = false;

        // Reset agent statuses
        this.currentAgents.forEach((agentName) => {
            this.setAgentStatus(agentName, 'idle');
        });
        this.currentAgents.clear();
    }

    // UI updates

    renderAgents() {
        if (this.agents.length === 0) {
            this.agentsList.innerHTML = '<div class="empty-state">No agents available</div>';
            return;
        }

        this.agentsList.innerHTML = this.agents
            .map((agent) => {
                const capabilities = agent.capabilities
                    .map((cap) => `<span class="capability-tag">${cap}</span>`)
                    .join('');

                return `
                    <div class="agent-card" id="agent-${agent.name}">
                        <div class="agent-name">${agent.full_name || agent.name}</div>
                        <div class="agent-capabilities">${capabilities}</div>
                        <div class="agent-status status-idle" id="status-${agent.name}">Idle</div>
                    </div>
                `;
            })
            .join('');
    }

    setAgentStatus(agentName, status) {
        const agentCard = document.getElementById(`agent-${agentName}`);
        const statusEl = document.getElementById(`status-${agentName}`);

        if (!agentCard || !statusEl) return;

        // Remove all status classes
        agentCard.classList.remove('active', 'completed');
        statusEl.classList.remove('status-idle', 'status-working', 'status-done');

        // Add new status
        if (status === 'working') {
            agentCard.classList.add('active');
            statusEl.classList.add('status-working');
            statusEl.textContent = 'Working...';
            this.currentAgents.add(agentName);
        } else if (status === 'done') {
            agentCard.classList.add('completed');
            statusEl.classList.add('status-done');
            statusEl.textContent = 'Completed';
        } else {
            statusEl.classList.add('status-idle');
            statusEl.textContent = 'Idle';
            this.currentAgents.delete(agentName);
        }
    }

    addResultCard(config) {
        // Remove empty state if present
        const emptyState = this.resultsContent.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const card = document.createElement('div');
        card.className = `result-card ${config.type}`;

        let html = `<div class="result-header">${config.header}`;

        if (config.type === 'processing') {
            html += ' <span class="spinner"></span>';
        }

        html += '</div>';
        html += `<div class="result-content">${this.escapeHtml(config.content)}</div>`;

        if (config.metadata) {
            const agentsInvolved = config.metadata.agents_involved || [];
            if (agentsInvolved.length > 0) {
                html += '<div style="margin-top: 15px; font-size: 12px; color: #999;">';
                html += `Agents: ${agentsInvolved.join(', ')} | `;
                html += `Success Rate: ${config.metadata.agent_results ? Math.round((config.metadata.agent_results.filter(r => r.status === 'completed').length / config.metadata.agent_results.length) * 100) : 100}%`;
                html += '</div>';
            }
        }

        card.innerHTML = html;

        // Add to top of results
        this.resultsContent.insertBefore(card, this.resultsContent.firstChild);

        // Limit to 10 cards
        while (this.resultsContent.children.length > 10) {
            this.resultsContent.removeChild(this.resultsContent.lastChild);
        }

        // If this is a new query, simulate agent activity
        if (config.type === 'processing') {
            this.simulateAgentActivity();
        }
    }

    removeProcessingCards() {
        const processingCards = this.resultsContent.querySelectorAll('.result-card.processing');
        processingCards.forEach((card) => card.remove());
    }

    simulateAgentActivity() {
        // Based on query content, show which agents are likely working
        const query = this.queryInput.value.toLowerCase();

        setTimeout(() => {
            if (query.includes('research') || query.includes('what') || query.includes('who')) {
                this.setAgentStatus('research', 'working');
            }
            if (query.includes('calculate') || query.includes('number') || /\d/.test(query)) {
                this.setAgentStatus('calculator', 'working');
            }
            if (query.includes('write') || query.includes('report') || query.includes('create')) {
                this.setAgentStatus('writer', 'working');
            }
            if (query.includes('analyze') || query.includes('recommend') || query.includes('strategy')) {
                this.setAgentStatus('analyst', 'working');
            }
        }, 200);
    }

    updateStats() {
        document.getElementById('stat-coordinations').textContent = this.stats.totalCoordinations;
        const successRate =
            this.stats.totalCoordinations > 0
                ? Math.round((this.stats.successfulCoordinations / this.stats.totalCoordinations) * 100)
                : 100;
        document.getElementById('stat-success').textContent = `${successRate}%`;
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
    client = new MultiAgentClient();
    client.connect();
});

// Global functions for UI interactions

function sendQuery() {
    const query = document.getElementById('query-input').value.trim();

    if (query && client.isConnected) {
        client.send({
            type: 'message',
            message: query,
        });
    }
}

function sendQuickQuery(query) {
    document.getElementById('query-input').value = query;
    sendQuery();
}
