#!/usr/bin/env python3
"""
MiniGoogleADK - Google Agent Development Kit Equivalent Built on Agenkit

Demonstrates how Google ADK's multi-agent composition patterns can be built
ON TOP of Agenkit primitives, showing toolkit philosophy for Google's agent SDK.

Google ADK Key Concepts (Python SDK v0.1+, March 2026):
- Agent: base agent class with name, model, instruction, and tools
- SequentialAgent: runs sub-agents in sequence, passing output as input
- ParallelAgent: runs sub-agents in parallel and collects all results
- LoopAgent: repeats an agent until a stop signal or max_iterations
- @tool / tool decorator: marks a Python function as a callable tool
- InMemorySessionService: stores conversation state keyed by session_id
- Content(parts=[Part(text="...")]): ADK message format (wraps role + text)
- runner.run(agent, user_id, session_id, new_message): execute with session state
- LiteLlm(model="gemini/gemini-2.0-flash"): ADK LLM provider wrapper

Pattern Mappings:
- ADK.Agent                  → Agenkit Agent (base interface)
- ADK.SequentialAgent        → Agenkit SequentialAgent pattern
- ADK.ParallelAgent          → Agenkit ParallelAgent pattern
- ADK.LoopAgent              → Agenkit autonomous agent loop
- ADK.@tool                  → Agenkit Tool class
- ADK.InMemorySessionService → Agenkit InMemoryStorage / ConversationalAgent
- ADK.Content / Part         → Agenkit Message
- ADK.Runner                 → Agenkit agent.process()

Migration guide: docs/migrations/googleadk-to-agenkit.md

Usage: uv run python examples/frameworks/minigoogleadk.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, cast

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM, OpenAILLM


# ---------------------------------------------------------------------------
# Content model (mirrors ADK.Part / ADK.Content)
# ---------------------------------------------------------------------------


@dataclass
class Part:
    """
    Content part (mirrors ADK.Part).
    Pattern: ADK.Part → fragment of a message, typically a text string
    """

    text: str = ""


@dataclass
class Content:
    """
    Message content with role (mirrors ADK.Content).
    Pattern: ADK.Content(parts=[Part(text='...')]) → Agenkit Message(role=..., content=...)
    """

    role: str = "user"
    parts: list[Part] = field(default_factory=list)

    def text(self) -> str:
        """Join all part texts into a single string."""
        return " ".join(p.text for p in self.parts)

    def to_message(self) -> Message:
        """
        Convert to an Agenkit Message.

        Returns:
            Equivalent Agenkit Message
        """
        return Message(role=self.role, content=self.text())

    @classmethod
    def from_text(cls, text: str, role: str = "user") -> "Content":
        """
        Convenience constructor from a plain string.

        Args:
            text: Message text
            role: Message role (default 'user')

        Returns:
            Content wrapping the given text
        """
        return cls(role=role, parts=[Part(text=text)])

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Content(role={self.role!r}, text={self.text()!r})"


# ---------------------------------------------------------------------------
# ADKTool (mirrors ADK @tool decorator result)
# ---------------------------------------------------------------------------


class ADKTool:
    """
    Tool callable from an ADK agent (mirrors ADK tool wrapper).
    Pattern: ADK.@tool function → Agenkit Tool class
    """

    def __init__(self, fn: Callable[..., Any], name: str, description: str) -> None:
        """
        Create a tool from a callable.

        Args:
            fn: Underlying function (sync or async)
            name: Tool name for the agent to reference
            description: Human-readable description
        """
        self._fn = fn
        self.name = name
        self.description = description

    async def call(self, **kwargs: Any) -> str:
        """
        Invoke the tool with keyword arguments.

        Args:
            **kwargs: Arguments forwarded to the underlying function

        Returns:
            String result
        """
        import inspect

        try:
            if inspect.iscoroutinefunction(self._fn):
                result = await self._fn(**kwargs)
            else:
                result = self._fn(**kwargs)
            return str(result)
        except Exception as exc:
            return f"Tool error: {exc}"

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ADKTool(name={self.name!r})"


def adk_tool(description: str = "") -> Callable[[Callable[..., Any]], ADKTool]:
    """
    Decorator to mark a function as an ADK tool (mirrors ADK @tool).
    Pattern: ADK.@tool(description='...') → Agenkit Tool wrapper

    Args:
        description: Human-readable description of the tool

    Returns:
        Decorator that wraps the function as an ADKTool
    """

    def decorator(fn: Callable[..., Any]) -> ADKTool:
        return ADKTool(fn=fn, name=fn.__name__, description=description or (fn.__doc__ or ""))

    return decorator


# ---------------------------------------------------------------------------
# ADKAgent (mirrors ADK.Agent)
# ---------------------------------------------------------------------------


class ADKAgent(Agent):
    """
    Base ADK agent with instruction and optional tools (mirrors ADK.Agent).
    Pattern: ADK.Agent(name, model, instruction, tools) → Agenkit Agent
    """

    def __init__(
        self,
        name: str,
        model: LLM,
        instruction: str = "",
        tools: list[ADKTool] | None = None,
    ) -> None:
        """
        Create an ADK-style agent.

        Args:
            name: Agent identifier
            model: LLM adapter (mirrors ADK LiteLlm or Gemini model)
            instruction: System-level instruction / persona
            tools: Optional list of ADKTool instances
        """
        self._name = name
        self._model = model
        self.instruction = instruction
        self.tools = tools or []

    @property
    def name(self) -> str:
        """Return agent name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        caps = ["llm_completion"]
        if self.tools:
            caps.append("tool_use")
        return caps

    async def run(self, content: Content) -> Content:
        """
        Run the agent on the given content.

        Args:
            content: Input Content (ADK-style)

        Returns:
            Output Content with role 'model'
        """
        prompt_parts = []
        if self.instruction:
            prompt_parts.append(f"Instruction: {self.instruction}")
        if self.tools:
            tool_descs = ", ".join(f"{t.name}: {t.description}" for t in self.tools)
            prompt_parts.append(f"Available tools: {tool_descs}")
        prompt_parts.append(f"Input: {content.text()}")

        prompt = "\n\n".join(prompt_parts)
        response = await self._model.complete([Message(role="user", content=prompt)])
        reply_text = cast(str, response.content)

        return Content(role="model", parts=[Part(text=reply_text)])

    async def process(self, message: Message) -> Message:
        """
        Implement Agenkit Agent.process() by delegating to run().

        Args:
            message: Agenkit Message input

        Returns:
            Agenkit Message response
        """
        content = Content.from_text(cast(str, message.content), role=message.role)
        result = await self.run(content)
        return Message(role="agent", content=result.text(), metadata={"adk_agent": self._name})


# ---------------------------------------------------------------------------
# SequentialADKAgent (mirrors ADK.SequentialAgent)
# ---------------------------------------------------------------------------


class SequentialADKAgent:
    """
    Runs sub-agents in sequence, feeding each output as the next input
    (mirrors ADK.SequentialAgent).
    Pattern: ADK.SequentialAgent → Agenkit SequentialAgent pattern
    """

    def __init__(self, name: str, sub_agents: list[ADKAgent]) -> None:
        """
        Create a sequential multi-agent pipeline.

        Args:
            name: Pipeline name
            sub_agents: Ordered list of agents to run in sequence
        """
        self.name = name
        self.sub_agents = sub_agents

    async def run(self, content: Content) -> Content:
        """
        Run all sub-agents in sequence.

        Each agent's output becomes the next agent's input.

        Args:
            content: Initial input Content

        Returns:
            Final Content after all agents have processed
        """
        current = content
        execution_trace: list[str] = []

        for agent in self.sub_agents:
            current = await agent.run(current)
            execution_trace.append(agent.name)

        # Embed trace in metadata via a Part annotation (ADK pattern)
        trace_note = f" [pipeline: {' → '.join(execution_trace)}]"
        if current.parts:
            current.parts[-1].text += trace_note
        else:
            current.parts.append(Part(text=trace_note))

        return current

    def __repr__(self) -> str:
        """Return string representation."""
        return f"SequentialADKAgent(name={self.name!r}, agents={[a.name for a in self.sub_agents]})"


# ---------------------------------------------------------------------------
# ParallelADKAgent (mirrors ADK.ParallelAgent)
# ---------------------------------------------------------------------------


class ParallelADKAgent:
    """
    Runs sub-agents in parallel and collects all results
    (mirrors ADK.ParallelAgent).
    Pattern: ADK.ParallelAgent → asyncio.gather over Agenkit Agents
    """

    def __init__(self, name: str, sub_agents: list[ADKAgent]) -> None:
        """
        Create a parallel multi-agent executor.

        Args:
            name: Executor name
            sub_agents: Agents to run concurrently
        """
        self.name = name
        self.sub_agents = sub_agents

    async def run(self, content: Content) -> Content:
        """
        Run all sub-agents in parallel and merge their outputs.

        Args:
            content: Shared input Content sent to every sub-agent

        Returns:
            Merged Content combining all agent outputs
        """
        results = await asyncio.gather(*[agent.run(content) for agent in self.sub_agents])

        merged_parts: list[Part] = []
        for agent, result in zip(self.sub_agents, results):
            merged_parts.append(Part(text=f"[{agent.name}]: {result.text()}"))

        return Content(role="model", parts=merged_parts)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ParallelADKAgent(name={self.name!r}, agents={[a.name for a in self.sub_agents]})"


# ---------------------------------------------------------------------------
# LoopADKAgent (mirrors ADK.LoopAgent)
# ---------------------------------------------------------------------------


class LoopADKAgent:
    """
    Repeats an agent until a stop condition is met (mirrors ADK.LoopAgent).
    Pattern: ADK.LoopAgent → Agenkit autonomous loop with exit condition
    Stops when the response text contains 'STOP' or max_iterations is reached.
    """

    def __init__(self, name: str, agent: ADKAgent, max_iterations: int = 5) -> None:
        """
        Create a looping agent wrapper.

        Args:
            name: Loop name
            agent: Agent to repeat
            max_iterations: Hard cap on repetitions
        """
        self.name = name
        self.agent = agent
        self.max_iterations = max_iterations

    async def run(self, content: Content) -> Content:
        """
        Run the agent in a loop until 'STOP' appears or max_iterations is hit.

        Args:
            content: Initial input Content

        Returns:
            Content from the final iteration
        """
        current = content
        iterations_run = 0

        for iteration in range(self.max_iterations):
            iterations_run = iteration + 1
            current = await self.agent.run(current)

            # Stop condition: response contains the sentinel word
            if "STOP" in current.text().upper():
                break

        # Annotate with loop metadata
        current.parts.append(
            Part(text=f" [loop: {iterations_run}/{self.max_iterations} iterations]")
        )
        return current

    def __repr__(self) -> str:
        """Return string representation."""
        return f"LoopADKAgent(name={self.name!r}, max_iterations={self.max_iterations})"


# ---------------------------------------------------------------------------
# InMemorySessionService (mirrors ADK.InMemorySessionService)
# ---------------------------------------------------------------------------


class InMemorySessionService:
    """
    In-memory session persistence keyed by (user_id, session_id)
    (mirrors ADK.InMemorySessionService).
    Pattern: ADK.InMemorySessionService → Agenkit InMemoryStorage / conversation state
    """

    def __init__(self) -> None:
        """Create an empty session store."""
        self._sessions: dict[str, list[Content]] = {}

    def _key(self, user_id: str, session_id: str) -> str:
        """Build a composite key from user and session IDs."""
        return f"{user_id}::{session_id}"

    def create_session(self, user_id: str, session_id: str) -> None:
        """
        Initialize an empty session.

        Args:
            user_id: User identifier
            session_id: Session identifier
        """
        key = self._key(user_id, session_id)
        if key not in self._sessions:
            self._sessions[key] = []

    def get_history(self, user_id: str, session_id: str) -> list[Content]:
        """
        Retrieve all Content objects for a session.

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            List of Content objects in chronological order
        """
        return list(self._sessions.get(self._key(user_id, session_id), []))

    def append(self, user_id: str, session_id: str, content: Content) -> None:
        """
        Append a Content object to a session's history.

        Args:
            user_id: User identifier
            session_id: Session identifier
            content: Content to append
        """
        key = self._key(user_id, session_id)
        if key not in self._sessions:
            self._sessions[key] = []
        self._sessions[key].append(content)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"InMemorySessionService(sessions={list(self._sessions)})"


# ---------------------------------------------------------------------------
# Runner (mirrors ADK.Runner)
# ---------------------------------------------------------------------------


class Runner:
    """
    Agent runner that integrates session management (mirrors ADK.Runner).
    Pattern: ADK.Runner(agent, session_service) → Agenkit agent.process() + storage
    """

    def __init__(
        self,
        agent: ADKAgent | SequentialADKAgent | ParallelADKAgent | LoopADKAgent,
        session_service: InMemorySessionService,
    ) -> None:
        """
        Create a runner.

        Args:
            agent: Agent or composite agent to run
            session_service: Session storage backend
        """
        self._agent = agent
        self._session_service = session_service

    async def run(
        self,
        user_id: str,
        session_id: str,
        new_message: Content,
    ) -> Content:
        """
        Execute the agent with session context.

        Appends the user message, runs the agent, persists the response.

        Args:
            user_id: User identifier
            session_id: Session identifier
            new_message: Incoming Content from the user

        Returns:
            Agent's response Content
        """
        self._session_service.create_session(user_id, session_id)
        self._session_service.append(user_id, session_id, new_message)

        response = await self._agent.run(new_message)

        self._session_service.append(user_id, session_id, response)
        return response

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Runner(agent={self._agent!r})"


# ---------------------------------------------------------------------------
# Example tool definitions
# ---------------------------------------------------------------------------


@adk_tool(description="Search the web for information on a topic")
def web_search(query: str) -> str:
    """Search the web for information on a topic."""
    # Mock implementation — returns simulated search results
    return f"Search results for '{query}': [result1, result2, result3]"


@adk_tool(description="Fetch and summarize a web page by URL")
def fetch_page(url: str) -> str:
    """Fetch and summarize a web page by URL."""
    return f"Page content from {url}: [summary of page content]"


@adk_tool(description="Format text as a structured report")
def format_report(content: str, title: str = "Report") -> str:
    """Format text as a structured report."""
    return f"# {title}\n\n{content}\n\n---\nGenerated by format_report tool"


# ---------------------------------------------------------------------------
# Demo examples
# ---------------------------------------------------------------------------


async def example_single_agent() -> None:
    """Example 1: Single ADKAgent with tools."""
    print("=" * 60)
    print("Example 1: Single ADKAgent with Tools")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    agent = ADKAgent(
        name="research_agent",
        model=llm,
        instruction="You are a research assistant. Use available tools to answer questions.",
        tools=[web_search, fetch_page],
    )

    question = Content.from_text("What are the latest developments in quantum computing?")

    print("\n   agent = ADKAgent(")
    print("       name='research_agent',")
    print("       model=OpenAILLM(model='gpt-4o-mini', api_key='test-key'),")
    print("       instruction='You are a research assistant...',")
    print("       tools=[web_search, fetch_page],")
    print("   )")
    print("   question = Content(parts=[Part(text='What are the latest developments...')])")
    print("   result = await agent.run(question)")

    print(f"\n   Agent name: {agent.name}")
    print(f"   Capabilities: {agent.capabilities}")
    print(f"   Tools: {[t.name for t in agent.tools]}")

    # Show tool invocation directly
    tool_result = await web_search.call(query="quantum computing 2026")
    print(f"\n   Direct tool call: web_search(query='quantum computing 2026')")
    print(f"   → {tool_result!r}")

    print("\n   Pattern: ADK.Agent → Agenkit Agent with instruction + tool list")
    print("   ADK.Content/Part → Agenkit Message (role + content string)")


async def example_sequential_agent() -> None:
    """Example 2: SequentialADKAgent for researcher → writer pipeline."""
    print("\n\n" + "=" * 60)
    print("Example 2: SequentialADKAgent (Researcher → Writer Pipeline)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    researcher = ADKAgent(
        name="researcher",
        model=llm,
        instruction="You are a researcher. Gather and summarize information on the topic.",
        tools=[web_search],
    )

    writer = ADKAgent(
        name="writer",
        model=llm,
        instruction="You are a technical writer. Transform research notes into a polished article.",
        tools=[format_report],
    )

    pipeline = SequentialADKAgent(
        name="research_pipeline",
        sub_agents=[researcher, writer],
    )

    print("\n   researcher = ADKAgent(name='researcher', model=llm, tools=[web_search])")
    print("   writer     = ADKAgent(name='writer',     model=llm, tools=[format_report])")
    print("   pipeline   = SequentialADKAgent(name='research_pipeline',")
    print("                    sub_agents=[researcher, writer])")
    print("   result = await pipeline.run(Content.from_text('Write about AI agents'))")
    print(f"\n   Pipeline: {pipeline}")
    print("\n   Pattern: ADK.SequentialAgent → each sub-agent processes the previous output")
    print("   Agenkit: chain agent.process() calls; output Message feeds next input")


async def example_parallel_agent() -> None:
    """Example 3: ParallelADKAgent with specialist agents."""
    print("\n\n" + "=" * 60)
    print("Example 3: ParallelADKAgent (Three Specialists in Parallel)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    tech_analyst = ADKAgent(
        name="tech_analyst",
        model=llm,
        instruction="You are a technology analyst. Analyze technical aspects.",
    )

    market_analyst = ADKAgent(
        name="market_analyst",
        model=llm,
        instruction="You are a market analyst. Analyze market trends and business impact.",
    )

    risk_analyst = ADKAgent(
        name="risk_analyst",
        model=llm,
        instruction="You are a risk analyst. Identify risks and mitigation strategies.",
    )

    panel = ParallelADKAgent(
        name="analyst_panel",
        sub_agents=[tech_analyst, market_analyst, risk_analyst],
    )

    print("\n   tech_analyst   = ADKAgent(name='tech_analyst',   ...)")
    print("   market_analyst = ADKAgent(name='market_analyst', ...)")
    print("   risk_analyst   = ADKAgent(name='risk_analyst',   ...)")
    print("   panel = ParallelADKAgent(name='analyst_panel',")
    print("               sub_agents=[tech_analyst, market_analyst, risk_analyst])")
    print("   results = await panel.run(Content.from_text('Analyze autonomous vehicles'))")
    print(f"\n   Panel: {panel}")
    print("\n   Pattern: ADK.ParallelAgent → asyncio.gather over Agenkit Agents")
    print("   All sub-agents receive the same input; outputs merged into one Content")


async def example_loop_agent() -> None:
    """Example 4: LoopADKAgent for iterative refinement."""
    print("\n\n" + "=" * 60)
    print("Example 4: LoopADKAgent (Iterative Refinement)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    refiner = ADKAgent(
        name="refiner",
        model=llm,
        instruction=(
            "You are an iterative refiner. Improve the text quality each pass. "
            "When the text is satisfactory, respond with 'STOP' at the start."
        ),
    )

    loop_agent = LoopADKAgent(
        name="refinement_loop",
        agent=refiner,
        max_iterations=3,
    )

    print("\n   refiner = ADKAgent(")
    print("       name='refiner',")
    print("       instruction='... When satisfied, respond with STOP ...',")
    print("   )")
    print("   loop_agent = LoopADKAgent(name='refinement_loop', agent=refiner, max_iterations=3)")
    print("   result = await loop_agent.run(Content.from_text('Draft: AI is important.'))")
    print(f"\n   LoopAgent: {loop_agent}")
    print("\n   Pattern: ADK.LoopAgent → Agenkit autonomous loop with stop sentinel")
    print("   Loop exits when response contains 'STOP' OR max_iterations reached")
    print("   Mirrors ADK's exit_condition / escalation_agent mechanism")


async def example_session_runner() -> None:
    """Example 5: InMemorySessionService + Runner for multi-turn sessions."""
    print("\n\n" + "=" * 60)
    print("Example 5: InMemorySessionService + Runner (Session Management)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    agent = ADKAgent(
        name="chat_agent",
        model=llm,
        instruction="You are a helpful assistant. Maintain context across turns.",
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, session_service=session_service)

    user_id = "user_42"
    session_id = "session_abc"

    session_service.create_session(user_id, session_id)

    turn1 = Content.from_text("My name is Alex. What is machine learning?")
    turn2 = Content.from_text("Can you give me a simple example?")
    turn3 = Content.from_text("How does it relate to what I just asked?")

    print("\n   session_service = InMemorySessionService()")
    print("   runner = Runner(agent=agent, session_service=session_service)")
    print(f"   runner.run(user_id={user_id!r}, session_id={session_id!r}, new_message=turn1)")
    print(f"   runner.run(user_id={user_id!r}, session_id={session_id!r}, new_message=turn2)")
    print(f"   runner.run(user_id={user_id!r}, session_id={session_id!r}, new_message=turn3)")

    # Demonstrate session state accumulation (without real LLM calls)
    session_service.append(user_id, session_id, turn1)
    session_service.append(
        user_id, session_id, Content.from_text("Machine learning is...", role="model")
    )
    session_service.append(user_id, session_id, turn2)

    history = session_service.get_history(user_id, session_id)
    print(f"\n   Session history after 2 turns: {len(history)} Content objects")
    print(f"   Roles: {[c.role for c in history]}")
    print(f"\n   Runner: {runner}")
    print(f"   SessionService: {session_service}")

    print("\n   Pattern: ADK.InMemorySessionService → Agenkit ConversationalAgent storage")
    print("   ADK.Runner.run() → Agenkit agent.process() wrapped with session append")
    print("   Session keyed by (user_id, session_id) for multi-user, multi-session support")


async def main() -> None:
    """Run all MiniGoogleADK examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + "   MiniGoogleADK - Google ADK Built on Agenkit        " + "║")
    print("╚" + "=" * 58 + "╝")
    print("\nDemonstrate: Google Agent Development Kit patterns on Agenkit")

    await example_single_agent()
    await example_sequential_agent()
    await example_parallel_agent()
    await example_loop_agent()
    await example_session_runner()

    print("\n\n" + "=" * 60)
    print("MiniGoogleADK Examples Complete")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("   Agenkit supports Google ADK's full multi-agent composition model")
    print("   ADK patterns map directly to Agenkit primitives:")
    print("     - ADK.Agent                  → Agenkit Agent base interface")
    print("     - ADK.SequentialAgent        → Agenkit SequentialAgent pattern")
    print("     - ADK.ParallelAgent          → asyncio.gather over Agents")
    print("     - ADK.LoopAgent              → Autonomous loop with stop sentinel")
    print("     - ADK.@tool                  → Agenkit Tool class")
    print("     - ADK.Content/Part           → Agenkit Message(role, content)")
    print("     - ADK.InMemorySessionService → Agenkit ConversationalAgent storage")
    print("     - ADK.Runner                 → agent.process() + session persistence")

    print("\nMigration guide: docs/migrations/googleadk-to-agenkit.md")
    print("\nWhy Agenkit over Google ADK?")
    print("   6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   No Google Cloud / Vertex AI vendor dependency")
    print("   Any LLM provider (not just Gemini / Vertex)")
    print("   11+ patterns beyond ADK's 4 composition primitives")
    print("   OpenTelemetry observability (not just Cloud Trace)")
    print("   18x faster in Go for high-throughput production workloads")


if __name__ == "__main__":
    asyncio.run(main())
