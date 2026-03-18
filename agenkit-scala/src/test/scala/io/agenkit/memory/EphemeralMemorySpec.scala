package io.agenkit.memory

import io.agenkit.core.Message
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class EphemeralMemorySpec extends AnyFunSuite with Matchers:
  test("EphemeralMemory stores and retrieves messages"):
    val mem = EphemeralMemory()
    mem.store(Message.user("scala programming"))
    val results = mem.retrieve("scala")
    results should have size 1
    results.head.contentString should include("scala")

  test("EphemeralMemory retrieves no results for non-matching query"):
    val mem = EphemeralMemory()
    mem.store(Message.user("hello world"))
    val results = mem.retrieve("nonexistent")
    results shouldBe empty

  test("EphemeralMemory clear empties storage"):
    val mem = EphemeralMemory()
    mem.store(Message.user("test"))
    mem.clear()
    mem.size shouldBe 0
    mem.retrieve("test") shouldBe empty

  test("EphemeralMemory size returns count"):
    val mem = EphemeralMemory()
    mem.store(Message.user("a"))
    mem.store(Message.user("b"))
    mem.size shouldBe 2

  test("EphemeralMemory evicts oldest when at capacity"):
    val mem = EphemeralMemory(maxSize = 2)
    mem.store(Message.user("first"))
    mem.store(Message.user("second"))
    mem.store(Message.user("third"))
    mem.size shouldBe 2
    mem.retrieve("first") shouldBe empty

  test("EphemeralMemory respects limit parameter"):
    val mem = EphemeralMemory()
    (1 to 10).foreach(i => mem.store(Message.user(s"item $i")))
    val results = mem.retrieve("item", limit = 3)
    results.size should be <= 3

  test("EphemeralMemory stores assistant messages"):
    val mem = EphemeralMemory()
    mem.store(Message.assistant("assistant reply"))
    mem.size shouldBe 1
    mem.retrieve("assistant") should not be empty

  test("EphemeralMemory retrieve returns messages with matching content"):
    val mem = EphemeralMemory()
    mem.store(Message.user("machine learning"))
    mem.store(Message.user("deep neural networks"))
    mem.store(Message.user("cooking pasta"))
    val results = mem.retrieve("learning")
    results.foreach(r => r.contentString should include("learning"))

  test("EphemeralMemory default maxSize is larger than small stores"):
    val mem = EphemeralMemory()
    (1 to 5).foreach(i => mem.store(Message.user(s"msg $i")))
    mem.size shouldBe 5
