#!/usr/bin/env python3
"""
MiniSemanticKernel - Microsoft Semantic Kernel Equivalent Built on Agenkit

Demonstrates how Microsoft Semantic Kernel's plugin and orchestration patterns
can be built ON TOP of Agenkit primitives, showing toolkit philosophy for
enterprise-grade AI frameworks.

Semantic Kernel Key Concepts (v1.x Python, March 2026):
- Kernel: central orchestration object; registers plugins and LLM services
- KernelPlugin: named collection of KernelFunctions (semantic or native)
- KernelFunction: a callable unit — semantic (LLM-powered) or native (Python code)
- @kernel_function decorator: marks a method as a KernelFunction with metadata
- KernelArguments: typed dict passed to function invocations
- ChatHistory: ordered list of messages with roles (user/assistant/system)
- ChatCompletionService: abstraction over an LLM backend (OpenAI, Azure, etc.)
- kernel.invoke(function, KernelArguments(...)): call a registered function
- kernel.invoke_prompt(template, args): substitute {{$var}} and call LLM directly

Pattern Mappings:
- SK.Kernel                  → Agenkit Agent registry + LLM adapter
- SK.KernelPlugin            → Agenkit Tool collection
- SK.KernelFunction (native) → Agenkit Tool
- SK.KernelFunction (semantic)→ Agenkit Agent with prompt template
- SK.ChatHistory             → Agenkit ConversationalAgent history
- SK.SequentialPlanner       → Agenkit SequentialAgent
- SK.kernel.invoke()         → Agenkit agent.process()

Migration guide: docs/migrations/semantickernel-to-agenkit.md

Usage: uv run python examples/frameworks/minisemantickernel.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, cast

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM, OpenAILLM


# ---------------------------------------------------------------------------
# KernelArguments
# ---------------------------------------------------------------------------


@dataclass
class KernelArguments:
    """
    Typed argument container for kernel function invocations (mirrors SK.KernelArguments).
    Pattern: SK.KernelArguments → simple dict wrapper with keyword-arg construction
    """

    _data: dict[str, Any] = field(default_factory=dict)

    def __init__(self, **kwargs: Any) -> None:
        """Create arguments from keyword parameters."""
        self._data = dict(kwargs)

    def __getitem__(self, key: str) -> Any:
        """Get argument by name."""
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set argument by name."""
        self._data[key] = value

    def __contains__(self, key: object) -> bool:
        """Check if argument exists."""
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Get argument with optional default."""
        return self._data.get(key, default)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"KernelArguments({self._data!r})"


# ---------------------------------------------------------------------------
# kernel_function decorator
# ---------------------------------------------------------------------------


def kernel_function(name: str = "", description: str = "") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to mark a method as a KernelFunction (mirrors SK @kernel_function).
    Pattern: SK.@kernel_function → attaches metadata used by KernelPlugin discovery
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn.__kernel_function__ = True  # type: ignore[attr-defined]
        fn.__kernel_function_name__ = name or fn.__name__  # type: ignore[attr-defined]
        fn.__kernel_function_description__ = description or (fn.__doc__ or "")  # type: ignore[attr-defined]
        return fn

    return decorator


# ---------------------------------------------------------------------------
# KernelFunction
# ---------------------------------------------------------------------------


class KernelFunction:
    """
    A callable function — semantic (LLM-powered) or native (Python code)
    registered in the kernel (mirrors SK.KernelFunction).
    Pattern: SK.KernelFunction → Agenkit Tool (native) or Agent (semantic)
    """

    def __init__(
        self,
        name: str,
        description: str,
        fn: Callable[..., Any],
        plugin_name: str = "",
    ) -> None:
        """
        Create a kernel function.

        Args:
            name: Function name (used for invocation)
            description: Human-readable description
            fn: Underlying callable (sync or async)
            plugin_name: Name of the owning plugin
        """
        self.name = name
        self.description = description
        self._fn = fn
        self.plugin_name = plugin_name

    async def invoke(self, args: KernelArguments) -> str:
        """
        Invoke the function with the provided arguments.

        Args:
            args: Typed argument container

        Returns:
            String result from function execution
        """
        import inspect

        if inspect.iscoroutinefunction(self._fn):
            result = await self._fn(**args._data)
        else:
            result = self._fn(**args._data)
        return str(result)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"KernelFunction(plugin={self.plugin_name!r}, name={self.name!r})"


# ---------------------------------------------------------------------------
# KernelPlugin
# ---------------------------------------------------------------------------


class KernelPlugin:
    """
    Named collection of KernelFunctions (mirrors SK.KernelPlugin).
    Pattern: SK.KernelPlugin → Agenkit Tool collection / module
    """

    def __init__(self, name: str) -> None:
        """
        Create a plugin.

        Args:
            name: Plugin name (used for registration and lookup)
        """
        self.name = name
        self._functions: dict[str, KernelFunction] = {}

    def add_function(self, fn: KernelFunction) -> None:
        """Register a function in this plugin."""
        fn.plugin_name = self.name
        self._functions[fn.name] = fn

    def get_function(self, name: str) -> KernelFunction:
        """
        Retrieve a function by name.

        Args:
            name: Function name

        Returns:
            Matching KernelFunction

        Raises:
            KeyError: If function not found
        """
        if name not in self._functions:
            raise KeyError(f"Function '{name}' not found in plugin '{self.name}'")
        return self._functions[name]

    def __iter__(self) -> Any:
        """Iterate over all functions in the plugin."""
        return iter(self._functions.values())

    def __repr__(self) -> str:
        """Return string representation."""
        return f"KernelPlugin(name={self.name!r}, functions={list(self._functions)})"

    @classmethod
    def from_object(cls, obj: Any, plugin_name: str) -> "KernelPlugin":
        """
        Build a plugin by scanning an object for @kernel_function-decorated methods.
        Pattern: SK.kernel.add_plugin(MyClass(), 'MyPlugin') discovery mechanism

        Args:
            obj: Object whose methods are scanned
            plugin_name: Name to give the resulting plugin

        Returns:
            Populated KernelPlugin
        """
        plugin = cls(plugin_name)
        for attr_name in dir(obj):
            method = getattr(obj, attr_name, None)
            if callable(method) and getattr(method, "__kernel_function__", False):
                kf = KernelFunction(
                    name=getattr(method, "__kernel_function_name__", attr_name),
                    description=getattr(method, "__kernel_function_description__", ""),
                    fn=method,
                    plugin_name=plugin_name,
                )
                plugin.add_function(kf)
        return plugin


# ---------------------------------------------------------------------------
# ChatHistory
# ---------------------------------------------------------------------------


class ChatHistory:
    """
    Ordered conversation history with roles (mirrors SK.ChatHistory).
    Pattern: SK.ChatHistory → list of Agenkit Messages
    """

    def __init__(self, system_message: str = "") -> None:
        """
        Create chat history, optionally seeding a system message.

        Args:
            system_message: Optional system/persona instruction
        """
        self._messages: list[Message] = []
        if system_message:
            self._messages.append(Message(role="system", content=system_message))

    def add_user_message(self, content: str) -> None:
        """Append a user-role message."""
        self._messages.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant-role message."""
        self._messages.append(Message(role="assistant", content=content))

    def to_messages(self) -> list[Message]:
        """Return all messages as a list of Agenkit Messages."""
        return list(self._messages)

    def __len__(self) -> int:
        """Return message count."""
        return len(self._messages)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ChatHistory(messages={len(self._messages)})"


# ---------------------------------------------------------------------------
# Kernel
# ---------------------------------------------------------------------------


class Kernel:
    """
    Central orchestration object (mirrors SK.Kernel).
    Registers LLM services and plugins; executes functions and prompt templates.
    Pattern: SK.Kernel → Agenkit Agent registry + LLM adapter hub
    """

    def __init__(self) -> None:
        """Create an empty kernel with no services or plugins."""
        self._llm: LLM | None = None
        self._plugins: dict[str, KernelPlugin] = {}

    def add_service(self, llm: LLM) -> "Kernel":
        """
        Register an LLM as the chat-completion service (fluent).
        Pattern: SK.kernel.add_service(OpenAIChatCompletion(...)) → store LLM adapter

        Args:
            llm: LLM adapter (e.g. OpenAILLM)

        Returns:
            self for method chaining
        """
        self._llm = llm
        return self

    def add_plugin(self, plugin: KernelPlugin, plugin_name: str = "") -> "Kernel":
        """
        Register a plugin (fluent).
        Pattern: SK.kernel.add_plugin(plugin, 'PluginName')

        Args:
            plugin: Plugin to register
            plugin_name: Override name (defaults to plugin.name)

        Returns:
            self for method chaining
        """
        key = plugin_name or plugin.name
        self._plugins[key] = plugin
        return self

    async def invoke(self, function: KernelFunction, args: KernelArguments) -> str:
        """
        Invoke a registered kernel function.
        Pattern: SK.kernel.invoke(fn, KernelArguments(...)) → Agenkit agent.process()

        Args:
            function: KernelFunction to invoke
            args: Arguments for the function

        Returns:
            String result
        """
        return await function.invoke(args)

    async def invoke_prompt(self, prompt_template: str, args: KernelArguments) -> str:
        """
        Substitute {{$var}} placeholders and invoke the LLM directly.
        Pattern: SK.kernel.invoke_prompt(template, KernelArguments(...))

        Args:
            prompt_template: Template string with {{$variable}} placeholders
            args: Values to substitute

        Returns:
            LLM-generated string response

        Raises:
            RuntimeError: If no LLM service has been registered
        """
        if self._llm is None:
            raise RuntimeError("No LLM service registered. Call kernel.add_service(llm) first.")

        # Substitute {{$var}} placeholders
        prompt = prompt_template
        for key, value in args._data.items():
            prompt = prompt.replace(f"{{{{${key}}}}}", str(value))

        response = await self._llm.complete([Message(role="user", content=prompt)])
        return cast(str, response.content)

    def get_function(self, plugin_name: str, function_name: str) -> KernelFunction:
        """
        Retrieve a function from a registered plugin.

        Args:
            plugin_name: Plugin name
            function_name: Function name within the plugin

        Returns:
            Matching KernelFunction

        Raises:
            KeyError: If plugin or function not found
        """
        if plugin_name not in self._plugins:
            raise KeyError(f"Plugin '{plugin_name}' not found")
        return self._plugins[plugin_name].get_function(function_name)


# ---------------------------------------------------------------------------
# Example plugin definitions
# ---------------------------------------------------------------------------


class MathPlugin:
    """
    Native plugin with math functions (mirrors SK native plugins).
    Pattern: SK.KernelPlugin with native Python functions → Agenkit Tool collection
    """

    @kernel_function(name="add", description="Add two numbers together")
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    @kernel_function(name="multiply", description="Multiply two numbers together")
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    @kernel_function(name="subtract", description="Subtract b from a")
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b


class SemanticSummaryPlugin:
    """
    Semantic plugin backed by LLM (mirrors SK semantic function plugin).
    Pattern: SK semantic KernelFunction → Agenkit Agent with prompt template
    """

    def __init__(self, llm: LLM) -> None:
        """
        Create semantic plugin.

        Args:
            llm: LLM adapter used by semantic functions
        """
        self._llm = llm

    @kernel_function(name="summarize", description="Summarize text to a given number of sentences")
    async def summarize(self, text: str, sentence_count: int = 3) -> str:
        """Summarize text to a target sentence count using LLM."""
        prompt = (
            f"Summarize the following text in exactly {sentence_count} sentence(s):\n\n{text}"
        )
        response = await self._llm.complete([Message(role="user", content=prompt)])
        return cast(str, response.content)

    @kernel_function(name="translate", description="Translate text to a target language")
    async def translate(self, text: str, language: str) -> str:
        """Translate text to the given language using LLM."""
        prompt = f"Translate the following text to {language}:\n\n{text}"
        response = await self._llm.complete([Message(role="user", content=prompt)])
        return cast(str, response.content)


# ---------------------------------------------------------------------------
# SK-compatible Agent wrapper (for planner pattern)
# ---------------------------------------------------------------------------


class SKAgent(Agent):
    """
    Kernel-backed agent that drives a Kernel through process() calls.
    Pattern: SK planner/orchestrator → Agenkit Agent wrapping a Kernel
    """

    def __init__(self, kernel: Kernel, system_message: str = "") -> None:
        """
        Create a Kernel-backed agent.

        Args:
            kernel: Configured Kernel instance
            system_message: Optional system persona
        """
        self._kernel = kernel
        self._system_message = system_message
        self._history = ChatHistory(system_message=system_message)

    @property
    def name(self) -> str:
        """Return agent name."""
        return "sk_agent"

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["kernel_invocation", "chat_completion", "plugin_use"]

    async def process(self, message: Message) -> Message:
        """
        Process a message through the kernel's LLM service.

        Args:
            message: Incoming user message

        Returns:
            Agent response message
        """
        self._history.add_user_message(cast(str, message.content))
        response = await self._kernel._llm.complete(self._history.to_messages())  # type: ignore[union-attr]
        reply = cast(str, response.content)
        self._history.add_assistant_message(reply)
        return Message(role="agent", content=reply, metadata={"via": "kernel"})


# ---------------------------------------------------------------------------
# Demo examples
# ---------------------------------------------------------------------------


async def example_native_plugin() -> None:
    """Example 1: Native plugin with math functions."""
    print("=" * 60)
    print("Example 1: Native Plugin (MathPlugin)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Build kernel and register math plugin
    kernel = Kernel()
    kernel.add_service(llm)

    math_obj = MathPlugin()
    math_plugin = KernelPlugin.from_object(math_obj, "MathPlugin")
    kernel.add_plugin(math_plugin)

    print("\n   kernel = Kernel()")
    print("   kernel.add_service(OpenAILLM(model='gpt-4o-mini', ...))")
    print("   math_plugin = KernelPlugin.from_object(MathPlugin(), 'MathPlugin')")
    print("   kernel.add_plugin(math_plugin)")

    # Invoke native function directly
    add_fn = kernel.get_function("MathPlugin", "add")
    result = await kernel.invoke(add_fn, KernelArguments(a=7.0, b=5.0))
    print(f"\n   result = await kernel.invoke(add_fn, KernelArguments(a=7, b=5))")
    print(f"   → {result}")

    multiply_fn = kernel.get_function("MathPlugin", "multiply")
    result2 = await kernel.invoke(multiply_fn, KernelArguments(a=3.0, b=4.0))
    print(f"\n   result = await kernel.invoke(multiply_fn, KernelArguments(a=3, b=4))")
    print(f"   → {result2}")

    print("\n   Pattern: SK.KernelPlugin (native) → Agenkit Tool collection")
    print("   @kernel_function decorator attaches metadata for auto-discovery")


async def example_semantic_plugin() -> None:
    """Example 2: Semantic plugin backed by LLM."""
    print("\n\n" + "=" * 60)
    print("Example 2: Semantic Plugin (LLM-Powered Functions)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    kernel = Kernel()
    kernel.add_service(llm)

    summary_obj = SemanticSummaryPlugin(llm=llm)
    summary_plugin = KernelPlugin.from_object(summary_obj, "SummaryPlugin")
    kernel.add_plugin(summary_plugin)

    print("\n   summary_plugin = KernelPlugin.from_object(SemanticSummaryPlugin(llm), 'SummaryPlugin')")
    print("   kernel.add_plugin(summary_plugin)")

    summarize_fn = kernel.get_function("SummaryPlugin", "summarize")

    print("\n   summarize_fn = kernel.get_function('SummaryPlugin', 'summarize')")
    print("   result = await kernel.invoke(summarize_fn, KernelArguments(text='...', sentence_count=2))")
    print("\n   Pattern: SK.KernelFunction (semantic) → Agenkit Agent with prompt template")
    print("   LLM call is deferred until invoke(); kernel owns the service lifecycle")

    translate_fn = kernel.get_function("SummaryPlugin", "translate")
    print(f"\n   Available functions: {[fn.name for fn in summary_plugin]}")
    print(f"   translate_fn = {translate_fn}")


async def example_kernel_arguments() -> None:
    """Example 3: KernelArguments and invoke_prompt."""
    print("\n\n" + "=" * 60)
    print("Example 3: KernelArguments + invoke_prompt")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")
    kernel = Kernel()
    kernel.add_service(llm)

    # Build KernelArguments
    args = KernelArguments(topic="quantum computing", audience="high school students", length="3")
    print(f"\n   args = KernelArguments(topic='quantum computing', audience='high school students')")
    print(f"   args['topic'] → {args['topic']}")
    print(f"   args.get('length', '5') → {args.get('length', '5')}")

    # Inline prompt template with placeholder substitution
    template = "Explain {{$topic}} to {{$audience}} in {{$length}} sentences."
    print(f"\n   template = 'Explain {{{{$topic}}}} to {{{{$audience}}}} in {{{{$length}}}} sentences.'")
    print(f"   result = await kernel.invoke_prompt(template, args)")
    print(f"\n   Rendered prompt: {template.replace('{{$topic}}', args['topic']).replace('{{$audience}}', args['audience']).replace('{{$length}}', args['length'])!r}")
    print("\n   Pattern: SK.kernel.invoke_prompt → {{$var}} substitution + LLM call")
    print("   Agenkit Message wraps the rendered prompt; LLM adapter handles completion")


async def example_chat_history() -> None:
    """Example 4: ChatHistory for multi-turn conversation."""
    print("\n\n" + "=" * 60)
    print("Example 4: ChatHistory (Multi-Turn Conversation)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")
    kernel = Kernel()
    kernel.add_service(llm)

    chat = ChatHistory(system_message="You are a helpful coding assistant.")
    chat.add_user_message("What is a closure in Python?")
    chat.add_assistant_message("A closure is a function that remembers its enclosing scope.")
    chat.add_user_message("Can you give me an example?")

    print("\n   chat = ChatHistory(system_message='You are a helpful coding assistant.')")
    print("   chat.add_user_message('What is a closure in Python?')")
    print("   chat.add_assistant_message('A closure is a function that ...')")
    print("   chat.add_user_message('Can you give me an example?')")

    messages = chat.to_messages()
    print(f"\n   chat.to_messages() → {len(messages)} Message objects")
    print(f"   roles: {[m.role for m in messages]}")

    agent = SKAgent(kernel=kernel, system_message="You are a helpful coding assistant.")
    print("\n   agent = SKAgent(kernel=kernel, system_message='...')")
    print("   reply = await agent.process(Message(role='user', content='What is a list comprehension?'))")
    print("\n   Pattern: SK.ChatHistory → Agenkit ConversationalAgent history")
    print("   SKAgent wraps Kernel to expose Agent.process() interface")


async def example_planner_pattern() -> None:
    """Example 5: Sequential planner — chain multiple functions."""
    print("\n\n" + "=" * 60)
    print("Example 5: Sequential Planner (Multi-Step Orchestration)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    kernel = Kernel()
    kernel.add_service(llm)

    math_plugin = KernelPlugin.from_object(MathPlugin(), "MathPlugin")
    kernel.add_plugin(math_plugin)

    print("\n   # Planner: chain kernel.invoke calls sequentially")
    print("   step1 = await kernel.invoke(add_fn, KernelArguments(a=10, b=5))")
    print("   step2 = await kernel.invoke(multiply_fn, KernelArguments(a=float(step1), b=2))")
    print("   step3 = await kernel.invoke(subtract_fn, KernelArguments(a=float(step2), b=3))")

    # Demonstrate the actual chaining
    add_fn = kernel.get_function("MathPlugin", "add")
    multiply_fn = kernel.get_function("MathPlugin", "multiply")
    subtract_fn = kernel.get_function("MathPlugin", "subtract")

    step1 = await kernel.invoke(add_fn, KernelArguments(a=10.0, b=5.0))
    step2 = await kernel.invoke(multiply_fn, KernelArguments(a=float(step1), b=2.0))
    step3 = await kernel.invoke(subtract_fn, KernelArguments(a=float(step2), b=3.0))

    print(f"\n   step1 (10+5)  → {step1}")
    print(f"   step2 ({step1}*2) → {step2}")
    print(f"   step3 ({step2}-3) → {step3}")

    print("\n   Pattern: SK.SequentialPlanner → Agenkit SequentialAgent / manual chaining")
    print("   Each kernel.invoke() corresponds to one agent.process() in Agenkit")
    print("   Results flow: KernelArguments carry outputs between steps")


async def main() -> None:
    """Run all MiniSemanticKernel examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " MiniSemanticKernel - Semantic Kernel Built on Agenkit " + "║")
    print("╚" + "=" * 58 + "╝")
    print("\nDemonstrate: Microsoft Semantic Kernel v1.x patterns on Agenkit")

    await example_native_plugin()
    await example_semantic_plugin()
    await example_kernel_arguments()
    await example_chat_history()
    await example_planner_pattern()

    print("\n\n" + "=" * 60)
    print("MiniSemanticKernel Examples Complete")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("   Agenkit supports enterprise-grade plugin orchestration patterns")
    print("   Semantic Kernel patterns map to Agenkit primitives:")
    print("     - Kernel              → LLM adapter + plugin registry")
    print("     - KernelPlugin        → Tool collection / module")
    print("     - KernelFunction (native)   → Agenkit Tool")
    print("     - KernelFunction (semantic) → Agenkit Agent + prompt template")
    print("     - ChatHistory         → ConversationalAgent message list")
    print("     - SequentialPlanner   → Agenkit SequentialAgent")
    print("     - kernel.invoke()     → agent.process()")

    print("\nMigration guide: docs/migrations/semantickernel-to-agenkit.md")
    print("\nWhy Agenkit over Semantic Kernel?")
    print("   6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   No Azure/Microsoft vendor dependency")
    print("   11+ patterns (beyond plugin/planner)")
    print("   OpenTelemetry observability built-in")
    print("   Any LLM provider without a service adapter layer")
    print("   18x faster in Go for production throughput")


if __name__ == "__main__":
    asyncio.run(main())
