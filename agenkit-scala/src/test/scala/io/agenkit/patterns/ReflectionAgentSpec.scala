package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockLlmClient
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class ReflectionAgentSpec extends AnyFunSuite with Matchers:
  test("ReflectionAgent processes message"):
    val llm    = MockLlmClient()
    val agent  = ReflectionAgent("reflect", llm)
    val result = Await.result(agent.process(Message.user("hello")), 5.seconds)
    result.role shouldBe "assistant"

  test("ReflectionAgent with zero rounds returns initial response"):
    val llm   = MockLlmClient(_ => "initial")
    val agent = ReflectionAgent("reflect", llm, reflectionRounds = 0)
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "initial"

  test("ReflectionAgent calls LLM reflectionRounds + 1 times"):
    val llm   = MockLlmClient()
    val agent = ReflectionAgent("reflect", llm, reflectionRounds = 2)
    Await.result(agent.process(Message.user("test")), 5.seconds)
    llm.callCount shouldBe 3

  test("ReflectionAgent introspect"):
    val llm   = MockLlmClient()
    val agent = ReflectionAgent("reflect", llm)
    val r     = agent.introspect()
    r.name shouldBe "reflect"
    r.capabilities should contain("reflection")
