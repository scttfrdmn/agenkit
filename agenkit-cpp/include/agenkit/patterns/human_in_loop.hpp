/**
 * @file human_in_loop.hpp
 * @brief Human-in-the-loop oversight pattern
 *
 * This module provides the Human-in-Loop pattern for agent execution with human approval
 * for high-stakes decisions. When agent confidence is below a threshold,
 * human approval is requested before proceeding.
 */

#ifndef AGENKIT_PATTERNS_HUMAN_IN_LOOP_HPP
#define AGENKIT_PATTERNS_HUMAN_IN_LOOP_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <string>
#include <vector>
#include <functional>
#include <chrono>
#include <optional>

namespace agenkit {
namespace patterns {

/**
 * @brief Information about a pending approval decision
 */
struct ApprovalRequest {
    /// Message is the agent's proposed response
    core::Message message;
    /// Confidence is the agent's confidence level (0.0 to 1.0)
    double confidence;
    /// Context provides additional decision context
    nlohmann::json context;
    /// Timestamp when approval was requested
    std::chrono::system_clock::time_point timestamp;

    ApprovalRequest(
        core::Message msg,
        double conf,
        nlohmann::json ctx = nlohmann::json::object()
    )
        : message(std::move(msg))
        , confidence(conf)
        , context(std::move(ctx))
        , timestamp(std::chrono::system_clock::now())
    {}
};

/**
 * @brief Human's decision on approval request
 */
struct ApprovalResponse {
    /// Approved indicates if the action is approved
    bool approved;
    /// Feedback provides optional human feedback
    std::string feedback;
    /// ModifiedMessage is an optional modified version (if approved with changes)
    std::optional<core::Message> modified_message;

    ApprovalResponse(bool appr = false, std::string fb = "")
        : approved(appr)
        , feedback(std::move(fb))
    {}
};

/**
 * @brief Function type for requesting human approval
 *
 * The function receives an approval request and should return the human's
 * decision. This can be synchronous (blocking for user input) or asynchronous
 * (using a queue/callback system).
 */
using ApprovalFunc = std::function<core::Result<ApprovalResponse, core::AgentError>(const ApprovalRequest&)>;

/**
 * @brief Configuration for HumanInLoopAgent
 */
struct HumanInLoopConfig {
    /// Agent to wrap with human approval
    std::shared_ptr<core::Agent> agent;
    /// ApprovalThreshold for requiring approval (0.0 to 1.0, default: 0.8)
    /// Responses with confidence below this require approval
    double approval_threshold = 0.8;
    /// ApprovalFunc is called when approval is needed
    ApprovalFunc approval_func;
    /// ConfidenceKey specifies metadata key for confidence (default: "confidence")
    std::string confidence_key = "confidence";
};

/**
 * @brief Human-in-the-loop agent wrapper
 *
 * The HumanInLoopAgent wraps an agent with human approval gates.
 * The agent executes normally, but when confidence is below the threshold,
 * human approval is requested before returning the response. This provides
 * oversight for high-stakes decisions while allowing autonomous operation
 * for routine tasks.
 *
 * Key concepts:
 * - Confidence-based approval gates
 * - Human oversight for critical decisions
 * - Configurable approval thresholds
 * - Callback-based approval mechanism
 *
 * Performance characteristics:
 * - Time: O(agent) + human response time (when approval needed)
 * - Memory: O(1) for message passing
 * - Blocking on human input when required
 *
 * Example use cases:
 * - Financial trading: approve large transactions
 * - Content moderation: verify edge cases
 * - Healthcare: approve treatment recommendations
 * - Legal: review contract changes
 * - Security: approve access grants
 *
 * The human-in-loop pattern is ideal when autonomous operation needs
 * human oversight for critical or uncertain decisions.
 *
 * @example
 * @code
 * auto approval_func = [](const ApprovalRequest& request) {
 *     // Prompt user for approval
 *     std::cout << "Approve? (y/n): ";
 *     char response;
 *     std::cin >> response;
 *
 *     ApprovalResponse resp;
 *     resp.approved = (response == 'y');
 *     return core::Result<ApprovalResponse, core::AgentError>::ok(resp);
 * };
 *
 * HumanInLoopConfig config{
 *     my_agent,           // agent
 *     0.8,                // approval_threshold
 *     approval_func,      // approval_func
 *     "confidence"        // confidence_key
 * };
 *
 * HumanInLoopAgent hil_agent(config);
 * auto msg = core::Message::with_text("user", "Execute high-stakes action");
 * auto result = hil_agent.process(std::move(msg)).get();
 * @endcode
 */
class HumanInLoopAgent : public core::Agent {
public:
    /**
     * @brief Construct a human-in-loop agent
     * @param config Configuration with agent and approval settings
     * @throws std::invalid_argument if config is invalid
     */
    explicit HumanInLoopAgent(HumanInLoopConfig config);

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::shared_ptr<core::Agent> agent_;
    double approval_threshold_;
    ApprovalFunc approval_func_;
    std::string confidence_key_;

    /**
     * @brief Extract confidence value from message metadata
     * @param message Message to extract confidence from
     * @return Confidence value (0.0 if not found)
     */
    double extract_confidence(const core::Message& message) const;
};

/**
 * @brief Simple approval function for testing/demos
 *
 * This function automatically approves or rejects based on a static decision.
 * For production use, implement a custom ApprovalFunc that prompts humans.
 *
 * @param auto_approve Whether to auto-approve all requests
 * @return Approval function
 */
ApprovalFunc simple_approval_func(bool auto_approve);

/**
 * @brief Confidence-based approval function with dynamic thresholds
 *
 * This allows different approval rules based on confidence levels. For example:
 * - Very low confidence (< reject_below): always reject
 * - Low confidence (reject_below to auto_approve_above): require manual approval
 * - High confidence (>= auto_approve_above): auto-approve
 *
 * @param reject_below Confidence below this is auto-rejected
 * @param auto_approve_above Confidence above this is auto-approved
 * @return Approval function
 */
ApprovalFunc confidence_based_approval_func(double reject_below, double auto_approve_above);

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_HUMAN_IN_LOOP_HPP
