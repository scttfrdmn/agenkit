"""
Reasoning memory: structured reasoning artifacts, verification, and persistence.

Ports the Go reference (agenkit-go/agenkit/interfaces.go + memory/memory.go):

- ``Verifier`` — exact/binary check of an answer against ground truth, distinct
  from the heuristic float scores used to prune search.
- ``ReasoningArtifact`` — structured intermediate reasoning output (the scored
  candidates a technique explored), not just the final answer text.
- ``ReasoningMemory`` — a ``Memory`` that can also persist and retrieve
  reasoning artifacts per session and technique.
"""

from .artifact import ReasoningArtifact, ScoredCandidate
from .memory import InMemoryReasoningMemory, ReasoningMemory
from .verifier import VerificationResult, Verifier

__all__ = [
    "InMemoryReasoningMemory",
    "ReasoningArtifact",
    "ReasoningMemory",
    "ScoredCandidate",
    "VerificationResult",
    "Verifier",
]
