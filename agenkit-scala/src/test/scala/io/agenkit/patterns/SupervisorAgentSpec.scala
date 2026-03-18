package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.{MockAgent, MockLlmClient}
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class SupervisorAgentSpec extends AnyFunSuite with Matchers:
  test("SupervisorAgent delegates to workers"):
    val llm      = MockLlmClient(_ => "worker1: do task A\nworker2: do task B")
    val worker1  = MockAgent(name = "worker1", response = "result A")
    val worker2  = MockAgent(name = "worker2", response = "result B")
    val agent    = SupervisorAgent("super", llm, List(worker1, worker2))
    val result   = Await.result(agent.process(Message.user("do work")), 5.seconds)
    result.contentString should (include("result A") or include("result B"))

  test("SupervisorAgent introspect"):
    val llm   = MockLlmClient()
    val agent = SupervisorAgent("super", llm, List(MockAgent()))
    val r     = agent.introspect()
    r.name shouldBe "super"
    r.capabilities should contain("supervision")

  test("SupervisorAgent returns assistant role"):
    val llm    = MockLlmClient(_ => "worker1: task")
    val worker = MockAgent(name = "worker1", response = "done")
    val agent  = SupervisorAgent("super", llm, List(worker))
    val result = Await.result(agent.process(Message.user("go")), 5.seconds)
    result.role shouldBe "assistant"

  test("SupervisorAgent name getter"):
    val agent = SupervisorAgent("my-supervisor", MockLlmClient(), List(MockAgent()))
    agent.name shouldBe "my-supervisor"

  test("SupervisorAgent capabilities contain supervision"):
    val agent = SupervisorAgent("super", MockLlmClient(), List(MockAgent()))
    agent.capabilities should contain("supervision")

  test("SupervisorAgent introspect returns name"):
    val agent = SupervisorAgent("sup-agent", MockLlmClient(), List(MockAgent()))
    agent.introspect().name shouldBe "sup-agent"

  test("SupervisorAgent introspect has metadata"):
    val agent = SupervisorAgent("super", MockLlmClient(), List(MockAgent()))
    val r     = agent.introspect()
    r.metadata should not be null

  test("SupervisorAgent works with single worker"):
    val llm    = MockLlmClient(_ => "worker1: task")
    val worker = MockAgent(name = "worker1", response = "single result")
    val agent  = SupervisorAgent("super", llm, List(worker))
    val result = Await.result(agent.process(Message.user("do one thing")), 5.seconds)
    result.contentString should include("single result")

  test("SupervisorAgent multiple sequential calls"):
    val llm    = MockLlmClient(_ => "worker1: task")
    val worker = MockAgent(name = "worker1", response = "ok")
    val agent  = SupervisorAgent("super", llm, List(worker))
    val r1     = Await.result(agent.process(Message.user("first")), 5.seconds)
    val r2     = Await.result(agent.process(Message.user("second")), 5.seconds)
    r1.role shouldBe "assistant"
    r2.role shouldBe "assistant"
