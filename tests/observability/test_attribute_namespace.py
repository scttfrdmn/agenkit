"""
#783: an attribute-namespace test that catches the first divergence between
docs/OTEL_CONVENTION.md and what TracingMiddleware actually emits.

Per the #715 thread's own description of the idea ("an attribute is either
gen_ai.* or quarry.*, an unlisted key is a bug" — stolen here as "gen_ai.* or
agenkit.*, plus the grandfathered pre-GenAI keys").
"""

import re
from pathlib import Path

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from agenkit.interfaces import (
    METADATA_KEY_COST_MICRO_UNITS,
    METADATA_KEY_GEN_AI_SYSTEM,
    METADATA_KEY_REQUEST_MODEL,
    METADATA_KEY_RESPONSE_MODEL,
    METADATA_KEY_RETRY_COUNT,
    METADATA_KEY_VERIFY_RETRIES,
    Agent,
    Message,
)
from agenkit.observability import TracingMiddleware
from agenkit.reasoning import Verdict, VerificationResult
from tests.otel_helpers import isolated_tracer_provider

# The doc lives at the repo root, three levels up from this test file
# (tests/observability/test_attribute_namespace.py).
_OTEL_CONVENTION_PATH = (
    Path(__file__).resolve().parent.parent.parent / "docs" / "OTEL_CONVENTION.md"
)

# The grandfathered pre-GenAI keys docs/OTEL_CONVENTION.md's "Agent span
# attributes" table permits outside the gen_ai.*/agenkit.* namespaces.
_ALLOWED_EXACT_KEYS = {"agent.name", "message.role", "message.content_length"}
_ALLOWED_KEY_PREFIXES = ("message.metadata.",)

_DOC_KEY_PATTERN = re.compile(r"`([a-zA-Z0-9_.{}]+)`")


def _keys_documented_in_convention() -> set[str]:
    """
    Return every literal attribute-key cell from docs/OTEL_CONVENTION.md's
    tables (the first backtick-quoted token on any `| \\`...\\` | ... |` row).

    Read from disk rather than duplicated inline so this test fails the
    moment the doc and the code disagree, instead of the moment someone
    remembers to update a second hand-maintained list.
    """
    text = _OTEL_CONVENTION_PATH.read_text(encoding="utf-8")
    keys: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        matches = _DOC_KEY_PATTERN.findall(line)
        if not matches:
            continue
        # The key is always the first backtick-quoted token in a table row in
        # this doc's tables (column 1 is "Attribute" in every table this test
        # cares about).
        keys.add(matches[0])
    return keys


def _is_documented(key: str, doc_keys: set[str]) -> bool:
    """Check `key` against doc_keys, expanding `{placeholder}` prefixes like message.metadata.{key}."""
    if key in doc_keys:
        return True
    for doc_key in doc_keys:
        if "{" not in doc_key:
            continue
        prefix = doc_key[: doc_key.index("{")]
        if prefix and key.startswith(prefix):
            return True
    return False


def _is_namespaced_or_grandfathered(key: str) -> bool:
    if key.startswith("gen_ai.") or key.startswith("agenkit."):
        return True
    if key in _ALLOWED_EXACT_KEYS:
        return True
    return any(key.startswith(prefix) for prefix in _ALLOWED_KEY_PREFIXES)


class LLMLikeAgent(Agent):
    """
    Stands in for an agent whose process() wraps an LLM call: it returns a
    response carrying the well-known GenAI metadata keys an adapters.llm
    adapter sets (gen_ai_system, request_model, response_model, usage with
    cache tokens), plus the cost/retry counters, so the test drives a
    representative call through every promotion path #782 added.
    """

    @property
    def name(self) -> str:
        return "llm-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["chat"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content="hello from the model",
            metadata={
                METADATA_KEY_GEN_AI_SYSTEM: "aws.bedrock",
                METADATA_KEY_REQUEST_MODEL: "us.anthropic.claude-sonnet-5",
                METADATA_KEY_RESPONSE_MODEL: "us.anthropic.claude-sonnet-5",
                "usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 50,
                    "total_tokens": 1050,
                    "cache_read_tokens": 900,
                    "cache_creation_tokens": 100,
                },
                METADATA_KEY_COST_MICRO_UNITS: 42,
                METADATA_KEY_RETRY_COUNT: 1,
                METADATA_KEY_VERIFY_RETRIES: 2,
                "plain_string_field": "keep-me",
            },
        )


class SimpleAgent(Agent):
    """Plain agent with no GenAI metadata, for span-name/scope assertions."""

    def __init__(self, name: str = "checkout", response: str = "ok"):
        self._name = name
        self._response = response

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=self._response)


class FailedVerificationAgent(Agent):
    """
    Stands in for a technique that ran a Verifier and got a completed,
    unfavourable verdict — "the check ran and worked; the answer was bad" —
    which docs/OTEL_CONVENTION.md says must leave span status Ok, not Error.

    TracingMiddleware has no built-in verifier-verdict handling: a caller
    that ran a Verifier is expected to set the attribute itself, per the
    doc's own Python example. This agent stands in for that caller.
    """

    @property
    def name(self) -> str:
        return "verifier-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        result = VerificationResult(passed=False, reason="answer did not match expected output")
        assert result.verdict is Verdict.FAILED
        # Completing the check and disliking the answer is not the same claim
        # as the operation failing to complete — so this returns normally,
        # not an exception, regardless of the verdict.
        return Message(role="agent", content="checked, and it was wrong")


@pytest.fixture
def span_exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    with isolated_tracer_provider(provider):
        yield exporter
        provider.force_flush()
        provider.shutdown()


@pytest.mark.asyncio
async def test_every_key_is_genai_or_agenkit_or_grandfathered(span_exporter):
    traced = TracingMiddleware(LLMLikeAgent())
    await traced.process(Message(role="user", content="hi"))

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1

    for key in dict(spans[0].attributes):
        assert key != "trace_context", "trace_context must never appear as a span attribute"
        assert _is_namespaced_or_grandfathered(key), (
            f"attribute key {key!r} is neither gen_ai.*, agenkit.*, "
            "nor a grandfathered pre-GenAI key"
        )


@pytest.mark.asyncio
async def test_every_emitted_key_is_documented(span_exporter):
    traced = TracingMiddleware(LLMLikeAgent())
    await traced.process(Message(role="user", content="hi"))

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1

    doc_keys = _keys_documented_in_convention()
    assert doc_keys, (
        "doc-key parser found nothing in docs/OTEL_CONVENTION.md — "
        "the path or the parser is broken, which would make this test vacuously pass"
    )

    for key in dict(spans[0].attributes):
        assert _is_documented(key, doc_keys), (
            f"attribute key {key!r} was emitted but does not appear in "
            "docs/OTEL_CONVENTION.md's tables"
        )


@pytest.mark.asyncio
async def test_trace_context_never_promoted(span_exporter):
    traced = TracingMiddleware(SimpleAgent())
    message = Message(
        role="user",
        content="test",
        metadata={"trace_context": {"traceparent": "00-abc-def-01"}},
    )
    await traced.process(message)

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    for key in dict(spans[0].attributes):
        assert "trace_context" not in key


@pytest.mark.asyncio
async def test_span_name_and_scope(span_exporter):
    traced = TracingMiddleware(SimpleAgent(name="checkout"))
    await traced.process(Message(role="user", content="hi"))

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "agent.checkout.process"
    assert spans[0].instrumentation_scope.name == "agenkit.observability"


@pytest.mark.asyncio
async def test_failed_verification_is_not_an_error_status(span_exporter):
    """
    A completed check that returns an unfavourable verdict must leave span
    status Ok. Only a gap/timeout — something that did not run to completion
    — should set Error.

    TracingMiddleware itself only looks at whether process() raised; this
    test's real job is proving that a verifier-backed agent which completes
    its check and returns a "failed" verdict as a *successful* process() call
    gets Ok, not Error. If a verifier-backed pattern instead mapped a failed
    verdict to a raised exception, this test would catch it: TracingMiddleware
    would set span status Error, exactly the backwards behavior the doc warns
    about.
    """
    traced = TracingMiddleware(FailedVerificationAgent())
    await traced.process(Message(role="user", content="2+2?"))

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.status_code == StatusCode.OK, (
        "a completed verification that returned Verdict.FAILED must not set Error status"
    )
