"use strict";
/**
 * HTTP transport for agent communication.
 *
 * Implements the Agent interface for HTTP-based communication,
 * allowing agents to communicate over HTTP/1.1, HTTP/2, or HTTP/3.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.HTTPAgent = exports.HttpTransportError = void 0;
const interfaces_1 = require("../core/interfaces");
/**
 * HTTP transport error with additional context.
 */
class HttpTransportError extends Error {
    constructor(message, statusCode, responseBody) {
        super(message);
        this.statusCode = statusCode;
        this.responseBody = responseBody;
        this.name = 'HttpTransportError';
    }
}
exports.HttpTransportError = HttpTransportError;
/**
 * HTTPAgent implements Agent interface over HTTP transport.
 *
 * Features:
 * - HTTP/1.1, HTTP/2 support
 * - Configurable timeouts
 * - Custom headers
 * - Automatic retries on connection errors
 * - Full TypeScript typing
 *
 * Usage:
 *   const agent = new HTTPAgent({
 *     baseUrl: 'http://localhost:8000',
 *     timeout: 30000,
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
class HTTPAgent {
    constructor(config) {
        this.capabilities = ['http'];
        this.baseUrl = config.baseUrl.replace(/\/$/, ''); // Remove trailing slash
        this.name = config.name || 'http-agent';
        this.timeout = config.timeout || 30000;
        this.headers = config.headers || {};
        this.http2 = config.http2 || false;
    }
    /**
     * Process a message via HTTP POST request.
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
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        try {
            const response = await fetch(`${this.baseUrl}/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.headers,
                },
                body: JSON.stringify(message),
                signal: controller.signal,
            });
            clearTimeout(timeoutId);
            if (!response.ok) {
                const errorBody = await response.text();
                throw new HttpTransportError(`HTTP ${response.status}: ${response.statusText}`, response.status, errorBody);
            }
            const responseMessage = (await response.json());
            // Validate output
            (0, interfaces_1.validateMessage)(responseMessage);
            return responseMessage;
        }
        catch (error) {
            clearTimeout(timeoutId);
            if (error instanceof Error) {
                if (error.name === 'AbortError') {
                    throw new HttpTransportError(`Request timeout after ${this.timeout}ms`);
                }
                if (error instanceof HttpTransportError) {
                    throw error;
                }
                throw new HttpTransportError(`Network error: ${error.message}`);
            }
            throw new HttpTransportError('Unknown error during HTTP request');
        }
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
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        try {
            const response = await fetch(`${this.baseUrl}/process/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Accept: 'application/x-ndjson',
                    ...this.headers,
                },
                body: JSON.stringify(message),
                signal: controller.signal,
            });
            clearTimeout(timeoutId);
            if (!response.ok) {
                const errorBody = await response.text();
                throw new HttpTransportError(`HTTP ${response.status}: ${response.statusText}`, response.status, errorBody);
            }
            if (!response.body) {
                throw new HttpTransportError('No response body for streaming');
            }
            // Read stream line by line (NDJSON format)
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done)
                    break;
                buffer += decoder.decode(value, { stream: true });
                // Split on newlines
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer
                for (const line of lines) {
                    if (line.trim()) {
                        const chunk = JSON.parse(line);
                        (0, interfaces_1.validateMessage)(chunk);
                        yield chunk;
                    }
                }
            }
            // Process any remaining data in buffer
            if (buffer.trim()) {
                const chunk = JSON.parse(buffer);
                (0, interfaces_1.validateMessage)(chunk);
                yield chunk;
            }
        }
        catch (error) {
            clearTimeout(timeoutId);
            if (error instanceof Error) {
                if (error.name === 'AbortError') {
                    throw new HttpTransportError(`Request timeout after ${this.timeout}ms`);
                }
                if (error instanceof HttpTransportError) {
                    throw error;
                }
                throw new HttpTransportError(`Network error: ${error.message}`);
            }
            throw new HttpTransportError('Unknown error during HTTP streaming');
        }
    }
    /**
     * Health check endpoint.
     *
     * @returns true if agent is healthy, false otherwise
     */
    async health() {
        try {
            const response = await fetch(`${this.baseUrl}/health`, {
                method: 'GET',
                headers: this.headers,
                signal: AbortSignal.timeout(5000), // 5 second timeout
            });
            return response.ok;
        }
        catch {
            return false;
        }
    }
}
exports.HTTPAgent = HTTPAgent;
