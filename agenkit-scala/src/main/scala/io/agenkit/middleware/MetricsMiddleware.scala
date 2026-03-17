package io.agenkit.middleware

import io.agenkit.core.*
import org.slf4j.LoggerFactory
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Instruments an agent with request counts, success/error counts, and latency. */
class MetricsMiddleware(
  inner: Agent,
  prefix: String = ""
) extends Agent:
  private val logger          = LoggerFactory.getLogger(getClass)
  private val _totalRequests  = new AtomicLong(0)
  private val _successCount   = new AtomicLong(0)
  private val _errorCount     = new AtomicLong(0)
  private val _totalLatencyMs = new AtomicLong(0)

  def name: String               = s"metrics(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "metrics"

  def totalRequests: Long  = _totalRequests.get()
  def successCount: Long   = _successCount.get()
  def errorCount: Long     = _errorCount.get()
  def averageLatencyMs: Double =
    val total = _totalRequests.get()
    if total == 0 then 0.0 else _totalLatencyMs.get().toDouble / total

  def process(message: Message)(using ExecutionContext): Future[Message] =
    val start        = System.currentTimeMillis()
    val metricPrefix = if prefix.nonEmpty then s"$prefix." else ""
    _totalRequests.incrementAndGet()
    inner.process(message)
      .map { response =>
        val latency = System.currentTimeMillis() - start
        _successCount.incrementAndGet()
        _totalLatencyMs.addAndGet(latency)
        logger.debug(s"${metricPrefix}success latency=${latency}ms")
        response
      }
      .recoverWith { case ex =>
        val latency = System.currentTimeMillis() - start
        _errorCount.incrementAndGet()
        _totalLatencyMs.addAndGet(latency)
        logger.warn(s"${metricPrefix}error latency=${latency}ms error=${ex.getMessage}")
        Future.failed(ex)
      }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map(
        "totalRequests" -> _totalRequests.get(),
        "successCount"  -> _successCount.get(),
        "errorCount"    -> _errorCount.get(),
        "avgLatencyMs"  -> averageLatencyMs
      ),
      capabilities = capabilities,
      processedMessages = _totalRequests.get()
    )
