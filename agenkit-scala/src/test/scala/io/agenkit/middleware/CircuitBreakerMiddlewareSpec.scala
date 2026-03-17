package io.agenkit.middleware

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class CircuitBreakerMiddlewareSpec extends AnyFunSuite with Matchers:
  test("CircuitBreaker starts Closed"):
    val cb = CircuitBreakerMiddleware(MockAgent())
    cb.circuitState shouldBe CircuitState.Closed

  test("CircuitBreaker passes through on success"):
    val inner  = MockAgent(response = "ok")
    val cb     = CircuitBreakerMiddleware(inner)
    val result = Await.result(cb.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "ok"

  test("CircuitBreaker opens after threshold failures"):
    val inner = MockAgent(shouldFail = true)
    val cb    = CircuitBreakerMiddleware(inner, failureThreshold = 3)
    // exhaust the threshold
    (1 to 3).foreach { _ =>
      Await.result(cb.process(Message.user("fail")).recover { case _ => Message.of("assistant", "") }, 5.seconds)
    }
    cb.circuitState shouldBe CircuitState.Open

  test("CircuitBreaker rejects requests when Open"):
    val inner = MockAgent(shouldFail = true)
    val cb    = CircuitBreakerMiddleware(inner, failureThreshold = 1)
    Await.result(cb.process(Message.user("fail")).recover { case _ => Message.of("assistant", "") }, 5.seconds)
    val ex = Await.result(cb.process(Message.user("blocked")).failed, 5.seconds)
    ex.getMessage should include("Circuit breaker is open")

  test("CircuitBreaker introspect"):
    val cb = CircuitBreakerMiddleware(MockAgent())
    val r  = cb.introspect()
    r.capabilities should contain("circuit-breaker")
