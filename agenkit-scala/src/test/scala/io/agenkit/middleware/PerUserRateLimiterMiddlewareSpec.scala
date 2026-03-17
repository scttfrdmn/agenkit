package io.agenkit.middleware

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class PerUserRateLimiterMiddlewareSpec extends AnyFunSuite with Matchers:
  private def msgFor(userId: String) =
    Message(role = "user", content = Some("test"), metadata = Map("user_id" -> userId))

  test("PerUserRateLimiter allows request for user within limit"):
    val inner = MockAgent()
    val rl    = PerUserRateLimiterMiddleware(inner, requestsPerSecond = 5)
    val result = Await.result(rl.process(msgFor("u1")), 5.seconds)
    result.role shouldBe "assistant"

  test("PerUserRateLimiter independently limits different users"):
    val inner = MockAgent()
    val rl    = PerUserRateLimiterMiddleware(inner, requestsPerSecond = 1)
    Await.result(rl.process(msgFor("user1")), 5.seconds)
    // user2 should still have tokens
    val result = Await.result(rl.process(msgFor("user2")), 5.seconds)
    result.role shouldBe "assistant"

  test("PerUserRateLimiter rejects after exhausting per-user tokens"):
    val inner = MockAgent()
    val rl    = PerUserRateLimiterMiddleware(inner, requestsPerSecond = 1)
    Await.result(rl.process(msgFor("u1")), 5.seconds)
    val ex = Await.result(rl.process(msgFor("u1")).failed, 5.seconds)
    ex.getMessage should include("Rate limit exceeded")

  test("PerUserRateLimiter introspect"):
    val rl = PerUserRateLimiterMiddleware(MockAgent())
    val r  = rl.introspect()
    r.capabilities should contain("per-user-rate-limiting")
