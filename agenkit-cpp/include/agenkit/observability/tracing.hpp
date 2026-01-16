#pragma once

#ifdef AGENKIT_WITH_OBSERVABILITY

#include <memory>
#include <string>
#include <unordered_map>
#include <future>
#include <nlohmann/json.hpp>
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"
#include <opentelemetry/trace/provider.h>
#include <opentelemetry/trace/tracer.h>
#include <opentelemetry/trace/span.h>

namespace agenkit {
namespace observability {

using core::Agent;
using core::Message;
using core::Result;
using core::AgentError;

/**
 * @brief Initialize the tracing subsystem with the specified exporter
 *
 * @param exporter_type Type of exporter ("otlp", "jaeger", "zipkin", "console")
 * @param endpoint Optional endpoint URL for the exporter
 * @throws std::runtime_error if initialization fails or already initialized
 *
 * Example:
 * @code
 * agenkit::observability::init_tracing("otlp", "http://localhost:4317");
 * @endcode
 */
void init_tracing(const std::string& exporter_type,
                 const std::string& endpoint = "");

/**
 * @brief Get the global tracer instance
 *
 * @param name Name of the tracer (default: "agenkit-cpp")
 * @return Shared pointer to tracer
 * @throws std::runtime_error if tracing not initialized
 */
std::shared_ptr<opentelemetry::trace::Tracer> get_tracer(
    const std::string& name = "agenkit-cpp");

/**
 * @brief Extract W3C Trace Context from message
 *
 * @param message Message containing "traceparent" and optional "tracestate" in metadata
 * @return OpenTelemetry context with extracted trace information
 */
opentelemetry::context::Context extract_trace_context(const Message& message);

/**
 * @brief Inject W3C Trace Context into message
 *
 * @param message Message to inject trace context into
 * @param context OpenTelemetry context containing trace information
 */
void inject_trace_context(Message& message, const opentelemetry::context::Context& context);

/**
 * @brief RAII wrapper for OpenTelemetry span lifecycle
 *
 * This class manages the lifetime of a span, ensuring it is ended
 * when it goes out of scope. It follows RAII principles for safe
 * resource management.
 *
 * Example:
 * @code
 * {
 *     ScopedSpan span(tracer, "operation_name");
 *     span.set_attribute("key", "value");
 *     // Span automatically ended when scope exits
 * }
 * @endcode
 */
class ScopedSpan {
public:
    /**
     * @brief Create a new scoped span
     *
     * @param tracer Tracer to create span from
     * @param name Name of the span
     * @param parent_context Optional parent context for span nesting
     */
    explicit ScopedSpan(
        std::shared_ptr<opentelemetry::trace::Tracer> tracer,
        const std::string& name,
        const opentelemetry::context::Context& parent_context =
            opentelemetry::context::Context());

    /**
     * @brief Destructor - automatically ends the span
     */
    ~ScopedSpan();

    // Disable copying
    ScopedSpan(const ScopedSpan&) = delete;
    ScopedSpan& operator=(const ScopedSpan&) = delete;

    // Enable moving
    ScopedSpan(ScopedSpan&&) noexcept;
    ScopedSpan& operator=(ScopedSpan&&) noexcept;

    /**
     * @brief Set a string attribute on the span
     */
    void set_attribute(const std::string& key, const std::string& value);

    /**
     * @brief Set an integer attribute on the span
     */
    void set_attribute(const std::string& key, int64_t value);

    /**
     * @brief Set a double attribute on the span
     */
    void set_attribute(const std::string& key, double value);

    /**
     * @brief Set a boolean attribute on the span
     */
    void set_attribute(const std::string& key, bool value);

    /**
     * @brief Set span status to OK
     */
    void set_status_ok();

    /**
     * @brief Set span status to Error with description
     */
    void set_status_error(const std::string& description);

    /**
     * @brief Get the underlying span
     */
    opentelemetry::nostd::shared_ptr<opentelemetry::trace::Span> get_span() const;

    /**
     * @brief Get the span context for propagation
     */
    opentelemetry::trace::SpanContext get_context() const;

private:
    opentelemetry::nostd::shared_ptr<opentelemetry::trace::Span> span_;
    std::shared_ptr<opentelemetry::trace::Tracer> tracer_;
};

/**
 * @brief Middleware that adds distributed tracing to agents
 *
 * This middleware wraps an agent and automatically creates spans
 * for each process() call, propagating trace context via message
 * metadata.
 *
 * Thread-safe: Yes (uses message metadata, not thread-local storage)
 *
 * Example:
 * @code
 * auto agent = std::make_shared<MyAgent>();
 * auto traced = std::make_shared<TracingMiddleware>(agent);
 * auto response = traced->process(message).get();
 * // Trace automatically recorded
 * @endcode
 */
class TracingMiddleware : public Agent {
public:
    /**
     * @brief Wrap an agent with tracing middleware
     *
     * @param agent The agent to wrap
     * @param span_name Optional custom span name (default: "agent.process")
     */
    explicit TracingMiddleware(
        std::shared_ptr<Agent> agent,
        const std::string& span_name = "agent.process");

    /**
     * @brief Process message with automatic tracing
     *
     * Creates a span, extracts parent context from message metadata,
     * processes the message, and injects trace context into the response.
     *
     * @param message Input message
     * @return Future with Result containing response message with trace context
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
    std::string span_name_;
    std::shared_ptr<opentelemetry::trace::Tracer> tracer_;
};

} // namespace observability
} // namespace agenkit

#endif // AGENKIT_WITH_OBSERVABILITY
