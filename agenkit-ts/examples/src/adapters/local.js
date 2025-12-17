"use strict";
/**
 * Local agent adapter - wraps functions as agents.
 *
 * Enables using simple TypeScript functions as agents without implementing
 * the full Agent interface.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.LocalAgent = void 0;
exports.createEchoAgent = createEchoAgent;
exports.createCounterAgent = createCounterAgent;
const interfaces_1 = require("../core/interfaces");
/**
 * LocalAgent wraps a function to implement the Agent interface.
 *
 * Features:
 * - Zero network overhead
 * - Full async/await support
 * - Optional streaming support
 * - Automatic message validation
 *
 * Usage:
 *   const agent = new LocalAgent({
 *     name: 'echo',
 *     process: async (msg) => ({
 *       role: 'assistant',
 *       content: `Echo: ${msg.content}`,
 *     }),
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
class LocalAgent {
    constructor(config) {
        this.name = config.name;
        this.processFn = config.process;
        this.processStreamFn = config.processStream;
        this.capabilities = config.capabilities;
    }
    /**
     * Process a message through the wrapped function.
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
        // Process through function
        const response = await this.processFn(message);
        // Validate output
        (0, interfaces_1.validateMessage)(response);
        // Add timestamp to response if missing
        if (!response.timestamp) {
            response.timestamp = new Date().toISOString();
        }
        return response;
    }
    /**
     * Process a message with streaming response.
     *
     * @param message Input message
     * @returns Async iterator of response chunks
     */
    async *processStream(message) {
        if (!this.processStreamFn) {
            throw new Error(`Agent ${this.name} does not support streaming`);
        }
        // Validate input
        (0, interfaces_1.validateMessage)(message);
        // Add timestamp if missing
        if (!message.timestamp) {
            message.timestamp = new Date().toISOString();
        }
        // Stream through function
        for await (const chunk of this.processStreamFn(message)) {
            // Validate each chunk
            (0, interfaces_1.validateMessage)(chunk);
            // Add timestamp if missing
            if (!chunk.timestamp) {
                chunk.timestamp = new Date().toISOString();
            }
            yield chunk;
        }
    }
}
exports.LocalAgent = LocalAgent;
/**
 * Helper function to create a simple echo agent for testing.
 *
 * @param name Agent name
 * @returns Echo agent
 */
function createEchoAgent(name = 'echo') {
    return new LocalAgent({
        name,
        process: async (message) => (0, interfaces_1.createMessage)('assistant', `Echo: ${message.content}`),
        capabilities: ['echo'],
    });
}
/**
 * Helper function to create a simple counter agent for testing.
 *
 * @param name Agent name
 * @returns Counter agent that increments a counter on each message
 */
function createCounterAgent(name = 'counter') {
    let count = 0;
    return new LocalAgent({
        name,
        process: async (message) => {
            count++;
            return (0, interfaces_1.createMessage)('assistant', `Message ${count}: ${message.content}`, {
                count,
            });
        },
        capabilities: ['counter'],
    });
}
