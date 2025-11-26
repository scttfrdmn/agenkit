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
