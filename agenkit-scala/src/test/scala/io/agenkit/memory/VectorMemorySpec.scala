package io.agenkit.memory

import io.agenkit.core.Message
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class VectorMemorySpec extends AnyFunSuite with Matchers:
  test("VectorMemory stores messages"):
    val mem = VectorMemory()
    mem.store(Message.user("hello world"))
    mem.size shouldBe 1

  test("VectorMemory retrieves similar messages first"):
    val mem = VectorMemory()
    mem.store(Message.user("scala functional programming"))
    mem.store(Message.user("java object oriented"))
    mem.store(Message.user("cooking recipes food"))
    val results = mem.retrieve("scala programming", limit = 1)
    results should have size 1
    results.head.contentString should include("scala")

  test("VectorMemory clear empties storage"):
    val mem = VectorMemory()
    mem.store(Message.user("test"))
    mem.clear()
    mem.size shouldBe 0

  test("VectorMemory retrieve from empty returns empty"):
    val mem = VectorMemory()
    mem.retrieve("query") shouldBe empty

  test("VectorMemory respects maxSize"):
    val mem = VectorMemory(maxSize = 2)
    mem.store(Message.user("first"))
    mem.store(Message.user("second"))
    mem.store(Message.user("third"))
    mem.size shouldBe 2
