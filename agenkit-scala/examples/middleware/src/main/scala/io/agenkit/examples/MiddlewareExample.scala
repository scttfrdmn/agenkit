package io.agenkit.examples

import io.agenkit.adapters.MockAdapter
import io.agenkit.core.Message
import io.agenkit.middleware.*
import io.agenkit.patterns.ConversationalAgent
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

/** Demonstrates middleware composition using fluent extension methods. */
object MiddlewareExample:
  def main(args: Array[String]): Unit =
    val llm   = MockAdapter("I'm available!")
    val inner = ConversationalAgent("base", llm)

    // Compose middleware
    val agent = inner
      .withRetry(maxAttempts = 3)
      .withTimeout(30.seconds)
      .withMetrics("demo")

    val metricsAgent = agent.asInstanceOf[MetricsMiddleware]

    val result = Await.result(agent.process(Message.user("Hello!")), 10.seconds)
    println(s"Response: ${result.contentString}")
    println(s"Total requests: ${metricsAgent.totalRequests}")
    println(s"Success count:  ${metricsAgent.successCount}")
    println(s"Avg latency:    ${metricsAgent.averageLatencyMs.toLong}ms")

    // Circuit breaker example
    val resilient = inner.withCircuitBreaker(threshold = 5)
    val r2 = Await.result(resilient.process(Message.user("Are you there?")), 10.seconds)
    println(s"\nCircuit breaker response: ${r2.contentString}")

    // Rate limiter example
    val limited = inner.withRateLimit(rps = 10)
    val r3 = Await.result(limited.process(Message.user("Quick question")), 10.seconds)
    println(s"Rate-limited response: ${r3.contentString}")
