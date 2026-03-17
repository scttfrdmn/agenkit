package io.agenkit.helpers

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicInteger

class MockLlmClient(
  responseGenerator: List[Message] => String = _ => "mock llm response",
  shouldFail: Boolean = false
) extends LlmClient:
  private val _callCount     = new AtomicInteger(0)
  private val _conversations = collection.mutable.ListBuffer[List[Message]]()

  def callCount: Int                  = _callCount.get()
  def conversations: List[List[Message]] = _conversations.toList

  def complete(messages: List[Message])(using ExecutionContext): Future[Message] =
    _callCount.incrementAndGet()
    _conversations += messages
    if shouldFail then Future.failed(new RuntimeException("mock llm failure"))
    else Future.successful(Message.of("assistant", responseGenerator(messages)))
