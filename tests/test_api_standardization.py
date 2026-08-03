"""
Tests for v0.69.0 API Standardization — Issues #440, #443, #444.

Covers:
- ConversationalAgentConfig dataclass and dual constructor (Issue #440)
- Deprecation warnings for direct-parameter APIs (Issue #440)
- MemoryHierarchy.store() session_id deprecation (Issue #443)
- Canonical default configuration values (Issue #444)
"""

import warnings

import pytest

from agenkit import Message
from agenkit.patterns import (
    ConversationalAgent,
    ConversationalAgentConfig,
    ReActConfig,
)
from agenkit.patterns.memory import MemoryHierarchy, WorkingMemory

# ---------------------------------------------------------------------------
# Shared mock LLM (no real API calls)
# ---------------------------------------------------------------------------


class MockCompletionLLM:
    """Minimal mock implementing the LLM adapter contract.

    ``complete(messages, **kwargs)`` is what all seven shipped adapters implement
    (``agenkit.adapters.llm.base.LLM``). Named ``MockChatLLM`` with a ``chat()``
    method until #805 — a spelling no adapter ever had.
    """

    def __init__(self, response: str = "mock response") -> None:
        self._response = response
        self.calls: list[list[Message]] = []

    async def complete(self, messages: list[Message], **kwargs: object) -> Message:
        self.calls.append(list(messages))
        return Message(role="assistant", content=self._response)


# ---------------------------------------------------------------------------
# Group 1: ConversationalAgentConfig — 6 tests
# ---------------------------------------------------------------------------


class TestConversationalAgentConfig:
    """Tests for the new ConversationalAgentConfig dataclass."""

    def test_config_instantiation_defaults(self) -> None:
        """Config can be created with only the required llm_client."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(llm_client=llm)
        assert config.llm_client is llm
        assert config.max_history == 10
        assert config.system_prompt is None
        assert config.include_system is True

    def test_config_instantiation_custom(self) -> None:
        """Config accepts all optional parameters."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(
            llm_client=llm,
            max_history=20,
            system_prompt="You are a test assistant.",
            include_system=False,
        )
        assert config.max_history == 20
        assert config.system_prompt == "You are a test assistant."
        assert config.include_system is False

    def test_config_based_constructor_no_warning(self) -> None:
        """ConversationalAgent(config) must not emit any deprecation warning."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(llm_client=llm)
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            agent = ConversationalAgent(config)
        assert agent is not None

    def test_config_fields_propagated(self) -> None:
        """Agent constructed from config has correct attribute values."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(
            llm_client=llm,
            max_history=5,
            system_prompt="test prompt",
            include_system=True,
        )
        agent = ConversationalAgent(config)
        assert agent.max_history == 5
        assert agent.system_prompt == "test prompt"
        assert agent.include_system is True

    def test_system_prompt_in_history_when_include_system(self) -> None:
        """System prompt is added to history when include_system=True."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(
            llm_client=llm,
            system_prompt="Be concise.",
            include_system=True,
        )
        agent = ConversationalAgent(config)
        history = agent.get_history()
        assert len(history) == 1
        assert history[0].role == "system"
        assert history[0].content == "Be concise."

    def test_clear_and_get_history(self) -> None:
        """clear_history() and get_history() work on config-constructed agent."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(llm_client=llm, system_prompt="sys")
        agent = ConversationalAgent(config)
        agent.clear_history(keep_system=False)
        assert agent.get_history() == []

    def test_new_and_old_form_produce_identical_state(self) -> None:
        """New config-based form and deprecated kwargs form yield identical state."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(
            llm_client=llm,
            max_history=7,
            system_prompt="hello",
            include_system=True,
        )
        new_agent = ConversationalAgent(config)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            old_agent = ConversationalAgent(
                llm_client=llm,
                max_history=7,
                system_prompt="hello",
                include_system=True,
            )

        assert new_agent.max_history == old_agent.max_history
        assert new_agent.system_prompt == old_agent.system_prompt
        assert new_agent.include_system == old_agent.include_system
        assert len(new_agent.get_history()) == len(old_agent.get_history())


# ---------------------------------------------------------------------------
# Group 2: Deprecation warnings — 4 tests
# ---------------------------------------------------------------------------


class TestDeprecationWarnings:
    """Deprecation warning behavior for ConversationalAgent."""

    def test_direct_llm_client_emits_deprecation(self) -> None:
        """ConversationalAgent(llm_client=...) triggers a DeprecationWarning."""
        llm = MockCompletionLLM()
        with pytest.warns(DeprecationWarning):
            ConversationalAgent(llm_client=llm)

    def test_deprecation_message_mentions_config(self) -> None:
        """Deprecation message references ConversationalAgentConfig."""
        llm = MockCompletionLLM()
        with pytest.warns(DeprecationWarning, match="ConversationalAgentConfig"):
            ConversationalAgent(llm_client=llm)

    def test_config_form_no_deprecation(self) -> None:
        """Config-based form does NOT emit a deprecation warning."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(llm_client=llm)
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            agent = ConversationalAgent(config)
        assert agent.max_history == 10  # default still correct

    def test_deprecated_form_still_works(self) -> None:
        """Old kwargs form still constructs a functional agent."""
        llm = MockCompletionLLM()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            agent = ConversationalAgent(llm_client=llm, max_history=3)
        assert agent.max_history == 3
        assert agent.name == "ConversationalAgent"


# ---------------------------------------------------------------------------
# Group 3: MemoryHierarchy session_id deprecation — 4 tests
# ---------------------------------------------------------------------------


class TestMemorySessionIdDeprecation:
    """session_id deprecation warnings in MemoryHierarchy.store()."""

    def _make_hierarchy(self) -> MemoryHierarchy:
        return MemoryHierarchy(working_memory=WorkingMemory())

    @pytest.mark.asyncio
    async def test_session_id_kwarg_emits_deprecation(self) -> None:
        """store(session_id=...) emits DeprecationWarning."""
        hier = self._make_hierarchy()
        with pytest.warns(DeprecationWarning):
            await hier.store("test content", session_id="sess-1")

    @pytest.mark.asyncio
    async def test_no_session_id_no_deprecation(self) -> None:
        """store() without session_id does not emit DeprecationWarning."""
        hier = self._make_hierarchy()
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            await hier.store("test content")

    @pytest.mark.asyncio
    async def test_deprecated_session_id_still_writes(self) -> None:
        """Deprecated session_id path still stores the entry correctly."""
        hier = self._make_hierarchy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            entry_id = await hier.store("remember this", session_id="s42")
        assert entry_id  # non-empty id returned
        # Entry should be in working memory
        results = await hier.retrieve("remember", limit=5)
        assert any("remember this" in r.content for r in results)

    @pytest.mark.asyncio
    async def test_deprecation_message_mentions_memory_entry(self) -> None:
        """session_id deprecation message references MemoryEntry."""
        hier = self._make_hierarchy()
        with pytest.warns(DeprecationWarning, match="MemoryEntry"):
            await hier.store("content", session_id="sess-x")


# ---------------------------------------------------------------------------
# Group 4: Canonical defaults — 8 tests
# ---------------------------------------------------------------------------


class TestCanonicalDefaults:
    """Verify canonical default values match cross-language specification."""

    def test_conversational_agent_max_history_default(self) -> None:
        """ConversationalAgent max_history defaults to 10."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(llm_client=llm)
        agent = ConversationalAgent(config)
        assert agent.max_history == 10

    def test_conversational_agent_include_system_default(self) -> None:
        """ConversationalAgent include_system defaults to True."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(llm_client=llm)
        agent = ConversationalAgent(config)
        assert agent.include_system is True

    def test_conversational_agent_system_prompt_default(self) -> None:
        """ConversationalAgent system_prompt defaults to None."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(llm_client=llm)
        agent = ConversationalAgent(config)
        assert agent.system_prompt is None

    def test_conversational_agent_config_max_history_default(self) -> None:
        """ConversationalAgentConfig max_history field defaults to 10."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(llm_client=llm)
        assert config.max_history == 10

    def test_conversational_agent_config_include_system_default(self) -> None:
        """ConversationalAgentConfig include_system field defaults to True."""
        llm = MockCompletionLLM()
        config = ConversationalAgentConfig(llm_client=llm)
        assert config.include_system is True

    def test_router_config_default_key_default(self) -> None:
        """RouterConfig default_key defaults to None."""
        # RouterConfig requires classifier and agents — peek at the dataclass default
        # without constructing RouterAgent to avoid needing a classifier
        from agenkit.patterns.router import RouterConfig

        fields = {f.name: f.default for f in RouterConfig.__dataclass_fields__.values()}
        assert fields["default_key"] is None

    def test_react_config_max_steps_default(self) -> None:
        """ReActConfig max_steps defaults to 10."""

        fields = {f.name: f.default for f in ReActConfig.__dataclass_fields__.values()}
        assert fields["max_steps"] == 10

    def test_react_config_verbose_default(self) -> None:
        """ReActConfig verbose defaults to False."""
        fields = {f.name: f.default for f in ReActConfig.__dataclass_fields__.values()}
        assert fields["verbose"] is False
