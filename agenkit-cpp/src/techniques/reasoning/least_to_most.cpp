/**
 * @file least_to_most.cpp
 * @brief Least-to-Most Reasoning Technique Implementation
 */

#include "agenkit/techniques/reasoning/least_to_most.hpp"
#include "agenkit/infrastructure/thread_pool.hpp"
#include <regex>
#include <algorithm>
#include <sstream>
#include <stdexcept>

namespace agenkit {
namespace techniques {
namespace reasoning {

LeastToMostAgent::LeastToMostAgent(
    std::shared_ptr<core::Agent> agent,
    const LeastToMostConfig& config
) : agent_(std::move(agent)), config_(config) {}

std::string LeastToMostAgent::name() const {
    return "least_to_most";
}

std::vector<std::string> LeastToMostAgent::capabilities() const {
    return {
        "reasoning",
        "decomposition",
        "compositional_reasoning",
        "least_to_most",
        "sequential_solving"
    };
}

std::future<core::Result<core::Message, core::AgentError>>
LeastToMostAgent::process(core::Message message) {
    return infrastructure::global_thread_pool().enqueue([this, msg = std::move(message)]() -> core::Result<core::Message, core::AgentError> {
        std::string problem = msg.content_as_str();

        // Step 1: Decompose problem
        auto decompose_result = decompose(problem);
        if (!decompose_result.is_ok()) {
            return core::Result<core::Message, core::AgentError>::err(
                decompose_result.unwrap_err()
            );
        }
        auto subproblems = decompose_result.unwrap();

        // Step 2: Solve subproblems sequentially
        std::vector<std::string> solutions;
        for (const auto& subproblem : subproblems) {
            auto solution_result = solve_subproblem(subproblem, solutions);
            if (!solution_result.is_ok()) {
                return core::Result<core::Message, core::AgentError>::err(
                    solution_result.unwrap_err()
                );
            }
            solutions.push_back(solution_result.unwrap());
        }

        // Step 3: Final solution is the last one (hardest problem)
        std::string final_solution = solutions.empty() ? "" : solutions.back();

        // Build subproblem texts for metadata
        std::vector<std::string> subproblem_texts;
        for (const auto& sp : subproblems) {
            subproblem_texts.push_back(sp.content);
        }

        auto result = core::Message::with_text("assistant", final_solution);
        result.with_metadata("technique", nlohmann::json("least_to_most"))
              .with_metadata("num_subproblems", nlohmann::json(subproblems.size()))
              .with_metadata("subproblems", nlohmann::json(subproblem_texts))
              .with_metadata("subproblem_solutions", nlohmann::json(solutions))
              .with_metadata("compose_solutions", nlohmann::json(config_.compose_solutions));

        return core::Result<core::Message, core::AgentError>::ok(std::move(result));
    });
}

core::Result<std::vector<Subproblem>, core::AgentError>
LeastToMostAgent::decompose(const std::string& problem) {
    if (config_.decomposer.has_value()) {
        // Use custom decomposer
        try {
            auto subproblem_texts = config_.decomposer.value()(problem);
            std::vector<Subproblem> subproblems;

            for (size_t i = 0; i < subproblem_texts.size() && i < config_.max_subproblems; ++i) {
                subproblems.emplace_back(subproblem_texts[i], i);
            }

            return core::Result<std::vector<Subproblem>, core::AgentError>::ok(
                std::move(subproblems)
            );
        } catch (const std::exception& e) {
            return core::Result<std::vector<Subproblem>, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::ProcessingError,
                    std::string("Custom decomposer failed: ") + e.what()
                )
            );
        }
    }

    // Use LLM to decompose
    std::ostringstream decomposition_prompt;
    decomposition_prompt << "Break down this problem into simpler subproblems, ordered from easiest to hardest.\n"
                        << "List each subproblem on a separate line, numbered 1, 2, 3, etc.\n\n"
                        << "Problem: " << problem << "\n\n"
                        << "Subproblems (from simplest to most complex):";

    auto prompt_message = core::Message::with_text("user", decomposition_prompt.str());
    auto response_future = agent_->process(std::move(prompt_message));
    auto response_result = response_future.get();

    if (!response_result.is_ok()) {
        return core::Result<std::vector<Subproblem>, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::ProcessingError,
                "Decomposition failed: " + response_result.unwrap_err().message()
            )
        );
    }

    auto response = response_result.unwrap();
    auto subproblems = parse_subproblems(response.content_as_str(), problem);

    return core::Result<std::vector<Subproblem>, core::AgentError>::ok(
        std::move(subproblems)
    );
}

std::vector<Subproblem> LeastToMostAgent::parse_subproblems(
    const std::string& response_text,
    const std::string& original_problem
) {
    std::vector<Subproblem> subproblems;

    // Regex to match numbered lines (1., 1), etc.) with optional leading whitespace
    std::regex numbered_regex(R"(^\s*\d+[\.)]\s*(.+)$)", std::regex::multiline);
    auto numbered_begin = std::sregex_iterator(response_text.begin(), response_text.end(), numbered_regex);
    auto numbered_end = std::sregex_iterator();

    size_t difficulty = 0;
    for (auto it = numbered_begin; it != numbered_end && subproblems.size() < config_.max_subproblems; ++it) {
        std::smatch match = *it;
        std::string cleaned = match[1].str();
        cleaned = trim(cleaned);

        if (!cleaned.empty()) {
            subproblems.emplace_back(cleaned, difficulty++);
        }
    }

    // If decomposition failed or no valid numbered steps found, treat as atomic problem
    if (subproblems.empty()) {
        subproblems.emplace_back(original_problem, 0);
    }

    return subproblems;
}

core::Result<std::string, core::AgentError>
LeastToMostAgent::solve_subproblem(
    const Subproblem& subproblem,
    const std::vector<std::string>& previous_solutions
) {
    std::ostringstream prompt;

    if (config_.compose_solutions && !previous_solutions.empty()) {
        // Include previous solutions as context
        prompt << "Given these previous solutions to simpler subproblems:\n\n";
        for (size_t i = 0; i < previous_solutions.size(); ++i) {
            prompt << "Previous solution " << (i + 1) << ": " << previous_solutions[i] << "\n";
        }
        prompt << "\nNow solve this subproblem:\n" << subproblem.content << "\n\nSolution:";
    } else {
        // Solve without context
        prompt << "Solve this subproblem:\n\n" << subproblem.content << "\n\nSolution:";
    }

    auto prompt_message = core::Message::with_text("user", prompt.str());
    auto response_future = agent_->process(std::move(prompt_message));
    auto response_result = response_future.get();

    if (!response_result.is_ok()) {
        return core::Result<std::string, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::ProcessingError,
                "Subproblem solving failed: " + response_result.unwrap_err().message()
            )
        );
    }

    auto response = response_result.unwrap();
    std::string solution = trim(response.content_as_str());

    return core::Result<std::string, core::AgentError>::ok(std::move(solution));
}

std::string LeastToMostAgent::trim(const std::string& str) {
    if (str.empty()) {
        return str;
    }

    auto start = str.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) {
        return "";
    }

    auto end = str.find_last_not_of(" \t\r\n");
    return str.substr(start, end - start + 1);
}

} // namespace reasoning
} // namespace techniques
} // namespace agenkit
