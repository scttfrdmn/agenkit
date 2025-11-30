/**
 * @file sequential.cpp
 * @brief Implementation of Sequential pattern
 */

#include "agenkit/patterns/sequential.hpp"
#include <sstream>
#include <unordered_set>

namespace agenkit {
namespace patterns {

SequentialAgent::SequentialAgent(std::vector<std::shared_ptr<core::Agent>> agents)
    : agents_(std::move(agents))
{
    if (agents_.empty()) {
        throw std::invalid_argument("at least one agent is required");
    }
}

std::string SequentialAgent::name() const {
    return "sequential";
}

std::vector<std::string> SequentialAgent::capabilities() const {
    // Collect unique capabilities from all agents
    std::unordered_set<std::string> cap_set;

    for (const auto& agent : agents_) {
        auto agent_caps = agent->capabilities();
        cap_set.insert(agent_caps.begin(), agent_caps.end());
    }

    // Convert to vector
    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());

    // Add sequential-specific capabilities
    capabilities.push_back("sequential");
    capabilities.push_back("pipeline");

    return capabilities;
}

std::future<core::Result<core::Message, core::AgentError>>
SequentialAgent::process(core::Message message) {
    // Track pipeline stages for observability
    nlohmann::json stages = nlohmann::json::array();

    // Pass message through each agent
    core::Message current = std::move(message);

    for (size_t i = 0; i < agents_.size(); ++i) {
        auto& agent = agents_[i];

        // Process with current agent
        auto future = agent->process(core::Message(current));
        auto result = future.get();

        if (result.is_err()) {
            auto error = result.unwrap_err();
            std::ostringstream oss;
            oss << "agent " << i << " (" << agent->name() << ") failed: " << error.message();

            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(
                    core::AgentError(error.type(), oss.str())
                )
            );
        }

        // Extract result
        current = result.unwrap();

        // Record stage metadata
        nlohmann::json stage_info = {
            {"agent", agent->name()},
            {"stage", i}
        };

        if (!current.metadata().is_null() && current.metadata().is_object()) {
            stage_info["metadata"] = current.metadata();
        }

        stages.push_back(stage_info);
    }

    // Add pipeline metadata to final result
    current.with_metadata("pipeline_stages", stages);
    current.with_metadata("pipeline_length", static_cast<int>(agents_.size()));

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(current)
    );
}

} // namespace patterns
} // namespace agenkit
