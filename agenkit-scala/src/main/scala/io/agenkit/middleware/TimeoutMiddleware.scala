package io.agenkit.middleware

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future, Promise, TimeoutException}
import scala.concurrent.duration.*
import java.util.concurrent.atomic.AtomicLong
import java.util.{Timer, TimerTask}

/** Fails the request if the inner agent does not respond within `timeout`. */
class TimeoutMiddleware(
  inner: Agent,
  timeout: FiniteDuration
) extends Agent:
  private val _processedCount = new AtomicLong(0)
  private val timer           = new Timer(true) // daemon timer

  def name: String               = s"timeout(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "timeout"

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val promise = Promise[Message]()
    val task = new TimerTask:
      def run(): Unit =
        promise.tryFailure(new TimeoutException(s"Agent timed out after $timeout"))
        ()
    timer.schedule(task, timeout.toMillis)
    val innerFuture = inner.process(message)
    innerFuture.foreach { result =>
      task.cancel()
      promise.trySuccess(result)
      ()
    }
    innerFuture.failed.foreach { ex =>
      task.cancel()
      promise.tryFailure(ex)
      ()
    }
    promise.future

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("timeout" -> timeout.toString, "inner" -> inner.name),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
