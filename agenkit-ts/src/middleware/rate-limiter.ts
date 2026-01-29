/**
 * Rate limiting middleware using token bucket algorithm.
 *
 * The token bucket algorithm allows for smooth rate limiting with burst capacity:
 * - Tokens are added to the bucket at a constant rate
 * - Each request consumes tokens from the bucket
 * - If insufficient tokens are available, the request waits or is rejected
 * - Burst capacity allows temporary spikes in traffic
 *
 * This is useful for:
 * - Protecting downstream services from overload
 * - Complying with API rate limits (e.g., OpenAI: 3500 RPM)
 * - Fair resource allocation across tenants
 * - Cost control
 */

import { Agent, Message } from '../core/interfaces';

/**
 * Configuration for rate limiter behavior.
 */
export interface RateLimiterConfig {
  /** Tokens per second (default: 10) */
  rate?: number;

  /** Maximum burst capacity (default: 10) */
  capacity?: number;

  /** Tokens consumed per request (default: 1) */
  tokensPerRequest?: number;

  /**
   * Maximum time in milliseconds to wait for tokens (default: 0, meaning wait indefinitely).
   * If set and wait time exceeds this value, immediately reject with RateLimitError.
   */
  maxWaitTimeoutMs?: number;

  /**
   * @deprecated Use maxWaitTimeoutMs instead. Will be removed in v0.51.0.
   */
  maxWaitTimeout?: number;
}

/**
 * Metrics for rate limiter.
 */
export interface RateLimiterMetrics {
  totalRequests: number;
  allowedRequests: number;
  rejectedRequests: number;
  totalWaitTime: number;
  currentTokens: number;
}

/**
 * Error thrown when rate limit is exceeded.
 */
export class RateLimitError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RateLimitError';
  }
}

/**
 * Internal configuration after applying defaults (non-deprecated fields only).
 */
interface InternalRateLimiterConfig {
  rate: number;
  capacity: number;
  tokensPerRequest: number;
  maxWaitTimeoutMs: number;
}

/**
 * Agent decorator that implements rate limiting using token bucket algorithm.
 *
 * Example:
 *   const config: RateLimiterConfig = { rate: 100, capacity: 200 };
 *   const rateLimitedAgent = new RateLimiterDecorator(agent, config);
 *
 *   // Requests will be rate limited
 *   await rateLimitedAgent.process(msg);
 *
 *   console.log('Tokens remaining:', rateLimitedAgent.metrics.currentTokens);
 */
export class RateLimiterDecorator implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private agent: Agent;
  private config: InternalRateLimiterConfig;
  private tokens: number;
  private lastUpdate: number;
  private lock = Promise.resolve();
  private metricsData: RateLimiterMetrics;

  constructor(agent: Agent, config?: RateLimiterConfig) {
    this.agent = agent;
    this.name = agent.name;
    this.capabilities = agent.capabilities;

    // Handle deprecated 'maxWaitTimeout' field
    let maxWaitTimeoutMs = config?.maxWaitTimeoutMs ?? 0;
    if (config?.maxWaitTimeout !== undefined && config?.maxWaitTimeoutMs === undefined) {
      console.warn(
        'RateLimiterConfig.maxWaitTimeout is deprecated. Use maxWaitTimeoutMs instead. ' +
          'The maxWaitTimeout field will be removed in v0.51.0.',
      );
      maxWaitTimeoutMs = config.maxWaitTimeout;
    }

    // Apply defaults
    this.config = {
      rate: config?.rate ?? 10.0,
      capacity: config?.capacity ?? 10,
      tokensPerRequest: config?.tokensPerRequest ?? 1,
      maxWaitTimeoutMs,
    };

    // Validate configuration
    if (this.config.rate <= 0) {
      throw new Error('rate must be positive');
    }
    if (this.config.capacity < 1) {
      throw new Error('capacity must be at least 1');
    }
    if (this.config.tokensPerRequest < 1) {
      throw new Error('tokensPerRequest must be at least 1');
    }
    if (this.config.tokensPerRequest > this.config.capacity) {
      throw new Error('tokensPerRequest cannot exceed capacity');
    }

    // Initialize state
    this.tokens = this.config.capacity; // Start with full capacity
    this.lastUpdate = Date.now();

    // Initialize metrics
    this.metricsData = {
      totalRequests: 0,
      allowedRequests: 0,
      rejectedRequests: 0,
      totalWaitTime: 0,
      currentTokens: this.tokens,
    };
  }

  /**
   * Get rate limiter metrics.
   */
  get metrics(): RateLimiterMetrics {
    return { ...this.metricsData };
  }

  /**
   * Refill tokens based on elapsed time.
   */
  private refillTokens(): void {
    const now = Date.now();
    const elapsed = (now - this.lastUpdate) / 1000; // Convert to seconds

    // Add tokens based on elapsed time
    const tokensToAdd = elapsed * this.config.rate;
    this.tokens = Math.min(this.tokens + tokensToAdd, this.config.capacity);
    this.lastUpdate = now;

    // Update metrics
    this.metricsData.currentTokens = this.tokens;
  }

  /**
   * Acquire tokens from the bucket.
   *
   * @param tokensNeeded Number of tokens to acquire
   * @param wait If true, wait for tokens; if false, reject immediately
   * @returns true if tokens were acquired, false otherwise
   * @throws RateLimitError if wait=false and insufficient tokens available
   */
  private async acquireTokens(tokensNeeded: number, wait: boolean = true): Promise<boolean> {
    return await this.withLock(async () => {
      this.refillTokens();

      if (this.tokens >= tokensNeeded) {
        // Sufficient tokens available
        this.tokens -= tokensNeeded;
        this.metricsData.currentTokens = this.tokens;
        return true;
      }

      if (!wait) {
        // Insufficient tokens and not waiting
        throw new RateLimitError(
          `Rate limit exceeded: need ${tokensNeeded} tokens, ` +
            `only ${this.tokens.toFixed(2)} available`,
        );
      }

      // Calculate wait time for tokens
      const tokensDeficit = tokensNeeded - this.tokens;
      const waitTime = (tokensDeficit / this.config.rate) * 1000; // Convert to milliseconds

      // Check if wait time exceeds max wait timeout
      if (this.config.maxWaitTimeoutMs > 0 && waitTime > this.config.maxWaitTimeoutMs) {
        throw new RateLimitError(
          `Rate limit exceeded: would need to wait ${waitTime.toFixed(0)}ms, ` +
            `but max wait timeout is ${this.config.maxWaitTimeoutMs}ms`,
        );
      }

      // Wait for tokens (outside the lock would be better, but keep simple for now)
      await new Promise((resolve) => setTimeout(resolve, waitTime));

      // Refill and try again
      this.refillTokens();

      if (this.tokens >= tokensNeeded) {
        this.tokens -= tokensNeeded;
        this.metricsData.currentTokens = this.tokens;
        this.metricsData.totalWaitTime += waitTime;
        return true;
      }

      // Should not happen, but handle defensively
      throw new RateLimitError(`Failed to acquire ${tokensNeeded} tokens after waiting`);
    });
  }

  /**
   * Process message with rate limiting.
   *
   * @param message Input message
   * @returns Response message from agent
   * @throws RateLimitError if rate limit is exceeded
   */
  async process(message: Message): Promise<Message> {
    this.metricsData.totalRequests++;

    // Acquire tokens
    try {
      await this.acquireTokens(this.config.tokensPerRequest, true);
      this.metricsData.allowedRequests++;
    } catch (error) {
      if (error instanceof RateLimitError) {
        this.metricsData.rejectedRequests++;
      }
      throw error;
    }

    // Process request
    return await this.agent.process(message);
  }

  /**
   * Execute a function with async lock.
   */
  private async withLock<T>(fn: () => Promise<T> | T): Promise<T> {
    // Wait for current lock
    await this.lock;

    // Create new lock promise
    let releaseLock: () => void;
    this.lock = new Promise((resolve) => {
      releaseLock = resolve;
    });

    try {
      return await fn();
    } finally {
      // Release lock
      releaseLock!();
    }
  }
}
