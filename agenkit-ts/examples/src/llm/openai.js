"use strict";
/**
 * OpenAI LLM adapter.
 *
 * Implements Agent interface for OpenAI's Chat Completion API.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.OpenAIAgent = void 0;
const openai_1 = __importDefault(require("openai"));
const interfaces_1 = require("../core/interfaces");
/**
 * OpenAIAgent implements Agent interface using OpenAI's API.
 *
 * Features:
 * - Full OpenAI Chat API support
 * - Streaming support
 * - Configurable model and parameters
 * - Automatic message format conversion
 *
 * Usage:
 *   const agent = new OpenAIAgent({
 *     apiKey: process.env.OPENAI_API_KEY!,
 *     model: 'gpt-4o',
 *     temperature: 0.7,
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
class OpenAIAgent {
    constructor(config) {
        this.capabilities = ['openai', 'chat', 'streaming'];
        this.name = config.name || 'openai';
        this.client = new openai_1.default({ apiKey: config.apiKey });
        this.model = config.model || 'gpt-4o';
        this.temperature = config.temperature || 0.7;
        this.maxTokens = config.maxTokens;
        this.options = config.options || {};
    }
    /**
     * Convert agenkit Message to OpenAI message format.
     */
    toOpenAIMessage(message) {
        const content = typeof message.content === 'string' ? message.content : JSON.stringify(message.content);
        switch (message.role) {
            case 'user':
                return { role: 'user', content };
            case 'assistant':
                return { role: 'assistant', content };
            case 'system':
                return { role: 'system', content };
            default:
                // Default to user for unknown roles
                return { role: 'user', content };
        }
    }
    /**
     * Process a message using OpenAI API.
     *
     * @param message Input message
     * @returns Response message
     */
    async process(message) {
        const openaiMessage = this.toOpenAIMessage(message);
        const completion = (await this.client.chat.completions.create({
            model: this.model,
            messages: [openaiMessage],
            temperature: this.temperature,
            max_tokens: this.maxTokens,
            stream: false,
            ...this.options,
        }));
        const choice = completion.choices[0];
        const content = choice.message.content || '';
        return (0, interfaces_1.createMessage)('assistant', content, {
            model: this.model,
            finishReason: choice.finish_reason,
            usage: completion.usage,
            id: completion.id,
        });
    }
    /**
     * Process a message with streaming response.
     *
     * @param message Input message
     * @returns Async iterator of response chunks
     */
    async *processStream(message) {
        const openaiMessage = this.toOpenAIMessage(message);
        const stream = (await this.client.chat.completions.create({
            model: this.model,
            messages: [openaiMessage],
            temperature: this.temperature,
            max_tokens: this.maxTokens,
            stream: true,
            ...this.options,
        }));
        for await (const chunk of stream) {
            const delta = chunk.choices[0]?.delta;
            if (delta?.content) {
                yield (0, interfaces_1.createMessage)('assistant', delta.content, {
                    model: this.model,
                    id: chunk.id,
                });
            }
        }
    }
}
exports.OpenAIAgent = OpenAIAgent;
