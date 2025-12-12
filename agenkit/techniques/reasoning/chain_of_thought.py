"""
Chain-of-Thought (CoT) Reasoning Technique

Encourages step-by-step reasoning through structured prompting.

This technique applies structured prompting to encourage LLMs to show their
reasoning process explicitly, leading to more accurate and explainable results.

References:
    - Paper: https://arxiv.org/abs/2201.11903 (Wei et al., 2022)
    - "Let's think step by step" prompting
    - Critical for modern reasoning models (o3, Opus 4)

Example:
    Basic usage::

        from agenkit.techniques.reasoning import ChainOfThought
        from agenkit import Message

        cot = ChainOfThought(llm=my_llm)
        response = await cot.process(Message(content="What is 15 * 24?"))
        print(response.metadata["reasoning_steps"])

    Custom prompt template::

        cot = ChainOfThought(
            llm=my_llm,
            prompt_template="Solve step by step:\\n{query}"
        )
"""

import re
from typing import List, Optional
from agenkit import Agent, Message


class ChainOfThought(Agent):
    """
    Chain-of-Thought reasoning technique.

    Applies structured prompting to encourage step-by-step reasoning,
    optionally parsing and tracking individual reasoning steps.

    This technique is particularly effective for:
    - Mathematical reasoning
    - Logical deduction
    - Complex problem-solving
    - Multi-step tasks requiring explanation

    Attributes:
        name: Agent name (always "chain_of_thought")
        llm: LLM client for generating responses
        prompt_template: Template with {query} placeholder
        parse_steps: Whether to extract reasoning steps
        step_delimiter: Delimiter for splitting steps
        max_steps: Maximum number of steps to extract
    """

    def __init__(
        self,
        llm,  # LLMClient - type hint omitted for flexibility
        prompt_template: str = "Let's think step by step:\n{query}",
        parse_steps: bool = True,
        step_delimiter: str = "\n",
        max_steps: Optional[int] = None,
    ):
        """
        Initialize Chain-of-Thought agent.

        Args:
            llm: LLM client for generating responses. Must have a `complete()`
                or `process()` method that returns text.
            prompt_template: Template string with {query} placeholder for
                formatting the CoT prompt. Default encourages step-by-step
                reasoning with "Let's think step by step"
            parse_steps: Whether to extract and track individual reasoning steps
                in the response metadata. Default True.
            step_delimiter: String delimiter for splitting steps when using
                simple delimiter-based parsing. Default is newline.
            max_steps: Maximum number of reasoning steps to extract. None means
                unlimited. Useful for limiting verbosity.

        Example:
            >>> cot = ChainOfThought(
            ...     llm=my_llm,
            ...     prompt_template="Reason carefully:\n{query}",
            ...     max_steps=5
            ... )
        """
        self.llm = llm
        self.prompt_template = prompt_template
        self.parse_steps = parse_steps
        self.step_delimiter = step_delimiter
        self.max_steps = max_steps

    @property
    def name(self) -> str:
        """Return agent name."""
        return "chain_of_thought"

    async def process(self, message: Message) -> Message:
        """
        Process message with Chain-of-Thought reasoning.

        Applies the CoT prompt template to the input message, generates a
        response using the LLM, and optionally parses reasoning steps.

        Args:
            message: Input message with query content

        Returns:
            Message with response content and metadata. If parse_steps=True,
            metadata includes:
                - reasoning_steps: List of extracted reasoning steps
                - num_steps: Number of steps found
                - technique: Always "chain_of_thought"

        Raises:
            AttributeError: If LLM doesn't have complete() or process() method
            KeyError: If prompt_template doesn't contain {query} placeholder

        Example:
            >>> response = await cot.process(Message(content="Calculate 15*24"))
            >>> print(f"Steps: {len(response.metadata['reasoning_steps'])}")
            Steps: 3
        """
        # Apply CoT prompting
        cot_prompt = self.prompt_template.format(query=message.content)

        # Get response from LLM (support both complete() and process() methods)
        if hasattr(self.llm, "complete"):
            response_text = await self.llm.complete(cot_prompt)
        elif hasattr(self.llm, "process"):
            llm_response = await self.llm.process(Message(role="user", content=cot_prompt))
            response_text = llm_response.content
        else:
            raise AttributeError(
                "LLM must have either complete() or process() method"
            )

        # Parse steps if requested
        if self.parse_steps:
            steps = self._parse_steps(response_text)
            return Message(
                role="assistant",
                content=response_text,
                metadata={
                    "reasoning_steps": steps,
                    "num_steps": len(steps),
                    "technique": "chain_of_thought",
                },
            )

        return Message(
            role="assistant",
            content=response_text,
            metadata={"technique": "chain_of_thought"}
        )

    def _parse_steps(self, text: str) -> List[str]:
        """
        Parse reasoning steps from response text.

        Supports multiple common step formats:
        - Numbered steps (1. Step one, 2. Step two)
        - Bullet points (- Step, * Step, • Step)
        - Newline-separated thoughts (fallback)

        The parser tries formats in order: numbered, bullets, delimiter-based.

        Args:
            text: Response text to parse

        Returns:
            List of reasoning step strings, stripped of formatting

        Example:
            >>> steps = cot._parse_steps("1. First\\n2. Second\\n3. Third")
            >>> len(steps)
            3
        """
        # Try numbered steps first (1. 2. 3. or 1) 2) 3))
        numbered = re.findall(r"^\d+[\.)]\s*(.+)$", text, re.MULTILINE)
        if numbered and len(numbered) >= 2:
            steps = numbered
        else:
            # Try bullet points (-, *, •)
            bullets = re.findall(r"^[•\-\*]\s*(.+)$", text, re.MULTILINE)
            if bullets and len(bullets) >= 2:
                steps = bullets
            else:
                # Fall back to delimiter-based splitting
                steps = [
                    s.strip()
                    for s in text.split(self.step_delimiter)
                    if s.strip()
                ]

        # Apply max_steps limit if specified
        if self.max_steps:
            steps = steps[: self.max_steps]

        return steps

    @property
    def capabilities(self) -> list[str]:
        """
        Return agent capabilities.

        Returns:
            List of capability strings describing what this agent can do
        """
        return [
            "reasoning",
            "step_by_step",
            "chain_of_thought",
            "explainable_ai",
        ]
