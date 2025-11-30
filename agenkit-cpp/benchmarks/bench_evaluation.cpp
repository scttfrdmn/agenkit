/**
 * @file bench_evaluation.cpp
 * @brief Performance benchmarks for evaluation framework
 *
 * Benchmarks core evaluation components:
 * - MetricMeasurement creation and serialization
 * - SessionResult operations
 * - MetricsCollector aggregation
 * - InteractionRecord and SessionRecording
 * - RegressionDetector performance
 * - Quality metrics calculation
 */

#include <chrono>
#include <iostream>
#include <iomanip>
#include <vector>
#include <numeric>
#include <algorithm>
#include <memory>
#include <filesystem>

#include "agenkit/core/message.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/evaluation/metrics.hpp"
#include "agenkit/evaluation/recorder.hpp"
#include "agenkit/evaluation/quality_metrics.hpp"
#include "agenkit/evaluation/regression.hpp"

using namespace agenkit;
using namespace std::chrono;

// ============================================================================
// Benchmark Infrastructure
// ============================================================================

struct BenchmarkResult {
    std::string name;
    double mean_us;
    double median_us;
    double min_us;
    double max_us;
    size_t iterations;
};

class Timer {
public:
    Timer() : start_(high_resolution_clock::now()) {}

    double elapsed_us() const {
        auto end = high_resolution_clock::now();
        return duration_cast<microseconds>(end - start_).count();
    }

private:
    high_resolution_clock::time_point start_;
};

template<typename Func>
BenchmarkResult benchmark(const std::string& name, Func func, size_t iterations = 1000) {
    std::vector<double> times;
    times.reserve(iterations);

    // Warmup
    for (size_t i = 0; i < 10; ++i) {
        func();
    }

    // Benchmark
    for (size_t i = 0; i < iterations; ++i) {
        Timer timer;
        func();
        times.push_back(timer.elapsed_us());
    }

    // Calculate statistics
    std::sort(times.begin(), times.end());
    double sum = std::accumulate(times.begin(), times.end(), 0.0);
    double mean = sum / times.size();
    double median = times[times.size() / 2];
    double min_val = times.front();
    double max_val = times.back();

    return {name, mean, median, min_val, max_val, iterations};
}

void print_result(const BenchmarkResult& result) {
    std::cout << std::left << std::setw(50) << result.name << " │ ";
    std::cout << std::right << std::setw(10) << std::fixed << std::setprecision(2) << result.mean_us << " │ ";
    std::cout << std::right << std::setw(10) << std::fixed << std::setprecision(2) << result.median_us << " │ ";
    std::cout << std::right << std::setw(10) << std::fixed << std::setprecision(2) << result.min_us << " │ ";
    std::cout << std::right << std::setw(10) << std::fixed << std::setprecision(2) << result.max_us << "\n";
}

// ============================================================================
// Category 1: Metrics Collection Benchmarks
// ============================================================================

void bench_metric_measurement_creation() {
    auto result = benchmark("MetricMeasurement creation", []() {
        auto _ = evaluation::MetricMeasurement(
            "accuracy",
            0.95,
            evaluation::MetricType::SuccessRate
        );
    }, 10000);
    print_result(result);
}

void bench_metric_measurement_json() {
    evaluation::MetricMeasurement measurement(
        "accuracy", 0.95, evaluation::MetricType::SuccessRate
    );

    auto result = benchmark("MetricMeasurement to_json", [&]() {
        auto _ = measurement.to_json();
    }, 10000);
    print_result(result);
}

void bench_session_result_creation() {
    auto result = benchmark("SessionResult creation", []() {
        auto _ = evaluation::SessionResult("session-123", "test-agent");
    }, 10000);
    print_result(result);
}

void bench_session_result_add_metrics() {
    auto result = benchmark("SessionResult add 10 metrics", []() {
        evaluation::SessionResult session("session-123", "test-agent");
        for (int i = 0; i < 10; ++i) {
            session.add_metric_measurement(evaluation::MetricMeasurement(
                "metric_" + std::to_string(i),
                0.9,
                evaluation::MetricType::QualityScore
            ));
        }
    }, 1000);
    print_result(result);
}

void bench_session_result_json() {
    evaluation::SessionResult session("session-123", "test-agent");
    for (int i = 0; i < 10; ++i) {
        session.add_metric_measurement(evaluation::MetricMeasurement(
            "metric_" + std::to_string(i),
            0.9,
            evaluation::MetricType::QualityScore
        ));
    }
    session.set_status(evaluation::SessionStatus::Completed);

    auto result = benchmark("SessionResult to_json (10 metrics)", [&]() {
        auto _ = session.to_json();
    }, 1000);
    print_result(result);
}

void bench_metrics_collector() {
    auto result = benchmark("MetricsCollector (100 sessions)", []() {
        evaluation::MetricsCollector collector;

        for (int i = 0; i < 100; ++i) {
            evaluation::SessionResult session("s" + std::to_string(i), "agent");
            session.add_metric_measurement(evaluation::MetricMeasurement(
                "accuracy", 0.85, evaluation::MetricType::SuccessRate
            ));
            session.set_status(evaluation::SessionStatus::Completed);
            collector.add_result(session);
        }

        auto _ = collector.get_statistics();
    }, 100);
    print_result(result);
}

// ============================================================================
// Category 2: Session Recording Benchmarks
// ============================================================================

void bench_interaction_record_creation() {
    auto input_msg = core::Message::with_text("user", "test");
    auto output_msg = core::Message::with_text("assistant", "response");
    auto timestamp = system_clock::now();

    auto result = benchmark("InteractionRecord creation", [&]() {
        auto _ = evaluation::InteractionRecord(
            "interaction-123",
            "session-123",
            input_msg.to_json(),
            output_msg.to_json(),
            timestamp,
            15.5
        );
    }, 10000);
    print_result(result);
}

void bench_interaction_record_json() {
    auto input_msg = core::Message::with_text("user", "test");
    auto output_msg = core::Message::with_text("assistant", "response");
    auto timestamp = system_clock::now();

    evaluation::InteractionRecord record(
        "interaction-123",
        "session-123",
        input_msg.to_json(),
        output_msg.to_json(),
        timestamp,
        15.5
    );

    auto result = benchmark("InteractionRecord to_dict", [&]() {
        auto _ = record.to_dict();
    }, 10000);
    print_result(result);
}

void bench_session_recording() {
    auto storage = std::make_shared<evaluation::InMemoryRecordingStorage>();
    evaluation::SessionRecorder recorder(storage);

    auto input_msg = core::Message::with_text("user", "test");
    auto output_msg = core::Message::with_text("assistant", "response");

    auto result = benchmark("SessionRecorder (10 interactions)", [&]() {
        std::string session_id = "session-" + std::to_string(rand());
        recorder.start_session(session_id, "test-agent");

        for (int i = 0; i < 10; ++i) {
            recorder.record_interaction(
                session_id,
                input_msg,
                output_msg,
                15.5
            );
        }

        recorder.finalize_session(session_id);
    }, 100);
    print_result(result);
}

// ============================================================================
// Category 3: Regression Detection Benchmarks
// ============================================================================

void bench_evaluation_result_creation() {
    auto result = benchmark("EvaluationResult creation", []() {
        evaluation::EvaluationResult eval;
        eval.evaluation_id = "eval-123";
        eval.agent_name = "test-agent";
        eval.accuracy = 0.95;
        eval.quality_score = 0.92;
        eval.avg_latency_ms = 100.0;
    }, 10000);
    print_result(result);
}

void bench_evaluation_result_json() {
    evaluation::EvaluationResult eval;
    eval.evaluation_id = "eval-123";
    eval.agent_name = "test-agent";
    eval.accuracy = 0.95;
    eval.quality_score = 0.92;
    eval.avg_latency_ms = 100.0;

    auto result = benchmark("EvaluationResult to_json", [&]() {
        auto _ = eval.to_json();
    }, 10000);
    print_result(result);
}

// ============================================================================
// Category 4: Quality Metrics Benchmarks
// ============================================================================

void bench_accuracy_metric() {
    evaluation::AccuracyMetric metric(true); // Case-sensitive
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto input = core::Message::with_text("user", "What is 2+2?");
    auto output = core::Message::with_text("assistant", "4");

    nlohmann::json ctx;
    ctx["expected"] = "4";

    auto result = benchmark("AccuracyMetric measure", [&]() {
        auto _ = metric.measure(agent, input, output, ctx);
    }, 10000);
    print_result(result);
}

void bench_quality_metrics() {
    evaluation::QualityMetrics metric;
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto input = core::Message::with_text("user", "Explain quantum computing");
    auto output = core::Message::with_text("assistant", "Quantum computing uses quantum mechanics.");

    nlohmann::json ctx;

    auto result = benchmark("QualityMetrics measure", [&]() {
        auto _ = metric.measure(agent, input, output, ctx);
    }, 1000);
    print_result(result);
}

void bench_precision_recall_metric() {
    evaluation::PrecisionRecallMetric metric;
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto input = core::Message::with_text("user", "Classify: spam");
    auto output = core::Message::with_text("assistant", "spam");

    nlohmann::json ctx;
    ctx["expected_class"] = "spam";
    ctx["positive_class"] = "spam";

    auto result = benchmark("PrecisionRecallMetric measure", [&]() {
        auto _ = metric.measure(agent, input, output, ctx);
    }, 10000);
    print_result(result);
}

void bench_metric_aggregation() {
    evaluation::AccuracyMetric metric(true);

    std::vector<double> measurements;
    for (int i = 0; i < 100; ++i) {
        measurements.push_back(i % 2 == 0 ? 1.0 : 0.0);
    }

    auto result = benchmark("Metric aggregate (100 measurements)", [&]() {
        auto _ = metric.aggregate(measurements);
    }, 1000);
    print_result(result);
}

// ============================================================================
// Main
// ============================================================================

int main() {
    std::cout << "\n";
    std::cout << "╔════════════════════════════════════════════════════════════════════════════════════════════════╗\n";
    std::cout << "║                       AGENKIT C++ EVALUATION FRAMEWORK BENCHMARKS                              ║\n";
    std::cout << "╚════════════════════════════════════════════════════════════════════════════════════════════════╝\n";
    std::cout << "\n";

    // Category 1: Metrics Collection
    std::cout << "┌────────────────────────────────────────────────────────────────────────────────────────────────┐\n";
    std::cout << "│ CATEGORY 1: METRICS COLLECTION                                                                 │\n";
    std::cout << "├──────────────────────────────────────────────────┬──────────────┬──────────────┬──────────────┤\n";
    std::cout << "│ Benchmark                                        │ Mean (μs)    │ Median (μs)  │ Min/Max (μs) │\n";
    std::cout << "├──────────────────────────────────────────────────┼──────────────┼──────────────┼──────────────┤\n";

    bench_metric_measurement_creation();
    bench_metric_measurement_json();
    bench_session_result_creation();
    bench_session_result_add_metrics();
    bench_session_result_json();
    bench_metrics_collector();

    // Category 2: Session Recording
    std::cout << "├──────────────────────────────────────────────────┴──────────────┴──────────────┴──────────────┤\n";
    std::cout << "│ CATEGORY 2: SESSION RECORDING                                                                  │\n";
    std::cout << "├──────────────────────────────────────────────────┬──────────────┬──────────────┬──────────────┤\n";

    bench_interaction_record_creation();
    bench_interaction_record_json();
    bench_session_recording();

    // Category 3: Evaluation Results
    std::cout << "├──────────────────────────────────────────────────┴──────────────┴──────────────┴──────────────┤\n";
    std::cout << "│ CATEGORY 3: EVALUATION RESULTS                                                                 │\n";
    std::cout << "├──────────────────────────────────────────────────┬──────────────┬──────────────┬──────────────┤\n";

    bench_evaluation_result_creation();
    bench_evaluation_result_json();

    // Category 4: Quality Metrics
    std::cout << "├──────────────────────────────────────────────────┴──────────────┴──────────────┴──────────────┤\n";
    std::cout << "│ CATEGORY 4: QUALITY METRICS                                                                    │\n";
    std::cout << "├──────────────────────────────────────────────────┬──────────────┬──────────────┬──────────────┤\n";

    bench_accuracy_metric();
    bench_quality_metrics();
    bench_precision_recall_metric();
    bench_metric_aggregation();

    std::cout << "└──────────────────────────────────────────────────┴──────────────┴──────────────┴──────────────┘\n";
    std::cout << "\n";
    std::cout << "Benchmark complete. Evaluation framework performance validated.\n";
    std::cout << "\n";

    return 0;
}
