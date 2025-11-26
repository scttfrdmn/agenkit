/**
 * @file agents_as_tools.cpp
 * @brief Implementation of Agents-as-Tools pattern
 */

#include "agenkit/patterns/agents_as_tools.hpp"
#include <stdexcept>
#include <future>
#include <chrono>

namespace agenkit {
namespace patterns {

AgentTool::AgentTool(
    std::shared_ptr<core::Agent> agent,
    std::string tool_name,
    std::string tool_description,
    AgentToolConfig config
)
    : agent_(agent)
    , tool_name_(std::move(tool_name))
    , tool_description_(std::move(tool_description))
    , config_(std::move(config))
{
    if (!agent_) {
        throw std::invalid_argument("agent cannot be null");
    }
    if (tool_name_.empty()) {
        throw std::invalid_argument("tool_name cannot be empty");
    }
    if (tool_description_.empty()) {
        throw std::invalid_argument("tool_description cannot be empty");
    }
}

std::shared_ptr<core::Agent> AgentTool::get_agent() const {
    return agent_;
}

const AgentToolConfig& AgentTool::get_config() const {
    return config_;
}

void AgentTool::set_config(const AgentToolConfig& config) {
    config_ = config;
}

std::string AgentTool::name() const {
    return tool_name_;
}

std::string AgentTool::description() const {
    return tool_description_;
}

ToolResult AgentTool::execute(const std::string& input) {
    if (config_.timeout.count() > 0) {
        return execute_with_timeout(input);
    } else {
        return execute_without_timeout(input);
    }
}

ToolResult AgentTool::execute_with_timeout(const std::string& input) {
    auto start_time = std::chrono::steady_clock::now();

    // Create message
    auto message = core::Message::with_text(config_.message_role, input);

    // Launch async execution
    auto future = agent_->process(std::move(message));

    // Wait with timeout
    auto status = future.wait_for(config_.timeout);

    if (status == std::future_status::timeout) {
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - start_time
        );

        ToolResult result = ToolResult::error(
            "Agent execution timed out after " +
            std::to_string(config_.timeout.count()) + "ms"
        );

        if (config_.include_timing) {
            result.metadata["execution_time_ms"] = elapsed.count();
            result.metadata["timed_out"] = true;
        }

        return result;
    }

    // Get result
    auto agent_result = future.get();

    auto end_time = std::chrono::steady_clock::now();
    auto execution_time = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time
    );

    return convert_result(agent_result, execution_time);
}

ToolResult AgentTool::execute_without_timeout(const std::string& input) {
    auto start_time = std::chrono::steady_clock::now();

    // Create message
    auto message = core::Message::with_text(config_.message_role, input);

    // Execute agent
    auto future = agent_->process(std::move(message));
    auto agent_result = future.get();

    auto end_time = std::chrono::steady_clock::now();
    auto execution_time = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time
    );

    return convert_result(agent_result, execution_time);
}

ToolResult AgentTool::convert_result(
    const core::Result<core::Message, core::AgentError>& result,
    std::chrono::milliseconds execution_time
) {
    ToolResult tool_result;

    if (result.is_ok()) {
        auto message = result.unwrap();
        tool_result.success = true;
        tool_result.content = message.content_as_str();

        // Propagate metadata if configured
        if (config_.propagate_metadata) {
            tool_result.metadata = message.metadata();
        }
    } else {
        auto error = result.unwrap_err();
        tool_result.success = false;
        tool_result.content = "Agent error: " + error.message();

        // Include error details in metadata
        tool_result.metadata["error_type"] = static_cast<int>(error.type());
        tool_result.metadata["error_message"] = error.message();
    }

    // Add timing information if configured
    if (config_.include_timing) {
        tool_result.metadata["execution_time_ms"] = execution_time.count();
        tool_result.metadata["timed_out"] = false;
    }

    // Add agent information
    tool_result.metadata["agent_name"] = agent_->name();

    return tool_result;
}

// AgentToolBuilder implementation

AgentToolBuilder::AgentToolBuilder(
    std::shared_ptr<core::Agent> agent,
    std::string tool_name,
    std::string tool_description
)
    : agent_(agent)
    , tool_name_(std::move(tool_name))
    , tool_description_(std::move(tool_description))
{
}

AgentToolBuilder& AgentToolBuilder::with_timeout(std::chrono::milliseconds timeout) {
    config_.timeout = timeout;
    return *this;
}

AgentToolBuilder& AgentToolBuilder::with_metadata_propagation(bool propagate) {
    config_.propagate_metadata = propagate;
    return *this;
}

AgentToolBuilder& AgentToolBuilder::with_timing(bool include) {
    config_.include_timing = include;
    return *this;
}

AgentToolBuilder& AgentToolBuilder::with_message_role(std::string role) {
    config_.message_role = std::move(role);
    return *this;
}

std::shared_ptr<AgentTool> AgentToolBuilder::build() {
    return std::make_shared<AgentTool>(
        agent_,
        tool_name_,
        tool_description_,
        config_
    );
}

} // namespace patterns
} // namespace agenkit
