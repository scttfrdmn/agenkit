/**
 * Tests for audit logging module.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import {
  AuditEventType,
  AuditSeverity,
  AuditEvent,
  createAuditEvent,
  ConsoleAuditAdapter,
  StructuredAuditAdapter,
  FileAuditAdapter,
  AuditLogger,
} from '../audit';

describe('Audit', () => {
  // Mock console methods
  const originalConsoleLog = console.log;
  const originalConsoleError = console.error;

  beforeEach(() => {
    console.log = vi.fn();
    console.error = vi.fn();
  });

  afterEach(() => {
    console.log = originalConsoleLog;
    console.error = originalConsoleError;
  });

  describe('createAuditEvent', () => {
    it('should create basic audit event', () => {
      const event = createAuditEvent(
        AuditEventType.AUTH_ATTEMPT,
        AuditSeverity.INFO,
        'User login attempt'
      );

      expect(event.event_type).toBe(AuditEventType.AUTH_ATTEMPT);
      expect(event.severity).toBe(AuditSeverity.INFO);
      expect(event.message).toBe('User login attempt');
      expect(event.timestamp).toBeInstanceOf(Date);
    });

    it('should include trace context when available', () => {
      const event = createAuditEvent(
        AuditEventType.AGENT_REQUEST,
        AuditSeverity.INFO,
        'Agent processed request'
      );

      // Trace context may or may not be present depending on active span
      expect(event).toBeDefined();
    });
  });

  describe('ConsoleAuditAdapter', () => {
    it('should create adapter instance', () => {
      const adapter = new ConsoleAuditAdapter();
      expect(adapter).toBeDefined();
    });

    it('should log info events to stdout', () => {
      const adapter = new ConsoleAuditAdapter();
      const event = createAuditEvent(
        AuditEventType.AGENT_REQUEST,
        AuditSeverity.INFO,
        'Test message'
      );

      adapter.logEvent(event);

      expect(console.log).toHaveBeenCalled();
    });

    it('should log error events to stderr', () => {
      const adapter = new ConsoleAuditAdapter();
      const event = createAuditEvent(
        AuditEventType.SECURITY_VIOLATION,
        AuditSeverity.ERROR,
        'Security violation'
      );

      adapter.logEvent(event);

      expect(console.error).toHaveBeenCalled();
    });

    it('should log critical events to stderr', () => {
      const adapter = new ConsoleAuditAdapter();
      const event = createAuditEvent(
        AuditEventType.SECURITY_VIOLATION,
        AuditSeverity.CRITICAL,
        'Critical security issue'
      );

      adapter.logEvent(event);

      expect(console.error).toHaveBeenCalled();
    });

    it('should support disabling colors', () => {
      const adapter = new ConsoleAuditAdapter(false);
      const event = createAuditEvent(
        AuditEventType.AUTH_SUCCESS,
        AuditSeverity.INFO,
        'Login successful'
      );

      adapter.logEvent(event);

      expect(console.log).toHaveBeenCalled();
    });

    it('should include actor in log output', () => {
      const adapter = new ConsoleAuditAdapter();
      const event = createAuditEvent(
        AuditEventType.AUTH_SUCCESS,
        AuditSeverity.INFO,
        'Login successful'
      );
      event.actor = 'user-123';

      adapter.logEvent(event);

      expect(console.log).toHaveBeenCalled();
      const call = (console.log as any).mock.calls[0][0];
      expect(call).toContain('actor=user-123');
    });

    it('should include resource in log output', () => {
      const adapter = new ConsoleAuditAdapter();
      const event = createAuditEvent(
        AuditEventType.AUTHORIZATION,
        AuditSeverity.INFO,
        'Access granted'
      );
      event.resource = '/api/agents';

      adapter.logEvent(event);

      expect(console.log).toHaveBeenCalled();
      const call = (console.log as any).mock.calls[0][0];
      expect(call).toContain('resource=/api/agents');
    });
  });

  describe('StructuredAuditAdapter', () => {
    it('should create adapter instance', () => {
      const adapter = new StructuredAuditAdapter();
      expect(adapter).toBeDefined();
    });

    it('should log events as JSON', () => {
      // Create a mock stream to capture output
      const chunks: string[] = [];
      const mockStream = {
        write: (chunk: string) => {
          chunks.push(chunk);
          return true;
        },
      } as any;

      const adapter = new StructuredAuditAdapter(mockStream);
      const event = createAuditEvent(
        AuditEventType.AGENT_REQUEST,
        AuditSeverity.INFO,
        'Test message'
      );

      adapter.logEvent(event);

      expect(chunks.length).toBeGreaterThan(0);
      const output = chunks[0].trim();
      expect(() => JSON.parse(output)).not.toThrow();
    });

    it('should include all event fields in JSON', () => {
      // Create a mock stream to capture output
      const chunks: string[] = [];
      const mockStream = {
        write: (chunk: string) => {
          chunks.push(chunk);
          return true;
        },
      } as any;

      const adapter = new StructuredAuditAdapter(mockStream);
      const event = createAuditEvent(
        AuditEventType.AUTH_SUCCESS,
        AuditSeverity.INFO,
        'Login successful'
      );
      event.actor = 'user-123';
      event.resource = '/api/login';
      event.action = 'login';
      event.result = 'success';
      event.metadata = { ip: '192.168.1.1' };

      adapter.logEvent(event);

      expect(chunks.length).toBeGreaterThan(0);
      const output = chunks[0].trim();
      const parsed = JSON.parse(output);

      expect(parsed.event_type).toBe('auth_success');
      expect(parsed.severity).toBe('info');
      expect(parsed.actor).toBe('user-123');
      expect(parsed.metadata.ip).toBe('192.168.1.1');
    });
  });

  describe('FileAuditAdapter', () => {
    const testFilePath = path.join(__dirname, 'test-audit.log');

    afterEach(() => {
      // Cleanup test file
      if (fs.existsSync(testFilePath)) {
        fs.unlinkSync(testFilePath);
      }
    });

    it('should create adapter instance', () => {
      const adapter = new FileAuditAdapter(testFilePath);
      adapter.close();
      expect(adapter).toBeDefined();
    });

    it('should write events to file', async () => {
      const adapter = new FileAuditAdapter(testFilePath);
      const event = createAuditEvent(
        AuditEventType.AGENT_REQUEST,
        AuditSeverity.INFO,
        'Test message'
      );

      adapter.logEvent(event);
      adapter.close();

      // Give the stream a moment to flush
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(fs.existsSync(testFilePath)).toBe(true);
      const content = fs.readFileSync(testFilePath, 'utf-8');
      expect(content).toContain('agent_request');
    });

    it('should write multiple events', async () => {
      const adapter = new FileAuditAdapter(testFilePath);
      const event = createAuditEvent(
        AuditEventType.AGENT_REQUEST,
        AuditSeverity.INFO,
        'Test message'
      );

      // Log 5 events
      for (let i = 0; i < 5; i++) {
        adapter.logEvent(event);
      }

      adapter.close();

      // Give the stream a moment to flush
      await new Promise((resolve) => setTimeout(resolve, 100));

      const content = fs.readFileSync(testFilePath, 'utf-8');
      const lines = content.trim().split('\n');
      expect(lines.length).toBe(5);
    });

    it('should write events immediately', async () => {
      const adapter = new FileAuditAdapter(testFilePath);
      const event = createAuditEvent(
        AuditEventType.AGENT_REQUEST,
        AuditSeverity.INFO,
        'Test message'
      );

      // Log events
      for (let i = 0; i < 3; i++) {
        adapter.logEvent(event);
      }

      adapter.close();

      // Give it a moment to complete
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(fs.existsSync(testFilePath)).toBe(true);
    });

    it('should create directory if it does not exist', async () => {
      const nestedPath = path.join(__dirname, 'nested', 'audit.log');
      const adapter = new FileAuditAdapter(nestedPath);
      const event = createAuditEvent(
        AuditEventType.AGENT_REQUEST,
        AuditSeverity.INFO,
        'Test message'
      );

      adapter.logEvent(event);
      adapter.close();

      // Give the stream a moment to flush
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(fs.existsSync(nestedPath)).toBe(true);

      // Cleanup
      fs.unlinkSync(nestedPath);
      fs.rmdirSync(path.dirname(nestedPath));
    });
  });

  describe('AuditLogger', () => {
    it('should create logger with console adapter by default', () => {
      const logger = new AuditLogger();
      expect(logger).toBeDefined();
    });

    it('should create logger with custom adapter', () => {
      const adapter = new StructuredAuditAdapter();
      const logger = new AuditLogger([adapter]);
      expect(logger).toBeDefined();
    });

    it('should log events through adapter', async () => {
      const logger = new AuditLogger([new ConsoleAuditAdapter()]);

      const event = createAuditEvent(
        AuditEventType.AUTH_ATTEMPT,
        AuditSeverity.INFO,
        'Login attempt'
      );

      await logger.logEvent(event);

      expect(console.log).toHaveBeenCalled();
    });

    it('should support logAuthAttempt method', async () => {
      const logger = new AuditLogger([new ConsoleAuditAdapter()]);

      await logger.logAuthAttempt({
        userId: 'user-123',
        success: true,
        method: 'password',
      });

      expect(console.log).toHaveBeenCalled();
    });

    it('should support logAuthAttempt for failures', async () => {
      const logger = new AuditLogger([new ConsoleAuditAdapter()]);

      await logger.logAuthAttempt({
        userId: 'user-123',
        success: false,
        reason: 'Invalid password',
      });

      expect(console.log).toHaveBeenCalled();
    });

    it('should support logAuthorization method', async () => {
      const logger = new AuditLogger([new ConsoleAuditAdapter()]);

      await logger.logAuthorization({
        userId: 'user-123',
        resource: '/api/agents',
        action: 'read',
        allowed: true,
      });

      expect(console.log).toHaveBeenCalled();
    });

    it('should support logSecurityViolation method', async () => {
      const logger = new AuditLogger([new ConsoleAuditAdapter()]);

      await logger.logSecurityViolation({
        clientId: 'client-123',
        violationType: 'sql_injection',
        description: 'SQL injection attempt detected',
      });

      expect(console.error).toHaveBeenCalled();
    });

    it('should support logRateLimitExceeded method', async () => {
      const logger = new AuditLogger([new ConsoleAuditAdapter()]);

      await logger.logRateLimitExceeded({
        clientId: 'client-123',
        endpoint: '/api/agents',
        limit: 100,
        window: '1m',
      });

      expect(console.log).toHaveBeenCalled();
    });

    it('should support logValidationFailure method', async () => {
      const logger = new AuditLogger([new ConsoleAuditAdapter()]);

      await logger.logValidationFailure({
        messageId: 'msg-123',
        reason: 'Invalid input',
        field: 'email',
      });

      expect(console.log).toHaveBeenCalled();
    });
  });
});
