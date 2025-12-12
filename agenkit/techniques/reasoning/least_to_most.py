"""
Least-to-Most Prompting Technique

Breaks complex problems into simpler subproblems, solves them sequentially
from simplest to most complex, using solutions to build up to the final answer.

This technique is particularly effective for compositional reasoning where
complex problems can be decomposed into manageable pieces.

References:
    - Paper: https://arxiv.org/abs/2205.10625 (Zhou et al., 2022)
    - "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models"
    - Effective for math, symbolic manipulation, compositional generalization

Example:
    Basic usage::

        from agenkit.techniques.reasoning import LeastToMost
        from agenkit import Message

        ltm = LeastToMost(llm=my_llm, max_subproblems=5)

        response = await ltm.process(Message(
            role="user",
            content="Calculate the total cost of 3 apples at $2 each and 2 oranges at $3 each"
        ))

        # Access subproblems and solutions
        print(response.metadata['subproblems'])
        print(response.metadata['subproblem_solutions'])
"""

from dataclasses import dataclass
from typing import Callable, Optional, List
from agenkit import Agent, Message


@dataclass
class Subproblem:
    """Represents a subproblem in the decomposition."""

    content: str
    difficulty: int = 0  # 0 = easiest
    dependencies: List[int] = None  # Indices of subproblems this depends on

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class LeastToMost(Agent):
    """
    Least-to-Most prompting technique.

    Decomposes complex problems into simpler subproblems, solves them
    sequentially from easiest to hardest, using previous solutions as
    context for solving harder problems.

    This technique is particularly effective for:
    - Compositional reasoning tasks
    - Multi-step math problems
    - Problems that naturally decompose into stages
    - Tasks where simpler subtasks inform harder ones

    Attributes:
        name: Agent name (always "least_to_most")
        llm: LLM client for generating responses
        decomposer: Custom decomposition function
        max_subproblems: Maximum number of subproblems
        compose_solutions: Whether to use previous solutions as context
    """

    def __init__(
        self,
        llm,  # LLMClient - type hint omitted for flexibility
        decomposer: Optional[Callable[[str], List[str]]] = None,
        max_subproblems: int = 5,
        compose_solutions: bool = True,
    ):
        """
        Initialize Least-to-Most agent.

        Args:
            llm: LLM client for generating responses. Must have a `complete()`
                or `process()` method that returns text.
            decomposer: Optional custom function to decompose problems into
                subproblems (str -> List[str]). If None, uses LLM to decompose.
            max_subproblems: Maximum number of subproblems to generate.
                Limits decomposition depth. Default is 5.
            compose_solutions: Whether to use previous subproblem solutions
                as context when solving harder problems. Default True.

        Example:
            >>> ltm = LeastToMost(
            ...     llm=my_llm,
            ...     max_subproblems=5,
            ...     compose_solutions=True
            ... )
        """
        self.llm = llm
        self.decomposer = decomposer
        self.max_subproblems = max_subproblems
        self.compose_solutions = compose_solutions

    @property
    def name(self) -> str:
        """Return agent name."""
        return "least_to_most"

    async def _llm_call(self, prompt: str) -> str:
        """
        Call LLM with prompt.

        Args:
            prompt: Prompt to send to LLM

        Returns:
            LLM response text
        """
        if hasattr(self.llm, "complete"):
            return await self.llm.complete(prompt)
        elif hasattr(self.llm, "process"):
            response = await self.llm.process(Message(role="user", content=prompt))
            return response.content
        else:
            raise AttributeError("LLM must have either complete() or process() method")

    async def decompose(self, problem: str) -> List[Subproblem]:
        """
        Decompose problem into subproblems.

        Args:
            problem: Original problem to decompose

        Returns:
            List of Subproblem objects ordered from easiest to hardest
        """
        if self.decomposer:
            # Use custom decomposer
            subproblem_texts = self.decomposer(problem)
            subproblems = [
                Subproblem(content=text, difficulty=i)
                for i, text in enumerate(subproblem_texts[:self.max_subproblems])
            ]
            return subproblems

        # Use LLM to decompose
        decomposition_prompt = f"""Break down this problem into simpler subproblems, ordered from easiest to hardest.
List each subproblem on a separate line, numbered 1, 2, 3, etc.

Problem: {problem}

Subproblems (from simplest to most complex):"""

        response = await self._llm_call(decomposition_prompt)

        # Parse subproblems from response
        subproblems = []
        lines = response.strip().split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Remove numbering (1., 1), etc.)
            import re
            cleaned = re.sub(r'^\d+[\.)]\s*', '', line)

            if cleaned and len(subproblems) < self.max_subproblems:
                subproblems.append(
                    Subproblem(content=cleaned, difficulty=i)
                )

        # If decomposition failed, treat as atomic problem
        if not subproblems:
            subproblems = [Subproblem(content=problem, difficulty=0)]

        return subproblems

    async def solve_subproblem(
        self,
        subproblem: Subproblem,
        previous_solutions: List[str]
    ) -> str:
        """
        Solve one subproblem, optionally using previous solutions as context.

        Args:
            subproblem: Subproblem to solve
            previous_solutions: Solutions to previous (easier) subproblems

        Returns:
            Solution to this subproblem
        """
        if self.compose_solutions and previous_solutions:
            # Include previous solutions as context
            context = "\n".join([
                f"Previous solution {i+1}: {sol}"
                for i, sol in enumerate(previous_solutions)
            ])

            prompt = f"""Given these previous solutions to simpler subproblems:

{context}

Now solve this subproblem:
{subproblem.content}

Solution:"""
        else:
            # Solve without context
            prompt = f"""Solve this subproblem:

{subproblem.content}

Solution:"""

        solution = await self._llm_call(prompt)
        return solution.strip()

    async def process(self, message: Message) -> Message:
        """
        Process message with Least-to-Most prompting.

        Decomposes the problem, solves subproblems sequentially from easiest
        to hardest, and composes the final solution.

        Args:
            message: Input message with problem

        Returns:
            Message with final solution and metadata. Metadata includes:
                - subproblems: List of subproblem texts
                - subproblem_solutions: List of solutions to each subproblem
                - num_subproblems: Number of subproblems generated
                - technique: Always "least_to_most"

        Example:
            >>> response = await ltm.process(Message(
            ...     role="user",
            ...     content="Calculate 3*4 + 2*5"
            ... ))
            >>> print(response.metadata['subproblems'])
            >>> print(response.metadata['subproblem_solutions'])
        """
        problem = message.content

        # Step 1: Decompose problem
        subproblems = await self.decompose(problem)

        # Step 2: Solve subproblems sequentially
        solutions = []
        for subproblem in subproblems:
            solution = await self.solve_subproblem(subproblem, solutions)
            solutions.append(solution)

        # Step 3: Final solution is the last one (hardest problem)
        final_solution = solutions[-1] if solutions else ""

        return Message(
            role="assistant",
            content=final_solution,
            metadata={
                "technique": "least_to_most",
                "num_subproblems": len(subproblems),
                "subproblems": [sp.content for sp in subproblems],
                "subproblem_solutions": solutions,
                "compose_solutions": self.compose_solutions
            }
        )

    @property
    def capabilities(self) -> list[str]:
        """
        Return agent capabilities.

        Returns:
            List of capability strings describing what this agent can do
        """
        return [
            "reasoning",
            "decomposition",
            "compositional_reasoning",
            "least_to_most",
            "sequential_solving"
        ]
