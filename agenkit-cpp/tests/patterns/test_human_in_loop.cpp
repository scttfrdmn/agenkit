/**
 * @file test_human_in_loop.cpp
 * @brief Comprehensive tests for Human-in-Loop pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/human_in_loop.hpp"
#include "test_pattern_helpers.hpp"
#include <memory>
#include <string>
#include <stdexcept>

using namespace agenkit;
using namespace agenkit::test;

// Test: Valid construction
TEST(HumanInLoopAgentTest, Constructor) {
    auto agent = make_mock_agent("agent", "response");

    auto approval_func = patterns::simple_approval_func(true);

    patterns::HumanInLoopConfig config{
        agent,
        0.8,
        approval_func,
        "confidence"
    };

    patterns::HumanInLoopAgent hil(config);

    EXPECT_EQ(hil.name(), "human_in_loop");
}

// Test: Constructor with null agent
TEST(HumanInLoopAgentTest, ConstructorNullAgent) {
    auto approval_func = patterns::simple_approval_func(true);

    patterns::HumanInLoopConfig config{
        nullptr,
        0.8,
        approval_func,
        "confidence"
    };

    EXPECT_THROW(
        {
            patterns::HumanInLoopAgent hil(config);
        },
        std::invalid_argument
    );
}

// Test: Constructor with null approval function
TEST(HumanInLoopAgentTest, ConstructorNullApprovalFunc) {
    auto agent = make_mock_agent("agent");

    patterns::HumanInLoopConfig config{
        agent,
        0.8,
        nullptr,
        "confidence"
    };

    EXPECT_THROW(
        {
            patterns::HumanInLoopAgent hil(config);
        },
        std::invalid_argument
    );
}

// Test: High confidence - no approval needed
TEST(HumanInLoopAgentTest, HighConfidenceNoApproval) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "high confidence response");
            nlohmann::json metadata = {{"confidence", 0.95}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    bool approval_called = false;
    auto approval_func = [&approval_called](const patterns::ApprovalRequest& /* request */) {
        approval_called = true;
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(
            patterns::ApprovalResponse{true, ""}
        );
    };

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "high confidence response");

    // Approval should not have been called
    EXPECT_FALSE(approval_called);
}

// Test: Low confidence - approval required
TEST(HumanInLoopAgentTest, LowConfidenceApprovalRequired) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "low confidence response");
            nlohmann::json metadata = {{"confidence", 0.5}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    bool approval_called = false;
    auto approval_func = [&approval_called](const patterns::ApprovalRequest& /* request */) {
        approval_called = true;
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(
            patterns::ApprovalResponse{true, ""}
        );
    };

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "low confidence response");

    // Approval should have been called
    EXPECT_TRUE(approval_called);
}

// Test: Approval granted
TEST(HumanInLoopAgentTest, ApprovalGranted) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "response");
            nlohmann::json metadata = {{"confidence", 0.5}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    auto approval_func = patterns::simple_approval_func(true);

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "response");

    // Check approval metadata
    auto metadata = response.metadata();
    EXPECT_TRUE(metadata.contains("approval_required"));
    EXPECT_TRUE(metadata["approval_required"].get<bool>());
    EXPECT_TRUE(metadata.contains("approval_granted"));
    EXPECT_TRUE(metadata["approval_granted"].get<bool>());
}

// Test: Approval denied
TEST(HumanInLoopAgentTest, ApprovalDenied) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "response");
            nlohmann::json metadata = {{"confidence", 0.5}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    auto approval_func = patterns::simple_approval_func(false);

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("denied") != std::string::npos ||
                error.message().find("rejected") != std::string::npos);
}

// Test: Missing confidence metadata
TEST(HumanInLoopAgentTest, MissingConfidenceMetadata) {
    auto agent = make_mock_agent("agent", "response");

    auto approval_func = patterns::simple_approval_func(true);

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should default to low confidence (0.0) and require approval
    auto metadata = response.metadata();
    EXPECT_TRUE(metadata.contains("approval_required"));
}

// Test: Agent execution error
TEST(HumanInLoopAgentTest, AgentExecutionError) {
    auto agent = make_failing_mock_agent("agent", "agent failed");

    auto approval_func = patterns::simple_approval_func(true);

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("agent failed") != std::string::npos);
}

// Test: Approval function error
TEST(HumanInLoopAgentTest, ApprovalFunctionError) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "response");
            nlohmann::json metadata = {{"confidence", 0.5}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    auto approval_func = [](const patterns::ApprovalRequest& /* request */) {
        return core::Result<patterns::ApprovalResponse, core::AgentError>::err(
            core::AgentError(core::AgentErrorType::Internal, "approval system error")
        );
    };

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("approval system error") != std::string::npos);
}

// Test: Custom confidence key
TEST(HumanInLoopAgentTest, CustomConfidenceKey) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "response");
            nlohmann::json metadata = {{"custom_conf", 0.5}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    bool approval_called = false;
    auto approval_func = [&approval_called](const patterns::ApprovalRequest& /* request */) {
        approval_called = true;
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(
            patterns::ApprovalResponse{true, ""}
        );
    };

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "custom_conf"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_TRUE(approval_called);
}

// Test: Approval threshold boundary
TEST(HumanInLoopAgentTest, ApprovalThresholdBoundary) {
    // Test exact threshold value
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "response");
            nlohmann::json metadata = {{"confidence", 0.8}};  // Exactly at threshold
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    bool approval_called = false;
    auto approval_func = [&approval_called](const patterns::ApprovalRequest& /* request */) {
        approval_called = true;
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(
            patterns::ApprovalResponse{true, ""}
        );
    };

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());

    // At threshold - should NOT require approval (>= threshold means high confidence)
    EXPECT_FALSE(approval_called);
}

// Test: Approval with feedback
TEST(HumanInLoopAgentTest, ApprovalWithFeedback) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "response");
            nlohmann::json metadata = {{"confidence", 0.5}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    auto approval_func = [](const patterns::ApprovalRequest& /* request */) {
        patterns::ApprovalResponse resp{true, "Looks good!"};
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(resp);
    };

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_TRUE(metadata.contains("approval_feedback"));
    EXPECT_EQ(metadata["approval_feedback"].get<std::string>(), "Looks good!");
}

// Test: Capabilities aggregation
TEST(HumanInLoopAgentTest, Capabilities) {
    auto agent = make_mock_agent("agent");
    agent->set_capabilities({"cap1", "cap2"});

    auto approval_func = patterns::simple_approval_func(true);

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto caps = hil.capabilities();

    // Should have human_in_loop capability plus agent capabilities
    bool has_hil = false;
    for (const auto& cap : caps) {
        if (cap == "human_in_loop") {
            has_hil = true;
        }
    }

    EXPECT_TRUE(has_hil);
}

// Test: Modified message from approval
TEST(HumanInLoopAgentTest, ModifiedMessageFromApproval) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "original");
            nlohmann::json metadata = {{"confidence", 0.5}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    auto approval_func = [](const patterns::ApprovalRequest& /* request */) {
        patterns::ApprovalResponse resp{true, "Modified"};
        resp.modified_message = core::Message::with_text("assistant", "modified response");
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(resp);
    };

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should use modified message
    EXPECT_EQ(response.content_as_str(), "modified response");
}

// Test: Confidence-based approval function
TEST(HumanInLoopAgentTest, ConfidenceBasedApprovalFunc) {
    auto low_conf_agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "low");
            nlohmann::json metadata = {{"confidence", 0.3}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    // Auto-reject below 0.4, auto-approve above 0.9
    auto approval_func = patterns::confidence_based_approval_func(0.4, 0.9);

    patterns::HumanInLoopConfig config{low_conf_agent, 1.0, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    // Should be auto-rejected (confidence 0.3 < reject_below 0.4)
    ASSERT_TRUE(result.is_err());
}

// Test: Empty message handling
TEST(HumanInLoopAgentTest, EmptyMessage) {
    auto agent = make_mock_agent("agent", "response");

    auto approval_func = patterns::simple_approval_func(true);

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "");
    auto result = hil.process(std::move(msg)).get();

    // Should still process successfully
    ASSERT_TRUE(result.is_ok());
}

// Test: Approval request context
TEST(HumanInLoopAgentTest, ApprovalRequestContext) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "response");
            nlohmann::json metadata = {{"confidence", 0.5}, {"extra", "data"}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    double received_confidence = 0.0;
    auto approval_func = [&received_confidence](const patterns::ApprovalRequest& request) {
        received_confidence = request.confidence;
        // Context should include metadata
        EXPECT_TRUE(request.context.contains("extra"));
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(
            patterns::ApprovalResponse{true, ""}
        );
    };

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(received_confidence, 0.5);
}

// Test: Very low threshold
TEST(HumanInLoopAgentTest, VeryLowThreshold) {
    auto agent = std::make_shared<MockAgent>(
        "agent",
        [](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            auto response = core::Message::with_text("assistant", "response");
            nlohmann::json metadata = {{"confidence", 0.05}};
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            response.with_metadata(it.key(), it.value());
        }
            return core::Result<core::Message, core::AgentError>::ok(response);
        }
    );

    bool approval_called = false;
    auto approval_func = [&approval_called](const patterns::ApprovalRequest& /* request */) {
        approval_called = true;
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(
            patterns::ApprovalResponse{true, ""}
        );
    };

    patterns::HumanInLoopConfig config{agent, 0.1, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = hil.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_TRUE(approval_called);
}
