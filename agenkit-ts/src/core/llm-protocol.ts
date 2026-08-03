/**
 * Shared dispatch for calling an LLM adapter or an agent.
 *
 * Agenkit accumulated mutually incompatible ways to say "ask a model for a
 * response", and only one of them had any real implementation:
 *
 * | declared                       | implemented by                          |
 * |--------------------------------|-----------------------------------------|
 * | `complete(messages: Message[])`| all 6 shipped adapters                  |
 * | `chat(messages: Message[])`    | test doubles and examples only           |
 * | `process(message: Message)`    | every agent, incl. every pattern         |
 *
 * The consequence was that `ConversationalAgent` — which demanded `chat()` —
 * could not be used with any adapter the toolkit ships:
 *
 * ```
 * TypeError: this.llmClient.chat is not a function
 * ```
 *
 * It survived because every test double was shaped like the *call site* rather
 * than the *contract*, so the seam was never exercised against a real adapter.
 * See #805, and #802 for the same failure one layer down in Python.
 *
 * This module is the single place that resolves "what does this object respond
 * to", so a fourth spelling has one place to be rejected instead of three places
 * to appear. The order is deliberate: the contract adapters actually implement
 * first, the contract agents implement second, the deprecated one last.
 */

import { Message, createMessage } from './interfaces';

/**
 * An LLM adapter — the contract every shipped adapter implements.
 */
export interface CompletionClient {
  complete(messages: Message[]): Promise<Message>;
}

/**
 * An agent used as an LLM backend, as the Rust core does.
 */
export interface ProcessClient {
  process(message: Message): Promise<Message>;
}

/**
 * The deprecated protocol. Accepted for one release cycle; warns on use.
 *
 * @deprecated Implement {@link CompletionClient} instead. See #805.
 */
export interface ChatClient {
  chat(messages: Message[]): Promise<Message>;
}

/** Any client {@link completeMessages} accepts. */
export type AnyLLMClient = CompletionClient | ProcessClient | ChatClient;

const CHAT_DEPRECATION =
  'DeprecationWarning: passing an LLM client that only implements chat() is ' +
  'deprecated and will be removed in v2.0. Implement complete(messages) — the ' +
  'contract every shipped agenkit adapter uses — or process(message), the Agent ' +
  'contract. See #805.';

/**
 * Whether this client has already been warned about.
 *
 * Keyed on the client object so a long conversation warns once rather than once
 * per turn — an every-turn warning trains users to filter the channel, which
 * defeats the point of deprecating.
 */
const warnedClients = new WeakSet<object>();

function hasMethod(client: unknown, name: string): boolean {
  return typeof (client as Record<string, unknown> | null)?.[name] === 'function';
}

/**
 * Collapse a conversation into the single message the Agent contract takes.
 *
 * `Agent.process()` accepts one Message, so an agent used as a conversational
 * backend needs the history rendered into it. The `"{role}: {content}"` form
 * matches the Rust and Python cores so the three do not drift.
 *
 * @param messages Conversation history
 * @returns A single user message containing the rendered history
 */
export function flattenHistory(messages: Message[]): Message {
  const rendered = messages.map((m) => `${m.role}: ${String(m.content)}`).join('\n');
  return createMessage('user', rendered);
}

/**
 * Send a conversation to an adapter or agent and return the response.
 *
 * Dispatches in contract-priority order:
 *
 * 1. `complete(messages)` — what all shipped adapters implement.
 * 2. `process(message)` — the Agent contract, history flattened.
 * 3. `chat(messages)` — deprecated (#805), warns once per client.
 *
 * @param llm LLM adapter or agent
 * @param messages Conversation history
 * @returns The response message
 * @throws TypeError If the client implements none of the three
 */
export async function completeMessages(
  llm: AnyLLMClient,
  messages: Message[]
): Promise<Message> {
  if (hasMethod(llm, 'complete')) {
    return (llm as CompletionClient).complete(messages);
  }

  if (hasMethod(llm, 'process')) {
    return (llm as ProcessClient).process(flattenHistory(messages));
  }

  if (hasMethod(llm, 'chat')) {
    if (!warnedClients.has(llm as object)) {
      warnedClients.add(llm as object);
      console.warn(CHAT_DEPRECATION);
    }
    return (llm as ChatClient).chat(messages);
  }

  throw new TypeError(
    'LLM client must implement complete(messages) (the adapter contract), ' +
      'process(message) (the Agent contract), or the deprecated chat(messages). ' +
      `Got ${llm === null ? 'null' : typeof llm} with none of them.`
  );
}
