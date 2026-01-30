/**
 * @file test_cross_language_message_serialization.cpp
 * @brief Cross-language message serialization tests for C++
 *
 * Validates that Agenkit messages serialize/deserialize consistently
 * with the canonical JSON schema across all language implementations.
 */

#include <gtest/gtest.h>
#include <fstream>
#include <sstream>
#include <nlohmann/json.hpp>
#include "agenkit/core/message.hpp"

using json = nlohmann::json;
using namespace agenkit::core;

// Test fixture class
class CrossLanguageMessageTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Load fixtures
        std::ifstream fixtures_file("../../tests/cross_language/fixtures/messages.json");
        ASSERT_TRUE(fixtures_file.is_open()) << "Failed to open fixtures file";
        fixtures_file >> fixtures;

        // Load schema
        std::ifstream schema_file("../../tests/cross_language/schemas/message.schema.json");
        ASSERT_TRUE(schema_file.is_open()) << "Failed to open schema file";
        schema_file >> schema;
    }

    // Basic schema validation
    void validate_against_schema(const json& message_json) {
        // Check required fields
        ASSERT_TRUE(message_json.contains("role")) << "Message must have 'role' field";
        ASSERT_TRUE(message_json.contains("content")) << "Message must have 'content' field";

        // Validate role is valid enum value
        std::string role = message_json["role"].get<std::string>();
        std::vector<std::string> valid_roles = {"user", "assistant", "system", "tool", "agent"};
        bool valid_role = std::find(valid_roles.begin(), valid_roles.end(), role) != valid_roles.end();
        ASSERT_TRUE(valid_role) << "Invalid role: " << role;

        // Validate content is string or object
        bool valid_content = message_json["content"].is_string() || message_json["content"].is_object();
        ASSERT_TRUE(valid_content) << "Content must be string or object";

        // Validate metadata if present
        if (message_json.contains("metadata")) {
            ASSERT_TRUE(message_json["metadata"].is_object()) << "Metadata must be an object";
        }
    }

    json find_test_case(const std::string& id) {
        for (const auto& test_case : fixtures["test_cases"]) {
            if (test_case["id"] == id) {
                return test_case;
            }
        }
        ADD_FAILURE() << "Test case not found: " << id;
        return json::object();
    }

    json fixtures;
    json schema;
};

TEST_F(CrossLanguageMessageTest, FixturesLoad) {
    EXPECT_EQ(fixtures["version"], "1.0");
    EXPECT_GT(fixtures["test_cases"].size(), 0);
}

TEST_F(CrossLanguageMessageTest, SchemaValidatesFixtures) {
    for (const auto& test_case : fixtures["test_cases"]) {
        const auto& message = test_case["message"];
        SCOPED_TRACE("Test case: " + test_case["id"].get<std::string>());
        validate_against_schema(message);
    }
}

TEST_F(CrossLanguageMessageTest, SimpleUserMessage) {
    auto test_case = find_test_case("simple_user_message");
    auto msg_data = test_case["message"];

    // Create message from fixture
    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    // Validate properties
    EXPECT_EQ(msg.role(), "user");
    EXPECT_EQ(msg.content_as_str(), "Hello, agent!");

    // Serialize and validate
    auto serialized = msg.to_json();
    validate_against_schema(serialized);

    // Verify key properties match
    EXPECT_EQ(serialized["role"], msg_data["role"]);
    EXPECT_EQ(serialized["content"], msg_data["content"]);
}

TEST_F(CrossLanguageMessageTest, AssistantMessageWithMetadata) {
    auto test_case = find_test_case("assistant_message_with_metadata");
    auto msg_data = test_case["message"];

    // Create message with metadata
    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    // Add metadata
    for (auto& [key, value] : msg_data["metadata"].items()) {
        msg.with_metadata(key, value);
    }

    // Validate
    EXPECT_EQ(msg.role(), "assistant");
    EXPECT_EQ(msg.content_as_str(), "I can help you with that!");
    EXPECT_EQ(msg.metadata().size(), 3);
    EXPECT_TRUE(msg.metadata().contains("model"));
    EXPECT_TRUE(msg.metadata().contains("temperature"));
    EXPECT_TRUE(msg.metadata().contains("tokens"));

    // Serialize and validate
    auto serialized = msg.to_json();
    validate_against_schema(serialized);
}

TEST_F(CrossLanguageMessageTest, SystemMessage) {
    auto test_case = find_test_case("system_message");
    auto msg_data = test_case["message"];

    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    EXPECT_EQ(msg.role(), "system");
    std::string content_str = msg.content_as_str();
    EXPECT_NE(content_str.find("helpful assistant"), std::string::npos);

    auto serialized = msg.to_json();
    validate_against_schema(serialized);
}

TEST_F(CrossLanguageMessageTest, ToolMessageStructured) {
    auto test_case = find_test_case("tool_message_structured");
    auto msg_data = test_case["message"];

    // Structured content (already a JSON object)
    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    // Add metadata
    for (auto& [key, value] : msg_data["metadata"].items()) {
        msg.with_metadata(key, value);
    }

    // Validate structured content
    EXPECT_EQ(msg.role(), "tool");
    EXPECT_TRUE(msg.content().is_object());

    const auto& content_obj = msg.content();
    EXPECT_EQ(content_obj["tool_name"], "calculator");
    EXPECT_EQ(content_obj["result"], 5);
    EXPECT_EQ(content_obj["success"], true);

    // Serialize and validate
    auto serialized = msg.to_json();
    validate_against_schema(serialized);
}

TEST_F(CrossLanguageMessageTest, AgentMessage) {
    auto test_case = find_test_case("agent_message");
    auto msg_data = test_case["message"];

    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    // Add metadata
    for (auto& [key, value] : msg_data["metadata"].items()) {
        msg.with_metadata(key, value);
    }

    EXPECT_EQ(msg.role(), "agent");
    std::string content_str = msg.content_as_str();
    EXPECT_NE(content_str.find("reasoning steps"), std::string::npos);
    EXPECT_EQ(msg.metadata()["technique"], "chain_of_thought");

    auto serialized = msg.to_json();
    validate_against_schema(serialized);
}

TEST_F(CrossLanguageMessageTest, EmptyContent) {
    auto test_case = find_test_case("empty_content");
    auto msg_data = test_case["message"];

    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    EXPECT_EQ(msg.role(), "assistant");
    EXPECT_EQ(msg.content_as_str(), "");

    auto serialized = msg.to_json();
    validate_against_schema(serialized);
}

TEST_F(CrossLanguageMessageTest, LargeContent) {
    auto test_case = find_test_case("large_content");
    auto msg_data = test_case["message"];

    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    // Add metadata
    for (auto& [key, value] : msg_data["metadata"].items()) {
        msg.with_metadata(key, value);
    }

    auto validation = test_case["validation"];
    size_t min_length = validation["min_content_length"].get<size_t>();

    std::string content_str = msg.content_as_str();
    EXPECT_GE(content_str.length(), min_length);
    EXPECT_NE(content_str.find("Lorem ipsum"), std::string::npos);

    auto serialized = msg.to_json();
    validate_against_schema(serialized);
}

TEST_F(CrossLanguageMessageTest, UnicodeContent) {
    auto test_case = find_test_case("unicode_content");
    auto msg_data = test_case["message"];

    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    // Add metadata
    for (auto& [key, value] : msg_data["metadata"].items()) {
        msg.with_metadata(key, value);
    }

    // Verify Unicode characters preserved
    std::string content_str = msg.content_as_str();
    EXPECT_NE(content_str.find("世界"), std::string::npos);
    EXPECT_NE(content_str.find("🌍"), std::string::npos);
    EXPECT_NE(content_str.find("мир"), std::string::npos);

    auto serialized = msg.to_json();
    validate_against_schema(serialized);
}

TEST_F(CrossLanguageMessageTest, NestedMetadata) {
    auto test_case = find_test_case("nested_metadata");
    auto msg_data = test_case["message"];

    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    // Add metadata
    for (auto& [key, value] : msg_data["metadata"].items()) {
        msg.with_metadata(key, value);
    }

    // Verify nested structure
    EXPECT_TRUE(msg.metadata().contains("analysis"));
    EXPECT_TRUE(msg.metadata()["analysis"].is_object());
    EXPECT_EQ(msg.metadata()["analysis"]["sentiment"], "positive");

    EXPECT_TRUE(msg.metadata().contains("processing"));
    EXPECT_TRUE(msg.metadata()["processing"].is_object());

    EXPECT_TRUE(msg.metadata().contains("tags"));
    EXPECT_TRUE(msg.metadata()["tags"].is_array());

    auto serialized = msg.to_json();
    validate_against_schema(serialized);
}

TEST_F(CrossLanguageMessageTest, NumericMetadata) {
    auto test_case = find_test_case("numeric_metadata");
    auto msg_data = test_case["message"];

    Message msg(
        msg_data["role"].get<std::string>(),
        msg_data["content"]
    );

    // Add metadata
    for (auto& [key, value] : msg_data["metadata"].items()) {
        msg.with_metadata(key, value);
    }

    // Verify numeric types preserved
    EXPECT_EQ(msg.metadata()["count"].get<int>(), 42);
    EXPECT_NEAR(msg.metadata()["score"].get<double>(), 3.14159, 0.0001);
    EXPECT_EQ(msg.metadata()["is_final"].get<bool>(), true);
    EXPECT_TRUE(msg.metadata()["optional_value"].is_null());

    auto serialized = msg.to_json();
    validate_against_schema(serialized);
}

TEST_F(CrossLanguageMessageTest, AllFixturesRoundtrip) {
    for (const auto& test_case : fixtures["test_cases"]) {
        SCOPED_TRACE("Test case: " + test_case["id"].get<std::string>());

        auto msg_data = test_case["message"];

        // Create message
        Message msg(
            msg_data["role"].get<std::string>(),
            msg_data["content"]
        );

        // Add metadata if present
        if (msg_data.contains("metadata")) {
            for (auto& [key, value] : msg_data["metadata"].items()) {
                msg.with_metadata(key, value);
            }
        }

        // Serialize and validate
        auto serialized = msg.to_json();
        validate_against_schema(serialized);

        // Verify core properties match
        EXPECT_EQ(serialized["role"].get<std::string>(), msg_data["role"].get<std::string>());
        EXPECT_TRUE(serialized.contains("content"));
    }
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
