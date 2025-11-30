/**
 * @file parallel.cpp
 * @brief Implementation of Parallel pattern
 */

#include "agenkit/patterns/parallel.hpp"
#include <sstream>
#include <unordered_set>
#include <unordered_map>
#include <future>
#include <thread>

namespace agenkit {
namespace patterns {

ParallelAgent::ParallelAgent(
    std::vector<std::shared_ptr<core::Agent>> agents,
    AggregatorFunc aggregator
)
    : agents_(std::move(agents))
    , aggregator_(std::move(aggregator))
{
    if (agents_.empty()) {
        throw std::invalid_argument("at least one agent is required");
    }
    if (!aggregator_) {
        throw std::invalid_argument("aggregator function is required");
    }
}

std::string ParallelAgent::name() const {
    return "parallel";
}

std::vector<std::string> ParallelAgent::capabilities() const {
    // Collect unique capabilities from all agents
    std::unordered_set<std::string> cap_set;

    for (const auto& agent : agents_) {
        auto agent_caps = agent->capabilities();
        cap_set.insert(agent_caps.begin(), agent_caps.end());
    }

    // Convert to vector
    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());

    // Add parallel-specific capabilities
    capabilities.push_back("parallel");
    capabilities.push_back("ensemble");

    return capabilities;
}

std::future<core::Result<core::Message, core::AgentError>>
ParallelAgent::process(core::Message message) {
    // Launch all agents concurrently
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;
    futures.reserve(agents_.size());

    for (auto& agent : agents_) {
        futures.push_back(agent->process(core::Message(message)));
    }

    // Collect all results
    std::vector<core::Message> successes;
    nlohmann::json errors = nlohmann::json::array();

    for (size_t i = 0; i < futures.size(); ++i) {
        auto result = futures[i].get();

        if (result.is_ok()) {
            successes.push_back(result.unwrap());
        } else {
            auto error = result.unwrap_err();
            nlohmann::json error_info = {
                {"agent", agents_[i]->name()},
                {"error", error.message()}
            };
            errors.push_back(error_info);
        }
    }

    // Check if all agents failed
    if (successes.empty()) {
        std::ostringstream oss;
        oss << "all agents failed: " << errors.dump();

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(core::AgentErrorType::ProcessingError, oss.str())
            )
        );
    }

    // Aggregate successful results
    core::Message aggregated = aggregator_(successes);

    // Add parallel execution metadata
    aggregated.with_metadata("parallel_agents", static_cast<int>(agents_.size()));
    aggregated.with_metadata("successful_agents", static_cast<int>(successes.size()));
    if (!errors.empty()) {
        aggregated.with_metadata("errors", errors);
    }

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(aggregated)
    );
}

// Default aggregators implementation

namespace default_aggregators {

core::Message first(const std::vector<core::Message>& messages) {
    if (messages.empty()) {
        return core::Message::with_text("assistant", "No results to aggregate");
    }
    return messages[0];
}

core::Message concatenate(const std::vector<core::Message>& messages) {
    if (messages.empty()) {
        return core::Message::with_text("assistant", "No results to aggregate");
    }

    std::ostringstream combined;
    for (size_t i = 0; i < messages.size(); ++i) {
        if (i > 0) {
            combined << "\n\n---\n\n";
        }
        combined << messages[i].content_as_str();
    }

    return core::Message::with_text("assistant", combined.str());
}

core::Message majority_vote(const std::vector<core::Message>& messages) {
    if (messages.empty()) {
        return core::Message::with_text("assistant", "No results to aggregate");
    }

    // Count occurrences of each response
    std::unordered_map<std::string, int> votes;
    std::unordered_map<std::string, core::Message> msg_by_content;

    for (const auto& msg : messages) {
        std::string content = msg.content_as_str();
        votes[content]++;
        if (msg_by_content.find(content) == msg_by_content.end()) {
            msg_by_content.insert({content, msg});
        }
    }

    // Find most common response
    int max_votes = 0;
    std::string winner;
    for (const auto& [content, count] : votes) {
        if (count > max_votes) {
            max_votes = count;
            winner = content;
        }
    }

    core::Message result = msg_by_content.at(winner);
    result.with_metadata("votes", max_votes);
    result.with_metadata("total_agents", static_cast<int>(messages.size()));

    return result;
}

} // namespace default_aggregators

} // namespace patterns
} // namespace agenkit
