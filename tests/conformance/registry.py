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
from agenkit.interfaces import Tool, ToolResult
from agenkit.middleware.batching import BatchingDecorator
from agenkit.middleware.caching import CachingDecorator
from agenkit.middleware.circuit_breaker import CircuitBreakerDecorator
from agenkit.middleware.metrics import MetricsDecorator
from agenkit.middleware.per_user_rate_limiter import PerUserRateLimiterDecorator
from agenkit.middleware.rate_limiter import RateLimiterDecorator
from agenkit.middleware.retry import RetryDecorator
from agenkit.middleware.timeout import TimeoutDecorator
from agenkit.patterns.autonomous import AutonomousAgent, AutonomousConfig
from agenkit.patterns.collaborative import (
    CollaborativeAgent,
    CollaborativeConfig,
    default_merge_funcs,
)
from agenkit.patterns.conversational import (
    ConversationalAgent,
    ConversationalAgentConfig,
    StreamingConversationalAgent,
)
from agenkit.patterns.fallback import FallbackAgent, RecoveryAgent, default_recovery
from agenkit.patterns.human_in_loop import HumanInLoopAgent, HumanInLoopConfig, simple_approval_func
from agenkit.patterns.multiagent import (
    ConsensusAgent,
    ConsensusConfig,
    MultiAgentConfig,
    MultiAgentOrchestrator,
)
from agenkit.patterns.orchestration import (
    OrchestrationAgent,
    OrchestrationConfig,
    ParallelPattern,
    RouterPattern,
    SequentialPattern,
)
from agenkit.patterns.parallel import ParallelAgent, default_aggregators
from agenkit.patterns.planning import PlanningAgent, PlanningConfig
from agenkit.patterns.react import ReActAgent, ReActConfig
from agenkit.patterns.reasoning_with_tools import ReasoningWithToolsAgent
from agenkit.patterns.reflection import ReflectionAgent, ReflectionConfig
from agenkit.patterns.router import RouterAgent, RouterConfig, SimpleClassifier
from agenkit.patterns.sequential import SequentialAgent
from agenkit.patterns.supervisor import SimplePlanner, SupervisorAgent, SupervisorConfig
from agenkit.routing.load_balancer import LoadBalancerRouter
from agenkit.safety.anomaly_detection import AnomalyDetectionMiddleware
from agenkit.safety.input_validation import InputValidationMiddleware
from agenkit.safety.output_validation import OutputValidationMiddleware
from agenkit.safety.permissions import PermissionMiddleware
from agenkit.skills.agent import SkillEnabledAgent
from agenkit.skills.loader import SkillRegistry
from agenkit.techniques.compositions.actor_critic_variation import ActorCriticVariation
from agenkit.techniques.compositions.context_optimization import ContextOptimizer
from agenkit.techniques.compositions.exploration import ExplorationStrategy
from agenkit.techniques.compositions.goal_monitoring import GoalMonitor
from agenkit.techniques.compositions.learning_feedback import LearningFromFeedback
from agenkit.techniques.compositions.rag import SimpleRAG
from agenkit.techniques.compositions.rag_with_citations import CitedRAG, Document
from agenkit.techniques.reasoning.chain_of_thought import ChainOfThought
from agenkit.techniques.reasoning.graph_of_thought import GraphOfThought
from agenkit.techniques.reasoning.least_to_most import LeastToMost
from agenkit.techniques.reasoning.plan_and_solve import PlanAndSolve
from agenkit.techniques.reasoning.self_consistency import SelfConsistency
from agenkit.techniques.reasoning.tree_of_thought import TreeOfThought
from agenkit.tools.tool_agent import ToolAgent
from agenkit.tools.tool_registry import ToolRegistry

# Reuses the reasoning-technique suite's real-``LLM``-contract double (see
# tests/techniques/reasoning/conftest.py's module docstring for why this
# subclasses agenkit.adapters.llm.base.LLM rather than duck-typing it, #802).
from tests.techniques.reasoning.conftest import ContractLLM

from .conftest import ContractAgent

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
# Tier 1a (truly zero-arg constructible) and Tier 1b (needs a trivial fake
# agent/LLM/config) are registered below. Tier 1c (needs a real remote
# endpoint/transport) and the out-of-scope-by-design decorators remain in
# EXCLUDED -- see the comments there. Tier 1b was drained in subsystem-sized
# tranches per #923; this file's history is the tranche log.
# ---------------------------------------------------------------------------


class _EchoTool(Tool):
    """Trivial ``Tool`` double: echoes its ``input`` parameter back.

    Used by the ``ReActAgent``/``ToolAgent`` fixtures below, which need at
    least one real tool but not one that does anything interesting -- the
    conformance suite is testing the agent's own contract, not the tool's.
    """

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes its input parameter back."

    async def execute(self, params: dict) -> ToolResult:
        return ToolResult(success=True, data=params.get("input", ""))


def _make_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_EchoTool())
    return registry


def _make_react_agent() -> ReActAgent:
    # The wrapped reasoning agent must emit the ReAct "Final Answer" shape
    # ReActAgent's parser expects, or it would loop to max_steps every time.
    base = ContractAgent(
        name="react_base",
        response="Thought: done\nAction: Final Answer\nAction Input: 42",
    )
    return ReActAgent(ReActConfig(agent=base, tools=[_EchoTool()]))


def _make_cited_rag() -> CitedRAG:
    def retriever(_query: str) -> list[Document]:
        # CitedRAG.process() reads .content/.source off each item and calls
        # ._build_citations() (doc.source) -- a plain string retriever
        # (SimpleRAG's shape) would raise AttributeError here, hence real
        # Document objects rather than reusing SimpleRAG's fixture.
        return [
            Document(content="Aspirin reduces fever.", source="Smith et al. 2020"),
            Document(content="Exercise reduces stress.", source="Jones et al. 2021"),
        ]

    return CitedRAG(retriever=retriever, answerer=ContractAgent(name="cited_rag_answerer"))


AGENT_CASES = [
    pytest.param(lambda: MultiAgentOrchestrator(MultiAgentConfig()), id="multi_agent_orchestrator"),
    pytest.param(lambda: ConsensusAgent(ConsensusConfig()), id="consensus_agent"),
    # --- Tier 1b: trivial fake agent/LLM, no special config -----------------
    pytest.param(
        lambda: AutonomousAgent(AutonomousConfig(objective="conformance probe")),
        id="autonomous_agent",
    ),
    pytest.param(
        lambda: ConversationalAgent(ConversationalAgentConfig(llm_client=ContractLLM())),
        id="conversational_agent",
    ),
    pytest.param(
        lambda: StreamingConversationalAgent(ConversationalAgentConfig(llm_client=ContractLLM())),
        id="streaming_conversational_agent",
    ),
    pytest.param(
        lambda: OrchestrationAgent(
            OrchestrationConfig(workflow=[{"agent": "a1"}], agents={"a1": ContractAgent(name="a1")})
        ),
        id="orchestration_agent",
    ),
    pytest.param(
        lambda: ParallelPattern([ContractAgent(name="a1"), ContractAgent(name="a2")]),
        id="parallel_pattern",
    ),
    pytest.param(
        lambda: RouterPattern(router=lambda m: "a1", handlers={"a1": ContractAgent(name="a1")}),
        id="router_pattern",
    ),
    pytest.param(
        lambda: SequentialPattern([ContractAgent(name="a1"), ContractAgent(name="a2")]),
        id="sequential_pattern",
    ),
    pytest.param(
        lambda: ParallelAgent(
            agents=[ContractAgent(name="a1"), ContractAgent(name="a2")],
            aggregator=default_aggregators.first,
        ),
        id="parallel_agent_patterns",
    ),
    pytest.param(
        lambda: CompositionParallelAgent(
            name="parallel_agent", agents=[ContractAgent(name="a1"), ContractAgent(name="a2")]
        ),
        id="parallel_agent_composition",
    ),
    pytest.param(
        lambda: PlanningAgent(
            PlanningConfig(
                planner=ContractAgent(name="planner", response="Goal: g\nSteps:\n1. step")
            )
        ),
        id="planning_agent",
    ),
    pytest.param(
        lambda: ReasoningWithToolsAgent(llm=ContractAgent(name="llm"), tools=[]),
        id="reasoning_with_tools_agent",
    ),
    pytest.param(
        lambda: RecoveryAgent(
            agent=ContractAgent(name="a1"),
            recovery_func=default_recovery.static_message("recovered"),
        ),
        id="recovery_agent",
    ),
    pytest.param(
        lambda: ReflectionAgent(
            ReflectionConfig(
                generator=ContractAgent(name="generator", response="draft"),
                critic=ContractAgent(name="critic", response='{"score": 0.95, "feedback": "good"}'),
                max_iterations=1,
            )
        ),
        id="reflection_agent",
    ),
    pytest.param(
        lambda: RouterAgent(
            RouterConfig(
                classifier=SimpleClassifier(
                    agent=ContractAgent(name="a1"), keywords={"a1": ["probe"]}
                ),
                agents={"a1": ContractAgent(name="a1")},
            )
        ),
        id="router_agent",
    ),
    pytest.param(
        lambda: FallbackAgent(agents=[ContractAgent(name="a1"), ContractAgent(name="a2")]),
        id="fallback_agent_patterns",
    ),
    pytest.param(
        lambda: CompositionFallbackAgent(
            name="fallback_agent", agents=[ContractAgent(name="a1"), ContractAgent(name="a2")]
        ),
        id="fallback_agent_composition",
    ),
    pytest.param(
        lambda: SequentialAgent(agents=[ContractAgent(name="a1"), ContractAgent(name="a2")]),
        id="sequential_agent_patterns",
    ),
    pytest.param(
        lambda: CompositionSequentialAgent(
            name="sequential_agent", agents=[ContractAgent(name="a1"), ContractAgent(name="a2")]
        ),
        id="sequential_agent_composition",
    ),
    pytest.param(
        lambda: SupervisorAgent(
            SupervisorConfig(
                planner=SimplePlanner(ContractAgent(name="planner")),
                specialists={"a1": ContractAgent(name="a1")},
            )
        ),
        id="supervisor_agent",
    ),
    pytest.param(
        lambda: ConditionalAgent(name="conditional_agent", default_agent=ContractAgent(name="a1")),
        id="conditional_agent",
    ),
    # --- Tier 1b: hand-tuned *Config literal --------------------------------
    pytest.param(
        lambda: CollaborativeAgent(
            CollaborativeConfig(
                agents=[ContractAgent(name="a1"), ContractAgent(name="a2")],
                merge_func=default_merge_funcs.first,
                max_rounds=1,
            )
        ),
        id="collaborative_agent",
    ),
    pytest.param(
        lambda: HumanInLoopAgent(
            HumanInLoopConfig(
                agent=ContractAgent(name="a1"),
                approval_func=simple_approval_func(auto_approve=True),
            )
        ),
        id="human_in_loop_agent",
    ),
    pytest.param(_make_react_agent, id="react_agent"),
    # --- Tier 1b: reasoning techniques ---------------------------------------
    pytest.param(lambda: ChainOfThought(llm=ContractLLM()), id="chain_of_thought"),
    pytest.param(lambda: GraphOfThought(llm=ContractLLM(), max_nodes=3), id="graph_of_thought"),
    pytest.param(lambda: LeastToMost(llm=ContractLLM()), id="least_to_most"),
    pytest.param(lambda: PlanAndSolve(llm=ContractLLM()), id="plan_and_solve"),
    pytest.param(
        lambda: SelfConsistency(
            agent=ContractAgent(response="Therefore, the answer is 42"), num_samples=2
        ),
        id="self_consistency",
    ),
    pytest.param(
        lambda: TreeOfThought(llm=ContractLLM(), branching_factor=2, max_depth=1),
        id="tree_of_thought",
    ),
    # --- Tier 1b: compositions -----------------------------------------------
    pytest.param(
        lambda: ActorCriticVariation(
            actor=ContractAgent(name="actor", response="an answer"),
            critic=ContractAgent(name="critic", response="score: 9/10"),
            max_iterations=1,
        ),
        id="actor_critic_variation",
    ),
    pytest.param(
        lambda: ContextOptimizer(
            agent=ContractAgent(name="a1"),
            summarizer=ContractAgent(name="summarizer", response="summary"),
        ),
        id="context_optimizer",
    ),
    pytest.param(
        # actions is deliberately non-empty: ExplorationStrategy.select_action()
        # calls max() over self.actions and crashes on an empty list -- see the
        # note on the (now-removed) EXCLUDED entry, and the PR description for
        # a possible follow-up issue on that crash.
        lambda: ExplorationStrategy(
            agent=ContractAgent(name="a1"), actions=["search", "calculate"]
        ),
        id="exploration_strategy",
    ),
    pytest.param(
        lambda: GoalMonitor(agent=ContractAgent(name="a1"), goal_fn=lambda state: True),
        id="goal_monitor",
    ),
    pytest.param(
        lambda: LearningFromFeedback(agent=ContractAgent(name="a1")),
        id="learning_from_feedback",
    ),
    pytest.param(
        lambda: SimpleRAG(
            retriever=lambda query: ["doc1", "doc2"], answerer=ContractAgent(name="answerer")
        ),
        id="simple_rag",
    ),
    pytest.param(_make_cited_rag, id="cited_rag"),
    # --- Tier 1b: skills and tools -------------------------------------------
    pytest.param(
        lambda: SkillEnabledAgent(ContractAgent(name="a1"), SkillRegistry(search_paths=[])),
        id="skill_enabled_agent",
    ),
    pytest.param(
        lambda: ToolAgent(ContractAgent(name="a1"), _make_tool_registry()),
        id="tool_agent",
    ),
]

# Census keys covered by AGENT_CASES above. Kept as an explicit, parallel
# set rather than derived from the factories themselves -- a lambda's
# closure isn't introspectable back to the class it constructs, so
# test_registry_coverage.py needs this list to check completeness.
REGISTERED_CENSUS_KEYS: set[tuple[str, str]] = {
    ("MultiAgentOrchestrator", "agenkit/patterns/multiagent.py"),
    ("ConsensusAgent", "agenkit/patterns/multiagent.py"),
    ("AutonomousAgent", "agenkit/patterns/autonomous.py"),
    ("ConversationalAgent", "agenkit/patterns/conversational.py"),
    ("StreamingConversationalAgent", "agenkit/patterns/conversational.py"),
    ("OrchestrationAgent", "agenkit/patterns/orchestration.py"),
    ("ParallelPattern", "agenkit/patterns/orchestration.py"),
    ("RouterPattern", "agenkit/patterns/orchestration.py"),
    ("SequentialPattern", "agenkit/patterns/orchestration.py"),
    ("ParallelAgent", "agenkit/patterns/parallel.py"),
    ("ParallelAgent", "agenkit/composition/parallel.py"),
    ("PlanningAgent", "agenkit/patterns/planning.py"),
    ("ReasoningWithToolsAgent", "agenkit/patterns/reasoning_with_tools.py"),
    ("RecoveryAgent", "agenkit/patterns/fallback.py"),
    ("ReflectionAgent", "agenkit/patterns/reflection.py"),
    ("RouterAgent", "agenkit/patterns/router.py"),
    ("FallbackAgent", "agenkit/patterns/fallback.py"),
    ("FallbackAgent", "agenkit/composition/fallback.py"),
    ("SequentialAgent", "agenkit/patterns/sequential.py"),
    ("SequentialAgent", "agenkit/composition/sequential.py"),
    ("SupervisorAgent", "agenkit/patterns/supervisor.py"),
    ("ConditionalAgent", "agenkit/composition/conditional.py"),
    ("CollaborativeAgent", "agenkit/patterns/collaborative.py"),
    ("HumanInLoopAgent", "agenkit/patterns/human_in_loop.py"),
    ("ReActAgent", "agenkit/patterns/react.py"),
    ("ChainOfThought", "agenkit/techniques/reasoning/chain_of_thought.py"),
    ("GraphOfThought", "agenkit/techniques/reasoning/graph_of_thought.py"),
    ("LeastToMost", "agenkit/techniques/reasoning/least_to_most.py"),
    ("PlanAndSolve", "agenkit/techniques/reasoning/plan_and_solve.py"),
    ("SelfConsistency", "agenkit/techniques/reasoning/self_consistency.py"),
    ("TreeOfThought", "agenkit/techniques/reasoning/tree_of_thought.py"),
    ("ActorCriticVariation", "agenkit/techniques/compositions/actor_critic_variation.py"),
    ("ContextOptimizer", "agenkit/techniques/compositions/context_optimization.py"),
    ("ExplorationStrategy", "agenkit/techniques/compositions/exploration.py"),
    ("GoalMonitor", "agenkit/techniques/compositions/goal_monitoring.py"),
    ("LearningFromFeedback", "agenkit/techniques/compositions/learning_feedback.py"),
    ("SimpleRAG", "agenkit/techniques/compositions/rag.py"),
    ("CitedRAG", "agenkit/techniques/compositions/rag_with_citations.py"),
    ("SkillEnabledAgent", "agenkit/skills/agent.py"),
    ("ToolAgent", "agenkit/tools/tool_agent.py"),
}

# {census_key: reason}. Every key here must exist in CENSUS_KEY_TO_CLASS;
# test_registry_coverage.py enforces census == (AGENT_CASES ids) | EXCLUDED.
EXCLUDED: dict[tuple[str, str], str] = {
    # Tier 1b is fully drained as of #923's Tier 1b tranche -- all classes
    # that needed only a trivial fake agent/LLM/config, or a hand-tuned
    # *Config literal, are registered in AGENT_CASES above. Tier 1c (below)
    # and the out-of-scope-by-design decorators remain.
    #
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
