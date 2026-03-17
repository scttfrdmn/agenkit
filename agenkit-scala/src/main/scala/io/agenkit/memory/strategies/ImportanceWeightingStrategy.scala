package io.agenkit.memory.strategies

import io.agenkit.core.Message
import io.agenkit.memory.Memory

/** Evicts the least-important message when at capacity.  Importance is based on role and length. */
class ImportanceWeightingStrategy(
  maxSize: Int = 1000
) extends Memory:
  private val items = collection.mutable.ListBuffer[(Message, Double)]()

  def store(message: Message): Unit =
    items.synchronized {
      val importance = computeImportance(message)
      items += (message -> importance)
      if items.size > maxSize then
        val minIdx = items.zipWithIndex.minBy(_._1._2)._2
        items.remove(minIdx)
    }

  def retrieve(query: String, limit: Int = 10): List[Message] =
    items.synchronized {
      items.sortBy(-_._2).take(limit).map(_._1).toList
    }

  def clear(): Unit = items.synchronized { items.clear() }
  def size: Int     = items.synchronized { items.size }

  private def computeImportance(message: Message): Double =
    val lengthScore = math.min(message.contentString.length.toDouble / 100.0, 1.0)
    val roleScore = message.role match
      case "system"    => 1.0
      case "user"      => 0.7
      case _           => 0.5
    (lengthScore + roleScore) / 2.0
