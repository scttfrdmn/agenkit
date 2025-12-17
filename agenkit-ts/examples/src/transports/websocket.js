"use strict";
/**
 * WebSocket transport for agent communication.
 *
 * Implements the Agent interface for WebSocket-based communication,
 * providing real-time bidirectional communication with automatic reconnection.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.WebSocketAgent = exports.WebSocketTransportError = void 0;
const ws_1 = __importDefault(require("ws"));
const interfaces_1 = require("../core/interfaces");
/**
 * WebSocket transport error.
 */
class WebSocketTransportError extends Error {
    constructor(message, code) {
        super(message);
        this.code = code;
        this.name = 'WebSocketTransportError';
    }
}
exports.WebSocketTransportError = WebSocketTransportError;
/**
 * WebSocketAgent implements Agent interface over WebSocket transport.
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Ping/pong keepalive
 * - Binary and text frame support
 * - Request/response correlation
 * - Full TypeScript typing
 *
 * Usage:
 *   const agent = new WebSocketAgent({
 *     url: 'ws://localhost:8080',
 *     maxRetries: 5,
 *   });
 *
 *   await agent.connect();
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
class WebSocketAgent {
    constructor(config) {
        this.capabilities = ['websocket'];
        this.ws = null;
        this.connected = false;
        this.reconnectLock = false;
        this.pendingRequests = new Map();
        this.requestIdCounter = 0;
        this.pingIntervalId = null;
        this.url = config.url;
        this.name = config.name || 'websocket-agent';
        this.maxRetries = config.maxRetries || 5;
        this.initialRetryDelay = config.initialRetryDelay || 1000;
        this.pingInterval = config.pingInterval || 30000;
        this.pingTimeout = config.pingTimeout || 10000;
        this.headers = config.headers || {};
    }
    /**
     * Establish WebSocket connection.
     */
    async connect() {
        await this.connectWithRetry();
    }
    /**
     * Connect with exponential backoff retry logic.
     */
    async connectWithRetry() {
        let lastError = null;
        let retryDelay = this.initialRetryDelay;
        for (let attempt = 0; attempt < this.maxRetries; attempt++) {
            try {
                await this.establishConnection();
                this.setupPingInterval();
                return;
            }
            catch (error) {
                lastError = error;
                if (attempt < this.maxRetries - 1) {
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                    retryDelay *= 2; // Exponential backoff
                }
            }
        }
        throw new WebSocketTransportError(`Failed to connect after ${this.maxRetries} attempts: ${lastError?.message}`, 'CONNECTION_FAILED');
    }
    /**
     * Establish WebSocket connection.
     */
    establishConnection() {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new ws_1.default(this.url, {
                    headers: this.headers,
                });
                this.ws.on('open', () => {
                    this.connected = true;
                    resolve();
                });
                this.ws.on('error', (error) => {
                    if (!this.connected) {
                        reject(new WebSocketTransportError(`Connection error: ${error.message}`, 'CONNECTION_ERROR'));
                    }
                });
                this.ws.on('close', () => {
                    this.connected = false;
                    this.cleanup();
                });
                this.ws.on('message', (data) => {
                    this.handleMessage(data);
                });
                this.ws.on('pong', () => {
                    // Pong received, connection is alive
                });
            }
            catch (error) {
                reject(error);
            }
        });
    }
    /**
     * Ensure connection is established, reconnect if necessary.
     */
    async ensureConnected() {
        if (!this.isConnected) {
            if (!this.reconnectLock) {
                this.reconnectLock = true;
                try {
                    await this.connectWithRetry();
                }
                finally {
                    this.reconnectLock = false;
                }
            }
            else {
                // Wait for ongoing reconnection
                while (this.reconnectLock) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
            }
        }
    }
    /**
     * Setup ping interval for keepalive.
     */
    setupPingInterval() {
        if (this.pingIntervalId) {
            clearInterval(this.pingIntervalId);
        }
        this.pingIntervalId = setInterval(() => {
            if (this.ws && this.connected) {
                this.ws.ping();
            }
        }, this.pingInterval);
    }
    /**
     * Handle incoming WebSocket message.
     */
    handleMessage(data) {
        try {
            const message = JSON.parse(data.toString());
            // Check if this is a response to a pending request
            if (message._requestId) {
                const pending = this.pendingRequests.get(message._requestId);
                if (pending) {
                    this.pendingRequests.delete(message._requestId);
                    // Remove internal field before resolving
                    delete message._requestId;
                    pending.resolve(message);
                }
            }
        }
        catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }
    /**
     * Process a message via WebSocket.
     *
     * @param message Input message
     * @returns Response message
     */
    async process(message) {
        // Validate input
        (0, interfaces_1.validateMessage)(message);
        // Add timestamp if missing
        if (!message.timestamp) {
            message.timestamp = new Date().toISOString();
        }
        // Ensure connected
        await this.ensureConnected();
        if (!this.ws) {
            throw new WebSocketTransportError('Not connected', 'NOT_CONNECTED');
        }
        // Generate request ID for correlation
        const requestId = `req_${++this.requestIdCounter}_${Date.now()}`;
        // Create promise for response
        const responsePromise = new Promise((resolve, reject) => {
            this.pendingRequests.set(requestId, { resolve, reject });
            // Set timeout
            setTimeout(() => {
                if (this.pendingRequests.has(requestId)) {
                    this.pendingRequests.delete(requestId);
                    reject(new WebSocketTransportError('Request timeout', 'TIMEOUT'));
                }
            }, 30000); // 30 second timeout
        });
        // Send message with request ID
        const messageWithId = { ...message, _requestId: requestId };
        this.ws.send(JSON.stringify(messageWithId));
        return responsePromise;
    }
    /**
     * Process a message with streaming response.
     *
     * @param message Input message
     * @returns Async iterator of response chunks
     */
    async *processStream(message) {
        // Validate input
        (0, interfaces_1.validateMessage)(message);
        // Add timestamp if missing
        if (!message.timestamp) {
            message.timestamp = new Date().toISOString();
        }
        // Ensure connected
        await this.ensureConnected();
        if (!this.ws) {
            throw new WebSocketTransportError('Not connected', 'NOT_CONNECTED');
        }
        // Generate request ID
        const requestId = `stream_${++this.requestIdCounter}_${Date.now()}`;
        // Create async queue for chunks
        const chunkQueue = [];
        let streamEnded = false;
        let streamError = null;
        // Setup handler for this stream
        const originalHandler = this.ws.listeners('message')[0];
        const streamHandler = (data) => {
            try {
                const msg = JSON.parse(data.toString());
                if (msg._requestId === requestId) {
                    if (msg._streamEnd) {
                        streamEnded = true;
                    }
                    else {
                        delete msg._requestId;
                        chunkQueue.push(msg);
                    }
                }
            }
            catch (error) {
                streamError = error;
            }
        };
        this.ws.on('message', streamHandler);
        try {
            // Send streaming request
            const streamMessage = {
                ...message,
                _requestId: requestId,
                _stream: true
            };
            this.ws.send(JSON.stringify(streamMessage));
            // Yield chunks as they arrive
            while (!streamEnded && !streamError) {
                if (chunkQueue.length > 0) {
                    yield chunkQueue.shift();
                }
                else {
                    // Wait a bit before checking again
                    await new Promise(resolve => setTimeout(resolve, 10));
                }
            }
            // Yield any remaining chunks
            while (chunkQueue.length > 0) {
                yield chunkQueue.shift();
            }
            if (streamError) {
                throw streamError;
            }
        }
        finally {
            // Remove stream handler
            this.ws.removeListener('message', streamHandler);
        }
    }
    /**
     * Close WebSocket connection.
     */
    async close() {
        this.cleanup();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
    /**
     * Cleanup resources.
     */
    cleanup() {
        if (this.pingIntervalId) {
            clearInterval(this.pingIntervalId);
            this.pingIntervalId = null;
        }
        // Reject all pending requests
        for (const [requestId, pending] of this.pendingRequests) {
            pending.reject(new WebSocketTransportError('Connection closed', 'CONNECTION_CLOSED'));
        }
        this.pendingRequests.clear();
    }
    /**
     * Check if WebSocket is connected.
     */
    get isConnected() {
        return this.connected && this.ws !== null && this.ws.readyState === ws_1.default.OPEN;
    }
    /**
     * Health check.
     *
     * @returns true if connected, false otherwise
     */
    async health() {
        return this.isConnected;
    }
}
exports.WebSocketAgent = WebSocketAgent;
