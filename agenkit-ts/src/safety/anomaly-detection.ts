/**
 * Anomaly detection for agent behavior monitoring.
 *
 * Detects:
 * - Unusual request patterns
 * - Rate anomalies
 * - Suspicious behavior
 * - Resource usage anomalies
 */

import { Agent, Message } from '../core/interfaces';

/**
 * Types of security events.
 */
export enum SecurityEvent {
  // Rate anomalies
  HIGH_REQUEST_RATE = 'high_request_rate',
  BURST_DETECTED = 'burst_detected',

  // Pattern anomalies
  REPEATED_FAILURES = 'repeated_failures',
  PERMISSION_DENIED_SPIKE = 'permission_denied_spike',
  VALIDATION_FAILURES = 'validation_failures',

  // Behavior anomalies
  UNUSUAL_INPUT_SIZE = 'unusual_input_size',
  UNUSUAL_OUTPUT_SIZE = 'unusual_output_size',
  UNUSUAL_PROCESSING_TIME = 'unusual_processing_time',

  // Content anomalies
  SUSPICIOUS_CONTENT_PATTERN = 'suspicious_content_pattern',
  REPETITIVE_CONTENT = 'repetitive_content',
}

/**
 * Detects anomalous agent behavior.
 *
 * Uses statistical methods and heuristics to identify:
 * - Rate-based anomalies
 * - Pattern-based anomalies
 * - Content-based anomalies
 *
 * Example:
 *   const detector = new AnomalyDetector({
 *     maxRequestsPerMinute: 60,
 *     maxBurstSize: 10,
 *   });
 *
 *   const rateAnomaly = detector.detectRateAnomaly('user_123');
 *   if (rateAnomaly) {
 *     console.log('Rate anomaly:', rateAnomaly);
 *   }
 */
export class AnomalyDetector {
  // Rate limiting thresholds
  private maxRequestsPerMinute: number;
  private maxBurstSize: number;

  // Size thresholds (standard deviations)
  private inputSizeThreshold: number;
  private outputSizeThreshold: number;

  // Processing time threshold (seconds)
  private processingTimeThreshold: number;

  // Failure rate threshold (percentage)
  private failureRateThreshold: number;

  // Tracking data structures
  private requestTimestamps: Map<string, number[]> = new Map();
  private failureCounts: Map<string, number> = new Map();
  private successCounts: Map<string, number> = new Map();

  // Statistics (rolling averages)
  private inputSizes: number[] = [];
  private outputSizes: number[] = [];
  private processingTimes: number[] = [];
  private maxStatsSize: number = 100;

  // Content tracking (for repetition detection)
  private recentContent: Map<string, number[]> = new Map();
  private maxContentHistory: number = 10;

  constructor(config?: {
    maxRequestsPerMinute?: number;
    maxBurstSize?: number;
    inputSizeThreshold?: number;
    outputSizeThreshold?: number;
    processingTimeThreshold?: number;
    failureRateThreshold?: number;
  }) {
    this.maxRequestsPerMinute = config?.maxRequestsPerMinute ?? 60;
    this.maxBurstSize = config?.maxBurstSize ?? 10;
    this.inputSizeThreshold = config?.inputSizeThreshold ?? 3.0; // 3 sigma
    this.outputSizeThreshold = config?.outputSizeThreshold ?? 3.0;
    this.processingTimeThreshold = config?.processingTimeThreshold ?? 30.0;
    this.failureRateThreshold = config?.failureRateThreshold ?? 0.5; // 50%
  }

  /**
   * Detect rate-based anomalies.
   */
  detectRateAnomaly(userId: string): [SecurityEvent, Record<string, unknown>] | null {
    const now = Date.now() / 1000; // seconds

    // Get or create user's timestamp list
    if (!this.requestTimestamps.has(userId)) {
      this.requestTimestamps.set(userId, []);
    }

    const timestamps = this.requestTimestamps.get(userId)!;

    // Record request
    timestamps.push(now);

    // Clean old timestamps (> 60 seconds)
    while (timestamps.length > 0 && now - timestamps[0] > 60) {
      timestamps.shift();
    }

    // Check request rate (per minute)
    const requestsPerMinute = timestamps.length;
    if (requestsPerMinute > this.maxRequestsPerMinute) {
      return [
        SecurityEvent.HIGH_REQUEST_RATE,
        {
          user_id: userId,
          requests_per_minute: requestsPerMinute,
          threshold: this.maxRequestsPerMinute,
        },
      ];
    }

    // Check burst rate (per second)
    const recent = timestamps.filter((ts) => now - ts < 1.0).length;
    if (recent > this.maxBurstSize) {
      return [
        SecurityEvent.BURST_DETECTED,
        {
          user_id: userId,
          burst_size: recent,
          threshold: this.maxBurstSize,
        },
      ];
    }

    return null;
  }

  /**
   * Detect failure rate anomalies.
   */
  detectFailureAnomaly(
    userId: string,
    isFailure: boolean,
  ): [SecurityEvent, Record<string, unknown>] | null {
    // Update counts
    if (isFailure) {
      this.failureCounts.set(userId, (this.failureCounts.get(userId) || 0) + 1);
    } else {
      this.successCounts.set(userId, (this.successCounts.get(userId) || 0) + 1);
    }

    // Calculate failure rate
    const failures = this.failureCounts.get(userId) || 0;
    const successes = this.successCounts.get(userId) || 0;
    const total = failures + successes;

    if (total >= 10) {
      // Need at least 10 requests for meaningful rate
      const failureRate = failures / total;

      if (failureRate > this.failureRateThreshold) {
        return [
          SecurityEvent.REPEATED_FAILURES,
          {
            user_id: userId,
            failure_rate: failureRate,
            failures,
            total,
          },
        ];
      }
    }

    return null;
  }

  /**
   * Detect unusual input/output sizes.
   */
  detectSizeAnomaly(
    inputSize: number,
    outputSize: number,
  ): [SecurityEvent, Record<string, unknown>] | null {
    // Track sizes
    this.inputSizes.push(inputSize);
    if (this.inputSizes.length > this.maxStatsSize) {
      this.inputSizes.shift();
    }

    this.outputSizes.push(outputSize);
    if (this.outputSizes.length > this.maxStatsSize) {
      this.outputSizes.shift();
    }

    // Need enough data points for statistics
    if (this.inputSizes.length < 20) {
      return null;
    }

    // Calculate mean and std dev
    const inputMean = this.mean(this.inputSizes);
    const inputStdev = this.stdev(this.inputSizes, inputMean);

    const outputMean = this.mean(this.outputSizes);
    const outputStdev = this.stdev(this.outputSizes, outputMean);

    // Check input size anomaly (> threshold std devs from mean)
    if (inputStdev > 0) {
      const inputZScore = Math.abs(inputSize - inputMean) / inputStdev;
      if (inputZScore > this.inputSizeThreshold) {
        return [
          SecurityEvent.UNUSUAL_INPUT_SIZE,
          {
            input_size: inputSize,
            mean: inputMean,
            stdev: inputStdev,
            z_score: inputZScore,
          },
        ];
      }
    }

    // Check output size anomaly
    if (outputStdev > 0) {
      const outputZScore = Math.abs(outputSize - outputMean) / outputStdev;
      if (outputZScore > this.outputSizeThreshold) {
        return [
          SecurityEvent.UNUSUAL_OUTPUT_SIZE,
          {
            output_size: outputSize,
            mean: outputMean,
            stdev: outputStdev,
            z_score: outputZScore,
          },
        ];
      }
    }

    return null;
  }

  /**
   * Detect content-based anomalies.
   */
  detectContentAnomaly(
    userId: string,
    content: string,
  ): [SecurityEvent, Record<string, unknown>] | null {
    // Track recent content (hash first 500 chars)
    const contentHash = this.simpleHash(content.substring(0, 500));

    if (!this.recentContent.has(userId)) {
      this.recentContent.set(userId, []);
    }

    const contentHashes = this.recentContent.get(userId)!;
    contentHashes.push(contentHash);

    if (contentHashes.length > this.maxContentHistory) {
      contentHashes.shift();
    }

    // Check for repetitive content (same content repeated)
    if (contentHashes.length >= 5) {
      const recent5 = contentHashes.slice(-5);
      const uniqueCount = new Set(recent5).size;

      if (uniqueCount === 1) {
        // All 5 are same
        return [
          SecurityEvent.REPETITIVE_CONTENT,
          {
            user_id: userId,
            repetitions: 5,
          },
        ];
      }
    }

    return null;
  }

  /**
   * Calculate mean of numbers.
   */
  private mean(values: number[]): number {
    return values.reduce((sum, val) => sum + val, 0) / values.length;
  }

  /**
   * Calculate standard deviation.
   */
  private stdev(values: number[], mean: number): number {
    const variance =
      values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    return Math.sqrt(variance);
  }

  /**
   * Simple hash function for content comparison.
   */
  private simpleHash(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash;
  }
}

/**
 * Middleware for anomaly detection.
 *
 * Monitors agent interactions and detects:
 * - Rate anomalies
 * - Failure patterns
 * - Size anomalies
 * - Content anomalies
 *
 * Example:
 *   const detector = new AnomalyDetector({
 *     maxRequestsPerMinute: 100,
 *     maxBurstSize: 20,
 *   });
 *
 *   const agent = new AnomalyDetectionMiddleware(
 *     baseAgent,
 *     detector,
 *     'user_123',
 *     (event, details) => {
 *       console.log('Anomaly:', event, details);
 *     },
 *   );
 */
export class AnomalyDetectionMiddleware implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private agent: Agent;
  private detector: AnomalyDetector;
  private userId: string;
  private onAnomaly: (event: SecurityEvent, details: Record<string, unknown>) => void;

  constructor(
    agent: Agent,
    detector?: AnomalyDetector,
    userId: string = 'default',
    onAnomaly?: (event: SecurityEvent, details: Record<string, unknown>) => void,
  ) {
    this.agent = agent;
    this.name = agent.name;
    this.capabilities = agent.capabilities;
    this.detector = detector || new AnomalyDetector();
    this.userId = userId;
    this.onAnomaly = onAnomaly || this.defaultAnomalyHandler;
  }

  /**
   * Default anomaly handler: log to console.
   */
  private defaultAnomalyHandler(event: SecurityEvent, details: Record<string, unknown>): void {
    console.log(`SECURITY ANOMALY DETECTED: ${event}`);
    console.log('Details:', details);
  }

  /**
   * Process message with anomaly detection.
   */
  async process(message: Message): Promise<Message> {
    const startTime = Date.now();

    // 1. Check rate anomaly
    const rateAnomaly = this.detector.detectRateAnomaly(this.userId);
    if (rateAnomaly) {
      this.onAnomaly(rateAnomaly[0], rateAnomaly[1]);
    }

    // 2. Check content anomaly
    const contentStr = message.content ? String(message.content) : '';
    const contentAnomaly = this.detector.detectContentAnomaly(this.userId, contentStr);
    if (contentAnomaly) {
      this.onAnomaly(contentAnomaly[0], contentAnomaly[1]);
    }

    // 3. Process with wrapped agent
    let isFailure = false;
    let response: Message | null = null;

    try {
      response = await this.agent.process(message);
      return response;
    } catch (error) {
      isFailure = true;
      throw error;
    } finally {
      // 4. Check failure anomaly
      const failureAnomaly = this.detector.detectFailureAnomaly(this.userId, isFailure);
      if (failureAnomaly) {
        this.onAnomaly(failureAnomaly[0], failureAnomaly[1]);
      }

      // 5. Check size and timing anomalies (if succeeded)
      if (response) {
        const processingTime = (Date.now() - startTime) / 1000;
        const inputSize = contentStr.length;
        const outputSize = response.content ? String(response.content).length : 0;

        const sizeAnomaly = this.detector.detectSizeAnomaly(inputSize, outputSize);
        if (sizeAnomaly) {
          this.onAnomaly(sizeAnomaly[0], sizeAnomaly[1]);
        }

        // Check processing time
        if (processingTime > this.detector['processingTimeThreshold']) {
          this.onAnomaly(SecurityEvent.UNUSUAL_PROCESSING_TIME, {
            user_id: this.userId,
            processing_time: processingTime,
            threshold: this.detector['processingTimeThreshold'],
          });
        }
      }
    }
  }
}

/**
 * Create anomaly detection middleware function.
 *
 * Example:
 *   const agent = applyMiddleware(baseAgent, [
 *     anomalyDetection({
 *       detector: new AnomalyDetector({ maxRequestsPerMinute: 100 }),
 *       userId: 'user_123',
 *       onAnomaly: (event, details) => alertSecurityTeam(event, details),
 *     }),
 *   ]);
 */
export function anomalyDetection(config?: {
  detector?: AnomalyDetector;
  userId?: string;
  onAnomaly?: (event: SecurityEvent, details: Record<string, unknown>) => void;
}): (agent: Agent) => Agent {
  return (agent: Agent) =>
    new AnomalyDetectionMiddleware(
      agent,
      config?.detector,
      config?.userId,
      config?.onAnomaly,
    );
}
