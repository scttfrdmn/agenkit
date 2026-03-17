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
