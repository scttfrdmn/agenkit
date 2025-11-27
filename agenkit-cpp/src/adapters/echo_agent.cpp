/**
 * @file echo_agent.cpp
 * @brief Implementation of Echo agent
 */

#include "agenkit/adapters/echo_agent.hpp"

namespace agenkit {
namespace adapters {

std::string EchoAgent::name() const {
    return "echo";
}

std::future<core::Result<core::Message, core::AgentError>>
EchoAgent::process(core::Message message) {
    // Echo back the content
    auto response = core::Message::with_text(
        "assistant",
        message.content_as_str()
    );

    // Preserve metadata from input message
    for (const auto& [key, value] : message.metadata().items()) {
        response.with_metadata(key, value);
    }

    // Return ready future with ok result
    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(std::move(response))
    );
}

std::vector<std::string> EchoAgent::capabilities() const {
    return {"echo", "test"};
}

} // namespace adapters
} // namespace agenkit
