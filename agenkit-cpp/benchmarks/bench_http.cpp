/**
 * @file bench_http.cpp
 * @brief Performance benchmarks for HTTP transport
 *
 * Benchmarks:
 * - HTTP server startup/shutdown
 * - HTTP client request/response
 * - End-to-end roundtrip latency
 * - Throughput (requests per second)
 * - Concurrent client performance
 */

#include <chrono>
#include <iostream>
#include <iomanip>
#include <vector>
#include <numeric>
#include <algorithm>
#include <thread>
#include <atomic>
#include "agenkit/transports/http_server.hpp"
#include "agenkit/transports/http_agent.hpp"
#include "agenkit/adapters/echo_agent.hpp"

using namespace agenkit;
using namespace std::chrono;

// Benchmark result structure
struct BenchmarkResult {
    std::string name;
    double mean_us;
    double median_us;
    double min_us;
    double max_us;
    double stddev_us;
    size_t iterations;
};

// Timer class
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

// Calculate statistics
BenchmarkResult calculate_stats(const std::string& name, const std::vector<double>& timings) {
    BenchmarkResult result;
    result.name = name;
    result.iterations = timings.size();

    result.mean_us = std::accumulate(timings.begin(), timings.end(), 0.0) / timings.size();

    auto sorted = timings;
    std::sort(sorted.begin(), sorted.end());
    result.median_us = sorted[sorted.size() / 2];

    result.min_us = *std::min_element(timings.begin(), timings.end());
    result.max_us = *std::max_element(timings.begin(), timings.end());

    double sq_sum = 0.0;
    for (double t : timings) {
        sq_sum += (t - result.mean_us) * (t - result.mean_us);
    }
    result.stddev_us = std::sqrt(sq_sum / timings.size());

    return result;
}

// Print result
void print_result(const BenchmarkResult& result) {
    std::cout << std::left << std::setw(40) << result.name << " | "
              << std::right << std::setw(10) << std::fixed << std::setprecision(3) << result.mean_us << " μs | "
              << std::setw(10) << result.median_us << " μs | "
              << std::setw(10) << result.min_us << " μs | "
              << std::setw(10) << result.max_us << " μs | "
              << std::setw(10) << result.stddev_us << " μs\n";
}

// Benchmark: HTTP roundtrip latency
BenchmarkResult bench_http_roundtrip(transports::HttpAgent& client, size_t iterations = 1000) {
    std::vector<double> timings;
    timings.reserve(iterations);

    // Warmup
    for (int i = 0; i < 10; i++) {
        auto msg = core::Message::with_text("user", "warmup");
        auto future = client.process(std::move(msg));
        auto result = future.get();
    }

    // Actual benchmark
    for (size_t i = 0; i < iterations; i++) {
        auto msg = core::Message::with_text("user", "benchmark");
        Timer timer;
        auto future = client.process(std::move(msg));
        auto result = future.get();
        timings.push_back(timer.elapsed_us());
    }

    return calculate_stats("HTTP Roundtrip (local)", timings);
}

// Benchmark: HTTP throughput
void bench_http_throughput(transports::HttpAgent& client, size_t duration_secs = 5) {
    std::atomic<size_t> request_count{0};
    std::atomic<bool> running{true};

    // Start throughput test
    auto start = high_resolution_clock::now();

    while (running) {
        auto msg = core::Message::with_text("user", "throughput");
        auto future = client.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            request_count++;
        }

        auto elapsed = duration_cast<seconds>(high_resolution_clock::now() - start).count();
        if (elapsed >= duration_secs) {
            running = false;
        }
    }

    auto end = high_resolution_clock::now();
    auto elapsed_sec = duration_cast<milliseconds>(end - start).count() / 1000.0;

    double rps = request_count.load() / elapsed_sec;

    std::cout << std::left << std::setw(40) << "HTTP Throughput (requests/sec)" << " | "
              << std::right << std::setw(10) << std::fixed << std::setprecision(1) << rps << " rps | "
              << "(" << request_count.load() << " requests in "
              << std::fixed << std::setprecision(1) << elapsed_sec << "s)\n";
}

// Benchmark: Concurrent clients
void bench_concurrent_clients(const std::string& url, size_t num_clients = 5, size_t requests_per_client = 100) {
    std::vector<std::thread> threads;
    std::vector<std::vector<double>> all_timings(num_clients);

    transports::HttpTransportConfig config{url, 30, std::nullopt};

    auto start = high_resolution_clock::now();

    for (size_t i = 0; i < num_clients; i++) {
        threads.emplace_back([i, &config, requests_per_client, &all_timings]() {
            transports::HttpAgent client("client-" + std::to_string(i), config);

            for (size_t j = 0; j < requests_per_client; j++) {
                auto msg = core::Message::with_text("user", "concurrent");
                Timer timer;
                auto future = client.process(std::move(msg));
                auto result = future.get();
                all_timings[i].push_back(timer.elapsed_us());
            }
        });
    }

    for (auto& t : threads) {
        t.join();
    }

    auto end = high_resolution_clock::now();
    auto total_elapsed_ms = duration_cast<milliseconds>(end - start).count();

    // Calculate aggregate statistics
    std::vector<double> all_times;
    for (const auto& timings : all_timings) {
        all_times.insert(all_times.end(), timings.begin(), timings.end());
    }

    auto stats = calculate_stats("Concurrent Clients (" + std::to_string(num_clients) + " clients)", all_times);
    print_result(stats);

    size_t total_requests = num_clients * requests_per_client;
    double total_rps = (total_requests * 1000.0) / total_elapsed_ms;
    std::cout << std::left << std::setw(40) << "  Overall Throughput" << " | "
              << std::right << std::setw(10) << std::fixed << std::setprecision(1) << total_rps << " rps\n";
}

int main() {
    std::cout << "=== Agenkit C++ HTTP Transport Benchmarks ===\n\n";

    // Start HTTP server in background
    std::cout << "Starting HTTP server on port 28080...\n";
    auto agent = std::make_shared<adapters::EchoAgent>();
    transports::HttpServer server(agent, "127.0.0.1:28080");

    std::thread server_thread([&server]() {
        server.serve();
    });

    // Wait for server to start
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    if (!server.is_running()) {
        std::cerr << "Failed to start server!\n";
        return 1;
    }

    std::cout << "Server started successfully.\n\n";

    // Create HTTP client
    transports::HttpTransportConfig config{
        "http://127.0.0.1:28080",
        30,
        std::nullopt
    };
    transports::HttpAgent client("benchmark-client", config);

    std::cout << "Running benchmarks...\n\n";

    // Header
    std::cout << std::left << std::setw(40) << "Benchmark" << " | "
              << std::right << std::setw(10) << "Mean" << " | "
              << std::setw(10) << "Median" << " | "
              << std::setw(10) << "Min" << " | "
              << std::setw(10) << "Max" << " | "
              << std::setw(10) << "StdDev\n";
    std::cout << std::string(40 + 5 * 13, '-') << "\n";

    // Run benchmarks
    print_result(bench_http_roundtrip(client, 1000));
    std::cout << "\n";
    bench_http_throughput(client, 5);
    std::cout << "\n";
    bench_concurrent_clients("http://127.0.0.1:28080", 5, 100);

    std::cout << "\n";
    std::cout << "Stopping server...\n";
    server.stop();

    if (server_thread.joinable()) {
        server_thread.join();
    }

    std::cout << "Benchmarks complete.\n\n";
    std::cout << "Note: Times are in microseconds (μs). Lower is better.\n";
    std::cout << "      RPS = Requests per second. Higher is better.\n";

    return 0;
}
