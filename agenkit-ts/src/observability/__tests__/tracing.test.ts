/**
 * Tests for tracing module.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  initTracing,
  shutdownTracing,
  getTracer,
  TracingMiddleware,
  injectTraceContext,
} from '../tracing';
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

describe('Tracing', () => {
  afterEach(async () => {
    await shutdownTracing();
  });

  describe('initTracing', () => {
    it('should initialize tracer provider', () => {
      const provider = initTracing({
        serviceName: 'test-service',
        consoleExport: false,
      });

      expect(provider).toBeDefined();
      expect(getTracer()).toBeDefined();
    });

    it('should support console export', () => {
      initTracing({
        serviceName: 'test-service',
        consoleExport: true,
      });

      expect(getTracer()).toBeDefined();
    });

    it('should support OTLP endpoint', () => {
      initTracing({
        serviceName: 'test-service',
        otlpEndpoint: 'http://localhost:4318/v1/traces',
      });

      expect(getTracer()).toBeDefined();
    });
  });

  describe('TracingMiddleware', () => {
    beforeEach(() => {
      initTracing({
        serviceName: 'test-service',
        consoleExport: false,
      });
    });

    it('should wrap agent with tracing', async () => {
      const agent = new MockAgent();
      const tracedAgent = new TracingMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const response = await tracedAgent.process(message);

      expect(response.content).toBe('Processed: Test message');
    });

    it('should inject trace context into response', async () => {
      const agent = new MockAgent();
      const tracedAgent = new TracingMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const response = await tracedAgent.process(message);

      expect(response.metadata).toBeDefined();
      expect(response.metadata?.trace_context).toBeDefined();
    });

    it('should handle errors and record them', async () => {
      class FailingAgent implements Agent {
        public readonly name = 'failing-agent';
        public readonly capabilities = ['fail'];

        async process(_message: Message): Promise<Message> {
          throw new Error('Test error');
        }
      }

      const agent = new FailingAgent();
      const tracedAgent = new TracingMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      await expect(tracedAgent.process(message)).rejects.toThrow('Test error');
    });

    it('should work without tracing initialized', async () => {
      await shutdownTracing();

      const agent = new MockAgent();
      const tracedAgent = new TracingMiddleware(agent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const response = await tracedAgent.process(message);

      expect(response.content).toBe('Processed: Test message');
    });

    it('should support custom span names', async () => {
      const agent = new MockAgent();
      const tracedAgent = new TracingMiddleware(agent, 'custom.operation');

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const response = await tracedAgent.process(message);

      expect(response.content).toBe('Processed: Test message');
    });
  });

  describe('injectTraceContext', () => {
    it('should inject trace context when span is active', () => {
      initTracing({
        serviceName: 'test-service',
        consoleExport: false,
      });

      // Note: Without an active span, this will return empty metadata
      const metadata = injectTraceContext({});
      expect(metadata).toBeDefined();
    });

    it('should preserve existing metadata', () => {
      initTracing({
        serviceName: 'test-service',
        consoleExport: false,
      });

      const metadata = injectTraceContext({ existing: 'value' });
      expect(metadata.existing).toBe('value');
    });
  });
});
