#pragma once

#include "agenkit/core/agent.hpp"
#include <atomic>
#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>

namespace agenkit {
namespace infrastructure {

/// Health status values.
enum class HealthStatus {
    Healthy,
    Unhealthy,
    Degraded,
    Unknown
};

/// Types of health probes.
enum class ProbeType {
    Liveness,
    Readiness,
    Startup
};

/// Result of a health check.
struct HealthCheckResult {
    HealthStatus status;
    ProbeType probe_type;
    std::string message;
    std::chrono::steady_clock::time_point timestamp;
    double duration_ms;
};

/// Health check configuration.
struct HealthCheckConfig {
    // Liveness probe settings
    bool liveness_enabled;
    std::chrono::milliseconds liveness_interval;
    std::chrono::milliseconds liveness_timeout;
    int liveness_failure_threshold;

    // Readiness probe settings
    bool readiness_enabled;
    std::chrono::milliseconds readiness_interval;
    std::chrono::milliseconds readiness_timeout;
    int readiness_failure_threshold;

    // Startup probe settings
    bool startup_enabled;
    std::chrono::milliseconds startup_timeout;
    int startup_failure_threshold;

    HealthCheckConfig()
        : liveness_enabled(true)
        , liveness_interval(10000)
        , liveness_timeout(5000)
        , liveness_failure_threshold(3)
        , readiness_enabled(true)
        , readiness_interval(5000)
        , readiness_timeout(3000)
        , readiness_failure_threshold(2)
        , startup_enabled(true)
        , startup_timeout(30000)
        , startup_failure_threshold(30)
    {}
};

/// Health check metrics.
struct HealthMetrics {
    std::unordered_map<ProbeType, uint64_t> total_checks;
    std::unordered_map<ProbeType, uint64_t> successful_checks;
    std::unordered_map<ProbeType, uint64_t> failed_checks;
    std::unordered_map<ProbeType, std::chrono::steady_clock::time_point> last_check_time;
    std::unordered_map<ProbeType, double> last_check_duration;
    std::unordered_map<ProbeType, int> consecutive_failures;
    std::chrono::steady_clock::time_point uptime_start;
    mutable std::mutex mutex;

    HealthMetrics()
        : uptime_start(std::chrono::steady_clock::now())
    {}

    double get_uptime() const {
        auto now = std::chrono::steady_clock::now();
        return std::chrono::duration<double>(now - uptime_start).count();
    }
};

/// Health checker monitors agent health.
class HealthChecker {
public:
    HealthChecker(
        std::shared_ptr<Agent> agent,
        const HealthCheckConfig& config = HealthCheckConfig()
    );

    ~HealthChecker();

    bool is_healthy() const;
    void start();
    void stop();

    HealthCheckResult check_liveness();
    HealthCheckResult check_readiness();
    HealthCheckResult check_startup();

    std::string export_prometheus_metrics() const;
    HealthMetrics get_metrics() const;

private:
    void liveness_loop();
    void readiness_loop();
    void startup_check();

    void track_check_started(ProbeType probe_type);
    void track_check_success(ProbeType probe_type, double duration_ms);
    void track_check_failure(ProbeType probe_type, double duration_ms);

    std::shared_ptr<Agent> agent_;
    HealthCheckConfig config_;
    HealthMetrics metrics_;
    std::atomic<bool> is_alive_{true};
    std::atomic<bool> is_ready_{false};
    std::atomic<bool> startup_complete_{false};
    std::atomic<bool> stop_threads_{false};
    std::thread liveness_thread_;
    std::thread readiness_thread_;
    std::thread startup_thread_;
};

} // namespace infrastructure
} // namespace agenkit
