#include "agenkit/infrastructure/load_balancer.hpp"
#include <algorithm>
#include <random>
#include <stdexcept>
#include <unordered_set>

namespace agenkit {
namespace infrastructure {

LoadBalancer::LoadBalancer(
    std::vector<std::shared_ptr<Agent>> agents,
    const LoadBalancerConfig& config,
    const std::vector<int>& weights
) : config_(config) {
    if (agents.empty()) {
        throw std::invalid_argument("At least one agent required");
    }

    // Default weights to 1 if not provided
    std::vector<int> final_weights = weights.empty()
        ? std::vector<int>(agents.size(), 1)
        : weights;

    if (final_weights.size() != agents.size()) {
        throw std::invalid_argument(
            "Weights length must match agents length"
        );
    }

    // Create backends
    backends_.reserve(agents.size());
    for (size_t i = 0; i < agents.size(); ++i) {
        backends_.push_back(
            std::make_shared<AgentBackend>(agents[i], final_weights[i])
        );
    }
}

LoadBalancer::~LoadBalancer() {
    stop_health_checks();
}

std::string LoadBalancer::name() const {
    std::lock_guard<std::mutex> lock(backends_mutex_);
    return "LoadBalancer(" + std::to_string(backends_.size()) + " backends)";
}

std::vector<std::string> LoadBalancer::capabilities() const {
    std::lock_guard<std::mutex> lock(backends_mutex_);
    std::unordered_set<std::string> caps_set;
    for (const auto& backend : backends_) {
        for (const auto& cap : backend->agent->capabilities()) {
            caps_set.insert(cap);
        }
    }
    return std::vector<std::string>(caps_set.begin(), caps_set.end());
}

std::vector<BackendStats> LoadBalancer::get_backend_stats() const {
    std::lock_guard<std::mutex> lock(backends_mutex_);
    std::vector<BackendStats> stats;
    stats.reserve(backends_.size());

    for (const auto& backend : backends_) {
        stats.push_back(BackendStats{
            backend->agent->name(),
            backend->healthy.load(),
            backend->weight,
            backend->active_connections.load(),
            backend->total_requests.load(),
            backend->total_failures.load()
        });
    }

    return stats;
}

void LoadBalancer::start_health_checks() {
    if (health_check_thread_.joinable()) {
        return; // Already started
    }

    stop_health_checks_ = false;
    health_check_thread_ = std::thread([this]() {
        while (!stop_health_checks_) {
            perform_health_checks();
            std::this_thread::sleep_for(config_.health_check_interval);
        }
    });
}

void LoadBalancer::stop_health_checks() {
    stop_health_checks_ = true;
    if (health_check_thread_.joinable()) {
        health_check_thread_.join();
    }
}

void LoadBalancer::perform_health_checks() {
    std::lock_guard<std::mutex> lock(backends_mutex_);

    for (auto& backend : backends_) {
        Message test_msg;
        test_msg.role = "system";
        test_msg.content = "health_check";

        try {
            backend->agent->process(test_msg);
            backend->last_health_check = std::chrono::steady_clock::now();

            // Success
            backend->consecutive_failures = 0;
            if (!backend->healthy && backend->consecutive_failures == 0) {
                backend->healthy = true;
                track_health_change(backend->agent->name(), "recovered");
            }
        } catch (...) {
            // Failure
            backend->consecutive_failures++;
            backend->total_failures++;

            if (backend->healthy &&
                backend->consecutive_failures.load() >= config_.failure_threshold) {
                backend->healthy = false;
                track_health_change(backend->agent->name(), "unhealthy");
            }
        }
    }
}

void LoadBalancer::track_health_change(
    const std::string& agent_name,
    const std::string& change_type
) {
    std::string key = agent_name + ":" + change_type;
    std::lock_guard<std::mutex> lock(metrics_.changes_mutex);
    metrics_.backend_health_changes[key]++;
}

size_t LoadBalancer::select_backend() {
    std::lock_guard<std::mutex> lock(backends_mutex_);

    std::vector<size_t> healthy_indices;
    for (size_t i = 0; i < backends_.size(); ++i) {
        if (backends_[i]->healthy) {
            healthy_indices.push_back(i);
        }
    }

    if (healthy_indices.empty()) {
        throw std::runtime_error("All backends unhealthy");
    }

    switch (config_.strategy) {
        case LoadBalancingStrategy::RoundRobin:
            return select_round_robin();
        case LoadBalancingStrategy::LeastConnections:
            return select_least_connections(healthy_indices);
        case LoadBalancingStrategy::WeightedRoundRobin:
            return select_weighted_round_robin(healthy_indices);
        case LoadBalancingStrategy::Random: {
            std::random_device rd;
            std::mt19937 gen(rd());
            std::uniform_int_distribution<> dis(0, healthy_indices.size() - 1);
            return healthy_indices[dis(gen)];
        }
        default:
            return healthy_indices[0];
    }
}

size_t LoadBalancer::select_round_robin() {
    // Find next healthy backend in rotation
    for (size_t i = 0; i < backends_.size(); ++i) {
        size_t index = (current_index_.fetch_add(1) + 1) % backends_.size();
        if (backends_[index]->healthy) {
            return index;
        }
    }

    // Fallback to first healthy
    for (size_t i = 0; i < backends_.size(); ++i) {
        if (backends_[i]->healthy) {
            return i;
        }
    }

    throw std::runtime_error("No healthy backends");
}

size_t LoadBalancer::select_least_connections(
    const std::vector<size_t>& healthy_indices
) {
    size_t selected = healthy_indices[0];
    int min_connections = backends_[selected]->active_connections;

    for (size_t i = 1; i < healthy_indices.size(); ++i) {
        size_t index = healthy_indices[i];
        int connections = backends_[index]->active_connections;
        if (connections < min_connections) {
            min_connections = connections;
            selected = index;
        }
    }

    return selected;
}

size_t LoadBalancer::select_weighted_round_robin(
    const std::vector<size_t>& healthy_indices
) {
    // Build weighted list
    std::vector<size_t> weighted;
    for (size_t index : healthy_indices) {
        for (int w = 0; w < backends_[index]->weight; ++w) {
            weighted.push_back(index);
        }
    }

    if (weighted.empty()) {
        return healthy_indices[0];
    }

    size_t idx = current_index_.fetch_add(1) % weighted.size();
    return weighted[idx];
}

Message LoadBalancer::process(const Message& message) {
    metrics_.total_requests++;

    std::unordered_set<std::string> attempted;

    while (true) {
        size_t backend_index = select_backend();

        std::string backend_name;
        {
            std::lock_guard<std::mutex> lock(backends_mutex_);
            backend_name = backends_[backend_index]->agent->name();
        }

        // Avoid retrying same backend
        if (attempted.count(backend_name)) {
            std::lock_guard<std::mutex> lock(backends_mutex_);
            if (!config_.enable_failover || attempted.size() >= backends_.size()) {
                throw std::runtime_error("All backends attempted");
            }
            continue;
        }

        attempted.insert(backend_name);

        // Track request
        {
            std::lock_guard<std::mutex> lock(backends_mutex_);
            backends_[backend_index]->active_connections++;
            backends_[backend_index]->total_requests++;
        }

        try {
            Message response;
            {
                std::lock_guard<std::mutex> lock(backends_mutex_);
                response = backends_[backend_index]->agent->process(message);
            }

            // Decrement active connections
            {
                std::lock_guard<std::mutex> lock(backends_mutex_);
                backends_[backend_index]->active_connections--;
            }

            // Success
            metrics_.successful_requests++;
            return response;
        } catch (const std::exception& e) {
            // Decrement active connections
            {
                std::lock_guard<std::mutex> lock(backends_mutex_);
                backends_[backend_index]->active_connections--;
            }

            // Failure
            {
                std::lock_guard<std::mutex> lock(backends_mutex_);
                backends_[backend_index]->total_failures++;
            }
            metrics_.failed_requests++;

            // Check if should mark unhealthy
            {
                std::lock_guard<std::mutex> lock(backends_mutex_);
                if (backends_[backend_index]->total_failures.load() >=
                    static_cast<uint64_t>(config_.failure_threshold)) {
                    backends_[backend_index]->healthy = false;
                    track_health_change(backend_name, "unhealthy");
                }
            }

            // Try failover if enabled
            std::lock_guard<std::mutex> lock(backends_mutex_);
            if (config_.enable_failover && attempted.size() < backends_.size()) {
                metrics_.failover_attempts++;
                continue;
            }

            // No more failover
            throw std::runtime_error(
                "Backend " + backend_name + " failed: " + e.what()
            );
        }
    }
}

LoadBalancerMetrics LoadBalancer::get_metrics() const {
    return metrics_;
}

} // namespace infrastructure
} // namespace agenkit
