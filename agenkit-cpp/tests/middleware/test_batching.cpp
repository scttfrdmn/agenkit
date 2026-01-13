/**
 * @file test_batching.cpp
 * @brief Comprehensive tests for Batching middleware
 */

#include <gtest/gtest.h>
#include "agenkit/middleware/batching.hpp"
#include "../patterns/test_pattern_helpers.hpp"
#include <memory>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <atomic>

using namespace agenkit;
using namespace agenkit::test;
using namespace agenkit::middleware;

// Test: Valid configuration with builder
TEST(BatchingConfigTest, BuilderValidConfiguration) {
    auto config = BatchingConfig::builder()
        .max_batch_size(20)
        .max_wait_time(std::chrono::milliseconds(200))
        .max_queue_size(500)
        .build();

    EXPECT_EQ(config.max_batch_size, 20);
    EXPECT_EQ(config.max_wait_time.count(), 200);
    EXPECT_EQ(config.max_queue_size, 500);
}

// Test: Default configuration values
TEST(BatchingConfigTest, DefaultConfiguration) {
    BatchingConfig config;
    EXPECT_EQ(config.max_batch_size, 10);
    EXPECT_EQ(config.max_wait_time.count(), 100);
    EXPECT_EQ(config.max_queue_size, 1000);
}

// Test: Invalid configuration - batch size too small
TEST(BatchingConfigTest, InvalidBatchSize) {
    EXPECT_THROW(
        {
            auto config = BatchingConfig::builder()
                .max_batch_size(0)
                .build();
        },
        std::invalid_argument
    );
}

// Test: Invalid configuration - wait time negative
TEST(BatchingConfigTest, InvalidWaitTime) {
    EXPECT_THROW(
        {
            auto config = BatchingConfig::builder()
                .max_wait_time(std::chrono::milliseconds(-1))
                .build();
        },
        std::invalid_argument
    );
}

// Test: Invalid configuration - queue smaller than batch
TEST(BatchingConfigTest, InvalidQueueSize) {
    EXPECT_THROW(
        {
            auto config = BatchingConfig::builder()
                .max_batch_size(20)
                .max_queue_size(10)
                .build();
        },
        std::invalid_argument
    );
}

// Test: Single request processing
TEST(BatchingMiddlewareTest, SingleRequest) {
    auto inner = std::make_shared<MockAgent>("test_agent", "response");
    auto config = BatchingConfig::builder()
        .max_batch_size(5)
        .max_wait_time(std::chrono::milliseconds(100))
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    auto msg = core::Message::with_text("user", "test");
    auto result = batching->process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "response");

    // Wait for batch processing
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    const auto& metrics = batching->metrics();
    EXPECT_EQ(metrics.total_requests.load(), 1);
    EXPECT_GE(metrics.total_batches.load(), 1);
}

// Test: Batch size trigger
TEST(BatchingMiddlewareTest, BatchSizeTrigger) {
    auto inner = std::make_shared<MockAgent>("test_agent", "response");
    auto config = BatchingConfig::builder()
        .max_batch_size(5)
        .max_wait_time(std::chrono::seconds(10))  // Long timeout
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    // Send exactly max_batch_size requests
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    for (int i = 0; i < 5; ++i) {
        auto msg = core::Message::with_text("user", "test " + std::to_string(i));
        futures.push_back(batching->process(std::move(msg)));
    }

    // All should complete quickly (not waiting for timeout)
    for (auto& fut : futures) {
        auto result = fut.get();
        ASSERT_TRUE(result.is_ok());
    }

    // Wait for metrics update
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    const auto& metrics = batching->metrics();
    EXPECT_EQ(metrics.total_requests.load(), 5);
    EXPECT_GE(metrics.total_batches.load(), 1);
}

// Test: Wait time trigger
TEST(BatchingMiddlewareTest, WaitTimeTrigger) {
    auto inner = std::make_shared<MockAgent>("test_agent", "response");
    auto config = BatchingConfig::builder()
        .max_batch_size(100)  // High limit
        .max_wait_time(std::chrono::milliseconds(150))
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    // Send just 3 requests (less than batch size)
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    for (int i = 0; i < 3; ++i) {
        auto msg = core::Message::with_text("user", "test " + std::to_string(i));
        futures.push_back(batching->process(std::move(msg)));
    }

    // Should complete after wait time expires
    for (auto& fut : futures) {
        auto result = fut.get();
        ASSERT_TRUE(result.is_ok());
    }

    const auto& metrics = batching->metrics();
    EXPECT_EQ(metrics.total_requests.load(), 3);
    EXPECT_GE(metrics.total_batches.load(), 1);
}

// Test: Concurrent requests batching
TEST(BatchingMiddlewareTest, ConcurrentRequests) {
    auto inner = std::make_shared<MockAgent>("test_agent", "response");
    auto config = BatchingConfig::builder()
        .max_batch_size(10)
        .max_wait_time(std::chrono::milliseconds(100))
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    // Launch 20 concurrent requests
    std::vector<std::thread> threads;
    std::atomic<int> success_count{0};

    for (int i = 0; i < 20; ++i) {
        threads.emplace_back([&batching, &success_count, i]() {
            auto msg = core::Message::with_text("user", "test " + std::to_string(i));
            auto result = batching->process(std::move(msg)).get();
            if (result.is_ok()) {
                success_count.fetch_add(1);
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    EXPECT_EQ(success_count.load(), 20);

    // Wait for final batch
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    const auto& metrics = batching->metrics();
    EXPECT_EQ(metrics.total_requests.load(), 20);
    EXPECT_GE(metrics.total_batches.load(), 2);  // Should have 2 batches
}

// Test: Queue size limit (backpressure)
TEST(BatchingMiddlewareTest, QueueSizeLimit) {
    // Create slow agent to fill queue
    auto inner = std::make_shared<MockAgent>("slow_agent", "response");
    inner->set_delay(std::chrono::milliseconds(100));

    auto config = BatchingConfig::builder()
        .max_batch_size(5)
        .max_wait_time(std::chrono::milliseconds(50))
        .max_queue_size(10)  // Small queue
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    // Fill queue beyond capacity
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    std::atomic<int> rejected_count{0};

    for (int i = 0; i < 20; ++i) {
        auto msg = core::Message::with_text("user", "test " + std::to_string(i));
        futures.push_back(batching->process(std::move(msg)));
    }

    // Check that some were rejected
    for (auto& fut : futures) {
        auto result = fut.get();
        if (result.is_err()) {
            auto error = result.unwrap_err();
            EXPECT_EQ(error.type(), core::AgentErrorType::Internal);
            rejected_count.fetch_add(1);
        }
    }

    EXPECT_GT(rejected_count.load(), 0);
}

// Test: Parallel batch processing
TEST(BatchingMiddlewareTest, ParallelProcessing) {
    // Agent with artificial delay
    auto inner = std::make_shared<MockAgent>("slow_agent", "response");
    inner->set_delay(std::chrono::milliseconds(50));

    auto config = BatchingConfig::builder()
        .max_batch_size(10)
        .max_wait_time(std::chrono::milliseconds(100))
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    // Send 10 requests to fill a batch
    auto start = std::chrono::steady_clock::now();
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;

    for (int i = 0; i < 10; ++i) {
        auto msg = core::Message::with_text("user", "test " + std::to_string(i));
        futures.push_back(batching->process(std::move(msg)));
    }

    // Wait for all to complete
    for (auto& fut : futures) {
        auto result = fut.get();
        ASSERT_TRUE(result.is_ok());
    }

    auto elapsed = std::chrono::steady_clock::now() - start;
    auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();

    // If sequential: 10 * 50ms = 500ms
    // If parallel: ~50-100ms (plus overhead)
    // Allow up to 300ms for parallel execution with overhead
    EXPECT_LT(elapsed_ms, 300);
}

// Test: Metrics tracking
TEST(BatchingMiddlewareTest, MetricsTracking) {
    auto inner = std::make_shared<MockAgent>("test_agent", "response");
    auto config = BatchingConfig::builder()
        .max_batch_size(5)
        .max_wait_time(std::chrono::milliseconds(100))
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    // Process requests in multiple batches
    for (int batch = 0; batch < 3; ++batch) {
        std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
        for (int i = 0; i < 5; ++i) {
            auto msg = core::Message::with_text("user", "test");
            futures.push_back(batching->process(std::move(msg)));
        }
        for (auto& fut : futures) {
            fut.get();
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    // Wait for final batch
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    const auto& metrics = batching->metrics();

    // Verify metrics
    EXPECT_EQ(metrics.total_requests.load(), 15);
    EXPECT_GE(metrics.total_batches.load(), 3);
    EXPECT_GT(metrics.successful_batches.load(), 0);
    EXPECT_EQ(metrics.failed_batches.load(), 0);
    EXPECT_EQ(metrics.partial_batches.load(), 0);

    // Check computed metrics
    EXPECT_GT(metrics.avg_batch_size(), 0.0);
    EXPECT_GE(metrics.avg_wait_time_ms(), 0.0);
    EXPECT_GT(metrics.throughput_improvement(), 1.0);
}

// Test: Min/max batch size tracking
TEST(BatchingMiddlewareTest, MinMaxBatchSize) {
    auto inner = std::make_shared<MockAgent>("test_agent", "response");
    auto config = BatchingConfig::builder()
        .max_batch_size(10)
        .max_wait_time(std::chrono::milliseconds(100))
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    // Send different batch sizes
    // Batch 1: 2 requests
    for (int i = 0; i < 2; ++i) {
        auto msg = core::Message::with_text("user", "test");
        batching->process(std::move(msg));
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(150));

    // Batch 2: 7 requests
    for (int i = 0; i < 7; ++i) {
        auto msg = core::Message::with_text("user", "test");
        batching->process(std::move(msg));
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(150));

    const auto& metrics = batching->metrics();
    EXPECT_LE(metrics.min_batch_size.load(), 2);
    EXPECT_GE(metrics.max_batch_size.load(), 7);
}

// Test: Error handling - agent failure
TEST(BatchingMiddlewareTest, AgentFailure) {
    auto inner = std::make_shared<MockAgent>(
        "failing_agent",
        core::AgentError(core::AgentErrorType::ProcessingError, "agent failed")
    );

    auto config = BatchingConfig::builder()
        .max_batch_size(5)
        .max_wait_time(std::chrono::milliseconds(100))
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    // Send requests
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    for (int i = 0; i < 5; ++i) {
        auto msg = core::Message::with_text("user", "test");
        futures.push_back(batching->process(std::move(msg)));
    }

    // All should fail
    int failures = 0;
    for (auto& fut : futures) {
        auto result = fut.get();
        if (result.is_err()) {
            failures++;
        }
    }

    EXPECT_EQ(failures, 5);

    // Wait for metrics update
    std::this_thread::sleep_for(std::chrono::milliseconds(150));

    const auto& metrics = batching->metrics();
    EXPECT_GT(metrics.failed_batches.load(), 0);
}

// Test: Mixed success/failure (partial batch)
TEST(BatchingMiddlewareTest, PartialBatchSuccess) {
    std::atomic<int> call_count{0};

    // Agent that fails on alternate calls
    auto process_func = [&call_count](const core::Message& msg) -> core::Result<core::Message, core::AgentError> {
        int count = call_count.fetch_add(1);
        if (count % 2 == 0) {
            return core::Result<core::Message, core::AgentError>::ok(
                core::Message::with_text("assistant", "success")
            );
        } else {
            return core::Result<core::Message, core::AgentError>::err(
                core::AgentError(core::AgentErrorType::ProcessingError, "failure")
            );
        }
    };

    auto inner = std::make_shared<MockAgent>("alternating_agent", process_func);

    auto config = BatchingConfig::builder()
        .max_batch_size(10)
        .max_wait_time(std::chrono::milliseconds(100))
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    // Send 10 requests
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    for (int i = 0; i < 10; ++i) {
        auto msg = core::Message::with_text("user", "test");
        futures.push_back(batching->process(std::move(msg)));
    }

    // Count successes and failures
    int successes = 0;
    int failures = 0;
    for (auto& fut : futures) {
        auto result = fut.get();
        if (result.is_ok()) {
            successes++;
        } else {
            failures++;
        }
    }

    EXPECT_EQ(successes, 5);
    EXPECT_EQ(failures, 5);

    // Wait for metrics update
    std::this_thread::sleep_for(std::chrono::milliseconds(150));

    const auto& metrics = batching->metrics();
    EXPECT_GT(metrics.partial_batches.load(), 0);
}

// Test: Graceful shutdown with flush
TEST(BatchingMiddlewareTest, GracefulShutdown) {
    auto inner = std::make_shared<MockAgent>("test_agent", "response");
    auto config = BatchingConfig::builder()
        .max_batch_size(100)  // High limit
        .max_wait_time(std::chrono::seconds(10))  // Long timeout
        .build();

    {
        auto batching = std::make_shared<BatchingMiddleware>(inner, config);

        // Send some requests
        std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
        for (int i = 0; i < 5; ++i) {
            auto msg = core::Message::with_text("user", "test");
            futures.push_back(batching->process(std::move(msg)));
        }

        // Destructor should flush pending items
        // Let batching go out of scope
    }

    // All futures should still be valid and complete
    // (destructor waits for processor thread)
}

// Test: Name forwarding
TEST(BatchingMiddlewareTest, NameForwarding) {
    auto inner = std::make_shared<MockAgent>("custom_agent", "response");
    auto config = BatchingConfig::builder().build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    EXPECT_EQ(batching->name(), "custom_agent");
}

// Test: Configuration access
TEST(BatchingMiddlewareTest, ConfigurationAccess) {
    auto inner = std::make_shared<MockAgent>("test_agent", "response");
    auto config = BatchingConfig::builder()
        .max_batch_size(15)
        .max_wait_time(std::chrono::milliseconds(250))
        .max_queue_size(500)
        .build();

    auto batching = std::make_shared<BatchingMiddleware>(inner, config);

    auto retrieved_config = batching->config();
    EXPECT_EQ(retrieved_config.max_batch_size, 15);
    EXPECT_EQ(retrieved_config.max_wait_time.count(), 250);
    EXPECT_EQ(retrieved_config.max_queue_size, 500);
}
