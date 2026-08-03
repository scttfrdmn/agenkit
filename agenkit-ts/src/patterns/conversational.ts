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

import { Agent, Message, createMessage } from '../core/interfaces';
import { AnyLLMClient, completeMessages } from '../core/llm-protocol';

/**
 * LLM client interface for conversational agents.
 *
 * Accepts any of:
 * - `complete(messages)` — the contract all six shipped adapters implement
 * - `process(message)` — the Agent contract, so any agent can be a backend
 * - `chat(messages)` — deprecated (#805), warns on use
 *
 * Until v0.86.0 this interface declared only `chat()`, which **no** shipped
 * adapter had, so `ConversationalAgent` could not be used with any real LLM.
 * Every test double implemented `chat()` because each was written against the
 * call site rather than the contract, so the tests could never have caught it.
 */
export type LLMClient = AnyLLMClient;

/**
 * Configuration for ConversationalAgent.
 */
export interface ConversationalAgentConfig {
  /** LLM client that implements the chat interface */
  llmClient: LLMClient;
  /** Maximum number of messages to retain (default: 10) */
  maxHistory?: number;
  /** Optional system prompt to prepend to conversations */
  systemPrompt?: string;
  /** Whether to include system prompt in history count (default: true) */
  includeSystem?: boolean;
}

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
export class ConversationalAgent implements Agent {
  readonly name = 'ConversationalAgent';
  private llmClient: LLMClient;
  private maxHistory: number;
  private systemPrompt?: string;
  private includeSystem: boolean;
  private history: Message[];

  constructor(config: ConversationalAgentConfig) {
    this.llmClient = config.llmClient;
    this.maxHistory = config.maxHistory || 10;
    this.systemPrompt = config.systemPrompt;
    this.includeSystem = config.includeSystem !== undefined ? config.includeSystem : true;
    this.history = [];

    // Add system prompt to history if provided
    if (this.systemPrompt && this.includeSystem) {
      this.history.push(createMessage('system', this.systemPrompt));
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
  async process(message: Message): Promise<Message> {
    // Add user message to history
    this.history.push(message);

    // Prune history if needed (keep system prompt if present)
    this.pruneHistory();

    // Generate response with full context. Dispatch is shared so a client that
    // works with one pattern works with the others (#805).
    const response = await completeMessages(this.llmClient, [...this.history]);

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
  private pruneHistory(): void {
    if (this.history.length <= this.maxHistory) {
      return;
    }

    // Separate system messages from conversation
    const systemMessages = this.history.filter(msg => msg.role === 'system');
    const conversationMessages = this.history.filter(msg => msg.role !== 'system');

    // Keep only the most recent conversation messages
    const messagesToKeep = this.maxHistory - systemMessages.length;
    const keptConversation =
      messagesToKeep > 0
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
  clearHistory(keepSystem: boolean = true): void {
    if (keepSystem && this.systemPrompt && this.includeSystem) {
      this.history = [createMessage('system', this.systemPrompt)];
    } else {
      this.history = [];
    }
  }

  /**
   * Get current conversation history.
   *
   * @returns Copy of current history
   */
  getHistory(): Message[] {
    return [...this.history];
  }

  /**
   * Get number of messages in history.
   */
  get historyLength(): number {
    return this.history.length;
  }

  /**
   * Set maximum history size.
   *
   * If new max is smaller than current history, history will be pruned immediately.
   *
   * @param max New maximum history size
   */
  setMaxHistory(max: number): void {
    this.maxHistory = max;
    this.pruneHistory();
  }

  get capabilities(): string[] {
    return ['conversational', 'history-management'];
  }
}

/**
 * Create a conversational agent with simple configuration.
 *
 * @param llmClient LLM client for generating responses
 * @param maxHistory Maximum conversation history length
 * @param systemPrompt Optional system prompt
 * @returns ConversationalAgent instance
 */
export function createConversationalAgent(
  llmClient: LLMClient,
  maxHistory?: number,
  systemPrompt?: string
): ConversationalAgent {
  return new ConversationalAgent({
    llmClient,
    maxHistory,
    systemPrompt,
  });
}
