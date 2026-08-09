"""
Getting Started with Agenkit

Interactive tutorial using Marimo - the reactive Python notebook.
Run with: marimo edit 01-getting-started.py
"""

import marimo

__generated_with = "0.9.0"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo

    return (mo,)


@app.cell
def __(mo):
    mo.md(
        """
        # Getting Started with Agenkit 🚀

        Welcome to Agenkit! This interactive tutorial will guide you through building AI agents.

        ## What You'll Learn

        1. **Installation** - Setting up Agenkit
        2. **Your First Agent** - Creating a simple echo agent
        3. **Composing Agents** - Building agent pipelines
        4. **Working with LLMs** - Connecting to OpenAI/Claude
        5. **Running and Testing** - Executing and validating agents

        ## Prerequisites

        - Python 3.9+
        - Basic Python knowledge
        - (Optional) OpenAI or Anthropic API key

        This notebook is reactive - cells update automatically when dependencies change!
        """
    )
    return


@app.cell
def __(mo):
    mo.md("## 1. Installation")
    return


@app.cell
def __():
    # Verify Agenkit is installed
    import agenkit

    version = agenkit.__version__
    print(f"✅ Agenkit version: {version}")
    return agenkit, version


@app.cell
def __(mo, version):
    mo.md(f"Great! You have Agenkit **{version}** installed.")
    return


@app.cell
def __(mo):
    mo.md(
        """
        ## 2. Your First Agent: Echo Agent

        Let's create the simplest possible agent - one that echoes back whatever you say.

        ### Core Concepts

        - **Agent**: Implements `name()` and `process()` methods
        - **Message**: Universal message format
        - **Async**: Agents use async/await
        """
    )
    return


@app.cell
def __(agenkit):
    from agenkit import Agent, Message

    class EchoAgent(Agent):
        """Simple agent that echoes messages back."""

        @property
        def name(self) -> str:
            return "echo-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["echo", "simple"]

        async def process(self, message: Message) -> Message:
            user_text = message.content

            response = Message(role="assistant", content=f"Echo: {user_text}")

            return response

    echo_agent = EchoAgent()
    print(f"✅ Created agent: {echo_agent.name}")
    print(f"   Capabilities: {echo_agent.capabilities}")
    return Agent, EchoAgent, Message, echo_agent


@app.cell
def __(mo):
    # Interactive input for testing the echo agent
    user_input = mo.ui.text(
        placeholder="Type something...", value="Hello, Agenkit!", label="Message to Echo Agent:"
    )
    user_input
    return (user_input,)


@app.cell
async def __(Message, echo_agent, user_input):
    # Process message when input changes (reactive!)
    if user_input.value:
        message = Message(role="user", content=user_input.value)
        response = await echo_agent.process(message)
        echo_result = response.content
    else:
        echo_result = "(Type something to see the echo)"

    print(f"🤖 Agent says: {echo_result}")
    return echo_result, message, response


@app.cell
def __(mo):
    mo.md(
        """
        ## 3. Composing Agents: Sequential Pipeline

        The real power comes from composing agents. Let's create a word counter agent and combine it with our echo agent.
        """
    )
    return


@app.cell
def __(Agent, Message):
    class WordCounterAgent(Agent):
        """Agent that counts words in a message."""

        @property
        def name(self) -> str:
            return "word-counter"

        @property
        def capabilities(self) -> list[str]:
            return ["word-count", "analysis"]

        async def process(self, message: Message) -> Message:
            text = message.content
            word_count = len(text.split())

            response = Message(
                role="assistant",
                content=f"{text} (Word count: {word_count})",
                metadata={"word_count": word_count},
            )

            return response

    counter_agent = WordCounterAgent()
    print(f"✅ Created agent: {counter_agent.name}")
    return WordCounterAgent, counter_agent


@app.cell
def __(EchoAgent, WordCounterAgent):
    from agenkit.composition import SequentialAgent

    # Create pipeline: Echo first, then count words
    pipeline = SequentialAgent("echo-then-count", [EchoAgent(), WordCounterAgent()])

    print(f"✅ Created pipeline: {pipeline.name}")
    print(f"   Agents in pipeline: {len(pipeline.get_agents())}")
    return SequentialAgent, pipeline


@app.cell
def __(mo):
    # Interactive input for pipeline
    pipeline_input = mo.ui.text(
        placeholder="Test the pipeline...",
        value="Agenkit makes building agents easy",
        label="Message to Pipeline:",
    )
    pipeline_input
    return (pipeline_input,)


@app.cell
async def __(Message, pipeline, pipeline_input):
    # Process through pipeline (reactive!)
    if pipeline_input.value:
        msg = Message(role="user", content=pipeline_input.value)
        pipeline_result = await pipeline.process(msg)

        print(f"📥 Input: {msg.content}")
        print(f"📤 Output: {pipeline_result.content}")
        print(f"📊 Metadata: {pipeline_result.metadata}")
    else:
        pipeline_result = None
    return msg, pipeline_result


@app.cell
def __(mo):
    mo.md(
        """
        ## 4. Working with LLMs

        Let's connect to real LLMs! Set your API keys below:
        """
    )
    return


@app.cell
def __(mo):
    import os

    # Check for existing API keys
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    status = mo.md(
        f"""
        API Key Status:
        - OpenAI: {"✅ Set" if has_openai else "❌ Not set"}
        - Anthropic: {"✅ Set" if has_anthropic else "❌ Not set"}

        {"You can test LLM agents below!" if (has_openai or has_anthropic) else "⚠️ Set API keys as environment variables to test LLM agents"}
        """
    )
    status
    return has_anthropic, has_openai, os, status


@app.cell
def __(has_openai, mo, os):
    # Create OpenAI agent if key is available
    openai_agent = None

    if has_openai:
        from agenkit.adapters.llm import OpenAILLM
        from agenkit.patterns import ConversationalAgent

        llm = OpenAILLM(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4")

        openai_agent = ConversationalAgent(
            llm=llm, system_prompt="You are a helpful AI assistant. Be concise and friendly."
        )

        mo.md("✅ GPT-4 agent ready!")
    else:
        mo.md("⚠️ OpenAI API key not set")
    return ConversationalAgent, OpenAILLM, llm, openai_agent


@app.cell
def __(has_anthropic, mo, os):
    # Create Anthropic agent if key is available
    claude_agent = None

    if has_anthropic:
        from agenkit.adapters.llm import AnthropicLLM
        from agenkit.patterns import ConversationalAgent as Conv

        anthropic_llm = AnthropicLLM(
            api_key=os.getenv("ANTHROPIC_API_KEY"), model="claude-sonnet-5"
        )

        claude_agent = Conv(
            llm=anthropic_llm,
            system_prompt="You are a helpful AI assistant. Be concise and friendly.",
        )

        mo.md("✅ Claude agent ready!")
    else:
        mo.md("⚠️ Anthropic API key not set")
    return AnthropicLLM, Conv, anthropic_llm, claude_agent


@app.cell
def __(claude_agent, has_anthropic, has_openai, mo, openai_agent):
    # Interactive LLM testing
    if has_openai or has_anthropic:
        llm_input = mo.ui.text(
            placeholder="Ask the LLM something...",
            value="What is Agenkit in one sentence?",
            label="Question for LLM:",
        )
        llm_input
    else:
        llm_input = None
        mo.md("⚠️ No LLM API keys available - skipping this section")
    return (llm_input,)


@app.cell
async def __(
    Message,
    claude_agent,
    has_anthropic,
    has_openai,
    llm_input,
    openai_agent,
):
    # Process LLM query (reactive!)
    if llm_input and llm_input.value:
        # Use whichever agent is available
        active_agent = openai_agent if has_openai else claude_agent
        agent_name = "GPT-4" if has_openai else "Claude"

        llm_msg = Message(role="user", content=llm_input.value)
        llm_response = await active_agent.process(llm_msg)

        print(f"💬 You: {llm_msg.content}")
        print(f"🤖 {agent_name}: {llm_response.content}")
    else:
        llm_response = None
    return active_agent, agent_name, llm_msg, llm_response


@app.cell
def __(mo):
    mo.md(
        """
        ## 5. Testing and Validation

        Let's write some tests to ensure our agents work correctly:
        """
    )
    return


@app.cell
async def __(EchoAgent, Message):
    # Test suite for echo agent
    async def test_echo_agent():
        agent = EchoAgent()

        # Test 1: Basic echoing
        msg = Message(role="user", content="test")
        response = await agent.process(msg)
        assert "Echo: test" in response.content
        print("✅ Test 1 passed: Basic echoing")

        # Test 2: Role is correct
        assert response.role == "assistant"
        print("✅ Test 2 passed: Correct role")

        # Test 3: Agent name
        assert agent.name == "echo-agent"
        print("✅ Test 3 passed: Correct name")

        return "All tests passed! 🎉"

    test_result = await test_echo_agent()
    print(f"\n{test_result}")
    return test_echo_agent, test_result


@app.cell
def __(mo):
    mo.md(
        """
        ## Summary

        Congratulations! 🎉 You've learned:

        ✅ Installation and setup
        ✅ Creating simple agents
        ✅ Composing agent pipelines
        ✅ LLM integration
        ✅ Testing and validation

        ## Next Steps

        - **[Tutorial 02: Production Patterns](02-production-patterns.py)** - Middleware, observability, error handling
        - **[Tutorial 03: Advanced Reasoning](03-advanced-reasoning.py)** - Chain-of-Thought, Tree-of-Thought, etc.
        - **[Examples Directory](https://github.com/scttfrdmn/agenkit/tree/main/examples)** - 150+ examples
        - **[API Documentation](https://agenkit.dev/api/)** - Complete reference

        ## Resources

        - 📚 [Documentation](https://agenkit.dev)
        - 💬 [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
        - 🐛 [Report Issues](https://github.com/scttfrdmn/agenkit/issues)
        - ⭐ [Star on GitHub](https://github.com/scttfrdmn/agenkit)

        Happy building! 🚀
        """
    )
    return


if __name__ == "__main__":
    app.run()
