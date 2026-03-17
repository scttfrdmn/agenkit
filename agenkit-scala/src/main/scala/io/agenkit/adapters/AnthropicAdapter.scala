package io.agenkit.adapters

import io.agenkit.core.Message
import org.slf4j.LoggerFactory
import scala.concurrent.{ExecutionContext, Future}

/** Anthropic adapter stub.  Extend with an HTTP client for production use. */
class AnthropicAdapter(
  apiKey: String,
  model: String = "claude-opus-4-6",
  baseUrl: String = "https://api.anthropic.com"
) extends LlmClient:
  private val logger = LoggerFactory.getLogger(getClass)

  def complete(messages: List[Message])(using ExecutionContext): Future[Message] =
    logger.warn("AnthropicAdapter.complete: HTTP not implemented; use MockAdapter for tests")
    Future.failed(new UnsupportedOperationException("Anthropic HTTP not implemented in core"))
