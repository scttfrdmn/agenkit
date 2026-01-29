/**
 * Tests for FallbackAgent composition pattern.
 */

import { describe, it, expect } from 'vitest';
import { FallbackAgent } from '../../composition/fallback';
import { Agent, Message, createMessage } from '../../core/interfaces';

// Mock agents for testing
class ReliableAgent implements Agent {
  constructor(public name: string) {}

  get capabilities(): string[] {
    return ['reliable'];
  }

  async process(message: Message): Promise<Message> {
    return createMessage('agent', `Processed by ${this.name}`);
  }
}

class UnreliableAgent implements Agent {
  constructor(
    public name: string,
    private shouldFail: boolean = true
  ) {}

  get capabilities(): string[] {
    return ['unreliable'];
  }

  async process(_message: Message): Promise<Message> {
    if (this.shouldFail) {
      throw new Error(`${this.name} failed`);
    }
    return createMessage('agent', `Processed by ${this.name}`);
  }
}

describe('FallbackAgent', () => {
  it('should use first successful agent', async () => {
    const primary = new ReliableAgent('primary');
    const secondary = new ReliableAgent('secondary');

    const fallback = new FallbackAgent('reliable', [primary, secondary]);

    const input = createMessage('user', 'test');
    const result = await fallback.process(input);

    expect(result.content).toBe('Processed by primary');
    expect(result.metadata?.fallback_agent_used).toBe('primary');
    expect(result.metadata?.fallback_attempt).toBe(1);
  });

  it('should fallback to next agent on failure', async () => {
    const primary = new UnreliableAgent('primary', true);
    const secondary = new ReliableAgent('secondary');

    const fallback = new FallbackAgent('reliable', [primary, secondary]);

    const input = createMessage('user', 'test');
    const result = await fallback.process(input);

    expect(result.content).toBe('Processed by secondary');
    expect(result.metadata?.fallback_agent_used).toBe('secondary');
    expect(result.metadata?.fallback_attempt).toBe(2);
  });

  it('should try all agents in order', async () => {
    const primary = new UnreliableAgent('primary', true);
    const secondary = new UnreliableAgent('secondary', true);
    const tertiary = new ReliableAgent('tertiary');

    const fallback = new FallbackAgent('reliable', [
      primary,
      secondary,
      tertiary,
    ]);

    const input = createMessage('user', 'test');
    const result = await fallback.process(input);

    expect(result.content).toBe('Processed by tertiary');
    expect(result.metadata?.fallback_agent_used).toBe('tertiary');
    expect(result.metadata?.fallback_attempt).toBe(3);
  });

  it('should throw error if all agents fail', async () => {
    const agent1 = new UnreliableAgent('agent1', true);
    const agent2 = new UnreliableAgent('agent2', true);

    const fallback = new FallbackAgent('failing', [agent1, agent2]);

    const input = createMessage('user', 'test');

    await expect(fallback.process(input)).rejects.toThrow(
      'All 2 agents failed'
    );
  });

  it('should throw error if no agents provided', () => {
    expect(() => new FallbackAgent('test', [])).toThrow(
      'Fallback agent requires at least one agent'
    );
  });

  it('should combine capabilities of all agents', () => {
    const agent1 = new ReliableAgent('agent1');
    const agent2 = new UnreliableAgent('agent2');

    const fallback = new FallbackAgent('reliable', [agent1, agent2]);

    const capabilities = fallback.capabilities;
    expect(capabilities).toContain('reliable');
    expect(capabilities).toContain('unreliable');
    expect(capabilities).toContain('fallback');
  });

  it('should return agents list', () => {
    const agent1 = new ReliableAgent('agent1');
    const agent2 = new ReliableAgent('agent2');

    const fallback = new FallbackAgent('reliable', [agent1, agent2]);

    const agents = fallback.getAgents();
    expect(agents).toHaveLength(2);
    expect(agents[0]).toBe(agent1);
    expect(agents[1]).toBe(agent2);
  });
});
