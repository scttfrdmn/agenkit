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
