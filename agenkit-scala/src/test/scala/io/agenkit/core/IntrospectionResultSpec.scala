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
