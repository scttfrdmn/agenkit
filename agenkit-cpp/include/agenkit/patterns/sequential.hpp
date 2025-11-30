/**
 * @file sequential.hpp
 * @brief Sequential agent pipeline pattern
 *
 * This module provides the Sequential pattern for agent composition where each agent
 * processes the output of the previous agent. This is ideal for multi-stage
 * processing workflows.
 */

#ifndef AGENKIT_PATTERNS_SEQUENTIAL_HPP
#define AGENKIT_PATTERNS_SEQUENTIAL_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <vector>
#include <string>

namespace agenkit {
namespace patterns {

/**
 * @brief Sequential pipeline agent for linear processing
 *
 * The SequentialAgent executes a pipeline of agents in order. Each agent receives
 * the output of the previous agent as input. The final agent's output is returned
 * as the result.
 *
 * Key concepts:
 * - Linear processing pipeline
 * - Output of agent N becomes input of agent N+1
 * - Early termination on errors
 * - Preserves metadata across pipeline stages
 *
 * Performance characteristics:
 * - Time: O(sum of agent times) - sequential execution
 * - Memory: O(1) for message passing (no accumulation)
 * - Each agent sees only previous agent's output
 *
 * Example use cases:
 * - Document processing: extract -> translate -> summarize
 * - Data pipeline: validate -> transform -> enrich
 * - Content generation: draft -> review -> format
 *
 * The pipeline stops immediately if any agent returns an error.
 *
 * @example
 * @code
 * std::vector<std::shared_ptr<core::Agent>> agents = {
 *     std::make_shared<ValidatorAgent>(),
 *     std::make_shared<TransformerAgent>(),
 *     std::make_shared<EnricherAgent>()
 * };
 *
 * SequentialAgent pipeline(agents);
 * auto msg = core::Message::with_text("user", "Process this data");
 * auto result = pipeline.process(std::move(msg)).get();
 *
 * if (result.is_ok()) {
 *     auto response = result.unwrap();
 *     std::cout << "Pipeline result: " << response.content_as_str() << std::endl;
 * }
 * @endcode
 */
class SequentialAgent : public core::Agent {
public:
    /**
     * @brief Construct a sequential pipeline agent
     * @param agents List of agents to execute in order (must have at least one)
     * @throws std::invalid_argument if agents vector is empty
     */
    explicit SequentialAgent(std::vector<std::shared_ptr<core::Agent>> agents);

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::vector<std::shared_ptr<core::Agent>> agents_;
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_SEQUENTIAL_HPP
