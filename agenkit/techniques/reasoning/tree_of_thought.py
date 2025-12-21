"""
Tree-of-Thought (ToT) Reasoning Technique

Explores multiple reasoning paths simultaneously using tree search with
branching, evaluation, and backtracking.

This technique builds a tree of reasoning paths, evaluates each path,
and uses search strategies to find the best solution. More sophisticated
than Chain-of-Thought for problems requiring exploration of solution space.

References:
    - Paper: https://arxiv.org/abs/2305.10601 (Yao et al., 2023)
    - Tree search with LLM-generated thoughts
    - Systematic exploration of reasoning space

Example:
    Basic usage::

        from agenkit.techniques.reasoning import TreeOfThought
        from agenkit import Message

        # Custom evaluator function
        def score_reasoning(text: str) -> float:
            # Simple heuristic: longer = more detailed = better
            return min(len(text) / 1000, 1.0)

        tot = TreeOfThought(
            llm=my_llm,
            branching_factor=3,
            max_depth=4,
            evaluator=score_reasoning
        )

        response = await tot.process(Message(
            role="user",
            content="Plan a 3-day trip to Tokyo"
        ))

        # Access reasoning tree
        tree_stats = response.metadata["tree_statistics"]
        print(f"Explored {tree_stats['total_nodes']} reasoning paths")
"""

from collections import deque
from collections.abc import Callable

from agenkit import Agent, Message

from .reasoning_tree import NodeState, ReasoningTree


class TreeOfThought(Agent):
    """
    Tree-of-Thought reasoning technique.

    Explores multiple reasoning paths in a tree structure, evaluates each path,
    and selects the best solution using configurable search strategies.

    This technique is particularly effective for:
    - Creative problem-solving requiring exploration
    - Planning and strategy tasks with multiple approaches
    - Problems where single path may lead to dead ends
    - Tasks benefiting from considering alternatives

    Attributes:
        name: Agent name (always "tree_of_thought")
        llm: LLM client for generating reasoning steps
        branching_factor: Number of branches to explore per step
        max_depth: Maximum tree depth
        evaluator: Function to score reasoning paths (returns 0.0-1.0)
        strategy: Search strategy ("bfs", "dfs", "best-first")
        prune_threshold: Prune paths with score below this threshold
    """

    def __init__(
        self,
        llm,  # LLMClient - type hint omitted for flexibility
        branching_factor: int = 3,
        max_depth: int = 5,
        evaluator: Callable[[str], float] | None = None,
        strategy: str = "best-first",
        prune_threshold: float = 0.3,
    ):
        """
        Initialize Tree-of-Thought agent.

        Args:
            llm: LLM client for generating responses. Must have a `complete()`
                or `process()` method that returns text.
            branching_factor: Number of alternative reasoning paths to explore
                at each step. Higher values explore more but cost more tokens.
                Default is 3 (explore 3 alternatives per step).
            max_depth: Maximum depth of reasoning tree. Limits how many
                reasoning steps to take. Default is 5 steps.
            evaluator: Function that scores a reasoning path (str -> float).
                Should return 0.0-1.0 where 1.0 is best. If None, uses
                a simple length-based heuristic.
            strategy: Search strategy to use:
                - "bfs": Breadth-first search (explore all at same depth first)
                - "dfs": Depth-first search (explore deep paths first)
                - "best-first": Always expand highest-scoring node
            prune_threshold: Prune paths with score below this threshold.
                Range 0.0-1.0. Lower values prune more aggressively.

        Example:
            >>> tot = TreeOfThought(
            ...     llm=my_llm,
            ...     branching_factor=3,
            ...     max_depth=4,
            ...     evaluator=my_scoring_fn,
            ...     strategy="best-first"
            ... )
        """
        self.llm = llm
        self.branching_factor = branching_factor
        self.max_depth = max_depth
        self.evaluator = evaluator or self._default_evaluator
        self.strategy = strategy
        self.prune_threshold = prune_threshold

    @property
    def name(self) -> str:
        """Return agent name."""
        return "tree_of_thought"

    def _default_evaluator(self, text: str) -> float:
        """
        Default evaluator using simple heuristics.

        Scores based on text length (more detailed = better) with
        a cap to avoid favoring extremely verbose reasoning.

        Args:
            text: Reasoning text to evaluate

        Returns:
            Score between 0.0 and 1.0
        """
        # Penalize very short responses
        if len(text) < 50:
            return 0.2

        # Favor moderate length (100-500 chars optimal)
        length_score = min(len(text) / 500, 1.0)

        # Bonus for structured reasoning (numbered steps)
        structure_bonus = 0.1 if any(c in text for c in ["1.", "2.", "-", "•"]) else 0.0

        return min(length_score + structure_bonus, 1.0)

    async def _generate_branches(
        self,
        prompt: str,
        n: int
    ) -> list[str]:
        """
        Generate N alternative reasoning branches.

        Args:
            prompt: Prompt to generate from
            n: Number of branches to generate

        Returns:
            List of generated reasoning texts
        """
        branches = []

        # Generate N branches (could be parallelized for speed)
        for i in range(n):
            # Add variation to prompt to encourage diversity
            varied_prompt = f"{prompt}\n\nAlternative approach #{i+1}:"

            # Get response from LLM
            if hasattr(self.llm, "complete"):
                response = await self.llm.complete(varied_prompt)
            elif hasattr(self.llm, "process"):
                llm_response = await self.llm.process(
                    Message(role="user", content=varied_prompt)
                )
                response = llm_response.content
            else:
                raise AttributeError(
                    "LLM must have either complete() or process() method"
                )

            branches.append(response)

        return branches

    async def _expand_node(
        self,
        tree: ReasoningTree,
        node_id: int,
        query: str
    ) -> list[int]:
        """
        Expand a node by generating child branches.

        Args:
            tree: Reasoning tree
            node_id: Node to expand
            query: Original query for context

        Returns:
            List of new child node IDs
        """
        node = tree.get_node(node_id)
        if not node:
            return []

        # Build prompt with path so far
        path_text = tree.get_path_text(node_id)
        prompt = f"Original question: {query}\n\nReasoning so far:\n{path_text}\n\nContinue reasoning:"

        # Generate branches
        branches = await self._generate_branches(prompt, self.branching_factor)

        # Add branches as children
        child_ids = []
        for branch_text in branches:
            # Score the branch
            full_path = f"{path_text}\n{branch_text}"
            score = self.evaluator(full_path)

            # Add child node
            child_id = tree.add_child(
                parent_id=node_id,
                content=branch_text,
                score=score
            )

            # Prune if score too low
            if score < self.prune_threshold:
                tree.prune_node(child_id)
            else:
                child_ids.append(child_id)

        # Mark node as evaluated
        node.state = NodeState.EVALUATED

        return child_ids

    async def _search_bfs(
        self,
        tree: ReasoningTree,
        root_id: int,
        query: str
    ) -> None:
        """
        Breadth-first search through reasoning tree.

        Args:
            tree: Reasoning tree
            root_id: Root node ID
            query: Original query
        """
        queue = deque([root_id])

        while queue:
            node_id = queue.popleft()
            node = tree.get_node(node_id)

            if not node or node.state == NodeState.PRUNED:
                continue

            # Stop if max depth reached
            if node.depth >= self.max_depth:
                node.state = NodeState.TERMINAL
                continue

            # Expand node
            child_ids = await self._expand_node(tree, node_id, query)
            queue.extend(child_ids)

    async def _search_dfs(
        self,
        tree: ReasoningTree,
        root_id: int,
        query: str
    ) -> None:
        """
        Depth-first search through reasoning tree.

        Args:
            tree: Reasoning tree
            root_id: Root node ID
            query: Original query
        """
        stack = [root_id]

        while stack:
            node_id = stack.pop()
            node = tree.get_node(node_id)

            if not node or node.state == NodeState.PRUNED:
                continue

            # Stop if max depth reached
            if node.depth >= self.max_depth:
                node.state = NodeState.TERMINAL
                continue

            # Expand node
            child_ids = await self._expand_node(tree, node_id, query)
            stack.extend(reversed(child_ids))  # Reverse to maintain left-to-right order

    async def _search_best_first(
        self,
        tree: ReasoningTree,
        root_id: int,
        query: str
    ) -> None:
        """
        Best-first search - always expand highest scoring node.

        Args:
            tree: Reasoning tree
            root_id: Root node ID
            query: Original query
        """
        # Priority queue (list of node_ids, sorted by score)
        open_nodes = [root_id]

        while open_nodes:
            # Sort by score (highest first)
            open_nodes.sort(
                key=lambda nid: tree.get_node(nid).score if tree.get_node(nid) else 0,
                reverse=True
            )

            # Pop highest scoring node
            node_id = open_nodes.pop(0)
            node = tree.get_node(node_id)

            if not node or node.state == NodeState.PRUNED:
                continue

            # Stop if max depth reached
            if node.depth >= self.max_depth:
                node.state = NodeState.TERMINAL
                continue

            # Expand node
            child_ids = await self._expand_node(tree, node_id, query)
            open_nodes.extend(child_ids)

    async def process(self, message: Message) -> Message:
        """
        Process message with Tree-of-Thought reasoning.

        Builds a reasoning tree, explores multiple paths using the configured
        search strategy, and returns the best complete reasoning path.

        Args:
            message: Input message with query content

        Returns:
            Message with best reasoning path and metadata. Metadata includes:
                - reasoning_tree_stats: Tree statistics
                - reasoning_path: List of steps in best path
                - num_steps: Number of steps in best path
                - best_score: Score of best path
                - technique: Always "tree_of_thought"
                - search_strategy: Strategy used

        Raises:
            AttributeError: If LLM doesn't have complete() or process() method
            ValueError: If invalid search strategy specified

        Example:
            >>> response = await tot.process(Message(role="user", content="Plan a trip"))
            >>> print(f"Explored {response.metadata['reasoning_tree_stats']['total_nodes']} paths")
            >>> print(f"Best path score: {response.metadata['best_score']}")
        """
        query = message.content

        # Create reasoning tree
        tree = ReasoningTree()
        root_id = tree.create_root(query)

        # Run search strategy
        if self.strategy == "bfs":
            await self._search_bfs(tree, root_id, query)
        elif self.strategy == "dfs":
            await self._search_dfs(tree, root_id, query)
        elif self.strategy == "best-first":
            await self._search_best_first(tree, root_id, query)
        else:
            raise ValueError(f"Invalid strategy: {self.strategy}")

        # Get best leaf node
        best_leaf = tree.get_best_leaf()

        if not best_leaf:
            # No valid path found
            return Message(
                role="assistant",
                content="Unable to find valid reasoning path.",
                metadata={
                    "technique": "tree_of_thought",
                    "search_strategy": self.strategy,
                    "reasoning_tree_stats": tree.get_statistics(),
                    "error": "no_valid_path"
                }
            )

        # Get best path
        best_path = tree.get_path(best_leaf.id)
        path_text = tree.get_path_text(best_leaf.id)

        return Message(
            role="assistant",
            content=path_text,
            metadata={
                "technique": "tree_of_thought",
                "search_strategy": self.strategy,
                "reasoning_tree_stats": tree.get_statistics(),
                "reasoning_path": [node.content for node in best_path],
                "num_steps": len(best_path),
                "best_score": best_leaf.score
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
            "tree_search",
            "multi_path_exploration",
            "backtracking",
            "tree_of_thought",
            "planning"
        ]
