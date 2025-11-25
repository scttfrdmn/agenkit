/**
 * Tests for orchestration patterns (Sequential and Parallel).
 */

import { SequentialPattern, ParallelPattern, Aggregator } from '../patterns/orchestration';
import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name: string;
  readonly capabilities?: string[];
  private response: string;

  constructor(name: string, response: string, capabilities?: string[]) {
    this.name = name;
    this.response = response;
    this.capabilities = capabilities;
  }

  async process(message: Message): Promise<Message> {
    // Append this agent's response to the input
    const content = `${message.content} -> ${this.response}`;
    return createMessage('assistant', content);
  }
}

/**
 * Counter agent for tracking execution order.
 */
class CounterAgent implements Agent {
  readonly name: string;
  private counter: number[];
  private id: number;

  constructor(name: string, counter: number[], id: number) {
    this.name = name;
    this.counter = counter;
    this.id = id;
  }

  async process(message: Message): Promise<Message> {
    this.counter.push(this.id);
    return createMessage('assistant', `Agent ${this.id}`);
  }
}

describe('SequentialPattern', () => {
  describe('Configuration', () => {
    it('should require at least one agent', () => {
      expect(() => {
        new SequentialPattern([]);
      }).toThrow('Sequential pattern requires at least one agent');
    });

    it('should use default name', () => {
      const agent = new MockAgent('test', 'response');
      const pattern = new SequentialPattern([agent]);

      expect(pattern.name).toBe('sequential');
    });

    it('should use custom name', () => {
      const agent = new MockAgent('test', 'response');
      const pattern = new SequentialPattern([agent], { name: 'my_pipeline' });

      expect(pattern.name).toBe('my_pipeline');
    });
  });

  describe('Sequential Execution', () => {
    it('should execute agents in order', async () => {
      const agent1 = new MockAgent('agent1', 'A');
      const agent2 = new MockAgent('agent2', 'B');
      const agent3 = new MockAgent('agent3', 'C');

      const pattern = new SequentialPattern([agent1, agent2, agent3]);
      const result = await pattern.process(createMessage('user', 'Start'));

      expect(result.content).toBe('Start -> A -> B -> C');
    });

    it('should pass output as input to next agent', async () => {
      const agent1 = new MockAgent('agent1', '1');
      const agent2 = new MockAgent('agent2', '2');

      const pattern = new SequentialPattern([agent1, agent2]);
      const result = await pattern.process(createMessage('user', 'X'));

      // X -> 1, then (X -> 1) -> 2
      expect(result.content).toBe('X -> 1 -> 2');
    });

    it('should handle single agent', async () => {
      const agent = new MockAgent('agent', 'response');
      const pattern = new SequentialPattern([agent]);

      const result = await pattern.process(createMessage('user', 'input'));

      expect(result.content).toBe('input -> response');
    });
  });

  describe('Hooks', () => {
    it('should call beforeAgent hook', async () => {
      const agent1 = new MockAgent('agent1', 'A');
      const agent2 = new MockAgent('agent2', 'B');
      const calls: string[] = [];

      const pattern = new SequentialPattern([agent1, agent2], {
        beforeAgent: (agent) => calls.push(`before:${agent.name}`),
      });

      await pattern.process(createMessage('user', 'test'));

      expect(calls).toEqual(['before:agent1', 'before:agent2']);
    });

    it('should call afterAgent hook', async () => {
      const agent1 = new MockAgent('agent1', 'A');
      const agent2 = new MockAgent('agent2', 'B');
      const calls: string[] = [];

      const pattern = new SequentialPattern([agent1, agent2], {
        afterAgent: (agent) => calls.push(`after:${agent.name}`),
      });

      await pattern.process(createMessage('user', 'test'));

      expect(calls).toEqual(['after:agent1', 'after:agent2']);
    });

    it('should call both hooks in correct order', async () => {
      const agent1 = new MockAgent('agent1', 'A');
      const agent2 = new MockAgent('agent2', 'B');
      const calls: string[] = [];

      const pattern = new SequentialPattern([agent1, agent2], {
        beforeAgent: (agent) => calls.push(`before:${agent.name}`),
        afterAgent: (agent) => calls.push(`after:${agent.name}`),
      });

      await pattern.process(createMessage('user', 'test'));

      expect(calls).toEqual([
        'before:agent1',
        'after:agent1',
        'before:agent2',
        'after:agent2',
      ]);
    });
  });

  describe('Capabilities', () => {
    it('should combine capabilities from all agents', () => {
      const agent1 = new MockAgent('agent1', 'A', ['coding', 'testing']);
      const agent2 = new MockAgent('agent2', 'B', ['testing', 'review']);
      const agent3 = new MockAgent('agent3', 'C', ['deployment']);

      const pattern = new SequentialPattern([agent1, agent2, agent3]);

      const caps = pattern.capabilities;
      expect(caps).toContain('coding');
      expect(caps).toContain('testing');
      expect(caps).toContain('review');
      expect(caps).toContain('deployment');
      expect(caps.length).toBe(4); // Unique capabilities
    });

    it('should handle agents without capabilities', () => {
      const agent1 = new MockAgent('agent1', 'A');
      const agent2 = new MockAgent('agent2', 'B');

      const pattern = new SequentialPattern([agent1, agent2]);

      expect(pattern.capabilities).toEqual([]);
    });
  });

  describe('Unwrap', () => {
    it('should return copy of agents array', () => {
      const agent1 = new MockAgent('agent1', 'A');
      const agent2 = new MockAgent('agent2', 'B');
      const pattern = new SequentialPattern([agent1, agent2]);

      const agents = pattern.unwrap();

      expect(agents).toEqual([agent1, agent2]);
      // Verify it's a copy
      agents.push(new MockAgent('agent3', 'C'));
      expect(pattern.unwrap().length).toBe(2);
    });
  });
});

describe('ParallelPattern', () => {
  describe('Configuration', () => {
    it('should require at least one agent', () => {
      expect(() => {
        new ParallelPattern([]);
      }).toThrow('Parallel pattern requires at least one agent');
    });

    it('should use default name', () => {
      const agent = new MockAgent('test', 'response');
      const pattern = new ParallelPattern([agent]);

      expect(pattern.name).toBe('parallel');
    });

    it('should use custom name', () => {
      const agent = new MockAgent('test', 'response');
      const pattern = new ParallelPattern([agent], { name: 'my_parallel' });

      expect(pattern.name).toBe('my_parallel');
    });
  });

  describe('Parallel Execution', () => {
    it('should execute all agents with same input', async () => {
      // Track execution order
      const counter: number[] = [];
      const agent1 = new CounterAgent('agent1', counter, 1);
      const agent2 = new CounterAgent('agent2', counter, 2);
      const agent3 = new CounterAgent('agent3', counter, 3);

      const pattern = new ParallelPattern([agent1, agent2, agent3]);
      await pattern.process(createMessage('user', 'test'));

      // All agents should execute
      expect(counter).toContain(1);
      expect(counter).toContain(2);
      expect(counter).toContain(3);
      expect(counter.length).toBe(3);
    });

    it('should use default aggregator', async () => {
      const agent1 = new MockAgent('agent1', 'Response1');
      const agent2 = new MockAgent('agent2', 'Response2');

      const pattern = new ParallelPattern([agent1, agent2]);
      const result = await pattern.process(createMessage('user', 'input'));

      // Default aggregator returns first result with metadata
      expect(result.content).toContain('Response1');
      expect(result.metadata?.parallelResults).toBeDefined();
      expect((result.metadata?.parallelResults as any[]).length).toBe(2);
    });

    it('should use custom aggregator', async () => {
      const agent1 = new MockAgent('agent1', 'A');
      const agent2 = new MockAgent('agent2', 'B');

      const customAggregator: Aggregator = (messages) => {
        const combined = messages.map(m => m.content).join(' | ');
        return createMessage('assistant', combined);
      };

      const pattern = new ParallelPattern([agent1, agent2], {
        aggregator: customAggregator,
      });
      const result = await pattern.process(createMessage('user', 'test'));

      expect(result.content).toContain('A');
      expect(result.content).toContain('B');
      expect(result.content).toContain('|');
    });

    it('should handle single agent', async () => {
      const agent = new MockAgent('agent', 'response');
      const pattern = new ParallelPattern([agent]);

      const result = await pattern.process(createMessage('user', 'input'));

      expect(result.content).toBe('input -> response');
    });
  });

  describe('Default Aggregator', () => {
    it('should throw if no messages', () => {
      expect(() => {
        ParallelPattern.defaultAggregator([]);
      }).toThrow('No messages to aggregate');
    });

    it('should combine all results in metadata', () => {
      const msg1 = createMessage('assistant', 'Response1');
      const msg2 = createMessage('assistant', 'Response2');

      const result = ParallelPattern.defaultAggregator([msg1, msg2]);

      expect(result.metadata?.parallelResults).toBeDefined();
      const results = result.metadata?.parallelResults as any[];
      expect(results.length).toBe(2);
      expect(results[0].content).toBe('Response1');
      expect(results[1].content).toBe('Response2');
    });
  });

  describe('Capabilities', () => {
    it('should combine capabilities from all agents', () => {
      const agent1 = new MockAgent('agent1', 'A', ['coding', 'testing']);
      const agent2 = new MockAgent('agent2', 'B', ['testing', 'review']);
      const agent3 = new MockAgent('agent3', 'C', ['deployment']);

      const pattern = new ParallelPattern([agent1, agent2, agent3]);

      const caps = pattern.capabilities;
      expect(caps).toContain('coding');
      expect(caps).toContain('testing');
      expect(caps).toContain('review');
      expect(caps).toContain('deployment');
      expect(caps.length).toBe(4); // Unique capabilities
    });
  });

  describe('Unwrap', () => {
    it('should return copy of agents array', () => {
      const agent1 = new MockAgent('agent1', 'A');
      const agent2 = new MockAgent('agent2', 'B');
      const pattern = new ParallelPattern([agent1, agent2]);

      const agents = pattern.unwrap();

      expect(agents).toEqual([agent1, agent2]);
      // Verify it's a copy
      agents.push(new MockAgent('agent3', 'C'));
      expect(pattern.unwrap().length).toBe(2);
    });
  });
});

describe('Pattern Composition', () => {
  it('should allow sequential of parallels', async () => {
    const agent1 = new MockAgent('agent1', 'A');
    const agent2 = new MockAgent('agent2', 'B');
    const agent3 = new MockAgent('agent3', 'C');

    const parallel = new ParallelPattern([agent1, agent2]);
    const sequential = new SequentialPattern([parallel, agent3]);

    const result = await sequential.process(createMessage('user', 'test'));

    expect(result.content).toContain('C');
  });

  it('should allow parallel of sequentials', async () => {
    const agent1 = new MockAgent('agent1', 'A');
    const agent2 = new MockAgent('agent2', 'B');
    const agent3 = new MockAgent('agent3', 'C');

    const seq1 = new SequentialPattern([agent1, agent2]);
    const seq2 = new SequentialPattern([agent3]);
    const parallel = new ParallelPattern([seq1, seq2]);

    const result = await parallel.process(createMessage('user', 'test'));

    expect(result.metadata?.parallelResults).toBeDefined();
  });
});
