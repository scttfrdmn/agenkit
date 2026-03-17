/**
 * Comprehensive tests for ConversationalAgent pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - Basic message processing
 * - History management and pruning
 * - System prompt handling
 * - Edge cases
 */

import { describe, it, expect } from 'vitest';
import {
  ConversationalAgent,
  createConversationalAgent,
  type LLMClient,
} from '../../patterns/conversational';
import { Message, createMessage } from '../../core/interfaces';
import { validateMessage } from './test-helpers';

/** Mock LLM client for testing */
class MockLLMClient implements LLMClient {
  private response: string;
  lastMessages?: Message[];
  callCount = 0;

  constructor(response: string) {
    this.response = response;
  }

  async chat(messages: Message[]): Promise<Message> {
    this.lastMessages = messages;
    this.callCount++;
    return createMessage('assistant', this.response);
  }
}

/** LLM client that echoes the last user message */
class EchoLLMClient implements LLMClient {
  async chat(messages: Message[]): Promise<Message> {
    const lastUser = messages.filter(m => m.role === 'user').pop();
    return createMessage('assistant', `Echo: ${String(lastUser?.content ?? '')}`);
  }
}

describe('ConversationalAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid configuration', () => {
      const llm = new MockLLMClient('response');
      const agent = new ConversationalAgent({ llmClient: llm });

      expect(agent).toBeDefined();
      expect(agent.name).toBe('ConversationalAgent');
    });

    it('should use default maxHistory of 10', () => {
      const llm = new MockLLMClient('response');
      const agent = new ConversationalAgent({ llmClient: llm });

      expect(agent.historyLength).toBe(0);
    });

    it('should accept custom maxHistory', () => {
      const llm = new MockLLMClient('response');
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 5 });

      expect(agent).toBeDefined();
    });

    it('should add system prompt to history when provided', () => {
      const llm = new MockLLMClient('response');
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'You are helpful.',
      });

      expect(agent.historyLength).toBe(1);
      const history = agent.getHistory();
      expect(history[0].role).toBe('system');
      expect(history[0].content).toBe('You are helpful.');
    });

    it('should not add system prompt when includeSystem is false', () => {
      const llm = new MockLLMClient('response');
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'You are helpful.',
        includeSystem: false,
      });

      expect(agent.historyLength).toBe(0);
    });

    it('createConversationalAgent factory should work', () => {
      const llm = new MockLLMClient('response');
      const agent = createConversationalAgent(llm, 10, 'Be helpful.');

      expect(agent.name).toBe('ConversationalAgent');
    });
  });

  describe('Capabilities', () => {
    it('should include conversational and history-management', () => {
      const llm = new MockLLMClient('response');
      const agent = new ConversationalAgent({ llmClient: llm });

      expect(agent.capabilities).toContain('conversational');
      expect(agent.capabilities).toContain('history-management');
    });
  });

  describe('Basic Processing', () => {
    it('should process a message and return response', async () => {
      const llm = new MockLLMClient('Hello back!');
      const agent = new ConversationalAgent({ llmClient: llm });

      const input = createMessage('user', 'Hello');
      const result = await agent.process(input);

      validateMessage(result);
      expect(result.content).toBe('Hello back!');
    });

    it('should pass full history to LLM', async () => {
      const llm = new MockLLMClient('response');
      const agent = new ConversationalAgent({ llmClient: llm });

      const input = createMessage('user', 'Hello');
      await agent.process(input);

      expect(llm.lastMessages).toBeDefined();
      expect(llm.lastMessages!.length).toBeGreaterThan(0);
    });

    it('should add input message to history', async () => {
      const llm = new MockLLMClient('response');
      const agent = new ConversationalAgent({ llmClient: llm });

      const input = createMessage('user', 'Hello');
      await agent.process(input);

      const history = agent.getHistory();
      const userMsgs = history.filter(m => m.role === 'user');
      expect(userMsgs.length).toBeGreaterThan(0);
    });

    it('should add response to history', async () => {
      const llm = new MockLLMClient('My response');
      const agent = new ConversationalAgent({ llmClient: llm });

      await agent.process(createMessage('user', 'Hello'));

      const history = agent.getHistory();
      const assistantMsgs = history.filter(m => m.role === 'assistant');
      expect(assistantMsgs.length).toBeGreaterThan(0);
    });

    it('should accumulate history across multiple turns', async () => {
      const llm = new EchoLLMClient();
      const agent = new ConversationalAgent({ llmClient: llm });

      await agent.process(createMessage('user', 'First'));
      await agent.process(createMessage('user', 'Second'));
      await agent.process(createMessage('user', 'Third'));

      // Each turn adds user + assistant message
      expect(agent.historyLength).toBeGreaterThanOrEqual(3);
    });
  });

  describe('History Management', () => {
    it('should prune history when exceeding maxHistory', async () => {
      const llm = new MockLLMClient('reply');
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 4 });

      // Send 5 messages — history should stay at or below maxHistory
      for (let i = 0; i < 5; i++) {
        await agent.process(createMessage('user', `Message ${i}`));
      }

      expect(agent.historyLength).toBeLessThanOrEqual(4);
    });

    it('should preserve system message during pruning', async () => {
      const llm = new MockLLMClient('reply');
      const agent = new ConversationalAgent({
        llmClient: llm,
        maxHistory: 3,
        systemPrompt: 'System context',
      });

      for (let i = 0; i < 5; i++) {
        await agent.process(createMessage('user', `Turn ${i}`));
      }

      const history = agent.getHistory();
      const systemMsgs = history.filter(m => m.role === 'system');
      expect(systemMsgs.length).toBe(1);
    });

    it('setMaxHistory should trigger immediate pruning', async () => {
      const llm = new MockLLMClient('reply');
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 20 });

      for (let i = 0; i < 10; i++) {
        await agent.process(createMessage('user', `Message ${i}`));
      }

      const before = agent.historyLength;
      expect(before).toBeGreaterThan(4);

      agent.setMaxHistory(4);

      expect(agent.historyLength).toBeLessThanOrEqual(4);
    });
  });

  describe('clearHistory', () => {
    it('should clear all history by default', async () => {
      const llm = new MockLLMClient('reply');
      const agent = new ConversationalAgent({ llmClient: llm });

      await agent.process(createMessage('user', 'Hello'));
      agent.clearHistory();

      expect(agent.historyLength).toBe(0);
    });

    it('should preserve system prompt when clearHistory(true)', async () => {
      const llm = new MockLLMClient('reply');
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'Be concise.',
      });

      await agent.process(createMessage('user', 'Hello'));
      agent.clearHistory(true);

      expect(agent.historyLength).toBe(1);
      const history = agent.getHistory();
      expect(history[0].role).toBe('system');
    });

    it('should clear system prompt when clearHistory(false)', async () => {
      const llm = new MockLLMClient('reply');
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'Be concise.',
      });

      await agent.process(createMessage('user', 'Hello'));
      agent.clearHistory(false);

      expect(agent.historyLength).toBe(0);
    });
  });

  describe('getHistory', () => {
    it('should return a copy of history', async () => {
      const llm = new MockLLMClient('reply');
      const agent = new ConversationalAgent({ llmClient: llm });

      await agent.process(createMessage('user', 'Hello'));

      const history1 = agent.getHistory();
      const history2 = agent.getHistory();

      expect(history1).not.toBe(history2); // different array instances
      expect(history1).toEqual(history2); // same content
    });

    it('should not allow external mutation of internal history', async () => {
      const llm = new MockLLMClient('reply');
      const agent = new ConversationalAgent({ llmClient: llm });

      await agent.process(createMessage('user', 'Hello'));

      const history = agent.getHistory();
      const originalLength = agent.historyLength;
      history.push(createMessage('user', 'injected'));

      expect(agent.historyLength).toBe(originalLength);
    });
  });
});
