package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class OrchestrationAgentSpec extends AnyFunSuite with Matchers:
  test("OrchestrationAgent sequential mode chains agents"):
    val agent1 = MockAgent(name = "a1", response = "step1")
    val agent2 = MockAgent(name = "a2", response = "step2")
    val agent  = OrchestrationAgent("orch", List(agent1, agent2), OrchestrationMode.Sequential)
    val result = Await.result(agent.process(Message.user("start")), 5.seconds)
    result.contentString shouldBe "step2"

  test("OrchestrationAgent parallel mode fans out"):
    val agent1 = MockAgent(name = "a1", response = "r1")
    val agent2 = MockAgent(name = "a2", response = "r2")
    val agent  = OrchestrationAgent("orch", List(agent1, agent2), OrchestrationMode.Parallel)
    val result = Await.result(agent.process(Message.user("go")), 5.seconds)
    result.contentString should include("r1")
    result.contentString should include("r2")

  test("OrchestrationAgent router mode dispatches by name"):
    val target = MockAgent(name = "target", response = "targeted")
    val agent  = OrchestrationAgent(
      "orch",
      List(target),
      OrchestrationMode.Router,
      routingFunction = _ => "target"
    )
    val result = Await.result(agent.process(Message.user("go")), 5.seconds)
    result.contentString shouldBe "targeted"

  test("OrchestrationAgent introspect"):
    val agent = OrchestrationAgent("orch", List(MockAgent()))
    val r     = agent.introspect()
    r.name shouldBe "orch"
    r.capabilities should contain("orchestration")
