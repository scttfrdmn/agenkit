/**
 * @file test_pattern_helpers.hpp
 * @brief Test helper utilities for pattern testing
 *
 * Provides mock agents and utilities for comprehensive pattern testing.
 * These helpers enable testing of complex scenarios including error handling,
 * concurrent execution, metadata tracking, and custom behaviors.
 */

#ifndef AGENKIT_TESTS_PATTERN_HELPERS_HPP
#define AGENKIT_TESTS_PATTERN_HELPERS_HPP

#include <gtest/gtest.h>
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <string>
#include <vector>
#include <functional>
#include <memory>
#include <thread>
#include <chrono>
#include <atomic>

namespace agenkit {
namespace test {

/**
 * @brief Process function type for custom behavior in mock agents
 */
using ProcessFunc = std::function<core::Result<core::Message, core::AgentError>(const core::Message&)>;

/**
 * @brief Extended mock agent with flexible behavior
 *
 * Provides comprehensive mocking capabilities for pattern tests including:
 * - Custom responses with optional errors
 * - Custom process functions for complex scenarios
 * - Capability specification
 * - Execution delay simulation
 * - Call counting for concurrency tests
 */
class MockAgent : public core::Agent {
private:
    std::string name_;
    std::string response_;
    std::vector<std::string> capabilities_;
    bool should_fail_;
    core::AgentError error_;
    ProcessFunc process_func_;
    std::chrono::milliseconds delay_;
    mutable std::atomic<int> call_count_{0};

public:
    /**
     * @brief Construct a basic mock agent
     * @param name Agent name
     * @param response Default response text
     * @param should_fail Whether to return error
     */
    MockAgent(
        const std::string& name,
        const std::string& response = "response",
        bool should_fail = false
    )
        : name_(name)
        , response_(response)
        , capabilities_({name})
        , should_fail_(should_fail)
        , error_(core::AgentErrorType::Internal, "mock failure")
        , process_func_(nullptr)
        , delay_(std::chrono::milliseconds(0))
    {}

    /**
     * @brief Construct mock agent with custom error
     * @param name Agent name
     * @param error Error to return
     */
    MockAgent(const std::string& name, const core::AgentError& error)
        : name_(name)
        , response_("")
        , capabilities_({name})
        , should_fail_(true)
        , error_(error)
        , process_func_(nullptr)
        , delay_(std::chrono::milliseconds(0))
    {}

    /**
     * @brief Construct mock agent with custom process function
     * @param name Agent name
     * @param func Custom process function
     */
    MockAgent(const std::string& name, ProcessFunc func)
        : name_(name)
        , response_("")
        , capabilities_({name})
        , should_fail_(false)
        , error_(core::AgentErrorType::Internal, "")
        , process_func_(std::move(func))
        , delay_(std::chrono::milliseconds(0))
    {}

    std::string name() const override {
        return name_;
    }

    std::vector<std::string> capabilities() const override {
        return capabilities_;
    }

    /**
     * @brief Set custom capabilities
     * @param caps Capability list
     */
    void set_capabilities(const std::vector<std::string>& caps) {
        capabilities_ = caps;
    }

    /**
     * @brief Set execution delay for concurrency testing
     * @param delay Delay duration
     */
    void set_delay(std::chrono::milliseconds delay) {
        delay_ = delay;
    }

    /**
     * @brief Get call count for concurrency testing
     * @return Number of times process was called
     */
    int call_count() const {
        return call_count_.load();
    }

    /**
     * @brief Reset call count
     */
    void reset_call_count() {
        call_count_.store(0);
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        call_count_.fetch_add(1);

        // Simulate delay if configured
        if (delay_.count() > 0) {
            std::this_thread::sleep_for(delay_);
        }

        // Use custom process function if provided
        if (process_func_) {
            auto result = process_func_(message);
            return core::make_ready_future(std::move(result));
        }

        // Return error if configured
        if (should_fail_) {
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(error_)
            );
        }

        // Return success response
        auto response_msg = core::Message::with_text("assistant", response_);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(response_msg)
        );
    }
};

/**
 * @brief Mock agent that appends to message content (for pipeline testing)
 */
class AppendingMockAgent : public core::Agent {
private:
    std::string name_;
    std::string suffix_;

public:
    AppendingMockAgent(const std::string& name, const std::string& suffix)
        : name_(name), suffix_(suffix) {}

    std::string name() const override { return name_; }

    std::vector<std::string> capabilities() const override {
        return {name_};
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        auto content = message.content_as_str() + suffix_;
        auto response = core::Message::with_text("assistant", content);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(response)
        );
    }
};

/**
 * @brief Mock agent that adds metadata (for metadata testing)
 */
class MetadataMockAgent : public core::Agent {
private:
    std::string name_;
    std::string response_;
    nlohmann::json metadata_;

public:
    MetadataMockAgent(
        const std::string& name,
        const std::string& response,
        const nlohmann::json& metadata
    )
        : name_(name), response_(response), metadata_(metadata) {}

    std::string name() const override { return name_; }

    std::vector<std::string> capabilities() const override {
        return {name_};
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        auto response_msg = core::Message::with_text("assistant", response_);
        // Add metadata entries individually
        for (auto it = metadata_.begin(); it != metadata_.end(); ++it) {
            response_msg.with_metadata(it.key(), it.value());
        }
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(response_msg)
        );
    }
};

/**
 * @brief Mock agent that tracks concurrent execution
 *
 * Increments counter when starting and decrements when finishing.
 * The max_concurrent counter tracks the highest concurrency level reached.
 */
class ConcurrencyTrackingAgent : public core::Agent {
private:
    std::string name_;
    std::string response_;
    std::chrono::milliseconds delay_;
    std::atomic<int>* active_counter_;
    std::atomic<int>* max_counter_;

public:
    ConcurrencyTrackingAgent(
        const std::string& name,
        const std::string& response,
        std::chrono::milliseconds delay,
        std::atomic<int>* active_counter,
        std::atomic<int>* max_counter
    )
        : name_(name)
        , response_(response)
        , delay_(delay)
        , active_counter_(active_counter)
        , max_counter_(max_counter)
    {}

    std::string name() const override { return name_; }

    std::vector<std::string> capabilities() const override {
        return {name_};
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        // Launch async work to enable true concurrent execution
        return std::async(std::launch::async, [this]() {
            // Increment active counter
            if (active_counter_) {
                int current = active_counter_->fetch_add(1) + 1;

                // Update max if higher
                int max = max_counter_->load();
                while (current > max && !max_counter_->compare_exchange_weak(max, current)) {
                    max = max_counter_->load();
                }
            }

            // Simulate work
            std::this_thread::sleep_for(delay_);

            // Decrement active counter
            if (active_counter_) {
                active_counter_->fetch_sub(1);
            }

            auto response_msg = core::Message::with_text("assistant", response_);
            return core::Result<core::Message, core::AgentError>::ok(response_msg);
        });
    }
};

/**
 * @brief Helper to create a simple mock agent
 */
inline std::shared_ptr<MockAgent> make_mock_agent(
    const std::string& name,
    const std::string& response = "response"
) {
    return std::make_shared<MockAgent>(name, response);
}

/**
 * @brief Helper to create a failing mock agent
 */
inline std::shared_ptr<MockAgent> make_failing_mock_agent(
    const std::string& name,
    const std::string& error_message = "mock failure"
) {
    return std::make_shared<MockAgent>(
        name,
        core::AgentError(core::AgentErrorType::Internal, error_message)
    );
}

/**
 * @brief Helper to create an appending mock agent
 */
inline std::shared_ptr<AppendingMockAgent> make_appending_mock_agent(
    const std::string& name,
    const std::string& suffix
) {
    return std::make_shared<AppendingMockAgent>(name, suffix);
}

/**
 * @brief Helper to create a metadata mock agent
 */
inline std::shared_ptr<MetadataMockAgent> make_metadata_mock_agent(
    const std::string& name,
    const std::string& response,
    const nlohmann::json& metadata
) {
    return std::make_shared<MetadataMockAgent>(name, response, metadata);
}

/**
 * @brief Helper to verify message content
 */
inline void expect_message_content(
    const core::Message& message,
    const std::string& expected_content
) {
    EXPECT_EQ(message.content_as_str(), expected_content);
}

/**
 * @brief Helper to verify metadata field exists
 */
inline void expect_metadata_exists(
    const core::Message& message,
    const std::string& key
) {
    auto metadata = message.metadata();
    EXPECT_TRUE(metadata.contains(key)) << "Metadata missing key: " << key;
}

/**
 * @brief Helper to verify metadata field value
 */
template<typename T>
inline void expect_metadata_value(
    const core::Message& message,
    const std::string& key,
    const T& expected_value
) {
    auto metadata = message.metadata();
    ASSERT_TRUE(metadata.contains(key)) << "Metadata missing key: " << key;
    EXPECT_EQ(metadata[key].get<T>(), expected_value);
}

} // namespace test
} // namespace agenkit

#endif // AGENKIT_TESTS_PATTERN_HELPERS_HPP
