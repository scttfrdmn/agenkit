"""
AWS Lambda Handler for Agenkit Agents

This handler provides a serverless interface for running Agenkit agents on AWS Lambda
with API Gateway integration, CloudWatch logging, and X-Ray tracing.
"""

import json
import os
from typing import Any, Dict

# AWS Lambda and X-Ray
try:
    from aws_xray_sdk.core import xray_recorder
    from aws_xray_sdk.core import patch_all

    patch_all()
    XRAY_ENABLED = True
except ImportError:
    XRAY_ENABLED = False
    print("Warning: aws-xray-sdk not installed. X-Ray tracing disabled.")

# Agenkit imports
from agenkit.interfaces import Message
from agenkit.patterns import ReActAgent, ConversationalAgent, RouterPattern


# ============================================================
# Agent Configuration
# ============================================================


def create_react_agent():
    """Create a ReAct agent with tool usage capabilities."""
    from agenkit.tools import Tool

    # Example tools
    class CalculatorTool(Tool):
        @property
        def name(self) -> str:
            return "calculator"

        @property
        def description(self) -> str:
            return "Performs basic arithmetic operations"

        async def execute(self, **kwargs) -> str:
            operation = kwargs.get("operation")
            a = float(kwargs.get("a", 0))
            b = float(kwargs.get("b", 0))

            if operation == "add":
                return str(a + b)
            elif operation == "subtract":
                return str(a - b)
            elif operation == "multiply":
                return str(a * b)
            elif operation == "divide":
                return str(a / b if b != 0 else "Error: Division by zero")
            else:
                return f"Unknown operation: {operation}"

    # Create mock LLM (replace with real LLM in production)
    class MockLLM:
        @property
        def name(self) -> str:
            return "mock-llm"

        @property
        def capabilities(self) -> list[str]:
            return ["text-generation"]

        async def process(self, message: Message) -> Message:
            # In production, replace with OpenAI, Anthropic, Bedrock, etc.
            return Message(
                role="assistant",
                content=f"Processed: {message.content}",
                metadata={"model": "mock-llm"},
            )

    agent = ReActAgent(
        agent=MockLLM(),
        tools=[CalculatorTool()],
        max_steps=5,
        verbose=True,
    )
    return agent


def create_conversational_agent():
    """Create a conversational agent with memory."""

    class MockLLMClient:
        async def chat(self, messages: list[Dict[str, str]]) -> str:
            # In production, integrate with real LLM
            last_message = messages[-1]["content"] if messages else ""
            return f"Response to: {last_message}"

    agent = ConversationalAgent(
        llm_client=MockLLMClient(),
        max_history=10,
        system_prompt="You are a helpful AI assistant deployed on AWS Lambda.",
    )
    return agent


def create_router_agent():
    """Create a router agent that delegates to specialists."""

    # Simple routing function
    def route_message(message: Message) -> str:
        content = message.content.lower()
        if "calculate" in content or "math" in content:
            return "calculator"
        elif "chat" in content or "talk" in content:
            return "conversational"
        else:
            return "react"

    router = RouterPattern(
        router=route_message,
        agents={
            "calculator": create_react_agent(),
            "conversational": create_conversational_agent(),
            "react": create_react_agent(),
        },
    )
    return router


# ============================================================
# Agent Registry
# ============================================================

AGENTS = {
    "react": create_react_agent,
    "conversational": create_conversational_agent,
    "router": create_router_agent,
}


# ============================================================
# Lambda Handler
# ============================================================


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Agenkit agents.

    Expected event format (API Gateway):
    {
        "body": json.dumps({
            "agent_type": "react",  # or "conversational", "router"
            "message": {
                "role": "user",
                "content": "Your message here",
                "metadata": {}
            }
        })
    }

    Returns:
    {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "role": "assistant",
            "content": "Agent response",
            "metadata": {...}
        })
    }
    """
    # Start X-Ray segment if enabled
    if XRAY_ENABLED:
        segment = xray_recorder.begin_segment("agenkit-lambda")
    else:
        segment = None

    try:
        # Parse request body
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        # Extract agent type and message
        agent_type = body.get("agent_type", "react")
        message_data = body.get("message", {})

        # Validate agent type
        if agent_type not in AGENTS:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "error": f"Unknown agent type: {agent_type}",
                        "available_types": list(AGENTS.keys()),
                    }
                ),
            }

        # Create message
        message = Message(
            role=message_data.get("role", "user"),
            content=message_data.get("content", ""),
            metadata=message_data.get("metadata", {}),
        )

        # X-Ray subsegment for agent execution
        if XRAY_ENABLED:
            subsegment = xray_recorder.begin_subsegment(f"agent-{agent_type}")

        # Create and execute agent
        agent = AGENTS[agent_type]()

        # Run agent (async requires event loop setup)
        import asyncio

        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(agent.process(message))

        if XRAY_ENABLED:
            xray_recorder.end_subsegment()

        # Convert response to dict
        response_dict = {
            "role": response.role,
            "content": response.content,
            "metadata": response.metadata,
        }

        # Add Lambda context metadata
        response_dict["metadata"]["lambda"] = {
            "request_id": context.request_id,
            "function_name": context.function_name,
            "memory_limit": context.memory_limit_in_mb,
            "remaining_time_ms": context.get_remaining_time_in_millis(),
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Agent-Type": agent_type,
            },
            "body": json.dumps(response_dict),
        }

    except Exception as e:
        # Log error
        print(f"Error processing request: {str(e)}")
        import traceback

        traceback.print_exc()

        # Return error response
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": "Internal server error", "message": str(e)}
            ),
        }

    finally:
        if XRAY_ENABLED and segment:
            xray_recorder.end_segment()


# ============================================================
# Local Testing
# ============================================================

if __name__ == "__main__":
    # Test locally
    test_event = {
        "body": json.dumps(
            {
                "agent_type": "react",
                "message": {"role": "user", "content": "Calculate 5 + 3"},
            }
        )
    }

    # Mock context
    class MockContext:
        request_id = "test-request-id"
        function_name = "test-function"
        memory_limit_in_mb = 128

        def get_remaining_time_in_millis(self):
            return 30000

    response = lambda_handler(test_event, MockContext())
    print(json.dumps(response, indent=2))
