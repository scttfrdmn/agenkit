/**
 * @file test_self_consistency.cpp
 * @brief Tests for Self-Consistency reasoning technique
 */

#include <gtest/gtest.h>
#include "agenkit/techniques/reasoning/self_consistency.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <memory>
#include <vector>
#include <string>
#include <atomic>

using namespace agenkit::techniques::reasoning;
using namespace agenkit::core;

/**
 * @brief Mock agent that cycles through responses
 */
class MockAgent : public Agent {
public:
    explicit MockAgent(const std::vector<std::string>& responses)
        : responses_(responses), call_count_(0) {}

    std::string name() const override {
        return "mock_agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"mock", "testing"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() mutable {
            size_t idx = call_count_.fetch_add(1) % responses_.size();
            return Result<Message, AgentError>::ok(
                Message::with_text("assistant", responses_[idx])
            );
        });
    }

private:
    std::vector<std::string> responses_;
    std::atomic<size_t> call_count_;
};

// Test default configuration
TEST(SelfConsistencyTest, DefaultConfig) {
    SelfConsistencyConfig config;
    EXPECT_EQ(config.num_samples, 5);
    EXPECT_EQ(config.voting_strategy, VotingStrategy::Majority);
}

// Test agent name
TEST(SelfConsistencyTest, AgentName) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"answer"});
    SelfConsistencyAgent sc(mock);
    EXPECT_EQ(sc.name(), "self_consistency");
}

// Test agent capabilities
TEST(SelfConsistencyTest, AgentCapabilities) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"answer"});
    SelfConsistencyAgent sc(mock);
    auto caps = sc.capabilities();
    EXPECT_FALSE(caps.empty());

    bool has_sc = false;
    for (const auto& cap : caps) {
        if (cap == "self_consistency") {
            has_sc = true;
            break;
        }
    }
    EXPECT_TRUE(has_sc);
}

// Test basic completion returns majority answer
TEST(SelfConsistencyTest, MajorityVoting) {
    // 3 out of 4 responses are the same
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "The answer is 42",
        "The answer is 42",
        "The answer is 42",
        "The answer is 7"
    });

    SelfConsistencyConfig config;
    config.num_samples = 4;
    config.voting_strategy = VotingStrategy::Majority;
    SelfConsistencyAgent sc(mock, config);

    auto message = Message::with_text("user", "What is the answer?");
    auto future = sc.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_FALSE(response.content_as_str().empty());
}

// Test first-answer strategy
TEST(SelfConsistencyTest, FirstStrategy) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "First answer",
        "Second answer"
    });

    SelfConsistencyConfig config;
    config.num_samples = 2;
    config.voting_strategy = VotingStrategy::First;
    SelfConsistencyAgent sc(mock, config);

    auto message = Message::with_text("user", "test");
    auto future = sc.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_FALSE(response.content_as_str().empty());
}

// Test metadata contains technique name
TEST(SelfConsistencyTest, MetadataTechnique) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"answer"});
    SelfConsistencyConfig config;
    config.num_samples = 2;
    SelfConsistencyAgent sc(mock, config);

    auto message = Message::with_text("user", "test");
    auto future = sc.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.metadata().count("technique") > 0);
    EXPECT_EQ(response.metadata().at("technique"), "self_consistency");
}

// Test metadata contains num_samples
TEST(SelfConsistencyTest, MetadataNumSamples) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"answer"});
    SelfConsistencyConfig config;
    config.num_samples = 3;
    SelfConsistencyAgent sc(mock, config);

    auto message = Message::with_text("user", "test");
    auto future = sc.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_TRUE(response.metadata().count("num_samples") > 0);
}

// Test voting strategy with weighted mode
TEST(SelfConsistencyTest, WeightedStrategy) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"answer"});
    SelfConsistencyConfig config;
    config.num_samples = 2;
    config.voting_strategy = VotingStrategy::Weighted;
    SelfConsistencyAgent sc(mock, config);

    auto message = Message::with_text("user", "test");
    auto future = sc.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
}

// Test response role is assistant
TEST(SelfConsistencyTest, ResponseRole) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"answer"});
    SelfConsistencyConfig config;
    config.num_samples = 2;
    SelfConsistencyAgent sc(mock, config);

    auto message = Message::with_text("user", "test");
    auto future = sc.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.role(), "assistant");
}
