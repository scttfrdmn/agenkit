/**
 * @file tracing.cpp
 * @brief Implementation of distributed tracing with OpenTelemetry
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include "agenkit/observability/tracing.hpp"
#include <opentelemetry/sdk/trace/tracer_provider.h>
#include <opentelemetry/sdk/trace/simple_processor.h>
#include <opentelemetry/sdk/trace/batch_span_processor.h>
#include <opentelemetry/exporters/ostream/span_exporter.h>
#include <opentelemetry/exporters/otlp/otlp_http_exporter.h>
#include <opentelemetry/trace/provider.h>
#include <opentelemetry/context/propagation/global_propagator.h>
#include <opentelemetry/context/propagation/text_map_propagator.h>
#include <opentelemetry/trace/propagation/http_trace_context.h>
#include <mutex>
#include <sstream>
#include <iomanip>

namespace agenkit {
namespace observability {

namespace trace = opentelemetry::trace;
namespace trace_sdk = opentelemetry::sdk::trace;
namespace trace_exporter = opentelemetry::exporter::trace;
namespace otlp = opentelemetry::exporter::otlp;
namespace nostd = opentelemetry::nostd;

// Global state for tracing
static std::mutex g_tracing_mutex;
static bool g_tracing_initialized = false;
static std::shared_ptr<trace::TracerProvider> g_tracer_provider;

/**
 * @brief Create OTLP HTTP exporter
 *
 * OtlpHttpExporterOptions' default constructor already resolves `url` from
 * OTEL_EXPORTER_OTLP_ENDPOINT / OTEL_EXPORTER_OTLP_TRACES_ENDPOINT (falling
 * back to the spec default http://localhost:4318/v1/traces if neither is
 * set) -- see otlp_environment.h. Only overwrite `url` when the caller
 * passed an explicit, non-empty endpoint: an explicit parameter must take
 * precedence over the environment, but overwriting it unconditionally with
 * a hardcoded default (as this used to do) would silently discard that
 * environment-variable resolution and reintroduce the #771 bug.
 */
static std::unique_ptr<trace_sdk::SpanExporter> create_otlp_exporter(
    const std::string& endpoint) {

    otlp::OtlpHttpExporterOptions options;
    if (!endpoint.empty()) {
        options.url = endpoint;
    }
    // else: leave options.url as resolved by the default constructor above,
    // which already consulted the environment.

    return std::make_unique<otlp::OtlpHttpExporter>(options);
}

/**
 * @brief Create console exporter (stdout)
 */
static std::unique_ptr<trace_sdk::SpanExporter> create_console_exporter() {
    return std::make_unique<trace_exporter::OStreamSpanExporter>();
}

void init_tracing(const std::string& exporter_type, const std::string& endpoint) {
    std::lock_guard<std::mutex> lock(g_tracing_mutex);

    if (g_tracing_initialized) {
        throw std::runtime_error("Tracing already initialized");
    }

    // Create exporter based on type
    std::unique_ptr<trace_sdk::SpanExporter> exporter;

    if (exporter_type == "otlp") {
        exporter = create_otlp_exporter(endpoint);
    } else if (exporter_type == "console") {
        exporter = create_console_exporter();
    } else if (exporter_type == "jaeger") {
        // Jaeger now uses OTLP - redirect to OTLP with Jaeger endpoint
        std::string jaeger_endpoint = endpoint.empty()
            ? "http://localhost:4318/v1/traces"
            : endpoint;
        exporter = create_otlp_exporter(jaeger_endpoint);
    } else if (exporter_type == "zipkin") {
        // Zipkin can also use OTLP
        std::string zipkin_endpoint = endpoint.empty()
            ? "http://localhost:9411/api/v2/spans"
            : endpoint;
        exporter = create_otlp_exporter(zipkin_endpoint);
    } else {
        throw std::runtime_error("Unknown exporter type: " + exporter_type);
    }

    // Create span processor with the exporter
    auto processor = std::make_unique<trace_sdk::BatchSpanProcessor>(std::move(exporter));

    // Create tracer provider
    auto provider = std::make_shared<trace_sdk::TracerProvider>(std::move(processor));

    // Set as global provider
    trace::Provider::SetTracerProvider(provider);

    // Set up W3C Trace Context propagator
    auto propagator = std::make_shared<trace::propagation::HttpTraceContext>();
    opentelemetry::context::propagation::GlobalTextMapPropagator::SetGlobalPropagator(
        nostd::shared_ptr<opentelemetry::context::propagation::TextMapPropagator>(propagator)
    );

    g_tracer_provider = provider;
    g_tracing_initialized = true;
}

std::shared_ptr<trace::Tracer> get_tracer(const std::string& name) {
    std::lock_guard<std::mutex> lock(g_tracing_mutex);

    if (!g_tracing_initialized) {
        throw std::runtime_error("Tracing not initialized. Call init_tracing() first.");
    }

    return g_tracer_provider->GetTracer(name);
}

/**
 * @brief Helper class for extracting trace context from message metadata
 */
class MetadataCarrier : public opentelemetry::context::propagation::TextMapCarrier {
public:
    explicit MetadataCarrier(const nlohmann::json& metadata)
        : metadata_(metadata) {}

    nostd::string_view Get(nostd::string_view key) const noexcept override {
        if (!metadata_.is_object()) {
            return "";
        }

        std::string key_str(key);
        if (metadata_.contains(key_str) && metadata_[key_str].is_string()) {
            // Store in temp_ to keep the string alive
            temp_ = metadata_[key_str].get<std::string>();
            return nostd::string_view(temp_);
        }
        return "";
    }

    void Set(nostd::string_view key, nostd::string_view value) noexcept override {
        // Not used for extraction
        (void)key;
        (void)value;
    }

private:
    const nlohmann::json& metadata_;
    mutable std::string temp_;  // Temporary storage for string_view
};

/**
 * @brief Helper class for injecting trace context into a Message
 */
class MessageInjector : public opentelemetry::context::propagation::TextMapCarrier {
public:
    explicit MessageInjector(Message& message)
        : message_(message) {}

    nostd::string_view Get(nostd::string_view key) const noexcept override {
        const auto& metadata = message_.metadata();
        if (!metadata.is_object()) {
            return "";
        }

        std::string key_str(key);
        if (metadata.contains(key_str) && metadata[key_str].is_string()) {
            temp_ = metadata[key_str].get<std::string>();
            return nostd::string_view(temp_);
        }
        return "";
    }

    void Set(nostd::string_view key, nostd::string_view value) noexcept override {
        message_.with_metadata(std::string(key), std::string(value));
    }

private:
    Message& message_;
    mutable std::string temp_;
};

opentelemetry::context::Context extract_trace_context(const Message& message) {
    auto propagator = opentelemetry::context::propagation::GlobalTextMapPropagator::GetGlobalPropagator();
    MetadataCarrier carrier(message.metadata());

    return propagator->Extract(carrier, opentelemetry::context::Context());
}

void inject_trace_context(Message& message, const opentelemetry::context::Context& context) {
    auto propagator = opentelemetry::context::propagation::GlobalTextMapPropagator::GetGlobalPropagator();
    MessageInjector injector(message);

    propagator->Inject(injector, context);
}

//=============================================================================
// ScopedSpan Implementation
//=============================================================================

ScopedSpan::ScopedSpan(
    std::shared_ptr<trace::Tracer> tracer,
    const std::string& name,
    const opentelemetry::context::Context& parent_context)
    : tracer_(tracer) {

    if (!tracer_) {
        throw std::invalid_argument("Tracer cannot be null");
    }

    trace::StartSpanOptions options;
    options.parent = trace::GetSpan(parent_context)->GetContext();

    span_ = tracer_->StartSpan(name, options);
}

ScopedSpan::~ScopedSpan() {
    if (span_) {
        span_->End();
    }
}

ScopedSpan::ScopedSpan(ScopedSpan&& other) noexcept
    : span_(std::move(other.span_))
    , tracer_(std::move(other.tracer_)) {
    other.span_ = nullptr;
}

ScopedSpan& ScopedSpan::operator=(ScopedSpan&& other) noexcept {
    if (this != &other) {
        if (span_) {
            span_->End();
        }
        span_ = std::move(other.span_);
        tracer_ = std::move(other.tracer_);
        other.span_ = nullptr;
    }
    return *this;
}

void ScopedSpan::set_attribute(const std::string& key, const std::string& value) {
    if (span_) {
        span_->SetAttribute(key, value);
    }
}

void ScopedSpan::set_attribute(const std::string& key, int64_t value) {
    if (span_) {
        span_->SetAttribute(key, value);
    }
}

void ScopedSpan::set_attribute(const std::string& key, double value) {
    if (span_) {
        span_->SetAttribute(key, value);
    }
}

void ScopedSpan::set_attribute(const std::string& key, bool value) {
    if (span_) {
        span_->SetAttribute(key, value);
    }
}

void ScopedSpan::set_status_ok() {
    if (span_) {
        span_->SetStatus(trace::StatusCode::kOk);
    }
}

void ScopedSpan::set_status_error(const std::string& description) {
    if (span_) {
        span_->SetStatus(trace::StatusCode::kError, description);
    }
}

nostd::shared_ptr<trace::Span> ScopedSpan::get_span() const {
    return span_;
}

trace::SpanContext ScopedSpan::get_context() const {
    if (span_) {
        return span_->GetContext();
    }
    return trace::SpanContext::GetInvalid();
}

//=============================================================================
// TracingMiddleware Implementation
//=============================================================================

TracingMiddleware::TracingMiddleware(
    std::shared_ptr<Agent> agent,
    const std::string& span_name)
    : agent_(agent)
    , span_name_(span_name)
    , tracer_(get_tracer("agenkit-cpp")) {

    if (!agent_) {
        throw std::invalid_argument("Agent cannot be null");
    }
}

std::string TracingMiddleware::name() const {
    return agent_->name();
}

std::future<Result<Message, AgentError>> TracingMiddleware::process(Message message) {
    try {
        // Extract parent context from message
        auto parent_context = extract_trace_context(message);

        // Create span
        ScopedSpan span(tracer_, span_name_, parent_context);
        span.set_attribute("agent.name", agent_->name());
        span.set_attribute("message.role", message.role());

        // Process message with inner agent
        auto future = agent_->process(std::move(message));
        auto result = future.get();

        // Record result in span
        if (result.is_ok()) {
            span.set_status_ok();

            // Inject trace context into response
            auto response = result.unwrap();
            auto span_context = span.get_context();

            if (span_context.IsValid()) {
                // Create context from span
                auto current_context = trace::SetSpan(parent_context, span.get_span());
                inject_trace_context(response, current_context);
            }

            return core::make_ready_future(Result<Message, AgentError>::ok(std::move(response)));
        } else {
            auto error = result.unwrap_err();
            span.set_status_error(error.message());

            return core::make_ready_future(Result<Message, AgentError>::err(std::move(error)));
        }

    } catch (const std::exception& e) {
        auto error = AgentError(
            core::AgentErrorType::ProcessingError,
            std::string("Tracing middleware error: ") + e.what()
        );
        return core::make_ready_future(Result<Message, AgentError>::err(std::move(error)));
    }
}

} // namespace observability
} // namespace agenkit

#endif // AGENKIT_WITH_OBSERVABILITY
