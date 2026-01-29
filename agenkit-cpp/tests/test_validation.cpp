/**
 * @file test_validation.cpp
 * @brief Tests for LLM parameter validation
 *
 * Ensures that temperature, max_tokens, and other parameters are validated
 * at construction time to provide clear errors before API calls.
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/openai_agent.hpp"

using namespace agenkit::core;
using namespace agenkit::adapters;

// ============================================================================
// OpenAI Temperature Validation Tests
// ============================================================================

TEST(OpenAIValidationTest, ValidTemperature0) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.temperature = 0.0;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}

TEST(OpenAIValidationTest, ValidTemperature1) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.temperature = 1.0;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}

TEST(OpenAIValidationTest, ValidTemperature2) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.temperature = 2.0;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}

TEST(OpenAIValidationTest, InvalidTemperatureNegative) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.temperature = -0.5;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

TEST(OpenAIValidationTest, InvalidTemperatureTooHigh) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.temperature = 3.0;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

// ============================================================================
// OpenAI Max Tokens Validation Tests
// ============================================================================

TEST(OpenAIValidationTest, ValidMaxTokens) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.max_tokens = 1024;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}

TEST(OpenAIValidationTest, InvalidMaxTokensZero) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.max_tokens = 0;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

TEST(OpenAIValidationTest, InvalidMaxTokensNegative) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.max_tokens = -10;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

// ============================================================================
// OpenAI Top P Validation Tests
// ============================================================================

TEST(OpenAIValidationTest, ValidTopP) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.top_p = 0.9;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}

TEST(OpenAIValidationTest, InvalidTopPNegative) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.top_p = -0.1;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

TEST(OpenAIValidationTest, InvalidTopPTooHigh) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.top_p = 1.5;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

// ============================================================================
// OpenAI Frequency Penalty Validation Tests
// ============================================================================

TEST(OpenAIValidationTest, InvalidFrequencyPenaltyTooLow) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.frequency_penalty = -3.0;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

TEST(OpenAIValidationTest, InvalidFrequencyPenaltyTooHigh) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.frequency_penalty = 3.0;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

// ============================================================================
// OpenAI Presence Penalty Validation Tests
// ============================================================================

TEST(OpenAIValidationTest, InvalidPresencePenaltyTooLow) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.presence_penalty = -2.5;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

TEST(OpenAIValidationTest, InvalidPresencePenaltyTooHigh) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.presence_penalty = 2.5;

    EXPECT_THROW({
        OpenAIAgent agent(config);
    }, std::invalid_argument);
}

// ============================================================================
// Boundary Value Tests
// ============================================================================

TEST(BoundaryValidationTest, TemperatureExactly0) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.temperature = 0.0;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}

TEST(BoundaryValidationTest, TemperatureExactly2) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.temperature = 2.0;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}

TEST(BoundaryValidationTest, MaxTokensExactly1) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.max_tokens = 1;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}

TEST(BoundaryValidationTest, TopPExactly0) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.top_p = 0.0;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}

TEST(BoundaryValidationTest, TopPExactly1) {
    OpenAIConfig config;
    config.api_key = "sk-test";
    config.top_p = 1.0;

    EXPECT_NO_THROW(OpenAIAgent agent(config));
}
