"""
Production Patterns with Agenkit

Learn middleware, observability, error handling, and production-ready patterns.
Run with: marimo edit 02-production-patterns.py

This Marimo notebook demonstrates reactive execution and interactive UI elements.
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
        # Production Patterns with Agenkit

        Building production-ready AI agent systems requires more than just functional agents.

        ## What You'll Learn

        1. **Middleware** - Retry logic, circuit breakers, rate limiting
        2. **Observability** - Tracing, metrics, logging
        3. **Error Handling** - Graceful degradation and recovery
        4. **Performance** - Caching, batching, optimization
        5. **Testing** - Unit tests, integration tests, mocks

        🎯 **Marimo Features**: This notebook is reactive - adjust sliders and see results update automatically!
        """
    )
    return


@app.cell
def __():
    # Setup
    import agenkit
    from agenkit import Agent, Message
    import asyncio
    import time
    from datetime import datetime

    print(f"✅ Agenkit version: {agenkit.__version__}")
    return Agent, Message, agenkit, asyncio, datetime, time


@app.cell
def __(mo):
    mo.md("## 1. Middleware: Building Robust Agents")
    return


@app.cell
def __(mo):
    # Interactive configuration for retry middleware
    retry_config = mo.md(
        """
        **Configure Retry Behavior** (adjust sliders to see changes):
        {max_retries}
        {backoff_factor}
        """
    ).batch(
        max_retries=mo.ui.slider(1, 10, value=3, label="Max Retries"),
        backoff_factor=mo.ui.slider(0.5, 5.0, step=0.5, value=2.0, label="Backoff Factor")
    )
    retry_config
    return retry_config,


@app.cell
def __(Agent, Message, retry_config):
    from agenkit.middleware import RetryMiddleware

    # Create agent that fails based on retry config
    class UnreliableAgent(Agent):
        def __init__(self, max_retries):
            self.attempt = 0
            self.required_attempts = max_retries

        def name(self) -> str:
            return "unreliable-agent"

        async def process(self, message: Message) -> Message:
            self.attempt += 1

            if self.attempt < self.required_attempts:
                raise Exception(f"Simulated failure (attempt {self.attempt}/{self.required_attempts})")

            return Message(
                role="assistant",
                content=f"✅ Success on attempt {self.attempt}!",
                metadata={"attempts": self.attempt}
            )

    # Reactively create agent with current config
    unreliable = UnreliableAgent(retry_config.value["max_retries"])
    retry_agent = RetryMiddleware(
        agent=unreliable,
        max_retries=retry_config.value["max_retries"],
        backoff_factor=retry_config.value["backoff_factor"]
    )

    config_summary = mo.md(f"""
    **Current Configuration:**
    - Max retries: {retry_config.value["max_retries"]}
    - Backoff factor: {retry_config.value["backoff_factor"]}x
    - Total max time: ~{retry_config.value["backoff_factor"] * (2**retry_config.value["max_retries"] - 1):.1f}s
    """)
    config_summary
    return (
        RetryMiddleware,
        UnreliableAgent,
        config_summary,
        retry_agent,
        unreliable,
    )


@app.cell
async def __(Message, mo, retry_agent, time):
    # Test retry behavior (reactive - updates when config changes!)
    start = time.time()
    try:
        result = await retry_agent.process(Message(role="user", content="test"))
        duration = time.time() - start

        retry_result = mo.md(f"""
        **Result:**
        - {result.content}
        - Total time: {duration:.2f}s
        - Attempts: {result.metadata.get('attempts', 1)}
        """)
    except Exception as e:
        duration = time.time() - start
        retry_result = mo.md(f"""
        **Result:**
        - ❌ Failed after all retries
        - Total time: {duration:.2f}s
        - Error: {str(e)}
        """)

    retry_result
    return duration, result, retry_result, start


@app.cell
def __(mo):
    mo.md("### Circuit Breaker: Interactive Demo")
    return


@app.cell
def __(mo):
    # Interactive failure simulation
    failure_selector = mo.ui.dropdown(
        options={
            "success": "All succeed",
            "partial": "Some fail",
            "all_fail": "All fail"
        },
        value="partial",
        label="Failure scenario:"
    )
    failure_selector
    return failure_selector,


@app.cell
def __(Agent, Message, failure_selector):
    from agenkit.middleware import CircuitBreakerMiddleware

    class ConfigurableAgent(Agent):
        def __init__(self, scenario):
            self.scenario = scenario
            self.call_count = 0

        def name(self) -> str:
            return "configurable-agent"

        async def process(self, message: Message) -> Message:
            self.call_count += 1

            if self.scenario == "all_fail":
                raise Exception("Configured to always fail")
            elif self.scenario == "partial" and self.call_count % 2 == 0:
                raise Exception(f"Configured partial failure (call {self.call_count})")

            return Message(
                role="assistant",
                content=f"Success (call {self.call_count})"
            )

    # Reactively create circuit breaker with selected scenario
    configurable = ConfigurableAgent(failure_selector.value)
    circuit_breaker = CircuitBreakerMiddleware(
        agent=configurable,
        failure_threshold=3,
        recovery_timeout=5.0
    )

    print(f"🔄 Circuit breaker configured for: {failure_selector.value}")
    return (
        CircuitBreakerMiddleware,
        ConfigurableAgent,
        circuit_breaker,
        configurable,
    )


@app.cell
def __(mo):
    mo.md("## 2. Performance Optimization")
    return


@app.cell
def __(mo):
    # Interactive cache TTL
    cache_ttl = mo.ui.slider(
        start=1,
        stop=60,
        step=5,
        value=10,
        label="Cache TTL (seconds):"
    )
    cache_ttl
    return cache_ttl,


@app.cell
def __(Agent, Message, asyncio, cache_ttl):
    from agenkit.middleware import CachingMiddleware

    class ExpensiveAgent(Agent):
        def __init__(self):
            self.call_count = 0

        def name(self) -> str:
            return "expensive-agent"

        async def process(self, message: Message) -> Message:
            self.call_count += 1
            # Simulate expensive operation
            await asyncio.sleep(0.5)

            return Message(
                role="assistant",
                content=f"Result (call #{self.call_count})",
                metadata={"cached": False, "call_count": self.call_count}
            )

    # Reactively create cache with current TTL
    expensive = ExpensiveAgent()
    cached_agent = CachingMiddleware(
        agent=expensive,
        ttl=cache_ttl.value
    )

    print(f"💾 Cache configured with {cache_ttl.value}s TTL")
    return CachingMiddleware, ExpensiveAgent, cached_agent, expensive


@app.cell
def __(mo):
    # Button to trigger cache test
    test_cache_btn = mo.ui.button(
        label="Test Cache Performance",
        on_click=lambda: "clicked"
    )
    test_cache_btn
    return test_cache_btn,


@app.cell
async def __(Message, cached_agent, mo, test_cache_btn, time):
    # Reactive cache test (runs when button clicked)
    if test_cache_btn.value:
        msg = Message(role="user", content="test query")

        # First call (cache miss)
        start = time.time()
        result1 = await cached_agent.process(msg)
        duration1 = time.time() - start

        # Second call (cache hit)
        start = time.time()
        result2 = await cached_agent.process(msg)
        duration2 = time.time() - start

        cache_results = mo.md(f"""
        **Cache Performance:**
        - First call (miss): {duration1:.3f}s - {result1.content}
        - Second call (hit): {duration2:.3f}s - {result2.content}
        - **Speedup: {duration1/duration2:.1f}x faster** 🚀
        """)
    else:
        cache_results = mo.md("*Click button to test cache*")

    cache_results
    return cache_results, duration1, duration2, msg, result1, result2, start


@app.cell
def __(mo):
    mo.md("## 3. Observability: Real-time Metrics")
    return


@app.cell
def __():
    # Simulated metrics storage
    metrics_history = []
    return metrics_history,


@app.cell
def __(mo):
    # Control panel for metric collection
    metric_controls = mo.md(
        """
        **Metric Collection Controls:**
        {collect_metrics}
        {sample_rate}
        """
    ).batch(
        collect_metrics=mo.ui.switch(value=True, label="Collect Metrics"),
        sample_rate=mo.ui.slider(1, 100, value=100, label="Sample Rate (%)")
    )
    metric_controls
    return metric_controls,


@app.cell
def __(Agent, Message, asyncio, metric_controls, metrics_history, time):
    class MeteredAgent(Agent):
        def name(self) -> str:
            return "metered-agent"

        async def process(self, message: Message) -> Message:
            start = time.time()

            # Simulate variable work
            await asyncio.sleep(0.05 + (len(message.content) * 0.01))

            duration = time.time() - start

            # Conditionally collect metrics based on UI
            if metric_controls.value["collect_metrics"]:
                import random
                if random.randint(1, 100) <= metric_controls.value["sample_rate"]:
                    metrics_history.append({
                        "timestamp": time.time(),
                        "duration_ms": duration * 1000,
                        "message_length": len(message.content)
                    })

            return Message(
                role="assistant",
                content=f"Processed {len(message.content)} chars in {duration*1000:.1f}ms",
                metadata={"duration_ms": duration * 1000}
            )

    metered_agent = MeteredAgent()

    status = "🟢 Active" if metric_controls.value["collect_metrics"] else "🔴 Disabled"
    print(f"Metrics: {status} | Sample rate: {metric_controls.value['sample_rate']}%")
    return metered_agent, status


@app.cell
def __(mo):
    # Input for testing metered agent
    test_input = mo.ui.text(
        placeholder="Type something to process...",
        value="Hello from Marimo!",
        label="Test message:"
    )
    test_input
    return test_input,


@app.cell
async def __(Message, metered_agent, metrics_history, mo, test_input):
    # Reactive processing (updates when input changes!)
    if test_input.value:
        result = await metered_agent.process(
            Message(role="user", content=test_input.value)
        )

        # Show recent metrics
        recent_metrics = metrics_history[-5:] if metrics_history else []
        avg_duration = sum(m["duration_ms"] for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0

        metrics_display = mo.md(f"""
        **Processing Result:**
        - {result.content}

        **Recent Metrics** (last 5 samples):
        - Average duration: {avg_duration:.2f}ms
        - Total samples: {len(metrics_history)}
        - Latest: {recent_metrics[-1]["duration_ms"]:.2f}ms if recent_metrics else "N/A"}
        """)
    else:
        metrics_display = mo.md("*Type something to see metrics*")

    metrics_display
    return avg_duration, metrics_display, recent_metrics, result


@app.cell
def __(mo):
    mo.md(
        """
        ## 4. Testing: Interactive Test Suite

        Run tests and see results in real-time:
        """
    )
    return


@app.cell
def __(mo):
    test_selector = mo.ui.multiselect(
        options={
            "basic": "Basic functionality",
            "error": "Error handling",
            "performance": "Performance",
            "integration": "Integration"
        },
        value=["basic", "error"],
        label="Select tests to run:"
    )
    test_selector
    return test_selector,


@app.cell
async def __(Agent, Message, mo, test_selector):
    # Reactive test execution
    test_results = []

    if "basic" in test_selector.value:
        class TestAgent(Agent):
            def name(self) -> str:
                return "test-agent"

            async def process(self, message: Message) -> Message:
                return Message(role="assistant", content=f"Echo: {message.content}")

        agent = TestAgent()
        try:
            result = await agent.process(Message(role="user", content="test"))
            assert result.role == "assistant"
            assert "test" in result.content
            test_results.append("✅ Basic tests passed")
        except AssertionError:
            test_results.append("❌ Basic tests failed")

    if "error" in test_selector.value:
        try:
            # Test error handling
            class ErrorAgent(Agent):
                def name(self) -> str:
                    return "error-agent"

                async def process(self, message: Message) -> Message:
                    if "error" in message.content:
                        raise ValueError("Test error")
                    return Message(role="assistant", content="OK")

            error_agent = ErrorAgent()
            try:
                await error_agent.process(Message(role="user", content="trigger error"))
                test_results.append("❌ Error test failed - should have raised")
            except ValueError:
                test_results.append("✅ Error handling passed")
        except Exception as e:
            test_results.append(f"❌ Error test failed: {e}")

    if "performance" in test_selector.value:
        import time
        start = time.time()
        # Simulate performance test
        await asyncio.sleep(0.01)
        duration = time.time() - start
        if duration < 0.1:
            test_results.append(f"✅ Performance test passed ({duration*1000:.1f}ms)")
        else:
            test_results.append(f"⚠️ Performance test slow ({duration*1000:.1f}ms)")

    if "integration" in test_selector.value:
        # Simulate integration test
        test_results.append("✅ Integration test passed")

    test_summary = mo.md(f"""
    **Test Results** ({len(test_selector.value)} suites):

    {chr(10).join(f"- {r}" for r in test_results)}

    *Select different tests above to run them!*
    """)
    test_summary
    return (
        ErrorAgent,
        TestAgent,
        agent,
        duration,
        error_agent,
        result,
        start,
        test_results,
        test_summary,
    )


@app.cell
def __(mo):
    mo.md(
        """
        ## Summary

        You've learned production patterns with **interactive controls**:

        ✅ **Middleware** - Adjusted retry config and saw real-time results
        ✅ **Caching** - Tested performance with configurable TTL
        ✅ **Observability** - Collected metrics with sampling control
        ✅ **Testing** - Ran selective test suites interactively

        ## Marimo Advantages Demonstrated

        1. **Reactive Execution** - Cells update automatically when you change sliders
        2. **Interactive UI** - Sliders, dropdowns, buttons, text inputs
        3. **No Hidden State** - Deterministic execution order
        4. **Real-time Feedback** - See results immediately as you adjust parameters

        ## Next Steps

        - **[Tutorial 03: Advanced Reasoning](03-advanced-reasoning.py)** - CoT, ToT, self-consistency
        - **[Jupyter Version](02-production-patterns.ipynb)** - Traditional notebook format
        - **[Deployment Guide](../docs/deployment.md)** - Production deployment

        Ready for advanced patterns! 🚀
        """
    )
    return


if __name__ == "__main__":
    app.run()
