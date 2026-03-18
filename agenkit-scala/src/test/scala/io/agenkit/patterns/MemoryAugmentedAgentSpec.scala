package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockLlmClient
import io.agenkit.memory.EphemeralMemory
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class MemoryAugmentedAgentSpec extends AnyFunSuite with Matchers:
  test("MemoryAugmentedAgent processes message and stores exchange"):
    val llm    = MockLlmClient()
    val memory = EphemeralMemory()
    val agent  = MemoryAugmentedAgent("maa", llm, memory)
    Await.result(agent.process(Message.user("hello")), 5.seconds)
    memory.size shouldBe 2

  test("MemoryAugmentedAgent retrieves relevant memories"):
    val llm    = MockLlmClient()
    val memory = EphemeralMemory()
    memory.store(Message.user("I like Scala"))
    val agent  = MemoryAugmentedAgent("maa", llm, memory)
    val result = Await.result(agent.process(Message.user("Tell me about Scala")), 5.seconds)
    result.role shouldBe "assistant"
    // LLM should have received context with the memory
    llm.conversations.head.head.contentString should include("Scala")

  test("MemoryAugmentedAgent introspect"):
    val llm    = MockLlmClient()
    val memory = EphemeralMemory()
    val agent  = MemoryAugmentedAgent("maa", llm, memory)
    val r      = agent.introspect()
    r.name shouldBe "maa"
    r.capabilities should contain("memory-augmented")

  test("MemoryAugmentedAgent returns assistant role"):
    val llm    = MockLlmClient()
    val memory = EphemeralMemory()
    val agent  = MemoryAugmentedAgent("maa", llm, memory)
    val result = Await.result(agent.process(Message.user("hello")), 5.seconds)
    result.role shouldBe "assistant"

  test("MemoryAugmentedAgent name getter"):
    val agent = MemoryAugmentedAgent("my-maa", MockLlmClient(), EphemeralMemory())
    agent.name shouldBe "my-maa"

  test("MemoryAugmentedAgent capabilities contain memory-augmented"):
    val agent = MemoryAugmentedAgent("maa", MockLlmClient(), EphemeralMemory())
    agent.capabilities should contain("memory-augmented")

  test("MemoryAugmentedAgent introspect returns name"):
    val agent = MemoryAugmentedAgent("maa-agent", MockLlmClient(), EphemeralMemory())
    agent.introspect().name shouldBe "maa-agent"

  test("MemoryAugmentedAgent accumulates memory across calls"):
    val llm    = MockLlmClient()
    val memory = EphemeralMemory()
    val agent  = MemoryAugmentedAgent("maa", llm, memory)
    Await.result(agent.process(Message.user("first")), 5.seconds)
    Await.result(agent.process(Message.user("second")), 5.seconds)
    memory.size shouldBe 4

  test("MemoryAugmentedAgent empty memory still processes message"):
    val llm    = MockLlmClient(_ => "response")
    val memory = EphemeralMemory()
    val agent  = MemoryAugmentedAgent("maa", llm, memory)
    val result = Await.result(agent.process(Message.user("go")), 5.seconds)
    result.contentString shouldBe "response"
