/**
 * Per-user rate limiting middleware with token bucket algorithm.
 *
 * Provides fine-grained rate limiting per user/client while also supporting
 * global rate limits to protect system resources.
 *
 * Features:
 * - Per-user rate limits (separate bucket per user)
 * - Optional global rate limits (protect system resources)
 * - Flexible user identification (user_id, api_key, ip_address)
 * - Automatic cleanup of inactive users
 */

import { Agent, Message } from '../core/interfaces';

/**
 * Configuration for per-user rate limiter.
 */
export interface PerUserRateLimiterConfig {
  /** Requests per second per user (default: 10) */
  userRate?: number;

  /** Burst capacity per user (default: 10) */
  userCapacity?: number;

  /** Total requests per second across all users (default: 100, set to undefined to disable) */
  globalRate?: number;

  /** Total burst capacity (default: 100, set to undefined to disable) */
  globalCapacity?: number;

  /** Function to extract user ID from message (optional) */
  identifierFn?: (message: Message) => string;

  /** Clean up inactive users every N milliseconds (default: 300000 = 5 minutes) */
  cleanupInterval?: number;

  /** Consider user inactive after N milliseconds (default: 600000 = 10 minutes) */
  inactiveThreshold?: number;
}

/**
 * Metrics for per-user rate limiter.
 */
export interface PerUserRateLimiterMetrics {
  totalRequests: number;
  allowedRequests: number;
  rejectedUserLimit: number;
  rejectedGlobalLimit: number;
  activeUsers: number;
  totalUsersSeen: number;
  totalWaitTime: number;
}

/**
 * Error thrown when per-user rate limit is exceeded.
 */
export class PerUserRateLimitError extends Error {
  constructor(public readonly userId: string, message: string) {
    super(message);
    this.name = 'PerUserRateLimitError';
  }
}

/**
 * Error thrown when global rate limit is exceeded.
 */
export class GlobalRateLimitError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'GlobalRateLimitError';
  }
}

/**
 * Token bucket for rate limiting.
 */
class TokenBucket {
  private tokens: number;
  private lastUpdate: number;

  constructor(private rate: number, private capacity: number) {
    this.tokens = capacity;
    this.lastUpdate = Date.now();
  }

  /**
   * Refill tokens based on elapsed time.
   */
  refill(): void {
    const now = Date.now();
    const elapsed = (now - this.lastUpdate) / 1000; // Convert to seconds

    // Add tokens based on elapsed time
    const tokensToAdd = elapsed * this.rate;
    this.tokens = Math.min(this.tokens + tokensToAdd, this.capacity);
    this.lastUpdate = now;
  }

  /**
   * Try to acquire tokens from bucket.
   *
   * @param tokensNeeded Number of tokens to acquire
   * @returns true if tokens were acquired, false otherwise
   */
  tryAcquire(tokensNeeded: number = 1): boolean {
    this.refill();
    if (this.tokens >= tokensNeeded) {
      this.tokens -= tokensNeeded;
      return true;
    }
    return false;
  }

  /**
   * Calculate time until tokens will be available.
   *
   * @param tokensNeeded Number of tokens needed
   * @returns Time in milliseconds until tokens will be available
   */
  timeUntilAvailable(tokensNeeded: number = 1): number {
    this.refill();
    if (this.tokens >= tokensNeeded) {
      return 0;
    }

    const tokensDeficit = tokensNeeded - this.tokens;
    return (tokensDeficit / this.rate) * 1000; // Convert to milliseconds
  }
}

/**
 * Agent decorator implementing per-user rate limiting.
 *
 * Example:
 *   const config: PerUserRateLimiterConfig = {
 *     userRate: 10.0,
 *     userCapacity: 20,
 *     globalRate: 100.0,
 *     globalCapacity: 200,
 *     identifierFn: (msg) => msg.metadata?.user_id || 'anonymous',
 *   };
 *   const limitedAgent = new PerUserRateLimiterDecorator(agent, config);
 *
 *   // Message with user ID
 *   const msg = { role: 'user', content: 'Hello', metadata: { user_id: 'alice' } };
 *   await limitedAgent.process(msg);
 */
export class PerUserRateLimiterDecorator implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private agent: Agent;
  private config: Required<Omit<PerUserRateLimiterConfig, 'globalRate' | 'globalCapacity'>> & {
    globalRate?: number;
    globalCapacity?: number;
  };
  private userBuckets = new Map<string, TokenBucket>();
  private userLastSeen = new Map<string, number>();
  private globalBucket: TokenBucket | null = null;
  private lock = Promise.resolve();
  private metricsData: PerUserRateLimiterMetrics;
  private cleanupTimer: NodeJS.Timeout | null = null;

  constructor(agent: Agent, config?: PerUserRateLimiterConfig) {
    this.agent = agent;
    this.name = agent.name;
    this.capabilities = agent.capabilities;

    // Apply defaults
    this.config = {
      userRate: config?.userRate ?? 10.0,
      userCapacity: config?.userCapacity ?? 10,
      globalRate: config?.globalRate,
      globalCapacity: config?.globalCapacity,
      identifierFn: config?.identifierFn ?? this.defaultIdentifier.bind(this),
      cleanupInterval: config?.cleanupInterval ?? 300000, // 5 minutes
      inactiveThreshold: config?.inactiveThreshold ?? 600000, // 10 minutes
    };

    // Validate configuration
    if (this.config.userRate <= 0) {
      throw new Error('userRate must be positive');
    }
    if (this.config.userCapacity < 1) {
      throw new Error('userCapacity must be at least 1');
    }
    if (this.config.globalRate !== undefined && this.config.globalRate <= 0) {
      throw new Error('globalRate must be positive or undefined');
    }
    if (this.config.globalCapacity !== undefined && this.config.globalCapacity < 1) {
      throw new Error('globalCapacity must be at least 1');
    }

    // Initialize global bucket if enabled
    if (this.config.globalRate !== undefined && this.config.globalCapacity !== undefined) {
      this.globalBucket = new TokenBucket(this.config.globalRate, this.config.globalCapacity);
    }

    // Initialize metrics
    this.metricsData = {
      totalRequests: 0,
      allowedRequests: 0,
      rejectedUserLimit: 0,
      rejectedGlobalLimit: 0,
      activeUsers: 0,
      totalUsersSeen: 0,
      totalWaitTime: 0,
    };

    // Start cleanup timer
    if (this.config.cleanupInterval > 0) {
      this.cleanupTimer = setInterval(() => {
        this.cleanupInactiveUsers();
      }, this.config.cleanupInterval);
    }
  }

  /**
   * Get rate limiter metrics.
   */
  get metrics(): PerUserRateLimiterMetrics {
    return { ...this.metricsData };
  }

  /**
   * Default identifier function that tries common fields.
   */
  private defaultIdentifier(message: Message): string {
    if (message.metadata) {
      // Try common identifier fields
      for (const field of ['user_id', 'api_key', 'client_id', 'ip_address']) {
        if (field in message.metadata) {
          return String(message.metadata[field]);
        }
      }
    }
    return 'anonymous';
  }

  /**
   * Get or create token bucket for user.
   */
  private getOrCreateUserBucket(userId: string): TokenBucket {
    if (!this.userBuckets.has(userId)) {
      this.userBuckets.set(
        userId,
        new TokenBucket(this.config.userRate, this.config.userCapacity),
      );
      this.metricsData.totalUsersSeen++;
    }

    this.userLastSeen.set(userId, Date.now());
    this.metricsData.activeUsers = this.userBuckets.size;

    return this.userBuckets.get(userId)!;
  }

  /**
   * Clean up inactive user buckets.
   */
  private cleanupInactiveUsers(): void {
    const now = Date.now();
    const inactiveUsers: string[] = [];

    for (const [userId, lastSeen] of this.userLastSeen.entries()) {
      if (now - lastSeen > this.config.inactiveThreshold) {
        inactiveUsers.push(userId);
      }
    }

    for (const userId of inactiveUsers) {
      this.userBuckets.delete(userId);
      this.userLastSeen.delete(userId);
    }

    if (inactiveUsers.length > 0) {
      this.metricsData.activeUsers = this.userBuckets.size;
    }
  }

  /**
   * Process message with per-user rate limiting.
   *
   * @param message Input message
   * @returns Response message from agent
   * @throws PerUserRateLimitError if per-user rate limit is exceeded
   * @throws GlobalRateLimitError if global rate limit is exceeded
   */
  async process(message: Message): Promise<Message> {
    this.metricsData.totalRequests++;

    // Extract user identifier
    const userId = this.config.identifierFn(message);

    // Check global limit first (if enabled)
    if (this.globalBucket) {
      await this.withLock(async () => {
        if (!this.globalBucket!.tryAcquire()) {
          this.metricsData.rejectedGlobalLimit++;
          throw new GlobalRateLimitError(
            `Global rate limit exceeded: ${this.config.globalRate} requests/sec`,
          );
        }
      });
    }

    // Check per-user limit
    await this.withLock(async () => {
      const userBucket = this.getOrCreateUserBucket(userId);

      if (!userBucket.tryAcquire()) {
        this.metricsData.rejectedUserLimit++;

        const waitTime = userBucket.timeUntilAvailable();
        throw new PerUserRateLimitError(
          userId,
          `Rate limit exceeded for user '${userId}': ` +
            `${this.config.userRate} requests/sec ` +
            `(retry after ${(waitTime / 1000).toFixed(2)}s)`,
        );
      }
    });

    // Rate limit passed - process request
    this.metricsData.allowedRequests++;
    return await this.agent.process(message);
  }

  /**
   * Cleanup on shutdown.
   */
  shutdown(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
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
