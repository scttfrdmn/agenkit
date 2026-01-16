#pragma once

#ifdef AGENKIT_WITH_OBSERVABILITY

#include <string>
#include <map>
#include <vector>
#include <memory>
#include <functional>
#include <chrono>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace observability {

/**
 * @brief Audit event severity level
 */
enum class Severity {
    INFO,       ///< Informational event
    WARNING,    ///< Warning event
    ERROR,      ///< Error event
    CRITICAL    ///< Critical event requiring immediate attention
};

/**
 * @brief Audit event type
 */
enum class AuditEventType {
    AgentCreated,           ///< Agent was created
    AgentDestroyed,         ///< Agent was destroyed
    MessageProcessed,       ///< Message was successfully processed
    MessageFailed,          ///< Message processing failed
    SecurityViolation,      ///< Security policy violation detected
    ConfigurationChanged,   ///< Configuration was modified
    ErrorOccurred,          ///< Error occurred during operation
    UserAction,             ///< User-initiated action
    SystemEvent            ///< System-level event
};

/**
 * @brief Convert audit event type to string
 */
std::string audit_event_type_to_string(AuditEventType type);

/**
 * @brief Convert severity to string
 */
std::string severity_to_string(Severity severity);

/**
 * @brief Audit event for compliance and security logging
 *
 * Audit events are immutable records of important system events
 * that require permanent storage for compliance, security, or debugging.
 *
 * Example:
 * @code
 * auto event = AuditEvent::create(
 *     AuditEventType::MessageProcessed,
 *     "agent_name",
 *     "session_123"
 * );
 * event.with_detail("message_id", "msg_456");
 * event.with_severity(Severity::INFO);
 * @endcode
 */
class AuditEvent {
public:
    /**
     * @brief Create a new audit event
     *
     * @param event_type Type of event
     * @param agent_name Name of agent involved
     * @param session_id Optional session identifier
     * @return New audit event
     */
    static AuditEvent create(
        AuditEventType event_type,
        const std::string& agent_name,
        const std::string& session_id = "");

    /**
     * @brief Add a detail key-value pair
     *
     * @param key Detail key
     * @param value Detail value (JSON serializable)
     * @return Reference to this event for chaining
     */
    AuditEvent& with_detail(const std::string& key, const nlohmann::json& value);

    /**
     * @brief Set the severity level
     *
     * @param severity Event severity
     * @return Reference to this event for chaining
     */
    AuditEvent& with_severity(Severity severity);

    /**
     * @brief Get event ID
     */
    const std::string& event_id() const { return event_id_; }

    /**
     * @brief Get timestamp
     */
    std::chrono::system_clock::time_point timestamp() const { return timestamp_; }

    /**
     * @brief Get event type
     */
    AuditEventType event_type() const { return event_type_; }

    /**
     * @brief Get agent name
     */
    const std::string& agent_name() const { return agent_name_; }

    /**
     * @brief Get session ID
     */
    const std::string& session_id() const { return session_id_; }

    /**
     * @brief Get details
     */
    const nlohmann::json& details() const { return details_; }

    /**
     * @brief Get severity
     */
    Severity severity() const { return severity_; }

    /**
     * @brief Serialize to JSON
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize from JSON
     */
    static AuditEvent from_json(const nlohmann::json& j);

private:
    AuditEvent(
        AuditEventType event_type,
        const std::string& agent_name,
        const std::string& session_id);

    std::string event_id_;
    std::chrono::system_clock::time_point timestamp_;
    AuditEventType event_type_;
    std::string agent_name_;
    std::string session_id_;
    nlohmann::json details_;
    Severity severity_;
};

/**
 * @brief Audit logger with buffered persistence
 *
 * The audit logger provides buffered, thread-safe logging of audit events
 * to a file. Events are buffered in memory and flushed to disk periodically
 * or when the buffer reaches capacity.
 *
 * Thread-safe: Yes (all operations protected by mutex)
 *
 * Example:
 * @code
 * auto logger = AuditLogger::create("/var/log/audit.log");
 * logger->set_buffer_size(100);
 *
 * auto event = AuditEvent::create(
 *     AuditEventType::MessageProcessed,
 *     "my_agent",
 *     "session_123"
 * );
 * logger->log(event);
 *
 * // Explicit flush
 * logger->flush();
 *
 * // Query events
 * auto events = logger->query_by_session("session_123");
 * @endcode
 */
class AuditLogger {
public:
    /**
     * @brief Create an audit logger
     *
     * @param log_path Path to audit log file
     * @param buffer_size Optional buffer size (default: 100)
     * @return Shared pointer to audit logger
     * @throws std::runtime_error if file cannot be opened
     */
    static std::shared_ptr<AuditLogger> create(
        const std::string& log_path,
        size_t buffer_size = 100);

    /**
     * @brief Destructor - flushes any pending events
     */
    ~AuditLogger();

    /**
     * @brief Log an audit event
     *
     * The event is added to the buffer. If the buffer is full,
     * it is automatically flushed to disk.
     *
     * @param event Event to log
     */
    void log(const AuditEvent& event);

    /**
     * @brief Flush buffered events to disk
     *
     * This method blocks until all buffered events are written.
     */
    void flush();

    /**
     * @brief Set buffer size
     *
     * @param size New buffer size
     */
    void set_buffer_size(size_t size);

    /**
     * @brief Query all events
     *
     * @return Vector of all audit events
     */
    std::vector<AuditEvent> query();

    /**
     * @brief Query events by session ID
     *
     * @param session_id Session identifier
     * @return Vector of matching audit events
     */
    std::vector<AuditEvent> query_by_session(const std::string& session_id);

    /**
     * @brief Query events by agent name
     *
     * @param agent_name Agent name
     * @return Vector of matching audit events
     */
    std::vector<AuditEvent> query_by_agent(const std::string& agent_name);

    /**
     * @brief Query events by type
     *
     * @param event_type Event type
     * @return Vector of matching audit events
     */
    std::vector<AuditEvent> query_by_type(AuditEventType event_type);

    /**
     * @brief Query events with custom filter
     *
     * @param filter Predicate function to filter events
     * @return Vector of matching audit events
     */
    std::vector<AuditEvent> query_with_filter(
        std::function<bool(const AuditEvent&)> filter);

private:
    explicit AuditLogger(const std::string& log_path, size_t buffer_size);

    void flush_internal();
    std::vector<AuditEvent> load_events();

    std::string log_path_;
    size_t buffer_size_;
    std::vector<AuditEvent> buffer_;
    mutable std::mutex mutex_;
};

} // namespace observability
} // namespace agenkit

#endif // AGENKIT_WITH_OBSERVABILITY
