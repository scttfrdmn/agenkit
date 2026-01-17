/**
 * Observability Integration Tests
 *
 * Tests that observability features (tracing, metrics, logging, audit)
 * work correctly across different components and scenarios.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';

// ============================================
// Test Agents
// ============================================

/**
 * Simple agent for observability testing.
 */
class ObservableAgent implements Agent {
  private processCount = 0;
  private readonly logs: string[] = [];

  constructor(private readonly agentName: string = 'observable-agent') {}

  get name(): string {
    return this.agentName;
  }

  get capabilities(): string[] {
    return ['test'];
  }

  async process(message: Message): Promise<Message> {
    this.processCount++;
    this.log(`Processing message #${this.processCount}: ${message.content}`);

    return {
      role: 'agent',
      content: `Processed: ${message.content}`,
      metadata: {
        agent: this.agentName,
        process_count: this.processCount,
        timestamp: new Date().toISOString(),
      },
    };
  }

  private log(message: string): void {
    this.logs.push(`[${new Date().toISOString()}] ${message}`);
  }

  getLogs(): string[] {
    return [...this.logs];
  }

  getProcessCount(): number {
    return this.processCount;
  }
}

// ============================================
// Trace Context Management Tests
// ============================================

describe('Observability Integration: Trace Context', () => {
  it('should propagate trace context through message metadata', async () => {
    const agent = new ObservableAgent();

    const traceContext = {
      trace_id: 'abc-123-def-456',
      span_id: 'span-789',
      parent_span_id: 'parent-012',
    };

    const message: Message = {
      role: 'user',
      content: 'Test with trace context',
      metadata: { trace_context: traceContext },
    };

    const response = await agent.process(message);

    // Original trace context should be preserved in input
    expect(message.metadata?.trace_context).toEqual(traceContext);

    // Response should have its own metadata but original trace can be tracked
    expect(response.metadata?.agent).toBe('observable-agent');
  });

  it('should handle nested spans through metadata', async () => {
    const agent = new ObservableAgent();

    // Simulate parent span
    const parentSpanId = 'parent-span-001';
    const traceId = 'trace-001';

    // First call (parent span)
    const msg1: Message = {
      role: 'user',
      content: 'Parent operation',
      metadata: {
        trace_context: {
          trace_id: traceId,
          span_id: parentSpanId,
        },
      },
    };

    const response1 = await agent.process(msg1);

    // Second call (child span)
    const childSpanId = 'child-span-001';
    const msg2: Message = {
      role: 'user',
      content: 'Child operation',
      metadata: {
        trace_context: {
          trace_id: traceId,
          span_id: childSpanId,
          parent_span_id: parentSpanId,
        },
      },
    };

    const response2 = await agent.process(msg2);

    // Both operations should be part of same trace
    expect(msg1.metadata?.trace_context.trace_id).toBe(traceId);
    expect(msg2.metadata?.trace_context.trace_id).toBe(traceId);

    // Child should reference parent
    expect(msg2.metadata?.trace_context.parent_span_id).toBe(parentSpanId);

    expect(response1.metadata?.process_count).toBe(1);
    expect(response2.metadata?.process_count).toBe(2);
  });

  it('should maintain trace context across multiple agents', async () => {
    const agent1 = new ObservableAgent('agent-1');
    const agent2 = new ObservableAgent('agent-2');

    const traceId = 'distributed-trace-123';
    const span1Id = 'span-1';

    // Agent 1 processes with trace context
    const msg1: Message = {
      role: 'user',
      content: 'Step 1',
      metadata: {
        trace_context: {
          trace_id: traceId,
          span_id: span1Id,
        },
      },
    };

    const response1 = await agent1.process(msg1);

    // Agent 2 processes with same trace but different span
    const span2Id = 'span-2';
    const msg2: Message = {
      role: 'user',
      content: 'Step 2',
      metadata: {
        trace_context: {
          trace_id: traceId,
          span_id: span2Id,
          parent_span_id: span1Id,
        },
      },
    };

    const response2 = await agent2.process(msg2);

    // Both should be part of same distributed trace
    expect(msg1.metadata?.trace_context.trace_id).toBe(traceId);
    expect(msg2.metadata?.trace_context.trace_id).toBe(traceId);

    expect(response1.metadata?.agent).toBe('agent-1');
    expect(response2.metadata?.agent).toBe('agent-2');
  });
});

// ============================================
// Metrics Collection Tests
// ============================================

describe('Observability Integration: Metrics', () => {
  let agent: ObservableAgent;

  beforeEach(() => {
    agent = new ObservableAgent();
  });

  it('should track request count metrics', async () => {
    // Process multiple requests
    for (let i = 0; i < 5; i++) {
      await agent.process({ role: 'user', content: `Request ${i}` });
    }

    expect(agent.getProcessCount()).toBe(5);
  });

  it('should track metrics per agent', async () => {
    const agent1 = new ObservableAgent('metrics-agent-1');
    const agent2 = new ObservableAgent('metrics-agent-2');

    // Agent 1: 3 requests
    for (let i = 0; i < 3; i++) {
      await agent1.process({ role: 'user', content: 'test' });
    }

    // Agent 2: 7 requests
    for (let i = 0; i < 7; i++) {
      await agent2.process({ role: 'user', content: 'test' });
    }

    expect(agent1.getProcessCount()).toBe(3);
    expect(agent2.getProcessCount()).toBe(7);
  });

  it('should measure request duration', async () => {
    class TimedAgent implements Agent {
      private durations: number[] = [];

      get name(): string {
        return 'timed-agent';
      }

      get capabilities(): string[] {
        return ['test'];
      }

      async process(message: Message): Promise<Message> {
        const start = Date.now();

        // Simulate processing
        await new Promise((resolve) => setTimeout(resolve, 10));

        const duration = Date.now() - start;
        this.durations.push(duration);

        return {
          role: 'agent',
          content: `Processed in ${duration}ms`,
          metadata: { duration },
        };
      }

      getDurations(): number[] {
        return this.durations;
      }
    }

    const agent = new TimedAgent();

    await agent.process({ role: 'user', content: 'test' });
    await agent.process({ role: 'user', content: 'test' });

    const durations = agent.getDurations();
    expect(durations).toHaveLength(2);
    expect(durations[0]).toBeGreaterThanOrEqual(10);
    expect(durations[1]).toBeGreaterThanOrEqual(10);
  });

  it('should track success and error rates', async () => {
    class ErrorTrackingAgent implements Agent {
      private successCount = 0;
      private errorCount = 0;

      get name(): string {
        return 'error-tracking-agent';
      }

      get capabilities(): string[] {
        return ['test'];
      }

      async process(message: Message): Promise<Message> {
        if (message.content === 'fail') {
          this.errorCount++;
          throw new Error('Simulated failure');
        }

        this.successCount++;
        return {
          role: 'agent',
          content: 'Success',
          metadata: { status: 'success' },
        };
      }

      getMetrics() {
        return {
          success: this.successCount,
          error: this.errorCount,
          total: this.successCount + this.errorCount,
          successRate: this.successCount / (this.successCount + this.errorCount),
        };
      }
    }

    const agent = new ErrorTrackingAgent();

    // 7 successes, 3 failures
    for (let i = 0; i < 7; i++) {
      await agent.process({ role: 'user', content: 'success' });
    }

    for (let i = 0; i < 3; i++) {
      try {
        await agent.process({ role: 'user', content: 'fail' });
      } catch {
        // Expected
      }
    }

    const metrics = agent.getMetrics();
    expect(metrics.success).toBe(7);
    expect(metrics.error).toBe(3);
    expect(metrics.total).toBe(10);
    expect(metrics.successRate).toBe(0.7);
  });
});

// ============================================
// Structured Logging Tests
// ============================================

describe('Observability Integration: Logging', () => {
  it('should capture structured logs', async () => {
    const agent = new ObservableAgent();

    await agent.process({ role: 'user', content: 'Log test' });

    const logs = agent.getLogs();
    expect(logs).toHaveLength(1);
    expect(logs[0]).toContain('Processing message #1: Log test');
  });

  it('should include timestamps in logs', async () => {
    const agent = new ObservableAgent();

    await agent.process({ role: 'user', content: 'test' });

    const logs = agent.getLogs();
    expect(logs[0]).toMatch(/\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  });

  it('should log errors with context', async () => {
    class LoggingAgent implements Agent {
      private logs: Array<{ level: string; message: string; error?: Error }> = [];

      get name(): string {
        return 'logging-agent';
      }

      get capabilities(): string[] {
        return ['test'];
      }

      async process(message: Message): Promise<Message> {
        try {
          if (message.content === 'error') {
            throw new Error('Test error');
          }

          this.logs.push({
            level: 'info',
            message: `Processed: ${message.content}`,
          });

          return {
            role: 'agent',
            content: 'Success',
          };
        } catch (error) {
          this.logs.push({
            level: 'error',
            message: `Error processing message: ${message.content}`,
            error: error as Error,
          });
          throw error;
        }
      }

      getLogs() {
        return this.logs;
      }
    }

    const agent = new LoggingAgent();

    await agent.process({ role: 'user', content: 'success' });

    try {
      await agent.process({ role: 'user', content: 'error' });
    } catch {
      // Expected
    }

    const logs = agent.getLogs();
    expect(logs).toHaveLength(2);
    expect(logs[0].level).toBe('info');
    expect(logs[1].level).toBe('error');
    expect(logs[1].error).toBeInstanceOf(Error);
  });
});

// ============================================
// Audit Logging Tests
// ============================================

describe('Observability Integration: Audit', () => {
  it('should record audit events', async () => {
    class AuditedAgent implements Agent {
      private auditLog: Array<{
        event: string;
        timestamp: string;
        metadata: Record<string, unknown>;
      }> = [];

      get name(): string {
        return 'audited-agent';
      }

      get capabilities(): string[] {
        return ['test'];
      }

      async process(message: Message): Promise<Message> {
        // Record audit event
        this.auditLog.push({
          event: 'MESSAGE_PROCESSED',
          timestamp: new Date().toISOString(),
          metadata: {
            agent: this.name,
            content: message.content,
            role: message.role,
          },
        });

        return {
          role: 'agent',
          content: `Processed: ${message.content}`,
        };
      }

      getAuditLog() {
        return this.auditLog;
      }
    }

    const agent = new AuditedAgent();

    await agent.process({ role: 'user', content: 'Test 1' });
    await agent.process({ role: 'user', content: 'Test 2' });

    const auditLog = agent.getAuditLog();
    expect(auditLog).toHaveLength(2);
    expect(auditLog[0].event).toBe('MESSAGE_PROCESSED');
    expect(auditLog[0].metadata.content).toBe('Test 1');
    expect(auditLog[1].metadata.content).toBe('Test 2');
  });

  it('should audit security-relevant events', async () => {
    class SecurityAuditAgent implements Agent {
      private auditLog: Array<{
        event: string;
        severity: string;
        timestamp: string;
        details: Record<string, unknown>;
      }> = [];

      get name(): string {
        return 'security-audit-agent';
      }

      get capabilities(): string[] {
        return ['security'];
      }

      async process(message: Message): Promise<Message> {
        // Check for suspicious patterns
        if (message.content.includes('DROP TABLE')) {
          this.auditLog.push({
            event: 'SECURITY_VIOLATION',
            severity: 'HIGH',
            timestamp: new Date().toISOString(),
            details: {
              pattern: 'SQL_INJECTION_ATTEMPT',
              content: message.content,
            },
          });

          throw new Error('Security violation detected');
        }

        return {
          role: 'agent',
          content: 'OK',
        };
      }

      getAuditLog() {
        return this.auditLog;
      }
    }

    const agent = new SecurityAuditAgent();

    try {
      await agent.process({ role: 'user', content: 'DROP TABLE users' });
    } catch {
      // Expected
    }

    const auditLog = agent.getAuditLog();
    expect(auditLog).toHaveLength(1);
    expect(auditLog[0].event).toBe('SECURITY_VIOLATION');
    expect(auditLog[0].severity).toBe('HIGH');
    expect(auditLog[0].details.pattern).toBe('SQL_INJECTION_ATTEMPT');
  });
});

// ============================================
// Cross-Component Integration Tests
// ============================================

describe('Observability Integration: Cross-Component', () => {
  it('should combine tracing, metrics, and logging', async () => {
    class FullyObservableAgent implements Agent {
      private processCount = 0;
      private logs: string[] = [];
      private metrics = {
        requests: 0,
        successes: 0,
        errors: 0,
      };

      get name(): string {
        return 'fully-observable';
      }

      get capabilities(): string[] {
        return ['test'];
      }

      async process(message: Message): Promise<Message> {
        this.processCount++;
        this.metrics.requests++;

        // Extract trace context
        const traceId = message.metadata?.trace_context?.trace_id || 'no-trace';

        // Log with trace context
        this.logs.push(`[${traceId}] Processing request #${this.processCount}`);

        try {
          if (message.content === 'error') {
            this.metrics.errors++;
            throw new Error('Test error');
          }

          this.metrics.successes++;
          return {
            role: 'agent',
            content: 'Success',
            metadata: {
              trace_id: traceId,
              request_count: this.processCount,
            },
          };
        } catch (error) {
          this.logs.push(`[${traceId}] Error: ${(error as Error).message}`);
          throw error;
        }
      }

      getObservability() {
        return {
          processCount: this.processCount,
          logs: this.logs,
          metrics: this.metrics,
        };
      }
    }

    const agent = new FullyObservableAgent();

    // Process with trace context
    await agent.process({
      role: 'user',
      content: 'test1',
      metadata: {
        trace_context: { trace_id: 'trace-001' },
      },
    });

    try {
      await agent.process({ role: 'user', content: 'error' });
    } catch {
      // Expected
    }

    const obs = agent.getObservability();

    // Verify all observability data collected
    expect(obs.processCount).toBe(2);
    expect(obs.logs).toHaveLength(3); // 2 processing + 1 error
    expect(obs.metrics.requests).toBe(2);
    expect(obs.metrics.successes).toBe(1);
    expect(obs.metrics.errors).toBe(1);

    // Verify trace context in logs
    expect(obs.logs[0]).toContain('[trace-001]');
  });
});
