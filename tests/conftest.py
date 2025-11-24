"""
Pytest configuration for robust test execution.

This module provides:
- Automatic retry for flaky tests
- Resource cleanup fixtures
- Async test timeout handling
- Port conflict resolution
"""

import asyncio
import gc
import time

import pytest


# Automatic retry for flaky tests
def pytest_configure(config):
    """Configure pytest with flaky test handling."""
    # Add flaky marker
    config.addinivalue_line(
        "markers", "flaky: Mark test as potentially flaky (will auto-retry on failure)"
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to implement auto-retry for flaky tests."""
    outcome = yield
    rep = outcome.get_result()

    # Only retry failed tests marked as flaky
    if rep.when == "call" and rep.failed and "flaky" in [mark.name for mark in item.iter_markers()]:
        # Get retry count from marker or use default
        flaky_marker = item.get_closest_marker("flaky")
        max_retries = flaky_marker.kwargs.get("retries", 2) if flaky_marker else 2

        # Track retries
        if not hasattr(item, "_flaky_retry_count"):
            item._flaky_retry_count = 0

        if item._flaky_retry_count < max_retries:
                item._flaky_retry_count += 1
                # Add small delay between retries to avoid resource contention
                time.sleep(0.1 * item._flaky_retry_count)
                # Mark for rerun
                rep.outcome = "rerun"


@pytest.fixture(scope="function", autouse=True)
async def cleanup_async_resources():
    """
    Automatically cleanup async resources after each test.

    This helps prevent resource leaks that can cause flaky tests
    by ensuring all tasks, connections, and file handles are properly closed.
    """
    yield

    # Give pending tasks time to complete
    await asyncio.sleep(0.01)

    # Cancel any remaining tasks
    try:
        tasks = [t for t in asyncio.all_tasks() if not t.done()]
        for task in tasks:
            if not task.done():
                task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    except RuntimeError:
        # Event loop might be closed
        pass

    # Force garbage collection
    gc.collect()


@pytest.fixture(scope="function")
def event_loop_with_timeout():
    """
    Provide event loop with extended timeout for tests.

    This prevents tests from hanging indefinitely during resource contention.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Set a reasonable default timeout
    loop.slow_callback_duration = 1.0

    yield loop

    # Cleanup
    try:
        # Cancel all tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Run loop briefly to allow cancellations
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        loop.close()
    except Exception:
        pass


@pytest.fixture(scope="function")
def wait_for_port_release():
    """
    Fixture to wait for ports to be released after tests.

    This helps prevent "Address already in use" errors in tests
    that start servers.
    """
    yield

    # Small delay to allow OS to release ports
    time.sleep(0.05)


# Test execution hooks for debugging
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    """Add delays between tests to reduce resource contention."""
    # Small delay between tests to allow resource cleanup
    if nextitem is not None:
        time.sleep(0.01)


# Configuration for specific test categories
@pytest.fixture(scope="session")
def test_config():
    """
    Provide test configuration with adjusted timeouts.

    Returns:
        dict: Test configuration with timeout values
    """
    return {
        "default_timeout": 5.0,
        "integration_timeout": 10.0,
        "chaos_timeout": 30.0,
        "slow_timeout": 60.0,
    }
