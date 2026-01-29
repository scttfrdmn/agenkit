/**
 * @file sequential.cpp
 * @brief Implementation of SequentialAgent
 */

#include "agenkit/composition/sequential.hpp"
#include <stdexcept>
#include <set>

namespace agenkit {
namespace composition {

using namespace core;

SequentialAgent::SequentialAgent(
    std::string name,
    std::vector<std::shared_ptr<Agent>> agents
) : name_(std::move(name)), agents_(std::move(agents)) {
    if (agents_.empty()) {
        throw std::invalid_argument("Sequential agent requires at least one agent");
    }
}

std::vector<std::string> SequentialAgent::capabilities() const {
    // Collect unique capabilities from all agents
    std::set<std::string> cap_set;

    for (const auto& agent : agents_) {
        for (const auto& cap : agent->capabilities()) {
            cap_set.insert(cap);
        }
    }

    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());
    capabilities.push_back("sequential");

    return capabilities;
}

std::future<Result<Message, AgentError>>
SequentialAgent::process(Message message) {
    return std::async(std::launch::async, [this, message = std::move(message)]() mutable {
        Message current = std::move(message);

        for (size_t i = 0; i < agents_.size(); ++i) {
            const auto& agent = agents_[i];

            try {
                auto future = agent->process(std::move(current));
                auto result = future.get();

                if (result.is_err()) {
                    return Result<Message, AgentError>::err(AgentError(
                        AgentErrorType::ProcessingError,
                        "Step " + std::to_string(i + 1) + " (" + agent->name() + ") failed: " +
                        result.unwrap_err().message()
                    ));
                }

                current = std::move(result.unwrap());
            } catch (const std::exception& e) {
                return Result<Message, AgentError>::err(AgentError(
                    AgentErrorType::ProcessingError,
                    "Step " + std::to_string(i + 1) + " (" + agent->name() + ") failed: " +
                    std::string(e.what())
                ));
            }
        }

        return Result<Message, AgentError>::ok(std::move(current));
    });
}

} // namespace composition
} // namespace agenkit
