package io.agenkit.middleware

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Batching facade. Delegates individual requests to the inner agent.
 *
 *  A full batching implementation requires a shared event loop; this class
 *  provides the interface and single-request path while keeping the API
 *  consistent with the other language implementations.
 */
class BatchingMiddleware(
  inner: Agent,
  maxBatchSize: Int = 10,
  windowMs: Long = 50L
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def name: String               = s"batching(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "batching"

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    inner.process(message)

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("maxBatchSize" -> maxBatchSize, "windowMs" -> windowMs),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
