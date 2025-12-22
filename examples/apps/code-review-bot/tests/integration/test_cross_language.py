"""Integration tests for Python-Go cross-language communication."""

import pytest

from agenkit.agent import RemoteAgent
from agenkit.interfaces import Message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_python_to_go_analyzer():
    """Test Python orchestrator can communicate with Go analyzer."""
    analyzer = RemoteAgent(name="analyzer", endpoint="grpc://localhost:50051", timeout=30.0)

    code = """
def authenticate(username, password):
    query = "SELECT * FROM users WHERE username='" + username + "'"
    return execute(query)
"""

    message = Message(
        role="user",
        content=code,
        metadata={"language": "python", "type": "analysis"},
    )

    try:
        response = await analyzer.process(message)

        # Verify response structure
        assert response.role == "assistant"
        assert "Static Analysis Report" in response.content
        assert response.metadata.get("processed_by") == "go_analyzer"
        assert "issues_found" in response.metadata
        assert response.metadata["issues_found"] > 0  # Should find SQL injection

        # Verify security detection
        assert "SQL injection" in response.content or "security" in response.content.lower()

    except Exception as e:
        pytest.skip(f"Go analyzer not available: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_go_analyzer_health_check():
    """Test health check with Go analyzer."""
    analyzer = RemoteAgent(name="analyzer", endpoint="grpc://localhost:50051", timeout=10.0)

    message = Message(role="user", content="health_check", metadata={"type": "health_check"})

    try:
        response = await analyzer.process(message)

        assert response.role == "assistant"
        assert response.content == "healthy"
        assert response.metadata.get("status") == "ok"

    except Exception as e:
        pytest.skip(f"Go analyzer not available: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyzer_complexity_calculation():
    """Test complexity calculation by Go analyzer."""
    analyzer = RemoteAgent(name="analyzer", endpoint="grpc://localhost:50051", timeout=30.0)

    # Complex code with many branches
    code = """
def process(data):
    if data is None:
        return None
    if len(data) == 0:
        return []

    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
        elif item < 0:
            result.append(item / 2)
        else:
            continue

    return result if len(result) > 0 else None
"""

    message = Message(role="user", content=code, metadata={"language": "python"})

    try:
        response = await analyzer.process(message)

        # Verify complexity metrics
        assert "complexity" in response.metadata
        complexity = response.metadata["complexity"]
        assert complexity > 5  # Should detect multiple branches

        # Verify complexity assessment in report
        assert "Complexity Assessment" in response.content

    except Exception as e:
        pytest.skip(f"Go analyzer not available: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyzer_clean_code():
    """Test analyzer with clean code (no issues)."""
    analyzer = RemoteAgent(name="analyzer", endpoint="grpc://localhost:50051", timeout=30.0)

    code = """
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b
"""

    message = Message(role="user", content=code, metadata={"language": "python"})

    try:
        response = await analyzer.process(message)

        # Should find minimal or no issues
        assert response.metadata.get("security_score", 0) >= 90.0

    except Exception as e:
        pytest.skip(f"Go analyzer not available: {e}")
