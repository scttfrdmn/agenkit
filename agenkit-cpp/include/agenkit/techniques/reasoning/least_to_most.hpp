/**
 * @file least_to_most.hpp
 * @brief Least-to-Most Prompting Technique
 *
 * Breaks complex problems into simpler subproblems, solves them sequentially
 * from simplest to most complex, using solutions to build up to the final answer.
 *
 * This technique is particularly effective for compositional reasoning where
 * complex problems can be decomposed into manageable pieces.
 *
 * Reference: "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models"
 * Zhou et al., 2022 - https://arxiv.org/abs/2205.10625
 */

#ifndef AGENKIT_TECHNIQUES_REASONING_LEAST_TO_MOST_HPP
#define AGENKIT_TECHNIQUES_REASONING_LEAST_TO_MOST_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/call_options.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <string>
#include <vector>
#include <memory>
#include <future>
#include <functional>
#include <optional>

namespace agenkit {
namespace techniques {
namespace reasoning {

/**
 * @brief Represents a subproblem in the decomposition
 */
struct Subproblem {
    /** The content/description of the subproblem */
    std::string content;

    /** Difficulty level (0 = easiest) */
    size_t difficulty;

    /** Indices of subproblems this depends on */
    std::vector<size_t> dependencies;

    Subproblem(const std::string& content, size_t difficulty)
        : content(content), difficulty(difficulty), dependencies() {}
};

/**
 * @brief Custom function type for decomposing problems into subproblems
 *
 * Takes a problem string and returns a vector of subproblem strings
 * ordered from simplest to most complex.
 */
using DecomposerFunc = std::function<std::vector<std::string>(const std::string&)>;

/**
 * @brief Configuration for Least-to-Most
 */
struct LeastToMostConfig {
    /**
     * Custom function to decompose problems into subproblems.
     * If not provided, uses LLM to decompose.
     */
    std::optional<DecomposerFunc> decomposer;

    /**
     * Maximum number of subproblems to generate.
     * Limits decomposition depth.
     * Default: 5
     */
    size_t max_subproblems = 5;

    /**
     * Whether to use previous subproblem solutions as context
     * when solving harder problems.
     * Default: true
     */
    bool compose_solutions = true;
};

/**
 * @brief Least-to-Most agent that wraps a base agent
 *
 * Decomposes complex problems into simpler subproblems, solves them
 * sequentially from easiest to hardest, using previous solutions as
 * context for solving harder problems.
 *
 * This technique is particularly effective for:
 * - Compositional reasoning tasks
 * - Multi-step math problems
 * - Problems that naturally decompose into stages
 * - Tasks where simpler subtasks inform harder ones
 *
 * @example
 * @code
 * auto base_agent = std::make_shared<MyAgent>();
 * LeastToMostConfig config;
 * config.max_subproblems = 5;
 * config.compose_solutions = true;
 *
 * auto ltm = std::make_shared<LeastToMostAgent>(base_agent, config);
 * auto future = ltm->process(Message::with_text("user", "Calculate 3*4 + 2*5"));
 * auto result = future.get();
 * if (result.is_ok()) {
 *     auto response = result.unwrap();
 *     std::cout << "Answer: " << response.content_as_str() << std::endl;
 *     // Access subproblems and solutions from metadata
 * }
 * @endcode
 */
class LeastToMostAgent : public core::Agent, public core::OptionsAgent {
public:
    /**
     * @brief Create a new Least-to-Most agent
     * @param agent Base agent to wrap
     * @param config Configuration options
     */
    LeastToMostAgent(
        std::shared_ptr<core::Agent> agent,
        const LeastToMostConfig& config = LeastToMostConfig{}
    );

    /**
     * @brief Agent identifier
     * @return "least_to_most"
     */
    std::string name() const override;

    /**
     * @brief Agent capabilities
     * @return List of capabilities
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Process a message with Least-to-Most reasoning
     *
     * Decomposes the problem, solves subproblems sequentially from easiest
     * to hardest, and composes the final solution.
     *
     * @param message Input message with problem content
     * @return Future with result containing response with metadata:
     *         - technique: "least_to_most"
     *         - num_subproblems: size_t
     *         - subproblems: std::vector<std::string>
     *         - subproblem_solutions: std::vector<std::string>
     *         - compose_solutions: bool
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Process a message, forwarding per-call options to the wrapped agent
     *
     * Same as process(), except that `options` reaches the wrapped agent if it
     * honours them, on both the decomposition call and every subproblem call.
     * process() is this method with an empty option set.
     *
     * @param message Input message with problem content
     * @param options Per-call options to forward
     * @return Future with result containing response with metadata (see process())
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process_with(core::Message message, const core::CallOptions& options) override;

private:
    std::shared_ptr<core::Agent> agent_;
    LeastToMostConfig config_;

    /**
     * @brief Decompose problem into subproblems
     *
     * Uses custom decomposer if provided, otherwise uses LLM.
     *
     * @param problem Original problem to decompose
     * @return Result with vector of Subproblems ordered from easiest to hardest
     */
    core::Result<std::vector<Subproblem>, core::AgentError>
    decompose(const std::string& problem, const core::CallOptions& options);

    /**
     * @brief Parse subproblems from LLM response
     *
     * Extracts numbered lines (1., 2., 3. or 1), 2), 3)) from the response.
     * If no valid numbered steps found, treats the original problem as atomic.
     *
     * @param response_text Text to parse
     * @param original_problem Original problem (fallback)
     * @return Vector of Subproblem objects
     */
    std::vector<Subproblem> parse_subproblems(
        const std::string& response_text,
        const std::string& original_problem
    );

    /**
     * @brief Solve one subproblem, optionally using previous solutions as context
     *
     * @param subproblem Subproblem to solve
     * @param previous_solutions Solutions to previous (easier) subproblems
     * @return Result with solution string
     */
    core::Result<std::string, core::AgentError>
    solve_subproblem(
        const Subproblem& subproblem,
        const std::vector<std::string>& previous_solutions,
        const core::CallOptions& options
    );

    /**
     * @brief Trim whitespace from both ends of a string
     * @param str String to trim
     * @return Trimmed string
     */
    static std::string trim(const std::string& str);
};

} // namespace reasoning
} // namespace techniques
} // namespace agenkit

#endif // AGENKIT_TECHNIQUES_REASONING_LEAST_TO_MOST_HPP
