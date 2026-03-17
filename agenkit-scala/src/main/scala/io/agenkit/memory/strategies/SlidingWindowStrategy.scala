package io.agenkit.memory.strategies

import io.agenkit.core.Message
import io.agenkit.memory.Memory

/** Keeps only the most recent `windowSize` messages. */
class SlidingWindowStrategy(
  windowSize: Int = 20
) extends Memory:
  private val window = collection.mutable.ArrayDeque[Message]()

  def store(message: Message): Unit =
    window.synchronized {
      window.addOne(message)
      while window.size > windowSize do window.removeHead()
    }

  def retrieve(query: String, limit: Int = 10): List[Message] =
    window.synchronized { window.takeRight(limit).toList }

  def clear(): Unit = window.synchronized { window.clear() }
  def size: Int     = window.synchronized { window.size }
