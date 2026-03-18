package io.agenkit.properties

import io.agenkit.core.Message
import io.agenkit.helpers.MockAgent
import io.agenkit.middleware.*
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import org.scalatestplus.scalacheck.ScalaCheckPropertyChecks
import org.scalacheck.Gen
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class MiddlewarePropertySpec extends AnyFunSuite with Matchers with ScalaCheckPropertyChecks:

  test("RetryMiddleware name contains inner agent name"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val inner = MockAgent(name = name)
        val retry = RetryMiddleware(inner, maxAttempts = 2)
        retry.name should include(name)
      }
    }

  test("RetryMiddleware on success returns same content as inner"):
    forAll { (response: String, text: String) =>
      val inner  = MockAgent(response = response)
      val retry  = RetryMiddleware(inner, maxAttempts = 3)
      val result = Await.result(retry.process(Message.user(text)), 5.seconds)
      result.contentString shouldBe response
    }

  test("CachingMiddleware name contains inner agent name"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val inner = MockAgent(name = name)
        val cache = CachingMiddleware(inner, ttl = 10.seconds)
        cache.name should include(name)
      }
    }

  test("RateLimiterMiddleware name contains inner agent name"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val inner = MockAgent(name = name)
        val rl    = RateLimiterMiddleware(inner, requestsPerSecond = 10)
        rl.name should include(name)
      }
    }

  test("RetryMiddleware with any maxAttempts >= 1 processes without exception on success"):
    forAll(Gen.choose(1, 10)) { (attempts: Int) =>
      val inner  = MockAgent(response = "ok")
      val retry  = RetryMiddleware(inner, maxAttempts = attempts)
      noException should be thrownBy Await.result(retry.process(Message.user("q")), 5.seconds)
    }

  test("RetryMiddleware wrapping preserves assistant role on success"):
    forAll { (response: String) =>
      val inner  = MockAgent(response = response)
      val retry  = RetryMiddleware(inner, maxAttempts = 2)
      val result = Await.result(retry.process(Message.user("q")), 5.seconds)
      result.role shouldBe "assistant"
    }

  test("Success path through any middleware always returns assistant role"):
    forAll { (response: String, text: String) =>
      val inner   = MockAgent(response = response)
      val metrics = MetricsMiddleware(inner)
      val result  = Await.result(metrics.process(Message.user(text)), 5.seconds)
      result.role shouldBe "assistant"
    }

  test("Introspect name from wrapped agents is non-empty"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val inner   = MockAgent(name = name)
        val wrapped = RetryMiddleware(inner, maxAttempts = 2)
        wrapped.introspect().name should not be empty
      }
    }

  test("Middleware name is stable across multiple accesses"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val inner = MockAgent(name = name)
        val retry = RetryMiddleware(inner, maxAttempts = 1)
        retry.name shouldBe retry.name
      }
    }

  test("Capabilities list from middleware is non-empty"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val inner   = MockAgent(name = name)
        val retry   = RetryMiddleware(inner, maxAttempts = 1)
        val caps    = retry.introspect().capabilities
        caps should not be empty
      }
    }
