#!/usr/bin/env python3
"""
Python test harness for cross-language equivalence testing.

Implements the JSON protocol for executing pattern tests.
"""

import json
import sys
import time
from typing import Any, Dict

# Import agenkit patterns
from agenkit.patterns import (
    AgentTool,
    AutonomousAgent,
    CollaborativeAgent,
    ConversationalAgent,
    FallbackAgent,
    HumanInLoopAgent,
    MemoryHierarchy,
    MultiAgentOrchestrator,
    ParallelAgent,
    PlanningAgent,
    ReActAgent,
    ReasoningWithToolsAgent,
    ReflectionAgent,
    RouterAgent,
    SequentialAgent,
    SupervisorAgent,
    Task,
)
from agenkit.techniques.reasoning import (
    ChainOfThought,
    SelfConsistency,
    TreeOfThought,
)
from agenkit.interfaces import Agent, Message

PROTOCOL_VERSION = "1.0"
VERSION = "0.43.0"


# Simple mock agent for testing reasoning techniques
class MockAgent(Agent):
    """Mock agent that returns predictable responses for testing."""

    def __init__(self, responses: list[str] | None = None):
        """Initialize with optional list of responses."""
        self._responses = responses or [
            "1. First, let's analyze the problem.\n2. Then, we'll solve it step by step.\n3. Finally, we arrive at the answer: 42."
        ]
        self._call_count = 0

    @property
    def name(self) -> str:
        return "mock_agent"

    @property
    def capabilities(self) -> list[str]:
        return ["mock", "test"]

    async def process(self, message: Message) -> Message:
        """Return a mock response."""
        response_text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return Message(role="assistant", content=response_text)


# Pattern registry
PATTERNS = {
    "reflection": ReflectionAgent,
    "sequential": SequentialAgent,
    "parallel": ParallelAgent,
    "router": RouterAgent,
    "react": ReActAgent,
    "conversational": ConversationalAgent,
    "agents_as_tools": AgentTool,
    "fallback": FallbackAgent,
    "supervisor": SupervisorAgent,
    "planning": PlanningAgent,
    "task": Task,
    "collaborative": CollaborativeAgent,
    "human_in_loop": HumanInLoopAgent,
    "autonomous": AutonomousAgent,
    "multiagent": MultiAgentOrchestrator,
    "orchestration": None,  # Deprecated - use sequential/parallel/router
    "memory": MemoryHierarchy,
    "reasoning_with_tools": ReasoningWithToolsAgent,
    "self_consistency": SelfConsistency,
    "ChainOfThought": ChainOfThought,
    "TreeOfThought": TreeOfThought,
}


def execute_test(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a test scenario.

    Args:
        payload: Test payload with pattern, scenario_id, and input

    Returns:
        Test result
    """
    pattern_name = payload.get("pattern")
    scenario_id = payload.get("scenario_id")
    input_data = payload.get("input", {})

    # Check if pattern is supported
    if pattern_name not in PATTERNS:
        return {
            "status": "not_implemented",
            "result": None,
            "error": {
                "type": "PatternNotFound",
                "message": f"Pattern '{pattern_name}' not implemented in Python harness",
            },
        }

    pattern_class = PATTERNS[pattern_name]
    if pattern_class is None:
        return {
            "status": "not_implemented",
            "result": None,
            "error": {
                "type": "NotImplemented",
                "message": f"Pattern '{pattern_name}' not yet implemented",
            },
        }

    try:
        # Parse input message
        message_data = input_data.get("message", {})
        message = Message(
            role=message_data.get("role", "user"),
            content=message_data.get("content", ""),
            metadata=message_data.get("metadata", {}),
        )

        # Get configuration
        config = input_data.get("config", {})

        # Create pattern instance and execute
        start_time = time.time()

        # Handle reasoning techniques that need a base agent
        if pattern_name in ("ChainOfThought", "TreeOfThought", "self_consistency"):
            # Create mock agent with varied responses for tree branching
            mock_agent = MockAgent(
                responses=[
                    "1. First approach: analyze directly.\n2. Calculate step by step.\n3. Result: 42",
                    "- Alternative method: work backwards.\n- Apply the formula.\n- Answer: 42",
                    "Step 1: Identify key variables.\nStep 2: Solve systematically.\nStep 3: Verify result is 42",
                ]
            )

            if pattern_name == "ChainOfThought":
                agent = pattern_class(
                    llm=mock_agent,
                    prompt_template=config.get(
                        "prompt_template", "Let's think step by step:\n{query}"
                    ),
                    parse_steps=config.get("parse_steps", True),
                    step_delimiter=config.get("step_delimiter", "\n"),
                    max_steps=config.get("max_steps"),
                )
            elif pattern_name == "TreeOfThought":
                agent = pattern_class(
                    llm=mock_agent,
                    branching_factor=config.get("branching_factor", 2),
                    max_depth=config.get("max_depth", 2),
                    strategy=config.get("strategy", "best-first"),
                    prune_threshold=config.get("prune_threshold", 0.3),
                )
            else:  # self_consistency
                agent = pattern_class(
                    llm=mock_agent,
                    num_samples=config.get("num_samples", 3),
                    voting_strategy=config.get("voting_strategy", "majority"),
                )
        else:
            # For other patterns, instantiation would need more complex setup
            # For now, return not implemented
            return {
                "status": "not_implemented",
                "result": None,
                "error": {
                    "type": "NotImplemented",
                    "message": f"Pattern '{pattern_name}' execution not yet fully implemented in harness",
                },
            }

        # Execute the agent
        import asyncio

        output_message = asyncio.run(agent.process(message))

        duration_ms = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "result": {
                "output": {
                    "message": {
                        "role": output_message.role,
                        "content": output_message.content,
                        "metadata": output_message.metadata,
                    },
                    "behavior": {
                        "turns": 1,
                        "tool_calls": [],
                        "sub_agents": [],
                    },
                },
                "execution_info": {
                    "duration_ms": duration_ms,
                    "llm_calls": 0,
                    "tokens_used": 0,
                },
            },
            "error": None,
        }

    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "error": {
                "type": type(e).__name__,
                "message": str(e),
                "details": {},
            },
        }


def get_info() -> Dict[str, Any]:
    """Get harness information."""
    return {
        "status": "success",
        "result": {
            "language": "python",
            "version": VERSION,
            "patterns_supported": list(PATTERNS.keys()),
            "capabilities": {
                "streaming": True,
                "async": True,
                "llm_providers": ["openai", "anthropic"],
            },
        },
        "error": None,
    }


def health_check() -> Dict[str, Any]:
    """Check harness health."""
    return {
        "status": "success",
        "result": {
            "healthy": True,
            "uptime_seconds": 0.0,  # Stateless harness
        },
        "error": None,
    }


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a request and generate response.

    Args:
        request: Request message

    Returns:
        Response message
    """
    # Validate protocol version
    protocol_version = request.get("protocol_version")
    if protocol_version != PROTOCOL_VERSION:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request.get("request_id"),
            "status": "error",
            "result": None,
            "error": {
                "type": "ProtocolError",
                "message": f"Protocol version mismatch: expected {PROTOCOL_VERSION}, got {protocol_version}",
            },
        }

    command = request.get("command")
    payload = request.get("payload", {})
    request_id = request.get("request_id")

    # Route command
    if command == "execute_test":
        result = execute_test(payload)
    elif command == "get_info":
        result = get_info()
    elif command == "health_check":
        result = health_check()
    else:
        result = {
            "status": "error",
            "result": None,
            "error": {
                "type": "CommandNotFound",
                "message": f"Unknown command: {command}",
            },
        }

    # Build response
    response = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        **result,
    }

    return response


def main():
    """Main entry point - read from stdin, write to stdout."""
    try:
        # Read request from stdin
        request_json = sys.stdin.read()

        # Parse request
        request = json.loads(request_json)

        # Handle request
        response = handle_request(request)

        # Write response to stdout
        print(json.dumps(response))

        # Exit with appropriate code
        sys.exit(0 if response["status"] == "success" else 1)

    except json.JSONDecodeError as e:
        # Invalid JSON
        error_response = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": None,
            "status": "error",
            "result": None,
            "error": {
                "type": "ProtocolError",
                "message": f"Invalid JSON: {e}",
            },
        }
        print(json.dumps(error_response))
        sys.exit(2)

    except Exception as e:
        # Unexpected error
        error_response = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": None,
            "status": "error",
            "result": None,
            "error": {
                "type": "InternalError",
                "message": f"Internal error: {e}",
            },
        }
        print(json.dumps(error_response))
        sys.exit(4)


if __name__ == "__main__":
    main()
