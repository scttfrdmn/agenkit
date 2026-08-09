package io.agenkit.protocols.mcp

import java.net.URI
import java.net.http.{HttpClient as JHttpClient, HttpRequest, HttpResponse}
import java.util.concurrent.atomic.AtomicLong
import upickle.default.*

/** MCP client that communicates over HTTP/JSON-RPC. */
class HttpClient(baseUrl: String) extends McpClient:
  private val http        = JHttpClient.newHttpClient()
  private val nextId      = AtomicLong(0)
  private var _serverInfo = McpServerInfo()
  private val url         = baseUrl.stripSuffix("/")

  def initialize(): Unit =
    val params = ujson.Obj(
      "protocolVersion" -> ProtocolVersion,
      "capabilities"    -> ujson.Obj(),
      "clientInfo"      -> ujson.Obj("name" -> "agenkit", "version" -> ClientVersion)
    )
    val resp = sendRequest("initialize", Some(params))
    resp.error.foreach(e => throw RuntimeException(s"mcp initialize error ${e.code}: ${e.message}"))
    resp.result.foreach { r =>
      _serverInfo = McpVersionNegotiation.parseServerInfo(r)
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

  def close(): Unit = ()

  private def sendRequest(method: String, params: Option[ujson.Value]): JsonRpcResponse =
    val id      = nextId.incrementAndGet()
    val req     = JsonRpcRequest("2.0", id, method, params)
    val body    = write(req)
    val request = HttpRequest.newBuilder()
      .uri(URI.create(url))
      .POST(HttpRequest.BodyPublishers.ofString(body))
      .header("Content-Type", "application/json")
      .build()
    val response = http.send(request, HttpResponse.BodyHandlers.ofString())
    read[JsonRpcResponse](response.body())

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
