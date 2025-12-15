/**
 * OpenTelemetry observability for Agenkit.
 *
 * Provides distributed tracing, Prometheus metrics, and structured logging
 * with trace correlation for production-grade agent monitoring.
 *
 * @module observability
 */

// Tracing
export {
  TracingConfig,
  TraceContext,
  initTracing,
  shutdownTracing,
  getTracer,
  injectTraceContext,
  extractTraceContext,
  TracingMiddleware,
  createTracedAgent,
} from './tracing';

// Metrics
export {
  MetricsConfig,
  initMetrics,
  shutdownMetrics,
  getMetricsUrl,
  MetricsMiddleware,
  createMonitoredAgent,
} from './metrics';

// Logging
export {
  LogLevel,
  LoggingConfig,
  LogEntry,
  Logger,
  configureLogging,
  getLoggingConfig,
  getLoggerWithTrace,
} from './logging';
