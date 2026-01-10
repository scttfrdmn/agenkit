/**
 * Batching middleware for combining multiple requests.
 *
 * This middleware collects multiple concurrent requests and processes them as a batch,
 * improving throughput at the cost of added latency.
 *
 * Use cases:
 * - LLM batch processing (reduce API costs via batch endpoints)
 * - Database bulk operations (reduce round trips)
 * - High-throughput data processing (maximize resource utilization)
 *
 * Trade-offs:
 * - Latency vs throughput: Adds wait time but improves throughput
 * - Memory usage: Buffers requests in queue
 * - Complexity: Handles partial failures and request/response mapping
 */

import { Agent, Message } from '../core/interfaces';

/**
 * Configuration for batching behavior.
 */
export interface BatchingConfig {
  /** Process when we have this many requests (default: 10) */
  maxBatchSize?: number;

  /** Process after this many milliseconds (default: 100) */
  maxWaitTime?: number;

  /** Backpressure limit (default: 1000) */
  maxQueueSize?: number;
}

/**
 * Metrics for batching middleware.
 */
export interface BatchingMetrics {
  totalRequests: number;
  totalBatches: number;
  successfulBatches: number;
  failedBatches: number;
  partialBatches: number;
  totalWaitTime: number;
  minBatchSize: number | null;
  maxBatchSize: number | null;
}

/**
 * Represents a single request in a batch.
 */
class BatchRequest {
  message: Message;
  resolve: (value: Message) => void;
  reject: (error: Error) => void;
  enqueuedAt: number;

  constructor(
    message: Message,
    resolve: (value: Message) => void,
    reject: (error: Error) => void,
  ) {
    this.message = message;
    this.resolve = resolve;
    this.reject = reject;
    this.enqueuedAt = Date.now();
  }
}

/**
 * Agent decorator that batches multiple concurrent requests.
 *
 * This middleware collects concurrent requests and processes them as a batch,
 * improving throughput by amortizing per-request overhead across multiple requests.
 *
 * The batch is processed when either:
 * 1. maxBatchSize requests have been collected, OR
 * 2. maxWaitTime has elapsed since the first request in the batch
 *
 * Each request receives its individual result, even if other requests in the
 * batch fail (partial failure support).
 *
 * Example:
 *   const config: BatchingConfig = { maxBatchSize: 5, maxWaitTime: 50 };
 *   const batchingAgent = new BatchingDecorator(agent, config);
 *
 *   // Concurrent requests will be automatically batched
 *   const results = await Promise.all([
 *     batchingAgent.process(msg1),
 *     batchingAgent.process(msg2),
 *     batchingAgent.process(msg3),
 *   ]);
 */
export class BatchingDecorator implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private agent: Agent;
  private config: Required<BatchingConfig>;
  private metricsData: BatchingMetrics;
  private queue: BatchRequest[] = [];
  private queueSize = 0;
  private batchTimeout: NodeJS.Timeout | null = null;
  private shutdown = false;

  constructor(agent: Agent, config?: BatchingConfig) {
    this.agent = agent;
    this.name = agent.name;
    this.capabilities = agent.capabilities;

    // Apply defaults
    this.config = {
      maxBatchSize: config?.maxBatchSize ?? 10,
      maxWaitTime: config?.maxWaitTime ?? 100,
      maxQueueSize: config?.maxQueueSize ?? 1000,
    };

    // Validate configuration
    if (this.config.maxBatchSize < 1) {
      throw new Error('maxBatchSize must be at least 1');
    }
    if (this.config.maxWaitTime <= 0) {
      throw new Error('maxWaitTime must be positive');
    }
    if (this.config.maxQueueSize < this.config.maxBatchSize) {
      throw new Error('maxQueueSize must be >= maxBatchSize');
    }

    // Initialize metrics
    this.metricsData = {
      totalRequests: 0,
      totalBatches: 0,
      successfulBatches: 0,
      failedBatches: 0,
      partialBatches: 0,
      totalWaitTime: 0,
      minBatchSize: null,
      maxBatchSize: null,
    };
  }

  /**
   * Get batching metrics.
   */
  get metrics(): BatchingMetrics & {
    avgBatchSize: number;
    avgWaitTime: number;
  } {
    return {
      ...this.metricsData,
      avgBatchSize:
        this.metricsData.totalBatches === 0
          ? 0
          : this.metricsData.totalRequests / this.metricsData.totalBatches,
      avgWaitTime:
        this.metricsData.totalRequests === 0
          ? 0
          : this.metricsData.totalWaitTime / this.metricsData.totalRequests,
    };
  }

  /**
   * Process message with batching.
   *
   * This method enqueues the message and waits for it to be processed as part
   * of a batch.
   *
   * @param message Input message
   * @returns Response message from agent
   * @throws Error if queue is at capacity (backpressure)
   */
  async process(message: Message): Promise<Message> {
    if (this.shutdown) {
      throw new Error('Batching middleware is shut down');
    }

    // Check queue capacity
    if (this.queueSize >= this.config.maxQueueSize) {
      throw new Error(
        `Queue at capacity (size: ${this.queueSize}, max: ${this.config.maxQueueSize})`,
      );
    }

    // Create batch request with promise
    return new Promise<Message>((resolve, reject) => {
      const request = new BatchRequest(message, resolve, reject);
      this.queue.push(request);
      this.queueSize++;

      // Check if we should process immediately
      if (this.queue.length >= this.config.maxBatchSize) {
        this.processImmediately();
      } else if (!this.batchTimeout) {
        // Start timeout for first request in batch
        this.batchTimeout = setTimeout(() => {
          this.processImmediately();
        }, this.config.maxWaitTime);
      }
    });
  }

  /**
   * Process the current batch immediately.
   */
  private processImmediately(): void {
    // Clear timeout if set
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }

    // Extract batch
    const batch = this.queue.splice(0, this.config.maxBatchSize);
    this.queueSize -= batch.length;

    if (batch.length > 0) {
      // Process asynchronously
      this.processBatch(batch).catch((error) => {
        console.error('Batch processing error:', error);
      });
    }
  }

  /**
   * Process a batch of requests.
   *
   * @param batch List of batch requests to process
   */
  private async processBatch(batch: BatchRequest[]): Promise<void> {
    if (batch.length === 0) return;

    const batchSize = batch.length;
    this.metricsData.totalBatches++;
    this.metricsData.totalRequests += batchSize;

    // Update batch size metrics
    if (this.metricsData.minBatchSize === null) {
      this.metricsData.minBatchSize = batchSize;
    } else {
      this.metricsData.minBatchSize = Math.min(
        this.metricsData.minBatchSize,
        batchSize,
      );
    }

    if (this.metricsData.maxBatchSize === null) {
      this.metricsData.maxBatchSize = batchSize;
    } else {
      this.metricsData.maxBatchSize = Math.max(
        this.metricsData.maxBatchSize,
        batchSize,
      );
    }

    // Calculate wait times
    const now = Date.now();
    for (const req of batch) {
      const waitTime = now - req.enqueuedAt;
      this.metricsData.totalWaitTime += waitTime;
    }

    // Process each request individually (parallel execution)
    // Note: For true batch processing (single API call for multiple requests),
    // the underlying agent would need to support batch operations.
    // This implementation processes requests in parallel.
    const results = await Promise.allSettled(
      batch.map((req) => this.agent.process(req.message)),
    );

    // Distribute results to individual promises
    let successes = 0;
    let failures = 0;

    for (let i = 0; i < batch.length; i++) {
      const req = batch[i];
      const result = results[i];

      if (result.status === 'fulfilled') {
        req.resolve(result.value);
        successes++;
      } else {
        req.reject(result.reason);
        failures++;
      }
    }

    // Update batch metrics
    if (failures === 0) {
      this.metricsData.successfulBatches++;
    } else if (successes === 0) {
      this.metricsData.failedBatches++;
    } else {
      this.metricsData.partialBatches++;
    }
  }

  /**
   * Flush any pending requests in the queue.
   *
   * This method processes any remaining requests in the queue immediately,
   * regardless of batch size thresholds. Useful for graceful shutdown.
   */
  async flush(): Promise<void> {
    while (this.queue.length > 0) {
      const batch = this.queue.splice(0, this.config.maxBatchSize);
      this.queueSize -= batch.length;
      await this.processBatch(batch);
    }
  }

  /**
   * Shutdown the batching middleware.
   *
   * This method:
   * 1. Stops accepting new requests
   * 2. Flushes pending requests
   * 3. Clears any pending timeout
   */
  async shutdownMiddleware(): Promise<void> {
    this.shutdown = true;

    // Clear timeout
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }

    // Flush any pending requests
    await this.flush();
  }
}
