package io.agenkit.memory

import io.agenkit.core.Message

/** Composite memory that stores to all layers and merges retrieval results. */
class MemoryHierarchy(
  layers: List[Memory]
) extends Memory:
  def store(message: Message): Unit =
    layers.foreach(_.store(message))

  def retrieve(query: String, limit: Int = 10): List[Message] =
    layers.flatMap(_.retrieve(query, limit)).distinct.take(limit)

  def clear(): Unit = layers.foreach(_.clear())
  def size: Int     = layers.map(_.size).sum
