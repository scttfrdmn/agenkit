#include "agenkit/infrastructure/health.hpp"
#include <sstream>
#include <iomanip>

namespace agenkit {
namespace infrastructure {

HealthChecker::HealthChecker(
    std::shared_ptr<Agent> agent,
    const HealthCheckConfig& config
) : agent_(std::move(agent))
  , config_(config)
{
}

HealthChecker::~HealthChecker() {
    stop();
}

bool HealthChecker::is_healthy() const {
    return is_alive_.load() && is_ready_.load();
}

void HealthChecker::start() {
    if (liveness_thread_.joinable() || readiness_thread_.joinable()) {
        return; // Already started
    }

    stop_threads_ = false;

    if (config_.liveness_enabled) {
        liveness_thread_ = std::thread([this]() {
            liveness_loop();
        });
    }

    if (config_.readiness_enabled) {
        readiness_thread_ = std::thread([this]() {
            readiness_loop();
        });
    }

    if (config_.startup_enabled && !startup_complete_) {
        startup_thread_ = std::thread([this]() {
            startup_check();
        });
    }
}

void HealthChecker::stop() {
    stop_threads_ = true;

    if (liveness_thread_.joinable()) {
        liveness_thread_.join();
    }

    if (readiness_thread_.joinable()) {
        readiness_thread_.join();
    }

    if (startup_thread_.joinable()) {
        startup_thread_.join();
    }
}

HealthCheckResult HealthChecker::check_liveness() {
    auto start_time = std::chrono::steady_clock::now();
    auto probe_type = ProbeType::Liveness;

    track_check_started(probe_type);

    try {
        // Basic liveness: Can we call methods?
        agent_->name();
        agent_->capabilities();

        // Custom check if provided
        if (config_.customCheck && !config_.customCheck(agent_.get())) {
            auto duration = std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - start_time
            ).count();
            track_check_failure(probe_type, duration);

            return HealthCheckResult{
                HealthStatus::Unhealthy,
                probe_type,
                "Custom health check failed",
                std::chrono::steady_clock::now(),
                duration
            };
        }

        // Success
        auto duration = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - start_time
        ).count();
        track_check_success(probe_type, duration);

        return HealthCheckResult{
            HealthStatus::Healthy,
            probe_type,
            "Agent process is alive",
            std::chrono::steady_clock::now(),
            duration
        };
    } catch (const std::exception& e) {
        auto duration = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - start_time
        ).count();
        track_check_failure(probe_type, duration);

        return HealthCheckResult{
            HealthStatus::Unhealthy,
            probe_type,
            std::string("Liveness check failed: ") + e.what(),
            std::chrono::steady_clock::now(),
            duration
        };
    }
}

HealthCheckResult HealthChecker::check_readiness() {
    auto start_time = std::chrono::steady_clock::now();
    auto probe_type = ProbeType::Readiness;

    track_check_started(probe_type);

    // Check if startup completed
    if (config_.startup_enabled && !startup_complete_) {
        auto duration = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - start_time
        ).count();
        track_check_failure(probe_type, duration);

        return HealthCheckResult{
            HealthStatus::Unhealthy,
            probe_type,
            "Startup not complete",
            std::chrono::steady_clock::now(),
            duration
        };
    }

    try {
        // Test with a simple request
        Message test_msg;
        test_msg.role = "system";
        test_msg.content = "readiness_check";

        auto response = agent_->process(test_msg);
        auto duration = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - start_time
        ).count();

        if (response.content.empty()) {
            track_check_failure(probe_type, duration);
            return HealthCheckResult{
                HealthStatus::Unhealthy,
                probe_type,
                "Readiness check failed: empty response",
                std::chrono::steady_clock::now(),
                duration
            };
        }

        // Success
        track_check_success(probe_type, duration);

        return HealthCheckResult{
            HealthStatus::Healthy,
            probe_type,
            "Agent is ready to handle requests",
            std::chrono::steady_clock::now(),
            duration
        };
    } catch (const std::exception& e) {
        auto duration = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - start_time
        ).count();
        track_check_failure(probe_type, duration);

        return HealthCheckResult{
            HealthStatus::Unhealthy,
            probe_type,
            std::string("Readiness check failed: ") + e.what(),
            std::chrono::steady_clock::now(),
            duration
        };
    }
}

HealthCheckResult HealthChecker::check_startup() {
    auto start_time = std::chrono::steady_clock::now();
    auto probe_type = ProbeType::Startup;

    track_check_started(probe_type);

    // Perform readiness check as startup test
    auto readiness_result = check_readiness();

    if (readiness_result.status == HealthStatus::Healthy) {
        startup_complete_ = true;

        auto duration = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - start_time
        ).count();
        track_check_success(probe_type, duration);

        return HealthCheckResult{
            HealthStatus::Healthy,
            probe_type,
            "Startup complete",
            std::chrono::steady_clock::now(),
            duration
        };
    }

    auto duration = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - start_time
    ).count();
    track_check_failure(probe_type, duration);

    return HealthCheckResult{
        HealthStatus::Unhealthy,
        probe_type,
        "Startup checks not passing yet",
        std::chrono::steady_clock::now(),
        duration
    };
}

void HealthChecker::liveness_loop() {
    while (!stop_threads_) {
        auto result = check_liveness();

        if (result.status == HealthStatus::Unhealthy) {
            std::lock_guard<std::mutex> lock(metrics_.mutex);
            auto failures = metrics_.consecutive_failures[ProbeType::Liveness];
            if (failures >= config_.liveness_failure_threshold) {
                is_alive_ = false;
            }
        } else {
            is_alive_ = true;
        }

        std::this_thread::sleep_for(config_.liveness_interval);
    }
}

void HealthChecker::readiness_loop() {
    while (!stop_threads_) {
        auto result = check_readiness();

        if (result.status == HealthStatus::Unhealthy) {
            std::lock_guard<std::mutex> lock(metrics_.mutex);
            auto failures = metrics_.consecutive_failures[ProbeType::Readiness];
            if (failures >= config_.readiness_failure_threshold) {
                is_ready_ = false;
            }
        } else {
            is_ready_ = true;
        }

        std::this_thread::sleep_for(config_.readiness_interval);
    }
}

void HealthChecker::startup_check() {
    auto start_time = std::chrono::steady_clock::now();
    int attempts = 0;

    while (!stop_threads_) {
        if (std::chrono::steady_clock::now() - start_time > config_.startup_timeout) {
            break;
        }

        attempts++;
        if (attempts > config_.startup_failure_threshold) {
            break;
        }

        auto result = check_startup();
        if (result.status == HealthStatus::Healthy) {
            break;
        }

        std::this_thread::sleep_for(std::chrono::seconds(10));
    }
}

void HealthChecker::track_check_started(ProbeType probe_type) {
    std::lock_guard<std::mutex> lock(metrics_.mutex);
    metrics_.total_checks[probe_type]++;
}

void HealthChecker::track_check_success(ProbeType probe_type, double duration_ms) {
    std::lock_guard<std::mutex> lock(metrics_.mutex);
    metrics_.successful_checks[probe_type]++;
    metrics_.last_check_time[probe_type] = std::chrono::steady_clock::now();
    metrics_.last_check_duration[probe_type] = duration_ms;
    metrics_.consecutive_failures[probe_type] = 0;
}

void HealthChecker::track_check_failure(ProbeType probe_type, double duration_ms) {
    std::lock_guard<std::mutex> lock(metrics_.mutex);
    metrics_.failed_checks[probe_type]++;
    metrics_.last_check_time[probe_type] = std::chrono::steady_clock::now();
    metrics_.last_check_duration[probe_type] = duration_ms;
    metrics_.consecutive_failures[probe_type]++;
}

std::string HealthChecker::export_prometheus_metrics() const {
    std::lock_guard<std::mutex> lock(metrics_.mutex);
    std::ostringstream ss;

    // Total checks
    ss << "# HELP agenkit_health_checks_total Total number of health checks performed\n";
    ss << "# TYPE agenkit_health_checks_total counter\n";
    for (const auto& [probe_type, count] : metrics_.total_checks) {
        ss << "agenkit_health_checks_total{probe=\"";
        switch (probe_type) {
            case ProbeType::Liveness: ss << "liveness"; break;
            case ProbeType::Readiness: ss << "readiness"; break;
            case ProbeType::Startup: ss << "startup"; break;
        }
        ss << "\"} " << count << "\n";
    }

    // Failed checks
    ss << "\n# HELP agenkit_health_check_failures_total Total number of failed health checks\n";
    ss << "# TYPE agenkit_health_check_failures_total counter\n";
    for (const auto& [probe_type, count] : metrics_.failed_checks) {
        ss << "agenkit_health_check_failures_total{probe=\"";
        switch (probe_type) {
            case ProbeType::Liveness: ss << "liveness"; break;
            case ProbeType::Readiness: ss << "readiness"; break;
            case ProbeType::Startup: ss << "startup"; break;
        }
        ss << "\"} " << count << "\n";
    }

    // Duration
    ss << "\n# HELP agenkit_health_check_duration_ms Duration of last health check in milliseconds\n";
    ss << "# TYPE agenkit_health_check_duration_ms gauge\n";
    for (const auto& [probe_type, duration] : metrics_.last_check_duration) {
        ss << "agenkit_health_check_duration_ms{probe=\"";
        switch (probe_type) {
            case ProbeType::Liveness: ss << "liveness"; break;
            case ProbeType::Readiness: ss << "readiness"; break;
            case ProbeType::Startup: ss << "startup"; break;
        }
        ss << "\"} " << std::fixed << std::setprecision(2) << duration << "\n";
    }

    // Uptime
    ss << "\n# HELP agenkit_agent_uptime_seconds Uptime in seconds\n";
    ss << "# TYPE agenkit_agent_uptime_seconds gauge\n";
    ss << "agenkit_agent_uptime_seconds " << std::fixed << std::setprecision(2)
       << metrics_.get_uptime() << "\n";

    // Health status
    ss << "\n# HELP agenkit_agent_healthy Agent health status (1=healthy, 0=unhealthy)\n";
    ss << "# TYPE agenkit_agent_healthy gauge\n";
    ss << "agenkit_agent_healthy " << (is_healthy() ? 1 : 0) << "\n";

    return ss.str();
}

HealthMetrics HealthChecker::get_metrics() const {
    std::lock_guard<std::mutex> lock(metrics_.mutex);
    return metrics_;
}

} // namespace infrastructure
} // namespace agenkit
