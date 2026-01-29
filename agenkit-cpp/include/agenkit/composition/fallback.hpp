/**
 * @file fallback.hpp
 * @brief Fallback agent composition pattern
 *
 * Tries agents in order until one succeeds.
 * This implements the Fallback/Retry pattern for reliability.
 */

#ifndef AGENKIT_COMPOSITION_FALLBACK_HPP
#define AGENKIT_COMPOSITION_FALLBACK_HPP

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
 * @brief Agent that tries agents in order until one succeeds
 *
 * This is useful for building fault-tolerant systems where you want
 * to try multiple agents as fallbacks.
 */
class FallbackAgent : public core::Agent {
public:
    /**
     * @brief Create a new fallback agent
     *
     * @param name Name of this fallback agent
     * @param agents List of agents to try in order
     * @throws std::invalid_argument if agents list is empty
     */
    FallbackAgent(
        std::string name,
        std::vector<std::shared_ptr<core::Agent>> agents
    );

    std::string name() const override { return name_; }

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get the list of fallback agents
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

#endif // AGENKIT_COMPOSITION_FALLBACK_HPP
