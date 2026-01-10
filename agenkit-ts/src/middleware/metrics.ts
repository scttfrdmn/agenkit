/**
 * Metrics collection middleware.
 *
 * Collects observability metrics for agent operations including:
 * - Request counts (total, success, error)
 * - Latency statistics (min, max, average)
 * - In-flight request tracking
 * - Error rates
 */

import { Agent, Message } from '../core/interfaces';

/**
 * Observability metrics for an agent.
 */
export interface Metrics {
  /** Total number of requests */
  totalRequests: number;

  /** Number of successful requests */
  successRequests: number;

  /** Number of failed requests */
  errorRequests: number;

  /** Total latency in milliseconds */
  totalLatency: number;

  /** Minimum latency in milliseconds */
  minLatency: number;

  /** Maximum latency in milliseconds */
  maxLatency: number;

  /** Current number of in-flight requests */
  inFlightRequests: number;
}

/**
 * Agent decorator that collects observability metrics.
 *
 * Example:
 *   const metricsAgent = new MetricsDecorator(agent);
 *
 *   await metricsAgent.process(msg1);
 *   await metricsAgent.process(msg2);
 *
 *   const metrics = metricsAgent.getMetrics();
 *   console.log('Average latency:', metrics.averageLatency, 'ms');
 *   console.log('Error rate:', metrics.errorRate);
 */
export class MetricsDecorator implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private agent: Agent;
  private metrics: Metrics;
  private lock = Promise.resolve(); // Simple async lock

  constructor(agent: Agent) {
    this.agent = agent;
    this.name = agent.name;
    this.capabilities = agent.capabilities;

    // Initialize metrics
    this.metrics = {
      totalRequests: 0,
      successRequests: 0,
      errorRequests: 0,
      totalLatency: 0,
      minLatency: 0,
      maxLatency: 0,
      inFlightRequests: 0,
    };
  }

  /**
   * Get current metrics with calculated values.
   */
  getMetrics(): Metrics & {
    averageLatency: number;
    errorRate: number;
  } {
    return {
      ...this.metrics,
      averageLatency:
        this.metrics.totalRequests === 0
          ? 0
          : this.metrics.totalLatency / this.metrics.totalRequests,
      errorRate:
        this.metrics.totalRequests === 0
          ? 0
          : this.metrics.errorRequests / this.metrics.totalRequests,
    };
  }

  /**
   * Get a snapshot of current metrics.
   */
  snapshot(): Metrics {
    return { ...this.metrics };
  }

  /**
   * Reset all metrics to zero.
   */
  async reset(): Promise<void> {
    await this.withLock(async () => {
      this.metrics = {
        totalRequests: 0,
        successRequests: 0,
        errorRequests: 0,
        totalLatency: 0,
        minLatency: 0,
        maxLatency: 0,
        inFlightRequests: 0,
      };
    });
  }

  /**
   * Process message with metrics collection.
   *
   * @param message Input message
   * @returns Response message from agent
   * @throws Error if the underlying agent raises an error
   */
  async process(message: Message): Promise<Message> {
    // Increment in-flight requests
    await this.withLock(async () => {
      this.metrics.inFlightRequests++;
    });

    const startTime = Date.now();
    let success = false;

    try {
      // Call underlying agent
      const response = await this.agent.process(message);
      success = true;

      // Calculate latency
      const latency = Date.now() - startTime;

      // Update success metrics
      await this.withLock(async () => {
        this.metrics.totalRequests++;
        this.metrics.successRequests++;
        this.metrics.totalLatency += latency;

        // Update min/max latency
        if (this.metrics.minLatency === 0 || latency < this.metrics.minLatency) {
          this.metrics.minLatency = latency;
        }
        this.metrics.maxLatency = Math.max(this.metrics.maxLatency, latency);
      });

      return response;
    } catch (error) {
      // Calculate latency even on error
      const latency = Date.now() - startTime;

      // Update error metrics
      await this.withLock(async () => {
        this.metrics.totalRequests++;
        this.metrics.errorRequests++;
        this.metrics.totalLatency += latency;

        // Update min/max latency
        if (this.metrics.minLatency === 0 || latency < this.metrics.minLatency) {
          this.metrics.minLatency = latency;
        }
        this.metrics.maxLatency = Math.max(this.metrics.maxLatency, latency);
      });

      throw error;
    } finally {
      // Decrement in-flight requests
      await this.withLock(async () => {
        this.metrics.inFlightRequests--;
      });
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
