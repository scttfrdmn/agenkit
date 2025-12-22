"""
Routing and tool selection for agents.

This module provides intelligent routing and tool selection:
- SemanticToolSelector: Embedding-based tool selection
- LoadBalancerRouter: Distribute load across agent instances
- EnhancedCircuitBreaker: Circuit breaker with advanced features
"""

from .load_balancer import (AgentInstance, InstanceMetrics, LoadBalancerRouter,
                            LoadBalancingStrategy)
from .semantic_selector import (EmbeddingProvider, SemanticToolSelector,
                                ToolDescription, ToolMatch)

__all__ = [
    "AgentInstance",
    "EmbeddingProvider",
    "InstanceMetrics",
    "LoadBalancerRouter",
    "LoadBalancingStrategy",
    "SemanticToolSelector",
    "ToolDescription",
    "ToolMatch",
]
