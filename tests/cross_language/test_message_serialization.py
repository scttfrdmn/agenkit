"""
Cross-language message serialization tests.

Tests that Agenkit messages serialize/deserialize consistently with the
canonical JSON schema across all language implementations.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import validate, ValidationError

from agenkit import Message


# Load test fixtures and schema
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCHEMAS_DIR = Path(__file__).parent / "schemas"

with open(FIXTURES_DIR / "messages.json") as f:
    MESSAGE_FIXTURES = json.load(f)

with open(SCHEMAS_DIR / "message.schema.json") as f:
    MESSAGE_SCHEMA = json.load(f)


class TestMessageSerialization:
    """Test message serialization against cross-language fixtures."""

    @pytest.fixture
    def message_test_cases(self):
        """Load message test cases from fixtures."""
        return MESSAGE_FIXTURES["test_cases"]

    def test_fixtures_load(self, message_test_cases):
        """Verify test fixtures load correctly."""
        assert len(message_test_cases) > 0
        assert MESSAGE_FIXTURES["version"] == "1.0"

    def test_schema_validates_fixtures(self, message_test_cases):
        """Verify all fixtures validate against JSON schema."""
        for test_case in message_test_cases:
            # Each fixture message should validate against schema
            validate(instance=test_case["message"], schema=MESSAGE_SCHEMA)

    def test_simple_user_message(self, message_test_cases):
        """Test simple user message serialization."""
        test_case = next(tc for tc in message_test_cases if tc["id"] == "simple_user_message")

        # Create message from fixture
        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
            metadata=msg_data.get("metadata", {}),
        )

        # Validate properties
        assert msg.role == "user"
        assert msg.content == "Hello, agent!"
        assert isinstance(msg.metadata, dict)

        # Serialize back to dict
        serialized = self._message_to_dict(msg)

        # Verify against schema
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

        # Verify key properties match
        assert serialized["role"] == msg_data["role"]
        assert serialized["content"] == msg_data["content"]

    def test_assistant_message_with_metadata(self, message_test_cases):
        """Test assistant message with metadata."""
        test_case = next(
            tc for tc in message_test_cases
            if tc["id"] == "assistant_message_with_metadata"
        )

        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
            metadata=msg_data["metadata"],
        )

        # Validate
        assert msg.role == "assistant"
        assert msg.content == "I can help you with that!"
        assert len(msg.metadata) == 3
        assert "model" in msg.metadata
        assert "temperature" in msg.metadata
        assert "tokens" in msg.metadata

        # Verify metadata types
        validation = test_case["validation"]
        assert set(msg.metadata.keys()) == set(validation["metadata_keys"])

        # Serialize and validate
        serialized = self._message_to_dict(msg)
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_system_message(self, message_test_cases):
        """Test system message without metadata."""
        test_case = next(tc for tc in message_test_cases if tc["id"] == "system_message")

        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
        )

        assert msg.role == "system"
        assert "helpful assistant" in msg.content

        serialized = self._message_to_dict(msg)
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_tool_message_structured(self, message_test_cases):
        """Test tool message with structured content."""
        test_case = next(
            tc for tc in message_test_cases
            if tc["id"] == "tool_message_structured"
        )

        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
            metadata=msg_data["metadata"],
        )

        # Validate structured content
        assert msg.role == "tool"
        assert isinstance(msg.content, dict)
        assert msg.content["tool_name"] == "calculator"
        assert msg.content["result"] == 5
        assert msg.content["success"] is True

        # Verify content keys
        validation = test_case["validation"]
        assert set(msg.content.keys()) == set(validation["content_keys"])

        # Serialize and validate
        serialized = self._message_to_dict(msg)
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_agent_message(self, message_test_cases):
        """Test agent message from internal reasoning."""
        test_case = next(tc for tc in message_test_cases if tc["id"] == "agent_message")

        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
            metadata=msg_data["metadata"],
        )

        assert msg.role == "agent"
        assert "reasoning steps" in msg.content
        assert msg.metadata["technique"] == "chain_of_thought"

        serialized = self._message_to_dict(msg)
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_empty_content(self, message_test_cases):
        """Test message with empty string content."""
        test_case = next(tc for tc in message_test_cases if tc["id"] == "empty_content")

        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
        )

        assert msg.role == "assistant"
        assert msg.content == ""
        assert len(msg.content) == 0

        serialized = self._message_to_dict(msg)
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_large_content(self, message_test_cases):
        """Test message with larger text content."""
        test_case = next(tc for tc in message_test_cases if tc["id"] == "large_content")

        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
            metadata=msg_data["metadata"],
        )

        validation = test_case["validation"]
        assert len(msg.content) >= validation["min_content_length"]
        assert "Lorem ipsum" in msg.content

        serialized = self._message_to_dict(msg)
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_unicode_content(self, message_test_cases):
        """Test message with Unicode characters."""
        test_case = next(tc for tc in message_test_cases if tc["id"] == "unicode_content")

        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
            metadata=msg_data["metadata"],
        )

        # Verify Unicode characters preserved
        validation = test_case["validation"]
        for substring in validation["contains"]:
            assert substring in msg.content

        assert "世界" in msg.content
        assert "🌍" in msg.content
        assert "мир" in msg.content

        serialized = self._message_to_dict(msg)
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_nested_metadata(self, message_test_cases):
        """Test message with nested metadata."""
        test_case = next(tc for tc in message_test_cases if tc["id"] == "nested_metadata")

        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
            metadata=msg_data["metadata"],
        )

        # Verify nested structure
        assert "analysis" in msg.metadata
        assert isinstance(msg.metadata["analysis"], dict)
        assert msg.metadata["analysis"]["sentiment"] == "positive"

        assert "processing" in msg.metadata
        assert isinstance(msg.metadata["processing"], dict)

        assert "tags" in msg.metadata
        assert isinstance(msg.metadata["tags"], list)

        serialized = self._message_to_dict(msg)
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_numeric_metadata(self, message_test_cases):
        """Test message with various numeric metadata types."""
        test_case = next(
            tc for tc in message_test_cases
            if tc["id"] == "numeric_metadata"
        )

        msg_data = test_case["message"]
        msg = Message(
            role=msg_data["role"],
            content=msg_data["content"],
            metadata=msg_data["metadata"],
        )

        # Verify numeric types preserved
        assert isinstance(msg.metadata["count"], int)
        assert msg.metadata["count"] == 42

        assert isinstance(msg.metadata["score"], float)
        assert abs(msg.metadata["score"] - 3.14159) < 0.0001

        assert isinstance(msg.metadata["is_final"], bool)
        assert msg.metadata["is_final"] is True

        assert msg.metadata["optional_value"] is None

        serialized = self._message_to_dict(msg)
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_all_fixtures_roundtrip(self, message_test_cases):
        """Test that all fixtures roundtrip correctly."""
        for test_case in message_test_cases:
            msg_data = test_case["message"]

            # Create message
            msg = Message(
                role=msg_data["role"],
                content=msg_data["content"],
                metadata=msg_data.get("metadata", {}),
            )

            # Serialize
            serialized = self._message_to_dict(msg)

            # Validate against schema
            try:
                validate(instance=serialized, schema=MESSAGE_SCHEMA)
            except ValidationError as e:
                pytest.fail(
                    f"Test case '{test_case['id']}' failed schema validation: {e.message}"
                )

            # Verify core properties match
            assert serialized["role"] == msg_data["role"]
            # Content may be transformed (e.g., dict preserved)
            if isinstance(msg_data["content"], str):
                assert serialized["content"] == msg_data["content"]

    @staticmethod
    def _message_to_dict(msg: Message) -> dict[str, Any]:
        """Convert Message to dict for serialization testing."""
        result = {
            "role": msg.role,
            "content": msg.content,
        }

        if msg.metadata:
            result["metadata"] = msg.metadata

        if hasattr(msg, "timestamp") and msg.timestamp:
            result["timestamp"] = msg.timestamp.isoformat() if hasattr(msg.timestamp, "isoformat") else str(msg.timestamp)

        return result


class TestSchemaCompliance:
    """Test that Message implementation complies with JSON schema."""

    def test_role_validation(self):
        """Test that invalid roles are rejected."""
        with pytest.raises((ValueError, TypeError)):
            Message(role="invalid_role", content="test")

    def test_metadata_structure(self):
        """Test metadata follows schema constraints."""
        msg = Message(
            role="user",
            content="test",
            metadata={"key1": "value1", "key2": 123},
        )

        serialized = TestMessageSerialization._message_to_dict(msg)

        # Should validate against schema
        validate(instance=serialized, schema=MESSAGE_SCHEMA)

    def test_schema_version(self):
        """Verify schema version matches implementation."""
        assert MESSAGE_SCHEMA["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert "message.json" in MESSAGE_SCHEMA["$id"]
