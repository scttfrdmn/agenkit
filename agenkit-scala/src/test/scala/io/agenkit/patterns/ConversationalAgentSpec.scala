package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockLlmClient
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class ConversationalAgentSpec extends AnyFunSuite with Matchers:
  test("ConversationalAgent processes message and returns assistant response"):
    val llm    = MockLlmClient()
    val agent  = ConversationalAgent("test", llm)
    val result = Await.result(agent.process(Message.user("hello")), 5.seconds)
    result.role shouldBe "assistant"

  test("ConversationalAgent maintains conversation history"):
    val llm   = MockLlmClient()
    val agent = ConversationalAgent("test", llm)
    Await.result(agent.process(Message.user("hello")), 5.seconds)
    agent.getHistory should have size 2

  test("ConversationalAgent with system prompt"):
    val llm   = MockLlmClient()
    val agent = ConversationalAgent("test", llm, systemPrompt = Some("You are helpful"))
    val result = Await.result(agent.process(Message.user("hi")), 5.seconds)
    result.role shouldBe "assistant"
    llm.conversations.head.head.role shouldBe "system"

  test("ConversationalAgent clear history"):
    val llm   = MockLlmClient()
    val agent = ConversationalAgent("test", llm)
    Await.result(agent.process(Message.user("hello")), 5.seconds)
    agent.clearHistory()
    agent.getHistory shouldBe empty

  test("ConversationalAgent introspect"):
    val llm    = MockLlmClient()
    val agent  = ConversationalAgent("test-agent", llm)
    val result = agent.introspect()
    result.name shouldBe "test-agent"
    result.capabilities should contain("conversation")

  test("ConversationalAgent accumulates multiple turns"):
    val llm   = MockLlmClient()
    val agent = ConversationalAgent("test", llm)
    Await.result(agent.process(Message.user("first")), 5.seconds)
    Await.result(agent.process(Message.user("second")), 5.seconds)
    agent.getHistory should have size 4

  test("ConversationalAgent name getter"):
    val agent = ConversationalAgent("my-agent", MockLlmClient())
    agent.name shouldBe "my-agent"

  test("ConversationalAgent capabilities contain conversation"):
    val agent = ConversationalAgent("test", MockLlmClient())
    agent.capabilities should contain("conversation")

  test("ConversationalAgent content includes LLM response"):
    val llm    = MockLlmClient(_ => "hello back")
    val agent  = ConversationalAgent("test", llm)
    val result = Await.result(agent.process(Message.user("hello")), 5.seconds)
    result.contentString shouldBe "hello back"
