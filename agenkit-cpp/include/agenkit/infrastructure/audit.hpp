/**
 * Security audit logging for agent operations.
 *
 * Provides structured logging with:
 * - Event type classification
 * - Severity levels
 * - JSON formatting
 * - Log rotation support
 * - Searchable audit trail
 */

#pragma once

#include <chrono>
#include <fstream>
#include <memory>
#include <mutex>
#include <string>

#include "agenkit/infrastructure/anomaly.hpp"
#include <nlohmann/json.hpp>

namespace agenkit {
namespace infrastructure {

/**
 * Types of security audit events.
 */
enum class AuditEventType {
  ACCESS_GRANTED,
  ACCESS_DENIED,
  PERMISSION_GRANTED,
  PERMISSION_DENIED,
  INPUT_VALIDATION_FAILED,
  OUTPUT_VALIDATION_FAILED,
  PROMPT_INJECTION_DETECTED,
  SENSITIVE_DATA_DETECTED,
  ANOMALY_DETECTED,
  AGENT_STARTED,
  AGENT_COMPLETED,
  AGENT_FAILED
};

/**
 * Convert AuditEventType to string.
 */
std::string audit_event_type_to_string(AuditEventType type);

/**
 * Severity levels for audit events.
 */
enum class AuditSeverity { INFO, WARNING, ERROR, CRITICAL };

/**
 * Convert AuditSeverity to string.
 */
std::string audit_severity_to_string(AuditSeverity severity);

/**
 * Structured audit event.
 */
struct AuditEvent {
  AuditEventType event_type;
  AuditSeverity severity;
  std::string user_id;
  std::string agent_name;
  std::string message;
  std::string timestamp;  // ISO 8601
  nlohmann::json details;

  /**
   * Convert event to JSON.
   */
  nlohmann::json to_json() const;

  /**
   * Create event from JSON.
   */
  static AuditEvent from_json(const nlohmann::json& j);
};

/**
 * Security audit logger with structured logging and log rotation.
 *
 * Features:
 * - Structured JSON logging
 * - Log rotation based on file size
 * - Severity-based filtering
 * - Console and file output
 * - Searchable audit trail
 */
class SecurityAuditLogger {
 public:
  /**
   * Configuration for audit logger.
   */
  struct Config {
    std::string log_file = "security_audit.log";
    size_t max_bytes = 100 * 1024 * 1024;  // 100MB
    int backup_count = 10;
    AuditSeverity min_severity = AuditSeverity::INFO;
    bool also_log_to_console = true;
  };

  SecurityAuditLogger();
  explicit SecurityAuditLogger(const Config& config);
  ~SecurityAuditLogger();

  // Disable copy
  SecurityAuditLogger(const SecurityAuditLogger&) = delete;
  SecurityAuditLogger& operator=(const SecurityAuditLogger&) = delete;

  /**
   * Log audit event.
   */
  void log(const AuditEvent& event);

  /**
   * Log access attempt.
   */
  void log_access(bool granted, const std::string& user_id,
                  const std::string& agent_name, const std::string& action,
                  const nlohmann::json& details = nlohmann::json::object());

  /**
   * Log permission check.
   */
  void log_permission_check(
      bool granted, const std::string& user_id,
      const std::string& agent_name, const std::string& permission,
      const nlohmann::json& details = nlohmann::json::object());

  /**
   * Log validation failure.
   */
  void log_validation_failure(const std::string& user_id,
                               const std::string& validation_type,
                               const std::string& reason,
                               const std::string& content_preview = "",
                               const std::string& agent_name = "");

  /**
   * Log prompt injection detection.
   */
  void log_prompt_injection(
      const std::string& user_id, double score, const std::string& details,
      const std::string& agent_name = "");

  /**
   * Log sensitive data detection.
   */
  void log_sensitive_data(const std::string& user_id,
                          const std::string& data_type,
                          const nlohmann::json& details = nlohmann::json::object(),
                          const std::string& agent_name = "");

  /**
   * Log anomaly detection.
   */
  void log_anomaly(const std::string& user_id, SecurityEvent anomaly_type,
                   const nlohmann::json& details = nlohmann::json::object(),
                   const std::string& agent_name = "");

  /**
   * Log agent lifecycle event.
   */
  void log_agent_event(AuditEventType event_type, const std::string& user_id,
                       const std::string& agent_name,
                       const nlohmann::json& details = nlohmann::json::object());

 private:
  Config config_;
  std::ofstream log_stream_;
  size_t current_size_;
  std::mutex mutex_;

  bool should_log(AuditSeverity severity) const;
  void rotate_log();
  AuditEvent create_event(AuditEventType event_type, AuditSeverity severity,
                          const std::string& user_id,
                          const std::string& agent_name,
                          const std::string& message,
                          const nlohmann::json& details) const;
  std::string current_timestamp() const;
};

}  // namespace infrastructure
}  // namespace agenkit
