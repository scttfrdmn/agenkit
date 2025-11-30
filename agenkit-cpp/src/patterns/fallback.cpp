/**
 * @file fallback.cpp
 * @brief Implementation of Fallback pattern
 */

#include "agenkit/patterns/fallback.hpp"
#include <sstream>
#include <unordered_set>

namespace agenkit {
namespace patterns {

FallbackAgent::FallbackAgent(std::vector<std::shared_ptr<core::Agent>> agents)
    : agents_(std::move(agents))
{
    if (agents_.empty()) {
        throw std::invalid_argument("at least one agent is required");
    }
}

std::string FallbackAgent::name() const {
    return "fallback";
}

std::vector<std::string> FallbackAgent::capabilities() const {
    // Collect unique capabilities from all agents
    std::unordered_set<std::string> cap_set;

    for (const auto& agent : agents_) {
        auto agent_caps = agent->capabilities();
        cap_set.insert(agent_caps.begin(), agent_caps.end());
    }

    // Convert to vector
    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());

    // Add fallback-specific capabilities
    capabilities.push_back("fallback");
    capabilities.push_back("retry");
    capabilities.push_back("high-availability");

    return capabilities;
}

std::future<core::Result<core::Message, core::AgentError>>
FallbackAgent::process(core::Message message) {
    nlohmann::json failed_attempts = nlohmann::json::array();

    for (size_t i = 0; i < agents_.size(); ++i) {
        auto& agent = agents_[i];

        // Try agent
        auto future = agent->process(core::Message(message));
        auto result = future.get();

        // If successful, return immediately
        if (result.is_ok()) {
            auto response = result.unwrap();

            // Add fallback metadata
            response.with_metadata("fallback_attempts", static_cast<int>(i + 1));
            response.with_metadata("fallback_success_index", static_cast<int>(i));
            response.with_metadata("fallback_success_agent", agent->name());
            response.with_metadata("fallback_total_agents", static_cast<int>(agents_.size()));

            // Include failed attempts for observability
            if (i > 0) {
                response.with_metadata("fallback_failed_attempts", failed_attempts);
            }

            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::ok(response)
            );
        }

        // Agent failed, record error
        auto error = result.unwrap_err();
        nlohmann::json attempt_info = {
            {"index", i},
            {"agent", agent->name()},
            {"error", error.message()}
        };
        failed_attempts.push_back(attempt_info);
    }

    // All agents failed
    std::ostringstream oss;
    oss << "all " << agents_.size() << " agents failed:\n";
    for (const auto& attempt : failed_attempts) {
        oss << "  [" << attempt["index"] << "] " << attempt["agent"]
            << ": " << attempt["error"] << "\n";
    }

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::err(
            core::AgentError(core::AgentErrorType::ProcessingError, oss.str())
        )
    );
}

// RecoveryAgent implementation

RecoveryAgent::RecoveryAgent(
    std::shared_ptr<core::Agent> agent,
    RecoveryFunc recovery_func
)
    : agent_(std::move(agent))
    , recovery_func_(std::move(recovery_func))
{
    if (!agent_) {
        throw std::invalid_argument("agent is required");
    }
    if (!recovery_func_) {
        throw std::invalid_argument("recovery function is required");
    }
}

std::string RecoveryAgent::name() const {
    return agent_->name() + "+Recovery";
}

std::vector<std::string> RecoveryAgent::capabilities() const {
    auto caps = agent_->capabilities();
    caps.push_back("recovery");
    caps.push_back("error-handling");
    return caps;
}

std::future<core::Result<core::Message, core::AgentError>>
RecoveryAgent::process(core::Message message) {
    auto future = agent_->process(core::Message(message));
    auto result = future.get();

    if (result.is_ok()) {
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(result.unwrap())
        );
    }

    // Primary agent failed, try recovery
    auto error = result.unwrap_err();
    auto recovery_result = recovery_func_(message, error);

    if (recovery_result.is_err()) {
        auto recovery_err = recovery_result.unwrap_err();
        std::ostringstream oss;
        oss << "primary agent failed: " << error.message()
            << "; recovery failed: " << recovery_err.message();

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(error.type(), oss.str())
            )
        );
    }

    auto recovered = recovery_result.unwrap();

    // Add recovery metadata
    recovered.with_metadata("recovery_used", true);
    recovered.with_metadata("original_error", error.message());

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(recovered)
    );
}

// Default recovery strategies

namespace default_recovery {

RecoveryFunc static_message(const std::string& message) {
    return [message](const core::Message& /* msg */, const core::AgentError& /* err */) {
        return core::Result<core::Message, core::AgentError>::ok(
            core::Message::with_text("assistant", message)
        );
    };
}

RecoveryFunc empty_response() {
    return [](const core::Message& /* msg */, const core::AgentError& /* err */) {
        return core::Result<core::Message, core::AgentError>::ok(
            core::Message::with_text("assistant", "")
        );
    };
}

} // namespace default_recovery

} // namespace patterns
} // namespace agenkit
