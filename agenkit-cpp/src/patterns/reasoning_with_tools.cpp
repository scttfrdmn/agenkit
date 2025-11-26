/**
 * @file reasoning_with_tools.cpp
 * @brief Implementation of Reasoning with Tools pattern
 */

#include "agenkit/patterns/reasoning_with_tools.hpp"
#include <stdexcept>
#include <sstream>
#include <regex>

namespace agenkit {
namespace patterns {

ReasoningAgent::ReasoningAgent(
    std::shared_ptr<core::Agent> agent,
    ReasoningConfig config
)
    : agent_(agent)
    , config_(std::move(config))
    , confidence_extractor_(default_confidence_extractor)
    , tool_need_detector_(default_tool_need_detector)
{
    if (!agent_) {
        throw std::invalid_argument("agent cannot be null");
    }
}

void ReasoningAgent::add_tool(std::shared_ptr<Tool> tool) {
    if (!tool) {
        throw std::invalid_argument("tool cannot be null");
    }
    tools_.push_back(tool);
    tool_map_[tool->name()] = tool;
}

const std::vector<std::shared_ptr<Tool>>& ReasoningAgent::get_tools() const {
    return tools_;
}

void ReasoningAgent::set_confidence_extractor(ConfidenceExtractor extractor) {
    confidence_extractor_ = std::move(extractor);
}

void ReasoningAgent::set_tool_need_detector(ToolNeedDetector detector) {
    tool_need_detector_ = std::move(detector);
}

const std::vector<ReasoningStep>& ReasoningAgent::get_reasoning_history() const {
    return history_;
}

void ReasoningAgent::clear_history() {
    history_.clear();
}

const ReasoningConfig& ReasoningAgent::get_config() const {
    return config_;
}

void ReasoningAgent::set_config(const ReasoningConfig& config) {
    config_ = config;
}

std::string ReasoningAgent::name() const {
    return "reasoning";
}

std::vector<std::string> ReasoningAgent::capabilities() const {
    return {"reasoning", "chain-of-thought", "tool-use", "planning"};
}

std::future<core::Result<core::Message, core::AgentError>>
ReasoningAgent::process(core::Message message) {
    history_.clear();

    // Create chain-of-thought prompt
    auto cot_prompt = create_cot_prompt(message);

    // Reasoning loop
    for (int step = 1; step <= config_.max_reasoning_steps; step++) {
        // Get reasoning from LLM
        auto future = agent_->process(core::Message(cot_prompt));
        auto result = future.get();

        if (result.is_err()) {
            return core::make_ready_future(result);
        }

        auto response = result.unwrap();
        std::string response_text = response.content_as_str();

        // Parse reasoning step
        auto reasoning_step = parse_reasoning_step(response_text, step);

        // Execute tool if needed
        if (reasoning_step.requires_tool) {
            reasoning_step.tool_result = execute_tool_if_needed(reasoning_step);
        }

        history_.push_back(reasoning_step);

        // Check if we should continue
        if (!should_continue_reasoning(reasoning_step)) {
            break;
        }

        // Create continuation prompt
        cot_prompt = create_continuation_prompt(message, history_);
    }

    // Extract final answer
    std::string final_answer = extract_final_answer(history_);
    auto final_msg = core::Message::with_text("assistant", final_answer);

    // Preserve metadata
    for (const auto& item : message.metadata().items()) {
        final_msg.with_metadata(item.key(), item.value());
    }

    add_reasoning_metadata(final_msg);

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(final_msg)
    );
}

core::Message ReasoningAgent::create_cot_prompt(const core::Message& original_message) {
    std::ostringstream prompt;

    prompt << "You are a reasoning agent that uses chain-of-thought to solve problems.\n\n";

    if (!tools_.empty()) {
        prompt << "Available tools:\n";
        for (const auto& tool : tools_) {
            prompt << "- " << tool->name() << ": " << tool->description() << "\n";
        }
        prompt << "\n";
    }

    prompt << "Approach this step-by-step:\n";
    prompt << "1. State your reasoning clearly\n";
    prompt << "2. If you need a tool, specify: USE TOOL: [tool_name: input]\n";
    prompt << "3. Draw intermediate conclusions\n";
    prompt << "4. Indicate confidence: CONFIDENCE: [0.0-1.0]\n";
    prompt << "5. When ready, provide: FINAL ANSWER: [your answer]\n\n";

    prompt << "Question: " << original_message.content_as_str() << "\n";

    return core::Message::with_text("user", prompt.str());
}

ReasoningStep ReasoningAgent::parse_reasoning_step(
    const std::string& response,
    int step_number
) {
    ReasoningStep step;
    step.step = step_number;
    step.reasoning = response;
    step.confidence = confidence_extractor_(response);
    step.requires_tool = tool_need_detector_(response);

    // Extract tool usage if present
    std::regex tool_regex(R"(USE TOOL:\s*(\w+):\s*(.+))");
    std::smatch match;
    if (std::regex_search(response, match, tool_regex)) {
        step.tool_name = match[1];
        step.tool_input = match[2];
    }

    // Extract conclusion
    auto conclusion_pos = response.find("Conclusion:");
    if (conclusion_pos != std::string::npos) {
        step.conclusion = response.substr(conclusion_pos + 11);
        // Trim
        step.conclusion.erase(0, step.conclusion.find_first_not_of(" \t\n\r"));
        auto newline_pos = step.conclusion.find('\n');
        if (newline_pos != std::string::npos) {
            step.conclusion = step.conclusion.substr(0, newline_pos);
        }
    }

    return step;
}

double ReasoningAgent::default_confidence_extractor(const std::string& reasoning) {
    // Look for explicit confidence statement
    std::regex confidence_regex(R"(CONFIDENCE:\s*(0?\.\d+|1\.0|0|1))");
    std::smatch match;
    if (std::regex_search(reasoning, match, confidence_regex)) {
        return std::stod(match[1]);
    }

    // Default medium confidence
    return 0.75;
}

bool ReasoningAgent::default_tool_need_detector(const std::string& reasoning) {
    return reasoning.find("USE TOOL:") != std::string::npos;
}

std::string ReasoningAgent::execute_tool_if_needed(ReasoningStep& step) {
    if (!step.requires_tool || step.tool_name.empty()) {
        return "";
    }

    auto it = tool_map_.find(step.tool_name);
    if (it == tool_map_.end()) {
        return "Error: Tool not found: " + step.tool_name;
    }

    auto result = it->second->execute(step.tool_input);
    return result.success ? result.content : "Error: " + result.content;
}

bool ReasoningAgent::should_continue_reasoning(const ReasoningStep& step) {
    // Check for final answer
    if (step.reasoning.find("FINAL ANSWER:") != std::string::npos) {
        return false;
    }

    // Check confidence threshold
    if (config_.verify_conclusions && step.confidence < config_.min_confidence) {
        return config_.allow_backtracking;
    }

    return true;
}

core::Message ReasoningAgent::create_continuation_prompt(
    const core::Message& original_message,
    const std::vector<ReasoningStep>& steps
) {
    std::ostringstream prompt;

    prompt << "Question: " << original_message.content_as_str() << "\n\n";
    prompt << "Your reasoning so far:\n\n";

    for (const auto& step : steps) {
        prompt << "Step " << step.step << ":\n";
        prompt << step.reasoning << "\n";

        if (!step.tool_result.empty()) {
            prompt << "Tool result: " << step.tool_result << "\n";
        }

        if (!step.conclusion.empty()) {
            prompt << "Conclusion: " << step.conclusion << "\n";
        }

        prompt << "Confidence: " << step.confidence << "\n\n";
    }

    prompt << "Continue your reasoning. What's the next step?\n";

    return core::Message::with_text("user", prompt.str());
}

std::string ReasoningAgent::extract_final_answer(const std::vector<ReasoningStep>& steps) {
    // Look for explicit final answer
    for (auto it = steps.rbegin(); it != steps.rend(); ++it) {
        auto pos = it->reasoning.find("FINAL ANSWER:");
        if (pos != std::string::npos) {
            std::string answer = it->reasoning.substr(pos + 13);
            // Trim
            answer.erase(0, answer.find_first_not_of(" \t\n\r"));
            return answer;
        }
    }

    // Fallback: use last conclusion
    if (!steps.empty() && !steps.back().conclusion.empty()) {
        return steps.back().conclusion;
    }

    // Last resort: use last reasoning
    if (!steps.empty()) {
        return steps.back().reasoning;
    }

    return "No conclusion reached";
}

void ReasoningAgent::add_reasoning_metadata(core::Message& message) {
    message.with_metadata("reasoning_steps", static_cast<int>(history_.size()));
    message.with_metadata("pattern", "reasoning_with_tools");

    // Calculate average confidence
    double total_confidence = 0.0;
    for (const auto& step : history_) {
        total_confidence += step.confidence;
    }
    double avg_confidence = history_.empty() ? 0.0 : total_confidence / history_.size();
    message.with_metadata("average_confidence", avg_confidence);

    // Count tool uses
    int tool_uses = 0;
    for (const auto& step : history_) {
        if (step.requires_tool) {
            tool_uses++;
        }
    }
    message.with_metadata("tool_uses", tool_uses);
}

} // namespace patterns
} // namespace agenkit
