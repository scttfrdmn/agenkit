/**
 * @file batching_example.cpp
 * @brief Demonstrates batching middleware usage and patterns
 *
 * This example shows:
 * 1. Basic batching setup and configuration
 * 2. Batch size trigger (max_batch_size)
 * 3. Wait time trigger (max_wait_time)
 * 4. Queue size limiting and backpressure
 * 5. Metrics tracking and analysis
 * 6. Concurrent request handling
 * 7. Performance comparison (batched vs unbatched)
 */

#include <agenkit/middleware/batching.hpp>
#include <agenkit/core/agent.hpp>
#include <agenkit/core/message.hpp>
#include <iostream>
#include <iomanip>
#include <chrono>
#include <thread>
#include <vector>
#include <atomic>

using namespace agenkit;
using namespace agenkit::middleware;
using namespace agenkit::core;

void print_separator() {
    std::cout << "\n" << std::string(70, '=') << "\n\n";
}

void print_metrics(const BatchingMetrics& metrics) {
    std::cout << "  Metrics:\n";
    std::cout << "    Total requests:      " << metrics.total_requests.load() << "\n";
    std::cout << "    Total batches:       " << metrics.total_batches.load() << "\n";
    std::cout << "    Successful batches:  " << metrics.successful_batches.load() << "\n";
    std::cout << "    Failed batches:      " << metrics.failed_batches.load() << "\n";
    std::cout << "    Partial batches:     " << metrics.partial_batches.load() << "\n";
    std::cout << "    Min batch size:      " << metrics.min_batch_size.load() << "\n";
    std::cout << "    Max batch size:      " << metrics.max_batch_size.load() << "\n";
    std::cout << "    Avg batch size:      " << std::fixed << std::setprecision(2)
              << metrics.avg_batch_size() << "\n";
    std::cout << "    Avg wait time:       " << std::fixed << std::setprecision(2)
              << metrics.avg_wait_time_ms() << " ms\n";
    std::cout << "    Throughput boost:    " << std::fixed << std::setprecision(2)
              << metrics.throughput_improvement() << "x\n";
}

/// Simulated LLM agent with processing delay
class LLMAgent : public Agent {
public:
    LLMAgent(std::chrono::milliseconds processing_time = std::chrono::milliseconds(100))
        : processing_time_(processing_time) {}

    std::string name() const override {
        return "llm_agent";
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        request_count_.fetch_add(1);

        // Simulate LLM processing time
        std::this_thread::sleep_for(processing_time_);

        auto response = Message::with_text(
            "assistant",
            "Response to: " + message.content_as_str()
        );

        return make_ready_future(Result<Message, AgentError>::ok(response));
    }

    int request_count() const { return request_count_.load(); }
    void reset_count() { request_count_.store(0); }

private:
    std::chrono::milliseconds processing_time_;
    std::atomic<int> request_count_{0};
};

void example_batch_size_trigger() {
    std::cout << "=== Batch Size Trigger Example ===\n\n";

    auto agent = std::make_shared<LLMAgent>(std::chrono::milliseconds(50));

    auto config = BatchingConfig::builder()
        .max_batch_size(5)
        .max_wait_time(std::chrono::seconds(10))  // Long timeout
        .max_queue_size(100)
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(agent, config);

    std::cout << "Configuration:\n";
    std::cout << "  max_batch_size:  " << config.max_batch_size << "\n";
    std::cout << "  max_wait_time:   " << config.max_wait_time.count() << " ms\n";
    std::cout << "  max_queue_size:  " << config.max_queue_size << "\n\n";

    std::cout << "Sending exactly 5 requests (batch size = 5)...\n";
    auto start = std::chrono::steady_clock::now();

    std::vector<std::future<Result<Message, AgentError>>> futures;
    for (int i = 0; i < 5; i++) {
        auto msg = Message::with_text("user", "Request " + std::to_string(i));
        futures.push_back(batching->process(std::move(msg)));
    }

    // Wait for all responses
    int successes = 0;
    for (auto& fut : futures) {
        auto result = fut.get();
        if (result.is_ok()) {
            successes++;
        }
    }

    auto elapsed = std::chrono::steady_clock::now() - start;
    auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();

    std::cout << "\n  Result:\n";
    std::cout << "    Successes:     " << successes << "/" << futures.size() << "\n";
    std::cout << "    Time:          " << elapsed_ms << " ms\n";
    std::cout << "    Agent calls:   " << agent->request_count() << "\n\n";

    // Wait for batch processing to complete
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    print_metrics(batching->metrics());
}

void example_wait_time_trigger() {
    std::cout << "\n=== Wait Time Trigger Example ===\n\n";

    auto agent = std::make_shared<LLMAgent>(std::chrono::milliseconds(50));

    auto config = BatchingConfig::builder()
        .max_batch_size(10)
        .max_wait_time(std::chrono::milliseconds(100))
        .max_queue_size(100)
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(agent, config);

    std::cout << "Configuration:\n";
    std::cout << "  max_batch_size:  " << config.max_batch_size << "\n";
    std::cout << "  max_wait_time:   " << config.max_wait_time.count() << " ms\n\n";

    std::cout << "Sending 3 requests (less than batch size)...\n";
    std::cout << "Batch will trigger after wait time expires.\n";

    auto start = std::chrono::steady_clock::now();

    std::vector<std::future<Result<Message, AgentError>>> futures;
    for (int i = 0; i < 3; i++) {
        auto msg = Message::with_text("user", "Request " + std::to_string(i));
        futures.push_back(batching->process(std::move(msg)));
    }

    // Wait for all responses
    int successes = 0;
    for (auto& fut : futures) {
        auto result = fut.get();
        if (result.is_ok()) {
            successes++;
        }
    }

    auto elapsed = std::chrono::steady_clock::now() - start;
    auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();

    std::cout << "\n  Result:\n";
    std::cout << "    Successes:     " << successes << "/" << futures.size() << "\n";
    std::cout << "    Time:          " << elapsed_ms << " ms\n";
    std::cout << "    Agent calls:   " << agent->request_count() << "\n";
    std::cout << "\n  Note: Requests waited ~" << config.max_wait_time.count()
              << " ms for batch timer\n\n";

    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    print_metrics(batching->metrics());
}

void example_concurrent_requests() {
    std::cout << "\n=== Concurrent Requests Example ===\n\n";

    auto agent = std::make_shared<LLMAgent>(std::chrono::milliseconds(30));

    auto config = BatchingConfig::builder()
        .max_batch_size(10)
        .max_wait_time(std::chrono::milliseconds(50))
        .max_queue_size(100)
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(agent, config);

    std::cout << "Launching 50 concurrent requests...\n";
    std::cout << "Batch size: " << config.max_batch_size << "\n\n";

    auto start = std::chrono::steady_clock::now();

    std::vector<std::thread> threads;
    std::atomic<int> success_count{0};

    for (int i = 0; i < 50; i++) {
        threads.emplace_back([&batching, &success_count, i]() {
            auto msg = Message::with_text("user", "Request " + std::to_string(i));
            auto result = batching->process(std::move(msg)).get();
            if (result.is_ok()) {
                success_count.fetch_add(1);
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    auto elapsed = std::chrono::steady_clock::now() - start;
    auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();

    std::cout << "  Result:\n";
    std::cout << "    Successes:     " << success_count.load() << "/50\n";
    std::cout << "    Time:          " << elapsed_ms << " ms\n";
    std::cout << "    Agent calls:   " << agent->request_count() << "\n\n";

    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    print_metrics(batching->metrics());
}

void example_backpressure() {
    std::cout << "\n=== Backpressure Example ===\n\n";

    auto agent = std::make_shared<LLMAgent>(std::chrono::milliseconds(100));

    auto config = BatchingConfig::builder()
        .max_batch_size(5)
        .max_wait_time(std::chrono::milliseconds(50))
        .max_queue_size(10)  // Small queue
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(agent, config);

    std::cout << "Configuration:\n";
    std::cout << "  max_batch_size:  " << config.max_batch_size << "\n";
    std::cout << "  max_queue_size:  " << config.max_queue_size << " (small)\n\n";

    std::cout << "Rapidly sending 30 requests to small queue...\n";

    std::atomic<int> accepted{0};
    std::atomic<int> rejected{0};

    std::vector<std::future<Result<Message, AgentError>>> futures;
    for (int i = 0; i < 30; i++) {
        auto msg = Message::with_text("user", "Request " + std::to_string(i));
        futures.push_back(batching->process(std::move(msg)));
    }

    for (auto& fut : futures) {
        auto result = fut.get();
        if (result.is_ok()) {
            accepted.fetch_add(1);
        } else {
            rejected.fetch_add(1);
        }
    }

    std::cout << "\n  Result:\n";
    std::cout << "    Accepted:      " << accepted.load() << "\n";
    std::cout << "    Rejected:      " << rejected.load() << " (queue full)\n";
    std::cout << "    Agent calls:   " << agent->request_count() << "\n\n";

    std::cout << "  Note: Rejected requests received immediate error response\n";
    std::cout << "        without waiting or consuming resources.\n\n";

    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    print_metrics(batching->metrics());
}

void example_performance_comparison() {
    std::cout << "\n=== Performance Comparison ===\n\n";

    auto processing_time = std::chrono::milliseconds(50);
    int num_requests = 20;

    // Unbatched version
    std::cout << "Testing unbatched agent...\n";
    auto unbatched = std::make_shared<LLMAgent>(processing_time);

    auto start = std::chrono::steady_clock::now();

    for (int i = 0; i < num_requests; i++) {
        auto msg = Message::with_text("user", "Request " + std::to_string(i));
        auto result = unbatched->process(std::move(msg)).get();
    }

    auto unbatched_time = std::chrono::steady_clock::now() - start;
    auto unbatched_ms = std::chrono::duration_cast<std::chrono::milliseconds>(unbatched_time).count();

    std::cout << "  Time: " << unbatched_ms << " ms\n\n";

    // Batched version
    std::cout << "Testing batched agent...\n";
    auto batched_inner = std::make_shared<LLMAgent>(processing_time);

    auto config = BatchingConfig::builder()
        .max_batch_size(10)
        .max_wait_time(std::chrono::milliseconds(50))
        .build();

    auto batched = std::make_shared<BatchingMiddleware>(batched_inner, config);

    start = std::chrono::steady_clock::now();

    std::vector<std::future<Result<Message, AgentError>>> futures;
    for (int i = 0; i < num_requests; i++) {
        auto msg = Message::with_text("user", "Request " + std::to_string(i));
        futures.push_back(batched->process(std::move(msg)));
    }

    for (auto& fut : futures) {
        fut.get();
    }

    auto batched_time = std::chrono::steady_clock::now() - start;
    auto batched_ms = std::chrono::duration_cast<std::chrono::milliseconds>(batched_time).count();

    std::cout << "  Time: " << batched_ms << " ms\n\n";

    // Wait for batch processing
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    // Results
    std::cout << "  Comparison:\n";
    std::cout << "    Unbatched:     " << unbatched_ms << " ms\n";
    std::cout << "    Batched:       " << batched_ms << " ms\n";
    std::cout << "    Speedup:       " << std::fixed << std::setprecision(2)
              << (double)unbatched_ms / batched_ms << "x\n\n";

    print_metrics(batched->metrics());

    std::cout << "\n  Note: Batching enables parallel processing, reducing overall\n";
    std::cout << "        latency when the agent can handle concurrent requests.\n";
}

int main() {
    std::cout << "Batching Middleware Examples\n";
    std::cout << "============================\n\n";

    try {
        example_batch_size_trigger();
        print_separator();

        example_wait_time_trigger();
        print_separator();

        example_concurrent_requests();
        print_separator();

        example_backpressure();
        print_separator();

        example_performance_comparison();
        print_separator();

        std::cout << "All examples completed successfully!\n\n";
        std::cout << "Key Takeaways:\n";
        std::cout << "1. Batching reduces overhead by processing multiple requests together\n";
        std::cout << "2. max_batch_size controls maximum batch size\n";
        std::cout << "3. max_wait_time ensures latency bounds for small batches\n";
        std::cout << "4. max_queue_size provides backpressure protection\n";
        std::cout << "5. Comprehensive metrics enable monitoring and tuning\n";
        std::cout << "6. Parallel processing within batches improves throughput\n\n";

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}
