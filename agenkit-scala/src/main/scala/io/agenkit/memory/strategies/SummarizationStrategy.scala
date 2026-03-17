package io.agenkit.memory.strategies

import io.agenkit.core.Message
import io.agenkit.memory.Memory

/** Periodically collapses older messages into a summary to bound memory growth. */
class SummarizationStrategy(
  maxItems: Int = 100,
  summarizeAfter: Int = 50
) extends Memory:
  private val items        = collection.mutable.ListBuffer[Message]()
  private var summaryCount = 0

  def store(message: Message): Unit =
    items.synchronized {
      items += message
      val threshold = summarizeAfter + summaryCount * summarizeAfter
      if items.size >= threshold then summarize()
    }

  def retrieve(query: String, limit: Int = 10): List[Message] =
    items.synchronized {
      items.filter(m => m.contentString.toLowerCase.contains(query.toLowerCase))
        .takeRight(limit)
        .toList
    }

  def clear(): Unit = items.synchronized { items.clear(); summaryCount = 0 }
  def size: Int     = items.synchronized { items.size }

  private def summarize(): Unit =
    val toSummarize = items.take(summarizeAfter).toList
    val preview     = toSummarize.map(_.contentString.take(20)).mkString(", ")
    val summary     = s"[Summary of ${toSummarize.size} messages: $preview...]"
    items.remove(0, summarizeAfter)
    items.prepend(Message.of("system", summary))
    summaryCount += 1
