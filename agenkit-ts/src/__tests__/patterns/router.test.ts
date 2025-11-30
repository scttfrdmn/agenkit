/**
 * Comprehensive tests for Router pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - Classification and routing
 * - Default routes
 * - Multiple classifiers
 * - Error handling
 * - Edge cases
 */

import { describe, it, expect } from 'vitest';
import {
  RouterAgent,
  SimpleClassifier,
  LLMClassifier,
  ClassifierAgent,
} from '../../patterns/router';
import { Message, createMessage, Agent } from '../../core/interfaces';
import {
  createMockAgent,
  createErrorAgent,
  validateMessage,
  hasMetadata,
  getMetadata,
} from './test-helpers';

/** Mock classifier for testing */
class MockClassifier implements ClassifierAgent {
  readonly name = 'MockClassifier';
  private categoryMap: Map<string, string>;
  private defaultCategory?: string;

  constructor(categoryMap: Record<string, string>, defaultCategory?: string) {
    this.categoryMap = new Map(Object.entries(categoryMap));
    this.defaultCategory = defaultCategory;
  }

  get capabilities(): string[] {
    return ['mock', 'classification'];
  }

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', 'classifier response');
  }

  async classify(message: Message): Promise<string> {
    const content = String(message.content);
    return this.categoryMap.get(content) || this.defaultCategory || 'unknown';
  }
}

describe('RouterAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid configuration', () => {
      const classifier = new MockClassifier({}, 'default');
      const agent = createMockAgent('agent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { default: agent },
      });

      expect(router).toBeDefined();
      expect(router.name).toBe('RouterAgent');
    });

    it('should throw error with null config', () => {
      expect(() => new RouterAgent(null as any)).toThrow('config is required');
    });

    it('should throw error with undefined config', () => {
      expect(() => new RouterAgent(undefined as any)).toThrow('config is required');
    });

    it('should throw error with missing classifier', () => {
      const agent = createMockAgent('agent', 'result');

      expect(
        () =>
          new RouterAgent({
            classifier: null as any,
            agents: { cat: agent },
          }),
      ).toThrow('classifier is required');
    });

    it('should throw error with empty agents', () => {
      const classifier = new MockClassifier({});

      expect(
        () =>
          new RouterAgent({
            classifier,
            agents: {},
          }),
      ).toThrow('at least one agent is required');
    });

    it('should throw error with null agents', () => {
      const classifier = new MockClassifier({});

      expect(
        () =>
          new RouterAgent({
            classifier,
            agents: null as any,
          }),
      ).toThrow('at least one agent is required');
    });

    it('should validate default key exists', () => {
      const classifier = new MockClassifier({});
      const agent = createMockAgent('agent', 'result');

      expect(
        () =>
          new RouterAgent({
            classifier,
            agents: { cat1: agent },
            defaultKey: 'missing',
          }),
      ).toThrow("default key 'missing' not found");
    });

    it('should accept valid default key', () => {
      const classifier = new MockClassifier({});
      const agent = createMockAgent('agent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { default: agent },
        defaultKey: 'default',
      });

      expect(router).toBeDefined();
    });
  });

  describe('Capabilities', () => {
    it('should include router capabilities', () => {
      const classifier = new MockClassifier({});
      const agent = createMockAgent('agent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { cat: agent },
      });

      const caps = router.capabilities;
      expect(caps).toContain('router');
      expect(caps).toContain('conditional');
      expect(caps).toContain('classification');
    });

    it('should combine classifier and agent capabilities', () => {
      const classifier = new MockClassifier({});
      const agent = createMockAgent('agent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { cat: agent },
      });

      const caps = router.capabilities;
      expect(caps).toContain('mock');
      expect(caps).toContain('classification');
    });
  });

  describe('Basic Routing', () => {
    it('should route to correct agent based on classification', async () => {
      const classifier = new MockClassifier({ input1: 'cat1', input2: 'cat2' });
      const agent1 = createMockAgent('agent1', 'result from agent1');
      const agent2 = createMockAgent('agent2', 'result from agent2');

      const router = new RouterAgent({
        classifier,
        agents: { cat1: agent1, cat2: agent2 },
      });

      const input1 = createMessage('user', 'input1');
      const result1 = await router.process(input1);
      expect(result1.content).toBe('result from agent1');

      const input2 = createMessage('user', 'input2');
      const result2 = await router.process(input2);
      expect(result2.content).toBe('result from agent2');
    });

    it('should throw error with null message', async () => {
      const classifier = new MockClassifier({});
      const agent = createMockAgent('agent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { cat: agent },
      });

      await expect(router.process(null as any)).rejects.toThrow('message cannot be nil');
    });

    it('should route single category', async () => {
      const classifier = new MockClassifier({ test: 'support' });
      const support = createMockAgent('support', 'support response');

      const router = new RouterAgent({
        classifier,
        agents: { support },
      });

      const input = createMessage('user', 'test');
      const result = await router.process(input);

      validateMessage(result);
      expect(result.content).toBe('support response');
    });

    it('should route to different agents', async () => {
      const classifier = new MockClassifier({
        billing: 'billing',
        technical: 'technical',
        account: 'account',
      });

      const billing = createMockAgent('billing', 'billing help');
      const technical = createMockAgent('technical', 'technical help');
      const account = createMockAgent('account', 'account help');

      const router = new RouterAgent({
        classifier,
        agents: { billing, technical, account },
      });

      const billingMsg = await router.process(createMessage('user', 'billing'));
      expect(billingMsg.content).toBe('billing help');

      const technicalMsg = await router.process(createMessage('user', 'technical'));
      expect(technicalMsg.content).toBe('technical help');

      const accountMsg = await router.process(createMessage('user', 'account'));
      expect(accountMsg.content).toBe('account help');
    });
  });

  describe('Default Routes', () => {
    it('should use default when category not found', async () => {
      const classifier = new MockClassifier({ test: 'unknown' });
      const agent1 = createMockAgent('agent1', 'result1');
      const defaultAgent = createMockAgent('default', 'default response');

      const router = new RouterAgent({
        classifier,
        agents: { cat1: agent1, default: defaultAgent },
        defaultKey: 'default',
      });

      const input = createMessage('user', 'test');
      const result = await router.process(input);

      expect(result.content).toBe('default response');
    });

    it('should throw error when no default and category not found', async () => {
      const classifier = new MockClassifier({ test: 'unknown' });
      const agent = createMockAgent('agent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { cat1: agent },
      });

      const input = createMessage('user', 'test');
      await expect(router.process(input)).rejects.toThrow("no agent found for category 'unknown'");
    });

    it('should list available categories in error', async () => {
      const classifier = new MockClassifier({ test: 'missing' });
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const router = new RouterAgent({
        classifier,
        agents: { cat1: agent1, cat2: agent2 },
      });

      const input = createMessage('user', 'test');

      try {
        await router.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('cat1');
        expect(errorMsg).toContain('cat2');
      }
    });
  });

  describe('Metadata', () => {
    it('should add routing metadata to result', async () => {
      const classifier = new MockClassifier({ test: 'target' });
      const agent = createMockAgent('targetAgent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { target: agent },
      });

      const input = createMessage('user', 'test');
      const result = await router.process(input);

      expect(hasMetadata(result, 'routed_category')).toBe(true);
      expect(hasMetadata(result, 'routed_agent')).toBe(true);
      expect(hasMetadata(result, 'available_routes')).toBe(true);
    });

    it('should record correct routing information', async () => {
      const classifier = new MockClassifier({ test: 'billing' });
      const billing = createMockAgent('billingAgent', 'result');
      const tech = createMockAgent('techAgent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { billing, tech },
      });

      const input = createMessage('user', 'test');
      const result = await router.process(input);

      expect(getMetadata(result, 'routed_category')).toBe('billing');
      expect(getMetadata(result, 'routed_agent')).toBe('billingAgent');
      expect(getMetadata(result, 'available_routes')).toBe(2);
    });

    it('should update category when using default', async () => {
      const classifier = new MockClassifier({ test: 'unknown' });
      const agent = createMockAgent('agent', 'result');
      const defaultAgent = createMockAgent('defaultAgent', 'default result');

      const router = new RouterAgent({
        classifier,
        agents: { cat: agent, fallback: defaultAgent },
        defaultKey: 'fallback',
      });

      const input = createMessage('user', 'test');
      const result = await router.process(input);

      expect(getMetadata(result, 'routed_category')).toBe('fallback');
      expect(getMetadata(result, 'routed_agent')).toBe('defaultAgent');
    });
  });

  describe('Error Handling', () => {
    it('should handle classification failure', async () => {
      class ErrorClassifier implements ClassifierAgent {
        readonly name = 'ErrorClassifier';
        get capabilities() {
          return ['classification'];
        }
        async process(message: Message) {
          return createMessage('assistant', 'response');
        }
        async classify(message: Message) {
          throw new Error('classification error');
        }
      }

      const classifier = new ErrorClassifier();
      const agent = createMockAgent('agent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { cat: agent },
      });

      const input = createMessage('user', 'test');
      await expect(router.process(input)).rejects.toThrow('classification failed');
    });

    it('should handle agent execution failure', async () => {
      const classifier = new MockClassifier({ test: 'error' });
      const errorAgent = createErrorAgent('errorAgent', 'agent failed');

      const router = new RouterAgent({
        classifier,
        agents: { error: errorAgent },
      });

      const input = createMessage('user', 'test');
      await expect(router.process(input)).rejects.toThrow('agent failed');
    });

    it('should include category in agent error', async () => {
      const classifier = new MockClassifier({ test: 'billing' });
      const errorAgent = createErrorAgent('billingAgent', 'billing error');

      const router = new RouterAgent({
        classifier,
        agents: { billing: errorAgent },
      });

      const input = createMessage('user', 'test');

      try {
        await router.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('category: billing');
        expect(errorMsg).toContain('billing error');
      }
    });
  });

  describe('SimpleClassifier', () => {
    it('should create classifier with keywords', () => {
      const agent = createMockAgent('agent', 'result');
      const classifier = new SimpleClassifier(agent, {
        billing: ['invoice', 'payment'],
        technical: ['bug', 'error'],
      });

      expect(classifier).toBeDefined();
      expect(classifier.name).toBe('SimpleClassifier');
    });

    it('should classify based on keyword matches', async () => {
      const agent = createMockAgent('agent', 'result');
      const classifier = new SimpleClassifier(agent, {
        billing: ['invoice', 'payment', 'charge'],
        technical: ['bug', 'error', 'broken'],
      });

      const billing = createMessage('user', 'I have a question about my invoice');
      expect(await classifier.classify(billing)).toBe('billing');

      const technical = createMessage('user', 'The app has a bug and shows an error');
      expect(await classifier.classify(technical)).toBe('technical');
    });

    it('should be case insensitive', async () => {
      const agent = createMockAgent('agent', 'result');
      const classifier = new SimpleClassifier(agent, {
        support: ['Help', 'SUPPORT'],
      });

      const msg = createMessage('user', 'I need help with SUPPORT');
      expect(await classifier.classify(msg)).toBe('support');
    });

    it('should return category with most matches', async () => {
      const agent = createMockAgent('agent', 'result');
      const classifier = new SimpleClassifier(agent, {
        billing: ['billing', 'invoice'],
        account: ['account', 'billing'],
      });

      const msg = createMessage('user', 'billing invoice question');
      const category = await classifier.classify(msg);
      expect(category).toBe('billing');
    });

    it('should throw error when no matches found', async () => {
      const agent = createMockAgent('agent', 'result');
      const classifier = new SimpleClassifier(agent, {
        billing: ['invoice'],
      });

      const msg = createMessage('user', 'random text');
      await expect(classifier.classify(msg)).rejects.toThrow('unable to classify');
    });

    it('should process messages normally', async () => {
      const agent = createMockAgent('agent', 'direct response');
      const classifier = new SimpleClassifier(agent, {});

      const msg = createMessage('user', 'test');
      const result = await classifier.process(msg);
      expect(result.content).toBe('direct response');
    });
  });

  describe('LLMClassifier', () => {
    it('should create classifier with categories', () => {
      const agent = createMockAgent('agent', 'result');
      const classifier = new LLMClassifier(agent, ['support', 'sales', 'technical']);

      expect(classifier).toBeDefined();
      expect(classifier.name).toBe('LLMClassifier');
    });

    it('should use default category when empty', () => {
      const agent = createMockAgent('agent', 'result');
      const classifier = new LLMClassifier(agent, []);

      expect(classifier).toBeDefined();
    });

    it('should classify using LLM response', async () => {
      const agent = createMockAgent('agent', 'support');
      const classifier = new LLMClassifier(agent, ['support', 'sales', 'technical']);

      const msg = createMessage('user', 'I need help');
      const category = await classifier.classify(msg);

      expect(category).toBe('support');
    });

    it('should handle case-insensitive category matching', async () => {
      const agent = createMockAgent('agent', 'SUPPORT');
      const classifier = new LLMClassifier(agent, ['support', 'sales']);

      const msg = createMessage('user', 'help');
      const category = await classifier.classify(msg);

      expect(category).toBe('support');
    });

    it('should throw error for invalid category', async () => {
      const agent = createMockAgent('agent', 'invalid');
      const classifier = new LLMClassifier(agent, ['cat1', 'cat2']);

      const msg = createMessage('user', 'test');
      await expect(classifier.classify(msg)).rejects.toThrow('llm returned invalid category');
    });

    it('should handle llm failure', async () => {
      const agent = createErrorAgent('agent', 'llm error');
      const classifier = new LLMClassifier(agent, ['cat1']);

      const msg = createMessage('user', 'test');
      await expect(classifier.classify(msg)).rejects.toThrow('llm classification failed');
    });
  });

  describe('Edge Cases', () => {
    it('should handle many routing categories', async () => {
      const categoryMap: Record<string, string> = {};
      const agents: Record<string, Agent> = {};

      for (let i = 0; i < 10; i++) {
        categoryMap[`input${i}`] = `cat${i}`;
        agents[`cat${i}`] = createMockAgent(`agent${i}`, `result${i}`);
      }

      const classifier = new MockClassifier(categoryMap);
      const router = new RouterAgent({ classifier, agents });

      const input = createMessage('user', 'input5');
      const result = await router.process(input);

      expect(result.content).toBe('result5');
    });

    it('should handle same agent for multiple categories', async () => {
      const classifier = new MockClassifier({
        input1: 'shared',
        input2: 'shared',
      });
      const agent = createMockAgent('sharedAgent', 'shared result');

      const router = new RouterAgent({
        classifier,
        agents: { shared: agent },
      });

      const result1 = await router.process(createMessage('user', 'input1'));
      const result2 = await router.process(createMessage('user', 'input2'));

      expect(result1.content).toBe('shared result');
      expect(result2.content).toBe('shared result');
    });

    it('should handle rapid classification requests', async () => {
      const classifier = new MockClassifier({ test: 'cat' });
      const agent = createMockAgent('agent', 'result');

      const router = new RouterAgent({
        classifier,
        agents: { cat: agent },
      });

      const input = createMessage('user', 'test');
      const results = await Promise.all([
        router.process(input),
        router.process(input),
        router.process(input),
      ]);

      expect(results).toHaveLength(3);
      results.forEach((r) => expect(r.content).toBe('result'));
    });
  });
});
