"""
Reflection Pattern - Self-Critique and Iterative Refinement

The Reflection pattern enables agents to review and improve their own outputs
through an iterative cycle of generation, critique, and refinement.

Key Concepts:
- Generator: Agent that produces initial output
- Critic: Agent that evaluates output quality and provides feedback
- Iteration: Repeated refinement based on critique
- Quality Threshold: Stop when output quality is sufficient
- Improvement Threshold: Stop when incremental improvements become minimal

Use Cases:
- Code generation with self-review
- Content creation with quality improvement
- Multi-draft writing and editing
- Error detection and correction
- Iterative problem solving

Example:
    >>> from agenkit.patterns import ReflectionAgent
    >>>
    >>> agent = ReflectionAgent(
    ...     generator=MyGeneratorAgent(),
    ...     critic=MyCriticAgent(),
    ...     max_reflections=3,
    ...     quality_threshold=0.9
    ... )
    >>>
    >>> result = await agent.process(
    ...     Message(role="user", content="Write a function to check if a number is prime")
    ... )
    >>>
    >>> # Inspect reflection history
    >>> print(result.metadata["reflection_iterations"])  # 3
    >>> print(result.metadata["final_quality_score"])     # 0.95
    >>> print(result.metadata["stop_reason"])             # "quality_threshold_met"

References:
- Reflexion: Language Agents with Verbal Reinforcement Learning (https://arxiv.org/abs/2303.11366)
- Self-Refine: Iterative Refinement with Self-Feedback (https://arxiv.org/abs/2303.17651)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from agenkit.interfaces import Agent, Message

__all__ = [
    "ReflectionAgent",
    "ReflectionConfig",
    "ReflectionStep",
    "StopReason",
    "CritiqueFormat",
]


class StopReason(Enum):
    """Reason why reflection loop stopped."""

    QUALITY_THRESHOLD_MET = "quality_threshold_met"
    MINIMAL_IMPROVEMENT = "minimal_improvement"
    MAX_REFLECTIONS = "max_reflections"
    PERFECT_SCORE = "perfect_score"


class CritiqueFormat(Enum):
    """Format expected from critic agent."""

    STRUCTURED = "structured"  # JSON: {"score": 0.8, "feedback": "..."}
    FREE_FORM = "free_form"  # Free text with score extracted


@dataclass
class ReflectionConfig:
    """
    Configuration for ReflectionAgent.

    This config-based approach provides:
    - Cross-language API consistency (matches Go/C++/Rust/TypeScript/Zig)
    - Better documentation (all parameters in one place)
    - Type safety and IDE autocomplete
    - Extensibility without breaking changes

    Attributes:
        generator: Agent that produces/refines output
        critic: Agent that evaluates output (returns score + feedback)
        max_iterations: Maximum refinement iterations (default: 3)
        quality_threshold: Stop when score exceeds this (default: 0.9)
        improvement_threshold: Min improvement to continue (default: 0.05)
        critique_format: Expected format from critic (default: structured)
        verbose: Include full reflection history in output (default: False)

    Example:
        >>> from agenkit.patterns import ReflectionAgent, ReflectionConfig
        >>>
        >>> config = ReflectionConfig(
        ...     generator=my_generator,
        ...     critic=my_critic,
        ...     max_iterations=5,
        ...     quality_threshold=0.95
        ... )
        >>> agent = ReflectionAgent(config)
    """

    generator: Agent
    critic: Agent
    max_iterations: int = 3
    quality_threshold: float = 0.9
    improvement_threshold: float = 0.05
    critique_format: CritiqueFormat = CritiqueFormat.STRUCTURED
    verbose: bool = False

    def __post_init__(self):
        """Validate configuration."""
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        if not 0.0 <= self.quality_threshold <= 1.0:
            raise ValueError("quality_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.improvement_threshold <= 1.0:
            raise ValueError("improvement_threshold must be between 0.0 and 1.0")


@dataclass
class ReflectionStep:
    """
    Single iteration in the reflection loop.

    Attributes:
        iteration: Iteration number (1-indexed)
        output: Generated output for this iteration
        critique: Feedback from critic
        quality_score: Quality score (0.0-1.0)
        improvement: Improvement over previous iteration
        timestamp: When this iteration occurred
    """

    iteration: int
    output: str
    critique: str
    quality_score: float
    improvement: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "iteration": self.iteration,
            "output": self.output,
            "critique": self.critique,
            "quality_score": self.quality_score,
            "improvement": self.improvement,
            "timestamp": self.timestamp.isoformat(),
        }


class ReflectionAgent(Agent):
    """
    Agent that iteratively refines output through self-critique.

    The reflection loop:
    1. Generator creates initial output
    2. Critic evaluates output, provides score and feedback
    3. Generator refines output based on feedback
    4. Repeat until quality threshold, minimal improvement, or max iterations

    Performance Characteristics:
    - Latency: N × (generator + critic), where N = number of iterations
    - Quality: Generally improves with iterations
    - Cost: N × (generator cost + critic cost)
    - Best for: Tasks where quality improvement justifies additional cost

    Args:
        generator: Agent that produces/refines output
        critic: Agent that evaluates output (returns score + feedback)
        max_reflections: Maximum refinement iterations (default: 3)
        quality_threshold: Stop when score exceeds this (default: 0.9)
        improvement_threshold: Min improvement to continue (default: 0.05)
        critique_format: Expected format from critic (default: structured)
        verbose: Include full reflection history in output (default: False)

    Example:
        >>> generator = OpenAIAgent(model="gpt-4")
        >>> critic = OpenAIAgent(model="gpt-4", system_prompt="You are a code reviewer...")
        >>>
        >>> agent = ReflectionAgent(
        ...     generator=generator,
        ...     critic=critic,
        ...     max_reflections=3,
        ...     quality_threshold=0.9
        ... )
        >>>
        >>> result = await agent.process(
        ...     Message(role="user", content="Write a function to merge two sorted lists")
        ... )
        >>>
        >>> print(f"Final score: {result.metadata['final_quality_score']}")
        >>> print(f"Iterations: {result.metadata['reflection_iterations']}")
        >>> print(f"Stop reason: {result.metadata['stop_reason']}")
    """

    def __init__(
        self,
        config: ReflectionConfig | None = None,
        *,
        # Deprecated parameters (kept for backward compatibility)
        generator: Agent | None = None,
        critic: Agent | None = None,
        max_reflections: int = 3,
        quality_threshold: float = 0.9,
        improvement_threshold: float = 0.05,
        critique_format: CritiqueFormat = CritiqueFormat.STRUCTURED,
        verbose: bool = False,
    ):
        """
        Initialize ReflectionAgent.

        Args:
            config: Configuration object (recommended, matches other languages)
            generator: (Deprecated) Agent that produces/refines output
            critic: (Deprecated) Agent that evaluates output
            max_reflections: (Deprecated) Use config.max_iterations instead
            quality_threshold: (Deprecated) Use config.quality_threshold instead
            improvement_threshold: (Deprecated) Use config.improvement_threshold instead
            critique_format: (Deprecated) Use config.critique_format instead
            verbose: (Deprecated) Use config.verbose instead

        Examples:
            >>> # Recommended: config-based (matches all other languages)
            >>> config = ReflectionConfig(generator=gen, critic=critic)
            >>> agent = ReflectionAgent(config)
            >>>
            >>> # Deprecated: direct parameters (will be removed in v2.0)
            >>> agent = ReflectionAgent(generator=gen, critic=critic)

        Raises:
            ValueError: If neither config nor generator/critic are provided
            ValueError: If validation fails
        """
        import warnings

        if config is not None:
            # New config-based API (recommended)
            self.generator = config.generator
            self.critic = config.critic
            self.max_reflections = config.max_iterations
            self.quality_threshold = config.quality_threshold
            self.improvement_threshold = config.improvement_threshold
            self.critique_format = config.critique_format
            self.verbose = config.verbose
        elif generator is not None and critic is not None:
            # Old direct-parameter API (deprecated)
            warnings.warn(
                "Direct parameters for ReflectionAgent are deprecated and will be removed in v2.0. "
                "Use ReflectionConfig instead: "
                "ReflectionAgent(ReflectionConfig(generator=..., critic=...)). "
                "See migration guide for details.",
                DeprecationWarning,
                stacklevel=2,
            )

            # Validate old-style parameters
            if max_reflections < 1:
                raise ValueError("max_reflections must be at least 1")
            if not 0.0 <= quality_threshold <= 1.0:
                raise ValueError("quality_threshold must be between 0.0 and 1.0")
            if not 0.0 <= improvement_threshold <= 1.0:
                raise ValueError("improvement_threshold must be between 0.0 and 1.0")

            self.generator = generator
            self.critic = critic
            self.max_reflections = max_reflections
            self.quality_threshold = quality_threshold
            self.improvement_threshold = improvement_threshold
            self.critique_format = critique_format
            self.verbose = verbose
        else:
            raise ValueError(
                "Either 'config' or both 'generator' and 'critic' must be provided. "
                "Recommended: Use ReflectionConfig for cross-language API consistency."
            )

        self.history: list[ReflectionStep] = []

    @property
    def name(self) -> str:
        """Agent name."""
        return "ReflectionAgent"

    @property
    def capabilities(self) -> list[str]:
        """Combined capabilities of generator and critic."""
        caps = set(self.generator.capabilities)
        caps.update(self.critic.capabilities)
        caps.add("reflection")
        caps.add("self-critique")
        return list(caps)

    async def process(self, message: Message) -> Message:
        """
        Execute reflection loop.

        Args:
            message: User's request/task

        Returns:
            Message containing refined output with reflection metadata

        Metadata Structure:
            - reflection_iterations: Number of iterations performed
            - final_quality_score: Final quality score achieved
            - stop_reason: Why the loop stopped
            - reflection_history: List of ReflectionStep dicts (if verbose=True)
            - initial_quality_score: Quality score of first output
            - total_improvement: improvement from first to final
        """
        self.history = []  # Reset for new task

        # Initial generation
        output = await self.generator.process(message)
        previous_score = 0.0

        for iteration in range(1, self.max_reflections + 1):
            # Critique current output
            critique_message = self._build_critique_prompt(
                original_query=message.content,
                current_output=output.content,
            )
            critique_response = await self.critic.process(critique_message)

            # Parse critique (score + feedback)
            score, feedback = self._parse_critique(critique_response.content)
            improvement = score - previous_score

            # Record step
            step = ReflectionStep(
                iteration=iteration,
                output=output.content,
                critique=feedback,
                quality_score=score,
                improvement=improvement,
            )
            self.history.append(step)

            # Check stopping conditions
            stop_reason, should_stop = self._check_stop_conditions(score, improvement)

            if should_stop:
                return self._format_result(output, stop_reason)

            # Refine based on critique
            refine_message = self._build_refinement_prompt(
                original_query=message.content,
                current_output=output.content,
                critique=feedback,
                iteration=iteration,
            )
            output = await self.generator.process(refine_message)
            previous_score = score

        # Max reflections reached
        return self._format_result(output, StopReason.MAX_REFLECTIONS)

    def _build_critique_prompt(self, original_query: str, current_output: str) -> Message:
        """
        Build prompt for critic agent.

        Args:
            original_query: User's original request
            current_output: Current output to critique

        Returns:
            Message for critic agent
        """
        if self.critique_format == CritiqueFormat.STRUCTURED:
            prompt = f"""Please evaluate the following output and provide structured feedback.

Original Request:
{original_query}

Current Output:
{current_output}

Provide your evaluation in this JSON format:
{{
  "score": <float between 0.0 and 1.0>,
  "feedback": "<specific feedback on what could be improved>"
}}

Focus on:
- Correctness: Does it solve the problem?
- Quality: Is it well-structured and clear?
- Completeness: Does it address all aspects?
- Potential Issues: Are there bugs or edge cases?
"""
        else:  # FREE_FORM
            prompt = f"""Please evaluate the following output on a scale of 0.0 to 1.0.

Original Request:
{original_query}

Current Output:
{current_output}

Provide:
1. A score (0.0-1.0) indicating quality
2. Specific feedback on what could be improved

Your evaluation:
"""

        return Message(role="user", content=prompt)

    def _build_refinement_prompt(
        self,
        original_query: str,
        current_output: str,
        critique: str,
        iteration: int,
    ) -> Message:
        """
        Build prompt for generator to refine output.

        Args:
            original_query: User's original request
            current_output: Current output to refine
            critique: Feedback from critic
            iteration: Current iteration number

        Returns:
            Message for generator agent
        """
        prompt = f"""Please refine your previous output based on the following critique.

Original Request:
{original_query}

Your Previous Output (Iteration {iteration}):
{current_output}

Critique:
{critique}

Please provide an improved version that addresses the critique while maintaining what was already good.

Refined Output:
"""

        return Message(role="user", content=prompt)

    def _parse_critique(self, critique_content: str) -> tuple[float, str]:
        """
        Parse critic's response into score and feedback.

        Args:
            critique_content: Raw critique content from critic agent

        Returns:
            Tuple of (score, feedback)
        """
        if self.critique_format == CritiqueFormat.STRUCTURED:
            # Try to parse JSON
            try:
                import json

                # Handle markdown code blocks
                content = critique_content.strip()
                if content.startswith("```"):
                    # Extract JSON from code block
                    lines = content.split("\n")
                    json_lines = [
                        line for line in lines if line and not line.startswith("```")
                    ]
                    content = "\n".join(json_lines)

                data = json.loads(content)
                score = float(data.get("score", 0.5))
                feedback = data.get("feedback", critique_content)

                # Clamp score to valid range
                score = max(0.0, min(1.0, score))

                return score, feedback

            except (json.JSONDecodeError, ValueError, KeyError):
                # Fallback to free-form parsing
                return self._parse_free_form_critique(critique_content)
        else:
            return self._parse_free_form_critique(critique_content)

    def _parse_free_form_critique(self, content: str) -> tuple[float, str]:
        """
        Parse free-form critique text.

        Looks for score indicators like:
        - "Score: 0.8"
        - "8/10"
        - "Rating: 7.5"

        Args:
            content: Free-form critique text

        Returns:
            Tuple of (score, feedback)
        """
        import re

        score = 0.5  # Default if no score found

        # Try to find score patterns
        patterns = [
            r"score[:\s]+([0-9]*\.?[0-9]+)",  # "Score: 0.8"
            r"rating[:\s]+([0-9]*\.?[0-9]+)",  # "Rating: 8"
            r"([0-9]+)/10",  # "8/10"
            r"([0-9]*\.?[0-9]+)/1\.?0",  # "0.8/1.0"
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # Normalize to 0.0-1.0 range
                if value > 1.0:
                    value = value / 10.0  # Assume 0-10 scale
                score = max(0.0, min(1.0, value))
                break

        return score, content

    def _check_stop_conditions(self, score: float, improvement: float) -> tuple[StopReason, bool]:
        """
        Check if reflection loop should stop.

        Args:
            score: Current quality score
            improvement: Improvement over previous iteration

        Returns:
            Tuple of (stop_reason, should_stop)
        """
        # Perfect score
        if score >= 1.0:
            return StopReason.PERFECT_SCORE, True

        # Quality threshold met
        if score >= self.quality_threshold:
            return StopReason.QUALITY_THRESHOLD_MET, True

        # Minimal improvement (skip on first iteration)
        if len(self.history) > 1 and improvement < self.improvement_threshold:
            return StopReason.MINIMAL_IMPROVEMENT, True

        # Continue iterating
        return StopReason.MAX_REFLECTIONS, False  # Placeholder, will be overridden if needed

    def _format_result(self, output: Message, stop_reason: StopReason) -> Message:
        """
        Format final result with metadata.

        Args:
            output: Final output message
            stop_reason: Why reflection stopped

        Returns:
            Message with reflection metadata
        """
        # Gather metadata
        metadata = {
            "reflection_iterations": len(self.history),
            "final_quality_score": self.history[-1].quality_score if self.history else 0.0,
            "stop_reason": stop_reason.value,
        }

        if self.history:
            metadata["initial_quality_score"] = self.history[0].quality_score
            metadata["total_improvement"] = (
                self.history[-1].quality_score - self.history[0].quality_score
            )

        # Include history if verbose
        if self.verbose:
            metadata["reflection_history"] = [step.to_dict() for step in self.history]

        # Create result message
        result = Message(
            role=output.role,
            content=output.content,
            metadata={**output.metadata, **metadata},
        )

        return result

    def get_history(self) -> list[ReflectionStep]:
        """
        Get reflection history from last execution.

        Returns:
            List of ReflectionStep objects
        """
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear reflection history."""
        self.history = []
