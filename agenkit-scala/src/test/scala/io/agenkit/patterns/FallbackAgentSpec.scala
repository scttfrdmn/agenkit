package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class FallbackAgentSpec extends AnyFunSuite with Matchers:
  test("FallbackAgent uses first agent when it succeeds"):
    val first  = MockAgent(name = "first", response = "first response")
    val second = MockAgent(name = "second", response = "second response")
    val agent  = FallbackAgent("fallback", List(first, second))
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "first response"
    second.callCount shouldBe 0

  test("FallbackAgent falls back to second agent on first failure"):
    val first  = MockAgent(name = "first", shouldFail = true)
    val second = MockAgent(name = "second", response = "fallback response")
    val agent  = FallbackAgent("fallback", List(first, second))
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "fallback response"

  test("FallbackAgent fails when all agents fail"):
    val first  = MockAgent(shouldFail = true)
    val second = MockAgent(shouldFail = true)
    val agent  = FallbackAgent("fallback", List(first, second))
    val result = agent.process(Message.user("test")).failed
    val ex     = Await.result(result, 5.seconds)
    ex.getMessage should include("All agents failed")

  test("FallbackAgent introspect"):
    val agent = FallbackAgent("fallback", List(MockAgent()))
    val r     = agent.introspect()
    r.name shouldBe "fallback"
    r.capabilities should contain("fallback")

  test("FallbackAgent returns assistant role on success"):
    val first  = MockAgent(name = "first", response = "ok")
    val agent  = FallbackAgent("fallback", List(first))
    val result = Await.result(agent.process(Message.user("hi")), 5.seconds)
    result.role shouldBe "assistant"

  test("FallbackAgent name getter"):
    val agent = FallbackAgent("my-fallback", List(MockAgent()))
    agent.name shouldBe "my-fallback"

  test("FallbackAgent capabilities contain fallback"):
    val agent = FallbackAgent("fallback", List(MockAgent()))
    agent.capabilities should contain("fallback")

  test("FallbackAgent introspect returns name"):
    val agent = FallbackAgent("fallback-agent", List(MockAgent()))
    agent.introspect().name shouldBe "fallback-agent"

  test("FallbackAgent multiple sequential calls each succeed via first agent"):
    val first = MockAgent(name = "first", response = "good")
    val agent = FallbackAgent("fallback", List(first))
    val r1    = Await.result(agent.process(Message.user("one")), 5.seconds)
    val r2    = Await.result(agent.process(Message.user("two")), 5.seconds)
    r1.contentString shouldBe "good"
    r2.contentString shouldBe "good"
    first.callCount shouldBe 2
