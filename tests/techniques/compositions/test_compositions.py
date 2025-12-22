"""Tests for composition techniques."""

from unittest.mock import patch

import pytest

from agenkit import Message
from agenkit.techniques.compositions import (
    ActionStats,
    ActorCriticVariation,
    CitedRAG,
    ContextOptimizer,
    Document,
    ExplorationStrategy,
    GoalMonitor,
    Interaction,
    LearningFromFeedback,
    PrioritizedTask,
    PriorityTaskExecutor,
    SimpleApprovalTool,
    SimpleRAG,
    TaskQueue,
)


# Mock agents for testing
class MockAgent:
    """Mock agent for testing."""

    def __init__(self, response="Mock response"):
        self.response = response
        self.name = "mock_agent"
        self.capabilities = ["mock"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=self.response,
            metadata={"processed": True}
        )


# Simple Human Approval Tests

@pytest.mark.asyncio
async def test_simple_approval_tool():
    """Test basic approval tool."""
    tool = SimpleApprovalTool()

    with patch('builtins.input', return_value='y'):
        result = await tool.execute("test action")

    assert result["approved"] is True
    assert result["response"] == "y"


@pytest.mark.asyncio
async def test_simple_approval_tool_reject():
    """Test approval rejection."""
    tool = SimpleApprovalTool()

    with patch('builtins.input', return_value='n'):
        result = await tool.execute("test action")

    assert result["approved"] is False
    assert result["response"] == "n"


@pytest.mark.asyncio
async def test_simple_approval_with_details():
    """Test approval with details."""
    tool = SimpleApprovalTool()

    with patch('builtins.input', return_value='yes'):
        result = await tool.execute("delete file", details="file.txt")

    assert result["approved"] is True


# RAG Tests

@pytest.mark.asyncio
async def test_simple_rag():
    """Test basic RAG composition."""
    def mock_retriever(query: str):
        return ["Document 1 content", "Document 2 content"]

    agent = MockAgent("Answer based on documents")
    rag = SimpleRAG(
        retriever=mock_retriever,
        answerer=agent,
        max_docs=5
    )

    response = await rag.process(Message(
        role="user",
        content="What is the answer?"
    ))

    assert response.content == "Answer based on documents"
    assert response.metadata["technique"] == "simple_rag"
    assert response.metadata["num_sources"] == 2
    assert "sources" in response.metadata


@pytest.mark.asyncio
async def test_simple_rag_no_documents():
    """Test RAG with no retrieved documents."""
    def mock_retriever(query: str):
        return []

    agent = MockAgent("No documents available")
    rag = SimpleRAG(
        retriever=mock_retriever,
        answerer=agent
    )

    response = await rag.process(Message(
        role="user",
        content="Question"
    ))

    assert response.metadata["num_sources"] == 0


@pytest.mark.asyncio
async def test_simple_rag_max_docs():
    """Test RAG respects max_docs limit."""
    def mock_retriever(query: str):
        return [f"Doc {i}" for i in range(10)]

    agent = MockAgent()
    rag = SimpleRAG(
        retriever=mock_retriever,
        answerer=agent,
        max_docs=3
    )

    response = await rag.process(Message(
        role="user",
        content="Question"
    ))

    assert response.metadata["num_sources"] == 3


# Cited RAG Tests

@pytest.mark.asyncio
async def test_cited_rag():
    """Test RAG with citations."""
    def mock_retriever(query: str):
        return [
            Document("Content 1", "Source 1"),
            Document("Content 2", "Source 2")
        ]

    agent = MockAgent("Answer with [1] and [2] citations")
    rag = CitedRAG(
        retriever=mock_retriever,
        answerer=agent
    )

    response = await rag.process(Message(
        role="user",
        content="Question"
    ))

    assert response.metadata["technique"] == "cited_rag"
    assert response.metadata["num_sources"] == 2
    assert len(response.metadata["citations"]) == 2
    assert "Source 1" in response.metadata["sources"]


@pytest.mark.asyncio
async def test_cited_rag_no_documents():
    """Test cited RAG with no documents."""
    def mock_retriever(query: str):
        return []

    agent = MockAgent()
    rag = CitedRAG(
        retriever=mock_retriever,
        answerer=agent
    )

    response = await rag.process(Message(
        role="user",
        content="Question"
    ))

    assert response.metadata["num_sources"] == 0
    assert "No relevant sources" in response.content


@pytest.mark.asyncio
async def test_cited_rag_citation_format():
    """Test different citation formats."""
    def mock_retriever(query: str):
        return [Document("Content", "Author 2020")]

    agent = MockAgent()

    # Numeric format
    rag_numeric = CitedRAG(
        retriever=mock_retriever,
        answerer=agent,
        citation_format="numeric"
    )
    response = await rag_numeric.process(Message(role="user", content="Q"))
    assert "[1]" in response.metadata["citations"][0]

    # Author-year format
    rag_author = CitedRAG(
        retriever=mock_retriever,
        answerer=agent,
        citation_format="author_year"
    )
    response = await rag_author.process(Message(role="user", content="Q"))
    assert "(" in response.metadata["citations"][0]


# Context Optimization Tests

@pytest.mark.asyncio
async def test_context_optimizer_no_optimization():
    """Test context optimizer when under token limit."""
    agent = MockAgent("Response")
    summarizer = MockAgent("Summary")

    optimizer = ContextOptimizer(
        agent=agent,
        summarizer=summarizer,
        max_tokens=1000
    )

    short_message = Message(role="user", content="Short query")
    response = await optimizer.process(short_message)

    assert response.metadata["optimized"] is False
    assert response.metadata["original_tokens"] < 1000


@pytest.mark.asyncio
async def test_context_optimizer_with_optimization():
    """Test context optimizer when over token limit."""
    agent = MockAgent("Response")
    summarizer = MockAgent("Short summary")

    optimizer = ContextOptimizer(
        agent=agent,
        summarizer=summarizer,
        max_tokens=10  # Very low limit to trigger optimization
    )

    long_message = Message(role="user", content=" ".join(["word"] * 100))
    response = await optimizer.process(long_message)

    assert response.metadata["optimized"] is True
    assert "compressed_tokens" in response.metadata
    assert "compression_ratio" in response.metadata


# Prioritization Tests

def test_task_queue_add_task():
    """Test adding tasks to queue."""
    queue = TaskQueue()

    task_id = queue.add_task({"name": "Task 1"})

    assert task_id == 0
    assert queue.size() == 1


def test_task_queue_get_next():
    """Test getting next task."""
    queue = TaskQueue(priority_fn=lambda t: t.get("priority", 0))

    queue.add_task({"name": "Low", "priority": 1})
    queue.add_task({"name": "High", "priority": 10})

    next_task = queue.get_next_task()
    assert next_task["name"] == "High"  # Higher priority first


def test_task_queue_empty():
    """Test empty queue behavior."""
    queue = TaskQueue()

    assert queue.is_empty()
    assert queue.get_next_task() is None


def test_task_queue_peek():
    """Test peeking at next task."""
    queue = TaskQueue()
    queue.add_task({"name": "Task"})

    peeked = queue.peek_next_task()
    assert peeked["name"] == "Task"
    assert queue.size() == 1  # Not removed


def test_task_queue_clear():
    """Test clearing queue."""
    queue = TaskQueue()
    queue.add_task({"name": "Task"})
    queue.clear()

    assert queue.is_empty()


@pytest.mark.asyncio
async def test_priority_task_executor():
    """Test priority task executor."""
    results = []

    async def process_fn(task):
        results.append(task["name"])
        return task["name"]

    executor = PriorityTaskExecutor(
        priority_fn=lambda t: t.get("priority", 0),
        process_fn=process_fn
    )

    executor.add_task({"name": "Low", "priority": 1})
    executor.add_task({"name": "High", "priority": 10})

    await executor.execute_all()

    assert results[0] == "High"  # Executed first
    assert len(results) == 2


# Goal Monitoring Tests

@pytest.mark.asyncio
async def test_goal_monitor_goal_reached():
    """Test goal monitoring when goal is reached."""
    agent = MockAgent("Progress made")

    def goal_fn(state):
        return state.get("progress", 0) >= 1.0

    monitor = GoalMonitor(
        agent=agent,
        goal_fn=goal_fn,
        max_iterations=10
    )

    # Mock extract state to return progress
    def extract_state(msg):
        return {"progress": 1.0}

    monitor.extract_state_fn = extract_state

    result = await monitor.achieve_goal(
        initial_message=Message(role="user", content="Start task")
    )

    assert result.metadata["goal_reached"] is True
    assert result.metadata["iterations"] <= 10


@pytest.mark.asyncio
async def test_goal_monitor_max_iterations():
    """Test goal monitoring reaches max iterations."""
    agent = MockAgent("Still working")

    def goal_fn(state):
        return False  # Never reached

    monitor = GoalMonitor(
        agent=agent,
        goal_fn=goal_fn,
        max_iterations=3
    )

    result = await monitor.achieve_goal(
        initial_message=Message(role="user", content="Start task")
    )

    assert result.metadata["goal_reached"] is False
    assert result.metadata["iterations"] == 3


# Exploration Strategy Tests

@pytest.mark.asyncio
async def test_exploration_strategy():
    """Test exploration strategy with UCB."""
    agent = MockAgent("Action result")
    actions = ["action1", "action2", "action3"]

    explorer = ExplorationStrategy(
        agent=agent,
        actions=actions,
        exploration_constant=1.0
    )

    response = await explorer.process(Message(
        role="user",
        content="Task"
    ))

    assert response.metadata["technique"] == "exploration_strategy"
    assert "selected_action" in response.metadata
    assert response.metadata["selected_action"] in actions


@pytest.mark.asyncio
async def test_exploration_selects_untried_first():
    """Test that UCB selects untried actions first."""
    agent = MockAgent("Result")
    actions = ["action1", "action2"]

    explorer = ExplorationStrategy(
        agent=agent,
        actions=actions
    )

    # First call should select action (both untried)
    response1 = await explorer.process(Message(role="user", content="Task"))
    selected1 = response1.metadata["selected_action"]

    # Second call should select the other untried action
    response2 = await explorer.process(Message(role="user", content="Task"))
    selected2 = response2.metadata["selected_action"]

    # Both actions should be tried
    assert {selected1, selected2} == set(actions)


def test_exploration_get_best_action():
    """Test getting best action by mean reward."""
    agent = MockAgent()
    explorer = ExplorationStrategy(agent=agent, actions=["a1", "a2"])

    # Manually update stats
    explorer.update_stats("a1", 0.9)
    explorer.update_stats("a2", 0.5)

    best = explorer.get_best_action()
    assert best == "a1"


# Learning from Feedback Tests

@pytest.mark.asyncio
async def test_learning_from_feedback():
    """Test learning from feedback composition."""
    agent = MockAgent("Answer")

    learner = LearningFromFeedback(
        agent=agent,
        max_context_examples=3
    )

    # First interaction - no context
    response1 = await learner.process(Message(
        role="user",
        content="How do I sort a list?"
    ))

    assert response1.metadata["similar_examples"] == 0

    # Add feedback
    learner.add_feedback(response1, score=0.8)

    # Second interaction - should use first as context
    response2 = await learner.process(Message(
        role="user",
        content="How do I sort a dictionary?"
    ))

    assert response2.metadata["similar_examples"] > 0


def test_learning_similarity():
    """Test similarity computation."""
    agent = MockAgent()
    learner = LearningFromFeedback(agent=agent)

    similarity = learner._default_similarity(
        "sort a list",
        "sort a dictionary"
    )

    assert 0.0 <= similarity <= 1.0
    assert similarity > 0  # Should have some overlap


def test_learning_memory_stats():
    """Test memory statistics."""
    agent = MockAgent()
    learner = LearningFromFeedback(agent=agent)

    # Add some interactions
    learner.memory.append(Interaction("Q1", "A1", feedback_score=0.8))
    learner.memory.append(Interaction("Q2", "A2", feedback_score=0.9))

    stats = learner.get_memory_stats()

    assert stats["total_interactions"] == 2
    assert stats["with_feedback"] == 2
    assert 0.8 <= stats["average_feedback"] <= 0.9


# Actor-Critic Variation Tests

@pytest.mark.asyncio
async def test_actor_critic_variation():
    """Test actor-critic composition."""
    actor = MockAgent("Initial solution")
    critic = MockAgent("Score: 8/10\nGood but could be better")

    ac = ActorCriticVariation(
        actor=actor,
        critic=critic,
        max_iterations=3
    )

    response = await ac.process(Message(
        role="user",
        content="Write a function"
    ))

    assert response.metadata["technique"] == "actor_critic_variation"
    assert "iterations" in response.metadata
    assert "final_score" in response.metadata
    assert "note" in response.metadata  # Educational note


@pytest.mark.asyncio
async def test_actor_critic_score_extraction():
    """Test score extraction from critique."""
    actor = MockAgent()
    critic_low = MockAgent("Score: 3/10\nNeeds improvement")
    MockAgent("Score: 9/10\nExcellent")

    ac = ActorCriticVariation(actor=actor, critic=critic_low, max_iterations=5)

    response = await ac.process(Message(role="user", content="Task"))

    # Should iterate more due to low score
    assert response.metadata["iterations"] > 1


# Data Class Tests

def test_prioritized_task():
    """Test PrioritizedTask dataclass."""
    task = PrioritizedTask(priority=5.0, task="Task data", task_id=1)

    assert task.priority == 5.0
    assert task.task == "Task data"
    assert task.task_id == 1


def test_action_stats():
    """Test ActionStats dataclass."""
    stats = ActionStats(action="test_action")

    assert stats.trials == 0
    assert stats.mean_reward == 0.0

    stats.update(0.8)
    assert stats.trials == 1
    assert stats.mean_reward == 0.8

    stats.update(0.6)
    assert stats.trials == 2
    assert stats.mean_reward == 0.7  # (0.8 + 0.6) / 2


def test_interaction():
    """Test Interaction dataclass."""
    interaction = Interaction(
        query="Test query",
        response="Test response",
        feedback_score=0.9
    )

    assert interaction.query == "Test query"
    assert interaction.response == "Test response"
    assert interaction.feedback_score == 0.9
    assert interaction.timestamp is not None


def test_document():
    """Test Document dataclass."""
    doc = Document(
        content="Document content",
        source="Source 2020",
        metadata={"page": 42}
    )

    assert doc.content == "Document content"
    assert doc.source == "Source 2020"
    assert doc.metadata["page"] == 42


# Capability Tests

def test_simple_rag_capabilities():
    """Test SimpleRAG capabilities."""
    rag = SimpleRAG(retriever=lambda q: [], answerer=MockAgent())

    caps = rag.capabilities

    assert "retrieval" in caps
    assert "rag" in caps


def test_exploration_capabilities():
    """Test ExplorationStrategy capabilities."""
    explorer = ExplorationStrategy(
        agent=MockAgent(),
        actions=["a1", "a2"]
    )

    caps = explorer.capabilities

    assert "exploration" in caps
    assert "ucb" in caps


# Name Tests

def test_agent_names():
    """Test that all agents have correct names."""
    assert SimpleRAG(lambda q: [], MockAgent()).name == "simple_rag"
    assert CitedRAG(lambda q: [], MockAgent()).name == "cited_rag"
    assert ContextOptimizer(MockAgent(), MockAgent()).name == "context_optimizer"
    assert GoalMonitor(MockAgent(), lambda s: False).name == "goal_monitor"
    assert ExplorationStrategy(MockAgent(), ["a"]).name == "exploration_strategy"
    assert LearningFromFeedback(MockAgent()).name == "learning_feedback"
    assert ActorCriticVariation(MockAgent(), MockAgent()).name == "actor_critic_variation"
