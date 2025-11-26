/**
 * @file bench_core.cpp
 * @brief Performance benchmarks for core components
 *
 * Benchmarks:
 * - Message creation and serialization
 * - Agent creation and processing
 * - Result<T,E> operations
 * - Error handling
 */

#include <chrono>
#include <iostream>
#include <iomanip>
#include <vector>
#include <numeric>
#include <algorithm>
#include "agenkit/core/message.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/core/errors.hpp"

using namespace agenkit;
using namespace std::chrono;

// Benchmark result structure
struct BenchmarkResult {
    std::string name;
    double mean_us;      // Mean time in microseconds
    double median_us;    // Median time in microseconds
    double min_us;       // Min time in microseconds
    double max_us;       // Max time in microseconds
    double stddev_us;    // Standard deviation in microseconds
    size_t iterations;
};

// Timer class for precise measurements
class Timer {
public:
    Timer() : start_(high_resolution_clock::now()) {}

    double elapsed_us() const {
        auto end = high_resolution_clock::now();
        return duration_cast<microseconds>(end - start_).count();
    }

    void reset() {
        start_ = high_resolution_clock::now();
    }

private:
    high_resolution_clock::time_point start_;
};

// Calculate statistics from timings
BenchmarkResult calculate_stats(const std::string& name, const std::vector<double>& timings) {
    BenchmarkResult result;
    result.name = name;
    result.iterations = timings.size();

    // Mean
    result.mean_us = std::accumulate(timings.begin(), timings.end(), 0.0) / timings.size();

    // Median
    auto sorted = timings;
    std::sort(sorted.begin(), sorted.end());
    result.median_us = sorted[sorted.size() / 2];

    // Min/Max
    result.min_us = *std::min_element(timings.begin(), timings.end());
    result.max_us = *std::max_element(timings.begin(), timings.end());

    // Standard deviation
    double sq_sum = 0.0;
    for (double t : timings) {
        sq_sum += (t - result.mean_us) * (t - result.mean_us);
    }
    result.stddev_us = std::sqrt(sq_sum / timings.size());

    return result;
}

// Print benchmark result
void print_result(const BenchmarkResult& result) {
    std::cout << std::left << std::setw(40) << result.name << " | "
              << std::right << std::setw(10) << std::fixed << std::setprecision(3) << result.mean_us << " μs | "
              << std::setw(10) << result.median_us << " μs | "
              << std::setw(10) << result.min_us << " μs | "
              << std::setw(10) << result.max_us << " μs | "
              << std::setw(10) << result.stddev_us << " μs\n";
}

// Benchmark: Message creation
BenchmarkResult bench_message_creation(size_t iterations = 100000) {
    std::vector<double> timings;
    timings.reserve(iterations);

    for (size_t i = 0; i < iterations; i++) {
        Timer timer;
        auto msg = core::Message::with_text("user", "Hello, world!");
        timings.push_back(timer.elapsed_us());
    }

    return calculate_stats("Message Creation", timings);
}

// Benchmark: Message with metadata
BenchmarkResult bench_message_with_metadata(size_t iterations = 100000) {
    std::vector<double> timings;
    timings.reserve(iterations);

    for (size_t i = 0; i < iterations; i++) {
        Timer timer;
        auto msg = core::Message::with_text("user", "Hello!");
        msg.with_metadata("key1", "value1")
           .with_metadata("key2", 42)
           .with_metadata("key3", nlohmann::json::array({"a", "b", "c"}));
        timings.push_back(timer.elapsed_us());
    }

    return calculate_stats("Message with Metadata", timings);
}

// Benchmark: Message serialization
BenchmarkResult bench_message_serialization(size_t iterations = 100000) {
    auto msg = core::Message::with_text("user", "Benchmark message");
    msg.with_metadata("session_id", "test123")
       .with_metadata("priority", 5);

    std::vector<double> timings;
    timings.reserve(iterations);

    for (size_t i = 0; i < iterations; i++) {
        Timer timer;
        auto json = msg.to_json();
        timings.push_back(timer.elapsed_us());
    }

    return calculate_stats("Message Serialization", timings);
}

// Benchmark: Message deserialization
BenchmarkResult bench_message_deserialization(size_t iterations = 100000) {
    auto msg = core::Message::with_text("user", "Benchmark message");
    msg.with_metadata("session_id", "test123");
    auto json = msg.to_json();

    std::vector<double> timings;
    timings.reserve(iterations);

    for (size_t i = 0; i < iterations; i++) {
        Timer timer;
        auto deserialized = core::Message::from_json(json);
        timings.push_back(timer.elapsed_us());
    }

    return calculate_stats("Message Deserialization", timings);
}

// Benchmark: Agent creation
BenchmarkResult bench_agent_creation(size_t iterations = 100000) {
    std::vector<double> timings;
    timings.reserve(iterations);

    for (size_t i = 0; i < iterations; i++) {
        Timer timer;
        adapters::EchoAgent agent;
        timings.push_back(timer.elapsed_us());
    }

    return calculate_stats("Agent Creation", timings);
}

// Benchmark: Agent processing (echo)
BenchmarkResult bench_agent_process(size_t iterations = 10000) {
    adapters::EchoAgent agent;

    std::vector<double> timings;
    timings.reserve(iterations);

    for (size_t i = 0; i < iterations; i++) {
        auto msg = core::Message::with_text("user", "Benchmark");
        Timer timer;
        auto future = agent.process(std::move(msg));
        auto result = future.get();
        timings.push_back(timer.elapsed_us());
    }

    return calculate_stats("Agent Process (Echo)", timings);
}

// Benchmark: Result<T,E> ok path
BenchmarkResult bench_result_ok(size_t iterations = 100000) {
    std::vector<double> timings;
    timings.reserve(iterations);

    for (size_t i = 0; i < iterations; i++) {
        Timer timer;
        auto result = core::Result<int, std::string>::ok(42);
        bool is_ok = result.is_ok();
        int value = result.unwrap();
        timings.push_back(timer.elapsed_us());
        (void)is_ok;
        (void)value;
    }

    return calculate_stats("Result<T,E> OK Path", timings);
}

// Benchmark: Result<T,E> error path
BenchmarkResult bench_result_err(size_t iterations = 100000) {
    std::vector<double> timings;
    timings.reserve(iterations);

    for (size_t i = 0; i < iterations; i++) {
        Timer timer;
        auto result = core::Result<int, std::string>::err("error");
        bool is_err = result.is_err();
        auto error = result.unwrap_err();
        timings.push_back(timer.elapsed_us());
        (void)is_err;
        (void)error;
    }

    return calculate_stats("Result<T,E> Error Path", timings);
}

// Benchmark: Error creation
BenchmarkResult bench_error_creation(size_t iterations = 100000) {
    std::vector<double> timings;
    timings.reserve(iterations);

    for (size_t i = 0; i < iterations; i++) {
        Timer timer;
        core::AgentError error(core::AgentErrorType::ProcessingError, "Test error");
        timings.push_back(timer.elapsed_us());
    }

    return calculate_stats("Error Creation", timings);
}

int main() {
    std::cout << "=== Agenkit C++ Core Benchmarks ===\n\n";

    std::cout << "Running benchmarks (this may take a minute)...\n\n";

    // Header
    std::cout << std::left << std::setw(40) << "Benchmark" << " | "
              << std::right << std::setw(10) << "Mean" << " | "
              << std::setw(10) << "Median" << " | "
              << std::setw(10) << "Min" << " | "
              << std::setw(10) << "Max" << " | "
              << std::setw(10) << "StdDev\n";
    std::cout << std::string(40 + 5 * 13, '-') << "\n";

    // Run benchmarks
    print_result(bench_message_creation());
    print_result(bench_message_with_metadata());
    print_result(bench_message_serialization());
    print_result(bench_message_deserialization());
    print_result(bench_agent_creation());
    print_result(bench_agent_process());
    print_result(bench_result_ok());
    print_result(bench_result_err());
    print_result(bench_error_creation());

    std::cout << "\nNote: Times are in microseconds (μs). Lower is better.\n";
    std::cout << "1 millisecond (ms) = 1,000 microseconds (μs)\n";

    return 0;
}
