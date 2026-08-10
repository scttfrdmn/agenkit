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
  resolveOtlpEndpoint,
  resolveServiceName,
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

  // #771: negative-verification target — OTEL_EXPORTER_OTLP_ENDPOINT /
  // OTEL_SERVICE_NAME must be read as defaults when the corresponding
  // config field is not supplied, and an explicit config field must still
  // win over the environment.
  describe('env var fallback (#771)', () => {
    const ENV_KEYS = ['OTEL_EXPORTER_OTLP_ENDPOINT', 'OTEL_SERVICE_NAME'];
    const savedEnv: Record<string, string | undefined> = {};

    beforeEach(() => {
      for (const key of ENV_KEYS) {
        savedEnv[key] = process.env[key];
      }
    });

    afterEach(() => {
      for (const key of ENV_KEYS) {
        if (savedEnv[key] === undefined) {
          delete process.env[key];
        } else {
          process.env[key] = savedEnv[key];
        }
      }
    });

    it('resolveOtlpEndpoint falls back to OTEL_EXPORTER_OTLP_ENDPOINT when not supplied', () => {
      process.env.OTEL_EXPORTER_OTLP_ENDPOINT = 'http://collector-from-env:4318/v1/traces';
      expect(resolveOtlpEndpoint(undefined)).toBe('http://collector-from-env:4318/v1/traces');
    });

    it('resolveOtlpEndpoint prefers an explicit value over the env var', () => {
      process.env.OTEL_EXPORTER_OTLP_ENDPOINT = 'http://collector-from-env:4318/v1/traces';
      expect(resolveOtlpEndpoint('http://explicit:4318/v1/traces')).toBe(
        'http://explicit:4318/v1/traces'
      );
    });

    it('resolveOtlpEndpoint returns undefined when neither is set', () => {
      delete process.env.OTEL_EXPORTER_OTLP_ENDPOINT;
      expect(resolveOtlpEndpoint(undefined)).toBeUndefined();
    });

    it('resolveServiceName falls back to OTEL_SERVICE_NAME when not supplied', () => {
      process.env.OTEL_SERVICE_NAME = 'service-from-env';
      expect(resolveServiceName(undefined)).toBe('service-from-env');
    });

    it('resolveServiceName prefers an explicit value over the env var', () => {
      process.env.OTEL_SERVICE_NAME = 'service-from-env';
      expect(resolveServiceName('explicit-service')).toBe('explicit-service');
    });

    it('resolveServiceName defaults to "agenkit" when neither is set', () => {
      delete process.env.OTEL_SERVICE_NAME;
      expect(resolveServiceName(undefined)).toBe('agenkit');
    });

    it('initTracing builds a provider using OTEL_EXPORTER_OTLP_ENDPOINT when otlpEndpoint is not supplied', () => {
      process.env.OTEL_EXPORTER_OTLP_ENDPOINT = 'http://collector-from-env:4318/v1/traces';
      process.env.OTEL_SERVICE_NAME = 'service-from-env';

      const provider = initTracing({ consoleExport: false });

      expect(provider).toBeDefined();
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
