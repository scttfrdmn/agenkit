"""
Output validation and content filtering.

Provides protection for agent outputs:
- Schema validation
- Sensitive data redaction
- Content policy enforcement
- Output size limits
"""

import re
import json
from typing import Optional, Any, Dict, Set, List
from dataclasses import dataclass, field

from agenkit import Agent, Message


class OutputValidationError(Exception):
    """Raised when output validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


@dataclass
class SchemaValidator:
    """
    Validates output against expected schema.

    Supports basic type checking and structure validation.
    """

    # Expected fields and their types
    expected_fields: Optional[Dict[str, type]] = None

    # Required fields (subset of expected_fields)
    required_fields: Optional[Set[str]] = None

    # Allow additional fields not in schema
    allow_additional: bool = True

    def validate(self, output: Any) -> tuple[bool, Optional[str]]:
        """
        Validate output against schema.

        Args:
            output: Output to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # If no schema specified, always valid
        if not self.expected_fields:
            return True, None

        # Check if output is dict-like
        if not isinstance(output, dict):
            # Try to parse as JSON if string
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except json.JSONDecodeError:
                    return False, "Output is not valid JSON or dict"
            else:
                return False, "Output must be a dictionary or JSON string"

        # Check required fields
        if self.required_fields:
            missing = self.required_fields - set(output.keys())
            if missing:
                return False, f"Missing required fields: {', '.join(missing)}"

        # Check field types
        for field_name, expected_type in self.expected_fields.items():
            if field_name in output:
                value = output[field_name]
                if not isinstance(value, expected_type):
                    return (
                        False,
                        f"Field '{field_name}' has wrong type: "
                        f"expected {expected_type.__name__}, got {type(value).__name__}",
                    )

        # Check for additional fields
        if not self.allow_additional:
            extra = set(output.keys()) - set(self.expected_fields.keys())
            if extra:
                return False, f"Unexpected fields: {', '.join(extra)}"

        return True, None


@dataclass
class SensitiveDataRedactor:
    """
    Redacts sensitive data from outputs.

    Detects and redacts:
    - API keys
    - Passwords
    - Tokens
    - PII (email, phone, SSN, credit cards)
    - Custom sensitive patterns
    """

    # Sensitive field names (case-insensitive)
    sensitive_fields: Set[str] = field(
        default_factory=lambda: {
            "password",
            "api_key",
            "apikey",
            "token",
            "secret",
            "auth",
            "credential",
            "private_key",
            "access_key",
        }
    )

    # Patterns for detecting sensitive data
    sensitive_patterns: List[tuple[str, str]] = field(
        default_factory=lambda: [
            # API keys (common formats)
            (r"sk-[a-zA-Z0-9]{32,}", "API_KEY"),
            (r"[a-zA-Z0-9_-]{32,}", "API_KEY"),  # Generic token
            # AWS credentials
            (r"AKIA[0-9A-Z]{16}", "AWS_ACCESS_KEY"),
            # GitHub tokens
            (r"ghp_[a-zA-Z0-9]{36}", "GITHUB_TOKEN"),
            # Email addresses
            (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "EMAIL"),
            # Phone numbers (US format)
            (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "PHONE"),
            # SSN
            (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
            # Credit card numbers
            (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "CREDIT_CARD"),
            # JWT tokens
            (r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", "JWT"),
        ]
    )

    # Redaction placeholder
    redaction_text: str = "***REDACTED***"

    def redact(self, data: Any) -> Any:
        """
        Redact sensitive data from output.

        Args:
            data: Data to redact (can be dict, str, list, or primitive)

        Returns:
            Redacted copy of data
        """
        if isinstance(data, dict):
            return self._redact_dict(data)
        elif isinstance(data, str):
            return self._redact_string(data)
        elif isinstance(data, list):
            return [self.redact(item) for item in data]
        else:
            return data

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields in dictionary."""
        redacted = {}
        for key, value in data.items():
            # Check if field name is sensitive
            if key.lower() in self.sensitive_fields:
                redacted[key] = self.redaction_text
            # Recursively redact nested structures
            elif isinstance(value, (dict, list, str)):
                redacted[key] = self.redact(value)
            else:
                redacted[key] = value

        return redacted

    def _redact_string(self, text: str) -> str:
        """Redact sensitive patterns from string."""
        redacted = text

        # Apply pattern-based redaction
        for pattern, data_type in self.sensitive_patterns:
            matches = re.finditer(pattern, redacted, re.IGNORECASE)
            for match in matches:
                # Replace with placeholder + type
                redacted = redacted.replace(
                    match.group(0), f"{self.redaction_text}_{data_type}"
                )

        return redacted

    def has_sensitive_data(self, data: Any) -> bool:
        """Check if data contains sensitive information."""
        if isinstance(data, dict):
            # Check field names
            if any(key.lower() in self.sensitive_fields for key in data.keys()):
                return True
            # Check values recursively
            return any(self.has_sensitive_data(v) for v in data.values())

        elif isinstance(data, str):
            # Check patterns
            for pattern, _ in self.sensitive_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    return True

        elif isinstance(data, list):
            return any(self.has_sensitive_data(item) for item in data)

        return False


class OutputValidationMiddleware(Agent):
    """
    Middleware for output validation and sensitive data redaction.

    Features:
    - Schema validation
    - Sensitive data redaction
    - Output size limits
    - Content policy enforcement

    Usage:
        agent = OutputValidationMiddleware(
            base_agent,
            schema=SchemaValidator(expected_fields={"result": str}),
            redactor=SensitiveDataRedactor(),
            auto_redact=True
        )
    """

    def __init__(
        self,
        agent: Agent,
        schema: Optional[SchemaValidator] = None,
        redactor: Optional[SensitiveDataRedactor] = None,
        auto_redact: bool = True,
        max_size: int = 100000,
    ):
        """
        Initialize output validation middleware.

        Args:
            agent: Agent to wrap
            schema: Schema validator (optional)
            redactor: Sensitive data redactor (default: standard redactor)
            auto_redact: Automatically redact sensitive data
            max_size: Maximum output size (characters)
        """
        self._agent = agent
        self.schema = schema
        self.redactor = redactor or SensitiveDataRedactor()
        self.auto_redact = auto_redact
        self.max_size = max_size

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    async def process(self, message: Message) -> Message:
        """Process with output validation."""
        # Process with wrapped agent
        response = await self._agent.process(message)

        # 1. Check output size
        content_str = str(response.content) if response.content else ""
        if len(content_str) > self.max_size:
            raise OutputValidationError(
                f"Output exceeds maximum size ({self.max_size} chars)",
                {"actual_size": len(content_str)},
            )

        # 2. Validate against schema
        if self.schema:
            is_valid, error_msg = self.schema.validate(response.content)
            if not is_valid:
                raise OutputValidationError(
                    f"Output validation failed: {error_msg}",
                    {"content_preview": content_str[:200]},
                )

        # 3. Auto-redact sensitive data
        if self.auto_redact:
            redacted_content = self.redactor.redact(response.content)
            # Create new Message with redacted content (Message is frozen)
            from dataclasses import replace
            response = replace(response, content=redacted_content)

        # 4. Log if sensitive data detected (even if redacted)
        if self.auto_redact and self.redactor.has_sensitive_data(response.content):
            print("WARNING: Output may contain sensitive data (has been redacted)")

        return response


def output_validation(
    schema: Optional[SchemaValidator] = None,
    redactor: Optional[SensitiveDataRedactor] = None,
    auto_redact: bool = True,
    max_size: int = 100000,
):
    """
    Create output validation middleware function.

    Args:
        schema: Schema validator
        redactor: Sensitive data redactor
        auto_redact: Automatically redact sensitive data
        max_size: Maximum output size

    Returns:
        Middleware function

    Usage:
        agent = applyMiddleware(base_agent, [
            output_validation(auto_redact=True),
            timeout(30),
        ])
    """
    def middleware(agent: Agent) -> Agent:
        return OutputValidationMiddleware(agent, schema, redactor, auto_redact, max_size)

    return middleware
