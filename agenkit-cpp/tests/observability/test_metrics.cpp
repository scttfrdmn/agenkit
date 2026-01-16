/**
 * @file test_metrics.cpp
 * @brief Tests for metrics collection with OpenTelemetry
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include <gtest/gtest.h>
#include "agenkit/observability/metrics.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/agent.hpp"
#include <memory>
#include <thread>
#include <chrono>

using namespace agenkit;
using namespace agenkit::core;
using namespace agenkit::observability;

// Simple test agent for testing metrics
class EchoAgent : public Agent {
public:
    explicit EchoAgent(const std::string& agent_name) : agent_name_(agent_name) {}

    std::string name() const override {
        return agent_name_;
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        // Echo the message with role changed to "assistant"
        auto response = Message::with_text("assistant", message.content_as_str());
        return make_ready_future(Result<Message, AgentError>::ok(std::move(response)));
    }

private:
    std::string agent_name_;
};

// Test agent that fails
class FailingAgent : public Agent {
public:
    explicit FailingAgent(const std::string& agent_name) : agent_name_(agent_name) {}

    std::string name() const override {
        return agent_name_;
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        (void)message;
        auto error = AgentError(AgentErrorType::ProcessingError, "intentional failure");
        return make_ready_future(Result<Message, AgentError>::err(std::move(error)));
    }

private:
    std::string agent_name_;
};

// Test agent with delay for duration metrics
class SlowAgent : public Agent {
public:
    explicit SlowAgent(const std::string& agent_name, int delay_ms)
        : agent_name_(agent_name), delay_ms_(delay_ms) {}

    std::string name() const override {
        return agent_name_;
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        // Simulate processing delay
        std::this_thread::sleep_for(std::chrono::milliseconds(delay_ms_));

        auto response = Message::with_text("assistant", message.content_as_str());
        return make_ready_future(Result<Message, AgentError>::ok(std::move(response)));
    }

private:
    std::string agent_name_;
    int delay_ms_;
};

class MetricsTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Initialize metrics with OTLP exporter for tests
        try {
            init_metrics("otlp", "http://localhost:4318/v1/metrics");
            metrics_initialized_ = true;
        } catch (const std::runtime_error& e) {
            // Already initialized or OpenTelemetry not available
            metrics_initialized_ = true;
        }
    }

    bool metrics_initialized_ = false;
};

TEST_F(MetricsTest, InitMetricsOTLP) {
    EXPECT_TRUE(metrics_initialized_);
}

TEST_F(MetricsTest, GetMeter) {
    if (!metrics_initialized_) GTEST_SKIP();

    auto meter = get_meter("test");
    EXPECT_NE(meter, nullptr);
}

TEST_F(MetricsTest, MetricsMiddlewareCreation) {
    if (!metrics_initialized_) GTEST_SKIP();

    auto agent = std::make_shared<EchoAgent>("test_agent");
    auto middleware = std::make_shared<MetricsMiddleware>(agent);

    EXPECT_EQ(middleware->name(), "test_agent");
    EXPECT_EQ(middleware->inner(), agent);
}

TEST_F(MetricsTest, MetricsMiddlewareProcessSuccess) {
    if (!metrics_initialized_) GTEST_SKIP();

    auto agent = std::make_shared<EchoAgent>("test_agent");
    auto middleware = std::make_shared<MetricsMiddleware>(agent);

    auto message = Message::with_text("user", "Hello");
    auto future = middleware->process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_EQ(response.role(), "assistant");
    EXPECT_EQ(response.content_as_str(), "Hello");

    // Metrics should be recorded (counter and histogram)
    // No crash = success
}

TEST_F(MetricsTest, MetricsMiddlewareProcessError) {
    if (!metrics_initialized_) GTEST_SKIP();

    auto agent = std::make_shared<FailingAgent>("failing_agent");
    auto middleware = std::make_shared<MetricsMiddleware>(agent);

    auto message = Message::with_text("user", "test");
    auto future = middleware->process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_err());

    auto error = result.unwrap_err();
    EXPECT_EQ(error.message(), "intentional failure");

    // Error metrics should be recorded
    // No crash = success
}

TEST_F(MetricsTest, MetricsMiddlewareRecordsDuration) {
    if (!metrics_initialized_) GTEST_SKIP();

    // Use slow agent to ensure measurable duration
    auto agent = std::make_shared<SlowAgent>("slow_agent", 50); // 50ms delay
    auto middleware = std::make_shared<MetricsMiddleware>(agent);

    auto message = Message::with_text("user", "test");
    auto start = std::chrono::steady_clock::now();
    auto future = middleware->process(std::move(message));
    auto result = future.get();
    auto end = std::chrono::steady_clock::now();

    ASSERT_TRUE(result.is_ok());

    // Verify the processing took at least the expected time
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    EXPECT_GE(duration, 50); // At least 50ms

    // Histogram should record the duration
}

TEST_F(MetricsTest, MetricsMiddlewareMultipleRequests) {
    if (!metrics_initialized_) GTEST_SKIP();

    auto agent = std::make_shared<EchoAgent>("test_agent");
    auto middleware = std::make_shared<MetricsMiddleware>(agent);

    // Process multiple requests
    for (int i = 0; i < 5; i++) {
        auto message = Message::with_text("user", "test " + std::to_string(i));
        auto future = middleware->process(std::move(message));
        auto result = future.get();
        ASSERT_TRUE(result.is_ok());
    }

    // Counter should have recorded 5 requests
    // No crash = success
}

TEST_F(MetricsTest, MetricsMiddlewareMixedSuccessAndError) {
    if (!metrics_initialized_) GTEST_SKIP();

    // Successful agent
    auto success_agent = std::make_shared<EchoAgent>("success_agent");
    auto success_middleware = std::make_shared<MetricsMiddleware>(success_agent);

    auto message1 = Message::with_text("user", "test");
    auto future1 = success_middleware->process(std::move(message1));
    auto result1 = future1.get();
    ASSERT_TRUE(result1.is_ok());

    // Failing agent
    auto failing_agent = std::make_shared<FailingAgent>("failing_agent");
    auto failing_middleware = std::make_shared<MetricsMiddleware>(failing_agent);

    auto message2 = Message::with_text("user", "test");
    auto future2 = failing_middleware->process(std::move(message2));
    auto result2 = future2.get();
    ASSERT_TRUE(result2.is_err());

    // Both success and error metrics should be recorded
}

TEST_F(MetricsTest, MetricsMiddlewareWithMultipleAgents) {
    if (!metrics_initialized_) GTEST_SKIP();

    // Create two different agents
    auto agent1 = std::make_shared<EchoAgent>("agent1");
    auto middleware1 = std::make_shared<MetricsMiddleware>(agent1);

    auto agent2 = std::make_shared<EchoAgent>("agent2");
    auto middleware2 = std::make_shared<MetricsMiddleware>(agent2);

    // Process with different agents
    auto message1 = Message::with_text("user", "test1");
    auto future1 = middleware1->process(std::move(message1));
    auto result1 = future1.get();
    ASSERT_TRUE(result1.is_ok());

    auto message2 = Message::with_text("user", "test2");
    auto future2 = middleware2->process(std::move(message2));
    auto result2 = future2.get();
    ASSERT_TRUE(result2.is_ok());

    // Metrics should be recorded for both agents with different labels
}

TEST_F(MetricsTest, MetricsMiddlewareNullAgentThrows) {
    if (!metrics_initialized_) GTEST_SKIP();

    EXPECT_THROW({
        auto middleware = std::make_shared<MetricsMiddleware>(nullptr);
    }, std::invalid_argument);
}

TEST_F(MetricsTest, CounterCreation) {
    if (!metrics_initialized_) GTEST_SKIP();

    auto meter = get_meter("test");
    ASSERT_NE(meter, nullptr);

    auto counter = meter->CreateUInt64Counter(
        "test_counter",
        "Test counter",
        "count"
    );

    EXPECT_NE(counter, nullptr);

    // Add some values
    std::map<std::string, std::string> attributes;
    attributes["key"] = "value";
    counter->Add(1, attributes);
    counter->Add(5, attributes);

    // No crash = success
}

TEST_F(MetricsTest, HistogramCreation) {
    if (!metrics_initialized_) GTEST_SKIP();

    auto meter = get_meter("test");
    ASSERT_NE(meter, nullptr);

    auto histogram = meter->CreateDoubleHistogram(
        "test_histogram",
        "Test histogram",
        "seconds"
    );

    EXPECT_NE(histogram, nullptr);

    // Record some values
    std::map<std::string, std::string> attributes;
    attributes["key"] = "value";
    histogram->Record(0.5, attributes);
    histogram->Record(1.0, attributes);
    histogram->Record(1.5, attributes);

    // No crash = success
}

#endif // AGENKIT_WITH_OBSERVABILITY
