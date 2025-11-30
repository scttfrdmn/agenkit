/**
 * @file quality_scoring.cpp
 * @brief Quality metrics and scoring example
 */

#include "agenkit/evaluation/quality_metrics.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <iostream>

using namespace agenkit;
using namespace agenkit::evaluation;

int main() {
    std::cout << "Quality Scoring Example" << std::endl;
    std::cout << "=======================" << std::endl << std::endl;

    auto agent = std::make_shared<adapters::EchoAgent>("Echo");

    // Test case 1: Accuracy metric
    std::cout << "Test 1: Accuracy Metric" << std::endl;
    AccuracyMetric accuracy_metric(false); // Case-insensitive

    auto input1 = core::Message::with_text("user", "What is the capital of France?");
    auto output1 = core::Message::with_text("assistant", "The capital is Paris");
    nlohmann::json ctx1 = {{"expected", "Paris"}};

    double accuracy = accuracy_metric.measure(agent, input1, output1, ctx1);
    std::cout << "  Accuracy: " << accuracy << " (1.0 = correct)" << std::endl << std::endl;

    // Test case 2: Quality metrics
    std::cout << "Test 2: Quality Metrics" << std::endl;
    QualityMetrics quality_metric;

    auto input2 = core::Message::with_text("user", "Explain quantum computing");
    auto output2 = core::Message::with_text("assistant",
        "Quantum computing uses quantum mechanical phenomena like superposition and entanglement "
        "to perform computations. Unlike classical bits that are 0 or 1, quantum bits (qubits) "
        "can exist in multiple states simultaneously, enabling parallel processing.");

    double quality = quality_metric.measure(agent, input2, output2, nlohmann::json::object());
    std::cout << "  Quality Score: " << quality << " (0.0-1.0 scale)" << std::endl << std::endl;

    // Test case 3: Precision/Recall
    std::cout << "Test 3: Precision/Recall Metric" << std::endl;
    PrecisionRecallMetric pr_metric;

    // Simulate classification results
    std::vector<std::pair<bool, bool>> classifications = {
        {true, true},   // TP
        {true, true},   // TP
        {false, true},  // FP
        {true, false},  // FN
        {false, false}  // TN
    };

    for (const auto& pair : classifications) {
        nlohmann::json ctx = {
            {"true_label", pair.first},
            {"predicted_label", pair.second}
        };
        pr_metric.measure(agent, input1, output1, ctx);
    }

    auto pr_stats = pr_metric.aggregate({});
    std::cout << "  Precision: " << pr_stats["precision"] << std::endl;
    std::cout << "  Recall: " << pr_stats["recall"] << std::endl;
    std::cout << "  F1 Score: " << pr_stats["f1_score"] << std::endl;

    std::cout << "\nQuality metrics help evaluate agent performance comprehensively!" << std::endl;

    return 0;
}
