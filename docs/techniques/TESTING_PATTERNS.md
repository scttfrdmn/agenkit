# Testing Patterns for AI Agents

AI agents present unique testing challenges compared to deterministic software. Outputs are
probabilistic, behavior depends on external LLM calls, and correctness is often subjective.
This guide covers five proven patterns for building a rigorous, practical test suite around
agenkit agents.

---

## Table of Contents

1. [AI Judges for Automated Evaluation](#1-ai-judges-for-automated-evaluation)
2. [Shadow Mode Testing](#2-shadow-mode-testing)
3. [Regression Testing with LLM Trace Comparison](#3-regression-testing-with-llm-trace-comparison)
4. [Property-Based Testing](#4-property-based-testing)
5. [Chaos Testing for Resilience](#5-chaos-testing-for-resilience)

---

## 1. AI Judges for Automated Evaluation

Manual review does not scale. An AI judge — another LLM invocation — evaluates whether an
agent's output meets a rubric and returns structured feedback. This is more reliable than
simple string matching for open-ended responses, and far faster than human review.

### The JudgeAgent Pattern

```python
import json
import asyncio
from dataclasses import dataclass
from typing import Any

from agenkit import Agent, Message


@dataclass
class JudgementResult:
    """Structured output from the judge."""

    score: int           # 1-5
    passed: bool         # score >= threshold
    reasoning: str       # why this score was given
    criteria_met: list[str]
    criteria_missed: list[str]


class JudgeAgent:
    """
    Uses an LLM to evaluate another agent's output against a rubric.

    The judge receives the original input, the agent's output, and a set
    of criteria. It returns a structured score and reasoning that can be
    used in automated test assertions.

    Usage:
        judge = JudgeAgent(llm_agent, threshold=3)
        result = await judge.evaluate(
            input_message=user_msg,
            output_message=agent_response,
            criteria=[
                "Response directly addresses the user's question",
                "No hallucinated facts",
                "Tone is professional and helpful",
            ],
        )
        assert result.passed, f"Judge failed: {result.reasoning}"
    """

    JUDGE_PROMPT = """You are an impartial evaluator of AI assistant responses.

You will be given:
- The user's original message
- The assistant's response
- A list of evaluation criteria

Score the response from 1 to 5:
  1 = Completely fails to meet criteria
  2 = Meets some criteria but has major gaps
  3 = Meets most criteria with minor issues
  4 = Meets all criteria well
  5 = Exceptional response, exceeds all criteria

Respond with valid JSON only, in this exact format:
{{
  "score": <integer 1-5>,
  "criteria_met": [<list of criteria strings that were satisfied>],
  "criteria_missed": [<list of criteria strings that were not satisfied>],
  "reasoning": "<concise explanation of the score>"
}}

--- USER MESSAGE ---
{user_message}

--- ASSISTANT RESPONSE ---
{agent_response}

--- CRITERIA ---
{criteria_list}
"""

    def __init__(self, judge_llm: Agent, threshold: int = 3):
        """
        Args:
            judge_llm: An agenkit Agent that wraps an LLM for scoring.
            threshold: Minimum score (inclusive) for a response to pass.
        """
        if not (1 <= threshold <= 5):
            raise ValueError("threshold must be between 1 and 5")
        self._judge = judge_llm
        self.threshold = threshold

    async def evaluate(
        self,
        input_message: Message,
        output_message: Message,
        criteria: list[str],
    ) -> JudgementResult:
        """
        Evaluate an agent's response against the given criteria.

        Args:
            input_message: The original user message sent to the agent.
            output_message: The agent's response message.
            criteria: List of plain-English criteria the response should meet.

        Returns:
            JudgementResult with score, pass/fail, and reasoning.

        Raises:
            ValueError: If the judge LLM returns malformed JSON.
        """
        criteria_list = "\n".join(f"- {c}" for c in criteria)
        prompt = self.JUDGE_PROMPT.format(
            user_message=str(input_message.content),
            agent_response=str(output_message.content),
            criteria_list=criteria_list,
        )

        judge_input = Message(role="user", content=prompt)
        judge_response = await self._judge.process(judge_input)

        # Parse structured JSON response
        raw = str(judge_response.content).strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"judge returned non-JSON response: {judge_response.content!r}"
            ) from exc

        score = int(data["score"])
        return JudgementResult(
            score=score,
            passed=score >= self.threshold,
            reasoning=data.get("reasoning", ""),
            criteria_met=data.get("criteria_met", []),
            criteria_missed=data.get("criteria_missed", []),
        )

    async def evaluate_batch(
        self,
        test_cases: list[tuple[Message, Message]],
        criteria: list[str],
        concurrency: int = 5,
    ) -> list[JudgementResult]:
        """
        Evaluate multiple (input, output) pairs concurrently.

        Args:
            test_cases: List of (input_message, output_message) pairs.
            criteria: Shared evaluation criteria for all cases.
            concurrency: Maximum simultaneous judge calls.

        Returns:
            List of JudgementResult, one per test case.
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def evaluate_one(pair: tuple[Message, Message]) -> JudgementResult:
            async with semaphore:
                return await self.evaluate(pair[0], pair[1], criteria)

        return await asyncio.gather(*[evaluate_one(tc) for tc in test_cases])
```

### pytest Fixture for Automatic Evaluation

Integrate the judge into your pytest suite with a fixture so any test can assert on quality
scores without boilerplate.

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from agenkit import Message
from agenkit.adapters.openai import OpenAIAgent   # your LLM adapter

from tests.helpers import JudgeAgent


@pytest.fixture(scope="session")
def judge_llm():
    """Session-scoped LLM for judging — reuse across all tests."""
    return OpenAIAgent(model="gpt-4o-mini", temperature=0)


@pytest.fixture
def judge(judge_llm):
    """Per-test judge with default pass threshold of 3/5."""
    return JudgeAgent(judge_llm, threshold=3)


@pytest.fixture
def strict_judge(judge_llm):
    """Stricter judge requiring score >= 4."""
    return JudgeAgent(judge_llm, threshold=4)


# tests/test_customer_agent.py
import pytest
from agenkit import Message


@pytest.mark.asyncio
async def test_customer_agent_answers_product_questions(customer_agent, judge):
    user_msg = Message(role="user", content="What is your return policy?")
    response = await customer_agent.process(user_msg)

    result = await judge.evaluate(
        input_message=user_msg,
        output_message=response,
        criteria=[
            "Directly answers the question about return policy",
            "Does not make up specific timeframes not in the prompt",
            "Offers to provide more information or escalate",
        ],
    )

    assert result.passed, (
        f"Score {result.score}/5 — {result.reasoning}\n"
        f"Missed: {result.criteria_missed}"
    )


@pytest.mark.asyncio
async def test_agent_handles_ambiguous_requests(customer_agent, judge):
    user_msg = Message(role="user", content="I need help with my thing")
    response = await customer_agent.process(user_msg)

    result = await judge.evaluate(
        input_message=user_msg,
        output_message=response,
        criteria=[
            "Asks a clarifying question to understand the user's need",
            "Does not assume or fabricate context",
            "Response is concise (under 100 words)",
        ],
    )

    assert result.passed, f"Score {result.score}/5 — {result.reasoning}"
```

---

## 2. Shadow Mode Testing

Shadow mode runs a new (candidate) agent in parallel with the production agent. Both receive
the same input, but only the production agent's response is returned to the caller. The
candidate's output is logged for comparison. This is the lowest-risk way to validate a new
model or prompt change in production conditions before cutting over.

### ShadowAgent Wrapper

```python
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agenkit import Agent, Message


logger = logging.getLogger(__name__)


@dataclass
class ShadowComparison:
    """Record of one shadow mode comparison."""

    timestamp: datetime
    input_content: Any
    production_content: Any
    candidate_content: Any
    production_latency_ms: float
    candidate_latency_ms: float
    candidate_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def candidate_succeeded(self) -> bool:
        return self.candidate_error is None

    @property
    def outputs_match(self) -> bool:
        """Exact string equality — use a fuzzy matcher for semantic comparison."""
        return str(self.production_content) == str(self.candidate_content)


class ShadowAgent(Agent):
    """
    Wraps a production agent and runs a candidate agent in shadow mode.

    The production agent's response is always returned. The candidate
    runs concurrently but its result is only logged, never returned.

    Usage:
        shadow = ShadowAgent(
            production=prod_agent,
            candidate=new_agent,
            on_comparison=my_logging_callback,
        )
        # Callers interact with `shadow` exactly like `prod_agent`.
        response = await shadow.process(message)
    """

    def __init__(
        self,
        production: Agent,
        candidate: Agent,
        on_comparison: Any | None = None,
        log_mismatches: bool = True,
    ):
        """
        Args:
            production: The live agent whose response is returned.
            candidate: The new agent running in shadow.
            on_comparison: Optional async callback(ShadowComparison) for
                           custom logging / metrics ingestion.
            log_mismatches: If True, log when outputs differ.
        """
        self._production = production
        self._candidate = candidate
        self._on_comparison = on_comparison
        self._log_mismatches = log_mismatches
        self._comparisons: list[ShadowComparison] = []

    @property
    def name(self) -> str:
        return self._production.name

    @property
    def capabilities(self) -> list[str]:
        return self._production.capabilities

    async def process(self, message: Message) -> Message:
        """
        Run both agents concurrently; return only the production result.
        """
        prod_task = asyncio.create_task(self._timed_process(self._production, message))
        cand_task = asyncio.create_task(self._timed_process(self._candidate, message))

        # Wait for both; production failure propagates, candidate failure is absorbed
        prod_result, cand_result = await asyncio.gather(
            prod_task,
            cand_task,
            return_exceptions=True,
        )

        # Production failures are real errors — re-raise
        if isinstance(prod_result, Exception):
            raise prod_result

        prod_response, prod_latency = prod_result

        # Build comparison record regardless of candidate outcome
        if isinstance(cand_result, Exception):
            comparison = ShadowComparison(
                timestamp=datetime.now(timezone.utc),
                input_content=message.content,
                production_content=prod_response.content,
                candidate_content=None,
                production_latency_ms=prod_latency,
                candidate_latency_ms=0.0,
                candidate_error=str(cand_result),
            )
        else:
            cand_response, cand_latency = cand_result
            comparison = ShadowComparison(
                timestamp=datetime.now(timezone.utc),
                input_content=message.content,
                production_content=prod_response.content,
                candidate_content=cand_response.content,
                production_latency_ms=prod_latency,
                candidate_latency_ms=cand_latency,
            )

            if self._log_mismatches and not comparison.outputs_match:
                logger.info(
                    "shadow mismatch | prod=%r | candidate=%r",
                    str(prod_response.content)[:120],
                    str(cand_response.content)[:120],
                )

        self._comparisons.append(comparison)

        if self._on_comparison is not None:
            # Fire-and-forget; don't block the caller
            asyncio.create_task(self._on_comparison(comparison))

        return prod_response

    async def _timed_process(
        self, agent: Agent, message: Message
    ) -> tuple[Message, float]:
        start = time.perf_counter()
        response = await agent.process(message)
        latency = (time.perf_counter() - start) * 1000
        return response, latency

    def get_comparisons(self) -> list[ShadowComparison]:
        """Return all recorded comparisons (for test assertions)."""
        return list(self._comparisons)

    def mismatch_rate(self) -> float:
        """Fraction of comparisons where outputs differed."""
        succeeded = [c for c in self._comparisons if c.candidate_succeeded]
        if not succeeded:
            return 0.0
        mismatches = sum(1 for c in succeeded if not c.outputs_match)
        return mismatches / len(succeeded)
```

### Testing the Shadow Agent

```python
# tests/test_shadow_mode.py
import pytest
from agenkit import Message

from tests.helpers import ShadowAgent


@pytest.mark.asyncio
async def test_candidate_does_not_change_production_output(
    prod_agent, candidate_agent
):
    shadow = ShadowAgent(production=prod_agent, candidate=candidate_agent)
    msg = Message(role="user", content="Summarize quantum computing in one sentence.")

    response = await shadow.process(msg)

    # Caller always receives the production response
    prod_response = await prod_agent.process(msg)
    assert response.content == prod_response.content


@pytest.mark.asyncio
async def test_shadow_records_comparison(prod_agent, candidate_agent):
    shadow = ShadowAgent(production=prod_agent, candidate=candidate_agent)
    msg = Message(role="user", content="What is 2 + 2?")

    await shadow.process(msg)

    comparisons = shadow.get_comparisons()
    assert len(comparisons) == 1
    assert comparisons[0].candidate_succeeded
    assert comparisons[0].production_content is not None


@pytest.mark.asyncio
async def test_candidate_error_does_not_affect_caller(prod_agent, always_failing_agent):
    shadow = ShadowAgent(production=prod_agent, candidate=always_failing_agent)
    msg = Message(role="user", content="Hello")

    # Should not raise despite candidate failing
    response = await shadow.process(msg)
    assert response.role == "assistant"

    comparisons = shadow.get_comparisons()
    assert comparisons[0].candidate_error is not None
```

---

## 3. Regression Testing with LLM Trace Comparison

Record the complete execution trace of an agent (input, output, intermediate steps,
tool calls) and store it as a golden reference. On each test run, compare the current
trace against the golden to detect behavioral drift. This catches silent regressions
that simple output comparison misses — for example, an agent that reaches the same final
answer through a different reasoning path.

### TraceRecorder

```python
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agenkit import Agent, Message


@dataclass
class TraceStep:
    step_index: int
    step_type: str        # "input", "output", "tool_call", "tool_result"
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentTrace:
    trace_id: str
    agent_name: str
    input_content: Any
    output_content: Any
    steps: list[TraceStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def content_hash(self) -> str:
        """Stable hash of the trace content for quick equality checks."""
        payload = json.dumps(
            {
                "input": str(self.input_content),
                "output": str(self.output_content),
                "steps": [
                    {"type": s.step_type, "content": str(s.content)}
                    for s in self.steps
                ],
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "input_content": str(self.input_content),
            "output_content": str(self.output_content),
            "steps": [
                {
                    "step_index": s.step_index,
                    "step_type": s.step_type,
                    "content": str(s.content),
                    "metadata": s.metadata,
                }
                for s in self.steps
            ],
            "metadata": self.metadata,
            "recorded_at": self.recorded_at.isoformat(),
            "content_hash": self.content_hash(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentTrace":
        steps = [
            TraceStep(
                step_index=s["step_index"],
                step_type=s["step_type"],
                content=s["content"],
                metadata=s.get("metadata", {}),
            )
            for s in data.get("steps", [])
        ]
        return cls(
            trace_id=data["trace_id"],
            agent_name=data["agent_name"],
            input_content=data["input_content"],
            output_content=data["output_content"],
            steps=steps,
            metadata=data.get("metadata", {}),
        )


class TracingAgent(Agent):
    """
    Wraps an agent and records a detailed execution trace.

    If the wrapped agent emits tool calls via metadata, those are
    captured as TraceStep entries. Extend _extract_steps() for
    agent-specific trace structure.
    """

    def __init__(self, agent: Agent):
        self._agent = agent
        self._traces: list[AgentTrace] = []

    @property
    def name(self) -> str:
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    async def process(self, message: Message) -> Message:
        import uuid

        trace_id = str(uuid.uuid4())[:8]
        steps: list[TraceStep] = [
            TraceStep(step_index=0, step_type="input", content=message.content)
        ]

        response = await self._agent.process(message)

        # Extract intermediate steps from response metadata if present
        intermediate = response.metadata.get("steps", [])
        for i, step in enumerate(intermediate, start=1):
            steps.append(
                TraceStep(
                    step_index=i,
                    step_type=step.get("type", "intermediate"),
                    content=step.get("content", ""),
                    metadata=step.get("metadata", {}),
                )
            )

        steps.append(
            TraceStep(
                step_index=len(steps),
                step_type="output",
                content=response.content,
            )
        )

        trace = AgentTrace(
            trace_id=trace_id,
            agent_name=self.name,
            input_content=message.content,
            output_content=response.content,
            steps=steps,
        )
        self._traces.append(trace)
        return response

    def latest_trace(self) -> AgentTrace | None:
        return self._traces[-1] if self._traces else None

    def all_traces(self) -> list[AgentTrace]:
        return list(self._traces)


class GoldenTraceStore:
    """
    Persists and retrieves golden traces for regression comparison.

    Golden traces are stored as JSON files under the given directory,
    keyed by a test name. When a trace does not exist, the first
    recorded trace is automatically promoted to golden.
    """

    def __init__(self, store_dir: str | Path):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.json"

    def save(self, key: str, trace: AgentTrace) -> None:
        self._path(key).write_text(
            json.dumps(trace.to_dict(), indent=2), encoding="utf-8"
        )

    def load(self, key: str) -> AgentTrace | None:
        path = self._path(key)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return AgentTrace.from_dict(data)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


@dataclass
class TraceDiff:
    key: str
    golden_hash: str
    current_hash: str
    output_changed: bool
    step_count_changed: bool
    golden_step_count: int
    current_step_count: int
    changed_steps: list[int] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return self.output_changed or self.step_count_changed or bool(self.changed_steps)


class TraceComparator:
    """
    Compares a current trace against a stored golden trace.

    Detects:
    - Output content changes (final answer drift)
    - Step count changes (reasoning path length)
    - Individual step content changes (intermediate reasoning drift)
    """

    def compare(self, golden: AgentTrace, current: AgentTrace) -> TraceDiff:
        golden_steps = {s.step_index: s for s in golden.steps}
        current_steps = {s.step_index: s for s in current.steps}

        changed: list[int] = []
        for idx in set(golden_steps) & set(current_steps):
            if str(golden_steps[idx].content) != str(current_steps[idx].content):
                changed.append(idx)

        return TraceDiff(
            key=golden.trace_id,
            golden_hash=golden.content_hash(),
            current_hash=current.content_hash(),
            output_changed=str(golden.output_content) != str(current.output_content),
            step_count_changed=len(golden.steps) != len(current.steps),
            golden_step_count=len(golden.steps),
            current_step_count=len(current.steps),
            changed_steps=sorted(changed),
        )
```

### Using Traces in Tests

```python
# tests/test_regression.py
import pytest
from pathlib import Path
from agenkit import Message

from tests.helpers import TracingAgent, GoldenTraceStore, TraceComparator


GOLDEN_DIR = Path(__file__).parent / "golden_traces"


@pytest.fixture(scope="session")
def golden_store():
    return GoldenTraceStore(GOLDEN_DIR)


@pytest.fixture
def comparator():
    return TraceComparator()


@pytest.mark.asyncio
async def test_summarization_trace_regression(my_agent, golden_store, comparator):
    """Detects drift in summarization reasoning path."""
    tracing = TracingAgent(my_agent)
    msg = Message(role="user", content="Summarize the water cycle in 3 sentences.")

    await tracing.process(msg)
    current_trace = tracing.latest_trace()

    key = "summarize_water_cycle"
    if not golden_store.exists(key):
        # First run: promote current trace to golden
        golden_store.save(key, current_trace)
        pytest.skip("golden trace created; re-run to validate regression")

    golden = golden_store.load(key)
    diff = comparator.compare(golden, current_trace)

    assert not diff.output_changed, (
        f"output drifted from golden\n"
        f"  golden:  {golden.output_content!r}\n"
        f"  current: {current_trace.output_content!r}"
    )
    assert not diff.step_count_changed, (
        f"step count changed: {diff.golden_step_count} -> {diff.current_step_count}"
    )
```

---

## 4. Property-Based Testing

Property-based testing generates hundreds of diverse inputs automatically using
[Hypothesis](https://hypothesis.readthedocs.io/). Instead of testing specific examples, you
test invariants — properties that must hold for all valid inputs. This is especially
effective for catching edge cases in input handling and output formatting.

Install the dependency:

```
uv add hypothesis --dev
```

### Core Invariants to Test

```python
# tests/test_properties.py
import asyncio
import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from agenkit import Message


# ---------------------------------------------------------------
# Strategy helpers
# ---------------------------------------------------------------

printable_text = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Po")),
    min_size=1,
    max_size=500,
)

user_messages = printable_text.map(
    lambda content: Message(role="user", content=content)
)


def run(coro):
    """Run async code synchronously inside Hypothesis @given."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------
# Property 1: Response is never empty
# ---------------------------------------------------------------

@given(message=user_messages)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_response_is_never_empty(my_agent, message):
    response = run(my_agent.process(message))
    content_str = str(response.content) if response.content is not None else ""
    assert len(content_str.strip()) > 0, (
        f"agent returned empty response for input: {message.content!r}"
    )


# ---------------------------------------------------------------
# Property 2: Response role is always "assistant"
# ---------------------------------------------------------------

@given(message=user_messages)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_response_role_is_always_assistant(my_agent, message):
    response = run(my_agent.process(message))
    assert response.role == "assistant", (
        f"expected role='assistant', got {response.role!r}"
    )


# ---------------------------------------------------------------
# Property 3: Metadata always contains required keys
# ---------------------------------------------------------------

REQUIRED_METADATA_KEYS = {"session_id", "model"}

@given(message=user_messages)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_metadata_always_has_required_keys(production_agent, message):
    """
    Agents in production should always attach session and model metadata
    so downstream systems can route and audit responses.
    """
    response = run(production_agent.process(message))
    missing = REQUIRED_METADATA_KEYS - set(response.metadata.keys())
    assert not missing, (
        f"response metadata missing required keys: {missing}\n"
        f"  got keys: {set(response.metadata.keys())}"
    )


# ---------------------------------------------------------------
# Property 4: Response latency scales sub-linearly with input length
#             (basic sanity — not a strict SLA)
# ---------------------------------------------------------------

import time

short_messages = st.text(min_size=1, max_size=50).map(
    lambda c: Message(role="user", content=c)
)
long_messages = st.text(min_size=200, max_size=500).map(
    lambda c: Message(role="user", content=c)
)

@given(short=short_messages, long=long_messages)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_latency_does_not_explode_with_longer_inputs(my_agent, short, long):
    start = time.perf_counter()
    run(my_agent.process(short))
    short_latency = time.perf_counter() - start

    start = time.perf_counter()
    run(my_agent.process(long))
    long_latency = time.perf_counter() - start

    # Allow up to 10x longer for a 10x longer input — very loose bound
    input_ratio = len(str(long.content)) / max(len(str(short.content)), 1)
    assert long_latency < short_latency * max(10.0, input_ratio * 2), (
        f"latency grew disproportionately: short={short_latency:.2f}s, "
        f"long={long_latency:.2f}s, input_ratio={input_ratio:.1f}x"
    )


# ---------------------------------------------------------------
# Property 5: Structured output agents always return valid JSON
# ---------------------------------------------------------------

@given(query=printable_text)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_structured_agent_always_returns_valid_json(structured_agent, query):
    """
    Agents that claim to return JSON should always produce parseable output,
    regardless of what the user sends.
    """
    import json

    message = Message(role="user", content=query)
    response = run(structured_agent.process(message))

    try:
        parsed = json.loads(str(response.content))
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"structured agent returned non-JSON for input {query!r}:\n"
            f"  output: {response.content!r}\n"
            f"  error:  {exc}"
        )

    # The parsed result must be a dict (not a bare string or list)
    assert isinstance(parsed, dict), (
        f"expected dict output, got {type(parsed).__name__}: {parsed!r}"
    )
```

### Reproducing Hypothesis Failures

When Hypothesis finds a failure, it prints a `@reproduce_failure` decorator or a minimal
example. Always add these to a dedicated regression file:

```python
# tests/test_hypothesis_regressions.py
# Shrunk examples that once caused failures — kept as permanent regression tests.

import pytest
from agenkit import Message


@pytest.mark.asyncio
async def test_empty_looking_unicode_input_does_not_crash(my_agent):
    """Hypothesis found: zero-width spaces caused empty stripped output."""
    msg = Message(role="user", content="\u200b")
    response = await my_agent.process(msg)
    assert response.content is not None
```

---

## 5. Chaos Testing for Resilience

Chaos testing injects failures — timeouts, rate limits, partial errors — to verify that
your agent handles adverse conditions gracefully and still meets latency and correctness
SLAs. This is critical for production readiness: LLM APIs are unreliable, and agents must
degrade gracefully.

### ChaosAgent Wrapper

```python
import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any

from agenkit import Agent, Message


class RateLimitError(Exception):
    """Simulated 429 Too Many Requests."""


class UpstreamTimeoutError(Exception):
    """Simulated upstream LLM timeout."""


class PartialFailureError(Exception):
    """Simulated partial/truncated response."""


@dataclass
class ChaosConfig:
    """
    Controls the type and probability of injected failures.

    All probabilities are independent and checked in order:
    timeout → rate_limit → partial_failure.
    """

    # Probability of injecting a timeout (0.0–1.0)
    timeout_probability: float = 0.0
    # How long the simulated timeout takes (seconds)
    timeout_duration_s: float = 2.0

    # Probability of injecting a rate limit error
    rate_limit_probability: float = 0.0

    # Probability of returning a truncated/partial response
    partial_failure_probability: float = 0.0

    # Probability of adding random latency
    latency_jitter_probability: float = 0.0
    # Max extra latency to add (seconds)
    max_jitter_s: float = 1.0

    # Random seed for reproducibility in tests
    seed: int | None = None


class ChaosAgent(Agent):
    """
    Wraps an agent and injects configurable failures for resilience testing.

    Use in tests to verify that retry logic, fallback patterns, and circuit
    breakers work correctly under failure conditions.

    Usage:
        config = ChaosConfig(
            timeout_probability=0.3,
            rate_limit_probability=0.2,
        )
        chaos = ChaosAgent(base_agent, config)

        # Now wrap with your retry/fallback middleware
        resilient = FallbackAgent(agents=[chaos, backup_agent])
        response = await resilient.process(message)
    """

    def __init__(self, agent: Agent, config: ChaosConfig):
        self._agent = agent
        self._config = config
        self._rng = random.Random(config.seed)
        self._call_count = 0
        self._failure_count = 0

    @property
    def name(self) -> str:
        return f"chaos({self._agent.name})"

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    async def process(self, message: Message) -> Message:
        self._call_count += 1

        # Inject failures in priority order
        await self._maybe_inject_timeout()
        self._maybe_raise_rate_limit()
        await self._maybe_inject_jitter()

        response = await self._agent.process(message)

        if self._rng.random() < self._config.partial_failure_probability:
            self._failure_count += 1
            # Truncate content to simulate partial response
            content = str(response.content)
            truncate_at = max(1, int(len(content) * self._rng.uniform(0.1, 0.5)))
            from dataclasses import replace
            response = replace(response, content=content[:truncate_at] + "…[TRUNCATED]")

        return response

    async def _maybe_inject_timeout(self) -> None:
        if self._rng.random() < self._config.timeout_probability:
            self._failure_count += 1
            await asyncio.sleep(self._config.timeout_duration_s)
            raise UpstreamTimeoutError(
                f"simulated timeout after {self._config.timeout_duration_s}s"
            )

    def _maybe_raise_rate_limit(self) -> None:
        if self._rng.random() < self._config.rate_limit_probability:
            self._failure_count += 1
            raise RateLimitError("simulated 429 Too Many Requests — retry after 1s")

    async def _maybe_inject_jitter(self) -> None:
        if self._rng.random() < self._config.latency_jitter_probability:
            jitter = self._rng.uniform(0, self._config.max_jitter_s)
            await asyncio.sleep(jitter)

    @property
    def failure_rate(self) -> float:
        if self._call_count == 0:
            return 0.0
        return self._failure_count / self._call_count

    @property
    def call_count(self) -> int:
        return self._call_count
```

### Resilience Tests

```python
# tests/test_chaos.py
import asyncio
import pytest
from agenkit import Agent, Message, FallbackAgent

from tests.helpers import ChaosAgent, ChaosConfig, RateLimitError, UpstreamTimeoutError


SLA_LATENCY_S = 5.0   # Maximum acceptable wall-clock time under chaos
SAMPLE_SIZE = 20       # How many requests to send in load tests


@pytest.mark.asyncio
async def test_fallback_activates_on_timeout(primary_agent, backup_agent):
    """FallbackAgent should transparently switch to backup when primary times out."""
    chaos_config = ChaosConfig(timeout_probability=1.0, timeout_duration_s=0.1)
    chaotic = ChaosAgent(primary_agent, chaos_config)

    fallback = FallbackAgent(agents=[chaotic, backup_agent])
    msg = Message(role="user", content="What is 1 + 1?")

    response = await fallback.process(msg)

    assert response is not None
    assert response.role == "assistant"


@pytest.mark.asyncio
async def test_agent_meets_sla_under_30_percent_timeout_rate(my_agent, backup_agent):
    """
    Under 30% timeout injection, end-to-end latency must stay under SLA.
    Uses FallbackAgent to demonstrate the pattern.
    """
    chaos_config = ChaosConfig(
        timeout_probability=0.3,
        timeout_duration_s=0.05,
        seed=42,
    )
    chaotic = ChaosAgent(my_agent, chaos_config)
    resilient = FallbackAgent(agents=[chaotic, backup_agent])

    msg = Message(role="user", content="Hello")
    latencies: list[float] = []

    for _ in range(SAMPLE_SIZE):
        start = asyncio.get_event_loop().time()
        response = await resilient.process(msg)
        latencies.append(asyncio.get_event_loop().time() - start)
        assert response is not None

    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < SLA_LATENCY_S, (
        f"p95 latency {p95:.2f}s exceeds SLA of {SLA_LATENCY_S}s under 30% timeout rate"
    )


@pytest.mark.asyncio
async def test_agent_handles_rate_limit_with_retry(my_agent):
    """Agent wrapped with retry middleware should recover from rate limit errors."""
    from agenkit.middleware.retry import RetryMiddleware  # adjust import to your setup

    chaos_config = ChaosConfig(rate_limit_probability=0.5, seed=99)
    chaotic = ChaosAgent(my_agent, chaos_config)
    retrying = RetryMiddleware(chaotic, max_attempts=5, backoff_s=0.01)

    msg = Message(role="user", content="Generate a haiku about testing.")
    response = await retrying.process(msg)

    assert response is not None
    assert response.role == "assistant"


@pytest.mark.asyncio
async def test_partial_failure_content_is_detected_downstream(my_agent):
    """
    Show that a downstream validator catches truncated responses.
    The chaos agent injects truncation; the caller checks for the sentinel.
    """
    chaos_config = ChaosConfig(partial_failure_probability=1.0, seed=0)
    chaotic = ChaosAgent(my_agent, chaos_config)

    msg = Message(role="user", content="Write a 5 sentence summary of the French Revolution.")
    response = await chaotic.process(msg)

    # Downstream systems should inspect for truncation markers
    assert "[TRUNCATED]" in str(response.content), (
        "expected truncation marker in partial failure response"
    )


@pytest.mark.asyncio
async def test_chaos_agent_records_accurate_failure_rate():
    """ChaosAgent's failure_rate property should reflect actual injection rate."""

    class EchoAgent(Agent):
        @property
        def name(self) -> str:
            return "echo"

        async def process(self, msg: Message) -> Message:
            return Message(role="assistant", content=msg.content)

    config = ChaosConfig(rate_limit_probability=0.5, seed=7)
    chaos = ChaosAgent(EchoAgent(), config)
    msg = Message(role="user", content="ping")

    successes = 0
    for _ in range(100):
        try:
            await chaos.process(msg)
            successes += 1
        except Exception:  # noqa: S110
            pass  # Expected: testing failure rate tracking

    # With seed=7 and p=0.5, roughly half should fail
    assert 30 <= successes <= 70, (
        f"expected ~50 successes in 100 calls, got {successes}"
    )
    assert 0.25 < chaos.failure_rate < 0.75
```

---

## Summary

| Pattern | Best For | Key Tradeoff |
|---|---|---|
| AI Judges | Open-ended correctness | Costs LLM tokens per evaluation |
| Shadow Mode | Safe production validation | Doubles LLM cost during shadow period |
| Trace Comparison | Detecting reasoning drift | Golden traces need periodic refreshing |
| Property-Based | Edge cases and invariants | Requires Hypothesis; async needs care |
| Chaos Testing | Resilience verification | Must pair with retry/fallback middleware |

### Combining Patterns

For production-ready test suites, combine them:

1. **Property tests** gate every PR (fast, no LLM cost).
2. **Chaos tests** validate resilience on each release.
3. **Trace regression tests** run nightly to detect model drift.
4. **Shadow mode** validates major prompt/model changes before full rollout.
5. **AI judges** provide detailed quality scoring for weekly reports.
