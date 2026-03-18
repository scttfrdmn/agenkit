package io.agenkit.middleware

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class AgentOpsSpec extends AnyFunSuite with Matchers:
  test("withRetry wraps agent in RetryMiddleware"):
    val inner = MockAgent()
    val wrapped = inner.withRetry(3)
    wrapped shouldBe a[RetryMiddleware]

  test("withTimeout wraps agent in TimeoutMiddleware"):
    val inner = MockAgent()
    val wrapped = inner.withTimeout(1.second)
    wrapped shouldBe a[TimeoutMiddleware]

  test("withCircuitBreaker wraps agent in CircuitBreakerMiddleware"):
    val inner = MockAgent()
    val wrapped = inner.withCircuitBreaker(5)
    wrapped shouldBe a[CircuitBreakerMiddleware]

  test("withCaching wraps agent in CachingMiddleware"):
    val inner = MockAgent()
    val wrapped = inner.withCaching(1.second)
    wrapped shouldBe a[CachingMiddleware]

  test("withRateLimit wraps agent in RateLimiterMiddleware"):
    val inner = MockAgent()
    val wrapped = inner.withRateLimit(10)
    wrapped shouldBe a[RateLimiterMiddleware]

  test("withMetrics wraps agent in MetricsMiddleware"):
    val inner = MockAgent()
    val wrapped = inner.withMetrics()
    wrapped shouldBe a[MetricsMiddleware]

  test("chained middleware all work together"):
    val inner   = MockAgent(response = "ok")
    val wrapped = inner.withRetry(2).withMetrics("test")
    val result  = Await.result(wrapped.process(Message.user("hi")), 5.seconds)
    result.contentString shouldBe "ok"

  test("withRetry preserves response content"):
    val inner   = MockAgent(response = "preserved")
    val wrapped = inner.withRetry(3)
    val result  = Await.result(wrapped.process(Message.user("q")), 5.seconds)
    result.contentString shouldBe "preserved"

  test("withCaching wraps then withTimeout produces valid agent"):
    val inner   = MockAgent(response = "data")
    val wrapped = inner.withCaching(1.second).withTimeout(5.seconds)
    val result  = Await.result(wrapped.process(Message.user("q")), 10.seconds)
    result.role shouldBe "assistant"
