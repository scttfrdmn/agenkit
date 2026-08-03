"""
Tests that the patterns work with the LLM clients agenkit actually ships (#805).

`LLMClient` used to require `chat()`. Not one of the seven shipped adapters has a
`chat()` — they all implement `complete()` — so `ConversationalAgent` could not be
used with any real LLM:

    AttributeError: 'AnthropicLLM' object has no attribute 'chat'

Every test double in the suite implemented `chat()`, because each was written
against the *call site* rather than against the contract. So the seam was fully
covered by tests and none of them could ever have caught it. That is the same
failure as #802, one layer up.

The load-bearing test in this file is therefore
:meth:`TestRealAdapterContract.test_conversational_agent_works_with_an_llm_subclass`
— it subclasses the real :class:`~agenkit.adapters.llm.LLM` ABC rather than
duck-typing a double, so a double cannot silently diverge from the contract again.
The rest of the file exists to pin the dispatch order and the deprecation.
"""

import warnings
from dataclasses import dataclass, field

import pytest

from agenkit import Agent, CallOptions, Message
from agenkit._llm_protocol import (
    can_carry_options,
    complete_messages,
    flatten_history,
    stream_messages,
)
from agenkit.adapters.llm import LLM
from agenkit.patterns import (
    ConversationalAgent,
    ConversationalAgentConfig,
    StreamingConversationalAgent,
)


@dataclass
class Recorded:
    """One captured call."""

    messages: list[Message]
    kwargs: dict


class RecordingAdapter(LLM):
    """
    A real adapter.

    Subclasses the actual :class:`~agenkit.adapters.llm.LLM` ABC — not a duck-typed
    stand-in — so that if the base contract changes, these tests break rather than
    quietly continuing to pass against a shape nothing ships.
    """

    calls: list[Recorded] = field(default_factory=list)

    def __init__(self, response: str = "adapter response") -> None:
        self.calls: list[Recorded] = []
        self.response = response

    async def complete(self, messages: list[Message], **kwargs) -> Message:
        if not isinstance(messages, list):
            raise TypeError(
                f"complete() takes list[Message], got {type(messages).__name__} — see #802"
            )
        for m in messages:
            if not isinstance(m, Message):
                raise TypeError(
                    f"complete() takes list[Message], got a list of {type(m).__name__} — see #802"
                )
        self.calls.append(Recorded(messages=list(messages), kwargs=dict(kwargs)))
        return Message(role="agent", content=self.response)

    async def stream(self, messages: list[Message], **kwargs):
        self.calls.append(Recorded(messages=list(messages), kwargs=dict(kwargs)))
        for word in self.response.split():
            yield Message(role="agent", content=word + " ")


class ChatOnlyClient:
    """A client shaped like the deprecated protocol — i.e. like the old doubles."""

    def __init__(self, response: str = "chat response") -> None:
        self.calls: list[list[Message]] = []
        self.response = response

    async def chat(self, messages: list[Message]) -> Message:
        self.calls.append(list(messages))
        return Message(role="agent", content=self.response)


class AgentBackend(Agent):
    """An agent used as a conversational backend, as the Rust core does."""

    def __init__(self, response: str = "agent response") -> None:
        self.received: list[Message] = []
        self.response = response

    @property
    def name(self) -> str:
        return "agent_backend"

    async def process(self, message: Message) -> Message:
        self.received.append(message)
        return Message(role="agent", content=self.response)


class TunableAgentBackend(AgentBackend):
    """An agent backend that can honour per-call options (#801)."""

    def __init__(self, response: str = "tunable response") -> None:
        super().__init__(response)
        self.options: list[CallOptions] = []

    async def process(self, message: Message) -> Message:
        return await self.process_with(message, CallOptions())

    async def process_with(self, message: Message, options: CallOptions) -> Message:
        self.options.append(options)
        return await AgentBackend.process(self, message)


class TestRealAdapterContract:
    """The bug: patterns must work with the LLM clients the toolkit ships."""

    @pytest.mark.asyncio
    async def test_conversational_agent_works_with_an_llm_subclass(self):
        """
        The regression test for #805.

        Before the fix this raised
        ``AttributeError: 'RecordingAdapter' object has no attribute 'chat'``.
        """
        adapter = RecordingAdapter("Hello!")
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=adapter))

        response = await agent.process(Message(role="user", content="Hi"))

        assert response.content == "Hello!"
        assert len(adapter.calls) == 1

    @pytest.mark.asyncio
    async def test_adapter_receives_the_real_history_as_messages(self):
        """
        Not just "it didn't crash" — the adapter must get a real message list.

        #802 was a call that survived a `hasattr` check while passing the wrong
        type. Asserting on the argument's shape is what distinguishes a working
        seam from one that merely doesn't raise.
        """
        adapter = RecordingAdapter()
        agent = ConversationalAgent(
            ConversationalAgentConfig(llm_client=adapter, system_prompt="Be terse.")
        )

        await agent.process(Message(role="user", content="Q1"))
        await agent.process(Message(role="user", content="Q2"))

        first, second = adapter.calls
        assert [m.role for m in first.messages] == ["system", "user"]
        assert [m.content for m in first.messages] == ["Be terse.", "Q1"]
        # Second turn must include the first exchange — that is the whole pattern.
        assert [m.role for m in second.messages] == ["system", "user", "agent", "user"]
        assert [m.content for m in second.messages][-1] == "Q2"

    @pytest.mark.asyncio
    async def test_streaming_agent_works_with_an_llm_subclass(self):
        """
        `StreamingConversationalAgent` required `stream()` while its parent required
        `chat()`, and `LLMClient` declared only `chat()`. So the declared protocol
        described neither half of the hierarchy (#805).
        """
        adapter = RecordingAdapter("one two three")
        agent = StreamingConversationalAgent(ConversationalAgentConfig(llm_client=adapter))

        chunks = [c.content async for c in agent.stream(Message(role="user", content="Q"))]

        assert "".join(chunks).strip() == "one two three"
        assert agent.get_history()[-1].content.strip() == "one two three"

    @pytest.mark.asyncio
    async def test_no_options_means_no_kwargs(self):
        """
        Plain `process()` must not send inference kwargs at all.

        Not "must send defaults" — must send nothing. Forwarding unset values would
        make every call through a pattern override whatever the adapter was
        configured with (#801).
        """
        adapter = RecordingAdapter()
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=adapter))

        await agent.process(Message(role="user", content="Q"))

        assert adapter.calls[0].kwargs == {}


class TestAgentBackend:
    """An `Agent` must be usable as a conversational backend, as in Rust."""

    @pytest.mark.asyncio
    async def test_agent_backend_accepted(self):
        backend = AgentBackend("from agent")
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=backend))

        response = await agent.process(Message(role="user", content="Q"))

        assert response.content == "from agent"

    @pytest.mark.asyncio
    async def test_history_is_flattened_for_the_agent_contract(self):
        """
        `Agent.process()` takes one Message, so the history has to be rendered into
        it. The format matches the Rust core so the two cannot drift.
        """
        backend = AgentBackend()
        agent = ConversationalAgent(
            ConversationalAgentConfig(llm_client=backend, system_prompt="S")
        )

        await agent.process(Message(role="user", content="Q"))

        assert backend.received[0].content == "system: S\nuser: Q"

    def test_flatten_history_format(self):
        assert (
            flatten_history(
                [Message(role="system", content="S"), Message(role="user", content="Q")]
            ).content
            == "system: S\nuser: Q"
        )

    def test_flatten_history_empty(self):
        assert flatten_history([]).content == ""


class TestDeprecatedChat:
    """`chat()` keeps working for one cycle, but says so."""

    @pytest.mark.asyncio
    async def test_chat_client_still_works(self):
        """Existing user code that copied the examples must not break outright."""
        client = ChatOnlyClient("legacy!")
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=client))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            response = await agent.process(Message(role="user", content="Q"))

        assert response.content == "legacy!"
        assert len(client.calls) == 1

    @pytest.mark.asyncio
    async def test_chat_client_warns(self):
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=ChatOnlyClient()))

        with pytest.warns(DeprecationWarning, match=r"only implements chat\(\)"):
            await agent.process(Message(role="user", content="Q"))

    @pytest.mark.asyncio
    async def test_chat_client_that_also_streams_keeps_streaming(self):
        """
        `chat()` + `stream()` is a real shape and must survive the cycle.

        `LLMClient` never declared `stream()`, so `StreamingConversationalAgent`
        required a method its own protocol did not have. Clients grew a `stream()`
        anyway to satisfy it — deprecating `chat()` must not take their streaming
        away in the same release.
        """

        class ChatAndStream(ChatOnlyClient):
            async def stream(self, messages):
                self.calls.append(list(messages))
                for word in ("a", "b"):
                    yield Message(role="agent", content=word + " ")

        client = ChatAndStream()
        agent = StreamingConversationalAgent(ConversationalAgentConfig(llm_client=client))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            chunks = [c.content async for c in agent.stream(Message(role="user", content="Q"))]

        assert "".join(chunks).strip() == "a b"
        # Got the real history, not a flattened single message.
        assert [m.content for m in client.calls[0]] == ["Q"]

    @pytest.mark.asyncio
    async def test_chat_stream_rejects_options_it_cannot_forward(self):
        class ChatAndStream(ChatOnlyClient):
            async def stream(self, messages):
                yield Message(role="agent", content="a")

        with pytest.raises(ValueError, match="cannot be applied when streaming"):
            stream_messages(ChatAndStream(), [], CallOptions(temperature=0.5))

    @pytest.mark.asyncio
    async def test_chat_client_cannot_stream(self):
        """
        A `chat()`-only client has no `stream()`, and the error must say why.

        Previously this surfaced as a bare missing-attribute error from deep inside
        the generator, with nothing pointing at the protocol mismatch.
        """
        agent = StreamingConversationalAgent(ConversationalAgentConfig(llm_client=ChatOnlyClient()))

        with pytest.raises(AttributeError, match=r"deprecated chat\(\) cannot stream"):
            async for _ in agent.stream(Message(role="user", content="Q")):
                pass


class TestDispatchOrder:
    """`complete()` wins over the alternatives, deterministically."""

    @pytest.mark.asyncio
    async def test_complete_preferred_over_chat(self):
        """
        A client offering both must take the contract path, silently.

        Any real adapter that gains a `chat()` shim during the deprecation window
        must not start warning or change behaviour.
        """

        class Both(RecordingAdapter):
            def __init__(self):
                super().__init__("via complete")
                self.chat_calls = 0

            async def chat(self, messages):
                self.chat_calls += 1
                return Message(role="agent", content="via chat")

        client = Both()
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            response = await complete_messages(client, [Message(role="user", content="Q")])

        assert response.content == "via complete"
        assert client.chat_calls == 0

    @pytest.mark.asyncio
    async def test_process_preferred_over_chat(self):
        class Both(AgentBackend):
            async def chat(self, messages):
                return Message(role="agent", content="via chat")

        response = await complete_messages(Both("via process"), [Message(role="user", content="Q")])

        assert response.content == "via process"

    @pytest.mark.asyncio
    async def test_no_protocol_raises_with_all_three_named(self):
        """The error has to tell the user what to implement, not just what failed."""
        with pytest.raises(AttributeError) as exc:
            await complete_messages(object(), [Message(role="user", content="Q")])

        text = str(exc.value)
        assert "complete(" in text
        assert "process(" in text
        assert "chat(" in text

    @pytest.mark.asyncio
    async def test_stream_dispatches_on_contract_not_just_hasattr(self):
        """
        `stream()` means two incompatible things, so it needs the same dispatch.

        `LLM.stream` takes `list[Message]`; `Agent.stream` takes a single `Message`.
        The `Agent` base defines `stream()` as a raising default, so
        `hasattr(x, "stream")` is True for *every* agent — dispatching on that alone
        would hand an agent a list where it expects one Message, recreating #802 in
        the fix for #805.
        """

        class StreamingAgentBackend(AgentBackend):
            def __init__(self):
                super().__init__()
                self.received_type: type | None = None

            async def stream(self, message: Message):
                self.received_type = type(message)
                yield Message(role="agent", content="chunk")

        backend = StreamingAgentBackend()
        chunks = [
            c.content async for c in stream_messages(backend, [Message(role="user", content="Q")])
        ]

        assert chunks == ["chunk"]
        assert backend.received_type is Message, (
            "an Agent was handed a list where its contract declares a single Message"
        )

    @pytest.mark.asyncio
    async def test_stream_rejects_options_it_cannot_forward(self):
        """
        Dropped options must fail loudly.

        The Agent streaming contract has no options parameter, so silently ignoring
        them would be the exact failure #801 was filed about. Refusing is the only
        honest answer.
        """

        class StreamingAgentBackend(AgentBackend):
            async def stream(self, message: Message):
                yield Message(role="agent", content="chunk")

        with pytest.raises(ValueError, match="cannot be applied when streaming"):
            stream_messages(StreamingAgentBackend(), [], CallOptions(temperature=0.5))

    def test_stream_rejects_a_client_with_neither_contract(self):
        with pytest.raises(AttributeError, match="Streaming requires"):
            stream_messages(ChatOnlyClient(), [])

    @pytest.mark.asyncio
    async def test_bare_string_response_is_wrapped(self):
        """
        Techniques have always documented `llm` as returning text, so a plain
        string is accepted and wrapped. Unlike the *argument* type (#802) the two
        are trivially distinguishable, so this is not the same ambiguity.
        """

        class StringReturning:
            async def complete(self, messages, **kwargs):
                return "just text"

        response = await complete_messages(StringReturning(), [Message(role="user", content="Q")])

        assert isinstance(response, Message)
        assert response.content == "just text"


class TestOptionsReachTheLLM:
    """The #801 channel, now available to the patterns too."""

    @pytest.mark.asyncio
    async def test_options_forwarded_to_adapter(self):
        adapter = RecordingAdapter()
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=adapter))

        await agent.process_with(
            Message(role="user", content="Q"), CallOptions(temperature=0.9, max_tokens=50)
        )

        assert adapter.calls[0].kwargs == {"temperature": 0.9, "max_tokens": 50}

    @pytest.mark.asyncio
    async def test_zero_temperature_forwarded(self):
        """0.0 is greedy decoding — a real request, not an absence."""
        adapter = RecordingAdapter()
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=adapter))

        await agent.process_with(Message(role="user", content="Q"), CallOptions(temperature=0.0))

        assert adapter.calls[0].kwargs == {"temperature": 0.0}

    @pytest.mark.asyncio
    async def test_options_forwarded_to_capable_agent_backend(self):
        backend = TunableAgentBackend()
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=backend))

        await agent.process_with(Message(role="user", content="Q"), CallOptions(temperature=0.7))

        assert [o.temperature for o in backend.options] == [0.7]

    @pytest.mark.asyncio
    async def test_options_forwarded_to_stream(self):
        adapter = RecordingAdapter("a b")
        agent = StreamingConversationalAgent(ConversationalAgentConfig(llm_client=adapter))

        async for _ in agent.stream(
            Message(role="user", content="Q"), CallOptions(temperature=0.4)
        ):
            pass

        assert adapter.calls[0].kwargs == {"temperature": 0.4}

    @pytest.mark.asyncio
    async def test_legacy_agent_backend_still_works_without_options(self):
        """An agent that never heard of CallOptions must keep working."""
        backend = AgentBackend()
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=backend))

        response = await agent.process_with(
            Message(role="user", content="Q"), CallOptions(temperature=0.9)
        )

        assert response.content == "agent response"


class TestSupportsOptions:
    """A dropped option must be visible rather than silent (#801)."""

    def test_true_for_adapter(self):
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=RecordingAdapter()))
        assert agent.supports_options is True

    def test_true_for_capable_agent_backend(self):
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=TunableAgentBackend()))
        assert agent.supports_options is True

    def test_false_for_plain_agent_backend(self):
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=AgentBackend()))
        assert agent.supports_options is False

    def test_false_for_chat_only_client(self):
        """The deprecated protocol has no parameter to carry options."""
        agent = ConversationalAgent(ConversationalAgentConfig(llm_client=ChatOnlyClient()))
        assert agent.supports_options is False

    def test_can_carry_options_rejects_unknown_object(self):
        assert can_carry_options(object()) is False
