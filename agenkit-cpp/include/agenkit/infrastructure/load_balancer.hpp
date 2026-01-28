#pragma once

#include "agenkit/core/agent.hpp"
#include <atomic>
#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace agenkit {
namespace infrastructure {

/// Load balancing strategy.
enum class LoadBalancingStrategy {
    RoundRobin,
    LeastConnections,
    WeightedRoundRobin,
    Random
};

/// Backend agent with metadata.
struct AgentBackend {
    std::shared_ptr<Agent> agent;
    int weight;
    std::atomic<bool> healthy;
    std::atomic<int> active_connections;
    std::atomic<uint64_t> total_requests;
    std::atomic<uint64_t> total_failures;
    std::chrono::steady_clock::time_point last_health_check;
    std::atomic<int> consecutive_failures;

    AgentBackend(std::shared_ptr<Agent> a, int w)
        : agent(std::move(a))
        , weight(w)
        , healthy(true)
        , active_connections(0)
        , total_requests(0)
        , total_failures(0)
        , last_health_check(std::chrono::steady_clock::now())
        , consecutive_failures(0)
    {}
};

/// Load balancer configuration.
struct LoadBalancerConfig {
    LoadBalancingStrategy strategy;
    std::chrono::milliseconds health_check_interval;
    std::chrono::milliseconds health_check_timeout;
    int failure_threshold;
    int success_threshold;
    bool enable_failover;

    LoadBalancerConfig()
        : strategy(LoadBalancingStrategy::RoundRobin)
        , health_check_interval(30000)
        , health_check_timeout(5000)
        , failure_threshold(3)
        , success_threshold(2)
        , enable_failover(true)
    {}
};

/// Load balancer performance metrics.
struct LoadBalancerMetrics {
    std::atomic<uint64_t> total_requests{0};
    std::atomic<uint64_t> successful_requests{0};
    std::atomic<uint64_t> failed_requests{0};
    std::atomic<uint64_t> failover_attempts{0};
    std::unordered_map<std::string, uint64_t> backend_health_changes;
    std::mutex changes_mutex;
};

/// Backend statistics.
struct BackendStats {
    std::string name;
    bool healthy;
    int weight;
    int active_connections;
    uint64_t total_requests;
    uint64_t total_failures;
};

/// Load balancer distributes requests across multiple agents.
class LoadBalancer : public Agent {
public:
    LoadBalancer(
        std::vector<std::shared_ptr<Agent>> agents,
        const LoadBalancerConfig& config,
        const std::vector<int>& weights = {}
    );

    ~LoadBalancer() override;

    std::string name() const override;
    std::vector<std::string> capabilities() const override;
    Message process(const Message& message) override;

    std::vector<BackendStats> get_backend_stats() const;
    void start_health_checks();
    void stop_health_checks();
    LoadBalancerMetrics get_metrics() const;

private:
    size_t select_backend();
    size_t select_round_robin();
    size_t select_least_connections(const std::vector<size_t>& healthy_indices);
    size_t select_weighted_round_robin(const std::vector<size_t>& healthy_indices);
    void perform_health_checks();
    void track_health_change(const std::string& agent_name, const std::string& change_type);

    std::vector<std::shared_ptr<AgentBackend>> backends_;
    LoadBalancerConfig config_;
    LoadBalancerMetrics metrics_;
    std::atomic<size_t> current_index_{0};
    mutable std::mutex backends_mutex_;
    std::atomic<bool> stop_health_checks_{false};
    std::thread health_check_thread_;
};

} // namespace infrastructure
} // namespace agenkit
