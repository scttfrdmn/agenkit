package io.agenkit.middleware

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class MetricsMiddlewareSpec extends AnyFunSuite with Matchers:
  test("MetricsMiddleware tracks successful requests"):
    val inner   = MockAgent()
    val metrics = MetricsMiddleware(inner)
    Await.result(metrics.process(Message.user("test")), 5.seconds)
    metrics.totalRequests shouldBe 1
    metrics.successCount  shouldBe 1
    metrics.errorCount    shouldBe 0

  test("MetricsMiddleware tracks failed requests"):
    val inner   = MockAgent(shouldFail = true)
    val metrics = MetricsMiddleware(inner)
    Await.result(metrics.process(Message.user("test")).recover { case _ => Message.of("assistant", "") }, 5.seconds)
    metrics.totalRequests shouldBe 1
    metrics.errorCount    shouldBe 1

  test("MetricsMiddleware computes average latency"):
    val inner   = MockAgent()
    val metrics = MetricsMiddleware(inner)
    Await.result(metrics.process(Message.user("t1")), 5.seconds)
    Await.result(metrics.process(Message.user("t2")), 5.seconds)
    metrics.averageLatencyMs should be >= 0.0

  test("MetricsMiddleware name includes inner name"):
    val metrics = MetricsMiddleware(MockAgent(name = "base"))
    metrics.name shouldBe "metrics(base)"

  test("MetricsMiddleware introspect"):
    val metrics = MetricsMiddleware(MockAgent())
    val r       = metrics.introspect()
    r.capabilities should contain("metrics")
