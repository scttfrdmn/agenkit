/**
 * @file react.hpp
 * @brief ReAct (Reasoning + Acting) pattern implementation
 *
 * The ReAct pattern implements the Thought → Action → Observation loop
 * for agentic reasoning and decision-making.
 *
 * @see https://arxiv.org/abs/2210.03629
 */

#ifndef AGENKIT_PATTERNS_REACT_HPP
#define AGENKIT_PATTERNS_REACT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/errors.hpp"
#include <memory>
#include <string>
#include <vector>
#include <unordered_map>
#include <future>

namespace agenkit {
namespace patterns {

/**
 * @brief Result of a tool execution
 */
struct ToolResult {
    /// Success flag
    bool success;

    /// Result content or error message
    std::string content;

    /// Optional metadata
    nlohmann::json metadata;

    /**
     * @brief Create a successful tool result
     */
    static ToolResult ok(const std::string& content) {
        return ToolResult{true, content, nlohmann::json::object()};
    }

    /**
     * @brief Create a failed tool result
     */
    static ToolResult error(const std::string& error_msg) {
        return ToolResult{false, error_msg, nlohmann::json::object()};
    }
};

/**
 * @brief Abstract tool interface for ReAct pattern
 *
 * Tools are actions that the agent can take to interact with
 * the environment (e.g., search, calculate, query database).
 */
class Tool {
public:
    virtual ~Tool() = default;

    /**
     * @brief Get the tool's name
     * @return Tool name (used in action selection)
     */
    virtual std::string name() const = 0;

    /**
     * @brief Get the tool's description
     * @return Human-readable description of what the tool does
     */
    virtual std::string description() const = 0;

    /**
     * @brief Execute the tool with given input
     * @param input Tool input (typically parsed from agent's action)
     * @return ToolResult containing success status and content
     */
    virtual ToolResult execute(const std::string& input) = 0;
};

/**
 * @brief A single step in the ReAct loop
 */
struct ReactStep {
    /// Step number (1-indexed)
    int step;

    /// Agent's thought process
    std::string thought;

    /// Action to take (tool name + input)
    std::string action;

    /// Tool name
    std::string tool_name;

    /// Tool input
    std::string tool_input;

    /// Observation from tool execution
    std::string observation;

    /// Whether execution was successful
    bool success;
};

/**
 * @brief ReAct agent implementing Reasoning + Acting pattern
 *
 * The ReAct pattern combines:
 * - **Thought**: Agent reasons about the current state
 * - **Action**: Agent selects and executes a tool
 * - **Observation**: Agent observes the result
 *
 * This loop continues until the agent produces a final answer
 * or reaches the maximum number of steps.
 *
 * @par Example
 * @code
 * // Create tools
 * auto search = std::make_shared<SearchTool>();
 * auto calculator = std::make_shared<CalculatorTool>();
 *
 * // Create ReAct agent
 * ReactAgent agent(llm_agent);
 * agent.add_tool(search);
 * agent.add_tool(calculator);
 *
 * // Process query
 * auto msg = Message::with_text("user", "What is 15% of 200?");
 * auto result = agent.process(std::move(msg)).get();
 * @endcode
 */
class ReactAgent : public core::Agent {
public:
    /**
     * @brief Construct a ReAct agent
     *
     * @param agent Underlying agent (typically an LLM) that does reasoning
     * @param max_steps Maximum number of ReAct loop iterations (default: 10)
     *
     * @throws std::invalid_argument if agent is null or max_steps <= 0
     */
    explicit ReactAgent(
        std::shared_ptr<core::Agent> agent,
        int max_steps = 10
    );

    /**
     * @brief Add a tool to the agent's toolkit
     * @param tool Tool to add
     * @throws std::invalid_argument if tool is null
     */
    void add_tool(std::shared_ptr<Tool> tool);

    /**
     * @brief Get all available tools
     * @return Vector of tools
     */
    const std::vector<std::shared_ptr<Tool>>& get_tools() const;

    /**
     * @brief Get the ReAct history for the last execution
     * @return Vector of ReAct steps
     */
    const std::vector<ReactStep>& get_history() const;

    /**
     * @brief Clear the ReAct history
     */
    void clear_history();

    // Agent interface
    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    /// Underlying reasoning agent (typically LLM)
    std::shared_ptr<core::Agent> agent_;

    /// Maximum ReAct loop iterations
    int max_steps_;

    /// Available tools
    std::vector<std::shared_ptr<Tool>> tools_;

    /// Tool lookup by name
    std::unordered_map<std::string, std::shared_ptr<Tool>> tool_map_;

    /// ReAct history for last execution
    std::vector<ReactStep> history_;

    /**
     * @brief Create the initial ReAct prompt with tool descriptions
     */
    core::Message create_react_prompt(const core::Message& original_message);

    /**
     * @brief Parse agent's response to extract thought and action
     * @return Pair of (thought, action_string)
     */
    std::pair<std::string, std::string> parse_response(const std::string& response);

    /**
     * @brief Parse action string to extract tool name and input
     * @return Pair of (tool_name, tool_input)
     */
    std::pair<std::string, std::string> parse_action(const std::string& action);

    /**
     * @brief Execute a tool and get observation
     */
    ToolResult execute_tool(const std::string& tool_name, const std::string& input);

    /**
     * @brief Check if the response contains a final answer
     */
    bool is_final_answer(const std::string& response);

    /**
     * @brief Extract final answer from response
     */
    std::string extract_final_answer(const std::string& response);

    /**
     * @brief Create continuation prompt with observation
     */
    core::Message create_continuation_prompt(
        const core::Message& original_message,
        const std::vector<ReactStep>& steps,
        const std::string& observation
    );

    /**
     * @brief Add ReAct metadata to the final message
     */
    void add_react_metadata(core::Message& message);
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_REACT_HPP
