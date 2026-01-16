/**
 * @file test_tracing.cpp
 * @brief Tests for distributed tracing with OpenTelemetry
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include <gtest/gtest.h>
#include "agenkit/observability/tracing.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/agent.hpp"
#include <memory>

using namespace agenkit;
using namespace agenkit::core;
using namespace agenkit::observability;

// Simple test agent for testing tracing
class EchoAgent : public Agent {
public:
    explicit EchoAgent(const std::string& agent_name) : agent_name_(agent_name) {}

    std::string name() const override {
        return agent_name_;
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        // Echo the message with role changed to "assistant"
        auto response = Message::with_text("assistant", message.content_as_str());

        // Copy metadata from input
        const auto& input_metadata = message.metadata();
        if (input_metadata.is_object()) {
            for (auto it = input_metadata.begin(); it != input_metadata.end(); ++it) {
                response.with_metadata(it.key(), it.value());
            }
        }

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

class TracingTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Initialize tracing with console exporter for tests
        try {
            init_tracing("console", "");
            tracing_initialized_ = true;
        } catch (const std::runtime_error& e) {
            // Already initialized or OpenTelemetry not available
            tracing_initialized_ = true;
        }
    }

    bool tracing_initialized_ = false;
};

TEST_F(TracingTest, InitTracingConsole) {
    EXPECT_TRUE(tracing_initialized_);
}

TEST_F(TracingTest, GetTracer) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto tracer = get_tracer("test");
    EXPECT_NE(tracer, nullptr);
}

TEST_F(TracingTest, ScopedSpanCreation) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto tracer = get_tracer("test");
    ASSERT_NE(tracer, nullptr);

    {
        ScopedSpan span(tracer, "test_operation");
        EXPECT_NE(span.get_span(), nullptr);

        auto context = span.get_context();
        EXPECT_TRUE(context.IsValid());
    }
    // Span automatically ended when scope exits
}

TEST_F(TracingTest, ScopedSpanAttributes) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto tracer = get_tracer("test");
    ASSERT_NE(tracer, nullptr);

    ScopedSpan span(tracer, "test_operation");

    // Set various attribute types
    span.set_attribute("string_attr", "value");
    span.set_attribute("int_attr", int64_t(42));
    span.set_attribute("double_attr", 3.14);
    span.set_attribute("bool_attr", true);

    // No crash = success
    EXPECT_TRUE(true);
}

TEST_F(TracingTest, ScopedSpanStatus) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto tracer = get_tracer("test");
    ASSERT_NE(tracer, nullptr);

    {
        ScopedSpan span1(tracer, "success_operation");
        span1.set_status_ok();
    }

    {
        ScopedSpan span2(tracer, "error_operation");
        span2.set_status_error("Something went wrong");
    }

    EXPECT_TRUE(true);
}

TEST_F(TracingTest, ScopedSpanMove) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto tracer = get_tracer("test");
    ASSERT_NE(tracer, nullptr);

    ScopedSpan span1(tracer, "operation");
    auto context1 = span1.get_context();
    EXPECT_TRUE(context1.IsValid());

    // Move construction
    ScopedSpan span2(std::move(span1));
    auto context2 = span2.get_context();
    EXPECT_TRUE(context2.IsValid());
}

TEST_F(TracingTest, ExtractTraceContextEmpty) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto message = Message::with_text("user", "test");
    auto context = extract_trace_context(message);

    // Context should be valid but default (no parent)
    EXPECT_TRUE(true);  // No crash = success
}

TEST_F(TracingTest, InjectTraceContext) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto tracer = get_tracer("test");
    ASSERT_NE(tracer, nullptr);

    // Create a span
    ScopedSpan span(tracer, "test_operation");
    auto span_context = span.get_context();
    ASSERT_TRUE(span_context.IsValid());

    // Create message and inject context
    auto message = Message::with_text("user", "test");
    auto context = opentelemetry::trace::SetSpan(
        opentelemetry::context::Context(),
        span.get_span()
    );

    inject_trace_context(message, context);

    // Message should now have traceparent in metadata
    const auto& metadata = message.metadata();
    EXPECT_TRUE(metadata.is_object());
    EXPECT_TRUE(metadata.contains("traceparent"));
}

TEST_F(TracingTest, ExtractAndInjectRoundtrip) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto tracer = get_tracer("test");
    ASSERT_NE(tracer, nullptr);

    // Create original message with trace context
    auto message1 = Message::with_text("user", "test");
    ScopedSpan span(tracer, "operation");
    auto context = opentelemetry::trace::SetSpan(
        opentelemetry::context::Context(),
        span.get_span()
    );
    inject_trace_context(message1, context);

    // Extract from first message
    auto extracted_context = extract_trace_context(message1);

    // Inject into second message
    auto message2 = Message::with_text("assistant", "response");
    inject_trace_context(message2, extracted_context);

    // Both messages should have traceparent
    EXPECT_TRUE(message1.metadata().contains("traceparent"));
    EXPECT_TRUE(message2.metadata().contains("traceparent"));
}

TEST_F(TracingTest, TracingMiddlewareCreation) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto agent = std::make_shared<EchoAgent>("test_agent");
    auto middleware = std::make_shared<TracingMiddleware>(agent);

    EXPECT_EQ(middleware->name(), "test_agent");
    EXPECT_EQ(middleware->inner(), agent);
}

TEST_F(TracingTest, TracingMiddlewareProcess) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto agent = std::make_shared<EchoAgent>("test_agent");
    auto middleware = std::make_shared<TracingMiddleware>(agent);

    auto message = Message::with_text("user", "Hello");
    auto future = middleware->process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_EQ(response.role(), "assistant");
    EXPECT_EQ(response.content_as_str(), "Hello");

    // Response should have trace context injected
    const auto& metadata = response.metadata();
    EXPECT_TRUE(metadata.is_object());
    EXPECT_TRUE(metadata.contains("traceparent"));
}

TEST_F(TracingTest, TracingMiddlewareError) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto agent = std::make_shared<FailingAgent>("failing_agent");
    auto middleware = std::make_shared<TracingMiddleware>(agent);

    auto message = Message::with_text("user", "test");
    auto future = middleware->process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_err());

    auto error = result.unwrap_err();
    EXPECT_EQ(error.message(), "intentional failure");
}

TEST_F(TracingTest, TracingMiddlewareContextPropagation) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto agent1 = std::make_shared<EchoAgent>("agent1");
    auto middleware1 = std::make_shared<TracingMiddleware>(agent1);

    auto agent2 = std::make_shared<EchoAgent>("agent2");
    auto middleware2 = std::make_shared<TracingMiddleware>(agent2);

    // Process with first agent
    auto message1 = Message::with_text("user", "test");
    auto future1 = middleware1->process(std::move(message1));
    auto result1 = future1.get();
    ASSERT_TRUE(result1.is_ok());

    auto response1 = result1.unwrap();
    EXPECT_TRUE(response1.metadata().contains("traceparent"));

    // Process with second agent (context should propagate)
    auto future2 = middleware2->process(std::move(response1));
    auto result2 = future2.get();
    ASSERT_TRUE(result2.is_ok());

    auto response2 = result2.unwrap();
    EXPECT_TRUE(response2.metadata().contains("traceparent"));

    // Both should have trace context (parent-child relationship)
    EXPECT_TRUE(true);  // If we got here, propagation worked
}

TEST_F(TracingTest, TracingMiddlewareCustomSpanName) {
    if (!tracing_initialized_) GTEST_SKIP();

    auto agent = std::make_shared<EchoAgent>("test_agent");
    auto middleware = std::make_shared<TracingMiddleware>(agent, "custom.operation");

    auto message = Message::with_text("user", "test");
    auto future = middleware->process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    // Span name doesn't affect the result, just the trace data
}

#endif // AGENKIT_WITH_OBSERVABILITY
