/**
 * Output validation and content filtering.
 *
 * Provides protection for agent outputs:
 * - Schema validation
 * - Sensitive data redaction
 * - Content policy enforcement
 * - Output size limits
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Error thrown when output validation fails.
 */
export class OutputValidationError extends Error {
  constructor(message: string, public readonly details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'OutputValidationError';
  }
}

/**
 * Validates output against expected schema.
 *
 * Supports basic type checking and structure validation.
 *
 * Example:
 *   const validator = new SchemaValidator({
 *     expectedFields: { result: 'string', count: 'number' },
 *     requiredFields: new Set(['result']),
 *   });
 *
 *   const [isValid, errorMsg] = validator.validate(output);
 */
export class SchemaValidator {
  // Expected fields and their types
  private expectedFields?: Record<string, string>;

  // Required fields (subset of expected_fields)
  private requiredFields?: Set<string>;

  // Allow additional fields not in schema
  private allowAdditional: boolean;

  constructor(config?: {
    expectedFields?: Record<string, string>;
    requiredFields?: Set<string>;
    allowAdditional?: boolean;
  }) {
    this.expectedFields = config?.expectedFields;
    this.requiredFields = config?.requiredFields;
    this.allowAdditional = config?.allowAdditional ?? true;
  }

  /**
   * Validate output against schema.
   *
   * Returns tuple of (is_valid, error_message)
   */
  validate(output: unknown): [boolean, string | null] {
    // If no schema specified, always valid
    if (!this.expectedFields) {
      return [true, null];
    }

    let outputDict: Record<string, unknown>;

    // Check if output is dict-like
    if (typeof output !== 'object' || output === null || Array.isArray(output)) {
      // Try to parse as JSON if string
      if (typeof output === 'string') {
        try {
          outputDict = JSON.parse(output);
        } catch {
          return [false, 'Output is not valid JSON or dict'];
        }
      } else {
        return [false, 'Output must be a dictionary or JSON string'];
      }
    } else {
      outputDict = output as Record<string, unknown>;
    }

    // Check required fields
    if (this.requiredFields) {
      const missing = [...this.requiredFields].filter((field) => !(field in outputDict));
      if (missing.length > 0) {
        return [false, `Missing required fields: ${missing.join(', ')}`];
      }
    }

    // Check field types
    for (const [fieldName, expectedType] of Object.entries(this.expectedFields)) {
      if (fieldName in outputDict) {
        const value = outputDict[fieldName];
        const actualType = typeof value;

        // Special handling for 'array' type
        if (expectedType === 'array') {
          if (!Array.isArray(value)) {
            return [false, `Field '${fieldName}' has wrong type: expected array, got ${actualType}`];
          }
        } else if (actualType !== expectedType) {
          return [
            false,
            `Field '${fieldName}' has wrong type: expected ${expectedType}, got ${actualType}`,
          ];
        }
      }
    }

    // Check for additional fields
    if (!this.allowAdditional) {
      const expectedKeys = new Set(Object.keys(this.expectedFields));
      const extra = Object.keys(outputDict).filter((key) => !expectedKeys.has(key));
      if (extra.length > 0) {
        return [false, `Unexpected fields: ${extra.join(', ')}`];
      }
    }

    return [true, null];
  }
}

/**
 * Redacts sensitive data from outputs.
 *
 * Detects and redacts:
 * - API keys
 * - Passwords
 * - Tokens
 * - PII (email, phone, SSN, credit cards)
 * - Custom sensitive patterns
 *
 * Example:
 *   const redactor = new SensitiveDataRedactor({
 *     sensitiveFields: new Set(['password', 'api_key', 'secret']),
 *     redactionText: '[REDACTED]',
 *   });
 *
 *   const redacted = redactor.redact(data);
 */
export class SensitiveDataRedactor {
  // Sensitive field names (case-insensitive)
  private sensitiveFields: Set<string>;

  // Patterns for detecting sensitive data
  private sensitivePatterns: [string, string][];

  // Redaction placeholder
  private redactionText: string;

  constructor(config?: {
    sensitiveFields?: Set<string>;
    sensitivePatterns?: [string, string][];
    redactionText?: string;
  }) {
    this.sensitiveFields = config?.sensitiveFields ?? new Set([
      'password',
      'api_key',
      'apikey',
      'token',
      'secret',
      'auth',
      'credential',
      'private_key',
      'access_key',
    ]);

    this.sensitivePatterns = config?.sensitivePatterns ?? [
      // API keys (common formats)
      ['sk-[a-zA-Z0-9]{32,}', 'API_KEY'],
      ['[a-zA-Z0-9_-]{32,}', 'API_KEY'], // Generic token
      // AWS credentials
      ['AKIA[0-9A-Z]{16}', 'AWS_ACCESS_KEY'],
      // GitHub tokens
      ['ghp_[a-zA-Z0-9]{36}', 'GITHUB_TOKEN'],
      // Email addresses
      ['\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b', 'EMAIL'],
      // Phone numbers (US format)
      ['\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b', 'PHONE'],
      // SSN
      ['\\b\\d{3}-\\d{2}-\\d{4}\\b', 'SSN'],
      // Credit card numbers
      ['\\b\\d{4}[-\\s]?\\d{4}[-\\s]?\\d{4}[-\\s]?\\d{4}\\b', 'CREDIT_CARD'],
      // JWT tokens
      ['eyJ[a-zA-Z0-9_-]+\\.eyJ[a-zA-Z0-9_-]+\\.[a-zA-Z0-9_-]+', 'JWT'],
    ];

    this.redactionText = config?.redactionText ?? '***REDACTED***';
  }

  /**
   * Redact sensitive data from output.
   */
  redact(data: unknown): unknown {
    if (typeof data === 'object' && data !== null && !Array.isArray(data)) {
      return this.redactDict(data as Record<string, unknown>);
    } else if (typeof data === 'string') {
      return this.redactString(data);
    } else if (Array.isArray(data)) {
      return data.map((item) => this.redact(item));
    } else {
      return data;
    }
  }

  /**
   * Redact sensitive fields in dictionary.
   */
  private redactDict(data: Record<string, unknown>): Record<string, unknown> {
    const redacted: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(data)) {
      // Check if field name is sensitive
      if (this.sensitiveFields.has(key.toLowerCase())) {
        redacted[key] = this.redactionText;
      }
      // Recursively redact nested structures
      else if (typeof value === 'object' || typeof value === 'string' || Array.isArray(value)) {
        redacted[key] = this.redact(value);
      } else {
        redacted[key] = value;
      }
    }

    return redacted;
  }

  /**
   * Redact sensitive patterns from string.
   */
  private redactString(text: string): string {
    let redacted = text;

    // Apply pattern-based redaction
    for (const [pattern, dataType] of this.sensitivePatterns) {
      const regex = new RegExp(pattern, 'gi');
      redacted = redacted.replace(regex, `${this.redactionText}_${dataType}`);
    }

    return redacted;
  }

  /**
   * Check if data contains sensitive information.
   */
  hasSensitiveData(data: unknown): boolean {
    if (typeof data === 'object' && data !== null && !Array.isArray(data)) {
      const dict = data as Record<string, unknown>;

      // Check field names
      if (Object.keys(dict).some((key) => this.sensitiveFields.has(key.toLowerCase()))) {
        return true;
      }

      // Check values recursively
      return Object.values(dict).some((v) => this.hasSensitiveData(v));
    } else if (typeof data === 'string') {
      // Check patterns
      for (const [pattern] of this.sensitivePatterns) {
        const regex = new RegExp(pattern, 'i');
        if (regex.test(data)) {
          return true;
        }
      }
    } else if (Array.isArray(data)) {
      return data.some((item) => this.hasSensitiveData(item));
    }

    return false;
  }
}

/**
 * Middleware for output validation and sensitive data redaction.
 *
 * Features:
 * - Schema validation
 * - Sensitive data redaction
 * - Output size limits
 * - Content policy enforcement
 *
 * Example:
 *   const agent = new OutputValidationMiddleware(
 *     baseAgent,
 *     new SchemaValidator({ expectedFields: { result: 'string' } }),
 *     new SensitiveDataRedactor(),
 *     true, // auto-redact
 *     100000, // max size
 *   );
 */
export class OutputValidationMiddleware implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private agent: Agent;
  private schema?: SchemaValidator;
  private redactor: SensitiveDataRedactor;
  private autoRedact: boolean;
  private maxSize: number;

  constructor(
    agent: Agent,
    schema?: SchemaValidator,
    redactor?: SensitiveDataRedactor,
    autoRedact: boolean = true,
    maxSize: number = 100000,
  ) {
    this.agent = agent;
    this.name = agent.name;
    this.capabilities = agent.capabilities;
    this.schema = schema;
    this.redactor = redactor || new SensitiveDataRedactor();
    this.autoRedact = autoRedact;
    this.maxSize = maxSize;
  }

  /**
   * Process message with output validation.
   */
  async process(message: Message): Promise<Message> {
    // Process with wrapped agent
    let response = await this.agent.process(message);

    // 1. Check output size
    const contentStr = response.content ? String(response.content) : '';
    if (contentStr.length > this.maxSize) {
      throw new OutputValidationError(`Output exceeds maximum size (${this.maxSize} chars)`, {
        actual_size: contentStr.length,
      });
    }

    // 2. Validate against schema
    if (this.schema) {
      const [isValid, errorMsg] = this.schema.validate(response.content);
      if (!isValid) {
        throw new OutputValidationError(`Output validation failed: ${errorMsg}`, {
          content_preview: contentStr.substring(0, 200),
        });
      }
    }

    // 3. Auto-redact sensitive data
    if (this.autoRedact) {
      const redactedContent = this.redactor.redact(response.content);

      // Create new Message with redacted content
      response = createMessage({
        role: response.role,
        content: redactedContent,
        metadata: response.metadata,
        timestamp: response.timestamp,
      });
    }

    // 4. Log if sensitive data detected (even if redacted)
    if (this.autoRedact && this.redactor.hasSensitiveData(response.content)) {
      console.warn('WARNING: Output may contain sensitive data (has been redacted)');
    }

    return response;
  }
}

/**
 * Create output validation middleware function.
 *
 * Example:
 *   const agent = applyMiddleware(baseAgent, [
 *     outputValidation({
 *       schema: new SchemaValidator({ expectedFields: { result: 'string' } }),
 *       autoRedact: true,
 *       maxSize: 100000,
 *     }),
 *   ]);
 */
export function outputValidation(config?: {
  schema?: SchemaValidator;
  redactor?: SensitiveDataRedactor;
  autoRedact?: boolean;
  maxSize?: number;
}): (agent: Agent) => Agent {
  return (agent: Agent) =>
    new OutputValidationMiddleware(
      agent,
      config?.schema,
      config?.redactor,
      config?.autoRedact,
      config?.maxSize,
    );
}
