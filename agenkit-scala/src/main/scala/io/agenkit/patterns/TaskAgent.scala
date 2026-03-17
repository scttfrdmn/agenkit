package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.{AtomicLong, AtomicReference}

enum TaskStatus:
  case Pending, Running, Complete, Failed

/** Single-task agent that tracks its own lifecycle status. */
class TaskAgent(
  val name: String,
  llm: LlmClient
) extends Agent:
  private val _status          = new AtomicReference[TaskStatus](TaskStatus.Pending)
  private val _processedCount  = new AtomicLong(0)

  def status: TaskStatus = _status.get()

  def capabilities: List[String] = List("task", "lifecycle")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _status.set(TaskStatus.Running)
    _processedCount.incrementAndGet()
    llm.complete(List(message))
      .map { response =>
        _status.set(TaskStatus.Complete)
        response
      }
      .recoverWith { case ex =>
        _status.set(TaskStatus.Failed)
        Future.failed(ex)
      }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("status" -> _status.get().toString),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
