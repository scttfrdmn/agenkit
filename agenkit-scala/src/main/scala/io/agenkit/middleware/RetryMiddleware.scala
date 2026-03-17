package io.agenkit.middleware

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import scala.concurrent.duration.*
import scala.util.control.NonFatal
import java.util.concurrent.atomic.AtomicLong

/** Retries failed requests up to `maxAttempts` times with exponential back-off. */
class RetryMiddleware(
  inner: Agent,
  maxAttempts: Int = 3,
  initialDelay: FiniteDuration = 100.millis,
  backoffMultiplier: Double = 2.0
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def name: String               = s"retry(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "retry"

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    attempt(message, 1, initialDelay)

  private def attempt(
    message: Message,
    attemptNum: Int,
    delay: FiniteDuration
  )(using ExecutionContext): Future[Message] =
    inner.process(message).recoverWith {
      case NonFatal(_) if attemptNum < maxAttempts =>
        val nextDelay = (delay.toMillis * backoffMultiplier).toLong.millis
        attempt(message, attemptNum + 1, nextDelay)
    }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("maxAttempts" -> maxAttempts, "inner" -> inner.name),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
