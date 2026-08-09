/**
 * @file react.cpp
 * @brief Implementation of ReAct (Reasoning + Acting) pattern
 */

#include "agenkit/patterns/react.hpp"
#include <sstream>
#include <algorithm>
#include <cctype>
#include <stdexcept>

namespace agenkit {
namespace patterns {

ReactAgent::ReactAgent(
    std::shared_ptr<core::Agent> agent,
    int max_steps
)
    : agent_(agent)
    , max_steps_(max_steps)
{
    if (!agent_) {
        throw std::invalid_argument("agent cannot be null");
    }
    if (max_steps_ <= 0) {
        throw std::invalid_argument("max_steps must be positive");
    }
}

void ReactAgent::add_tool(std::shared_ptr<Tool> tool) {
    if (!tool) {
        throw std::invalid_argument("tool cannot be null");
    }
    tools_.push_back(tool);
    tool_map_[tool->name()] = tool;
}

const std::vector<std::shared_ptr<Tool>>& ReactAgent::get_tools() const {
    return tools_;
}

const std::vector<ReactStep>& ReactAgent::get_history() const {
    return history_;
}

void ReactAgent::clear_history() {
    history_.clear();
}

std::string ReactAgent::name() const {
    return "react";
}

std::vector<std::string> ReactAgent::capabilities() const {
    return {"react", "reasoning", "tool-use"};
}

core::Message ReactAgent::create_react_prompt(const core::Message& original_message) {
    std::ostringstream prompt;

    prompt << "You are a ReAct agent that uses tools to answer questions.\n\n";
    prompt << "Available tools:\n";

    for (const auto& tool : tools_) {
        prompt << "- " << tool->name() << ": " << tool->description() << "\n";
    }

    prompt << "\nYou should respond using this format:\n\n";
    prompt << "Thought: [your reasoning about what to do next]\n";
    prompt << "Action: [tool_name: input for the tool]\n\n";
    prompt << "You will receive an Observation from the tool execution.\n";
    prompt << "Repeat Thought/Action/Observation as needed.\n\n";
    prompt << "When you have enough information, respond with:\n";
    prompt << "Final Answer: [your complete answer to the question]\n\n";
    prompt << "Question: " << original_message.content_as_str() << "\n";

    auto msg = core::Message::with_text("user", prompt.str());

    // Preserve original metadata
    for (const auto& item : original_message.metadata().items()) {
        msg.with_metadata(item.key(), item.value());
    }

    return msg;
}

std::pair<std::string, std::string> ReactAgent::parse_response(const std::string& response) {
    std::string thought;
    std::string action;

    std::istringstream stream(response);
    std::string line;

    while (std::getline(stream, line)) {
        if (line.find("Thought:") == 0) {
            thought = line.substr(8);
            // Trim leading whitespace
            thought.erase(0, thought.find_first_not_of(" \t\n\r"));
        } else if (line.find("Action:") == 0) {
            action = line.substr(7);
            // Trim leading whitespace
            action.erase(0, action.find_first_not_of(" \t\n\r"));
        }
    }

    return {thought, action};
}

std::pair<std::string, std::string> ReactAgent::parse_action(const std::string& action) {
    // Format: "tool_name: input"
    auto colon_pos = action.find(':');
    if (colon_pos == std::string::npos) {
        return {"", action};
    }

    std::string tool_name = action.substr(0, colon_pos);
    std::string tool_input = action.substr(colon_pos + 1);

    // Trim whitespace
    tool_name.erase(0, tool_name.find_first_not_of(" \t\n\r"));
    tool_name.erase(tool_name.find_last_not_of(" \t\n\r") + 1);
    tool_input.erase(0, tool_input.find_first_not_of(" \t\n\r"));
    tool_input.erase(tool_input.find_last_not_of(" \t\n\r") + 1);

    return {tool_name, tool_input};
}

ToolResult ReactAgent::execute_tool(const std::string& tool_name, const std::string& input) {
    auto it = tool_map_.find(tool_name);
    if (it == tool_map_.end()) {
        return ToolResult::error("Unknown tool: " + tool_name);
    }

    try {
        return it->second->execute(input);
    } catch (const std::exception& e) {
        return ToolResult::error(std::string("Tool execution failed: ") + e.what());
    }
}

namespace {

/// Case-insensitive string equality, used to recognize the "Final Answer"
/// sentinel action name regardless of case.
bool iequals(const std::string& a, const std::string& b) {
    if (a.size() != b.size()) {
        return false;
    }
    return std::equal(a.begin(), a.end(), b.begin(), [](char x, char y) {
        return std::tolower(static_cast<unsigned char>(x)) == std::tolower(static_cast<unsigned char>(y));
    });
}

/// Extracts the trimmed action name from a response's "Action:" line, if any.
/// Returns an empty string if no such line is present.
std::string extract_action_line(const std::string& response) {
    std::istringstream stream(response);
    std::string line;
    while (std::getline(stream, line)) {
        if (line.find("Action:") == 0) {
            std::string action = line.substr(7);
            action.erase(0, action.find_first_not_of(" \t\n\r"));
            auto last = action.find_last_not_of(" \t\n\r");
            if (last != std::string::npos) {
                action.erase(last + 1);
            }
            return action;
        }
    }
    return "";
}

} // namespace

bool ReactAgent::is_final_answer(const std::string& response) {
    if (response.find("Final Answer:") != std::string::npos) {
        return true;
    }

    // Python/Zig convention (#765): "Final Answer" as a sentinel *action
    // name*, with the answer in a following "Action Input:" line, rather
    // than this core's own "Final Answer:" line prefix. Without this, a
    // Python-style response reaching this core looks up "Final Answer" as
    // a tool name (via parse_action's "tool_name: input" split), misses,
    // and silently degrades into max_steps.
    return iequals(extract_action_line(response), "Final Answer");
}

std::string ReactAgent::extract_final_answer(const std::string& response) {
    auto pos = response.find("Final Answer:");
    if (pos != std::string::npos) {
        std::string answer = response.substr(pos + 13);
        // Trim whitespace
        answer.erase(0, answer.find_first_not_of(" \t\n\r"));
        return answer;
    }

    // Python/Zig convention: the answer lives in the "Action Input:" line.
    std::istringstream stream(response);
    std::string line;
    while (std::getline(stream, line)) {
        if (line.find("Action Input:") == 0) {
            std::string answer = line.substr(13);
            answer.erase(0, answer.find_first_not_of(" \t\n\r"));
            return answer;
        }
    }

    return response;
}

core::Message ReactAgent::create_continuation_prompt(
    const core::Message& original_message,
    const std::vector<ReactStep>& steps,
    const std::string& observation
) {
    std::ostringstream prompt;

    // Reconstruct the conversation
    prompt << "Question: " << original_message.content_as_str() << "\n\n";

    // Add previous steps
    for (const auto& step : steps) {
        prompt << "Thought: " << step.thought << "\n";
        prompt << "Action: " << step.action << "\n";
        prompt << "Observation: " << step.observation << "\n\n";
    }

    // Add current observation
    prompt << "Observation: " << observation << "\n\n";
    prompt << "What should you do next?\n";

    auto msg = core::Message::with_text("user", prompt.str());

    // Preserve original metadata
    for (const auto& item : original_message.metadata().items()) {
        msg.with_metadata(item.key(), item.value());
    }

    return msg;
}

void ReactAgent::add_react_metadata(core::Message& message) {
    message.with_metadata("react_steps", static_cast<int>(history_.size()));
    message.with_metadata("pattern", "react");

    // Add tools used
    std::vector<std::string> tools_used;
    for (const auto& step : history_) {
        if (!step.tool_name.empty()) {
            tools_used.push_back(step.tool_name);
        }
    }
    message.with_metadata("tools_used", tools_used);
}

std::future<core::Result<core::Message, core::AgentError>>
ReactAgent::process(core::Message message) {
    // Clear previous history
    history_.clear();

    // Check if we have tools
    if (tools_.empty()) {
        auto error = core::AgentError(
            core::AgentErrorType::InvalidInput,
            "no tools available for ReAct agent"
        );
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(error)
        );
    }

    // Create initial prompt
    auto react_prompt = create_react_prompt(message);

    // ReAct loop
    for (int step = 1; step <= max_steps_; step++) {
        // Get agent's response
        auto result = agent_->process(core::Message(react_prompt)).get();

        if (result.is_err()) {
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(result.unwrap_err())
            );
        }

        auto response = result.unwrap();
        std::string response_text = response.content_as_str();

        // Check for final answer
        if (is_final_answer(response_text)) {
            std::string final_answer = extract_final_answer(response_text);
            auto final_msg = core::Message::with_text("assistant", final_answer);

            // Preserve metadata
            for (const auto& item : message.metadata().items()) {
                final_msg.with_metadata(item.key(), item.value());
            }

            add_react_metadata(final_msg);

            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::ok(final_msg)
            );
        }

        // Parse thought and action
        auto [thought, action] = parse_response(response_text);

        if (action.empty()) {
            // No action found, treat as final answer
            auto final_msg = core::Message::with_text("assistant", response_text);

            for (const auto& item : message.metadata().items()) {
                final_msg.with_metadata(item.key(), item.value());
            }

            add_react_metadata(final_msg);

            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::ok(final_msg)
            );
        }

        // Parse action into tool name and input
        auto [tool_name, tool_input] = parse_action(action);

        // Execute tool
        auto tool_result = execute_tool(tool_name, tool_input);

        // Record step
        ReactStep react_step{
            step,
            thought,
            action,
            tool_name,
            tool_input,
            tool_result.content,
            tool_result.success
        };
        history_.push_back(react_step);

        // Create continuation prompt
        react_prompt = create_continuation_prompt(message, history_, tool_result.content);
    }

    // Max steps reached - return last observation as answer
    std::string final_answer;
    if (!history_.empty()) {
        final_answer = "Reached maximum steps (" + std::to_string(max_steps_) + "). ";
        final_answer += "Last observation: " + history_.back().observation;
    } else {
        final_answer = "No solution found within maximum steps.";
    }

    auto final_msg = core::Message::with_text("assistant", final_answer);

    for (const auto& item : message.metadata().items()) {
        final_msg.with_metadata(item.key(), item.value());
    }

    add_react_metadata(final_msg);

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(final_msg)
    );
}

} // namespace patterns
} // namespace agenkit
