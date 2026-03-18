package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockLlmClient
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class AutonomousAgentSpec extends AnyFunSuite with Matchers:
  test("AutonomousAgent stops when goal is met"):
    val llm   = MockLlmClient(_ => "Goal is COMPLETE")
    val agent = AutonomousAgent("auto", llm)
    val result = Await.result(agent.process(Message.user("do it")), 5.seconds)
    result.contentString should include("COMPLETE")
    llm.callCount shouldBe 1

  test("AutonomousAgent hits max iterations"):
    val llm   = MockLlmClient(_ => "still working...")
    val agent = AutonomousAgent("auto", llm, maxIterations = 3)
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString should include("max iterations")
    llm.callCount shouldBe 3

  test("AutonomousAgent with custom goal checker"):
    val llm   = MockLlmClient(_ => "DONE")
    val agent = AutonomousAgent("auto", llm, goalChecker = _.contains("DONE"))
    val result = Await.result(agent.process(Message.user("go")), 5.seconds)
    result.contentString shouldBe "DONE"

  test("AutonomousAgent introspect"):
    val llm   = MockLlmClient()
    val agent = AutonomousAgent("auto", llm)
    val r     = agent.introspect()
    r.name shouldBe "auto"
    r.capabilities should contain("autonomous")

  test("AutonomousAgent returns assistant role"):
    val llm    = MockLlmClient(_ => "COMPLETE")
    val agent  = AutonomousAgent("auto", llm)
    val result = Await.result(agent.process(Message.user("run")), 5.seconds)
    result.role shouldBe "assistant"

  test("AutonomousAgent name getter"):
    val agent = AutonomousAgent("my-auto", MockLlmClient())
    agent.name shouldBe "my-auto"

  test("AutonomousAgent capabilities contain autonomous"):
    val agent = AutonomousAgent("auto", MockLlmClient())
    agent.capabilities should contain("autonomous")

  test("AutonomousAgent introspect returns name"):
    val agent = AutonomousAgent("auto-agent", MockLlmClient())
    agent.introspect().name shouldBe "auto-agent"

  test("AutonomousAgent with maxIterations of 1 makes exactly one LLM call"):
    val llm   = MockLlmClient(_ => "still going")
    val agent = AutonomousAgent("auto", llm, maxIterations = 1)
    Await.result(agent.process(Message.user("test")), 5.seconds)
    llm.callCount shouldBe 1
