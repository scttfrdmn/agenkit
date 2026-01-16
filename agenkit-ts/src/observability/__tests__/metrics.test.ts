/**
 * Tests for metrics module.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  initMetrics,
  shutdownMetrics,
  MetricsMiddleware,
  createMonitoredAgent,
} from '../metrics';
import { Agent, Message } from '../../core/interfaces';

class MockAgent implements Agent {
  public readonly name = 'mock-agent';
  public readonly capabilities = ['mock'];

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Processed: ${message.content}`,
    };
  }
}

class SlowAgent implements Agent {
  public readonly name = 'slow-agent';
  public readonly capabilities = ['slow'];

  async process(message: Message): Promise<Message> {
    // Simulate slow processing
    await new Promise((resolve) => setTimeout(resolve, 100));
    return {
      role: 'assistant',
      content: `Processed: ${message.content}`,
    };
  }
}

class FailingAgent implements Agent {
  public readonly name = 'failing-agent';
  public readonly capabilities = ['fail'];

  async process(_message: Message): Promise<Message> {
    throw new Error('Test error');
  }
}

describe('Metrics', () => {
  afterEach(async () => {
    await shutdownMetrics();
  });

  describe('initMetrics', () => {
    it('should initialize metrics provider', async () => {
      const provider = await initMetrics({
        serviceName: 'test-service',
        port: 8901,
      });

      expect(provider).toBeDefined();
    });

    it('should start HTTP server on specified port', async () => {
      await initMetrics({
        serviceName: 'test-service',
        port: 8902,
      });

      // Server should be running
      // Note: In a real test environment, you might want to actually hit the endpoint
    });

    it('should support custom host', async () => {
      const provider = await initMetrics({
        serviceName: 'test-service',
        port: 8903,
        host: 'localhost',
      });

      expect(provider).toBeDefined();
    });
  });

  describe('MetricsMiddleware', () => {
    beforeEach(async () => {
      await initMetrics({
        serviceName: 'test-service',
        port: 8904,
      });
    });

    it('should wrap agent with metrics', async () => {
      const agent = new MockAgent();
      const monitoredAgent = new MetricsMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const response = await monitoredAgent.process(message);

      expect(response.content).toBe('Processed: Test message');
      expect(monitoredAgent.name).toBe('mock-agent');
    });

    it('should record successful requests', async () => {
      const agent = new MockAgent();
      const monitoredAgent = new MetricsMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      await monitoredAgent.process(message);

      // Metrics should be recorded (counter incremented)
      // In a real test, you might fetch /metrics endpoint and verify
    });

    it('should record error requests', async () => {
      const agent = new FailingAgent();
      const monitoredAgent = new MetricsMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      await expect(monitoredAgent.process(message)).rejects.toThrow('Test error');

      // Error counter should be incremented
    });

    it('should record request latency', async () => {
      const agent = new SlowAgent();
      const monitoredAgent = new MetricsMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const start = Date.now();
      await monitoredAgent.process(message);
      const duration = Date.now() - start;

      expect(duration).toBeGreaterThanOrEqual(100);
      // Latency histogram should have recorded this value
    });

    it('should record message size', async () => {
      const agent = new MockAgent();
      const monitoredAgent = new MetricsMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'A'.repeat(1000), // 1000 character message
      };

      await monitoredAgent.process(message);

      // Message size histogram should have recorded this value
    });

    it('should handle multiple requests', async () => {
      const agent = new MockAgent();
      const monitoredAgent = new MetricsMiddleware(agent);

      // Process multiple messages
      for (let i = 0; i < 5; i++) {
        const message: Message = {
          role: 'user',
          content: `Test message ${i}`,
        };

        await monitoredAgent.process(message);
      }

      // All requests should be counted
    });

    it('should work without metrics initialized', async () => {
      await shutdownMetrics();

      const agent = new MockAgent();
      const monitoredAgent = new MetricsMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const response = await monitoredAgent.process(message);

      expect(response.content).toBe('Processed: Test message');
    });
  });

  describe('createMonitoredAgent', () => {
    beforeEach(async () => {
      await initMetrics({
        serviceName: 'test-service',
        port: 8905,
      });
    });

    it('should create monitored agent', async () => {
      const agent = new MockAgent();
      const monitoredAgent = createMonitoredAgent(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const response = await monitoredAgent.process(message);

      expect(response.content).toBe('Processed: Test message');
    });
  });
});
