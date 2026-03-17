package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.{MockLlmClient, MockTool}
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class ReActAgentSpec extends AnyFunSuite with Matchers:
  test("ReActAgent returns ANSWER directly"):
    val llm   = MockLlmClient(_ => "ANSWER: 42")
    val agent = ReActAgent("test", llm)
    val result = Await.result(agent.process(Message.user("What is 6 * 7?")), 5.seconds)
    result.contentString shouldBe "42"

  test("ReActAgent uses tool and returns answer"):
    var iteration = 0
    val llm = MockLlmClient { _ =>
      iteration += 1
      if iteration == 1 then "THOUGHT: use calc\nACTION: calc\nPARAMS: x=6"
      else "ANSWER: tool said tool result"
    }
    val tool  = MockTool(name = "calc")
    val agent = ReActAgent("test", llm, tools = Map("calc" -> tool))
    val result = Await.result(agent.process(Message.user("compute")), 5.seconds)
    result.contentString should include("tool said")
    tool.callCount shouldBe 1

  test("ReActAgent handles missing tool gracefully"):
    var iteration = 0
    val llm = MockLlmClient { _ =>
      iteration += 1
      if iteration == 1 then "ACTION: nonexistent\nPARAMS: "
      else "ANSWER: done"
    }
    val agent  = ReActAgent("test", llm)
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "done"

  test("ReActAgent respects maxIterations"):
    val llm   = MockLlmClient(_ => "THOUGHT: still thinking")
    val agent = ReActAgent("test", llm, maxIterations = 2)
    val result = Await.result(agent.process(Message.user("loop")), 5.seconds)
    result.contentString should include("Max iterations")

  test("ReActAgent introspect"):
    val llm   = MockLlmClient()
    val agent = ReActAgent("react-agent", llm)
    val r     = agent.introspect()
    r.name shouldBe "react-agent"
    r.capabilities should contain("react")
