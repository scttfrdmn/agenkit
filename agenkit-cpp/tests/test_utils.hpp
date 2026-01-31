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
    std::string introspect() const {
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
    std::string introspect() const {
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

/**
 * @brief Mock LLM agent for testing
 *
 * Provides a mock LLM implementation with configurable responses,
 * delays, and failure modes. Useful for testing without external API calls.
 *
 * @example
 * @code
 * auto mock_llm = std::make_shared<MockLLM>(std::vector<std::string>{
 *     "Response 1",
 *     "Response 2"
 * });
 * mock_llm->set_temperature(0.7);
 * mock_llm->set_max_tokens(100);
 *
 * auto message = Message::with_text("user", "test");
 * auto result = mock_llm->process(std::move(message)).get();
 * @endcode
 */
class MockLLM : public Agent {
public:
    /**
     * @brief Construct a mock LLM with predefined responses
     * @param responses List of responses to cycle through
     * @param model_name Optional model name (default: "mock-llm")
     */
    explicit MockLLM(
        const std::vector<std::string>& responses,
        std::string model_name = "mock-llm"
    )
        : responses_(responses),
          call_count_(0),
          model_name_(std::move(model_name)),
          temperature_(1.0),
          max_tokens_(std::nullopt),
          top_p_(std::nullopt),
          delay_ms_(0),
          should_fail_(false) {
        if (responses_.empty()) {
            responses_.push_back("Mock LLM response");
        }
    }

    /**
     * @brief Construct a mock LLM with a single response
     * @param response Single response to return
     * @param model_name Optional model name (default: "mock-llm")
     */
    explicit MockLLM(
        std::string response = "Mock LLM response",
        std::string model_name = "mock-llm"
    )
        : MockLLM(std::vector<std::string>{std::move(response)}, std::move(model_name)) {}

    std::string name() const override {
        return model_name_;
    }

    std::vector<std::string> capabilities() const override {
        return {"text-generation", "chat", "mock", "testing"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() {
            // Simulate network delay if configured
            if (delay_ms_ > 0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(delay_ms_));
            }

            // Simulate failure if configured
            if (should_fail_) {
                return Result<Message, AgentError>::err(
                    AgentError(AgentErrorType::ProcessingError, failure_message_)
                );
            }

            // Get response (cycle through responses)
            size_t idx = call_count_.fetch_add(1) % responses_.size();
            const std::string& response_text = responses_[idx];

            // Create response message
            auto response = Message::with_text("assistant", response_text);

            // Add LLM metadata
            nlohmann::json metadata;
            metadata["model"] = model_name_;
            metadata["temperature"] = temperature_;
            if (max_tokens_.has_value()) {
                metadata["max_tokens"] = max_tokens_.value();
            }
            if (top_p_.has_value()) {
                metadata["top_p"] = top_p_.value();
            }
            metadata["mock"] = true;
            response.with_metadata("llm", metadata);

            return Result<Message, AgentError>::ok(std::move(response));
        });
    }

    // LLM-specific configuration methods

    /**
     * @brief Set temperature for sampling (0.0 - 2.0)
     * @param temp Temperature value
     */
    void set_temperature(double temp) {
        temperature_ = temp;
    }

    /**
     * @brief Get current temperature setting
     * @return Temperature value
     */
    double get_temperature() const {
        return temperature_;
    }

    /**
     * @brief Set maximum tokens to generate
     * @param tokens Maximum tokens
     */
    void set_max_tokens(int tokens) {
        max_tokens_ = tokens;
    }

    /**
     * @brief Get maximum tokens setting
     * @return Maximum tokens (if set)
     */
    std::optional<int> get_max_tokens() const {
        return max_tokens_;
    }

    /**
     * @brief Set top-p sampling parameter (0.0 - 1.0)
     * @param p Top-p value
     */
    void set_top_p(double p) {
        top_p_ = p;
    }

    /**
     * @brief Get top-p setting
     * @return Top-p value (if set)
     */
    std::optional<double> get_top_p() const {
        return top_p_;
    }

    /**
     * @brief Set delay to simulate network latency
     * @param ms Delay in milliseconds
     */
    void set_delay(int ms) {
        delay_ms_ = ms;
    }

    /**
     * @brief Configure mock to fail on next call(s)
     * @param should_fail Whether to fail
     * @param message Error message to return
     */
    void set_failure_mode(bool should_fail, std::string message = "Mock LLM failure") {
        should_fail_ = should_fail;
        failure_message_ = std::move(message);
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
     * @return JSON string describing the mock LLM
     */
    std::string introspect() const {
        std::stringstream ss;
        ss << "MockLLM(model=" << model_name_
           << ", responses=" << responses_.size()
           << ", calls=" << call_count_.load()
           << ", temperature=" << temperature_;
        if (max_tokens_.has_value()) {
            ss << ", max_tokens=" << max_tokens_.value();
        }
        if (top_p_.has_value()) {
            ss << ", top_p=" << top_p_.value();
        }
        ss << ")";
        return ss.str();
    }

private:
    std::vector<std::string> responses_;
    std::atomic<size_t> call_count_;
    std::string model_name_;

    // LLM parameters
    double temperature_;
    std::optional<int> max_tokens_;
    std::optional<double> top_p_;

    // Testing configuration
    int delay_ms_;
    bool should_fail_;
    std::string failure_message_;
};

} // namespace test
} // namespace agenkit

#endif // AGENKIT_TESTS_TEST_UTILS_HPP
