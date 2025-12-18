/**
 * @file chain_of_thought.hpp
 * @brief Chain-of-Thought Reasoning Technique
 *
 * Chain-of-Thought applies structured prompting to encourage step-by-step reasoning,
 * optionally parsing and tracking individual reasoning steps.
 *
 * Reference: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
 * Wei et al., 2022 - https://arxiv.org/abs/2201.11903
 */

#ifndef AGENKIT_TECHNIQUES_REASONING_CHAIN_OF_THOUGHT_HPP
#define AGENKIT_TECHNIQUES_REASONING_CHAIN_OF_THOUGHT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <string>
#include <vector>
#include <memory>
#include <future>
#include <optional>

namespace agenkit {
namespace techniques {
namespace reasoning {

/**
 * @brief Configuration for Chain-of-Thought
 */
struct ChainOfThoughtConfig {
    /** Prompt template with {query} placeholder (default: "Let's think step by step:\n{query}") */
    std::string prompt_template = "Let's think step by step:\n{query}";

    /** Whether to extract and track individual reasoning steps (default: true) */
    bool parse_steps = true;

    /** Delimiter for splitting steps (default: "\n") */
    std::string step_delimiter = "\n";

    /** Maximum number of reasoning steps to extract (optional) */
    std::optional<size_t> max_steps;
};

/**
 * @brief Chain-of-Thought agent that wraps a base agent
 *
 * This technique encourages step-by-step reasoning through structured prompting,
 * leading to more accurate and explainable results.
 *
 * Particularly effective for:
 * - Mathematical reasoning
 * - Logical deduction
 * - Complex problem-solving
 * - Multi-step tasks requiring explanation
 *
 * @example
 * @code
 * auto base_agent = std::make_shared<MyAgent>();
 * ChainOfThoughtConfig config;
 * config.prompt_template = "Solve step by step:\n{query}";
 * config.max_steps = 5;
 *
 * auto cot = std::make_shared<ChainOfThoughtAgent>(base_agent, config);
 * auto future = cot->process(Message::with_text("user", "What is 15 * 24?"));
 * auto result = future.get();
 * if (result.is_ok()) {
 *     auto response = result.unwrap();
 *     std::cout << "Answer: " << response.content_as_str() << std::endl;
 *     // Access reasoning_steps from metadata
 * }
 * @endcode
 */
class ChainOfThoughtAgent : public core::Agent {
public:
    /**
     * @brief Create a new Chain-of-Thought agent
     * @param agent Base agent to wrap
     * @param config Configuration options
     */
    ChainOfThoughtAgent(
        std::shared_ptr<core::Agent> agent,
        const ChainOfThoughtConfig& config = ChainOfThoughtConfig{}
    );

    /**
     * @brief Agent identifier
     * @return "chain_of_thought"
     */
    std::string name() const override;

    /**
     * @brief Agent capabilities
     * @return List of capabilities
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Process a message with Chain-of-Thought reasoning
     *
     * Applies the CoT prompt template to the input message, generates a
     * response using the wrapped agent, and optionally parses reasoning steps.
     *
     * @param message Input message with query content
     * @return Future with result containing response with metadata:
     *         - technique: "chain_of_thought"
     *         - reasoning_steps: std::vector<std::string> (if parse_steps is true)
     *         - num_steps: size_t (if parse_steps is true)
     *
     * @throws std::runtime_error if prompt template doesn't contain {query} placeholder
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::shared_ptr<core::Agent> agent_;
    ChainOfThoughtConfig config_;

    /**
     * @brief Extract reasoning steps from response text
     *
     * Supports multiple common step formats:
     * - Numbered steps (1. Step one, 2. Step two)
     * - Bullet points (- Step, * Step, • Step)
     * - Newline-separated thoughts (fallback)
     *
     * @param text Response text to parse
     * @return Vector of reasoning step strings
     */
    std::vector<std::string> extract_steps(const std::string& text) const;

    /**
     * @brief Apply max_steps limit if configured
     * @param steps Vector of steps to limit
     * @return Limited vector of steps
     */
    std::vector<std::string> limit_steps(std::vector<std::string> steps) const;
};

} // namespace reasoning
} // namespace techniques
} // namespace agenkit

#endif // AGENKIT_TECHNIQUES_REASONING_CHAIN_OF_THOUGHT_HPP
