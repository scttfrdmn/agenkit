"""
Tests for agenkit.interfaces.Usage / usage_from_message (#664).

Mirrors agenkit-go/agenkit/usage_test.go so the two languages agree on the
normalization behavior. The two shapes below are the two real ones #664
was filed about: Bedrock's usage map stores plain ints in Python (unlike Go's
int32 via aws.ToInt32 — but the Python Bedrock adapter builds its usage dict
straight from boto3's JSON-decoded response, so it's a plain int in this
language already), and the native Anthropic adapter uses different key names
(input_tokens/output_tokens) than everyone else (prompt_tokens/completion_tokens).
"""

from agenkit.interfaces import Message, Usage, usage_from_message


def test_usage_from_message_nil_message():
    usage, ok = usage_from_message(None)
    assert ok is False
    assert usage == Usage()


def test_usage_from_message_no_usage_metadata():
    msg = Message(role="agent", content="hi")
    _, ok = usage_from_message(msg)
    assert ok is False


def test_usage_from_message_openai_style_prompt_completion():
    msg = Message(
        role="agent",
        content="hi",
        metadata={
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }
        },
    )
    usage, ok = usage_from_message(msg)
    assert ok is True
    assert usage == Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)


def test_usage_from_message_bedrock_style():
    """Bedrock's usage dict (agenkit/adapters/llm/bedrock.py), plain ints from a JSON-decoded boto3 response."""
    msg = Message(
        role="agent",
        content="hi",
        metadata={
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 50,
                "total_tokens": 1050,
            }
        },
    )
    usage, ok = usage_from_message(msg)
    assert ok is True
    assert usage == Usage(prompt_tokens=1000, completion_tokens=50, total_tokens=1050)


def test_usage_from_message_anthropic_style_input_output_keys():
    """The native Anthropic adapter uses input_tokens/output_tokens, not prompt_tokens/completion_tokens."""
    msg = Message(
        role="agent",
        content="hi",
        metadata={"usage": {"input_tokens": 30, "output_tokens": 7}},
    )
    usage, ok = usage_from_message(msg)
    assert ok is True
    # total is derived from prompt+completion when absent
    assert usage == Usage(prompt_tokens=30, completion_tokens=7, total_tokens=37)


def test_usage_from_message_float_values():
    """Values that round-tripped through JSON (e.g. a serialized-then-deserialized metadata dict) come back as floats."""
    msg = Message(
        role="agent",
        content="hi",
        metadata={"usage": {"prompt_tokens": 8.0, "completion_tokens": 2.0}},
    )
    usage, ok = usage_from_message(msg)
    assert ok is True
    assert usage == Usage(prompt_tokens=8, completion_tokens=2, total_tokens=10)


def test_usage_from_message_cache_tokens():
    msg = Message(
        role="agent",
        content="hi",
        metadata={
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 50,
                "total_tokens": 1050,
                "cache_read_tokens": 900,
                "cache_creation_tokens": 100,
            }
        },
    )
    usage, ok = usage_from_message(msg)
    assert ok is True
    assert usage == Usage(
        prompt_tokens=1000,
        completion_tokens=50,
        total_tokens=1050,
        cache_read_tokens=900,
        cache_creation_tokens=100,
    )


def test_usage_from_message_raw_provider_cache_key_aliases():
    """Anthropic's raw API key names (cache_read_input_tokens/cache_creation_input_tokens) are also recognized."""
    msg = Message(
        role="agent",
        content="hi",
        metadata={
            "usage": {
                "input_tokens": 20,
                "output_tokens": 4,
                "cache_read_input_tokens": 15,
                "cache_creation_input_tokens": 5,
            }
        },
    )
    usage, ok = usage_from_message(msg)
    assert ok is True
    assert usage == Usage(
        prompt_tokens=20,
        completion_tokens=4,
        total_tokens=24,
        cache_read_tokens=15,
        cache_creation_tokens=5,
    )
