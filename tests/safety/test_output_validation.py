"""Tests for output validation and sensitive data redaction."""

import pytest
from agenkit.interfaces import Agent, Message
from agenkit.safety.output_validation import (
    OutputValidationMiddleware,
    SchemaValidator,
    SensitiveDataRedactor,
    OutputValidationError,
)


class ResponseAgent(Agent):
    """Agent that returns structured responses."""

    @property
    def name(self) -> str:
        return "responder"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content={"result": "success", "data": "test output"}
        )


class SensitiveAgent(Agent):
    """Agent that returns sensitive data."""

    @property
    def name(self) -> str:
        return "sensitive"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content={
                "api_key": "sk-1234567890abcdef",
                "password": "secret123",
                "email": "user@example.com",
                "result": "User data retrieved"
            }
        )


@pytest.fixture
def response_agent():
    """Agent that returns structured responses."""
    return ResponseAgent()


@pytest.fixture
def sensitive_agent():
    """Agent that returns sensitive data."""
    return SensitiveAgent()


class TestSchemaValidator:
    """Tests for SchemaValidator."""

    def test_validates_correct_schema(self):
        """Test validation of correct schema."""
        validator = SchemaValidator(
            expected_fields={"result": str, "data": str},
            required_fields={"result"}
        )

        output = {"result": "success", "data": "test"}
        is_valid, error = validator.validate(output)

        assert is_valid is True
        assert error is None

    def test_catches_missing_required_fields(self):
        """Test detection of missing required fields."""
        validator = SchemaValidator(
            expected_fields={"result": str, "data": str},
            required_fields={"result", "data"}
        )

        output = {"result": "success"}
        is_valid, error = validator.validate(output)

        assert is_valid is False
        assert "missing required fields" in error.lower()
        assert "data" in error

    def test_catches_wrong_types(self):
        """Test detection of wrong field types."""
        validator = SchemaValidator(
            expected_fields={"result": str, "count": int}
        )

        output = {"result": "success", "count": "not_an_int"}
        is_valid, error = validator.validate(output)

        assert is_valid is False
        assert "wrong type" in error.lower()

    def test_allows_additional_fields(self):
        """Test that additional fields are allowed by default."""
        validator = SchemaValidator(
            expected_fields={"result": str},
            allow_additional=True
        )

        output = {"result": "success", "extra": "field"}
        is_valid, error = validator.validate(output)

        assert is_valid is True

    def test_rejects_additional_fields_when_disabled(self):
        """Test rejection of additional fields when disabled."""
        validator = SchemaValidator(
            expected_fields={"result": str},
            allow_additional=False
        )

        output = {"result": "success", "extra": "field"}
        is_valid, error = validator.validate(output)

        assert is_valid is False
        assert "unexpected fields" in error.lower()


class TestSensitiveDataRedactor:
    """Tests for SensitiveDataRedactor."""

    def test_redacts_sensitive_field_names(self):
        """Test redaction of sensitive field names."""
        redactor = SensitiveDataRedactor()

        data = {
            "username": "alice",
            "password": "secret123",
            "api_key": "sk-abcdef",
            "result": "success"
        }

        redacted = redactor.redact(data)

        assert redacted["password"] == "***REDACTED***"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["username"] == "alice"  # Not sensitive
        assert redacted["result"] == "success"

    def test_redacts_api_keys_in_strings(self):
        """Test redaction of API keys in string content."""
        redactor = SensitiveDataRedactor()

        text = "Your API key is sk-1234567890abcdefghij1234567890ab"
        redacted = redactor.redact(text)

        assert "sk-1234567890" not in redacted
        assert "***REDACTED***_API_KEY" in redacted

    def test_redacts_email_addresses(self):
        """Test redaction of email addresses."""
        redactor = SensitiveDataRedactor()

        text = "Contact me at user@example.com for details"
        redacted = redactor.redact(text)

        assert "user@example.com" not in redacted
        assert "***REDACTED***_EMAIL" in redacted

    def test_redacts_phone_numbers(self):
        """Test redaction of phone numbers."""
        redactor = SensitiveDataRedactor()

        text = "Call me at 123-456-7890"
        redacted = redactor.redact(text)

        assert "123-456-7890" not in redacted
        assert "***REDACTED***_PHONE" in redacted

    def test_detects_sensitive_data(self):
        """Test detection of sensitive data."""
        redactor = SensitiveDataRedactor()

        sensitive_data = {"password": "secret"}
        assert redactor.has_sensitive_data(sensitive_data) is True

        safe_data = {"username": "alice", "result": "success"}
        assert redactor.has_sensitive_data(safe_data) is False

    def test_redacts_nested_structures(self):
        """Test redaction in nested dictionaries."""
        redactor = SensitiveDataRedactor()

        data = {
            "user": {
                "name": "Alice",
                "password": "secret123"
            },
            "api_key": "sk-abcdef"
        }

        redacted = redactor.redact(data)

        assert redacted["user"]["password"] == "***REDACTED***"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["user"]["name"] == "Alice"


class TestOutputValidationMiddleware:
    """Tests for OutputValidationMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_valid_output(self, response_agent):
        """Test that valid output passes through."""
        schema = SchemaValidator(
            expected_fields={"result": str, "data": str}
        )
        agent = OutputValidationMiddleware(response_agent, schema=schema)

        message = Message(role="user", content="test")
        response = await agent.process(message)

        assert response.content["result"] == "success"

    @pytest.mark.asyncio
    async def test_blocks_invalid_schema(self, response_agent):
        """Test that invalid schema is blocked."""
        schema = SchemaValidator(
            expected_fields={"result": str, "count": int},
            required_fields={"count"}
        )
        agent = OutputValidationMiddleware(response_agent, schema=schema)

        message = Message(role="user", content="test")

        with pytest.raises(OutputValidationError) as exc_info:
            await agent.process(message)

        assert "validation failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_auto_redacts_sensitive_data(self, sensitive_agent):
        """Test automatic redaction of sensitive data."""
        agent = OutputValidationMiddleware(sensitive_agent, auto_redact=True)

        message = Message(role="user", content="test")
        response = await agent.process(message)

        # Sensitive fields should be redacted
        assert response.content["api_key"] == "***REDACTED***"
        assert response.content["password"] == "***REDACTED***"
        # Non-sensitive fields should remain
        assert response.content["result"] == "User data retrieved"

    @pytest.mark.asyncio
    async def test_blocks_oversized_output(self):
        """Test that oversized output is blocked."""
        # Create an agent that returns large output
        class LargeOutputAgent(Agent):
            @property
            def name(self) -> str:
                return "large"

            @property
            def capabilities(self) -> list[str]:
                return []

            async def process(self, message: Message) -> Message:
                return Message(role="assistant", content="x" * 100)

        large_agent = LargeOutputAgent()
        agent = OutputValidationMiddleware(large_agent, max_size=50)

        message = Message(role="user", content="test")

        with pytest.raises(OutputValidationError) as exc_info:
            await agent.process(message)

        assert "exceeds maximum size" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_can_disable_auto_redaction(self, sensitive_agent):
        """Test that auto-redaction can be disabled."""
        agent = OutputValidationMiddleware(sensitive_agent, auto_redact=False)

        message = Message(role="user", content="test")
        response = await agent.process(message)

        # Sensitive data should NOT be redacted
        assert response.content["api_key"] == "sk-1234567890abcdef"
        assert response.content["password"] == "secret123"
