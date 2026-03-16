#!/usr/bin/env python3
"""
MiniLangGraph - LangGraph Equivalent Built on Agenkit

Demonstrates how LangGraph's StateGraph-based workflow patterns can be built
ON TOP of Agenkit primitives, showing toolkit philosophy for graph-based orchestration.

Pattern Mappings:
  LangGraph.StateGraph            → Agenkit graph-based orchestration (custom)
  LangGraph.add_node              → Agenkit patterns.GraphExecutor nodes
  LangGraph.add_conditional_edges → Agenkit conditional routing
  LangGraph.ToolNode              → Agenkit Tool executor
  LangGraph.MemorySaver           → Agenkit checkpointing
  LangGraph.MessagesState         → Agenkit conversation history (GraphState)

Migration guide: docs/migrations/langgraph-to-agenkit.md

Usage: uv run python examples/frameworks/minilanggraph.py
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM, OpenAILLM

# Sentinel value for terminal nodes — mirrors LangGraph END constant
END = "__end__"


# ---------------------------------------------------------------------------
# GraphState (mirrors LangGraph.MessagesState)
# ---------------------------------------------------------------------------


@dataclass
class GraphState:
    """
    Shared typed state passed between graph nodes (mirrors LangGraph.MessagesState).
    Pattern: LangGraph.MessagesState → Agenkit conversation history + routing metadata

    In LangGraph, state is a TypedDict; here we use a dataclass for type safety.
    The 'next' field mirrors LangGraph's built-in routing key used with
    add_conditional_edges to determine which node runs next.
    """

    messages: list[Message] = field(default_factory=list)
    next: str = ""  # routing key — set by nodes or condition functions
    metadata: dict[str, Any] = field(default_factory=dict)

    def last_content(self) -> str:
        """Return the content of the most recent message, or empty string."""
        if not self.messages:
            return ""
        return cast(str, self.messages[-1].content)

    def add_message(self, role: str, content: str, **meta: Any) -> None:
        """Append a message to the state."""
        self.messages.append(Message(role=role, content=content, metadata=meta))


# Type aliases — mirrors LangGraph node/condition signatures
NodeFn = Callable[[GraphState], GraphState]
ConditionFn = Callable[[GraphState], str]  # returns node name or END


# ---------------------------------------------------------------------------
# StateGraph (mirrors LangGraph.StateGraph)
# ---------------------------------------------------------------------------


class StateGraph:
    """
    Directed graph whose nodes share a typed state dict (mirrors LangGraph.StateGraph).
    Pattern: LangGraph.StateGraph → Agenkit custom graph orchestration

    In LangGraph you write:
        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent_fn)
        graph.add_edge("agent", END)
        graph.set_entry_point("agent")
        app = graph.compile()
        result = app.invoke({"messages": [...]})

    Below we implement the same API directly on Agenkit primitives.
    """

    def __init__(self) -> None:
        """Create an empty state graph."""
        self._nodes: dict[str, NodeFn] = {}
        self._edges: dict[str, str] = {}  # unconditional: from → to
        self._conditional: dict[str, tuple[ConditionFn, dict[str, str]]] = {}
        self._entry: str | None = None

    def add_node(self, name: str, fn: NodeFn) -> "StateGraph":
        """
        Register a node (mirrors LangGraph.add_node).

        Args:
            name: Node identifier
            fn: Callable that takes GraphState and returns updated GraphState

        Returns:
            self (fluent API)
        """
        self._nodes[name] = fn
        return self

    def add_edge(self, from_node: str, to_node: str) -> "StateGraph":
        """
        Add an unconditional edge (mirrors LangGraph.add_edge).

        Args:
            from_node: Source node name
            to_node: Destination node name or END

        Returns:
            self (fluent API)
        """
        self._edges[from_node] = to_node
        return self

    def add_conditional_edges(
        self,
        from_node: str,
        condition: ConditionFn,
        mapping: dict[str, str],
    ) -> "StateGraph":
        """
        Add conditional routing from a node (mirrors LangGraph.add_conditional_edges).

        The condition function receives the current state and returns a string key.
        The mapping dict translates that key to the actual next node name (or END).

        Args:
            from_node: Source node name
            condition: Function that inspects state and returns a routing key
            mapping: Dict mapping routing keys to node names / END

        Returns:
            self (fluent API)
        """
        self._conditional[from_node] = (condition, mapping)
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        """
        Set the graph's entry node (mirrors LangGraph.set_entry_point).

        Args:
            name: Entry node name

        Returns:
            self (fluent API)
        """
        self._entry = name
        return self

    def compile(self) -> "CompiledGraph":
        """
        Compile the graph into a runnable (mirrors LangGraph.compile()).

        Returns:
            CompiledGraph ready to invoke
        """
        if self._entry is None:
            raise ValueError("Graph has no entry point — call set_entry_point() first")
        return CompiledGraph(
            nodes=dict(self._nodes),
            edges=dict(self._edges),
            conditional=dict(self._conditional),
            entry=self._entry,
        )


# ---------------------------------------------------------------------------
# CompiledGraph (mirrors LangGraph compiled app)
# ---------------------------------------------------------------------------


class CompiledGraph:
    """
    Compiled, runnable graph (mirrors LangGraph CompiledGraph / Pregel).
    Pattern: LangGraph compiled app → Agenkit custom graph executor
    """

    def __init__(
        self,
        nodes: dict[str, NodeFn],
        edges: dict[str, str],
        conditional: dict[str, tuple[ConditionFn, dict[str, str]]],
        entry: str,
        max_steps: int = 20,
    ) -> None:
        """
        Create compiled graph.

        Args:
            nodes: Registered node functions
            edges: Unconditional edges
            conditional: Conditional edge routing
            entry: Entry node name
            max_steps: Maximum execution steps (prevents infinite loops)
        """
        self._nodes = nodes
        self._edges = edges
        self._conditional = conditional
        self._entry = entry
        self._max_steps = max_steps

    def invoke(self, initial_state: dict[str, Any]) -> GraphState:
        """
        Run the graph synchronously (mirrors LangGraph CompiledGraph.invoke).

        Internally calls _run via asyncio.  For async callers use ainvoke().

        Args:
            initial_state: Dict matching GraphState fields

        Returns:
            Final GraphState after execution
        """
        return asyncio.get_event_loop().run_until_complete(self.ainvoke(initial_state))

    async def ainvoke(self, initial_state: dict[str, Any]) -> GraphState:
        """
        Run the graph asynchronously.

        Args:
            initial_state: Dict matching GraphState fields

        Returns:
            Final GraphState after execution
        """
        state = GraphState(
            messages=initial_state.get("messages", []),
            next=initial_state.get("next", ""),
            metadata=initial_state.get("metadata", {}),
        )

        current = self._entry
        execution_path: list[str] = []

        for _ in range(self._max_steps):
            if current == END or current not in self._nodes:
                break

            execution_path.append(current)
            node_fn = self._nodes[current]

            # Support both sync and async node functions
            result = node_fn(state)
            if asyncio.iscoroutine(result):
                state = await result
            else:
                state = result

            # Determine next node
            next_node: str = END

            if current in self._conditional:
                condition_fn, mapping = self._conditional[current]
                routing_key = condition_fn(state)
                next_node = mapping.get(routing_key, END)
            elif current in self._edges:
                next_node = self._edges[current]

            current = next_node

        state.metadata["execution_path"] = execution_path
        return state


# ---------------------------------------------------------------------------
# MemorySaver (mirrors LangGraph.MemorySaver)
# ---------------------------------------------------------------------------


class MemorySaver:
    """
    In-memory state persistence across graph runs (mirrors LangGraph.MemorySaver).
    Pattern: LangGraph.MemorySaver → Agenkit checkpointing

    LangGraph usage:
        memory = MemorySaver()
        app = graph.compile(checkpointer=memory)
        app.invoke(..., config={"configurable": {"thread_id": "42"}})

    Here we expose save/load explicitly for clarity.
    """

    def __init__(self) -> None:
        """Create an empty memory store."""
        self._store: dict[str, GraphState] = {}

    def save(self, thread_id: str, state: GraphState) -> None:
        """
        Persist state for a thread.

        Args:
            thread_id: Conversation / session identifier
            state: GraphState to persist
        """
        self._store[thread_id] = state

    def load(self, thread_id: str) -> GraphState | None:
        """
        Load persisted state for a thread.

        Args:
            thread_id: Conversation / session identifier

        Returns:
            Saved GraphState or None if not found
        """
        return self._store.get(thread_id)

    def list_threads(self) -> list[str]:
        """Return all saved thread IDs."""
        return list(self._store.keys())


# ---------------------------------------------------------------------------
# ToolNode helper (mirrors LangGraph.ToolNode)
# ---------------------------------------------------------------------------


@dataclass
class SimpleTool:
    """Lightweight tool for use inside ToolNode."""

    name: str
    description: str
    fn: Callable[..., str]

    def call(self, input: str) -> str:
        """Execute the tool with a string input."""
        return self.fn(input)


class ToolNode:
    """
    Graph node that executes tool calls embedded in the last message.
    Pattern: LangGraph.ToolNode → Agenkit Tool executor node

    LangGraph's ToolNode reads AIMessage.tool_calls and runs matching tools.
    Here we look for TOOL: <name> INPUT: <value> in the last message content.
    """

    def __init__(self, tools: list[SimpleTool]) -> None:
        """
        Create a tool node.

        Args:
            tools: Available tools
        """
        self._tools = {t.name: t for t in tools}

    def __call__(self, state: GraphState) -> GraphState:
        """Execute tool call found in last message, append result."""
        content = state.last_content()
        result = "[no tool call detected]"

        if "TOOL:" in content:
            tool_name = content.split("TOOL:")[1].split("\n")[0].strip()
            tool_input = ""
            if "INPUT:" in content:
                tool_input = content.split("INPUT:")[1].split("\n")[0].strip()

            if tool_name in self._tools:
                result = self._tools[tool_name].call(tool_input)
            else:
                result = f"Error: tool '{tool_name}' not found"

        state.add_message("tool", result, tool_result=True)
        return state


# ---------------------------------------------------------------------------
# Demo node helpers
# ---------------------------------------------------------------------------


def make_llm_node(llm: LLM, system_prompt: str, node_name: str) -> NodeFn:
    """
    Build an async node function that calls an LLM and appends the response.

    Args:
        llm: LLM adapter
        system_prompt: System instructions for this node
        node_name: Used in metadata

    Returns:
        NodeFn suitable for StateGraph.add_node
    """

    async def _node(state: GraphState) -> GraphState:
        prompt = system_prompt + "\n\n" + state.last_content()
        response = await llm.complete([Message(role="user", content=prompt)])
        state.add_message(
            "assistant",
            cast(str, response.content),
            node=node_name,
        )
        return state

    return _node


# ---------------------------------------------------------------------------
# Demo examples
# ---------------------------------------------------------------------------


async def example_simple_graph() -> None:
    """Example 1: Two-node linear graph — preprocess → generate."""
    print("=" * 60)
    print("Example 1: Simple 2-Node Graph (preprocess → generate)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    def preprocess_node(state: GraphState) -> GraphState:
        """Normalize and clean the input text."""
        raw = state.last_content().strip().lower()
        state.add_message("system", f"[preprocessed] {raw}", node="preprocess")
        return state

    generate_node = make_llm_node(llm, "Generate a helpful response.", "generate")

    graph = (
        StateGraph()
        .add_node("preprocess", preprocess_node)
        .add_node("generate", generate_node)
        .add_edge("preprocess", "generate")
        .add_edge("generate", END)
        .set_entry_point("preprocess")
        .compile()
    )

    print("\n   # LangGraph-style API:")
    print("   graph = StateGraph(MessagesState)")
    print("   graph.add_node('preprocess', preprocess_fn)")
    print("   graph.add_node('generate', generate_fn)")
    print("   graph.add_edge('preprocess', 'generate')")
    print("   graph.add_edge('generate', END)")
    print("   graph.set_entry_point('preprocess')")
    print("   app = graph.compile()")
    print("   result = app.invoke({'messages': [HumanMessage(content='Hello')]})")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import SequentialAgent")
    print("   pipeline = SequentialAgent([preprocess_agent, generate_agent])")
    print("   result = await pipeline.process(message)")

    state = await graph.ainvoke({"messages": [Message(role="user", content="Tell me about Agenkit")]})
    path = state.metadata.get("execution_path", [])
    print(f"\n   Execution path: {' → '.join(path)} → END")
    print("   Pattern: LangGraph.StateGraph → Agenkit SequentialAgent / custom graph")


async def example_conditional_routing() -> None:
    """Example 2: Conditional routing based on intent classification."""
    print("\n\n" + "=" * 60)
    print("Example 2: Conditional Routing (classify_intent → branch)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    def classify_intent(state: GraphState) -> GraphState:
        """Classify message intent to set routing key."""
        content = state.last_content().lower()
        intent = "creative"
        if any(kw in content for kw in ("what is", "how does", "define", "explain")):
            intent = "factual"
        elif content.strip() == "":
            intent = "empty"
        state.next = intent
        state.add_message("system", f"[intent: {intent}]", node="classify")
        return state

    factual_node = make_llm_node(llm, "Answer this factual question accurately.", "factual")
    creative_node = make_llm_node(llm, "Respond creatively and imaginatively.", "creative")

    def route_by_intent(state: GraphState) -> str:
        """Condition function: return the intent stored in state.next."""
        return state.next

    graph = (
        StateGraph()
        .add_node("classify_intent", classify_intent)
        .add_node("answer_factual", factual_node)
        .add_node("answer_creative", creative_node)
        .add_conditional_edges(
            "classify_intent",
            route_by_intent,
            {
                "factual": "answer_factual",
                "creative": "answer_creative",
                "empty": END,
            },
        )
        .add_edge("answer_factual", END)
        .add_edge("answer_creative", END)
        .set_entry_point("classify_intent")
        .compile()
    )

    print("\n   # LangGraph-style API:")
    print("   graph.add_conditional_edges(")
    print("       'classify_intent',")
    print("       route_by_intent,   # returns 'factual' | 'creative' | END")
    print("       {'factual': 'answer_factual', 'creative': 'answer_creative', 'empty': END}")
    print("   )")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import RouterAgent, RouterConfig")
    print("   router = RouterAgent(RouterConfig(")
    print("       classifier=intent_classifier,")
    print("       agents={'factual': factual_agent, 'creative': creative_agent},")
    print("   ))")
    print("   result = await router.process(message)")

    factual_state = await graph.ainvoke(
        {"messages": [Message(role="user", content="What is Agenkit?")]}
    )
    creative_state = await graph.ainvoke(
        {"messages": [Message(role="user", content="Write a poem about agents")]}
    )
    print(f"\n   'What is Agenkit?' → path: {' → '.join(factual_state.metadata.get('execution_path', []))}")
    print(f"   'Write a poem...'  → path: {' → '.join(creative_state.metadata.get('execution_path', []))}")
    print("   Pattern: LangGraph.add_conditional_edges → Agenkit RouterAgent / conditional routing")


async def example_agent_tool_loop() -> None:
    """Example 3: Agent ↔ ToolNode cycle (LangGraph agent loop pattern)."""
    print("\n\n" + "=" * 60)
    print("Example 3: Agent Loop with ToolNode (agent → tools → agent)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    calculator = SimpleTool(
        name="calculator",
        description="Evaluate arithmetic",
        fn=lambda expr: str(eval("".join(c for c in expr if c in "0123456789+-*/(). "))),  # noqa: S307
    )
    search = SimpleTool(
        name="search",
        description="Search the web",
        fn=lambda q: f"[Search results for '{q}']",
    )

    tool_node = ToolNode(tools=[calculator, search])

    agent_node = make_llm_node(
        llm,
        (
            "You are a helpful assistant. If you need a tool, respond with:\n"
            "TOOL: <name>\nINPUT: <value>\n"
            "Otherwise give your final answer."
        ),
        "agent",
    )

    def should_continue(state: GraphState) -> str:
        """Route: continue to tools if last message has a tool call, else end."""
        if "TOOL:" in state.last_content():
            return "continue"
        return "end"

    graph = (
        StateGraph()
        .add_node("agent", agent_node)
        .add_node("tools", tool_node)
        .add_conditional_edges(
            "agent",
            should_continue,
            {"continue": "tools", "end": END},
        )
        .add_edge("tools", "agent")
        .set_entry_point("agent")
        .compile()
    )

    print("\n   # LangGraph-style API (canonical agent loop):")
    print("   graph.add_node('agent', call_model)")
    print("   graph.add_node('tools', ToolNode(tools))")
    print("   graph.add_conditional_edges('agent', should_continue, {'continue': 'tools', 'end': END})")
    print("   graph.add_edge('tools', 'agent')  # cycle back")
    print("   graph.set_entry_point('agent')")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import ReActAgent")
    print("   agent = ReActAgent(llm=llm, tools=[calculator, search])")
    print("   result = await agent.process(message)")

    state = await graph.ainvoke(
        {"messages": [Message(role="user", content="What is 144 / 12?")]}
    )
    path = state.metadata.get("execution_path", [])
    print(f"\n   Execution path: {' → '.join(path + ['END'])}")
    print("   Pattern: LangGraph agent loop → Agenkit ReActAgent (reason+act+observe)")
    print("   Cycle: agent → ToolNode → agent → ... → END (when no more tool calls)")


async def example_memory_saver() -> None:
    """Example 4: MemorySaver — persist and resume graph state."""
    print("\n\n" + "=" * 60)
    print("Example 4: MemorySaver (state persistence across runs)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")
    memory = MemorySaver()

    chat_node = make_llm_node(llm, "Continue the conversation helpfully.", "chat")

    graph = (
        StateGraph()
        .add_node("chat", chat_node)
        .add_edge("chat", END)
        .set_entry_point("chat")
        .compile()
    )

    thread_id = "user-session-42"

    # First run
    state1 = await graph.ainvoke(
        {"messages": [Message(role="user", content="My name is Alex.")]}
    )
    memory.save(thread_id, state1)

    # Reload state and continue
    saved = memory.load(thread_id)
    assert saved is not None  # noqa: S101 — demo assertion
    saved.add_message("user", "What is my name?")
    state2 = await graph.ainvoke(
        {
            "messages": saved.messages,
            "metadata": saved.metadata,
        }
    )
    memory.save(thread_id, state2)

    print("\n   # LangGraph-style API:")
    print("   memory = MemorySaver()")
    print("   app = graph.compile(checkpointer=memory)")
    print("   config = {'configurable': {'thread_id': 'user-session-42'}}")
    print("   app.invoke({'messages': [HumanMessage('My name is Alex.')]}, config)")
    print("   app.invoke({'messages': [HumanMessage('What is my name?')]}, config)  # resumes!")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import ConversationalAgent")
    print("   agent = ConversationalAgent(llm_client=llm_client, max_history=10)")
    print("   await agent.process(Message(role='user', content='My name is Alex.'))")
    print("   await agent.process(Message(role='user', content='What is my name?'))  # remembers!")

    print(f"\n   Thread '{thread_id}' — messages after 2 runs: {len(state2.messages)}")
    print(f"   Saved threads: {memory.list_threads()}")
    print("   Pattern: LangGraph.MemorySaver → Agenkit ConversationalAgent (built-in history)")
    print("   LangGraph externalizes checkpointing; Agenkit bakes it into ConversationalAgent.")


async def main() -> None:
    """Run all MiniLangGraph examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 7 + "MiniLangGraph - LangGraph Built on Agenkit" + " " * 8 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n   Demonstrate: LangGraph StateGraph patterns ON TOP of Agenkit")

    await example_simple_graph()
    await example_conditional_routing()
    await example_agent_tool_loop()
    await example_memory_saver()

    print("\n\n" + "=" * 60)
    print("MiniLangGraph Examples Complete")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("   Agenkit covers every core LangGraph concept:")
    print("     - StateGraph / CompiledGraph → custom graph executor")
    print("     - add_node / add_edge        → explicit wiring")
    print("     - add_conditional_edges      → RouterAgent / condition functions")
    print("     - ToolNode                   → Agenkit Tool executor")
    print("     - MemorySaver                → ConversationalAgent (built-in history)")
    print("     - MessagesState              → GraphState / message list")
    print("     - Agent loop (ReAct)         → agenkit.patterns.ReActAgent")

    print("\nMigration guide: docs/migrations/langgraph-to-agenkit.md")
    print("\nWhy Agenkit over LangGraph?")
    print("   6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   18x faster in Go for production workloads")
    print("   No LangChain dependency — standalone toolkit")
    print("   11+ patterns (ReAct, Sequential, Router, Parallel, ...)")
    print("   OpenTelemetry observability built-in")
    print("   Production middleware: retry, circuit breaker, timeout")


if __name__ == "__main__":
    asyncio.run(main())
