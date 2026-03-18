/**
 * @file plan_and_solve.cpp
 * @brief Implementation of Plan-and-Solve Reasoning Technique
 */

#include "agenkit/techniques/reasoning/plan_and_solve.hpp"
#include <regex>
#include <sstream>
#include <algorithm>
#include <cctype>

namespace agenkit {
namespace techniques {
namespace reasoning {

PlanAndSolveAgent::PlanAndSolveAgent(
    std::shared_ptr<core::Agent> agent,
    const PlanAndSolveConfig& config)
    : agent_(agent)
    , planner_(config.planner)
    , solver_(config.solver)
    , validate_plan_(config.validate_plan)
    , allow_replanning_(config.allow_replanning) {}

std::string PlanAndSolveAgent::name() const {
    return "plan_and_solve";
}

std::vector<std::string> PlanAndSolveAgent::capabilities() const {
    return {
        "reasoning",
        "planning",
        "plan_and_solve",
        "strategic_thinking",
        "step_by_step_execution"
    };
}

std::future<core::Result<std::string, core::AgentError>> PlanAndSolveAgent::llm_call(const std::string& prompt) {
    return std::async(std::launch::async, [this, prompt]() -> core::Result<std::string, core::AgentError> {
        auto message = core::Message::with_text("user", prompt);

        auto result_future = agent_->process(message);
        auto result = result_future.get();

        if (!result.is_ok()) {
            return core::Result<std::string, core::AgentError>::err(result.unwrap_err());
        }

        return core::Result<std::string, core::AgentError>::ok(result.unwrap().content_as_str());
    });
}

std::future<core::Result<Plan, core::AgentError>> PlanAndSolveAgent::create_plan(const std::string& problem) {
    return std::async(std::launch::async, [this, problem]() -> core::Result<Plan, core::AgentError> {
        if (planner_) {
            return core::Result<Plan, core::AgentError>::ok((*planner_)(problem));
        }

        std::ostringstream prompt;
        prompt << "Create a detailed step-by-step plan to solve this problem.\n"
               << "List each step on a separate line, numbered 1, 2, 3, etc.\n"
               << "Focus on WHAT needs to be done, not HOW to do it yet.\n\n"
               << "Problem: " << problem << "\n\n"
               << "Solution Plan:";

        auto result_future = llm_call(prompt.str());
        auto result = result_future.get();

        if (!result.is_ok()) {
            return core::Result<Plan, core::AgentError>::err(result.unwrap_err());
        }

        Plan plan(problem);

        // Parse numbered lines
        std::regex number_pattern(R"(^\d+[\.\)]\s*)");
        std::istringstream stream(result.unwrap());
        std::string line;
        int order = 0;

        while (std::getline(stream, line)) {
            // Trim whitespace
            line.erase(0, line.find_first_not_of(" \t\n\r\f\v"));
            line.erase(line.find_last_not_of(" \t\n\r\f\v") + 1);

            if (line.empty()) {
                continue;
            }

            // Remove numbering
            std::string cleaned = std::regex_replace(line, number_pattern, "");
            if (!cleaned.empty()) {
                plan.steps.emplace_back(cleaned, order++);
            }
        }

        return core::Result<Plan, core::AgentError>::ok(plan);
    });
}

std::future<core::Result<void, core::AgentError>> PlanAndSolveAgent::validate(Plan& plan) {
    return std::async(std::launch::async, [this, &plan]() -> core::Result<void, core::AgentError> {
        std::ostringstream prompt;
        prompt << "Review this solution plan for completeness and feasibility.\n"
               << "Is this plan sufficient to solve the problem? Are there any missing steps or issues?\n\n"
               << "Problem: " << plan.problem << "\n\n"
               << "Plan:\n" << format_plan(plan) << "\n\n"
               << "Validation (answer \"VALID\" or describe issues):";

        auto result_future = llm_call(prompt.str());
        auto result = result_future.get();

        if (!result.is_ok()) {
            return core::Result<void, core::AgentError>::err(result.unwrap_err());
        }

        std::string response = result.unwrap();

        // Convert to uppercase for comparison
        std::string response_upper = response;
        std::transform(response_upper.begin(), response_upper.end(),
                       response_upper.begin(), ::toupper);

        // Check INVALID first since it contains "VALID" as a substring
        bool is_invalid = response_upper.find("INVALID") != std::string::npos;
        bool is_valid = !is_invalid && (
            response_upper.find("VALID") != std::string::npos ||
            response_upper.find("YES") != std::string::npos
        );

        plan.validated = is_valid;

        // Trim response
        response.erase(0, response.find_first_not_of(" \t\n\r\f\v"));
        response.erase(response.find_last_not_of(" \t\n\r\f\v") + 1);
        plan.validation_notes = response;

        return core::Result<void, core::AgentError>::ok();
    });
}

std::string PlanAndSolveAgent::format_plan(const Plan& plan) {
    std::ostringstream formatted;
    for (size_t i = 0; i < plan.steps.size(); ++i) {
        const auto& step = plan.steps[i];
        std::string status = step.executed ? "✓" : "○";
        formatted << (i + 1) << ". [" << status << "] " << step.description;
        if (i < plan.steps.size() - 1) {
            formatted << "\n";
        }
    }
    return formatted.str();
}

std::future<core::Result<std::string, core::AgentError>> PlanAndSolveAgent::execute_step(
    const PlanStep& step,
    const std::vector<std::string>& previous_results) {

    return std::async(std::launch::async, [this, step, previous_results]() -> core::Result<std::string, core::AgentError> {
        if (solver_) {
            return core::Result<std::string, core::AgentError>::ok((*solver_)(step, previous_results));
        }

        std::ostringstream prompt;
        if (!previous_results.empty()) {
            prompt << "Execute this step of the plan, using previous results as context.\n\n";
            prompt << "Previous Results:\n";
            for (size_t i = 0; i < previous_results.size(); ++i) {
                prompt << "Previous step " << (i + 1) << " result: "
                       << previous_results[i] << "\n";
            }
            prompt << "\nCurrent Step: " << step.description << "\n\n";
            prompt << "Execution Result:";
        } else {
            prompt << "Execute this step of the plan:\n\n";
            prompt << "Step: " << step.description << "\n\n";
            prompt << "Execution Result:";
        }

        auto result_future = llm_call(prompt.str());
        auto result = result_future.get();

        if (!result.is_ok()) {
            return core::Result<std::string, core::AgentError>::err(result.unwrap_err());
        }

        std::string output = result.unwrap();

        // Trim result
        output.erase(0, output.find_first_not_of(" \t\n\r\f\v"));
        output.erase(output.find_last_not_of(" \t\n\r\f\v") + 1);

        return core::Result<std::string, core::AgentError>::ok(output);
    });
}

std::future<core::Result<std::vector<std::string>, core::AgentError>> PlanAndSolveAgent::execute_plan(Plan& plan) {
    return std::async(std::launch::async, [this, &plan]() -> core::Result<std::vector<std::string>, core::AgentError> {
        std::vector<std::string> results;

        for (auto& step : plan.steps) {
            auto result_future = execute_step(step, results);
            auto result = result_future.get();

            if (!result.is_ok()) {
                return core::Result<std::vector<std::string>, core::AgentError>::err(result.unwrap_err());
            }

            std::string step_result = result.unwrap();
            step.result = step_result;
            step.executed = true;
            results.push_back(step_result);
        }

        return core::Result<std::vector<std::string>, core::AgentError>::ok(results);
    });
}

std::future<core::Result<core::Message, core::AgentError>> PlanAndSolveAgent::process(core::Message message) {
    return std::async(std::launch::async, [this, message]() -> core::Result<core::Message, core::AgentError> {
        std::string problem = message.content_as_str();

        // Create plan
        auto plan_future = create_plan(problem);
        auto plan_result = plan_future.get();

        if (!plan_result.is_ok()) {
            return core::Result<core::Message, core::AgentError>::err(plan_result.unwrap_err());
        }

        Plan plan = plan_result.unwrap();

        // Validate plan if configured
        if (validate_plan_) {
            auto validate_future = validate(plan);
            auto validate_result = validate_future.get();

            if (!validate_result.is_ok()) {
                return core::Result<core::Message, core::AgentError>::err(validate_result.unwrap_err());
            }

            // Replan if validation failed and replanning is allowed
            if (!plan.validated && allow_replanning_) {
                std::ostringstream improved_prompt;
                improved_prompt << "The previous plan had issues. Create an improved plan.\n\n";
                improved_prompt << "Problem: " << problem << "\n\n";
                improved_prompt << "Previous Plan Issues:\n";
                improved_prompt << plan.validation_notes.value_or("") << "\n\n";
                improved_prompt << "Improved Plan:";

                auto llm_future = llm_call(improved_prompt.str());
                auto llm_result = llm_future.get();

                if (!llm_result.is_ok()) {
                    return core::Result<core::Message, core::AgentError>::err(llm_result.unwrap_err());
                }

                // Create new plan
                plan_future = create_plan(problem);
                plan_result = plan_future.get();

                if (!plan_result.is_ok()) {
                    return core::Result<core::Message, core::AgentError>::err(plan_result.unwrap_err());
                }

                plan = plan_result.unwrap();

                // Validate new plan
                validate_future = validate(plan);
                validate_result = validate_future.get();

                if (!validate_result.is_ok()) {
                    return core::Result<core::Message, core::AgentError>::err(validate_result.unwrap_err());
                }
            }
        }

        // Execute plan
        auto execution_future = execute_plan(plan);
        auto execution_result = execution_future.get();

        if (!execution_result.is_ok()) {
            return core::Result<core::Message, core::AgentError>::err(execution_result.unwrap_err());
        }

        std::vector<std::string> execution_results = execution_result.unwrap();
        std::string final_solution = execution_results.empty() ? "" : execution_results.back();

        // Build response message with metadata
        auto result = core::Message::with_text("assistant", final_solution);
        result.with_metadata("technique", "plan_and_solve");
        result.with_metadata("num_steps", static_cast<int>(plan.steps.size()));
        result.with_metadata("validated", plan.validated);
        if (plan.validation_notes) {
            result.with_metadata("validation_notes", *plan.validation_notes);
        }
        result.with_metadata("allow_replanning", allow_replanning_);

        // Add plan_steps array
        nlohmann::json plan_steps_json = nlohmann::json::array();
        for (const auto& step : plan.steps) {
            plan_steps_json.push_back(step.description);
        }
        result.with_metadata("plan_steps", plan_steps_json);

        // Add execution_steps array
        nlohmann::json execution_steps_json = nlohmann::json::array();
        for (const auto& exec_result : execution_results) {
            execution_steps_json.push_back(exec_result);
        }
        result.with_metadata("execution_steps", execution_steps_json);

        // Add strategy if provided by planner
        if (plan.strategy) {
            result.with_metadata("strategy", *plan.strategy);
        }

        return core::Result<core::Message, core::AgentError>::ok(result);
    });
}

} // namespace reasoning
} // namespace techniques
} // namespace agenkit
