"""
Shared test doubles for the reasoning techniques.

Every double in this package used to be a hand-rolled class with
``async def complete(self, prompt: str) -> str`` — written against the *call site*
rather than the ``LLM`` contract. Since the techniques dispatch on
``hasattr(llm, "complete")``, those doubles were accepted, and the fact that the
techniques were passing a bare ``str`` where every shipped adapter declares
``messages: list[Message]`` went unnoticed for as long as the code existed (#802).

`ContractLLM` below is the fix for the test side: it subclasses the real
:class:`~agenkit.adapters.llm.base.LLM`, so a double cannot silently diverge from
the contract again — if the technique passes the wrong type, the double raises the
same way a real adapter does. Prefer it over a bare class in new tests.
"""

from typing import Any

import pytest

from agenkit import Message
from agenkit.adapters.llm.base import LLM


class ContractLLM(LLM):
    """
    Test double that enforces the real ``LLM`` contract.

    Subclasses :class:`~agenkit.adapters.llm.base.LLM` rather than duck-typing it, and
    validates the argument the way a real adapter does — a real adapter iterates
    ``messages`` and reads ``.role``/``.content`` off each one, so a bare string fails
    there with ``AttributeError``. Doing the same here means a regression of #802 is
    caught by every test that uses this double, not just by a dedicated one.

    Subclasses implement :meth:`respond` to return text for a prompt.
    """

    def __init__(self) -> None:
        self.call_count = 0
        self.received_kwargs: list[dict[str, Any]] = []
        self.received_prompts: list[str] = []

    def respond(self, prompt: str) -> str:
        """
        Return the response text for a prompt. Override in subclasses.

        Args:
            prompt: The prompt text extracted from the incoming messages.

        Returns:
            Response text.
        """
        return "Therefore, the answer is 42"

    async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
        """
        Validate the contract, record the call, and return a ``Message``.

        Args:
            messages: Conversation history. Must be a list of ``Message`` — passing a
                bare ``str`` here is the #802 bug and raises, as a real adapter would.
            **kwargs: Provider options; recorded for assertions.

        Returns:
            Response as a ``Message``, per the ``LLM`` contract.

        Raises:
            TypeError: If ``messages`` is not a list.
            AttributeError: If an element is not a ``Message``.
        """
        if not isinstance(messages, list):
            raise TypeError(
                f"complete() takes list[Message], got {type(messages).__name__} — see #802"
            )

        # A real adapter converts each message; a str would blow up here on .role.
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)

        self.call_count += 1
        self.received_kwargs.append(kwargs)
        self.received_prompts.append(prompt)

        return Message(role="agent", content=self.respond(prompt))

    async def stream(self, messages: list[Message], **kwargs: Any):
        """
        Stream the response as a single chunk.

        Args:
            messages: Conversation history.
            **kwargs: Provider options.

        Yields:
            One ``Message`` containing the full response.
        """
        yield await self.complete(messages, **kwargs)


@pytest.fixture
def contract_llm() -> ContractLLM:
    """Return a default contract-conformant LLM double."""
    return ContractLLM()
