"""
Example: Output Validation and Sensitive Data Redaction

This example demonstrates how to use OutputValidationMiddleware to validate
agent outputs and automatically redact sensitive information.
"""

import asyncio

from agenkit.interfaces import Agent, Message
from agenkit.safety.output_validation import (OutputValidationError,
                                              OutputValidationMiddleware,
                                              SchemaValidator,
                                              SensitiveDataRedactor)


# Agent that returns structured data
class DataAgent(Agent):
    """Agent that returns structured API-style responses."""

    @property
    def name(self) -> str:
        return "data_agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content={
                "status": "success",
                "data": {"user": "alice", "age": 30},
                "timestamp": "2025-11-14T10:00:00Z",
            },
        )


# Agent that may leak sensitive data
class SensitiveAgent(Agent):
    """Agent that returns potentially sensitive information."""

    @property
    def name(self) -> str:
        return "sensitive_agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content={
                "user_info": {
                    "name": "Alice",
                    "email": "alice@example.com",
                    "api_key": "sk-1234567890abcdefghij1234567890ab",
                    "password": "my_secret_password",
                },
                "message": "User data retrieved successfully",
            },
        )


async def main():
    """Demonstrate output validation."""
    print("=" * 60)
    print("Output Validation Example")
    print("=" * 60)

    # 1. Schema validation
    print("\n1. Schema Validation")
    print("-" * 60)

    schema = SchemaValidator(
        expected_fields={"status": str, "data": dict, "timestamp": str},
        required_fields={"status", "data"},
    )

    data_agent = DataAgent()
    validated_agent = OutputValidationMiddleware(data_agent, schema=schema)

    try:
        response = await validated_agent.process(Message(role="user", content="get data"))
        print(f"✓ Valid output: {response.content}")
    except OutputValidationError as e:
        print(f"✗ Validation failed: {e}")

    # 2. Automatic sensitive data redaction
    print("\n2. Automatic Sensitive Data Redaction")
    print("-" * 60)

    sensitive_agent = SensitiveAgent()
    redacting_agent = OutputValidationMiddleware(
        sensitive_agent,
        auto_redact=True,  # Enable automatic redaction
    )

    try:
        response = await redacting_agent.process(Message(role="user", content="get user"))
        print("✓ Response with redacted sensitive data:")
        print(f"  {response.content}")
        print("\n  Note: API key, password, and email are redacted!")
    except OutputValidationError as e:
        print(f"✗ Error: {e}")

    # 3. Manual redaction (inspection only)
    print("\n3. Manual Redaction (for inspection)")
    print("-" * 60)

    redactor = SensitiveDataRedactor()

    test_data = {
        "username": "alice",
        "password": "secret123",
        "api_key": "sk-abc123",
        "public_info": "This is fine",
    }

    # Check for sensitive data
    if redactor.has_sensitive_data(test_data):
        print(f"⚠ Sensitive data detected in: {test_data}")
        redacted = redactor.redact(test_data)
        print(f"✓ After redaction: {redacted}")

    # 4. Custom schema with strict validation
    print("\n4. Custom Schema with Strict Validation")
    print("-" * 60)

    strict_schema = SchemaValidator(
        expected_fields={"status": str, "code": int},
        required_fields={"status", "code"},
        allow_additional=False,  # Don't allow extra fields
    )

    strict_agent = OutputValidationMiddleware(data_agent, schema=strict_schema)

    try:
        response = await strict_agent.process(Message(role="user", content="test"))
        print(f"✓ Response: {response.content}")
    except OutputValidationError as e:
        print(f"✗ Validation failed (extra fields not allowed): {e}")

    # 5. Size limits
    print("\n5. Output Size Limits")
    print("-" * 60)

    class LargeOutputAgent(Agent):
        @property
        def name(self) -> str:
            return "large"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="x" * 10000)

    large_agent = LargeOutputAgent()
    size_limited_agent = OutputValidationMiddleware(large_agent, max_size=100)

    try:
        response = await size_limited_agent.process(Message(role="user", content="test"))
        print(f"✓ Response: {response.content[:50]}...")
    except OutputValidationError as e:
        print(f"✗ Output too large: {e}")

    print("\n" + "=" * 60)
    print("Output Validation Example Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
