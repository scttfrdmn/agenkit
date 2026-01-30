/**
 * @file test_utils.hpp
 * @brief Test utilities for Agenkit C++
 *
 * Provides reusable mocks, fixtures, and helpers for testing agents.
 */

#ifndef AGENKIT_TESTS_TEST_UTILS_HPP
#define AGENKIT_TESTS_TEST_UTILS_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/errors.hpp"
#include "agenkit/core/result.hpp"
#include <vector>
#include <string>
#include <sstream>
#include <atomic>
#include <memory>
#include <future>
#include <algorithm>

namespace agenkit {
namespace test {

using namespace agenkit::core;

/**
 * @brief Mock agent for testing
 *
 * Provides configurable responses for testing agent interactions.
 * Cycles through provided responses on each process() call.
 *
 * @example
 * @code
 * auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
 *     "Response 1",
 *     "Response 2"
 * });
 *
 * auto message = Message::with_text("user", "test");
 * auto result = mock->process(std::move(message)).get();
 * // First call returns "Response 1"
 * // Second call returns "Response 2"
 * // Third call returns "Response 1" (cycles)
 * @endcode
 */
class MockAgent : public Agent {
public:
    /**
     * @brief Construct a mock agent with predefined responses
     * @param responses List of responses to cycle through
     * @param agent_name Optional name for the agent (default: "mock_agent")
     */
    explicit MockAgent(
        const std::vector<std::string>& responses,
        std::string agent_name = "mock_agent"
    )
        : responses_(responses),
          call_count_(0),
          agent_name_(std::move(agent_name)) {
        if (responses_.empty()) {
            responses_.push_back("default_response");
        }
    }

    std::string name() const override {
        return agent_name_;
    }

    std::vector<std::string> capabilities() const override {
        return {"mock", "testing"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() {
            // Get response (cycle through responses)
            size_t idx = call_count_.fetch_add(1) % responses_.size();
            const std::string& response_text = responses_[idx];

            // Create response message
            auto response = Message::with_text("assistant", response_text);
            response.with_metadata("mock", nlohmann::json(true));

            return Result<Message, AgentError>::ok(std::move(response));
        });
    }

    /**
     * @brief Get the number of times process() has been called
     * @return Call count
     */
    size_t get_call_count() const {
        return call_count_.load();
    }

    /**
     * @brief Reset the call count to zero
     */
    void reset_call_count() {
        call_count_.store(0);
    }

    /**
     * @brief Get introspection information
     * @return JSON string describing the agent
     */
    std::string introspect() const override {
        std::stringstream ss;
        ss << "MockAgent(name=" << agent_name_
           << ", responses=" << responses_.size()
           << ", calls=" << call_count_.load() << ")";
        return ss.str();
    }

private:
    std::vector<std::string> responses_;
    std::atomic<size_t> call_count_;
    std::string agent_name_;
};

/**
 * @brief Mock agent that always fails with a specific error
 *
 * Useful for testing error handling paths.
 *
 * @example
 * @code
 * auto failing = std::make_shared<FailingMockAgent>(
 *     AgentErrorType::ProcessingError,
 *     "Simulated failure"
 * );
 *
 * auto message = Message::with_text("user", "test");
 * auto result = failing->process(std::move(message)).get();
 * EXPECT_TRUE(result.is_err());
 * @endcode
 */
class FailingMockAgent : public Agent {
public:
    /**
     * @brief Construct a failing mock agent
     * @param error_type Type of error to return
     * @param error_message Error message
     * @param agent_name Optional name for the agent (default: "failing_mock_agent")
     */
    FailingMockAgent(
        AgentErrorType error_type,
        std::string error_message,
        std::string agent_name = "failing_mock_agent"
    )
        : error_type_(error_type),
          error_message_(std::move(error_message)),
          agent_name_(std::move(agent_name)) {}

    std::string name() const override {
        return agent_name_;
    }

    std::vector<std::string> capabilities() const override {
        return {"failing", "testing"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() {
            return Result<Message, AgentError>::err(
                AgentError(error_type_, error_message_)
            );
        });
    }

    /**
     * @brief Get introspection information
     * @return JSON string describing the agent
     */
    std::string introspect() const override {
        std::stringstream ss;
        ss << "FailingMockAgent(name=" << agent_name_
           << ", error=" << to_string(error_type_)
           << ", message=" << error_message_ << ")";
        return ss.str();
    }

private:
    AgentErrorType error_type_;
    std::string error_message_;
    std::string agent_name_;
};

} // namespace test
} // namespace agenkit

#endif // AGENKIT_TESTS_TEST_UTILS_HPP
