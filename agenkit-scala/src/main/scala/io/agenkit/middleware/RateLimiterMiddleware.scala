package io.agenkit.middleware

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Token-bucket rate limiter; refills to `requestsPerSecond` tokens every second. */
class RateLimiterMiddleware(
  inner: Agent,
  requestsPerSecond: Int
) extends Agent:
  private val tokens          = new AtomicLong(requestsPerSecond)
  private val lastRefill      = new AtomicLong(System.currentTimeMillis())
  private val _processedCount = new AtomicLong(0)

  def name: String               = s"rate-limiter(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "rate-limiting"

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    refillTokens()
    val available = tokens.get()
    if available > 0 && tokens.compareAndSet(available, available - 1) then
      inner.process(message)
    else
      Future.failed(new RuntimeException("Rate limit exceeded"))

  private def refillTokens(): Unit =
    val now     = System.currentTimeMillis()
    val last    = lastRefill.get()
    val elapsed = now - last
    if elapsed >= 1000 && lastRefill.compareAndSet(last, now) then
      tokens.set(requestsPerSecond)

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("rps" -> requestsPerSecond, "tokens" -> tokens.get()),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
