/**
 * @file cross_language_circuit_breaker_behavior_test.cpp
 * @brief Cross-language circuit breaker behavior tests for C++
 *
 * Validates that Agenkit's C++ circuit breaker middleware behaves consistently
 * with the cross-language circuit breaker behavior specification.
 */

#include <gtest/gtest.h>
#include <fstream>
#include <chrono>
#include <thread>
#include <nlohmann/json.hpp>
#include "agenkit/middleware/circuit_breaker.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"

using json = nlohmann::json;
using namespace agenkit::core;
using namespace agenkit::middleware;
using namespace std::chrono;

/// Agent response from fixture
struct AgentResponse {
    bool success;
    std::string content;
    std::string error;
};

/// Mock agent that simulates responses for circuit breaker testing
class MockCircuitBreakerAgent : public Agent {
public:
    explicit MockCircuitBreakerAgent(const std::vector<AgentResponse>& responses)
        : responses_(responses), call_count_(0) {}

    std::string name() const override {
        return "mock-circuit-breaker-agent";
    }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        return std::async(std::launch::async, [this, message]() -> Result<Message, AgentError> {
            size_t index = call_count_.fetch_add(1);

            if (index >= responses_.size()) {
                return Result<Message, AgentError>::err(
                    AgentError(AgentErrorType::ProcessingError, "No more responses available")
                );
            }

            const auto& response = responses_[index];

            if (response.success) {
                return Result<Message, AgentError>::ok(Message("agent", response.content));
            } else {
                return Result<Message, AgentError>::err(
                    AgentError(AgentErrorType::ProcessingError, response.error)
                );
            }
        });
    }

    size_t get_call_count() const {
        return call_count_.load();
    }

private:
    std::vector<AgentResponse> responses_;
    std::atomic<size_t> call_count_;
};

/// Test fixture class
class CrossLanguageCircuitBreakerTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Load fixtures - path is relative to build/tests working directory
        std::ifstream fixtures_file("../../../tests/cross_language/fixtures/circuit_breaker_behavior.json");
        ASSERT_TRUE(fixtures_file.is_open()) << "Failed to open circuit_breaker_behavior.json";
        fixtures_file >> fixtures_;
    }

    json find_test_case(const std::string& id) {
        for (const auto& test_case : fixtures_["test_cases"]) {
            if (test_case["id"] == id) {
                return test_case;
            }
        }
        ADD_FAILURE() << "Test case not found: " << id;
        return json::object();
    }

    AgentResponse parse_response(const json& response_json) {
        AgentResponse response;
        response.success = response_json["success"].get<bool>();
        if (response_json.contains("content")) {
            response.content = response_json["content"].get<std::string>();
        }
        if (response_json.contains("error")) {
            response.error = response_json["error"].get<std::string>();
        }
        return response;
    }

    std::vector<AgentResponse> parse_responses(const json& responses_json) {
        std::vector<AgentResponse> responses;
        for (const auto& response_json : responses_json) {
            responses.push_back(parse_response(response_json));
        }
        return responses;
    }

    CircuitBreakerConfig create_config(const json& config_data) {
        return CircuitBreakerConfig::builder()
            .failure_threshold(config_data["failure_threshold"].get<uint32_t>())
            .recovery_timeout(milliseconds(config_data["recovery_timeout_ms"].get<uint64_t>()))
            .success_threshold(config_data["success_threshold"].get<uint32_t>())
            .timeout(milliseconds(config_data["timeout_ms"].get<uint64_t>()))
            .build();
    }

    std::string state_to_lower(CircuitState state) {
        switch (state) {
            case CircuitState::CLOSED: return "closed";
            case CircuitState::OPEN: return "open";
            case CircuitState::HALF_OPEN: return "half_open";
            default: return "unknown";
        }
    }

    /// Render a state_changes map for assertion messages.
    static std::string describe(const std::map<std::string, uint64_t>& changes) {
        std::string out = "{";
        for (const auto& [key, count] : changes) {
            if (out.size() > 1) out += ", ";
            out += key + ": " + std::to_string(count);
        }
        return out + "}";
    }

    /// Expect every named transition was taken at least once.
    ///
    /// Final-state checks alone are weak: a breaker that opened and never probed half-open
    /// ends "open" just like one that reopened after a failed probe, and one that never
    /// opened at all ends "closed" just like one that fully recovered. Checking the path
    /// distinguishes them. These replace `EXPECT_TRUE(expected["some_flag"].get<bool>())`,
    /// which only proved the fixture contained `true` and passed with the middleware
    /// deleted (#791).
    static void expect_transitions(
        const std::map<std::string, uint64_t>& changes,
        const std::vector<std::string>& expected
    ) {
        for (const auto& key : expected) {
            auto it = changes.find(key);
            uint64_t count = it == changes.end() ? 0 : it->second;
            EXPECT_GE(count, 1u) << "transition " << key << " never happened: "
                                 << describe(changes);
        }
    }

    json fixtures_;
};

TEST_F(CrossLanguageCircuitBreakerTest, ClosedSuccess) {
    auto test_case = find_test_case("circuit_breaker_closed_success");

    // Create mock agent
    auto responses = parse_responses(test_case["scenario"]["agent_responses"]);
    auto mock_agent = std::make_shared<MockCircuitBreakerAgent>(responses);

    // Create circuit breaker
    auto config = create_config(test_case["config"]);
    auto circuit_breaker = std::make_shared<CircuitBreakerMiddleware>(mock_agent, config);

    // Execute requests
    size_t successful = 0;
    for (size_t i = 0; i < responses.size(); i++) {
        Message msg("user", "test");
        auto result = circuit_breaker->process(msg).get();
        if (result.is_ok()) {
            successful++;
        }
    }

    // Verify expected behavior
    const auto& expected = test_case["expected_behavior"];
    auto metrics = circuit_breaker->metrics().snapshot(circuit_breaker->state());

    EXPECT_EQ(state_to_lower(circuit_breaker->state()), expected["final_state"].get<std::string>());
    EXPECT_EQ(metrics.total_requests, expected["total_requests"].get<uint64_t>());
    EXPECT_EQ(metrics.successful_requests, expected["successful_requests"].get<uint64_t>());
    EXPECT_EQ(metrics.failed_requests, expected["failed_requests"].get<uint64_t>());
    EXPECT_EQ(metrics.rejected_requests, expected["rejected_requests"].get<uint64_t>());
    EXPECT_EQ(successful, expected["total_requests"].get<size_t>());

    // A circuit that never leaves CLOSED records no transitions at all.
    EXPECT_TRUE(metrics.state_changes.empty()) << describe(metrics.state_changes);
    EXPECT_EQ(metrics.state_transitions, 0u);
}

TEST_F(CrossLanguageCircuitBreakerTest, OpensOnFailures) {
    auto test_case = find_test_case("circuit_breaker_opens_on_failures");

    // Create mock agent
    auto responses = parse_responses(test_case["scenario"]["agent_responses"]);
    auto mock_agent = std::make_shared<MockCircuitBreakerAgent>(responses);

    // Create circuit breaker
    auto config = create_config(test_case["config"]);
    auto circuit_breaker = std::make_shared<CircuitBreakerMiddleware>(mock_agent, config);

    // Execute requests, recording each outcome so per-request claims can be checked
    size_t rejected = 0;
    std::vector<std::string> outcomes;
    for (size_t i = 0; i < responses.size(); i++) {
        Message msg("user", "test");
        auto result = circuit_breaker->process(msg).get();
        if (result.is_ok()) {
            outcomes.push_back("ok");
            continue;
        }
        auto error = result.unwrap_err();
        if (error.type() == AgentErrorType::ProcessingError &&
            error.message().find("Circuit breaker is OPEN") != std::string::npos) {
            rejected++;
            outcomes.push_back("rejected");
        } else {
            outcomes.push_back("failed");
        }
    }

    // Verify expected behavior
    const auto& expected = test_case["expected_behavior"];
    auto metrics = circuit_breaker->metrics().snapshot(circuit_breaker->state());

    EXPECT_EQ(state_to_lower(circuit_breaker->state()), expected["final_state"].get<std::string>());
    EXPECT_EQ(metrics.total_requests, expected["total_requests"].get<uint64_t>());
    EXPECT_EQ(metrics.failed_requests, expected["failed_requests"].get<uint64_t>());
    EXPECT_EQ(metrics.rejected_requests, expected["rejected_requests"].get<uint64_t>());
    EXPECT_GT(rejected, 0u);

    // `EXPECT_TRUE(expected["fourth_request_rejected"].get<bool>())` was a tautology (#791).
    // Check the actual claim — the fourth request was rejected by the open circuit, not
    // merely failed by the inner agent (whose fourth scripted response is a success).
    if (expected.value("fourth_request_rejected", false)) {
        ASSERT_EQ(outcomes.size(), 4u);
        EXPECT_EQ(outcomes[3], "rejected") << "expected 4th request rejected";
    }
}

TEST_F(CrossLanguageCircuitBreakerTest, HalfOpenTransition) {
    auto test_case = find_test_case("circuit_breaker_half_open_transition");

    // Extract responses from steps
    std::vector<AgentResponse> responses;
    for (const auto& step : test_case["scenario"]["steps"]) {
        if (step["action"] == "request") {
            responses.push_back(parse_response(step["agent_response"]));
        }
    }

    auto mock_agent = std::make_shared<MockCircuitBreakerAgent>(responses);

    // Create circuit breaker
    auto config = create_config(test_case["config"]);
    auto circuit_breaker = std::make_shared<CircuitBreakerMiddleware>(mock_agent, config);

    // Execute steps
    for (const auto& step : test_case["scenario"]["steps"]) {
        if (step["action"] == "request") {
            Message msg("user", "test");
            auto result = circuit_breaker->process(msg).get();
            // Ignore result - we're testing state transitions
            (void)result;
        } else if (step["action"] == "wait") {
            std::this_thread::sleep_for(milliseconds(step["duration_ms"].get<uint64_t>()));
        }
    }

    // Verify expected behavior
    const auto& expected = test_case["expected_behavior"];
    auto metrics = circuit_breaker->metrics().snapshot(circuit_breaker->state());
    EXPECT_EQ(state_to_lower(circuit_breaker->state()), expected["final_state"].get<std::string>());
    if (expected.value("recovery_successful", false)) {
        expect_transitions(metrics.state_changes,
                           {"closed->open", "open->half_open", "half_open->closed"});
    }
}

TEST_F(CrossLanguageCircuitBreakerTest, HalfOpenToClosed) {
    auto test_case = find_test_case("circuit_breaker_half_open_to_closed");

    // Extract responses from steps
    std::vector<AgentResponse> responses;
    for (const auto& step : test_case["scenario"]["steps"]) {
        if (step["action"] == "request") {
            responses.push_back(parse_response(step["agent_response"]));
        }
    }

    auto mock_agent = std::make_shared<MockCircuitBreakerAgent>(responses);

    // Create circuit breaker
    auto config = create_config(test_case["config"]);
    auto circuit_breaker = std::make_shared<CircuitBreakerMiddleware>(mock_agent, config);

    // Execute steps
    for (const auto& step : test_case["scenario"]["steps"]) {
        if (step["action"] == "request") {
            Message msg("user", "test");
            auto result = circuit_breaker->process(msg).get();
            (void)result;
        } else if (step["action"] == "wait") {
            std::this_thread::sleep_for(milliseconds(step["duration_ms"].get<uint64_t>()));
        }
    }

    // Verify expected behavior
    const auto& expected = test_case["expected_behavior"];
    auto metrics = circuit_breaker->metrics().snapshot(circuit_breaker->state());
    EXPECT_EQ(state_to_lower(circuit_breaker->state()), expected["final_state"].get<std::string>());
    if (expected.value("circuit_fully_recovered", false)) {
        expect_transitions(metrics.state_changes, {"open->half_open", "half_open->closed"});
    }
}

TEST_F(CrossLanguageCircuitBreakerTest, HalfOpenReopens) {
    auto test_case = find_test_case("circuit_breaker_half_open_reopens");

    // Extract responses from steps
    std::vector<AgentResponse> responses;
    for (const auto& step : test_case["scenario"]["steps"]) {
        if (step["action"] == "request") {
            responses.push_back(parse_response(step["agent_response"]));
        }
    }

    auto mock_agent = std::make_shared<MockCircuitBreakerAgent>(responses);

    // Create circuit breaker
    auto config = create_config(test_case["config"]);
    auto circuit_breaker = std::make_shared<CircuitBreakerMiddleware>(mock_agent, config);

    // Execute steps
    for (const auto& step : test_case["scenario"]["steps"]) {
        if (step["action"] == "request") {
            Message msg("user", "test");
            auto result = circuit_breaker->process(msg).get();
            (void)result;
        } else if (step["action"] == "wait") {
            std::this_thread::sleep_for(milliseconds(step["duration_ms"].get<uint64_t>()));
        }
    }

    // Verify expected behavior
    const auto& expected = test_case["expected_behavior"];
    auto metrics = circuit_breaker->metrics().snapshot(circuit_breaker->state());
    EXPECT_EQ(state_to_lower(circuit_breaker->state()), expected["final_state"].get<std::string>());
    if (expected.value("reopened_after_partial_recovery", false)) {
        expect_transitions(metrics.state_changes,
                           {"closed->open", "open->half_open", "half_open->open"});
    }
}

TEST_F(CrossLanguageCircuitBreakerTest, RejectsWhenOpen) {
    auto test_case = find_test_case("circuit_breaker_rejects_when_open");

    // Create mock agent
    auto responses = parse_responses(test_case["scenario"]["agent_responses"]);
    auto mock_agent = std::make_shared<MockCircuitBreakerAgent>(responses);

    // Create circuit breaker
    auto config = create_config(test_case["config"]);
    auto circuit_breaker = std::make_shared<CircuitBreakerMiddleware>(mock_agent, config);

    // Execute requests
    size_t rejected = 0;
    for (size_t i = 0; i < responses.size(); i++) {
        Message msg("user", "test");
        auto result = circuit_breaker->process(msg).get();
        if (result.is_err()) {
            auto error = result.unwrap_err();
            if (error.type() == AgentErrorType::ProcessingError &&
                error.message().find("Circuit breaker is OPEN") != std::string::npos) {
                rejected++;
            }
        }
    }

    // Verify expected behavior
    const auto& expected = test_case["expected_behavior"];
    auto metrics = circuit_breaker->metrics().snapshot(circuit_breaker->state());

    EXPECT_EQ(state_to_lower(circuit_breaker->state()), expected["final_state"].get<std::string>());
    EXPECT_EQ(metrics.rejected_requests, expected["rejected_requests"].get<uint64_t>());
    EXPECT_EQ(rejected, expected["rejected_requests"].get<size_t>());
}

TEST_F(CrossLanguageCircuitBreakerTest, MetricsTracking) {
    auto test_case = find_test_case("circuit_breaker_metrics_tracking");

    // Extract responses from steps
    std::vector<AgentResponse> responses;
    for (const auto& step : test_case["scenario"]["steps"]) {
        if (step["action"] == "request") {
            responses.push_back(parse_response(step["agent_response"]));
        }
    }

    auto mock_agent = std::make_shared<MockCircuitBreakerAgent>(responses);

    // Create circuit breaker
    auto config = create_config(test_case["config"]);
    auto circuit_breaker = std::make_shared<CircuitBreakerMiddleware>(mock_agent, config);

    // Execute steps
    for (const auto& step : test_case["scenario"]["steps"]) {
        if (step["action"] == "request") {
            Message msg("user", "test");
            auto result = circuit_breaker->process(msg).get();
            (void)result;
        } else if (step["action"] == "wait") {
            std::this_thread::sleep_for(milliseconds(step["duration_ms"].get<uint64_t>()));
        }
    }

    // Verify expected metrics
    const auto& expected = test_case["expected_metrics"];
    auto metrics = circuit_breaker->metrics().snapshot(circuit_breaker->state());

    EXPECT_EQ(metrics.total_requests, expected["total_requests"].get<uint64_t>());
    EXPECT_EQ(metrics.successful_requests, expected["successful_requests"].get<uint64_t>());
    EXPECT_EQ(metrics.failed_requests, expected["failed_requests"].get<uint64_t>());
    EXPECT_EQ(metrics.rejected_requests, expected["rejected_requests"].get<uint64_t>());
    EXPECT_EQ(state_to_lower(circuit_breaker->state()), expected["final_state"].get<std::string>());

    // Assert the state_changes map itself, not just the scalar counters. This field is the
    // cross-language transition-key contract; it went unasserted in all five harnesses long
    // enough for four different key formats to appear — and this core did not have a keyed
    // map at all, only the `state_transitions` total (#791).
    std::map<std::string, uint64_t> want_changes;
    for (const auto& [key, count] : expected["state_changes"].items()) {
        want_changes[key] = count.get<uint64_t>();
    }
    EXPECT_EQ(metrics.state_changes, want_changes) << "got " << describe(metrics.state_changes);

    // The scalar total must stay consistent with the keyed map it now derives from.
    uint64_t keyed_total = 0;
    for (const auto& [key, count] : metrics.state_changes) {
        (void)key;
        keyed_total += count;
    }
    EXPECT_EQ(metrics.state_transitions, keyed_total);
}
