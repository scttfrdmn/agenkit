"""
Exploration Strategy Composition

Implements exploration-exploitation tradeoff using Upper Confidence Bound (UCB)
for action selection. This is useful when an agent needs to balance trying
new actions vs exploiting known good actions.

This composition demonstrates that "exploration strategies" are just:
1. Action statistics tracking
2. UCB scoring
3. Action selection logic

For production reinforcement learning systems, use proper RL frameworks
(Stable-Baselines3, Ray RLlib, etc.) with sophisticated exploration strategies.

This composition is perfect for:
- Simple bandit problems
- Learning exploration concepts
- Quick experiments
- Non-critical decision making

References:
    Algorithm: Upper Confidence Bound (UCB1)
    Pattern: Could be combined with ReActAgent

Example:
    Basic usage::

        from agenkit.techniques.compositions import ExplorationStrategy
        from agenkit import Message

        explorer = ExplorationStrategy(
            agent=my_react_agent,
            actions=["search", "calculate", "reason"],
            exploration_constant=1.0
        )

        response = await explorer.process(
            Message(role="user", content="Solve this problem")
        )

        print(f"Selected action: {response.metadata['selected_action']}")
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

from agenkit import Agent, Message


@dataclass
class ActionStats:
    """
    Statistics for an action in exploration strategy.

    Attributes:
        action: Action identifier
        trials: Number of times tried
        total_reward: Cumulative reward
        mean_reward: Average reward
    """

    action: str
    trials: int = 0
    total_reward: float = 0.0
    mean_reward: float = 0.0

    def update(self, reward: float):
        """Update statistics with new reward."""
        self.trials += 1
        self.total_reward += reward
        self.mean_reward = self.total_reward / self.trials


class ExplorationStrategy(Agent):
    """
    Exploration strategy composition using UCB.

    Implements Upper Confidence Bound (UCB1) algorithm for balancing
    exploration (trying new actions) with exploitation (using known
    good actions).

    This is a simple composition (~70 LOC) showing exploration-exploitation
    tradeoff. For production RL systems, use proper RL frameworks.

    For advanced use cases, consider:
    - Thompson Sampling
    - Epsilon-greedy with decay
    - Contextual bandits
    - Deep RL approaches

    Attributes:
        name: Agent name (always "exploration_strategy")
        agent: Base agent to wrap
        actions: Available actions
        stats: Statistics for each action
        exploration_constant: UCB exploration parameter
        total_trials: Total trials across all actions
    """

    def __init__(
        self,
        agent: Agent,
        actions: list[str],
        exploration_constant: float = 1.0,
        reward_fn: Callable | None = None,
    ):
        """
        Initialize exploration strategy.

        Args:
            agent: Base agent to wrap with exploration
            actions: List of available action identifiers
            exploration_constant: UCB exploration parameter (c).
                Higher values = more exploration. Typical range: 0.5-2.0.
                Default: 1.0
            reward_fn: Optional function to compute reward from response.
                If None, uses simple success heuristic.

        Example:
            >>> explorer = ExplorationStrategy(
            ...     agent=my_agent,
            ...     actions=["search", "calculate", "reason"],
            ...     exploration_constant=1.5
            ... )
        """
        self.agent = agent
        self.actions = actions
        self.exploration_constant = exploration_constant
        self.reward_fn = reward_fn or self._default_reward

        # Initialize statistics
        self.stats: dict[str, ActionStats] = {
            action: ActionStats(action=action) for action in actions
        }
        self.total_trials = 0

    @property
    def name(self) -> str:
        """Return agent name."""
        return "exploration_strategy"

    def _default_reward(self, response: Message) -> float:
        """
        Default reward function.

        Args:
            response: Agent response

        Returns:
            Reward between 0 and 1
        """
        # Simple heuristic: longer responses = better
        # In practice, you'd use task-specific metrics
        content_length = len(response.content)
        return min(1.0, content_length / 1000.0)

    def _compute_ucb_score(self, action: str) -> float:
        """
        Compute UCB score for an action.

        Args:
            action: Action to score

        Returns:
            UCB score (higher = should be selected)
        """
        stats = self.stats[action]

        # If never tried, return infinity (always try untried actions first)
        if stats.trials == 0:
            return float("inf")

        # UCB1 formula: mean_reward + c * sqrt(ln(total_trials) / trials)
        exploration_bonus = self.exploration_constant * math.sqrt(
            math.log(self.total_trials) / stats.trials
        )

        return stats.mean_reward + exploration_bonus

    def select_action(self) -> str:
        """
        Select action using UCB strategy.

        Returns:
            Selected action identifier

        Example:
            >>> action = explorer.select_action()
            >>> print(f"Selected: {action}")
        """
        # Compute UCB scores for all actions
        scores = {action: self._compute_ucb_score(action) for action in self.actions}

        # Select action with highest UCB score
        best_action = max(scores, key=scores.get)
        return best_action

    def update_stats(self, action: str, reward: float):
        """
        Update statistics after action execution.

        Args:
            action: Action that was executed
            reward: Reward received

        Example:
            >>> explorer.update_stats("search", 0.8)
        """
        self.stats[action].update(reward)
        self.total_trials += 1

    async def process(self, message: Message) -> Message:
        """
        Process message with exploration strategy.

        Selects action using UCB, executes with agent, updates statistics.

        Args:
            message: Input message

        Returns:
            Message from agent. Metadata includes:
                - selected_action: Action chosen by UCB
                - ucb_scores: UCB scores for all actions
                - action_stats: Current statistics for all actions
                - reward: Reward received
                - technique: Always "exploration_strategy"

        Example:
            >>> response = await explorer.process(Message(
            ...     role="user",
            ...     content="Solve problem X"
            ... ))
            >>> print(f"Used action: {response.metadata['selected_action']}")
        """
        # Select action using UCB
        selected_action = self.select_action()

        # Compute current UCB scores for metadata
        ucb_scores = {action: self._compute_ucb_score(action) for action in self.actions}

        # Add action hint to message
        enhanced_message = Message(
            role=message.role,
            content=f"[Action Hint: {selected_action}]\n\n{message.content}",
            metadata=message.metadata,
        )

        # Process with agent
        response = await self.agent.process(enhanced_message)

        # Compute reward
        reward = self.reward_fn(response)

        # Update statistics
        self.update_stats(selected_action, reward)

        # Build metadata
        metadata = {
            "technique": "exploration_strategy",
            "selected_action": selected_action,
            "ucb_scores": ucb_scores,
            "action_stats": {
                action: {"trials": stats.trials, "mean_reward": stats.mean_reward}
                for action, stats in self.stats.items()
            },
            "reward": reward,
            "total_trials": self.total_trials,
        }

        if response.metadata:
            metadata.update(response.metadata)

        return Message(role=response.role, content=response.content, metadata=metadata)

    def get_best_action(self) -> str:
        """
        Get best action based on mean reward (exploitation only).

        Returns:
            Action with highest mean reward
        """
        return max(self.stats, key=lambda a: self.stats[a].mean_reward)

    def reset_stats(self):
        """Reset all statistics."""
        for action in self.actions:
            self.stats[action] = ActionStats(action=action)
        self.total_trials = 0

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        base_caps = self.agent.capabilities if hasattr(self.agent, "capabilities") else []
        return [*base_caps, "exploration", "exploitation", "action_selection", "ucb"]
