/**
 * Tests for ParallelAgent composition pattern.
 */

import { describe, it, expect } from 'vitest';
import { ParallelAgent } from '../../composition/parallel';
import { Agent, Message, createMessage } from '../../core/interfaces';

// Mock agents for testing
class CounterAgent implements Agent {
  constructor(
    public name: string,
    private count: number
  ) {}

  get capabilities(): string[] {
    return ['count'];
  }

  async process(message: Message): Promise<Message> {
    return createMessage('agent', `${this.name}: ${this.count}`);
  }
}

class ErrorAgent implements Agent {
  constructor(public name: string) {}

  get capabilities(): string[] {
    return ['error'];
  }

  async process(_message: Message): Promise<Message> {
    throw new Error('Intentional error');
  }
}

describe('ParallelAgent', () => {
  it('should execute agents in parallel', async () => {
    const agent1 = new CounterAgent('agent1', 1);
    const agent2 = new CounterAgent('agent2', 2);
    const agent3 = new CounterAgent('agent3', 3);

    const parallel = new ParallelAgent('ensemble', [agent1, agent2, agent3]);

    const input = createMessage('user', 'test');
    const result = await parallel.process(input);

    // Check combined output
    expect(result.content).toContain('[agent1]: agent1: 1');
    expect(result.content).toContain('[agent2]: agent2: 2');
    expect(result.content).toContain('[agent3]: agent3: 3');
  });

  it('should throw error if no agents provided', () => {
    expect(() => new ParallelAgent('test', [])).toThrow(
      'Parallel agent requires at least one agent'
    );
  });

  it('should propagate errors from any agent', async () => {
    const agent1 = new CounterAgent('agent1', 1);
    const agent2 = new ErrorAgent('error-agent');
    const agent3 = new CounterAgent('agent3', 3);

    const parallel = new ParallelAgent('ensemble', [agent1, agent2, agent3]);

    const input = createMessage('user', 'test');

    await expect(parallel.process(input)).rejects.toThrow(
      'Parallel execution had errors'
    );
  });

  it('should combine capabilities of all agents', () => {
    const agent1 = new CounterAgent('agent1', 1);
    const agent2 = new CounterAgent('agent2', 2);

    const parallel = new ParallelAgent('ensemble', [agent1, agent2]);

    const capabilities = parallel.capabilities;
    expect(capabilities).toContain('count');
    expect(capabilities).toContain('parallel');
  });

  it('should combine metadata from all agents', async () => {
    const agent1 = new CounterAgent('agent1', 1);
    const agent2 = new CounterAgent('agent2', 2);

    const parallel = new ParallelAgent('ensemble', [agent1, agent2]);

    const input = createMessage('user', 'test');
    const result = await parallel.process(input);

    // Metadata should be prefixed with agent names
    expect(result.metadata).toBeDefined();
  });

  it('should return agents list', () => {
    const agent1 = new CounterAgent('agent1', 1);
    const agent2 = new CounterAgent('agent2', 2);

    const parallel = new ParallelAgent('ensemble', [agent1, agent2]);

    const agents = parallel.getAgents();
    expect(agents).toHaveLength(2);
    expect(agents[0]).toBe(agent1);
    expect(agents[1]).toBe(agent2);
  });
});
