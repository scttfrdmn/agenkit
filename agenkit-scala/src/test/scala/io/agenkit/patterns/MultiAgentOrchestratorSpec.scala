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

  test("MultiAgentOrchestrator returns assistant role"):
    val llm    = MockLlmClient(_ => "worker")
    val worker = MockAgent(name = "worker", response = "worker reply")
    val agent  = MultiAgentOrchestrator("mao", llm, Map("worker" -> worker))
    val result = Await.result(agent.process(Message.user("go")), 5.seconds)
    result.role shouldBe "assistant"

  test("MultiAgentOrchestrator name getter"):
    val agent = MultiAgentOrchestrator("my-mao", MockLlmClient(), Map("a" -> MockAgent()))
    agent.name shouldBe "my-mao"

  test("MultiAgentOrchestrator capabilities contain multi-agent"):
    val agent = MultiAgentOrchestrator("mao", MockLlmClient(), Map("a" -> MockAgent()))
    agent.capabilities should contain("multi-agent")

  test("MultiAgentOrchestrator introspect returns name"):
    val agent = MultiAgentOrchestrator("mao-agent", MockLlmClient(), Map("a" -> MockAgent()))
    agent.introspect().name shouldBe "mao-agent"

  test("MultiAgentOrchestrator calls target agent exactly once"):
    val llm    = MockLlmClient(_ => "target")
    val target = MockAgent(name = "target", response = "targeted")
    val other  = MockAgent(name = "other", response = "other")
    val agent  = MultiAgentOrchestrator("mao", llm, Map("target" -> target, "other" -> other))
    Await.result(agent.process(Message.user("route")), 5.seconds)
    target.callCount shouldBe 1
    other.callCount shouldBe 0

  test("MultiAgentOrchestrator multiple sequential calls"):
    val llm    = MockLlmClient(_ => "spec")
    val spec   = MockAgent(name = "spec", response = "ok")
    val agent  = MultiAgentOrchestrator("mao", llm, Map("spec" -> spec))
    val r1     = Await.result(agent.process(Message.user("first")), 5.seconds)
    val r2     = Await.result(agent.process(Message.user("second")), 5.seconds)
    r1.role shouldBe "assistant"
    r2.role shouldBe "assistant"
