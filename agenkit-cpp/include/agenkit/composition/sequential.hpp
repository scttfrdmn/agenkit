/**
 * @file sequential.hpp
 * @brief Sequential agent composition pattern
 *
 * Executes multiple agents in sequence where the output of one agent
 * becomes the input to the next agent.
 */

#ifndef AGENKIT_COMPOSITION_SEQUENTIAL_HPP
#define AGENKIT_COMPOSITION_SEQUENTIAL_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"
#include <memory>
#include <vector>
#include <string>
#include <future>

namespace agenkit {
namespace composition {

/**
 * @brief Agent that executes multiple agents in sequence
 *
 * The output of one agent becomes the input to the next agent.
 * This is useful for building processing pipelines.
 *
 * @example
 * @code
 * auto sequential = std::make_shared<SequentialAgent>(
 *     "pipeline",
 *     std::vector<std::shared_ptr<Agent>>{extract, translate, summarize}
 * );
 *
 * auto result = sequential->process(message).get();
 * @endcode
 */
class SequentialAgent : public core::Agent {
public:
    /**
     * @brief Create a new sequential agent
     *
     * @param name Name of this sequential agent
     * @param agents List of agents to execute in sequence
     * @throws std::invalid_argument if agents list is empty
     */
    SequentialAgent(
        std::string name,
        std::vector<std::shared_ptr<core::Agent>> agents
    );

    std::string name() const override { return name_; }

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get the list of agents in the sequence
     */
    const std::vector<std::shared_ptr<core::Agent>>& agents() const {
        return agents_;
    }

private:
    std::string name_;
    std::vector<std::shared_ptr<core::Agent>> agents_;
};

} // namespace composition
} // namespace agenkit

#endif // AGENKIT_COMPOSITION_SEQUENTIAL_HPP
