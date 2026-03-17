package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.{MockLlmClient, MockTool}
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class ReasoningWithToolsAgentSpec extends AnyFunSuite with Matchers:
  test("ReasoningWithToolsAgent returns ANSWER"):
    val llm   = MockLlmClient(_ => "THINK: simple\nANSWER: 42")
    val agent = ReasoningWithToolsAgent("rta", llm)
    val result = Await.result(agent.process(Message.user("what is 6*7")), 5.seconds)
    result.contentString shouldBe "42"

  test("ReasoningWithToolsAgent uses tool"):
    var step = 0
    val llm = MockLlmClient { _ =>
      step += 1
      if step == 1 then "USE_TOOL: calc with params x=6"
      else "ANSWER: tool worked"
    }
    val tool  = MockTool(name = "calc")
    val agent = ReasoningWithToolsAgent("rta", llm, tools = Map("calc" -> tool))
    val result = Await.result(agent.process(Message.user("compute")), 5.seconds)
    result.contentString shouldBe "tool worked"
    tool.callCount shouldBe 1

  test("ReasoningWithToolsAgent respects maxSteps"):
    val llm   = MockLlmClient(_ => "THINK: still thinking")
    val agent = ReasoningWithToolsAgent("rta", llm, maxSteps = 2)
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString should include("Max reasoning steps")

  test("ReasoningWithToolsAgent introspect"):
    val llm   = MockLlmClient()
    val agent = ReasoningWithToolsAgent("rta", llm)
    val r     = agent.introspect()
    r.name shouldBe "rta"
    r.capabilities should contain("reasoning")
