package io.agenkit.adapters

import io.agenkit.core.Message
import scala.concurrent.{ExecutionContext, Future}

/** In-memory LLM stub for tests and examples. */
class MockAdapter(
  response: String = "mock adapter response"
) extends LlmClient:
  def complete(messages: List[Message])(using ExecutionContext): Future[Message] =
    Future.successful(Message.of("assistant", response))
