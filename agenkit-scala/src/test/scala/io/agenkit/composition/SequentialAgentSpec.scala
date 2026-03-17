package io.agenkit.composition

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class SequentialAgentSpec extends AnyFunSuite with Matchers:
  test("SequentialAgent passes output of one stage as input to next"):
    val stage1 = MockAgent(name = "s1", response = "stage1 output")
    val stage2 = MockAgent(name = "s2", response = "stage2 output")
    val agent  = SequentialAgent("seq", List(stage1, stage2))
    val result = Await.result(agent.process(Message.user("start")), 5.seconds)
    result.contentString shouldBe "stage2 output"
    stage1.callCount shouldBe 1
    stage2.callCount shouldBe 1

  test("SequentialAgent with empty stages returns input"):
    val agent  = SequentialAgent("seq", List.empty)
    val msg    = Message.user("unchanged")
    val result = Await.result(agent.process(msg), 5.seconds)
    result.contentString shouldBe "unchanged"

  test("SequentialAgent introspect"):
    val agent = SequentialAgent("seq", List(MockAgent(), MockAgent()))
    val r     = agent.introspect()
    r.name shouldBe "seq"
    r.capabilities should contain("sequential")
    r.metadata("stageCount") shouldBe 2
