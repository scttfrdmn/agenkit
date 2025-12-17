"use strict";
/**
 * Prometheus metrics collection for Agenkit agents.
 *
 * Provides automatic metrics collection with:
 * - Request counters
 * - Error tracking
 * - Latency histograms
 * - Message size tracking
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.MetricsMiddleware = void 0;
exports.initMetrics = initMetrics;
exports.shutdownMetrics = shutdownMetrics;
exports.getMetricsUrl = getMetricsUrl;
exports.createMonitoredAgent = createMonitoredAgent;
const sdk_metrics_1 = require("@opentelemetry/sdk-metrics");
const exporter_prometheus_1 = require("@opentelemetry/exporter-prometheus");
const resources_1 = require("@opentelemetry/resources");
const semantic_conventions_1 = require("@opentelemetry/semantic-conventions");
const api_1 = require("@opentelemetry/api");
const base_1 = require("../middleware/base");
let meterProvider = null;
let prometheusExporter = null;
let metricsServer = null;
// Metric instruments
let requestCounter = null;
let errorCounter = null;
let latencyHistogram = null;
let messageSizeHistogram = null;
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
async function initMetrics(config) {
    // Create Prometheus exporter
    prometheusExporter = new exporter_prometheus_1.PrometheusExporter({
        port: config.port,
        host: config.host || '0.0.0.0',
    }, () => {
        console.log(`Prometheus metrics server started on port ${config.port}`);
        console.log(`Metrics available at http://localhost:${config.port}/metrics`);
    });
    // Create resource
    const resource = resources_1.Resource.default().merge(new resources_1.Resource({
        [semantic_conventions_1.ATTR_SERVICE_NAME]: config.serviceName,
    }));
    // Create meter provider
    meterProvider = new sdk_metrics_1.MeterProvider({
        resource,
        readers: [prometheusExporter], // Type mismatch between OpenTelemetry versions
    });
    // Register as global provider
    api_1.metrics.setGlobalMeterProvider(meterProvider);
    // Get meter
    const meter = api_1.metrics.getMeter('@agenkit/core', '0.2.0');
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
    metricsServer = prometheusExporter.getServer?.() || null;
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
async function shutdownMetrics() {
    if (meterProvider) {
        await meterProvider.shutdown();
        meterProvider = null;
    }
    if (prometheusExporter) {
        await prometheusExporter.shutdown();
        prometheusExporter = null;
    }
    if (metricsServer) {
        await new Promise((resolve) => {
            metricsServer.close(() => resolve());
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
function getMetricsUrl() {
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
class MetricsMiddleware extends base_1.BaseMiddleware {
    /**
     * Create a new metrics middleware.
     *
     * @param agent - Agent to wrap
     */
    constructor(agent) {
        super(agent);
    }
    /**
     * Process a message with metrics collection.
     *
     * @param message - Input message
     * @returns Output message
     */
    async process(message) {
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
        messageSizeHistogram.record(messageSize, baseLabels);
        try {
            // Process message
            const response = await this.agent.process(message);
            // Record successful request
            const latency = Date.now() - startTime;
            requestCounter.add(1, {
                ...baseLabels,
                status: 'success',
            });
            latencyHistogram.record(latency, {
                ...baseLabels,
                status: 'success',
            });
            return response;
        }
        catch (error) {
            // Record error
            const latency = Date.now() - startTime;
            const errorType = error instanceof Error ? error.constructor.name : 'Unknown';
            requestCounter.add(1, {
                ...baseLabels,
                status: 'error',
            });
            errorCounter.add(1, {
                ...baseLabels,
                'error.type': errorType,
            });
            latencyHistogram.record(latency, {
                ...baseLabels,
                status: 'error',
            });
            throw error;
        }
    }
}
exports.MetricsMiddleware = MetricsMiddleware;
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
function createMonitoredAgent(agent) {
    return new MetricsMiddleware(agent);
}
