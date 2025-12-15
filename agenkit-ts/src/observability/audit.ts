/**
 * Pluggable audit logging for security and compliance.
 *
 * Provides structured audit logging with support for multiple backends
 * through a pluggable adapter architecture.
 */

import { trace } from '@opentelemetry/api';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Types of audit events.
 */
export enum AuditEventType {
  AUTH_ATTEMPT = 'auth_attempt',
  AUTH_SUCCESS = 'auth_success',
  AUTH_FAILURE = 'auth_failure',
  AUTHORIZATION = 'authorization',
  RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded',
  VALIDATION_FAILURE = 'validation_failure',
  CONFIGURATION_CHANGE = 'configuration_change',
  SECURITY_VIOLATION = 'security_violation',
  SUSPICIOUS_ACTIVITY = 'suspicious_activity',
  AGENT_REQUEST = 'agent_request',
  AGENT_RESPONSE = 'agent_response',
  AGENT_ERROR = 'agent_error',
}

/**
 * Severity levels for audit events.
 */
export enum AuditSeverity {
  DEBUG = 'debug',
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

/**
 * Structured audit event.
 */
export interface AuditEvent {
  event_type: AuditEventType;
  severity: AuditSeverity;
  message: string;
  timestamp: Date;
  actor?: string;
  resource?: string;
  action?: string;
  result?: string;
  metadata?: Record<string, any>;
  trace_id?: string;
  span_id?: string;
}

/**
 * Create a new audit event with trace context.
 */
export function createAuditEvent(
  eventType: AuditEventType,
  severity: AuditSeverity,
  message: string,
): AuditEvent {
  const event: AuditEvent = {
    event_type: eventType,
    severity,
    message,
    timestamp: new Date(),
    metadata: {},
  };

  // Add trace context if available
  const span = trace.getActiveSpan();
  if (span) {
    const spanContext = span.spanContext();
    if (spanContext.traceId) {
      event.trace_id = spanContext.traceId;
      event.span_id = spanContext.spanId;
    }
  }

  return event;
}

/**
 * Interface for audit log adapters.
 */
export interface AuditAdapter {
  logEvent(event: AuditEvent): void | Promise<void>;
}

/**
 * Audit adapter that logs to console.
 */
export class ConsoleAuditAdapter implements AuditAdapter {
  private useColors: boolean;
  private colors: Record<AuditSeverity, string>;
  private reset: string;

  constructor(useColors = true) {
    this.useColors = useColors;
    this.colors = {
      [AuditSeverity.DEBUG]: '\x1b[36m', // Cyan
      [AuditSeverity.INFO]: '\x1b[32m', // Green
      [AuditSeverity.WARNING]: '\x1b[33m', // Yellow
      [AuditSeverity.ERROR]: '\x1b[31m', // Red
      [AuditSeverity.CRITICAL]: '\x1b[35m', // Magenta
    };
    this.reset = '\x1b[0m';
  }

  logEvent(event: AuditEvent): void {
    const color = this.useColors ? this.colors[event.severity] : '';
    const reset = this.useColors ? this.reset : '';

    const parts: string[] = [
      event.timestamp.toISOString(),
      `${color}${event.severity.toUpperCase()}${reset}`,
      `[${event.event_type}]`,
    ];

    if (event.actor) {
      parts.push(`actor=${event.actor}`);
    }
    if (event.resource) {
      parts.push(`resource=${event.resource}`);
    }
    if (event.action) {
      parts.push(`action=${event.action}`);
    }
    if (event.result) {
      parts.push(`result=${event.result}`);
    }

    parts.push(event.message);

    if (event.trace_id) {
      parts.push(`trace_id=${event.trace_id}`);
    }

    const message = parts.join(' ');

    // Write to stderr for errors, stdout for others
    if (event.severity === AuditSeverity.ERROR || event.severity === AuditSeverity.CRITICAL) {
      console.error(message);
    } else {
      console.log(message);
    }
  }
}

/**
 * Audit adapter that outputs JSON structured logs.
 */
export class StructuredAuditAdapter implements AuditAdapter {
  private stream: NodeJS.WritableStream;

  constructor(stream: NodeJS.WritableStream = process.stdout) {
    this.stream = stream;
  }

  logEvent(event: AuditEvent): void {
    const data = {
      ...event,
      timestamp: event.timestamp.toISOString(),
    };
    this.stream.write(JSON.stringify(data) + '\n');
  }
}

/**
 * Audit adapter that logs to a file.
 */
export class FileAuditAdapter implements AuditAdapter {
  private filePath: string;
  private structured: boolean;
  private stream: fs.WriteStream;

  constructor(filePath: string, structured = true) {
    this.filePath = filePath;
    this.structured = structured;

    // Create parent directory if needed
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    // Open file for appending
    this.stream = fs.createWriteStream(filePath, { flags: 'a', mode: 0o600 });
  }

  logEvent(event: AuditEvent): void {
    let message: string;

    if (this.structured) {
      const data = {
        ...event,
        timestamp: event.timestamp.toISOString(),
      };
      message = JSON.stringify(data);
    } else {
      // Human-readable format
      const parts: string[] = [
        event.timestamp.toISOString(),
        `[${event.event_type}]`,
        `severity=${event.severity}`,
      ];

      if (event.actor) {
        parts.push(`actor=${event.actor}`);
      }
      if (event.resource) {
        parts.push(`resource=${event.resource}`);
      }
      if (event.result) {
        parts.push(`result=${event.result}`);
      }
      parts.push(event.message);

      message = parts.join(' ');
    }

    this.stream.write(message + '\n');
  }

  close(): void {
    this.stream.end();
  }
}

/**
 * Main audit logger with pluggable adapters.
 */
export class AuditLogger {
  private adapters: AuditAdapter[];

  constructor(adapters?: AuditAdapter[]) {
    this.adapters = adapters || [new ConsoleAuditAdapter()];
  }

  /**
   * Log an audit event to all adapters.
   */
  async logEvent(event: AuditEvent): Promise<void> {
    const promises: Array<void | Promise<void>> = [];

    for (const adapter of this.adapters) {
      try {
        const result = adapter.logEvent(event);
        if (result instanceof Promise) {
          promises.push(result);
        }
      } catch (error) {
        // Don't let adapter failures break the application
        console.error('Audit adapter error:', error);
      }
    }

    // Wait for async adapters
    if (promises.length > 0) {
      await Promise.all(promises);
    }
  }

  /**
   * Log an authentication attempt.
   */
  async logAuthAttempt(options: {
    userId: string;
    success: boolean;
    method?: string;
    ipAddress?: string;
    reason?: string;
    metadata?: Record<string, any>;
  }): Promise<void> {
    const { userId, success, method, ipAddress, reason, metadata = {} } = options;

    const eventType = success ? AuditEventType.AUTH_SUCCESS : AuditEventType.AUTH_FAILURE;
    const severity = success ? AuditSeverity.INFO : AuditSeverity.WARNING;

    let message = `Authentication ${success ? 'succeeded' : 'failed'} for user ${userId}`;
    if (method) {
      message += ` using ${method}`;
    }
    if (!success && reason) {
      message += `: ${reason}`;
    }

    const event = createAuditEvent(eventType, severity, message);
    event.actor = userId;
    event.action = 'authenticate';
    event.result = success ? 'success' : 'failure';
    event.metadata = { ...metadata, method, ip_address: ipAddress };

    await this.logEvent(event);
  }

  /**
   * Log an authorization decision.
   */
  async logAuthorization(options: {
    userId: string;
    resource: string;
    action: string;
    allowed: boolean;
    reason?: string;
    metadata?: Record<string, any>;
  }): Promise<void> {
    const { userId, resource, action, allowed, reason, metadata = {} } = options;

    const severity = allowed ? AuditSeverity.INFO : AuditSeverity.WARNING;

    let message = `Authorization ${allowed ? 'granted' : 'denied'} for user ${userId} to ${action} ${resource}`;
    if (!allowed && reason) {
      message += `: ${reason}`;
    }

    const event = createAuditEvent(AuditEventType.AUTHORIZATION, severity, message);
    event.actor = userId;
    event.resource = resource;
    event.action = action;
    event.result = allowed ? 'allowed' : 'denied';
    event.metadata = { ...metadata, reason };

    await this.logEvent(event);
  }

  /**
   * Log a rate limit violation.
   */
  async logRateLimitExceeded(options: {
    clientId: string;
    endpoint: string;
    limit: number;
    window: string;
    metadata?: Record<string, any>;
  }): Promise<void> {
    const { clientId, endpoint, limit, window, metadata = {} } = options;

    const message = `Rate limit exceeded for ${clientId} on ${endpoint} (${limit} requests per ${window})`;

    const event = createAuditEvent(AuditEventType.RATE_LIMIT_EXCEEDED, AuditSeverity.WARNING, message);
    event.actor = clientId;
    event.resource = endpoint;
    event.action = 'request';
    event.result = 'rate_limited';
    event.metadata = { ...metadata, limit, window };

    await this.logEvent(event);
  }

  /**
   * Log an input validation failure.
   */
  async logValidationFailure(options: {
    messageId: string;
    reason: string;
    field?: string;
    value?: any;
    metadata?: Record<string, any>;
  }): Promise<void> {
    const { messageId, reason, field, value, metadata = {} } = options;

    let message = `Validation failure for message ${messageId}: ${reason}`;
    if (field) {
      message += ` (field: ${field})`;
    }

    const event = createAuditEvent(AuditEventType.VALIDATION_FAILURE, AuditSeverity.WARNING, message);
    event.resource = messageId;
    event.action = 'validate';
    event.result = 'failure';
    event.metadata = { ...metadata, reason, field, value };

    await this.logEvent(event);
  }

  /**
   * Log a configuration change.
   */
  async logConfigurationChange(options: {
    userId: string;
    component: string;
    parameter: string;
    oldValue: any;
    newValue: any;
    metadata?: Record<string, any>;
  }): Promise<void> {
    const { userId, component, parameter, oldValue, newValue, metadata = {} } = options;

    const message = `Configuration changed: ${component}.${parameter} changed from ${oldValue} to ${newValue}`;

    const event = createAuditEvent(AuditEventType.CONFIGURATION_CHANGE, AuditSeverity.INFO, message);
    event.actor = userId;
    event.resource = `${component}.${parameter}`;
    event.action = 'configure';
    event.result = 'success';
    event.metadata = { ...metadata, old_value: oldValue, new_value: newValue };

    await this.logEvent(event);
  }

  /**
   * Log a security violation.
   */
  async logSecurityViolation(options: {
    clientId: string;
    violationType: string;
    description: string;
    severity?: AuditSeverity;
    metadata?: Record<string, any>;
  }): Promise<void> {
    const { clientId, violationType, description, severity = AuditSeverity.ERROR, metadata = {} } = options;

    const message = `Security violation (${violationType}): ${description}`;

    const event = createAuditEvent(AuditEventType.SECURITY_VIOLATION, severity, message);
    event.actor = clientId;
    event.action = violationType;
    event.result = 'violation';
    event.metadata = metadata;

    await this.logEvent(event);
  }

  /**
   * Log suspicious activity.
   */
  async logSuspiciousActivity(options: {
    clientId: string;
    activityType: string;
    description: string;
    indicators?: string[];
    metadata?: Record<string, any>;
  }): Promise<void> {
    const { clientId, activityType, description, indicators = [], metadata = {} } = options;

    const message = `Suspicious activity detected (${activityType}): ${description}`;

    const event = createAuditEvent(AuditEventType.SUSPICIOUS_ACTIVITY, AuditSeverity.WARNING, message);
    event.actor = clientId;
    event.action = activityType;
    event.result = 'suspicious';
    event.metadata = { ...metadata, indicators };

    await this.logEvent(event);
  }
}
