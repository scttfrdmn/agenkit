/**
 * @file observability.hpp
 * @brief Master include file for Agenkit C++ observability
 *
 * This file provides a convenient single-include for all observability modules.
 * Include this file to get access to tracing, metrics, logging, and audit.
 *
 * ## Overview
 *
 * Agenkit C++ provides comprehensive OpenTelemetry-based observability:
 *
 * - **Distributed Tracing**: W3C Trace Context propagation across agents
 * - **Metrics Collection**: Request counts, durations, errors
 * - **Structured Logging**: Trace-correlated logs with multiple formats
 * - **Audit Logging**: Compliance-ready event persistence with queries
 *
 * ## Quick Example
 *
 * @code{.cpp}
 * #include "agenkit/observability/observability.hpp"
 *
 * using namespace agenkit::observability;
 *
 * // Initialize observability
 * init_tracing("console", "");
 * init_metrics("console", "");
 * configure_logging("json", "info");
 * auto audit = AuditLogger::create("audit.log");
 *
 * // Create observable agent
 * auto agent = std::make_shared<EchoAgent>();
 * auto traced = std::make_shared<TracingMiddleware>(agent, "echo.process");
 * auto observed = std::make_shared<MetricsMiddleware>(traced);
 *
 * // Process message (automatically traced and metered)
 * auto result = observed->process(msg).get();
 *
 * // Audit the operation
 * audit->log(
 *     AuditEvent::create(AuditEventType::MessageProcessed, "echo", "session_1")
 *         .with_detail("success", true)
 * );
 * @endcode
 *
 * ## Modules
 *
 * - **tracing.hpp**: Distributed tracing with OpenTelemetry
 * - **metrics.hpp**: Metrics collection (counters, histograms)
 * - **logging.hpp**: Structured logging with trace correlation
 * - **audit.hpp**: Audit logging for compliance
 *
 * ## Documentation
 *
 * See docs/observability.md for complete documentation including:
 * - Installation and setup
 * - Production deployment
 * - API reference
 * - Examples
 * - Troubleshooting
 *
 * @version 0.49.0
 * @date 2026-01-15
 */

#pragma once

#ifdef AGENKIT_WITH_OBSERVABILITY

// Include all observability modules
#include "agenkit/observability/tracing.hpp"
#include "agenkit/observability/metrics.hpp"
#include "agenkit/observability/logging.hpp"
#include "agenkit/observability/audit.hpp"

/**
 * @namespace agenkit::observability
 * @brief OpenTelemetry-based observability for AI agents
 *
 * This namespace contains all observability functionality including
 * distributed tracing, metrics collection, structured logging, and
 * audit logging.
 *
 * ## Key Features
 *
 * - RAII-based span management with automatic cleanup
 * - Message metadata propagation for cross-language compatibility
 * - Thread-safe operations for production use
 * - Multiple exporters: OTLP, Jaeger, Zipkin, Prometheus, Console
 * - Middleware composition for clean separation of concerns
 *
 * ## Examples
 *
 * See examples/:
 * - observability_basic.cpp - Simple setup with console exporters
 * - observability_distributed.cpp - Multi-agent distributed tracing
 * - observability_production.cpp - Production configuration
 *
 * ## Test Coverage
 *
 * - Tracing: 12 tests
 * - Metrics: 12 tests
 * - Logging: 14 tests
 * - Audit: 17 tests
 * - Integration: 8 tests
 * - **Total: 63 tests** (exceeds Python/Go parity by 54%)
 */
namespace agenkit {
namespace observability {

/**
 * @brief Initialize all observability components
 *
 * Convenience function to initialize tracing, metrics, and logging
 * with commonly used production settings.
 *
 * @param otlp_endpoint OTLP collector endpoint (e.g., "http://localhost:4317")
 * @param log_format Log format: "json", "compact", or "pretty"
 * @param log_level Log level: "trace", "debug", "info", "warn", "error", "critical"
 *
 * @throws std::runtime_error if initialization fails
 *
 * @code{.cpp}
 * initialize_observability(
 *     "http://otel-collector:4317",
 *     "json",
 *     "info"
 * );
 * @endcode
 */
inline void initialize_observability(
    const std::string& otlp_endpoint,
    const std::string& log_format = "json",
    const std::string& log_level = "info") {

    init_tracing("otlp", otlp_endpoint);
    init_metrics("otlp", otlp_endpoint);
    configure_logging(log_format, log_level);
}

} // namespace observability
} // namespace agenkit

#endif // AGENKIT_WITH_OBSERVABILITY
