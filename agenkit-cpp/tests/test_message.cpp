/**
 * @file test_message.cpp
 * @brief Tests for Message class
 */

#include <gtest/gtest.h>
#include "agenkit/core/message.hpp"

using namespace agenkit::core;

TEST(MessageTest, CreateTextMessage) {
    auto msg = Message::with_text("user", "Hello, agent!");

    EXPECT_EQ(msg.role(), "user");
    EXPECT_EQ(msg.content_as_str(), "Hello, agent!");
}

TEST(MessageTest, CreateWithJsonContent) {
    nlohmann::json content = {
        {"type", "query"},
        {"value", "test"}
    };

    Message msg("assistant", content);

    EXPECT_EQ(msg.role(), "assistant");
    EXPECT_EQ(msg.content()["type"], "query");
    EXPECT_EQ(msg.content()["value"], "test");
}

TEST(MessageTest, AddMetadata) {
    auto msg = Message::with_text("user", "Test");

    msg.with_metadata("session_id", "abc123")
       .with_metadata("user_id", 42);

    EXPECT_EQ(msg.metadata()["session_id"], "abc123");
    EXPECT_EQ(msg.metadata()["user_id"], 42);
}

TEST(MessageTest, JsonSerialization) {
    auto msg = Message::with_text("user", "Test message");
    msg.with_metadata("key", "value");

    auto json = msg.to_json();

    EXPECT_EQ(json["role"], "user");
    EXPECT_EQ(json["content"], "Test message");
    EXPECT_EQ(json["metadata"]["key"], "value");
    EXPECT_TRUE(json.contains("timestamp"));
}

TEST(MessageTest, JsonDeserialization) {
    nlohmann::json j = {
        {"role", "assistant"},
        {"content", "Response"},
        {"metadata", {{"key", "value"}}},
        {"timestamp", "2025-11-26T12:00:00Z"}
    };

    auto msg = Message::from_json(j);

    EXPECT_EQ(msg.role(), "assistant");
    EXPECT_EQ(msg.content_as_str(), "Response");
    EXPECT_EQ(msg.metadata()["key"], "value");
}

TEST(MessageTest, EmptyRoleThrows) {
    EXPECT_THROW(
        Message("", nlohmann::json("content")),
        std::invalid_argument
    );
}

TEST(MessageTest, InvalidJsonThrows) {
    nlohmann::json invalid = {
        {"content", "test"}
        // Missing "role"
    };

    EXPECT_THROW(
        Message::from_json(invalid),
        std::invalid_argument
    );
}

TEST(ToolResultTest, CreateToolResult) {
    nlohmann::json result = {{"output", "success"}};
    ToolResult tr("tool-123", result, false);

    EXPECT_EQ(tr.tool_use_id(), "tool-123");
    EXPECT_EQ(tr.result()["output"], "success");
    EXPECT_FALSE(tr.is_error());
}

TEST(ToolResultTest, CreateErrorResult) {
    nlohmann::json error = {{"error", "failed"}};
    ToolResult tr("tool-456", error, true);

    EXPECT_EQ(tr.tool_use_id(), "tool-456");
    EXPECT_TRUE(tr.is_error());
}

TEST(ToolResultTest, JsonSerialization) {
    nlohmann::json result = {{"data", 42}};
    ToolResult tr("tool-789", result, false);

    auto json = tr.to_json();

    EXPECT_EQ(json["tool_use_id"], "tool-789");
    EXPECT_EQ(json["result"]["data"], 42);
    EXPECT_EQ(json["is_error"], false);
}

TEST(ToolResultTest, JsonDeserialization) {
    nlohmann::json j = {
        {"tool_use_id", "tool-999"},
        {"result", {{"value", "test"}}},
        {"is_error", true}
    };

    auto tr = ToolResult::from_json(j);

    EXPECT_EQ(tr.tool_use_id(), "tool-999");
    EXPECT_EQ(tr.result()["value"], "test");
    EXPECT_TRUE(tr.is_error());
}

// Message validation tests

TEST(MessageValidationTest, ValidateValidMessage) {
    auto msg = Message::with_text("user", "Hello");
    EXPECT_NO_THROW(msg.validate());
}

TEST(MessageValidationTest, ValidateRoleTooLong) {
    std::string long_role(21, 'a');
    auto msg = Message::with_text(long_role, "Hello");
    EXPECT_THROW(msg.validate(), MessageValidationError);
}

TEST(MessageValidationTest, ValidateInvalidRole) {
    auto msg = Message::with_text("invalid_role", "Hello");
    EXPECT_THROW(msg.validate(), MessageValidationError);
}

TEST(MessageValidationTest, ValidateAllValidRoles) {
    std::vector<std::string> valid_roles = {"user", "assistant", "system", "tool", "agent"};
    for (const auto& role : valid_roles) {
        auto msg = Message::with_text(role, "Hello");
        EXPECT_NO_THROW(msg.validate());
    }
}

TEST(MessageValidationTest, ValidateContentTooLarge) {
    // Create a large string (>16MB)
    std::string large_content(17 * 1024 * 1024, 'a');
    auto msg = Message::with_text("user", large_content);
    EXPECT_THROW(msg.validate(), MessageValidationError);
}

TEST(MessageValidationTest, ValidateContentUnderLimit) {
    // Create a 1MB string
    std::string content(1024 * 1024, 'a');
    auto msg = Message::with_text("user", content);
    EXPECT_NO_THROW(msg.validate());
}

TEST(MessageValidationTest, ValidateTooManyMetadataKeys) {
    auto msg = Message::with_text("user", "Hello");
    for (int i = 0; i < 101; i++) {
        msg.with_metadata("key" + std::to_string(i), "value");
    }
    EXPECT_THROW(msg.validate(), MessageValidationError);
}

TEST(MessageValidationTest, Validate100MetadataKeys) {
    auto msg = Message::with_text("user", "Hello");
    for (int i = 0; i < 100; i++) {
        msg.with_metadata("key" + std::to_string(i), "value");
    }
    EXPECT_NO_THROW(msg.validate());
}

TEST(MessageValidationTest, ValidateMetadataKeyTooLong) {
    std::string long_key(51, 'a');
    auto msg = Message::with_text("user", "Hello");
    msg.with_metadata(long_key, "value");
    EXPECT_THROW(msg.validate(), MessageValidationError);
}

TEST(MessageValidationTest, ValidateMetadataKey50Chars) {
    std::string key(50, 'a');
    auto msg = Message::with_text("user", "Hello");
    msg.with_metadata(key, "value");
    EXPECT_NO_THROW(msg.validate());
}

TEST(MessageValidationTest, ValidateMetadataValueTooLarge) {
    std::string large_value(17 * 1024 * 1024, 'a');
    auto msg = Message::with_text("user", "Hello");
    msg.with_metadata("key", large_value);
    EXPECT_THROW(msg.validate(), MessageValidationError);
}

TEST(MessageValidationTest, ValidateMetadataValueUnderLimit) {
    std::string value(1024 * 1024, 'a');
    auto msg = Message::with_text("user", "Hello");
    msg.with_metadata("key", value);
    EXPECT_NO_THROW(msg.validate());
}

TEST(MessageValidationTest, ValidateStructuredMetadataValue) {
    // Create a large array that exceeds 16MB when serialized
    nlohmann::json large_array = nlohmann::json::array();
    for (int i = 0; i < 1000000; i++) {
        large_array.push_back({{"key", std::string(20, 'a')}});
    }
    auto msg = Message::with_text("user", "Hello");
    msg.with_metadata("data", large_array);
    EXPECT_THROW(msg.validate(), MessageValidationError);
}
