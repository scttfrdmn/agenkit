package io.agenkit.protocols.mcp

import io.agenkit.core.{Tool, ToolResult}
import scala.concurrent.{ExecutionContext, Future}

/** Wraps a single MCP tool as an agenkit Tool. */
private class McpToolAdapter(client: McpClient, mcpTool: McpTool) extends Tool:
  def name: String        = mcpTool.name
  def description: String = mcpTool.description

  def execute(parameters: Map[String, Any])(using ExecutionContext): Future[ToolResult] =
    Future {
      val result = client.callTool(name, parameters)
      val text   = textContent(result.content)
      if result.isError then ToolResult.fail(text)
      else ToolResult.ok(text)
    }

/** Wraps all tools advertised by an MCP client as agenkit Tools. */
def toolsFromClient(client: McpClient): List[Tool] =
  client.listTools().map(t => McpToolAdapter(client, t))
