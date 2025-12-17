"use strict";
/**
 * Anthropic (Claude) LLM adapter.
 *
 * Implements Agent interface for Anthropic's Messages API.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AnthropicAgent = void 0;
const sdk_1 = __importDefault(require("@anthropic-ai/sdk"));
const interfaces_1 = require("../core/interfaces");
/**
 * AnthropicAgent implements Agent interface using Anthropic's API.
 *
 * Features:
 * - Full Anthropic Messages API support
 * - Streaming support
 * - Configurable model and parameters
 * - Automatic message format conversion
 *
 * Usage:
 *   const agent = new AnthropicAgent({
 *     apiKey: process.env.ANTHROPIC_API_KEY!,
 *     model: 'claude-sonnet-4-20250514',
 *     temperature: 1.0,
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
class AnthropicAgent {
    constructor(config) {
        this.capabilities = ['anthropic', 'claude', 'chat', 'streaming'];
        this.name = config.name || 'claude';
        this.client = new sdk_1.default({ apiKey: config.apiKey });
        this.model = config.model || 'claude-sonnet-4-20250514';
        this.temperature = config.temperature || 1.0;
        this.maxTokens = config.maxTokens || 4096;
        this.options = config.options || {};
    }
    /**
     * Convert agenkit Message to Anthropic message format.
     */
    toAnthropicMessage(message) {
        const content = typeof message.content === 'string' ? message.content : JSON.stringify(message.content);
        // Anthropic only supports 'user' and 'assistant' roles
        const role = message.role === 'assistant' ? 'assistant' : 'user';
        return { role, content };
    }
    /**
     * Process a message using Anthropic API.
     *
     * @param message Input message
     * @returns Response message
     */
    async process(message) {
        const anthropicMessage = this.toAnthropicMessage(message);
        const response = (await this.client.messages.create({
            model: this.model,
            messages: [anthropicMessage],
            temperature: this.temperature,
            max_tokens: this.maxTokens,
            stream: false,
            ...this.options,
        }));
        // Extract text from content blocks
        const content = response.content
            .filter((block) => block.type === 'text')
            .map((block) => ('text' in block ? block.text : ''))
            .join('');
        return (0, interfaces_1.createMessage)('assistant', content, {
            model: this.model,
            stopReason: response.stop_reason,
            usage: response.usage,
            id: response.id,
        });
    }
    /**
     * Process a message with streaming response.
     *
     * @param message Input message
     * @returns Async iterator of response chunks
     */
    async *processStream(message) {
        const anthropicMessage = this.toAnthropicMessage(message);
        const stream = (await this.client.messages.create({
            model: this.model,
            messages: [anthropicMessage],
            temperature: this.temperature,
            max_tokens: this.maxTokens,
            stream: true,
            ...this.options,
        }));
        for await (const event of stream) {
            if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
                yield (0, interfaces_1.createMessage)('assistant', event.delta.text, {
                    model: this.model,
                });
            }
        }
    }
}
exports.AnthropicAgent = AnthropicAgent;
