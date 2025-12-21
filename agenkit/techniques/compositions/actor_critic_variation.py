"""
Actor-Critic Variation Composition

Demonstrates that "actor-critic" in LLM context is just the Reflection pattern
with different terminology borrowed from reinforcement learning.

This composition exists for educational purposes to show:
1. Actor = Generator (proposes solutions)
2. Critic = Evaluator (assesses solutions)
3. The loop is identical to Reflection pattern

**IMPORTANT**: For production use, use the ReflectionAgent pattern directly.
This composition is here to show equivalence with RL terminology.

This composition is perfect for:
- Understanding terminology mapping
- Learning pattern equivalence
- Academic discussions
- Comparing with RL literature

References:
    Source: Albada "Building Applications with AI Agents" (2025)
    Pattern: ReflectionAgent in agenkit.patterns.reflection
    RL Concept: Actor-Critic algorithms (but adapted for LLMs, not true RL)

Example:
    Educational usage::

        from agenkit.techniques.compositions import ActorCriticVariation
        from agenkit import Message

        # This is just ReflectionAgent with RL terms!
        ac = ActorCriticVariation(
            actor=my_generator_agent,  # "actor" = generator
            critic=my_evaluator_agent,  # "critic" = evaluator
            max_iterations=5
        )

        response = await ac.process(Message(
            role="user",
            content="Write a haiku about coding"
        ))

        # For production, use ReflectionAgent instead:
        # from agenkit.patterns import ReflectionAgent
        # reflection = ReflectionAgent(
        #     generator=my_generator_agent,
        #     critic=my_evaluator_agent,
        #     max_iterations=5
        # )
"""

from agenkit import Agent, Message


class ActorCriticVariation(Agent):
    """
    Actor-Critic variation showing equivalence to Reflection pattern.

    This is an educational composition (~80 LOC) that demonstrates
    how "actor-critic" in LLM context is just the Reflection pattern
    with terminology borrowed from reinforcement learning.

    **Terminology Mapping:**
    - Actor = Generator (proposes solutions)
    - Critic = Evaluator (assesses quality, suggests improvements)
    - Policy = Generation strategy
    - Value function = Quality assessment

    **Key Difference from RL:**
    Unlike true actor-critic in RL (which uses gradient updates and
    value functions), this is just iterative refinement via prompting.

    **For Production Use:**
    Use `agenkit.patterns.reflection.ReflectionAgent` which provides:
    - Quality thresholds
    - Convergence detection
    - Multiple stopping criteria
    - Structured critique formats
    - Production error handling

    Attributes:
        name: Agent name (always "actor_critic_variation")
        actor: Generator agent (proposes solutions)
        critic: Evaluator agent (critiques solutions)
        max_iterations: Maximum refinement iterations
    """

    def __init__(
        self,
        actor: Agent,
        critic: Agent,
        max_iterations: int = 5,
        improvement_threshold: float = 0.05
    ):
        """
        Initialize actor-critic variation.

        Args:
            actor: Actor agent that generates solutions.
                In RL: the policy. In LLMs: the generator.
            critic: Critic agent that evaluates solutions.
                In RL: the value function. In LLMs: the evaluator.
            max_iterations: Maximum refinement iterations. Default: 5
            improvement_threshold: Minimum improvement to continue.
                Default: 0.05

        Example:
            >>> # Educational: showing equivalence
            >>> ac = ActorCriticVariation(
            ...     actor=generator_agent,
            ...     critic=evaluator_agent,
            ...     max_iterations=5
            ... )
            >>>
            >>> # Production: use ReflectionAgent instead
            >>> from agenkit.patterns import ReflectionAgent
            >>> reflection = ReflectionAgent(
            ...     generator=generator_agent,
            ...     critic=evaluator_agent,
            ...     max_iterations=5
            ... )
        """
        self.actor = actor
        self.critic = critic
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold

    @property
    def name(self) -> str:
        """Return agent name."""
        return "actor_critic_variation"

    async def _actor_step(self, message: Message) -> Message:
        """
        Actor generates a solution (analogous to policy in RL).

        Args:
            message: Input message

        Returns:
            Generated solution
        """
        return await self.actor.process(message)

    async def _critic_step(self, solution: Message) -> tuple[float, str]:
        """
        Critic evaluates solution (analogous to value function in RL).

        Args:
            solution: Generated solution to evaluate

        Returns:
            Tuple of (score, critique_text)
        """
        critique_prompt = f"""Evaluate the following solution and provide:
1. A quality score (0-10)
2. Specific improvements

Solution:
{solution.content}

Evaluation:"""

        critique_response = await self.critic.process(
            Message(role="user", content=critique_prompt)
        )

        # Extract score (simple parsing)
        score = self._extract_score(critique_response.content)

        return score, critique_response.content

    def _extract_score(self, critique: str) -> float:
        """
        Extract numerical score from critique.

        Args:
            critique: Critique text

        Returns:
            Score normalized to 0-1 scale
        """
        # Simple extraction - look for "score: X" or "X/10"
        import re

        # Try to find "score: X" or "X/10"
        patterns = [
            r'score[:\s]+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)/10',
            r'quality[:\s]+(\d+(?:\.\d+)?)'
        ]

        for pattern in patterns:
            match = re.search(pattern, critique.lower())
            if match:
                score = float(match.group(1))
                # Normalize to 0-1
                return min(1.0, score / 10.0)

        # Default if no score found
        return 0.5

    async def process(self, message: Message) -> Message:
        """
        Process message with actor-critic loop.

        This demonstrates the equivalence to Reflection pattern:
        1. Actor generates solution (generator)
        2. Critic evaluates solution (critic)
        3. If score low, actor refines based on critique (reflection)
        4. Repeat until good enough or max iterations

        Args:
            message: Input message

        Returns:
            Final refined solution. Metadata includes:
                - technique: Always "actor_critic_variation"
                - iterations: Number of refinement iterations
                - final_score: Final quality score
                - scores_history: List of scores across iterations
                - note: Reminder to use ReflectionAgent for production

        Example:
            >>> response = await ac.process(Message(
            ...     role="user",
            ...     content="Write a function to sort a list"
            ... ))
            >>> print(f"Refined {response.metadata['iterations']} times")
            >>> print(f"Final score: {response.metadata['final_score']}")
        """
        current_solution = message
        iteration = 0
        scores_history = []
        critiques_history = []

        previous_score = 0.0

        while iteration < self.max_iterations:
            iteration += 1

            # Actor step: generate/refine solution
            solution = await self._actor_step(current_solution)

            # Critic step: evaluate solution
            score, critique = await self._critic_step(solution)

            scores_history.append(score)
            critiques_history.append(critique)

            # Check for sufficient quality or diminishing returns
            improvement = score - previous_score

            if score >= 0.9 or (iteration > 1 and improvement < self.improvement_threshold):
                # Good enough or not improving
                break

            # Prepare refinement message for next iteration
            refinement_prompt = f"""Your previous solution:
{solution.content}

Critique:
{critique}

Please refine your solution addressing the critique."""

            current_solution = Message(
                role="user",
                content=refinement_prompt
            )

            previous_score = score

        # Final solution
        final_solution = solution

        metadata = {
            "technique": "actor_critic_variation",
            "iterations": iteration,
            "final_score": scores_history[-1] if scores_history else 0.0,
            "scores_history": scores_history,
            "critiques_history": critiques_history,
            "note": "This is equivalent to ReflectionAgent. Use agenkit.patterns.reflection.ReflectionAgent for production."
        }

        if final_solution.metadata:
            metadata.update(final_solution.metadata)

        return Message(
            role=final_solution.role,
            content=final_solution.content,
            metadata=metadata
        )

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return [
            "iterative_refinement",
            "actor_critic",
            "reflection",  # Because it's the same thing!
            "quality_improvement"
        ]


# Educational note for users
def why_use_reflection_instead() -> str:
    """
    Explain why ReflectionAgent is preferred over this composition.

    Returns:
        Explanation text
    """
    return """
## Why Use ReflectionAgent Instead?

The Actor-Critic Variation demonstrates that "actor-critic" in LLM context
is just the Reflection pattern with terminology borrowed from RL.

### Terminology Mapping:
- **Actor** = Generator (proposes solutions)
- **Critic** = Evaluator/Critic (assesses and suggests improvements)
- **Policy optimization** = Iterative prompt refinement
- **Value function** = Quality scoring

### Key Differences from True RL:
1. **No gradient updates** - This uses prompting, not backpropagation
2. **No learned value function** - The critic is prompted, not trained
3. **No policy network** - The actor is prompted, not a neural network
4. **Synchronous** - True actor-critic is often asynchronous

### For Production Use:
```python
from agenkit.patterns import ReflectionAgent

# Use ReflectionAgent - it's the same pattern with:
# - Better error handling
# - Quality thresholds
# - Convergence detection
# - Structured critique formats
# - Production-grade features

reflection = ReflectionAgent(
    generator=my_generator,
    critic=my_critic,
    max_iterations=5,
    quality_threshold=0.8,
    improvement_threshold=0.05
)
```

### When This Composition Is Useful:
- **Educational**: Understanding terminology equivalence
- **Academic**: Discussing RL concepts in LLM context
- **Book discussions**: When books call this "actor-critic"

### Bottom Line:
If a book or framework calls something "actor-critic" for LLMs,
it's probably just the Reflection pattern. Use Agenkit's
ReflectionAgent for production systems.
"""
