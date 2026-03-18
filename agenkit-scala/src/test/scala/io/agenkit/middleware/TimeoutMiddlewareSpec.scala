package io.agenkit.middleware

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.{Await, Future, Promise}
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global
import java.util.concurrent.TimeoutException

class TimeoutMiddlewareSpec extends AnyFunSuite with Matchers:
  test("TimeoutMiddleware passes through fast responses"):
    val inner   = MockAgent(response = "fast")
    val timeout = TimeoutMiddleware(inner, 5.seconds)
    val result  = Await.result(timeout.process(Message.user("test")), 10.seconds)
    result.contentString shouldBe "fast"

  test("TimeoutMiddleware times out slow agents"):
    val slowAgent = new MockAgent("slow"):
      override def process(message: Message)(using ec: scala.concurrent.ExecutionContext) =
        Promise[Message]().future // never completes
    val timeout = TimeoutMiddleware(slowAgent, 200.millis)
    val result  = timeout.process(Message.user("test")).failed
    val ex      = Await.result(result, 5.seconds)
    ex shouldBe a[TimeoutException]

  test("TimeoutMiddleware name includes inner name"):
    val inner   = MockAgent(name = "slow")
    val timeout = TimeoutMiddleware(inner, 1.second)
    timeout.name shouldBe "timeout(slow)"

  test("TimeoutMiddleware introspect"):
    val inner   = MockAgent()
    val timeout = TimeoutMiddleware(inner, 1.second)
    val r       = timeout.introspect()
    r.capabilities should contain("timeout")

  test("TimeoutMiddleware name includes timeout label"):
    val inner   = MockAgent(name = "agent")
    val timeout = TimeoutMiddleware(inner, 1.second)
    timeout.name should include("timeout")

  test("TimeoutMiddleware introspect capabilities are non-empty"):
    val inner   = MockAgent()
    val timeout = TimeoutMiddleware(inner, 1.second)
    val r       = timeout.introspect()
    r.capabilities should not be empty
