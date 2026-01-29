/**
 * @file conditional.hpp
 * @brief Conditional agent composition pattern
 *
 * Routes messages to different agents based on conditions.
 */

#ifndef AGENKIT_COMPOSITION_CONDITIONAL_HPP
#define AGENKIT_COMPOSITION_CONDITIONAL_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"
#include <memory>
#include <vector>
#include <string>
#include <functional>
#include <future>

namespace agenkit {
namespace composition {

/**
 * @brief Condition function type
 *
 * Returns true if the message should be routed to the associated agent.
 */
using Condition = std::function<bool(const core::Message&)>;

/**
 * @brief Represents a condition-agent pair
 */
struct ConditionalRoute {
    Condition condition;
    std::shared_ptr<core::Agent> agent;
};

/**
 * @brief Agent that routes messages to different agents based on conditions
 *
 * Evaluates conditions in order and routes to the first matching agent.
 * Falls back to default agent if no condition matches.
 */
class ConditionalAgent : public core::Agent {
public:
    /**
     * @brief Create a new conditional agent
     *
     * @param name Name of this conditional agent
     * @param default_agent Agent to use when no condition matches
     */
    ConditionalAgent(
        std::string name,
        std::shared_ptr<core::Agent> default_agent
    );

    std::string name() const override { return name_; }

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Add a conditional route
     *
     * @param condition Function that returns true if this agent should be used
     * @param agent Agent to use when condition is met
     */
    void add_route(Condition condition, std::shared_ptr<core::Agent> agent);

    /**
     * @brief Get the conditional routes
     */
    const std::vector<ConditionalRoute>& routes() const { return routes_; }

    /**
     * @brief Get the default agent
     */
    const std::shared_ptr<core::Agent>& default_agent() const {
        return default_agent_;
    }

private:
    std::string name_;
    std::vector<ConditionalRoute> routes_;
    std::shared_ptr<core::Agent> default_agent_;
};

// Common condition helpers

/**
 * @brief Return a condition that checks if message content contains a substring
 */
Condition content_contains(const std::string& substr);

/**
 * @brief Return a condition that checks if message role equals the given role
 */
Condition role_equals(const std::string& role);

} // namespace composition
} // namespace agenkit

#endif // AGENKIT_COMPOSITION_CONDITIONAL_HPP
