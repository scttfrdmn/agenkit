package io.agenkit.memory

import io.agenkit.core.Message

/** In-memory storage with a bounded capacity; oldest entries are evicted first. */
class EphemeralMemory(
  maxSize: Int = 1000
) extends Memory:
  private val items = collection.mutable.ListBuffer[Message]()

  def store(message: Message): Unit =
    items.synchronized {
      items += message
      if items.size > maxSize then items.remove(0)
    }

  def retrieve(query: String, limit: Int = 10): List[Message] =
    items.synchronized {
      val q = query.toLowerCase
      items.filter(m => m.contentString.toLowerCase.contains(q))
        .takeRight(limit)
        .toList
    }

  def clear(): Unit = items.synchronized { items.clear() }
  def size: Int     = items.synchronized { items.size }
