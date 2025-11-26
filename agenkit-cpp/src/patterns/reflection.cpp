/**
 * @file reflection.cpp
 * @brief Implementation of Reflection pattern
 */

#include "agenkit/patterns/reflection.hpp"
#include <stdexcept>
#include <algorithm>

namespace agenkit {
namespace patterns {

ReflectionAgent::ReflectionAgent(
    std::shared_ptr<core::Agent> agent,
    std::shared_ptr<core::Agent> reflector,
    int max_reflections
)
    : agent_(std::move(agent))
    , reflector_(std::move(reflector))
    , max_reflections_(max_reflections)
{
    if (!agent_) {
        throw std::invalid_argument("agent cannot be null");
    }
    if (!reflector_) {
        throw std::invalid_argument("reflector cannot be null");
    }
    if (max_reflections_ < 1) {
        throw std::invalid_argument("max_reflections must be at least 1");
    }
}

std::string ReflectionAgent::name() const {
    return "reflection";
}

std::future<core::Result<core::Message, core::AgentError>>
ReflectionAgent::process(core::Message message) {
    // Clear previous history
    reflection_history_.clear();

    // Get initial response from agent
    auto future = agent_->process(core::Message(message));
    auto result = future.get();

    if (result.is_err()) {
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(result.unwrap_err())
        );
    }

    auto response = result.unwrap();

    // Reflection loop
    for (int iteration = 1; iteration <= max_reflections_; iteration++) {
        // Create reflection prompt
        auto reflection_prompt = create_reflection_prompt(message, response);

        // Get reflector feedback
        auto reflection_future = reflector_->process(std::move(reflection_prompt));
        auto reflection_result = reflection_future.get();

        if (reflection_result.is_err()) {
            // If reflector fails, return current response
            add_reflection_metadata(response);
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::ok(response)
            );
        }

        auto feedback = reflection_result.unwrap();

        // Check if we should continue reflecting
        bool should_continue = should_continue_reflecting(feedback);

        // Record reflection step
        ReflectionStep step{
            iteration,
            response,
            feedback,
            should_continue
        };
        reflection_history_.push_back(step);

        if (!should_continue) {
            // Response is good enough
            break;
        }

        if (iteration < max_reflections_) {
            // Generate improved response
            auto improvement_prompt = create_improvement_prompt(
                message,
                response,
                feedback
            );

            auto improvement_future = agent_->process(std::move(improvement_prompt));
            auto improvement_result = improvement_future.get();

            if (improvement_result.is_err()) {
                // If improvement fails, return current response
                break;
            }

            response = improvement_result.unwrap();
        }
    }

    // Add reflection metadata to final response
    add_reflection_metadata(response);

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(response)
    );
}

std::vector<std::string> ReflectionAgent::capabilities() const {
    return {"reflection", "self-improvement"};
}

const std::vector<ReflectionStep>& ReflectionAgent::get_reflection_history() const {
    return reflection_history_;
}

void ReflectionAgent::clear_history() {
    reflection_history_.clear();
}

core::Message ReflectionAgent::create_reflection_prompt(
    const core::Message& original,
    const core::Message& response
) {
    // Create a prompt that asks reflector to critique the response
    nlohmann::json prompt_content = nlohmann::json::object();
    prompt_content["original_query"] = original.content();
    prompt_content["response"] = response.content();
    prompt_content["task"] = "Critique the response. If it's good, respond with 'APPROVED'. "
                            "If it needs improvement, explain what's wrong and how to improve it.";

    auto prompt = core::Message("user", prompt_content);
    prompt.with_metadata("reflection_type", "critique");

    return prompt;
}

bool ReflectionAgent::should_continue_reflecting(const core::Message& feedback) {
    // Check if feedback indicates response is approved
    std::string feedback_str = feedback.content_as_str();

    // Convert to uppercase for comparison
    std::transform(feedback_str.begin(), feedback_str.end(),
                   feedback_str.begin(), ::toupper);

    // If feedback contains "APPROVED", stop reflecting
    if (feedback_str.find("APPROVED") != std::string::npos) {
        return false;
    }

    // Otherwise, continue reflecting
    return true;
}

core::Message ReflectionAgent::create_improvement_prompt(
    const core::Message& original,
    const core::Message& previous_response,
    const core::Message& feedback
) {
    // Create a prompt that asks agent to improve based on feedback
    nlohmann::json prompt_content = nlohmann::json::object();
    prompt_content["original_query"] = original.content();
    prompt_content["previous_response"] = previous_response.content();
    prompt_content["feedback"] = feedback.content();
    prompt_content["task"] = "Improve your previous response based on the feedback provided.";

    auto prompt = core::Message("user", prompt_content);
    prompt.with_metadata("reflection_type", "improvement");

    return prompt;
}

void ReflectionAgent::add_reflection_metadata(core::Message& message) {
    // Add reflection history to metadata
    message.with_metadata("reflection_iterations",
                         static_cast<int>(reflection_history_.size()));

    // Add full reflection history
    nlohmann::json history_json = nlohmann::json::array();
    for (const auto& step : reflection_history_) {
        nlohmann::json step_json = nlohmann::json::object();
        step_json["iteration"] = step.iteration;
        step_json["response_preview"] = step.response.content_as_str().substr(0, 100);
        step_json["feedback_preview"] = step.feedback.content_as_str().substr(0, 100);
        step_json["should_continue"] = step.should_continue;
        history_json.push_back(step_json);
    }
    message.with_metadata("reflection_history", history_json);

    if (!reflection_history_.empty()) {
        message.with_metadata("final_iteration",
                             reflection_history_.back().iteration);
    }
}

} // namespace patterns
} // namespace agenkit
