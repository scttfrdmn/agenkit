"""
Platform adapters for A2A protocol.

Enables integration with cloud AI platforms:
- Google Cloud Vertex AI Agent Builder
- AWS Bedrock Agents
"""

from .vertex_ai import VertexAIAdapter, create_vertex_agent
from .bedrock import BedrockAdapter, create_bedrock_agent

__all__ = [
    "VertexAIAdapter",
    "create_vertex_agent",
    "BedrockAdapter",
    "create_bedrock_agent",
]
