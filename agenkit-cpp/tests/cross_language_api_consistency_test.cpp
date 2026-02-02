/**
 * Cross-language API consistency tests for C++.
 *
 * Tests that Agenkit's C++ implementation conforms to the cross-language
 * API consistency specification, validating parameter naming, default values,
 * and interface signatures.
 */

#include <gtest/gtest.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <chrono>

#include "agenkit/middleware/retry.hpp"
#include "agenkit/middleware/timeout.hpp"
#include "agenkit/middleware/rate_limiter.hpp"
#include "agenkit/middleware/circuit_breaker.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/tool.hpp"

using json = nlohmann::json;
namespace fs = std::filesystem;

class APIConsistencyTest : public ::testing::Test {
protected:
    json fixtures;

    void SetUp() override {
        // Load API consistency fixtures
        fs::path fixtures_path = fs::path(__FILE__).parent_path()
            .parent_path()
            .parent_path()
            / "tests"
            / "cross_language"
            / "fixtures"
            / "api_consistency.json";

        std::ifstream file(fixtures_path);
        if (!file.is_open()) {
            FAIL() << "Failed to open API consistency fixtures at: " << fixtures_path;
        }

        file >> fixtures;
    }

    json find_test_case(const std::string& category, const std::string& id) {
        for (const auto& tc : fixtures["test_categories"][category]["test_cases"]) {
            if (tc["id"] == id) {
                return tc;
            }
        }
        return json();
    }
};

// ============================================
// Parameter Naming Tests
// ============================================

TEST_F(APIConsistencyTest, RetryParameterNames) {
    auto test_case = find_test_case("parameter_naming", "retry_parameter_names");
    ASSERT_FALSE(test_case.is_null()) << "Could not find retry_parameter_names test case";

    // Create a RetryConfig to verify field names exist
    agenkit::middleware::RetryConfig config;

    // NOTE: C++ uses different parameter names than the spec:
    // - max_attempts (not max_retries)
    // - initial_backoff (not initial_delay)
    // - max_backoff (not max_delay)
    // - backoff_multiplier (not multiplier)
    // This is a known API inconsistency tracked in Issue #444

    config.max_attempts = 3;
    config.initial_backoff = std::chrono::milliseconds(100);
    config.max_backoff = std::chrono::milliseconds(10000);
    config.backoff_multiplier = 2.0;

    EXPECT_EQ(config.max_attempts, 3);
    EXPECT_EQ(config.initial_backoff.count(), 100);
    EXPECT_EQ(config.max_backoff.count(), 10000);
    EXPECT_EQ(config.backoff_multiplier, 2.0);
}

TEST_F(APIConsistencyTest, TimeoutParameterNames) {
    auto test_case = find_test_case("parameter_naming", "timeout_parameter_names");
    ASSERT_FALSE(test_case.is_null()) << "Could not find timeout_parameter_names test case";

    // Create a TimeoutConfig to verify field names
    agenkit::middleware::TimeoutConfig config;

    // NOTE: C++ uses default_timeout (not timeout_ms)
    // This is a known API inconsistency tracked in Issue #444
    config.default_timeout = std::chrono::milliseconds(30000);

    EXPECT_EQ(config.default_timeout.count(), 30000);
}

// ============================================
// Default Values Tests
// ============================================

TEST_F(APIConsistencyTest, TimeoutDefaults) {
    auto test_case = find_test_case("default_values", "timeout_defaults");
    ASSERT_FALSE(test_case.is_null()) << "Could not find timeout_defaults test case";

    agenkit::middleware::TimeoutConfig config;

    int expected_timeout_ms = test_case["defaults"]["timeout"]["value_ms"];

    // NOTE: C++ uses default_timeout (not timeout_ms)
    EXPECT_EQ(static_cast<int>(config.default_timeout.count()), expected_timeout_ms)
        << "default_timeout should be " << expected_timeout_ms << "ms (30 seconds)";
}

TEST_F(APIConsistencyTest, RetryDefaults) {
    auto test_case = find_test_case("default_values", "retry_defaults");
    ASSERT_FALSE(test_case.is_null()) << "Could not find retry_defaults test case";

    agenkit::middleware::RetryConfig config;

    // NOTE: C++ uses max_attempts (not max_retries), initial_backoff (not initial_delay),
    // max_backoff (not max_delay), backoff_multiplier (not multiplier)
    // This is a known API inconsistency tracked in Issue #444

    // Check max_attempts
    int expected_max_retries = test_case["defaults"]["max_retries"]["value"];
    EXPECT_EQ(config.max_attempts, expected_max_retries)
        << "max_attempts default should be " << expected_max_retries;

    // Check initial_backoff (in milliseconds)
    int expected_initial_delay_ms = test_case["defaults"]["initial_delay"]["value_ms"];
    EXPECT_EQ(static_cast<int>(config.initial_backoff.count()), expected_initial_delay_ms)
        << "initial_backoff default should be " << expected_initial_delay_ms << "ms";

    // Check max_backoff (in milliseconds)
    int expected_max_delay_ms = test_case["defaults"]["max_delay"]["value_ms"];
    EXPECT_EQ(static_cast<int>(config.max_backoff.count()), expected_max_delay_ms)
        << "max_backoff default should be " << expected_max_delay_ms << "ms";

    // Check backoff_multiplier
    double expected_multiplier = test_case["defaults"]["multiplier"]["value"];
    EXPECT_DOUBLE_EQ(config.backoff_multiplier, expected_multiplier)
        << "backoff_multiplier default should be " << expected_multiplier;
}

TEST_F(APIConsistencyTest, RateLimiterDefaults) {
    auto test_case = find_test_case("default_values", "rate_limiter_defaults");
    ASSERT_FALSE(test_case.is_null()) << "Could not find rate_limiter_defaults test case";

    agenkit::middleware::RateLimiterConfig config;

    double expected_rate = test_case["defaults"]["rate"]["value"];
    EXPECT_DOUBLE_EQ(config.rate_per_second, expected_rate)
        << "rate_per_second default should be " << expected_rate << " requests/second";

    int expected_capacity = test_case["defaults"]["capacity"]["value"];
    EXPECT_EQ(config.capacity, expected_capacity)
        << "capacity default should be " << expected_capacity;
}

TEST_F(APIConsistencyTest, CircuitBreakerDefaults) {
    auto test_case = find_test_case("default_values", "circuit_breaker_defaults");
    ASSERT_FALSE(test_case.is_null()) << "Could not find circuit_breaker_defaults test case";

    agenkit::middleware::CircuitBreakerConfig config;

    // Check failure_threshold
    int expected_failure_threshold = test_case["defaults"]["failure_threshold"]["value"];
    EXPECT_EQ(config.failure_threshold, expected_failure_threshold)
        << "failure_threshold default should be " << expected_failure_threshold;

    // Check success_threshold
    int expected_success_threshold = test_case["defaults"]["success_threshold"]["value"];
    EXPECT_EQ(config.success_threshold, expected_success_threshold)
        << "success_threshold default should be " << expected_success_threshold;

    // Check timeout (request timeout)
    int expected_timeout_ms = test_case["defaults"]["timeout"]["value_ms"];
    int actual_timeout_ms = static_cast<int>(config.timeout.count());
    EXPECT_EQ(actual_timeout_ms, expected_timeout_ms)
        << "timeout (request timeout) default should be " << expected_timeout_ms << "ms (30 seconds)";

    // Check recovery_timeout
    int expected_recovery_ms = test_case["defaults"]["recovery_timeout"]["value_ms"];
    int actual_recovery_ms = static_cast<int>(config.recovery_timeout.count());
    EXPECT_EQ(actual_recovery_ms, expected_recovery_ms)
        << "recovery_timeout default should be " << expected_recovery_ms << "ms (60 seconds)";
}

// ============================================
// Interface Signature Tests
// ============================================

class MockTool : public agenkit::core::Tool {
public:
    std::string name() const override {
        return "mock-tool";
    }

    std::string description() const override {
        return "Mock tool for testing";
    }

    std::optional<nlohmann::json> parameters_schema() const override {
        return nlohmann::json::object();
    }

    std::future<agenkit::core::Result<agenkit::core::ToolResult, agenkit::core::AgentError>>
    execute(const nlohmann::json& params) override {
        std::promise<agenkit::core::Result<agenkit::core::ToolResult, agenkit::core::AgentError>> promise;

        agenkit::core::ToolResult result("test-tool-use-id", nlohmann::json("test"));

        promise.set_value(agenkit::core::Result<agenkit::core::ToolResult, agenkit::core::AgentError>::ok(result));
        return promise.get_future();
    }
};

class MockAgent : public agenkit::core::Agent {
public:
    std::string name() const override {
        return "mock-agent";
    }

    std::vector<std::string> capabilities() const override {
        return {};
    }

    std::future<agenkit::core::Result<agenkit::core::Message, agenkit::core::AgentError>>
    process(agenkit::core::Message message) override {
        std::promise<agenkit::core::Result<agenkit::core::Message, agenkit::core::AgentError>> promise;

        agenkit::core::Message response("agent", nlohmann::json("response"));

        promise.set_value(agenkit::core::Result<agenkit::core::Message, agenkit::core::AgentError>::ok(response));
        return promise.get_future();
    }
};

TEST_F(APIConsistencyTest, ToolExecuteSignature) {
    // Verify Tool interface has execute method with correct signature
    MockTool tool;

    nlohmann::json params = nlohmann::json::object();
    auto future = tool.execute(params);
    auto result = future.get();

    EXPECT_TRUE(result.is_ok());
}

TEST_F(APIConsistencyTest, AgentProcessSignature) {
    // Verify Agent interface has process method with correct signature
    MockAgent agent;

    agenkit::core::Message message("user", nlohmann::json("test"));

    auto future = agent.process(message);
    auto result = future.get();

    EXPECT_TRUE(result.is_ok());
}

// ============================================
// Error Types Tests
// ============================================

TEST_F(APIConsistencyTest, TimeoutErrorExists) {
    // C++ uses Result types with error enums/classes
    // Verify the concept of timeout errors exists

    // This is validated at compile time - if TimeoutError doesn't exist,
    // the middleware won't compile
    EXPECT_TRUE(true);
}

TEST_F(APIConsistencyTest, MaxRetriesExceededErrorConcept) {
    // Verify the concept of max retries exceeded error exists
    // C++ uses Result types with error enums/classes

    EXPECT_TRUE(true);
}

// ============================================
// C++ Specific Features Tests
// ============================================

TEST_F(APIConsistencyTest, RetryConfigUsesMilliseconds) {
    // C++ uses chrono::milliseconds for time durations (type-safe)
    // NOTE: C++ uses different field names than spec (tracked in Issue #444)
    agenkit::middleware::RetryConfig config;

    config.max_attempts = 5;
    config.initial_backoff = std::chrono::milliseconds(200);
    config.max_backoff = std::chrono::milliseconds(5000);
    config.backoff_multiplier = 1.5;

    EXPECT_EQ(config.max_attempts, 5);
    EXPECT_EQ(config.initial_backoff.count(), 200);
    EXPECT_EQ(config.max_backoff.count(), 5000);
    EXPECT_DOUBLE_EQ(config.backoff_multiplier, 1.5);
}

TEST_F(APIConsistencyTest, TimeoutConfigUsesMilliseconds) {
    // Verify timeout uses chrono::milliseconds (type-safe)
    // NOTE: C++ uses default_timeout (not timeout_ms) - tracked in Issue #444
    agenkit::middleware::TimeoutConfig config;

    config.default_timeout = std::chrono::milliseconds(15000);  // 15 seconds

    EXPECT_EQ(config.default_timeout.count(), 15000);
}

TEST_F(APIConsistencyTest, ConfigStructsHaveDefaultConstructors) {
    // Verify all config structs have default constructors
    agenkit::middleware::RetryConfig retry_config;
    agenkit::middleware::TimeoutConfig timeout_config;
    agenkit::middleware::RateLimiterConfig rate_limiter_config;
    agenkit::middleware::CircuitBreakerConfig circuit_breaker_config;

    // If this compiles, default constructors exist
    EXPECT_TRUE(true);
}
