/**
 * @file fallback.cpp
 * @brief Implementation of FallbackAgent
 */

#include "agenkit/composition/fallback.hpp"
#include <stdexcept>
#include <set>
#include <sstream>

namespace agenkit {
namespace composition {

using namespace core;

FallbackAgent::FallbackAgent(
    std::string name,
    std::vector<std::shared_ptr<Agent>> agents
) : name_(std::move(name)), agents_(std::move(agents)) {
    if (agents_.empty()) {
        throw std::invalid_argument("Fallback agent requires at least one agent");
    }
}

std::vector<std::string> FallbackAgent::capabilities() const {
    std::set<std::string> cap_set;

    for (const auto& agent : agents_) {
        for (const auto& cap : agent->capabilities()) {
            cap_set.insert(cap);
        }
    }

    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());
    capabilities.push_back("fallback");

    return capabilities;
}

std::future<Result<Message, AgentError>>
FallbackAgent::process(Message message) {
    return std::async(std::launch::async, [this, message]() {
        std::vector<std::string> errors;

        for (size_t i = 0; i < agents_.size(); ++i) {
            const auto& agent = agents_[i];

            try {
                auto future = agent->process(message);
                auto result = future.get();

                if (result.is_ok()) {
                    // Success! Add metadata about which agent was used
                    auto response = std::move(result.unwrap());
                    response.with_metadata("fallback_agent_used", agent->name());
                    response.with_metadata("fallback_attempt", static_cast<double>(i + 1));
                    return Result<Message, AgentError>::ok(std::move(response));
                } else {
                    errors.push_back(
                        "agent " + std::to_string(i + 1) + " (" + agent->name() + "): " +
                        result.unwrap_err().message()
                    );
                }
            } catch (const std::exception& e) {
                errors.push_back(
                    "agent " + std::to_string(i + 1) + " (" + agent->name() + "): " +
                    std::string(e.what())
                );
            }
        }

        // All agents failed
        std::ostringstream oss;
        oss << "All " << agents_.size() << " agents failed: ";
        for (size_t i = 0; i < errors.size(); ++i) {
            if (i > 0) oss << "; ";
            oss << errors[i];
        }

        return Result<Message, AgentError>::err(AgentError(
            AgentErrorType::ProcessingError,
            oss.str()
        ));
    });
}

} // namespace composition
} // namespace agenkit
