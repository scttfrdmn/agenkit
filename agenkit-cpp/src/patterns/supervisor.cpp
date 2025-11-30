/**
 * @file supervisor.cpp
 * @brief Implementation of Supervisor pattern
 */

#include "agenkit/patterns/supervisor.hpp"
#include <sstream>
#include <unordered_set>
#include <algorithm>

namespace agenkit {
namespace patterns {

SupervisorAgent::SupervisorAgent(
    std::shared_ptr<PlannerAgent> planner,
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists
)
    : planner_(std::move(planner))
    , specialists_(std::move(specialists))
{
    if (!planner_) {
        throw std::invalid_argument("planner is required");
    }
    if (specialists_.empty()) {
        throw std::invalid_argument("at least one specialist is required");
    }
}

std::string SupervisorAgent::name() const {
    return "supervisor";
}

std::vector<std::string> SupervisorAgent::capabilities() const {
    // Collect unique capabilities from all agents
    std::unordered_set<std::string> cap_set;

    // Add planner capabilities
    auto planner_caps = planner_->capabilities();
    cap_set.insert(planner_caps.begin(), planner_caps.end());

    // Add specialist capabilities
    for (const auto& [type, specialist] : specialists_) {
        auto spec_caps = specialist->capabilities();
        cap_set.insert(spec_caps.begin(), spec_caps.end());
    }

    // Convert to vector
    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());

    // Add supervisor-specific capabilities
    capabilities.push_back("supervisor");
    capabilities.push_back("hierarchical");
    capabilities.push_back("coordination");

    return capabilities;
}

std::future<core::Result<core::Message, core::AgentError>>
SupervisorAgent::process(core::Message message) {
    // Step 1: Plan - decompose task into subtasks
    auto plan_result = planner_->plan(message);

    if (plan_result.is_err()) {
        auto error = plan_result.unwrap_err();
        std::ostringstream oss;
        oss << "planning failed: " << error.message();

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(error.type(), oss.str())
            )
        );
    }

    auto subtasks = plan_result.unwrap();

    // If no subtasks, let planner handle directly
    if (subtasks.empty()) {
        return planner_->process(std::move(message));
    }

    // Step 2: Validate specialist availability
    for (size_t i = 0; i < subtasks.size(); ++i) {
        const auto& subtask = subtasks[i];
        if (specialists_.find(subtask.type) == specialists_.end()) {
            std::vector<std::string> available_types;
            available_types.reserve(specialists_.size());
            for (const auto& [type, _] : specialists_) {
                available_types.push_back(type);
            }

            std::ostringstream oss;
            oss << "subtask " << i << " references unknown specialist type '"
                << subtask.type << "' (available: ";
            for (size_t j = 0; j < available_types.size(); ++j) {
                if (j > 0) oss << ", ";
                oss << available_types[j];
            }
            oss << ")";

            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(
                    core::AgentError(core::AgentErrorType::InvalidInput, oss.str())
                )
            );
        }
    }

    // Step 3: Execute subtasks with specialists
    std::unordered_map<std::string, core::Message> results;
    nlohmann::json execution_order = nlohmann::json::array();

    for (size_t i = 0; i < subtasks.size(); ++i) {
        const auto& subtask = subtasks[i];
        auto specialist = specialists_[subtask.type];

        // Execute subtask
        auto future = specialist->process(core::Message(subtask.message));
        auto result = future.get();

        if (result.is_err()) {
            auto error = result.unwrap_err();
            std::ostringstream oss;
            oss << "specialist '" << subtask.type << "' failed on subtask "
                << i << ": " << error.message();

            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(
                    core::AgentError(error.type(), oss.str())
                )
            );
        }

        // Store result keyed by specialist type and index for synthesis
        std::ostringstream result_key;
        result_key << subtask.type << "_" << i;
        results.insert({result_key.str(), result.unwrap()});

        // Track execution order
        nlohmann::json exec_info = {
            {"index", i},
            {"type", subtask.type},
            {"specialist", specialist->name()}
        };
        execution_order.push_back(exec_info);
    }

    // Step 4: Synthesize - combine specialist results
    auto synthesis_result = planner_->synthesize(message, results);

    if (synthesis_result.is_err()) {
        auto error = synthesis_result.unwrap_err();
        std::ostringstream oss;
        oss << "synthesis failed: " << error.message();

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(error.type(), oss.str())
            )
        );
    }

    auto final = synthesis_result.unwrap();

    // Add supervisor metadata
    final.with_metadata("supervisor_subtasks", static_cast<int>(subtasks.size()));
    final.with_metadata("supervisor_specialists", static_cast<int>(specialists_.size()));
    final.with_metadata("execution_order", execution_order);

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(final)
    );
}

// SimplePlanner implementation

SimplePlanner::SimplePlanner(std::shared_ptr<core::Agent> agent)
    : agent_(std::move(agent))
{
    if (!agent_) {
        throw std::invalid_argument("agent is required");
    }
}

std::string SimplePlanner::name() const {
    return "simple_planner";
}

std::vector<std::string> SimplePlanner::capabilities() const {
    auto caps = agent_->capabilities();
    caps.push_back("planning");
    caps.push_back("synthesis");
    return caps;
}

std::future<core::Result<core::Message, core::AgentError>>
SimplePlanner::process(core::Message message) {
    return agent_->process(std::move(message));
}

core::Result<std::vector<Subtask>, core::AgentError>
SimplePlanner::plan(const core::Message& /* message */) {
    // In a real implementation, this would prompt the LLM to create a plan
    // and parse the response into Subtask structures.
    // For now, return empty to trigger direct processing.
    return core::Result<std::vector<Subtask>, core::AgentError>::ok(
        std::vector<Subtask>()
    );
}

core::Result<core::Message, core::AgentError>
SimplePlanner::synthesize(
    const core::Message& /* original */,
    const std::unordered_map<std::string, core::Message>& results
) {
    // Combine all results
    std::ostringstream combined;
    combined << "Synthesis of specialist results:\n\n";

    for (const auto& [key, result] : results) {
        combined << "Result from " << key << ":\n"
                 << result.content_as_str() << "\n\n";
    }

    return core::Result<core::Message, core::AgentError>::ok(
        core::Message::with_text("assistant", combined.str())
    );
}

} // namespace patterns
} // namespace agenkit
