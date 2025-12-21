"""
Platform adapters for A2A protocol.

Enables integration with cloud AI platforms:
- Google Cloud Vertex AI Agent Builder
- AWS Bedrock Agents
"""

from .bedrock import BedrockAdapter, create_bedrock_agent
from .vertex_ai import VertexAIAdapter, create_vertex_agent

__all__ = [
    "BedrockAdapter",
    "VertexAIAdapter",
    "create_bedrock_agent",
    "create_vertex_agent",
]
