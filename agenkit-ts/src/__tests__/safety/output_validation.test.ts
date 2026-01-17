/**
 * Comprehensive Output Validation Tests
 *
 * Tests cover:
 * - Schema validation patterns
 * - Sensitive data redaction
 * - Output validation middleware
 * - Size limits and security policies
 */

import { describe, it, expect } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import {
  OutputValidationError,
  SchemaValidator,
  SensitiveDataRedactor,
  OutputValidationMiddleware,
  outputValidation,
} from '../../safety/output-validation';

// ============================================
// Test Agents
// ============================================

/**
 * Agent that returns structured responses.
 */
class ResponseAgent implements Agent {
  get name(): string {
    return 'responder';
  }

  get capabilities(): string[] {
    return [];
  }

  async process(_message: Message): Promise<Message> {
    return {
      role: 'agent',
      content: { result: 'success', data: 'test output' },
    };
  }
}

/**
 * Agent that returns sensitive data.
 */
class SensitiveAgent implements Agent {
  get name(): string {
    return 'sensitive';
  }

  get capabilities(): string[] {
    return [];
  }

  async process(_message: Message): Promise<Message> {
    return {
      role: 'agent',
      content: {
        api_key: 'sk-1234567890abcdef',
        password: 'secret123',
        email: 'user@example.com',
        result: 'User data retrieved',
      },
    };
  }
}

/**
 * Agent that returns large output.
 */
class LargeOutputAgent implements Agent {
  get name(): string {
    return 'large';
  }

  get capabilities(): string[] {
    return [];
  }

  async process(_message: Message): Promise<Message> {
    return {
      role: 'agent',
      content: 'x'.repeat(100),
    };
  }
}

// ============================================
// Schema Validator Tests
// ============================================

describe('Safety: SchemaValidator', () => {
  it('should validate correct schema', () => {
    const validator = new SchemaValidator({
      expectedFields: { result: 'string', data: 'string' },
      requiredFields: new Set(['result']),
    });

    const output = { result: 'success', data: 'test' };
    const [isValid, error] = validator.validate(output);

    expect(isValid).toBe(true);
    expect(error).toBe(null);
  });

  it('should catch missing required fields', () => {
    const validator = new SchemaValidator({
      expectedFields: { result: 'string', data: 'string' },
      requiredFields: new Set(['result', 'data']),
    });

    const output = { result: 'success' };
    const [isValid, error] = validator.validate(output);

    expect(isValid).toBe(false);
    expect(error?.toLowerCase()).toContain('missing required fields');
    expect(error).toContain('data');
  });

  it('should catch wrong types', () => {
    const validator = new SchemaValidator({
      expectedFields: { result: 'string', count: 'number' },
    });

    const output = { result: 'success', count: 'not_an_int' };
    const [isValid, error] = validator.validate(output);

    expect(isValid).toBe(false);
    expect(error?.toLowerCase()).toContain('wrong type');
  });

  it('should allow additional fields by default', () => {
    const validator = new SchemaValidator({
      expectedFields: { result: 'string' },
      allowAdditional: true,
    });

    const output = { result: 'success', extra: 'field' };
    const [isValid, _error] = validator.validate(output);

    expect(isValid).toBe(true);
  });

  it('should reject additional fields when disabled', () => {
    const validator = new SchemaValidator({
      expectedFields: { result: 'string' },
      allowAdditional: false,
    });

    const output = { result: 'success', extra: 'field' };
    const [isValid, error] = validator.validate(output);

    expect(isValid).toBe(false);
    expect(error?.toLowerCase()).toContain('unexpected fields');
  });

  it('should parse JSON string', () => {
    const validator = new SchemaValidator({
      expectedFields: { name: 'string', count: 'number' },
    });

    const jsonStr = JSON.stringify({ name: 'test', count: 42 });
    const [isValid, error] = validator.validate(jsonStr);

    expect(isValid).toBe(true);
    expect(error).toBe(null);
  });

  it('should handle invalid JSON string', () => {
    const validator = new SchemaValidator({
      expectedFields: { name: 'string' },
    });

    const [isValid, error] = validator.validate('not valid json');
    expect(isValid).toBe(false);
    expect(error?.toLowerCase()).toContain('json');
  });

  it('should reject non-dict non-JSON input', () => {
    const validator = new SchemaValidator({
      expectedFields: { name: 'string' },
    });

    const [isValid, error] = validator.validate(12345);
    expect(isValid).toBe(false);
    expect(error?.toLowerCase()).toMatch(/dictionary|json/);
  });

  it('should support optional fields', () => {
    const validator = new SchemaValidator({
      expectedFields: { name: 'string', age: 'number', email: 'string' },
      requiredFields: new Set(['name']), // age and email are optional
    });

    // Without optional fields
    let [isValid] = validator.validate({ name: 'Alice' });
    expect(isValid).toBe(true);

    // With some optional fields
    [isValid] = validator.validate({ name: 'Alice', age: 30 });
    expect(isValid).toBe(true);

    // With all fields
    [isValid] = validator.validate({ name: 'Alice', age: 30, email: 'alice@example.com' });
    expect(isValid).toBe(true);

    // With optional field but wrong type
    const [isValidWrong, error] = validator.validate({ name: 'Alice', age: 'thirty' });
    expect(isValidWrong).toBe(false);
    expect(error?.toLowerCase()).toContain('wrong type');
  });

  it('should accept anything when no schema specified', () => {
    const validator = new SchemaValidator();

    let [isValid] = validator.validate({ any: 'data', structure: 123 });
    expect(isValid).toBe(true);

    [isValid] = validator.validate('plain string');
    expect(isValid).toBe(true);

    [isValid] = validator.validate([1, 2, 3]);
    expect(isValid).toBe(true);
  });
});

// ============================================
// Sensitive Data Redactor Tests
// ============================================

describe('Safety: SensitiveDataRedactor', () => {
  it('should redact sensitive field names', () => {
    const redactor = new SensitiveDataRedactor();

    const data = {
      username: 'alice',
      password: 'secret123',
      api_key: 'sk-abcdef',
      result: 'success',
    };

    const redacted = redactor.redact(data) as Record<string, unknown>;

    expect(redacted['password']).toBe('***REDACTED***');
    expect(redacted['api_key']).toBe('***REDACTED***');
    expect(redacted['username']).toBe('alice');
    expect(redacted['result']).toBe('success');
  });

  it('should redact API keys in strings', () => {
    const redactor = new SensitiveDataRedactor();

    const text = 'Your API key is sk-1234567890abcdefghij1234567890ab';
    const redacted = redactor.redact(text) as string;

    expect(redacted).not.toContain('sk-1234567890');
    expect(redacted).toContain('***REDACTED***_API_KEY');
  });

  it('should redact email addresses', () => {
    const redactor = new SensitiveDataRedactor();

    const text = 'Contact me at user@example.com for details';
    const redacted = redactor.redact(text) as string;

    expect(redacted).not.toContain('user@example.com');
    expect(redacted).toContain('***REDACTED***_EMAIL');
  });

  it('should redact phone numbers', () => {
    const redactor = new SensitiveDataRedactor();

    const text = 'Call me at 123-456-7890';
    const redacted = redactor.redact(text) as string;

    expect(redacted).not.toContain('123-456-7890');
    expect(redacted).toContain('***REDACTED***_PHONE');
  });

  it('should detect sensitive data', () => {
    const redactor = new SensitiveDataRedactor();

    const sensitiveData = { password: 'secret' };
    expect(redactor.hasSensitiveData(sensitiveData)).toBe(true);

    const safeData = { username: 'alice', result: 'success' };
    expect(redactor.hasSensitiveData(safeData)).toBe(false);
  });

  it('should redact nested structures', () => {
    const redactor = new SensitiveDataRedactor();

    const data = {
      user: { name: 'Alice', password: 'secret123' },
      api_key: 'sk-abcdef',
    };

    const redacted = redactor.redact(data) as Record<string, unknown>;
    const user = redacted['user'] as Record<string, unknown>;

    expect(user['password']).toBe('***REDACTED***');
    expect(redacted['api_key']).toBe('***REDACTED***');
    expect(user['name']).toBe('Alice');
  });

  it('should redact SSN', () => {
    const redactor = new SensitiveDataRedactor();

    const text = 'My SSN is 123-45-6789';
    const redacted = redactor.redact(text) as string;

    expect(redacted).not.toContain('123-45-6789');
    expect(redacted).toContain('***REDACTED***_SSN');
  });

  it('should redact credit card numbers', () => {
    const redactor = new SensitiveDataRedactor();

    const text = 'Card: 1234 5678 9012 3456';
    const redacted = redactor.redact(text) as string;

    expect(redacted).not.toContain('1234 5678 9012 3456');
    expect(redacted).toContain('***REDACTED***_CREDIT_CARD');
  });

  it('should redact JWT tokens', () => {
    const redactor = new SensitiveDataRedactor();

    const text =
      'Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U';
    const redacted = redactor.redact(text) as string;

    expect(redacted).not.toContain('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9');
    expect(redacted).toContain('***REDACTED***');
  });

  it('should redact AWS access keys', () => {
    const redactor = new SensitiveDataRedactor();

    const text = 'AWS Key: AKIAIOSFODNN7EXAMPLE';
    const redacted = redactor.redact(text) as string;

    expect(redacted).not.toContain('AKIAIOSFODNN7EXAMPLE');
    expect(redacted).toContain('***REDACTED***_AWS_ACCESS_KEY');
  });

  it('should redact GitHub tokens', () => {
    const redactor = new SensitiveDataRedactor();

    const text = 'GitHub: ghp_1234567890abcdefghijklmnopqrstuv12';
    const redacted = redactor.redact(text) as string;

    expect(redacted).not.toContain('ghp_1234567890abcdefghijklmnopqrstuv12');
    expect(redacted).toContain('***REDACTED***');
  });

  it('should redact list of dicts', () => {
    const redactor = new SensitiveDataRedactor();

    const data = [
      { name: 'Alice', password: 'secret1' },
      { name: 'Bob', api_key: 'key123' },
    ];

    const redacted = redactor.redact(data) as Array<Record<string, unknown>>;

    expect(redacted[0]['name']).toBe('Alice');
    expect(redacted[0]['password']).toBe('***REDACTED***');
    expect(redacted[1]['name']).toBe('Bob');
    expect(redacted[1]['api_key']).toBe('***REDACTED***');
  });

  it('should match sensitive fields case-insensitively', () => {
    const redactor = new SensitiveDataRedactor();

    const data = {
      PASSWORD: 'secret',
      ApiKey: 'key123',
      Token: 'token456',
    };

    const redacted = redactor.redact(data) as Record<string, unknown>;

    expect(redacted['PASSWORD']).toBe('***REDACTED***');
    expect(redacted['ApiKey']).toBe('***REDACTED***');
    expect(redacted['Token']).toBe('***REDACTED***');
  });

  it('should support custom sensitive fields', () => {
    const redactor = new SensitiveDataRedactor({
      sensitiveFields: new Set(['internal_id', 'employee_code']),
    });

    const data = {
      name: 'Alice',
      internal_id: 'EMP-12345',
      employee_code: 'ABC123',
    };

    const redacted = redactor.redact(data) as Record<string, unknown>;

    expect(redacted['name']).toBe('Alice');
    expect(redacted['internal_id']).toBe('***REDACTED***');
    expect(redacted['employee_code']).toBe('***REDACTED***');
  });

  it('should support custom redaction text', () => {
    const redactor = new SensitiveDataRedactor({ redactionText: '[HIDDEN]' });

    const data = { password: 'secret' };
    const redacted = redactor.redact(data) as Record<string, unknown>;

    expect(redacted['password']).toBe('[HIDDEN]');
  });

  it('should detect sensitive data in nested structures', () => {
    const redactor = new SensitiveDataRedactor();

    const data = { user: { profile: { password: 'secret' } } };

    expect(redactor.hasSensitiveData(data)).toBe(true);

    // Also test list with nested dicts
    const dataList = [{ safe: 'data' }, { nested: { password: 'secret' } }];
    expect(redactor.hasSensitiveData(dataList)).toBe(true);
  });

  it('should pass primitives through unchanged', () => {
    const redactor = new SensitiveDataRedactor();

    expect(redactor.redact(123)).toBe(123);
    expect(redactor.redact(45.67)).toBe(45.67);
    expect(redactor.redact(true)).toBe(true);
    expect(redactor.redact(null)).toBe(null);
  });

  it('should redact string with multiple PII types', () => {
    const redactor = new SensitiveDataRedactor();

    const text = 'Contact: user@example.com, SSN: 123-45-6789, Card: 1234567890123456';
    const redacted = redactor.redact(text) as string;

    expect(redacted).not.toContain('user@example.com');
    expect(redacted).not.toContain('123-45-6789');
    expect(redacted).not.toContain('1234567890123456');
    expect(redacted).toContain('***REDACTED***');
  });
});

// ============================================
// Output Validation Middleware Tests
// ============================================

describe('Safety: OutputValidationMiddleware', () => {
  it('should allow valid output', async () => {
    const agent = new ResponseAgent();
    const schema = new SchemaValidator({
      expectedFields: { result: 'string', data: 'string' },
    });
    const middleware = new OutputValidationMiddleware(agent, schema);

    const message: Message = { role: 'user', content: 'test' };
    const response = await middleware.process(message);

    const content = response.content as Record<string, unknown>;
    expect(content['result']).toBe('success');
  });

  it('should block invalid schema', async () => {
    const agent = new ResponseAgent();
    const schema = new SchemaValidator({
      expectedFields: { result: 'string', count: 'number' },
      requiredFields: new Set(['count']),
    });
    const middleware = new OutputValidationMiddleware(agent, schema);

    const message: Message = { role: 'user', content: 'test' };

    await expect(middleware.process(message)).rejects.toThrow(OutputValidationError);
    await expect(middleware.process(message)).rejects.toThrow(/validation failed/i);
  });

  it('should auto-redact sensitive data', async () => {
    const agent = new SensitiveAgent();
    const middleware = new OutputValidationMiddleware(agent, undefined, undefined, true);

    const message: Message = { role: 'user', content: 'test' };
    const response = await middleware.process(message);

    const content = response.content as Record<string, unknown>;

    // Sensitive fields should be redacted
    expect(content['api_key']).toBe('***REDACTED***');
    expect(content['password']).toBe('***REDACTED***');
    // Non-sensitive fields should remain
    expect(content['result']).toBe('User data retrieved');
  });

  it('should block oversized output', async () => {
    const agent = new LargeOutputAgent();
    const middleware = new OutputValidationMiddleware(agent, undefined, undefined, true, 50);

    const message: Message = { role: 'user', content: 'test' };

    await expect(middleware.process(message)).rejects.toThrow(OutputValidationError);
    await expect(middleware.process(message)).rejects.toThrow(/exceeds maximum size/i);
  });

  it('should allow disabling auto-redaction', async () => {
    const agent = new SensitiveAgent();
    const middleware = new OutputValidationMiddleware(agent, undefined, undefined, false);

    const message: Message = { role: 'user', content: 'test' };
    const response = await middleware.process(message);

    const content = response.content as Record<string, unknown>;

    // Sensitive data should NOT be redacted
    expect(content['api_key']).toBe('sk-1234567890abcdef');
    expect(content['password']).toBe('secret123');
  });

  it('should preserve agent name', () => {
    const agent = new ResponseAgent();
    const middleware = new OutputValidationMiddleware(agent);
    expect(middleware.name).toBe(agent.name);
  });

  it('should preserve agent capabilities', () => {
    const agent = new ResponseAgent();
    const middleware = new OutputValidationMiddleware(agent);
    expect(middleware.capabilities).toEqual(agent.capabilities);
  });

  it('should warn when sensitive data detected', async () => {
    const agent = new SensitiveAgent();
    const middleware = new OutputValidationMiddleware(agent, undefined, undefined, true);

    // Capture console output
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const message: Message = { role: 'user', content: 'test' };
    await middleware.process(message);

    expect(consoleWarnSpy).toHaveBeenCalled();
    expect(consoleWarnSpy.mock.calls[0][0]).toMatch(/WARNING/);

    consoleWarnSpy.mockRestore();
  });

  it('should support custom redactor', async () => {
    class CustomAgent implements Agent {
      get name(): string {
        return 'custom';
      }

      get capabilities(): string[] {
        return [];
      }

      async process(_message: Message): Promise<Message> {
        return {
          role: 'agent',
          content: { internal_id: 'SECRET-123', data: 'public' },
        };
      }
    }

    const customRedactor = new SensitiveDataRedactor({
      sensitiveFields: new Set(['internal_id']),
      redactionText: '[REMOVED]',
    });

    const agent = new CustomAgent();
    const middleware = new OutputValidationMiddleware(agent, undefined, customRedactor, true);

    const message: Message = { role: 'user', content: 'test' };
    const response = await middleware.process(message);

    const content = response.content as Record<string, unknown>;
    expect(content['internal_id']).toBe('[REMOVED]');
    expect(content['data']).toBe('public');
  });

  it('should combine schema validation and redaction', async () => {
    class CombinedAgent implements Agent {
      get name(): string {
        return 'combined';
      }

      get capabilities(): string[] {
        return [];
      }

      async process(_message: Message): Promise<Message> {
        return {
          role: 'agent',
          content: {
            username: 'alice',
            password: 'secret',
            age: 30,
            status: 'active',
          },
        };
      }
    }

    const schema = new SchemaValidator({
      expectedFields: {
        username: 'string',
        password: 'string',
        age: 'number',
        status: 'string',
      },
    });

    const agent = new CombinedAgent();
    const middleware = new OutputValidationMiddleware(agent, schema, undefined, true);

    const message: Message = { role: 'user', content: 'test' };
    const response = await middleware.process(message);

    const content = response.content as Record<string, unknown>;

    // Should pass schema validation AND redact password
    expect(content['username']).toBe('alice');
    expect(content['password']).toBe('***REDACTED***');
    expect(content['age']).toBe(30);
    expect(content['status']).toBe('active');
  });
});

// ============================================
// Decorator Function Tests
// ============================================

describe('Safety: outputValidation Decorator', () => {
  it('should create middleware with decorator', () => {
    class TestAgent implements Agent {
      get name(): string {
        return 'test';
      }

      get capabilities(): string[] {
        return [];
      }

      async process(message: Message): Promise<Message> {
        return { role: 'agent', content: 'test output' };
      }
    }

    const baseAgent = new TestAgent();
    const middlewareFn = outputValidation({ autoRedact: true, maxSize: 5000 });

    const agent = middlewareFn(baseAgent);

    expect(agent).toBeInstanceOf(OutputValidationMiddleware);
    expect((agent as any).autoRedact).toBe(true);
    expect((agent as any).maxSize).toBe(5000);
  });

  it('should support schema in decorator', () => {
    class TestAgent implements Agent {
      get name(): string {
        return 'test';
      }

      get capabilities(): string[] {
        return [];
      }

      async process(message: Message): Promise<Message> {
        return { role: 'agent', content: 'test output' };
      }
    }

    const baseAgent = new TestAgent();
    const schema = new SchemaValidator({ expectedFields: { result: 'string' } });

    const middlewareFn = outputValidation({ schema, autoRedact: false });

    const agent = middlewareFn(baseAgent);

    expect(agent).toBeInstanceOf(OutputValidationMiddleware);
    expect((agent as any).schema).toBe(schema);
    expect((agent as any).autoRedact).toBe(false);
  });
});
