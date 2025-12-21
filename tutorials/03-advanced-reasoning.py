"""
Advanced Reasoning with Agenkit

Learn Chain-of-Thought, Tree-of-Thought, and Self-Consistency techniques.
Run with: marimo edit 03-advanced-reasoning.py

This Marimo notebook demonstrates reactive execution with interactive parameter tuning.
"""

import marimo

__generated_with = "0.9.0"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo
    return mo,


@app.cell
def __(mo):
    mo.md(
        """
        # Advanced Reasoning with Agenkit 🧠

        Unlock powerful reasoning techniques to make your agents smarter and more reliable.

        ## What You'll Learn

        1. **Chain-of-Thought (CoT)** - Step-by-step reasoning
        2. **Tree-of-Thought (ToT)** - Explore multiple paths
        3. **Self-Consistency** - Voting for reliability
        4. **Comparison** - When to use each technique
        5. **Interactive Tuning** - Adjust parameters and see results

        🎯 **Marimo Features**: Adjust sliders and see reasoning update in real-time!
        """
    )
    return


@app.cell
def __():
    # Setup
    import agenkit
    from agenkit import Agent, Message
    from agenkit.techniques.reasoning import ChainOfThought, TreeOfThought, SelfConsistency
    import asyncio
    import time

    print(f"✅ Agenkit version: {agenkit.__version__}")
    return Agent, ChainOfThought, Message, SelfConsistency, TreeOfThought, agenkit, asyncio, time


@app.cell
def __(Agent, Message):
    # Mock LLM for demonstrations
    class MockLLM:
        """Mock LLM that demonstrates reasoning techniques."""

        def __init__(self, vary_responses=False):
            self.vary_responses = vary_responses
            self.call_count = 0

        async def complete(self, prompt: str) -> str:
            """Return mock response."""
            self.call_count += 1

            if "15 * 24" in prompt or "15*24" in prompt or "math" in prompt.lower():
                # Math problem responses
                if self.vary_responses and self.call_count % 3 == 0:
                    return """Step 1: Use (15 * 20) + (15 * 4)
Step 2: 15 * 20 = 300
Step 3: 15 * 4 = 60
Step 4: 300 + 60 = 360
Therefore, 15 * 24 = 360"""
                else:
                    return """Let me solve this step by step:

1. First, I'll break down 24 into 20 + 4
2. Multiply 15 × 20 = 300
3. Multiply 15 × 4 = 60
4. Add the results: 300 + 60 = 360

Therefore, 15 × 24 = 360"""

            elif "alternative" in prompt.lower() or "branches" in prompt.lower():
                # ToT branching responses
                responses = [
                    "Approach 1: Break into subproblems and solve iteratively",
                    "Approach 2: Identify patterns and apply known solutions",
                    "Approach 3: Work backwards from the goal",
                ]
                return responses[self.call_count % len(responses)]

            return "Let me think through this carefully..."

    print("✅ Created MockLLM")
    return MockLLM,


@app.cell
def __(mo):
    mo.md("## 1. Chain-of-Thought (CoT): Step-by-Step Reasoning")
    return


@app.cell
def __(mo):
    # Interactive query input
    cot_query = mo.ui.text(
        placeholder="Enter a question or problem...",
        value="What is 15 * 24?",
        label="Query for Chain-of-Thought:"
    )
    cot_query
    return cot_query,


@app.cell
async def __(ChainOfThought, Message, MockLLM, cot_query, mo):
    # Reactive Chain-of-Thought processing
    if cot_query.value:
        cot_agent = ChainOfThought(llm=MockLLM())
        cot_response = await cot_agent.process(Message(role="user", content=cot_query.value))

        cot_result = mo.md(f"""
        **🔍 Chain-of-Thought Result:**

        **Response:**
        ```
        {cot_response.content}
        ```

        **Metadata:**
        - Reasoning steps: {cot_response.metadata['num_steps']}
        - Technique: {cot_response.metadata['technique']}

        **Extracted Steps:**
        {chr(10).join(f"{i}. {step}" for i, step in enumerate(cot_response.metadata['reasoning_steps'], 1))}
        """)
    else:
        cot_result = mo.md("*Enter a query to see Chain-of-Thought reasoning*")

    cot_result
    return cot_agent, cot_response, cot_result


@app.cell
def __(mo):
    mo.md(
        """
        ## 2. Tree-of-Thought (ToT): Explore Multiple Paths

        Adjust parameters to control exploration:
        """
    )
    return


@app.cell
def __(mo):
    # Interactive ToT configuration
    tot_config = mo.md(
        """
        **Configure Tree-of-Thought** (adjust and see results update):
        {branching_factor}
        {max_depth}
        {search_strategy}
        """
    ).batch(
        branching_factor=mo.ui.slider(2, 5, value=3, label="Branching Factor"),
        max_depth=mo.ui.slider(1, 4, value=2, label="Max Depth"),
        search_strategy=mo.ui.dropdown(
            options={
                "best-first": "Best-First (recommended)",
                "bfs": "Breadth-First Search",
                "dfs": "Depth-First Search"
            },
            value="best-first",
            label="Search Strategy:"
        )
    )
    tot_config
    return tot_config,


@app.cell
def __(mo):
    # Query for ToT
    tot_query = mo.ui.text(
        placeholder="Enter a planning or design problem...",
        value="Design a strategy for optimizing database queries",
        label="Query for Tree-of-Thought:"
    )
    tot_query
    return tot_query,


@app.cell
async def __(Message, MockLLM, TreeOfThought, mo, tot_config, tot_query):
    # Simple evaluator for ToT
    def simple_evaluator(text: str) -> float:
        """Evaluate reasoning quality (0.0-1.0)."""
        score = 0.0
        score += min(len(text) / 300, 0.4)
        if any(marker in text for marker in ["1.", "Step", "-"]):
            score += 0.3
        keywords = ["approach", "solution", "consider", "therefore"]
        score += sum(0.1 for kw in keywords if kw.lower() in text.lower())
        return min(score, 1.0)

    # Reactive Tree-of-Thought processing
    if tot_query.value:
        tot_agent = TreeOfThought(
            llm=MockLLM(),
            branching_factor=tot_config.value["branching_factor"],
            max_depth=tot_config.value["max_depth"],
            evaluator=simple_evaluator,
            strategy=tot_config.value["search_strategy"]
        )

        tot_response = await tot_agent.process(Message(role="user", content=tot_query.value))
        stats = tot_response.metadata['reasoning_tree_stats']

        tot_result = mo.md(f"""
        **🌳 Tree-of-Thought Result:**

        **Configuration:**
        - Branching factor: {tot_config.value["branching_factor"]}
        - Max depth: {tot_config.value["max_depth"]}
        - Strategy: {tot_config.value["search_strategy"]}

        **Best Path (Score: {tot_response.metadata['best_score']:.2f}):**
        {chr(10).join(f"{i}. {step}" for i, step in enumerate(tot_response.metadata['reasoning_path'], 1))}

        **Tree Statistics:**
        - Total nodes explored: {stats['total_nodes']}
        - Max depth reached: {stats['max_depth']}
        - Leaf nodes: {stats['num_leaves']}
        - Pruned nodes: {stats['num_pruned']}

        💡 **Try adjusting** branching factor or depth to see how exploration changes!
        """)
    else:
        tot_result = mo.md("*Enter a query to see Tree-of-Thought exploration*")

    tot_result
    return simple_evaluator, stats, tot_agent, tot_response, tot_result


@app.cell
def __(mo):
    mo.md(
        """
        ## 3. Self-Consistency: Voting for Reliability

        Generate multiple samples and vote for consensus:
        """
    )
    return


@app.cell
def __(mo):
    # Interactive Self-Consistency configuration
    sc_config = mo.md(
        """
        **Configure Self-Consistency** (adjust to see consensus change):
        {num_samples}
        {voting_strategy}
        """
    ).batch(
        num_samples=mo.ui.slider(3, 10, value=5, label="Number of Samples"),
        voting_strategy=mo.ui.dropdown(
            options={
                "majority": "Majority Voting (recommended)",
                "weighted": "Weighted Voting",
                "first": "First Sample (baseline)"
            },
            value="majority",
            label="Voting Strategy:"
        )
    )
    sc_config
    return sc_config,


@app.cell
def __(mo):
    # Query for Self-Consistency
    sc_query = mo.ui.text(
        placeholder="Enter a question with objective answer...",
        value="What is 15 * 24?",
        label="Query for Self-Consistency:"
    )
    sc_query
    return sc_query,


@app.cell
async def __(ChainOfThought, Message, MockLLM, SelfConsistency, mo, sc_config, sc_query):
    # Reactive Self-Consistency processing
    if sc_query.value:
        sc_base = ChainOfThought(llm=MockLLM(vary_responses=True))
        sc_agent = SelfConsistency(
            agent=sc_base,
            num_samples=sc_config.value["num_samples"],
            voting_strategy=sc_config.value["voting_strategy"]
        )

        sc_response = await sc_agent.process(Message(role="user", content=sc_query.value))

        sc_result = mo.md(f"""
        **🗳️  Self-Consistency Result:**

        **Configuration:**
        - Samples: {sc_config.value["num_samples"]}
        - Strategy: {sc_config.value["voting_strategy"]}

        **Consensus Answer:** {sc_response.content}

        **Consistency Metrics:**
        - Consistency score: {sc_response.metadata['consistency_score']:.2%}
        - Base agent: {sc_response.metadata['base_agent']}

        **Answer Distribution:**
        {chr(10).join(f"- '{ans}': {count} votes" for ans, count in sc_response.metadata['answer_counts'].items())}

        💡 **Higher consistency score** = more agreement = higher confidence
        """)
    else:
        sc_result = mo.md("*Enter a query to see Self-Consistency voting*")

    sc_result
    return sc_agent, sc_base, sc_response, sc_result


@app.cell
def __(mo):
    mo.md("## 4. Technique Comparison")
    return


@app.cell
def __(mo):
    # Comparison query
    comparison_query = mo.ui.text(
        placeholder="Enter problem to compare techniques...",
        value="What is 15 * 24?",
        label="Query for comparison:"
    )
    comparison_query
    return comparison_query,


@app.cell
def __(mo):
    # Button to trigger comparison
    compare_btn = mo.ui.button(
        label="🔬 Run Comparison",
        on_click=lambda: "clicked"
    )
    compare_btn
    return compare_btn,


@app.cell
async def __(ChainOfThought, Message, MockLLM, SelfConsistency, TreeOfThought, compare_btn, comparison_query, mo, simple_evaluator, time):
    # Reactive comparison (runs when button clicked)
    if compare_btn.value and comparison_query.value:
        message = Message(role="user", content=comparison_query.value)

        # Chain-of-Thought
        start = time.time()
        cot_comp = await ChainOfThought(llm=MockLLM()).process(message)
        cot_time = time.time() - start

        # Tree-of-Thought
        start = time.time()
        tot_comp = await TreeOfThought(
            llm=MockLLM(),
            branching_factor=2,
            max_depth=2,
            evaluator=simple_evaluator
        ).process(message)
        tot_time = time.time() - start
        tot_stats = tot_comp.metadata['reasoning_tree_stats']

        # Self-Consistency
        start = time.time()
        sc_comp = await SelfConsistency(
            agent=ChainOfThought(llm=MockLLM(vary_responses=True)),
            num_samples=5
        ).process(message)
        sc_time = time.time() - start

        comparison_result = mo.md(f"""
        **📊 Technique Comparison**

        **Query:** {comparison_query.value}

        ---

        **🔗 Chain-of-Thought:**
        - Steps: {cot_comp.metadata['num_steps']}
        - Time: {cot_time:.3f}s
        - Cost: 1 LLM call
        - Best for: Fast, straightforward reasoning

        **🌳 Tree-of-Thought:**
        - Nodes explored: {tot_stats['total_nodes']}
        - Best path score: {tot_comp.metadata['best_score']:.2f}
        - Time: {tot_time:.3f}s
        - Cost: {tot_stats['total_nodes']} LLM calls
        - Best for: Creative tasks, planning

        **🗳️  Self-Consistency:**
        - Consensus: {sc_comp.content}
        - Confidence: {sc_comp.metadata['consistency_score']:.2%}
        - Time: {sc_time:.3f}s
        - Cost: {sc_comp.metadata['num_samples']} LLM calls
        - Best for: High-reliability decisions

        ---

        **💡 Decision Matrix:**
        - **Fast response needed?** → Chain-of-Thought
        - **Creative/planning task?** → Tree-of-Thought
        - **Critical decision?** → Self-Consistency
        - **Maximum quality?** → Combine ToT + SC
        """)
    else:
        comparison_result = mo.md("*Click button to compare techniques*")

    comparison_result
    return comparison_result, cot_comp, cot_time, message, sc_comp, sc_time, start, tot_comp, tot_stats, tot_time


@app.cell
def __(mo):
    mo.md(
        """
        ## 5. When to Use Each Technique

        **Decision Matrix:**

        | Scenario | Recommended | Why |
        |----------|------------|-----|
        | Math problems | Self-Consistency + CoT | Objective answer, high accuracy |
        | Creative writing | Tree-of-Thought | Explore alternatives |
        | Planning | Tree-of-Thought | Evaluate strategies |
        | Q&A | Chain-of-Thought | Fast, transparent |
        | Critical decisions | Self-Consistency + ToT | Maximum reliability |
        | Code debugging | Chain-of-Thought | Step-by-step analysis |
        | Fast responses | Chain-of-Thought | Single pass |
        """
    )
    return


@app.cell
def __(mo):
    mo.md(
        """
        ## 6. Cost-Quality Trade-offs

        **Interactive Visualization:**
        """
    )
    return


@app.cell
def __(mo):
    # Interactive cost-quality slider
    quality_slider = mo.ui.slider(
        start=1,
        stop=10,
        step=1,
        value=5,
        label="Quality Level (1=Fast, 10=Best):"
    )
    quality_slider
    return quality_slider,


@app.cell
def __(mo, quality_slider):
    # Reactive recommendation based on quality level
    quality_level = quality_slider.value

    if quality_level <= 3:
        recommendation = """
        **Low Cost, Fast (Quality Level {}):**

        ✓ **Chain-of-Thought**
        - 1 LLM call
        - ~0.1s response time
        - Good for: High volume, real-time apps
        - Cost: $
        """.format(quality_level)
    elif quality_level <= 7:
        recommendation = """
        **Medium Cost, Better Quality (Quality Level {}):**

        ✓ **Self-Consistency (3-5 samples)**
        - 3-5 LLM calls
        - ~0.5s response time
        - Good for: Important decisions
        - Cost: $$$
        """.format(quality_level)
    else:
        recommendation = """
        **High Cost, Highest Quality (Quality Level {}):**

        ✓ **Tree-of-Thought + Self-Consistency**
        - Many LLM calls (branching × samples)
        - ~2-5s response time
        - Good for: Critical, complex problems
        - Cost: $$$$$
        """.format(quality_level)

    mo.md(recommendation)
    return quality_level, recommendation


@app.cell
def __(mo):
    mo.md(
        """
        ## Summary

        You've mastered advanced reasoning with **interactive controls**! 🎉

        ✅ **Chain-of-Thought** - Adjusted queries and saw step-by-step reasoning
        ✅ **Tree-of-Thought** - Tuned branching/depth and explored alternatives
        ✅ **Self-Consistency** - Configured voting and saw consensus
        ✅ **Comparison** - Ran side-by-side analysis
        ✅ **Trade-offs** - Understood cost-quality spectrum

        ## Marimo Advantages Demonstrated

        1. **Reactive Execution** - Parameter changes update results automatically
        2. **Interactive UI** - Sliders, dropdowns, buttons for live tuning
        3. **Real-time Feedback** - See reasoning quality as you adjust
        4. **No Hidden State** - Deterministic, reproducible experiments

        ## Next Steps

        - **[Jupyter Version](03-advanced-reasoning.ipynb)** - Traditional notebook format
        - **[Deployment Guide](../docs/deployment.md)** - Deploy reasoning agents
        - **[Evaluation Framework](../docs/evaluation.md)** - Measure quality
        - **[Advanced Examples](https://github.com/scttfrdmn/agenkit/tree/main/examples/techniques/reasoning)** - More patterns

        ## Quick Reference

        ```python
        # Chain-of-Thought
        cot = ChainOfThought(llm=my_llm)

        # Tree-of-Thought
        tot = TreeOfThought(
            llm=my_llm,
            branching_factor=3,
            max_depth=3,
            strategy="best-first"
        )

        # Self-Consistency
        sc = SelfConsistency(
            agent=cot,
            num_samples=5,
            voting_strategy="majority"
        )
        ```

        Ready to build intelligent reasoning systems! 🧠🚀
        """
    )
    return


if __name__ == "__main__":
    app.run()
