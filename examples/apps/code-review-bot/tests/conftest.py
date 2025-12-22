"""Pytest configuration and fixtures."""


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires services)"
    )
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
