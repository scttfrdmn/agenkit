/**
 * @file test_budget.cpp
 * @brief Comprehensive tests for budget tracking and cost management
 */

#include <gtest/gtest.h>
#include "agenkit/infrastructure/budget/budget.hpp"
#include <thread>
#include <chrono>

using namespace agenkit::infrastructure::budget;

// ============================================================================
// ModelPricing Tests
// ============================================================================

TEST(ModelPricingTest, GetPricingForKnownModels) {
    ModelPricing pricing;

    auto claude_opus = pricing.get_model_pricing("claude-opus-4");
    EXPECT_EQ(claude_opus.model, "claude-opus-4");
    EXPECT_EQ(claude_opus.provider, "anthropic");
    EXPECT_GT(claude_opus.input_cost_per_million, 0);
    EXPECT_GT(claude_opus.output_cost_per_million, 0);

    auto gpt4o = pricing.get_model_pricing("gpt-4o");
    EXPECT_EQ(gpt4o.provider, "openai");
}

TEST(ModelPricingTest, GetPricingForUnknownModel) {
    ModelPricing pricing;

    auto unknown = pricing.get_model_pricing("unknown-model");
    EXPECT_EQ(unknown.model, "unknown-model");
    EXPECT_EQ(unknown.provider, "unknown");
    // Should return default pricing
}

TEST(ModelPricingTest, ListAllModels) {
    ModelPricing pricing;

    auto models = pricing.list_models();
    EXPECT_GT(models.size(), 0);

    // Check for expected models
    bool has_claude = false;
    bool has_gpt = false;
    for (const auto& model : models) {
        if (model.find("claude") != std::string::npos) has_claude = true;
        if (model.find("gpt") != std::string::npos) has_gpt = true;
    }
    EXPECT_TRUE(has_claude);
    EXPECT_TRUE(has_gpt);
}

TEST(ModelPricingTest, CalculateInputCost) {
    ModelPricing pricing;

    // Test with Claude Sonnet 4
    double cost = pricing.calculate("claude-sonnet-4", 1000, "input");
    EXPECT_GT(cost, 0);
    EXPECT_LT(cost, 1.0);  // 1000 tokens should cost less than $1
}

TEST(ModelPricingTest, CalculateOutputCost) {
    ModelPricing pricing;

    double input_cost = pricing.calculate("claude-sonnet-4", 1000, "input");
    double output_cost = pricing.calculate("claude-sonnet-4", 1000, "output");

    // Output should be more expensive than input
    EXPECT_GT(output_cost, input_cost);
}

TEST(ModelPricingTest, UpdatePricing) {
    ModelPricing pricing;

    pricing.update_pricing("custom-model", 1.0, 2.0);

    auto info = pricing.get_model_pricing("custom-model");
    EXPECT_EQ(info.input_cost_per_million, 1.0);
    EXPECT_EQ(info.output_cost_per_million, 2.0);

    double cost = pricing.calculate("custom-model", 1000000, "input");
    EXPECT_DOUBLE_EQ(cost, 1.0);
}

TEST(ModelPricingTest, EstimateConversationCost) {
    ModelPricing pricing;

    // Estimate 10-turn conversation
    double cost = pricing.estimate_conversation_cost(
        "claude-sonnet-4",
        10,      // turns
        800,     // avg input tokens per turn
        400      // avg output tokens per turn
    );

    EXPECT_GT(cost, 0);

    // More turns should cost more
    double cost_20_turns = pricing.estimate_conversation_cost(
        "claude-sonnet-4", 20, 800, 400
    );
    EXPECT_GT(cost_20_turns, cost * 1.9);  // Should be roughly 2x
}

TEST(ModelPricingTest, CompareModels) {
    ModelPricing pricing;

    std::vector<std::string> models = {
        "claude-haiku-3",
        "claude-sonnet-4",
        "claude-opus-4"
    };

    auto comparison = pricing.compare_models(models, 1000, 500);

    EXPECT_EQ(comparison.size(), 3);
    EXPECT_TRUE(comparison.count("claude-haiku-3") > 0);
    EXPECT_TRUE(comparison.count("claude-sonnet-4") > 0);
    EXPECT_TRUE(comparison.count("claude-opus-4") > 0);

    // Haiku should be cheapest
    EXPECT_LT(comparison["claude-haiku-3"], comparison["claude-opus-4"]);
}

TEST(ModelPricingTest, CompareModelsDetailed) {
    ModelPricing pricing;

    std::vector<std::string> models = {
        "claude-haiku-3",
        "claude-sonnet-4",
        "claude-opus-4"
    };

    auto comparison = pricing.compare_models_detailed(models, 1000, 500);

    ASSERT_EQ(comparison.size(), 3);

    // First entry should be cheapest (sorted by cost)
    EXPECT_EQ(comparison[0].model, "claude-haiku-3");

    // Check cost ratio
    EXPECT_DOUBLE_EQ(comparison[0].cost_ratio, 1.0);  // Cheapest has ratio 1.0
    EXPECT_GT(comparison[1].cost_ratio, 1.0);
    EXPECT_GT(comparison[2].cost_ratio, comparison[1].cost_ratio);
}

// ============================================================================
// CostTracker Tests
// ============================================================================

TEST(CostTrackerTest, RecordSingleCost) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    auto record = tracker->record_cost(
        "session-1",
        "agent-1",
        "claude-sonnet-4",
        1000,  // input tokens
        500    // output tokens
    );

    EXPECT_EQ(record.session_id, "session-1");
    EXPECT_EQ(record.agent_name, "agent-1");
    EXPECT_EQ(record.model, "claude-sonnet-4");
    EXPECT_EQ(record.input_tokens, 1000);
    EXPECT_EQ(record.output_tokens, 500);
    EXPECT_GT(record.total_cost, 0);
    EXPECT_EQ(record.total_tokens(), 1500);
}

TEST(CostTrackerTest, RecordCostWithThinkingTokens) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    auto record = tracker->record_cost(
        "session-1",
        "agent-1",
        "o3",
        1000,   // input
        500,    // output
        3000    // thinking tokens
    );

    EXPECT_EQ(record.thinking_tokens, 3000);
    EXPECT_GT(record.thinking_cost, 0);
    EXPECT_EQ(record.total_tokens(), 4500);
}

TEST(CostTrackerTest, GetSessionCost) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 800, 400);
    tracker->record_cost("session-2", "agent-1", "claude-sonnet-4", 1000, 500);

    double session1_cost = tracker->get_session_cost("session-1");
    double session2_cost = tracker->get_session_cost("session-2");

    EXPECT_GT(session1_cost, 0);
    EXPECT_GT(session2_cost, 0);
    EXPECT_GT(session1_cost, session2_cost);  // session-1 has more requests
}

TEST(CostTrackerTest, GetAgentCost) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-1", "agent-2", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 800, 400);

    double agent1_cost = tracker->get_agent_cost("agent-1");
    double agent2_cost = tracker->get_agent_cost("agent-2");

    EXPECT_GT(agent1_cost, 0);
    EXPECT_GT(agent2_cost, 0);
    EXPECT_GT(agent1_cost, agent2_cost);  // agent-1 has more requests
}

TEST(CostTrackerTest, GetGlobalCost) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-2", "agent-2", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-3", "agent-3", "claude-sonnet-4", 1000, 500);

    double global_cost = tracker->get_global_cost();
    EXPECT_GT(global_cost, 0);

    // Should equal sum of all session costs
    double sum = tracker->get_session_cost("session-1") +
                 tracker->get_session_cost("session-2") +
                 tracker->get_session_cost("session-3");
    EXPECT_DOUBLE_EQ(global_cost, sum);
}

TEST(CostTrackerTest, GetCostBreakdown) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-1", "agent-1", "claude-haiku-3", 2000, 300);
    tracker->record_cost("session-1", "agent-1", "gpt-4o", 1000, 500);

    auto breakdown = tracker->get_breakdown();

    EXPECT_EQ(breakdown.size(), 3);
    EXPECT_TRUE(breakdown.count("claude-sonnet-4") > 0);
    EXPECT_TRUE(breakdown.count("claude-haiku-3") > 0);
    EXPECT_TRUE(breakdown.count("gpt-4o") > 0);
}

TEST(CostTrackerTest, GetCostBreakdownWithFilters) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-1", "agent-2", "claude-haiku-3", 2000, 300);
    tracker->record_cost("session-2", "agent-1", "claude-sonnet-4", 1000, 500);

    // Breakdown for specific session
    auto breakdown_session1 = tracker->get_breakdown("session-1");
    EXPECT_EQ(breakdown_session1.size(), 2);

    // Breakdown for specific agent
    auto breakdown_agent1 = tracker->get_breakdown(std::nullopt, "agent-1");
    EXPECT_EQ(breakdown_agent1.size(), 1);
    EXPECT_TRUE(breakdown_agent1.count("claude-sonnet-4") > 0);
}

TEST(CostTrackerTest, GetTopSessions) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    // Create sessions with different costs
    tracker->record_cost("session-1", "agent-1", "claude-opus-4", 1000, 1000);
    tracker->record_cost("session-2", "agent-1", "claude-haiku-3", 1000, 500);
    tracker->record_cost("session-3", "agent-1", "claude-sonnet-4", 2000, 1000);

    auto top_sessions = tracker->get_top_sessions(3);

    ASSERT_EQ(top_sessions.size(), 3);

    // First should be most expensive
    EXPECT_GT(top_sessions[0].second, top_sessions[1].second);
    EXPECT_GT(top_sessions[1].second, top_sessions[2].second);
}

TEST(CostTrackerTest, GetTopAgents) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    tracker->record_cost("session-1", "agent-1", "claude-opus-4", 1000, 1000);
    tracker->record_cost("session-1", "agent-2", "claude-haiku-3", 1000, 500);
    tracker->record_cost("session-1", "agent-3", "claude-sonnet-4", 2000, 1000);

    auto top_agents = tracker->get_top_agents(3);

    ASSERT_EQ(top_agents.size(), 3);

    // Sorted by cost descending
    EXPECT_GT(top_agents[0].second, top_agents[1].second);
}

TEST(CostTrackerTest, GetStatistics) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 800, 400);
    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1200, 600);

    auto stats = tracker->get_statistics();

    EXPECT_EQ(stats.total_requests, 3);
    EXPECT_GT(stats.total_cost, 0);
    EXPECT_EQ(stats.total_input_tokens, 3000);
    EXPECT_EQ(stats.total_output_tokens, 1500);
    EXPECT_EQ(stats.total_tokens, 4500);
    EXPECT_GT(stats.avg_cost_per_request, 0);
    EXPECT_DOUBLE_EQ(stats.avg_tokens_per_request, 1500.0);
}

TEST(CostTrackerTest, GetStatisticsWithFilters) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-1", "agent-2", "claude-sonnet-4", 800, 400);
    tracker->record_cost("session-2", "agent-1", "claude-sonnet-4", 1200, 600);

    // Stats for specific session
    auto stats_session1 = tracker->get_statistics("session-1");
    EXPECT_EQ(stats_session1.total_requests, 2);

    // Stats for specific agent
    auto stats_agent1 = tracker->get_statistics(std::nullopt, "agent-1");
    EXPECT_EQ(stats_agent1.total_requests, 2);

    // Stats for session + agent
    auto stats_both = tracker->get_statistics("session-1", "agent-1");
    EXPECT_EQ(stats_both.total_requests, 1);
}

TEST(CostTrackerTest, ClearTracker) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-2", "agent-1", "claude-sonnet-4", 1000, 500);

    EXPECT_EQ(tracker->count(), 2);

    tracker->clear();

    EXPECT_EQ(tracker->count(), 0);
    EXPECT_DOUBLE_EQ(tracker->get_global_cost(), 0.0);
}

// ============================================================================
// CostRecord Serialization Tests
// ============================================================================

TEST(CostRecordTest, SerializeAndDeserialize) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    auto record = tracker->record_cost(
        "session-1",
        "agent-1",
        "claude-sonnet-4",
        1000,
        500,
        0,
        nlohmann::json{{"test", "metadata"}}
    );

    // Serialize
    auto json = record.to_json();
    EXPECT_FALSE(json.empty());

    // Deserialize
    auto deserialized = CostRecord::from_json(json);

    EXPECT_EQ(deserialized.record_id, record.record_id);
    EXPECT_EQ(deserialized.session_id, record.session_id);
    EXPECT_EQ(deserialized.agent_name, record.agent_name);
    EXPECT_EQ(deserialized.model, record.model);
    EXPECT_EQ(deserialized.input_tokens, record.input_tokens);
    EXPECT_EQ(deserialized.output_tokens, record.output_tokens);
    EXPECT_DOUBLE_EQ(deserialized.total_cost, record.total_cost);
    ASSERT_TRUE(deserialized.metadata.has_value());
    EXPECT_EQ(deserialized.metadata.value()["test"], "metadata");
}

// ============================================================================
// Thread Safety Tests
// ============================================================================

TEST(CostTrackerThreadSafetyTest, ConcurrentRecordCost) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    std::vector<std::thread> threads;
    const int num_threads = 10;
    const int ops_per_thread = 100;

    for (int t = 0; t < num_threads; t++) {
        threads.emplace_back([&tracker, t, ops_per_thread]() {
            for (int i = 0; i < ops_per_thread; i++) {
                tracker->record_cost(
                    "session-" + std::to_string(t),
                    "agent-" + std::to_string(t),
                    "claude-sonnet-4",
                    1000,
                    500
                );
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    EXPECT_EQ(tracker->count(), num_threads * ops_per_thread);

    double global_cost = tracker->get_global_cost();
    EXPECT_GT(global_cost, 0);
}

TEST(CostTrackerThreadSafetyTest, ConcurrentQueries) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    // Pre-populate with data
    for (int i = 0; i < 100; i++) {
        tracker->record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500);
    }

    std::vector<std::thread> threads;
    const int num_threads = 10;

    for (int t = 0; t < num_threads; t++) {
        threads.emplace_back([&tracker]() {
            for (int i = 0; i < 50; i++) {
                tracker->get_session_cost("session-1");
                tracker->get_agent_cost("agent-1");
                tracker->get_global_cost();
                tracker->get_breakdown();
                tracker->get_statistics();
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    // Should not crash and data should be consistent
    EXPECT_EQ(tracker->count(), 100);
}

// ============================================================================
// Integration Tests
// ============================================================================

TEST(BudgetIntegrationTest, FullWorkflow) {
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    // Simulate a multi-turn conversation
    for (int turn = 0; turn < 5; turn++) {
        tracker->record_cost(
            "conversation-1",
            "chatbot",
            "claude-sonnet-4",
            800 + (turn * 100),  // Increasing context
            400
        );
    }

    // Check statistics
    auto stats = tracker->get_statistics("conversation-1");
    EXPECT_EQ(stats.total_requests, 5);
    EXPECT_GT(stats.total_cost, 0);

    // Check breakdown
    auto breakdown = tracker->get_breakdown("conversation-1");
    EXPECT_EQ(breakdown.size(), 1);
    EXPECT_TRUE(breakdown.count("claude-sonnet-4") > 0);

    // Compare with alternative model
    std::vector<std::string> models = {"claude-sonnet-4", "claude-haiku-3"};
    auto comparison = pricing->compare_models(models, stats.total_input_tokens, stats.total_output_tokens);

    // Haiku should be cheaper for same token count
    EXPECT_LT(comparison["claude-haiku-3"], comparison["claude-sonnet-4"]);
}
