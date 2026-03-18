package io.agenkit.protocols.mcp

import upickle.default.*

val ProtocolVersion = "2024-11-05"
val ClientVersion   = "0.83.0"

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

case class McpServerInfo(
  name: String = "",
  version: String = ""
) derives ReadWriter

def textContent(contents: List[McpContent]): String =
  contents.filter(c => c.`type` == "text" && c.text.nonEmpty).map(_.text).mkString(" ")
