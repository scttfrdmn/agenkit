/**
 * Tests for introspection capability.
 */

import { describe, it, expect } from 'vitest';
import {
  IntrospectionResult,
  createDefaultIntrospectionResult,
  validateIntrospectionResult,
} from './introspection';
import { Agent, Message } from './interfaces';

// Test agent implementations
class SimpleAgent implements Agent {
  readonly name = 'simple';
  readonly capabilities = ['test', 'simple'];

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Processed: ${message.content}`,
    };
  }

  introspect(): IntrospectionResult {
    return createDefaultIntrospectionResult(this);
  }
}

class AgentWithMemory implements Agent {
  readonly name = 'memory_agent';
  readonly capabilities = ['memory', 'stateful'];

  private memory = {
    shortTerm: ['item1', 'item2'],
    longTerm: ['memory1'],
  };

  private messageCount = 0;

  async process(message: Message): Promise<Message> {
    this.messageCount++;
    return {
      role: 'assistant',
      content: 'Processed',
    };
  }

  introspect(): IntrospectionResult {
    return {
      timestamp: new Date().toISOString(),
      agentName: this.name,
      capabilities: this.capabilities,
      memoryState: {
        shortTermCount: this.memory.shortTerm.length,
        longTermCount: this.memory.longTerm.length,
      },
      internalState: {
        messageCount: this.messageCount,
        hasMemory: true,
      },
      metadata: {},
    };
  }
}

describe('IntrospectionResult', () => {
  it('should create introspection result', () => {
    const result: IntrospectionResult = {
      timestamp: new Date().toISOString(),
      agentName: 'test',
      capabilities: ['test'],
      memoryState: undefined,
      internalState: {},
      metadata: {},
    };

    expect(result.agentName).toBe('test');
    expect(result.capabilities).toEqual(['test']);
    expect(result.memoryState).toBeUndefined();
    expect(result.internalState).toEqual({});
  });

  it('should validate introspection result', () => {
    const validResult: IntrospectionResult = {
      timestamp: new Date().toISOString(),
      agentName: 'test',
      capabilities: ['test'],
      memoryState: undefined,
      internalState: {},
      metadata: {},
    };

    expect(() => validateIntrospectionResult(validResult)).not.toThrow();
  });

  it('should reject empty agent name', () => {
    const invalidResult = {
      timestamp: new Date().toISOString(),
      agentName: '',
      capabilities: [],
      internalState: {},
      metadata: {},
    } as IntrospectionResult;

    expect(() => validateIntrospectionResult(invalidResult)).toThrow(
      'agentName must be a non-empty string',
    );
  });

  it('should reject non-array capabilities', () => {
    const invalidResult = {
      timestamp: new Date().toISOString(),
      agentName: 'test',
      capabilities: 'not an array',
      internalState: {},
      metadata: {},
    } as unknown as IntrospectionResult;

    expect(() => validateIntrospectionResult(invalidResult)).toThrow(
      'capabilities must be an array',
    );
  });

  it('should reject non-object internal state', () => {
    const invalidResult = {
      timestamp: new Date().toISOString(),
      agentName: 'test',
      capabilities: [],
      internalState: 'not an object',
      metadata: {},
    } as unknown as IntrospectionResult;

    expect(() => validateIntrospectionResult(invalidResult)).toThrow(
      'internalState must be an object',
    );
  });
});

describe('SimpleAgent introspection', () => {
  it('should introspect basic agent', () => {
    const agent = new SimpleAgent();
    const result = agent.introspect();

    expect(result.agentName).toBe('simple');
    expect(result.capabilities).toEqual(['test', 'simple']);
    expect(result.memoryState).toBeUndefined();
    expect(result.internalState).toEqual({});
    expect(result.timestamp).toBeDefined();
  });

  it('should have recent timestamp', () => {
    const agent = new SimpleAgent();
    const before = new Date().toISOString();
    const result = agent.introspect();
    const after = new Date().toISOString();

    expect(result.timestamp >= before).toBe(true);
    expect(result.timestamp <= after).toBe(true);
  });
});

describe('AgentWithMemory introspection', () => {
  it('should introspect agent with memory', () => {
    const agent = new AgentWithMemory();
    const result = agent.introspect();

    expect(result.agentName).toBe('memory_agent');
    expect(result.capabilities).toEqual(['memory', 'stateful']);
    expect(result.memoryState).toBeDefined();
    expect(result.memoryState?.shortTermCount).toBe(2);
    expect(result.memoryState?.longTermCount).toBe(1);
    expect(result.internalState.messageCount).toBe(0);
    expect(result.internalState.hasMemory).toBe(true);
  });

  it('should reflect state changes', async () => {
    const agent = new AgentWithMemory();

    // Initial state
    const result1 = agent.introspect();
    expect(result1.internalState.messageCount).toBe(0);

    // Process a message
    await agent.process({ role: 'user', content: 'test' });

    // State should have changed
    const result2 = agent.introspect();
    expect(result2.internalState.messageCount).toBe(1);
  });
});

describe('createDefaultIntrospectionResult', () => {
  it('should create default result for agent', () => {
    const agent = {
      name: 'test-agent',
      capabilities: ['test', 'demo'],
    };

    const result = createDefaultIntrospectionResult(agent);

    expect(result.agentName).toBe('test-agent');
    expect(result.capabilities).toEqual(['test', 'demo']);
    expect(result.memoryState).toBeUndefined();
    expect(result.internalState).toEqual({});
    expect(result.metadata).toEqual({});
    expect(result.timestamp).toBeDefined();
  });

  it('should handle agent without capabilities', () => {
    const agent = {
      name: 'simple-agent',
    };

    const result = createDefaultIntrospectionResult(agent);

    expect(result.agentName).toBe('simple-agent');
    expect(result.capabilities).toEqual([]);
  });
});

describe('introspection with metadata', () => {
  it('should support custom metadata', () => {
    const result: IntrospectionResult = {
      timestamp: new Date().toISOString(),
      agentName: 'test',
      capabilities: [],
      internalState: {},
      metadata: { custom: 'data', version: '1.0' },
    };

    expect(result.metadata.custom).toBe('data');
    expect(result.metadata.version).toBe('1.0');
  });
});
