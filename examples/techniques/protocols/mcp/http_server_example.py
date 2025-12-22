#!/usr/bin/env python3
"""
MCP HTTP Server Example

Demonstrates running an MCP server over HTTP for web-based integrations.

Unlike the stdio transport (used by Claude Desktop), HTTP transport
allows remote clients to connect via HTTP POST requests.

Usage:
    python http_server_example.py

Then test with:
    curl -X POST http://localhost:3000/mcp \
      -H "Content-Type: application/json" \
      -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1.0"}}'

Requirements:
    pip install agenkit aiohttp
"""

import asyncio

from agenkit.techniques.protocols.mcp import MCPServer


async def main():
    """Run HTTP MCP server."""

    # Create MCP server
    server = MCPServer(
        name="http-example",
        version="1.0",
        capabilities={
            "resources": True,
            "tools": True
        }
    )

    # Register resources
    @server.resource(
        uri="system://info",
        name="System Information",
        description="Get system information",
        mime_type="application/json"
    )
    async def get_system_info(params):
        """Get system information."""
        import platform

        import psutil  # type: ignore

        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2)
        }

    @server.resource(
        uri="api://status",
        name="API Status",
        description="Get API server status",
        mime_type="application/json"
    )
    async def get_status(params):
        """Get API status."""
        from datetime import datetime

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": server.version,
            "uptime_seconds": 0  # Would track actual uptime in production
        }

    @server.resource(
        uri="config://settings",
        name="Configuration Settings",
        description="Get configuration settings",
        mime_type="application/json"
    )
    async def get_settings(params):
        """Get configuration settings."""
        return {
            "environment": "development",
            "log_level": "info",
            "features": {
                "authentication": True,
                "caching": True,
                "rate_limiting": False
            },
            "limits": {
                "max_request_size_mb": 10,
                "max_connections": 1000,
                "timeout_seconds": 30
            }
        }

    # Register tools
    @server.tool(
        name="ping",
        description="Ping a host to check connectivity",
        input_schema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Hostname or IP address to ping"
                },
                "count": {
                    "type": "number",
                    "description": "Number of ping packets",
                    "default": 4
                }
            },
            "required": ["host"]
        }
    )
    async def ping_host(params):
        """Ping a host."""
        import subprocess

        host = params["host"]
        count = params.get("count", 4)

        try:
            # Simple ping command (works on Unix-like systems)
            result = subprocess.run(  # noqa: ASYNC221, S603 - Example MCP tool demonstrating process execution
                ["ping", "-c", str(count), host],  # noqa: S607 - Standard ping utility for example
                check=False, capture_output=True,
                text=True,
                timeout=10
            )

            return {
                "host": host,
                "reachable": result.returncode == 0,
                "packets_sent": count,
                "output": result.stdout if result.returncode == 0 else result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "host": host,
                "reachable": False,
                "error": "Ping timeout"
            }
        except Exception as e:
            return {
                "host": host,
                "reachable": False,
                "error": str(e)
            }

    @server.tool(
        name="validate_email",
        description="Validate an email address format",
        input_schema={
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Email address to validate"
                }
            },
            "required": ["email"]
        }
    )
    async def validate_email(params):
        """Validate email format."""
        import re

        email = params["email"]
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        is_valid = bool(re.match(pattern, email))

        return {
            "email": email,
            "valid": is_valid,
            "reason": "Valid format" if is_valid else "Invalid email format"
        }

    @server.tool(
        name="generate_uuid",
        description="Generate a UUID (v4)",
        input_schema={
            "type": "object",
            "properties": {
                "count": {
                    "type": "number",
                    "description": "Number of UUIDs to generate",
                    "default": 1
                }
            }
        }
    )
    async def generate_uuid(params):
        """Generate UUIDs."""
        import uuid

        count = params.get("count", 1)
        uuids = [str(uuid.uuid4()) for _ in range(count)]

        return {
            "count": count,
            "uuids": uuids
        }

    # Print server info
    print("=" * 60)
    print("MCP HTTP Server Example")
    print("=" * 60)
    print(f"Server: {server.name} v{server.version}")
    print(f"Resources: {len(server.resources)}")
    print(f"Tools: {len(server.tools)}")
    print()
    print("Server starting on http://localhost:3000/mcp")
    print()
    print("Test with curl:")
    print("  curl -X POST http://localhost:3000/mcp \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"jsonrpc\": \"2.0\", \"id\": 1, \"method\": \"initialize\", \"params\": {\"protocolVersion\": \"1.0\"}}'")
    print()
    print("=" * 60)

    # Start HTTP server
    try:
        await server.start(transport="http", host="localhost", port=3000)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
