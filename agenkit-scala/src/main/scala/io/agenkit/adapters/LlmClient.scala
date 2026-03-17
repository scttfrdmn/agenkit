package io.agenkit.adapters

import io.agenkit.core.Message
import scala.concurrent.{ExecutionContext, Future}

/** Minimal interface for any LLM backend. */
trait LlmClient:
  def complete(messages: List[Message])(using ExecutionContext): Future[Message]
