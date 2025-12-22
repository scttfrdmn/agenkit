"""
Automated Optimization Framework Demo

Demonstrates:
1. Bayesian optimization for hyperparameter tuning
2. Prompt optimization with multiple strategies
3. Search space definition
4. Result analysis and visualization

Run: python examples/evaluation/optimization_demo.py
"""

import asyncio
import random

from agenkit.evaluation import (BayesianOptimizer, PromptOptimizer,
                                RandomSearchOptimizer, SearchSpace)
from agenkit.interfaces import Message


class SimpleLLMAgent:
    """
    Simple LLM agent simulator for demonstration.

    Simulates an LLM with configurable temperature and top_p.
    Performance improves with lower temperature and higher top_p.
    """

    def __init__(self, temperature: float = 0.7, top_p: float = 0.9, system_prompt: str = ""):
        self.temperature = temperature
        self.top_p = top_p
        self.system_prompt = system_prompt

    async def process(self, message: Message, session_id: str = "") -> Message:
        """Process message with simulated performance."""
        # Simulate performance based on config
        # Lower temperature + higher top_p = better performance
        base_score = (1 - self.temperature) * self.top_p

        # Add prompt bonus
        prompt_bonus = 0.0
        if "expert" in self.system_prompt.lower():
            prompt_bonus += 0.1
        if "detailed" in self.system_prompt.lower():
            prompt_bonus += 0.05
        if "concise" in self.system_prompt.lower():
            prompt_bonus += 0.05

        score = min(1.0, base_score + prompt_bonus)

        # Simulate latency (higher temp = slower)
        await asyncio.sleep(0.001 * (1 + self.temperature))

        # Return correct answer if score > threshold
        is_correct = random.random() < score
        content = "correct answer" if is_correct else "incorrect answer"

        return Message(role="assistant", content=content)


async def demo_random_search():
    """Demo 1: Random search baseline."""
    print("=" * 70)
    print("Demo 1: Random Search Optimization (Baseline)")
    print("=" * 70)

    random.seed(42)

    def agent_factory(config):
        return SimpleLLMAgent(**config)

    # Define search space
    search_space = {"temperature": (0.0, 1.0), "top_p": (0.5, 1.0)}

    # Create optimizer
    optimizer = RandomSearchOptimizer(
        agent_factory=agent_factory, search_space=search_space, objective="accuracy", maximize=True
    )

    # Generate test cases
    test_cases = [{"input": f"Question {i}", "expected": "correct answer"} for i in range(10)]

    print("\n🔍 Running random search...")
    print("  Search space: temperature=[0.0, 1.0], top_p=[0.5, 1.0]")
    print("  Iterations: 20")

    result = await optimizer.optimize(test_cases, n_iterations=20)

    print("\n📊 Results:")
    print(
        f"  Best config: temperature={result.best_config['temperature']:.3f}, top_p={result.best_config['top_p']:.3f}"
    )
    print(f"  Best score: {result.best_score:.3f}")
    print(f"  Improvement: {result.get_improvement():.1f}%")
    print(f"  Duration: {result.duration_seconds:.2f}s")

    return result


async def demo_bayesian_optimization():
    """Demo 2: Bayesian optimization with Gaussian Process."""
    print("\n" + "=" * 70)
    print("Demo 2: Bayesian Optimization (Smart Search)")
    print("=" * 70)

    random.seed(42)

    def agent_factory(config):
        return SimpleLLMAgent(**config)

    # Define search space
    search_space = {"temperature": (0.0, 1.0), "top_p": (0.5, 1.0)}

    # Create Bayesian optimizer
    optimizer = BayesianOptimizer(
        agent_factory=agent_factory,
        search_space=search_space,
        objective="accuracy",
        maximize=True,
        acquisition="ei",  # Expected Improvement
        n_initial=5,  # Random initialization
    )

    test_cases = [{"input": f"Question {i}", "expected": "correct answer"} for i in range(10)]

    print("\n🧠 Running Bayesian optimization...")
    print("  Algorithm: Gaussian Process with Expected Improvement")
    print("  Initial samples: 5 (random)")
    print("  Optimization samples: 15 (intelligent)")
    print("  Total iterations: 20")

    result = await optimizer.optimize(test_cases, n_iterations=20)

    print("\n📊 Results:")
    print(
        f"  Best config: temperature={result.best_config['temperature']:.3f}, top_p={result.best_config['top_p']:.3f}"
    )
    print(f"  Best score: {result.best_score:.3f}")
    print(f"  Improvement: {result.get_improvement():.1f}%")
    print(f"  Duration: {result.duration_seconds:.2f}s")

    print("\n💡 Bayesian optimization intelligently explores the space,")
    print("   balancing exploration (trying new areas) and exploitation")
    print("   (refining good areas) using Gaussian Process.")

    return result


async def demo_prompt_optimization_grid():
    """Demo 3: Prompt optimization with grid search."""
    print("\n" + "=" * 70)
    print("Demo 3: Prompt Optimization - Grid Search")
    print("=" * 70)

    random.seed(42)

    # Define prompt template
    template = """You are a {role}.
{instructions}

Please answer the following question."""

    # Define variations
    variations = {
        "role": ["helpful assistant", "expert advisor", "knowledgeable guide"],
        "instructions": ["Be concise and direct.", "Provide detailed explanations."],
    }

    def agent_factory(prompt):
        return SimpleLLMAgent(temperature=0.3, top_p=0.9, system_prompt=prompt)

    optimizer = PromptOptimizer(
        template=template,
        variations=variations,
        agent_factory=agent_factory,
        metrics=["accuracy"],
        objective_metric="accuracy",
    )

    test_cases = [{"input": f"Question {i}", "expected": "correct answer"} for i in range(5)]

    print("\n📝 Running grid search over prompt variations...")
    print("  Template variables: role (3 options), instructions (2 options)")
    print("  Total combinations: 3 × 2 = 6")

    result = await optimizer.optimize(test_cases, strategy="grid")

    print("\n📊 Results:")
    print("  Best prompt config:")
    for key, value in result.best_config.items():
        print(f"    {key}: {value}")
    print(f"  Best score: {result.best_scores['accuracy']:.3f}")
    print(f"  Evaluated: {result.n_evaluated} prompts")
    print(f"  Duration: {result.duration_seconds:.2f}s")

    print("\n✨ Best prompt:")
    print("-" * 70)
    print(result.best_prompt)
    print("-" * 70)

    return result


async def demo_prompt_optimization_genetic():
    """Demo 4: Prompt optimization with genetic algorithm."""
    print("\n" + "=" * 70)
    print("Demo 4: Prompt Optimization - Genetic Algorithm")
    print("=" * 70)

    random.seed(42)

    template = """You are a {role}.
{instructions}
{style}"""

    variations = {
        "role": ["assistant", "advisor", "expert", "guide"],
        "instructions": ["Be brief.", "Be thorough.", "Be clear.", "Be precise."],
        "style": ["Use simple language.", "Use technical terms.", "Use examples."],
    }

    def agent_factory(prompt):
        return SimpleLLMAgent(temperature=0.4, top_p=0.85, system_prompt=prompt)

    optimizer = PromptOptimizer(
        template=template,
        variations=variations,
        agent_factory=agent_factory,
        metrics=["accuracy"],
    )

    test_cases = [{"input": f"Question {i}", "expected": "correct answer"} for i in range(5)]

    print("\n🧬 Running genetic algorithm for prompt evolution...")
    print("  Search space: 4 × 4 × 3 = 48 combinations")
    print("  Population size: 10")
    print("  Generations: 5")
    print("  Mutation rate: 20%")

    result = await optimizer.optimize(
        test_cases, strategy="genetic", population_size=10, n_generations=5, mutation_rate=0.2
    )

    print("\n📊 Results:")
    print("  Best prompt config:")
    for key, value in result.best_config.items():
        print(f"    {key}: {value}")
    print(f"  Best score: {result.best_scores['accuracy']:.3f}")
    print(f"  Evaluated: {result.n_evaluated} prompts")
    print(f"  Duration: {result.duration_seconds:.2f}s")

    print("\n✨ Evolved prompt:")
    print("-" * 70)
    print(result.best_prompt)
    print("-" * 70)

    print("\n💡 Genetic algorithm evolves prompts through selection,")
    print("   mutation, and natural selection over multiple generations.")

    return result


async def demo_complex_search_space():
    """Demo 5: Complex search space with multiple parameter types."""
    print("\n" + "=" * 70)
    print("Demo 5: Complex Search Space Definition")
    print("=" * 70)

    # Create search space with all parameter types
    space = SearchSpace()

    # Continuous parameters
    space.add_continuous("temperature", 0.0, 1.0)
    space.add_continuous("top_p", 0.0, 1.0)

    # Discrete parameters
    space.add_discrete("max_tokens", [128, 256, 512, 1024])

    # Integer parameters
    space.add_integer("n_examples", 0, 5)

    # Categorical parameters
    space.add_categorical("model", ["gpt-4", "claude-3", "gemini"])

    print("\n🔧 Defined search space:")
    print("  Continuous: temperature, top_p")
    print("  Discrete: max_tokens (4 values)")
    print("  Integer: n_examples (0-5)")
    print("  Categorical: model (3 options)")

    print("\n🎲 Sampling 5 random configurations:")
    for i in range(5):
        config = space.sample()
        print(f"\n  Config {i + 1}:")
        for key, value in config.items():
            if isinstance(value, float):
                print(f"    {key}: {value:.3f}")
            else:
                print(f"    {key}: {value}")


async def main():
    """Run all demos."""
    print("\n" + "🚀" * 35)
    print("AUTOMATED OPTIMIZATION FRAMEWORK DEMONSTRATION")
    print("🚀" * 35 + "\n")

    # Run demos
    await demo_random_search()
    await demo_bayesian_optimization()
    await demo_prompt_optimization_grid()
    await demo_prompt_optimization_genetic()
    await demo_complex_search_space()

    print("\n" + "=" * 70)
    print("🎉 All demos completed!")
    print("=" * 70)
    print("\n📚 Key Takeaways:")
    print("  • Random search: Simple baseline for optimization")
    print("  • Bayesian optimization: Intelligent search with Gaussian Process")
    print("  • Prompt optimization: Systematic prompt improvement")
    print("  • Genetic algorithms: Evolutionary optimization")
    print("  • Search spaces: Support continuous, discrete, integer, categorical")
    print("\n💡 Use Cases:")
    print("  • Tune LLM hyperparameters (temperature, top_p, max_tokens)")
    print("  • Optimize system prompts for better performance")
    print("  • Find best model configuration for your use case")
    print("  • A/B test different agent configurations")
    print()


if __name__ == "__main__":
    asyncio.run(main())
