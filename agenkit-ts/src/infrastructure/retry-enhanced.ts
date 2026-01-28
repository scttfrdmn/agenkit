/**
 * Enhanced retry logic with:
 * - Multiple jitter types (Full, Equal, Decorrelated)
 * - Per-error-type retry strategies
 * - Budget awareness (cost and count limits)
 * - Backpressure detection
 * - Detailed metrics
 */

import type { Agent, Message } from '../core';

/**
 * Jitter types for retry backoff.
 */
export enum JitterType {
  NONE = 'none',
  FULL = 'full',
  EQUAL = 'equal',
  DECORRELATED = 'decorrelated',
}

/**
 * Error classification for retry strategies.
 */
export enum ErrorClass {
  TRANSIENT = 'transient',
  RATE_LIMIT = 'rate_limit',
  TIMEOUT = 'timeout',
  SERVER_ERROR = 'server_error',
  CLIENT_ERROR = 'client_error',
  UNKNOWN = 'unknown',
}

/**
 * Retry strategy for specific error class.
 */
export interface ErrorStrategy {
  errorClass: ErrorClass;
  maxAttempts: number;
  initialBackoff: number; // milliseconds
  maxBackoff: number; // milliseconds
  backoffMultiplier: number;
  shouldRetry: boolean;
}

/**
 * Retry budget to limit costs.
 */
export interface RetryBudget {
  maxCost: number;
  currentCost: number;
  maxRetriesPerHour: number;
  retryCount: number;
  windowStart: Date;
}

/**
 * Enhanced retry configuration.
 */
export interface EnhancedRetryConfig {
  // Basic retry settings
  maxAttempts: number;
  initialBackoff: number; // milliseconds
  maxBackoff: number; // milliseconds
  backoffMultiplier: number;

  // Jitter settings
  jitterType: JitterType;
  jitterMinRatio: number; // For EqualJitter

  // Error-specific strategies
  errorStrategies: Record<ErrorClass, ErrorStrategy>;
  errorClassifier?: (error: Error) => ErrorClass;

  // Budget settings
  enableBudget: boolean;
  costTracker?: (message: Message) => number;
  maxCostPerHour: number;
  maxRetriesPerHour: number;

  // Backpressure detection
  enableBackpressure: boolean;
  backpressureThreshold: number;
  backpressureWindow: number;
}

/**
 * Default enhanced retry configuration with error strategies.
 */
export function defaultEnhancedRetryConfig(): EnhancedRetryConfig {
  return {
    maxAttempts: 3,
    initialBackoff: 1000,
    maxBackoff: 30000,
    backoffMultiplier: 2.0,
    jitterType: JitterType.FULL,
    jitterMinRatio: 0.5,
    enableBudget: false,
    maxCostPerHour: 100.0,
    maxRetriesPerHour: 1000,
    enableBackpressure: true,
    backpressureThreshold: 0.5,
    backpressureWindow: 100,
    errorStrategies: {
      [ErrorClass.TRANSIENT]: {
        errorClass: ErrorClass.TRANSIENT,
        maxAttempts: 5,
        initialBackoff: 100,
        maxBackoff: 5000,
        backoffMultiplier: 2.0,
        shouldRetry: true,
      },
      [ErrorClass.RATE_LIMIT]: {
        errorClass: ErrorClass.RATE_LIMIT,
        maxAttempts: 10,
        initialBackoff: 60000,
        maxBackoff: 300000,
        backoffMultiplier: 1.5,
        shouldRetry: true,
      },
      [ErrorClass.TIMEOUT]: {
        errorClass: ErrorClass.TIMEOUT,
        maxAttempts: 3,
        initialBackoff: 2000,
        maxBackoff: 30000,
        backoffMultiplier: 2.0,
        shouldRetry: true,
      },
      [ErrorClass.SERVER_ERROR]: {
        errorClass: ErrorClass.SERVER_ERROR,
        maxAttempts: 3,
        initialBackoff: 5000,
        maxBackoff: 60000,
        backoffMultiplier: 2.0,
        shouldRetry: true,
      },
      [ErrorClass.CLIENT_ERROR]: {
        errorClass: ErrorClass.CLIENT_ERROR,
        maxAttempts: 1,
        initialBackoff: 0,
        maxBackoff: 0,
        backoffMultiplier: 1.0,
        shouldRetry: false,
      },
      [ErrorClass.UNKNOWN]: {
        errorClass: ErrorClass.UNKNOWN,
        maxAttempts: 3,
        initialBackoff: 1000,
        maxBackoff: 30000,
        backoffMultiplier: 2.0,
        shouldRetry: true,
      },
    },
  };
}

/**
 * Enhanced retry metrics.
 */
export interface EnhancedRetryMetrics {
  totalAttempts: number;
  successfulFirstAttempt: number;
  successfulOnRetry: number;
  failedAfterRetries: number;
  totalRetries: number;
  totalJitterAdded: number; // seconds
  budgetExceededCount: number;
  backpressureDetected: number;
  errorClassCounts: Record<ErrorClass, number>;
  recentResults: boolean[];
}

/**
 * Enhanced retry decorator wraps an agent with enhanced retry logic.
 */
export class EnhancedRetryDecorator implements Agent {
  private agent: Agent;
  private config: EnhancedRetryConfig;
  private metrics: EnhancedRetryMetrics;
  private budget: RetryBudget;

  constructor(agent: Agent, config?: EnhancedRetryConfig) {
    this.agent = agent;
    this.config = config || defaultEnhancedRetryConfig();
    this.metrics = {
      totalAttempts: 0,
      successfulFirstAttempt: 0,
      successfulOnRetry: 0,
      failedAfterRetries: 0,
      totalRetries: 0,
      totalJitterAdded: 0,
      budgetExceededCount: 0,
      backpressureDetected: 0,
      errorClassCounts: {} as Record<ErrorClass, number>,
      recentResults: [],
    };
    this.budget = {
      maxCost: this.config.maxCostPerHour,
      currentCost: 0,
      maxRetriesPerHour: this.config.maxRetriesPerHour,
      retryCount: 0,
      windowStart: new Date(),
    };
  }

  name(): string {
    return this.agent.name();
  }

  capabilities(): string[] {
    return this.agent.capabilities();
  }

  private classifyError(error: Error): ErrorClass {
    if (this.config.errorClassifier) {
      return this.config.errorClassifier(error);
    }

    // Default classification
    const errStr = error.message.toLowerCase();

    if (errStr.includes('rate limit') || errStr.includes('429')) {
      return ErrorClass.RATE_LIMIT;
    } else if (errStr.includes('timeout') || errStr.includes('timed out')) {
      return ErrorClass.TIMEOUT;
    } else if (errStr.includes('500') || errStr.includes('502') || errStr.includes('503')) {
      return ErrorClass.SERVER_ERROR;
    } else if (
      errStr.includes('400') ||
      errStr.includes('401') ||
      errStr.includes('403') ||
      errStr.includes('404')
    ) {
      return ErrorClass.CLIENT_ERROR;
    }

    return ErrorClass.UNKNOWN;
  }

  private getStrategy(errorClass: ErrorClass): ErrorStrategy {
    return (
      this.config.errorStrategies[errorClass] || {
        errorClass,
        maxAttempts: this.config.maxAttempts,
        initialBackoff: this.config.initialBackoff,
        maxBackoff: this.config.maxBackoff,
        backoffMultiplier: this.config.backoffMultiplier,
        shouldRetry: true,
      }
    );
  }

  private calculateBackoff(baseBackoff: number, attempt: number): number {
    let jittered = baseBackoff;

    switch (this.config.jitterType) {
      case JitterType.NONE:
        break;

      case JitterType.FULL:
        jittered = Math.random() * baseBackoff;
        this.metrics.totalJitterAdded += (baseBackoff - jittered) / 1000;
        break;

      case JitterType.EQUAL: {
        const minBackoff = baseBackoff * this.config.jitterMinRatio;
        jittered = minBackoff + Math.random() * (baseBackoff - minBackoff);
        this.metrics.totalJitterAdded += (baseBackoff - jittered) / 1000;
        break;
      }

      case JitterType.DECORRELATED: {
        if (attempt === 1) {
          jittered = baseBackoff;
        } else {
          const previous = this.calculateBackoff(baseBackoff, attempt - 1);
          jittered = Math.random() * previous * 3 + baseBackoff;
          if (jittered > this.config.maxBackoff) {
            jittered = this.config.maxBackoff;
          }
        }
        break;
      }
    }

    return jittered;
  }

  private checkBudget(cost: number): boolean {
    if (!this.config.enableBudget) {
      return true;
    }

    // Reset window if hour has passed
    const hourInMs = 3600000;
    if (Date.now() - this.budget.windowStart.getTime() > hourInMs) {
      this.budget.currentCost = 0;
      this.budget.retryCount = 0;
      this.budget.windowStart = new Date();
    }

    // Check cost budget
    if (this.budget.currentCost + cost > this.budget.maxCost) {
      this.metrics.budgetExceededCount++;
      return false;
    }

    // Check retry count budget
    if (this.budget.retryCount >= this.budget.maxRetriesPerHour) {
      this.metrics.budgetExceededCount++;
      return false;
    }

    return true;
  }

  private checkBackpressure(): boolean {
    if (!this.config.enableBackpressure) {
      return false;
    }

    const recent = this.metrics.recentResults;
    if (recent.length < this.config.backpressureWindow) {
      return false;
    }

    // Calculate failure rate
    const failures = recent.filter((success) => !success).length;
    const failureRate = failures / recent.length;

    if (failureRate > this.config.backpressureThreshold) {
      this.metrics.backpressureDetected++;
      return true;
    }

    return false;
  }

  /**
   * Process a message with enhanced retry logic.
   */
  async process(message: Message): Promise<Message> {
    let lastError: Error | null = null;
    let errorClass: ErrorClass = ErrorClass.UNKNOWN;
    let strategy: ErrorStrategy = this.getStrategy(errorClass);

    for (let attempt = 1; attempt <= this.config.maxAttempts; attempt++) {
      this.metrics.totalAttempts++;

      // Check budget before attempt
      if (this.config.enableBudget && this.config.costTracker) {
        const estimatedCost = this.config.costTracker(message);
        if (!this.checkBudget(estimatedCost)) {
          throw new Error('Retry budget exceeded');
        }
      }

      // Check backpressure
      if (this.checkBackpressure()) {
        await new Promise((resolve) => setTimeout(resolve, 5000));
      }

      try {
        // Process message
        const response = await this.agent.process(message);

        // Success
        if (attempt === 1) {
          this.metrics.successfulFirstAttempt++;
        } else {
          this.metrics.successfulOnRetry++;
        }
        this.metrics.recentResults.push(true);
        if (this.metrics.recentResults.length > this.config.backpressureWindow) {
          this.metrics.recentResults.shift();
        }

        // Track cost
        if (this.config.enableBudget && this.config.costTracker) {
          const cost = this.config.costTracker(message);
          this.budget.currentCost += cost;
        }

        return response;
      } catch (error) {
        // Failure
        lastError = error as Error;

        // Track failure for backpressure
        this.metrics.recentResults.push(false);
        if (this.metrics.recentResults.length > this.config.backpressureWindow) {
          this.metrics.recentResults.shift();
        }

        // Classify error
        errorClass = this.classifyError(lastError);
        this.metrics.errorClassCounts[errorClass] =
          (this.metrics.errorClassCounts[errorClass] || 0) + 1;

        // Get strategy for error class
        strategy = this.getStrategy(errorClass);

        // Check if should retry
        if (!strategy.shouldRetry) {
          this.metrics.failedAfterRetries++;
          throw new Error(`Non-retryable error (${errorClass}): ${lastError.message}`);
        }

        // Check if exceeded max attempts for this error class
        if (attempt >= strategy.maxAttempts) {
          break;
        }

        // Track retry
        this.metrics.totalRetries++;
        this.budget.retryCount++;

        // Calculate backoff with jitter
        let baseBackoff = strategy.initialBackoff * Math.pow(strategy.backoffMultiplier, attempt - 1);
        if (baseBackoff > strategy.maxBackoff) {
          baseBackoff = strategy.maxBackoff;
        }
        const backoff = this.calculateBackoff(baseBackoff, attempt);

        // Sleep with backoff
        await new Promise((resolve) => setTimeout(resolve, backoff));
      }
    }

    // All attempts failed
    this.metrics.failedAfterRetries++;
    throw new Error(
      `Max retry attempts (${strategy.maxAttempts}) exceeded for ${errorClass}: ${lastError?.message}`
    );
  }

  /**
   * Get current metrics.
   */
  getMetrics(): EnhancedRetryMetrics {
    return this.metrics;
  }
}
