package io.agenkit.composition

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class ParallelAgentSpec extends AnyFunSuite with Matchers:
  test("ParallelAgent runs all agents and merges responses"):
    val a1     = MockAgent(name = "a1", response = "r1")
    val a2     = MockAgent(name = "a2", response = "r2")
    val agent  = ParallelAgent("par", List(a1, a2))
    val result = Await.result(agent.process(Message.user("go")), 5.seconds)
    result.contentString should include("r1")
    result.contentString should include("r2")
    a1.callCount shouldBe 1
    a2.callCount shouldBe 1

  test("ParallelAgent custom merger"):
    val a1    = MockAgent(name = "a1", response = "hello")
    val a2    = MockAgent(name = "a2", response = "world")
    val agent = ParallelAgent("par", List(a1, a2), merger = msgs => Message.of("assistant", msgs.map(_.contentString).mkString(" ")))
    val result = Await.result(agent.process(Message.user("go")), 5.seconds)
    result.contentString shouldBe "hello world"

  test("ParallelAgent introspect"):
    val agent = ParallelAgent("par", List(MockAgent()))
    val r     = agent.introspect()
    r.name shouldBe "par"
    r.capabilities should contain("parallel")
