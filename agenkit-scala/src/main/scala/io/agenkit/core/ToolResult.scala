package io.agenkit.core

/** Result of a tool invocation. */
sealed trait ToolResult

/** Successful tool result carrying arbitrary data. */
case class ToolOk(data: Any) extends ToolResult

/** Failed tool result carrying an error message. */
case class ToolFail(error: String) extends ToolResult

object ToolResult:
  def ok(data: Any): ToolResult    = ToolOk(data)
  def fail(error: String): ToolResult = ToolFail(error)
