"use strict";
/**
 * Conversational Agent Pattern
 *
 * A conversational agent maintains context across multiple turns of conversation,
 * managing message history and ensuring responses take into account previous exchanges.
 *
 * Key Features:
 * - Message history management
 * - Context window limiting
 * - Automatic history pruning
 * - Support for system prompts
 *
 * Example:
 * ```typescript
 * const agent = new ConversationalAgent({
 *   llmClient: myLLMClient,
 *   maxHistory: 10,
 *   systemPrompt: "You are a helpful assistant."
 * });
 *
 * // First turn
 * const response1 = await agent.process(
 *   createMessage('user', 'My name is Alice')
 * );
 *
 * // Second turn - agent remembers the name
 * const response2 = await agent.process(
 *   createMessage('user', "What's my name?")
 * );
 * // Response: "Your name is Alice."
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConversationalAgent = void 0;
exports.createConversationalAgent = createConversationalAgent;
const interfaces_1 = require("../core/interfaces");
/**
 * Agent that maintains conversation history for context-aware responses.
 *
 * This agent stores previous messages and includes them when processing new messages,
 * allowing the LLM to maintain context across multiple turns.
 *
 * History Management:
 * - Messages are pruned when history exceeds maxHistory
 * - System messages are always preserved
 * - Oldest user/assistant messages are removed first
 * - Both input and response messages are added to history
 *
 * Performance:
 * - O(1) message append
 * - O(n) history pruning (only when limit exceeded)
 * - Memory: O(maxHistory) messages
 */
class ConversationalAgent {
    constructor(config) {
        this.name = 'ConversationalAgent';
        this.llmClient = config.llmClient;
        this.maxHistory = config.maxHistory || 10;
        this.systemPrompt = config.systemPrompt;
        this.includeSystem = config.includeSystem !== undefined ? config.includeSystem : true;
        this.history = [];
        // Add system prompt to history if provided
        if (this.systemPrompt && this.includeSystem) {
            this.history.push((0, interfaces_1.createMessage)('system', this.systemPrompt));
        }
    }
    /**
     * Process a message with full conversation context.
     *
     * The message is added to history, and the LLM generates a response
     * considering all previous messages within the history limit.
     *
     * @param message The incoming user message
     * @returns The agent's response message
     *
     * Note:
     * Both the input message and the response are added to history.
     * If history exceeds maxHistory, oldest non-system messages are removed.
     */
    async process(message) {
        // Add user message to history
        this.history.push(message);
        // Prune history if needed (keep system prompt if present)
        this.pruneHistory();
        // Generate response with full context
        const response = await this.llmClient.chat([...this.history]);
        // Add response to history
        this.history.push(response);
        // Prune again after adding response
        this.pruneHistory();
        return response;
    }
    /**
     * Prune history to stay within maxHistory limit.
     *
     * System messages are preserved, and oldest user/assistant messages
     * are removed first.
     */
    pruneHistory() {
        if (this.history.length <= this.maxHistory) {
            return;
        }
        // Separate system messages from conversation
        const systemMessages = this.history.filter(msg => msg.role === 'system');
        const conversationMessages = this.history.filter(msg => msg.role !== 'system');
        // Keep only the most recent conversation messages
        const messagesToKeep = this.maxHistory - systemMessages.length;
        const keptConversation = messagesToKeep > 0
            ? conversationMessages.slice(-messagesToKeep)
            : [];
        // Rebuild history with system messages first
        this.history = [...systemMessages, ...keptConversation];
    }
    /**
     * Clear conversation history.
     *
     * @param keepSystem Whether to preserve system prompt (default: true)
     */
    clearHistory(keepSystem = true) {
        if (keepSystem && this.systemPrompt && this.includeSystem) {
            this.history = [(0, interfaces_1.createMessage)('system', this.systemPrompt)];
        }
        else {
            this.history = [];
        }
    }
    /**
     * Get current conversation history.
     *
     * @returns Copy of current history
     */
    getHistory() {
        return [...this.history];
    }
    /**
     * Get number of messages in history.
     */
    get historyLength() {
        return this.history.length;
    }
    /**
     * Set maximum history size.
     *
     * If new max is smaller than current history, history will be pruned immediately.
     *
     * @param max New maximum history size
     */
    setMaxHistory(max) {
        this.maxHistory = max;
        this.pruneHistory();
    }
    get capabilities() {
        return ['conversational', 'history-management'];
    }
}
exports.ConversationalAgent = ConversationalAgent;
/**
 * Create a conversational agent with simple configuration.
 *
 * @param llmClient LLM client for generating responses
 * @param maxHistory Maximum conversation history length
 * @param systemPrompt Optional system prompt
 * @returns ConversationalAgent instance
 */
function createConversationalAgent(llmClient, maxHistory, systemPrompt) {
    return new ConversationalAgent({
        llmClient,
        maxHistory,
        systemPrompt,
    });
}
