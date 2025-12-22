"""Pytest configuration for customer support tests."""


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests requiring services")
    config.addinivalue_line("markers", "e2e: End-to-end tests requiring full stack")
