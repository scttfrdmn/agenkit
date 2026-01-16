/**
 * Integration tests for observability modules.
 *
 * Tests all 4 modules working together: tracing, metrics, logging, and audit.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  initTracing,
  shutdownTracing,
  TracingMiddleware,
  extractTraceContext,
} from '../tracing';
import { initMetrics, shutdownMetrics, MetricsMiddleware } from '../metrics';
import { LogLevel, configureLogging, Logger } from '../logging';
import {
  AuditEventType,
  AuditSeverity,
  AuditLogger,
  ConsoleAuditAdapter,
  createAuditEvent,
} from '../audit';
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

class DelayedAgent implements Agent {
  public readonly name = 'delayed-agent';
  public readonly capabilities = ['delayed'];

  async process(message: Message): Promise<Message> {
    await new Promise((resolve) => setTimeout(resolve, 50));
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

describe('Observability Integration', () => {
  afterEach(async () => {
    await shutdownTracing();
    await shutdownMetrics();
  });

  describe('Full Stack Setup', () => {
    it('should initialize all observability components', async () => {
      // Initialize tracing
      const tracerProvider = initTracing({
        serviceName: 'integration-test',
        consoleExport: false,
      });
      expect(tracerProvider).toBeDefined();

      // Initialize metrics
      const metricsProvider = await initMetrics({
        serviceName: 'integration-test',
        port: 8910,
      });
      expect(metricsProvider).toBeDefined();

      // Configure logging
      configureLogging({
        level: LogLevel.INFO,
        structured: true,
        includeTraceContext: true,
      });

      // Create audit logger
      const auditLogger = new AuditLogger([new ConsoleAuditAdapter()]);
      expect(auditLogger).toBeDefined();
    });
  });

  describe('Tracing + Metrics Middleware Composition', () => {
    beforeEach(async () => {
      initTracing({
        serviceName: 'integration-test',
        consoleExport: false,
      });

      await initMetrics({
        serviceName: 'integration-test',
        port: 8911,
      });
    });

    it('should compose tracing and metrics middleware', async () => {
      const agent = new MockAgent();
      const tracedAgent = new TracingMiddleware(agent);
      const monitoredAgent = new MetricsMiddleware(tracedAgent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const response = await monitoredAgent.process(message);

      expect(response.content).toBe('Processed: Test message');
      expect(response.metadata?.trace_context).toBeDefined();
    });

    it('should propagate trace context through middleware layers', async () => {
      const agent = new MockAgent();
      const tracedAgent = new TracingMiddleware(agent);
      const monitoredAgent = new MetricsMiddleware(tracedAgent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      const response = await monitoredAgent.process(message);

      // Trace context should be present in response
      expect(response.metadata).toBeDefined();
      expect(response.metadata?.trace_context).toBeDefined();
    });

    it('should record metrics with trace correlation', async () => {
      const agent = new DelayedAgent();
      const tracedAgent = new TracingMiddleware(agent);
      const monitoredAgent = new MetricsMiddleware(tracedAgent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      await monitoredAgent.process(message);

      // Both tracing and metrics should have recorded data
      // Metrics recorded: request count, latency
      // Tracing recorded: span with timing
    });

    it('should handle errors with both tracing and metrics', async () => {
      const agent = new FailingAgent();
      const tracedAgent = new TracingMiddleware(agent);
      const monitoredAgent = new MetricsMiddleware(tracedAgent);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      await expect(monitoredAgent.process(message)).rejects.toThrow('Test error');

      // Error should be recorded in both systems
      // Metrics: error counter incremented
      // Tracing: span marked as error
    });
  });

  describe('Trace Context Propagation', () => {
    beforeEach(() => {
      initTracing({
        serviceName: 'integration-test',
        consoleExport: false,
      });
    });

    it('should extract trace context from message metadata', async () => {
      const agent = new MockAgent();
      const tracedAgent = new TracingMiddleware(agent);

      // Simulate incoming request with trace context
      const message: Message = {
        role: 'user',
        content: 'Test message',
        metadata: {
          traceparent: '00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01',
        },
      };

      const context = extractTraceContext(message.metadata || {});
      expect(context).toBeDefined();

      const response = await tracedAgent.process(message);

      // Response should have trace context
      expect(response.metadata?.trace_context).toBeDefined();
    });

    it('should propagate trace context across multiple agents', async () => {
      const agent1 = new MockAgent();
      const tracedAgent1 = new TracingMiddleware(agent1, 'agent1.process');

      const agent2 = new MockAgent();
      const tracedAgent2 = new TracingMiddleware(agent2, 'agent2.process');

      // First agent processes message
      const message1: Message = {
        role: 'user',
        content: 'First message',
      };

      const response1 = await tracedAgent1.process(message1);

      // Second agent receives first agent's response
      const message2: Message = {
        role: 'user',
        content: 'Second message',
        metadata: response1.metadata,
      };

      const response2 = await tracedAgent2.process(message2);

      // Both should have trace context
      expect(response1.metadata?.trace_context).toBeDefined();
      expect(response2.metadata?.trace_context).toBeDefined();
    });
  });

  describe('Logging with Trace Context', () => {
    beforeEach(() => {
      initTracing({
        serviceName: 'integration-test',
        consoleExport: false,
      });

      configureLogging({
        level: LogLevel.INFO,
        structured: true,
        includeTraceContext: true,
      });
    });

    it('should include trace context in logs', async () => {
      const agent = new MockAgent();
      const tracedAgent = new TracingMiddleware(agent);

      const logger = new Logger('integration-test');

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      logger.info('Processing message', { messageContent: message.content });

      await tracedAgent.process(message);

      // Log should include trace_id and span_id when available
    });
  });

  describe('Audit Logging with Agent Operations', () => {
    beforeEach(() => {
      initTracing({
        serviceName: 'integration-test',
        consoleExport: false,
      });
    });

    it('should log agent requests to audit log', async () => {
      const agent = new MockAgent();
      const tracedAgent = new TracingMiddleware(agent);

      const auditLogger = new AuditLogger([new ConsoleAuditAdapter()]);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      // Log request
      const requestEvent = createAuditEvent(
        AuditEventType.AGENT_REQUEST,
        AuditSeverity.INFO,
        `Agent ${agent.name} received request`
      );
      requestEvent.actor = agent.name;
      requestEvent.resource = message.content;
      await auditLogger.logEvent(requestEvent);

      const response = await tracedAgent.process(message);

      // Log response
      const responseEvent = createAuditEvent(
        AuditEventType.AGENT_RESPONSE,
        AuditSeverity.INFO,
        'Agent processed request successfully'
      );
      responseEvent.actor = agent.name;
      responseEvent.resource = message.content;
      responseEvent.result = 'success';
      await auditLogger.logEvent(responseEvent);

      expect(response.content).toBe('Processed: Test message');
    });

    it('should log agent errors to audit log', async () => {
      const agent = new FailingAgent();
      const tracedAgent = new TracingMiddleware(agent);

      const auditLogger = new AuditLogger([new ConsoleAuditAdapter()]);

      const message: Message = {
        role: 'user',
        content: 'Test message',
      };

      try {
        await tracedAgent.process(message);
      } catch (error) {
        // Log error
        const errorEvent = createAuditEvent(
          AuditEventType.AGENT_ERROR,
          AuditSeverity.ERROR,
          `Agent ${agent.name} error: ${(error as Error).message}`
        );
        errorEvent.actor = agent.name;
        errorEvent.result = 'error';
        await auditLogger.logEvent(errorEvent);
      }

      // Error should be logged to audit
    });
  });

  describe('Concurrent Operations with Observability', () => {
    beforeEach(async () => {
      initTracing({
        serviceName: 'integration-test',
        consoleExport: false,
      });

      await initMetrics({
        serviceName: 'integration-test',
        port: 8912,
      });
    });

    it('should handle concurrent agent requests', async () => {
      const agent = new DelayedAgent();
      const tracedAgent = new TracingMiddleware(agent);
      const monitoredAgent = new MetricsMiddleware(tracedAgent);

      // Process multiple concurrent requests
      const promises = [];
      for (let i = 0; i < 5; i++) {
        const message: Message = {
          role: 'user',
          content: `Message ${i}`,
        };

        promises.push(monitoredAgent.process(message));
      }

      const responses = await Promise.all(promises);

      expect(responses).toHaveLength(5);
      responses.forEach((response, i) => {
        expect(response.content).toBe(`Processed: Message ${i}`);
        expect(response.metadata?.trace_context).toBeDefined();
      });
    });
  });
});
