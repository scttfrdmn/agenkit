/**
 * Tests for SequentialAgent composition pattern.
 */

import { describe, it, expect } from 'vitest';
import { SequentialAgent } from '../../composition/sequential';
import { Agent, Message, createMessage } from '../../core/interfaces';

// Mock agents for testing
class EchoAgent implements Agent {
  constructor(
    public name: string,
    private prefix: string = ''
  ) {}

  get capabilities(): string[] {
    return ['echo'];
  }

  async process(message: Message): Promise<Message> {
    const content =
      typeof message.content === 'string'
        ? this.prefix + message.content
        : this.prefix;
    return createMessage('agent', content);
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

describe('SequentialAgent', () => {
  it('should execute agents in sequence', async () => {
    const agent1 = new EchoAgent('agent1', 'A:');
    const agent2 = new EchoAgent('agent2', 'B:');
    const agent3 = new EchoAgent('agent3', 'C:');

    const sequential = new SequentialAgent('pipeline', [agent1, agent2, agent3]);

    const input = createMessage('user', 'test');
    const result = await sequential.process(input);

    expect(result.content).toBe('C:B:A:test');
  });

  it('should throw error if no agents provided', () => {
    expect(() => new SequentialAgent('test', [])).toThrow(
      'Sequential agent requires at least one agent'
    );
  });

  it('should propagate errors with context', async () => {
    const agent1 = new EchoAgent('agent1', 'A:');
    const agent2 = new ErrorAgent('error-agent');
    const agent3 = new EchoAgent('agent3', 'C:');

    const sequential = new SequentialAgent('pipeline', [agent1, agent2, agent3]);

    const input = createMessage('user', 'test');

    await expect(sequential.process(input)).rejects.toThrow(
      'Step 2 (error-agent) failed: Intentional error'
    );
  });

  it('should combine capabilities of all agents', () => {
    const agent1 = new EchoAgent('agent1');
    const agent2 = new EchoAgent('agent2');

    const sequential = new SequentialAgent('pipeline', [agent1, agent2]);

    const capabilities = sequential.capabilities;
    expect(capabilities).toContain('echo');
    expect(capabilities).toContain('sequential');
  });

  it('should return agents list', () => {
    const agent1 = new EchoAgent('agent1');
    const agent2 = new EchoAgent('agent2');

    const sequential = new SequentialAgent('pipeline', [agent1, agent2]);

    const agents = sequential.getAgents();
    expect(agents).toHaveLength(2);
    expect(agents[0]).toBe(agent1);
    expect(agents[1]).toBe(agent2);
  });
});
