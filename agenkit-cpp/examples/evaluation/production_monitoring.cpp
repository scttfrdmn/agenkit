/**
 * @file production_monitoring.cpp
 * @brief Production monitoring example combining metrics and regression detection
 */

#include "agenkit/evaluation/metrics.hpp"
#include "agenkit/evaluation/regression.hpp"
#include <iostream>
#include <random>

using namespace agenkit::evaluation;

SessionResult simulate_production_session(int id, double quality_degradation = 0.0) {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    std::uniform_real_distribution<> dist(0.8, 1.0);

    SessionResult result("prod-" + std::to_string(id), "production-agent");

    double quality = dist(gen) - quality_degradation;
    result.add_metric_measurement(create_quality_metric("quality", quality * 10, 10.0));

    result.set_status(quality > 0.7 ? SessionStatus::Completed : SessionStatus::Failed);
    return result;
}

int main() {
    std::cout << "Production Monitoring Example" << std::endl;
    std::cout << "=============================" << std::endl << std::endl;

    MetricsCollector collector;
    RegressionDetector detector;

    // Phase 1: Normal operation (baseline)
    std::cout << "Phase 1: Establishing Baseline (10 sessions)" << std::endl;
    for (int i = 0; i < 10; ++i) {
        auto result = simulate_production_session(i);
        collector.add_result(result);
    }

    auto stats1 = collector.get_statistics();
    std::cout << "  Success Rate: " << stats1["success_rate"].get<double>() * 100 << "%" << std::endl;
    auto quality1 = collector.get_metric_aggregates("quality");
    std::cout << "  Avg Quality: " << quality1["mean"] << std::endl << std::endl;

    // Set baseline for regression detection
    EvaluationResult baseline;
    baseline.evaluation_id = "baseline";
    baseline.agent_name = "production-agent";
    baseline.timestamp = std::chrono::system_clock::now();
    baseline.quality_score = quality1["mean"].get<double>();
    detector.set_baseline(baseline);

    // Phase 2: Degraded performance
    std::cout << "Phase 2: Degraded Performance (10 sessions)" << std::endl;
    collector.clear();

    for (int i = 10; i < 20; ++i) {
        auto result = simulate_production_session(i, 0.2); // Introduce degradation
        collector.add_result(result);
    }

    auto stats2 = collector.get_statistics();
    std::cout << "  Success Rate: " << stats2["success_rate"].get<double>() * 100 << "%" << std::endl;
    auto quality2 = collector.get_metric_aggregates("quality");
    std::cout << "  Avg Quality: " << quality2["mean"] << std::endl;

    // Check for regressions
    EvaluationResult current;
    current.evaluation_id = "current";
    current.agent_name = "production-agent";
    current.timestamp = std::chrono::system_clock::now();
    current.quality_score = quality2["mean"].get<double>();

    auto regressions = detector.detect(current);
    if (!regressions.empty()) {
        std::cout << "\n⚠️  ALERT: Regressions Detected!" << std::endl;
        for (const auto& reg : regressions) {
            std::cout << "  - " << reg.metric_name << ": "
                      << reg.degradation_percent << "% worse" << std::endl;
        }
    }

    std::cout << "\nProduction monitoring catches issues before users do!" << std::endl;

    return 0;
}
