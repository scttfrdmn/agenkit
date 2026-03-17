package io.agenkit.adapters

import io.agenkit.core.Message
import org.slf4j.LoggerFactory
import scala.concurrent.{ExecutionContext, Future}

/** OpenAI adapter stub.  Extend with an HTTP client for production use. */
class OpenAiAdapter(
  apiKey: String,
  model: String = "gpt-4o",
  baseUrl: String = "https://api.openai.com/v1"
) extends LlmClient:
  private val logger = LoggerFactory.getLogger(getClass)

  def complete(messages: List[Message])(using ExecutionContext): Future[Message] =
    logger.warn("OpenAiAdapter.complete: HTTP not implemented; use MockAdapter for tests")
    Future.failed(new UnsupportedOperationException("OpenAI HTTP not implemented in core"))
