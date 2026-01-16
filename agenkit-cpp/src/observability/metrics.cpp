/**
 * @file metrics.cpp
 * @brief Implementation of metrics collection with OpenTelemetry
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include "agenkit/observability/metrics.hpp"
#include <opentelemetry/sdk/metrics/meter_provider.h>
#include <opentelemetry/sdk/metrics/export/periodic_exporting_metric_reader.h>
#include <opentelemetry/exporters/prometheus/exporter.h>
#include <opentelemetry/exporters/otlp/otlp_http_metric_exporter.h>
#include <opentelemetry/metrics/provider.h>
#include <mutex>
#include <chrono>

namespace agenkit {
namespace observability {

namespace metrics = opentelemetry::metrics;
namespace metrics_sdk = opentelemetry::sdk::metrics;
namespace metrics_exporter = opentelemetry::exporter::metrics;
namespace otlp = opentelemetry::exporter::otlp;
namespace nostd = opentelemetry::nostd;

// Global state for metrics
static std::mutex g_metrics_mutex;
static bool g_metrics_initialized = false;
static std::shared_ptr<metrics::MeterProvider> g_meter_provider;

void init_metrics(const std::string& exporter_type, const std::string& endpoint) {
    std::lock_guard<std::mutex> lock(g_metrics_mutex);

    if (g_metrics_initialized) {
        throw std::runtime_error("Metrics already initialized");
    }

    std::shared_ptr<metrics_sdk::MeterProvider> provider;

    if (exporter_type == "prometheus") {
        #ifdef AGENKIT_WITH_PROMETHEUS
        // Prometheus exporter
        metrics_exporter::PrometheusExporterOptions options;
        if (!endpoint.empty()) {
            // Parse host:port from endpoint
            size_t colon_pos = endpoint.find(':');
            if (colon_pos != std::string::npos) {
                options.url = "0.0.0.0"; // Bind to all interfaces
                try {
                    options.port = static_cast<uint16_t>(std::stoi(endpoint.substr(colon_pos + 1)));
                } catch (...) {
                    options.port = 9464; // Default port
                }
            }
        } else {
            options.url = "0.0.0.0";
            options.port = 9464; // Default Prometheus port
        }

        auto exporter = std::unique_ptr<metrics_sdk::PushMetricExporter>(
            new metrics_exporter::PrometheusExporter(options)
        );

        provider = std::make_shared<metrics_sdk::MeterProvider>();
        // Note: Prometheus exporter is pull-based and doesn't need a reader
        #else
        throw std::runtime_error("Prometheus exporter not enabled. Rebuild with Prometheus support.");
        #endif

    } else if (exporter_type == "otlp") {
        // OTLP exporter
        otlp::OtlpHttpMetricExporterOptions options;
        if (!endpoint.empty()) {
            options.url = endpoint;
        } else {
            options.url = "http://localhost:4318/v1/metrics"; // Default OTLP HTTP endpoint
        }

        auto exporter = std::unique_ptr<metrics_sdk::PushMetricExporter>(
            new otlp::OtlpHttpMetricExporter(options)
        );

        // Create periodic reader with 10 second interval
        metrics_sdk::PeriodicExportingMetricReaderOptions reader_options;
        reader_options.export_interval_millis = std::chrono::milliseconds(10000);
        reader_options.export_timeout_millis = std::chrono::milliseconds(5000);

        auto reader = std::make_shared<metrics_sdk::PeriodicExportingMetricReader>(
            std::move(exporter),
            reader_options
        );

        provider = std::make_shared<metrics_sdk::MeterProvider>(
            std::move(reader)
        );

    } else {
        throw std::runtime_error("Unknown exporter type: " + exporter_type);
    }

    // Set as global provider
    metrics::Provider::SetMeterProvider(provider);

    g_meter_provider = provider;
    g_metrics_initialized = true;
}

nostd::shared_ptr<metrics::Meter> get_meter(const std::string& name) {
    std::lock_guard<std::mutex> lock(g_metrics_mutex);

    if (!g_metrics_initialized) {
        throw std::runtime_error("Metrics not initialized. Call init_metrics() first.");
    }

    return g_meter_provider->GetMeter(name);
}

//=============================================================================
// MetricsMiddleware Implementation
//=============================================================================

MetricsMiddleware::MetricsMiddleware(std::shared_ptr<Agent> agent)
    : agent_(agent)
    , meter_(get_meter("agenkit-cpp")) {

    if (!agent_) {
        throw std::invalid_argument("Agent cannot be null");
    }

    // Create counter for total requests
    requests_total_ = meter_->CreateUInt64Counter(
        "agent_requests_total",
        "Total number of agent requests",
        "requests"
    );

    // Create histogram for request duration
    request_duration_ = meter_->CreateDoubleHistogram(
        "agent_request_duration_seconds",
        "Agent request duration in seconds",
        "seconds"
    );
}

std::string MetricsMiddleware::name() const {
    return agent_->name();
}

std::future<Result<Message, AgentError>> MetricsMiddleware::process(Message message) {
    auto start = std::chrono::steady_clock::now();

    try {
        // Process message with inner agent
        auto future = agent_->process(std::move(message));
        auto result = future.get();

        // Calculate duration
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration<double>(end - start).count();

        // Record metrics
        std::string status = result.is_ok() ? "success" : "error";
        std::string agent_name = agent_->name();

        // Create attributes for metrics
        std::map<std::string, std::string> attributes;
        attributes["agent.name"] = agent_name;
        attributes["status"] = status;

        // Record counter
        requests_total_->Add(1, attributes);

        // Record histogram
        std::map<std::string, std::string> duration_attributes;
        duration_attributes["agent.name"] = agent_name;
        request_duration_->Record(duration, duration_attributes);

        return core::make_ready_future(std::move(result));

    } catch (const std::exception& e) {
        // Calculate duration even on exception
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration<double>(end - start).count();

        // Record error metrics
        std::map<std::string, std::string> attributes;
        attributes["agent.name"] = agent_->name();
        attributes["status"] = "error";

        requests_total_->Add(1, attributes);

        std::map<std::string, std::string> duration_attributes;
        duration_attributes["agent.name"] = agent_->name();
        request_duration_->Record(duration, duration_attributes);

        // Re-throw as AgentError
        auto error = AgentError(
            core::AgentErrorType::ProcessingError,
            std::string("Metrics middleware error: ") + e.what()
        );
        return core::make_ready_future(Result<Message, AgentError>::err(std::move(error)));
    }
}

} // namespace observability
} // namespace agenkit

#endif // AGENKIT_WITH_OBSERVABILITY
