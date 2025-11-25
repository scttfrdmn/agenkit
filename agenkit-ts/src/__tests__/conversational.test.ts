/**
 * Tests for Conversational Agent Pattern.
 */

import {
  ConversationalAgent,
  LLMClient,
  createConversationalAgent,
} from '../patterns/conversational';
import { Message, createMessage } from '../core/interfaces';

/**
 * Mock LLM client for testing.
 */
class MockLLMClient implements LLMClient {
  private responses: string[];
  private callCount: number;
  public lastMessages: Message[];

  constructor(responses: string[]) {
    this.responses = responses;
    this.callCount = 0;
    this.lastMessages = [];
  }

  async chat(messages: Message[]): Promise<Message> {
    this.lastMessages = [...messages];
    if (this.callCount >= this.responses.length) {
      throw new Error('No more mock responses available');
    }
    const response = this.responses[this.callCount];
    this.callCount++;
    return createMessage('assistant', response);
  }
}

/**
 * Context-aware LLM client that echoes the last message.
 */
class EchoLLMClient implements LLMClient {
  async chat(messages: Message[]): Promise<Message> {
    const lastUserMessage = messages.filter(m => m.role === 'user').pop();
    return createMessage('assistant', `Echo: ${lastUserMessage?.content || ''}`);
  }
}

describe('ConversationalAgent', () => {
  describe('Configuration', () => {
    it('should create with default configuration', () => {
      const llm = new MockLLMClient(['response']);
      const agent = new ConversationalAgent({ llmClient: llm });

      expect(agent.name).toBe('ConversationalAgent');
      expect(agent.historyLength).toBe(0);
      expect((agent as any).maxHistory).toBe(10);
    });

    it('should create with custom max history', () => {
      const llm = new MockLLMClient(['response']);
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 5 });

      expect((agent as any).maxHistory).toBe(5);
    });

    it('should add system prompt to history', () => {
      const llm = new MockLLMClient(['response']);
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'You are helpful',
      });

      expect(agent.historyLength).toBe(1);
      const history = agent.getHistory();
      expect(history[0].role).toBe('system');
      expect(history[0].content).toBe('You are helpful');
    });

    it('should not include system prompt in history if includeSystem is false', () => {
      const llm = new MockLLMClient(['response']);
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'You are helpful',
        includeSystem: false,
      });

      expect(agent.historyLength).toBe(0);
    });
  });

  describe('Basic Conversation', () => {
    it('should process single message', async () => {
      const llm = new MockLLMClient(['Hello!']);
      const agent = new ConversationalAgent({ llmClient: llm });

      const response = await agent.process(createMessage('user', 'Hi'));

      expect(response.content).toBe('Hello!');
      expect(agent.historyLength).toBe(2); // user + assistant
    });

    it('should maintain conversation history', async () => {
      const llm = new MockLLMClient(['Hi Alice!', 'Your name is Alice']);
      const agent = new ConversationalAgent({ llmClient: llm });

      await agent.process(createMessage('user', 'My name is Alice'));
      await agent.process(createMessage('user', "What's my name?"));

      const history = agent.getHistory();
      expect(history.length).toBe(4); // 2 user + 2 assistant
      expect(history[0].content).toBe('My name is Alice');
      expect(history[2].content).toBe("What's my name?");
    });

    it('should pass full history to LLM', async () => {
      const llm = new MockLLMClient(['Response 1', 'Response 2']);
      const agent = new ConversationalAgent({ llmClient: llm });

      await agent.process(createMessage('user', 'First'));
      await agent.process(createMessage('user', 'Second'));

      // Check that second call received full history
      expect(llm.lastMessages.length).toBe(3); // First user + Response 1 + Second user
    });

    it('should include system prompt in context', async () => {
      const llm = new MockLLMClient(['Sure!']);
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'You are helpful',
      });

      await agent.process(createMessage('user', 'Help me'));

      expect(llm.lastMessages[0].role).toBe('system');
      expect(llm.lastMessages[0].content).toBe('You are helpful');
      expect(llm.lastMessages[1].role).toBe('user');
    });
  });

  describe('History Pruning', () => {
    it('should prune history when exceeding max', async () => {
      const llm = new MockLLMClient(['R1', 'R2', 'R3', 'R4']);
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 4 });

      await agent.process(createMessage('user', 'M1'));
      await agent.process(createMessage('user', 'M2'));
      await agent.process(createMessage('user', 'M3'));

      expect(agent.historyLength).toBe(4); // Only last 4 messages
      const history = agent.getHistory();
      expect(history[0].content).toBe('M2'); // M1 pruned
    });

    it('should preserve system messages during pruning', async () => {
      const llm = new MockLLMClient(['R1', 'R2', 'R3']);
      const agent = new ConversationalAgent({
        llmClient: llm,
        maxHistory: 4,
        systemPrompt: 'System',
      });

      await agent.process(createMessage('user', 'M1'));
      await agent.process(createMessage('user', 'M2'));
      await agent.process(createMessage('user', 'M3'));

      const history = agent.getHistory();
      expect(history[0].role).toBe('system');
      expect(history[0].content).toBe('System');
      expect(history.length).toBe(4); // system + 3 most recent
    });

    it('should prune oldest conversations first', async () => {
      const llm = new MockLLMClient(['R1', 'R2', 'R3']);
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 4 });

      await agent.process(createMessage('user', 'Old'));
      await agent.process(createMessage('user', 'Middle'));
      await agent.process(createMessage('user', 'New'));

      const history = agent.getHistory();
      // Should keep: Middle, R2, New, R3
      expect(history[0].content).toBe('Middle');
      expect(history[history.length - 1].content).toBe('R3');
    });
  });

  describe('History Management', () => {
    it('should clear history', () => {
      const llm = new MockLLMClient([]);
      const agent = new ConversationalAgent({ llmClient: llm });
      (agent as any).history = [
        createMessage('user', 'Test'),
        createMessage('assistant', 'Response'),
      ];

      agent.clearHistory();

      expect(agent.historyLength).toBe(0);
    });

    it('should clear history but keep system prompt', () => {
      const llm = new MockLLMClient([]);
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'System',
      });
      (agent as any).history.push(createMessage('user', 'Test'));

      agent.clearHistory(true);

      expect(agent.historyLength).toBe(1);
      expect(agent.getHistory()[0].role).toBe('system');
    });

    it('should clear history including system prompt', () => {
      const llm = new MockLLMClient([]);
      const agent = new ConversationalAgent({
        llmClient: llm,
        systemPrompt: 'System',
      });

      agent.clearHistory(false);

      expect(agent.historyLength).toBe(0);
    });

    it('should return copy of history', async () => {
      const llm = new MockLLMClient(['Response']);
      const agent = new ConversationalAgent({ llmClient: llm });

      await agent.process(createMessage('user', 'Test'));
      const history1 = agent.getHistory();
      const history2 = agent.getHistory();

      expect(history1).toEqual(history2);
      expect(history1).not.toBe(history2); // Different array instances
    });

    it('should update max history dynamically', async () => {
      const llm = new MockLLMClient(['R1', 'R2', 'R3']);
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 10 });

      await agent.process(createMessage('user', 'M1'));
      await agent.process(createMessage('user', 'M2'));
      await agent.process(createMessage('user', 'M3'));

      expect(agent.historyLength).toBe(6); // 3 user + 3 assistant

      agent.setMaxHistory(3);

      expect(agent.historyLength).toBe(3); // Pruned to 3
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty responses', async () => {
      const llm = new MockLLMClient(['']);
      const agent = new ConversationalAgent({ llmClient: llm });

      const response = await agent.process(createMessage('user', 'Test'));

      expect(response.content).toBe('');
      expect(agent.historyLength).toBe(2);
    });

    it('should handle very small max history', async () => {
      const llm = new MockLLMClient(['R1']);
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 1 });

      await agent.process(createMessage('user', 'Test'));

      expect(agent.historyLength).toBe(1); // Only keeps response
    });

    it('should handle max history of 0', () => {
      const llm = new MockLLMClient([]);
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 0 });

      expect(agent.historyLength).toBe(0);
    });

    it('should handle system prompt with small max history', async () => {
      const llm = new MockLLMClient(['R1']);
      const agent = new ConversationalAgent({
        llmClient: llm,
        maxHistory: 2,
        systemPrompt: 'System',
      });

      await agent.process(createMessage('user', 'Test'));

      const history = agent.getHistory();
      expect(history[0].role).toBe('system');
      expect(history.length).toBe(2); // system + response (user message pruned)
    });
  });

  describe('Integration Scenarios', () => {
    it('should support context-aware responses', async () => {
      const llm = new EchoLLMClient();
      const agent = new ConversationalAgent({ llmClient: llm });

      const response1 = await agent.process(createMessage('user', 'Hello'));
      const response2 = await agent.process(createMessage('user', 'Goodbye'));

      expect(response1.content).toBe('Echo: Hello');
      expect(response2.content).toBe('Echo: Goodbye');
    });

    it('should work with multi-turn conversations', async () => {
      const llm = new MockLLMClient([
        'Nice to meet you, Alice!',
        'Your name is Alice.',
        'You told me earlier.',
      ]);
      const agent = new ConversationalAgent({ llmClient: llm, maxHistory: 10 });

      await agent.process(createMessage('user', 'My name is Alice'));
      await agent.process(createMessage('user', "What's my name?"));
      const response3 = await agent.process(createMessage('user', 'How do you know?'));

      expect(response3.content).toBe('You told me earlier.');
      expect(agent.historyLength).toBe(6); // 3 user + 3 assistant
    });
  });

  describe('Capabilities', () => {
    it('should declare capabilities', () => {
      const llm = new MockLLMClient([]);
      const agent = new ConversationalAgent({ llmClient: llm });

      const caps = agent.capabilities;
      expect(caps).toContain('conversational');
      expect(caps).toContain('history-management');
    });
  });

  describe('Convenience Function', () => {
    it('should create agent with createConversationalAgent', () => {
      const llm = new MockLLMClient([]);
      const agent = createConversationalAgent(llm, 5, 'System prompt');

      expect(agent.name).toBe('ConversationalAgent');
      expect((agent as any).maxHistory).toBe(5);
      expect(agent.historyLength).toBe(1); // system prompt
    });
  });
});
