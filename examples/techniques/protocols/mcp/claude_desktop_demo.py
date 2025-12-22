#!/usr/bin/env python3
"""
Claude Desktop MCP Demo

Demonstrates how to expose an Agenkit agent as an MCP server that
Claude Desktop can connect to and use.

This example creates a simple knowledge agent with access to user data
and exposes it via MCP protocol using stdio transport (required by Claude Desktop).

Setup Instructions:
1. Install dependencies:
   pip install agenkit

2. Test the server:
   python claude_desktop_demo.py

3. Configure Claude Desktop:
   Edit ~/.config/Claude/claude_desktop_config.json (Mac/Linux)
   or %APPDATA%/Claude/claude_desktop_config.json (Windows)

   Add this server configuration:
   {
     "mcpServers": {
       "agenkit-demo": {
         "command": "python",
         "args": ["/path/to/claude_desktop_demo.py"]
       }
     }
   }

4. Restart Claude Desktop

5. In Claude Desktop, you can now use the agent:
   "Use the agenkit-demo server to get user profile information"

Requirements:
    pip install agenkit asyncio
"""

import asyncio
import sys

from agenkit.techniques.protocols.mcp import MCPServer


async def main():
    """Run MCP server for Claude Desktop."""

    # Create MCP server
    server = MCPServer(
        name="agenkit-demo", version="1.0", capabilities={"resources": True, "tools": True}
    )

    # Register resources (data sources)
    @server.resource(
        uri="user://profile",
        name="User Profile",
        description="Get user profile information",
        mime_type="application/json",
    )
    async def get_user_profile(params):
        """Get user profile data."""
        user_id = params.get("user_id", "default")
        return {
            "user_id": user_id,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "role": "Developer",
            "joined": "2024-01-15",
        }

    @server.resource(
        uri="data://statistics",
        name="Usage Statistics",
        description="Get usage statistics",
        mime_type="application/json",
    )
    async def get_statistics(params):
        """Get usage statistics."""
        period = params.get("period", "week")
        return {
            "period": period,
            "requests": 1250,
            "tokens_used": 45000,
            "average_response_time": 1.2,
        }

    @server.resource(
        uri="docs://getting-started",
        name="Getting Started Guide",
        description="Agenkit getting started documentation",
        mime_type="text/markdown",
    )
    async def get_docs(params):
        """Get documentation."""
        return """# Agenkit Getting Started

## Installation
```bash
pip install agenkit
```

## Quick Example
```python
from agenkit import Agent, Message

class MyAgent(Agent):
    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=f"Echo: {message.content}"
        )
```

## Patterns
Agenkit provides 11 agent patterns:
1. Reflection - Self-improvement through critique
2. Agents-as-Tools - Hierarchical delegation
3. Sequential - Pipeline processing
4. Parallel - Concurrent execution
... and more!
"""

    # Register tools (actions)
    @server.tool(
        name="search_knowledge",
        description="Search the knowledge base for information",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "category": {
                    "type": "string",
                    "description": "Category to search in",
                    "enum": ["users", "docs", "statistics"],
                },
            },
            "required": ["query"],
        },
    )
    async def search_knowledge(params):
        """Search knowledge base."""
        query = params["query"]
        category = params.get("category", "all")

        # Simple mock search
        results = []

        if category in ["all", "users"]:
            results.append(
                {
                    "type": "user",
                    "title": "User Profile",
                    "content": "John Doe - Developer - john.doe@example.com",
                }
            )

        if category in ["all", "docs"]:
            results.append(
                {
                    "type": "documentation",
                    "title": "Agenkit Patterns",
                    "content": "11 agent patterns for building AI systems",
                }
            )

        if category in ["all", "statistics"]:
            results.append(
                {
                    "type": "statistics",
                    "title": "Usage Stats",
                    "content": "1250 requests, 45K tokens used this week",
                }
            )

        return {"query": query, "category": category, "results": results, "count": len(results)}

    @server.tool(
        name="calculate",
        description="Perform mathematical calculations",
        input_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate",
                }
            },
            "required": ["expression"],
        },
    )
    async def calculate(params):
        """Perform calculation using safe AST evaluation."""
        import ast
        import operator

        expression = params["expression"]

        # Safe operations mapping
        safe_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

        def safe_eval(node):
            """Safely evaluate a math expression AST node."""
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                left = safe_eval(node.left)
                right = safe_eval(node.right)
                op = safe_ops.get(type(node.op))
                if op is None:
                    raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
                return op(left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = safe_eval(node.operand)
                op = safe_ops.get(type(node.op))
                if op is None:
                    raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
                return op(operand)
            else:
                raise ValueError(f"Unsupported expression: {type(node).__name__}")

        try:
            tree = ast.parse(expression, mode="eval")
            result = safe_eval(tree.body)
            return {"expression": expression, "result": result, "success": True}
        except Exception as e:
            return {"expression": expression, "error": str(e), "success": False}

    @server.tool(
        name="format_data",
        description="Format data in various formats",
        input_schema={
            "type": "object",
            "properties": {
                "data": {"type": "object", "description": "Data to format"},
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["json", "markdown", "table"],
                },
            },
            "required": ["data", "format"],
        },
    )
    async def format_data(params):
        """Format data."""
        data = params["data"]
        format_type = params["format"]

        if format_type == "json":
            import json

            return json.dumps(data, indent=2)

        elif format_type == "markdown":
            lines = ["# Data\n"]
            for key, value in data.items():
                lines.append(f"- **{key}**: {value}")
            return "\n".join(lines)

        elif format_type == "table":
            lines = ["| Key | Value |", "|-----|-------|"]
            for key, value in data.items():
                lines.append(f"| {key} | {value} |")
            return "\n".join(lines)

        return str(data)

    # Log server info to stderr (won't interfere with stdio protocol)
    sys.stderr.write("=" * 60 + "\n")
    sys.stderr.write("Agenkit MCP Server for Claude Desktop\n")
    sys.stderr.write("=" * 60 + "\n")
    sys.stderr.write(f"Server: {server.name} v{server.version}\n")
    sys.stderr.write(f"Resources: {len(server.resources)}\n")
    sys.stderr.write(f"Tools: {len(server.tools)}\n")
    sys.stderr.write("\nConfiguration:\n")
    sys.stderr.write("Add to ~/.config/Claude/claude_desktop_config.json:\n")
    sys.stderr.write("{\n")
    sys.stderr.write('  "mcpServers": {\n')
    sys.stderr.write('    "agenkit-demo": {\n')
    sys.stderr.write('      "command": "python",\n')
    sys.stderr.write(f'      "args": ["{sys.argv[0]}"]\n')
    sys.stderr.write("    }\n")
    sys.stderr.write("  }\n")
    sys.stderr.write("}\n")
    sys.stderr.write("\nServer starting on stdio...\n")
    sys.stderr.write("=" * 60 + "\n")
    sys.stderr.flush()

    # Start server with stdio transport (required by Claude Desktop)
    await server.start(transport="stdio")


if __name__ == "__main__":
    asyncio.run(main())
