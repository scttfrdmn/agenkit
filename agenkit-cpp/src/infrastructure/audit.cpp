/**
 * Implementation of security audit logging for agent operations.
 */

#include "agenkit/infrastructure/audit.hpp"

#include <ctime>
#include <iomanip>
#include <iostream>
#include <sstream>

namespace agenkit {
namespace infrastructure {

// ============================================================================
// AuditEventType
// ============================================================================

std::string audit_event_type_to_string(AuditEventType type) {
  switch (type) {
    case AuditEventType::ACCESS_GRANTED:
      return "access_granted";
    case AuditEventType::ACCESS_DENIED:
      return "access_denied";
    case AuditEventType::PERMISSION_GRANTED:
      return "permission_granted";
    case AuditEventType::PERMISSION_DENIED:
      return "permission_denied";
    case AuditEventType::INPUT_VALIDATION_FAILED:
      return "input_validation_failed";
    case AuditEventType::OUTPUT_VALIDATION_FAILED:
      return "output_validation_failed";
    case AuditEventType::PROMPT_INJECTION_DETECTED:
      return "prompt_injection_detected";
    case AuditEventType::SENSITIVE_DATA_DETECTED:
      return "sensitive_data_detected";
    case AuditEventType::ANOMALY_DETECTED:
      return "anomaly_detected";
    case AuditEventType::AGENT_STARTED:
      return "agent_started";
    case AuditEventType::AGENT_COMPLETED:
      return "agent_completed";
    case AuditEventType::AGENT_FAILED:
      return "agent_failed";
    default:
      return "unknown";
  }
}

// ============================================================================
// AuditSeverity
// ============================================================================

std::string audit_severity_to_string(AuditSeverity severity) {
  switch (severity) {
    case AuditSeverity::INFO:
      return "INFO";
    case AuditSeverity::WARNING:
      return "WARNING";
    case AuditSeverity::ERROR:
      return "ERROR";
    case AuditSeverity::CRITICAL:
      return "CRITICAL";
    default:
      return "UNKNOWN";
  }
}

// ============================================================================
// AuditEvent
// ============================================================================

nlohmann::json AuditEvent::to_json() const {
  nlohmann::json j;
  j["event_type"] = audit_event_type_to_string(event_type);
  j["severity"] = audit_severity_to_string(severity);
  j["user_id"] = user_id;
  j["agent_name"] = agent_name;
  j["message"] = message;
  j["timestamp"] = timestamp;
  j["details"] = details;
  return j;
}

AuditEvent AuditEvent::from_json(const nlohmann::json& j) {
  AuditEvent event;
  // Note: Converting strings back to enums would require reverse mapping
  // For simplicity, this is a placeholder
  event.user_id = j["user_id"];
  event.agent_name = j["agent_name"];
  event.message = j["message"];
  event.timestamp = j["timestamp"];
  event.details = j["details"];
  return event;
}

// ============================================================================
// SecurityAuditLogger
// ============================================================================

SecurityAuditLogger::SecurityAuditLogger()
    : SecurityAuditLogger(Config{}) {}

SecurityAuditLogger::SecurityAuditLogger(const Config& config)
    : config_(config), current_size_(0) {
  // Create log file if it doesn't exist and get current size
  log_stream_.open(config_.log_file, std::ios::app);
  if (!log_stream_.is_open()) {
    std::cerr << "Failed to open audit log file: " << config_.log_file
              << std::endl;
    return;
  }

  // Get current file size
  log_stream_.seekp(0, std::ios::end);
  current_size_ = log_stream_.tellp();
}

SecurityAuditLogger::~SecurityAuditLogger() {
  if (log_stream_.is_open()) {
    log_stream_.close();
  }
}

bool SecurityAuditLogger::should_log(AuditSeverity severity) const {
  auto severity_order = [](AuditSeverity s) -> int {
    switch (s) {
      case AuditSeverity::INFO:
        return 0;
      case AuditSeverity::WARNING:
        return 1;
      case AuditSeverity::ERROR:
        return 2;
      case AuditSeverity::CRITICAL:
        return 3;
      default:
        return 0;
    }
  };

  return severity_order(severity) >= severity_order(config_.min_severity);
}

void SecurityAuditLogger::rotate_log() {
  // Called from log() which already holds mutex_; do not re-lock here.

  // Close current stream
  if (log_stream_.is_open()) {
    log_stream_.close();
  }

  // Rotate backup files
  for (int i = config_.backup_count - 1; i >= 1; i--) {
    std::string old_path = config_.log_file + "." + std::to_string(i);
    std::string new_path = config_.log_file + "." + std::to_string(i + 1);
    std::filesystem::remove(new_path);
    if (std::filesystem::exists(old_path)) {
      std::filesystem::rename(old_path, new_path);
    }
  }

  // Move current log to .1
  std::string backup_path = config_.log_file + ".1";
  if (std::filesystem::exists(config_.log_file)) {
    std::filesystem::rename(config_.log_file, backup_path);
  }

  // Open new stream
  log_stream_.open(config_.log_file, std::ios::app);
  current_size_ = 0;
}

std::string SecurityAuditLogger::current_timestamp() const {
  auto now = std::chrono::system_clock::now();
  auto time_t_now = std::chrono::system_clock::to_time_t(now);
  auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                now.time_since_epoch()) %
            1000;

  std::stringstream ss;
  ss << std::put_time(std::gmtime(&time_t_now), "%Y-%m-%dT%H:%M:%S");
  ss << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';
  return ss.str();
}

AuditEvent SecurityAuditLogger::create_event(
    AuditEventType event_type, AuditSeverity severity,
    const std::string& user_id, const std::string& agent_name,
    const std::string& message, const nlohmann::json& details) const {
  AuditEvent event;
  event.event_type = event_type;
  event.severity = severity;
  event.user_id = user_id;
  event.agent_name = agent_name;
  event.message = message;
  event.timestamp = current_timestamp();
  event.details = details;
  return event;
}

void SecurityAuditLogger::log(const AuditEvent& event) {
  if (!should_log(event.severity)) {
    return;
  }

  std::lock_guard<std::mutex> lock(mutex_);

  std::string log_line = event.to_json().dump() + "\n";
  size_t log_bytes = log_line.size();

  // Check if rotation needed
  if (current_size_ + log_bytes > config_.max_bytes) {
    rotate_log();
  }

  // Write to file
  if (log_stream_.is_open()) {
    log_stream_ << log_line;
    log_stream_.flush();
    current_size_ += log_bytes;
  }

  // Also log to console if configured
  if (config_.also_log_to_console) {
    std::string level = audit_severity_to_string(event.severity);
    std::cout << "[" << level << "] " << event.message << std::endl;
    if (!event.details.empty()) {
      std::cout << "Details: " << event.details.dump(2) << std::endl;
    }
  }
}

void SecurityAuditLogger::log_access(bool granted, const std::string& user_id,
                                      const std::string& agent_name,
                                      const std::string& action,
                                      const nlohmann::json& details) {
  auto event_type =
      granted ? AuditEventType::ACCESS_GRANTED : AuditEventType::ACCESS_DENIED;
  auto severity = granted ? AuditSeverity::INFO : AuditSeverity::WARNING;
  std::string message =
      std::string("Access ") + (granted ? "granted" : "denied") +
      " for action: " + action;

  auto event =
      create_event(event_type, severity, user_id, agent_name, message, details);
  log(event);
}

void SecurityAuditLogger::log_permission_check(
    bool granted, const std::string& user_id, const std::string& agent_name,
    const std::string& permission, const nlohmann::json& details) {
  auto event_type = granted ? AuditEventType::PERMISSION_GRANTED
                            : AuditEventType::PERMISSION_DENIED;
  auto severity = granted ? AuditSeverity::INFO : AuditSeverity::WARNING;
  std::string message = "Permission " + permission + ": " +
                        (granted ? "granted" : "denied");

  auto event =
      create_event(event_type, severity, user_id, agent_name, message, details);
  log(event);
}

void SecurityAuditLogger::log_validation_failure(
    const std::string& user_id, const std::string& validation_type,
    const std::string& reason, const std::string& content_preview,
    const std::string& agent_name) {
  // Truncate content preview
  std::string truncated =
      content_preview.length() > 200
          ? content_preview.substr(0, 200) + "..."
          : content_preview;

  auto event_type = (validation_type == "input")
                        ? AuditEventType::INPUT_VALIDATION_FAILED
                        : AuditEventType::OUTPUT_VALIDATION_FAILED;

  std::string message = validation_type + " validation failed: " + reason;

  nlohmann::json details;
  details["validation_type"] = validation_type;
  details["reason"] = reason;
  details["content_preview"] = truncated;

  auto event = create_event(event_type, AuditSeverity::ERROR, user_id,
                             agent_name, message, details);
  log(event);
}

void SecurityAuditLogger::log_prompt_injection(const std::string& user_id,
                                                double score,
                                                const std::string& details_str,
                                                const std::string& agent_name) {
  std::string message = "Prompt injection detected (score: " +
                        std::to_string(score) + ")";

  nlohmann::json details;
  details["score"] = score;
  details["detection_details"] = details_str;

  auto event = create_event(AuditEventType::PROMPT_INJECTION_DETECTED,
                             AuditSeverity::CRITICAL, user_id, agent_name,
                             message, details);
  log(event);
}

void SecurityAuditLogger::log_sensitive_data(const std::string& user_id,
                                              const std::string& data_type,
                                              const nlohmann::json& details,
                                              const std::string& agent_name) {
  std::string message = "Sensitive data detected: " + data_type;

  auto event = create_event(AuditEventType::SENSITIVE_DATA_DETECTED,
                             AuditSeverity::WARNING, user_id, agent_name,
                             message, details);
  log(event);
}

void SecurityAuditLogger::log_anomaly(const std::string& user_id,
                                       SecurityEvent anomaly_type,
                                       const nlohmann::json& details,
                                       const std::string& agent_name) {
  std::string message = "Anomaly detected: " +
                        security_event_to_string(anomaly_type);

  auto event = create_event(AuditEventType::ANOMALY_DETECTED,
                             AuditSeverity::WARNING, user_id, agent_name,
                             message, details);
  log(event);
}

void SecurityAuditLogger::log_agent_event(AuditEventType event_type,
                                           const std::string& user_id,
                                           const std::string& agent_name,
                                           const nlohmann::json& details) {
  std::string message;
  AuditSeverity severity = AuditSeverity::INFO;

  switch (event_type) {
    case AuditEventType::AGENT_STARTED:
      message = "Agent started";
      break;
    case AuditEventType::AGENT_COMPLETED:
      message = "Agent completed successfully";
      break;
    case AuditEventType::AGENT_FAILED:
      message = "Agent failed";
      severity = AuditSeverity::ERROR;
      break;
    default:
      message = "Agent event";
      break;
  }

  auto event =
      create_event(event_type, severity, user_id, agent_name, message, details);
  log(event);
}

}  // namespace infrastructure
}  // namespace agenkit
