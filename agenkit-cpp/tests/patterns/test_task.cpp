/**
 * @file test_task.cpp
 * @brief Tests for Task pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/task.hpp"
#include <memory>
#include <thread>

using namespace agenkit;

// Mock agent for testing
class MockAgent : public core::Agent {
private:
    std::string response_;
    std::chrono::milliseconds delay_;
    bool should_fail_;
    int call_count_;

public:
    MockAgent(
        const std::string& response = "Mock response",
        std::chrono::milliseconds delay = std::chrono::milliseconds(0),
        bool should_fail = false
    ) : response_(response), delay_(delay), should_fail_(should_fail), call_count_(0) {}

    std::string name() const override { return "mock_agent"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        call_count_++;

        // Simulate delay
        if (delay_.count() > 0) {
            std::this_thread::sleep_for(delay_);
        }

        if (should_fail_) {
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(
                    core::AgentError(core::AgentErrorType::Internal, "Mock failure")
                )
            );
        }

        auto msg = core::Message::with_text("assistant", response_);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }

    int get_call_count() const { return call_count_; }
};

// Test: Basic task execution
TEST(TaskTest, BasicExecution) {
    auto agent = std::make_shared<MockAgent>("Response");
    patterns::Task task(agent);

    auto msg = core::Message::with_text("user", "Test");
    auto result = task.execute(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.unwrap().content_as_str(), "Response");
    EXPECT_TRUE(task.is_completed());
}

// Test: Cannot execute twice
TEST(TaskTest, CannotExecuteTwice) {
    auto agent = std::make_shared<MockAgent>();
    patterns::Task task(agent);

    auto msg1 = core::Message::with_text("user", "Test 1");
    task.execute(std::move(msg1)).get();

    auto msg2 = core::Message::with_text("user", "Test 2");
    EXPECT_THROW(task.execute(std::move(msg2)), std::runtime_error);
}

// Test: Retry on failure
TEST(TaskTest, RetryOnFailure) {
    auto agent = std::make_shared<MockAgent>("Success", std::chrono::milliseconds(0), true);

    patterns::TaskConfig config;
    config.retries = 2; // Total 3 attempts
    config.retry_delay = std::chrono::milliseconds(10);

    patterns::Task task(agent, config);

    auto msg = core::Message::with_text("user", "Test");
    auto result = task.execute(std::move(msg)).get();

    // Should fail after all retries
    ASSERT_TRUE(result.is_err());
    EXPECT_EQ(agent->get_call_count(), 3); // 1 + 2 retries
}

// Test: Successful retry
TEST(TaskTest, SuccessfulRetry) {
    // Agent that fails first time, succeeds second time
    class FailThenSucceedAgent : public core::Agent {
    private:
        int call_count_;

    public:
        FailThenSucceedAgent() : call_count_(0) {}

        std::string name() const override { return "fail_then_succeed"; }

        std::future<core::Result<core::Message, core::AgentError>>
        process(core::Message /* message */) override {
            call_count_++;

            if (call_count_ == 1) {
                return core::make_ready_future(
                    core::Result<core::Message, core::AgentError>::err(
                        core::AgentError(core::AgentErrorType::Internal, "First attempt fails")
                    )
                );
            }

            auto msg = core::Message::with_text("assistant", "Success on retry");
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::ok(msg)
            );
        }

        int get_call_count() const { return call_count_; }
    };

    auto agent = std::make_shared<FailThenSucceedAgent>();

    patterns::TaskConfig config;
    config.retries = 2;
    config.retry_delay = std::chrono::milliseconds(10);

    patterns::Task task(agent, config);

    auto msg = core::Message::with_text("user", "Test");
    auto result = task.execute(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.unwrap().content_as_str(), "Success on retry");
    EXPECT_EQ(agent->get_call_count(), 2); // Failed once, succeeded second time
}

// Note: Timeout tests are commented out because std::future::wait_for()
// does not actually cancel the underlying operation in C++. It only checks
// if the future is ready. True async cancellation would require more complex
// infrastructure like std::stop_token (C++20) or platform-specific APIs.

// Test: Timeout configuration is accepted
TEST(TaskTest, TimeoutConfig) {
    auto agent = std::make_shared<MockAgent>();

    patterns::TaskConfig config;
    config.timeout = std::chrono::milliseconds(1000);

    patterns::Task task(agent, config);

    EXPECT_EQ(task.get_config().timeout.count(), 1000);
}

// Test: Get result
TEST(TaskTest, GetResult) {
    auto agent = std::make_shared<MockAgent>("Test response");
    patterns::Task task(agent);

    EXPECT_FALSE(task.get_result().has_value());

    auto msg = core::Message::with_text("user", "Test");
    task.execute(std::move(msg)).get();

    ASSERT_TRUE(task.get_result().has_value());
    EXPECT_EQ(task.get_result().value().content_as_str(), "Test response");
}

// Test: Get result on failure
TEST(TaskTest, GetResultOnFailure) {
    auto agent = std::make_shared<MockAgent>("Response", std::chrono::milliseconds(0), true);
    patterns::Task task(agent);

    auto msg = core::Message::with_text("user", "Test");
    task.execute(std::move(msg)).get();

    // Result should not be set on failure
    EXPECT_FALSE(task.get_result().has_value());
}

// Test: Is completed
TEST(TaskTest, IsCompleted) {
    auto agent = std::make_shared<MockAgent>();
    patterns::Task task(agent);

    EXPECT_FALSE(task.is_completed());

    auto msg = core::Message::with_text("user", "Test");
    task.execute(std::move(msg)).get();

    EXPECT_TRUE(task.is_completed());
}

// Test: Get/set config
TEST(TaskTest, GetConfig) {
    auto agent = std::make_shared<MockAgent>();

    patterns::TaskConfig config;
    config.timeout = std::chrono::milliseconds(5000);
    config.retries = 3;
    config.retry_delay = std::chrono::milliseconds(200);

    patterns::Task task(agent, config);

    auto retrieved = task.get_config();
    EXPECT_EQ(retrieved.timeout.count(), 5000);
    EXPECT_EQ(retrieved.retries, 3);
    EXPECT_EQ(retrieved.retry_delay.count(), 200);
}

// Test: Null agent error
TEST(TaskTest, NullAgentError) {
    EXPECT_THROW(
        patterns::Task(nullptr),
        std::invalid_argument
    );
}

// Test: Zero retries means one attempt
TEST(TaskTest, ZeroRetriesMeansOneAttempt) {
    auto agent = std::make_shared<MockAgent>("Response", std::chrono::milliseconds(0), true);

    patterns::TaskConfig config;
    config.retries = 0; // No retries

    patterns::Task task(agent, config);

    auto msg = core::Message::with_text("user", "Test");
    task.execute(std::move(msg)).get();

    EXPECT_EQ(agent->get_call_count(), 1); // Only one attempt
}

// Test: Cleanup is called
TEST(TaskTest, CleanupCalled) {
    class CleanupTrackingTask : public patterns::Task {
    public:
        mutable bool cleanup_called = false;

        CleanupTrackingTask(std::shared_ptr<core::Agent> agent)
            : Task(agent) {}

        void cleanup() override {
            cleanup_called = true;
            Task::cleanup();
        }
    };

    auto agent = std::make_shared<MockAgent>();
    CleanupTrackingTask task(agent);

    EXPECT_FALSE(task.cleanup_called);

    auto msg = core::Message::with_text("user", "Test");
    task.execute(std::move(msg)).get();

    EXPECT_TRUE(task.cleanup_called);
}
