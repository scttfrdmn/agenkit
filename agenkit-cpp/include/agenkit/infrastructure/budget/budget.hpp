#pragma once

/// @file budget.hpp
/// @brief Budget tracking and cost management system
///
/// The budget tracking system provides:
///
/// 1. **Cost Tracking** - Record and query LLM API costs
/// 2. **Model Pricing** - Centralized pricing database (November 2025 rates)
/// 3. **Budget Analytics** - Statistics and cost breakdowns
/// 4. **Multi-level Queries** - Per-session, per-agent, and global costs
///
/// # Architecture
///
/// The system has three layers:
///
/// - **Models**: Data structures (CostRecord, PricingInfo, UsageStats)
/// - **Pricing**: Centralized pricing database with 12+ pre-configured models
/// - **Tracker**: Recording and querying with flexible storage backends
///
/// # Basic Usage
///
/// ```cpp
/// #include <agenkit/infrastructure/budget/budget.hpp>
///
/// // 1. Create components
/// auto pricing = std::make_shared<ModelPricing>();
/// auto tracker = std::make_shared<CostTracker>(pricing);
///
/// // 2. Record costs
/// tracker->record_cost(
///     "session-123",          // session_id
///     "my-agent",             // agent_name
///     "claude-sonnet-4",      // model
///     1000,                   // input_tokens
///     500                     // output_tokens
/// );
///
/// // 3. Query costs
/// double session_cost = tracker->get_session_cost("session-123");
/// double agent_cost = tracker->get_agent_cost("my-agent");
/// double global_cost = tracker->get_global_cost();
///
/// // 4. Get statistics
/// auto stats = tracker->get_statistics("session-123");
/// std::cout << "Total cost: $" << stats.total_cost << "\n";
/// std::cout << "Total tokens: " << stats.total_tokens << "\n";
/// ```
///
/// # Model Pricing
///
/// Pre-configured pricing (November 2025 rates, per 1M tokens):
///
/// **OpenAI:**
/// - gpt-4o: $2.50 in / $10.00 out
/// - gpt-4-turbo: $10.00 in / $30.00 out
/// - gpt-3.5-turbo: $0.50 in / $1.50 out
/// - o3: $10.00 in / $40.00 out
/// - o3-mini: $1.10 in / $4.40 out
///
/// **Anthropic:**
/// - claude-opus-4: $15.00 in / $75.00 out
/// - claude-sonnet-4: $3.00 in / $15.00 out
/// - claude-haiku-3: $0.25 in / $1.25 out
///
/// **Google:**
/// - gemini-2.0-flash-exp: Free
/// - gemini-pro: $0.50 in / $1.50 out
///
/// # Cost Analysis
///
/// ```cpp
/// // Get cost breakdown by model
/// auto breakdown = tracker->get_breakdown("session-123");
/// for (const auto& [model, cost] : breakdown) {
///     std::cout << model << ": $" << cost << "\n";
/// }
///
/// // Get top sessions
/// auto top_sessions = tracker->get_top_sessions(10);
/// for (const auto& [session_id, cost] : top_sessions) {
///     std::cout << session_id << ": $" << cost << "\n";
/// }
///
/// // Compare model costs
/// std::vector<std::string> models = {
///     "claude-haiku-3", "claude-sonnet-4", "claude-opus-4"
/// };
/// auto comparison = pricing->compare_models_detailed(models, 1000, 500);
/// ```
///
/// # Thinking Tokens
///
/// For models supporting extended reasoning (o3, Claude 4):
///
/// ```cpp
/// tracker->record_cost(
///     session_id,
///     agent_name,
///     "o3",
///     1000,      // input_tokens
///     500,       // output_tokens
///     3000       // thinking_tokens
/// );
/// ```
///
/// # Custom Storage
///
/// Implement CostStorage interface for custom backends:
///
/// ```cpp
/// class DatabaseCostStorage : public CostStorage {
/// public:
///     void store(const CostRecord& record) override {
///         // Store to database
///     }
///
///     std::vector<CostRecord> query(...) override {
///         // Query from database
///     }
/// };
///
/// auto storage = std::make_unique<DatabaseCostStorage>();
/// auto tracker = std::make_shared<CostTracker>(pricing, std::move(storage));
/// ```
///
/// # Thread Safety
///
/// All components are thread-safe:
/// - ModelPricing uses std::shared_mutex for concurrent reads
/// - CostTracker delegates to storage implementation
/// - InMemoryCostStorage uses std::shared_mutex
///
/// # Error Handling
///
/// All operations use exceptions for error handling:
/// - Invalid model names fall back to "default" pricing
/// - Empty queries return empty vectors
/// - Division by zero protected in statistics
///
/// # Performance Characteristics
///
/// | Operation             | InMemory      |
/// |-----------------------|---------------|
/// | record_cost           | O(1)          |
/// | get_session_cost      | O(n)          |
/// | get_agent_cost        | O(n)          |
/// | get_global_cost       | O(n)          |
/// | get_top_sessions      | O(n log n)    |
/// | get_statistics        | O(n)          |
///
/// Where n = total number of cost records
///
/// # Integration Points
///
/// Budget tracking integrates with:
/// - **Checkpointing**: Store cost metadata in checkpoints
/// - **Observability**: Log costs in traces
/// - **Middleware**: Track costs per request
/// - **Memory Systems**: Budget token usage

#include "agenkit/infrastructure/budget/models.hpp"
#include "agenkit/infrastructure/budget/pricing.hpp"
#include "agenkit/infrastructure/budget/tracker.hpp"
