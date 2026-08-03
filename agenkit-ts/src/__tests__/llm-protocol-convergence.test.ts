/**
 * Tests that the patterns work with the LLM adapters agenkit actually ships (#805).
 *
 * `LLMClient` used to require `chat()`. Not one of the six shipped adapters has a
 * `chat()` — they all implement `complete(messages)` — so `ConversationalAgent`
 * and `PlanningAgent` could not be used with any real LLM:
 *
 * ```
 * TypeError: this.llmClient.chat is not a function
 * ```
 *
 * Every test double in the suite implemented `chat()`, because each was written
 * against the *call site* rather than against the contract. So the seam was fully
 * covered by tests and none of them could ever have caught it.
 *
 * The load-bearing tests here are the ones driving a pattern with a client shaped
 * like a real adapter — `complete(messages): Promise<Message>`, exactly the
 * signature in `src/adapters/*.ts`.
 */

import { describe, expect, it, vi } from 'vitest';
import { Message, createMessage } from '../core/interfaces';
import { completeMessages, flattenHistory } from '../core/llm-protocol';
import { ConversationalAgent } from '../patterns/conversational';

/**
 * Shaped exactly like the shipped adapters: `async complete(messages: Message[])`.
 * See `src/adapters/anthropic.ts:233`, `openai.ts:243`, `gemini.ts:196`, etc.
 */
class AdapterShapedClient {
  calls: Message[][] = [];

  constructor(private response = 'adapter response') {}

  async complete(messages: Message[]): Promise<Message> {
    if (!Array.isArray(messages)) {
      throw new TypeError(`complete() takes Message[], got ${typeof messages} — see #802`);
    }
    this.calls.push([...messages]);
    return createMessage('assistant', this.response);
  }
}

/** The deprecated shape — i.e. what every old double looked like. */
class ChatOnlyClient {
  calls: Message[][] = [];

  constructor(private response = 'chat response') {}

  async chat(messages: Message[]): Promise<Message> {
    this.calls.push([...messages]);
    return createMessage('assistant', this.response);
  }
}

/** An agent used as a backend, as the Rust core does. */
class AgentBackend {
  readonly name = 'agent_backend';
  received: Message[] = [];

  constructor(private response = 'agent response') {}

  async process(message: Message): Promise<Message> {
    this.received.push(message);
    return createMessage('assistant', this.response);
  }
}

describe('LLM protocol convergence (#805)', () => {
  describe('real adapter contract', () => {
    it('drives ConversationalAgent with an adapter-shaped client', async () => {
      // Before the fix: TypeError: this.llmClient.chat is not a function
      const llm = new AdapterShapedClient('Hello!');
      const agent = new ConversationalAgent({ llmClient: llm });

      const response = await agent.process(createMessage('user', 'Hi'));

      expect(response.content).toBe('Hello!');
      expect(llm.calls).toHaveLength(1);
    });

    it('passes the real history as a Message array', async () => {
      // Not just "it didn't throw" — the adapter must receive the right shape.
      const llm = new AdapterShapedClient();
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'Be terse.',
      });

      await agent.process(createMessage('user', 'Q1'));
      await agent.process(createMessage('user', 'Q2'));

      expect(llm.calls[0].map((m) => m.role)).toEqual(['system', 'user']);
      expect(llm.calls[0].map((m) => m.content)).toEqual(['Be terse.', 'Q1']);
      // Second turn must carry the first exchange — that is the whole pattern.
      expect(llm.calls[1].map((m) => m.role)).toEqual(['system', 'user', 'assistant', 'user']);
    });
  });

  describe('agent backend', () => {
    it('accepts an agent as the LLM', async () => {
      const backend = new AgentBackend('from agent');
      const agent = new ConversationalAgent({ llmClient: backend });

      const response = await agent.process(createMessage('user', 'Q'));

      expect(response.content).toBe('from agent');
    });

    it('flattens history for the single-Message Agent contract', () => {
      // Matches the Python and Rust cores so the three cannot drift.
      const flat = flattenHistory([
        createMessage('system', 'S'),
        createMessage('user', 'Q'),
      ]);

      expect(flat.content).toBe('system: S\nuser: Q');
    });

    it('gives the agent a flattened message, not an array', async () => {
      const backend = new AgentBackend();
      const agent = new ConversationalAgent({ llmClient: backend, systemPrompt: 'S' });

      await agent.process(createMessage('user', 'Q'));

      expect(backend.received[0].content).toBe('system: S\nuser: Q');
    });
  });

  describe('deprecated chat()', () => {
    it('still works so copied example code does not break outright', async () => {
      const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const llm = new ChatOnlyClient('legacy!');
      const agent = new ConversationalAgent({ llmClient: llm });

      const response = await agent.process(createMessage('user', 'Q'));

      expect(response.content).toBe('legacy!');
      expect(warn).toHaveBeenCalledWith(expect.stringContaining('#805'));
      warn.mockRestore();
    });

    it('warns once per client, not once per turn', async () => {
      // An every-turn warning trains users to filter the channel, which defeats
      // the point of deprecating.
      const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const agent = new ConversationalAgent({ llmClient: new ChatOnlyClient() });

      await agent.process(createMessage('user', 'Q1'));
      await agent.process(createMessage('user', 'Q2'));
      await agent.process(createMessage('user', 'Q3'));

      expect(warn).toHaveBeenCalledTimes(1);
      warn.mockRestore();
    });
  });

  describe('dispatch order', () => {
    it('prefers complete() over chat() without warning', async () => {
      // A real adapter that gains a chat() shim must not start warning.
      const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const client = {
        async complete(): Promise<Message> {
          return createMessage('assistant', 'via complete');
        },
        async chat(): Promise<Message> {
          return createMessage('assistant', 'via chat');
        },
      };

      const response = await completeMessages(client, [createMessage('user', 'Q')]);

      expect(response.content).toBe('via complete');
      expect(warn).not.toHaveBeenCalled();
      warn.mockRestore();
    });

    it('prefers process() over chat()', async () => {
      const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const client = {
        async process(): Promise<Message> {
          return createMessage('assistant', 'via process');
        },
        async chat(): Promise<Message> {
          return createMessage('assistant', 'via chat');
        },
      };

      const response = await completeMessages(client, [createMessage('user', 'Q')]);

      expect(response.content).toBe('via process');
      warn.mockRestore();
    });

    it('names all three contracts when none is implemented', async () => {
      // The error has to say what to implement, not just what failed.
      await expect(
        completeMessages({} as never, [createMessage('user', 'Q')])
      ).rejects.toThrow(/complete\(messages\).*process\(message\).*chat\(messages\)/s);
    });

    it('rejects a non-function property of the right name', async () => {
      // `'complete' in client` would pass here; a callable check must not.
      await expect(
        completeMessages({ complete: 'not a function' } as never, [])
      ).rejects.toThrow(TypeError);
    });
  });
});
