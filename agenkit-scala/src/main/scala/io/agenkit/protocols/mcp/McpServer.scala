package io.agenkit.protocols.mcp

import io.agenkit.core.{Tool, ToolOk, ToolFail}
import java.io.*
import scala.concurrent.{Await, ExecutionContext}
import scala.concurrent.duration.*
import upickle.default.*

/** Stdio MCP server that exposes a list of Tools via JSON-RPC. */
class McpServer(name: String, version: String, tools: List[Tool]):
  private val toolMap = tools.map(t => t.name -> t).toMap

  given ExecutionContext = ExecutionContext.global

  def serveStdio(): Unit =
    val reader = BufferedReader(InputStreamReader(System.in))
    val writer = PrintWriter(OutputStreamWriter(System.out), true)
    var line   = reader.readLine()
    while line != null do
      try
        val req  = read[JsonRpcRequest](line)
        val resp = handleRequest(req)
        writer.println(write(resp))
      catch
        case _: Exception =>
          writer.println(
            """{"jsonrpc":"2.0","id":0,"error":{"code":-32700,"message":"parse error"}}"""
          )
      line = reader.readLine()

  def handleRequest(req: JsonRpcRequest): JsonRpcResponse = req.method match
    case "initialize"  => handleInitialize(req)
    case "tools/list"  => handleToolsList(req)
    case "tools/call"  => handleToolsCall(req)
    case m =>
      JsonRpcResponse("2.0", req.id, error = Some(JsonRpcError(-32601, s"method not found: $m")))

  private def handleInitialize(req: JsonRpcRequest): JsonRpcResponse =
    val result = ujson.Obj(
      "protocolVersion" -> ProtocolVersion,
      "capabilities"    -> ujson.Obj(),
      "serverInfo"      -> ujson.Obj("name" -> name, "version" -> version)
    )
    JsonRpcResponse("2.0", req.id, result = Some(result))

  private def handleToolsList(req: JsonRpcRequest): JsonRpcResponse =
    val toolsArr = ujson.Arr.from(tools.map { t =>
      ujson.Obj("name" -> t.name, "description" -> t.description, "inputSchema" -> ujson.Obj())
    })
    val result = ujson.Obj("tools" -> toolsArr)
    JsonRpcResponse("2.0", req.id, result = Some(result))

  private def handleToolsCall(req: JsonRpcRequest): JsonRpcResponse =
    req.params match
      case None =>
        JsonRpcResponse(
          "2.0", req.id,
          error = Some(JsonRpcError(-32602, "missing params"))
        )
      case Some(params) =>
        val toolName = params("name").str
        val argsObj  = params.obj.get("arguments").getOrElse(ujson.Obj())
        val argsMap  = argsObj.obj.toMap.view.mapValues(ujsonToAny).toMap

        toolMap.get(toolName) match
          case None =>
            JsonRpcResponse(
              "2.0", req.id,
              error = Some(JsonRpcError(-32601, s"tool not found: $toolName"))
            )
          case Some(tool) =>
            try
              val toolResult = Await.result(tool.execute(argsMap), 30.seconds)
              toolResult match
                case ToolOk(data) =>
                  val content = ujson.Arr(ujson.Obj("type" -> "text", "text" -> data.toString))
                  val result  = ujson.Obj("content" -> content, "isError" -> false)
                  JsonRpcResponse("2.0", req.id, result = Some(result))
                case ToolFail(error) =>
                  val content = ujson.Arr(ujson.Obj("type" -> "text", "text" -> error))
                  val result  = ujson.Obj("content" -> content, "isError" -> true)
                  JsonRpcResponse("2.0", req.id, result = Some(result))
            catch
              case e: Exception =>
                JsonRpcResponse(
                  "2.0", req.id,
                  error = Some(JsonRpcError(-32603, s"internal error: ${e.getMessage}"))
                )

  private def ujsonToAny(v: ujson.Value): Any = v match
    case ujson.Str(s)  => s
    case ujson.Num(n)  => n
    case ujson.Bool(b) => b
    case ujson.Null    => null
    case ujson.Obj(m)  => m.toMap.view.mapValues(ujsonToAny).toMap
    case ujson.Arr(a)  => a.toList.map(ujsonToAny)
