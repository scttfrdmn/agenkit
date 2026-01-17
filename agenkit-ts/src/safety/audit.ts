/**
 * Security audit logging for agent operations.
 *
 * Provides structured logging with:
 * - Event type classification
 * - Severity levels
 * - JSON formatting
 * - Log rotation support
 * - Searchable audit trail
 */

import * as fs from 'fs';
import * as path from 'path';

/**
 * Types of security audit events.
 */
export enum AuditEventType {
  ACCESS_GRANTED = 'access_granted',
  ACCESS_DENIED = 'access_denied',
  PERMISSION_GRANTED = 'permission_granted',
  PERMISSION_DENIED = 'permission_denied',
  INPUT_VALIDATION_FAILED = 'input_validation_failed',
  OUTPUT_VALIDATION_FAILED = 'output_validation_failed',
  PROMPT_INJECTION_DETECTED = 'prompt_injection_detected',
  SENSITIVE_DATA_DETECTED = 'sensitive_data_detected',
  ANOMALY_DETECTED = 'anomaly_detected',
  AGENT_STARTED = 'agent_started',
  AGENT_COMPLETED = 'agent_completed',
  AGENT_FAILED = 'agent_failed',
}

/**
 * Severity levels for audit events.
 */
export enum AuditSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

/**
 * Structured audit event.
 */
export interface AuditEvent {
  /** Type of audit event */
  eventType: AuditEventType;

  /** Event severity */
  severity: AuditSeverity;

  /** User identifier */
  userId: string;

  /** Agent name (if applicable) */
  agentName: string;

  /** Human-readable message */
  message: string;

  /** ISO 8601 timestamp */
  timestamp: string;

  /** Additional event details */
  details: Record<string, unknown>;
}

/**
 * Configuration for audit logger.
 */
export interface SecurityAuditLoggerConfig {
  /** Path to log file (default: 'security_audit.log') */
  logFile?: string;

  /** Maximum log file size before rotation in bytes (default: 100MB) */
  maxBytes?: number;

  /** Number of backup files to keep (default: 10) */
  backupCount?: number;

  /** Minimum severity to log (default: INFO) */
  minSeverity?: AuditSeverity;

  /** Also output to console (default: true) */
  alsoLogToConsole?: boolean;
}

/**
 * Security audit logger with structured logging and log rotation.
 *
 * Features:
 * - Structured JSON logging
 * - Log rotation based on file size
 * - Severity-based filtering
 * - Console and file output
 * - Searchable audit trail
 *
 * Example:
 *   const logger = new SecurityAuditLogger({
 *     logFile: 'audit.log',
 *     minSeverity: AuditSeverity.WARNING,
 *   });
 *
 *   logger.logAccessDenied('user_123', 'admin_panel', 'read', 'Insufficient permissions');
 */
export class SecurityAuditLogger {
  private logFile: string;
  private maxBytes: number;
  private backupCount: number;
  private minSeverity: AuditSeverity;
  private alsoLogToConsole: boolean;
  private writeStream: fs.WriteStream | null = null;
  private currentSize: number = 0;

  constructor(config?: SecurityAuditLoggerConfig) {
    this.logFile = config?.logFile ?? 'security_audit.log';
    this.maxBytes = config?.maxBytes ?? 100 * 1024 * 1024; // 100MB
    this.backupCount = config?.backupCount ?? 10;
    this.minSeverity = config?.minSeverity ?? AuditSeverity.INFO;
    this.alsoLogToConsole = config?.alsoLogToConsole ?? true;

    // Create log file if it doesn't exist and get current size
    if (fs.existsSync(this.logFile)) {
      const stats = fs.statSync(this.logFile);
      this.currentSize = stats.size;
    }

    // Open write stream
    this.writeStream = fs.createWriteStream(this.logFile, { flags: 'a' });
  }

  /**
   * Check if severity should be logged based on minimum severity.
   */
  private shouldLog(severity: AuditSeverity): boolean {
    const severityOrder: Record<AuditSeverity, number> = {
      [AuditSeverity.INFO]: 0,
      [AuditSeverity.WARNING]: 1,
      [AuditSeverity.ERROR]: 2,
      [AuditSeverity.CRITICAL]: 3,
    };

    return severityOrder[severity] >= severityOrder[this.minSeverity];
  }

  /**
   * Rotate log files when size limit reached.
   */
  private rotateLog(): void {
    // Close current stream
    if (this.writeStream) {
      this.writeStream.end();
    }

    // Rotate backup files
    for (let i = this.backupCount - 1; i >= 1; i--) {
      const oldPath = `${this.logFile}.${i}`;
      const newPath = `${this.logFile}.${i + 1}`;
      if (fs.existsSync(oldPath)) {
        fs.renameSync(oldPath, newPath);
      }
    }

    // Move current log to .1
    if (fs.existsSync(this.logFile)) {
      fs.renameSync(this.logFile, `${this.logFile}.1`);
    }

    // Open new stream
    this.writeStream = fs.createWriteStream(this.logFile, { flags: 'a' });
    this.currentSize = 0;
  }

  /**
   * Create audit event object.
   */
  private createEvent(
    eventType: AuditEventType,
    severity: AuditSeverity,
    userId: string,
    agentName: string,
    message: string,
    details: Record<string, unknown>,
  ): AuditEvent {
    return {
      eventType,
      severity,
      userId,
      agentName,
      message,
      timestamp: new Date().toISOString(),
      details,
    };
  }

  /**
   * Log audit event.
   */
  log(event: AuditEvent): void {
    if (!this.shouldLog(event.severity)) {
      return;
    }

    const logLine = JSON.stringify(event) + '\n';
    const logBytes = Buffer.byteLength(logLine, 'utf8');

    // Check if rotation needed
    if (this.currentSize + logBytes > this.maxBytes) {
      this.rotateLog();
    }

    // Write to file
    if (this.writeStream) {
      this.writeStream.write(logLine);
      this.currentSize += logBytes;
    }

    // Also log to console if configured
    if (this.alsoLogToConsole) {
      const level = event.severity.toLowerCase();
      console.log(`[${level.toUpperCase()}] ${event.message}`, event.details);
    }
  }

  /**
   * Log access attempt.
   */
  logAccess(
    granted: boolean,
    userId: string,
    agentName: string,
    action: string,
    details?: Record<string, unknown>,
  ): void {
    const event = this.createEvent(
      granted ? AuditEventType.ACCESS_GRANTED : AuditEventType.ACCESS_DENIED,
      granted ? AuditSeverity.INFO : AuditSeverity.WARNING,
      userId,
      agentName,
      `Access ${granted ? 'granted' : 'denied'} for action: ${action}`,
      details || {},
    );
    this.log(event);
  }

  /**
   * Log permission check.
   */
  logPermissionCheck(
    granted: boolean,
    userId: string,
    agentName: string,
    permission: string,
    details?: Record<string, unknown>,
  ): void {
    const event = this.createEvent(
      granted ? AuditEventType.PERMISSION_GRANTED : AuditEventType.PERMISSION_DENIED,
      granted ? AuditSeverity.INFO : AuditSeverity.WARNING,
      userId,
      agentName,
      `Permission ${permission}: ${granted ? 'granted' : 'denied'}`,
      details || {},
    );
    this.log(event);
  }

  /**
   * Log validation failure.
   */
  logValidationFailure(
    userId: string,
    validationType: 'input' | 'output',
    reason: string,
    contentPreview?: string,
    agentName?: string,
  ): void {
    // Truncate content preview
    const truncatedPreview = contentPreview
      ? contentPreview.substring(0, 200) + (contentPreview.length > 200 ? '...' : '')
      : '';

    const event = this.createEvent(
      validationType === 'input'
        ? AuditEventType.INPUT_VALIDATION_FAILED
        : AuditEventType.OUTPUT_VALIDATION_FAILED,
      AuditSeverity.ERROR,
      userId,
      agentName || '',
      `${validationType.charAt(0).toUpperCase() + validationType.slice(1)} validation failed: ${reason}`,
      {
        validation_type: validationType,
        reason,
        content_preview: truncatedPreview,
      },
    );
    this.log(event);
  }

  /**
   * Log prompt injection detection.
   */
  logPromptInjection(
    userId: string,
    score: number,
    matchedPatterns: string[],
    contentPreview?: string,
    agentName?: string,
  ): void {
    // Truncate content preview
    const truncatedPreview = contentPreview
      ? contentPreview.substring(0, 200) + (contentPreview.length > 200 ? '...' : '')
      : '';

    const event = this.createEvent(
      AuditEventType.PROMPT_INJECTION_DETECTED,
      AuditSeverity.ERROR,
      userId,
      agentName || '',
      `Prompt injection detected (score: ${score}, patterns: ${matchedPatterns.length})`,
      {
        score,
        matched_patterns: matchedPatterns,
        content_preview: truncatedPreview,
      },
    );
    this.log(event);
  }

  /**
   * Log anomaly detection.
   */
  logAnomaly(
    userId: string,
    anomalyType: string,
    details?: Record<string, unknown>,
    agentName?: string,
  ): void {
    const eventDetails = { ...details, anomaly_type: anomalyType };

    const event = this.createEvent(
      AuditEventType.ANOMALY_DETECTED,
      AuditSeverity.WARNING,
      userId,
      agentName || '',
      `Anomaly detected: ${anomalyType}`,
      eventDetails,
    );
    this.log(event);
  }

  /**
   * Log agent execution.
   */
  logAgentExecution(
    userId: string,
    agentName: string,
    status: 'started' | 'completed' | 'failed',
    duration?: number,
    error?: string,
    details?: Record<string, unknown>,
  ): void {
    const eventTypeMap: Record<string, AuditEventType> = {
      started: AuditEventType.AGENT_STARTED,
      completed: AuditEventType.AGENT_COMPLETED,
      failed: AuditEventType.AGENT_FAILED,
    };

    const severityMap: Record<string, AuditSeverity> = {
      started: AuditSeverity.INFO,
      completed: AuditSeverity.INFO,
      failed: AuditSeverity.ERROR,
    };

    const eventDetails = { ...details };
    if (duration !== undefined) {
      eventDetails.duration_seconds = duration;
    }
    if (error) {
      eventDetails.error = error;
    }

    const message = `Agent ${status}${duration !== undefined ? ` (${duration.toFixed(2)}s)` : ''}`;

    const event = this.createEvent(
      eventTypeMap[status],
      severityMap[status],
      userId,
      agentName,
      message,
      eventDetails,
    );
    this.log(event);
  }

  /**
   * Log successful access grant.
   */
  logAccessGranted(
    userId: string,
    resource: string,
    permission: string,
    agentName?: string,
  ): void {
    const event = this.createEvent(
      AuditEventType.ACCESS_GRANTED,
      AuditSeverity.INFO,
      userId,
      agentName || '',
      `Access granted to resource: ${resource}`,
      { resource, permission },
    );
    this.log(event);
  }

  /**
   * Log access denial.
   */
  logAccessDenied(
    userId: string,
    resource: string,
    permission: string,
    reason: string,
    agentName?: string,
  ): void {
    const event = this.createEvent(
      AuditEventType.ACCESS_DENIED,
      AuditSeverity.WARNING,
      userId,
      agentName || '',
      `Access denied to resource: ${resource}`,
      { resource, permission, reason },
    );
    this.log(event);
  }

  /**
   * Log sensitive data redaction.
   */
  logSensitiveDataRedaction(
    userId: string,
    fieldsRedacted: string[],
    outputPreview: string,
    agentName?: string,
  ): void {
    // Truncate output preview
    const truncatedPreview =
      outputPreview.substring(0, 200) + (outputPreview.length > 200 ? '...' : '');

    const event = this.createEvent(
      AuditEventType.SENSITIVE_DATA_DETECTED,
      AuditSeverity.WARNING,
      userId,
      agentName || '',
      `Sensitive data redacted: ${fieldsRedacted.length} field(s)`,
      {
        fields_redacted: fieldsRedacted,
        output_preview: truncatedPreview,
      },
    );
    this.log(event);
  }

  /**
   * Close the logger and flush logs.
   * Returns a Promise that resolves when the stream is fully closed.
   */
  close(): Promise<void> {
    return new Promise((resolve) => {
      if (this.writeStream) {
        this.writeStream.end(() => {
          this.writeStream = null;
          resolve();
        });
      } else {
        resolve();
      }
    });
  }
}

// Global audit logger instance
let globalAuditLogger: SecurityAuditLogger | null = null;

/**
 * Get global audit logger instance.
 */
export function getAuditLogger(): SecurityAuditLogger {
  if (!globalAuditLogger) {
    globalAuditLogger = new SecurityAuditLogger();
  }
  return globalAuditLogger;
}

/**
 * Configure global audit logger.
 */
export async function configureAuditLogger(config: SecurityAuditLoggerConfig): Promise<void> {
  if (globalAuditLogger) {
    await globalAuditLogger.close();
  }
  globalAuditLogger = new SecurityAuditLogger(config);
}
