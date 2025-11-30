/**
 * @file collaborative.hpp
 * @brief Collaborative peer-to-peer agent pattern
 *
 * This module provides the Collaborative pattern for peer-to-peer agent collaboration with
 * iterative refinement. Multiple agents work together, each contributing their perspective
 * and refining the collective output through rounds.
 */

#ifndef AGENKIT_PATTERNS_COLLABORATIVE_HPP
#define AGENKIT_PATTERNS_COLLABORATIVE_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <vector>
#include <string>
#include <functional>

namespace agenkit {
namespace patterns {

/**
 * @brief Function type for determining consensus among agents
 *
 * The function receives all agent responses from a round and returns true
 * if consensus is achieved. Common strategies include:
 * - Content similarity threshold
 * - Voting on same answer
 * - Agreement indicators in responses
 * - Convergence metrics
 */
using ConsensusFunc = std::function<bool(const std::vector<core::Message>&)>;

/**
 * @brief Function type for merging multiple agent responses
 *
 * The function receives all responses and produces a merged output.
 * Common strategies include:
 * - Voting/majority rule
 * - Weighted combination
 * - Concatenation with synthesis
 * - Best response selection
 */
using MergeFunc = std::function<core::Message(const std::vector<core::Message>&)>;

/**
 * @brief Configuration for CollaborativeAgent
 */
struct CollaborativeConfig {
    /// Agents participating in collaboration
    std::vector<std::shared_ptr<core::Agent>> agents;
    /// MaxRounds limits iteration (default: 3)
    int max_rounds = 3;
    /// ConsensusFunc detects agreement (optional)
    ConsensusFunc consensus_func;
    /// MergeFunc combines responses (required)
    MergeFunc merge_func;
};

/**
 * @brief Collaborative agent for peer-to-peer iterative refinement
 *
 * The CollaborativeAgent enables peer collaboration with iterative refinement.
 * Agents work together in rounds, each seeing previous responses and
 * contributing refinements. The process continues until consensus is
 * reached or maximum rounds are exhausted.
 *
 * Key concepts:
 * - Peer-to-peer collaboration (no hierarchy)
 * - Iterative refinement through rounds
 * - Consensus detection or max rounds limit
 * - Each agent sees all previous responses
 *
 * Performance characteristics:
 * - Time: O(rounds * n agents) worst case
 * - Memory: O(rounds * n agents * message size)
 * - Early termination on consensus
 *
 * Example use cases:
 * - Code review: multiple reviewers provide feedback
 * - Document editing: iterative improvements from editors
 * - Decision making: collaborative analysis and consensus
 * - Creative writing: multiple perspectives and refinement
 * - Research: peer review and iteration
 *
 * The collaborative pattern is ideal when multiple perspectives improve
 * output quality through discussion and refinement.
 *
 * @example
 * @code
 * auto merge = [](const std::vector<core::Message>& messages) {
 *     // Return last response (most refined)
 *     return messages.back();
 * };
 *
 * CollaborativeConfig config{
 *     {agent1, agent2, agent3}, // agents
 *     3,                         // max_rounds
 *     nullptr,                   // no consensus check
 *     merge                      // merge function
 * };
 *
 * CollaborativeAgent collaborative(config);
 * auto msg = core::Message::with_text("user", "Review this code");
 * auto result = collaborative.process(std::move(msg)).get();
 * @endcode
 */
class CollaborativeAgent : public core::Agent {
public:
    /**
     * @brief Construct a collaborative agent
     * @param config Configuration with agents and collaboration settings
     * @throws std::invalid_argument if config is invalid
     */
    explicit CollaborativeAgent(CollaborativeConfig config);

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::vector<std::shared_ptr<core::Agent>> agents_;
    int max_rounds_;
    ConsensusFunc consensus_func_;
    MergeFunc merge_func_;

    /**
     * @brief Build context message with conversation history
     * @param context Message history
     * @param round Current round number
     * @param agent_name Name of agent receiving context
     * @return Context message
     */
    core::Message build_context_message(
        const std::vector<core::Message>& context,
        int round,
        const std::string& agent_name
    ) const;
};

/**
 * @brief Default consensus detection strategies
 */
namespace default_consensus {

/**
 * @brief Requires all responses to be identical
 * @param messages Vector of messages to check
 * @return true if all messages have identical content
 */
bool exact_match(const std::vector<core::Message>& messages);

/**
 * @brief Creates similarity threshold consensus function
 * @param threshold Similarity threshold (0.0 to 1.0)
 * @return Consensus function
 */
ConsensusFunc similarity_threshold(double threshold);

/**
 * @brief Requires majority of responses to match
 * @param messages Vector of messages to check
 * @return true if majority agree
 */
bool majority_agreement(const std::vector<core::Message>& messages);

} // namespace default_consensus

/**
 * @brief Default merge strategies
 */
namespace default_merge {

/**
 * @brief Concatenates all responses with separators
 * @param messages Vector of messages to merge
 * @return Message with concatenated content
 */
core::Message concatenate(const std::vector<core::Message>& messages);

/**
 * @brief Returns most common response (voting)
 * @param messages Vector of messages to merge
 * @return Most common message with vote metadata
 */
core::Message vote(const std::vector<core::Message>& messages);

/**
 * @brief Returns first response
 * @param messages Vector of messages to merge
 * @return First message
 */
core::Message first(const std::vector<core::Message>& messages);

/**
 * @brief Returns last response
 * @param messages Vector of messages to merge
 * @return Last message
 */
core::Message last(const std::vector<core::Message>& messages);

} // namespace default_merge

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_COLLABORATIVE_HPP
