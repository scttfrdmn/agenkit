/**
 * Comprehensive Security Audit Logging Tests
 *
 * Tests cover:
 * - Audit event creation and serialization
 * - Security audit logger functionality
 * - Event types and severity levels
 * - Log file management
 */

import { describe, it, expect, afterEach } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import {
  AuditEvent,
  AuditEventType,
  AuditSeverity,
  SecurityAuditLogger,
} from '../../safety/audit';

// ============================================
// Test Helpers
// ============================================

/**
 * Create a temporary log file for testing.
 */
function createTempLogFile(): string {
  const tmpDir = os.tmpdir();
  const logFile = path.join(tmpDir, `test-audit-${Date.now()}-${Math.random()}.log`);
  return logFile;
}

/**
 * Clean up temporary log file.
 */
function cleanupLogFile(logFile: string): void {
  try {
    if (fs.existsSync(logFile)) {
      fs.unlinkSync(logFile);
    }
  } catch {
    // Ignore cleanup errors
  }
}

// ============================================
// Audit Event Tests
// ============================================

describe('Safety: AuditEvent Interface', () => {
  it('should create event object with correct structure', () => {
    const event: AuditEvent = {
      eventType: AuditEventType.ACCESS_GRANTED,
      severity: AuditSeverity.INFO,
      userId: 'user_123',
      agentName: 'test_agent',
      message: 'Access granted',
      timestamp: new Date().toISOString(),
      details: { resource: 'file.txt' },
    };

    expect(event.timestamp).toBeDefined();
    expect(event.eventType).toBe(AuditEventType.ACCESS_GRANTED);
    expect(event.severity).toBe(AuditSeverity.INFO);
    expect(event.userId).toBe('user_123');
  });

  it('should serialize to JSON correctly', () => {
    const event: AuditEvent = {
      eventType: AuditEventType.PROMPT_INJECTION_DETECTED,
      severity: AuditSeverity.ERROR,
      userId: 'user_123',
      agentName: 'test_agent',
      message: 'Prompt injection detected',
      timestamp: new Date().toISOString(),
      details: { score: 15, patterns: ['ignore instructions'] },
    };

    const jsonStr = JSON.stringify(event);
    const parsed = JSON.parse(jsonStr);

    expect(parsed.eventType).toBe('prompt_injection_detected');
    expect(parsed.severity).toBe('error');
    expect(parsed.userId).toBe('user_123');
    expect(parsed.agentName).toBe('test_agent');
    expect(parsed.details.score).toBe(15);
  });

  it('should handle optional fields', () => {
    const event: AuditEvent = {
      eventType: AuditEventType.ACCESS_DENIED,
      severity: AuditSeverity.WARNING,
      userId: 'user_123',
      agentName: '',
      message: 'Access denied',
      timestamp: new Date().toISOString(),
      details: { reason: 'insufficient permissions' },
    };

    const jsonStr = JSON.stringify(event);
    const parsed = JSON.parse(jsonStr);

    expect(parsed.eventType).toBe('access_denied');
    expect(parsed.severity).toBe('warning');
    expect(parsed.details.reason).toBe('insufficient permissions');
  });
});

// ============================================
// Audit Event Type Tests
// ============================================

describe('Safety: AuditEventType', () => {
  it('should have correct event type values', () => {
    expect(AuditEventType.ACCESS_GRANTED).toBe('access_granted');
    expect(AuditEventType.ACCESS_DENIED).toBe('access_denied');
    expect(AuditEventType.PROMPT_INJECTION_DETECTED).toBe('prompt_injection_detected');
    expect(AuditEventType.SENSITIVE_DATA_DETECTED).toBe('sensitive_data_detected');
    expect(AuditEventType.INPUT_VALIDATION_FAILED).toBe('input_validation_failed');
    expect(AuditEventType.ANOMALY_DETECTED).toBe('anomaly_detected');
  });
});

// ============================================
// Audit Severity Tests
// ============================================

describe('Safety: AuditSeverity', () => {
  it('should have correct severity values', () => {
    expect(AuditSeverity.INFO).toBe('info');
    expect(AuditSeverity.WARNING).toBe('warning');
    expect(AuditSeverity.ERROR).toBe('error');
    expect(AuditSeverity.CRITICAL).toBe('critical');
  });
});

// ============================================
// Security Audit Logger Tests
// ============================================

describe('Safety: SecurityAuditLogger', () => {
  let logFile: string;

  afterEach(() => {
    if (logFile) {
      cleanupLogFile(logFile);
    }
  });

  it('should create log file', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logAccessGranted('user_123', 'file.txt', 'read:files');
    logger.close(); // Flush and close before reading

    // Check that log file was created and has content
    expect(fs.existsSync(logFile)).toBe(true);
    expect(fs.statSync(logFile).size).toBeGreaterThan(0);
  });

  it('should log in JSON format', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logPromptInjection('user_123', 15, ['ignore instructions']);
    logger.close();

    // Read log file
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();

    // Should be valid JSON
    const parsed = JSON.parse(logLine);
    expect(parsed.eventType).toBe('prompt_injection_detected');
    expect(parsed.severity).toBe('error');
  });

  it('should log access granted events', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logAccessGranted('user_123', 'file.txt', 'read:files');
    logger.close();

    // Verify log
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();
    const parsed = JSON.parse(logLine);

    expect(parsed.eventType).toBe('access_granted');
    expect(parsed.severity).toBe('info');
    expect(parsed.details.resource).toBe('file.txt');
  });

  it('should log access denied events', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logAccessDenied('user_123', 'secrets.txt', 'access:secrets', 'insufficient permissions');
    logger.close();

    // Verify log
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();
    const parsed = JSON.parse(logLine);

    expect(parsed.eventType).toBe('access_denied');
    expect(parsed.severity).toBe('warning');
    expect(parsed.details.reason).toBe('insufficient permissions');
  });

  it('should log prompt injection detection', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logPromptInjection(
      'user_123',
      15,
      ['ignore instructions', 'system mode'],
      'Ignore previous instructions...'
    );
    logger.close();

    // Verify log
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();
    const parsed = JSON.parse(logLine);

    expect(parsed.eventType).toBe('prompt_injection_detected');
    expect(parsed.severity).toBe('error');
    expect(parsed.details.score).toBe(15);
    expect(parsed.details.matched_patterns).toContain('ignore instructions');
  });

  it('should log sensitive data redaction', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logSensitiveDataRedaction('user_123', ['password', 'api_key'], '{"result": "success", ...}');
    logger.close();

    // Verify log
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();
    const parsed = JSON.parse(logLine);

    expect(parsed.eventType).toBe('sensitive_data_detected');
    expect(parsed.severity).toBe('warning');
    expect(parsed.details.fields_redacted).toContain('password');
  });

  it('should log validation failures', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logValidationFailure('user_123', 'output', 'Missing required field: result', '{"data": "test"}');
    logger.close();

    // Verify log
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();
    const parsed = JSON.parse(logLine);

    expect(parsed.eventType).toBe('output_validation_failed');
    expect(parsed.severity).toBe('error');
    expect(parsed.details.validation_type).toBe('output');
  });

  it('should log anomaly detection', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logAnomaly('user_123', 'high_request_rate', { requests_per_minute: 150, threshold: 100 });
    logger.close();

    // Verify log
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();
    const parsed = JSON.parse(logLine);

    expect(parsed.eventType).toBe('anomaly_detected');
    expect(parsed.severity).toBe('warning');
    expect(parsed.details.anomaly_type).toBe('high_request_rate');
  });

  it('should handle multiple log entries', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    // Log multiple events
    logger.logAccessGranted('user_1', 'file1.txt', 'read:files');
    logger.logAccessGranted('user_2', 'file2.txt', 'read:files');
    logger.logAccessDenied('user_3', 'secrets.txt', 'access:secrets', 'denied');
    logger.close();

    // Verify multiple entries
    const lines = fs.readFileSync(logFile, 'utf-8').trim().split('\n');
    expect(lines.length).toBe(3);

    // Each line should be valid JSON
    for (const line of lines) {
      const parsed = JSON.parse(line);
      expect(parsed.eventType).toBeDefined();
      expect(parsed.timestamp).toBeDefined();
    }
  });

  it('should include agent name when provided', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logAccessGranted('user_123', 'file.txt', 'read:files', 'test_agent');
    logger.close();

    // Verify agent name in log
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();
    const parsed = JSON.parse(logLine);

    expect(parsed.agentName).toBe('test_agent');
  });

  it('should truncate long content previews', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    const longContent = 'x'.repeat(500);
    logger.logValidationFailure('user_123', 'input', 'Too large', longContent);
    logger.close();

    // Verify truncation
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();
    const parsed = JSON.parse(logLine);
    const contentPreview = parsed.details.content_preview;

    // Allow a bit of flexibility for "..." suffix
    expect(contentPreview.length).toBeLessThanOrEqual(203); // 200 + "..."
    expect(contentPreview).toContain('...');
  });

  it('should handle missing optional fields', () => {
    logFile = createTempLogFile();
    const logger = new SecurityAuditLogger({ logFile, alsoLogToConsole: false });

    logger.logAccessGranted('user_123', 'file.txt', 'read:files');
    logger.close();

    // Should log successfully without agent_name
    const logLine = fs.readFileSync(logFile, 'utf-8').trim();
    const parsed = JSON.parse(logLine);

    expect(parsed.eventType).toBe('access_granted');
    expect(parsed.agentName === '' || parsed.agentName === undefined).toBe(true);
  });
});
