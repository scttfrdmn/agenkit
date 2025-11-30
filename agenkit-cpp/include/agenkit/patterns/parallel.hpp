/**
 * @file parallel.hpp
 * @brief Parallel agent execution pattern
 *
 * This module provides the Parallel pattern for concurrent execution of multiple agents
 * with result aggregation. This is ideal for ensemble methods, multi-perspective
 * analysis, or parallelizing independent tasks.
 */

#ifndef AGENKIT_PATTERNS_PARALLEL_HPP
#define AGENKIT_PATTERNS_PARALLEL_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <vector>
#include <string>
#include <functional>

namespace agenkit {
namespace patterns {

/**
 * @brief Function type for aggregating multiple agent responses
 *
 * The aggregator receives all agent responses and should return a single
 * aggregated response. Common aggregation strategies include:
 * - Voting: Select most common response
 * - Averaging: Combine numeric results
 * - Concatenation: Merge all responses
 * - First-success: Return first successful result
 * - Consensus: Require agreement threshold
 */
using AggregatorFunc = std::function<core::Message(const std::vector<core::Message>&)>;

/**
 * @brief Parallel execution agent with result aggregation
 *
 * The ParallelAgent executes multiple agents concurrently and aggregates their results.
 * All agents receive the same input message and execute in parallel using std::async.
 * Results are collected and passed to the aggregator function which produces the final output.
 *
 * Key concepts:
 * - Concurrent agent execution using std::async
 * - Custom aggregation function for combining results
 * - All agents receive the same input message
 * - Results collected and aggregated after all complete
 *
 * Performance characteristics:
 * - Time: O(max agent time) - parallel execution
 * - Memory: O(n * message size) for concurrent processing
 * - Thread-safe with proper synchronization
 *
 * Example use cases:
 * - Multi-model ensemble for improved accuracy
 * - Parallel document analysis (sentiment, entities, topics)
 * - A/B testing different agent implementations
 * - Redundant processing for reliability
 *
 * If any agent fails, the error is collected but other agents continue.
 * The aggregator receives all successful results.
 *
 * @example
 * @code
 * auto aggregator = [](const std::vector<core::Message>& messages) {
 *     // Concatenate all responses
 *     std::string combined;
 *     for (const auto& msg : messages) {
 *         if (!combined.empty()) combined += "\n\n---\n\n";
 *         combined += msg.content_as_str();
 *     }
 *     return core::Message::with_text("assistant", combined);
 * };
 *
 * std::vector<std::shared_ptr<core::Agent>> agents = {
 *     std::make_shared<SentimentAgent>(),
 *     std::make_shared<EntityAgent>(),
 *     std::make_shared<TopicAgent>()
 * };
 *
 * ParallelAgent parallel(agents, aggregator);
 * auto msg = core::Message::with_text("user", "Analyze this text");
 * auto result = parallel.process(std::move(msg)).get();
 * @endcode
 */
class ParallelAgent : public core::Agent {
public:
    /**
     * @brief Construct a parallel execution agent
     * @param agents List of agents to execute concurrently (must have at least one)
     * @param aggregator Function to combine agent results into final output
     * @throws std::invalid_argument if agents is empty or aggregator is null
     */
    ParallelAgent(
        std::vector<std::shared_ptr<core::Agent>> agents,
        AggregatorFunc aggregator
    );

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::vector<std::shared_ptr<core::Agent>> agents_;
    AggregatorFunc aggregator_;
};

/**
 * @brief Default aggregation strategies
 */
namespace default_aggregators {

/**
 * @brief Returns the first successful result
 * @param messages Vector of messages to aggregate
 * @return First message in the vector
 */
core::Message first(const std::vector<core::Message>& messages);

/**
 * @brief Concatenates all results with separator
 * @param messages Vector of messages to aggregate
 * @return Message with concatenated content
 */
core::Message concatenate(const std::vector<core::Message>& messages);

/**
 * @brief Returns the most common response (majority vote)
 * @param messages Vector of messages to aggregate
 * @return Most common message with vote metadata
 */
core::Message majority_vote(const std::vector<core::Message>& messages);

} // namespace default_aggregators

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_PARALLEL_HPP
