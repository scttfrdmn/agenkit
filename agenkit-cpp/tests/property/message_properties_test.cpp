/**
 * @file message_properties_test.cpp
 * @brief Property-based tests for Message invariants using RapidCheck
 *
 * Verifies that Message upholds its contract under arbitrary inputs:
 * role/content preservation, JSON round-trips, metadata accumulation,
 * timestamp ordering, and serialization correctness.
 */

#include <gtest/gtest.h>
#include <rapidcheck.h>
#include <rapidcheck/gtest.h>
#include "agenkit/core/message.hpp"
#include <vector>
#include <string>

using namespace agenkit;

namespace {
const std::vector<std::string> kValidRoles = {
    "user", "assistant", "system", "tool", "agent"
};
} // namespace

// 1. Role is preserved after construction
RC_GTEST_PROP(MessageProperties, RolePreservedRoundTrip, (std::string text)) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, text);
    RC_ASSERT(msg.role() == role);
}

// 2. Text content is preserved after construction
RC_GTEST_PROP(MessageProperties, ContentPreservedRoundTrip, (std::string text)) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, text);
    RC_ASSERT(msg.content_as_str() == text);
}

// 3. JSON serialization is a round-trip identity for role and content
RC_GTEST_PROP(MessageProperties, JsonSerializationRoundTrip, (std::string text)) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, text);
    auto json = msg.to_json();
    auto restored = core::Message::from_json(json);
    RC_ASSERT(restored.role() == msg.role());
    RC_ASSERT(restored.content_as_str() == msg.content_as_str());
}

// 4. A metadata key set via with_metadata is retrievable
RC_GTEST_PROP(MessageProperties, MetadataKeyPreserved, (std::string key, std::string val)) {
    RC_PRE(!key.empty());
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, "hello");
    msg.with_metadata(key, val);
    RC_ASSERT(msg.metadata().contains(key));
    RC_ASSERT(msg.metadata()[key].get<std::string>() == val);
}

// 5. Two distinct metadata keys do not overwrite each other
RC_GTEST_PROP(MessageProperties, MultipleMetadataNoOverwrite, (std::string v1, std::string v2)) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, "test");
    // Use fixed distinct keys so there is no collision
    msg.with_metadata("key_a", v1);
    msg.with_metadata("key_b", v2);
    RC_ASSERT(msg.metadata()["key_a"].get<std::string>() == v1);
    RC_ASSERT(msg.metadata()["key_b"].get<std::string>() == v2);
}

// 6. Adding metadata does not mutate the role
RC_GTEST_PROP(MessageProperties, RoleNotMutatedByMetadata, (std::string val)) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, "hello");
    msg.with_metadata("some_key", val);
    RC_ASSERT(msg.role() == role);
}

// 7. Empty text content is valid and round-trips correctly
RC_GTEST_PROP(MessageProperties, EmptyContentValid, ()) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, "");
    RC_ASSERT(msg.content_as_str() == "");
}

// 8. Two messages created sequentially have non-decreasing timestamps
RC_GTEST_PROP(MessageProperties, TimestampNonDecreasing, ()) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg1 = core::Message::with_text(role, "first");
    auto msg2 = core::Message::with_text(role, "second");
    RC_ASSERT(msg1.timestamp() <= msg2.timestamp());
}

// 9. content_as_str returns empty when content is a JSON object (not a string)
RC_GTEST_PROP(MessageProperties, ContentAsStrForNonStringReturnsEmpty, ()) {
    auto role = *rc::gen::elementOf(kValidRoles);
    nlohmann::json obj = nlohmann::json::object();
    obj["key"] = "value";
    core::Message msg(role, obj);
    RC_ASSERT(msg.content_as_str() == "");
}

// 10. with_text is equivalent to constructor with string JSON value
RC_GTEST_PROP(MessageProperties, WithTextConvenience, (std::string text)) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg_convenience = core::Message::with_text(role, text);
    core::Message msg_direct(role, nlohmann::json(text));
    RC_ASSERT(msg_convenience.role() == msg_direct.role());
    RC_ASSERT(msg_convenience.content_as_str() == msg_direct.content_as_str());
}

// 11. A freshly created message has empty metadata
RC_GTEST_PROP(MessageProperties, MetadataInitiallyEmpty, (std::string text)) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, text);
    RC_ASSERT(msg.metadata().empty());
}

// 12. All valid roles survive a JSON round-trip
RC_GTEST_PROP(MessageProperties, RoleRoundTripAllValid, ()) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, "content");
    auto restored = core::Message::from_json(msg.to_json());
    RC_ASSERT(restored.role() == role);
}

// 13. Long text content (up to 1000 chars) is preserved correctly
RC_GTEST_PROP(MessageProperties, LongContentPreserved, ()) {
    // Generate a text of 0..1000 printable ASCII characters
    auto len = *rc::gen::inRange(0, 1001);
    auto chars = *rc::gen::container<std::vector<char>>(
        len,
        rc::gen::inRange<char>('a', 'z' + 1)
    );
    std::string text(chars.begin(), chars.end());
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, text);
    RC_ASSERT(msg.content_as_str() == text);
}

// 14. metadata() always returns a JSON object (never array or scalar)
RC_GTEST_PROP(MessageProperties, MetadataJsonObjectType, (std::string key, std::string val)) {
    RC_PRE(!key.empty());
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, "test");
    msg.with_metadata(key, val);
    RC_ASSERT(msg.metadata().is_object());
}

// 15. Fluent with_metadata chaining accumulates all keys
RC_GTEST_PROP(MessageProperties, MultipleMetadataChainingAccumulatesKeys, ()) {
    auto role = *rc::gen::elementOf(kValidRoles);
    auto msg = core::Message::with_text(role, "test");
    msg.with_metadata("k1", "v1")
       .with_metadata("k2", "v2")
       .with_metadata("k3", "v3");
    RC_ASSERT(msg.metadata().contains("k1"));
    RC_ASSERT(msg.metadata().contains("k2"));
    RC_ASSERT(msg.metadata().contains("k3"));
    RC_ASSERT(msg.metadata().size() == 3);
}
