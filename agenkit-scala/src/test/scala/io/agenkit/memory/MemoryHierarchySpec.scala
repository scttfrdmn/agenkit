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
