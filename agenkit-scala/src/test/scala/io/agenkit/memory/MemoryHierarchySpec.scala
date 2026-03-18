package io.agenkit.memory

import io.agenkit.core.Message
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class MemoryHierarchySpec extends AnyFunSuite with Matchers:
  test("MemoryHierarchy stores to all layers"):
    val layer1 = EphemeralMemory()
    val layer2 = EphemeralMemory()
    val hier   = MemoryHierarchy(List(layer1, layer2))
    hier.store(Message.user("test"))
    layer1.size shouldBe 1
    layer2.size shouldBe 1

  test("MemoryHierarchy retrieves from all layers and deduplicates"):
    val layer1 = EphemeralMemory()
    val layer2 = EphemeralMemory()
    val msg    = Message.user("shared content")
    layer1.store(msg)
    layer2.store(msg)
    val hier    = MemoryHierarchy(List(layer1, layer2))
    val results = hier.retrieve("shared")
    results should have size 1

  test("MemoryHierarchy clear empties all layers"):
    val layer1 = EphemeralMemory()
    val layer2 = EphemeralMemory()
    val hier   = MemoryHierarchy(List(layer1, layer2))
    hier.store(Message.user("test"))
    hier.clear()
    layer1.size shouldBe 0
    layer2.size shouldBe 0

  test("MemoryHierarchy size sums all layers"):
    val layer1 = EphemeralMemory()
    val layer2 = EphemeralMemory()
    layer1.store(Message.user("a"))
    layer2.store(Message.user("b"))
    val hier = MemoryHierarchy(List(layer1, layer2))
    hier.size shouldBe 2

  test("MemoryHierarchy works with single layer"):
    val layer = EphemeralMemory()
    val hier  = MemoryHierarchy(List(layer))
    hier.store(Message.user("single layer test"))
    hier.size shouldBe 1
    hier.retrieve("single") should not be empty

  test("MemoryHierarchy retrieve returns results from both layers"):
    val layer1 = EphemeralMemory()
    val layer2 = EphemeralMemory()
    layer1.store(Message.user("unique in layer one"))
    layer2.store(Message.user("unique in layer two"))
    val hier    = MemoryHierarchy(List(layer1, layer2))
    val results = hier.retrieve("unique")
    results should have size 2

  test("MemoryHierarchy store followed by clear yields zero size"):
    val layer1 = EphemeralMemory()
    val layer2 = EphemeralMemory()
    val hier   = MemoryHierarchy(List(layer1, layer2))
    hier.store(Message.user("a"))
    hier.store(Message.user("b"))
    hier.clear()
    hier.size shouldBe 0
