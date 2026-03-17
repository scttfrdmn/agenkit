package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.{MockAgent, MockLlmClient}
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class MultiAgentOrchestratorSpec extends AnyFunSuite with Matchers:
  test("MultiAgentOrchestrator routes to correct agent"):
    val llm    = MockLlmClient(_ => "specialist")
    val spec   = MockAgent(name = "specialist", response = "specialist answer")
    val agent  = MultiAgentOrchestrator("mao", llm, Map("specialist" -> spec))
    val result = Await.result(agent.process(Message.user("complex question")), 5.seconds)
    result.contentString shouldBe "specialist answer"

  test("MultiAgentOrchestrator handles unknown agent"):
    val llm   = MockLlmClient(_ => "nonexistent")
    val agent = MultiAgentOrchestrator("mao", llm, Map.empty)
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString should include("not found")

  test("MultiAgentOrchestrator introspect"):
    val llm   = MockLlmClient()
    val agent = MultiAgentOrchestrator("mao", llm, Map("a" -> MockAgent()))
    val r     = agent.introspect()
    r.name shouldBe "mao"
    r.capabilities should contain("multi-agent")
