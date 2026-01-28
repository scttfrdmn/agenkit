// Production-ready agent with load balancing, health checks, and enhanced retry.
//
// This example demonstrates how to build a production agent system with:
// - Load balancing across multiple backend agents
// - Health monitoring with Kubernetes-style probes
// - Enhanced retry with jitter and backpressure detection
// - Prometheus metrics export
//
// Perfect for 30-hour autonomous agent deployments.

#include "agenkit/core/agent.hpp"
#include "agenkit/infrastructure/health.hpp"
#include "agenkit/infrastructure/load_balancer.hpp"
#include "agenkit/infrastructure/retry_enhanced.hpp"

#include <chrono>
#include <iostream>
#include <memory>
#include <random>
#include <thread>

using namespace agenkit;
using namespace agenkit::core;
using namespace agenkit::infrastructure;

/// Simulated agent for testing production infrastructure.
class SimulatedAgent : public Agent {
public:
    SimulatedAgent(const std::string& name, double failure_rate)
        : agent_name_(name), failure_rate_(failure_rate), request_count_(0) {}

    std::string name() const override {
        return agent_name_;
    }

    std::vector<std::string> capabilities() const override {
        return {"text_generation", "reasoning"};
    }

    Message process(const Message& message) override {
        request_count_++;

        // Simulate processing time
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        // Simulate occasional failures
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<> dis(0.0, 1.0);

        if (dis(gen) < failure_rate_) {
            throw std::runtime_error(agent_name_ + ": Simulated transient error");
        }

        Message response;
        response.role = "agent";
        response.content = agent_name_ + " processed: " + message.content;
        response.metadata["agent"] = agent_name_;
        response.metadata["request_count"] = std::to_string(request_count_);

        return response;
    }

private:
    std::string agent_name_;
    double failure_rate_;
    int request_count_;
};

int main() {
    std::cout << "Starting production agent system...\n";

    // 1. Create backend agents with varying failure rates
    auto backend1 = std::make_shared<SimulatedAgent>("agent-1", 0.1);
    auto backend2 = std::make_shared<SimulatedAgent>("agent-2", 0.05);
    auto backend3 = std::make_shared<SimulatedAgent>("agent-3", 0.15);

    // 2. Wrap each backend with enhanced retry
    EnhancedRetryConfig retry_config;
    retry_config.max_attempts = 3;
    retry_config.initial_backoff = std::chrono::milliseconds(100);
    retry_config.max_backoff = std::chrono::milliseconds(5000);
    retry_config.backoff_multiplier = 2.0;
    retry_config.jitter_type = JitterType::Full;
    retry_config.enable_backpressure = true;
    retry_config.backpressure_threshold = 0.3;
    retry_config.backpressure_window = 10;

    auto retry_backend1 = std::make_shared<EnhancedRetryDecorator>(backend1, retry_config);
    auto retry_backend2 = std::make_shared<EnhancedRetryDecorator>(backend2, retry_config);
    auto retry_backend3 = std::make_shared<EnhancedRetryDecorator>(backend3, retry_config);

    // 3. Create load balancer with health checking
    LoadBalancerConfig lb_config;
    lb_config.strategy = LoadBalancingStrategy::LeastConnections;
    lb_config.health_check_enabled = true;
    lb_config.health_check_interval = std::chrono::seconds(5);
    lb_config.health_check_timeout = std::chrono::seconds(2);
    lb_config.max_retries_per_backend = 2;

    auto load_balancer = std::make_shared<LoadBalancer>(
        std::vector<std::shared_ptr<Agent>>{retry_backend1, retry_backend2, retry_backend3},
        lb_config
    );

    // 4. Set up health checker for the load balancer
    HealthCheckConfig health_config;
    health_config.liveness_enabled = true;
    health_config.liveness_interval = std::chrono::seconds(10);
    health_config.liveness_failure_threshold = 3;
    health_config.readiness_enabled = true;
    health_config.readiness_interval = std::chrono::seconds(5);
    health_config.readiness_failure_threshold = 2;
    health_config.startup_enabled = true;
    health_config.startup_timeout = std::chrono::seconds(30);
    health_config.startup_failure_threshold = 5;

    HealthChecker health_checker(load_balancer, health_config);
    health_checker.start();

    // Wait for startup to complete
    std::cout << "Waiting for startup checks...\n";
    std::this_thread::sleep_for(std::chrono::seconds(2));

    if (!health_checker.is_healthy()) {
        std::cerr << "System failed startup checks\n";
        return 1;
    }

    std::cout << "System is healthy and ready!\n";

    // 5. Process requests through the production system
    int successful = 0;
    int failed = 0;

    for (int i = 0; i < 20; i++) {
        Message request;
        request.role = "user";
        request.content = "Request " + std::to_string(i);

        try {
            Message response = load_balancer->process(request);
            std::cout << "Request " << i << ": SUCCESS - " << response.content << "\n";
            successful++;
        } catch (const std::exception& e) {
            std::cerr << "Request " << i << ": FAILED - " << e.what() << "\n";
            failed++;
        }

        // Brief pause between requests
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    // 6. Export metrics
    std::cout << "\n" << std::string(60, '=') << "\n";
    std::cout << "FINAL METRICS\n";
    std::cout << std::string(60, '=') << "\n";

    // Load balancer metrics
    auto lb_metrics = load_balancer->get_metrics();
    std::cout << "\nLoad Balancer:\n";
    std::cout << "  Total requests: " << lb_metrics.total_requests << "\n";
    std::cout << "  Successful: " << lb_metrics.successful_requests << "\n";
    std::cout << "  Failed: " << lb_metrics.failed_requests << "\n";
    if (lb_metrics.total_requests > 0) {
        double success_rate = static_cast<double>(lb_metrics.successful_requests) /
                            lb_metrics.total_requests * 100.0;
        std::cout << "  Success rate: " << std::fixed << std::setprecision(1)
                  << success_rate << "%\n";
    }

    // Backend distribution
    std::cout << "\nBackend Distribution:\n";
    for (const auto& [backend_id, count] : lb_metrics.backend_request_counts) {
        std::cout << "  " << backend_id << ": " << count << " requests\n";
    }

    // Retry metrics for each backend
    std::cout << "\nRetry Metrics:\n";
    std::vector<std::shared_ptr<EnhancedRetryDecorator>> backends = {
        retry_backend1, retry_backend2, retry_backend3
    };
    for (size_t i = 0; i < backends.size(); i++) {
        auto metrics = backends[i]->get_metrics();
        std::cout << "  Agent " << (i + 1) << ":\n";
        std::cout << "    Total attempts: " << metrics.total_attempts << "\n";
        std::cout << "    Successful on first: " << metrics.successful_first_attempt << "\n";
        std::cout << "    Successful on retry: " << metrics.successful_on_retry << "\n";
        std::cout << "    Failed after retries: " << metrics.failed_after_retries << "\n";
        std::cout << "    Total retries: " << metrics.total_retries << "\n";
        if (metrics.backpressure_detected > 0) {
            std::cout << "    Backpressure detected: " << metrics.backpressure_detected << " times\n";
        }
    }

    // Health metrics
    auto health_metrics = health_checker.get_metrics();
    std::cout << "\nHealth Checks:\n";
    for (const auto& [probe_type, count] : health_metrics.total_checks) {
        auto success = health_metrics.successful_checks.at(probe_type);
        auto failed_count = health_metrics.failed_checks.at(probe_type);
        std::cout << "  " << static_cast<int>(probe_type) << ": "
                  << success << "/" << count << " passed ("
                  << failed_count << " failed)\n";
    }

    // Export Prometheus metrics
    std::cout << "\nPrometheus Metrics:\n";
    std::cout << std::string(60, '=') << "\n";
    std::string prometheus_metrics = health_checker.export_prometheus_metrics();
    std::cout << prometheus_metrics;

    // Stop health checker
    health_checker.stop();
    std::cout << "\nProduction agent system stopped.\n";

    return 0;
}
