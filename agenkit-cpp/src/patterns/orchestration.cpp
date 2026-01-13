/**
 * @file orchestration.cpp
 * @brief Implementation of Orchestration pattern
 */

#include "agenkit/patterns/orchestration.hpp"
#include "agenkit/infrastructure/thread_pool.hpp"
#include <stdexcept>
#include <sstream>

namespace agenkit {
namespace patterns {

OrchestrationAgent::OrchestrationAgent(OrchestrationConfig config)
    : config_(std::move(config))
    , combiner_(default_combiner)
{
}

void OrchestrationAgent::add_agent(const std::string& name, std::shared_ptr<core::Agent> agent) {
    if (name.empty()) {
        throw std::invalid_argument("agent name cannot be empty");
    }
    if (!agent) {
        throw std::invalid_argument("agent cannot be null");
    }
    agents_[name] = agent;
}

bool OrchestrationAgent::remove_agent(const std::string& name) {
    return agents_.erase(name) > 0;
}

std::shared_ptr<core::Agent> OrchestrationAgent::get_agent(const std::string& name) const {
    auto it = agents_.find(name);
    if (it != agents_.end()) {
        return it->second;
    }
    return nullptr;
}

const std::unordered_map<std::string, std::shared_ptr<core::Agent>>&
OrchestrationAgent::get_agents() const {
    return agents_;
}

void OrchestrationAgent::set_strategy(OrchestrationStrategy strategy) {
    config_.strategy = strategy;
}

OrchestrationStrategy OrchestrationAgent::get_strategy() const {
    return config_.strategy;
}

void OrchestrationAgent::set_routing(RoutingFunction router) {
    router_ = std::move(router);
}

void OrchestrationAgent::set_combiner(CombinerFunction combiner) {
    combiner_ = std::move(combiner);
}

const std::vector<OrchestrationStep>& OrchestrationAgent::get_history() const {
    return history_;
}

void OrchestrationAgent::clear_history() {
    history_.clear();
}

const OrchestrationConfig& OrchestrationAgent::get_config() const {
    return config_;
}

void OrchestrationAgent::set_config(const OrchestrationConfig& config) {
    config_ = config;
}

std::string OrchestrationAgent::name() const {
    return "orchestration";
}

std::vector<std::string> OrchestrationAgent::capabilities() const {
    return {"orchestration", "coordination", "multi-agent"};
}

std::future<core::Result<core::Message, core::AgentError>>
OrchestrationAgent::process(core::Message message) {
    // Clear previous history
    history_.clear();

    // Check if we have agents
    if (agents_.empty()) {
        auto error = core::AgentError(
            core::AgentErrorType::InvalidInput,
            "no agents registered for orchestration"
        );
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(error)
        );
    }

    // Execute based on strategy
    switch (config_.strategy) {
        case OrchestrationStrategy::Sequential:
            return core::make_ready_future(execute_sequential(std::move(message)));

        case OrchestrationStrategy::Parallel:
            return core::make_ready_future(execute_parallel(std::move(message)));

        case OrchestrationStrategy::Conditional:
            return core::make_ready_future(execute_conditional(std::move(message)));

        case OrchestrationStrategy::Custom:
            // Custom strategy uses sequential with custom router
            return core::make_ready_future(execute_sequential(std::move(message)));

        default:
            auto error = core::AgentError(
                core::AgentErrorType::Internal,
                "unknown orchestration strategy"
            );
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(error)
            );
    }
}

core::Result<core::Message, core::AgentError>
OrchestrationAgent::execute_sequential(core::Message message) {
    if (!router_) {
        auto error = core::AgentError(
            core::AgentErrorType::InvalidInput,
            "no routing function set for sequential orchestration"
        );
        return core::Result<core::Message, core::AgentError>::err(error);
    }

    core::Message current_message = std::move(message);

    for (int step = 1; step <= config_.max_steps; step++) {
        // Ask router which agent to invoke next
        std::string next_agent = router_(current_message);

        // Empty string means we're done
        if (next_agent.empty()) {
            add_orchestration_metadata(current_message);
            return core::Result<core::Message, core::AgentError>::ok(current_message);
        }

        // Invoke the agent
        auto result = invoke_agent(next_agent, current_message, step);

        if (result.is_err()) {
            if (config_.stop_on_error) {
                return result;
            }
            // Continue with current message on error
            continue;
        }

        current_message = result.unwrap();
    }

    // Reached max steps
    add_orchestration_metadata(current_message);
    return core::Result<core::Message, core::AgentError>::ok(current_message);
}

core::Result<core::Message, core::AgentError>
OrchestrationAgent::execute_parallel(core::Message message) {
    // Launch all agents in parallel using std::async
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    std::vector<std::string> agent_names;

    for (const auto& [name, agent] : agents_) {
        agent_names.push_back(name);

        // Use thread pool for parallel execution
        // Capture agent pointer separately to avoid C++20 structured binding capture issue
        auto agent_ptr = agent;
        auto future = infrastructure::global_thread_pool().enqueue([agent_ptr, msg = core::Message(message)]() mutable {
            return agent_ptr->process(std::move(msg)).get();
        });
        futures.push_back(std::move(future));
    }

    // Collect results (all agents running in parallel now)
    std::vector<core::Message> results;
    int step = 1;

    for (size_t i = 0; i < futures.size(); i++) {
        auto result = futures[i].get();

        if (result.is_ok()) {
            auto output = result.unwrap();
            OrchestrationStep orch_step{
                step++,
                agent_names[i],
                core::Message(message),
                output,
                true,
                "",
                nlohmann::json::object()
            };
            history_.push_back(orch_step);
            results.push_back(output);
        } else {
            auto error_msg = result.unwrap_err().message();
            OrchestrationStep orch_step{
                step++,
                agent_names[i],
                core::Message(message),
                core::Message::with_text("assistant", ""),
                false,
                error_msg,
                nlohmann::json::object()
            };
            history_.push_back(orch_step);

            if (config_.stop_on_error) {
                return result;
            }
        }
    }

    // Combine results
    auto combined = combiner_(results);
    add_orchestration_metadata(combined);

    return core::Result<core::Message, core::AgentError>::ok(combined);
}

core::Result<core::Message, core::AgentError>
OrchestrationAgent::execute_conditional(core::Message message) {
    // Conditional is similar to sequential but router determines flow
    return execute_sequential(std::move(message));
}

core::Result<core::Message, core::AgentError>
OrchestrationAgent::invoke_agent(
    const std::string& agent_name,
    core::Message message,
    int step
) {
    auto agent = get_agent(agent_name);
    if (!agent) {
        OrchestrationStep orch_step{
            step,
            agent_name,
            core::Message(message),
            core::Message::with_text("assistant", ""),
            false,
            "Agent not found: " + agent_name,
            nlohmann::json::object()
        };
        history_.push_back(orch_step);

        auto error = core::AgentError(
            core::AgentErrorType::NotFound,
            "agent not found: " + agent_name
        );
        return core::Result<core::Message, core::AgentError>::err(error);
    }

    // Invoke agent
    auto future = agent->process(core::Message(message));
    auto result = future.get();

    // Record step
    if (result.is_ok()) {
        OrchestrationStep orch_step{
            step,
            agent_name,
            core::Message(message),
            result.unwrap(),
            true,
            "",
            nlohmann::json::object()
        };
        history_.push_back(orch_step);
    } else {
        OrchestrationStep orch_step{
            step,
            agent_name,
            core::Message(message),
            core::Message::with_text("assistant", ""),
            false,
            result.unwrap_err().message(),
            nlohmann::json::object()
        };
        history_.push_back(orch_step);
    }

    return result;
}

core::Message OrchestrationAgent::default_combiner(const std::vector<core::Message>& messages) {
    if (messages.empty()) {
        return core::Message::with_text("assistant", "No results to combine");
    }

    if (messages.size() == 1) {
        return messages[0];
    }

    // Concatenate all message contents
    std::ostringstream combined;
    for (size_t i = 0; i < messages.size(); i++) {
        if (i > 0) {
            combined << "\n\n";
        }
        combined << "Agent " << (i + 1) << " response:\n";
        combined << messages[i].content_as_str();
    }

    return core::Message::with_text("assistant", combined.str());
}

void OrchestrationAgent::add_orchestration_metadata(core::Message& message) {
    message.with_metadata("orchestration_steps", static_cast<int>(history_.size()));
    message.with_metadata("pattern", "orchestration");
    message.with_metadata("strategy", static_cast<int>(config_.strategy));

    // Add agent names that were invoked
    std::vector<std::string> invoked_agents;
    for (const auto& step : history_) {
        invoked_agents.push_back(step.agent_name);
    }
    message.with_metadata("invoked_agents", invoked_agents);
}

} // namespace patterns
} // namespace agenkit
