#!/usr/bin/env python3
"""
Agent as MCP Server Example

Demonstrates how to expose an Agenkit agent as an MCP server,
making it accessible to Claude Desktop or other MCP clients.

This example shows:
1. Creating a simple agent (or using a pattern like ReActAgent)
2. Wrapping the agent with MCP adapter
3. Running the agent as an MCP server

Usage:
    # For Claude Desktop (stdio):
    python agent_server_example.py --transport stdio

    # For HTTP:
    python agent_server_example.py --transport http --port 3000

Claude Desktop Configuration:
    Add to ~/.config/Claude/claude_desktop_config.json:
    {
      "mcpServers": {
        "agenkit-agent": {
          "command": "python",
          "args": ["/path/to/agent_server_example.py", "--transport", "stdio"]
        }
      }
    }

Requirements:
    pip install agenkit
"""

import asyncio
import argparse
from agenkit import Agent, Message
from agenkit.techniques.protocols.mcp import MCPAdapter, AgentMCPServer


class MathAgent(Agent):
    """
    Simple agent that can perform mathematical calculations.

    In a real application, this could be a more complex agent
    with LLM integration, tools, memory, etc.
    """

    @property
    def name(self) -> str:
        """Agent name."""
        return "math_agent"

    @property
    def capabilities(self) -> list[str]:
        """Agent capabilities."""
        return ["mathematics", "calculation", "arithmetic"]

    async def process(self, message: Message) -> Message:
        """
        Process mathematical queries.

        In production, this would likely use an LLM with math tools,
        or a specialized ReActAgent with calculator tools.
        """
        content = message.content.strip()

        try:
            # Safe AST-based evaluation (no arbitrary code execution)
            if any(op in content for op in ['+', '-', '*', '/', '**', '%']):
                import ast
                import operator

                # Safe operations mapping
                safe_ops = {
                    ast.Add: operator.add,
                    ast.Sub: operator.sub,
                    ast.Mult: operator.mul,
                    ast.Div: operator.truediv,
                    ast.Pow: operator.pow,
                    ast.Mod: operator.mod,
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

                tree = ast.parse(content, mode="eval")
                result = safe_eval(tree.body)

                response = f"Calculation: {content} = {result}"

                return Message(
                    role="assistant",
                    content=response,
                    metadata={
                        "calculation": content,
                        "result": result,
                        "agent": self.name
                    }
                )
            elif "help" in content.lower():
                help_text = """
I'm a mathematical calculation agent. I can help you with:

- Basic arithmetic: 2 + 2, 10 - 5, 3 * 4, 10 / 2
- Exponents: 2 ** 3
- Modulo: 10 % 3
- Complex expressions: (5 + 3) * 2

Just send me a mathematical expression and I'll calculate it!
"""
                return Message(
                    role="assistant",
                    content=help_text,
                    metadata={"agent": self.name}
                )
            else:
                return Message(
                    role="assistant",
                    content=f"I received: '{content}'. Send a mathematical expression or 'help' for usage info.",
                    metadata={"agent": self.name}
                )

        except Exception as e:
            return Message(
                role="assistant",
                content=f"Error processing '{content}': {str(e)}",
                metadata={
                    "error": str(e),
                    "agent": self.name
                }
            )


class DataProcessingAgent(Agent):
    """
    Agent that can process and transform data.

    Demonstrates an agent with multiple capabilities exposed via MCP.
    """

    @property
    def name(self) -> str:
        """Agent name."""
        return "data_processing_agent"

    @property
    def capabilities(self) -> list[str]:
        """Agent capabilities."""
        return ["data_processing", "transformation", "analysis"]

    async def process(self, message: Message) -> Message:
        """Process data transformation requests."""
        import json

        content = message.content.strip()

        try:
            # Try to parse as JSON
            if content.startswith('{') or content.startswith('['):
                data = json.loads(content)

                # Perform simple analysis
                if isinstance(data, dict):
                    response = f"Analyzed dictionary: {len(data)} keys found - {list(data.keys())}"
                elif isinstance(data, list):
                    response = f"Analyzed list: {len(data)} items, types: {set(type(x).__name__ for x in data)}"
                else:
                    response = f"Data type: {type(data).__name__}"

                return Message(
                    role="assistant",
                    content=response,
                    metadata={
                        "data_type": type(data).__name__,
                        "agent": self.name
                    }
                )
            else:
                return Message(
                    role="assistant",
                    content=f"Received text: '{content}' (length: {len(content)})",
                    metadata={
                        "length": len(content),
                        "agent": self.name
                    }
                )

        except json.JSONDecodeError:
            return Message(
                role="assistant",
                content=f"Text input received (not JSON): '{content}'",
                metadata={"agent": self.name}
            )
        except Exception as e:
            return Message(
                role="assistant",
                content=f"Error: {str(e)}",
                metadata={"error": str(e), "agent": self.name}
            )


async def run_agent_server(agent: Agent, transport: str = "stdio", host: str = "localhost", port: int = 3000):
    """
    Run an Agenkit agent as an MCP server.

    Args:
        agent: Agent to expose
        transport: Transport type ("stdio", "http", "sse")
        host: Host for HTTP/SSE
        port: Port for HTTP/SSE
    """
    # Wrap agent as MCP server
    wrapper = AgentMCPServer(agent, server_name=f"{agent.name}-mcp")

    # Print info
    print("=" * 60)
    print(f"Agenkit Agent MCP Server")
    print("=" * 60)
    print(f"Agent: {agent.name}")
    print(f"Capabilities: {', '.join(agent.capabilities)}")
    print(f"Server: {wrapper.server.name}")
    print(f"Transport: {transport}")

    if transport == "stdio":
        print()
        print("Running in stdio mode (for Claude Desktop)")
        print()
        print("Claude Desktop Configuration:")
        print('{')
        print('  "mcpServers": {')
        print(f'    "{agent.name}": {{')
        print('      "command": "python",')
        print(f'      "args": ["{__file__}", "--transport", "stdio"]')
        print('    }')
        print('  }')
        print('}')
    elif transport == "http":
        print(f"Server will start on http://{host}:{port}/mcp")
        print()
        print("Test with curl:")
        print(f"  curl -X POST http://{host}:{port}/mcp \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"jsonrpc\": \"2.0\", \"id\": 1, \"method\": \"initialize\", \"params\": {\"protocolVersion\": \"1.0\"}}'")

    print("=" * 60)

    # Start server
    try:
        await wrapper.run(transport=transport, host=host, port=port)
    except KeyboardInterrupt:
        print("\nShutting down server...")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Agenkit agent as MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Transport type (default: stdio for Claude Desktop)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for HTTP/SSE (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port for HTTP/SSE (default: 3000)"
    )
    parser.add_argument(
        "--agent",
        choices=["math", "data"],
        default="math",
        help="Agent to run (default: math)"
    )

    args = parser.parse_args()

    # Create agent
    if args.agent == "math":
        agent = MathAgent()
    else:
        agent = DataProcessingAgent()

    # Run server
    asyncio.run(run_agent_server(
        agent=agent,
        transport=args.transport,
        host=args.host,
        port=args.port
    ))


if __name__ == "__main__":
    main()
