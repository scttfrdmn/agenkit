package io.agenkit.helpers

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicInteger

class MockAgent(
  val name: String = "mock",
  response: String = "mock response",
  shouldFail: Boolean = false,
  failMessage: String = "mock failure"
) extends Agent:
  private val _callCount = new AtomicInteger(0)
  private val _messages  = collection.mutable.ListBuffer[Message]()

  def callCount: Int               = _callCount.get()
  def receivedMessages: List[Message] = _messages.toList

  def capabilities: List[String] = List("mock")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _callCount.incrementAndGet()
    _messages += message
    if shouldFail then Future.failed(new RuntimeException(failMessage))
    else Future.successful(Message.of("assistant", response))

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("callCount" -> _callCount.get()),
      capabilities = capabilities,
      processedMessages = _callCount.get().toLong
    )
