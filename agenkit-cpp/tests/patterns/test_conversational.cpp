/**
 * @file test_conversational.cpp
 * @brief Tests for Conversational pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/conversational.hpp"
#include <memory>

using namespace agenkit;

// Mock agent for testing
class MockLLMAgent : public core::Agent {
private:
    std::string response_text_;
    int call_count_;

public:
    MockLLMAgent(const std::string& response = "Mock response")
        : response_text_(response), call_count_(0) {}

    std::string name() const override { return "mock_llm"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        call_count_++;

        // Check if conversation history is in metadata
        std::string response = response_text_;
        if (message.metadata().contains("conversation_history")) {
            auto history = message.metadata()["conversation_history"];
            response += " (with " + std::to_string(history.size()) + " messages in history)";
        }

        auto msg = core::Message::with_text("assistant", response);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }

    int get_call_count() const { return call_count_; }
};

// Test: Basic conversation
TEST(ConversationalTest, BasicConversation) {
    auto llm = std::make_shared<MockLLMAgent>("Hello!");
    patterns::ConversationalAgent agent(llm);

    auto msg = core::Message::with_text("user", "Hi");
    auto result = agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.content_as_str().find("Hello!") != std::string::npos);
    EXPECT_EQ(agent.get_context_length(), 2); // User message + assistant response
}

// Test: Multi-turn conversation
TEST(ConversationalTest, MultiTurnConversation) {
    auto llm = std::make_shared<MockLLMAgent>("Response");
    patterns::ConversationalAgent agent(llm);

    // Turn 1
    auto msg1 = core::Message::with_text("user", "Message 1");
    agent.process(std::move(msg1)).get();

    // Turn 2
    auto msg2 = core::Message::with_text("user", "Message 2");
    auto result2 = agent.process(std::move(msg2)).get();

    ASSERT_TRUE(result2.is_ok());
    EXPECT_EQ(agent.get_context_length(), 4); // 2 user + 2 assistant messages
}

// Test: System prompt
TEST(ConversationalTest, SystemPrompt) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalConfig config;
    config.system_prompt = "You are a helpful assistant.";

    patterns::ConversationalAgent agent(llm, config);

    // System prompt should be in history
    EXPECT_EQ(agent.get_context_length(), 1);

    auto history = agent.get_history();
    EXPECT_EQ(history[0].role(), "system");
    EXPECT_EQ(history[0].content_as_str(), "You are a helpful assistant.");
}

// Test: History pruning
TEST(ConversationalTest, HistoryPruning) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalConfig config;
    config.max_history = 4; // Keep only 4 messages

    patterns::ConversationalAgent agent(llm, config);

    // Send 5 messages (10 total with responses)
    for (int i = 0; i < 5; i++) {
        auto msg = core::Message::with_text("user", "Message " + std::to_string(i));
        agent.process(std::move(msg)).get();
    }

    // Should be pruned to max_history
    EXPECT_EQ(agent.get_context_length(), 4);

    // Should keep most recent messages
    auto history = agent.get_history();
    EXPECT_TRUE(history.back().content_as_str().find("with 4 messages") != std::string::npos);
}

// Test: System prompt preservation during pruning
TEST(ConversationalTest, SystemPromptPreservation) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalConfig config;
    config.max_history = 5;
    config.system_prompt = "System prompt";
    config.include_system_in_count = false;

    patterns::ConversationalAgent agent(llm, config);

    // Send many messages
    for (int i = 0; i < 10; i++) {
        auto msg = core::Message::with_text("user", "Message " + std::to_string(i));
        agent.process(std::move(msg)).get();
    }

    // System message should be preserved
    auto history = agent.get_history();
    EXPECT_EQ(history[0].role(), "system");
    EXPECT_EQ(history[0].content_as_str(), "System prompt");

    // Total should be system + max_history conversation messages
    EXPECT_EQ(agent.get_context_length(), 6); // 1 system + 5 conversation
}

// Test: Clear history
TEST(ConversationalTest, ClearHistory) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalConfig config;
    config.system_prompt = "System prompt";

    patterns::ConversationalAgent agent(llm, config);

    // Add some messages
    auto msg = core::Message::with_text("user", "Test");
    agent.process(std::move(msg)).get();

    EXPECT_GT(agent.get_context_length(), 1);

    // Clear but keep system
    agent.clear_history(true);
    EXPECT_EQ(agent.get_context_length(), 1);

    auto history = agent.get_history();
    EXPECT_EQ(history[0].role(), "system");
}

// Test: Clear history without keeping system
TEST(ConversationalTest, ClearHistoryNoSystem) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalConfig config;
    config.system_prompt = "System prompt";

    patterns::ConversationalAgent agent(llm, config);

    auto msg = core::Message::with_text("user", "Test");
    agent.process(std::move(msg)).get();

    // Clear without keeping system
    agent.clear_history(false);
    EXPECT_EQ(agent.get_context_length(), 0);
}

// Test: Export/import history
TEST(ConversationalTest, ExportImportHistory) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalAgent agent(llm);

    // Build some history
    auto msg1 = core::Message::with_text("user", "Message 1");
    agent.process(std::move(msg1)).get();

    auto msg2 = core::Message::with_text("user", "Message 2");
    agent.process(std::move(msg2)).get();

    // Export history
    auto exported = agent.export_history();
    EXPECT_TRUE(exported.is_array());
    EXPECT_EQ(exported.size(), 4); // 2 user + 2 assistant

    // Create new agent and import
    auto llm2 = std::make_shared<MockLLMAgent>();
    patterns::ConversationalAgent agent2(llm2);

    agent2.import_history(exported);
    EXPECT_EQ(agent2.get_context_length(), 4);

    // Verify content
    auto history = agent2.get_history();
    EXPECT_EQ(history[0].content_as_str(), "Message 1");
}

// Test: Get/set config
TEST(ConversationalTest, GetSetConfig) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalConfig config;
    config.max_history = 20;
    config.system_prompt = "Test";

    patterns::ConversationalAgent agent(llm, config);

    auto retrieved = agent.get_config();
    EXPECT_EQ(retrieved.max_history, 20);
    EXPECT_TRUE(retrieved.system_prompt.has_value());
    EXPECT_EQ(retrieved.system_prompt.value(), "Test");

    // Update config
    patterns::ConversationalConfig new_config;
    new_config.max_history = 5;
    agent.set_config(new_config);

    EXPECT_EQ(agent.get_config().max_history, 5);
}

// Test: Capabilities
TEST(ConversationalTest, Capabilities) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalAgent agent(llm);

    auto caps = agent.capabilities();
    EXPECT_EQ(caps.size(), 4);
    EXPECT_EQ(caps[0], "conversation");
    EXPECT_EQ(caps[1], "history");
    EXPECT_EQ(caps[2], "context");
    EXPECT_EQ(caps[3], "multi-turn");
}

// Test: Name
TEST(ConversationalTest, Name) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalAgent agent(llm);

    EXPECT_EQ(agent.name(), "conversational");
}

// Test: Metadata
TEST(ConversationalTest, Metadata) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalAgent agent(llm);

    auto msg = core::Message::with_text("user", "Test");
    auto result = agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.metadata().contains("pattern"));
    EXPECT_EQ(response.metadata()["pattern"], "conversational");
    EXPECT_TRUE(response.metadata().contains("history_length"));
    EXPECT_TRUE(response.metadata().contains("turn"));
}

// Test: Null agent error
TEST(ConversationalTest, NullAgentError) {
    EXPECT_THROW(
        patterns::ConversationalAgent(nullptr),
        std::invalid_argument
    );
}

// Test: Invalid import history
TEST(ConversationalTest, InvalidImportHistory) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalAgent agent(llm);

    // Not an array
    nlohmann::json invalid = nlohmann::json::object();

    EXPECT_THROW(
        agent.import_history(invalid),
        std::invalid_argument
    );
}

// Test: Context message creation
TEST(ConversationalTest, ContextMessageCreation) {
    auto llm = std::make_shared<MockLLMAgent>();
    patterns::ConversationalAgent agent(llm);

    // First message
    auto msg1 = core::Message::with_text("user", "First");
    auto result1 = agent.process(std::move(msg1)).get();
    ASSERT_TRUE(result1.is_ok());

    // Second message should have history context
    // At this point, history has: [user: First, assistant: Mock response]
    auto msg2 = core::Message::with_text("user", "Second");
    auto result2 = agent.process(std::move(msg2)).get();
    ASSERT_TRUE(result2.is_ok());

    auto response = result2.unwrap();
    // After adding "Second", before getting response, history has 3 messages:
    // [user: First, assistant: Mock response, user: Second]
    // But the response will indicate history size when context message was created
    // which includes the user message being processed
    EXPECT_TRUE(response.content_as_str().find("with 3 messages") != std::string::npos);
}
