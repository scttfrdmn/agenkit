/**
 * @file reflection.hpp
 * @brief Reflection pattern for agent self-improvement
 *
 * The Reflection pattern enables agents to critique and improve their own
 * outputs through iterative self-reflection. This pattern is useful for
 * improving response quality, catching errors, and refining answers.
 *
 * @example
 * @code
 * auto agent = std::make_shared<MyAgent>();
 * auto reflector = std::make_shared<CriticAgent>();
 *
 * ReflectionAgent reflection_agent(agent, reflector, 3);
 * auto msg = Message::with_text("user", "Explain quantum computing");
 * auto result = reflection_agent.process(std::move(msg)).get();
 * @endcode
 */

#ifndef AGENKIT_PATTERNS_REFLECTION_HPP
#define AGENKIT_PATTERNS_REFLECTION_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <memory>
#include <vector>

namespace agenkit {
namespace patterns {

/**
 * @brief Reflection step in the improvement loop
 */
struct ReflectionStep {
    int iteration;                  ///< Iteration number (1-based)
    core::Message response;         ///< Agent's response
    core::Message feedback;         ///< Reflector's feedback
    bool should_continue;           ///< Whether to continue reflecting
};

/**
 * @brief Agent that improves outputs through self-reflection
 *
 * The ReflectionAgent wraps two agents:
 * 1. A primary agent that generates responses
 * 2. A reflector agent that critiques those responses
 *
 * The pattern iteratively improves the response by:
 * 1. Getting initial response from primary agent
 * 2. Having reflector critique the response
 * 3. Using feedback to generate improved response
 * 4. Repeating until quality threshold met or max iterations reached
 *
 * Design principles:
 * - Composable: Works with any Agent implementation
 * - Configurable: Max reflections can be tuned
 * - Transparent: Full reflection history in metadata
 * - Type-safe: Uses Result<T,E> for error handling
 */
class ReflectionAgent : public core::Agent {
public:
    /**
     * @brief Construct a reflection agent
     *
     * @param agent Primary agent that generates responses
     * @param reflector Agent that critiques responses
     * @param max_reflections Maximum number of reflection iterations (default: 3)
     *
     * @throws std::invalid_argument if agent or reflector is null
     */
    ReflectionAgent(
        std::shared_ptr<core::Agent> agent,
        std::shared_ptr<core::Agent> reflector,
        int max_reflections = 3
    );

    /**
     * @brief Get agent name
     * @return "reflection"
     */
    std::string name() const override;

    /**
     * @brief Process message with reflection loop
     *
     * Processing steps:
     * 1. Get initial response from agent
     * 2. Loop up to max_reflections:
     *    a. Get reflector feedback
     *    b. Check if feedback indicates response is good enough
     *    c. If not, get improved response from agent
     * 3. Return final response with reflection history in metadata
     *
     * Metadata added:
     * - "reflection_iterations": Number of reflection steps
     * - "reflection_history": Array of reflection steps
     * - "final_iteration": Final iteration number
     *
     * @param message Input message
     * @return Future with result containing final response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get agent capabilities
     * @return List of capabilities: ["reflection", "self-improvement"]
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Get reflection history from last process call
     * @return Vector of reflection steps
     */
    const std::vector<ReflectionStep>& get_reflection_history() const;

    /**
     * @brief Clear reflection history
     */
    void clear_history();

private:
    std::shared_ptr<core::Agent> agent_;
    std::shared_ptr<core::Agent> reflector_;
    int max_reflections_;
    std::vector<ReflectionStep> reflection_history_;

    /**
     * @brief Create reflection prompt for reflector
     * @param original Original user message
     * @param response Agent's current response
     * @return Message for reflector with context
     */
    core::Message create_reflection_prompt(
        const core::Message& original,
        const core::Message& response
    );

    /**
     * @brief Parse reflector feedback to determine if should continue
     * @param feedback Reflector's feedback message
     * @return true if should continue reflecting, false if response is good
     */
    bool should_continue_reflecting(const core::Message& feedback);

    /**
     * @brief Create improvement prompt for agent
     * @param original Original user message
     * @param previous_response Previous response
     * @param feedback Reflector's feedback
     * @return Message for agent to generate improved response
     */
    core::Message create_improvement_prompt(
        const core::Message& original,
        const core::Message& previous_response,
        const core::Message& feedback
    );

    /**
     * @brief Add reflection history to message metadata
     * @param message Message to add metadata to
     */
    void add_reflection_metadata(core::Message& message);
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_REFLECTION_HPP
