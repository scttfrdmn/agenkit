/**
 * @file test_agent.cpp
 * @brief Tests for Agent interface and Echo agent
 */

#include <gtest/gtest.h>
#include "agenkit/core/agent.hpp"
#include "agenkit/adapters/echo_agent.hpp"

using namespace agenkit::core;
using namespace agenkit::adapters;

TEST(EchoAgentTest, HasCorrectName) {
    EchoAgent agent;
    EXPECT_EQ(agent.name(), "echo");
}

TEST(EchoAgentTest, EchoesTextMessage) {
    EchoAgent agent;
    auto msg = Message::with_text("user", "Hello, world!");

    auto future = agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.role(), "assistant");
    EXPECT_EQ(response.content_as_str(), "Hello, world!");
}

TEST(EchoAgentTest, EchoesEmptyMessage) {
    EchoAgent agent;
    auto msg = Message::with_text("user", "");

    auto future = agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "");
}

TEST(EchoAgentTest, HasCapabilities) {
    EchoAgent agent;
    auto caps = agent.capabilities();

    EXPECT_EQ(caps.size(), 2);
    EXPECT_EQ(caps[0], "echo");
    EXPECT_EQ(caps[1], "test");
}

TEST(EchoAgentTest, ProcessReturnsImmediately) {
    EchoAgent agent;
    auto msg = Message::with_text("user", "Test");

    auto future = agent.process(std::move(msg));

    // Future should be ready immediately for echo agent
    auto status = future.wait_for(std::chrono::milliseconds(0));
    EXPECT_EQ(status, std::future_status::ready);
}

TEST(MakeReadyFutureTest, CreatesReadyFuture) {
    int value = 42;
    auto future = make_ready_future(value);

    auto status = future.wait_for(std::chrono::milliseconds(0));
    EXPECT_EQ(status, std::future_status::ready);
    EXPECT_EQ(future.get(), 42);
}

TEST(MakeReadyFutureTest, WorksWithMoveOnlyTypes) {
    auto msg = Message::with_text("test", "content");
    auto future = make_ready_future(std::move(msg));

    EXPECT_EQ(future.get().role(), "test");
}

// Agent::introspect() (#850): docs/API.md documented this method on the
// Agent interface for years while the header had no such member. These
// tests confirm the default virtual implementation actually exists and
// returns sensible data for a concrete, production Agent subclass.
TEST(EchoAgentTest, IntrospectReturnsNameAndCapabilities) {
    EchoAgent agent;

    nlohmann::json result = agent.introspect();

    EXPECT_EQ(result["agent_name"], agent.name());
    ASSERT_TRUE(result["capabilities"].is_array());
    std::vector<std::string> expected_caps = agent.capabilities();
    std::vector<std::string> actual_caps =
        result["capabilities"].get<std::vector<std::string>>();
    EXPECT_EQ(actual_caps, expected_caps);
}

TEST(EchoAgentTest, IntrospectDefaultShapeHasEmptyStateAndTimestamp) {
    EchoAgent agent;

    nlohmann::json result = agent.introspect();

    EXPECT_TRUE(result["memory_state"].is_null());
    EXPECT_TRUE(result["internal_state"].is_object());
    EXPECT_TRUE(result["internal_state"].empty());
    EXPECT_TRUE(result["metadata"].is_object());
    EXPECT_TRUE(result["metadata"].empty());

    ASSERT_TRUE(result.contains("timestamp"));
    // ISO 8601 UTC, e.g. "2026-08-08T12:34:56Z" -- must at least parse as a
    // non-empty string in that general shape.
    std::string ts = result["timestamp"].get<std::string>();
    EXPECT_FALSE(ts.empty());
    EXPECT_EQ(ts.back(), 'Z');
}
