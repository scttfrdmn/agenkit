package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockLlmClient
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class PlanningAgentSpec extends AnyFunSuite with Matchers:
  test("PlanningAgent produces a plan and executes it"):
    var callNum = 0
    val llm = MockLlmClient { _ =>
      callNum += 1
      if callNum == 1 then "1. Step one\n2. Step two"
      else s"result $callNum"
    }
    val agent  = PlanningAgent("planner", llm)
    val result = Await.result(agent.process(Message.user("do something")), 5.seconds)
    result.contentString should include("Plan executed")

  test("PlanningAgent with empty plan returns empty result"):
    val llm    = MockLlmClient(_ => "no numbered steps here")
    val agent  = PlanningAgent("planner", llm)
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.role shouldBe "assistant"

  test("PlanningAgent introspect"):
    val llm   = MockLlmClient()
    val agent = PlanningAgent("planner", llm)
    val r     = agent.introspect()
    r.name shouldBe "planner"
    r.capabilities should contain("planning")
