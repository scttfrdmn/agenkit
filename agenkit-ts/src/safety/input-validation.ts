/**
 * Input validation and prompt injection defense.
 *
 * Provides protection against:
 * - Prompt injection attacks
 * - Malicious inputs
 * - Content policy violations
 * - Input size limits
 */

import { Agent, Message } from '../core/interfaces';

/**
 * Error thrown when input validation fails.
 */
export class ValidationError extends Error {
  constructor(message: string, public readonly details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'ValidationError';
  }
}

/**
 * Detects potential prompt injection attempts.
 *
 * Uses pattern matching and heuristics to identify common prompt injection
 * techniques like instruction overrides, jailbreaks, and system prompts.
 *
 * Example:
 *   const detector = new PromptInjectionDetector({ threshold: 15 });
 *   const [isInjection, score, matched] = detector.detect(userInput);
 *   if (isInjection) {
 *     throw new ValidationError('Prompt injection detected');
 *   }
 */
export class PromptInjectionDetector {
  // Patterns indicating prompt injection attempts
  private dangerousPatterns: string[] = [
    'ignore\\s+.*?(previous|all|above|prior).*?instructions?',
    'disregard\\s+.*?(previous|all|above|prior)',
    'forget\\s+.*?(everything|all|previous)',
    'new\\s+instructions?:',
    'system\\s*(prompt|message)?:',
    'you\\s+are\\s+now',
    'act\\s+as\\s+(if|though)',
    'pretend\\s+(you|to)\\s+(are|be)',
    'roleplay\\s+as',
    '^sudo\\s+',
    'admin\\s+mode',
    'developer\\s+mode',
    'god\\s+mode',
    'jailbreak',
    '</?\\s*system\\s*>',
    '<\\|.*?\\|>', // Special tokens
    '\\[INST\\]', // Llama-style tokens
    '\\{system\\}',
  ];

  // Suspicious keywords (weighted scoring)
  private suspiciousKeywords: Record<string, number> = {
    ignore: 3,
    disregard: 3,
    override: 2,
    bypass: 3,
    jailbreak: 5,
    prompt: 2,
    injection: 4,
    system: 2,
    admin: 2,
    root: 2,
    sudo: 3,
    privilege: 2,
    instructions: 2,
  };

  // Score threshold for blocking (0-100)
  private threshold: number;

  constructor(config?: { patterns?: string[]; keywords?: Record<string, number>; threshold?: number }) {
    this.dangerousPatterns = config?.patterns ?? this.dangerousPatterns;
    this.suspiciousKeywords = config?.keywords ?? this.suspiciousKeywords;
    this.threshold = config?.threshold ?? 8;
  }

  /**
   * Detect prompt injection attempts.
   *
   * Returns tuple of (is_injection, score, matched_patterns)
   */
  detect(text: string): [boolean, number, string[]] {
    const textLower = text.toLowerCase();
    let score = 0;
    const matched: string[] = [];

    // Check dangerous patterns
    for (const pattern of this.dangerousPatterns) {
      const regex = new RegExp(pattern, 'i');
      if (regex.test(textLower)) {
        score += 10;
        matched.push(pattern);
      }
    }

    // Check suspicious keywords
    const words = textLower.match(/\w+/g) || [];
    for (const word of words) {
      if (word in this.suspiciousKeywords) {
        score += this.suspiciousKeywords[word];
      }
    }

    // Heuristics
    // Multiple special characters (possible encoding/obfuscation)
    const specialChars = (text.match(/[<>{}[\]|]/g) || []).length;
    if (specialChars > 5) {
      score += 2;
    }

    // Very long prompts (possible payload)
    if (text.length > 5000) {
      score += 1;
    }

    // Repeated instructions
    const instructionMatches = (textLower.match(/(please|must|you (should|will|must))/g) || [])
      .length;
    if (instructionMatches > 5) {
      score += 2;
    }

    const isInjection = score >= this.threshold;

    return [isInjection, score, matched];
  }

  /**
   * Check if text is safe (no injection detected).
   */
  isSafe(text: string): boolean {
    const [isInjection] = this.detect(text);
    return !isInjection;
  }
}

/**
 * Filters content based on policies.
 *
 * Supports:
 * - Banned words/phrases
 * - PII detection (basic)
 * - Size limits
 * - Format validation
 *
 * Example:
 *   const filter = new ContentFilter({
 *     bannedWords: new Set(['spam', 'inappropriate']),
 *     maxSize: 5000,
 *   });
 *
 *   const [isValid, errorMsg] = filter.validate(content);
 *   if (!isValid) {
 *     throw new ValidationError(errorMsg);
 *   }
 */
export class ContentFilter {
  // Banned words/phrases
  private bannedWords: Set<string>;

  // Maximum content size (characters)
  private maxSize: number;

  // Minimum content size (characters)
  private minSize: number;

  // Allowed content types (if specified)
  private allowedContentTypes?: Set<string>;

  constructor(config?: {
    bannedWords?: Set<string>;
    maxSize?: number;
    minSize?: number;
    allowedContentTypes?: Set<string>;
  }) {
    this.bannedWords = config?.bannedWords ?? new Set();
    this.maxSize = config?.maxSize ?? 10000;
    this.minSize = config?.minSize ?? 1;
    this.allowedContentTypes = config?.allowedContentTypes;
  }

  /**
   * Validate content against policies.
   *
   * Returns tuple of (is_valid, error_message)
   */
  validate(content: unknown): [boolean, string | null] {
    // Convert to string for validation
    const contentStr = typeof content === 'string' ? content : String(content);

    // Size checks
    if (contentStr.length > this.maxSize) {
      return [false, `Content exceeds maximum size (${this.maxSize} chars)`];
    }

    if (contentStr.length < this.minSize) {
      return [false, `Content below minimum size (${this.minSize} chars)`];
    }

    // Banned words
    const contentLower = contentStr.toLowerCase();
    for (const word of this.bannedWords) {
      if (contentLower.includes(word.toLowerCase())) {
        return [false, `Content contains banned word: ${word}`];
      }
    }

    // Basic PII detection (simple patterns)
    const piiPatterns: [string, string][] = [
      ['\\b\\d{3}-\\d{2}-\\d{4}\\b', 'Social Security Number'],
      ['\\b\\d{16}\\b', 'Credit Card Number'],
      ['\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b', 'Email Address'],
    ];

    for (const [pattern, piiType] of piiPatterns) {
      const regex = new RegExp(pattern, 'i');
      if (regex.test(contentStr)) {
        return [false, `Content may contain ${piiType}`];
      }
    }

    return [true, null];
  }

  /**
   * Check if content is safe.
   */
  isSafe(content: unknown): boolean {
    const [isValid] = this.validate(content);
    return isValid;
  }
}

/**
 * Middleware for input validation and prompt injection defense.
 *
 * Features:
 * - Prompt injection detection
 * - Content filtering
 * - Input sanitization
 * - Size limits
 *
 * Example:
 *   const agent = new InputValidationMiddleware(
 *     baseAgent,
 *     new PromptInjectionDetector({ threshold: 15 }),
 *     new ContentFilter({ maxSize: 5000 }),
 *     true, // strict mode
 *   );
 */
export class InputValidationMiddleware implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private agent: Agent;
  private detector: PromptInjectionDetector;
  private contentFilter: ContentFilter;
  private strict: boolean;

  constructor(
    agent: Agent,
    detector?: PromptInjectionDetector,
    contentFilter?: ContentFilter,
    strict: boolean = true,
  ) {
    this.agent = agent;
    this.name = agent.name;
    this.capabilities = agent.capabilities;
    this.detector = detector || new PromptInjectionDetector();
    this.contentFilter = contentFilter || new ContentFilter();
    this.strict = strict;
  }

  /**
   * Process message with input validation.
   */
  async process(message: Message): Promise<Message> {
    // Validate message content
    const contentStr = message.content ? String(message.content) : '';

    // 1. Check for prompt injection
    const [isInjection, score, matched] = this.detector.detect(contentStr);
    if (isInjection) {
      const errorMsg = `Potential prompt injection detected (score: ${score}, patterns: ${matched.length})`;

      if (this.strict) {
        throw new ValidationError(errorMsg, {
          score,
          matched_patterns: matched.slice(0, 3), // Show first 3
          content_preview: contentStr.substring(0, 100),
        });
      }

      // Non-strict mode: log warning and continue
      console.warn(`WARNING: ${errorMsg}`);
    }

    // 2. Check content filter
    const [isValid, errorMsg] = this.contentFilter.validate(message.content);
    if (!isValid) {
      if (this.strict) {
        throw new ValidationError(`Content validation failed: ${errorMsg}`, {
          content_preview: contentStr.substring(0, 100),
        });
      }
      console.warn(`WARNING: Content validation failed: ${errorMsg}`);
    }

    // 3. Process with wrapped agent
    return await this.agent.process(message);
  }
}

/**
 * Create input validation middleware function.
 *
 * Example:
 *   const agent = applyMiddleware(baseAgent, [
 *     inputValidation({
 *       detector: new PromptInjectionDetector({ threshold: 15 }),
 *       contentFilter: new ContentFilter({ maxSize: 5000 }),
 *       strict: true,
 *     }),
 *   ]);
 */
export function inputValidation(config?: {
  detector?: PromptInjectionDetector;
  contentFilter?: ContentFilter;
  strict?: boolean;
}): (agent: Agent) => Agent {
  return (agent: Agent) =>
    new InputValidationMiddleware(
      agent,
      config?.detector,
      config?.contentFilter,
      config?.strict,
    );
}
