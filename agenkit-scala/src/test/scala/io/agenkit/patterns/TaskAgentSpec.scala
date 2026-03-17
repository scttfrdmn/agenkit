package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockLlmClient
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global
import scala.util.{Failure, Success}

class TaskAgentSpec extends AnyFunSuite with Matchers:
  test("TaskAgent starts as Pending"):
    val llm   = MockLlmClient()
    val agent = TaskAgent("task", llm)
    agent.status shouldBe TaskStatus.Pending

  test("TaskAgent transitions to Complete on success"):
    val llm   = MockLlmClient()
    val agent = TaskAgent("task", llm)
    Await.result(agent.process(Message.user("do task")), 5.seconds)
    agent.status shouldBe TaskStatus.Complete

  test("TaskAgent transitions to Failed on error"):
    val llm   = MockLlmClient(shouldFail = true)
    val agent = TaskAgent("task", llm)
    val result = agent.process(Message.user("fail")).transform {
      case Failure(_) => Success(())
      case Success(_) => Success(())
    }
    Await.result(result, 5.seconds)
    agent.status shouldBe TaskStatus.Failed

  test("TaskAgent returns response from LLM"):
    val llm    = MockLlmClient(_ => "task done")
    val agent  = TaskAgent("task-agent", llm)
    val result = Await.result(agent.process(Message.user("do it")), 5.seconds)
    result.contentString shouldBe "task done"

  test("TaskAgent introspect"):
    val llm   = MockLlmClient()
    val agent = TaskAgent("task-agent", llm)
    val r     = agent.introspect()
    r.name shouldBe "task-agent"
    r.capabilities should contain("task")
