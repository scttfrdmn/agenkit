#!/usr/bin/env python3
"""
MiniDSPy - DSPy Equivalent Built on Agenkit

Demonstrates how DSPy's declarative LM programming patterns can be built
ON TOP of Agenkit primitives, showing toolkit philosophy.

DSPy Key Concepts (dspy-ai package, Stanford NLP):
- Signature: declares input/output fields and task instructions (like a typed prompt)
- Predict: runs a Signature once; produces structured output dict
- ChainOfThought: Predict variant that adds implicit "reasoning" output field
- ReAct: iterative tool-calling loop (Reason + Act + Observe)
- Module: composable DSPy program; override forward() to wire sub-modules
- LM (dspy.LM): the language model backend (here replaced by Agenkit LLM)

Pattern Mappings:
  DSPy.Signature       → Agenkit Message fields + system prompt
  DSPy.Predict         → Agenkit LLM.complete() with structured output parsing
  DSPy.ChainOfThought  → Predict + implicit reasoning field
  DSPy.ReAct           → Agenkit ReActAgent / tool-calling loop
  DSPy.Module          → Agenkit Agent base class (composable programs)
  DSPy.LM              → Agenkit LLM adapter

Migration guide: docs/migrations/dspy-to-agenkit.md

Usage: uv run python examples/frameworks/minidspy.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from agenkit import Message
from agenkit.adapters.llm import LLM, OpenAILLM

# ---------------------------------------------------------------------------
# Signature (mirrors DSPy.Signature)
# ---------------------------------------------------------------------------


@dataclass
class Signature:
    """
    Typed declaration of a language model task (mirrors DSPy.Signature).
    Pattern: DSPy.Signature → structured system prompt + field schema

    In DSPy you write:
        class QASignature(dspy.Signature):
            \"\"\"Answer the question.\"\"\"
            question: str = dspy.InputField()
            answer: str = dspy.OutputField()

    Here we represent the same information as plain dataclass fields.
    input_fields list the keys the caller must supply; output_fields list
    the keys the LLM is asked to produce.
    """

    input_fields: list[str]
    output_fields: list[str]
    instructions: str = ""

    def to_prompt(self, inputs: dict[str, str]) -> str:
        """
        Render a prompt string from the signature and caller-supplied inputs.

        Args:
            inputs: Values for each input field

        Returns:
            Formatted prompt instructing the LLM to produce output fields
        """
        parts: list[str] = []
        if self.instructions:
            parts.append(self.instructions)
        for key in self.input_fields:
            parts.append(f"{key}: {inputs.get(key, '')}")
        parts.append("")
        parts.append("Produce the following output fields (one per line, key: value):")
        for key in self.output_fields:
            parts.append(f"  {key}:")
        return "\n".join(parts)

    @staticmethod
    def parse_output(text: str, output_fields: list[str]) -> dict[str, str]:
        """
        Parse LLM response text into a dict keyed by output field names.

        Args:
            text: Raw LLM response
            output_fields: Expected output field names

        Returns:
            Dict mapping output field names to extracted values
        """
        result: dict[str, str] = {}
        lines = text.strip().splitlines()
        for field_name in output_fields:
            for line in lines:
                if line.lower().startswith(field_name.lower() + ":"):
                    result[field_name] = line.split(":", 1)[1].strip()
                    break
            if field_name not in result:
                # Fallback: first non-empty line
                result[field_name] = next((ln.strip() for ln in lines if ln.strip()), text.strip())
        return result


# ---------------------------------------------------------------------------
# Predict (mirrors DSPy.Predict)
# ---------------------------------------------------------------------------


class Predict:
    """
    Runs a Signature once against a language model (mirrors DSPy.Predict).
    Pattern: DSPy.Predict → Agenkit LLM.complete() + structured output

    In DSPy:
        predict = dspy.Predict(QASignature)
        result = predict(question="What is Agenkit?")
        # result.answer → str

    Here we call the Agenkit LLM adapter and parse the response back into
    the output fields defined in the signature.
    """

    def __init__(self, signature: Signature, llm: LLM) -> None:
        """
        Create a Predict module.

        Args:
            signature: Task declaration with input/output fields
            llm: Agenkit LLM adapter (replaces dspy.LM)
        """
        self.signature = signature
        self.llm = llm

    async def acall(self, **kwargs: str) -> dict[str, str]:
        """
        Execute the prediction asynchronously.

        Args:
            **kwargs: Values for each input field defined in the signature

        Returns:
            Dict mapping output field names to generated values
        """
        prompt = self.signature.to_prompt(kwargs)
        response = await self.llm.complete([Message(role="user", content=prompt)])
        text = str(response.content) if response.content is not None else ""
        return Signature.parse_output(text, self.signature.output_fields)

    def __call__(self, **kwargs: str) -> dict[str, str]:
        """
        Execute the prediction synchronously (blocks the event loop).

        Args:
            **kwargs: Values for each input field defined in the signature

        Returns:
            Dict mapping output field names to generated values
        """
        return asyncio.get_event_loop().run_until_complete(self.acall(**kwargs))


# ---------------------------------------------------------------------------
# ChainOfThought (mirrors DSPy.ChainOfThought)
# ---------------------------------------------------------------------------


class ChainOfThought(Predict):
    """
    Predict variant that injects a "reasoning" output field (mirrors DSPy.ChainOfThought).
    Pattern: DSPy.ChainOfThought → Predict + implicit reasoning step

    In DSPy, ChainOfThought automatically prepends a hidden "Reasoning" field
    to the signature's outputs before the final answer fields. This encourages
    the model to reason before answering.

    DSPy usage:
        cot = dspy.ChainOfThought(QASignature)
        result = cot(question="Why is the sky blue?")
        # result.reasoning → str  (automatic)
        # result.answer    → str

    Here we inject "reasoning" into output_fields before calling Predict.
    """

    def __init__(self, signature: Signature, llm: LLM) -> None:
        """
        Create a ChainOfThought module.

        Args:
            signature: Original task signature (reasoning field added automatically)
            llm: Agenkit LLM adapter
        """
        # Inject reasoning field before the declared output fields
        cot_sig = Signature(
            input_fields=signature.input_fields,
            output_fields=["reasoning", *signature.output_fields],
            instructions=(
                signature.instructions
                + "\nThink step by step. First produce a 'reasoning' field, then your answer."
            ),
        )
        super().__init__(cot_sig, llm)


# ---------------------------------------------------------------------------
# DSPy tool type
# ---------------------------------------------------------------------------


@dataclass
class DSPyTool:
    """Lightweight tool used by ReAct."""

    name: str
    description: str
    fn: Callable[[str], str]

    def call(self, arg: str) -> str:
        """Execute tool with a single string argument."""
        return self.fn(arg)


# ---------------------------------------------------------------------------
# ReAct (mirrors DSPy.ReAct)
# ---------------------------------------------------------------------------


class ReAct:
    """
    Iterative Reason-Act-Observe loop (mirrors DSPy.ReAct).
    Pattern: DSPy.ReAct → Agenkit ReActAgent / tool-calling loop

    In DSPy:
        react = dspy.ReAct(QASignature, tools=[my_tool])
        result = react(question="What year was the Eiffel Tower built?")

    The loop:
    1. Ask LLM to reason and pick a tool (Action: <name> Input: <arg>)
    2. Execute the tool; append Observation: <result>
    3. Repeat until the LLM produces a Finish: <answer>
    """

    def __init__(
        self,
        signature: Signature,
        tools: list[DSPyTool],
        llm: LLM,
        max_iters: int = 5,
    ) -> None:
        """
        Create a ReAct module.

        Args:
            signature: Task signature describing the goal
            tools: Available tools for Thought→Action→Observation steps
            llm: Agenkit LLM adapter
            max_iters: Maximum tool-call iterations before forcing a finish
        """
        self.signature = signature
        self.tools = {t.name: t for t in tools}
        self.llm = llm
        self.max_iters = max_iters

    async def acall(self, **kwargs: str) -> dict[str, str]:
        """
        Run the ReAct loop asynchronously.

        Args:
            **kwargs: Input field values for the signature

        Returns:
            Dict with output field values (plus tool trace in "trace")
        """
        tool_descriptions = "; ".join(f"{t.name}: {t.description}" for t in self.tools.values())
        task = self.signature.to_prompt(kwargs)

        system = (
            f"{self.signature.instructions}\n\n"
            f"Available tools: {tool_descriptions}\n\n"
            "Format each step as:\n"
            "Thought: <reasoning>\n"
            "Action: <tool_name> Input: <argument>\n"
            "... (repeat until done)\n"
            "Finish: <final answer>"
        )

        messages = [
            Message(role="system", content=system),
            Message(role="user", content=task),
        ]
        trace: list[str] = []

        for _ in range(self.max_iters):
            response = await self.llm.complete(messages)
            reply = str(response.content) if response.content is not None else ""
            messages.append(Message(role="assistant", content=reply))
            trace.append(reply)

            if "Finish:" in reply:
                answer = reply.split("Finish:")[1].strip().split("\n")[0]
                result = dict.fromkeys(self.signature.output_fields, answer)
                result["trace"] = "\n---\n".join(trace)
                return result

            if "Action:" in reply:
                action_line = reply.split("Action:")[1].split("\n")[0].strip()
                parts = action_line.split(" Input:", 1)
                tool_name = parts[0].strip()
                tool_input = parts[1].strip() if len(parts) > 1 else ""
                if tool_name in self.tools:
                    observation = self.tools[tool_name].call(tool_input)
                    messages.append(Message(role="user", content=f"Observation: {observation}"))

        # Fallback if max_iters reached
        last = str(messages[-1].content) if messages else ""
        result = dict.fromkeys(self.signature.output_fields, last)
        result["trace"] = "\n---\n".join(trace)
        return result

    def __call__(self, **kwargs: str) -> dict[str, str]:
        """Run the ReAct loop synchronously."""
        return asyncio.get_event_loop().run_until_complete(self.acall(**kwargs))


# ---------------------------------------------------------------------------
# Module (mirrors DSPy.Module)
# ---------------------------------------------------------------------------


class Module:
    """
    Composable DSPy program (mirrors DSPy.Module).
    Pattern: DSPy.Module → Agenkit Agent base class (composable programs)

    In DSPy, Module is the base class for all programs:
        class RAGPipeline(dspy.Module):
            def __init__(self):
                self.retrieve = dspy.Retrieve(k=3)
                self.generate = dspy.ChainOfThought(GenerateAnswer)

            def forward(self, question):
                context = self.retrieve(question).passages
                return self.generate(context=context, question=question)

    Here forward() is async; __call__ wraps it synchronously.
    """

    async def forward(self, **kwargs: Any) -> dict[str, str]:
        """
        Override in subclasses to define the program logic.

        Args:
            **kwargs: Program inputs

        Returns:
            Dict of output field values
        """
        raise NotImplementedError

    def __call__(self, **kwargs: Any) -> dict[str, str]:
        """Run the module synchronously via asyncio."""
        return asyncio.get_event_loop().run_until_complete(self.forward(**kwargs))


# ---------------------------------------------------------------------------
# Demo examples
# ---------------------------------------------------------------------------


async def example_predict() -> None:
    """Example 1: Predict — simple Q&A with structured output."""
    print("=" * 60)
    print("Example 1: Predict (structured Q&A)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    qa_sig = Signature(
        input_fields=["question"],
        output_fields=["answer"],
        instructions="Answer the question clearly and concisely.",
    )
    predict = Predict(qa_sig, llm)

    print("\n   # DSPy equivalent:")
    print("   import dspy")
    print("   class QA(dspy.Signature):")
    print('       """Answer the question."""')
    print("       question: str = dspy.InputField()")
    print("       answer: str = dspy.OutputField()")
    print("   predict = dspy.Predict(QA)")
    print("   result = predict(question='What is Agenkit?')")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.adapters.llm import OpenAILLM")
    print("   llm = OpenAILLM(model='gpt-4o-mini')")
    print("   response = await llm.complete([Message(role='user', content=prompt)])")

    result = await predict.acall(question="What is a language model?")
    print("\n   Input  → question: 'What is a language model?'")
    print(f"   Output → answer: {result.get('answer', '')[:80]}...")
    print("   Pattern: DSPy.Predict → Agenkit LLM.complete() + field parsing")


async def example_chain_of_thought() -> None:
    """Example 2: ChainOfThought — reasoning before answering."""
    print("\n\n" + "=" * 60)
    print("Example 2: ChainOfThought (reason then answer)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    reasoning_sig = Signature(
        input_fields=["question"],
        output_fields=["answer"],
        instructions="Answer complex questions.",
    )
    cot = ChainOfThought(reasoning_sig, llm)

    print("\n   # DSPy equivalent:")
    print("   cot = dspy.ChainOfThought(QASignature)")
    print("   result = cot(question='Why is the sky blue?')")
    print("   print(result.reasoning)  # automatic reasoning field")
    print("   print(result.answer)")
    print()
    print("   # Agenkit equivalent:")
    print("   # Add 'Think step by step. First produce reasoning:' to prompt")
    print("   # Then parse both 'reasoning:' and 'answer:' fields from response")

    print("\n   Output fields (after ChainOfThought injects 'reasoning'):")
    print(f"   {cot.signature.output_fields}")

    result = await cot.acall(question="Why does ice float on water?")
    print(f"\n   reasoning: {result.get('reasoning', '')[:60]}...")
    print(f"   answer:    {result.get('answer', '')[:60]}...")
    print("   Pattern: DSPy.ChainOfThought → Predict + implicit reasoning field")


async def example_react() -> None:
    """Example 3: ReAct — multi-step tool-calling loop."""
    print("\n\n" + "=" * 60)
    print("Example 3: ReAct (Reason + Act + Observe loop)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    research_tool = DSPyTool(
        name="search",
        description="Search the web for a fact",
        fn=lambda q: f"[search result for '{q}': relevant information about {q}]",
    )
    calc_tool = DSPyTool(
        name="calculate",
        description="Evaluate a math expression",
        fn=lambda expr: str(eval("".join(c for c in expr if c in "0123456789+-*/(). "))),
    )

    task_sig = Signature(
        input_fields=["question"],
        output_fields=["answer"],
        instructions="Answer multi-step questions using available tools.",
    )
    react = ReAct(task_sig, tools=[research_tool, calc_tool], llm=llm, max_iters=4)

    print("\n   # DSPy equivalent:")
    print("   react = dspy.ReAct(TaskSignature, tools=[search, calculate])")
    print("   result = react(question='What is 15% of 240?')")
    print("   # Internally: Thought → Action: calculate Input: 240 * 0.15 → Observation: 36.0")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import ReActAgent")
    print("   agent = ReActAgent(llm=llm, tools=[search_tool, calc_tool])")
    print("   result = await agent.process(Message(role='user', content=question))")

    result = await react.acall(question="What is 15 percent of 240?")
    print(f"\n   answer: {result.get('answer', '')[:80]}")
    steps = len(result.get("trace", "").split("---"))
    print(f"   steps:  {steps} reasoning step(s)")
    print("   Pattern: DSPy.ReAct → Agenkit ReActAgent (iterative tool loop)")


async def example_module_composition() -> None:
    """Example 4: Module — composable multi-hop program."""
    print("\n\n" + "=" * 60)
    print("Example 4: Module Composition (multi-hop Q&A)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    class MultiHopQA(Module):
        """
        Two-hop Q&A pipeline: decompose question → answer each sub-question → synthesize.
        Mirrors DSPy multi-hop RAG pipelines.
        """

        def __init__(self, llm: LLM) -> None:
            """Create the pipeline with three sub-Predict modules."""
            self.decompose = Predict(
                Signature(
                    input_fields=["question"],
                    output_fields=["sub_question_1", "sub_question_2"],
                    instructions="Decompose the question into two simpler sub-questions.",
                ),
                llm,
            )
            self.answer_sub = Predict(
                Signature(
                    input_fields=["question"],
                    output_fields=["answer"],
                    instructions="Answer this specific question.",
                ),
                llm,
            )
            self.synthesize = Predict(
                Signature(
                    input_fields=["context", "question"],
                    output_fields=["answer"],
                    instructions="Synthesize the context to answer the original question.",
                ),
                llm,
            )

        async def forward(self, **kwargs: Any) -> dict[str, str]:
            """
            Three-step pipeline: decompose → answer sub-questions → synthesize.

            Args:
                question: The main question to answer

            Returns:
                Dict with final 'answer' key
            """
            question = kwargs.get("question", "")

            # Step 1: decompose
            decomposed = await self.decompose.acall(question=question)
            sq1 = decomposed.get("sub_question_1", question)
            sq2 = decomposed.get("sub_question_2", "")

            # Step 2: answer each sub-question
            ans1 = await self.answer_sub.acall(question=sq1)
            ans2 = await self.answer_sub.acall(question=sq2) if sq2 else {"answer": ""}

            # Step 3: synthesize
            context = (
                f"Q1: {sq1}\nA1: {ans1.get('answer', '')}\nQ2: {sq2}\nA2: {ans2.get('answer', '')}"
            )
            return await self.synthesize.acall(context=context, question=question)

    pipeline = MultiHopQA(llm)

    print("\n   # DSPy equivalent:")
    print("   class MultiHopQA(dspy.Module):")
    print("       def __init__(self):")
    print("           self.decompose = dspy.ChainOfThought(DecomposeSignature)")
    print("           self.answer    = dspy.ChainOfThought(AnswerSignature)")
    print("           self.synthesize = dspy.ChainOfThought(SynthesizeSignature)")
    print("       def forward(self, question):")
    print("           ...")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import SequentialAgent")
    print("   pipeline = SequentialAgent([decompose_agent, answer_agent, synthesize_agent])")

    result = await pipeline.forward(question="How do neural networks learn from data?")
    print(f"\n   Final answer: {result.get('answer', '')[:80]}...")
    print("   Pipeline: decompose → answer sub-questions → synthesize")
    print("   Pattern: DSPy.Module.forward() → Agenkit SequentialAgent / custom composition")


async def main() -> None:
    """Run all MiniDSPy examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 12 + "MiniDSPy - DSPy Built on Agenkit" + " " * 13 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n   Demonstrate: DSPy declarative LM programming ON TOP of Agenkit")

    await example_predict()
    await example_chain_of_thought()
    await example_react()
    await example_module_composition()

    print("\n\n" + "=" * 60)
    print("MiniDSPy Examples Complete")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("   Agenkit covers every core DSPy concept:")
    print("     - Signature        → Agenkit structured prompt + field schema")
    print("     - Predict          → Agenkit LLM.complete() + output parsing")
    print("     - ChainOfThought   → Predict + implicit reasoning field injection")
    print("     - ReAct            → Agenkit ReActAgent (reason + act + observe)")
    print("     - Module.forward() → Agenkit SequentialAgent / custom composition")
    print("     - LM backend       → Agenkit LLM adapter (any provider)")

    print("\nMigration guide: docs/migrations/dspy-to-agenkit.md")
    print("\nWhy Agenkit over DSPy?")
    print("   6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   No optimizer dependency (DSPy needs BootstrapFewShot, MIPRO)")
    print("   OpenTelemetry observability built-in")
    print("   Production patterns (retry, circuit breaker, timeout)")
    print("   Explicit, readable code — no magical compilation step")


if __name__ == "__main__":
    asyncio.run(main())
