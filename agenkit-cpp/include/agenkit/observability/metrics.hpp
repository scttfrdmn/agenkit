#pragma once

#ifdef AGENKIT_WITH_OBSERVABILITY

#include <memory>
#include <string>
#include <future>
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"
#include <opentelemetry/metrics/provider.h>
#include <opentelemetry/metrics/meter.h>

namespace agenkit {
namespace observability {

using core::Agent;
using core::Message;
using core::Result;
using core::AgentError;

/**
 * @brief Initialize the metrics subsystem with the specified exporter
 *
 * @param exporter_type Type of exporter ("prometheus" or "otlp")
 * @param endpoint Optional endpoint for the exporter (for OTLP)
 * @throws std::runtime_error if initialization fails or already initialized
 *
 * Example:
 * @code
 * // Prometheus exporter (pull-based, serves metrics on port 9464)
 * agenkit::observability::init_metrics("prometheus", "0.0.0.0:9464");
 *
 * // OTLP exporter (push-based)
 * agenkit::observability::init_metrics("otlp", "http://localhost:4318/v1/metrics");
 * @endcode
 */
void init_metrics(const std::string& exporter_type,
                  const std::string& endpoint = "");

/**
 * @brief Get the global meter instance
 *
 * @param name Name of the meter (default: "agenkit-cpp")
 * @return Shared pointer to meter
 * @throws std::runtime_error if metrics not initialized
 */
opentelemetry::nostd::shared_ptr<opentelemetry::metrics::Meter> get_meter(
    const std::string& name = "agenkit-cpp");

/**
 * @brief Middleware that adds automatic metrics collection to agents
 *
 * This middleware wraps an agent and automatically records:
 * - Request count (counter with success/error status)
 * - Request duration (histogram in seconds)
 *
 * Metrics are recorded with labels:
 * - agent.name: Name of the wrapped agent
 * - status: "success" or "error"
 *
 * Thread-safe: Yes (OpenTelemetry SDK handles synchronization)
 *
 * Example:
 * @code
 * auto agent = std::make_shared<MyAgent>();
 * auto metrics_agent = std::make_shared<MetricsMiddleware>(agent);
 * auto response = metrics_agent->process(message).get();
 * // Metrics automatically recorded
 * @endcode
 */
class MetricsMiddleware : public Agent {
public:
    /**
     * @brief Wrap an agent with metrics middleware
     *
     * @param agent The agent to wrap
     * @throws std::invalid_argument if agent is null
     * @throws std::runtime_error if metrics not initialized
     */
    explicit MetricsMiddleware(std::shared_ptr<Agent> agent);

    /**
     * @brief Process message with automatic metrics recording
     *
     * Records:
     * - agent_requests_total counter (incremented on every call)
     * - agent_request_duration_seconds histogram
     *
     * @param message Input message
     * @return Future with Result containing response message
     */
    std::future<Result<Message, AgentError>> process(Message message) override;

    /**
     * @brief Get the name of the wrapped agent
     */
    std::string name() const override;

    /**
     * @brief Get the wrapped agent
     */
    std::shared_ptr<Agent> inner() const { return agent_; }

private:
    std::shared_ptr<Agent> agent_;
    opentelemetry::nostd::shared_ptr<opentelemetry::metrics::Meter> meter_;
    opentelemetry::nostd::shared_ptr<opentelemetry::metrics::Counter<uint64_t>> requests_total_;
    opentelemetry::nostd::shared_ptr<opentelemetry::metrics::Histogram<double>> request_duration_;
};

} // namespace observability
} // namespace agenkit

#endif // AGENKIT_WITH_OBSERVABILITY
