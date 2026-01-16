#pragma once

#ifdef AGENKIT_WITH_OBSERVABILITY

#include <string>
#include <map>
#include <vector>

namespace agenkit {
namespace observability {

/**
 * @brief Logging format type
 */
enum class LogFormat {
    JSON,       ///< JSON format for structured logging
    COMPACT,    ///< Compact single-line format
    PRETTY      ///< Pretty multi-line format for development
};

/**
 * @brief Logging level
 */
enum class LogLevel {
    TRACE,      ///< Trace level (most verbose)
    DEBUG,      ///< Debug level
    INFO,       ///< Info level
    WARN,       ///< Warning level
    ERROR,      ///< Error level
    CRITICAL    ///< Critical level (least verbose)
};

/**
 * @brief Configure structured logging with trace correlation
 *
 * This function sets up logging with the specified format and level.
 * When tracing is enabled, log entries automatically include trace context.
 *
 * @param format Logging format ("json", "compact", or "pretty")
 * @param level Logging level ("trace", "debug", "info", "warn", "error", "critical")
 * @throws std::runtime_error if configuration fails or already configured
 *
 * Example:
 * @code
 * // JSON logging for production
 * agenkit::observability::configure_logging("json", "info");
 *
 * // Pretty logging for development
 * agenkit::observability::configure_logging("pretty", "debug");
 * @endcode
 */
void configure_logging(const std::string& format, const std::string& level);

/**
 * @brief Log an agent event with context
 *
 * Logs an informational event with optional context key-value pairs.
 * If tracing is enabled, includes trace context in the log entry.
 *
 * @param event_type Type of event (e.g., "agent_start", "processing_complete")
 * @param message Human-readable message
 * @param context Optional context as key-value pairs
 *
 * Example:
 * @code
 * std::map<std::string, std::string> context;
 * context["agent"] = "my_agent";
 * context["session_id"] = "abc123";
 * log_agent_event("processing_start", "Started processing message", context);
 * @endcode
 */
void log_agent_event(
    const std::string& event_type,
    const std::string& message,
    const std::map<std::string, std::string>& context = {});

/**
 * @brief Log an agent error
 *
 * Logs an error event with error details.
 * If tracing is enabled, includes trace context in the log entry.
 *
 * @param event_type Type of error event (e.g., "processing_error", "timeout")
 * @param message Human-readable error message
 * @param error Error details or stack trace
 *
 * Example:
 * @code
 * log_agent_error("processing_error", "Failed to process message", error.what());
 * @endcode
 */
void log_agent_error(
    const std::string& event_type,
    const std::string& message,
    const std::string& error);

/**
 * @brief Log an agent warning
 *
 * Logs a warning event with optional context.
 * If tracing is enabled, includes trace context in the log entry.
 *
 * @param event_type Type of warning event (e.g., "retry_attempt", "rate_limit")
 * @param message Human-readable warning message
 * @param context Optional context as key-value pairs
 *
 * Example:
 * @code
 * std::map<std::string, std::string> context;
 * context["attempt"] = "2";
 * context["max_attempts"] = "3";
 * log_agent_warning("retry_attempt", "Retrying after failure", context);
 * @endcode
 */
void log_agent_warning(
    const std::string& event_type,
    const std::string& message,
    const std::map<std::string, std::string>& context = {});

/**
 * @brief Convert log format string to enum
 */
LogFormat parse_log_format(const std::string& format);

/**
 * @brief Convert log level string to enum
 */
LogLevel parse_log_level(const std::string& level);

} // namespace observability
} // namespace agenkit

#endif // AGENKIT_WITH_OBSERVABILITY
