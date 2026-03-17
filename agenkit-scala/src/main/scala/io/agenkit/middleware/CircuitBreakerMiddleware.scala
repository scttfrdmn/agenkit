package io.agenkit.middleware

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.{AtomicInteger, AtomicLong, AtomicReference}
import java.time.Instant

enum CircuitState:
  case Closed, Open, HalfOpen

/** Circuit breaker: opens after `failureThreshold` consecutive errors; attempts reset after `resetTimeout` ms. */
class CircuitBreakerMiddleware(
  inner: Agent,
  failureThreshold: Int = 5,
  resetTimeout: Long = 60000L
) extends Agent:
  private val state           = new AtomicReference[CircuitState](CircuitState.Closed)
  private val failureCount    = new AtomicInteger(0)
  private val lastFailureTime = new AtomicLong(0L)
  private val _processedCount = new AtomicLong(0)

  def name: String               = s"circuit-breaker(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "circuit-breaker"
  def circuitState: CircuitState = state.get()

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    state.get() match
      case CircuitState.Open =>
        val elapsed = Instant.now().toEpochMilli - lastFailureTime.get()
        if elapsed > resetTimeout then
          state.set(CircuitState.HalfOpen)
          tryCall(message)
        else
          Future.failed(new RuntimeException("Circuit breaker is open"))
      case CircuitState.HalfOpen | CircuitState.Closed =>
        tryCall(message)

  private def tryCall(message: Message)(using ExecutionContext): Future[Message] =
    inner.process(message)
      .map { result =>
        failureCount.set(0)
        state.set(CircuitState.Closed)
        result
      }
      .recoverWith { case ex =>
        val failures = failureCount.incrementAndGet()
        lastFailureTime.set(Instant.now().toEpochMilli)
        if failures >= failureThreshold then state.set(CircuitState.Open)
        Future.failed(ex)
      }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map(
        "state"        -> state.get().toString,
        "failureCount" -> failureCount.get(),
        "threshold"    -> failureThreshold
      ),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
