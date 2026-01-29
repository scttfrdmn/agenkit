#pragma once

#include <stdexcept>
#include <string>

namespace agenkit {
namespace adapters {

/**
 * Shared LLM parameter validation utilities.
 *
 * Provides standard validation for common LLM parameters across all adapters.
 * All adapters should use these functions to ensure consistent parameter validation.
 */
class LLMParameterValidator {
public:
    /**
     * Validate temperature parameter (0.0-2.0).
     *
     * @param temperature Temperature value to validate
     * @throws std::invalid_argument if temperature is out of range
     */
    static void validate_temperature(double temperature) {
        if (temperature < 0.0 || temperature > 2.0) {
            throw std::invalid_argument(
                "temperature must be between 0 and 2, got " +
                std::to_string(temperature)
            );
        }
    }

    /**
     * Validate max_tokens parameter (must be positive).
     *
     * @param max_tokens Maximum tokens value to validate
     * @throws std::invalid_argument if max_tokens is not positive
     */
    static void validate_max_tokens(int max_tokens) {
        if (max_tokens <= 0) {
            throw std::invalid_argument(
                "max_tokens must be positive, got " +
                std::to_string(max_tokens)
            );
        }
    }

    /**
     * Validate top_p parameter (0.0-1.0).
     *
     * @param top_p Top-p value to validate
     * @throws std::invalid_argument if top_p is out of range
     */
    static void validate_top_p(double top_p) {
        if (top_p < 0.0 || top_p > 1.0) {
            throw std::invalid_argument(
                "top_p must be between 0 and 1, got " +
                std::to_string(top_p)
            );
        }
    }

    /**
     * Validate frequency_penalty parameter (-2.0 to 2.0).
     *
     * @param frequency_penalty Frequency penalty value to validate
     * @throws std::invalid_argument if frequency_penalty is out of range
     */
    static void validate_frequency_penalty(double frequency_penalty) {
        if (frequency_penalty < -2.0 || frequency_penalty > 2.0) {
            throw std::invalid_argument(
                "frequency_penalty must be between -2 and 2, got " +
                std::to_string(frequency_penalty)
            );
        }
    }

    /**
     * Validate presence_penalty parameter (-2.0 to 2.0).
     *
     * @param presence_penalty Presence penalty value to validate
     * @throws std::invalid_argument if presence_penalty is out of range
     */
    static void validate_presence_penalty(double presence_penalty) {
        if (presence_penalty < -2.0 || presence_penalty > 2.0) {
            throw std::invalid_argument(
                "presence_penalty must be between -2 and 2, got " +
                std::to_string(presence_penalty)
            );
        }
    }

    /**
     * Validate all common LLM parameters.
     *
     * @param temperature Temperature value
     * @param max_tokens Maximum tokens value
     * @param top_p Top-p value
     * @param frequency_penalty Frequency penalty value (optional)
     * @param presence_penalty Presence penalty value (optional)
     * @throws std::invalid_argument if any parameter is out of valid range
     */
    static void validate_all(
        double temperature,
        int max_tokens,
        double top_p,
        double frequency_penalty = 0.0,
        double presence_penalty = 0.0
    ) {
        validate_temperature(temperature);
        validate_max_tokens(max_tokens);
        validate_top_p(top_p);
        validate_frequency_penalty(frequency_penalty);
        validate_presence_penalty(presence_penalty);
    }
};

} // namespace adapters
} // namespace agenkit
