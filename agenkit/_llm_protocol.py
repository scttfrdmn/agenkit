"""
Shared dispatch for calling an LLM, an adapter, or an agent.

Agenkit accumulated four mutually incompatible ways to say "ask a model for a
response", and only one of them had any real implementation:

======================================  ==================================
declared                                implemented by
======================================  ==================================
``LLM.complete(list[Message], **kw)``   all 7 shipped adapters
``LLMClient.chat(list[Message])``       test doubles and examples only
``Agent.process(Message)``              ~500 agents, incl. every technique
``complete(str)``                       nothing (see #802)
======================================  ==================================

The consequence was that :class:`~agenkit.patterns.ConversationalAgent` — which
demanded ``chat()`` — could not be used with any adapter the toolkit ships:

.. code-block:: text

    AttributeError: 'AnthropicLLM' object has no attribute 'chat'

It survived because every test double was shaped like the *call site* rather than
the *contract*, so the seam was never exercised against a real adapter. That is the
same failure as #802, one layer up. See #805.

This module is the single place that resolves "what does this object respond to",
so a fifth spelling has one place to be rejected instead of four places to appear.
The order is deliberate: the contract that adapters actually implement first, the
contract that agents implement second, the deprecated one last.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, cast

from agenkit.interfaces import CallOptions, Message

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_CHAT_DEPRECATION = (
    "Passing an LLM client that only implements chat() is deprecated and will be "
    "removed in v2.0. Implement complete(messages, **kwargs) — the contract every "
    "shipped agenkit adapter uses (agenkit.adapters.llm.LLM) — or process(message), "
    "the Agent contract. See #805."
)


def can_carry_options(llm: Any) -> bool:
    """
    Report whether per-call options can actually reach this client.

    Exists so a dropped option is *visible* rather than silent — the whole
    complaint in #801. A caller that checks this before using the options path
    never has options quietly discarded, and
    :attr:`~agenkit.patterns.ConversationalAgent.supports_options` is built on it.

    Args:
        llm: LLM client, adapter, or agent.

    Returns:
        True if :func:`complete_messages` would forward set options to it.
        ``chat()``-only clients return False: the deprecated protocol has no
        parameter to put them in.
    """
    if hasattr(llm, "complete"):
        return True
    if hasattr(llm, "process"):
        return bool(getattr(llm, "supports_options", False))
    return False


def flatten_history(messages: list[Message]) -> Message:
    """
    Collapse a conversation into the single message the ``Agent`` contract takes.

    ``Agent.process()`` accepts one :class:`~agenkit.Message`, so an agent used as a
    conversational backend needs the history rendered into it. The
    ``"{role}: {content}"`` form matches what the Rust core already does
    (``agenkit-rust/src/patterns/conversational.rs``), so the two do not drift.

    Args:
        messages: Conversation history.

    Returns:
        A single ``user`` message containing the rendered history.
    """
    rendered = "\n".join(f"{m.role}: {m.content}" for m in messages)
    return Message(role="user", content=rendered)


async def complete_messages(
    llm: Any,
    messages: list[Message],
    options: CallOptions | None = None,
) -> Message:
    """
    Send a conversation to an LLM, adapter, or agent and return the response.

    Dispatches in contract-priority order:

    1. ``complete(messages, **kwargs)`` — the
       :class:`~agenkit.adapters.llm.LLM` contract. Preferred: it is what all
       shipped adapters implement, and it carries per-call options.
    2. ``process(message)`` — the :class:`~agenkit.Agent` contract, with the
       history flattened via :func:`flatten_history`. Options are forwarded
       through ``process_with()`` when the agent advertises it.
    3. ``chat(messages)`` — deprecated (#805), emits ``DeprecationWarning``.

    Args:
        llm: LLM client, adapter, or agent.
        messages: Conversation history.
        options: Optional per-call inference options (#801). Set options are
            omitted entirely when unset, never forwarded as ``None`` — see
            :meth:`~agenkit.CallOptions.to_kwargs`.

    Returns:
        The response message.

    Raises:
        AttributeError: If ``llm`` implements none of the three.
    """
    kwargs = options.to_kwargs() if options is not None else {}

    if hasattr(llm, "complete"):
        response = await llm.complete(messages, **kwargs)
    elif hasattr(llm, "process"):
        message = flatten_history(messages)
        if kwargs and getattr(llm, "supports_options", False):
            response = await llm.process_with(message, options)
        else:
            response = await llm.process(message)
    elif hasattr(llm, "chat"):
        warnings.warn(_CHAT_DEPRECATION, DeprecationWarning, stacklevel=2)
        response = await llm.chat(messages)
    else:
        raise AttributeError(
            "LLM client must implement complete(messages, **kwargs) (the LLM "
            "contract), process(message) (the Agent contract), or the deprecated "
            f"chat(messages). Got {type(llm).__name__} with none of them."
        )

    return _as_message(response)


def stream_messages(
    llm: Any,
    messages: list[Message],
    options: CallOptions | None = None,
) -> AsyncIterator[Message]:
    """
    Stream a response for a conversation.

    Dispatches on the same contract priority as :func:`complete_messages`, because
    ``stream()`` means two different things depending on which contract the object
    implements and they are not interchangeable:

    * :class:`~agenkit.adapters.llm.LLM` declares ``stream(list[Message], **kwargs)``
    * :class:`~agenkit.Agent` declares ``stream(Message)`` — one message, no kwargs

    So dispatching on ``hasattr(llm, "stream")`` alone would hand an ``Agent`` a
    list where it expects a single ``Message``, which is exactly the silent type
    mismatch of #802. The ``Agent`` base defines ``stream()`` as a default that
    raises, so ``hasattr`` is True for *every* agent and the mismatch would be
    reachable from any of them.

    ``LLMClient`` itself never declared ``stream()`` at all, so
    :class:`~agenkit.patterns.StreamingConversationalAgent` required a method its
    own declared protocol did not have — the parent required one protocol and the
    child required another, and neither was declared (#805). A ``chat()`` client
    that also happens to define ``stream(messages)`` therefore worked in practice
    and keeps working for the deprecation cycle; one that does not gets an error
    naming the contract instead of a bare missing attribute.

    Args:
        llm: LLM client, adapter, or agent.
        messages: Conversation history.
        options: Optional per-call inference options (#801). Only forwardable on the
            ``LLM`` path; see Raises.

    Returns:
        An async iterator of response chunks.

    Raises:
        AttributeError: If ``llm`` implements no recognised ``stream()``.
        ValueError: If options are set but ``llm`` only offers a streaming contract
            with no parameter to carry them. Raised rather than dropped so the
            caller learns the options had no effect — the failure #801 was about.
    """
    kwargs = options.to_kwargs() if options is not None else {}

    # ``llm`` is deliberately untyped — the three contracts cannot be expressed as
    # one protocol — so the returned iterator has to be cast rather than inferred.
    if hasattr(llm, "complete"):
        return cast("AsyncIterator[Message]", llm.stream(messages, **kwargs))

    if hasattr(llm, "process"):
        _reject_unforwardable(llm, kwargs, "the Agent streaming contract is stream(message)")
        return cast("AsyncIterator[Message]", llm.stream(flatten_history(messages)))

    if hasattr(llm, "chat") and hasattr(llm, "stream"):
        warnings.warn(_CHAT_DEPRECATION, DeprecationWarning, stacklevel=2)
        _reject_unforwardable(
            llm, kwargs, "the deprecated chat() protocol never declared stream() options"
        )
        return cast("AsyncIterator[Message]", llm.stream(messages))

    raise AttributeError(
        f"Streaming requires stream(messages, **kwargs) (the LLM contract, "
        f"agenkit.adapters.llm.LLM) or stream(message) (the Agent contract). Got "
        f"{type(llm).__name__}, which implements neither. A client that only "
        "implements the deprecated chat() cannot stream."
    )


def _reject_unforwardable(llm: Any, kwargs: dict[str, Any], why: str) -> None:
    """
    Refuse to stream with options that cannot reach the client.

    Silently ignoring them would be the exact failure #801 was filed about, so the
    only honest answer is to refuse. Only raises when options are actually set, so
    the common no-options path is unaffected.

    Args:
        llm: The client, named in the message.
        kwargs: Rendered options; empty means nothing to forward.
        why: Contract-specific explanation of what is missing.

    Raises:
        ValueError: If ``kwargs`` is non-empty.
    """
    if not kwargs:
        return
    raise ValueError(
        f"Per-call options cannot be applied when streaming through "
        f"{type(llm).__name__}: {why}, so there is nowhere to put them. Use a client "
        "implementing stream(messages, **kwargs), or drop the options rather than "
        "have them silently ignored."
    )


async def complete_text(llm: Any, prompt: str, options: CallOptions | None = None) -> str:
    """
    Send a single prompt to an LLM (or agent) and return the response as text.

    The prompt-shaped convenience wrapper over :func:`complete_messages`, used by
    the reasoning techniques. It exists because all five of them used to carry
    their own copy of the dispatch block, and all five copies drifted the same way
    — they called ``complete(prompt)`` with a bare ``str`` where the contract and
    all seven shipped adapters declare ``messages: list[Message]``. Against a real
    adapter that raised ``AttributeError: 'str' object has no attribute 'role'``,
    because the adapter iterated the string's characters looking for ``.role``.
    See #802.

    Args:
        llm: LLM client or agent.
        prompt: Prompt text to send.
        options: Optional per-call inference options (#801).

    Returns:
        Response text.

    Raises:
        AttributeError: If ``llm`` implements none of the accepted protocols.
    """
    response = await complete_messages(llm, [Message(role="user", content=prompt)], options)
    return response.content if isinstance(response.content, str) else str(response.content)


def _as_message(response: Any) -> Message:
    """
    Normalize a response to a :class:`~agenkit.Message`.

    The contract returns a ``Message``, but the reasoning techniques have always
    documented their ``llm`` parameter as needing a method "that returns text", so a
    bare string is also accepted and wrapped. Unlike the *argument* type this is not
    ambiguous — the two are trivially distinguishable and both were documented — so
    accepting either does not recreate the silent mismatch #802 was about.

    Args:
        response: A ``Message`` or a ``str``.

    Returns:
        The response as a ``Message``.
    """
    if isinstance(response, Message):
        return response
    if isinstance(response, str):
        return Message(role="assistant", content=response)
    content = getattr(response, "content", response)
    return Message(role="assistant", content=content if isinstance(content, str) else str(content))
