package io.agenkit.examples

import io.agenkit.core.*
import io.agenkit.helpers.{MockLlmClient, MockTool}
import io.agenkit.patterns.ReActAgent
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

/** Demonstrates a ReAct agent that uses tools to answer questions. */
object ReactAgentExample:
  def main(args: Array[String]): Unit =
    val calculatorTool = MockTool(
      name        = "calculator",
      description = "Performs arithmetic calculations",
      result      = ToolOk("42")
    )

    var turn = 0
    val llm = MockLlmClient { _ =>
      turn += 1
      if turn == 1 then
        "THOUGHT: I need to use the calculator\nACTION: calculator\nPARAMS: expr=6*7"
      else
        "ANSWER: The answer is 42"
    }

    val agent = ReActAgent(
      name          = "react-agent",
      llm           = llm,
      tools         = Map("calculator" -> calculatorTool),
      maxIterations = 5
    )

    val result = Await.result(agent.process(Message.user("What is 6 times 7?")), 10.seconds)
    println(s"Question: What is 6 times 7?")
    println(s"Answer: ${result.contentString}")
    println(s"Tool calls: ${calculatorTool.callCount}")

    val status = agent.introspect()
    println(s"Agent capabilities: ${status.capabilities.mkString(", ")}")
