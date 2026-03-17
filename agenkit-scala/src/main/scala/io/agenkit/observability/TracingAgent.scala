package io.agenkit.observability

import io.agenkit.core.*
import org.slf4j.LoggerFactory
import scala.concurrent.{ExecutionContext, Future}
import java.util.UUID
import java.util.concurrent.atomic.AtomicLong

case class TraceSpan(
  traceId: String,
  spanId: String,
  operation: String,
  startMs: Long,
  endMs: Long,
  success: Boolean
)

/** Wraps an agent with distributed tracing spans, propagating trace IDs via message metadata. */
class TracingAgent(
  inner: Agent,
  serviceName: String = "agenkit"
) extends Agent:
  private val logger          = LoggerFactory.getLogger(getClass)
  private val _processedCount = new AtomicLong(0)
  private val spans           = collection.mutable.ListBuffer[TraceSpan]()

  def name: String               = s"tracing(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "tracing"
  def getSpans: List[TraceSpan]  = spans.toList

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val traceId = message.metadata.get("trace_id").map(_.toString).getOrElse(UUID.randomUUID().toString)
    val spanId  = UUID.randomUUID().toString
    val start   = System.currentTimeMillis()
    logger.debug(s"[$serviceName] trace=$traceId span=$spanId START ${inner.name}")
    inner.process(message.copy(metadata = message.metadata + ("trace_id" -> traceId)))
      .map { response =>
        val end = System.currentTimeMillis()
        spans += TraceSpan(traceId, spanId, inner.name, start, end, success = true)
        logger.debug(s"[$serviceName] trace=$traceId span=$spanId END latency=${end - start}ms")
        response
      }
      .recoverWith { case ex =>
        val end = System.currentTimeMillis()
        spans += TraceSpan(traceId, spanId, inner.name, start, end, success = false)
        logger.warn(s"[$serviceName] trace=$traceId span=$spanId ERROR ${ex.getMessage}")
        Future.failed(ex)
      }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("spanCount" -> spans.size, "service" -> serviceName),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
