/**
 * @file multiagent.cpp
 * @brief Implementation of Multi-agent pattern
 */

#include "agenkit/patterns/multiagent.hpp"
#include <sstream>

namespace agenkit {
namespace patterns {

// MultiAgentOrchestrator implementation

MultiAgentOrchestrator::MultiAgentOrchestrator(MultiAgentStrategy strategy)
    : strategy_(strategy) {}

std::string MultiAgentOrchestrator::name() const {
    return "multiagent_orchestrator";
}

std::vector<std::string> MultiAgentOrchestrator::capabilities() const {
    return {"orchestration", "multi-agent", "coordination", "delegation"};
}

std::future<core::Result<core::Message, core::AgentError>>
MultiAgentOrchestrator::process(core::Message message) {
    switch (strategy_) {
        case MultiAgentStrategy::Sequential:
            return core::make_ready_future(execute_sequential(message));
        case MultiAgentStrategy::Parallel:
            return core::make_ready_future(execute_parallel(message));
        case MultiAgentStrategy::Delegate:
            // For now, delegate uses sequential execution
            return core::make_ready_future(execute_sequential(message));
    }

    // Should never reach here
    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::err(
            core::AgentError(core::AgentErrorType::Internal, "Invalid strategy")
        )
    );
}

void MultiAgentOrchestrator::register_agent(
    const std::string& name,
    std::shared_ptr<core::Agent> agent
) {
    agents_[name] = agent;
}

void MultiAgentOrchestrator::unregister_agent(const std::string& name) {
    agents_.erase(name);
}

std::vector<std::string> MultiAgentOrchestrator::list_agents() const {
    std::vector<std::string> names;
    names.reserve(agents_.size());
    for (const auto& pair : agents_) {
        names.push_back(pair.first);
    }
    return names;
}

std::vector<AgentTask> MultiAgentOrchestrator::get_tasks() const {
    return tasks_;
}

void MultiAgentOrchestrator::clear_tasks() {
    tasks_.clear();
}

void MultiAgentOrchestrator::set_strategy(MultiAgentStrategy strategy) {
    strategy_ = strategy;
}

MultiAgentStrategy MultiAgentOrchestrator::get_strategy() const {
    return strategy_;
}

core::Result<core::Message, core::AgentError>
MultiAgentOrchestrator::execute_sequential(const core::Message& message) {
    std::vector<std::string> results;
    results.reserve(agents_.size());

    for (auto& [agent_name, agent] : agents_) {
        AgentTask task;
        task.agent_name = agent_name;
        task.description = message.content_as_str();
        task.status = TaskStatus::InProgress;

        tasks_.push_back(task);

        // Execute agent
        auto future = agent->process(core::Message(message));
        auto result = future.get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            task.result = response.content_as_str();
            task.status = TaskStatus::Completed;

            results.push_back(agent_name + ": " + response.content_as_str());
        } else {
            auto error = result.unwrap_err();
            task.error = error.message();
            task.status = TaskStatus::Failed;

            results.push_back(agent_name + ": Failed - " + error.message());
        }

        // Update task in list
        tasks_.back() = task;
    }

    // Combine results
    std::ostringstream combined;
    for (size_t i = 0; i < results.size(); i++) {
        if (i > 0) combined << "\n\n";
        combined << results[i];
    }

    auto response = core::Message::with_text("assistant", combined.str());
    response.with_metadata("pattern", "multiagent");
    response.with_metadata("strategy", "sequential");
    response.with_metadata("agent_count", static_cast<int>(agents_.size()));
    response.with_metadata("tasks_completed", static_cast<int>(results.size()));

    return core::Result<core::Message, core::AgentError>::ok(response);
}

core::Result<core::Message, core::AgentError>
MultiAgentOrchestrator::execute_parallel(const core::Message& message) {
    // Launch all agents in parallel using std::async
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    std::vector<std::string> agent_names;
    std::vector<AgentTask> pending_tasks;

    for (auto& [agent_name, agent] : agents_) {
        agent_names.push_back(agent_name);

        AgentTask task;
        task.agent_name = agent_name;
        task.description = message.content_as_str();
        task.status = TaskStatus::InProgress;
        pending_tasks.push_back(task);

        // Use std::async with launch::async policy to force parallel execution
        // Capture agent pointer separately to avoid C++20 structured binding capture issue
        auto agent_ptr = agent;
        auto future = std::async(std::launch::async, [agent_ptr, msg = core::Message(message)]() mutable {
            return agent_ptr->process(std::move(msg)).get();
        });
        futures.push_back(std::move(future));
    }

    // Collect results from all parallel executions
    std::vector<std::string> results;
    results.reserve(agent_names.size());

    for (size_t i = 0; i < futures.size(); i++) {
        auto& task = pending_tasks[i];
        auto result = futures[i].get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            task.result = response.content_as_str();
            task.status = TaskStatus::Completed;

            results.push_back(agent_names[i] + ": " + response.content_as_str());
        } else {
            auto error = result.unwrap_err();
            task.error = error.message();
            task.status = TaskStatus::Failed;

            results.push_back(agent_names[i] + ": Failed - " + error.message());
        }

        tasks_.push_back(task);
    }

    // Combine results
    std::ostringstream combined;
    for (size_t i = 0; i < results.size(); i++) {
        if (i > 0) combined << "\n\n";
        combined << results[i];
    }

    auto response = core::Message::with_text("assistant", combined.str());
    response.with_metadata("pattern", "multiagent");
    response.with_metadata("strategy", "parallel");
    response.with_metadata("agent_count", static_cast<int>(agents_.size()));
    response.with_metadata("tasks_completed", static_cast<int>(results.size()));

    return core::Result<core::Message, core::AgentError>::ok(response);
}

// ConsensusAgent implementation

ConsensusAgent::ConsensusAgent() {}

std::string ConsensusAgent::name() const {
    return "consensus";
}

std::vector<std::string> ConsensusAgent::capabilities() const {
    return {"consensus", "multi-perspective", "aggregation"};
}

std::future<core::Result<core::Message, core::AgentError>>
ConsensusAgent::process(core::Message message) {
    // Launch all agents in parallel using std::async
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    futures.reserve(agents_.size());

    for (auto& agent : agents_) {
        // Capture agent pointer separately to avoid potential issues
        auto agent_ptr = agent;
        auto future = std::async(std::launch::async, [agent_ptr, msg = core::Message(message)]() mutable {
            return agent_ptr->process(std::move(msg)).get();
        });
        futures.push_back(std::move(future));
    }

    // Collect responses from all parallel executions
    std::vector<std::string> responses;
    responses.reserve(agents_.size());

    for (auto& future : futures) {
        auto result = future.get();

        if (result.is_ok()) {
            responses.push_back(result.unwrap().content_as_str());
        } else {
            responses.push_back("Error: " + result.unwrap_err().message());
        }
    }

    // Form consensus
    std::ostringstream consensus;
    consensus << "Consensus from " << responses.size() << " agents:\n\n";

    for (size_t i = 0; i < responses.size(); i++) {
        if (i > 0) consensus << "\n\n";
        consensus << "Agent " << (i + 1) << ": " << responses[i];
    }

    auto response = core::Message::with_text("assistant", consensus.str());
    response.with_metadata("pattern", "consensus");
    response.with_metadata("agent_count", static_cast<int>(agents_.size()));

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(response)
    );
}

void ConsensusAgent::add_agent(std::shared_ptr<core::Agent> agent) {
    agents_.push_back(agent);
}

void ConsensusAgent::clear_agents() {
    agents_.clear();
}

size_t ConsensusAgent::agent_count() const {
    return agents_.size();
}

} // namespace patterns
} // namespace agenkit
