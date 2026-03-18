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

  test("ReflectionAgent name getter"):
    val agent = ReflectionAgent("my-reflect", MockLlmClient())
    agent.name shouldBe "my-reflect"

  test("ReflectionAgent capabilities contain reflection"):
    val agent = ReflectionAgent("reflect", MockLlmClient())
    agent.capabilities should contain("reflection")

  test("ReflectionAgent introspect returns name"):
    val agent = ReflectionAgent("reflect-agent", MockLlmClient())
    agent.introspect().name shouldBe "reflect-agent"

  test("ReflectionAgent with one round calls LLM twice"):
    val llm   = MockLlmClient()
    val agent = ReflectionAgent("reflect", llm, reflectionRounds = 1)
    Await.result(agent.process(Message.user("test")), 5.seconds)
    llm.callCount shouldBe 2

  test("ReflectionAgent multiple sequential calls"):
    val llm   = MockLlmClient(_ => "refined answer")
    val agent = ReflectionAgent("reflect", llm, reflectionRounds = 0)
    val r1    = Await.result(agent.process(Message.user("first")), 5.seconds)
    val r2    = Await.result(agent.process(Message.user("second")), 5.seconds)
    r1.contentString shouldBe "refined answer"
    r2.contentString shouldBe "refined answer"
