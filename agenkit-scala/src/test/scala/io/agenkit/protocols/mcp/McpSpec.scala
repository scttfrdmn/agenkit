package io.agenkit.protocols.mcp

import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import upickle.default.*
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global
import io.agenkit.core.{ToolOk, ToolFail}

class McpSpec extends AnyFunSuite with Matchers:

  class MockMcpClient(
    toolList: List[McpTool] = Nil,
    callResult: McpToolResult = McpToolResult(List(McpContent("text", "result")), false)
  ) extends McpClient:
    def initialize(): Unit                                    = ()
    def listTools(): List[McpTool]                            = toolList
    def callTool(name: String, args: Map[String, Any]): McpToolResult = callResult
    def serverInfo(): McpServerInfo                           = McpServerInfo()
    def close(): Unit                                         = ()

  // ── JSON-RPC wire type tests ─────────────────────────────────────────────

  test("JsonRpcRequest serializes correctly"):
    val req  = JsonRpcRequest("2.0", 1L, "tools/list", None)
    val json = write(req)
    json should include("\"jsonrpc\":\"2.0\"")
    json should include("\"id\":1")
    json should include("\"method\":\"tools/list\"")

  test("JsonRpcResponse deserializes correctly"):
    val json = """{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}"""
    val resp = read[JsonRpcResponse](json)
    resp.jsonrpc shouldBe "2.0"
    resp.id shouldBe 1L
    resp.result shouldBe defined
    resp.error shouldBe None

  test("McpTool round-trips JSON"):
    val tool = McpTool("my_tool", "does stuff", None)
    val json = write(tool)
    val back = read[McpTool](json)
    back.name shouldBe "my_tool"
    back.description shouldBe "does stuff"
    back.inputSchema shouldBe None

  // ── textContent helper ───────────────────────────────────────────────────

  test("textContent joins single block"):
    val contents = List(McpContent("text", "hello"))
    textContent(contents) shouldBe "hello"

  test("textContent joins multiple blocks"):
    val contents = List(McpContent("text", "hello"), McpContent("text", "world"))
    textContent(contents) shouldBe "hello world"

  test("textContent skips non-text types"):
    val contents = List(McpContent("image", "data"), McpContent("text", "hello"))
    textContent(contents) shouldBe "hello"

  // ── McpClient structural tests ───────────────────────────────────────────

  test("StdioClient implements McpClient"):
    val client = StdioClient("echo", "test")
    client shouldBe a[McpClient]

  test("HttpClient implements McpClient"):
    val client = HttpClient("http://localhost:9999")
    client shouldBe a[McpClient]

  // ── McpToolAdapter tests ─────────────────────────────────────────────────

  test("adapter name"):
    val mcpTool = McpTool("search", "search the web")
    val client  = MockMcpClient(toolList = List(mcpTool))
    val tools   = toolsFromClient(client)
    tools.head.name shouldBe "search"

  test("adapter description"):
    val mcpTool = McpTool("search", "search the web")
    val client  = MockMcpClient(toolList = List(mcpTool))
    val tools   = toolsFromClient(client)
    tools.head.description shouldBe "search the web"

  test("adapter execute success"):
    val mcpTool = McpTool("echo", "echo input")
    val callRes = McpToolResult(List(McpContent("text", "pong")), false)
    val client  = MockMcpClient(toolList = List(mcpTool), callResult = callRes)
    val tools   = toolsFromClient(client)
    val result  = Await.result(tools.head.execute(Map("input" -> "ping")), 5.seconds)
    result shouldBe a[ToolOk]
    result.asInstanceOf[ToolOk].data shouldBe "pong"

  test("adapter execute isError"):
    val mcpTool = McpTool("fail_tool", "always fails")
    val callRes = McpToolResult(List(McpContent("text", "something went wrong")), true)
    val client  = MockMcpClient(toolList = List(mcpTool), callResult = callRes)
    val tools   = toolsFromClient(client)
    val result  = Await.result(tools.head.execute(Map.empty), 5.seconds)
    result shouldBe a[ToolFail]
    result.asInstanceOf[ToolFail].error shouldBe "something went wrong"

  test("toolsFromClient wraps tools"):
    val mcpTools = List(
      McpTool("tool_a", "first tool"),
      McpTool("tool_b", "second tool")
    )
    val client = MockMcpClient(toolList = mcpTools)
    val tools  = toolsFromClient(client)
    tools.length shouldBe 2
    tools.map(_.name) shouldBe List("tool_a", "tool_b")
