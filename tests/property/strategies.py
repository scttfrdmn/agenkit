"""
Hypothesis Strategies for Property-Based Testing

Defines reusable strategies for generating test data.
"""
from hypothesis import strategies as st
from agenkit.interfaces import Message


# Basic data strategies
content_strategy = st.text(min_size=0, max_size=1000)
short_content_strategy = st.text(min_size=1, max_size=100)
role_strategy = st.sampled_from(["user", "agent", "system"])

# Numeric strategies
positive_int_strategy = st.integers(min_value=1, max_value=1000)
small_positive_int_strategy = st.integers(min_value=1, max_value=10)
probability_strategy = st.floats(min_value=0.0, max_value=1.0)
duration_ms_strategy = st.integers(min_value=1, max_value=5000)
ttl_strategy = st.integers(min_value=1, max_value=3600)  # 1s to 1 hour

# Metadata strategies
metadata_value_strategy = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-1000, max_value=1000),
    st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    st.text(min_size=0, max_size=100),
)

metadata_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
    values=metadata_value_strategy,
    min_size=0,
    max_size=10
)

# Message strategy
@st.composite
def message_strategy(draw):
    """Generate a Message with random content and metadata."""
    role = draw(role_strategy)
    content = draw(content_strategy)
    metadata = draw(metadata_strategy)

    return Message(
        role=role,
        content=content,
        metadata=metadata if metadata else None
    )

# List of messages strategy
messages_strategy = st.lists(message_strategy(), min_size=1, max_size=100)
small_messages_strategy = st.lists(message_strategy(), min_size=1, max_size=10)

# Cache configuration strategies
cache_config_strategy = st.fixed_dictionaries({
    "max_cache_size": positive_int_strategy,
    "default_ttl": ttl_strategy,
})

# Circuit breaker configuration strategies
circuit_breaker_config_strategy = st.fixed_dictionaries({
    "failure_threshold": st.integers(min_value=1, max_value=10),
    "success_threshold": st.integers(min_value=1, max_value=10),
    "recovery_timeout": st.floats(min_value=0.1, max_value=5.0),
})

# Retry configuration strategies
retry_config_strategy = st.fixed_dictionaries({
    "max_retries": st.integers(min_value=1, max_value=10),
    "backoff_base": st.floats(min_value=0.01, max_value=1.0),
    "max_delay": st.floats(min_value=1.0, max_value=10.0),
})

# Rate limiter configuration strategies
rate_limiter_config_strategy = st.fixed_dictionaries({
    "rate": st.floats(min_value=1.0, max_value=100.0),  # requests per second
    "burst_capacity": st.integers(min_value=1, max_value=100),
})

# Batching configuration strategies
batching_config_strategy = st.fixed_dictionaries({
    "max_batch_size": st.integers(min_value=1, max_value=100),
    "max_wait_time": st.floats(min_value=0.01, max_value=1.0),
})

# Timeout configuration strategies
timeout_config_strategy = st.fixed_dictionaries({
    "timeout": st.floats(min_value=0.1, max_value=5.0),
})
