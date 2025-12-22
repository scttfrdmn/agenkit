#!/usr/bin/env python3
"""
MCP Client Example

Demonstrates how to connect to an MCP server and use its resources and tools.

This example shows:
1. Connecting to an MCP server
2. Listing available resources and tools
3. Fetching resource data
4. Calling tools

Usage:
    # Start the HTTP server example first:
    python http_server_example.py

    # Then run this client:
    python client_example.py --server http://localhost:3000/mcp

Requirements:
    pip install agenkit httpx
"""

import argparse
import asyncio

from agenkit.techniques.protocols.mcp import MCPClient


async def demonstrate_client(server_url: str):
    """
    Demonstrate MCP client capabilities.

    Args:
        server_url: URL of MCP server
    """
    print("=" * 60)
    print("MCP Client Example")
    print("=" * 60)
    print(f"Connecting to: {server_url}")
    print()

    # Create client
    client = MCPClient(server_url=server_url)

    try:
        # Step 1: Initialize connection
        print("1. Initializing connection...")
        server_info = await client.initialize()
        print(
            f"   ✓ Connected to {server_info['serverInfo']['name']} v{server_info['serverInfo']['version']}"
        )
        print(f"   Protocol version: {server_info.get('protocolVersion', 'unknown')}")
        print()

        # Step 2: List resources
        print("2. Listing resources...")
        resources = await client.list_resources()
        print(f"   ✓ Found {len(resources)} resources:")
        for resource in resources:
            print(f"      - {resource.name} ({resource.uri})")
            if resource.description:
                print(f"        {resource.description}")
        print()

        # Step 3: Read a resource
        if resources:
            print("3. Reading resource data...")
            resource_uri = resources[0].uri
            print(f"   Reading: {resource_uri}")

            data = await client.get_resource(resource_uri)
            print(f"   ✓ Data: {data[:200]}..." if len(str(data)) > 200 else f"   ✓ Data: {data}")
            print()

        # Step 4: List tools
        print("4. Listing tools...")
        tools = await client.list_tools()
        print(f"   ✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"      - {tool.name}: {tool.description}")
        print()

        # Step 5: Call a tool
        if tools:
            print("5. Calling tool...")

            # Find a suitable tool to call
            tool_to_call = None
            tool_params = {}

            for tool in tools:
                if tool.name == "validate_email":
                    tool_to_call = tool
                    tool_params = {"email": "test@example.com"}
                    break
                elif tool.name == "generate_uuid":
                    tool_to_call = tool
                    tool_params = {"count": 3}
                    break
                elif tool.name == "ping":
                    tool_to_call = tool
                    tool_params = {"host": "localhost", "count": 2}
                    break

            if tool_to_call:
                print(f"   Calling: {tool_to_call.name}")
                print(f"   Parameters: {tool_params}")

                result = await client.call_tool(tool_to_call.name, **tool_params)
                print(f"   ✓ Result: {result}")
            else:
                print("   No suitable tools found to demonstrate")
            print()

        # Step 6: Demonstrate error handling
        print("6. Error handling...")
        try:
            await client.get_resource("nonexistent://resource")
        except ValueError as e:
            print(f"   ✓ Caught expected error: {e}")
        print()

        print("=" * 60)
        print("Client demonstration completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await client.close()


async def interactive_client(server_url: str):
    """
    Interactive MCP client for manual testing.

    Args:
        server_url: URL of MCP server
    """
    print("=" * 60)
    print("MCP Interactive Client")
    print("=" * 60)
    print(f"Server: {server_url}")
    print()

    client = MCPClient(server_url=server_url)

    try:
        # Initialize
        print("Initializing...")
        server_info = await client.initialize()
        print(f"Connected to {server_info['serverInfo']['name']}")
        print()

        # List resources
        resources = await client.list_resources()
        print(f"Resources ({len(resources)}):")
        for i, resource in enumerate(resources, 1):
            print(f"  {i}. {resource.name} - {resource.uri}")
        print()

        # List tools
        tools = await client.list_tools()
        print(f"Tools ({len(tools)}):")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool.name} - {tool.description}")
        print()

        # Interactive loop
        print("Commands:")
        print("  resource <uri> - Read a resource")
        print("  tool <name> <json_params> - Call a tool")
        print("  list resources - List all resources")
        print("  list tools - List all tools")
        print("  quit - Exit")
        print()

        while True:
            try:
                command = input("> ").strip()

                if not command:
                    continue

                if command == "quit":
                    break

                elif command.startswith("resource "):
                    uri = command[9:].strip()
                    data = await client.get_resource(uri)
                    print(f"Result: {data}")

                elif command.startswith("tool "):
                    import json

                    parts = command[5:].split(maxsplit=1)
                    if len(parts) < 2:
                        print("Usage: tool <name> <json_params>")
                        continue

                    tool_name = parts[0]
                    params = json.loads(parts[1])

                    result = await client.call_tool(tool_name, **params)
                    print(f"Result: {result}")

                elif command == "list resources":
                    for resource in resources:
                        print(f"  {resource.name} - {resource.uri}")

                elif command == "list tools":
                    for tool in tools:
                        print(f"  {tool.name} - {tool.description}")

                else:
                    print("Unknown command")

            except Exception as e:
                print(f"Error: {e}")

    finally:
        await client.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MCP Client Example")
    parser.add_argument(
        "--server",
        default="http://localhost:3000/mcp",
        help="MCP server URL (default: http://localhost:3000/mcp)",
    )
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")

    args = parser.parse_args()

    if args.interactive:
        asyncio.run(interactive_client(args.server))
    else:
        asyncio.run(demonstrate_client(args.server))


if __name__ == "__main__":
    main()
