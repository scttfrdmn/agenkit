/**
 * @file test_usage.cpp
 * @brief Tests for typed token usage normalization.
 */

#include <gtest/gtest.h>

#include "agenkit/adapters/usage.hpp"
#include "agenkit/core/message.hpp"

using agenkit::adapters::Usage;
using agenkit::adapters::usage_from_message;
using agenkit::core::Message;

namespace {

Message msg_with(const nlohmann::json& usage) {
    Message m = Message::with_text("assistant", "hi");
    m.with_metadata("usage", usage);
    return m;
}

}  // namespace

TEST(UsageTest, NulloptWhenNoUsage) {
    Message m = Message::with_text("assistant", "hi");
    EXPECT_FALSE(usage_from_message(m).has_value());
}

TEST(UsageTest, PromptCompletionConvention) {
    auto u = usage_from_message(msg_with(
        {{"prompt_tokens", 10}, {"completion_tokens", 5}, {"total_tokens", 15}}));
    ASSERT_TRUE(u.has_value());
    EXPECT_EQ(u->prompt_tokens, 10);
    EXPECT_EQ(u->completion_tokens, 5);
    EXPECT_EQ(u->total_tokens, 15);
}

TEST(UsageTest, AnthropicConventionDerivesTotal) {
    auto u = usage_from_message(msg_with({{"input_tokens", 30}, {"output_tokens", 7}}));
    ASSERT_TRUE(u.has_value());
    EXPECT_EQ(u->prompt_tokens, 30);
    EXPECT_EQ(u->completion_tokens, 7);
    EXPECT_EQ(u->total_tokens, 37);
}

TEST(UsageTest, NormalizedCacheKeys) {
    auto u = usage_from_message(msg_with({{"prompt_tokens", 1000},
                                          {"completion_tokens", 50},
                                          {"total_tokens", 1050},
                                          {"cache_read_tokens", 900},
                                          {"cache_creation_tokens", 100}}));
    ASSERT_TRUE(u.has_value());
    EXPECT_EQ(u->cache_read_tokens, 900);
    EXPECT_EQ(u->cache_creation_tokens, 100);
}

TEST(UsageTest, RawProviderCacheAliases) {
    auto u = usage_from_message(msg_with({{"input_tokens", 20},
                                          {"output_tokens", 4},
                                          {"cache_read_input_tokens", 15},
                                          {"cache_creation_input_tokens", 5}}));
    ASSERT_TRUE(u.has_value());
    EXPECT_EQ(*u, (Usage{20, 4, 24, 15, 5}));
}

TEST(UsageTest, IgnoresNonNumeric) {
    auto u = usage_from_message(msg_with({{"prompt_tokens", "x"}, {"completion_tokens", 5}}));
    ASSERT_TRUE(u.has_value());
    EXPECT_EQ(u->prompt_tokens, 0);
    EXPECT_EQ(u->completion_tokens, 5);
}
