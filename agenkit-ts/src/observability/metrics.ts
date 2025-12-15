/**
 * Prometheus metrics collection for Agenkit agents.
 *
 * Provides automatic metrics collection with:
 * - Request counters
 * - Error tracking
 * - Latency histograms
 * - Message size tracking
 */

import {
  MeterProvider,
  PeriodicExportingMetricReader,
} from '@opentelemetry/sdk-metrics';
import { PrometheusExporter } from '@opentelemetry/exporter-prometheus';
import { Resource } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME } from '@opentelemetry/semantic-conventions';
import { metrics, Counter, Histogram } from '@opentelemetry/api';
import { Agent, Message } from '../core/interfaces';
import { BaseMiddleware } from '../middleware/base';
import * as http from 'http';

/**
 * Configuration for metrics initialization.
 */
export interface MetricsConfig {
  /** Service name for metrics */
  serviceName: string;
  /** Port for Prometheus scrape endpoint */
  port: number;
  /** Custom hostname (optional) */
  host?: string;
}

let meterProvider: MeterProvider | null = null;
let prometheusExporter: PrometheusExporter | null = null;
let metricsServer: http.Server | null = null;

// Metric instruments
let requestCounter: Counter | null = null;
let errorCounter: Counter | null = null;
let latencyHistogram: Histogram | null = null;
let messageSizeHistogram: Histogram | null = null;

/**
 * Initialize Prometheus metrics collection.
 *
 * Must be called once at application startup before creating monitored agents.
 * Starts an HTTP server on the specified port for Prometheus scraping.
 *
 * @param config - Metrics configuration
 * @returns MeterProvider instance
 *
 * @example
 * ```typescript
 * import { initMetrics } from '@agenkit/core/observability';
 *
 * // Initialize metrics on port 8003
 * await initMetrics({
 *   serviceName: 'my-agent-service',
 *   port: 8003
 * });
 *
 * // Metrics available at http://localhost:8003/metrics
 * ```
 */
export async function initMetrics(config: MetricsConfig): Promise<MeterProvider> {
  // Create Prometheus exporter
  prometheusExporter = new PrometheusExporter(
    {
      port: config.port,
      host: config.host || '0.0.0.0',
    },
    () => {
      console.log(`Prometheus metrics server started on port ${config.port}`);
      console.log(`Metrics available at http://localhost:${config.port}/metrics`);
    }
  );

  // Create resource
  const resource = Resource.default().merge(
    new Resource({
      [ATTR_SERVICE_NAME]: config.serviceName,
    })
  );

  // Create meter provider
  meterProvider = new MeterProvider({
    resource,
    readers: [prometheusExporter as any], // Type mismatch between OpenTelemetry versions
  });

  // Register as global provider
  metrics.setGlobalMeterProvider(meterProvider);

  // Get meter
  const meter = metrics.getMeter('@agenkit/core', '0.2.0');

  // Create metric instruments
  requestCounter = meter.createCounter('agenkit.agent.requests', {
    description: 'Total number of agent requests processed',
  });

  errorCounter = meter.createCounter('agenkit.agent.errors', {
    description: 'Total number of agent errors encountered',
  });

  latencyHistogram = meter.createHistogram('agenkit.agent.latency', {
    description: 'Agent processing latency in milliseconds',
    unit: 'ms',
  });

  messageSizeHistogram = meter.createHistogram('agenkit.agent.message_size', {
    description: 'Message content size in bytes',
    unit: 'bytes',
  });

  // Store metrics server reference (if available)
  metricsServer = (prometheusExporter as any).getServer?.() || null;

  return meterProvider;
}

/**
 * Shutdown metrics and close Prometheus endpoint.
 *
 * Should be called on application shutdown.
 *
 * @example
 * ```typescript
 * process.on('SIGTERM', async () => {
 *   await shutdownMetrics();
 *   process.exit(0);
 * });
 * ```
 */
export async function shutdownMetrics(): Promise<void> {
  if (meterProvider) {
    await meterProvider.shutdown();
    meterProvider = null;
  }

  if (prometheusExporter) {
    await prometheusExporter.shutdown();
    prometheusExporter = null;
  }

  if (metricsServer) {
    await new Promise<void>((resolve) => {
      metricsServer!.close(() => resolve());
    });
    metricsServer = null;
  }

  requestCounter = null;
  errorCounter = null;
  latencyHistogram = null;
  messageSizeHistogram = null;
}

/**
 * Get metrics endpoint URL.
 *
 * @returns Metrics URL or null if not initialized
 */
export function getMetricsUrl(): string | null {
  if (!metricsServer) {
    return null;
  }

  const address = metricsServer.address();
  if (!address || typeof address === 'string') {
    return null;
  }

  return `http://localhost:${address.port}/metrics`;
}

/**
 * Middleware that collects Prometheus metrics for agent processing.
 *
 * Automatically tracks:
 * - Request counts by agent, role, and status
 * - Error counts by agent and error type
 * - Processing latency distribution
 * - Message size distribution
 *
 * @example
 * ```typescript
 * import { MetricsMiddleware } from '@agenkit/core/observability';
 *
 * const agent = new MyAgent();
 * const monitoredAgent = new MetricsMiddleware(agent);
 *
 * // Process messages - metrics collected automatically
 * const response = await monitoredAgent.process(message);
 * ```
 */
export class MetricsMiddleware extends BaseMiddleware {
  /**
   * Create a new metrics middleware.
   *
   * @param agent - Agent to wrap
   */
  constructor(agent: Agent) {
    super(agent);
  }

  /**
   * Process a message with metrics collection.
   *
   * @param message - Input message
   * @returns Output message
   */
  async process(message: Message): Promise<Message> {
    if (!requestCounter || !errorCounter || !latencyHistogram || !messageSizeHistogram) {
      // Metrics not initialized, pass through
      return this.agent.process(message);
    }

    const startTime = Date.now();

    // Common labels
    const baseLabels = {
      'agent.name': this.agent.name,
      'message.role': message.role,
    };

    // Track message size
    const messageContent = String(message.content || '');
    const messageSize = new TextEncoder().encode(messageContent).length;
    messageSizeHistogram.record(messageSize, baseLabels as Record<string, string>);

    try {
      // Process message
      const response = await this.agent.process(message);

      // Record successful request
      const latency = Date.now() - startTime;
      requestCounter.add(1, {
        ...(baseLabels as Record<string, string>),
        status: 'success',
      });

      latencyHistogram.record(latency, {
        ...(baseLabels as Record<string, string>),
        status: 'success',
      });

      return response;
    } catch (error) {
      // Record error
      const latency = Date.now() - startTime;
      const errorType = error instanceof Error ? error.constructor.name : 'Unknown';

      requestCounter.add(1, {
        ...(baseLabels as Record<string, string>),
        status: 'error',
      });

      errorCounter.add(1, {
        ...(baseLabels as Record<string, string>),
        'error.type': errorType,
      });

      latencyHistogram.record(latency, {
        ...(baseLabels as Record<string, string>),
        status: 'error',
      });

      throw error;
    }
  }
}

/**
 * Create a monitored agent by wrapping with MetricsMiddleware.
 *
 * Convenience function for wrapping agents with metrics.
 *
 * @param agent - Agent to wrap
 * @returns Monitored agent
 *
 * @example
 * ```typescript
 * import { createMonitoredAgent } from '@agenkit/core/observability';
 *
 * const agent = new MyAgent();
 * const monitoredAgent = createMonitoredAgent(agent);
 * ```
 */
export function createMonitoredAgent(agent: Agent): Agent {
  return new MetricsMiddleware(agent);
}
