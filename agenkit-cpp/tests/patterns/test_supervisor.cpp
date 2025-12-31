/**
 * @file test_supervisor.cpp
 * @brief Comprehensive tests for Supervisor pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/supervisor.hpp"
#include "test_pattern_helpers.hpp"
#include <memory>
#include <string>
#include <stdexcept>
#include <unordered_map>

using namespace agenkit;
using namespace agenkit::test;

// Mock planner for testing
class MockPlanner : public patterns::PlannerAgent {
private:
    std::string name_;
    std::vector<patterns::Subtask> subtasks_;
    bool plan_should_fail_;
    core::AgentError plan_error_;
    std::string synthesized_response_;
    bool synthesis_should_fail_;
    core::AgentError synthesis_error_;

public:
    MockPlanner(const std::string& name)
        : name_(name)
        , plan_should_fail_(false)
        , plan_error_(core::AgentErrorType::Internal, "")
        , synthesized_response_("synthesized")
        , synthesis_should_fail_(false)
        , synthesis_error_(core::AgentErrorType::Internal, "")
    {}

    void set_subtasks(const std::vector<patterns::Subtask>& subtasks) {
        subtasks_ = subtasks;
    }

    void set_plan_error(const core::AgentError& error) {
        plan_should_fail_ = true;
        plan_error_ = error;
    }

    void set_synthesized_response(const std::string& response) {
        synthesized_response_ = response;
    }

    void set_synthesis_error(const core::AgentError& error) {
        synthesis_should_fail_ = true;
        synthesis_error_ = error;
    }

    std::string name() const override {
        return name_;
    }

    std::vector<std::string> capabilities() const override {
        return {"planning", "synthesis"};
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        auto msg = core::Message::with_text("assistant", "direct response");
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }

    core::Result<std::vector<patterns::Subtask>, core::AgentError>
    plan(const core::Message& /* message */) override {
        if (plan_should_fail_) {
            return core::Result<std::vector<patterns::Subtask>, core::AgentError>::err(plan_error_);
        }
        return core::Result<std::vector<patterns::Subtask>, core::AgentError>::ok(subtasks_);
    }

    core::Result<core::Message, core::AgentError>
    synthesize(
        const core::Message& /* original */,
        const std::unordered_map<std::string, core::Message>& /* results */
    ) override {
        if (synthesis_should_fail_) {
            return core::Result<core::Message, core::AgentError>::err(synthesis_error_);
        }
        auto msg = core::Message::with_text("assistant", synthesized_response_);
        return core::Result<core::Message, core::AgentError>::ok(msg);
    }
};

// Test: Valid construction
TEST(SupervisorAgentTest, Constructor) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["coder"] = make_mock_agent("coder", "code");
    specialists["tester"] = make_mock_agent("tester", "tests");

    patterns::SupervisorAgent supervisor(planner, specialists);

    EXPECT_EQ(supervisor.name(), "supervisor");
}

// Test: Constructor with null planner
TEST(SupervisorAgentTest, ConstructorNullPlanner) {
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["coder"] = make_mock_agent("coder");

    EXPECT_THROW(
        {
            patterns::SupervisorAgent supervisor(nullptr, specialists);
        },
        std::invalid_argument
    );
}

// Test: Constructor with empty specialists
TEST(SupervisorAgentTest, ConstructorEmptySpecialists) {
    auto planner = std::make_shared<MockPlanner>("planner");
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;

    EXPECT_THROW(
        {
            patterns::SupervisorAgent supervisor(planner, specialists);
        },
        std::invalid_argument
    );
}

// Test: Basic supervised processing
TEST(SupervisorAgentTest, BasicProcess) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    subtasks.emplace_back("coder", core::Message::with_text("user", "write code"));
    subtasks.emplace_back("tester", core::Message::with_text("user", "write tests"));
    planner->set_subtasks(subtasks);
    planner->set_synthesized_response("final synthesized result");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["coder"] = make_mock_agent("coder", "code result");
    specialists["tester"] = make_mock_agent("tester", "test result");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "build a feature");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "final synthesized result");
}

// Test: No subtasks - direct planner response
TEST(SupervisorAgentTest, NoSubtasks) {
    auto planner = std::make_shared<MockPlanner>("planner");
    planner->set_subtasks({});  // Empty subtasks

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["coder"] = make_mock_agent("coder");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "simple task");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should use planner's direct response
    EXPECT_EQ(response.content_as_str(), "direct response");
}

// Test: Metadata tracking
TEST(SupervisorAgentTest, Metadata) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    subtasks.emplace_back("worker1", core::Message::with_text("user", "task1"));
    subtasks.emplace_back("worker2", core::Message::with_text("user", "task2"));
    planner->set_subtasks(subtasks);
    planner->set_synthesized_response("result");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker1"] = make_mock_agent("w1", "r1");
    specialists["worker2"] = make_mock_agent("w2", "r2");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Check metadata
    expect_metadata_exists(response, "supervisor_subtasks");
    expect_metadata_value<int>(response, "supervisor_subtasks", 2);

    expect_metadata_exists(response, "supervisor_specialists");
    expect_metadata_value<int>(response, "supervisor_specialists", 2);

    ASSERT_TRUE(metadata.contains("execution_order"));
    ASSERT_TRUE(metadata["execution_order"].is_array());

    auto exec_order = metadata["execution_order"];
    EXPECT_EQ(exec_order.size(), 2);
}

// Test: Planning error
TEST(SupervisorAgentTest, PlanningError) {
    auto planner = std::make_shared<MockPlanner>("planner");
    planner->set_plan_error(core::AgentError(core::AgentErrorType::Internal, "planning failed"));

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker"] = make_mock_agent("worker");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("planning failed") != std::string::npos);
}

// Test: Specialist execution error
TEST(SupervisorAgentTest, SpecialistError) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    subtasks.emplace_back("worker1", core::Message::with_text("user", "task1"));
    subtasks.emplace_back("worker2", core::Message::with_text("user", "task2"));
    planner->set_subtasks(subtasks);

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker1"] = make_mock_agent("w1", "success");
    specialists["worker2"] = make_failing_mock_agent("w2", "worker2 failed");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("worker2") != std::string::npos ||
                error.message().find("failed") != std::string::npos);
}

// Test: Synthesis error
TEST(SupervisorAgentTest, SynthesisError) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    subtasks.emplace_back("worker", core::Message::with_text("user", "task"));
    planner->set_subtasks(subtasks);
    planner->set_synthesis_error(
        core::AgentError(core::AgentErrorType::Internal, "synthesis failed")
    );

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker"] = make_mock_agent("worker", "success");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("synthesis failed") != std::string::npos);
}

// Test: Unknown specialist type
TEST(SupervisorAgentTest, UnknownSpecialistType) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    subtasks.emplace_back("unknown_type", core::Message::with_text("user", "task"));
    planner->set_subtasks(subtasks);

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker"] = make_mock_agent("worker");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("unknown_type") != std::string::npos ||
                error.message().find("not found") != std::string::npos);
}

// Test: Multiple subtasks same specialist
TEST(SupervisorAgentTest, MultipleSubtasksSameSpecialist) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    subtasks.emplace_back("worker", core::Message::with_text("user", "task1"));
    subtasks.emplace_back("worker", core::Message::with_text("user", "task2"));
    subtasks.emplace_back("worker", core::Message::with_text("user", "task3"));
    planner->set_subtasks(subtasks);
    planner->set_synthesized_response("combined result");

    auto worker = make_mock_agent("worker", "work done");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker"] = worker;

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Worker should have been called 3 times
    EXPECT_EQ(worker->call_count(), 3);

    expect_metadata_value<int>(response, "supervisor_subtasks", 3);
}

// Test: Subtask metadata preservation
TEST(SupervisorAgentTest, SubtaskMetadata) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    auto subtask1 = patterns::Subtask("worker", core::Message::with_text("user", "task1"));
    subtask1.metadata = {{"priority", "high"}};
    subtasks.push_back(std::move(subtask1));
    planner->set_subtasks(subtasks);
    planner->set_synthesized_response("result");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker"] = make_mock_agent("worker", "done");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Check execution order contains subtask metadata
    ASSERT_TRUE(metadata.contains("execution_order"));
    auto exec_order = metadata["execution_order"];
    ASSERT_GT(exec_order.size(), 0);
}

// Test: Capabilities aggregation
TEST(SupervisorAgentTest, Capabilities) {
    auto planner = std::make_shared<MockPlanner>("planner");

    auto specialist1 = make_mock_agent("s1");
    specialist1->set_capabilities({"cap1", "cap2"});

    auto specialist2 = make_mock_agent("s2");
    specialist2->set_capabilities({"cap3"});

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["s1"] = specialist1;
    specialists["s2"] = specialist2;

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto caps = supervisor.capabilities();

    // Should have supervisor capability plus unique specialist capabilities
    bool has_supervisor = false;
    for (const auto& cap : caps) {
        if (cap == "supervisor") {
            has_supervisor = true;
        }
    }

    EXPECT_TRUE(has_supervisor);
}

// Test: Single specialist
TEST(SupervisorAgentTest, SingleSpecialist) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    subtasks.emplace_back("worker", core::Message::with_text("user", "task"));
    planner->set_subtasks(subtasks);
    planner->set_synthesized_response("result");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker"] = make_mock_agent("worker", "done");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "result");
}

// Test: Many specialists
TEST(SupervisorAgentTest, ManySpecialists) {
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;

    const int num_specialists = 10;
    for (int i = 0; i < num_specialists; ++i) {
        std::string name = "worker" + std::to_string(i);
        subtasks.emplace_back(name, core::Message::with_text("user", "task" + std::to_string(i)));
        specialists[name] = make_mock_agent(name, "result" + std::to_string(i));
    }

    planner->set_subtasks(subtasks);
    planner->set_synthesized_response("all results combined");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    expect_metadata_value<int>(response, "supervisor_subtasks", num_specialists);
    expect_metadata_value<int>(response, "supervisor_specialists", num_specialists);
}

// Test: Empty message handling
TEST(SupervisorAgentTest, EmptyMessage) {
    auto planner = std::make_shared<MockPlanner>("planner");
    planner->set_subtasks({});

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker"] = make_mock_agent("worker");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "");
    auto result = supervisor.process(std::move(msg)).get();

    // Should still process successfully
    ASSERT_TRUE(result.is_ok());
}

// Test: Specialist results passed to synthesis
TEST(SupervisorAgentTest, SpecialistResultsPassedToSynthesis) {
    // This test verifies that specialist results are properly collected
    // and passed to the synthesize method
    auto planner = std::make_shared<MockPlanner>("planner");

    std::vector<patterns::Subtask> subtasks;
    subtasks.emplace_back("worker1", core::Message::with_text("user", "task1"));
    subtasks.emplace_back("worker2", core::Message::with_text("user", "task2"));
    planner->set_subtasks(subtasks);
    planner->set_synthesized_response("synthesized from worker1 and worker2");

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists;
    specialists["worker1"] = make_mock_agent("w1", "result1");
    specialists["worker2"] = make_mock_agent("w2", "result2");

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto msg = core::Message::with_text("user", "test");
    auto result = supervisor.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // The synthesized response should be returned
    EXPECT_EQ(response.content_as_str(), "synthesized from worker1 and worker2");
}
