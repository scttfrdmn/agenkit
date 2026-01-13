/**
 * @file chain_of_thought.cpp
 * @brief Chain-of-Thought Reasoning Technique Implementation
 */

#include "agenkit/techniques/reasoning/chain_of_thought.hpp"
#include "agenkit/infrastructure/thread_pool.hpp"
#include <regex>
#include <algorithm>
#include <sstream>
#include <stdexcept>

namespace agenkit {
namespace techniques {
namespace reasoning {

ChainOfThoughtAgent::ChainOfThoughtAgent(
    std::shared_ptr<core::Agent> agent,
    const ChainOfThoughtConfig& config
) : agent_(std::move(agent)), config_(config) {}

std::string ChainOfThoughtAgent::name() const {
    return "chain_of_thought";
}

std::vector<std::string> ChainOfThoughtAgent::capabilities() const {
    return {
        "reasoning",
        "step_by_step",
        "chain_of_thought",
        "explainable_ai"
    };
}

std::future<core::Result<core::Message, core::AgentError>>
ChainOfThoughtAgent::process(core::Message message) {
    return infrastructure::global_thread_pool().enqueue([this, msg = std::move(message)]() -> core::Result<core::Message, core::AgentError> {
        // Validate prompt template
        if (config_.prompt_template.find("{query}") == std::string::npos) {
            return core::Result<core::Message, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::ProcessingError,
                    "Prompt template must contain {query} placeholder"
                )
            );
        }

        // Apply CoT prompting
        std::string cot_prompt = config_.prompt_template;
        size_t pos = cot_prompt.find("{query}");
        cot_prompt.replace(pos, 7, msg.content_as_str());

        // Get response from agent
        auto prompt_msg = core::Message::with_text("user", cot_prompt);
        auto response_future = agent_->process(std::move(prompt_msg));
        auto response_result = response_future.get();

        if (!response_result.is_ok()) {
            return core::Result<core::Message, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::ProcessingError,
                    "Chain of thought processing failed: " + response_result.unwrap_err().message()
                )
            );
        }

        auto response = response_result.unwrap();

        // Parse steps if requested
        if (config_.parse_steps) {
            auto steps = extract_steps(response.content_as_str());

            // Add metadata
            response.with_metadata("reasoning_steps", nlohmann::json(steps))
                   .with_metadata("num_steps", nlohmann::json(steps.size()));
        }

        response.with_metadata("technique", nlohmann::json("chain_of_thought"));

        return core::Result<core::Message, core::AgentError>::ok(std::move(response));
    });
}

std::vector<std::string> ChainOfThoughtAgent::extract_steps(const std::string& text) const {
    std::vector<std::string> steps;

    // Try numbered steps first (1. 2. 3. or 1) 2) 3))
    std::regex numbered_regex(R"(^\d+[\.)]\s*(.+)$)", std::regex::multiline);
    auto numbered_begin = std::sregex_iterator(text.begin(), text.end(), numbered_regex);
    auto numbered_end = std::sregex_iterator();

    if (std::distance(numbered_begin, numbered_end) >= 2) {
        for (auto it = numbered_begin; it != numbered_end; ++it) {
            std::smatch match = *it;
            std::string step = match[1].str();
            // Trim whitespace
            step.erase(0, step.find_first_not_of(" \t\r\n"));
            step.erase(step.find_last_not_of(" \t\r\n") + 1);
            steps.push_back(step);
        }
        return limit_steps(std::move(steps));
    }

    // Try bullet points (-, *, •)
    std::regex bullet_regex(R"(^[•\-\*]\s*(.+)$)", std::regex::multiline);
    auto bullet_begin = std::sregex_iterator(text.begin(), text.end(), bullet_regex);
    auto bullet_end = std::sregex_iterator();

    if (std::distance(bullet_begin, bullet_end) >= 2) {
        for (auto it = bullet_begin; it != bullet_end; ++it) {
            std::smatch match = *it;
            std::string step = match[1].str();
            // Trim whitespace
            step.erase(0, step.find_first_not_of(" \t\r\n"));
            step.erase(step.find_last_not_of(" \t\r\n") + 1);
            steps.push_back(step);
        }
        return limit_steps(std::move(steps));
    }

    // Fall back to delimiter-based splitting
    std::istringstream stream(text);
    std::string line;
    while (std::getline(stream, line, config_.step_delimiter[0])) {
        // Trim whitespace
        line.erase(0, line.find_first_not_of(" \t\r\n"));
        line.erase(line.find_last_not_of(" \t\r\n") + 1);
        if (!line.empty()) {
            steps.push_back(line);
        }
    }

    return limit_steps(std::move(steps));
}

std::vector<std::string> ChainOfThoughtAgent::limit_steps(std::vector<std::string> steps) const {
    if (config_.max_steps.has_value() && steps.size() > config_.max_steps.value()) {
        steps.resize(config_.max_steps.value());
    }
    return steps;
}

} // namespace reasoning
} // namespace techniques
} // namespace agenkit
