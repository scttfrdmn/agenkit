"""
Message Serialization Property-Based Tests

Validates message serialization/deserialization invariants:
- Round-trip consistency: deserialize(serialize(msg)) == msg
- Type preservation: Message fields maintain correct types
- Metadata preservation: Metadata survives serialization
- Size bounds: Serialized size is reasonable
"""
import json
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, assume, strategies as st

from agenkit.interfaces import Message
from tests.property.strategies import (
    role_strategy,
    content_strategy,
    metadata_strategy,
    message_strategy,
)


def serialize_message(msg: Message) -> str:
    """Serialize message to JSON."""
    data = {
        "role": msg.role,
        "content": msg.content,
    }

    if msg.metadata:
        data["metadata"] = msg.metadata

    if msg.timestamp:
        data["timestamp"] = msg.timestamp.isoformat()

    return json.dumps(data)


def deserialize_message(json_str: str) -> Message:
    """Deserialize message from JSON."""
    data = json.loads(json_str)

    timestamp = None
    if "timestamp" in data:
        timestamp = datetime.fromisoformat(data["timestamp"])

    return Message(
        role=data["role"],
        content=data["content"],
        metadata=data.get("metadata"),
        timestamp=timestamp
    )


# ============================================
# Property: Round-Trip Consistency
# ============================================

@pytest.mark.property
@given(message=message_strategy())
@settings(max_examples=200, deadline=None)
def test_message_round_trip_consistency(message):
    """Property: deserialize(serialize(msg)) preserves all fields."""
    # Clear timestamp for comparison (we'll check it separately)
    original_msg = Message(
        role=message.role,
        content=message.content,
        metadata=message.metadata
    )

    # Serialize and deserialize
    serialized = serialize_message(original_msg)
    deserialized = deserialize_message(serialized)

    # Property: All fields should match
    assert deserialized.role == original_msg.role, "Role should be preserved"
    assert deserialized.content == original_msg.content, "Content should be preserved"

    # Compare metadata
    if original_msg.metadata is None:
        assert deserialized.metadata is None, "None metadata should be preserved"
    else:
        assert deserialized.metadata == original_msg.metadata, "Metadata should be preserved"


# ============================================
# Property: Type Preservation
# ============================================

@pytest.mark.property
@given(
    role=role_strategy,
    content=content_strategy,
)
@settings(max_examples=200, deadline=None)
def test_message_type_preservation(role, content):
    """Property: Message fields maintain correct types after serialization."""
    msg = Message(role=role, content=content)

    serialized = serialize_message(msg)
    deserialized = deserialize_message(serialized)

    # Property: Types should be preserved
    assert isinstance(deserialized.role, str), "Role should be string"
    assert isinstance(deserialized.content, str), "Content should be string"


# ============================================
# Property: Metadata Type Preservation
# ============================================

@pytest.mark.property
@given(metadata=metadata_strategy)
@settings(max_examples=200, deadline=None)
def test_metadata_type_preservation(metadata):
    """Property: Metadata types are preserved through serialization."""
    assume(metadata is not None and len(metadata) > 0)

    msg = Message(role="user", content="test", metadata=metadata)

    serialized = serialize_message(msg)
    deserialized = deserialize_message(serialized)

    # Property: Metadata should be preserved with correct types
    assert deserialized.metadata is not None, "Metadata should not be None"

    for key, value in metadata.items():
        assert key in deserialized.metadata, f"Key {key} should be in metadata"

        # Check type preservation
        original_value = metadata[key]
        deserialized_value = deserialized.metadata[key]

        if original_value is None:
            assert deserialized_value is None, f"None value for {key} should be preserved"
        elif isinstance(original_value, bool):
            assert isinstance(deserialized_value, bool), f"Bool type for {key} should be preserved"
        elif isinstance(original_value, int):
            assert isinstance(deserialized_value, int), f"Int type for {key} should be preserved"
        elif isinstance(original_value, float):
            assert isinstance(deserialized_value, float), f"Float type for {key} should be preserved"
        elif isinstance(original_value, str):
            assert isinstance(deserialized_value, str), f"String type for {key} should be preserved"


# ============================================
# Property: Serialized Size is Reasonable
# ============================================

@pytest.mark.property
@given(message=message_strategy())
@settings(max_examples=200, deadline=None)
def test_serialized_size_is_reasonable(message):
    """Property: Serialized size doesn't grow exponentially."""
    serialized = serialize_message(message)

    # Property: Serialized size should be roughly proportional to content size
    # Allow 3x overhead for JSON structure and metadata
    content_size = len(message.content)
    metadata_size = len(json.dumps(message.metadata)) if message.metadata else 0
    expected_max_size = (content_size + metadata_size + 100) * 3  # 3x overhead

    actual_size = len(serialized)

    assert actual_size <= expected_max_size, \
        f"Serialized size {actual_size} too large (expected <={expected_max_size})"


# ============================================
# Property: Empty Content Handling
# ============================================

@pytest.mark.property
@given(role=role_strategy)
@settings(max_examples=100, deadline=None)
def test_empty_content_handling(role):
    """Property: Empty content is handled correctly."""
    msg = Message(role=role, content="")

    serialized = serialize_message(msg)
    deserialized = deserialize_message(serialized)

    # Property: Empty content should be preserved
    assert deserialized.content == "", "Empty content should be preserved"
    assert isinstance(deserialized.content, str), "Empty content should still be string"


# ============================================
# Property: Unicode Content Preservation
# ============================================

@pytest.mark.property
@given(
    unicode_content=st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Sm", "Sc", "So")),
        min_size=1,
        max_size=100
    )
)
@settings(max_examples=200, deadline=None)
def test_unicode_content_preservation(unicode_content):
    """Property: Unicode content is preserved through serialization."""
    msg = Message(role="user", content=unicode_content)

    serialized = serialize_message(msg)
    deserialized = deserialize_message(serialized)

    # Property: Unicode characters should be preserved exactly
    assert deserialized.content == unicode_content, \
        f"Unicode content not preserved: expected {unicode_content!r}, got {deserialized.content!r}"


# ============================================
# Property: Timestamp Preservation
# ============================================

@pytest.mark.property
@given(
    content=content_strategy,
)
@settings(max_examples=100, deadline=None)
def test_timestamp_preservation(content):
    """Property: Timestamp is preserved through serialization."""
    # Create message with explicit timestamp
    timestamp = datetime.now(timezone.utc)
    msg = Message(role="user", content=content, timestamp=timestamp)

    serialized = serialize_message(msg)
    deserialized = deserialize_message(serialized)

    # Property: Timestamp should be preserved (within microsecond precision)
    assert deserialized.timestamp is not None, "Timestamp should not be None"
    # Compare timestamps (allow small difference due to serialization)
    time_diff = abs((deserialized.timestamp - timestamp).total_seconds())
    assert time_diff < 0.001, f"Timestamp not preserved: diff={time_diff}s"


# ============================================
# Property: Large Metadata Handling
# ============================================

@pytest.mark.property
@given(
    num_keys=st.integers(min_value=1, max_value=50),
)
@settings(max_examples=100, deadline=None)
def test_large_metadata_handling(num_keys):
    """Property: Large metadata dicts are handled correctly."""
    # Create large metadata dict
    metadata = {f"key_{i}": f"value_{i}" for i in range(num_keys)}

    msg = Message(role="user", content="test", metadata=metadata)

    serialized = serialize_message(msg)
    deserialized = deserialize_message(serialized)

    # Property: All metadata keys should be preserved
    assert len(deserialized.metadata) == num_keys, \
        f"Expected {num_keys} keys, got {len(deserialized.metadata)}"

    for i in range(num_keys):
        key = f"key_{i}"
        assert key in deserialized.metadata, f"Key {key} should be in metadata"
        assert deserialized.metadata[key] == f"value_{i}", \
            f"Value for {key} should be preserved"


# ============================================
# Property: Nested Metadata (if supported)
# ============================================

@pytest.mark.property
@given(
    outer_key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll"))),
    inner_key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll"))),
    value=st.integers(min_value=-1000, max_value=1000),
)
@settings(max_examples=100, deadline=None)
def test_nested_metadata_preservation(outer_key, inner_key, value):
    """Property: Nested metadata structures are preserved."""
    # Ensure keys are different
    assume(outer_key != inner_key)

    metadata = {
        outer_key: {
            inner_key: value
        }
    }

    msg = Message(role="user", content="test", metadata=metadata)

    serialized = serialize_message(msg)
    deserialized = deserialize_message(serialized)

    # Property: Nested structure should be preserved
    assert outer_key in deserialized.metadata, f"Outer key {outer_key} should exist"
    assert isinstance(deserialized.metadata[outer_key], dict), "Nested dict should be preserved"
    assert inner_key in deserialized.metadata[outer_key], f"Inner key {inner_key} should exist"
    assert deserialized.metadata[outer_key][inner_key] == value, "Nested value should be preserved"


# ============================================
# Property: Serialization is Deterministic
# ============================================

@pytest.mark.property
@given(message=message_strategy())
@settings(max_examples=100, deadline=None)
def test_serialization_is_deterministic(message):
    """Property: Serializing the same message multiple times produces same result."""
    # Clear timestamp for determinism
    msg = Message(
        role=message.role,
        content=message.content,
        metadata=message.metadata
    )

    # Serialize multiple times
    serialized1 = serialize_message(msg)
    serialized2 = serialize_message(msg)
    serialized3 = serialize_message(msg)

    # Property: All serializations should be identical
    assert serialized1 == serialized2, "Serialization should be deterministic"
    assert serialized2 == serialized3, "Serialization should be deterministic"


# ============================================
# Property: Deserialization of Serialization is Idempotent
# ============================================

@pytest.mark.property
@given(message=message_strategy())
@settings(max_examples=100, deadline=None)
def test_deserialization_idempotency(message):
    """Property: deserialize(serialize(msg)) multiple times produces same result."""
    # Clear timestamp
    msg = Message(
        role=message.role,
        content=message.content,
        metadata=message.metadata
    )

    serialized = serialize_message(msg)

    # Deserialize multiple times
    deserialized1 = deserialize_message(serialized)
    deserialized2 = deserialize_message(serialized)
    deserialized3 = deserialize_message(serialized)

    # Property: All deserializations should produce equivalent messages
    assert deserialized1.role == deserialized2.role
    assert deserialized1.content == deserialized2.content
    assert deserialized1.metadata == deserialized2.metadata

    assert deserialized2.role == deserialized3.role
    assert deserialized2.content == deserialized3.content
    assert deserialized2.metadata == deserialized3.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property"])
