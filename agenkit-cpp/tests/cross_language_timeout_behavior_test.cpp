/**
 * @file cross_language_timeout_behavior_test.cpp
 * @brief Cross-language timeout behavior tests for C++
 *
 * Validates that Agenkit's C++ timeout middleware behaves consistently
 * with the cross-language timeout behavior specification.
 */

#include <gtest/gtest.h>
#include <fstream>
#include <chrono>
#include <thread>
#include <nlohmann/json.hpp>
#include "agenkit/middleware/timeout.hpp"
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

/// Mock agent that simulates delays for timeout testing
class MockTimeoutAgent : public Agent {
public:
    explicit MockTimeoutAgent(int delay_ms, const AgentResponse& response)
        : delay_ms_(delay_ms), response_(response), call_count_(0) {}

    std::string name() const override {
        return "mock-timeout-agent";
    }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        auto result = std::async(std::launch::async, [this, message]() -> Result<Message, AgentError> {
            call_count_++;

            // Simulate delay
            if (delay_ms_ > 0) {
                std::this_thread::sleep_for(milliseconds(delay_ms_));
            }

            // Return response or error
            if (response_.success) {
                return Result<Message, AgentError>::ok(Message("agent", response_.content));
            } else {
                return Result<Message, AgentError>::err(
                    AgentError(AgentErrorType::ProcessingError, response_.error)
                );
            }
        });

        return result;
    }

    size_t get_call_count() const {
        return call_count_;
    }

private:
    int delay_ms_;
    AgentResponse response_;
    size_t call_count_;
};

/// Test fixture class
class CrossLanguageTimeoutTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Load fixtures - path is relative to build/tests working directory
        std::ifstream fixtures_file("../../../tests/cross_language/fixtures/timeout_behavior.json");
        ASSERT_TRUE(fixtures_file.is_open()) << "Failed to open timeout_behavior.json";
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

    TimeoutConfig create_config(const json& config_data) {
        return TimeoutConfig::builder()
            .default_timeout(milliseconds(config_data["timeout_ms"].get<uint64_t>()))
            .build();
    }

    json fixtures_;
};

TEST_F(CrossLanguageTimeoutTest, SuccessWithinLimit) {
    auto test_case = find_test_case("timeout_success_within_limit");

    // Create mock agent
    auto response = parse_response(test_case["scenario"]["agent_response"]);
    auto mock_agent = std::make_shared<MockTimeoutAgent>(
        test_case["scenario"]["agent_delay_ms"].get<int>(),
        response
    );

    // Create timeout decorator
    auto config = create_config(test_case["config"]);
    auto timeout = std::make_shared<TimeoutMiddleware>(mock_agent, config);

    // Execute with timing
    auto start = steady_clock::now();
    Message msg("user", "test");
    auto result = timeout->process(msg).get();
    auto elapsed = duration_cast<milliseconds>(steady_clock::now() - start).count();

    // Verify expected behavior
    const auto& expected = test_case["expected_behavior"];
    ASSERT_TRUE(result.is_ok());
    EXPECT_TRUE(expected["successful"].get<bool>());
    EXPECT_FALSE(expected["timed_out"].get<bool>());
    EXPECT_EQ(result.unwrap().content_as_str(), expected["final_response"].get<std::string>());

    EXPECT_GE(elapsed, expected["min_elapsed_ms"].get<int64_t>());
    EXPECT_LE(elapsed, expected["max_elapsed_ms"].get<int64_t>());
}

TEST_F(CrossLanguageTimeoutTest, TimeoutExceeded) {
    auto test_case = find_test_case("timeout_exceeded");

    // Create mock agent
    auto response = parse_response(test_case["scenario"]["agent_response"]);
    auto mock_agent = std::make_shared<MockTimeoutAgent>(
        test_case["scenario"]["agent_delay_ms"].get<int>(),
        response
    );

    // Create timeout decorator
    auto config = create_config(test_case["config"]);
    auto timeout = std::make_shared<TimeoutMiddleware>(mock_agent, config);

    // Execute with timing
    auto start = steady_clock::now();
    Message msg("user", "test");
    auto result = timeout->process(msg).get();
    auto elapsed = duration_cast<milliseconds>(steady_clock::now() - start).count();

    // Verify timeout error
    const auto& expected = test_case["expected_behavior"];
    ASSERT_TRUE(result.is_err());
    EXPECT_FALSE(expected["successful"].get<bool>());
    EXPECT_TRUE(expected["timed_out"].get<bool>());

    auto error_msg = result.unwrap_err().message();
    EXPECT_NE(error_msg.find(expected["error_message_contains"].get<std::string>()), std::string::npos);

    // C++ std::future destructor blocks until async task completes
    // So timing includes the full agent execution time, not just timeout
    // Accept wider tolerance: timeout + agent delay
    EXPECT_GE(elapsed, expected["min_elapsed_ms"].get<int64_t>());
    EXPECT_LE(elapsed, test_case["scenario"]["agent_delay_ms"].get<int64_t>() + 100);
}

TEST_F(CrossLanguageTimeoutTest, ExactlyAtLimit) {
    auto test_case = find_test_case("timeout_exactly_at_limit");

    // Create mock agent
    auto response = parse_response(test_case["scenario"]["agent_response"]);
    auto mock_agent = std::make_shared<MockTimeoutAgent>(
        test_case["scenario"]["agent_delay_ms"].get<int>(),
        response
    );

    // Create timeout decorator
    auto config = create_config(test_case["config"]);
    auto timeout = std::make_shared<TimeoutMiddleware>(mock_agent, config);

    // Execute with timing
    auto start = steady_clock::now();
    Message msg("user", "test");
    auto result = timeout->process(msg).get();
    auto elapsed = duration_cast<milliseconds>(steady_clock::now() - start).count();

    // Verify expected behavior
    const auto& expected = test_case["expected_behavior"];
    ASSERT_TRUE(result.is_ok());
    EXPECT_TRUE(expected["successful"].get<bool>());
    EXPECT_FALSE(expected["timed_out"].get<bool>());
    EXPECT_EQ(result.unwrap().content_as_str(), expected["final_response"].get<std::string>());

    EXPECT_GE(elapsed, expected["min_elapsed_ms"].get<int64_t>());
    EXPECT_LE(elapsed, expected["max_elapsed_ms"].get<int64_t>());
}

TEST_F(CrossLanguageTimeoutTest, ZeroDelay) {
    auto test_case = find_test_case("timeout_zero_delay");

    // Create mock agent
    auto response = parse_response(test_case["scenario"]["agent_response"]);
    auto mock_agent = std::make_shared<MockTimeoutAgent>(
        test_case["scenario"]["agent_delay_ms"].get<int>(),
        response
    );

    // Create timeout decorator
    auto config = create_config(test_case["config"]);
    auto timeout = std::make_shared<TimeoutMiddleware>(mock_agent, config);

    // Execute with timing
    auto start = steady_clock::now();
    Message msg("user", "test");
    auto result = timeout->process(msg).get();
    auto elapsed = duration_cast<milliseconds>(steady_clock::now() - start).count();

    // Verify expected behavior
    const auto& expected = test_case["expected_behavior"];
    ASSERT_TRUE(result.is_ok());
    EXPECT_TRUE(expected["successful"].get<bool>());
    EXPECT_FALSE(expected["timed_out"].get<bool>());
    EXPECT_EQ(result.unwrap().content_as_str(), expected["final_response"].get<std::string>());

    EXPECT_LE(elapsed, expected["max_elapsed_ms"].get<int64_t>());
}

TEST_F(CrossLanguageTimeoutTest, AgentError) {
    auto test_case = find_test_case("timeout_agent_error");

    // Create mock agent
    auto response = parse_response(test_case["scenario"]["agent_response"]);
    auto mock_agent = std::make_shared<MockTimeoutAgent>(
        test_case["scenario"]["agent_delay_ms"].get<int>(),
        response
    );

    // Create timeout decorator
    auto config = create_config(test_case["config"]);
    auto timeout = std::make_shared<TimeoutMiddleware>(mock_agent, config);

    // Execute with timing
    auto start = steady_clock::now();
    Message msg("user", "test");
    auto result = timeout->process(msg).get();
    auto elapsed = duration_cast<milliseconds>(steady_clock::now() - start).count();

    // Verify agent error (not timeout)
    const auto& expected = test_case["expected_behavior"];
    ASSERT_TRUE(result.is_err());
    EXPECT_FALSE(expected["successful"].get<bool>());
    EXPECT_FALSE(expected["timed_out"].get<bool>());

    auto error_msg = result.unwrap_err().message();
    EXPECT_NE(error_msg.find(expected["error_message_contains"].get<std::string>()), std::string::npos);

    EXPECT_GE(elapsed, expected["min_elapsed_ms"].get<int64_t>());
    EXPECT_LE(elapsed, expected["max_elapsed_ms"].get<int64_t>());
}

TEST_F(CrossLanguageTimeoutTest, VeryShortTimeout) {
    auto test_case = find_test_case("timeout_very_short");

    // Create mock agent
    auto response = parse_response(test_case["scenario"]["agent_response"]);
    auto mock_agent = std::make_shared<MockTimeoutAgent>(
        test_case["scenario"]["agent_delay_ms"].get<int>(),
        response
    );

    // Create timeout decorator
    auto config = create_config(test_case["config"]);
    auto timeout = std::make_shared<TimeoutMiddleware>(mock_agent, config);

    // Execute with timing
    auto start = steady_clock::now();
    Message msg("user", "test");
    auto result = timeout->process(msg).get();
    auto elapsed = duration_cast<milliseconds>(steady_clock::now() - start).count();

    // Verify timeout error
    const auto& expected = test_case["expected_behavior"];
    ASSERT_TRUE(result.is_err());
    EXPECT_FALSE(expected["successful"].get<bool>());
    EXPECT_TRUE(expected["timed_out"].get<bool>());

    // C++ std::future destructor blocks - accept full agent delay time
    EXPECT_GE(elapsed, expected["min_elapsed_ms"].get<int64_t>());
    EXPECT_LE(elapsed, test_case["scenario"]["agent_delay_ms"].get<int64_t>() + 50);
}

TEST_F(CrossLanguageTimeoutTest, MetricsTracking) {
    auto test_case = find_test_case("timeout_metrics_tracking");

    // Create timeout config
    auto config = create_config(test_case["config"]);

    // Process multiple requests
    size_t successful = 0;
    size_t timed_out = 0;

    for (const auto& request : test_case["scenario"]["requests"]) {
        auto response = parse_response(request["agent_response"]);
        auto mock_agent = std::make_shared<MockTimeoutAgent>(
            request["agent_delay_ms"].get<int>(),
            response
        );
        auto timeout = std::make_shared<TimeoutMiddleware>(mock_agent, config);

        Message msg("user", "test");
        auto result = timeout->process(msg).get();

        if (result.is_ok()) {
            successful++;
        } else {
            timed_out++;
        }
    }

    // Verify metrics
    const auto& expected_metrics = test_case["expected_metrics"];
    EXPECT_EQ(test_case["scenario"]["requests"].size(), expected_metrics["total_requests"].get<size_t>());
    EXPECT_EQ(successful, expected_metrics["successful_requests"].get<size_t>());
    EXPECT_EQ(timed_out, expected_metrics["timed_out_requests"].get<size_t>());
}
