/**
 * @file parallel.hpp
 * @brief Parallel agent composition pattern
 *
 * Executes multiple agents concurrently and combines their results.
 */

#ifndef AGENKIT_COMPOSITION_PARALLEL_HPP
#define AGENKIT_COMPOSITION_PARALLEL_HPP

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
 * @brief Agent that executes multiple agents concurrently
 *
 * All agents receive the same input message and execute in parallel.
 * Results are combined into a single output message.
 */
class ParallelAgent : public core::Agent {
public:
    /**
     * @brief Create a new parallel agent
     *
     * @param name Name of this parallel agent
     * @param agents List of agents to execute in parallel
     * @throws std::invalid_argument if agents list is empty
     */
    ParallelAgent(
        std::string name,
        std::vector<std::shared_ptr<core::Agent>> agents
    );

    std::string name() const override { return name_; }

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get the list of agents that run in parallel
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

#endif // AGENKIT_COMPOSITION_PARALLEL_HPP
