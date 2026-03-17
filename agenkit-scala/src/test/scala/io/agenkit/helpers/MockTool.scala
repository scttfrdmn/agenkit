package io.agenkit.helpers

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicInteger

class MockTool(
  val name: String = "mock_tool",
  val description: String = "A mock tool for testing",
  result: ToolResult = ToolOk("tool result"),
  shouldFail: Boolean = false
) extends Tool:
  private val _callCount = new AtomicInteger(0)
  private val _params    = collection.mutable.ListBuffer[Map[String, Any]]()

  def callCount: Int                      = _callCount.get()
  def receivedParams: List[Map[String, Any]] = _params.toList

  def execute(parameters: Map[String, Any])(using ExecutionContext): Future[ToolResult] =
    _callCount.incrementAndGet()
    _params += parameters
    if shouldFail then Future.failed(new RuntimeException("mock tool failure"))
    else Future.successful(result)
