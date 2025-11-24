"""
Input validation and prompt injection defense.

Provides protection against:
- Prompt injection attacks
- Malicious inputs
- Content policy violations
- Input size limits
"""

import re
from dataclasses import dataclass, field
from typing import Any

from agenkit import Agent, Message


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


@dataclass
class PromptInjectionDetector:
    """
    Detects potential prompt injection attempts.

    Uses pattern matching and heuristics to identify common prompt injection
    techniques like instruction overrides, jailbreaks, and system prompts.
    """

    # Patterns indicating prompt injection attempts
    dangerous_patterns: list[str] = field(
        default_factory=lambda: [
            r"ignore\s+.*?(previous|all|above|prior).*?instructions?",
            r"disregard\s+.*?(previous|all|above|prior)",
            r"forget\s+.*?(everything|all|previous)",
            r"new\s+instructions?:",
            r"system\s*(prompt|message)?:",
            r"you\s+are\s+now",
            r"act\s+as\s+(if|though)",
            r"pretend\s+(you|to)\s+(are|be)",
            r"roleplay\s+as",
            r"^sudo\s+",
            r"admin\s+mode",
            r"developer\s+mode",
            r"god\s+mode",
            r"jailbreak",
            r"</?\s*system\s*>",
            r"<\|.*?\|>",  # Special tokens
            r"\[INST\]",  # Llama-style tokens
            r"\{system\}",
        ]
    )

    # Suspicious keywords (weighted scoring)
    suspicious_keywords: dict[str, int] = field(
        default_factory=lambda: {
            "ignore": 3,
            "disregard": 3,
            "override": 2,
            "bypass": 3,
            "jailbreak": 5,
            "prompt": 2,
            "injection": 4,
            "system": 2,
            "admin": 2,
            "root": 2,
            "sudo": 3,
            "privilege": 2,
            "instructions": 2,
        }
    )

    # Score threshold for blocking (0-100)
    threshold: int = 8

    def detect(self, text: str) -> tuple[bool, int, list[str]]:
        """
        Detect prompt injection attempts.

        Args:
            text: Input text to analyze

        Returns:
            Tuple of (is_injection, score, matched_patterns)
        """
        text_lower = text.lower()
        score = 0
        matched = []

        # Check dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 10
                matched.append(pattern)

        # Check suspicious keywords
        words = re.findall(r"\w+", text_lower)
        for word in words:
            if word in self.suspicious_keywords:
                score += self.suspicious_keywords[word]

        # Heuristics
        # Multiple special characters (possible encoding/obfuscation)
        special_chars = len(re.findall(r"[<>{}[\]|]", text))
        if special_chars > 5:
            score += 2

        # Very long prompts (possible payload)
        if len(text) > 5000:
            score += 1

        # Repeated instructions
        if len(re.findall(r"(please|must|you (should|will|must))", text_lower)) > 5:
            score += 2

        is_injection = score >= self.threshold

        return is_injection, score, matched

    def is_safe(self, text: str) -> bool:
        """Check if text is safe (no injection detected)."""
        is_injection, _, _ = self.detect(text)
        return not is_injection


@dataclass
class ContentFilter:
    """
    Filters content based on policies.

    Supports:
    - Banned words/phrases
    - PII detection (basic)
    - Size limits
    - Format validation
    """

    # Banned words/phrases
    banned_words: set[str] = field(default_factory=set)

    # Maximum content size (characters)
    max_size: int = 10000

    # Minimum content size (characters)
    min_size: int = 1

    # Allowed content types (if specified)
    allowed_content_types: set[str] | None = None

    def validate(self, content: Any) -> tuple[bool, str | None]:
        """
        Validate content against policies.

        Args:
            content: Content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Convert to string for validation
        content_str = str(content) if not isinstance(content, str) else content

        # Size checks
        if len(content_str) > self.max_size:
            return False, f"Content exceeds maximum size ({self.max_size} chars)"

        if len(content_str) < self.min_size:
            return False, f"Content below minimum size ({self.min_size} chars)"

        # Banned words
        content_lower = content_str.lower()
        for word in self.banned_words:
            if word.lower() in content_lower:
                return False, f"Content contains banned word: {word}"

        # Basic PII detection (simple patterns)
        pii_patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "Social Security Number"),
            (r"\b\d{16}\b", "Credit Card Number"),
            (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "Email Address"),
        ]

        for pattern, pii_type in pii_patterns:
            if re.search(pattern, content_str, re.IGNORECASE):
                return False, f"Content may contain {pii_type}"

        return True, None

    def is_safe(self, content: Any) -> bool:
        """Check if content is safe."""
        is_valid, _ = self.validate(content)
        return is_valid


class InputValidationMiddleware(Agent):
    """
    Middleware for input validation and prompt injection defense.

    Features:
    - Prompt injection detection
    - Content filtering
    - Input sanitization
    - Size limits

    Usage:
        agent = InputValidationMiddleware(
            base_agent,
            detector=PromptInjectionDetector(threshold=15),
            content_filter=ContentFilter(max_size=5000)
        )
    """

    def __init__(
        self,
        agent: Agent,
        detector: PromptInjectionDetector | None = None,
        content_filter: ContentFilter | None = None,
        strict: bool = True,
    ):
        """
        Initialize input validation middleware.

        Args:
            agent: Agent to wrap
            detector: Prompt injection detector (default: standard detector)
            content_filter: Content filter (default: basic filter)
            strict: If True, block on validation failure. If False, log warning only.
        """
        self._agent = agent
        self.detector = detector or PromptInjectionDetector()
        self.content_filter = content_filter or ContentFilter()
        self.strict = strict

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    async def process(self, message: Message) -> Message:
        """Process with input validation."""
        # Validate message content
        content_str = str(message.content) if message.content else ""

        # 1. Check for prompt injection
        is_injection, score, matched = self.detector.detect(content_str)
        if is_injection:
            error_msg = (
                f"Potential prompt injection detected (score: {score}, patterns: {len(matched)})"
            )
            if self.strict:
                raise ValidationError(
                    error_msg,
                    {
                        "score": score,
                        "matched_patterns": matched[:3],  # Show first 3
                        "content_preview": content_str[:100],
                    },
                )
            # Non-strict mode: log warning and continue
            print(f"WARNING: {error_msg}")

        # 2. Check content filter
        is_valid, error_msg = self.content_filter.validate(message.content)
        if not is_valid:
            if self.strict:
                raise ValidationError(
                    f"Content validation failed: {error_msg}",
                    {"content_preview": content_str[:100]},
                )
            print(f"WARNING: Content validation failed: {error_msg}")

        # 3. Process with wrapped agent
        return await self._agent.process(message)


def input_validation(
    detector: PromptInjectionDetector | None = None,
    content_filter: ContentFilter | None = None,
    strict: bool = True,
):
    """
    Create input validation middleware function.

    Args:
        detector: Prompt injection detector
        content_filter: Content filter
        strict: Strict mode (block on failure)

    Returns:
        Middleware function

    Usage:
        agent = applyMiddleware(base_agent, [
            input_validation(strict=True),
            retry(),
        ])
    """

    def middleware(agent: Agent) -> Agent:
        return InputValidationMiddleware(agent, detector, content_filter, strict)

    return middleware
