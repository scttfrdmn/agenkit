"""Simple chat agent for custom frontend examples."""

from __future__ import annotations

import asyncio
from typing import Any

from agenkit import Agent, Message, Tool, ToolResult


class GreetingTool(Tool):
    """Greeting tool for demonstrations."""

    @property
    def name(self) -> str:
        return "greet"

    @property
    def description(self) -> str:
        return "Greet the user with a personalized message"

    async def execute(self, name: str) -> ToolResult:
        await asyncio.sleep(0.2)
        return ToolResult(
            success=True,
            data={"greeting": f"Hello, {name}! Welcome to the custom frontend demo."},
        )


class SimpleChatAgent(Agent):
    """Simple chat agent for demonstrating custom frontends."""

    def __init__(self, name: str = "ChatBot"):
        self._name = name
        self._tools = {"greet": GreetingTool()}

    @property
    def name(self) -> str:
        return self._name

    @property
    def tools(self) -> dict[str, Tool]:
        return self._tools

    async def process(self, message: Message) -> Message:
        content = message.content

        # Simple responses for demonstration
        if "hello" in content.lower() or "hi" in content.lower():
            response = "👋 Hello! I'm a simple chat agent. I can greet you by name if you ask!"
        elif "help" in content.lower():
            response = "I can:\n• Respond to greetings\n• Answer simple questions\n• Greet you by name"
        else:
            response = f"You said: '{content}'\n\nThis is a demonstration of custom AG-UI frontends built with React, Vue, and Svelte!"

        return Message(role="assistant", content=response)


__all__ = ["SimpleChatAgent"]
