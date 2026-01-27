/**
 * Tool Dashboard WebSocket Client
 *
 * Connects to AG-UI backend and visualizes tool execution in real-time.
 */

class ToolDashboardClient {
    constructor(wsUrl = 'ws://localhost:8000/ws') {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.isConnected = false;
        this.messageHandlers = new Map();
        this.tools = [];
        this.toolStats = new Map();
        this.executionMetrics = {
            totalExecutions: 0,
            totalTime: 0,
            successCount: 0,
            errorCount: 0,
        };
        this.currentMessageId = null;
        this.currentMessageContent = '';
        this.currentMessageMetadata = null;

        // DOM elements
        this.connectionStatus = document.getElementById('connection-status');
        this.toolsList = document.getElementById('tools-list');
        this.executionLog = document.getElementById('execution-log');
        this.queryInput = document.getElementById('query-input');
        this.sendButton = document.getElementById('send-button');

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
            this.updateConnectionStatus('connected');
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
            this.updateConnectionStatus('disconnected');

            // Attempt reconnection after 3 seconds
            setTimeout(() => this.connect(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('error');
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

    sendMessage(content) {
        if (!this.isConnected) {
            console.error('Cannot send message: not connected');
            return;
        }

        const message = {
            type: 'message',
            message: content,
            timestamp: new Date().toISOString(),
        };

        this.ws.send(JSON.stringify(message));
        console.log('Sent message:', content);

        // Add user query to log
        this.addLogEntry({
            type: 'user-query',
            content: content,
            timestamp: new Date().toISOString(),
        });
    }

    handleMetadata(event) {
        console.log('Received metadata:', event);

        // Store available tools
        if (event.data && event.data.available_tools) {
            this.tools = event.data.available_tools;
            this.renderTools();
        }
    }

    handleMessageStart(event) {
        console.log('Message start:', event);
        this.currentMessageId = event.message_id;
        this.currentMessageContent = '';
        this.currentMessageMetadata = event.metadata || {};

        // Show that agent is processing
        this.addLogEntry({
            type: 'processing',
            content: 'Agent is processing your request...',
            timestamp: new Date().toISOString(),
        });
    }

    handleMessageChunk(event) {
        this.currentMessageContent += event.content;
        // Update current message display (optional for streaming visualization)
    }

    handleMessageComplete(event) {
        console.log('Message complete:', event);

        // Extract tool execution information from metadata
        const metadata = event.metadata || {};
        const toolResults = metadata.tool_results || [];

        // Update tool stats and visualize executions
        toolResults.forEach((result) => {
            this.updateToolStats(result);
            this.visualizeToolExecution(result);
        });

        // Display final response
        this.addLogEntry({
            type: 'response',
            content: event.content,
            metadata: metadata,
            timestamp: new Date().toISOString(),
        });

        // Update global metrics
        this.updateMetrics();

        // Reset current message tracking
        this.currentMessageId = null;
        this.currentMessageContent = '';
        this.currentMessageMetadata = null;
    }

    handleError(event) {
        console.error('Error event:', event);
        this.addLogEntry({
            type: 'error',
            content: `Error: ${event.error.message}`,
            timestamp: new Date().toISOString(),
        });
    }

    updateToolStats(result) {
        const toolName = result.tool;

        if (!this.toolStats.has(toolName)) {
            this.toolStats.set(toolName, {
                executionCount: 0,
                totalTime: 0,
                successCount: 0,
                errorCount: 0,
                lastExecution: null,
            });
        }

        const stats = this.toolStats.get(toolName);
        stats.executionCount++;
        stats.totalTime += result.execution_time;
        stats.lastExecution = new Date().toISOString();

        if (result.status === 'success') {
            stats.successCount++;
            this.executionMetrics.successCount++;
        } else {
            stats.errorCount++;
            this.executionMetrics.errorCount++;
        }

        this.executionMetrics.totalExecutions++;
        this.executionMetrics.totalTime += result.execution_time;
    }

    visualizeToolExecution(result) {
        const toolName = result.tool;
        const status = result.status;
        const executionTime = result.execution_time;

        // Highlight tool in sidebar
        const toolCard = document.querySelector(`[data-tool="${toolName}"]`);
        if (toolCard) {
            // Show executing state briefly
            toolCard.classList.add('executing');
            setTimeout(() => {
                toolCard.classList.remove('executing');
                toolCard.classList.add(status);
                setTimeout(() => toolCard.classList.remove(status), 2000);
            }, executionTime * 1000);
        }

        // Add detailed log entry
        this.addLogEntry({
            type: `tool-${status}`,
            tool: toolName,
            params: result.params,
            result: result.result || result.error,
            executionTime: executionTime,
            status: status,
            timestamp: new Date().toISOString(),
        });

        // Update tool stats display
        this.renderTools();
    }

    renderTools() {
        if (this.tools.length === 0) {
            this.toolsList.innerHTML = '<div class="empty-state">No tools available</div>';
            return;
        }

        this.toolsList.innerHTML = this.tools
            .map((tool) => {
                const stats = this.toolStats.get(tool.name) || {
                    executionCount: 0,
                    totalTime: 0,
                    successCount: 0,
                };

                const avgTime =
                    stats.executionCount > 0
                        ? (stats.totalTime / stats.executionCount).toFixed(2)
                        : '0.00';

                return `
                    <div class="tool-card" data-tool="${tool.name}">
                        <div class="tool-name">${tool.name}</div>
                        <div class="tool-description">${tool.description}</div>
                        <div class="tool-stats">
                            <div class="tool-stat">
                                <strong>${stats.executionCount}</strong> calls
                            </div>
                            <div class="tool-stat">
                                <strong>${avgTime}s</strong> avg
                            </div>
                        </div>
                    </div>
                `;
            })
            .join('');
    }

    addLogEntry(entry) {
        // Remove empty state if present
        const emptyState = this.executionLog.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${entry.type}`;

        const timestamp = new Date(entry.timestamp).toLocaleTimeString();

        let content = '';

        if (entry.type === 'user-query') {
            content = `
                <div class="timestamp">${timestamp} - USER QUERY</div>
                <div class="content">${entry.content}</div>
            `;
        } else if (entry.type === 'processing') {
            content = `
                <div class="timestamp">${timestamp} - PROCESSING</div>
                <div class="content">
                    <span class="spinner"></span>
                    ${entry.content}
                </div>
            `;
        } else if (entry.type === 'response') {
            content = `
                <div class="timestamp">${timestamp} - RESPONSE</div>
                <div class="response-content">${this.escapeHtml(entry.content)}</div>
            `;

            if (entry.metadata && entry.metadata.total_execution_time) {
                content += `
                    <div class="metrics">
                        <div class="metric">
                            Total Time: ${entry.metadata.total_execution_time.toFixed(2)}s
                        </div>
                        <div class="metric">
                            Tools Used: ${entry.metadata.tools_used.length}
                        </div>
                    </div>
                `;
            }
        } else if (entry.type.startsWith('tool-')) {
            const statusEmoji = entry.status === 'success' ? '✅' : '❌';
            content = `
                <div class="timestamp">${timestamp} - TOOL EXECUTION ${statusEmoji}</div>
                <div class="content">
                    <strong>${entry.tool}</strong>
                    ${entry.status === 'success' ? 'completed successfully' : 'failed'}
                </div>
                <div class="metrics">
                    <div class="metric">
                        Execution Time: ${entry.executionTime.toFixed(3)}s
                    </div>
                    <div class="metric">
                        Status: ${entry.status}
                    </div>
                </div>
            `;
        } else if (entry.type === 'error') {
            content = `
                <div class="timestamp">${timestamp} - ERROR</div>
                <div class="content">${entry.content}</div>
            `;
        }

        logEntry.innerHTML = content;

        // Add to log (prepend for newest first)
        this.executionLog.insertBefore(logEntry, this.executionLog.firstChild);

        // Limit log entries to 50
        while (this.executionLog.children.length > 50) {
            this.executionLog.removeChild(this.executionLog.lastChild);
        }
    }

    updateMetrics() {
        // Update displayed metrics
        document.getElementById('tools-executed').textContent =
            this.executionMetrics.totalExecutions;

        const avgTime =
            this.executionMetrics.totalExecutions > 0
                ? (this.executionMetrics.totalTime / this.executionMetrics.totalExecutions).toFixed(2)
                : '0.00';
        document.getElementById('avg-time').textContent = `${avgTime}s`;

        const successRate =
            this.executionMetrics.totalExecutions > 0
                ? ((this.executionMetrics.successCount / this.executionMetrics.totalExecutions) * 100).toFixed(0)
                : '100';
        document.getElementById('success-rate').textContent = `${successRate}%`;
    }

    updateConnectionStatus(status) {
        const statusMap = {
            connected: { text: 'Connected', class: 'connected' },
            disconnected: { text: 'Disconnected', class: 'disconnected' },
            error: { text: 'Error', class: 'disconnected' },
        };

        const statusInfo = statusMap[status] || { text: 'Unknown', class: '' };

        this.connectionStatus.className = `status-item ${statusInfo.class}`;
        this.connectionStatus.querySelector('.status-value').textContent = statusInfo.text;

        // Enable/disable input based on connection
        this.sendButton.disabled = status !== 'connected';
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
    client = new ToolDashboardClient();
    client.connect();
});

// Global functions for UI interactions
function sendQuery() {
    const input = document.getElementById('query-input');
    const query = input.value.trim();

    if (query && client.isConnected) {
        client.sendMessage(query);
        input.value = '';
    }
}

function sendQuickQuery(query) {
    const input = document.getElementById('query-input');
    input.value = query;
    sendQuery();
}
