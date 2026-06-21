#ifndef AGENKIT_ADAPTERS_USAGE_HPP
#define AGENKIT_ADAPTERS_USAGE_HPP

#include <cstdint>
#include <optional>

#include <nlohmann/json.hpp>

#include "agenkit/core/message.hpp"

/**
 * @file usage.hpp
 * @brief Typed token usage for LLM adapter responses.
 *
 * Adapters record token counts in `Message::metadata()["usage"]` as a JSON
 * object, but key names differ between the prompt_tokens/completion_tokens
 * convention and the Anthropic input_tokens/output_tokens convention.
 * usage_from_message() normalizes both into one struct so cost-metering and
 * budgeting layers consume a single shape.
 *
 * Mirrors the Go reference (agenkit-go/adapter/llm/usage.go).
 */

namespace agenkit {
namespace adapters {

/**
 * @brief Normalized, typed token usage.
 *
 * Fields are 0 when the provider does not report them. The cache fields are
 * provider-dependent (e.g. Anthropic prompt caching, including via Bedrock) and
 * are 0 when caching is inactive.
 */
struct Usage {
    std::int64_t prompt_tokens = 0;
    std::int64_t completion_tokens = 0;
    std::int64_t total_tokens = 0;
    std::int64_t cache_read_tokens = 0;
    std::int64_t cache_creation_tokens = 0;

    bool operator==(const Usage& other) const {
        return prompt_tokens == other.prompt_tokens &&
               completion_tokens == other.completion_tokens &&
               total_tokens == other.total_tokens &&
               cache_read_tokens == other.cache_read_tokens &&
               cache_creation_tokens == other.cache_creation_tokens;
    }
};

namespace detail {

/// First present integer-valued key, or 0 if none.
template <typename... Keys>
inline std::int64_t pick_token(const nlohmann::json& usage, Keys... keys) {
    for (const char* key : {keys...}) {
        auto it = usage.find(key);
        if (it != usage.end() && it->is_number()) {
            return it->get<std::int64_t>();
        }
    }
    return 0;
}

}  // namespace detail

/**
 * @brief Extract normalized token usage from an adapter response message.
 *
 * Reads the `metadata()["usage"]` object, normalizing both naming conventions
 * (prompt_tokens/completion_tokens and Anthropic input_tokens/output_tokens) and
 * the cache keys (cache_read_tokens/cache_creation_tokens, plus the raw provider
 * aliases cache_read_input_tokens/cache_creation_input_tokens).
 *
 * @return the Usage, or std::nullopt when no usage metadata is present. When
 *   total_tokens is absent it is derived as prompt + completion.
 */
inline std::optional<Usage> usage_from_message(const core::Message& message) {
    const nlohmann::json& metadata = message.metadata();
    auto it = metadata.find("usage");
    if (it == metadata.end() || !it->is_object()) {
        return std::nullopt;
    }
    const nlohmann::json& usage = *it;

    Usage result;
    result.prompt_tokens = detail::pick_token(usage, "prompt_tokens", "input_tokens");
    result.completion_tokens = detail::pick_token(usage, "completion_tokens", "output_tokens");
    result.total_tokens = detail::pick_token(usage, "total_tokens");
    if (result.total_tokens == 0) {
        result.total_tokens = result.prompt_tokens + result.completion_tokens;
    }
    result.cache_read_tokens =
        detail::pick_token(usage, "cache_read_tokens", "cache_read_input_tokens");
    result.cache_creation_tokens = detail::pick_token(
        usage, "cache_creation_tokens", "cache_creation_input_tokens", "cache_write_tokens");

    return result;
}

}  // namespace adapters
}  // namespace agenkit

#endif  // AGENKIT_ADAPTERS_USAGE_HPP
