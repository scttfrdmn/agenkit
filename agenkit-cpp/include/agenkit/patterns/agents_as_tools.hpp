/**
 * @file agents_as_tools.hpp
 * @brief Agents-as-Tools pattern implementation
 *
 * This pattern allows agents to be used as tools, enabling composition
 * and delegation. Any agent can be wrapped as a tool for use in ReAct
 * or other tool-using patterns.
 *
 * @see https://langchain.com/agents-as-tools
 */

#ifndef AGENKIT_PATTERNS_AGENTS_AS_TOOLS_HPP
#define AGENKIT_PATTERNS_AGENTS_AS_TOOLS_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/patterns/react.hpp"
#include <memory>
#include <string>
#include <chrono>

namespace agenkit {
namespace patterns {

/**
 * @brief Configuration for AgentTool behavior
 */
struct AgentToolConfig {
    /// Timeout for agent execution (0 = no timeout)
    std::chrono::milliseconds timeout{0};

    /// Whether to propagate metadata from tool input to agent message
    bool propagate_metadata{true};

    /// Whether to include agent execution time in result metadata
    bool include_timing{false};

    /// Custom role for the message sent to the agent (default: "user")
    std::string message_role{"user"};
};

/**
 * @brief Wrapper that exposes an agent as a tool
 *
 * This class wraps any agent and exposes it through the Tool interface,
 * allowing agents to be used as tools in ReAct and other patterns.
 *
 * Features:
 * - Wraps any agent as a tool
 * - Configurable timeout
 * - Metadata propagation
 * - Execution timing
 * - Error handling and recovery
 *
 * @par Example
 * @code
 * // Create a specialized agent
 * auto calculator_agent = std::make_shared<CalculatorAgent>();
 *
 * // Wrap it as a tool
 * auto calculator_tool = std::make_shared<AgentTool>(
 *     calculator_agent,
 *     "calculator",
 *     "Performs mathematical calculations"
 * );
 *
 * // Use in ReAct agent
 * ReactAgent react_agent(llm);
 * react_agent.add_tool(calculator_tool);
 * @endcode
 */
class AgentTool : public Tool {
public:
    /**
     * @brief Construct an agent tool
     *
     * @param agent The agent to wrap as a tool
     * @param tool_name Name for this tool (used in action selection)
     * @param tool_description Human-readable description of what the tool does
     * @param config Optional configuration
     *
     * @throws std::invalid_argument if agent is null or names are empty
     */
    AgentTool(
        std::shared_ptr<core::Agent> agent,
        std::string tool_name,
        std::string tool_description,
        AgentToolConfig config = AgentToolConfig{}
    );

    /**
     * @brief Get the wrapped agent
     * @return Shared pointer to the underlying agent
     */
    std::shared_ptr<core::Agent> get_agent() const;

    /**
     * @brief Get the tool configuration
     * @return Current configuration
     */
    const AgentToolConfig& get_config() const;

    /**
     * @brief Update the tool configuration
     * @param config New configuration
     */
    void set_config(const AgentToolConfig& config);

    // Tool interface
    std::string name() const override;
    std::string description() const override;
    ToolResult execute(const std::string& input) override;

private:
    /// Wrapped agent
    std::shared_ptr<core::Agent> agent_;

    /// Tool name
    std::string tool_name_;

    /// Tool description
    std::string tool_description_;

    /// Configuration
    AgentToolConfig config_;

    /**
     * @brief Execute agent with timeout handling
     */
    ToolResult execute_with_timeout(const std::string& input);

    /**
     * @brief Execute agent without timeout
     */
    ToolResult execute_without_timeout(const std::string& input);

    /**
     * @brief Convert agent result to tool result
     */
    ToolResult convert_result(
        const core::Result<core::Message, core::AgentError>& result,
        std::chrono::milliseconds execution_time
    );
};

/**
 * @brief Builder for creating AgentTool instances with fluent API
 *
 * @par Example
 * @code
 * auto tool = AgentToolBuilder(agent, "calculator", "Does math")
 *     .with_timeout(std::chrono::seconds(5))
 *     .with_timing()
 *     .build();
 * @endcode
 */
class AgentToolBuilder {
public:
    /**
     * @brief Start building an agent tool
     *
     * @param agent The agent to wrap
     * @param tool_name Name for the tool
     * @param tool_description Description of what the tool does
     */
    AgentToolBuilder(
        std::shared_ptr<core::Agent> agent,
        std::string tool_name,
        std::string tool_description
    );

    /**
     * @brief Set execution timeout
     * @param timeout Maximum execution time
     * @return Builder for chaining
     */
    AgentToolBuilder& with_timeout(std::chrono::milliseconds timeout);

    /**
     * @brief Enable metadata propagation
     * @param propagate Whether to propagate metadata
     * @return Builder for chaining
     */
    AgentToolBuilder& with_metadata_propagation(bool propagate = true);

    /**
     * @brief Enable execution timing in results
     * @param include Whether to include timing
     * @return Builder for chaining
     */
    AgentToolBuilder& with_timing(bool include = true);

    /**
     * @brief Set message role for agent communication
     * @param role Role to use (e.g., "user", "system")
     * @return Builder for chaining
     */
    AgentToolBuilder& with_message_role(std::string role);

    /**
     * @brief Build the AgentTool
     * @return Shared pointer to the configured AgentTool
     */
    std::shared_ptr<AgentTool> build();

private:
    std::shared_ptr<core::Agent> agent_;
    std::string tool_name_;
    std::string tool_description_;
    AgentToolConfig config_;
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_AGENTS_AS_TOOLS_HPP
