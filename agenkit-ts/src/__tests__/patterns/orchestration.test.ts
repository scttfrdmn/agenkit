/**
 * Comprehensive tests for orchestration patterns.
 *
 * Tests cover:
 * - SequentialPattern: pipeline execution
 * - ParallelPattern: concurrent execution and aggregation
 * - RouterPattern: conditional routing
 */

import { describe, it, expect } from 'vitest';
import {
  SequentialPattern,
  ParallelPattern,
  RouterPattern,
} from '../../patterns/orchestration';
import { Message, createMessage } from '../../core/interfaces';
import {
  createMockAgent,
  createErrorAgent,
  createEchoAgent,
  createAppendAgent,
  validateMessage,
} from './test-helpers';

describe('SequentialPattern', () => {
  describe('Constructor', () => {
    it('should create pattern with valid agents', () => {
      const agent = createMockAgent('a', 'result');
      const pattern = new SequentialPattern([agent]);

      expect(pattern).toBeDefined();
      expect(pattern.name).toBe('sequential');
    });

    it('should throw with empty agents array', () => {
      expect(() => new SequentialPattern([])).toThrow(
        'Sequential pattern requires at least one agent'
      );
    });

    it('should throw with null agents', () => {
      expect(() => new SequentialPattern(null as any)).toThrow();
    });

    it('should accept custom name', () => {
      const agent = createMockAgent('a', 'result');
      const pattern = new SequentialPattern([agent], { name: 'my-pipeline' });

      expect(pattern.name).toBe('my-pipeline');
    });
  });

  describe('Capabilities', () => {
    it('should aggregate capabilities from all agents', () => {
      const agent1 = new (class {
        name = 'a1';
        capabilities = ['cap1', 'cap2'];
        async process(m: Message) { return createMessage('assistant', ''); }
      })();
      const agent2 = new (class {
        name = 'a2';
        capabilities = ['cap3'];
        async process(m: Message) { return createMessage('assistant', ''); }
      })();

      const pattern = new SequentialPattern([agent1, agent2]);

      expect(pattern.capabilities).toContain('cap1');
      expect(pattern.capabilities).toContain('cap2');
      expect(pattern.capabilities).toContain('cap3');
    });
  });

  describe('Processing', () => {
    it('should process message through single agent', async () => {
      const agent = createMockAgent('only', 'final result');
      const pattern = new SequentialPattern([agent]);

      const result = await pattern.process(createMessage('user', 'input'));

      validateMessage(result);
      expect(result.content).toBe('final result');
    });

    it('should pass output of first agent to second', async () => {
      const agent1 = createEchoAgent('echo1', '[step1]');
      const agent2 = createEchoAgent('echo2', '[step2]');

      const pattern = new SequentialPattern([agent1, agent2]);
      const result = await pattern.process(createMessage('user', 'hello'));

      // agent2 echoes agent1's output
      expect(String(result.content)).toContain('[step2]');
      expect(String(result.content)).toContain('[step1]hello');
    });

    it('should execute three agents in order', async () => {
      const agent1 = createAppendAgent('a1', '-1');
      const agent2 = createAppendAgent('a2', '-2');
      const agent3 = createAppendAgent('a3', '-3');

      const pattern = new SequentialPattern([agent1, agent2, agent3]);
      const result = await pattern.process(createMessage('user', 'start'));

      expect(String(result.content)).toBe('start-1-2-3');
    });

    it('should propagate errors from agents', async () => {
      const good = createMockAgent('good', 'ok');
      const bad = createErrorAgent('bad', 'agent error');

      const pattern = new SequentialPattern([good, bad]);

      await expect(pattern.process(createMessage('user', 'input'))).rejects.toThrow('agent error');
    });
  });

  describe('Hooks', () => {
    it('should call beforeAgent hook for each agent', async () => {
      const agent1 = createMockAgent('a1', 'r1');
      const agent2 = createMockAgent('a2', 'r2');

      const hookCalls: string[] = [];
      const pattern = new SequentialPattern([agent1, agent2], {
        beforeAgent: (agent) => hookCalls.push(`before:${agent.name}`),
      });

      await pattern.process(createMessage('user', 'input'));

      expect(hookCalls).toContain('before:a1');
      expect(hookCalls).toContain('before:a2');
    });

    it('should call afterAgent hook for each agent', async () => {
      const agent = createMockAgent('a1', 'r1');

      const hookCalls: string[] = [];
      const pattern = new SequentialPattern([agent], {
        afterAgent: (agent) => hookCalls.push(`after:${agent.name}`),
      });

      await pattern.process(createMessage('user', 'input'));

      expect(hookCalls).toContain('after:a1');
    });
  });

  describe('unwrap', () => {
    it('should return copy of agents list', () => {
      const agent1 = createMockAgent('a1', 'r1');
      const agent2 = createMockAgent('a2', 'r2');
      const pattern = new SequentialPattern([agent1, agent2]);

      const agents = pattern.unwrap();
      expect(agents).toHaveLength(2);
      expect(agents[0].name).toBe('a1');
    });
  });
});

describe('ParallelPattern', () => {
  describe('Constructor', () => {
    it('should create pattern with valid agents', () => {
      const agent = createMockAgent('a', 'result');
      const pattern = new ParallelPattern([agent]);

      expect(pattern).toBeDefined();
      expect(pattern.name).toBe('parallel');
    });

    it('should throw with empty agents', () => {
      expect(() => new ParallelPattern([])).toThrow(
        'Parallel pattern requires at least one agent'
      );
    });

    it('should accept custom name', () => {
      const agent = createMockAgent('a', 'result');
      const pattern = new ParallelPattern([agent], { name: 'my-parallel' });

      expect(pattern.name).toBe('my-parallel');
    });
  });

  describe('Processing', () => {
    it('should execute all agents and aggregate results', async () => {
      const agent1 = createMockAgent('a1', 'result1');
      const agent2 = createMockAgent('a2', 'result2');
      const agent3 = createMockAgent('a3', 'result3');

      const pattern = new ParallelPattern([agent1, agent2, agent3]);
      const result = await pattern.process(createMessage('user', 'input'));

      validateMessage(result);
      // Default aggregator stores all results in metadata
      const parallelResults = result.metadata?.parallelResults as any[];
      expect(parallelResults).toHaveLength(3);
    });

    it('should send same input to all agents', async () => {
      const inputs: string[] = [];

      class CapturingAgent {
        readonly name: string;
        readonly capabilities = ['mock'];

        constructor(name: string) {
          this.name = name;
        }

        async process(message: Message): Promise<Message> {
          inputs.push(String(message.content));
          return createMessage('assistant', `from ${this.name}`);
        }
      }

      const pattern = new ParallelPattern([
        new CapturingAgent('a1'),
        new CapturingAgent('a2'),
      ]);

      await pattern.process(createMessage('user', 'broadcast'));

      expect(inputs).toHaveLength(2);
      inputs.forEach(input => expect(input).toBe('broadcast'));
    });

    it('should support custom aggregator', async () => {
      const agent1 = createMockAgent('a1', 'hello');
      const agent2 = createMockAgent('a2', 'world');

      const pattern = new ParallelPattern([agent1, agent2], {
        aggregator: (msgs) => createMessage('assistant', msgs.map(m => m.content).join(', ')),
      });

      const result = await pattern.process(createMessage('user', 'input'));
      expect(String(result.content)).toContain('hello');
      expect(String(result.content)).toContain('world');
    });

    it('should propagate first error from agents', async () => {
      const good = createMockAgent('good', 'ok');
      const bad = createErrorAgent('bad', 'parallel error');

      const pattern = new ParallelPattern([good, bad]);

      await expect(pattern.process(createMessage('user', 'input'))).rejects.toThrow();
    });
  });

  describe('defaultAggregator', () => {
    it('should return first message with all results in metadata', () => {
      const msgs = [
        createMessage('assistant', 'r1'),
        createMessage('assistant', 'r2'),
      ];

      const result = ParallelPattern.defaultAggregator(msgs);

      expect(result.content).toBe('r1');
      expect((result.metadata?.parallelResults as any[]).length).toBe(2);
    });

    it('should throw for empty messages', () => {
      expect(() => ParallelPattern.defaultAggregator([])).toThrow();
    });
  });
});

describe('RouterPattern', () => {
  describe('Constructor', () => {
    it('should create pattern with valid handlers', () => {
      const agent = createMockAgent('a', 'result');
      const pattern = new RouterPattern(() => 'cat', { cat: agent });

      expect(pattern).toBeDefined();
      expect(pattern.name).toBe('router');
    });

    it('should throw with empty handlers', () => {
      expect(() => new RouterPattern(() => 'cat', {})).toThrow(
        'Router pattern requires at least one handler'
      );
    });

    it('should accept custom name', () => {
      const agent = createMockAgent('a', 'result');
      const pattern = new RouterPattern(() => 'cat', { cat: agent }, { name: 'my-router' });

      expect(pattern.name).toBe('my-router');
    });
  });

  describe('Routing', () => {
    it('should route to correct handler', async () => {
      const agent1 = createMockAgent('a1', 'from cat1');
      const agent2 = createMockAgent('a2', 'from cat2');

      const pattern = new RouterPattern(
        (msg) => String(msg.content) === 'go-cat1' ? 'cat1' : 'cat2',
        { cat1: agent1, cat2: agent2 }
      );

      const result1 = await pattern.process(createMessage('user', 'go-cat1'));
      expect(result1.content).toBe('from cat1');

      const result2 = await pattern.process(createMessage('user', 'other'));
      expect(result2.content).toBe('from cat2');
    });

    it('should use default handler when key not found', async () => {
      const agent = createMockAgent('a', 'from specific');
      const defaultAgent = createMockAgent('default', 'from default');

      const pattern = new RouterPattern(
        () => 'unknown',
        { specific: agent },
        { default: defaultAgent }
      );

      const result = await pattern.process(createMessage('user', 'input'));
      expect(result.content).toBe('from default');
    });

    it('should throw when no handler and no default', async () => {
      const agent = createMockAgent('a', 'result');
      const pattern = new RouterPattern(() => 'unknown', { known: agent });

      await expect(pattern.process(createMessage('user', 'input'))).rejects.toThrow("unknown");
    });
  });

  describe('unwrap', () => {
    it('should return handlers record', () => {
      const agent1 = createMockAgent('a1', 'r1');
      const agent2 = createMockAgent('a2', 'r2');

      const pattern = new RouterPattern(() => 'h1', { h1: agent1, h2: agent2 });
      const handlers = pattern.unwrap();

      expect(handlers).toHaveProperty('h1');
      expect(handlers).toHaveProperty('h2');
    });
  });
});
