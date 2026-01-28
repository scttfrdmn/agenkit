/**
 * Health checking for agents with Kubernetes-style probes:
 * - Liveness: Is the agent alive?
 * - Readiness: Is the agent ready to accept traffic?
 * - Startup: Has initialization completed?
 * - Prometheus metrics export
 */

import type { Agent, Message } from '../core';

/**
 * Health status values.
 */
export enum HealthStatus {
  HEALTHY = 'healthy',
  UNHEALTHY = 'unhealthy',
  DEGRADED = 'degraded',
  UNKNOWN = 'unknown',
}

/**
 * Types of health probes.
 */
export enum ProbeType {
  LIVENESS = 'liveness',
  READINESS = 'readiness',
  STARTUP = 'startup',
}

/**
 * Result of a health check.
 */
export interface HealthCheckResult {
  status: HealthStatus;
  probeType: ProbeType;
  message: string;
  timestamp: Date;
  durationMs: number;
  metadata?: Record<string, unknown>;
}

/**
 * Health check configuration.
 */
export interface HealthCheckConfig {
  // Liveness probe settings
  livenessEnabled: boolean;
  livenessInterval: number; // milliseconds
  livenessTimeout: number; // milliseconds
  livenessFailureThreshold: number;

  // Readiness probe settings
  readinessEnabled: boolean;
  readinessInterval: number; // milliseconds
  readinessTimeout: number; // milliseconds
  readinessFailureThreshold: number;

  // Startup probe settings
  startupEnabled: boolean;
  startupTimeout: number; // milliseconds
  startupFailureThreshold: number;

  // Custom health check function
  customCheck?: (agent: Agent) => boolean;
}

/**
 * Default health check configuration.
 */
export function defaultHealthCheckConfig(): HealthCheckConfig {
  return {
    livenessEnabled: true,
    livenessInterval: 10000,
    livenessTimeout: 5000,
    livenessFailureThreshold: 3,
    readinessEnabled: true,
    readinessInterval: 5000,
    readinessTimeout: 3000,
    readinessFailureThreshold: 2,
    startupEnabled: true,
    startupTimeout: 30000,
    startupFailureThreshold: 30,
  };
}

/**
 * Health check metrics.
 */
export interface HealthMetrics {
  totalChecks: Record<ProbeType, number>;
  successfulChecks: Record<ProbeType, number>;
  failedChecks: Record<ProbeType, number>;
  lastCheckTime: Record<ProbeType, Date>;
  lastCheckDuration: Record<ProbeType, number>;
  consecutiveFailures: Record<ProbeType, number>;
  uptimeStart: Date;
}

/**
 * Create new health metrics.
 */
function newHealthMetrics(): HealthMetrics {
  return {
    totalChecks: {} as Record<ProbeType, number>,
    successfulChecks: {} as Record<ProbeType, number>,
    failedChecks: {} as Record<ProbeType, number>,
    lastCheckTime: {} as Record<ProbeType, Date>,
    lastCheckDuration: {} as Record<ProbeType, number>,
    consecutiveFailures: {} as Record<ProbeType, number>,
    uptimeStart: new Date(),
  };
}

/**
 * Health checker monitors agent health.
 */
export class HealthChecker {
  private agent: Agent;
  private config: HealthCheckConfig;
  private metrics: HealthMetrics;
  private isAlive: boolean;
  private isReady: boolean;
  private startupComplete: boolean;
  private lastSuccessfulRequest: Date;
  private livenessInterval?: NodeJS.Timeout;
  private readinessInterval?: NodeJS.Timeout;
  private startupTimeout?: NodeJS.Timeout;

  constructor(agent: Agent, config?: HealthCheckConfig) {
    this.agent = agent;
    this.config = config || defaultHealthCheckConfig();
    this.metrics = newHealthMetrics();
    this.isAlive = true;
    this.isReady = false;
    this.startupComplete = false;
    this.lastSuccessfulRequest = new Date();
  }

  /**
   * Check if agent is healthy overall.
   */
  isHealthy(): boolean {
    return this.isAlive && this.isReady;
  }

  /**
   * Start background health check tasks.
   */
  async start(): Promise<void> {
    if (this.config.livenessEnabled) {
      this.livenessInterval = setInterval(() => {
        void this.livenessLoop();
      }, this.config.livenessInterval);
    }

    if (this.config.readinessEnabled) {
      this.readinessInterval = setInterval(() => {
        void this.readinessLoop();
      }, this.config.readinessInterval);
    }

    if (this.config.startupEnabled && !this.startupComplete) {
      void this.startupCheck();
    }
  }

  /**
   * Stop background health check tasks.
   */
  async stop(): Promise<void> {
    if (this.livenessInterval) {
      clearInterval(this.livenessInterval);
      this.livenessInterval = undefined;
    }

    if (this.readinessInterval) {
      clearInterval(this.readinessInterval);
      this.readinessInterval = undefined;
    }

    if (this.startupTimeout) {
      clearTimeout(this.startupTimeout);
      this.startupTimeout = undefined;
    }
  }

  /**
   * Perform a liveness check.
   */
  async checkLiveness(): Promise<HealthCheckResult> {
    const startTime = Date.now();
    const probeType = ProbeType.LIVENESS;

    this.trackCheckStarted(probeType);

    try {
      // Basic liveness: Can we call methods?
      this.agent.name();
      this.agent.capabilities();

      // Custom check if provided
      if (this.config.customCheck && !this.config.customCheck(this.agent)) {
        const duration = Date.now() - startTime;
        this.trackCheckFailure(probeType, duration);
        return {
          status: HealthStatus.UNHEALTHY,
          probeType,
          message: 'Custom health check failed',
          timestamp: new Date(),
          durationMs: duration,
        };
      }

      // Success
      const duration = Date.now() - startTime;
      this.trackCheckSuccess(probeType, duration);

      return {
        status: HealthStatus.HEALTHY,
        probeType,
        message: 'Agent process is alive',
        timestamp: new Date(),
        durationMs: duration,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      this.trackCheckFailure(probeType, duration);
      return {
        status: HealthStatus.UNHEALTHY,
        probeType,
        message: `Liveness check failed: ${error}`,
        timestamp: new Date(),
        durationMs: duration,
      };
    }
  }

  /**
   * Perform a readiness check.
   */
  async checkReadiness(): Promise<HealthCheckResult> {
    const startTime = Date.now();
    const probeType = ProbeType.READINESS;

    this.trackCheckStarted(probeType);

    // Check if startup completed
    if (this.config.startupEnabled && !this.startupComplete) {
      const duration = Date.now() - startTime;
      this.trackCheckFailure(probeType, duration);
      return {
        status: HealthStatus.UNHEALTHY,
        probeType,
        message: 'Startup not complete',
        timestamp: new Date(),
        durationMs: duration,
      };
    }

    try {
      // Test with a simple request
      const timeoutPromise = new Promise<Message>((_, reject) => {
        setTimeout(() => reject(new Error('Timeout')), this.config.readinessTimeout);
      });

      const testMsg: Message = {
        role: 'system',
        content: 'readiness_check',
      };

      const checkPromise = this.agent.process(testMsg);
      const response = await Promise.race([checkPromise, timeoutPromise]);
      const duration = Date.now() - startTime;

      if (!response || !response.content) {
        this.trackCheckFailure(probeType, duration);
        return {
          status: HealthStatus.UNHEALTHY,
          probeType,
          message: 'Readiness check failed: empty response',
          timestamp: new Date(),
          durationMs: duration,
        };
      }

      // Success
      this.trackCheckSuccess(probeType, duration);
      this.lastSuccessfulRequest = new Date();

      return {
        status: HealthStatus.HEALTHY,
        probeType,
        message: 'Agent is ready to handle requests',
        timestamp: new Date(),
        durationMs: duration,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      this.trackCheckFailure(probeType, duration);
      return {
        status: HealthStatus.UNHEALTHY,
        probeType,
        message: `Readiness check failed: ${error}`,
        timestamp: new Date(),
        durationMs: duration,
      };
    }
  }

  /**
   * Perform a startup check.
   */
  async checkStartup(): Promise<HealthCheckResult> {
    const startTime = Date.now();
    const probeType = ProbeType.STARTUP;

    this.trackCheckStarted(probeType);

    // Perform readiness check as startup test
    const readinessResult = await this.checkReadiness();

    if (readinessResult.status === HealthStatus.HEALTHY) {
      this.startupComplete = true;

      const duration = Date.now() - startTime;
      this.trackCheckSuccess(probeType, duration);

      return {
        status: HealthStatus.HEALTHY,
        probeType,
        message: 'Startup complete',
        timestamp: new Date(),
        durationMs: duration,
      };
    }

    const duration = Date.now() - startTime;
    this.trackCheckFailure(probeType, duration);

    return {
      status: HealthStatus.UNHEALTHY,
      probeType,
      message: 'Startup checks not passing yet',
      timestamp: new Date(),
      durationMs: duration,
    };
  }

  private async livenessLoop(): Promise<void> {
    const result = await this.checkLiveness();

    if (result.status === HealthStatus.UNHEALTHY) {
      const failures = this.metrics.consecutiveFailures[ProbeType.LIVENESS] || 0;
      if (failures >= this.config.livenessFailureThreshold) {
        this.isAlive = false;
      }
    } else {
      this.isAlive = true;
    }
  }

  private async readinessLoop(): Promise<void> {
    const result = await this.checkReadiness();

    if (result.status === HealthStatus.UNHEALTHY) {
      const failures = this.metrics.consecutiveFailures[ProbeType.READINESS] || 0;
      if (failures >= this.config.readinessFailureThreshold) {
        this.isReady = false;
      }
    } else {
      this.isReady = true;
    }
  }

  private async startupCheck(): Promise<void> {
    const startTime = Date.now();
    let attempts = 0;

    const checkInterval = setInterval(async () => {
      if (Date.now() - startTime > this.config.startupTimeout) {
        clearInterval(checkInterval);
        return;
      }

      attempts++;
      if (attempts > this.config.startupFailureThreshold) {
        clearInterval(checkInterval);
        return;
      }

      const result = await this.checkStartup();
      if (result.status === HealthStatus.HEALTHY) {
        clearInterval(checkInterval);
      }
    }, 10000); // Wait 10s between startup checks
  }

  private trackCheckStarted(probeType: ProbeType): void {
    this.metrics.totalChecks[probeType] = (this.metrics.totalChecks[probeType] || 0) + 1;
  }

  private trackCheckSuccess(probeType: ProbeType, durationMs: number): void {
    this.metrics.successfulChecks[probeType] =
      (this.metrics.successfulChecks[probeType] || 0) + 1;
    this.metrics.lastCheckTime[probeType] = new Date();
    this.metrics.lastCheckDuration[probeType] = durationMs;
    this.metrics.consecutiveFailures[probeType] = 0;
  }

  private trackCheckFailure(probeType: ProbeType, durationMs: number): void {
    this.metrics.failedChecks[probeType] = (this.metrics.failedChecks[probeType] || 0) + 1;
    this.metrics.lastCheckTime[probeType] = new Date();
    this.metrics.lastCheckDuration[probeType] = durationMs;
    this.metrics.consecutiveFailures[probeType] =
      (this.metrics.consecutiveFailures[probeType] || 0) + 1;
  }

  /**
   * Get uptime in seconds.
   */
  getUptime(): number {
    return (Date.now() - this.metrics.uptimeStart.getTime()) / 1000;
  }

  /**
   * Export metrics in Prometheus format.
   */
  exportPrometheusMetrics(): string {
    const lines: string[] = [];

    // Total checks
    lines.push('# HELP agenkit_health_checks_total Total number of health checks performed');
    lines.push('# TYPE agenkit_health_checks_total counter');
    for (const [probeType, count] of Object.entries(this.metrics.totalChecks)) {
      lines.push(`agenkit_health_checks_total{probe="${probeType}"} ${count}`);
    }

    // Failed checks
    lines.push('');
    lines.push('# HELP agenkit_health_check_failures_total Total number of failed health checks');
    lines.push('# TYPE agenkit_health_check_failures_total counter');
    for (const [probeType, count] of Object.entries(this.metrics.failedChecks)) {
      lines.push(`agenkit_health_check_failures_total{probe="${probeType}"} ${count}`);
    }

    // Duration
    lines.push('');
    lines.push('# HELP agenkit_health_check_duration_ms Duration of last health check in milliseconds');
    lines.push('# TYPE agenkit_health_check_duration_ms gauge');
    for (const [probeType, duration] of Object.entries(this.metrics.lastCheckDuration)) {
      lines.push(`agenkit_health_check_duration_ms{probe="${probeType}"} ${duration.toFixed(2)}`);
    }

    // Uptime
    lines.push('');
    lines.push('# HELP agenkit_agent_uptime_seconds Uptime in seconds');
    lines.push('# TYPE agenkit_agent_uptime_seconds gauge');
    lines.push(`agenkit_agent_uptime_seconds ${this.getUptime().toFixed(2)}`);

    // Health status
    lines.push('');
    lines.push('# HELP agenkit_agent_healthy Agent health status (1=healthy, 0=unhealthy)');
    lines.push('# TYPE agenkit_agent_healthy gauge');
    lines.push(`agenkit_agent_healthy ${this.isHealthy() ? 1 : 0}`);

    return lines.join('\n');
  }

  /**
   * Get current metrics.
   */
  getMetrics(): HealthMetrics {
    return this.metrics;
  }
}
