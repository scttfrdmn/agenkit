/**
 * @file human_in_loop.cpp
 * @brief Implementation of Human-in-Loop pattern
 */

#include "agenkit/patterns/human_in_loop.hpp"
#include <sstream>

namespace agenkit {
namespace patterns {

HumanInLoopAgent::HumanInLoopAgent(HumanInLoopConfig config)
    : agent_(std::move(config.agent))
    , approval_threshold_(config.approval_threshold)
    , approval_func_(std::move(config.approval_func))
    , confidence_key_(std::move(config.confidence_key))
{
    if (!agent_) {
        throw std::invalid_argument("agent is required");
    }
    if (!approval_func_) {
        throw std::invalid_argument("approval function is required");
    }
    if (approval_threshold_ < 0.0 || approval_threshold_ > 1.0) {
        std::ostringstream oss;
        oss << "approval threshold must be between 0 and 1 (got " << approval_threshold_ << ")";
        throw std::invalid_argument(oss.str());
    }
    if (confidence_key_.empty()) {
        confidence_key_ = "confidence";
    }
}

std::string HumanInLoopAgent::name() const {
    return "human_in_loop";
}

std::vector<std::string> HumanInLoopAgent::capabilities() const {
    auto caps = agent_->capabilities();
    caps.push_back("human-in-loop");
    caps.push_back("approval");
    caps.push_back("oversight");
    return caps;
}

std::future<core::Result<core::Message, core::AgentError>>
HumanInLoopAgent::process(core::Message message) {
    // Execute underlying agent
    auto future = agent_->process(std::move(message));
    auto result = future.get();

    if (result.is_err()) {
        auto error = result.unwrap_err();
        std::ostringstream oss;
        oss << "agent execution failed: " << error.message();

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(error.type(), oss.str())
            )
        );
    }

    auto response = result.unwrap();

    // Extract confidence from metadata
    double confidence = extract_confidence(response);

    // Check if approval needed
    bool needs_approval = confidence < approval_threshold_;

    // Add approval metadata
    response.with_metadata("approval_needed", needs_approval);
    response.with_metadata("confidence", confidence);
    response.with_metadata("approval_threshold", approval_threshold_);

    // If high confidence, return without approval
    if (!needs_approval) {
        response.with_metadata("approval_status", "bypassed");
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(response)
        );
    }

    // Request human approval
    nlohmann::json context = {
        {"agent", agent_->name()},
        {"approval_threshold", approval_threshold_},
        {"confidence_shortfall", approval_threshold_ - confidence}
    };

    ApprovalRequest request(response, confidence, context);

    auto approval_result = approval_func_(request);

    if (approval_result.is_err()) {
        auto error = approval_result.unwrap_err();
        std::ostringstream oss;
        oss << "approval request failed: " << error.message();

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(error.type(), oss.str())
            )
        );
    }

    auto approval = approval_result.unwrap();

    // Handle approval decision
    if (!approval.approved) {
        // Request denied
        auto rejection_msg = core::Message::with_text("agent",
            "Action rejected by human reviewer");

        if (!approval.feedback.empty()) {
            rejection_msg.with_metadata("rejection_reason", approval.feedback);
        }

        rejection_msg.with_metadata("approval_status", "rejected");
        rejection_msg.with_metadata("original_response", response.content_as_str());
        rejection_msg.with_metadata("confidence", confidence);

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(rejection_msg)
        );
    }

    // Request approved
    core::Message final_response = response;
    if (approval.modified_message.has_value()) {
        // Use modified version
        final_response = approval.modified_message.value();
        final_response.with_metadata("approval_status", "approved_with_modifications");
        final_response.with_metadata("original_response", response.content_as_str());
    } else {
        final_response.with_metadata("approval_status", "approved");
    }

    if (!approval.feedback.empty()) {
        final_response.with_metadata("approval_feedback", approval.feedback);
    }

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(final_response)
    );
}

double HumanInLoopAgent::extract_confidence(const core::Message& message) const {
    const auto& metadata = message.metadata();

    if (metadata.is_null() || !metadata.is_object()) {
        return 0.0;
    }

    if (!metadata.contains(confidence_key_)) {
        return 0.0;
    }

    const auto& confidence_val = metadata[confidence_key_];

    // Try to convert to double
    if (confidence_val.is_number_float()) {
        return confidence_val.get<double>();
    } else if (confidence_val.is_number_integer()) {
        return static_cast<double>(confidence_val.get<int>());
    }

    return 0.0;
}

// Helper approval functions

ApprovalFunc simple_approval_func(bool auto_approve) {
    return [auto_approve](const ApprovalRequest& request) {
        std::ostringstream feedback;
        feedback << "Auto-" << (auto_approve ? "approved" : "rejected")
                 << " (confidence: " << request.confidence << ")";

        ApprovalResponse response;
        response.approved = auto_approve;
        response.feedback = feedback.str();

        return core::Result<ApprovalResponse, core::AgentError>::ok(response);
    };
}

ApprovalFunc confidence_based_approval_func(double reject_below, double auto_approve_above) {
    return [reject_below, auto_approve_above](const ApprovalRequest& request) {
        ApprovalResponse response;

        if (request.confidence < reject_below) {
            response.approved = false;
            std::ostringstream feedback;
            feedback << "Confidence too low (" << request.confidence
                    << " < " << reject_below << ")";
            response.feedback = feedback.str();
        } else if (request.confidence >= auto_approve_above) {
            response.approved = true;
            std::ostringstream feedback;
            feedback << "Auto-approved (" << request.confidence
                    << " >= " << auto_approve_above << ")";
            response.feedback = feedback.str();
        } else {
            // In this range, reject to be safe (or could prompt human)
            response.approved = false;
            std::ostringstream feedback;
            feedback << "Manual approval required (" << request.confidence
                    << " in threshold range)";
            response.feedback = feedback.str();
        }

        return core::Result<ApprovalResponse, core::AgentError>::ok(response);
    };
}

} // namespace patterns
} // namespace agenkit
