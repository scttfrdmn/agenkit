"""
Multi-LLM Cost Optimizer - Complete Implementation

Demonstrates intelligent LLM routing based on complexity and cost optimization.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# ============================================================================
# Classification
# ============================================================================


class ComplexityLevel(Enum):
    """Complexity level of a request."""

    SIMPLE = "simple"  # Basic queries, < 50 tokens
    MEDIUM = "medium"  # Standard queries, 50-200 tokens
    COMPLEX = "complex"  # Complex queries, > 200 tokens
    CRITICAL = "critical"  # Requires best model regardless of cost


@dataclass
class ClassificationResult:
    """Result of complexity classification."""

    level: ComplexityLevel
    confidence: float
    reasoning: str
    estimated_tokens: int
    metadata: dict[str, Any] = field(default_factory=dict)


class ComplexityClassifier:
    """Classifies request complexity for optimal LLM routing."""

    def classify(self, prompt: str, context: str | None = None) -> ClassificationResult:
        """Classify prompt complexity."""
        # Simple heuristics (in production, use ML model)
        token_estimate = len(prompt.split())

        # Check for complexity keywords
        complex_keywords = ["explain", "analyze", "compare", "detailed", "comprehensive"]
        simple_keywords = ["what is", "define", "list", "name"]
        critical_keywords = ["legal", "medical", "financial advice", "diagnosis"]

        prompt_lower = prompt.lower()

        # Critical check
        if any(kw in prompt_lower for kw in critical_keywords):
            return ClassificationResult(
                level=ComplexityLevel.CRITICAL,
                confidence=0.95,
                reasoning="Contains critical keywords requiring best model",
                estimated_tokens=token_estimate,
            )

        # Complex check
        if token_estimate > 200 or any(kw in prompt_lower for kw in complex_keywords):
            return ClassificationResult(
                level=ComplexityLevel.COMPLEX,
                confidence=0.8,
                reasoning=f"Long prompt ({token_estimate} tokens) or complex keywords",
                estimated_tokens=token_estimate,
            )

        # Simple check
        if token_estimate < 50 or any(kw in prompt_lower for kw in simple_keywords):
            return ClassificationResult(
                level=ComplexityLevel.SIMPLE,
                confidence=0.85,
                reasoning=f"Short prompt ({token_estimate} tokens) or simple keywords",
                estimated_tokens=token_estimate,
            )

        # Default to medium
        return ClassificationResult(
            level=ComplexityLevel.MEDIUM,
            confidence=0.7,
            reasoning=f"Standard prompt ({token_estimate} tokens)",
            estimated_tokens=token_estimate,
        )


# ============================================================================
# LLM Models Configuration
# ============================================================================


@dataclass
class LLMModel:
    """Configuration for an LLM model."""

    name: str
    cost_per_1k_tokens: float
    max_tokens: int
    quality_score: float  # 0-10
    latency_ms: int
    provider: str


# Available models (mock configurations)
MODELS = {
    "gpt-4": LLMModel(
        name="gpt-4",
        cost_per_1k_tokens=0.03,
        max_tokens=8192,
        quality_score=9.5,
        latency_ms=2000,
        provider="openai",
    ),
    "gpt-3.5-turbo": LLMModel(
        name="gpt-3.5-turbo",
        cost_per_1k_tokens=0.002,
        max_tokens=4096,
        quality_score=7.5,
        latency_ms=500,
        provider="openai",
    ),
    "claude-2": LLMModel(
        name="claude-2",
        cost_per_1k_tokens=0.01,
        max_tokens=100000,
        quality_score=9.0,
        latency_ms=1500,
        provider="anthropic",
    ),
    "llama-2-70b": LLMModel(
        name="llama-2-70b",
        cost_per_1k_tokens=0.001,
        max_tokens=4096,
        quality_score=6.5,
        latency_ms=800,
        provider="meta",
    ),
}


# ============================================================================
# Cost Tracking
# ============================================================================


@dataclass
class RequestMetrics:
    """Metrics for a single request."""

    prompt: str
    model_used: str
    complexity: ComplexityLevel
    tokens_used: int
    cost: float
    latency_ms: float
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)


class CostTracker:
    """Tracks costs and usage across requests."""

    def __init__(self):
        self.requests: list[RequestMetrics] = []
        self.total_cost = 0.0
        self.total_tokens = 0

    def record(self, metrics: RequestMetrics):
        """Record request metrics."""
        self.requests.append(metrics)
        self.total_cost += metrics.cost
        self.total_tokens += metrics.tokens_used

    def get_stats(self) -> dict[str, Any]:
        """Get usage statistics."""
        if not self.requests:
            return {"total_requests": 0, "total_cost": 0.0, "total_tokens": 0}

        by_model = {}
        for req in self.requests:
            if req.model_used not in by_model:
                by_model[req.model_used] = {"count": 0, "cost": 0.0, "tokens": 0}
            by_model[req.model_used]["count"] += 1
            by_model[req.model_used]["cost"] += req.cost
            by_model[req.model_used]["tokens"] += req.tokens_used

        return {
            "total_requests": len(self.requests),
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "avg_cost_per_request": self.total_cost / len(self.requests),
            "by_model": by_model,
            "success_rate": sum(1 for r in self.requests if r.success) / len(self.requests),
        }


# ============================================================================
# LLM Router
# ============================================================================


@dataclass
class RoutingDecision:
    """Decision about which LLM to use."""

    primary_model: str
    fallback_models: list[str]
    reasoning: str
    estimated_cost: float


class LLMRouter:
    """Routes requests to optimal LLM based on complexity and cost."""

    def __init__(
        self,
        classifier: ComplexityClassifier,
        cost_tracker: CostTracker,
        budget_limit: float | None = None,
    ):
        self.classifier = classifier
        self.cost_tracker = cost_tracker
        self.budget_limit = budget_limit

    def route(self, prompt: str, context: str | None = None) -> RoutingDecision:
        """Determine which LLM to use for this request."""
        # Classify complexity
        classification = self.classifier.classify(prompt, context)

        # Check budget
        if self.budget_limit and self.cost_tracker.total_cost >= self.budget_limit:
            return RoutingDecision(
                primary_model="llama-2-70b",
                fallback_models=["gpt-3.5-turbo"],
                reasoning="Budget limit reached, using cheapest model",
                estimated_cost=MODELS["llama-2-70b"].cost_per_1k_tokens
                * classification.estimated_tokens
                / 1000,
            )

        # Route based on complexity
        if classification.level == ComplexityLevel.CRITICAL:
            return RoutingDecision(
                primary_model="gpt-4",
                fallback_models=["claude-2"],
                reasoning="Critical request requires best model",
                estimated_cost=MODELS["gpt-4"].cost_per_1k_tokens
                * classification.estimated_tokens
                / 1000,
            )

        elif classification.level == ComplexityLevel.COMPLEX:
            return RoutingDecision(
                primary_model="claude-2",
                fallback_models=["gpt-4", "gpt-3.5-turbo"],
                reasoning="Complex request, using high-quality model",
                estimated_cost=MODELS["claude-2"].cost_per_1k_tokens
                * classification.estimated_tokens
                / 1000,
            )

        elif classification.level == ComplexityLevel.SIMPLE:
            return RoutingDecision(
                primary_model="llama-2-70b",
                fallback_models=["gpt-3.5-turbo"],
                reasoning="Simple request, using cost-effective model",
                estimated_cost=MODELS["llama-2-70b"].cost_per_1k_tokens
                * classification.estimated_tokens
                / 1000,
            )

        else:  # MEDIUM
            return RoutingDecision(
                primary_model="gpt-3.5-turbo",
                fallback_models=["llama-2-70b", "claude-2"],
                reasoning="Standard request, balancing cost and quality",
                estimated_cost=MODELS["gpt-3.5-turbo"].cost_per_1k_tokens
                * classification.estimated_tokens
                / 1000,
            )

    async def execute(self, prompt: str, context: str | None = None, verbose: bool = True) -> str:
        """Execute request with optimal routing and fallback."""
        # Classify and route
        classification = self.classifier.classify(prompt, context)
        decision = self.route(prompt, context)

        if verbose:
            print(f"\n{'=' * 70}")
            print(f"REQUEST: {prompt[:50]}...")
            print(f"{'=' * 70}")
            print(
                f"Complexity: {classification.level.value} (confidence: {classification.confidence:.2f})"
            )
            print(f"Reasoning: {classification.reasoning}")
            print(f"Primary Model: {decision.primary_model}")
            print(f"Estimated Cost: ${decision.estimated_cost:.6f}")

        # Try primary model
        start = datetime.now()
        try:
            response = await self._call_llm(decision.primary_model, prompt)
            latency = (datetime.now() - start).total_seconds() * 1000

            # Record metrics
            model_config = MODELS[decision.primary_model]
            actual_cost = model_config.cost_per_1k_tokens * classification.estimated_tokens / 1000

            self.cost_tracker.record(
                RequestMetrics(
                    prompt=prompt,
                    model_used=decision.primary_model,
                    complexity=classification.level,
                    tokens_used=classification.estimated_tokens,
                    cost=actual_cost,
                    latency_ms=latency,
                    success=True,
                )
            )

            if verbose:
                print(
                    f"✓ Success with {decision.primary_model} ({latency:.0f}ms, ${actual_cost:.6f})"
                )

            return response

        except Exception as e:
            if verbose:
                print(f"✗ Failed with {decision.primary_model}: {e}")

            # Try fallback models
            for fallback_model in decision.fallback_models:
                if verbose:
                    print(f"  Trying fallback: {fallback_model}")

                try:
                    response = await self._call_llm(fallback_model, prompt)
                    model_config = MODELS[fallback_model]
                    actual_cost = (
                        model_config.cost_per_1k_tokens * classification.estimated_tokens / 1000
                    )

                    self.cost_tracker.record(
                        RequestMetrics(
                            prompt=prompt,
                            model_used=fallback_model,
                            complexity=classification.level,
                            tokens_used=classification.estimated_tokens,
                            cost=actual_cost,
                            latency_ms=(datetime.now() - start).total_seconds() * 1000,
                            success=True,
                        )
                    )

                    if verbose:
                        print(f"✓ Success with fallback {fallback_model}")

                    return response

                except Exception as e2:
                    if verbose:
                        print(f"✗ Fallback {fallback_model} also failed: {e2}")
                    continue

            # All models failed
            self.cost_tracker.record(
                RequestMetrics(
                    prompt=prompt,
                    model_used=decision.primary_model,
                    complexity=classification.level,
                    tokens_used=0,
                    cost=0.0,
                    latency_ms=(datetime.now() - start).total_seconds() * 1000,
                    success=False,
                )
            )

            raise RuntimeError(f"All models failed for request: {prompt[:50]}")

    async def _call_llm(self, model_name: str, prompt: str) -> str:
        """Mock LLM call (in production, use real API)."""
        import asyncio

        model = MODELS[model_name]

        # Simulate API call with latency
        await asyncio.sleep(model.latency_ms / 1000.0)

        # Mock response based on model quality
        if model.quality_score > 9:
            return f"[{model_name}] Comprehensive answer: {prompt[:30]}... (high quality response)"
        elif model.quality_score > 7:
            return f"[{model_name}] Good answer: {prompt[:30]}... (standard response)"
        else:
            return f"[{model_name}] Basic answer: {prompt[:30]}... (simple response)"
