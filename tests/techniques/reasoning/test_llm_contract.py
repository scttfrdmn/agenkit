"""
Contract tests for the reasoning-technique → LLM seam (#802).

The five reasoning techniques that own an LLM all called ``complete()`` with a bare
``str`` while the ``LLM`` contract and all seven shipped adapters declare
``messages: list[Message]``. Against a real adapter that raised
``AttributeError: 'str' object has no attribute 'role'`` — the adapter iterated the
string's characters looking for ``.role``.

Nothing caught it because:

* the call was guarded by ``hasattr(llm, "complete")``, so any object with a method
  of that name was accepted, and
* every test double in this package was written against the *call site*
  (``complete(self, prompt: str) -> str``) rather than the contract.

So the seam was never once exercised against something adapter-shaped. These tests
close that hole: they drive each technique through :class:`ContractLLM`, which
subclasses the real ``LLM`` and rejects a non-list argument the way an adapter would.
"""

import pytest

from agenkit import Message
from agenkit.techniques.reasoning import (
    ChainOfThought,
    GraphOfThought,
    LeastToMost,
    PlanAndSolve,
    TreeOfThought,
)

from .conftest import ContractLLM


class RecordingLLM(ContractLLM):
    """Contract-conformant double that records the messages it receives."""

    def __init__(self) -> None:
        super().__init__()
        self.received_messages: list[list[Message]] = []

    async def complete(self, messages, **kwargs):  # type: ignore[no-untyped-def]
        """Record the raw argument, then delegate to the contract-checking base."""
        # Recorded before validation so a bad type is still visible in the failure.
        self.received_messages.append(messages)
        return await super().complete(messages, **kwargs)

    def respond(self, prompt: str) -> str:
        """Return a response that satisfies every technique's parser."""
        return "1. First step\n2. Second step\nTherefore, the answer is 42"


@pytest.mark.asyncio
async def test_chain_of_thought_passes_message_list_to_complete():
    """CoT must call complete() with list[Message], not a bare string."""
    llm = RecordingLLM()
    cot = ChainOfThought(llm=llm)

    await cot.process(Message(role="user", content="What is 15 * 24?"))

    assert llm.call_count == 1
    sent = llm.received_messages[0]
    assert isinstance(sent, list), f"complete() received {type(sent).__name__}, not a list"
    assert all(isinstance(m, Message) for m in sent)
    # The prompt must actually survive the conversion.
    assert "15 * 24" in sent[0].content


@pytest.mark.asyncio
async def test_chain_of_thought_unwraps_message_response():
    """A Message returned by the adapter must be unwrapped, not stringified."""
    llm = RecordingLLM()
    cot = ChainOfThought(llm=llm, parse_steps=False)

    response = await cot.process(Message(role="user", content="Q"))

    # If the Message were used directly, content would contain "role=" / "Message(".
    assert "Message(" not in response.content
    assert "role=" not in response.content
    assert "Therefore, the answer is 42" in response.content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "make_technique",
    [
        pytest.param(lambda llm: ChainOfThought(llm=llm), id="chain_of_thought"),
        pytest.param(
            lambda llm: TreeOfThought(llm=llm, branching_factor=2, max_depth=1),
            id="tree_of_thought",
        ),
        pytest.param(lambda llm: PlanAndSolve(llm=llm), id="plan_and_solve"),
        pytest.param(lambda llm: LeastToMost(llm=llm), id="least_to_most"),
        pytest.param(lambda llm: GraphOfThought(llm=llm, max_nodes=3), id="graph_of_thought"),
    ],
)
async def test_technique_honours_llm_contract(make_technique):
    """
    Every technique that owns an LLM must satisfy the real adapter contract.

    Parametrized rather than written once per technique because all five carried
    identical copies of the same call-site block, and all five were wrong the same
    way. A shared test means a future divergence in any one of them fails here.
    """
    llm = RecordingLLM()
    technique = make_technique(llm)

    await technique.process(Message(role="user", content="What is 15 * 24?"))

    assert llm.call_count >= 1, "technique never called the LLM"
    for sent in llm.received_messages:
        assert isinstance(sent, list), (
            f"complete() received {type(sent).__name__}, not list[Message] — "
            "a real adapter would raise AttributeError on .role (#802)"
        )
        assert sent, "complete() received an empty message list"
        assert all(isinstance(m, Message) for m in sent)


@pytest.mark.asyncio
async def test_contract_llm_rejects_bare_string():
    """
    The double must reject the old call shape.

    Without this, `ContractLLM` could quietly grow lenient and stop defending the
    contract — which is exactly how the original doubles came to accept a `str`.
    """
    llm = ContractLLM()

    with pytest.raises(TypeError, match="list\\[Message\\]"):
        await llm.complete("a bare prompt string")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_agent_style_llm_still_supported():
    """
    Objects exposing process() rather than complete() must keep working.

    The techniques document support for both, and the process() path takes a single
    Message rather than a list — so it needs its own coverage.
    """

    class AgentStyleLLM:
        def __init__(self) -> None:
            self.received: list[Message] = []

        async def process(self, message: Message) -> Message:
            self.received.append(message)
            return Message(role="agent", content="Therefore, the answer is 42")

    llm = AgentStyleLLM()
    cot = ChainOfThought(llm=llm, parse_steps=False)

    response = await cot.process(Message(role="user", content="Q"))

    assert len(llm.received) == 1
    assert isinstance(llm.received[0], Message)
    assert "42" in response.content


@pytest.mark.asyncio
async def test_llm_without_any_contract_raises():
    """An object with none of the accepted contracts must fail loudly.

    Since #805 the techniques and the patterns share one dispatch point, so the
    accepted set is three contracts rather than two, and the error names all of
    them — the caller needs to know what to implement, not just what failed.
    """
    cot = ChainOfThought(llm=object())

    with pytest.raises(
        AttributeError, match=r"complete\(messages.*process\(message\).*chat\(messages\)"
    ):
        await cot.process(Message(role="user", content="Q"))
