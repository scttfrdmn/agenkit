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
