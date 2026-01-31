/**
 * @file test_plan_and_solve.cpp
 * @brief Tests for Plan-and-Solve reasoning technique
 */

#include <gtest/gtest.h>
#include "agenkit/techniques/reasoning/plan_and_solve.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <memory>
#include <vector>
#include <string>
#include <atomic>

using namespace agenkit::techniques::reasoning;
using namespace agenkit::core;

/**
 * @brief Mock agent for testing
 */
class MockAgent : public Agent {
public:
    MockAgent(const std::vector<std::string>& responses)
        : responses_(responses), call_count_(0) {}

    std::string name() const override {
        return "mock_agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"mock", "testing"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() {
            size_t idx = call_count_.fetch_add(1) % responses_.size();
            return Result<Message, AgentError>::ok(
                Message::with_text("assistant", responses_[idx])
            );
        });
    }

    size_t get_call_count() const {
        return call_count_.load();
    }

private:
    std::vector<std::string> responses_;
    std::atomic<size_t> call_count_;
};

// Test basic Plan-and-Solve functionality
TEST(PlanAndSolveTest, BasicFunctionality) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Gather ingredients\n2. Preheat oven\n3. Mix ingredients\n4. Bake",
        "VALID: Plan is complete",
        "Gathered: flour, sugar, eggs",
        "Preheated oven to 350°F",
        "Mixed all ingredients thoroughly",
        "Baked for 30 minutes"
    });

    PlanAndSolveConfig config;
    config.validate_plan = true;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "How do I bake a cake?");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_FALSE(response.content_as_str().empty());

    auto metadata = response.metadata();
    EXPECT_EQ(metadata["technique"].get<std::string>(), "plan_and_solve");
    EXPECT_EQ(metadata["num_steps"].get<size_t>(), 4);
}

// Test name and capabilities
TEST(PlanAndSolveTest, NameAndCapabilities) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"response"});

    PlanAndSolveConfig config;
    PlanAndSolveAgent agent(mock, config);

    EXPECT_EQ(agent.name(), "plan_and_solve");

    auto caps = agent.capabilities();
    EXPECT_TRUE(std::find(caps.begin(), caps.end(), "reasoning") != caps.end());
    EXPECT_TRUE(std::find(caps.begin(), caps.end(), "planning") != caps.end());
    EXPECT_TRUE(std::find(caps.begin(), caps.end(), "plan_and_solve") != caps.end());
    EXPECT_TRUE(std::find(caps.begin(), caps.end(), "strategic_thinking") != caps.end());
    EXPECT_TRUE(std::find(caps.begin(), caps.end(), "step_by_step_execution") != caps.end());
}

// Test plan creation
TEST(PlanAndSolveTest, CreatePlan) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Step one\n2. Step two\n3. Step three"
    });

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    auto plan_steps = metadata["plan_steps"].get<std::vector<std::string>>();
    EXPECT_EQ(plan_steps.size(), 3);
    EXPECT_EQ(plan_steps[0], "Step one");
}

// Test step parsing
TEST(PlanAndSolveTest, ParseSteps) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. First step\n2. Second step"
    });

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    auto plan_steps = metadata["plan_steps"].get<std::vector<std::string>>();
    EXPECT_EQ(plan_steps.size(), 2);
    EXPECT_EQ(plan_steps[0], "First step");
    EXPECT_EQ(plan_steps[1], "Second step");
}

// Test validation when enabled
TEST(PlanAndSolveTest, ValidateWhenEnabled) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Step 1\n2. Step 2",
        "VALID: The plan is complete and feasible",
        "Result 1",
        "Result 2"
    });

    PlanAndSolveConfig config;
    config.validate_plan = true;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["validated"].get<bool>(), true);
    EXPECT_TRUE(metadata["validation_notes"].get<std::string>().find("VALID") != std::string::npos);
}

// Test skipping validation when disabled
TEST(PlanAndSolveTest, SkipValidationWhenDisabled) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Step",
        "Result"
    });

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Simple problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    // With validation disabled, should only call LLM twice (plan + execute)
    // not three times (plan + validate + execute)
    EXPECT_EQ(mock->get_call_count(), 2);
}

// Test handling invalid plan validation
TEST(PlanAndSolveTest, HandleInvalidPlanValidation) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Step 1",
        "INVALID: Missing important step",
        "Result 1"
    });

    PlanAndSolveConfig config;
    config.validate_plan = true;
    config.allow_replanning = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["validated"].get<bool>(), false);
    EXPECT_TRUE(metadata["validation_notes"].get<std::string>().find("INVALID") != std::string::npos);
}

// Test sequential execution
TEST(PlanAndSolveTest, ExecuteStepsSequentially) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Step A\n2. Step B",
        "Answer A",
        "Answer B"
    });

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    auto execution_steps = metadata["execution_steps"].get<std::vector<std::string>>();
    EXPECT_EQ(execution_steps.size(), 2);
    EXPECT_EQ(execution_steps[0], "Answer A");
    EXPECT_EQ(execution_steps[1], "Answer B");
}

// Test final solution return
TEST(PlanAndSolveTest, ReturnFinalSolution) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Subproblem 1\n2. Subproblem 2",
        "Intermediate",
        "Final answer"
    });

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "Final answer");
}

// Test execution state tracking
TEST(PlanAndSolveTest, TrackExecutionState) {
    PlanStep step("Test step", 0);

    EXPECT_FALSE(step.executed);

    step.executed = true;
    step.result = "Test result";

    EXPECT_TRUE(step.executed);
    EXPECT_EQ(step.result.value(), "Test result");
}

// Test custom planner
TEST(PlanAndSolveTest, CustomPlanner) {
    PlannerFunc custom_planner = [](const std::string& problem) {
        Plan plan(problem);
        plan.steps.push_back(PlanStep("Custom step 1", 0));
        plan.steps.push_back(PlanStep("Custom step 2", 1));
        plan.strategy = "Custom strategy";
        return plan;
    };

    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "Step 1 result",
        "Step 2 result"
    });

    PlanAndSolveConfig config;
    config.planner = custom_planner;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    auto plan_steps = metadata["plan_steps"].get<std::vector<std::string>>();
    EXPECT_EQ(plan_steps.size(), 2);
    EXPECT_EQ(plan_steps[0], "Custom step 1");
    EXPECT_EQ(metadata["strategy"].get<std::string>(), "Custom strategy");
}

// Test custom solver
TEST(PlanAndSolveTest, CustomSolver) {
    SolverFunc custom_solver = [](const PlanStep& step, const std::vector<std::string>& previous) {
        return "Custom solution for: " + step.description;
    };

    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Test step"
    });

    PlanAndSolveConfig config;
    config.solver = custom_solver;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_TRUE(response.content_as_str().find("Custom solution") != std::string::npos);
}

// Test replanning when validation fails
TEST(PlanAndSolveTest, ReplanningWhenValidationFails) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Initial step",
        "INVALID: Missing steps",
        "",  // Replanning prompt response
        "1. Better step 1\n2. Better step 2",
        "VALID",
        "Result 1",
        "Result 2"
    });

    PlanAndSolveConfig config;
    config.validate_plan = true;
    config.allow_replanning = true;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Complex problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Should have replanned and gotten a valid plan
    EXPECT_EQ(metadata["num_steps"].get<size_t>(), 2);
}

// Test empty plan handling
TEST(PlanAndSolveTest, HandleEmptyPlan) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{""});

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["num_steps"].get<size_t>(), 0);
}

// Test single step plan
TEST(PlanAndSolveTest, HandleSingleStepPlan) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Only step",
        "Step result"
    });

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Simple task");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["num_steps"].get<size_t>(), 1);
    EXPECT_EQ(response.content_as_str(), "Step result");
}

// Test period numbering format
TEST(PlanAndSolveTest, ParsePeriodNumbering) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Step one\n2. Step two\n3. Step three"
    });

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    auto plan_steps = metadata["plan_steps"].get<std::vector<std::string>>();
    EXPECT_EQ(plan_steps.size(), 3);
    EXPECT_EQ(plan_steps[0], "Step one");
    EXPECT_EQ(plan_steps[1], "Step two");
    EXPECT_EQ(plan_steps[2], "Step three");
}

// Test parenthesis numbering format
TEST(PlanAndSolveTest, ParseParenthesisNumbering) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1) Step one\n2) Step two"
    });

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    auto plan_steps = metadata["plan_steps"].get<std::vector<std::string>>();
    EXPECT_EQ(plan_steps.size(), 2);
    EXPECT_EQ(plan_steps[0], "Step one");
    EXPECT_EQ(plan_steps[1], "Step two");
}

// Test skipping empty lines
TEST(PlanAndSolveTest, SkipEmptyLines) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Step one\n\n2. Step two\n\n"
    });

    PlanAndSolveConfig config;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["num_steps"].get<size_t>(), 2);
}

// Test all required metadata fields
TEST(PlanAndSolveTest, IncludeAllRequiredMetadataFields) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Step 1\n2. Step 2",
        "VALID",
        "Result 1",
        "Result 2"
    });

    PlanAndSolveConfig config;
    config.validate_plan = true;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Test");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_TRUE(metadata.contains("technique"));
    EXPECT_EQ(metadata["technique"].get<std::string>(), "plan_and_solve");
    EXPECT_TRUE(metadata.contains("num_steps"));
    EXPECT_EQ(metadata["num_steps"].get<size_t>(), 2);
    EXPECT_TRUE(metadata.contains("plan_steps"));
    EXPECT_TRUE(metadata.contains("execution_steps"));
    EXPECT_TRUE(metadata.contains("validated"));
    EXPECT_TRUE(metadata.contains("validation_notes"));
    EXPECT_TRUE(metadata.contains("allow_replanning"));
}

// Test strategy tracking when provided
TEST(PlanAndSolveTest, TrackStrategyWhenProvided) {
    PlannerFunc custom_planner = [](const std::string& problem) {
        Plan plan(problem);
        plan.steps.push_back(PlanStep("Step", 0));
        plan.strategy = "Divide and conquer";
        return plan;
    };

    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"Result"});

    PlanAndSolveConfig config;
    config.planner = custom_planner;
    config.validate_plan = false;

    PlanAndSolveAgent agent(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["strategy"].get<std::string>(), "Divide and conquer");
}

// Test step dependencies tracking
TEST(PlanAndSolveTest, TrackStepDependencies) {
    Plan plan("Test");

    PlanStep step1("Step 1", 0);
    plan.steps.push_back(step1);

    PlanStep step2("Step 2", 1);
    step2.dependencies.push_back(0);
    plan.steps.push_back(step2);

    PlanStep step3("Step 3", 2);
    step3.dependencies.push_back(0);
    step3.dependencies.push_back(1);
    step3.estimated_complexity = 2;
    plan.steps.push_back(step3);

    // Verify step 2 depends on step 1
    EXPECT_EQ(plan.steps[1].dependencies.size(), 1);
    EXPECT_EQ(plan.steps[1].dependencies[0], 0);

    // Verify step 3 depends on steps 1 and 2
    EXPECT_EQ(plan.steps[2].dependencies.size(), 2);
    EXPECT_EQ(plan.steps[2].dependencies[0], 0);
    EXPECT_EQ(plan.steps[2].dependencies[1], 1);

    // Verify complexity tracking
    EXPECT_EQ(plan.steps[2].estimated_complexity, 2);
}

// Test valid plan structure creation
TEST(PlanAndSolveTest, CreateValidPlanStructure) {
    Plan plan("Test problem");

    EXPECT_EQ(plan.problem, "Test problem");
    EXPECT_EQ(plan.steps.size(), 0);
    EXPECT_FALSE(plan.validated);
}

// Test optional fields support
TEST(PlanAndSolveTest, SupportOptionalFields) {
    Plan plan("Test");
    plan.validated = true;
    plan.strategy = "Test strategy";
    plan.validation_notes = "All good";

    EXPECT_EQ(plan.strategy.value(), "Test strategy");
    EXPECT_EQ(plan.validation_notes.value(), "All good");
}

// Test valid plan step structure creation
TEST(PlanAndSolveTest, CreateValidPlanStepStructure) {
    PlanStep step("Test step", 0);

    EXPECT_EQ(step.description, "Test step");
    EXPECT_EQ(step.order, 0);
    EXPECT_EQ(step.dependencies.size(), 0);
    EXPECT_EQ(step.estimated_complexity, 1);
    EXPECT_FALSE(step.executed);
}

// Test optional result field support
TEST(PlanAndSolveTest, SupportOptionalResultField) {
    PlanStep step("Test step", 0);
    step.executed = true;
    step.result = "Test result";

    EXPECT_EQ(step.result.value(), "Test result");
}
