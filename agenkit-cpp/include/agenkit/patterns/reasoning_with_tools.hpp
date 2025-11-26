/**
 * @file reasoning_with_tools.hpp
 * @brief Reasoning with Tools pattern implementation
 *
 * This pattern extends ReAct with advanced reasoning capabilities including
 * chain-of-thought reasoning, tool planning, and multi-step inference.
 *
 * @see https://arxiv.org/abs/2205.00445
 */

#ifndef AGENKIT_PATTERNS_REASONING_WITH_TOOLS_HPP
#define AGENKIT_PATTERNS_REASONING_WITH_TOOLS_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/patterns/react.hpp"
#include <memory>
#include <string>
#include <vector>
#include <functional>

namespace agenkit {
namespace patterns {

/**
 * @brief A reasoning step in the chain-of-thought process
 */
struct ReasoningStep {
    /// Step number (1-indexed)
    int step;

    /// Reasoning/thought at this step
    std::string reasoning;

    /// Intermediate conclusion
    std::string conclusion;

    /// Confidence score (0.0 to 1.0)
    double confidence;

    /// Whether this step requires tool use
    bool requires_tool;

    /// Tool name if requires_tool is true
    std::string tool_name;

    /// Tool input if requires_tool is true
    std::string tool_input;

    /// Tool result if tool was used
    std::string tool_result;
};

/**
 * @brief Configuration for reasoning behavior
 */
struct ReasoningConfig {
    /// Maximum reasoning steps
    int max_reasoning_steps{10};

    /// Minimum confidence to accept conclusion (0.0 to 1.0)
    double min_confidence{0.7};

    /// Whether to use chain-of-thought prompting
    bool use_chain_of_thought{true};

    /// Whether to verify conclusions before finalizing
    bool verify_conclusions{false};

    /// Whether to allow backtracking on low confidence
    bool allow_backtracking{false};
};

/**
 * @brief Function type for extracting confidence from reasoning
 */
using ConfidenceExtractor = std::function<double(const std::string&)>;

/**
 * @brief Function type for determining if tool use is needed
 */
using ToolNeedDetector = std::function<bool(const std::string&)>;

/**
 * @brief Reasoning with Tools agent
 *
 * This pattern combines chain-of-thought reasoning with tool use,
 * enabling agents to:
 * - Plan multi-step reasoning sequences
 * - Use tools strategically based on reasoning needs
 * - Evaluate confidence in intermediate conclusions
 * - Backtrack and revise reasoning when needed
 *
 * @par Example
 * @code
 * // Create reasoning agent
 * ReasoningAgent agent(llm_agent);
 * agent.add_tool(calculator_tool);
 * agent.add_tool(search_tool);
 *
 * // Configure reasoning behavior
 * ReasoningConfig config;
 * config.max_reasoning_steps = 15;
 * config.min_confidence = 0.8;
 * config.allow_backtracking = true;
 * agent.set_config(config);
 *
 * // Process complex query
 * auto result = agent.process(message).get();
 * @endcode
 */
class ReasoningAgent : public core::Agent {
public:
    /**
     * @brief Construct a reasoning agent
     *
     * @param agent Underlying LLM agent for reasoning
     * @param config Optional configuration
     *
     * @throws std::invalid_argument if agent is null
     */
    explicit ReasoningAgent(
        std::shared_ptr<core::Agent> agent,
        ReasoningConfig config = ReasoningConfig{}
    );

    /**
     * @brief Add a tool to the reasoning agent
     *
     * @param tool Tool to add
     * @throws std::invalid_argument if tool is null
     */
    void add_tool(std::shared_ptr<Tool> tool);

    /**
     * @brief Get all available tools
     *
     * @return Vector of tools
     */
    const std::vector<std::shared_ptr<Tool>>& get_tools() const;

    /**
     * @brief Set confidence extractor function
     *
     * @param extractor Function to extract confidence from reasoning text
     */
    void set_confidence_extractor(ConfidenceExtractor extractor);

    /**
     * @brief Set tool need detector function
     *
     * @param detector Function to determine if tool use is needed
     */
    void set_tool_need_detector(ToolNeedDetector detector);

    /**
     * @brief Get reasoning history
     *
     * @return Vector of reasoning steps
     */
    const std::vector<ReasoningStep>& get_reasoning_history() const;

    /**
     * @brief Clear reasoning history
     */
    void clear_history();

    /**
     * @brief Get configuration
     *
     * @return Current configuration
     */
    const ReasoningConfig& get_config() const;

    /**
     * @brief Set configuration
     *
     * @param config New configuration
     */
    void set_config(const ReasoningConfig& config);

    // Agent interface
    std::string name() const override;
    std::vector<std::string> capabilities() const override;
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    /// Underlying reasoning agent (LLM)
    std::shared_ptr<core::Agent> agent_;

    /// Configuration
    ReasoningConfig config_;

    /// Available tools
    std::vector<std::shared_ptr<Tool>> tools_;

    /// Tool lookup by name
    std::unordered_map<std::string, std::shared_ptr<Tool>> tool_map_;

    /// Reasoning history
    std::vector<ReasoningStep> history_;

    /// Confidence extractor
    ConfidenceExtractor confidence_extractor_;

    /// Tool need detector
    ToolNeedDetector tool_need_detector_;

    /**
     * @brief Create chain-of-thought prompt
     */
    core::Message create_cot_prompt(const core::Message& original_message);

    /**
     * @brief Parse reasoning step from LLM response
     */
    ReasoningStep parse_reasoning_step(
        const std::string& response,
        int step_number
    );

    /**
     * @brief Default confidence extractor
     */
    static double default_confidence_extractor(const std::string& reasoning);

    /**
     * @brief Default tool need detector
     */
    static bool default_tool_need_detector(const std::string& reasoning);

    /**
     * @brief Execute tool if needed
     */
    std::string execute_tool_if_needed(ReasoningStep& step);

    /**
     * @brief Check if reasoning should continue
     */
    bool should_continue_reasoning(const ReasoningStep& step);

    /**
     * @brief Create continuation prompt with previous reasoning
     */
    core::Message create_continuation_prompt(
        const core::Message& original_message,
        const std::vector<ReasoningStep>& steps
    );

    /**
     * @brief Extract final answer from reasoning chain
     */
    std::string extract_final_answer(const std::vector<ReasoningStep>& steps);

    /**
     * @brief Add reasoning metadata to final message
     */
    void add_reasoning_metadata(core::Message& message);
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_REASONING_WITH_TOOLS_HPP
