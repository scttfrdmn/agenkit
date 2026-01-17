"""
Tests for experimental RLM implementations.

Note: These are basic validation tests, not comprehensive.
The RLM pattern is experimental and requires real LLM integration for full testing.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from basic_rlm import RecursiveREPLAgent

from agenkit.interfaces import Agent, Message


class MockAgent(Agent):
    """Mock agent for testing RLM mechanics."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or []
        self.call_count = 0

    def name(self) -> str:
        return "mock-agent"

    async def process(self, message: Message) -> Message:
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
        else:
            response = "FINAL(test answer)"

        self.call_count += 1
        return Message("assistant", response)


@pytest.mark.asyncio
async def test_rlm_initialization():
    """Test RLM agent can be initialized."""
    agent = MockAgent()
    rlm = RecursiveREPLAgent(agent=agent, max_iterations=10)

    assert rlm.agent == agent
    assert rlm.max_iterations == 10


@pytest.mark.asyncio
async def test_rlm_extracts_final_direct():
    """Test RLM extracts FINAL(answer) format."""
    agent = MockAgent(responses=["FINAL(test answer)"])
    rlm = RecursiveREPLAgent(agent=agent)

    message = Message("user", "test context")
    result = await rlm.process(message)

    assert "test answer" in result.content


@pytest.mark.asyncio
async def test_rlm_extracts_final_var():
    """Test RLM extracts FINAL_VAR(variable) format."""
    responses = [
        """
```python
result_var = "computed answer"
```
FINAL_VAR(result_var)
"""
    ]

    agent = MockAgent(responses=responses)
    rlm = RecursiveREPLAgent(agent=agent)

    message = Message("user", "test context")
    result = await rlm.process(message)

    assert "computed answer" in result.content


@pytest.mark.asyncio
async def test_rlm_executes_code():
    """Test RLM can execute Python code in REPL."""
    responses = [
        """
```python
x = 5 + 3
print(f"Result: {x}")
```
""",
        "FINAL(8)",
    ]

    agent = MockAgent(responses=responses)
    rlm = RecursiveREPLAgent(agent=agent)

    message = Message("user", "calculate 5 + 3")
    result = await rlm.process(message)

    assert "8" in result.content


@pytest.mark.asyncio
async def test_rlm_max_iterations():
    """Test RLM respects max iterations limit."""
    # Agent never outputs FINAL - should hit max iterations
    agent = MockAgent(responses=['print("still working")'] * 100)
    rlm = RecursiveREPLAgent(agent=agent, max_iterations=3)

    message = Message("user", "test context")
    result = await rlm.process(message)

    assert "Maximum iterations" in result.content
    assert agent.call_count <= 3


@pytest.mark.asyncio
async def test_rlm_context_loaded():
    """Test context is properly loaded into REPL namespace."""
    responses = [
        """
```python
context_length = len(context)
print(f"Context has {context_length} characters")
```
FINAL_VAR(context_length)
"""
    ]

    agent = MockAgent(responses=responses)
    rlm = RecursiveREPLAgent(agent=agent)

    test_context = "A" * 1000
    message = Message("user", test_context)
    result = await rlm.process(message)

    assert "1000" in result.content


@pytest.mark.asyncio
async def test_code_extraction():
    """Test code block extraction from agent responses."""
    agent = MockAgent()
    rlm = RecursiveREPLAgent(agent=agent)

    text = """
Here's some code:
```python
x = 5
print(x)
```

And more:
```repl
y = 10
```
"""

    blocks = rlm._extract_code_blocks(text)
    assert len(blocks) == 2
    assert "x = 5" in blocks[0]
    assert "y = 10" in blocks[1]


@pytest.mark.asyncio
async def test_system_prompt_generation():
    """Test system prompt includes context metadata."""
    agent = MockAgent()
    rlm = RecursiveREPLAgent(agent=agent)

    prompt = rlm._build_system_prompt(context_length=100000)

    assert "100,000" in prompt
    assert "context" in prompt.lower()
    assert "llm_query" in prompt


def test_final_answer_extraction():
    """Test final answer extraction from text."""
    agent = MockAgent()
    rlm = RecursiveREPLAgent(agent=agent)

    # Test FINAL() extraction
    text1 = "Some reasoning... FINAL(the answer is 42)"
    answer1 = rlm._extract_final_answer(text1, {})
    assert answer1 == "the answer is 42"

    # Test FINAL_VAR() extraction
    namespace = {"my_var": "variable answer"}
    text2 = "Computing... FINAL_VAR(my_var)"
    answer2 = rlm._extract_final_answer(text2, namespace)
    assert answer2 == "variable answer"

    # Test no answer
    text3 = "Still working on it..."
    answer3 = rlm._extract_final_answer(text3, {})
    assert answer3 is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
