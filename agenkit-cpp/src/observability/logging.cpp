/**
 * @file logging.cpp
 * @brief Implementation of structured logging with trace correlation
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include "agenkit/observability/logging.hpp"
#include "agenkit/observability/tracing.hpp"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <mutex>
#include <nlohmann/json.hpp>
#include <opentelemetry/trace/span.h>
#include <opentelemetry/trace/span_context.h>

namespace agenkit {
namespace observability {

namespace trace = opentelemetry::trace;

// Global logging state
static std::mutex g_logging_mutex;
static bool g_logging_configured = false;
static LogFormat g_log_format = LogFormat::COMPACT;
static LogLevel g_log_level = LogLevel::INFO;

// Helper to get current timestamp as ISO 8601 string
static std::string get_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;

    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S")
       << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';
    return ss.str();
}

// Helper to get current trace context if available
static std::string get_trace_id() {
    try {
        auto span = trace::GetSpan(opentelemetry::context::RuntimeContext::GetCurrent());
        if (span && span->GetContext().IsValid()) {
            std::stringstream ss;
            ss << span->GetContext().trace_id();
            return ss.str();
        }
    } catch (...) {
        // Tracing not available or not initialized
    }
    return "";
}

static std::string get_span_id() {
    try {
        auto span = trace::GetSpan(opentelemetry::context::RuntimeContext::GetCurrent());
        if (span && span->GetContext().IsValid()) {
            std::stringstream ss;
            ss << span->GetContext().span_id();
            return ss.str();
        }
    } catch (...) {
        // Tracing not available or not initialized
    }
    return "";
}

// Helper to convert level to string
static std::string level_to_string(LogLevel level) {
    switch (level) {
        case LogLevel::TRACE: return "TRACE";
        case LogLevel::DEBUG: return "DEBUG";
        case LogLevel::INFO: return "INFO";
        case LogLevel::WARN: return "WARN";
        case LogLevel::ERROR: return "ERROR";
        case LogLevel::CRITICAL: return "CRITICAL";
        default: return "UNKNOWN";
    }
}

// Helper to check if level should be logged
static bool should_log(LogLevel level) {
    return level >= g_log_level;
}

LogFormat parse_log_format(const std::string& format) {
    if (format == "json") return LogFormat::JSON;
    if (format == "compact") return LogFormat::COMPACT;
    if (format == "pretty") return LogFormat::PRETTY;
    throw std::invalid_argument("Unknown log format: " + format);
}

LogLevel parse_log_level(const std::string& level) {
    if (level == "trace") return LogLevel::TRACE;
    if (level == "debug") return LogLevel::DEBUG;
    if (level == "info") return LogLevel::INFO;
    if (level == "warn") return LogLevel::WARN;
    if (level == "error") return LogLevel::ERROR;
    if (level == "critical") return LogLevel::CRITICAL;
    throw std::invalid_argument("Unknown log level: " + level);
}

void configure_logging(const std::string& format, const std::string& level) {
    std::lock_guard<std::mutex> lock(g_logging_mutex);

    if (g_logging_configured) {
        throw std::runtime_error("Logging already configured");
    }

    g_log_format = parse_log_format(format);
    g_log_level = parse_log_level(level);
    g_logging_configured = true;
}

// Internal function to log with specified level
static void log_internal(
    LogLevel level,
    const std::string& event_type,
    const std::string& message,
    const std::map<std::string, std::string>& context) {

    std::lock_guard<std::mutex> lock(g_logging_mutex);

    if (!g_logging_configured) {
        // Auto-configure with defaults if not configured
        g_log_format = LogFormat::COMPACT;
        g_log_level = LogLevel::INFO;
        g_logging_configured = true;
    }

    if (!should_log(level)) {
        return;
    }

    std::string timestamp = get_timestamp();
    std::string trace_id = get_trace_id();
    std::string span_id = get_span_id();
    std::string level_str = level_to_string(level);

    if (g_log_format == LogFormat::JSON) {
        // JSON format
        nlohmann::json log_entry;
        log_entry["timestamp"] = timestamp;
        log_entry["level"] = level_str;
        log_entry["event_type"] = event_type;
        log_entry["message"] = message;

        if (!trace_id.empty()) {
            log_entry["trace_id"] = trace_id;
        }
        if (!span_id.empty()) {
            log_entry["span_id"] = span_id;
        }

        if (!context.empty()) {
            nlohmann::json context_obj = nlohmann::json::object();
            for (const auto& [key, value] : context) {
                context_obj[key] = value;
            }
            log_entry["context"] = context_obj;
        }

        std::cout << log_entry.dump() << std::endl;

    } else if (g_log_format == LogFormat::PRETTY) {
        // Pretty format (multi-line, indented)
        std::cout << "┌─ " << level_str << " [" << timestamp << "]" << std::endl;
        std::cout << "│  Event: " << event_type << std::endl;
        std::cout << "│  Message: " << message << std::endl;

        if (!trace_id.empty()) {
            std::cout << "│  Trace ID: " << trace_id << std::endl;
        }
        if (!span_id.empty()) {
            std::cout << "│  Span ID: " << span_id << std::endl;
        }

        if (!context.empty()) {
            std::cout << "│  Context:" << std::endl;
            for (const auto& [key, value] : context) {
                std::cout << "│    " << key << ": " << value << std::endl;
            }
        }
        std::cout << "└─" << std::endl;

    } else {
        // Compact format (single line)
        std::ostringstream oss;
        oss << timestamp << " [" << level_str << "] "
            << event_type << ": " << message;

        if (!trace_id.empty()) {
            oss << " trace_id=" << trace_id;
        }
        if (!span_id.empty()) {
            oss << " span_id=" << span_id;
        }

        if (!context.empty()) {
            for (const auto& [key, value] : context) {
                oss << " " << key << "=" << value;
            }
        }

        std::cout << oss.str() << std::endl;
    }
}

void log_agent_event(
    const std::string& event_type,
    const std::string& message,
    const std::map<std::string, std::string>& context) {

    log_internal(LogLevel::INFO, event_type, message, context);
}

void log_agent_error(
    const std::string& event_type,
    const std::string& message,
    const std::string& error) {

    std::map<std::string, std::string> context;
    context["error"] = error;
    log_internal(LogLevel::ERROR, event_type, message, context);
}

void log_agent_warning(
    const std::string& event_type,
    const std::string& message,
    const std::map<std::string, std::string>& context) {

    log_internal(LogLevel::WARN, event_type, message, context);
}

} // namespace observability
} // namespace agenkit

#endif // AGENKIT_WITH_OBSERVABILITY
