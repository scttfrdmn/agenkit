/**
 * @file basic_budget.cpp
 * @brief Demonstrates budget tracking and cost management system
 *
 * This example shows:
 * 1. Recording costs for LLM API calls
 * 2. Querying costs per-session, per-agent, and globally
 * 3. Model pricing comparisons
 * 4. Cost breakdowns by model
 * 5. Top sessions and agents by cost
 * 6. Usage statistics
 */

#include <agenkit/infrastructure/budget/budget.hpp>
#include <iostream>
#include <iomanip>

using namespace agenkit::infrastructure::budget;

void print_separator() {
    std::cout << "\n" << std::string(60, '=') << "\n\n";
}

void example_basic_tracking() {
    std::cout << "=== Basic Cost Tracking Example ===\n\n";

    // 1. Create components
    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    // 2. Record some costs
    std::cout << "Recording costs for multiple API calls...\n\n";

    tracker->record_cost("session-123", "assistant", "claude-sonnet-4", 1000, 500);
    tracker->record_cost("session-123", "assistant", "claude-sonnet-4", 800, 400);
    tracker->record_cost("session-456", "summarizer", "claude-haiku-3", 2000, 300);
    tracker->record_cost("session-456", "summarizer", "claude-haiku-3", 1500, 250);
    tracker->record_cost("session-789", "analyzer", "claude-opus-4", 500, 1000);

    std::cout << "Recorded 5 API calls across 3 sessions and 3 agents\n";

    // 3. Query costs
    print_separator();
    std::cout << "=== Cost Queries ===\n\n";

    double session_123_cost = tracker->get_session_cost("session-123");
    std::cout << "Session 123 cost: $" << std::fixed << std::setprecision(4)
              << session_123_cost << "\n";

    double session_456_cost = tracker->get_session_cost("session-456");
    std::cout << "Session 456 cost: $" << session_456_cost << "\n";

    double assistant_cost = tracker->get_agent_cost("assistant");
    std::cout << "\nAssistant agent cost: $" << assistant_cost << "\n";

    double summarizer_cost = tracker->get_agent_cost("summarizer");
    std::cout << "Summarizer agent cost: $" << summarizer_cost << "\n";

    double global_cost = tracker->get_global_cost();
    std::cout << "\nGlobal cost (all sessions): $" << global_cost << "\n";

    // 4. Get cost breakdown
    print_separator();
    std::cout << "=== Cost Breakdown by Model ===\n\n";

    auto breakdown = tracker->get_breakdown();
    for (const auto& [model, cost] : breakdown) {
        std::cout << "  " << model << ": $" << cost << "\n";
    }

    // 5. Get top sessions
    print_separator();
    std::cout << "=== Top Sessions by Cost ===\n\n";

    auto top_sessions = tracker->get_top_sessions(3);
    for (size_t i = 0; i < top_sessions.size(); i++) {
        const auto& [session_id, cost] = top_sessions[i];
        std::cout << "  " << (i + 1) << ". " << session_id
                  << ": $" << cost << "\n";
    }

    // 6. Get statistics
    print_separator();
    std::cout << "=== Usage Statistics ===\n\n";

    auto stats = tracker->get_statistics();
    std::cout << "Total cost: $" << stats.total_cost << "\n";
    std::cout << "Total requests: " << stats.total_requests << "\n";
    std::cout << "Total tokens: " << stats.total_tokens << "\n";
    std::cout << "  Input: " << stats.total_input_tokens << "\n";
    std::cout << "  Output: " << stats.total_output_tokens << "\n";
    std::cout << "Average cost per request: $" << stats.avg_cost_per_request << "\n";
    std::cout << "Average tokens per request: " << stats.avg_tokens_per_request << "\n";
}

void example_model_pricing() {
    std::cout << "\n";
    print_separator();
    std::cout << "=== Model Pricing Example ===\n\n";

    auto pricing = std::make_shared<ModelPricing>();

    // 1. List all models
    std::cout << "Supported models:\n";
    auto models = pricing->list_models();
    for (const auto& model : models) {
        auto info = pricing->get_model_pricing(model);
        std::cout << "  " << model << " (" << info.provider << "):\n";
        std::cout << "    Input: $" << info.input_cost_per_million << " / 1M tokens\n";
        std::cout << "    Output: $" << info.output_cost_per_million << " / 1M tokens\n";
    }

    // 2. Calculate costs for specific model
    print_separator();
    std::cout << "=== Cost Calculations ===\n\n";

    double input_cost = pricing->calculate("claude-sonnet-4", 1000, "input");
    double output_cost = pricing->calculate("claude-sonnet-4", 500, "output");
    std::cout << "Claude Sonnet 4 (1000 input, 500 output):\n";
    std::cout << "  Input cost: $" << std::fixed << std::setprecision(6) << input_cost << "\n";
    std::cout << "  Output cost: $" << output_cost << "\n";
    std::cout << "  Total: $" << (input_cost + output_cost) << "\n";

    // 3. Estimate conversation cost
    print_separator();
    std::cout << "=== Conversation Cost Estimation ===\n\n";

    double conversation_cost = pricing->estimate_conversation_cost(
        "claude-sonnet-4",
        10,    // 10 turns
        800,   // average 800 input tokens per turn
        400    // average 400 output tokens per turn
    );
    std::cout << "10-turn conversation with Claude Sonnet 4:\n";
    std::cout << "  Average input: 800 tokens/turn\n";
    std::cout << "  Average output: 400 tokens/turn\n";
    std::cout << "  Total estimated cost: $" << conversation_cost << "\n";

    // 4. Compare models
    print_separator();
    std::cout << "=== Model Cost Comparison ===\n\n";

    std::vector<std::string> comparison_models = {
        "claude-haiku-3",
        "claude-sonnet-4",
        "claude-opus-4",
        "gpt-3.5-turbo",
        "gpt-4o"
    };

    auto comparison = pricing->compare_models_detailed(comparison_models, 1000, 500);
    std::cout << "Cost for 1000 input + 500 output tokens:\n\n";
    for (const auto& result : comparison) {
        std::cout << "  " << result.model << ":\n";
        std::cout << "    Cost: $" << std::fixed << std::setprecision(6)
                  << result.estimated_cost << "\n";
        std::cout << "    Ratio: " << std::setprecision(2) << result.cost_ratio << "x cheapest\n";
        if (result.cost_difference > 0.0) {
            std::cout << "    Premium: +$" << std::setprecision(6)
                      << result.cost_difference << "\n";
        }
        std::cout << "\n";
    }
}

void example_thinking_tokens() {
    std::cout << "\n";
    print_separator();
    std::cout << "=== Thinking Tokens Example ===\n\n";

    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    // Record cost with thinking tokens (for o3, Claude extended thinking)
    std::cout << "Recording cost for o3 model with thinking tokens...\n\n";

    auto record = tracker->record_cost(
        "session-reasoning",
        "reasoning-agent",
        "o3",
        1000,      // input tokens
        500,       // output tokens
        3000       // thinking tokens
    );

    std::cout << "Cost breakdown:\n";
    std::cout << "  Input cost (1000 tokens): $" << std::fixed << std::setprecision(6)
              << record.input_cost << "\n";
    std::cout << "  Output cost (500 tokens): $" << record.output_cost << "\n";
    std::cout << "  Thinking cost (3000 tokens): $" << record.thinking_cost << "\n";
    std::cout << "  Total cost: $" << record.total_cost << "\n";
    std::cout << "  Total tokens: " << record.total_tokens() << "\n";
}

void example_session_filtering() {
    std::cout << "\n";
    print_separator();
    std::cout << "=== Session Filtering Example ===\n\n";

    auto pricing = std::make_shared<ModelPricing>();
    auto tracker = std::make_shared<CostTracker>(pricing);

    // Record costs for multiple sessions
    tracker->record_cost("user-alice", "chatbot", "claude-sonnet-4", 800, 400);
    tracker->record_cost("user-alice", "chatbot", "claude-sonnet-4", 900, 450);
    tracker->record_cost("user-bob", "chatbot", "claude-haiku-3", 1000, 300);
    tracker->record_cost("user-bob", "chatbot", "claude-haiku-3", 1200, 350);
    tracker->record_cost("user-charlie", "chatbot", "claude-opus-4", 500, 800);

    std::cout << "Recorded costs for 3 users (Alice, Bob, Charlie)\n\n";

    // Get statistics per session
    std::cout << "Cost breakdown by user:\n\n";

    auto alice_stats = tracker->get_statistics("user-alice");
    std::cout << "Alice:\n";
    std::cout << "  Total cost: $" << std::fixed << std::setprecision(4)
              << alice_stats.total_cost << "\n";
    std::cout << "  Requests: " << alice_stats.total_requests << "\n";
    std::cout << "  Avg cost/request: $" << alice_stats.avg_cost_per_request << "\n\n";

    auto bob_stats = tracker->get_statistics("user-bob");
    std::cout << "Bob:\n";
    std::cout << "  Total cost: $" << bob_stats.total_cost << "\n";
    std::cout << "  Requests: " << bob_stats.total_requests << "\n";
    std::cout << "  Avg cost/request: $" << bob_stats.avg_cost_per_request << "\n\n";

    auto charlie_stats = tracker->get_statistics("user-charlie");
    std::cout << "Charlie:\n";
    std::cout << "  Total cost: $" << charlie_stats.total_cost << "\n";
    std::cout << "  Requests: " << charlie_stats.total_requests << "\n";
    std::cout << "  Avg cost/request: $" << charlie_stats.avg_cost_per_request << "\n";
}

int main() {
    std::cout << "Agenkit C++ Budget Tracking Examples\n";
    std::cout << "=====================================\n";

    try {
        example_basic_tracking();
        example_model_pricing();
        example_thinking_tokens();
        example_session_filtering();

        print_separator();
        std::cout << "=== All Examples Completed ===\n\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}
