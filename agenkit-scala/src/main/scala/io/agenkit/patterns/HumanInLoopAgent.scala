package io.agenkit.patterns

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Gates every request through a human-approval callback before proceeding. */
class HumanInLoopAgent(
  val name: String,
  inner: Agent,
  approver: Message => Future[Boolean],
  rejectionMessage: String = "Action not approved by human reviewer"
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("human-in-loop", "approval-gate")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    approver(message).flatMap { approved =>
      if approved then inner.process(message)
      else Future.successful(Message.of("assistant", rejectionMessage))
    }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("innerAgent" -> inner.name),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
