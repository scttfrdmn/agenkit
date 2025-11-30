/**
 * @file regression_detection.cpp
 * @brief Regression detection example
 */

#include "agenkit/evaluation/regression.hpp"
#include <iostream>

using namespace agenkit::evaluation;

int main() {
    std::cout << "Regression Detection Example" << std::endl;
    std::cout << "============================" << std::endl << std::endl;

    // Create baseline result
    EvaluationResult baseline;
    baseline.evaluation_id = "baseline-1";
    baseline.agent_name = "my-agent-v1";
    baseline.timestamp = std::chrono::system_clock::now();
    baseline.accuracy = 0.95;
    baseline.quality_score = 0.90;
    baseline.avg_latency_ms = 100.0;

    std::cout << "Baseline Performance:" << std::endl;
    std::cout << "  Accuracy: " << *baseline.accuracy << std::endl;
    std::cout << "  Quality: " << *baseline.quality_score << std::endl;
    std::cout << "  Latency: " << *baseline.avg_latency_ms << "ms" << std::endl << std::endl;

    // Create detector
    RegressionDetector detector;
    detector.set_baseline(baseline);

    // Test with good result (no regression)
    std::cout << "Test 1: No Regression" << std::endl;
    EvaluationResult good_result;
    good_result.evaluation_id = "test-1";
    good_result.agent_name = "my-agent-v2";
    good_result.timestamp = std::chrono::system_clock::now();
    good_result.accuracy = 0.96;  // Better
    good_result.quality_score = 0.92;  // Better
    good_result.avg_latency_ms = 105.0;  // Slightly slower but within threshold

    auto regressions1 = detector.detect(good_result, true);
    std::cout << "  Regressions found: " << regressions1.size() << std::endl << std::endl;

    // Test with regression
    std::cout << "Test 2: With Regression" << std::endl;
    EvaluationResult bad_result;
    bad_result.evaluation_id = "test-2";
    bad_result.agent_name = "my-agent-v3";
    bad_result.timestamp = std::chrono::system_clock::now();
    bad_result.accuracy = 0.80;  // 15.8% worse - REGRESSION!
    bad_result.quality_score = 0.75;  // 16.7% worse - REGRESSION!
    bad_result.avg_latency_ms = 95.0;  // Better

    auto regressions2 = detector.detect(bad_result, true);
    std::cout << "  Regressions found: " << regressions2.size() << std::endl;
    for (const auto& reg : regressions2) {
        std::cout << "  - " << reg.metric_name << ": "
                  << reg.degradation_percent << "% worse ("
                  << severity_to_string(reg.severity) << ")" << std::endl;
    }

    std::cout << "\nRegression detection helps catch performance issues in CI/CD!" << std::endl;

    return 0;
}
