package io.agenkit.protocols.mcp

import org.slf4j.LoggerFactory
import upickle.default.*

// The MCP protocol revision this implementation speaks. A single named
// constant (agenkit#781) used by both client and server code, rather than
// each repeating the literal, so a version bump is a one-line change and
// the two halves of the protocol cannot drift from each other.
//
// 2025-11-25 is the latest *ratified* revision whose initialize/tools/list/
// tools/call surface is additive over 2024-11-05 (agenkit#733: the
// 2026-07-28 revision removes the initialize handshake in favor of a
// stateless core this package does not implement, so advertising that
// literal would claim a handshake the wire no longer has).
val ProtocolVersion = "2025-11-25"
val ClientVersion   = "0.92.0"

// Wire types (private to package)
private[mcp] case class JsonRpcRequest(
  jsonrpc: String,
  id: Long,
  method: String,
  params: Option[ujson.Value] = None
)

private[mcp] object JsonRpcRequest:
  given ReadWriter[JsonRpcRequest] = readwriter[ujson.Value].bimap(
    r =>
      val obj = ujson.Obj(
        "jsonrpc" -> ujson.Str(r.jsonrpc),
        "id"      -> ujson.Num(r.id.toDouble),
        "method"  -> ujson.Str(r.method)
      )
      r.params.foreach(p => obj("params") = p)
      obj,
    v =>
      JsonRpcRequest(
        v("jsonrpc").str,
        v("id").num.toLong,
        v("method").str,
        v.obj.get("params").filterNot(_ == ujson.Null)
      )
  )

private[mcp] case class JsonRpcError(
  code: Int,
  message: String
) derives ReadWriter

private[mcp] case class JsonRpcResponse(
  jsonrpc: String,
  id: Long,
  result: Option[ujson.Value] = None,
  error: Option[JsonRpcError] = None
)

private[mcp] object JsonRpcResponse:
  given ReadWriter[JsonRpcResponse] = readwriter[ujson.Value].bimap(
    r =>
      val obj = ujson.Obj(
        "jsonrpc" -> ujson.Str(r.jsonrpc),
        "id"      -> ujson.Num(r.id.toDouble)
      )
      r.result.foreach(v => obj("result") = v)
      r.error.foreach(e => obj("error") = writeJs(e))
      obj,
    v =>
      JsonRpcResponse(
        v("jsonrpc").str,
        v("id").num.toLong,
        v.obj.get("result").filterNot(_ == ujson.Null),
        v.obj.get("error").filterNot(_ == ujson.Null).map(e => read[JsonRpcError](e))
      )
  )

// Public domain types
case class McpTool(
  name: String,
  description: String,
  inputSchema: Option[ujson.Value] = None
)

object McpTool:
  given ReadWriter[McpTool] = readwriter[ujson.Value].bimap(
    t =>
      val obj = ujson.Obj(
        "name"        -> ujson.Str(t.name),
        "description" -> ujson.Str(t.description)
      )
      t.inputSchema.foreach(s => obj("inputSchema") = s)
      obj,
    v =>
      McpTool(
        v("name").str,
        v("description").str,
        v.obj.get("inputSchema").filterNot(_ == ujson.Null)
      )
  )

case class McpContent(
  `type`: String,
  text: String
) derives ReadWriter

case class McpToolResult(
  content: List[McpContent],
  isError: Boolean
) derives ReadWriter

/** Identity information about a connected MCP server.
  *
  * @param protocolVersion
  *   The MCP protocol revision the server actually reported in its initialize response
  *   (`result.protocolVersion`). Captured so a caller has a single place to check it after
  *   `initialize()` (agenkit#781 -- this field did not exist before, so a peer speaking a
  *   different revision was indistinguishable from one speaking ours).
  */
case class McpServerInfo(
  name: String = "",
  version: String = "",
  protocolVersion: String = ""
) derives ReadWriter

def textContent(contents: List[McpContent]): String =
  contents.filter(c => c.`type` == "text" && c.text.nonEmpty).map(_.text).mkString(" ")

/** Protocol version negotiation helpers shared by client and server (agenkit#781). */
private[mcp] object McpVersionNegotiation:
  private val logger = LoggerFactory.getLogger(getClass)

  /** Builds an [[McpServerInfo]] from a raw initialize result, capturing the server's reported
    * `protocolVersion` (previously discarded) and warning when it differs from ours, so version
    * skew is visible instead of surfacing later as an unrelated decode error or wrong result.
    */
  def parseServerInfo(result: ujson.Value): McpServerInfo =
    val name    = result.obj.get("serverInfo").flatMap(_.obj.get("name")).map(_.str).getOrElse("")
    val version = result.obj.get("serverInfo").flatMap(_.obj.get("version")).map(_.str).getOrElse("")
    val protocolVersion = result.obj.get("protocolVersion").map(_.str).getOrElse("")

    if protocolVersion.nonEmpty && protocolVersion != ProtocolVersion then
      logger.warn(
        "mcp: server protocol version \"{}\" does not match client version \"{}\"",
        protocolVersion,
        ProtocolVersion
      )

    McpServerInfo(name, version, protocolVersion)

  /** Reads (and thus stops discarding) the client's requested `protocolVersion` from an
    * initialize request's params, warning on a mismatch. Per the MCP spec's negotiation model
    * the server always replies with the revision it actually implements.
    */
  def warnIfClientVersionMismatch(params: Option[ujson.Value]): Unit =
    for
      p  <- params
      pv <- p.obj.get("protocolVersion")
    do
      val clientProtocolVersion = pv.str
      if clientProtocolVersion.nonEmpty && clientProtocolVersion != ProtocolVersion then
        logger.warn(
          "mcp: client requested protocol version \"{}\", server speaks \"{}\"",
          clientProtocolVersion,
          ProtocolVersion
        )
