/**
 * @file echo_agent.hpp
 * @brief Simple echo agent for testing and examples
 */

#ifndef AGENKIT_ADAPTERS_ECHO_AGENT_HPP
#define AGENKIT_ADAPTERS_ECHO_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include <string>

namespace agenkit {
namespace adapters {

/**
 * @brief Simple agent that echoes back the input message
 *
 * This is a reference implementation of the Agent interface,
 * useful for testing and examples.
 *
 * @example
 * @code
 * EchoAgent agent;
 * auto msg = Message::with_text("user", "Hello!");
 * auto future = agent.process(std::move(msg));
 * auto result = future.get();
 * if (result.is_ok()) {
 *     std::cout << "Response: " << result.unwrap().content_as_str() << std::endl;
 * }
 * @endcode
 */
class EchoAgent : public core::Agent {
public:
    /**
     * @brief Construct an echo agent
     */
    EchoAgent() = default;

    /**
     * @brief Get agent name
     * @return "echo"
     */
    std::string name() const override;

    /**
     * @brief Process message by echoing it back
     * @param message Input message
     * @return Future with result containing echoed message
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get capabilities
     * @return List of capabilities
     */
    std::vector<std::string> capabilities() const override;
};

} // namespace adapters
} // namespace agenkit

#endif // AGENKIT_ADAPTERS_ECHO_AGENT_HPP
