package io.agenkit.middleware

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class RateLimiterMiddlewareSpec extends AnyFunSuite with Matchers:
  test("RateLimiterMiddleware allows requests within limit"):
    val inner = MockAgent()
    val rl    = RateLimiterMiddleware(inner, requestsPerSecond = 5)
    val result = Await.result(rl.process(Message.user("test")), 5.seconds)
    result.role shouldBe "assistant"

  test("RateLimiterMiddleware rejects after exhausting tokens"):
    val inner = MockAgent()
    val rl    = RateLimiterMiddleware(inner, requestsPerSecond = 2)
    Await.result(rl.process(Message.user("1")), 5.seconds)
    Await.result(rl.process(Message.user("2")), 5.seconds)
    val ex = Await.result(rl.process(Message.user("3")).failed, 5.seconds)
    ex.getMessage should include("Rate limit exceeded")

  test("RateLimiterMiddleware name includes inner name"):
    val rl = RateLimiterMiddleware(MockAgent(name = "base"), requestsPerSecond = 10)
    rl.name shouldBe "rate-limiter(base)"

  test("RateLimiterMiddleware introspect"):
    val rl = RateLimiterMiddleware(MockAgent(), requestsPerSecond = 10)
    val r  = rl.introspect()
    r.capabilities should contain("rate-limiting")
