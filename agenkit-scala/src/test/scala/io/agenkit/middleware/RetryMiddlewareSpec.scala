package io.agenkit.middleware

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class RetryMiddlewareSpec extends AnyFunSuite with Matchers:
  test("RetryMiddleware passes through on first success"):
    val inner  = MockAgent(response = "ok")
    val retry  = RetryMiddleware(inner, maxAttempts = 3)
    val result = Await.result(retry.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "ok"
    inner.callCount shouldBe 1

  test("RetryMiddleware retries on failure and succeeds eventually"):
    var attempts = 0
    val inner = new MockAgent("inner"):
      override def process(message: Message)(using ec: scala.concurrent.ExecutionContext) =
        attempts += 1
        if attempts < 3 then scala.concurrent.Future.failed(new RuntimeException("fail"))
        else scala.concurrent.Future.successful(Message.of("assistant", "success"))
    val retry  = RetryMiddleware(inner, maxAttempts = 3)
    val result = Await.result(retry.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "success"
    attempts shouldBe 3

  test("RetryMiddleware fails after exhausting attempts"):
    val inner  = MockAgent(shouldFail = true)
    val retry  = RetryMiddleware(inner, maxAttempts = 2)
    val result = retry.process(Message.user("test")).failed
    val ex     = Await.result(result, 5.seconds)
    ex.getMessage shouldBe "mock failure"

  test("RetryMiddleware name includes inner name"):
    val inner = MockAgent(name = "myagent")
    val retry = RetryMiddleware(inner)
    retry.name shouldBe "retry(myagent)"

  test("RetryMiddleware introspect"):
    val inner = MockAgent(name = "inner")
    val retry = RetryMiddleware(inner)
    val r     = retry.introspect()
    r.capabilities should contain("retry")

  test("RetryMiddleware with zero retries fails immediately"):
    val inner  = MockAgent(shouldFail = true)
    val retry  = RetryMiddleware(inner, maxAttempts = 1)
    val ex     = Await.result(retry.process(Message.user("test")).failed, 5.seconds)
    ex.getMessage shouldBe "mock failure"
    inner.callCount shouldBe 1

  test("RetryMiddleware respects different maxAttempts configuration"):
    var attempts = 0
    val inner = new MockAgent("inner"):
      override def process(message: Message)(using ec: scala.concurrent.ExecutionContext) =
        attempts += 1
        if attempts < 4 then scala.concurrent.Future.failed(new RuntimeException("fail"))
        else scala.concurrent.Future.successful(Message.of("assistant", "ok"))
    val retry  = RetryMiddleware(inner, maxAttempts = 4)
    val result = Await.result(retry.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "ok"
    attempts shouldBe 4
