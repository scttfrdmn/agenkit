package io.agenkit.middleware

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class CachingMiddlewareSpec extends AnyFunSuite with Matchers:
  test("CachingMiddleware returns cached response on second call"):
    val inner  = MockAgent(response = "original")
    val cache  = CachingMiddleware(inner, ttl = 10.seconds)
    val msg    = Message.user("same question")
    Await.result(cache.process(msg), 5.seconds)
    Await.result(cache.process(msg), 5.seconds)
    inner.callCount shouldBe 1

  test("CachingMiddleware calls inner for different content"):
    val inner = MockAgent()
    val cache = CachingMiddleware(inner, ttl = 10.seconds)
    Await.result(cache.process(Message.user("q1")), 5.seconds)
    Await.result(cache.process(Message.user("q2")), 5.seconds)
    inner.callCount shouldBe 2

  test("CachingMiddleware name includes inner name"):
    val inner = MockAgent(name = "base")
    val cache = CachingMiddleware(inner, ttl = 1.second)
    cache.name shouldBe "caching(base)"

  test("CachingMiddleware introspect"):
    val cache = CachingMiddleware(MockAgent(), ttl = 1.second)
    val r     = cache.introspect()
    r.capabilities should contain("caching")
