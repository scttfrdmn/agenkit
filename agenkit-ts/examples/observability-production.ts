/**
 * Production Observability Example
 *
 * Demonstrates complete production-ready observability setup with:
 * - Distributed tracing with OTLP export
 * - Prometheus metrics
 * - Structured JSON logging with trace correlation
 * - Audit logging for security and compliance
 *
 * Usage:
 *   npx ts-node examples/observability-production.ts
 *
 * View metrics at: http://localhost:8004/metrics
 */

import * as path from 'path';
import {
  Agent,
  Message,
  initTracing,
  initMetrics,
  configureLogging,
  LogLevel,
  TracingMiddleware,
  MetricsMiddleware,
  AuditLogger,
  FileAuditAdapter,
  ConsoleAuditAdapter,
  AuditEventType,
  AuditSeverity,
  createAuditEvent,
  getLoggerWithTrace,
  shutdownTracing,
  shutdownMetrics,
} from '../src';

/**
 * Production-ready agent with full observability.
 */
class ProductionAgent implements Agent {
  public readonly name: string;
  public readonly capabilities: string[];
  private readonly logger;
  private readonly auditLogger: AuditLogger;

  constructor(name: string, auditLogger: AuditLogger) {
    this.name = name;
    this.capabilities = ['process'];
    this.logger = getLoggerWithTrace(`ProductionAgent.${name}`);
    this.auditLogger = auditLogger;
  }

  async process(message: Message): Promise<Message> {
    // Audit log: Request received
    const requestEvent = createAuditEvent(
      AuditEventType.AGENT_REQUEST,
      AuditSeverity.INFO,
      `Agent ${this.name} received request`
    );
    requestEvent.actor = this.name;
    requestEvent.resource = typeof message.content === 'string' ? message.content : 'unknown';
    requestEvent.action = 'process';
    await this.auditLogger.logEvent(requestEvent);

    this.logger.info('Processing message', {
      agent: this.name,
      role: message.role,
    });

    // Simulate processing
    await new Promise((resolve) => setTimeout(resolve, 50));

    const response: Message = {
      role: 'assistant',
      content: `Processed by ${this.name}: ${message.content}`,
      metadata: {
        processed_by: this.name,
        timestamp: new Date().toISOString(),
      },
    };

    // Audit log: Response sent
    const responseEvent = createAuditEvent(
      AuditEventType.AGENT_RESPONSE,
      AuditSeverity.INFO,
      `Agent ${this.name} sent response`
    );
    responseEvent.actor = this.name;
    responseEvent.result = 'success';
    await this.auditLogger.logEvent(responseEvent);

    this.logger.info('Message processed successfully', {
      agent: this.name,
    });

    return response;
  }
}

/**
 * Agent that validates input and logs security events.
 */
class ValidationAgent implements Agent {
  public readonly name = 'validator';
  public readonly capabilities = ['validate'];
  private readonly logger;
  private readonly auditLogger: AuditLogger;

  constructor(auditLogger: AuditLogger) {
    this.logger = getLoggerWithTrace('ValidationAgent');
    this.auditLogger = auditLogger;
  }

  async process(message: Message): Promise<Message> {
    this.logger.info('Validating message');

    // Simulate validation
    const content = typeof message.content === 'string' ? message.content : '';

    // Check for suspicious patterns
    if (content.includes('DROP TABLE') || content.includes('<script>')) {
      this.logger.warn('Security violation detected', {
        violation_type: 'sql_injection_or_xss',
      });

      // Audit log: Security violation
      await this.auditLogger.logSecurityViolation({
        clientId: 'user-unknown',
        violationType: 'injection_attempt',
        description: 'Detected SQL injection or XSS attempt in message',
        metadata: { pattern_matched: content.substring(0, 50) },
      });

      throw new Error('Validation failed: suspicious content detected');
    }

    // Check rate limiting (simulated)
    const messageCount = 10;
    if (messageCount > 5) {
      this.logger.warn('Rate limit check', {
        message_count: messageCount,
      });

      // Audit log: Rate limit (informational only)
      await this.auditLogger.logRateLimitExceeded({
        clientId: 'user-unknown',
        endpoint: '/agent/process',
        limit: 5,
        window: '1m',
      });
    }

    return message;
  }
}

/**
 * Main production example function.
 */
async function main() {
  console.log('=== Agenkit TypeScript Production Observability Example ===\n');

  // 1. Initialize full observability stack
  console.log('1. Initializing production observability stack...');

  // Initialize distributed tracing
  initTracing({
    serviceName: 'agenkit-production',
    // In production, configure OTLP endpoint:
    // otlpEndpoint: 'http://localhost:4317'
    consoleExport: true, // For demo purposes
  });

  // Initialize Prometheus metrics
  await initMetrics({
    serviceName: 'agenkit-production',
    port: 8004,
  });

  // Configure structured logging
  configureLogging({
    level: LogLevel.INFO,
    structured: true,
    includeTraceContext: true,
  });

  // Initialize audit logging to both console and file
  const auditLogPath = path.join(__dirname, 'audit.log');
  const auditLogger = new AuditLogger([
    new ConsoleAuditAdapter(false), // No colors for production
    new FileAuditAdapter(auditLogPath, true), // JSON structured
  ]);

  console.log('✓ Production observability initialized');
  console.log('  • Tracing: OpenTelemetry with OTLP');
  console.log('  • Metrics: Prometheus at http://localhost:8004/metrics');
  console.log('  • Logging: Structured JSON with trace context');
  console.log('  • Audit: Console + File (audit.log)\n');

  // 2. Create production agents
  console.log('2. Creating production agents...');

  const validator = new ValidationAgent(auditLogger);
  const processor = new ProductionAgent('processor-1', auditLogger);

  // Wrap with observability middleware
  const monitoredValidator = new MetricsMiddleware(new TracingMiddleware(validator));
  const monitoredProcessor = new MetricsMiddleware(new TracingMiddleware(processor));

  console.log('✓ Agents created with full observability\n');

  // 3. Log authentication (simulated)
  console.log('3. Simulating authentication...');

  await auditLogger.logAuthAttempt({
    userId: 'user-123',
    success: true,
    method: 'api_key',
    ipAddress: '192.168.1.100',
  });

  await auditLogger.logAuthorization({
    userId: 'user-123',
    resource: '/api/agents',
    action: 'process',
    allowed: true,
  });

  console.log('✓ Authentication events logged\n');

  // 4. Process valid message
  console.log('4. Processing valid message...');

  const validMessage: Message = {
    role: 'user',
    content: 'Hello from production system',
  };

  try {
    const validated = await monitoredValidator.process(validMessage);
    const response = await monitoredProcessor.process(validated);
    console.log(`✓ Valid message processed: "${response.content}"\n`);
  } catch (error) {
    console.error('✗ Processing failed:', (error as Error).message, '\n');
  }

  // 5. Attempt processing malicious message
  console.log('5. Processing malicious message (security demo)...');

  const maliciousMessage: Message = {
    role: 'user',
    content: 'DROP TABLE users; --',
  };

  try {
    await monitoredValidator.process(maliciousMessage);
  } catch (error) {
    console.log(`✓ Malicious message blocked: ${(error as Error).message}\n`);

    // Log the error event
    const errorEvent = createAuditEvent(
      AuditEventType.AGENT_ERROR,
      AuditSeverity.ERROR,
      `Validation failed: ${(error as Error).message}`
    );
    errorEvent.actor = 'validator';
    errorEvent.result = 'blocked';
    await auditLogger.logEvent(errorEvent);
  }

  // 6. Log configuration change (simulated)
  console.log('6. Logging configuration change...');

  await auditLogger.logConfigurationChange({
    userId: 'admin-456',
    component: 'agent',
    parameter: 'max_tokens',
    oldValue: 1000,
    newValue: 2000,
    metadata: { reason: 'Increased capacity for production' },
  });

  console.log('✓ Configuration change logged\n');

  // 7. Show production observability summary
  console.log('7. Production Observability Features:');
  console.log('   ✓ Distributed Tracing:');
  console.log('     - OpenTelemetry with OTLP export');
  console.log('     - W3C Trace Context propagation');
  console.log('     - Spans include agent metadata');
  console.log('   ✓ Metrics Collection:');
  console.log('     - Prometheus exposition format');
  console.log('     - Request counts by agent/status');
  console.log('     - Latency histograms');
  console.log('     - Error counters');
  console.log('   ✓ Structured Logging:');
  console.log('     - JSON format for log aggregation');
  console.log('     - Trace context correlation');
  console.log('     - Multiple log levels');
  console.log('   ✓ Audit Logging:');
  console.log('     - Authentication attempts');
  console.log('     - Authorization decisions');
  console.log('     - Security violations');
  console.log('     - Configuration changes');
  console.log('     - Multi-adapter support (file + console)\n');

  console.log('8. Access Observability Data:');
  console.log('   • Metrics: curl http://localhost:8004/metrics');
  console.log('   • Audit Log: cat examples/audit.log');
  console.log('   • Traces: Check console output or OTLP collector\n');

  console.log('=== Production Example Complete ===\n');

  // Wait for exporters to flush
  await new Promise((resolve) => setTimeout(resolve, 2000));

  // Cleanup
  await shutdownTracing();
  await shutdownMetrics();

  console.log('Observability shutdown complete');
  console.log(`Audit log saved to: ${auditLogPath}`);
}

// Run production example
main().catch((error) => {
  console.error('Production example failed:', error);
  process.exit(1);
});
