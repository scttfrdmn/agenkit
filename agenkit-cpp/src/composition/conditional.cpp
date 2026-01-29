/**
 * @file conditional.cpp
 * @brief Implementation of ConditionalAgent
 */

#include "agenkit/composition/conditional.hpp"
#include <set>

namespace agenkit {
namespace composition {

using namespace core;

ConditionalAgent::ConditionalAgent(
    std::string name,
    std::shared_ptr<Agent> default_agent
) : name_(std::move(name)), default_agent_(std::move(default_agent)) {
}

std::vector<std::string> ConditionalAgent::capabilities() const {
    std::set<std::string> cap_set;

    // Add default agent capabilities
    for (const auto& cap : default_agent_->capabilities()) {
        cap_set.insert(cap);
    }

    // Add route agent capabilities
    for (const auto& route : routes_) {
        for (const auto& cap : route.agent->capabilities()) {
            cap_set.insert(cap);
        }
    }

    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());
    capabilities.push_back("conditional");

    return capabilities;
}

void ConditionalAgent::add_route(Condition condition, std::shared_ptr<Agent> agent) {
    routes_.push_back(ConditionalRoute{std::move(condition), std::move(agent)});
}

std::future<Result<Message, AgentError>>
ConditionalAgent::process(Message message) {
    return std::async(std::launch::async, [this, message = std::move(message)]() {
        // Try each route in order
        for (size_t i = 0; i < routes_.size(); ++i) {
            const auto& route = routes_[i];

            if (route.condition(message)) {
                try {
                    auto future = route.agent->process(message);
                    auto result = future.get();

                    if (result.is_err()) {
                        return Result<Message, AgentError>::err(AgentError(
                            AgentErrorType::ProcessingError,
                            "Route " + std::to_string(i + 1) + " (" + route.agent->name() +
                            ") failed: " + result.unwrap_err().message()
                        ));
                    }

                    auto response = std::move(result.unwrap());
                    response.with_metadata("conditional_agent_used", route.agent->name());
                    response.with_metadata("conditional_route", static_cast<double>(i + 1));
                    return Result<Message, AgentError>::ok(std::move(response));
                } catch (const std::exception& e) {
                    return Result<Message, AgentError>::err(AgentError(
                        AgentErrorType::ProcessingError,
                        "Route " + std::to_string(i + 1) + " (" + route.agent->name() +
                        ") failed: " + std::string(e.what())
                    ));
                }
            }
        }

        // No condition matched, use default agent
        try {
            auto future = default_agent_->process(message);
            auto result = future.get();

            if (result.is_err()) {
                return Result<Message, AgentError>::err(AgentError(
                    AgentErrorType::ProcessingError,
                    "Default agent (" + default_agent_->name() +
                    ") failed: " + result.unwrap_err().message()
                ));
            }

            auto response = std::move(result.unwrap());
            response.with_metadata("conditional_agent_used", default_agent_->name());
            response.with_metadata("conditional_route", "default");
            return Result<Message, AgentError>::ok(std::move(response));
        } catch (const std::exception& e) {
            return Result<Message, AgentError>::err(AgentError(
                AgentErrorType::ProcessingError,
                "Default agent (" + default_agent_->name() +
                ") failed: " + std::string(e.what())
            ));
        }
    });
}

// Condition helpers

Condition content_contains(const std::string& substr) {
    return [substr](const Message& message) {
        return message.content_as_str().find(substr) != std::string::npos;
    };
}

Condition role_equals(const std::string& role) {
    return [role](const Message& message) {
        return message.role() == role;
    };
}

} // namespace composition
} // namespace agenkit
