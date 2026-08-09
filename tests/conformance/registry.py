"""Explicit registry of concrete Agent classes for the conformance suite.

Two lists, for two different jobs:

- ``ALL_AGENT_CLASSES``: every class object, for Layer A (static conformance,
  needs no instance).
- ``AGENT_CASES``: factory lambdas for Layer B (behavioral conformance,
  needs a real instance) -- following the only existing precedent in this
  repo for parametrizing over multiple concrete types,
  ``tests/techniques/reasoning/test_temperature_plumbing.py``'s
  ``pytest.param(lambda ...: SomeClass(...), id="...")`` style. Deliberately
  not auto-discovery: nothing here subclasses via ``__subclasses__()`` or a
  registry convention (this codebase uses hand-curated ``__all__`` lists
  throughout), and import-based discovery would throw on 6 optional LLM
  provider deps and still miss the 4 Protocol-implementing classes that
  don't subclass ``Agent`` at all.

``EXCLUDED`` documents every census entry NOT in ``AGENT_CASES``, each with
a reason and (where applicable) an issue number. ``test_registry_coverage.py``
asserts ``census == AGENT_CASES ids | EXCLUDED keys`` -- this registry can
never silently drift out of sync with the real codebase; a class that is
neither registered nor excluded fails CI.
"""

from __future__ import annotations

import pytest

# Layer A imports: every concrete Agent subclass, keyed the same way as the
# census ((name, relative_file_path) -> class object). Static conformance
# needs no fixtures, so this list is complete from day one -- only Layer B
# (below) is staged in tranches.
from agenkit.adapters.python.remote_agent import RemoteAgent
from agenkit.agents_md.integration import AgentsMdMiddleware
from agenkit.auth.middleware import APIKeyAuth, BearerTokenAuth
from agenkit.composition.conditional import ConditionalAgent
from agenkit.composition.fallback import FallbackAgent as CompositionFallbackAgent
from agenkit.composition.parallel import ParallelAgent as CompositionParallelAgent
from agenkit.composition.sequential import SequentialAgent as CompositionSequentialAgent
from agenkit.infrastructure.load_balancer import LoadBalancer
from agenkit.infrastructure.retry_enhanced import EnhancedRetryDecorator
from agenkit.middleware.batching import BatchingDecorator
from agenkit.middleware.caching import CachingDecorator
from agenkit.middleware.circuit_breaker import CircuitBreakerDecorator
from agenkit.middleware.metrics import MetricsDecorator
from agenkit.middleware.per_user_rate_limiter import PerUserRateLimiterDecorator
from agenkit.middleware.rate_limiter import RateLimiterDecorator
from agenkit.middleware.retry import RetryDecorator
from agenkit.middleware.timeout import TimeoutDecorator
from agenkit.patterns.autonomous import AutonomousAgent
from agenkit.patterns.collaborative import CollaborativeAgent
from agenkit.patterns.conversational import ConversationalAgent, StreamingConversationalAgent
from agenkit.patterns.fallback import FallbackAgent, RecoveryAgent
from agenkit.patterns.human_in_loop import HumanInLoopAgent
from agenkit.patterns.multiagent import (
    ConsensusAgent,
    ConsensusConfig,
    MultiAgentConfig,
    MultiAgentOrchestrator,
)
from agenkit.patterns.orchestration import (
    OrchestrationAgent,
    ParallelPattern,
    RouterPattern,
    SequentialPattern,
)
from agenkit.patterns.parallel import ParallelAgent
from agenkit.patterns.planning import PlanningAgent
from agenkit.patterns.react import ReActAgent
from agenkit.patterns.reasoning_with_tools import ReasoningWithToolsAgent
from agenkit.patterns.reflection import ReflectionAgent
from agenkit.patterns.router import RouterAgent
from agenkit.patterns.sequential import SequentialAgent
from agenkit.patterns.supervisor import SupervisorAgent
from agenkit.routing.load_balancer import LoadBalancerRouter
from agenkit.safety.anomaly_detection import AnomalyDetectionMiddleware
from agenkit.safety.input_validation import InputValidationMiddleware
from agenkit.safety.output_validation import OutputValidationMiddleware
from agenkit.safety.permissions import PermissionMiddleware
from agenkit.skills.agent import SkillEnabledAgent
from agenkit.techniques.compositions.actor_critic_variation import ActorCriticVariation
from agenkit.techniques.compositions.context_optimization import ContextOptimizer
from agenkit.techniques.compositions.exploration import ExplorationStrategy
from agenkit.techniques.compositions.goal_monitoring import GoalMonitor
from agenkit.techniques.compositions.learning_feedback import LearningFromFeedback
from agenkit.techniques.compositions.rag import SimpleRAG
from agenkit.techniques.compositions.rag_with_citations import CitedRAG
from agenkit.techniques.reasoning.chain_of_thought import ChainOfThought
from agenkit.techniques.reasoning.graph_of_thought import GraphOfThought
from agenkit.techniques.reasoning.least_to_most import LeastToMost
from agenkit.techniques.reasoning.plan_and_solve import PlanAndSolve
from agenkit.techniques.reasoning.self_consistency import SelfConsistency
from agenkit.techniques.reasoning.tree_of_thought import TreeOfThought
from agenkit.tools.tool_agent import ToolAgent

ALL_AGENT_CLASSES: list[type] = [
    APIKeyAuth,
    ActorCriticVariation,
    AgentsMdMiddleware,
    AnomalyDetectionMiddleware,
    AutonomousAgent,
    BatchingDecorator,
    BearerTokenAuth,
    CachingDecorator,
    ChainOfThought,
    CircuitBreakerDecorator,
    CitedRAG,
    CollaborativeAgent,
    ConditionalAgent,
    ConsensusAgent,
    ContextOptimizer,
    ConversationalAgent,
    EnhancedRetryDecorator,
    ExplorationStrategy,
    CompositionFallbackAgent,
    FallbackAgent,
    GoalMonitor,
    GraphOfThought,
    HumanInLoopAgent,
    InputValidationMiddleware,
    LearningFromFeedback,
    LeastToMost,
    LoadBalancer,
    LoadBalancerRouter,
    MetricsDecorator,
    MultiAgentOrchestrator,
    OrchestrationAgent,
    OutputValidationMiddleware,
    CompositionParallelAgent,
    ParallelAgent,
    ParallelPattern,
    PerUserRateLimiterDecorator,
    PermissionMiddleware,
    PlanAndSolve,
    PlanningAgent,
    RateLimiterDecorator,
    ReActAgent,
    ReasoningWithToolsAgent,
    RecoveryAgent,
    ReflectionAgent,
    RemoteAgent,
    RetryDecorator,
    RouterAgent,
    RouterPattern,
    SelfConsistency,
    CompositionSequentialAgent,
    SequentialAgent,
    SequentialPattern,
    SimpleRAG,
    SkillEnabledAgent,
    StreamingConversationalAgent,
    SupervisorAgent,
    TimeoutDecorator,
    ToolAgent,
    TreeOfThought,
]

# Census key -> class object, so test_registry_coverage.py can compare the
# AST census directly against this registry without a second name-collision
# hazard (SequentialAgent/ParallelAgent/FallbackAgent each have two distinct
# classes, one per module).
CENSUS_KEY_TO_CLASS: dict[tuple[str, str], type] = {
    ("APIKeyAuth", "agenkit/auth/middleware.py"): APIKeyAuth,
    (
        "ActorCriticVariation",
        "agenkit/techniques/compositions/actor_critic_variation.py",
    ): ActorCriticVariation,
    ("AgentsMdMiddleware", "agenkit/agents_md/integration.py"): AgentsMdMiddleware,
    (
        "AnomalyDetectionMiddleware",
        "agenkit/safety/anomaly_detection.py",
    ): AnomalyDetectionMiddleware,
    ("AutonomousAgent", "agenkit/patterns/autonomous.py"): AutonomousAgent,
    ("BatchingDecorator", "agenkit/middleware/batching.py"): BatchingDecorator,
    ("BearerTokenAuth", "agenkit/auth/middleware.py"): BearerTokenAuth,
    ("CachingDecorator", "agenkit/middleware/caching.py"): CachingDecorator,
    (
        "ChainOfThought",
        "agenkit/techniques/reasoning/chain_of_thought.py",
    ): ChainOfThought,
    (
        "CircuitBreakerDecorator",
        "agenkit/middleware/circuit_breaker.py",
    ): CircuitBreakerDecorator,
    ("CitedRAG", "agenkit/techniques/compositions/rag_with_citations.py"): CitedRAG,
    ("CollaborativeAgent", "agenkit/patterns/collaborative.py"): CollaborativeAgent,
    ("ConditionalAgent", "agenkit/composition/conditional.py"): ConditionalAgent,
    ("ConsensusAgent", "agenkit/patterns/multiagent.py"): ConsensusAgent,
    (
        "ContextOptimizer",
        "agenkit/techniques/compositions/context_optimization.py",
    ): ContextOptimizer,
    ("ConversationalAgent", "agenkit/patterns/conversational.py"): ConversationalAgent,
    (
        "EnhancedRetryDecorator",
        "agenkit/infrastructure/retry_enhanced.py",
    ): EnhancedRetryDecorator,
    (
        "ExplorationStrategy",
        "agenkit/techniques/compositions/exploration.py",
    ): ExplorationStrategy,
    ("FallbackAgent", "agenkit/composition/fallback.py"): CompositionFallbackAgent,
    ("FallbackAgent", "agenkit/patterns/fallback.py"): FallbackAgent,
    (
        "GoalMonitor",
        "agenkit/techniques/compositions/goal_monitoring.py",
    ): GoalMonitor,
    (
        "GraphOfThought",
        "agenkit/techniques/reasoning/graph_of_thought.py",
    ): GraphOfThought,
    ("HumanInLoopAgent", "agenkit/patterns/human_in_loop.py"): HumanInLoopAgent,
    (
        "InputValidationMiddleware",
        "agenkit/safety/input_validation.py",
    ): InputValidationMiddleware,
    (
        "LearningFromFeedback",
        "agenkit/techniques/compositions/learning_feedback.py",
    ): LearningFromFeedback,
    (
        "LeastToMost",
        "agenkit/techniques/reasoning/least_to_most.py",
    ): LeastToMost,
    ("LoadBalancer", "agenkit/infrastructure/load_balancer.py"): LoadBalancer,
    ("LoadBalancerRouter", "agenkit/routing/load_balancer.py"): LoadBalancerRouter,
    ("MetricsDecorator", "agenkit/middleware/metrics.py"): MetricsDecorator,
    ("MultiAgentOrchestrator", "agenkit/patterns/multiagent.py"): MultiAgentOrchestrator,
    ("OrchestrationAgent", "agenkit/patterns/orchestration.py"): OrchestrationAgent,
    (
        "OutputValidationMiddleware",
        "agenkit/safety/output_validation.py",
    ): OutputValidationMiddleware,
    ("ParallelAgent", "agenkit/composition/parallel.py"): CompositionParallelAgent,
    ("ParallelAgent", "agenkit/patterns/parallel.py"): ParallelAgent,
    ("ParallelPattern", "agenkit/patterns/orchestration.py"): ParallelPattern,
    (
        "PerUserRateLimiterDecorator",
        "agenkit/middleware/per_user_rate_limiter.py",
    ): PerUserRateLimiterDecorator,
    ("PermissionMiddleware", "agenkit/safety/permissions.py"): PermissionMiddleware,
    (
        "PlanAndSolve",
        "agenkit/techniques/reasoning/plan_and_solve.py",
    ): PlanAndSolve,
    ("PlanningAgent", "agenkit/patterns/planning.py"): PlanningAgent,
    ("RateLimiterDecorator", "agenkit/middleware/rate_limiter.py"): RateLimiterDecorator,
    ("ReActAgent", "agenkit/patterns/react.py"): ReActAgent,
    (
        "ReasoningWithToolsAgent",
        "agenkit/patterns/reasoning_with_tools.py",
    ): ReasoningWithToolsAgent,
    ("RecoveryAgent", "agenkit/patterns/fallback.py"): RecoveryAgent,
    ("ReflectionAgent", "agenkit/patterns/reflection.py"): ReflectionAgent,
    ("RemoteAgent", "agenkit/adapters/python/remote_agent.py"): RemoteAgent,
    ("RetryDecorator", "agenkit/middleware/retry.py"): RetryDecorator,
    ("RouterAgent", "agenkit/patterns/router.py"): RouterAgent,
    ("RouterPattern", "agenkit/patterns/orchestration.py"): RouterPattern,
    (
        "SelfConsistency",
        "agenkit/techniques/reasoning/self_consistency.py",
    ): SelfConsistency,
    ("SequentialAgent", "agenkit/composition/sequential.py"): CompositionSequentialAgent,
    ("SequentialAgent", "agenkit/patterns/sequential.py"): SequentialAgent,
    ("SequentialPattern", "agenkit/patterns/orchestration.py"): SequentialPattern,
    ("SimpleRAG", "agenkit/techniques/compositions/rag.py"): SimpleRAG,
    ("SkillEnabledAgent", "agenkit/skills/agent.py"): SkillEnabledAgent,
    (
        "StreamingConversationalAgent",
        "agenkit/patterns/conversational.py",
    ): StreamingConversationalAgent,
    ("SupervisorAgent", "agenkit/patterns/supervisor.py"): SupervisorAgent,
    ("TimeoutDecorator", "agenkit/middleware/timeout.py"): TimeoutDecorator,
    ("ToolAgent", "agenkit/tools/tool_agent.py"): ToolAgent,
    (
        "TreeOfThought",
        "agenkit/techniques/reasoning/tree_of_thought.py",
    ): TreeOfThought,
}

# ---------------------------------------------------------------------------
# Layer B: instantiable factories, for behavioral conformance.
#
# Tier 1a only (truly zero-arg constructible) -- registered now. Tier 1b
# (~39 classes needing a trivial fake agent/LLM/config) and Tier 1c (~11
# classes needing real registries/auth providers/non-empty collections) are
# staged into Phase 5 in subsystem-sized tranches, per the plan. Registering
# all of Layer B in one PR would have made this PR's review surface both
# the conformance-suite design AND ~40 individual fixture designs at once.
# ---------------------------------------------------------------------------

AGENT_CASES = [
    pytest.param(lambda: MultiAgentOrchestrator(MultiAgentConfig()), id="multi_agent_orchestrator"),
    pytest.param(lambda: ConsensusAgent(ConsensusConfig()), id="consensus_agent"),
]

# Census keys covered by AGENT_CASES above. Kept as an explicit, parallel
# set rather than derived from the factories themselves -- a lambda's
# closure isn't introspectable back to the class it constructs, so
# test_registry_coverage.py needs this list to check completeness.
REGISTERED_CENSUS_KEYS: set[tuple[str, str]] = {
    ("MultiAgentOrchestrator", "agenkit/patterns/multiagent.py"),
    ("ConsensusAgent", "agenkit/patterns/multiagent.py"),
}

# {census_key: reason}. Every key here must exist in CENSUS_KEY_TO_CLASS;
# test_registry_coverage.py enforces census == (AGENT_CASES ids) | EXCLUDED.
EXCLUDED: dict[tuple[str, str], str] = {
    # Tier 1b: needs a trivial fake agent/LLM/config -- deferred to Phase 5,
    # tranche "core patterns".
    ("AutonomousAgent", "agenkit/patterns/autonomous.py"): "Tier 1b, Phase 5",
    ("CollaborativeAgent", "agenkit/patterns/collaborative.py"): (
        "Tier 1b, Phase 5 -- CollaborativeConfig requires merge_func"
    ),
    ("ConversationalAgent", "agenkit/patterns/conversational.py"): "Tier 1b, Phase 5",
    (
        "StreamingConversationalAgent",
        "agenkit/patterns/conversational.py",
    ): "Tier 1b, Phase 5",
    ("HumanInLoopAgent", "agenkit/patterns/human_in_loop.py"): (
        "Tier 1b, Phase 5 -- HumanInLoopConfig requires approval_func"
    ),
    ("OrchestrationAgent", "agenkit/patterns/orchestration.py"): "Tier 1b, Phase 5",
    ("ParallelPattern", "agenkit/patterns/orchestration.py"): "Tier 1b, Phase 5",
    ("RouterPattern", "agenkit/patterns/orchestration.py"): "Tier 1b, Phase 5",
    ("SequentialPattern", "agenkit/patterns/orchestration.py"): "Tier 1b, Phase 5",
    ("ParallelAgent", "agenkit/composition/parallel.py"): "Tier 1b, Phase 5",
    ("ParallelAgent", "agenkit/patterns/parallel.py"): "Tier 1b, Phase 5",
    ("PlanningAgent", "agenkit/patterns/planning.py"): "Tier 1b, Phase 5",
    ("ReActAgent", "agenkit/patterns/react.py"): (
        "Tier 1b, Phase 5 -- ReActConfig rejects an empty tools list"
    ),
    (
        "ReasoningWithToolsAgent",
        "agenkit/patterns/reasoning_with_tools.py",
    ): "Tier 1b, Phase 5",
    ("RecoveryAgent", "agenkit/patterns/fallback.py"): "Tier 1b, Phase 5",
    ("ReflectionAgent", "agenkit/patterns/reflection.py"): "Tier 1b, Phase 5",
    ("RouterAgent", "agenkit/patterns/router.py"): "Tier 1b, Phase 5",
    ("FallbackAgent", "agenkit/composition/fallback.py"): "Tier 1b, Phase 5",
    ("FallbackAgent", "agenkit/patterns/fallback.py"): "Tier 1b, Phase 5",
    ("SequentialAgent", "agenkit/composition/sequential.py"): "Tier 1b, Phase 5",
    ("SequentialAgent", "agenkit/patterns/sequential.py"): "Tier 1b, Phase 5",
    ("SupervisorAgent", "agenkit/patterns/supervisor.py"): "Tier 1b, Phase 5",
    ("ConditionalAgent", "agenkit/composition/conditional.py"): "Tier 1b, Phase 5",
    ("ChainOfThought", "agenkit/techniques/reasoning/chain_of_thought.py"): "Tier 1b, Phase 5",
    ("GraphOfThought", "agenkit/techniques/reasoning/graph_of_thought.py"): "Tier 1b, Phase 5",
    ("LeastToMost", "agenkit/techniques/reasoning/least_to_most.py"): "Tier 1b, Phase 5",
    ("PlanAndSolve", "agenkit/techniques/reasoning/plan_and_solve.py"): "Tier 1b, Phase 5",
    ("SelfConsistency", "agenkit/techniques/reasoning/self_consistency.py"): ("Tier 1b, Phase 5"),
    ("TreeOfThought", "agenkit/techniques/reasoning/tree_of_thought.py"): "Tier 1b, Phase 5",
    (
        "ActorCriticVariation",
        "agenkit/techniques/compositions/actor_critic_variation.py",
    ): "Tier 1b, Phase 5",
    (
        "ContextOptimizer",
        "agenkit/techniques/compositions/context_optimization.py",
    ): "Tier 1b, Phase 5",
    (
        "ExplorationStrategy",
        "agenkit/techniques/compositions/exploration.py",
    ): "Tier 1b, Phase 5 -- crashes on an empty actions list, see plan notes",
    (
        "GoalMonitor",
        "agenkit/techniques/compositions/goal_monitoring.py",
    ): "Tier 1b, Phase 5",
    (
        "LearningFromFeedback",
        "agenkit/techniques/compositions/learning_feedback.py",
    ): "Tier 1b, Phase 5",
    ("SimpleRAG", "agenkit/techniques/compositions/rag.py"): "Tier 1b, Phase 5",
    ("CitedRAG", "agenkit/techniques/compositions/rag_with_citations.py"): (
        "Tier 1b, Phase 5 -- needs a retriever returning real Document objects"
    ),
    ("SkillEnabledAgent", "agenkit/skills/agent.py"): "Tier 1b, Phase 5",
    ("ToolAgent", "agenkit/tools/tool_agent.py"): (
        "Tier 1b, Phase 5 -- also gated on #762 (Tool.execute signature split)"
    ),
    # Tier 1c: needs a real registry/auth provider/non-empty collection --
    # excluded, not deferred to a fixture; building fixtures for subsystems
    # this suite isn't testing would make it depend on their correctness.
    ("RemoteAgent", "agenkit/adapters/python/remote_agent.py"): (
        "Tier 1c -- needs a real remote endpoint/transport"
    ),
    # Out-of-scope-by-design: middleware/auth/routing decorators. These wrap
    # another Agent and are subject to the same Layer A property contract
    # (included in ALL_AGENT_CLASSES above), but Layer B's process()
    # assertions test the wrapped delegate's behavior, not the decorator's,
    # so a decorator-over-a-fake test would be testing the fake.
    ("APIKeyAuth", "agenkit/auth/middleware.py"): "Out-of-scope-by-design: auth decorator",
    ("BearerTokenAuth", "agenkit/auth/middleware.py"): ("Out-of-scope-by-design: auth decorator"),
    ("AgentsMdMiddleware", "agenkit/agents_md/integration.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
    ("AnomalyDetectionMiddleware", "agenkit/safety/anomaly_detection.py"): (
        "Out-of-scope-by-design: safety decorator"
    ),
    ("BatchingDecorator", "agenkit/middleware/batching.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
    ("CachingDecorator", "agenkit/middleware/caching.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
    ("CircuitBreakerDecorator", "agenkit/middleware/circuit_breaker.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
    ("EnhancedRetryDecorator", "agenkit/infrastructure/retry_enhanced.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
    ("InputValidationMiddleware", "agenkit/safety/input_validation.py"): (
        "Out-of-scope-by-design: safety decorator"
    ),
    ("LoadBalancer", "agenkit/infrastructure/load_balancer.py"): (
        "Out-of-scope-by-design: routing decorator"
    ),
    ("LoadBalancerRouter", "agenkit/routing/load_balancer.py"): (
        "Out-of-scope-by-design: routing decorator"
    ),
    ("MetricsDecorator", "agenkit/middleware/metrics.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
    ("OutputValidationMiddleware", "agenkit/safety/output_validation.py"): (
        "Out-of-scope-by-design: safety decorator"
    ),
    ("PermissionMiddleware", "agenkit/safety/permissions.py"): (
        "Out-of-scope-by-design: safety decorator"
    ),
    ("PerUserRateLimiterDecorator", "agenkit/middleware/per_user_rate_limiter.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
    ("RateLimiterDecorator", "agenkit/middleware/rate_limiter.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
    ("RetryDecorator", "agenkit/middleware/retry.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
    ("TimeoutDecorator", "agenkit/middleware/timeout.py"): (
        "Out-of-scope-by-design: middleware decorator"
    ),
}

# Ceiling on EXCLUDED's size -- can only be lowered, mirroring
# scripts/version.py's _EXPECTED_DECLARATIONS floor-on-registry-size idiom,
# inverted. #868's rationale applies in reverse here: a reassuringly small
# EXCLUDED count would be the tell that entries were silently dropped
# without their classes being registered in AGENT_CASES -- so the ceiling
# must equal len(EXCLUDED) exactly today, and Phase 5 PRs lower it as they
# move entries from EXCLUDED into AGENT_CASES.
_MAX_EXCLUDED = len(EXCLUDED)
