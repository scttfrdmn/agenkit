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

  test("OrchestrationAgent returns assistant role"):
    val sub   = MockAgent(name = "sub", response = "sub result")
    val agent = OrchestrationAgent("orch", List(sub), OrchestrationMode.Sequential)
    val result = Await.result(agent.process(Message.user("run")), 5.seconds)
    result.role shouldBe "assistant"

  test("OrchestrationAgent name getter"):
    val agent = OrchestrationAgent("my-orch", List(MockAgent()))
    agent.name shouldBe "my-orch"

  test("OrchestrationAgent capabilities contain orchestration"):
    val agent = OrchestrationAgent("orch", List(MockAgent()))
    agent.capabilities should contain("orchestration")

  test("OrchestrationAgent introspect returns name"):
    val agent = OrchestrationAgent("orch-agent", List(MockAgent()))
    agent.introspect().name shouldBe "orch-agent"

  test("OrchestrationAgent sequential calls each sub-agent once"):
    val a1    = MockAgent(name = "a1", response = "r1")
    val a2    = MockAgent(name = "a2", response = "r2")
    val agent = OrchestrationAgent("orch", List(a1, a2), OrchestrationMode.Sequential)
    Await.result(agent.process(Message.user("go")), 5.seconds)
    a1.callCount shouldBe 1
    a2.callCount shouldBe 1
