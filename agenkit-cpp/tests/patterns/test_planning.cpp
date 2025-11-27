/**
 * @file test_planning.cpp
 * @brief Tests for Planning pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/planning.hpp"
#include <memory>

using namespace agenkit;

// Mock planner that returns a simple plan
class MockPlanner : public core::Agent {
private:
    std::string plan_response_;

public:
    MockPlanner(const std::string& plan_response =
        "1. First step\n2. Second step\n3. Third step")
        : plan_response_(plan_response) {}

    std::string name() const override { return "mock_planner"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        auto msg = core::Message::with_text("assistant", plan_response_);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

// Test: Basic planning
TEST(PlanningTest, BasicPlanning) {
    auto planner = std::make_shared<MockPlanner>();
    patterns::PlanningAgent agent(planner);

    auto msg = core::Message::with_text("user", "Complete task");
    auto result = agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.content_as_str().find("Task completed") != std::string::npos);
    EXPECT_TRUE(response.content_as_str().find("Steps completed") != std::string::npos);
}

// Test: Plan creation
TEST(PlanningTest, PlanCreation) {
    auto planner = std::make_shared<MockPlanner>();
    patterns::PlanningAgent agent(planner);

    auto msg = core::Message::with_text("user", "Test");
    agent.process(std::move(msg)).get();

    auto plan = agent.get_plan();
    ASSERT_TRUE(plan.has_value());
    EXPECT_EQ(plan->steps.size(), 3);
}

// Test: Step parsing
TEST(PlanningTest, StepParsing) {
    auto planner = std::make_shared<MockPlanner>("1. First\n2. Second");
    patterns::PlanningAgent agent(planner);

    auto msg = core::Message::with_text("user", "Test");
    agent.process(std::move(msg)).get();

    auto plan = agent.get_plan();
    ASSERT_TRUE(plan.has_value());
    ASSERT_EQ(plan->steps.size(), 2);

    EXPECT_EQ(plan->steps[0].description, "First");
    EXPECT_EQ(plan->steps[1].description, "Second");
}

// Test: Progress tracking
TEST(PlanningTest, ProgressTracking) {
    auto planner = std::make_shared<MockPlanner>();
    patterns::PlanningAgent agent(planner);

    EXPECT_EQ(agent.get_progress(), 0.0);

    auto msg = core::Message::with_text("user", "Test");
    agent.process(std::move(msg)).get();

    // After execution, progress should be 100%
    EXPECT_EQ(agent.get_progress(), 100.0);
}

// Test: Plan completion check
TEST(PlanningTest, PlanCompletion) {
    patterns::Plan plan;
    plan.goal = "Test goal";

    patterns::PlanStep step1;
    step1.status = patterns::StepStatus::Completed;
    plan.steps.push_back(step1);

    patterns::PlanStep step2;
    step2.status = patterns::StepStatus::Completed;
    plan.steps.push_back(step2);

    EXPECT_TRUE(plan.is_complete());
    EXPECT_FALSE(plan.has_failures());
}

// Test: Plan with failures
TEST(PlanningTest, PlanWithFailures) {
    patterns::Plan plan;

    patterns::PlanStep step1;
    step1.status = patterns::StepStatus::Completed;
    plan.steps.push_back(step1);

    patterns::PlanStep step2;
    step2.status = patterns::StepStatus::Failed;
    plan.steps.push_back(step2);

    EXPECT_FALSE(plan.is_complete());
    EXPECT_TRUE(plan.has_failures());
}

// Test: Clear plan
TEST(PlanningTest, ClearPlan) {
    auto planner = std::make_shared<MockPlanner>();
    patterns::PlanningAgent agent(planner);

    auto msg = core::Message::with_text("user", "Test");
    agent.process(std::move(msg)).get();

    EXPECT_TRUE(agent.get_plan().has_value());

    agent.clear_plan();
    EXPECT_FALSE(agent.get_plan().has_value());
}

// Test: Capabilities
TEST(PlanningTest, Capabilities) {
    auto planner = std::make_shared<MockPlanner>();
    patterns::PlanningAgent agent(planner);

    auto caps = agent.capabilities();
    EXPECT_EQ(caps.size(), 4);
}

// Test: Name
TEST(PlanningTest, Name) {
    auto planner = std::make_shared<MockPlanner>();
    patterns::PlanningAgent agent(planner);

    EXPECT_EQ(agent.name(), "planning");
}

// Test: Metadata
TEST(PlanningTest, Metadata) {
    auto planner = std::make_shared<MockPlanner>();
    patterns::PlanningAgent agent(planner);

    auto msg = core::Message::with_text("user", "Test");
    auto result = agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.metadata().contains("pattern"));
    EXPECT_EQ(response.metadata()["pattern"], "planning");
}

// Test: Null planner error
TEST(PlanningTest, NullPlannerError) {
    EXPECT_THROW(
        patterns::PlanningAgent(nullptr),
        std::invalid_argument
    );
}
