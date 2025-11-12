"""Tests for parse_endpoint with gRPC URLs."""

import pytest

from agenkit.adapters.python.grpc_transport import GRPCTransport
from agenkit.adapters.python.transport import parse_endpoint


class TestParseEndpointGRPC:
    """Tests for parse_endpoint with gRPC URLs."""

    def test_parse_grpc_url(self):
        """Test parsing gRPC URL."""
        transport = parse_endpoint("grpc://localhost:50051")
        assert isinstance(transport, GRPCTransport)
        assert transport._host == "localhost"
        assert transport._port == 50051

    def test_parse_grpc_url_default_port(self):
        """Test parsing gRPC URL with default port."""
        transport = parse_endpoint("grpc://example.com")
        assert isinstance(transport, GRPCTransport)
        assert transport._host == "example.com"
        assert transport._port == 50051

    def test_parse_grpc_url_custom_port(self):
        """Test parsing gRPC URL with custom port."""
        transport = parse_endpoint("grpc://api.example.com:9090")
        assert isinstance(transport, GRPCTransport)
        assert transport._host == "api.example.com"
        assert transport._port == 9090
