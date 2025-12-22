"""Tests for output validation and sensitive data redaction."""

import pytest

from agenkit.interfaces import Agent, Message
from agenkit.safety.output_validation import (OutputValidationError,
                                              OutputValidationMiddleware,
                                              SchemaValidator,
                                              SensitiveDataRedactor)


class ResponseAgent(Agent):
    """Agent that returns structured responses."""

    @property
    def name(self) -> str:
        return "responder"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content={"result": "success", "data": "test output"})


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
                "result": "User data retrieved",
            },
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
            expected_fields={"result": str, "data": str}, required_fields={"result"}
        )

        output = {"result": "success", "data": "test"}
        is_valid, error = validator.validate(output)

        assert is_valid is True
        assert error is None

    def test_catches_missing_required_fields(self):
        """Test detection of missing required fields."""
        validator = SchemaValidator(
            expected_fields={"result": str, "data": str}, required_fields={"result", "data"}
        )

        output = {"result": "success"}
        is_valid, error = validator.validate(output)

        assert is_valid is False
        assert "missing required fields" in error.lower()
        assert "data" in error

    def test_catches_wrong_types(self):
        """Test detection of wrong field types."""
        validator = SchemaValidator(expected_fields={"result": str, "count": int})

        output = {"result": "success", "count": "not_an_int"}
        is_valid, error = validator.validate(output)

        assert is_valid is False
        assert "wrong type" in error.lower()

    def test_allows_additional_fields(self):
        """Test that additional fields are allowed by default."""
        validator = SchemaValidator(expected_fields={"result": str}, allow_additional=True)

        output = {"result": "success", "extra": "field"}
        is_valid, _error = validator.validate(output)

        assert is_valid is True

    def test_rejects_additional_fields_when_disabled(self):
        """Test rejection of additional fields when disabled."""
        validator = SchemaValidator(expected_fields={"result": str}, allow_additional=False)

        output = {"result": "success", "extra": "field"}
        is_valid, error = validator.validate(output)

        assert is_valid is False
        assert "unexpected fields" in error.lower()

    def test_parses_json_string(self):
        """Test validation of JSON strings."""
        validator = SchemaValidator(expected_fields={"name": str, "count": int})

        import json

        json_str = json.dumps({"name": "test", "count": 42})
        is_valid, error = validator.validate(json_str)

        assert is_valid is True
        assert error is None

    def test_invalid_json_string(self):
        """Test handling of invalid JSON strings."""
        validator = SchemaValidator(expected_fields={"name": str})

        is_valid, error = validator.validate("not valid json")
        assert is_valid is False
        assert "json" in error.lower()

    def test_non_dict_non_json_input(self):
        """Test rejection of non-dict, non-JSON input."""
        validator = SchemaValidator(expected_fields={"name": str})

        is_valid, error = validator.validate(12345)
        assert is_valid is False
        assert "dictionary" in error.lower() or "json" in error.lower()

    def test_optional_fields(self):
        """Test validation with optional fields."""
        validator = SchemaValidator(
            expected_fields={"name": str, "age": int, "email": str},
            required_fields={"name"},  # age and email are optional
        )

        # Without optional fields
        is_valid, _ = validator.validate({"name": "Alice"})
        assert is_valid is True

        # With some optional fields
        is_valid, _ = validator.validate({"name": "Alice", "age": 30})
        assert is_valid is True

        # With all fields
        is_valid, _ = validator.validate({"name": "Alice", "age": 30, "email": "alice@example.com"})
        assert is_valid is True

        # With optional field but wrong type
        is_valid, error = validator.validate({"name": "Alice", "age": "thirty"})
        assert is_valid is False
        assert "wrong type" in error.lower()

    def test_no_schema_specified(self):
        """Test that validator with no schema accepts anything."""
        validator = SchemaValidator()

        is_valid, _ = validator.validate({"any": "data", "structure": 123})
        assert is_valid is True

        is_valid, _ = validator.validate("plain string")
        assert is_valid is True

        is_valid, _ = validator.validate([1, 2, 3])
        assert is_valid is True


class TestSensitiveDataRedactor:
    """Tests for SensitiveDataRedactor."""

    def test_redacts_sensitive_field_names(self):
        """Test redaction of sensitive field names."""
        redactor = SensitiveDataRedactor()

        data = {
            "username": "alice",
            "password": "secret123",
            "api_key": "sk-abcdef",
            "result": "success",
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

        data = {"user": {"name": "Alice", "password": "secret123"}, "api_key": "sk-abcdef"}

        redacted = redactor.redact(data)

        assert redacted["user"]["password"] == "***REDACTED***"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["user"]["name"] == "Alice"

    def test_redacts_ssn(self):
        """Test redaction of Social Security Numbers."""
        redactor = SensitiveDataRedactor()

        text = "My SSN is 123-45-6789"
        redacted = redactor.redact(text)

        assert "123-45-6789" not in redacted
        assert "***REDACTED***_SSN" in redacted

    def test_redacts_credit_card(self):
        """Test redaction of credit card numbers."""
        redactor = SensitiveDataRedactor()

        text = "Card: 1234 5678 9012 3456"
        redacted = redactor.redact(text)

        assert "1234 5678 9012 3456" not in redacted
        assert "***REDACTED***_CREDIT_CARD" in redacted

    def test_redacts_jwt_token(self):
        """Test redaction of JWT tokens."""
        redactor = SensitiveDataRedactor()

        text = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        redacted = redactor.redact(text)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
        # JWT is matched by generic API_KEY pattern, which is acceptable
        assert "***REDACTED***" in redacted

    def test_redacts_aws_access_key(self):
        """Test redaction of AWS access keys."""
        redactor = SensitiveDataRedactor()

        text = "AWS Key: AKIAIOSFODNN7EXAMPLE"
        redacted = redactor.redact(text)

        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "***REDACTED***_AWS_ACCESS_KEY" in redacted

    def test_redacts_github_token(self):
        """Test redaction of GitHub tokens."""
        redactor = SensitiveDataRedactor()

        text = "GitHub: ghp_1234567890abcdefghijklmnopqrstuv12"
        redacted = redactor.redact(text)

        assert "ghp_1234567890abcdefghijklmnopqrstuv12" not in redacted
        # GitHub token is matched by generic API_KEY pattern, which is acceptable
        assert "***REDACTED***" in redacted

    def test_redacts_list_of_dicts(self):
        """Test redaction of lists containing dictionaries."""
        redactor = SensitiveDataRedactor()

        data = [
            {"name": "Alice", "password": "secret1"},
            {"name": "Bob", "api_key": "key123"},
        ]

        redacted = redactor.redact(data)

        assert redacted[0]["name"] == "Alice"
        assert redacted[0]["password"] == "***REDACTED***"
        assert redacted[1]["name"] == "Bob"
        assert redacted[1]["api_key"] == "***REDACTED***"

    def test_case_insensitive_field_matching(self):
        """Test that sensitive field matching is case-insensitive."""
        redactor = SensitiveDataRedactor()

        data = {
            "PASSWORD": "secret",
            "ApiKey": "key123",
            "Token": "token456",
        }

        redacted = redactor.redact(data)

        assert redacted["PASSWORD"] == "***REDACTED***"
        assert redacted["ApiKey"] == "***REDACTED***"
        assert redacted["Token"] == "***REDACTED***"

    def test_custom_sensitive_fields(self):
        """Test adding custom sensitive fields."""
        redactor = SensitiveDataRedactor(sensitive_fields={"internal_id", "employee_code"})

        data = {
            "name": "Alice",
            "internal_id": "EMP-12345",
            "employee_code": "ABC123",
        }

        redacted = redactor.redact(data)

        assert redacted["name"] == "Alice"
        assert redacted["internal_id"] == "***REDACTED***"
        assert redacted["employee_code"] == "***REDACTED***"

    def test_custom_redaction_text(self):
        """Test custom redaction placeholder text."""
        redactor = SensitiveDataRedactor(redaction_text="[HIDDEN]")

        data = {"password": "secret"}
        redacted = redactor.redact(data)

        assert redacted["password"] == "[HIDDEN]"

    def test_has_sensitive_data_nested(self):
        """Test detection in nested structures."""
        redactor = SensitiveDataRedactor()

        data = {"user": {"profile": {"password": "secret"}}}

        assert redactor.has_sensitive_data(data) is True

        # Also test list with nested dicts
        data_list = [{"safe": "data"}, {"nested": {"password": "secret"}}]
        assert redactor.has_sensitive_data(data_list) is True

    def test_redact_primitives_unchanged(self):
        """Test that primitive types pass through unchanged."""
        redactor = SensitiveDataRedactor()

        assert redactor.redact(123) == 123
        assert redactor.redact(45.67) == 45.67
        assert redactor.redact(True) is True
        assert redactor.redact(None) is None

    def test_redact_string_with_multiple_pii(self):
        """Test redaction of string with multiple PII types."""
        redactor = SensitiveDataRedactor()

        text = "Contact: user@example.com, SSN: 123-45-6789, Card: 1234567890123456"
        redacted = redactor.redact(text)

        assert "user@example.com" not in redacted
        assert "123-45-6789" not in redacted
        assert "1234567890123456" not in redacted
        assert "***REDACTED***" in redacted


class TestOutputValidationMiddleware:
    """Tests for OutputValidationMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_valid_output(self, response_agent):
        """Test that valid output passes through."""
        schema = SchemaValidator(expected_fields={"result": str, "data": str})
        agent = OutputValidationMiddleware(response_agent, schema=schema)

        message = Message(role="user", content="test")
        response = await agent.process(message)

        assert response.content["result"] == "success"

    @pytest.mark.asyncio
    async def test_blocks_invalid_schema(self, response_agent):
        """Test that invalid schema is blocked."""
        schema = SchemaValidator(
            expected_fields={"result": str, "count": int}, required_fields={"count"}
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

    @pytest.mark.asyncio
    async def test_middleware_preserves_agent_name(self, response_agent):
        """Test that middleware preserves underlying agent name."""
        agent = OutputValidationMiddleware(response_agent)
        assert agent.name == response_agent.name

    @pytest.mark.asyncio
    async def test_middleware_preserves_capabilities(self, response_agent):
        """Test that middleware preserves underlying agent capabilities."""
        agent = OutputValidationMiddleware(response_agent)
        assert agent.capabilities == response_agent.capabilities

    @pytest.mark.asyncio
    async def test_sensitive_data_warning_logged(self, sensitive_agent, capfd):
        """Test that warning is logged when sensitive data detected."""
        agent = OutputValidationMiddleware(sensitive_agent, auto_redact=True)

        message = Message(role="user", content="test")
        await agent.process(message)

        # Check warning was printed
        captured = capfd.readouterr()
        assert "WARNING" in captured.out
        assert "sensitive data" in captured.out.lower()

    @pytest.mark.asyncio
    async def test_custom_redactor(self):
        """Test with custom redactor configuration."""

        class CustomAgent(Agent):
            @property
            def name(self) -> str:
                return "custom"

            @property
            def capabilities(self) -> list[str]:
                return []

            async def process(self, message: Message) -> Message:
                return Message(
                    role="assistant", content={"internal_id": "SECRET-123", "data": "public"}
                )

        custom_redactor = SensitiveDataRedactor(
            sensitive_fields={"internal_id"}, redaction_text="[REMOVED]"
        )
        agent = OutputValidationMiddleware(
            CustomAgent(), redactor=custom_redactor, auto_redact=True
        )

        message = Message(role="user", content="test")
        response = await agent.process(message)

        assert response.content["internal_id"] == "[REMOVED]"
        assert response.content["data"] == "public"

    @pytest.mark.asyncio
    async def test_combined_schema_and_redaction(self):
        """Test combining schema validation and redaction."""

        class CombinedAgent(Agent):
            @property
            def name(self) -> str:
                return "combined"

            @property
            def capabilities(self) -> list[str]:
                return []

            async def process(self, message: Message) -> Message:
                return Message(
                    role="assistant",
                    content={
                        "username": "alice",
                        "password": "secret",
                        "age": 30,
                        "status": "active",
                    },
                )

        schema = SchemaValidator(
            expected_fields={"username": str, "password": str, "age": int, "status": str}
        )
        agent = OutputValidationMiddleware(CombinedAgent(), schema=schema, auto_redact=True)

        message = Message(role="user", content="test")
        response = await agent.process(message)

        # Should pass schema validation AND redact password
        assert response.content["username"] == "alice"
        assert response.content["password"] == "***REDACTED***"
        assert response.content["age"] == 30
        assert response.content["status"] == "active"


def test_output_validation_decorator():
    """Test output_validation decorator function."""
    from agenkit.safety.output_validation import output_validation

    class TestAgent(Agent):
        @property
        def name(self) -> str:
            return "test"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="test output")

    base_agent = TestAgent()
    middleware_fn = output_validation(auto_redact=True, max_size=5000)

    agent = middleware_fn(base_agent)

    assert isinstance(agent, OutputValidationMiddleware)
    assert agent.auto_redact is True
    assert agent.max_size == 5000


def test_output_validation_decorator_with_schema():
    """Test output_validation decorator with schema."""
    from agenkit.safety.output_validation import output_validation

    class TestAgent(Agent):
        @property
        def name(self) -> str:
            return "test"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="test output")

    base_agent = TestAgent()
    schema = SchemaValidator(expected_fields={"result": str})

    middleware_fn = output_validation(schema=schema, auto_redact=False)

    agent = middleware_fn(base_agent)

    assert isinstance(agent, OutputValidationMiddleware)
    assert agent.schema == schema
    assert agent.auto_redact is False
