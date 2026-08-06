#!/usr/bin/env python3
"""
MiniOpenAIAgents - OpenAI Agents SDK Equivalent Built on Agenkit

Demonstrates how OpenAI Agents SDK patterns (openai-agents, Jan 2026) can be
built ON TOP of Agenkit primitives, showing toolkit philosophy.

OpenAI Agents SDK Key Concepts (v0.0.x, January 2026):
- Agent: named agent with instructions, tools, and handoffs list
- Runner: executes agents; run_sync() or async run() for streaming
- function_tool: decorator that wraps a Python function as a callable tool
- handoff(): creates a Handoff routing object pointing to another agent
- RunResult: holds final_output string and all messages from the run

Pattern Mappings:
  OAI.Agent           → Agenkit Agent (base interface)
  OAI.Runner          → Agenkit agent.process() / streaming loop
  OAI.function_tool   → Agenkit Tool class
  OAI.handoff()       → Agenkit RouterAgent / conditional routing
  OAI.RunResult       → Agenkit Message (final assistant message)

Migration guide: docs/migrations/openaiagents-to-agenkit.md

Usage: uv run python examples/frameworks/miniopenaiagents.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

from agenkit import Message
from agenkit.adapters.llm import LLM, OpenAILLM

# ---------------------------------------------------------------------------
# FunctionTool (mirrors OAI.function_tool decorator)
# ---------------------------------------------------------------------------


@dataclass
class FunctionTool:
    """
    A callable tool wrapping a plain Python function.
    Pattern: OAI.function_tool decorator → Agenkit Tool class

    The OpenAI Agents SDK uses @function_tool to expose Python functions to
    agents. Here we represent the same concept as a dataclass with a callable.
    The name and description come from the wrapped function's __name__ and
    __doc__, exactly as the SDK does.
    """

    name: str
    description: str
    fn: Callable[..., str]

    def call(self, **kwargs: Any) -> str:
        """Execute the tool and return its string result."""
        return self.fn(**kwargs)


def function_tool(fn: Callable[..., str]) -> FunctionTool:
    """
    Decorator that wraps a plain function as a FunctionTool.
    Pattern: @function_tool → Agenkit Tool

    In the OpenAI Agents SDK you write:
        @function_tool
        def lookup_order(order_id: str) -> str:
            \"\"\"Look up order status by ID.\"\"\"
            return f"Order {order_id}: shipped"

    Below we implement the same pattern without the openai-agents package.
    """
    return FunctionTool(
        name=fn.__name__,
        description=fn.__doc__ or fn.__name__,
        fn=fn,
    )


# ---------------------------------------------------------------------------
# Handoff (mirrors OAI.handoff())
# ---------------------------------------------------------------------------


@dataclass
class Handoff:
    """
    Routes execution to a different agent based on triage logic.
    Pattern: OAI.handoff(agent) → Agenkit RouterAgent / conditional dispatch

    In the OpenAI Agents SDK:
        agent = Agent(handoffs=[handoff(billing_agent), handoff(tech_agent)])

    When the triage agent produces a HANDOFF: <name> marker, the Runner
    switches to the named specialist agent.
    """

    agent: OAIAgent

    @property
    def name(self) -> str:
        """Return the target agent's name for routing lookups."""
        return self.agent.name


# ---------------------------------------------------------------------------
# RunResult (mirrors OAI.RunResult)
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """
    Outcome of a Runner.run_sync() or Runner.run() call.
    Pattern: OAI.RunResult → Agenkit final message + history

    The OpenAI Agents SDK's RunResult exposes:
        result.final_output  → str   last assistant message
        result.messages      → list  full conversation history
    """

    final_output: str
    messages: list[Message] = field(default_factory=list)


# ---------------------------------------------------------------------------
# OAIAgent (mirrors OAI.Agent)
# ---------------------------------------------------------------------------


@dataclass
class OAIAgent:
    """
    Named agent with instructions, tools, and optional handoff targets.
    Pattern: OAI.Agent → Agenkit Agent (base interface)

    In the OpenAI Agents SDK:
        triage = Agent(
            name="triage",
            instructions="Route requests to the right specialist.",
            handoffs=[handoff(billing_agent), handoff(tech_agent)],
        )

    Here we add an LLM field because Agenkit is LLM-backend-agnostic.
    """

    name: str
    instructions: str
    llm: LLM
    tools: list[FunctionTool] = field(default_factory=list)
    handoffs: list[Handoff] = field(default_factory=list)

    def _handoff_map(self) -> dict[str, OAIAgent]:
        """Return a dict mapping handoff names to target agents."""
        return {h.name: h.agent for h in self.handoffs}

    def _tool_map(self) -> dict[str, FunctionTool]:
        """Return a dict mapping tool names to FunctionTool instances."""
        return {t.name: t for t in self.tools}


# ---------------------------------------------------------------------------
# Runner (mirrors OAI.Runner)
# ---------------------------------------------------------------------------


class Runner:
    """
    Executes OAIAgent instances (mirrors OAI.Runner).
    Pattern: OAI.Runner → Agenkit agent.process() / streaming loop

    The OpenAI Agents SDK exposes:
        Runner.run_sync(agent, input)       → RunResult
        await Runner.run(agent, input)      → async streaming iterator

    Both are implemented below on top of Agenkit's LLM adapter.
    """

    @staticmethod
    def run_sync(agent: OAIAgent, input: str) -> RunResult:
        """
        Execute agent synchronously and return a RunResult.
        Pattern: OAI.Runner.run_sync → asyncio.run(Runner._execute)

        Args:
            agent: Agent to run
            input: Initial user message

        Returns:
            RunResult with final_output and full message list
        """
        return asyncio.get_event_loop().run_until_complete(Runner._execute(agent, input))

    @staticmethod
    async def run(agent: OAIAgent, input: str) -> AsyncIterator[str]:
        """
        Execute agent asynchronously, yielding output tokens as they arrive.
        Pattern: OAI.Runner.run (streaming) → async generator of str chunks

        Args:
            agent: Agent to run
            input: Initial user message

        Yields:
            String tokens / chunks as the agent produces them
        """
        result = await Runner._execute(agent, input)
        # Simulate streaming by yielding words one by one — in production
        # this would use LLM.stream() for real token-by-token delivery.
        for word in result.final_output.split():
            yield word + " "

    @staticmethod
    async def _execute(agent: OAIAgent, input: str) -> RunResult:
        """
        Core execution loop: tool calls and handoff routing.

        The loop mirrors the OpenAI Agents SDK's internal execution:
        1. Build system prompt from agent.instructions + available tools/handoffs
        2. Call LLM; check response for TOOL: or HANDOFF: markers
        3. If TOOL: → execute tool, append result, continue loop
        4. If HANDOFF: → switch to target agent, continue loop
        5. Otherwise → return RunResult with final_output
        """
        messages: list[Message] = [Message(role="user", content=input)]
        current_agent = agent
        max_steps = 10

        for _ in range(max_steps):
            # Build system context listing available tools and handoffs
            tool_names = [t.name for t in current_agent.tools]
            handoff_names = [h.name for h in current_agent.handoffs]

            system_parts = [current_agent.instructions]
            if tool_names:
                system_parts.append(
                    "Available tools: "
                    + ", ".join(tool_names)
                    + ". Call a tool with: TOOL: <name> ARGS: <value>"
                )
            if handoff_names:
                system_parts.append(
                    "Available handoffs: "
                    + ", ".join(handoff_names)
                    + ". Hand off with: HANDOFF: <agent_name>"
                )

            prompt_msgs = [Message(role="system", content="\n".join(system_parts)), *messages]
            response = await current_agent.llm.complete(prompt_msgs)
            reply = cast("str", response.content)
            messages.append(Message(role="assistant", content=reply))

            # Check for TOOL: call
            if "TOOL:" in reply:
                tool_name = reply.split("TOOL:")[1].split("\n")[0].strip().split()[0]
                args_str = ""
                if "ARGS:" in reply:
                    args_str = reply.split("ARGS:")[1].split("\n")[0].strip()
                tool_map = current_agent._tool_map()
                if tool_name in tool_map:
                    tool_result = tool_map[tool_name].call(input=args_str)
                    messages.append(Message(role="tool", content=f"[{tool_name}] {tool_result}"))
                    continue

            # Check for HANDOFF: routing
            if "HANDOFF:" in reply:
                target_name = reply.split("HANDOFF:")[1].split("\n")[0].strip()
                handoff_map = current_agent._handoff_map()
                if target_name in handoff_map:
                    current_agent = handoff_map[target_name]
                    print(f"   → Handing off to: {current_agent.name}")
                    continue

            # No special markers — final answer
            return RunResult(final_output=reply, messages=messages)

        return RunResult(final_output=messages[-1].content or "", messages=messages)


# ---------------------------------------------------------------------------
# Demo examples
# ---------------------------------------------------------------------------


async def example_triage_handoff() -> None:
    """Example 1: Triage agent hands off to specialist agents."""
    print("=" * 60)
    print("Example 1: Triage Agent + Handoff (billing vs tech support)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    billing_agent = OAIAgent(
        name="billing",
        instructions="You are a billing specialist. Help with invoices, payments, and subscriptions.",
        llm=llm,
    )

    tech_agent = OAIAgent(
        name="tech_support",
        instructions="You are a technical support specialist. Help with bugs, errors, and integrations.",
        llm=llm,
    )

    triage_agent = OAIAgent(
        name="triage",
        instructions=(
            "You are a triage agent. Route the user to the right specialist:\n"
            "- billing: for payment, invoice, subscription questions\n"
            "- tech_support: for technical issues, bugs, API questions\n"
            "Always start with: HANDOFF: <agent_name>"
        ),
        llm=llm,
        handoffs=[Handoff(billing_agent), Handoff(tech_agent)],
    )

    print("\n   # OpenAI Agents SDK equivalent:")
    print("   from openai_agents import Agent, Runner, handoff")
    print("   billing = Agent(name='billing', instructions='...')")
    print("   tech    = Agent(name='tech_support', instructions='...')")
    print(
        "   triage  = Agent(name='triage', instructions='...', handoffs=[handoff(billing), handoff(tech)])"
    )
    print("   result  = Runner.run_sync(triage, 'My invoice is wrong')")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import RouterAgent, RouterConfig")
    print("   router = RouterAgent(RouterConfig(agents={'billing': billing, 'tech': tech}))")

    result = Runner.run_sync(triage_agent, "I keep getting a 401 error on the API.")
    print(f"\n   Messages exchanged: {len(result.messages)}")
    print(f"   Final output (truncated): {result.final_output[:80]}...")
    print("   Pattern: OAI.Agent + handoff() → Agenkit RouterAgent / conditional dispatch")


async def example_function_tool() -> None:
    """Example 2: function_tool for mock order DB lookup."""
    print("\n\n" + "=" * 60)
    print("Example 2: function_tool (mock order lookup)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    @function_tool
    def lookup_order(input: str) -> str:
        """Look up an order status by order ID."""
        orders = {
            "ORD-001": "Shipped — arrives 2026-03-20",
            "ORD-002": "Processing — payment pending",
            "ORD-003": "Delivered — 2026-03-10",
        }
        return orders.get(input.strip(), f"Order {input!r} not found")

    @function_tool
    def get_account_balance(input: str) -> str:
        """Retrieve the account balance for a customer email."""
        return f"Account balance for {input}: $142.50"

    support_agent = OAIAgent(
        name="support",
        instructions=(
            "You are a helpful support agent. Use tools when needed.\n"
            "To call a tool: TOOL: <name> ARGS: <argument>"
        ),
        llm=llm,
        tools=[lookup_order, get_account_balance],
    )

    print("\n   # OpenAI Agents SDK equivalent:")
    print("   @function_tool")
    print("   def lookup_order(order_id: str) -> str:")
    print('       """Look up order status by ID."""')
    print("       ...")
    print("   agent = Agent(name='support', tools=[lookup_order])")
    print("   result = Runner.run_sync(agent, 'Where is order ORD-001?')")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import ReActAgent")
    print("   agent = ReActAgent(llm=llm, tools=[Tool('lookup_order', fn=lookup_order)])")

    result = Runner.run_sync(support_agent, "Where is my order ORD-001?")
    print(f"\n   Tool available: {lookup_order.name} — {lookup_order.description}")
    print(f"   Messages exchanged: {len(result.messages)}")
    print(f"   Final output (truncated): {result.final_output[:80]}...")
    print("   Pattern: @function_tool decorator → Agenkit Tool class")


async def example_async_streaming() -> None:
    """Example 3: Async streaming via Runner.run()."""
    print("\n\n" + "=" * 60)
    print("Example 3: Async Streaming (Runner.run)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    agent = OAIAgent(
        name="assistant",
        instructions="You are a helpful assistant. Be concise.",
        llm=llm,
    )

    print("\n   # OpenAI Agents SDK equivalent:")
    print("   async for event in Runner.run(agent, 'Explain streaming in one sentence'):")
    print("       if event.type == 'raw_response_event':")
    print("           print(event.data.delta, end='', flush=True)")
    print()
    print("   # Agenkit equivalent:")
    print("   async for chunk in agent.process_stream(message):")
    print("       print(chunk.content, end='', flush=True)")

    print("\n   Streaming output: ", end="", flush=True)
    async for chunk in Runner.run(agent, "Explain Agenkit in one sentence."):
        print(chunk, end="", flush=True)
    print()
    print("   Pattern: OAI.Runner.run (streaming) → Agenkit agent.process_stream()")


async def main() -> None:
    """Run all MiniOpenAIAgents examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 4 + "MiniOpenAIAgents - OpenAI Agents SDK on Agenkit" + " " * 7 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n   Demonstrate: OpenAI Agents SDK patterns ON TOP of Agenkit")

    await example_triage_handoff()
    await example_function_tool()
    await example_async_streaming()

    print("\n\n" + "=" * 60)
    print("MiniOpenAIAgents Examples Complete")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("   Agenkit covers every core OpenAI Agents SDK concept:")
    print("     - Agent                → OAIAgent (name, instructions, tools, handoffs)")
    print("     - @function_tool       → FunctionTool dataclass / Agenkit Tool")
    print("     - handoff(agent)       → Handoff routing / Agenkit RouterAgent")
    print("     - Runner.run_sync()    → synchronous execution via asyncio.run()")
    print("     - Runner.run()         → async streaming generator")
    print("     - RunResult            → final_output + messages history")

    print("\nMigration guide: docs/migrations/openaiagents-to-agenkit.md")
    print("\nWhy Agenkit over OpenAI Agents SDK?")
    print("   6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   LLM-agnostic — not locked to OpenAI models")
    print("   11+ patterns (ReAct, Sequential, Router, Parallel, ...)")
    print("   OpenTelemetry observability built-in")
    print("   Production middleware: retry, circuit breaker, timeout")


if __name__ == "__main__":
    asyncio.run(main())
