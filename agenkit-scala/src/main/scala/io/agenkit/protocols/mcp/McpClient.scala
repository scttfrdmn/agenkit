package io.agenkit.protocols.mcp

/** Client interface for connecting to an MCP server. */
trait McpClient:
  def initialize(): Unit
  def listTools(): List[McpTool]
  def callTool(name: String, args: Map[String, Any]): McpToolResult
  def serverInfo(): McpServerInfo
  def close(): Unit
