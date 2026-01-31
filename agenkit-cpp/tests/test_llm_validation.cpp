/**
 * @file test_llm_validation.cpp
 * @brief Tests for LLM parameter validation
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/validation.hpp"

using namespace agenkit::adapters;

// Test temperature validation
TEST(LLMValidation, ValidTemperature) {
    EXPECT_NO_THROW(LLMParameterValidator::validate_temperature(0.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_temperature(1.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_temperature(2.0));
}

TEST(LLMValidation, InvalidTemperatureTooLow) {
    EXPECT_THROW({
        LLMParameterValidator::validate_temperature(-0.1);
    }, std::invalid_argument);
}

TEST(LLMValidation, InvalidTemperatureTooHigh) {
    EXPECT_THROW({
        LLMParameterValidator::validate_temperature(2.1);
    }, std::invalid_argument);
}

TEST(LLMValidation, TemperatureErrorMessage) {
    try {
        LLMParameterValidator::validate_temperature(3.0);
        FAIL() << "Expected std::invalid_argument";
    } catch (const std::invalid_argument& e) {
        std::string message(e.what());
        EXPECT_TRUE(message.find("temperature must be between 0 and 2") != std::string::npos);
        EXPECT_TRUE(message.find("3.0") != std::string::npos ||
                    message.find("3.00") != std::string::npos);
    }
}

// Test max_tokens validation
TEST(LLMValidation, ValidMaxTokens) {
    EXPECT_NO_THROW(LLMParameterValidator::validate_max_tokens(1));
    EXPECT_NO_THROW(LLMParameterValidator::validate_max_tokens(100));
    EXPECT_NO_THROW(LLMParameterValidator::validate_max_tokens(4096));
}

TEST(LLMValidation, InvalidMaxTokensZero) {
    EXPECT_THROW({
        LLMParameterValidator::validate_max_tokens(0);
    }, std::invalid_argument);
}

TEST(LLMValidation, InvalidMaxTokensNegative) {
    EXPECT_THROW({
        LLMParameterValidator::validate_max_tokens(-100);
    }, std::invalid_argument);
}

TEST(LLMValidation, MaxTokensErrorMessage) {
    try {
        LLMParameterValidator::validate_max_tokens(0);
        FAIL() << "Expected std::invalid_argument";
    } catch (const std::invalid_argument& e) {
        std::string message(e.what());
        EXPECT_TRUE(message.find("max_tokens must be positive") != std::string::npos);
        EXPECT_TRUE(message.find("0") != std::string::npos);
    }
}

// Test top_p validation
TEST(LLMValidation, ValidTopP) {
    EXPECT_NO_THROW(LLMParameterValidator::validate_top_p(0.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_top_p(0.5));
    EXPECT_NO_THROW(LLMParameterValidator::validate_top_p(1.0));
}

TEST(LLMValidation, InvalidTopPTooLow) {
    EXPECT_THROW({
        LLMParameterValidator::validate_top_p(-0.1);
    }, std::invalid_argument);
}

TEST(LLMValidation, InvalidTopPTooHigh) {
    EXPECT_THROW({
        LLMParameterValidator::validate_top_p(1.1);
    }, std::invalid_argument);
}

TEST(LLMValidation, TopPErrorMessage) {
    try {
        LLMParameterValidator::validate_top_p(1.5);
        FAIL() << "Expected std::invalid_argument";
    } catch (const std::invalid_argument& e) {
        std::string message(e.what());
        EXPECT_TRUE(message.find("top_p must be between 0 and 1") != std::string::npos);
        EXPECT_TRUE(message.find("1.5") != std::string::npos);
    }
}

// Test frequency_penalty validation
TEST(LLMValidation, ValidFrequencyPenalty) {
    EXPECT_NO_THROW(LLMParameterValidator::validate_frequency_penalty(-2.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_frequency_penalty(0.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_frequency_penalty(2.0));
}

TEST(LLMValidation, InvalidFrequencyPenaltyTooLow) {
    EXPECT_THROW({
        LLMParameterValidator::validate_frequency_penalty(-2.1);
    }, std::invalid_argument);
}

TEST(LLMValidation, InvalidFrequencyPenaltyTooHigh) {
    EXPECT_THROW({
        LLMParameterValidator::validate_frequency_penalty(2.5);
    }, std::invalid_argument);
}

TEST(LLMValidation, FrequencyPenaltyErrorMessage) {
    try {
        LLMParameterValidator::validate_frequency_penalty(3.0);
        FAIL() << "Expected std::invalid_argument";
    } catch (const std::invalid_argument& e) {
        std::string message(e.what());
        EXPECT_TRUE(message.find("frequency_penalty must be between -2 and 2") != std::string::npos);
        EXPECT_TRUE(message.find("3.0") != std::string::npos ||
                    message.find("3.00") != std::string::npos);
    }
}

// Test presence_penalty validation
TEST(LLMValidation, ValidPresencePenalty) {
    EXPECT_NO_THROW(LLMParameterValidator::validate_presence_penalty(-2.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_presence_penalty(0.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_presence_penalty(2.0));
}

TEST(LLMValidation, InvalidPresencePenaltyTooLow) {
    EXPECT_THROW({
        LLMParameterValidator::validate_presence_penalty(-2.1);
    }, std::invalid_argument);
}

TEST(LLMValidation, InvalidPresencePenaltyTooHigh) {
    EXPECT_THROW({
        LLMParameterValidator::validate_presence_penalty(2.5);
    }, std::invalid_argument);
}

TEST(LLMValidation, PresencePenaltyErrorMessage) {
    try {
        LLMParameterValidator::validate_presence_penalty(3.0);
        FAIL() << "Expected std::invalid_argument";
    } catch (const std::invalid_argument& e) {
        std::string message(e.what());
        EXPECT_TRUE(message.find("presence_penalty must be between -2 and 2") != std::string::npos);
        EXPECT_TRUE(message.find("3.0") != std::string::npos ||
                    message.find("3.00") != std::string::npos);
    }
}

// Test validate_all function
TEST(LLMValidation, ValidateAllValid) {
    EXPECT_NO_THROW(LLMParameterValidator::validate_all(
        0.7,    // temperature
        1024,   // max_tokens
        0.9,    // top_p
        0.5,    // frequency_penalty
        -0.5    // presence_penalty
    ));
}

TEST(LLMValidation, ValidateAllInvalidTemperature) {
    EXPECT_THROW({
        LLMParameterValidator::validate_all(
            3.0,    // invalid temperature
            1024,
            0.9,
            0.0,
            0.0
        );
    }, std::invalid_argument);
}

TEST(LLMValidation, ValidateAllInvalidMaxTokens) {
    EXPECT_THROW({
        LLMParameterValidator::validate_all(
            0.7,
            0,      // invalid max_tokens
            0.9,
            0.0,
            0.0
        );
    }, std::invalid_argument);
}

TEST(LLMValidation, ValidateAllInvalidTopP) {
    EXPECT_THROW({
        LLMParameterValidator::validate_all(
            0.7,
            1024,
            1.5,    // invalid top_p
            0.0,
            0.0
        );
    }, std::invalid_argument);
}

TEST(LLMValidation, ValidateAllInvalidFrequencyPenalty) {
    EXPECT_THROW({
        LLMParameterValidator::validate_all(
            0.7,
            1024,
            0.9,
            3.0,    // invalid frequency_penalty
            0.0
        );
    }, std::invalid_argument);
}

TEST(LLMValidation, ValidateAllInvalidPresencePenalty) {
    EXPECT_THROW({
        LLMParameterValidator::validate_all(
            0.7,
            1024,
            0.9,
            0.0,
            3.0     // invalid presence_penalty
        );
    }, std::invalid_argument);
}

// Test boundary values
TEST(LLMValidation, BoundaryValues) {
    // Temperature boundaries
    EXPECT_NO_THROW(LLMParameterValidator::validate_temperature(0.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_temperature(2.0));

    // Max tokens boundary
    EXPECT_NO_THROW(LLMParameterValidator::validate_max_tokens(1));

    // Top P boundaries
    EXPECT_NO_THROW(LLMParameterValidator::validate_top_p(0.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_top_p(1.0));

    // Penalty boundaries
    EXPECT_NO_THROW(LLMParameterValidator::validate_frequency_penalty(-2.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_frequency_penalty(2.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_presence_penalty(-2.0));
    EXPECT_NO_THROW(LLMParameterValidator::validate_presence_penalty(2.0));
}
