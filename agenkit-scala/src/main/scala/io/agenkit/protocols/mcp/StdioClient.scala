package io.agenkit.protocols.mcp

import java.io.*
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.locks.ReentrantLock
import upickle.default.*

/** MCP client that communicates with a subprocess over stdin/stdout. */
class StdioClient(command: String, args: String*) extends McpClient:
  private val nextId      = AtomicLong(0)
  private val lock        = ReentrantLock()
  private var process: Process | Null = null
  private var reader: BufferedReader | Null = null
  private var writer: PrintWriter | Null = null
  private var _serverInfo = McpServerInfo()

  def initialize(): Unit =
    val cmdList = java.util.Arrays.asList((command +: args.toSeq)*)
    val pb      = ProcessBuilder(cmdList)
    pb.redirectErrorStream(false)
    process = pb.start()
    reader = BufferedReader(InputStreamReader(process.nn.getInputStream))
    writer = PrintWriter(OutputStreamWriter(process.nn.getOutputStream), true)

    val params = ujson.Obj(
      "protocolVersion" -> ProtocolVersion,
      "capabilities"    -> ujson.Obj(),
      "clientInfo"      -> ujson.Obj("name" -> "agenkit", "version" -> ClientVersion)
    )
    val resp = sendRequest("initialize", Some(params))
    resp.error.foreach(e => throw RuntimeException(s"mcp initialize error ${e.code}: ${e.message}"))
    resp.result.foreach { r =>
      r.obj.get("serverInfo").foreach { info =>
        _serverInfo = McpServerInfo(
          info.obj.get("name").map(_.str).getOrElse(""),
          info.obj.get("version").map(_.str).getOrElse("")
        )
      }
    }

  def listTools(): List[McpTool] =
    val resp = sendRequest("tools/list", None)
    resp.error.foreach(e => throw RuntimeException(s"mcp tools/list error ${e.code}: ${e.message}"))
    resp.result match
      case Some(r) =>
        r.obj.get("tools") match
          case Some(arr) => arr.arr.toList.map(v => read[McpTool](v))
          case None      => Nil
      case None => Nil

  def callTool(name: String, args: Map[String, Any]): McpToolResult =
    val argsJson = ujson.Obj.from(args.view.mapValues(anyToUjson))
    val params   = ujson.Obj("name" -> name, "arguments" -> argsJson)
    val resp     = sendRequest("tools/call", Some(params))
    resp.error.foreach(e => throw RuntimeException(s"mcp tools/call error ${e.code}: ${e.message}"))
    resp.result match
      case Some(r) => read[McpToolResult](r)
      case None    => McpToolResult(Nil, isError = true)

  def serverInfo(): McpServerInfo = _serverInfo

  def close(): Unit =
    writer = null
    reader = null
    process.nn.destroy()
    process = null

  private def sendRequest(method: String, params: Option[ujson.Value]): JsonRpcResponse =
    lock.lock()
    try
      val id  = nextId.incrementAndGet()
      val req = JsonRpcRequest("2.0", id, method, params)
      writer.nn.println(write(req))
      val line = reader.nn.readLine()
      if line == null then throw RuntimeException("mcp: server closed stdout")
      read[JsonRpcResponse](line)
    finally lock.unlock()

  private def anyToUjson(v: Any): ujson.Value = v match
    case s: String  => ujson.Str(s)
    case n: Int     => ujson.Num(n.toDouble)
    case n: Long    => ujson.Num(n.toDouble)
    case n: Double  => ujson.Num(n)
    case n: Float   => ujson.Num(n.toDouble)
    case b: Boolean => ujson.Bool(b)
    case null       => ujson.Null
    case m: Map[?, ?] =>
      ujson.Obj.from(m.asInstanceOf[Map[String, Any]].view.mapValues(anyToUjson))
    case l: List[?] =>
      ujson.Arr.from(l.asInstanceOf[List[Any]].map(anyToUjson))
    case other => ujson.Str(other.toString)
