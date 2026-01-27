/**
 * Multimodal Agent WebSocket Client
 *
 * Handles file uploads, image previews, and multimodal content analysis.
 */

class MultimodalClient {
    constructor(wsUrl = 'ws://localhost:8000/ws') {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.isConnected = false;
        this.currentFile = null;
        this.currentFileData = null;
        this.isProcessing = false;
        this.messageHandlers = new Map();

        // DOM elements
        this.uploadArea = document.getElementById('upload-area');
        this.fileInput = document.getElementById('file-input');
        this.previewContainer = document.getElementById('preview-container');
        this.previewArea = document.getElementById('preview-area');
        this.fileInfo = document.getElementById('file-info');
        this.queryInput = document.getElementById('query-input');
        this.analyzeBtn = document.getElementById('analyze-btn');
        this.clearBtn = document.getElementById('clear-btn');
        this.resultsContent = document.getElementById('results-content');
        this.statusIndicator = document.getElementById('status-indicator');
        this.statusText = document.getElementById('status-text');

        this.setupEventHandlers();
        this.setupUploadHandlers();
    }

    setupEventHandlers() {
        // AG-UI event handlers
        this.on('metadata', (event) => this.handleMetadata(event));
        this.on('text_message_start', (event) => this.handleMessageStart(event));
        this.on('text_message_chunk', (event) => this.handleMessageChunk(event));
        this.on('text_message_complete', (event) => this.handleMessageComplete(event));
        this.on('error', (event) => this.handleError(event));
    }

    setupUploadHandlers() {
        // File input change
        this.fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleFileSelect(file);
            }
        });

        // Drag and drop
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.uploadArea.classList.add('drag-over');
        });

        this.uploadArea.addEventListener('dragleave', () => {
            this.uploadArea.classList.remove('drag-over');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('drag-over');

            const file = e.dataTransfer.files[0];
            if (file) {
                this.handleFileSelect(file);
            }
        });
    }

    async handleFileSelect(file) {
        console.log('File selected:', file.name);
        this.currentFile = file;

        // Read file as base64
        const reader = new FileReader();
        reader.onload = (e) => {
            this.currentFileData = e.target.result.split(',')[1]; // Remove data:...;base64, prefix
            this.displayPreview(file, e.target.result);
            this.displayFileInfo(file);
            this.analyzeBtn.disabled = false;
            this.clearBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    displayPreview(file, dataUrl) {
        this.previewContainer.style.display = 'block';
        this.previewArea.innerHTML = '';

        if (file.type.startsWith('image/')) {
            // Show image preview
            const img = document.createElement('img');
            img.src = dataUrl;
            img.className = 'preview-image';
            this.previewArea.appendChild(img);
        } else {
            // Show file icon
            const icon = document.createElement('div');
            icon.style.textAlign = 'center';
            icon.style.padding = '40px';
            icon.style.fontSize = '64px';
            icon.textContent = this.getFileIcon(file.type);
            this.previewArea.appendChild(icon);
        }
    }

    displayFileInfo(file) {
        const sizeKB = (file.size / 1024).toFixed(1);
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        const displaySize = file.size > 1024 * 1024 ? `${sizeMB} MB` : `${sizeKB} KB`;

        this.fileInfo.innerHTML = `
            <div class="file-info-item">
                <span class="file-info-label">Filename:</span>
                <span class="file-info-value">${file.name}</span>
            </div>
            <div class="file-info-item">
                <span class="file-info-label">Size:</span>
                <span class="file-info-value">${displaySize}</span>
            </div>
            <div class="file-info-item">
                <span class="file-info-label">Type:</span>
                <span class="file-info-value">${file.type || 'unknown'}</span>
            </div>
        `;
    }

    getFileIcon(mimeType) {
        if (mimeType.startsWith('image/')) return '🖼️';
        if (mimeType.startsWith('text/')) return '📄';
        if (mimeType.includes('pdf')) return '📕';
        if (mimeType.includes('json')) return '📊';
        if (mimeType.includes('xml') || mimeType.includes('yaml')) return '📋';
        if (mimeType.includes('zip') || mimeType.includes('tar')) return '📦';
        return '📁';
    }

    connect() {
        console.log('Connecting to', this.wsUrl);

        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.updateConnectionStatus(true);
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
            this.updateConnectionStatus(false);

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
    }

    handleMessageStart(event) {
        console.log('Message start:', event);
        this.currentMessageContent = '';

        // Show processing card
        this.addResultCard({
            type: 'processing',
            title: '⏳ Processing...',
            content: 'Analyzing your content...',
        });
    }

    handleMessageChunk(event) {
        this.currentMessageContent += event.content;
    }

    handleMessageComplete(event) {
        console.log('Message complete:', event);

        // Remove processing card
        this.removeProcessingCards();

        // Add complete result card
        this.addResultCard({
            type: 'complete',
            title: '✅ Analysis Complete',
            content: event.content,
            metadata: event.metadata,
        });

        // Re-enable buttons
        this.isProcessing = false;
        this.analyzeBtn.disabled = false;
        this.clearBtn.disabled = false;
    }

    handleError(event) {
        console.error('Error event:', event);

        this.removeProcessingCards();
        this.addResultCard({
            type: 'error',
            title: '❌ Error',
            content: event.error.message || 'An error occurred',
        });

        this.isProcessing = false;
        this.analyzeBtn.disabled = false;
        this.clearBtn.disabled = false;
    }

    // UI updates

    updateConnectionStatus(connected) {
        if (connected) {
            this.statusIndicator.className = 'status-indicator status-connected';
            this.statusText.textContent = 'Connected';
        } else {
            this.statusIndicator.className = 'status-indicator status-disconnected';
            this.statusText.textContent = 'Disconnected';
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

        let html = `<h3>${config.title}</h3>`;
        html += `<div class="result-content">${this.escapeHtml(config.content)}</div>`;

        if (config.metadata) {
            html += '<div style="margin-top: 15px; font-size: 12px; color: #999;">';
            html += `Processing time: ${config.metadata.processing_time?.toFixed(2) || 0}s`;
            html += '</div>';
        }

        card.innerHTML = html;

        // Add to top of results
        this.resultsContent.insertBefore(card, this.resultsContent.firstChild);

        // Limit to 10 cards
        while (this.resultsContent.children.length > 10) {
            this.resultsContent.removeChild(this.resultsContent.lastChild);
        }
    }

    removeProcessingCards() {
        const processingCards = this.resultsContent.querySelectorAll('.result-card.processing');
        processingCards.forEach((card) => card.remove());
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
    client = new MultimodalClient();
    client.connect();
});

// Global functions for UI interactions

function analyzeContent() {
    if (!client.isConnected || client.isProcessing || !client.currentFile) {
        return;
    }

    client.isProcessing = true;
    client.analyzeBtn.disabled = true;
    client.clearBtn.disabled = true;

    const query = client.queryInput.value.trim() || 'Analyze this content';
    const file = client.currentFile;

    let message;

    if (file.type.startsWith('image/')) {
        // Send as image
        message = {
            type: 'image',
            message: query,
            image_data: client.currentFileData,
            image_format: file.type.split('/')[1],
            image_size: file.size,
        };
    } else {
        // Send as file
        message = {
            type: 'file',
            message: query,
            file_data: client.currentFileData,
            file_name: file.name,
            file_size: file.size,
            file_type: file.type || 'unknown',
        };
    }

    client.send(message);
}

function clearContent() {
    client.currentFile = null;
    client.currentFileData = null;
    client.previewContainer.style.display = 'none';
    client.fileInput.value = '';
    client.queryInput.value = '';
    client.analyzeBtn.disabled = true;
    client.clearBtn.disabled = true;
}
