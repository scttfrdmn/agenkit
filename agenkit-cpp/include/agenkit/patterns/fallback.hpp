/**
 * @file fallback.hpp
 * @brief Fallback sequential retry pattern
 *
 * This module provides the Fallback pattern for sequential retry across multiple agents.
 * If one agent fails, the next agent is tried until one succeeds or
 * all agents are exhausted.
 */

#ifndef AGENKIT_PATTERNS_FALLBACK_HPP
#define AGENKIT_PATTERNS_FALLBACK_HPP

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
 * @brief Fallback agent for sequential retry with automatic failover
 *
 * The FallbackAgent tries agents in sequence until one succeeds.
 * Each agent is attempted in order. The first agent to return a successful
 * response wins, and that response is returned immediately. If an agent
 * fails, the next agent is tried. If all agents fail, an error combining
 * all failure reasons is returned.
 *
 * Key concepts:
 * - Sequential attempt order
 * - Automatic failover on errors
 * - First successful result wins
 * - Error collection for debugging
 *
 * Performance characteristics:
 * - Best case: O(first agent) - immediate success
 * - Worst case: O(sum of all agents) - all fail
 * - Early termination on first success
 *
 * Example use cases:
 * - High availability: fallback from primary to backup systems
 * - Multi-provider: try different LLM providers until one succeeds
 * - Graceful degradation: try advanced model, fallback to simple model
 * - Retry with alternatives: different strategies for same task
 * - Error recovery: fallback to cached/default responses
 *
 * The fallback pattern is ideal when you need resilience and have
 * multiple ways to accomplish the same task.
 *
 * @example
 * @code
 * std::vector<std::shared_ptr<core::Agent>> agents = {
 *     std::make_shared<PrimaryAgent>(),
 *     std::make_shared<BackupAgent>(),
 *     std::make_shared<CacheAgent>()
 * };
 *
 * FallbackAgent fallback(agents);
 * auto msg = core::Message::with_text("user", "Process this request");
 * auto result = fallback.process(std::move(msg)).get();
 *
 * if (result.is_ok()) {
 *     auto response = result.unwrap();
 *     // Check which agent succeeded
 *     std::cout << "Success with: "
 *               << response.metadata()["fallback_success_agent"] << std::endl;
 * }
 * @endcode
 */
class FallbackAgent : public core::Agent {
public:
    /**
     * @brief Construct a fallback agent
     * @param agents List of agents to try in order (must have at least one)
     * @throws std::invalid_argument if agents vector is empty
     */
    explicit FallbackAgent(std::vector<std::shared_ptr<core::Agent>> agents);

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::vector<std::shared_ptr<core::Agent>> agents_;
};

/**
 * @brief Function type for recovery logic
 *
 * The function receives the original message and error, and attempts
 * to produce a fallback response.
 */
using RecoveryFunc = std::function<core::Result<core::Message, core::AgentError>(
    const core::Message& message,
    const core::AgentError& original_error
)>;

/**
 * @brief Recovery agent wrapper for automatic error recovery
 *
 * The RecoveryAgent wraps an agent with a recovery function.
 * If the primary agent fails, the recovery function is called to
 * attempt to produce a fallback response.
 *
 * This is useful for wrapping a single agent with error handling,
 * whereas FallbackAgent is for trying multiple agents sequentially.
 *
 * @example
 * @code
 * auto recovery = [](const core::Message& msg, const core::AgentError& err) {
 *     return core::Result<core::Message, core::AgentError>::ok(
 *         core::Message::with_text("assistant",
 *             "I'm experiencing technical difficulties. Please try again.")
 *     );
 * };
 *
 * RecoveryAgent recovery_agent(my_agent, recovery);
 * auto msg = core::Message::with_text("user", "Help me");
 * auto result = recovery_agent.process(std::move(msg)).get();
 * @endcode
 */
class RecoveryAgent : public core::Agent {
public:
    /**
     * @brief Construct a recovery agent
     * @param agent Primary agent to execute
     * @param recovery_func Recovery function for handling failures
     * @throws std::invalid_argument if agent or recovery_func is null
     */
    RecoveryAgent(
        std::shared_ptr<core::Agent> agent,
        RecoveryFunc recovery_func
    );

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::shared_ptr<core::Agent> agent_;
    RecoveryFunc recovery_func_;
};

/**
 * @brief Default recovery strategies
 */
namespace default_recovery {

/**
 * @brief Returns a fixed fallback message
 * @param message Static message to return
 * @return Recovery function
 */
RecoveryFunc static_message(const std::string& message);

/**
 * @brief Returns an empty but valid response
 * @return Recovery function
 */
RecoveryFunc empty_response();

} // namespace default_recovery

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_FALLBACK_HPP
