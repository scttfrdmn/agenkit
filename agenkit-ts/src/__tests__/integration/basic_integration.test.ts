/**
 * Basic Integration Tests
 *
 * Validates core integration functionality like message serialization
 * and agent behavior consistency. These tests can run without external dependencies.
 */

import { describe, it, expect } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';

/**
 * Simple echo agent for testing.
 */
class SimpleEchoAgent implements Agent {
  get name(): string {
    return 'simple-echo';
  }

  get capabilities(): string[] {
    return ['echo'];
  }

  async process(message: Message): Promise<Message> {
    return {
      role: 'agent',
      content: `Echo: ${message.content}`,
      metadata: {
        original: message.content,
        language: 'typescript',
        agent: this.name,
      },
    };
  }
}

// ============================================
// Message Tests
// ============================================

describe('Basic Integration: Messages', () => {
  it('should create message with basic properties', () => {
    const msg: Message = {
      role: 'user',
      content: 'Hello',
      metadata: { test: true },
    };

    expect(msg.role).toBe('user');
    expect(msg.content).toBe('Hello');
    expect(msg.metadata?.test).toBe(true);
  });

  it('should serialize message to JSON and back', () => {
    const original: Message = {
      role: 'user',
      content: 'Test message',
      metadata: {
        string: 'value',
        number: 42,
        float: 3.14,
        bool: true,
        nested: { key: 'value' },
        list: [1, 2, 3],
      },
    };

    // Serialize to JSON
    const jsonStr = JSON.stringify(original);
    expect(jsonStr).toBeTruthy();

    // Deserialize
    const deserialized = JSON.parse(jsonStr);

    // Validate
    expect(deserialized.role).toBe('user');
    expect(deserialized.content).toBe('Test message');
    expect(deserialized.metadata.string).toBe('value');
    expect(deserialized.metadata.number).toBe(42);
    expect(deserialized.metadata.float).toBe(3.14);
    expect(deserialized.metadata.bool).toBe(true);
    expect(deserialized.metadata.nested.key).toBe('value');
    expect(deserialized.metadata.list).toEqual([1, 2, 3]);
  });

  it('should handle empty content', () => {
    const msg: Message = {
      role: 'user',
      content: '',
    };

    expect(msg.content).toBe('');
  });

  it('should handle Unicode content', () => {
    const unicodeContent = 'Hello 世界 🌍 Привет';
    const msg: Message = {
      role: 'user',
      content: unicodeContent,
    };

    expect(msg.content).toBe(unicodeContent);

    // Should serialize/deserialize correctly
    const serialized = JSON.stringify(msg);
    const deserialized = JSON.parse(serialized);
    expect(deserialized.content).toBe(unicodeContent);
  });

  it('should handle complex nested metadata', () => {
    const complexMetadata = {
      trace_id: 'abc-123',
      user: {
        id: 42,
        name: 'Test User',
        preferences: { language: 'en', timezone: 'UTC' },
      },
      tags: ['test', 'integration', 'metadata'],
      counts: [1, 2, 3, 4, 5],
    };

    const msg: Message = {
      role: 'user',
      content: 'Complex test',
      metadata: complexMetadata,
    };

    expect(msg.metadata).toEqual(complexMetadata);
  });
});

// ============================================
// Agent Processing Tests
// ============================================

describe('Basic Integration: Agent Processing', () => {
  it('should process message with basic agent', async () => {
    const agent = new SimpleEchoAgent();

    expect(agent.name).toBe('simple-echo');
    expect(agent.capabilities).toContain('echo');

    const msg: Message = { role: 'user', content: 'Hello' };
    const response = await agent.process(msg);

    expect(response.role).toBe('agent');
    expect(response.content).toContain('Echo: Hello');
    expect(response.metadata?.original).toBe('Hello');
    expect(response.metadata?.language).toBe('typescript');
  });

  it('should preserve agent metadata', async () => {
    const agent = new SimpleEchoAgent();

    const msg: Message = {
      role: 'user',
      content: 'Test',
      metadata: { request_id: '123' },
    };

    const response = await agent.process(msg);

    // Agent adds its own metadata
    expect(response.metadata?.original).toBe('Test');
    expect(response.metadata?.language).toBe('typescript');
    expect(response.metadata?.agent).toBe('simple-echo');
  });

  it('should handle multiple sequential requests', async () => {
    const agent = new SimpleEchoAgent();

    const messages: Message[] = Array.from({ length: 5 }, (_, i) => ({
      role: 'user',
      content: `Message ${i}`,
    }));

    const responses = [];
    for (const msg of messages) {
      const response = await agent.process(msg);
      responses.push(response);
    }

    // Validate all responses
    expect(responses).toHaveLength(5);
    responses.forEach((response, i) => {
      expect(response.content).toContain(`Echo: Message ${i}`);
      expect(response.metadata?.original).toBe(`Message ${i}`);
    });
  });

  it('should not modify original message', async () => {
    const agent = new SimpleEchoAgent();

    const originalContent = 'Original message';
    const originalMetadata = { key: 'value' };

    const msg: Message = {
      role: 'user',
      content: originalContent,
      metadata: { ...originalMetadata },
    };

    // Store original values
    const msgContentBefore = msg.content;
    const msgMetadataBefore = { ...msg.metadata };

    // Process message
    await agent.process(msg);

    // Original message should be unchanged
    expect(msg.content).toBe(msgContentBefore);
    expect(msg.metadata).toEqual(msgMetadataBefore);
  });

  it('should produce consistent results for same input', async () => {
    const agent = new SimpleEchoAgent();

    const msg: Message = { role: 'user', content: 'Consistency test' };

    // Process same message multiple times
    const results = [];
    for (let i = 0; i < 3; i++) {
      const response = await agent.process(msg);
      results.push(response.content);
    }

    // All results should be identical
    const uniqueResults = new Set(results);
    expect(uniqueResults.size).toBe(1);
    expect(results[0]).toBe('Echo: Consistency test');
  });

  it('should handle empty content gracefully', async () => {
    const agent = new SimpleEchoAgent();

    const msg: Message = { role: 'user', content: '' };
    const response = await agent.process(msg);

    expect(response.role).toBe('agent');
    expect(response.content).toBe('Echo: ');
    expect(response.metadata?.original).toBe('');
  });

  it('should handle Unicode content in processing', async () => {
    const agent = new SimpleEchoAgent();

    const unicodeContent = 'Hello 世界 🌍 Привет';
    const msg: Message = { role: 'user', content: unicodeContent };
    const response = await agent.process(msg);

    expect(response.content).toContain(`Echo: ${unicodeContent}`);
    expect(response.metadata?.original).toBe(unicodeContent);
  });
});

// ============================================
// Agent Behavior Tests
// ============================================

describe('Basic Integration: Agent Behavior', () => {
  it('should handle concurrent requests', async () => {
    const agent = new SimpleEchoAgent();

    const messages: Message[] = Array.from({ length: 10 }, (_, i) => ({
      role: 'user',
      content: `Concurrent ${i}`,
    }));

    // Process all messages concurrently
    const results = await Promise.all(messages.map((msg) => agent.process(msg)));

    expect(results).toHaveLength(10);
    results.forEach((response, i) => {
      expect(response.content).toContain(`Echo: Concurrent ${i}`);
    });
  });

  it('should handle rapid sequential requests', async () => {
    const agent = new SimpleEchoAgent();

    const count = 100;
    const responses = [];

    for (let i = 0; i < count; i++) {
      const msg: Message = { role: 'user', content: `Request ${i}` };
      const response = await agent.process(msg);
      responses.push(response);
    }

    expect(responses).toHaveLength(count);
  });

  it('should handle messages with no metadata', async () => {
    const agent = new SimpleEchoAgent();

    const msg: Message = { role: 'user', content: 'No metadata' };
    const response = await agent.process(msg);

    expect(response.metadata?.original).toBe('No metadata');
    expect(response.metadata?.agent).toBe('simple-echo');
  });

  it('should handle very large metadata', async () => {
    const agent = new SimpleEchoAgent();

    const largeMetadata = {
      data: Array.from({ length: 1000 }, (_, i) => ({
        id: i,
        value: `value_${i}`,
      })),
    };

    const msg: Message = {
      role: 'user',
      content: 'Large metadata test',
      metadata: largeMetadata,
    };

    const response = await agent.process(msg);
    expect(response.content).toContain('Echo: Large metadata test');
  });
});
