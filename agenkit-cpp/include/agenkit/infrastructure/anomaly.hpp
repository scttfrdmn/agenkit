/**
 * Anomaly detection for agent behavior monitoring.
 *
 * Detects:
 * - Unusual request patterns
 * - Rate anomalies
 * - Suspicious behavior
 * - Resource usage anomalies
 */

#pragma once

#include <chrono>
#include <deque>
#include <functional>
#include <future>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "agenkit/core/agent.hpp"
#include "agenkit/core/errors.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <nlohmann/json.hpp>

namespace agenkit {
namespace infrastructure {

/**
 * Types of security events.
 */
enum class SecurityEvent {
  // Rate anomalies
  HIGH_REQUEST_RATE,
  BURST_DETECTED,

  // Pattern anomalies
  REPEATED_FAILURES,
  PERMISSION_DENIED_SPIKE,
  VALIDATION_FAILURES,

  // Behavior anomalies
  UNUSUAL_INPUT_SIZE,
  UNUSUAL_OUTPUT_SIZE,
  UNUSUAL_PROCESSING_TIME,

  // Content anomalies
  SUSPICIOUS_CONTENT_PATTERN,
  REPETITIVE_CONTENT
};

/**
 * Convert SecurityEvent to string.
 */
std::string security_event_to_string(SecurityEvent event);

/**
 * Detects anomalous agent behavior.
 *
 * Uses statistical methods and heuristics to identify:
 * - Rate-based anomalies
 * - Pattern-based anomalies
 * - Content-based anomalies
 */
class AnomalyDetector {
 public:
  /**
   * Configuration for anomaly detection.
   */
  struct Config {
    int max_requests_per_minute = 60;
    int max_burst_size = 10;
    double input_size_threshold = 3.0;   // sigma
    double output_size_threshold = 3.0;  // sigma
    double processing_time_threshold = 30.0;  // seconds
    double failure_rate_threshold = 0.5;      // 50%
    size_t max_stats_size = 100;
    size_t max_content_history = 10;
  };

  AnomalyDetector();
  explicit AnomalyDetector(const Config& config);

  /**
   * Detect rate-based anomalies.
   *
   * @return optional pair of (event, details) if anomaly detected
   */
  std::optional<std::pair<SecurityEvent, nlohmann::json>>
  detect_rate_anomaly(const std::string& user_id);

  /**
   * Detect failure rate anomalies.
   *
   * @return optional pair of (event, details) if anomaly detected
   */
  std::optional<std::pair<SecurityEvent, nlohmann::json>>
  detect_failure_anomaly(const std::string& user_id, bool is_failure);

  /**
   * Detect unusual input/output sizes.
   *
   * @return optional pair of (event, details) if anomaly detected
   */
  std::optional<std::pair<SecurityEvent, nlohmann::json>>
  detect_size_anomaly(size_t input_size, size_t output_size);

  /**
   * Detect content-based anomalies.
   *
   * @return optional pair of (event, details) if anomaly detected
   */
  std::optional<std::pair<SecurityEvent, nlohmann::json>>
  detect_content_anomaly(const std::string& user_id,
                         const std::string& content);

  /**
   * Get detector configuration.
   */
  const Config& config() const { return config_; }

 private:
  Config config_;

  // Tracking data structures
  std::unordered_map<std::string, std::deque<double>> request_timestamps_;
  std::unordered_map<std::string, size_t> failure_counts_;
  std::unordered_map<std::string, size_t> success_counts_;

  // Statistics (rolling averages)
  std::deque<double> input_sizes_;
  std::deque<double> output_sizes_;
  std::deque<double> processing_times_;

  // Content tracking
  std::unordered_map<std::string, std::deque<size_t>> recent_content_;

  double mean(const std::deque<double>& values) const;
  double stdev(const std::deque<double>& values, double mean) const;
  size_t simple_hash(const std::string& str) const;
};

/**
 * Middleware for anomaly detection.
 *
 * Monitors agent interactions and detects:
 * - Rate anomalies
 * - Failure patterns
 * - Size anomalies
 * - Content anomalies
 */
class AnomalyDetectionMiddleware : public core::Agent {
 public:
  using AnomalyCallback = std::function<void(SecurityEvent, nlohmann::json)>;

  /**
   * Create anomaly detection middleware.
   *
   * @param agent Agent to wrap
   * @param detector Anomaly detector (optional)
   * @param user_id User identifier
   * @param on_anomaly Callback for anomaly events (optional)
   */
  AnomalyDetectionMiddleware(
      std::shared_ptr<core::Agent> agent,
      std::shared_ptr<AnomalyDetector> detector = nullptr,
      std::string user_id = "default", AnomalyCallback on_anomaly = nullptr);

  std::string name() const override;
  std::future<core::Result<core::Message, core::AgentError>> process(
      core::Message message) override;

 private:
  std::shared_ptr<core::Agent> agent_;
  std::shared_ptr<AnomalyDetector> detector_;
  std::string user_id_;
  AnomalyCallback on_anomaly_;

  void default_anomaly_handler(SecurityEvent event, nlohmann::json details);
};

}  // namespace infrastructure
}  // namespace agenkit
