/**
 * Tests for ConditionalAgent composition pattern.
 */

import { describe, it, expect } from 'vitest';
import {
  ConditionalAgent,
  contentContains,
  roleEquals,
  metadataHasKey,
  metadataEquals,
  andConditions,
  orConditions,
  notCondition,
} from '../../composition/conditional';
import { Agent, Message, createMessage } from '../../core/interfaces';

// Mock agents for testing
class NamedAgent implements Agent {
  constructor(public name: string) {}

  get capabilities(): string[] {
    return [this.name];
  }

  async process(message: Message): Promise<Message> {
    return createMessage('agent', `Processed by ${this.name}`);
  }
}

describe('ConditionalAgent', () => {
  it('should route to first matching condition', async () => {
    const techAgent = new NamedAgent('tech-agent');
    const generalAgent = new NamedAgent('general-agent');
    const defaultAgent = new NamedAgent('default-agent');

    const conditional = new ConditionalAgent('router', defaultAgent);
    conditional.addRoute(contentContains('technical'), techAgent);
    conditional.addRoute(contentContains('general'), generalAgent);

    const input = createMessage('user', 'This is a technical question');
    const result = await conditional.process(input);

    expect(result.content).toBe('Processed by tech-agent');
    expect(result.metadata?.conditional_agent_used).toBe('tech-agent');
    expect(result.metadata?.conditional_route).toBe(1);
  });

  it('should use default agent when no condition matches', async () => {
    const techAgent = new NamedAgent('tech-agent');
    const defaultAgent = new NamedAgent('default-agent');

    const conditional = new ConditionalAgent('router', defaultAgent);
    conditional.addRoute(contentContains('technical'), techAgent);

    const input = createMessage('user', 'This is something else');
    const result = await conditional.process(input);

    expect(result.content).toBe('Processed by default-agent');
    expect(result.metadata?.conditional_agent_used).toBe('default-agent');
    expect(result.metadata?.conditional_route).toBe('default');
  });

  it('should combine capabilities of all agents', () => {
    const agent1 = new NamedAgent('agent1');
    const agent2 = new NamedAgent('agent2');
    const defaultAgent = new NamedAgent('default');

    const conditional = new ConditionalAgent('router', defaultAgent);
    conditional.addRoute(contentContains('test'), agent1);
    conditional.addRoute(contentContains('other'), agent2);

    const capabilities = conditional.capabilities;
    expect(capabilities).toContain('agent1');
    expect(capabilities).toContain('agent2');
    expect(capabilities).toContain('default');
    expect(capabilities).toContain('conditional');
  });

  describe('condition helpers', () => {
    it('contentContains should check message content', () => {
      const condition = contentContains('test');
      expect(condition(createMessage('user', 'this is a test'))).toBe(true);
      expect(condition(createMessage('user', 'this is something else'))).toBe(
        false
      );
    });

    it('roleEquals should check message role', () => {
      const condition = roleEquals('user');
      expect(condition(createMessage('user', 'test'))).toBe(true);
      expect(condition(createMessage('agent', 'test'))).toBe(false);
    });

    it('metadataHasKey should check for metadata key', () => {
      const condition = metadataHasKey('priority');
      expect(
        condition(createMessage('user', 'test', { priority: 'high' }))
      ).toBe(true);
      expect(condition(createMessage('user', 'test'))).toBe(false);
    });

    it('metadataEquals should check metadata value', () => {
      const condition = metadataEquals('priority', 'high');
      expect(
        condition(createMessage('user', 'test', { priority: 'high' }))
      ).toBe(true);
      expect(
        condition(createMessage('user', 'test', { priority: 'low' }))
      ).toBe(false);
    });

    it('andConditions should combine with AND logic', () => {
      const condition = andConditions(
        contentContains('test'),
        roleEquals('user')
      );
      expect(condition(createMessage('user', 'test'))).toBe(true);
      expect(condition(createMessage('agent', 'test'))).toBe(false);
      expect(condition(createMessage('user', 'other'))).toBe(false);
    });

    it('orConditions should combine with OR logic', () => {
      const condition = orConditions(
        contentContains('test'),
        contentContains('demo')
      );
      expect(condition(createMessage('user', 'test'))).toBe(true);
      expect(condition(createMessage('user', 'demo'))).toBe(true);
      expect(condition(createMessage('user', 'other'))).toBe(false);
    });

    it('notCondition should negate condition', () => {
      const condition = notCondition(contentContains('test'));
      expect(condition(createMessage('user', 'test'))).toBe(false);
      expect(condition(createMessage('user', 'other'))).toBe(true);
    });
  });

  it('should return routes and default agent', () => {
    const agent1 = new NamedAgent('agent1');
    const defaultAgent = new NamedAgent('default');

    const conditional = new ConditionalAgent('router', defaultAgent);
    conditional.addRoute(contentContains('test'), agent1);

    const routes = conditional.getRoutes();
    expect(routes).toHaveLength(1);
    expect(routes[0].agent).toBe(agent1);

    const retrieved = conditional.getDefaultAgent();
    expect(retrieved).toBe(defaultAgent);
  });
});
