/**
 * @file test_autonomous.cpp
 * @brief Tests for Autonomous pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/autonomous.hpp"
#include "agenkit/core/agent.hpp"
#include <memory>
#include <thread>
#include <chrono>

using namespace agenkit;
using namespace agenkit::patterns;

// ============================================================================
// Basic Autonomous Agent Tests
// ============================================================================

TEST(AutonomousAgentTest, BasicConstruction) {
    AutonomousAgent agent("Research AI trends");

    EXPECT_EQ(agent.name(), "autonomous");
    EXPECT_FALSE(agent.is_running());
    EXPECT_EQ(agent.get_iteration_count(), 0);
    EXPECT_DOUBLE_EQ(agent.get_progress(), 0.0);
}

TEST(AutonomousAgentTest, AddGoal) {
    AutonomousAgent agent("Complete project");

    auto& goal = agent.add_goal("Task 1", 1);
    EXPECT_EQ(goal.description, "Task 1");
    EXPECT_EQ(goal.priority, 1);
    EXPECT_EQ(goal.status, GoalStatus::Active);
    EXPECT_DOUBLE_EQ(goal.progress, 0.0);

    auto goals = agent.get_goals();
    EXPECT_EQ(goals.size(), 1);
}

TEST(AutonomousAgentTest, MultipleGoals) {
    AutonomousAgent agent("Complete project");

    agent.add_goal("High priority task", 3);
    agent.add_goal("Medium priority task", 2);
    agent.add_goal("Low priority task", 1);

    auto goals = agent.get_goals();
    EXPECT_EQ(goals.size(), 3);
    EXPECT_EQ(goals[0].priority, 3);
    EXPECT_EQ(goals[1].priority, 2);
    EXPECT_EQ(goals[2].priority, 1);
}

TEST(AutonomousAgentTest, RunWithSingleGoal) {
    AutonomousConfig config;
    config.max_iterations = 5;
    config.progress_per_iteration = 0.25;

    AutonomousAgent agent("Complete task", config);
    agent.add_goal("Main goal", 1);

    auto result = agent.run();

    EXPECT_EQ(result.objective, "Complete task");
    EXPECT_GT(result.iterations_completed, 0);
    EXPECT_EQ(result.goals_completed, 1);
    EXPECT_EQ(result.iteration_results.size(),
              static_cast<size_t>(result.iterations_completed));
    EXPECT_FALSE(result.stopped_early);

    auto goals = agent.get_goals();
    EXPECT_EQ(goals[0].status, GoalStatus::Completed);
    EXPECT_GE(goals[0].progress, 1.0);
}

TEST(AutonomousAgentTest, RunWithMultipleGoals) {
    AutonomousConfig config;
    config.max_iterations = 10;
    config.progress_per_iteration = 0.3;

    AutonomousAgent agent("Multi-goal project", config);
    agent.add_goal("Goal 1", 2);
    agent.add_goal("Goal 2", 1);

    auto result = agent.run();

    EXPECT_GT(result.goals_completed, 0);
    EXPECT_LE(result.iterations_completed, 10);
}

TEST(AutonomousAgentTest, PriorityBasedGoalSelection) {
    AutonomousConfig config;
    config.max_iterations = 3;
    config.progress_per_iteration = 0.5;

    AutonomousAgent agent("Priority test", config);
    agent.add_goal("Low priority", 1);
    agent.add_goal("High priority", 3);
    agent.add_goal("Medium priority", 2);

    auto result = agent.run();

    // High priority goal should be worked on first
    EXPECT_TRUE(result.iteration_results[0].find("High priority") != std::string::npos);
}

TEST(AutonomousAgentTest, MaxIterationsLimit) {
    AutonomousConfig config;
    config.max_iterations = 3;
    config.progress_per_iteration = 0.1;  // Won't complete in 3 iterations

    AutonomousAgent agent("Limited iterations", config);
    agent.add_goal("Long task", 1);

    auto result = agent.run();

    EXPECT_EQ(result.iterations_completed, 3);
    EXPECT_EQ(result.goals_completed, 0);  // Not enough iterations to complete
}

TEST(AutonomousAgentTest, StopCondition) {
    AutonomousConfig config;
    config.max_iterations = 100;
    config.progress_per_iteration = 0.1;

    int iteration_count = 0;
    config.stop_condition = [&iteration_count]() {
        return ++iteration_count >= 3;
    };

    AutonomousAgent agent("Stop condition test", config);
    agent.add_goal("Test goal", 1);

    auto result = agent.run();

    EXPECT_TRUE(result.stopped_early);
    EXPECT_LE(result.iterations_completed, 3);
}

TEST(AutonomousAgentTest, ManualStop) {
    AutonomousConfig config;
    config.max_iterations = 100;
    config.progress_per_iteration = 0.1;

    AutonomousAgent agent("Manual stop test", config);
    agent.add_goal("Long task", 1);

    // Start agent in a thread
    std::thread agent_thread([&agent]() {
        agent.run();
    });

    // Stop after brief delay
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    agent.stop();

    agent_thread.join();

    EXPECT_FALSE(agent.is_running());
}

TEST(AutonomousAgentTest, ProgressTracking) {
    AutonomousConfig config;
    config.max_iterations = 10;
    config.progress_per_iteration = 0.25;

    AutonomousAgent agent("Progress test", config);
    agent.add_goal("Goal 1", 1);
    agent.add_goal("Goal 2", 1);

    EXPECT_DOUBLE_EQ(agent.get_progress(), 0.0);

    agent.run();

    // Progress should be > 0 after running
    EXPECT_GT(agent.get_progress(), 0.0);
}

TEST(AutonomousAgentTest, NoGoalsProvided) {
    AutonomousConfig config;
    config.max_iterations = 5;

    AutonomousAgent agent("No goals", config);

    auto result = agent.run();

    EXPECT_EQ(result.iterations_completed, 0);
    EXPECT_EQ(result.goals_completed, 0);
    EXPECT_EQ(result.iteration_results.size(), 0);
}

TEST(AutonomousAgentTest, Process) {
    AutonomousAgent agent("Test objective");
    agent.add_goal("Goal 1", 1);
    agent.add_goal("Goal 2", 2);

    auto msg = core::Message::with_text("user", "Process test");
    auto future = agent.process(msg);
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.content_as_str().find("Test objective") != std::string::npos);
    EXPECT_TRUE(response.metadata().contains("pattern"));
    EXPECT_EQ(response.metadata()["pattern"], "autonomous");
    EXPECT_TRUE(response.metadata().contains("objective"));
    EXPECT_EQ(response.metadata()["objective"], "Test objective");
    EXPECT_TRUE(response.metadata().contains("goal_count"));
    EXPECT_EQ(response.metadata()["goal_count"], 2);
}

TEST(AutonomousAgentTest, Capabilities) {
    AutonomousAgent agent("Test");

    auto caps = agent.capabilities();
    EXPECT_EQ(caps.size(), 4);
    EXPECT_NE(std::find(caps.begin(), caps.end(), "autonomous"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "self-directed"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "goal-oriented"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "continuous"), caps.end());
}

TEST(AutonomousAgentTest, Name) {
    AutonomousAgent agent("Test");
    EXPECT_EQ(agent.name(), "autonomous");
}

// ============================================================================
// Goal Tests
// ============================================================================

TEST(GoalTest, Construction) {
    Goal goal("Test goal", 2);

    EXPECT_EQ(goal.description, "Test goal");
    EXPECT_EQ(goal.priority, 2);
    EXPECT_EQ(goal.status, GoalStatus::Active);
    EXPECT_DOUBLE_EQ(goal.progress, 0.0);
}

TEST(GoalTest, StatusTransitions) {
    Goal goal("Test", 1);

    EXPECT_EQ(goal.status, GoalStatus::Active);

    goal.status = GoalStatus::Completed;
    EXPECT_EQ(goal.status, GoalStatus::Completed);

    goal.status = GoalStatus::Abandoned;
    EXPECT_EQ(goal.status, GoalStatus::Abandoned);
}

// ============================================================================
// AutonomousResult Tests
// ============================================================================

TEST(AutonomousResultTest, DefaultConstruction) {
    AutonomousResult result;

    EXPECT_TRUE(result.objective.empty());
    EXPECT_EQ(result.iterations_completed, 0);
    EXPECT_EQ(result.goals_completed, 0);
    EXPECT_EQ(result.iteration_results.size(), 0);
    EXPECT_FALSE(result.stopped_early);
}
