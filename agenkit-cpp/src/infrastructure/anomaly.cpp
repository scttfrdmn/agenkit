/**
 * Implementation of anomaly detection for agent behavior monitoring.
 */

#include "agenkit/infrastructure/anomaly.hpp"
#include "agenkit/infrastructure/thread_pool.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <numeric>
#include <set>

namespace agenkit {
namespace infrastructure {

// ============================================================================
// SecurityEvent
// ============================================================================

std::string security_event_to_string(SecurityEvent event) {
  switch (event) {
    case SecurityEvent::HIGH_REQUEST_RATE:
      return "high_request_rate";
    case SecurityEvent::BURST_DETECTED:
      return "burst_detected";
    case SecurityEvent::REPEATED_FAILURES:
      return "repeated_failures";
    case SecurityEvent::PERMISSION_DENIED_SPIKE:
      return "permission_denied_spike";
    case SecurityEvent::VALIDATION_FAILURES:
      return "validation_failures";
    case SecurityEvent::UNUSUAL_INPUT_SIZE:
      return "unusual_input_size";
    case SecurityEvent::UNUSUAL_OUTPUT_SIZE:
      return "unusual_output_size";
    case SecurityEvent::UNUSUAL_PROCESSING_TIME:
      return "unusual_processing_time";
    case SecurityEvent::SUSPICIOUS_CONTENT_PATTERN:
      return "suspicious_content_pattern";
    case SecurityEvent::REPETITIVE_CONTENT:
      return "repetitive_content";
    default:
      return "unknown";
  }
}

// ============================================================================
// AnomalyDetector
// ============================================================================

AnomalyDetector::AnomalyDetector()
    : AnomalyDetector(Config{}) {}

AnomalyDetector::AnomalyDetector(const Config& config) : config_(config) {}

std::optional<std::pair<SecurityEvent, nlohmann::json>>
AnomalyDetector::detect_rate_anomaly(const std::string& user_id) {
  auto now = std::chrono::system_clock::now().time_since_epoch().count() /
             1000000000.0;  // seconds

  // Get or create user's timestamp list
  auto& timestamps = request_timestamps_[user_id];

  // Record request
  timestamps.push_back(now);

  // Clean old timestamps (> 60 seconds)
  while (!timestamps.empty() && (now - timestamps.front()) > 60.0) {
    timestamps.pop_front();
  }

  // Check request rate (per minute)
  size_t requests_per_minute = timestamps.size();
  if (requests_per_minute >
      static_cast<size_t>(config_.max_requests_per_minute)) {
    nlohmann::json details;
    details["user_id"] = user_id;
    details["requests_per_minute"] = requests_per_minute;
    details["threshold"] = config_.max_requests_per_minute;
    return {{SecurityEvent::HIGH_REQUEST_RATE, details}};
  }

  // Check burst rate (per second)
  size_t recent = std::count_if(
      timestamps.begin(), timestamps.end(),
      [now](double ts) { return (now - ts) < 1.0; });

  if (recent > static_cast<size_t>(config_.max_burst_size)) {
    nlohmann::json details;
    details["user_id"] = user_id;
    details["burst_size"] = recent;
    details["threshold"] = config_.max_burst_size;
    return {{SecurityEvent::BURST_DETECTED, details}};
  }

  return std::nullopt;
}

std::optional<std::pair<SecurityEvent, nlohmann::json>>
AnomalyDetector::detect_failure_anomaly(const std::string& user_id,
                                        bool is_failure) {
  // Update counts
  if (is_failure) {
    failure_counts_[user_id]++;
  } else {
    success_counts_[user_id]++;
  }

  // Calculate failure rate
  size_t failures = failure_counts_[user_id];
  size_t successes = success_counts_[user_id];
  size_t total = failures + successes;

  if (total >= 10) {  // Need at least 10 requests for meaningful rate
    double failure_rate = static_cast<double>(failures) / total;

    if (failure_rate > config_.failure_rate_threshold) {
      nlohmann::json details;
      details["user_id"] = user_id;
      details["failure_rate"] = failure_rate;
      details["failures"] = failures;
      details["total"] = total;
      return {{SecurityEvent::REPEATED_FAILURES, details}};
    }
  }

  return std::nullopt;
}

std::optional<std::pair<SecurityEvent, nlohmann::json>>
AnomalyDetector::detect_size_anomaly(size_t input_size, size_t output_size) {
  // Track sizes
  input_sizes_.push_back(static_cast<double>(input_size));
  if (input_sizes_.size() > config_.max_stats_size) {
    input_sizes_.pop_front();
  }

  output_sizes_.push_back(static_cast<double>(output_size));
  if (output_sizes_.size() > config_.max_stats_size) {
    output_sizes_.pop_front();
  }

  // Need enough data points for statistics
  if (input_sizes_.size() < 20) {
    return std::nullopt;
  }

  // Calculate mean and std dev
  double input_mean = mean(input_sizes_);
  double input_stdev = stdev(input_sizes_, input_mean);

  double output_mean = mean(output_sizes_);
  double output_stdev = stdev(output_sizes_, output_mean);

  // Check input size anomaly (> threshold std devs from mean)
  if (input_stdev > 0) {
    double input_z_score =
        std::abs(static_cast<double>(input_size) - input_mean) / input_stdev;
    if (input_z_score > config_.input_size_threshold) {
      nlohmann::json details;
      details["input_size"] = input_size;
      details["mean"] = input_mean;
      details["stdev"] = input_stdev;
      details["z_score"] = input_z_score;
      return {{SecurityEvent::UNUSUAL_INPUT_SIZE, details}};
    }
  }

  // Check output size anomaly
  if (output_stdev > 0) {
    double output_z_score =
        std::abs(static_cast<double>(output_size) - output_mean) /
        output_stdev;
    if (output_z_score > config_.output_size_threshold) {
      nlohmann::json details;
      details["output_size"] = output_size;
      details["mean"] = output_mean;
      details["stdev"] = output_stdev;
      details["z_score"] = output_z_score;
      return {{SecurityEvent::UNUSUAL_OUTPUT_SIZE, details}};
    }
  }

  return std::nullopt;
}

std::optional<std::pair<SecurityEvent, nlohmann::json>>
AnomalyDetector::detect_content_anomaly(const std::string& user_id,
                                        const std::string& content) {
  // Track recent content (hash first 500 chars)
  std::string content_sample =
      content.length() > 500 ? content.substr(0, 500) : content;
  size_t content_hash = simple_hash(content_sample);

  auto& content_hashes = recent_content_[user_id];
  content_hashes.push_back(content_hash);

  if (content_hashes.size() > config_.max_content_history) {
    content_hashes.pop_front();
  }

  // Check for repetitive content (same content repeated)
  if (content_hashes.size() >= 5) {
    std::deque<size_t> recent5(content_hashes.end() - 5, content_hashes.end());
    std::set<size_t> unique_set(recent5.begin(), recent5.end());

    if (unique_set.size() == 1) {  // All 5 are same
      nlohmann::json details;
      details["user_id"] = user_id;
      details["repetitions"] = 5;
      return {{SecurityEvent::REPETITIVE_CONTENT, details}};
    }
  }

  return std::nullopt;
}

double AnomalyDetector::mean(const std::deque<double>& values) const {
  if (values.empty()) return 0.0;
  return std::accumulate(values.begin(), values.end(), 0.0) / values.size();
}

double AnomalyDetector::stdev(const std::deque<double>& values,
                               double mean_val) const {
  if (values.empty()) return 0.0;
  double variance =
      std::accumulate(values.begin(), values.end(), 0.0,
                      [mean_val](double acc, double val) {
                        return acc + std::pow(val - mean_val, 2);
                      }) /
      values.size();
  return std::sqrt(variance);
}

size_t AnomalyDetector::simple_hash(const std::string& str) const {
  size_t hash = 0;
  for (char c : str) {
    hash = (hash << 5) - hash + static_cast<unsigned char>(c);
  }
  return hash;
}

// ============================================================================
// AnomalyDetectionMiddleware
// ============================================================================

AnomalyDetectionMiddleware::AnomalyDetectionMiddleware(
    std::shared_ptr<core::Agent> agent,
    std::shared_ptr<AnomalyDetector> detector, std::string user_id,
    AnomalyCallback on_anomaly)
    : agent_(agent),
      detector_(detector ? detector : std::make_shared<AnomalyDetector>()),
      user_id_(std::move(user_id)),
      on_anomaly_(on_anomaly ? on_anomaly
                              : [this](SecurityEvent event,
                                       nlohmann::json details) {
                                  default_anomaly_handler(event, details);
                                }) {}

std::string AnomalyDetectionMiddleware::name() const { return agent_->name(); }

void AnomalyDetectionMiddleware::default_anomaly_handler(
    SecurityEvent event, nlohmann::json details) {
  std::cout << "SECURITY ANOMALY DETECTED: "
            << security_event_to_string(event) << std::endl;
  std::cout << "Details: " << details.dump(2) << std::endl;
}

std::future<core::Result<core::Message, core::AgentError>>
AnomalyDetectionMiddleware::process(core::Message message) {
  return infrastructure::global_thread_pool().enqueue([this, message]() mutable {
    auto start_time = std::chrono::high_resolution_clock::now();

    // 1. Check rate anomaly
    auto rate_anomaly = detector_->detect_rate_anomaly(user_id_);
    if (rate_anomaly) {
      on_anomaly_(rate_anomaly->first, rate_anomaly->second);
    }

    // 2. Check content anomaly
    std::string content_str = message.content();
    auto content_anomaly =
        detector_->detect_content_anomaly(user_id_, content_str);
    if (content_anomaly) {
      on_anomaly_(content_anomaly->first, content_anomaly->second);
    }

    // 3. Process with wrapped agent
    bool is_failure = false;
    core::Result<core::Message, core::AgentError> result =
        core::Result<core::Message, core::AgentError>::err(
            core::AgentError(core::AgentErrorType::Internal, "Not initialized"));

    try {
      result = agent_->process(std::move(message)).get();
      is_failure = result.is_err();
    } catch (...) {
      is_failure = true;
      throw;
    }

    // 4. Check failure anomaly (in finally block equivalent)
    auto failure_anomaly = detector_->detect_failure_anomaly(user_id_, is_failure);
    if (failure_anomaly) {
      on_anomaly_(failure_anomaly->first, failure_anomaly->second);
    }

    // 5. Check size and timing anomalies (if succeeded)
    if (!is_failure) {
      auto end_time = std::chrono::high_resolution_clock::now();
      double processing_time =
          std::chrono::duration<double>(end_time - start_time).count();

      size_t input_size = content_str.length();
      size_t output_size = result.unwrap().content_as_str().length();

      auto size_anomaly = detector_->detect_size_anomaly(input_size, output_size);
      if (size_anomaly) {
        on_anomaly_(size_anomaly->first, size_anomaly->second);
      }

      // Check processing time
      if (processing_time > detector_->config().processing_time_threshold) {
        nlohmann::json details;
        details["user_id"] = user_id_;
        details["processing_time"] = processing_time;
        details["threshold"] = detector_->config().processing_time_threshold;
        on_anomaly_(SecurityEvent::UNUSUAL_PROCESSING_TIME, details);
      }
    }

    return result;
  });
}

}  // namespace infrastructure
}  // namespace agenkit
