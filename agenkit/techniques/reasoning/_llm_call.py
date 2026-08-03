"""
Shared LLM invocation for reasoning techniques.

The five reasoning techniques that own an LLM (`ChainOfThought`, `TreeOfThought`,
`PlanAndSolve`, `LeastToMost`, `GraphOfThought`) all need the same thing: turn a
prompt string into response text. Each one used to carry its own copy of the
dispatch block, and all five copies drifted the same way — they called
``complete(prompt)`` with a bare ``str`` where the LLM contract
(:meth:`agenkit.adapters.llm.base.LLM.complete`) and all seven shipped adapters
declare ``messages: list[Message]``. Against any real adapter that raised
``AttributeError: 'str' object has no attribute 'role'``, because the adapter
iterated the string's characters looking for ``.role``.

It survived because the call was guarded by ``hasattr(llm, "complete")``, which is
satisfied by any object with a method of that name — so test doubles shaped like the
*call site* rather than the *contract* passed cleanly and the seam was never checked
against a real adapter. See #802.

This module is the single dispatch point, so the next divergence has one place to
happen instead of five.
"""

from typing import Any

from agenkit import Message


async def complete_text(llm: Any, prompt: str) -> str:
    """
    Send a prompt to an LLM (or agent) and return the response as text.

    Calls ``complete()`` per the declared LLM contract — a ``list[Message]`` in,
    a ``Message`` out — falling back to ``process()`` for objects that implement
    the ``Agent`` interface instead.

    Args:
        llm: LLM client or agent. Must provide either ``complete()`` (preferred,
            the :class:`~agenkit.adapters.llm.base.LLM` contract) or
            ``process()`` (the :class:`~agenkit.Agent` contract).
        prompt: Prompt text to send.

    Returns:
        Response text.

    Raises:
        AttributeError: If ``llm`` provides neither ``complete()`` nor ``process()``.
    """
    message = Message(role="user", content=prompt)

    if hasattr(llm, "complete"):
        response = await llm.complete([message])
    elif hasattr(llm, "process"):
        response = await llm.process(message)
    else:
        raise AttributeError("LLM must have either complete() or process() method")

    return _as_text(response)


def _as_text(response: Any) -> str:
    """
    Normalize an LLM/agent response to text.

    The LLM contract returns a ``Message``, but the reasoning techniques have always
    documented their ``llm`` parameter as needing a method "that returns text". Both
    are therefore honoured: a ``Message`` is unwrapped, a plain string passes through.
    Unlike the argument type this is not ambiguous — the two are trivially
    distinguishable and both were documented — so accepting either does not recreate
    the silent mismatch #802 was about.

    Args:
        response: A ``Message``, a ``str``, or anything with a ``content`` attribute.

    Returns:
        The response text.
    """
    content = getattr(response, "content", response)
    return content if isinstance(content, str) else str(content)
