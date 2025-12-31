/**
 * @file test_router.cpp
 * @brief Comprehensive tests for Router pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/router.hpp"
#include "test_pattern_helpers.hpp"
#include <memory>
#include <string>
#include <stdexcept>
#include <unordered_map>

using namespace agenkit;
using namespace agenkit::test;

// Mock classifier for testing
class MockClassifier : public patterns::ClassifierAgent {
private:
    std::string name_;
    std::string category_;
    bool should_fail_;
    core::AgentError error_;

public:
    MockClassifier(const std::string& name, const std::string& category)
        : name_(name)
        , category_(category)
        , should_fail_(false)
        , error_(core::AgentErrorType::Internal, "")
    {}

    void set_category(const std::string& category) {
        category_ = category;
    }

    void set_error(const core::AgentError& error) {
        should_fail_ = true;
        error_ = error;
    }

    std::string name() const override {
        return name_;
    }

    std::vector<std::string> capabilities() const override {
        return {"classification"};
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        auto msg = core::Message::with_text("assistant", "classifier response");
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }

    core::Result<std::string, core::AgentError>
    classify(const core::Message& /* message */) override {
        if (should_fail_) {
            return core::Result<std::string, core::AgentError>::err(error_);
        }
        return core::Result<std::string, core::AgentError>::ok(category_);
    }
};

// Test: Valid construction
TEST(RouterAgentTest, Constructor) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "billing");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["billing"] = make_mock_agent("billing", "billing response");
    agents["technical"] = make_mock_agent("technical", "tech response");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    EXPECT_EQ(router.name(), "router");
}

// Test: Constructor with null classifier
TEST(RouterAgentTest, ConstructorNullClassifier) {
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["billing"] = make_mock_agent("billing");

    patterns::RouterConfig config{nullptr, agents, std::nullopt};

    EXPECT_THROW(
        {
            patterns::RouterAgent router(config);
        },
        std::invalid_argument
    );
}

// Test: Constructor with empty agents
TEST(RouterAgentTest, ConstructorEmptyAgents) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "billing");
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;

    patterns::RouterConfig config{classifier, agents, std::nullopt};

    EXPECT_THROW(
        {
            patterns::RouterAgent router(config);
        },
        std::invalid_argument
    );
}

// Test: Constructor with invalid default key
TEST(RouterAgentTest, ConstructorInvalidDefaultKey) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "billing");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["agent1"] = make_mock_agent("agent1");

    patterns::RouterConfig config{classifier, agents, "nonexistent"};

    EXPECT_THROW(
        {
            patterns::RouterAgent router(config);
        },
        std::invalid_argument
    );
}

// Test: Basic routing
TEST(RouterAgentTest, BasicRouting) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "billing");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["billing"] = make_mock_agent("billing", "billing handled");
    agents["technical"] = make_mock_agent("technical", "tech handled");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "I have a billing question");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "billing handled");
}

// Test: Routing metadata
TEST(RouterAgentTest, RoutingMetadata) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "support");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["support"] = make_mock_agent("support_agent", "support response");
    agents["sales"] = make_mock_agent("sales_agent", "sales response");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "help me");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    expect_metadata_exists(response, "routed_category");
    expect_metadata_value<std::string>(response, "routed_category", "support");

    expect_metadata_exists(response, "routed_agent");
    expect_metadata_value<std::string>(response, "routed_agent", "support_agent");

    expect_metadata_exists(response, "available_routes");
    expect_metadata_value<int>(response, "available_routes", 2);
}

// Test: Classification error
TEST(RouterAgentTest, ClassificationError) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "billing");
    classifier->set_error(core::AgentError(core::AgentErrorType::Internal, "classification failed"));

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["agent"] = make_mock_agent("agent");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("classification failed") != std::string::npos);
}

// Test: Unknown category without default
TEST(RouterAgentTest, UnknownCategoryNoDefault) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "unknown_category");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["known1"] = make_mock_agent("known1");
    agents["known2"] = make_mock_agent("known2");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("unknown_category") != std::string::npos ||
                error.message().find("not found") != std::string::npos);
}

// Test: Unknown category with default
TEST(RouterAgentTest, UnknownCategoryWithDefault) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "unknown_category");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["default_agent"] = make_mock_agent("default", "default handled");
    agents["known1"] = make_mock_agent("known1");

    patterns::RouterConfig config{classifier, agents, "default_agent"};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "default handled");
}

// Test: Agent execution error
TEST(RouterAgentTest, AgentExecutionError) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "failing");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["failing"] = make_failing_mock_agent("failing", "agent failed");
    agents["working"] = make_mock_agent("working");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("agent failed") != std::string::npos);
}

// Test: Multiple routes available
TEST(RouterAgentTest, MultipleRoutesAvailable) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "route3");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["route1"] = make_mock_agent("r1", "response1");
    agents["route2"] = make_mock_agent("r2", "response2");
    agents["route3"] = make_mock_agent("r3", "response3");
    agents["route4"] = make_mock_agent("r4", "response4");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "response3");

    expect_metadata_value<int>(response, "available_routes", 4);
}

// Test: Capabilities aggregation
TEST(RouterAgentTest, Capabilities) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "agent1");

    auto agent1 = make_mock_agent("agent1");
    agent1->set_capabilities({"cap1", "cap2"});

    auto agent2 = make_mock_agent("agent2");
    agent2->set_capabilities({"cap3"});

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["agent1"] = agent1;
    agents["agent2"] = agent2;

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto caps = router.capabilities();

    // Should have routing capability plus unique agent capabilities
    bool has_routing = false;
    for (const auto& cap : caps) {
        if (cap == "router") {
            has_routing = true;
        }
    }

    EXPECT_TRUE(has_routing);
}

// Test: Dynamic routing based on content
TEST(RouterAgentTest, DynamicRouting) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "technical");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["billing"] = make_mock_agent("billing", "billing response");
    agents["technical"] = make_mock_agent("technical", "technical response");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    // First message
    auto msg1 = core::Message::with_text("user", "technical issue");
    auto result1 = router.process(std::move(msg1)).get();

    ASSERT_TRUE(result1.is_ok());
    EXPECT_EQ(result1.unwrap().content_as_str(), "technical response");

    // Change classification for second message
    classifier->set_category("billing");

    auto msg2 = core::Message::with_text("user", "billing question");
    auto result2 = router.process(std::move(msg2)).get();

    ASSERT_TRUE(result2.is_ok());
    EXPECT_EQ(result2.unwrap().content_as_str(), "billing response");
}

// Test: Single route
TEST(RouterAgentTest, SingleRoute) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "only");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["only"] = make_mock_agent("only", "only response");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "only response");
}

// Test: Many routes
TEST(RouterAgentTest, ManyRoutes) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "route15");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    const int num_routes = 20;

    for (int i = 0; i < num_routes; ++i) {
        std::string name = "route" + std::to_string(i);
        agents[name] = make_mock_agent(name, "response" + std::to_string(i));
    }

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "response15");

    expect_metadata_value<int>(response, "available_routes", num_routes);
}

// Test: Empty message handling
TEST(RouterAgentTest, EmptyMessage) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "agent");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["agent"] = make_mock_agent("agent", "response");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "");
    auto result = router.process(std::move(msg)).get();

    // Should still process successfully
    ASSERT_TRUE(result.is_ok());
}

// Test: Case sensitivity in routing
TEST(RouterAgentTest, CaseSensitiveRouting) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "BILLING");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["billing"] = make_mock_agent("billing", "lowercase");
    agents["BILLING"] = make_mock_agent("BILLING", "uppercase");

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "uppercase");
}

// Test: Default route metadata
TEST(RouterAgentTest, DefaultRouteMetadata) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "unknown");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["default"] = make_mock_agent("default", "default response");
    agents["specific"] = make_mock_agent("specific");

    patterns::RouterConfig config{classifier, agents, "default"};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
}

// Test: Classification preserves original message
TEST(RouterAgentTest, ClassificationPreservesMessage) {
    auto classifier = std::make_shared<MockClassifier>("classifier", "agent");

    // Create agent that checks message content
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& msg) -> core::Result<core::Message, core::AgentError> {
            std::string content = msg.content_as_str();
            std::string response = "received: " + content;
            return core::Result<core::Message, core::AgentError>::ok(
                core::Message::with_text("assistant", response)
            );
        }
    );

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    agents["agent"] = agent;

    patterns::RouterConfig config{classifier, agents, std::nullopt};
    patterns::RouterAgent router(config);

    auto msg = core::Message::with_text("user", "original message");
    auto result = router.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "received: original message");
}
