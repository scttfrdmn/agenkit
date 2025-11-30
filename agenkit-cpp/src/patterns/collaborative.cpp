/**
 * @file collaborative.cpp
 * @brief Implementation of Collaborative pattern
 */

#include "agenkit/patterns/collaborative.hpp"
#include <sstream>
#include <unordered_set>
#include <unordered_map>
#include <algorithm>

namespace agenkit {
namespace patterns {

CollaborativeAgent::CollaborativeAgent(CollaborativeConfig config)
    : agents_(std::move(config.agents))
    , max_rounds_(config.max_rounds)
    , consensus_func_(std::move(config.consensus_func))
    , merge_func_(std::move(config.merge_func))
{
    if (agents_.size() < 2) {
        throw std::invalid_argument("at least two agents are required for collaboration");
    }
    if (!merge_func_) {
        throw std::invalid_argument("merge function is required");
    }
    if (max_rounds_ == 0) {
        max_rounds_ = 3;
    }
}

std::string CollaborativeAgent::name() const {
    return "collaborative";
}

std::vector<std::string> CollaborativeAgent::capabilities() const {
    // Collect unique capabilities from all agents
    std::unordered_set<std::string> cap_set;

    for (const auto& agent : agents_) {
        auto agent_caps = agent->capabilities();
        cap_set.insert(agent_caps.begin(), agent_caps.end());
    }

    // Convert to vector
    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());

    // Add collaborative-specific capabilities
    capabilities.push_back("collaborative");
    capabilities.push_back("iterative");
    capabilities.push_back("consensus");

    return capabilities;
}

std::future<core::Result<core::Message, core::AgentError>>
CollaborativeAgent::process(core::Message message) {
    std::vector<core::Message> current_context;
    current_context.push_back(message);

    nlohmann::json rounds_data = nlohmann::json::array();
    std::string stop_reason;

    for (int round = 0; round < max_rounds_; ++round) {
        // Collect responses from all agents
        std::vector<core::Message> responses;
        responses.reserve(agents_.size());

        for (const auto& agent : agents_) {
            // Build context message with conversation history
            auto context_msg = build_context_message(current_context, round, agent->name());

            // Get agent response
            auto future = agent->process(std::move(context_msg));
            auto result = future.get();

            if (result.is_err()) {
                auto error = result.unwrap_err();
                std::ostringstream oss;
                oss << "agent " << agent->name() << " failed in round " << round
                    << ": " << error.message();

                return core::make_ready_future(
                    core::Result<core::Message, core::AgentError>::err(
                        core::AgentError(error.type(), oss.str())
                    )
                );
            }

            responses.push_back(result.unwrap());
        }

        // Check for consensus
        bool has_consensus = false;
        if (consensus_func_) {
            has_consensus = consensus_func_(responses);
        }

        // Record round
        nlohmann::json round_info = {
            {"round", round},
            {"responses", responses.size()},
            {"consensus", has_consensus}
        };
        rounds_data.push_back(round_info);

        // Stop if consensus reached
        if (has_consensus) {
            stop_reason = "consensus";

            // Merge responses
            core::Message merged = merge_func_(responses);

            // Add collaboration metadata
            merged.with_metadata("collaboration_rounds", round + 1);
            merged.with_metadata("collaboration_agents", static_cast<int>(agents_.size()));
            merged.with_metadata("stop_reason", stop_reason);
            merged.with_metadata("rounds", rounds_data);

            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::ok(merged)
            );
        }

        // Prepare next round context
        current_context.insert(current_context.end(), responses.begin(), responses.end());
    }

    // Max rounds reached
    stop_reason = "max_rounds";

    // Get final round responses (last n messages where n = agents_.size())
    std::vector<core::Message> final_responses;
    size_t start_idx = current_context.size() - agents_.size();
    for (size_t i = start_idx; i < current_context.size(); ++i) {
        final_responses.push_back(current_context[i]);
    }

    // Merge final responses
    core::Message merged = merge_func_(final_responses);

    // Add collaboration metadata
    merged.with_metadata("collaboration_rounds", max_rounds_);
    merged.with_metadata("collaboration_agents", static_cast<int>(agents_.size()));
    merged.with_metadata("stop_reason", stop_reason);
    merged.with_metadata("rounds", rounds_data);

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(merged)
    );
}

core::Message CollaborativeAgent::build_context_message(
    const std::vector<core::Message>& context,
    int round,
    const std::string& agent_name
) const {
    std::ostringstream content;

    // Add round information
    content << "=== Collaboration Round " << round << " ===\n";
    content << "Agent: " << agent_name << "\n\n";

    // Add conversation history
    if (round == 0) {
        content << "Original Request:\n";
        content << context[0].content_as_str();
    } else {
        content << "Original Request:\n";
        content << context[0].content_as_str();
        content << "\n\n--- Previous Responses ---\n\n";

        for (size_t i = 1; i < context.size(); ++i) {
            content << "Response " << i << ":\n"
                   << context[i].content_as_str() << "\n\n";
        }

        content << "--- Your Turn ---\n";
        content << "Please review the above responses and provide your refined contribution.\n";
    }

    return core::Message::with_text("user", content.str());
}

// Default consensus functions

namespace default_consensus {

bool exact_match(const std::vector<core::Message>& messages) {
    if (messages.size() <= 1) {
        return true;
    }

    std::string first_content = messages[0].content_as_str();
    for (size_t i = 1; i < messages.size(); ++i) {
        if (messages[i].content_as_str() != first_content) {
            return false;
        }
    }
    return true;
}

ConsensusFunc similarity_threshold(double /* threshold */) {
    return [](const std::vector<core::Message>& messages) {
        if (messages.size() <= 1) {
            return true;
        }

        // Simple similarity: compare common words
        // In production, use proper similarity metrics
        std::string first_content = messages[0].content_as_str();
        std::transform(first_content.begin(), first_content.end(),
                      first_content.begin(), ::tolower);

        for (size_t i = 1; i < messages.size(); ++i) {
            std::string current = messages[i].content_as_str();
            std::transform(current.begin(), current.end(),
                          current.begin(), ::tolower);

            // Simple check: if first 20 chars don't appear in current, not similar
            size_t prefix_len = std::min(first_content.length(), size_t(20));
            if (current.find(first_content.substr(0, prefix_len)) == std::string::npos) {
                return false;
            }
        }
        return true;
    };
}

bool majority_agreement(const std::vector<core::Message>& messages) {
    if (messages.size() <= 1) {
        return true;
    }

    // Count identical responses
    std::unordered_map<std::string, int> content_count;
    for (const auto& msg : messages) {
        content_count[msg.content_as_str()]++;
    }

    // Check if any content has majority
    int majority = (messages.size() / 2) + 1;
    for (const auto& [content, count] : content_count) {
        if (count >= majority) {
            return true;
        }
    }

    return false;
}

} // namespace default_consensus

// Default merge functions

namespace default_merge {

core::Message concatenate(const std::vector<core::Message>& messages) {
    if (messages.empty()) {
        return core::Message::with_text("assistant", "No responses to merge");
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

core::Message vote(const std::vector<core::Message>& messages) {
    if (messages.empty()) {
        return core::Message::with_text("assistant", "No responses to merge");
    }

    // Count votes
    std::unordered_map<std::string, int> votes;
    std::unordered_map<std::string, core::Message> msg_by_content;

    for (const auto& msg : messages) {
        std::string content = msg.content_as_str();
        votes[content]++;
        if (msg_by_content.find(content) == msg_by_content.end()) {
            msg_by_content.insert({content, msg});
        }
    }

    // Find winner
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
    result.with_metadata("total", static_cast<int>(messages.size()));

    return result;
}

core::Message first(const std::vector<core::Message>& messages) {
    if (messages.empty()) {
        return core::Message::with_text("assistant", "No responses to merge");
    }
    return messages[0];
}

core::Message last(const std::vector<core::Message>& messages) {
    if (messages.empty()) {
        return core::Message::with_text("assistant", "No responses to merge");
    }
    return messages.back();
}

} // namespace default_merge

} // namespace patterns
} // namespace agenkit
