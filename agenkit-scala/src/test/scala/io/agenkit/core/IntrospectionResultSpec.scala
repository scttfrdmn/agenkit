package io.agenkit.core

import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class IntrospectionResultSpec extends AnyFunSuite with Matchers:
  test("IntrospectionResult has name"):
    val r = IntrospectionResult("agent1")
    r.name shouldBe "agent1"

  test("IntrospectionResult defaults"):
    val r = IntrospectionResult("agent1")
    r.metadata shouldBe Map.empty
    r.capabilities shouldBe List.empty
    r.activeConnections shouldBe 0
    r.processedMessages shouldBe 0L

  test("IntrospectionResult with metadata"):
    val r = IntrospectionResult(
      name = "agent1",
      metadata = Map("key" -> "value"),
      capabilities = List("chat"),
      activeConnections = 2,
      processedMessages = 100L
    )
    r.metadata("key") shouldBe "value"
    r.capabilities shouldBe List("chat")
    r.activeConnections shouldBe 2
    r.processedMessages shouldBe 100L

  test("IntrospectionResult copy updates fields"):
    val r     = IntrospectionResult("agent1", processedMessages = 5L)
    val updated = r.copy(processedMessages = 10L)
    updated.name shouldBe "agent1"
    updated.processedMessages shouldBe 10L

  test("IntrospectionResult multiple capabilities"):
    val r = IntrospectionResult("agent1", capabilities = List("chat", "tool-use", "memory"))
    r.capabilities should have size 3
    r.capabilities should contain("tool-use")
